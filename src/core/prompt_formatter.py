"""Prompt formatting utilities"""
from ..common_imports import *
from ..models.character import CharacterConfig
from ..models.chat_models import ChatMessage

class PromptFormatter:
    """Format prompts and messages for AI APIs"""
    
    def __init__(self):
        pass
    
    def format_system_message(self, character: CharacterConfig, user_name: str = "User") -> str:
        """Format system message for character"""
        template = character.interaction.greeting if hasattr(character, 'interaction') else "Hello!"
        
        # Replace placeholders
        formatted = template.replace("{character_name}", character.name)
        formatted = formatted.replace("{user_name}", user_name)
        formatted = formatted.replace("{personality}", character.personality)
        
        return formatted
    
    def format_messages_for_api(self, messages: List[ChatMessage], character: CharacterConfig, user_name: str = "User") -> List[Dict[str, str]]:
        """Format messages for API consumption"""
        formatted_messages = []
        
        # Add system message if needed
        system_message = self.format_system_message(character, user_name)
        if system_message:
            formatted_messages.append({
                "role": "system",
                "content": system_message
            })
        
        # Add conversation messages
        for message in messages:
            formatted_messages.append({
                "role": message.role,
                "content": message.content
            })
        
        return formatted_messages
    
    def create_character_prompt(self, character: CharacterConfig) -> str:
        """Create character personality prompt"""
        prompt_parts = [
            f"You are {character.name}.",
            f"Description: {character.description}",
            f"Personality: {character.personality}"
        ]
        
        return " ".join(prompt_parts)
