"""Core Business Logic Package

This package contains the core business logic for the character chat application,
including AI interface management, chat tree management, and prompt formatting.
"""

# Chat Management Classes
from .chat_manager import ChatTree, PromptFormatter

# AI Interface Classes and Functions
from .ai_interface import (
    EnhancedAIInterface,
    estimate_tokens,
    get_model_context_defaults,
    get_context_size_for_model,
    truncate_conversation_for_context
)

__all__ = [
    # Chat Management
    'ChatTree',
    'PromptFormatter',
    
    # AI Interface
    'EnhancedAIInterface',
    'estimate_tokens',
    'get_model_context_defaults',
    'get_context_size_for_model',
    'truncate_conversation_for_context'
]