"""API Configuration Models"""
from ..common_imports import *



@dataclass
class APIConfig:
    """Configuration for an API provider"""
    name: str
    provider: str
    api_key: str
    base_url: str
    model: str
    
    # Common parameters
    temperature: float = 0.7
    max_tokens: int = 150
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    context_size: int = 4096
    
    # Provider-specific parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    # Advanced settings
    timeout: int = 30
    streaming: bool = False
    enabled: bool = True
    
    # NEW: Prompt Structure Fields
    system_message_template: str = "You are {character_name}. {personality}"
    instruction_format: str = "default"
    use_examples: bool = True
    max_examples: int = 3
    output_format_instruction: str = ""
    prompt_prefix: str = ""
    prompt_suffix: str = ""
    use_chain_of_thought: bool = False
    use_role_context: bool = True
    conversation_style: str = "natural"


@dataclass
class ExternalAPI:
    """Configuration for external APIs"""
    name: str
    url: str
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    params: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    description: str = ""
    timeout: int = 10