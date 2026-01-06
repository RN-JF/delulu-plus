"""File management utilities"""
"""File management utilities"""
from ..common_imports import *
from ..models.character import CharacterConfig, Interaction
from ..models.user_profile import UserProfile, UserSettings
from ..models.api_config import ExternalAPI
from ..utils.helpers import safe_copy_file



def get_app_data_dir():
    """Get application data directory - LOCAL PROJECT STORAGE VERSION"""
    # Get the project root directory (where src/ is located)
    current_file = Path(__file__)  # This file: src/utils/file_manager.py
    project_root = current_file.parent.parent.parent  # Go up 3 levels to project root
    
    # Create data directory in project root
    app_dir = project_root / "data"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def cleanup_temp_files(character_name: str):
    """Clean up temporary files for a character"""
    try:
        app_data_dir = get_app_data_dir()
        char_dir = app_data_dir / "characters" / character_name
        
        # Clean up temp background files
        for temp_file in char_dir.glob("temp_bg_*.png"):
            try:
                temp_file.unlink()
                print(f"🧹 Cleaned up temp file: {temp_file}")
            except Exception as e:
                print(f"⚠️ Could not clean temp file {temp_file}: {e}")
                
        # Clean up any orphaned files
        for orphan in char_dir.glob("*.tmp"):
            try:
                orphan.unlink()
                print(f"🧹 Cleaned up orphaned file: {orphan}")
            except Exception as e:
                print(f"⚠️ Could not clean orphaned file {orphan}: {e}")
                
    except Exception as e:
        print(f"⚠️ Error during cleanup: {e}")


