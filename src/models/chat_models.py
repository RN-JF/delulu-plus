"""Chat-related Models"""
from ..common_imports import *


@dataclass
class ChatMessage:
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    sibling_index: int = 0  # Position among siblings
    is_active: bool = True  # Whether this is the active branch
    is_hidden: bool = False  # Add this field

    bubble_width: Optional[int] = None  # NEW: Cache the bubble width
    def __post_init__(self):
        if self.id is None:
            import uuid
            self.id = str(uuid.uuid4())
        if self.children_ids is None:
            self.children_ids = []

@dataclass
class ChatSettings:
    """Settings for chat appearance"""
    user_icon_path: str = ""
    character_icon_path: str = ""
    background_type: str = "color"  # "color" or "image"
    background_color: str = "#F0F4F8"
    background_image_path: str = ""
    # Background image positioning
    bg_image_scale: float = 1.0
    bg_image_offset_x: int = 0
    bg_image_offset_y: int = 0
    # Icon positioning settings
    user_icon_scale: float = 1.0
    user_icon_offset_x: int = 0
    user_icon_offset_y: int = 0
    character_icon_scale: float = 1.0
    character_icon_offset_x: int = 0
    character_icon_offset_y: int = 0
    
    # NEW: Window transparency settings
    window_transparency_enabled: bool = False
    window_transparency_value: int = 50  # 0-100
    window_transparency_mode: str = "focus"  # "focus", "time", "always"
    window_transparency_time: int = 3  # minutes


@dataclass
class ScheduledDialog:
    name: str
    prompt: str
    time: str  # "HH:MM"
    enabled: bool = True
    date: Optional[str] = None  # e.g., "2025-07-15"
    advance_days: int = 0  # 0 = same day
