"""AI API Interface"""
from ..common_imports import *
from ..models.api_config import APIConfig
from .chat_manager import PromptFormatter
from ..utils.file_manager import get_app_data_dir


def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 1 token ≈ 4 characters)"""
    return len(text) // 4

def get_model_context_defaults():
    """Get default context sizes for popular models"""
    return {
        # OpenAI Models
        "gpt-3.5-turbo": 4096,
        "gpt-3.5-turbo-16k": 16384,
        "gpt-4": 8192,
        "gpt-4-32k": 32768,
        "gpt-4-turbo": 128000,
        "gpt-4o": 128000,
        
        # Anthropic Models
        "claude-3-haiku-20240307": 200000,
        "claude-3-sonnet-20240229": 200000,
        "claude-3-opus-20240229": 200000,
        "claude-3-5-sonnet-20241022": 200000,
        
        # Google Models
        "gemini-pro": 32768,
        "gemini-1.5-pro": 1000000,
        "gemini-1.5-flash": 1000000,
        
        # DeepSeek Models
        "deepseek-chat": 32768,
        "deepseek-coder": 16384,
        
        # Groq Models
        "llama-3.1-8b-instant": 8192,
        "llama-3.1-70b-versatile": 8192,
        "mixtral-8x7b-32768": 32768,
        
        # Local/Other Models (common defaults)
        "local-model": 4096,
        "llama-2-7b-chat": 4096,
        "llama-2-70b-chat": 4096,
        "codellama": 16384,
        "mistral": 8192,
        
        # Default fallback
        "default": 4096
    }

def get_context_size_for_model(model_name: str) -> int:
    """Get appropriate context size for a model"""
    defaults = get_model_context_defaults()
    
    # Try exact match first
    if model_name in defaults:
        return defaults[model_name]
    
    # Try partial matches
    model_lower = model_name.lower()
    for key, value in defaults.items():
        if key in model_lower or model_lower in key:
            return value
    
    # Default fallback
  
    return defaults["default"]

def truncate_conversation_for_context(messages: List[dict], personality: str, 
                                    context_size: int, max_tokens: int) -> List[dict]:
    """Truncate conversation to fit within context window"""
    
    # Reserve tokens for response and system message
    reserved_tokens = max_tokens + estimate_tokens(personality) + 100  # 100 token buffer
    available_tokens = context_size - reserved_tokens
    
    if available_tokens <= 0:
        # Context too small, return minimal conversation
        return messages[-1:] if messages else []
    
    # Start from the most recent messages and work backwards
    selected_messages = []
    current_tokens = 0
    
    for message in reversed(messages):
        message_tokens = estimate_tokens(message["content"]) + 20  # 20 tokens for role/formatting
        
        if current_tokens + message_tokens <= available_tokens:
            selected_messages.insert(0, message)  # Insert at beginning to maintain order
            current_tokens += message_tokens
        else:
            break
    
    return selected_messages




class EnhancedAIInterface:
    """Enhanced AI interface supporting multiple providers"""
    
    def __init__(self):
        app_data_dir = get_app_data_dir()
        self.configs_dir = app_data_dir / "api_configs"
        self.configs_dir.mkdir(exist_ok=True)
        self.api_configs = {}
        self.default_config = None
        self.current_streaming_request = None
        self.streaming_stop_event = threading.Event()
        self.load_all_configs()
    
    def load_all_configs(self):
        """Load all API configurations from files"""
        self.api_configs = {}
        
        for config_file in self.configs_dir.glob("*.json"):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    config = APIConfig(**data)
                    if config.enabled:
                        self.api_configs[config.name] = config
                        
                        # Set first enabled config as default
                        if not self.default_config:
                            self.default_config = config.name
                            
            except Exception as e:
                print(f"Error loading API config {config_file.name}: {e}")


    def stop_streaming(self):
        """Stop the current streaming request"""
        print("🛑 Stopping streaming request...")
        self.streaming_stop_event.set()
        
        # If we have an active request, try to close it
        if self.current_streaming_request:
            try:
                self.current_streaming_request.close()
                print("✅ Streaming request closed")
            except Exception as e:
                print(f"Error closing streaming request: {e}")




    def debug_instruction_format(self, config_name: str, test_messages: List[dict]) -> str:
        """Debug method to show how messages are formatted for different instruction formats"""
        config = self._get_config(config_name)
        if not config:
            return "No configuration found"
        
        # Show original messages
        result = f"=== DEBUG: Instruction Format '{config.instruction_format}' ===\n\n"
        result += "ORIGINAL MESSAGES:\n"
        for i, msg in enumerate(test_messages):
            result += f"{i+1}. {msg['role']}: {msg['content']}\n"
        
        result += "\n" + "="*50 + "\n"
        
        # Show formatted messages
        formatted_messages = PromptFormatter.format_conversation(config, test_messages)
        result += "FORMATTED MESSAGES:\n"
        for i, msg in enumerate(formatted_messages):
            result += f"{i+1}. {msg['role']}: {msg['content']}\n"
        
        result += "\n" + "="*50 + "\n"
        
        # Show system message formatting
        test_personality = "You are a helpful assistant."
        character_name = "Assistant"
        formatted_system = PromptFormatter.format_system_message(config, character_name, test_personality)
        result += f"SYSTEM MESSAGE:\n{formatted_system}\n"
        
        return result




    def get_response(self, messages: List[dict], personality: str, 
                    config_name: Optional[str] = None) -> str:
        """Get AI response with enhanced prompt formatting"""
        config = self._get_config(config_name)
        if not config:
            return "No API configuration available."
        
        try:
            # NEW: Format messages using the prompt formatter
            formatted_messages = PromptFormatter.format_conversation(config, messages)
            
            # Truncate conversation to fit context window
            truncated_messages = truncate_conversation_for_context(
                formatted_messages, personality, config.context_size, config.max_tokens
            )
            
            # NEW: Create enhanced system message
            character_name = "Assistant"  # You can pass this as a parameter
            enhanced_personality = PromptFormatter.format_system_message(
                config, character_name, personality
            )
            
            if config.provider.lower() == "openai":
                return self._openai_request(truncated_messages, enhanced_personality, config)
            elif config.provider.lower() == "google":
                return self._google_request(truncated_messages, enhanced_personality, config)
            elif config.provider.lower() == "deepseek":
                return self._deepseek_request(truncated_messages, enhanced_personality, config)
            elif config.provider.lower() == "anthropic":
                return self._anthropic_request(truncated_messages, enhanced_personality, config)
            else:
                return self._generic_openai_format_request(truncated_messages, enhanced_personality, config)
                
        except Exception as e:
            return f"API Error ({config.provider}): {str(e)}"

    def _get_config(self, config_name: Optional[str]) -> Optional[APIConfig]:
        """Get API config by name or default - ENHANCED with better fallback"""
        if config_name and config_name in self.api_configs:
            return self.api_configs[config_name]

            
        # Fall back to default config
        if self.default_config and self.default_config in self.api_configs:
            return self.api_configs[self.default_config]
        
        # No default config available
        return None
    
    def _openai_request(self, messages: List[dict], personality: str, config: APIConfig) -> str:
        """OpenAI API request"""
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        system_message = {"role": "system", "content": personality}
        all_messages = [system_message] + messages
        
        data = {
            "model": config.model,
            "messages": all_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            **config.custom_params
        }
        
        response = requests.post(
            f"{config.base_url}/chat/completions", 
            json=data, 
            headers=headers, 
            timeout=config.timeout
        )
        response.raise_for_status()
        
        return response.json()['choices'][0]['message']['content']
    
    def _google_request(self, messages: List[dict], personality: str, config: APIConfig) -> str:
        import requests

        base_url = config.base_url.rstrip("/")
        model = config.model
        if model.startswith("models/"):
            model = model[len("models/"):]

        url = f"{base_url}/v1beta/models/{model}:generateContent"

        prompt_lines = [f"System: {personality}", ""]
        for msg in messages:
            prompt_lines.append(f"{msg['role']}: {msg['content']}")

        payload = {
            "contents": [{
                "parts": [{"text": "\n".join(prompt_lines)}]
            }],
            "generationConfig": {
                "temperature": config.temperature,
                "topP": config.top_p,
                "maxOutputTokens": config.max_tokens,
            }
        }

        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": config.api_key.strip(),
        }

        r = requests.post(url, json=payload, headers=headers, timeout=config.timeout)
        r.raise_for_status()

        data = r.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    
    def _deepseek_request(self, messages: List[dict], personality: str, config: APIConfig) -> str:
        """DeepSeek API request (OpenAI compatible)"""
        return self._openai_request(messages, personality, config)
    
    def _anthropic_request(self, messages: List[dict], personality: str, config: APIConfig) -> str:
        """Anthropic Claude API request"""
        headers = {
            "x-api-key": config.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert messages for Anthropic format
        anthropic_messages = []
        for msg in messages:
            anthropic_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        data = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "system": personality,
            "messages": anthropic_messages,
            **config.custom_params
        }
        
        response = requests.post(
            f"{config.base_url}/messages",
            json=data,
            headers=headers,
            timeout=config.timeout
        )
        response.raise_for_status()
        
        return response.json()['content'][0]['text']
    
    def _generic_openai_format_request(self, messages: List[dict], personality: str, config: APIConfig) -> str:
        """Generic OpenAI-compatible format (for custom providers)"""
        return self._openai_request(messages, personality, config)
    
    def _openai_streaming_request(self, messages: List[dict], personality: str, 
                                config: APIConfig, callback):
        """OpenAI streaming request with stop support"""
        # Reset stop event for new request
        self.streaming_stop_event.clear()
        
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json"
        }
        
        system_message = {"role": "system", "content": personality}
        all_messages = [system_message] + messages
        
        data = {
            "model": config.model,
            "messages": all_messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "top_p": config.top_p,
            "frequency_penalty": config.frequency_penalty,
            "presence_penalty": config.presence_penalty,
            "stream": True,
            **config.custom_params
        }
        
        try:
            # Start the request
            response = requests.post(
                f"{config.base_url}/chat/completions",
                json=data,
                headers=headers,
                timeout=config.timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Store the current request for potential stopping
            self.current_streaming_request = response
            
            full_content = ""
            
            # Stream the response
            for line in response.iter_lines():
                # Check if we should stop
                if self.streaming_stop_event.is_set():
                    print("🛑 Streaming stopped by user")
                    break
                
                if line:
                    line_text = line.decode('utf-8')
                    if line_text.startswith('data: '):
                        if line_text.strip() == 'data: [DONE]':
                            break
                        
                        try:
                            json_data = json.loads(line_text[6:])
                            if 'choices' in json_data and len(json_data['choices']) > 0:
                                delta = json_data['choices'][0].get('delta', {})
                                if 'content' in delta:
                                    content = delta['content']
                                    full_content += content
                                    
                                    # Check again before calling callback
                                    if not self.streaming_stop_event.is_set():
                                        callback(content, False)
                                    else:
                                        print("🛑 Stopping before callback")
                                        break
                                        
                        except json.JSONDecodeError:
                            continue
            
            # Send final callback only if not stopped
            if not self.streaming_stop_event.is_set():
                callback("", True)
            else:
                print("🛑 Stream was stopped, not sending final callback")
                
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            callback(f"Streaming Error: {str(e)}", True)
        finally:
            # Clean up
            self.current_streaming_request = None
            self.streaming_stop_event.clear()
    
    def _deepseek_streaming_request(self, messages: List[dict], personality: str, 
                                  config: APIConfig, callback):
        """DeepSeek streaming request with stop support (same as OpenAI)"""
        self._openai_streaming_request(messages, personality, config, callback)
    
    def get_streaming_response(self, messages: List[dict], personality: str, 
                            callback, config_name: Optional[str] = None):
        """Get streaming AI response with stop support"""
        config = self._get_config(config_name)
        if not config:
            callback("No API configuration available.", True)
            return
        
        try:
            # Format messages using the prompt formatter
            if hasattr(self, 'PromptFormatter'):  # Check if you have this
                formatted_messages = self.PromptFormatter.format_conversation(config, messages)
                truncated_messages = truncate_conversation_for_context(
                    formatted_messages, personality, config.context_size, config.max_tokens
                )
                character_name = "Assistant"
                enhanced_personality = self.PromptFormatter.format_system_message(
                    config, character_name, personality
                )
            else:
                # Fallback to simple formatting
                truncated_messages = messages
                enhanced_personality = personality
            
            if config.provider.lower() == "openai":
                self._openai_streaming_request(truncated_messages, enhanced_personality, config, callback)
            elif config.provider.lower() == "deepseek":
                self._deepseek_streaming_request(truncated_messages, enhanced_personality, config, callback)
            else:
                # Fallback to non-streaming
                response = self.get_response(messages, personality, config_name)
                callback(response, True)
                
        except Exception as e:
            callback(f"Streaming Error ({config.provider}): {str(e)}", True)

    def truncate_conversation_for_context(messages, personality, context_size, max_tokens):
        """Simple truncation if you don't have the full implementation"""
        if not context_size:
            return messages[-10:]  # Keep last 10 messages as fallback
        
        # Simple token estimation
        personality_tokens = len(personality) // 4
        response_tokens = max_tokens or 150
        available_tokens = context_size - personality_tokens - response_tokens - 500
        
        # Estimate tokens per message and keep what fits
        estimated_tokens = 0
        truncated = []
        
        for msg in reversed(messages):
            msg_tokens = len(msg.get('content', '')) // 4
            if estimated_tokens + msg_tokens < available_tokens:
                truncated.insert(0, msg)
                estimated_tokens += msg_tokens
            else:
                break
        
        return truncated or messages[-5:]  # At least keep last 5