class CharacterManager:
    """Manages character data and operations"""
    def __init__(self):
        app_data_dir = get_app_data_dir()
        self.characters_dir = app_data_dir / "characters"
        self.characters_dir.mkdir(exist_ok=True)
        
    def get_characters(self) -> List[str]:
        """Get list of all characters"""
        return [d.name for d in self.characters_dir.iterdir() if d.is_dir()]
    
    def create_character(self, folder_name: str, display_name: str, image_path: str, personality: str) -> bool:
        """Create a new character with separate folder and display names"""
        char_dir = self.characters_dir / folder_name
        if char_dir.exists():
            return False
            
        try:
            char_dir.mkdir()
            
            # For GIF files, copy directly without re-encoding
            if image_path.lower().endswith('.gif'):
                base_filename = "base_image.gif"
                base_path = char_dir / base_filename
                shutil.copy2(image_path, base_path)
            else:
                # For other formats, use PIL
                image = Image.open(image_path)
                ext = os.path.splitext(image_path)[1] or '.png'
                base_filename = f"base_image{ext}"
                base_path = char_dir / base_filename
                image.save(base_path)
            
            # Save personality
            with open(char_dir / "personality.txt", 'w', encoding='utf-8') as f:
                f.write(personality)
            
            # Create config with both names
            config = CharacterConfig(
                folder_name=folder_name,
                display_name=display_name,
                base_image=base_filename,
                personality=personality,
                user_bubble_color="#F0F0F0",
                user_text_color="#333333",
                text_font="Arial"
            )
            
            with open(char_dir / "config.json", 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, indent=2)
            
            # Create interactions directory
            (char_dir / "interactions").mkdir(exist_ok=True)
                
            return True
            
        except Exception as e:
            print(f"Error creating character: {e}")
            if char_dir.exists():
                shutil.rmtree(char_dir)
            return False

    def rename_character(self, old_folder_name: str, new_folder_name: str, new_display_name: str) -> bool:
        """Safely rename a character with backup protection"""
        old_char_dir = self.characters_dir / old_folder_name
        new_char_dir = self.characters_dir / new_folder_name
        backup_dir = self.characters_dir / f"{old_folder_name}_backup_{int(time.time())}"
        
        if not old_char_dir.exists():
            print(f"❌ Old character directory not found: {old_char_dir}")
            return False
        
        # If only display name changed (not folder name), just update config
        if old_folder_name == new_folder_name:
            return self._update_display_name_only(old_char_dir, new_display_name)
        
        if new_char_dir.exists():
            print(f"❌ New folder name already exists: {new_folder_name}")
            return False
        
        try:
            print(f"🔄 Starting safe character rename: {old_folder_name} → {new_folder_name}")
            
            # STEP 1: Create backup
            print("📦 Creating backup...")
            shutil.copytree(str(old_char_dir), str(backup_dir))
            print(f"✅ Backup created: {backup_dir}")
            
            # STEP 2: Create new directory with updated config
            print("📁 Creating new directory...")
            shutil.copytree(str(old_char_dir), str(new_char_dir))
            
            # STEP 3: Update config in new directory
            config_file = new_char_dir / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update names in config
            data['folder_name'] = new_folder_name
            data['display_name'] = new_display_name
            
            # Save updated config
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print("✅ New directory created with updated config")
            
            # STEP 4: Verify new directory is complete
            if not self._verify_character_directory(new_char_dir):
                raise Exception("New directory verification failed")
            
            # STEP 5: Remove old directory only after success
            print("🗑️ Removing old directory...")
            shutil.rmtree(str(old_char_dir))
            
            # STEP 6: Clean up backup after successful rename
            print("🧹 Cleaning up backup...")
            shutil.rmtree(str(backup_dir))
            
            print(f"✅ Character successfully renamed: {old_folder_name} → {new_folder_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error during rename: {e}")
            
            # RECOVERY: Restore from backup if anything went wrong
            try:
                if new_char_dir.exists():
                    shutil.rmtree(str(new_char_dir))
                
                if not old_char_dir.exists() and backup_dir.exists():
                    shutil.move(str(backup_dir), str(old_char_dir))
                    print("🔧 Restored from backup")
                elif backup_dir.exists():
                    shutil.rmtree(str(backup_dir))
                    
            except Exception as recovery_error:
                print(f"❌ Recovery error: {recovery_error}")
                print(f"⚠️ Manual recovery may be needed. Backup location: {backup_dir}")
            
            return False

    def _update_display_name_only(self, char_dir: Path, new_display_name: str) -> bool:
        """Update only the display name without moving files"""
        try:
            config_file = char_dir / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            data['display_name'] = new_display_name
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            print(f"✅ Display name updated to: {new_display_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating display name: {e}")
            return False

    def _verify_character_directory(self, char_dir: Path) -> bool:
        """Verify character directory has all required files"""
        try:
            required_files = ['config.json']
            
            for file_name in required_files:
                if not (char_dir / file_name).exists():
                    print(f"❌ Missing required file: {file_name}")
                    return False
            
            # Verify config.json is valid
            config_file = char_dir / "config.json"
            with open(config_file, 'r', encoding='utf-8') as f:
                json.load(f)  # This will raise an exception if invalid JSON
            
            print("✅ Character directory verification passed")
            return True
            
        except Exception as e:
            print(f"❌ Directory verification failed: {e}")
            return False


    # In your CharacterManager.load_character method, add this conversion after loading the JSON data
    # and before creating the CharacterConfig object:

    def load_character(self, name: str) -> Optional[CharacterConfig]:
        """Load character configuration with robust backward compatibility"""
        char_dir = self.characters_dir / name
        config_file = char_dir / "config.json"
        
        if not config_file.exists():
            return None
            
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # ... existing migration code ...
                
                # Add missing fields with defaults
                defaults = {
                    'folder_name': name,
                    'display_name': name,
                    'user_bubble_color': "#F0F0F0",
                    'user_text_color': "#333333",
                    'text_font': "Arial",
                    'text_size': 11,
                    'text_color': "#1976D2",
                    'bubble_color': "#E3F2FD",
                    'api_config_name': None,
                    'bubble_transparency': 0,
                    'user_bubble_transparency': 0,
                    'quote_color': "#666666",
                    'emphasis_color': "#0D47A1",
                    'strikethrough_color': "#757575",
                    'code_bg_color': "rgba(0,0,0,0.1)",
                    'code_text_color': "#D32F2F",
                    'link_color': "#1976D2",
                    'external_apis': []  # This should already be there
                }
                
                # Add any missing fields
                config_updated = False
                for key, default_value in defaults.items():
                    if key not in data:
                        data[key] = default_value
                        config_updated = True
                
                # Save updated config if any defaults were added
                if config_updated:
                    with open(config_file, 'w', encoding='utf-8') as f_write:
                        json.dump(data, f_write, indent=2)
                    print(f"✅ Updated character config with missing fields: {name}")
                
                # *** ADD THIS SECTION - Convert external_apis dictionaries to ExternalAPI objects ***
                if 'external_apis' in data and data['external_apis']:
                    converted_apis = []
                    for api_data in data['external_apis']:
                        if isinstance(api_data, dict):
                            # Convert dictionary to ExternalAPI object
                            try:
                                api_obj = ExternalAPI(**api_data)
                                converted_apis.append(api_obj)
                            except Exception as e:
                                print(f"⚠️ Error converting external API: {e}")
                                # Skip invalid API data
                                continue
                        else:
                            # Already an ExternalAPI object
                            converted_apis.append(api_data)
                    data['external_apis'] = converted_apis
                
                # Convert relative path to absolute path for base_image
                if 'base_image' in data:
                    base_image_path = data['base_image']
                    if not os.path.isabs(base_image_path):
                        # It's a relative path, make it absolute
                        abs_path = str(char_dir / base_image_path)
                        if os.path.exists(abs_path):
                            data['base_image'] = abs_path
                        else:
                            # Try to find the image with common extensions
                            for ext in ['.gif', '.png', '.jpg', '.jpeg']:
                                potential_path = char_dir / f"base_image{ext}"
                                if potential_path.exists():
                                    data['base_image'] = str(potential_path)
                                    break
                
                return CharacterConfig(**data)
                
        except Exception as e:
            print(f"Error loading character {name}: {e}")
            return None

    def delete_character(self, name: str) -> bool:
        """Delete a character"""
        char_dir = self.characters_dir / name
        if char_dir.exists():
            try:
                shutil.rmtree(char_dir)
                return True
            except Exception as e:
                print(f"Error deleting character: {e}")
        return False
    

    def update_character_image(self, name: str, new_image_path: str) -> bool:
        """Update character's base image SAFELY without affecting global state"""
        char_dir = self.characters_dir / name
        if not char_dir.exists():
            print(f"❌ Character directory not found: {char_dir}")
            return False
            
        # Create backup before making changes
        backup_timestamp = int(time.time())
        backup_config = None
        
        try:
            print(f"🔄 Starting safe character image update for: {name}")
            
            # STEP 1: Backup current config
            config_file = char_dir / "config.json"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    backup_config = json.load(f)
            
            # STEP 2: Find and backup old base images
            old_images = list(char_dir.glob("base_image.*"))
            backup_images = []
            
            for old_image in old_images:
                backup_name = f"backup_base_image_{backup_timestamp}{old_image.suffix}"
                backup_path = char_dir / backup_name
                shutil.copy2(str(old_image), str(backup_path))
                backup_images.append((old_image, backup_path))
                print(f"📦 Backed up: {old_image.name} → {backup_name}")
            
            # STEP 3: Determine target path for new image
            file_ext = os.path.splitext(new_image_path)[1]
            base_path = char_dir / f"base_image{file_ext}"
            
            # STEP 4: Copy new image with verification
            if not safe_copy_file(new_image_path, str(base_path)):
                raise Exception("Failed to copy new image file")
            
            # Verify the new image file exists and is valid
            if not base_path.exists() or base_path.stat().st_size == 0:
                raise Exception("New image file is missing or empty")
            
            # STEP 5: Update config file
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                
                config['base_image'] = str(base_path)
                
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=2)
            
            # STEP 6: Remove old base images ONLY after success
            for old_image, backup_path in backup_images:
                if old_image.exists() and old_image != base_path:
                    old_image.unlink()
                    print(f"🗑️ Removed old image: {old_image.name}")
            
            # STEP 7: Clean up backup images
            for _, backup_path in backup_images:
                if backup_path.exists():
                    backup_path.unlink()
                    print(f"🧹 Cleaned up backup: {backup_path.name}")
            
            print(f"✅ Character image safely updated: {base_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating image: {e}")
            
            # RECOVERY: Restore from backup
            try:
                print("🔧 Attempting recovery from backup...")
                
                # Restore config
                if backup_config and config_file.exists():
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(backup_config, f, indent=2)
                
                # Restore image files
                for old_image, backup_path in backup_images:
                    if backup_path.exists():
                        shutil.copy2(str(backup_path), str(old_image))
                        backup_path.unlink()
                        print(f"🔧 Restored: {old_image.name}")
                
                # Remove failed new image if it exists
                if base_path.exists():
                    base_path.unlink()
                    
                print("✅ Recovery completed successfully")
                
            except Exception as recovery_error:
                print(f"❌ Recovery error: {recovery_error}")
                print(f"⚠️ Manual recovery may be needed. Check backups in: {char_dir}")
            
            return False





    
    def get_interactions(self, character_name: str) -> List[Interaction]:
        """Load character interactions with path resolution"""
        interactions = []
        interactions_dir = self.characters_dir / character_name / "interactions"
        
        if not interactions_dir.exists():
            return interactions
            
        for interaction_dir in interactions_dir.iterdir():
            if interaction_dir.is_dir():
                try:
                    config_file = interaction_dir / "config.json"
                    if config_file.exists():
                        with open(config_file, 'r') as f:
                            data = json.load(f)
                            
                            # IMPORTANT: Convert relative paths to absolute paths
                            if 'icon_path' in data and data['icon_path']:
                                if not os.path.isabs(data['icon_path']):
                                    data['icon_path'] = str(interaction_dir / data['icon_path'])
                            
                            if 'base_image_path' in data and data['base_image_path']:
                                if not os.path.isabs(data['base_image_path']):
                                    data['base_image_path'] = str(interaction_dir / data['base_image_path'])
                            
                            interactions.append(Interaction(**data))
                except Exception as e:
                    print(f"Error loading interaction {interaction_dir.name}: {e}")
                    
        return interactions


        # 4. REPLACE CharacterManager.save_interaction method
    def save_interaction(self, character_name: str, interaction: Interaction) -> bool:
        """Save or update an interaction with robust file handling and path resolution"""
        interaction_dir = self.characters_dir / character_name / "interactions" / interaction.name

        try:
            interaction_dir.mkdir(parents=True, exist_ok=True)
            
            # Create a copy of the interaction for saving
            interaction_to_save = Interaction(
                name=interaction.name,
                icon_path=interaction.icon_path,
                base_image_path=interaction.base_image_path,
                duration=interaction.duration,
                position=interaction.position
            )

            # Save Icon Image with better error handling
            if interaction.icon_path:
                source_icon = self._resolve_source_path(interaction.icon_path)
                if source_icon and os.path.exists(source_icon):
                    icon_ext = os.path.splitext(source_icon)[1].lower()
                    icon_filename = f"icon{icon_ext}"
                    icon_target = interaction_dir / icon_filename
                    
                    # Use safe copy function
                    if safe_copy_file(source_icon, str(icon_target)):
                        interaction_to_save.icon_path = icon_filename  # Store relative path
                        print(f"✅ Icon saved: {icon_filename}")
                    else:
                        print(f"❌ Failed to copy icon from {source_icon}")
                        return False
                else:
                    print(f"❌ Icon source not found: {interaction.icon_path}")
                    return False

            # Save Base Image with better error handling
            if interaction.base_image_path:
                source_base = self._resolve_source_path(interaction.base_image_path)
                if source_base and os.path.exists(source_base):
                    base_ext = os.path.splitext(source_base)[1].lower()
                    base_filename = f"base{base_ext}"
                    base_target = interaction_dir / base_filename

                    # Use safe copy function
                    if safe_copy_file(source_base, str(base_target)):
                        interaction_to_save.base_image_path = base_filename  # Store relative path
                        print(f"✅ Base image saved: {base_filename}")
                    else:
                        print(f"❌ Failed to copy base image from {source_base}")
                        return False
                else:
                    print(f"❌ Base image source not found: {interaction.base_image_path}")
                    return False

            # Save config with relative paths
            config_file = interaction_dir / "config.json"
            config_data = {
                'name': interaction_to_save.name,
                'icon_path': interaction_to_save.icon_path,  # Already relative
                'base_image_path': interaction_to_save.base_image_path,  # Already relative
                'duration': interaction_to_save.duration,
                'position': interaction_to_save.position
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
            
            print(f"✅ Interaction '{interaction.name}' saved successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error saving interaction: {e}")
            return False

    def _resolve_source_path(self, path: str) -> str:
        """Resolve the actual source path for copying"""
        if not path:
            return None
            
        # If absolute path exists, use it
        if os.path.isabs(path) and os.path.exists(path):
            return path
        
        # If relative path exists from current directory
        if os.path.exists(path):
            return os.path.abspath(path)
        
        return None


    def delete_interaction(self, character_name: str, interaction_name: str) -> bool:
        """Delete an interaction - IMPROVED VERSION"""
        interaction_dir = self.characters_dir / character_name / "interactions" / interaction_name
        
        if interaction_dir.exists():
            try:
                # List contents before deletion for debugging
                print(f"Deleting interaction folder: {interaction_dir}")
                if interaction_dir.is_dir():
                    files = list(interaction_dir.glob("*"))
                    print(f"Files to delete: {[f.name for f in files]}")
                
                shutil.rmtree(interaction_dir)
                print(f"Successfully deleted interaction: {interaction_name}")
                return True
            except Exception as e:
                print(f"Error deleting interaction {interaction_name}: {e}")
                return False
        else:
            print(f"Interaction folder not found: {interaction_dir}")
            return True  # Consider it success if folder doesn't exist



class UserProfileManager:
    """Manages user profiles and personalities"""
    def __init__(self):
        self.app_data_dir = get_app_data_dir()
        self.settings_file = self.app_data_dir / "user_settings.json"
        self.settings = self._load_settings()
    
    def _load_settings(self) -> UserSettings:
        """Load user settings from file with enhanced backward compatibility"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Validate profile data structure
                    profiles = []
                    for p_data in data.get('profiles', []):
                        try:
                            # ENHANCED: Handle both old and new profile formats
                            if all(key in p_data for key in ['name', 'personality']):
                                # Check if this is old format (no user_name field)
                                if 'user_name' not in p_data:
                                    # OLD FORMAT: Add user_name field using name
                                    p_data['user_name'] = p_data['name']
                                    print(f"✅ Migrated old profile format: {p_data['name']} -> user_name: {p_data['user_name']}")
                                # Handle title->user_name migration
                                elif 'title' in p_data and 'user_name' not in p_data:
                                    p_data['user_name'] = p_data['title']
                                    del p_data['title']  # Remove old title field
                                    print(f"✅ Migrated title to user_name: {p_data['user_name']}")
                                
                                profile = UserProfile(**p_data)
                                profiles.append(profile)
                            else:
                                print(f"⚠️ Skipping invalid profile: {p_data}")
                        except Exception as e:
                            print(f"⚠️ Skipping corrupted profile: {e}")
                    
                    # Validate active profile
                    active_profile_name = data.get('active_profile_name')
                    show_about_on_startup = data.get('show_about_on_startup', True)
                    if active_profile_name and not any(p.name == active_profile_name for p in profiles):
                        print(f"⚠️ Active profile '{active_profile_name}' not found, clearing")
                        active_profile_name = None
                    
                    # Set first profile as active if none set
                    if not active_profile_name and profiles:
                        active_profile_name = profiles[0].name
                        print(f"✅ Set first profile as active: {active_profile_name}")
                    
                    return UserSettings(
                        profiles=profiles,
                        active_profile_name=active_profile_name,
                        show_about_on_startup=show_about_on_startup,
                    )
                    
            except Exception as e:
                print(f"❌ Error loading user settings: {e}")
                print("🔄 Creating fresh user settings")
        
        # Create default profile if loading failed or file doesn't exist
        default_profile = UserProfile(
            name="default_user",  # Folder name
            user_name="User",     # Name for {{user}} replacement
            personality="I am a friendly and curious person who enjoys learning new things.",
            is_active=True
        )
        return UserSettings(
            profiles=[default_profile],
            active_profile_name="default_user",
            show_about_on_startup=True,
        )
    
    def save_settings(self):
        """Save user settings to file"""
        try:
            data = {
                'profiles': [asdict(p) for p in self.settings.profiles],
                'active_profile_name': self.settings.active_profile_name,
                "show_about_on_startup": getattr(self.settings, "show_about_on_startup", True),
            }
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved user settings with {len(self.settings.profiles)} profiles")
        except Exception as e:
            print(f"Error saving user settings: {e}")
    
    def get_active_profile(self) -> Optional[UserProfile]:
        """Get currently active user profile"""
        if self.settings.active_profile_name:
            for profile in self.settings.profiles:
                if profile.name == self.settings.active_profile_name:
                    return profile
        return self.settings.profiles[0] if self.settings.profiles else None
    
    def add_profile(self, profile: UserProfile) -> bool:
        """Add new user profile"""
        if any(p.name == profile.name for p in self.settings.profiles):
            return False
        self.settings.profiles.append(profile)
        self.save_settings()
        return True
    
    def update_profile(self, old_name: str, new_profile: UserProfile) -> bool:
        """Update existing profile"""
        for i, profile in enumerate(self.settings.profiles):
            if profile.name == old_name:
                self.settings.profiles[i] = new_profile
                if self.settings.active_profile_name == old_name:
                    self.settings.active_profile_name = new_profile.name
                self.save_settings()
                return True
        return False
    
    def delete_profile(self, name: str) -> bool:
        """Delete profile and handle active profile cleanup"""
        if len(self.settings.profiles) <= 1:  # Keep at least one profile
            return False
        
        # Remove the profile
        self.settings.profiles = [p for p in self.settings.profiles if p.name != name]
        
        # If we deleted the active profile, set a new one
        if self.settings.active_profile_name == name:
            if self.settings.profiles:
                # Set the first remaining profile as active
                self.settings.active_profile_name = self.settings.profiles[0].name
                print(f"Active profile changed to: {self.settings.active_profile_name}")
            else:
                self.settings.active_profile_name = None
        
        self.save_settings()
        return True
    
    def set_active_profile(self, name: str):
        """Set active profile and save immediately"""
        if any(p.name == name for p in self.settings.profiles):
            self.settings.active_profile_name = name
            print(f"Setting active profile to: {name}")
            self.save_settings()
            return True
        return False

   