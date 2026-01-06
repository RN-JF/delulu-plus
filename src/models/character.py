"""Character Configuration Models"""
from ..common_imports import *
from .api_config import ExternalAPI


@dataclass
class IconSettings:
    """Settings for icon display"""
    image_path: str = ""
    scale: float = 1.0  # Zoom level
    offset_x: int = 0   # Horizontal offset
    offset_y: int = 0   # Vertical offset

@dataclass
class BackgroundImageSettings:
    """Settings for background image display"""
    image_path: str
    scale: float = 1.0  # Zoom level
    offset_x: int = 0   # Horizontal offset
    offset_y: int = 0   # Vertical offset


@dataclass
class Interaction:
    name: str
    icon_path: str
    base_image_path: str
    duration: int
    position: Tuple[int, int] = (50, 50)


@dataclass
class CharacterConfig:
    folder_name: str  # Name used for folder/file organization
    display_name: str  # Name shown in chat (what {{character}} becomes)
    base_image: str
    personality: str
    bubble_color: str = "#E3F2FD"
    user_bubble_color: str = "#F0F0F0"
    text_size: int = 11
    text_font: str = "Arial"
    api_config_name: Optional[str] = None

    # Bubble transparency fields
    bubble_transparency: int = 0
    user_bubble_transparency: int = 0

    external_apis: List[ExternalAPI] = field(default_factory=list)

    character_primary_color: str = ""  # Empty means use global
    character_secondary_color: str = ""  # Empty means use global
    use_character_colors: bool = False  # Enable/disable character colors

    # Text Style Colors
    text_color: str = "#1976D2"
    user_text_color: str = "#333333"
    quote_color: str = "#666666"
    emphasis_color: str = "#0D47A1"
    strikethrough_color: str = "#757575"
    code_bg_color: str = "rgba(0,0,0,0.1)"
    code_text_color: str = "#D32F2F"
    link_color: str = "#1976D2"

    # Legacy support - keep 'name' property for backward compatibility
    @property
    def name(self):
        return self.folder_name