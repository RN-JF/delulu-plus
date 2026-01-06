"""Utility Functions Package

This package contains utility functions and managers for file operations,
helper functions, and various utility classes used throughout the application.
"""

from .helpers import (
    hex_to_rgba, 
    safe_copy_file, 
    force_reload_image,
    replace_name_placeholders, 
    get_darker_secondary_with_transparency
)

from .file_manager import (
    get_app_data_dir, 
    cleanup_temp_files,
    CharacterManager, 
    UserProfileManager
)

__all__ = [
    # Helper Functions
    'hex_to_rgba',
    'safe_copy_file',
    'force_reload_image',
    'replace_name_placeholders',
    'get_darker_secondary_with_transparency',
    
    # File Management Functions
    'get_app_data_dir',
    'cleanup_temp_files',
    
    # Manager Classes
    'CharacterManager',
    'UserProfileManager'
]


