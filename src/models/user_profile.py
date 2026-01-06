"""User Profile Models"""
from ..common_imports import *

@dataclass
class UserProfile:
    """User profile configuration with folder name and user name"""
    name: str  # Folder name / identifier (for file system organization)
    user_name: str  # Actual user name (used for {{user}} replacement)
    personality: str
    is_active: bool = False

@dataclass
class UserSettings:
    """Global user settings"""
    profiles: List[UserProfile] = field(default_factory=list)
    active_profile_name: Optional[str] = None
    show_about_on_startup: bool = True
