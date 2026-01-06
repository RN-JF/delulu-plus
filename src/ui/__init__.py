"""User Interface Package

This package contains all UI components including the main window,
various dialogs, widgets, and animation classes.
"""

# Main Window Components
from .main_window import ChatWindow, MainApplication, CharacterAnimator

# Dialog Classes
from .dialogs import (
    APIConfigManager,
    APIConfigDialog,
    DialogEditWindow,
    DialogManagerWindow,
    InteractionEditDialog,
    UserProfileDialog,
    CharacterImportDialog,
    ChatSettingsDialog,
    IconPositioningDialog,
    EnhancedColorDialog,
    CharacterNameEditDialog,
    BubbleSettingsDialog,
    BackgroundImageDialog,
    ExternalAPIDialog,
    ExternalAPIManager,
    CharacterCreationDialog,
    CharacterColorDialog,
    UserProfileEditDialog,
    CheckInSettingsDialog,
    CheckInSettings,
    AboutDialog
)

# Widget Classes
from .widgets import (
    ChatBubble,
    InteractionIcon,
    ModernScrollbar,
    MessageEditDialog
)

__all__ = [
    # Main Window Classes
    'ChatWindow',
    'MainApplication', 
    'CharacterAnimator',
    
    # Dialog Classes
    'APIConfigManager',
    'APIConfigDialog',
    'DialogEditWindow',
    'DialogManagerWindow', 
    'InteractionEditDialog',
    'UserProfileDialog',
    'CharacterImportDialog',
    'ChatSettingsDialog',
    'IconPositioningDialog',
    'EnhancedColorDialog',
    'CharacterNameEditDialog',
    'BubbleSettingsDialog',
    'BackgroundImageDialog',
    'ExternalAPIDialog',
    'ExternalAPIManager',
    'CharacterCreationDialog',
    'CharacterColorDialog',
    'UserProfileEditDialog',
    'CheckInSettingsDialog',
    'CheckInSettings',
    'AboutDialog',
    
    # Widget Classes
    'ChatBubble',
    'InteractionIcon',
    'ModernScrollbar',
    'MessageEditDialog'
]