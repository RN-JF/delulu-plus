"""Main Application Window"""
from ..common_imports import *
from ..models.character import CharacterConfig, IconSettings, BackgroundImageSettings, Interaction
from ..models.api_config import APIConfig, ExternalAPI
from ..models.user_profile import UserProfile, UserSettings
from ..models.chat_models import ChatMessage, ChatSettings, ScheduledDialog
from ..models.ui_models import AppColors, app_colors
from ..utils.file_manager import get_app_data_dir, CharacterManager, UserProfileManager
from ..utils.helpers import hex_to_rgba, safe_copy_file, force_reload_image, replace_name_placeholders, get_darker_secondary_with_transparency
from ..core.ai_interface import EnhancedAIInterface
from .widgets import ChatBubble, InteractionIcon, ModernScrollbar, MessageEditDialog
from .dialogs import CheckInSettingsDialog, CheckInSettings,APIConfigManager, DialogEditWindow,DialogManagerWindow,APIConfigDialog, InteractionEditDialog, UserProfileDialog, CharacterImportDialog, ChatSettingsDialog, IconPositioningDialog, EnhancedColorDialog, CharacterNameEditDialog, BubbleSettingsDialog, BackgroundImageDialog, ExternalAPIDialog, ExternalAPIManager,CharacterCreationDialog,CharacterColorDialog,UserProfileEditDialog,AboutDialog
from ..core.ai_interface import estimate_tokens
from ..core.chat_manager import ChatTree
from pathlib import Path
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup

class CharacterAnimator(QObject):
    """Handles character animation with seamless transitions"""
    def __init__(self, scene):
        super().__init__()
        self.scene = scene
        self.frames = []
        self.delays = []
        self.current_frame_index = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.animate_gif)
        self.current_image_path = None
        self.pixmap_item = None
        self.is_playing = False
        
        # NEW: Pre-loading system for seamless transitions
        self.preloaded_animations = {}  # Cache for loaded animations
        self.pending_animation = None   # Animation waiting to be displayed
        
    def load_animation(self, image_path: str) -> Tuple[int, int]:
        """Load and prepare animation frames (original method for initial load)"""
        self.stop_animation()
        
        self.frames = []
        self.delays = []
        self.current_frame_index = 0
        self.current_image_path = image_path
        
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return 200, 200
            
        try:
            frames, delays, width, height = self._load_gif_data(image_path)
            self.frames = frames
            self.delays = delays
            
            # Cache this animation
            self.preloaded_animations[image_path] = (frames, delays, width, height)
            
            return width, height
            
        except Exception as e:
            print(f"Error loading animation: {e}")
            return 200, 200



    def clear_animation_cache(self, image_path: str = None):
        """Clear animation cache for specific image or all animations"""
        if image_path:
            # Clear specific image from cache
            if image_path in self.preloaded_animations:
                del self.preloaded_animations[image_path]
                print(f"🧹 Cleared cache for: {image_path}")
        else:
            # Clear all animation cache
            self.preloaded_animations.clear()
            print("🧹 Cleared all animation cache")

    def clear_interaction_cache(self, character_name: str, interaction_name: str = None):
        """Clear cache for specific interaction or all interactions of a character"""
        try:
            # Build paths to check
            if interaction_name:
                # Clear specific interaction
                interaction_path_patterns = [
                    f"*/{character_name}/interactions/{interaction_name}/base.*",
                    f"*/characters/{character_name}/interactions/{interaction_name}/base.*"
                ]
            else:
                # Clear all interactions for character
                interaction_path_patterns = [
                    f"*/{character_name}/interactions/*/base.*",
                    f"*/characters/{character_name}/interactions/*/base.*"
                ]
            
            # Remove matching cached animations
            paths_to_remove = []
            for cached_path in self.preloaded_animations.keys():
                for pattern in interaction_path_patterns:
                    if fnmatch.fnmatch(cached_path, pattern):
                        paths_to_remove.append(cached_path)
                        break
            
            for path in paths_to_remove:
                del self.preloaded_animations[path]
                print(f"🧹 Cleared interaction cache: {path}")
                
        except Exception as e:
            print(f"Error clearing interaction cache: {e}")

    def force_reload_animation(self, image_path: str):
        """Force reload animation by clearing cache and reloading"""
        self.clear_animation_cache(image_path)
        
        # If this is the currently displayed animation, reload it
        if self.current_image_path == image_path:
            print(f"🔄 Force reloading current animation: {image_path}")
            was_playing = self.is_playing
            self.stop_animation()
            self.load_animation(image_path)
            if was_playing:
                self.start_animation()



    def seamless_load_animation(self, image_path: str):
        """Load new animation seamlessly without stopping current display"""
        if not os.path.exists(image_path):
            print(f"Image file not found: {image_path}")
            return
            
        try:
            # Check if animation is already cached
            if image_path in self.preloaded_animations:
                frames, delays, width, height = self.preloaded_animations[image_path]
            else:
                # Load and cache new animation
                frames, delays, width, height = self._load_gif_data(image_path)
                self.preloaded_animations[image_path] = (frames, delays, width, height)
            
            # SEAMLESS SWITCH: Update data and continue animation without stopping
            self.frames = frames
            self.delays = delays
            self.current_frame_index = 0
            self.current_image_path = image_path
            
            # If not currently playing, start animation
            if not self.is_playing:
                self.start_animation()
            
            # The animation loop will automatically pick up the new frames
            
        except Exception as e:
            print(f"Error in seamless load: {e}")
    
    def _load_gif_data(self, image_path: str) -> Tuple[List, List, int, int]:
        """Internal method to load GIF data"""
        frames = []
        delays = []
        
        gif_image = Image.open(image_path)
        
        frame_count = 0
        for frame in ImageSequence.Iterator(gif_image):
            frame_rgba = frame.copy().convert('RGBA')
            data = frame_rgba.tobytes('raw', 'RGBA')
            qimg = QImage(data, frame_rgba.width, frame_rgba.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)
            frames.append(pixmap)
            
            try:
                delay = frame.info.get('duration', 100)
                delay = max(delay, 50)  # Minimum 50ms per frame
            except KeyError:
                delay = 100
            delays.append(delay)
            
            frame_count += 1
            if frame_count > 200:  # Memory protection
                break
        
        return frames, delays, gif_image.width, gif_image.height
    
    def start_animation(self):
        """Start the animation loop"""
        if not self.frames:
            return
            
        if self.is_playing:
            return  # Already playing, seamless switch will continue
            
        self.current_frame_index = 0
        self.is_playing = True
        self.animation_timer.stop()
        self.animate_gif()
    

    def _safe_stop_animation(self):
        """Internal safe stop method for error recovery"""
        print("🛡️ Performing safe animation stop")
        self.is_playing = False
        
        try:
            if self.animation_timer:
                self.animation_timer.stop()
        except:
            pass
        
        # Don't remove pixmap item during error recovery to avoid more errors
        # Just mark it as None and let Qt handle cleanup
        self.pixmap_item = None

    def _safe_cleanup_pixmap_item(self):
        """Safely clean up pixmap item"""
        if self.pixmap_item:
            try:
                # Check if the item is still valid before removing
                _ = self.pixmap_item.pos()
                
                # If we get here, the object is still valid, so we can remove it
                if self.scene:
                    try:
                        self.scene.removeItem(self.pixmap_item)
                    except (AttributeError, RuntimeError):
                        # Scene or item already invalid
                        pass
            except (AttributeError, RuntimeError):
                # Object already deleted, just clear our reference
                pass
            finally:
                self.pixmap_item = None


    def stop_animation(self):
        """SAFE stop animation with proper cleanup"""
        self.is_playing = False
        
        # Stop timer safely
        try:
            if self.animation_timer:
                self.animation_timer.stop()
        except (AttributeError, RuntimeError):
            pass
        
        # Clean up pixmap item safely
        self._safe_cleanup_pixmap_item()
    






    def force_start_animation(self):
        """Force start animation with better error handling"""
        try:
            print("🚀 Force starting animation...")
            
            if not self.frames or len(self.frames) == 0:
                print("⚠️ No frames to animate")
                return
                
            # Reset state
            self.current_frame_index = 0
            self.is_playing = True
            
            # Stop any existing timer
            if self.animation_timer:
                self.animation_timer.stop()
            
            # Clear any invalid pixmap item
            if self.pixmap_item:
                try:
                    _ = self.pixmap_item.isVisible()
                except (AttributeError, RuntimeError):
                    print("🧹 Clearing invalid pixmap item")
                    self.pixmap_item = None
            
            print(f"📊 Animation ready: {len(self.frames)} frames")
            
            # Start the animation loop
            self.animate_gif()
            
            print("✅ Animation force started successfully")
            
        except Exception as e:
            print(f"❌ Error force starting animation: {e}")








    def animate_gif(self):
        """SAFER animation loop - more resilient to temporary issues"""
        if not self.frames or not self.is_playing:
            return
            
        try:
            # Basic checks first
            if self.current_frame_index >= len(self.frames):
                self.current_frame_index = 0
                
            frame = self.frames[self.current_frame_index]
            delay = self.delays[self.current_frame_index]
            
            # Verify frame is valid
            if frame.isNull():
                print("⚠️ Invalid frame detected, skipping frame")
                self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
                if self.is_playing:
                    self.animation_timer.start(100)  # Try again in 100ms
                return
            
            # Handle pixmap item creation/update
            if self.pixmap_item:
                # Try to update existing item
                try:
                    self.pixmap_item.setPixmap(frame)
                except (AttributeError, RuntimeError):
                    print("🔧 Pixmap item invalid, recreating...")
                    self.pixmap_item = None
                    # Will be recreated below
            
            # Create new pixmap item if needed
            if not self.pixmap_item and self.scene:
                try:
                    self.pixmap_item = self.scene.addPixmap(frame)
                    print("🆕 Created new pixmap item")
                except (AttributeError, RuntimeError):
                    print("⚠️ Could not create pixmap item, retrying...")
                    if self.is_playing:
                        self.animation_timer.start(100)  # Retry in 100ms
                    return
            
            # Position the pixmap (with error handling)
            if self.scene and self.pixmap_item:
                try:
                    scene_rect = self.scene.sceneRect()
                    x = (scene_rect.width() - frame.width()) / 2
                    y = (scene_rect.height() - frame.height()) / 2
                    self.pixmap_item.setPos(x, y)
                except (AttributeError, RuntimeError):
                    # Positioning failed, but continue animation
                    print("⚠️ Could not position pixmap")
            
            # Move to next frame
            self.current_frame_index = (self.current_frame_index + 1) % len(self.frames)
            
            # Schedule next frame - be more resilient to issues
            if self.is_playing:
                self.animation_timer.start(delay)
                
        except Exception as e:
            print(f"Error in animate_gif: {e}")
            # Don't stop animation on every error - just retry
            if self.is_playing:
                self.animation_timer.start(100)  # Retry in 100ms


    # 2. REPLACE this safety check method in CharacterAnimator class (LESS AGGRESSIVE)
    def _verify_animation_objects(self):
        """Verify that animation objects are still valid - IMPROVED VERSION"""
        try:
            # Check if scene exists and has a valid parent
            if not self.scene:
                print("🔍 Scene is None")
                return False
                
            # Check if we have valid frames to animate
            if not self.frames or len(self.frames) == 0:
                print("🔍 No frames available")
                return False
                
            # Check if the current frame index is valid
            if self.current_frame_index >= len(self.frames):
                print("🔍 Invalid frame index")
                return False
                
            # Only check pixmap_item if animation is supposed to be playing
            if self.is_playing and self.pixmap_item:
                try:
                    # Light check - just see if we can access the item
                    _ = self.pixmap_item.isVisible()
                except (AttributeError, RuntimeError):
                    print("🔍 Pixmap item was deleted")
                    self.pixmap_item = None  # Clear invalid reference
                    # Don't return False - we can recreate the item
                    
            return True
            
        except Exception as e:
            print(f"🔍 Exception in object verification: {e}")
            return False
    
    def clear_cache(self):
        """Clear animation cache to free memory"""
        self.preloaded_animations.clear()



class MainApplication(QMainWindow):
    """Main application window with dynamic color updates"""
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Character Chat System")
        self.setFixedSize(400, 400)
        
        # Initialize components
        self.user_profile_manager = UserProfileManager()
        self.character_manager = CharacterManager()
        self.ai_interface = EnhancedAIInterface()



        self.current_character = None
        self.chat_windows = {}
        self.interaction_icons = []
        self.editor_mode = False
        self.current_interaction_timer = None
        self.interaction_in_progress = False
        self.current_interaction_timer = None
        self.last_interaction_time = 0
        self.interaction_debounce_ms = 300
        self._original_image_path = None
        self.menu_visible = True  # Add this to track menu state


        self.interaction_locks = {}
        self.last_interaction_times = {}
        self.interaction_sequences = {}
        
        self.global_schedule_timer = QTimer()
        self.global_schedule_timer.timeout.connect(self._check_all_scheduled_reminders)
        self.global_schedule_timer.start(60000) 



        # Periodic cleanup timer
        self.interaction_cleanup_timer = QTimer()
        self.interaction_cleanup_timer.timeout.connect(self._cleanup_interaction_tracking)
        self.interaction_cleanup_timer.start(10000)  # Clean up every 10 seconds




        # Window customization
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.always_on_top = False
        
        # IMPORTANT: Set up UI FIRST before connecting to color signals
        self._setup_ui()
        app_colors.colors_changed.connect(self.update_colors)

        
        # Load colors (this may trigger update_colors, but UI exists now)
        app_colors.load_colors()
        
        self._load_state()
        QTimer.singleShot(250, self._maybe_show_startup_about)

        # For window dragging
        self.drag_position = None
    
    def show_about_dialog(self):
        enabled = getattr(self.user_profile_manager.settings, "show_about_on_startup", True)
        dlg = AboutDialog(self, show_on_startup=enabled)
        dlg.exec()

        new_value = dlg.show_on_startup
        if new_value != enabled:
            self.user_profile_manager.settings.show_about_on_startup = new_value
            self.user_profile_manager.save_settings()

    def _maybe_show_startup_about(self):
        if getattr(self, "_startup_about_shown", False):
            return
        self._startup_about_shown = True

        if getattr(self.user_profile_manager.settings, "show_about_on_startup", True):
            self.show_about_dialog()








    def _setup_ui(self):
        """Create the main interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Custom title bar
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet(f"background-color: {app_colors.PRIMARY};")
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(5, 0, 5, 0)
        title_layout.addStretch()
        
        # Control buttons
        self.menu_toggle_btn = QPushButton("☰")
        self.menu_toggle_btn.setFixedSize(30, 25)
        self.menu_toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 0, 0, 0.5);
            }}
        """)
        self.menu_toggle_btn.clicked.connect(self._toggle_menu_bar)
        title_layout.addWidget(self.menu_toggle_btn)
        
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(30, 25)
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 9pt;
                font-weight: bold;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 0, 0, 0.5);
            }}
        """)
        self.pin_btn.clicked.connect(self._toggle_always_on_top)
        title_layout.addWidget(self.pin_btn)
        
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(30, 25)
        minimize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        minimize_btn.clicked.connect(self.showMinimized)
        title_layout.addWidget(minimize_btn)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 25)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 3px;
                padding: -3px 0px 0px 0px;  /* Added padding adjustment */
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 0, 0, 0.5);
            }}
        """)
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(self.title_bar)
        
        # Content frame
        self.content_frame = QWidget()
        self.content_frame.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(self.content_frame)
        
        content_layout = QVBoxLayout(self.content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Menu bar frame
        self.menu_frame = QWidget()
        self.menu_frame.setFixedHeight(25)
        self.menu_frame.setStyleSheet("background-color: #E0E0E0;")
        self.menu_visible = True
        content_layout.addWidget(self.menu_frame)
        
        # Create menu bar
        self._create_menu_bar()
        
        # Character display
        self.character_view = QGraphicsView()
        self.character_view.setStyleSheet("background-color: #F0F4F8; border: none;")
        self.character_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.character_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.scene = QGraphicsScene()
        self.character_view.setScene(self.scene)
        content_layout.addWidget(self.character_view)
        
        # Character animator
        self.animator = CharacterAnimator(self.scene)
        
        # Store current dimensions
        self.current_image_width = 400
        self.current_image_height = 400
    


    def _cleanup_interaction_tracking(self):
        """Clean up old interaction tracking data"""
        try:
            import time
            current_time = time.time()
            
            # Clean up old interaction times (keep only last 30 seconds)
            if hasattr(self, 'last_interaction_times'):
                old_times = []
                for key, timestamp in self.last_interaction_times.items():
                    if current_time - timestamp > 30:
                        old_times.append(key)
                for key in old_times:
                    del self.last_interaction_times[key]
            
            # Clean up old sequence tracking (keep only last 60 seconds)
            if hasattr(self, 'interaction_sequences'):
                old_sequences = []
                for key in self.interaction_sequences.keys():
                    try:
                        # Extract timestamp from sequence key
                        timestamp = float(key.split('_')[-1]) * 2  # Reverse the /2 operation
                        if current_time - timestamp > 60:
                            old_sequences.append(key)
                    except:
                        old_sequences.append(key)  # Remove malformed keys
                for key in old_sequences:
                    del self.interaction_sequences[key]
            
            # Clean up stale locks (shouldn't happen, but safety)
            if hasattr(self, 'interaction_locks'):
                stale_locks = []
                for key, timestamp in self.interaction_locks.items():
                    if current_time - timestamp > 10:  # 10 second timeout for locks
                        stale_locks.append(key)
                for key in stale_locks:
                    del self.interaction_locks[key]
                    print(f"🧹 Removed stale lock: {key}")
            
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")




    def _check_all_scheduled_reminders(self):
        """Check scheduled dialogs AND proactive check-ins for the current character"""
        if not self.current_character:
            return
        
        # Load scheduled dialogs for current character
        app_data_dir = get_app_data_dir()
        dialog_file = app_data_dir / "characters" / self.current_character.name / "scheduled_dialogs.json"
        
        if dialog_file.exists():
            try:
                with open(dialog_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    scheduled_dialogs = [ScheduledDialog(**d) for d in data]
            except Exception as e:
                print(f"Error loading dialogs: {e}")
        else:
            scheduled_dialogs = []
        
        # Check if any dialog should trigger
        now = datetime.now()
        now_str = now.strftime("%H:%M")
        
        for dialog in scheduled_dialogs:
            if not dialog.enabled:
                continue
            
            should_trigger = False
            
            if dialog.date:
                try:
                    target_date = datetime.strptime(dialog.date, "%Y-%m-%d")
                    delta_days = (target_date.date() - now.date()).days
                    if delta_days == dialog.advance_days and now_str == dialog.time:
                        should_trigger = True
                except ValueError:
                    continue
            else:
                if now_str == dialog.time:
                    should_trigger = True
            
            if should_trigger:
                if not hasattr(dialog, "triggered") or not dialog.triggered:
                    dialog.triggered = True
                    self._handle_scheduled_reminder(dialog.prompt)
        
        # Reset triggered flags
        for dialog in scheduled_dialogs:
            if hasattr(dialog, "triggered") and now_str != dialog.time:
                dialog.triggered = False
        
        # 🆕 NEW: Check for proactive check-ins
        self._check_proactive_checkins()

    def _check_proactive_checkins(self):
        """Check if character should send proactive check-in"""
        if not self.current_character:
            return
        
        char_name = self.current_character.name
        
        # Check if chat window is open to read its check-in settings
        if char_name in self.chat_windows:
            try:
                chat_window = self.chat_windows[char_name]
                if (chat_window.isVisible() or 
                    (hasattr(chat_window, 'minimize_bar') and chat_window.minimize_bar and chat_window.minimize_bar.isVisible())):
                    
                    # Window is open, check if it should send check-in
                    if hasattr(chat_window, '_should_check_in') and chat_window._should_check_in():
                        chat_window._send_checkin_message()
                    return
            except (RuntimeError, AttributeError):
                del self.chat_windows[char_name]
        
        # 🆕 NEW: Window is closed, but we might still need to check-in and auto-open
        self._check_checkin_for_closed_window()

    def _check_checkin_for_closed_window(self):
        """Check if we should send check-in for closed window and auto-open"""
        try:
            # Load check-in settings for the character
            app_data_dir = get_app_data_dir()
            settings_file = app_data_dir / "characters" / self.current_character.name / "checkin_settings.json"
            
            if not settings_file.exists():
                return
            
            with open(settings_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                checkin_settings = CheckInSettings.from_dict(data)
            
            if not checkin_settings.enabled:
                return
            
            # Load last user message time from chat history
            history_file = app_data_dir / "characters" / self.current_character.name / "chat_history.json"
            if not history_file.exists():
                return
            
            with open(history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            # Find the most recent user message
            last_user_time = None
            if "messages" in history_data:
                for msg_data in history_data["messages"].values():
                    if msg_data.get("role") == "user":
                        try:
                            msg_time = datetime.strptime(msg_data["timestamp"], "%Y-%m-%d %H:%M:%S")
                            if not last_user_time or msg_time > last_user_time:
                                last_user_time = msg_time
                        except:
                            continue
            
            if not last_user_time:
                return
            
            # Check if enough time has passed for check-in
            now = datetime.now()
            time_since_last = now - last_user_time
            
            # Check quiet hours
            if self._is_quiet_hours_global(checkin_settings):
                return
            
            # Check if should send check-in
            if (time_since_last >= timedelta(minutes=checkin_settings.interval_minutes) and
                time_since_last <= timedelta(hours=checkin_settings.max_idle_hours)):
                
                # Load last check-in time
                checkin_state_file = app_data_dir / "characters" / self.current_character.name / "last_checkin.json"
                last_checkin_time = None
                
                if checkin_state_file.exists():
                    try:
                        with open(checkin_state_file, 'r', encoding='utf-8') as f:
                            state_data = json.load(f)
                            last_checkin_time = datetime.strptime(state_data["last_checkin"], "%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                
                # Check if enough time since last check-in
                if (not last_checkin_time or 
                    now - last_checkin_time >= timedelta(minutes=checkin_settings.interval_minutes)):
                    
                    # 🆕 AUTO-OPEN CHAT AND SEND CHECK-IN WITH FLASH
                    print(f"📋 Auto-opening chat for proactive check-in: {self.current_character.display_name}")
                    self._create_new_chat_window_for_checkin()
                    
                    # Save check-in time
                    checkin_state_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(checkin_state_file, 'w', encoding='utf-8') as f:
                        json.dump({"last_checkin": now.strftime("%Y-%m-%d %H:%M:%S")}, f)
        
        except Exception as e:
            print(f"Error checking proactive check-in: {e}")

    def _is_quiet_hours_global(self, settings):
        """Check if current time is within quiet hours - GLOBAL VERSION"""
        if not settings.quiet_hours_start or not settings.quiet_hours_end:
            return False
            
        now = datetime.now().time()
        try:
            start = datetime.strptime(settings.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(settings.quiet_hours_end, "%H:%M").time()
            
            # 🆕 SPECIAL CASE: 00:00 to 00:00 means "always quiet" (block all messages)
            if start == end and start.hour == 0 and start.minute == 0:
                print(f"🔇 Always quiet hours detected (00:00-00:00) - blocking all messages")
                return True
            
            if start <= end:
                return start <= now <= end
            else:  # Quiet hours span midnight
                return now >= start or now <= end
        except:
            return False

    def _create_new_chat_window_for_checkin(self):
        """Create new chat window specifically for check-in with flash"""
        if not self.current_character:
            return
            
        char_name = self.current_character.name
        print(f"Creating new chat window for check-in: {char_name}")
        
        # Remove any existing reference
        if char_name in self.chat_windows:
            print(f"Removing existing window reference for {char_name}")
            del self.chat_windows[char_name]
        
        # Create new window with check-in flag
        chat_window = ChatWindow(self, self.current_character, self.ai_interface, None, is_checkin=True)
        self.chat_windows[char_name] = chat_window
        
        print(f"Chat window created for check-in: {char_name}")
        chat_window.show()
        return chat_window

    def _handle_scheduled_reminder(self, prompt_text: str):
        """Handle scheduled reminder - INSTANT PROCESSING"""
        char_name = self.current_character.name
        
        # Check if chat window is open
        if char_name in self.chat_windows:
            try:
                chat_window = self.chat_windows[char_name]
                if chat_window.isVisible() or (hasattr(chat_window, 'minimize_bar') and 
                                            chat_window.minimize_bar and 
                                            chat_window.minimize_bar.isVisible()):
                    # Window is open, send reminder directly
                    chat_window._send_reminder_as_character(prompt_text)
                    return
            except (RuntimeError, AttributeError):
                del self.chat_windows[char_name]
        
        # Create window WITH scheduled reminder for instant processing
        print(f"📅 Opening chat window for scheduled reminder: {self.current_character.display_name}")
        self._create_new_chat_window(scheduled_reminder=prompt_text)


    def update_colors(self):
        """Update all colors in main window - FIXED VERSION"""
        # Debouncing
        current_time = time.time()
        if hasattr(self, '_last_color_update_time'):
            if current_time - self._last_color_update_time < 0.1:
                return
        self._last_color_update_time = current_time
        
        # Check if UI components exist before updating them
        if not hasattr(self, 'title_bar') or self.title_bar is None:
            return
        
        # DETERMINE WHICH COLORS TO USE: Character-specific or Global
        primary_color = app_colors.PRIMARY
        secondary_color = app_colors.SECONDARY
        
        # Check if current character has custom colors enabled
        if (hasattr(self, 'current_character') and 
            self.current_character and 
            getattr(self.current_character, 'use_character_colors', False)):
            
            # Use character-specific colors
            char_primary = getattr(self.current_character, 'character_primary_color', '')
            char_secondary = getattr(self.current_character, 'character_secondary_color', '')
            
            if char_primary and char_secondary:
                primary_color = char_primary
                secondary_color = char_secondary
        
        # Only update if colors actually changed
        if hasattr(self, '_last_main_colors'):
            if self._last_main_colors == (primary_color, secondary_color):
                return
        
        self._last_main_colors = (primary_color, secondary_color)
        
        # UPDATE TITLE BAR
        try:
            self.title_bar.setStyleSheet(f"background-color: {primary_color};")
        except (AttributeError, RuntimeError):
            pass
        
        # UPDATE CHARACTER VIEW - ONLY if not using custom background settings
        if hasattr(self, 'character_view') and self.character_view is not None:
            try:
                # OPTION 1: Don't change character view background at all
                # (Comment out the lines below to prevent any background changes)
                
                # OPTION 2: Only change in editor mode, otherwise keep original
                if hasattr(self, 'editor_mode') and self.editor_mode:
                    bg_color = "#FFE0E0"  # Editor mode color
                    self.character_view.setStyleSheet(f"background-color: {bg_color}; border: none;")
                # Don't change background for normal mode - let it keep its original color
                    
            except (AttributeError, RuntimeError):
                pass
        
        # UPDATE ALL CONTROL BUTTONS
        self._update_all_control_buttons_with_colors(primary_color, secondary_color)
        
        # UPDATE CHAT WINDOWS (call their update_colors method)
        if hasattr(self, 'chat_windows'):
            for name, window in list(self.chat_windows.items()):
                try:
                    if window and hasattr(window, 'update_colors'):
                        window.update_colors()
                except (RuntimeError, AttributeError):
                    # Remove invalid windows
                    if name in self.chat_windows:
                        del self.chat_windows[name]
        
        # Single clean log message
        print(f"🎨 MainWindow: Colors updated ({primary_color[:7]} / {secondary_color[:7]})")


    def _update_all_control_buttons_with_colors(self, primary_color, secondary_color):
        """Update all control button styles with specific colors"""
        # Check if title_bar exists and has been set up
        if not hasattr(self, 'title_bar') or self.title_bar is None:
            return
        
        try:
            # Update menu toggle button
            if hasattr(self, 'menu_toggle_btn') and self.menu_toggle_btn is not None:
                self.menu_toggle_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {secondary_color};
                        border: none;
                        font-size: 9pt;
                        font-weight: bold;
                        border-radius: 3px;
                    }}
                    QPushButton:hover {{
                        background-color: {secondary_color};
                        color: {primary_color};
                    }}
                """)
            
            # Update pin button with special logic for active/inactive state
            if hasattr(self, 'pin_btn') and self.pin_btn is not None:
                pin_color = "#FFD700" if getattr(self, 'always_on_top', False) else secondary_color
                self.pin_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {pin_color};
                        border: none;
                        font-size: 11pt;
                        border-radius: 3px;
                    }}
                    QPushButton:hover {{
                        background-color: rgba(255, 255, 255, 0.2);
                    }}
                    QPushButton:pressed {{
                        background-color: rgba(255, 255, 255, 0.3);
                    }}
                """)
            
            # Update all other title bar buttons
            if hasattr(self, 'title_bar') and self.title_bar is not None:
                title_buttons = self.title_bar.findChildren(QPushButton)
                for btn in title_buttons:
                    if not btn:
                        continue
                        
                    button_text = btn.text()
                    
                    if button_text == "❖":  # Settings button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary_color};
                                border: none;
                                font-size: 11pt;
                                border-radius: 3px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
                    elif button_text == "−":  # Minimize button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary_color};
                                border: none;
                                font-size: 12pt;
                                font-weight: bold;
                                border-radius: 3px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
                    elif button_text == "×":  # Close button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary_color};
                                border: none;
                                font-size: 14pt;
                                font-weight: bold;
                                border-radius: 3px;
                                padding: -3px 0px 0px 0px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 0, 0, 0.3);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 0, 0, 0.5);
                            }}
                        """)
                        
        except (AttributeError, RuntimeError) as e:
            print(f"Error updating control buttons: {e}")





    def _run_interaction(self, interaction: Interaction):
        """Run an interaction animation with zero flicker"""
        if not self.animator.current_image_path:
            return
        
        current_time = QDateTime.currentMSecsSinceEpoch()
        
        # Debouncing: Prevent spam clicking
        if current_time - self.last_interaction_time < self.interaction_debounce_ms:
            return
        
        self.last_interaction_time = current_time
        
        # Store original image path if not already stored
        if not self._original_image_path:
            self._original_image_path = self.animator.current_image_path
        
        # Clean up any existing timer
        if self.current_interaction_timer:
            self.current_interaction_timer.stop()
            self.current_interaction_timer.deleteLater()
            self.current_interaction_timer = None
        
        # Mark interaction as in progress
        self.interaction_in_progress = True
        
        # SEAMLESS TRANSITION: Load new animation without stopping current display
        self.animator.seamless_load_animation(interaction.base_image_path)
        
        # Create timer for returning to original
        self.current_interaction_timer = QTimer()
        self.current_interaction_timer.setSingleShot(True)
        self.current_interaction_timer.timeout.connect(
            lambda: self._restore_original_animation()
        )
        
        # Start timer
        duration_ms = max(interaction.duration * 1000, 1000)
        self.current_interaction_timer.start(duration_ms)
        
        # Send to chat if window is open
        self._send_interaction_to_chat_if_open(interaction)

    def _start_new_interaction(self, interaction: Interaction):
        """Start a new interaction with comprehensive cleanup"""
        try:
            # Ensure we're in a clean state
            self._force_cleanup_interaction()
            
            # Mark interaction as in progress
            self.interaction_in_progress = True
            
            # Store original image path if not already stored
            if not self._original_image_path:
                self._original_image_path = self.animator.current_image_path
            
            print(f"Loading interaction animation: {interaction.base_image_path}")
            
            # Stop current animation completely before loading new one
            self.animator.stop_animation()
            QCoreApplication.processEvents()  # Process any pending events
            
            # Load and start interaction animation
            self.animator.load_animation(interaction.base_image_path)
            self.animator.start_animation()
            
            # Create timer for returning to original
            self.current_interaction_timer = QTimer()
            self.current_interaction_timer.setSingleShot(True)
            self.current_interaction_timer.timeout.connect(
                lambda: self._restore_original_animation()
            )
            
            # Start timer
            duration_ms = max(interaction.duration * 1000, 1000)  # Minimum 1 second
            self.current_interaction_timer.start(duration_ms)
            
            print(f"Interaction timer started for {duration_ms}ms")
            
            # Send to chat if window is open
            self._send_interaction_to_chat_if_open(interaction)
            
        except Exception as e:
            print(f"Error starting interaction: {e}")
            self._force_cleanup_interaction()


    def _send_interaction_to_chat(self, chat_window, interaction: Interaction):
        """Enhanced interaction handling with immediate UI updates"""
        from datetime import datetime
        import time
        
        # Check if AI is writing - block interactions
        if hasattr(chat_window, 'is_ai_writing') and chat_window.is_ai_writing:
            print("❌ BLOCKED INTERACTION - AI is writing!")
            return False
        
        # Your existing deduplication code...
        if not hasattr(self, 'interaction_locks'):
            self.interaction_locks = {}
        if not hasattr(self, 'last_interaction_times'):
            self.last_interaction_times = {}
        if not hasattr(self, 'interaction_sequences'):
            self.interaction_sequences = {}
        
        current_time = time.time()
        interaction_key = interaction.name
        
        print(f"🎭 INTERACTION START: {interaction.name}")
        
        # Time-based debouncing
        if interaction_key in self.last_interaction_times:
            time_diff = current_time - self.last_interaction_times[interaction_key]
            if time_diff < 0.8:
                print(f"⏱️ BLOCKED: Too soon ({time_diff:.2f}s)")
                return False
        
        self.last_interaction_times[interaction_key] = current_time
        
        # Active processing lock
        if interaction_key in self.interaction_locks:
            print(f"🔒 BLOCKED: Already processing {interaction_key}")
            return False
        
        self.interaction_locks[interaction_key] = current_time
        
        try:
            # Chat window validation
            if not chat_window or not hasattr(chat_window, 'chat_tree'):
                print("❌ BLOCKED: Invalid chat window")
                return False
            
            # Create interaction message
            interaction_message = f"*{interaction.name}*"
            current_timestamp = datetime.now()
            timestamp_str = current_timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"📝 Creating interaction message: '{interaction_message}'")
            
            # Create user message
            user_msg = ChatMessage("user", interaction_message, timestamp_str)
            print(f"📝 Created message: {user_msg.id[:8]} - '{interaction_message}'")
            
            # Add to chat tree
            msg_id = chat_window.chat_tree.add_message(user_msg)
            if msg_id != user_msg.id:
                print(f"⚠️ Message ID changed: {user_msg.id[:8]} -> {msg_id[:8]}")
                user_msg.id = msg_id
            
            print(f"📚 Added to tree: {msg_id[:8]}")
            
            # CRITICAL: Force immediate UI update for user message
            print(f"💬 Creating immediate bubble for interaction message...")
            
            # Use the signal-based approach to ensure immediate display
            chat_window.add_bubble_signal.emit(user_msg)
            
            # Process any pending UI events to ensure bubble appears
            from PySide6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Small delay to ensure UI is updated
            time.sleep(0.05)
            
            print(f"✅ User message bubble should now be visible")
            
            # Save chat history immediately after user message
            chat_window._save_chat_history()
            
            # Get character and user names for personality enhancement
            user_profile = chat_window._get_effective_user_profile()
            character_name = getattr(self.current_character, 'display_name', self.current_character.name)
            user_name = user_profile.user_name if user_profile else "User"
            
            print(f"👥 Context: {user_name} -> {character_name}")
            
            # Enhanced personality for interaction
            base_personality = f"You are {character_name} - {self.current_character.personality}"
            
            if user_profile:
                user_context = f"""
    User Profile:
    {user_name} is {user_profile.name}. {user_profile.personality}"""
            else:
                user_context = ""
            
            interaction_context = f"""
    INTERACTION: {user_name} just performed the '{interaction.name}' interaction with you.
    Respond naturally and briefly to this interaction. Acknowledge what happened and react in character."""
            
            enhanced_personality = f"""{base_personality}{user_context}{interaction_context}"""
            
            # Replace placeholders
            from ..utils.helpers import replace_name_placeholders
            enhanced_personality = replace_name_placeholders(enhanced_personality, character_name, user_name)
            
            print(f"🎭 Enhanced personality prepared")
            
            # Temporarily override personality
            original_personality = chat_window.character.personality
            chat_window.character.personality = enhanced_personality
            
            # Queue for AI response
            print(f"📤 Queuing for AI: '{interaction_message}' -> {user_msg.id[:8]}")
            
            if hasattr(chat_window, 'message_queue'):
                chat_window.message_queue.put((interaction_message, user_msg.id))
                print(f"✅ Queued successfully")
            else:
                print(f"❌ No message queue found!")
            
            # Restore original personality after a delay
            def restore_personality():
                try:
                    chat_window.character.personality = original_personality
                except:
                    pass
            
            from PySide6.QtCore import QTimer
            QTimer.singleShot(100, restore_personality)
            
            return True
            
        finally:
            # Clean up locks
            if interaction_key in self.interaction_locks:
                del self.interaction_locks[interaction_key]




    def _create_menu_bar(self):
        """Create the menu bar"""
        menu_layout = QHBoxLayout(self.menu_frame)
        menu_layout.setContentsMargins(5, 0, 5, 0)
        menu_layout.setSpacing(5)
        
        # File menu
        file_btn = QPushButton("File")
        file_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #ccc;
                padding: 2px 15px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        file_menu = QMenu(self)
        file_menu.addAction("New Character", self._new_character)
        self.add_interaction_action = file_menu.addAction("Add Interaction", self._add_interaction)
        self.add_interaction_action.setEnabled(False)
        file_menu.addSeparator()
        self.export_character_action = file_menu.addAction("Export Character", self._export_character)
        file_menu.addAction("Import Character", self._import_character)
        self.export_character_action.setEnabled(False)
        
        file_menu.addSeparator()
        file_menu.addAction("User Profiles", self._open_user_profiles)  # This was mentioned earlier
        file_menu.addSeparator()
        file_menu.addAction("Exit", self.close)
        file_btn.setMenu(file_menu)
        menu_layout.addWidget(file_btn)
        
        # Characters menu
        characters_btn = QPushButton("Characters")
        characters_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #ccc;
                padding: 2px 15px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        self.characters_menu = QMenu(self)
        self._update_characters_menu()
        characters_btn.setMenu(self.characters_menu)
        menu_layout.addWidget(characters_btn)
        
        # Edit menu
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #ccc;
                padding: 2px 15px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        edit_menu = QMenu(self)
        self.edit_image_action = edit_menu.addAction("Edit Image", self._edit_character_image)
        self.edit_personality_action = edit_menu.addAction("Edit Personality", self._edit_personality)
        self.edit_names_action = edit_menu.addAction("Edit Names", self._edit_character_names)  
        self.character_colors_action = edit_menu.addAction("Character Colors", self._open_character_colors) 
        # ADD THIS LINE:
        self.external_apis_action = edit_menu.addAction("🔌 External APIs", self._open_external_apis)
        edit_menu.addSeparator()
        self.editor_mode_action = edit_menu.addAction("Editor Mode", self._toggle_editor_mode)

        self.editor_mode_action.setCheckable(True)  # Make it show a checkmark
        self.editor_mode_action.setChecked(False) 
        edit_menu.addSeparator()
        self.delete_character_action = edit_menu.addAction("Delete Character", self._delete_character)

        # Disable edit actions initially
        self.edit_image_action.setEnabled(False)
        self.edit_personality_action.setEnabled(False)
        self.edit_names_action.setEnabled(False)
        self.character_colors_action.setEnabled(False)
        # ADD THIS LINE:
        self.external_apis_action.setEnabled(False)
        self.editor_mode_action.setEnabled(False)
        self.delete_character_action.setEnabled(False)



        
        edit_btn.setMenu(edit_menu)
        menu_layout.addWidget(edit_btn)
        
# In your _create_menu_bar method, update the API menu section:

        api_btn = QPushButton("API")
        api_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #ccc;
                padding: 2px 15px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        api_menu = QMenu(self)
        api_menu.addAction("📋 Manage API Configs", self._open_api_manager)
        api_menu.addAction("🎭 Select API for Character", self._select_character_api)
        api_menu.addSeparator()  # Add this line
        api_menu.addAction("🔧 Test Instruction Format", self.test_instruction_format_in_chat)  # Add this line
        api_menu.addSeparator()
        api_btn.setMenu(api_menu)
        menu_layout.addWidget(api_btn)

        # View menu
        view_btn = QPushButton("View")
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                border: 1px solid #ccc;
                padding: 2px 15px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
        """)
        view_menu = QMenu(self)
        view_menu.addAction("Reset Window", self._reset_window)
        view_menu.addAction("Edit Colors", self._open_color_editor)
        view_menu.addSeparator()
        view_menu.addAction("About", self.show_about_dialog)
        view_btn.setMenu(view_menu)
        menu_layout.addWidget(view_btn)
        
        menu_layout.addStretch()
    

    def _open_api_manager(self):
        """Open API configuration manager"""
        dialog = APIConfigManager(self, self.ai_interface)
        dialog.exec()

    def _select_character_api(self):
        """Select API configuration for current character"""
        if not self.current_character:
            QMessageBox.warning(self, "No Character", "Please load a character first.")
            return
        
        config_names = list(self.ai_interface.api_configs.keys())
        if not config_names:
            QMessageBox.warning(self, "No API Configs", 
                            "Please create an API configuration first.")
            return
        
        # Create selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Select API Configuration")
        dialog.setFixedSize(400, 250)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        layout.addWidget(QLabel(f"Select API for {self.current_character.display_name}:"))
        
        combo = QComboBox()
        combo.addItem("(Default)", None)
        for name in config_names:
            combo.addItem(name, name)
        
        # Set current selection
        if hasattr(self.current_character, 'api_config_name') and self.current_character.api_config_name:
            index = combo.findData(self.current_character.api_config_name)
            if index >= 0:
                combo.setCurrentIndex(index)
        
        layout.addWidget(combo)
        
        button_layout = QHBoxLayout()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        if dialog.exec():
            selected_config = combo.currentData()
            self.current_character.api_config_name = selected_config
            
            # FIXED: Save character config using proper path structure
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.current_character.folder_name
            config_file = char_dir / "config.json"
            
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(asdict(self.current_character), f, indent=2)
                
                api_name = selected_config or "Default"
                QMessageBox.information(self, "Success", f"API set to: {api_name}")
                print(f"✅ Saved API config '{api_name}' for character '{self.current_character.folder_name}'")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save API configuration: {str(e)}")
                print(f"❌ Error saving API config: {e}")


    def _open_user_profiles(self):
        """Open user profiles dialog"""
        dialog = UserProfileDialog(self, self.user_profile_manager)
        dialog.exec()


    def refresh_character_display(self):
        """SAFE refresh ONLY the character display without affecting chat windows or interactions"""
        try:
            print("🔄 Refreshing character display only (isolated)...")
            
            if not self.current_character:
                print("⚠️ No current character to refresh")
                return
            
            # CRITICAL: Stop all animations BEFORE clearing anything
            if hasattr(self, 'animator') and self.animator:
                print("🛑 Stopping animations before refresh...")
                self.animator.stop_animation()
                # Give Qt time to process the stop
                QCoreApplication.processEvents()
            
            # Stop any interaction timers (but don't affect interactions)
            if hasattr(self, 'current_interaction_timer') and self.current_interaction_timer:
                self.current_interaction_timer.stop()
                self.current_interaction_timer = None
            
            # Clear only character-specific caches
            QPixmapCache.clear()
            
            # Reload the character to get the updated image path
            updated_character = self.character_manager.load_character(self.current_character.name)
            if updated_character:
                # Update the current character reference
                old_character_name = self.current_character.display_name
                self.current_character = updated_character
                
                # SAFE: Clear and rebuild the scene
                if hasattr(self, 'scene') and self.scene:
                    print("🧹 Safely clearing scene...")
                    self.scene.clear()  # This will properly delete all items
                
                # CRITICAL: Reload and restart the animation (like _load_character does)
                if updated_character.base_image and os.path.exists(updated_character.base_image):
                    print(f"🔄 Reloading character animation: {os.path.basename(updated_character.base_image)}")
                    
                    # Load animation (this sets up frames and dimensions)
                    width, height = self.animator.load_animation(updated_character.base_image)
                    print(f"📏 Animation loaded with dimensions: {width}x{height}")
                    
                    # Update stored dimensions
                    self.current_image_width = width
                    self.current_image_height = height
                    
                    # Update window size if needed
                    self._update_window_size()
                    print("📐 Window size updated")
                    
                    # Start the animation with a small delay to ensure scene is ready
                    QTimer.singleShot(100, self.animator.force_start_animation)
                    print("⏰ Animation start scheduled")
                    
                    print(f"✅ Character animation reloaded: {width}x{height}")
                else:
                    print(f"⚠️ Character base image not found: {updated_character.base_image}")
                
                # Update window title if it shows character name
                if hasattr(self, 'setWindowTitle'):
                    self.setWindowTitle(f"Character Manager - {updated_character.display_name}")
                
                print(f"✅ Character display safely refreshed for: {updated_character.display_name}")
            else:
                print("⚠️ Could not reload character data")
                
        except Exception as e:
            print(f"❌ Error in isolated character refresh: {e}")


    # 7. REMOVE/SIMPLIFY the _update_character_view_image_only method (no longer needed)
    def _update_character_view_image_only(self):
        """This method is no longer needed - refresh_character_display handles everything"""
        # This method can be removed or simplified since refresh_character_display 
        # now handles the complete reload properly
        print("ℹ️ _update_character_view_image_only called but refresh_character_display handles this now")
        pass




    def test_instruction_format_in_chat(self):
        """Test method you can call to see if instruction format is working"""
        if not self.current_character:
            QMessageBox.warning(self, "No Character", "Please load a character first.")
            return
        
        config_name = getattr(self.current_character, 'api_config_name', None)
        if not config_name:
            QMessageBox.warning(self, "No API Config", "Character has no API configuration set.")
            return
        
        # Test messages
        test_messages = [
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"},
            {"role": "user", "content": "What's the weather like?"}
        ]
        
        # Get debug output
        debug_output = self.ai_interface.debug_instruction_format(config_name, test_messages)
        
        # Show in dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Instruction Format Debug")
        dialog.setFixedSize(600, 400)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setPlainText(debug_output)
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Courier", 10))
        layout.addWidget(text_edit)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        dialog.exec()


    def _export_character(self):
        """Enhanced export character with all current features including interactions"""
        if not self.current_character:
            QMessageBox.warning(self, "No Character", "Please load a character first.")
            return
        
        # Use display_name for the suggested filename, but sanitize it
        display_name = getattr(self.current_character, 'display_name', self.current_character.name)
        safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', display_name)
        
        # Select export location
        export_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Character Package", 
            f"{safe_name}.zip",
            "ZIP files (*.zip)"
        )
        
        if export_path:
            try:
                import zipfile
                app_data_dir = get_app_data_dir()
                # Use folder_name for the actual directory path
                folder_name = getattr(self.current_character, 'folder_name', self.current_character.name)
                char_dir = app_data_dir / "characters" / folder_name
                
                # IMPORTANT: Get interactions using CharacterManager
                interactions = self.character_manager.get_interactions(folder_name)
                
                # Clean up temp files before export
                for temp_file in char_dir.glob("temp_bg_*.png"):
                    try:
                        temp_file.unlink()
                    except:
                        pass
                
                with zipfile.ZipFile(export_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in char_dir.rglob('*'):
                        if file_path.is_file():
                            # Handle config.json specially to include ALL current fields
                            if file_path.name == 'config.json' and file_path.parent == char_dir:
                                # This is the main character config, not an interaction config
                                # Read and modify config for export
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    config_data = json.load(f)
                                
                                # Handle API config (clear for compatibility)
                                original_api_config = None
                                if 'api_config_name' in config_data:
                                    original_api_config = config_data['api_config_name']
                                    config_data['api_config_name'] = None
                                
                                # Ensure ALL current character fields are included
                                char = self.current_character
                                
                                # Core fields
                                config_data['folder_name'] = getattr(char, 'folder_name', char.name)
                                config_data['display_name'] = getattr(char, 'display_name', char.name)
                                config_data['base_image'] = getattr(char, 'base_image', '')
                                config_data['personality'] = getattr(char, 'personality', '')
                                
                                # Bubble colors and transparency
                                config_data['bubble_color'] = getattr(char, 'bubble_color', '#E3F2FD')
                                config_data['user_bubble_color'] = getattr(char, 'user_bubble_color', '#F0F0F0')
                                config_data['bubble_transparency'] = getattr(char, 'bubble_transparency', 0)
                                config_data['user_bubble_transparency'] = getattr(char, 'user_bubble_transparency', 0)
                                
                                # Typography
                                config_data['text_font'] = getattr(char, 'text_font', 'Arial')
                                config_data['text_size'] = getattr(char, 'text_size', 11)

                                
                                # Text colors - ALL of them
                                config_data['text_color'] = getattr(char, 'text_color', '#1976D2')
                                config_data['user_text_color'] = getattr(char, 'user_text_color', '#333333')
                                config_data['quote_color'] = getattr(char, 'quote_color', '#666666')
                                config_data['emphasis_color'] = getattr(char, 'emphasis_color', '#0D47A1')
                                config_data['strikethrough_color'] = getattr(char, 'strikethrough_color', '#757575')
                                config_data['code_bg_color'] = getattr(char, 'code_bg_color', 'rgba(0,0,0,0.1)')
                                config_data['code_text_color'] = getattr(char, 'code_text_color', '#D32F2F')
                                config_data['link_color'] = getattr(char, 'link_color', '#1976D2')
                                
                                # Character-specific colors
                                config_data['use_character_colors'] = getattr(char, 'use_character_colors', False)
                                config_data['character_primary_color'] = getattr(char, 'character_primary_color', '')
                                config_data['character_secondary_color'] = getattr(char, 'character_secondary_color', '')
                                
                                # External APIs - handle both dict and object formats
                                if hasattr(char, 'external_apis') and char.external_apis:
                                    exported_apis = []
                                    for api in char.external_apis:
                                        if hasattr(api, '__dict__'):
                                            # It's an object, convert to dict
                                            api_dict = {
                                                'name': getattr(api, 'name', ''),
                                                'url': getattr(api, 'url', ''),
                                                'method': getattr(api, 'method', 'GET'),
                                                'headers': getattr(api, 'headers', {}),
                                                'params': getattr(api, 'params', {}),
                                                'enabled': getattr(api, 'enabled', True),
                                                'description': getattr(api, 'description', ''),
                                                'timeout': getattr(api, 'timeout', 10),
                                            }
                                        else:
                                            # Already a dict
                                            api_dict = dict(api)
                                        exported_apis.append(api_dict)
                                    config_data['external_apis'] = exported_apis
                                else:
                                    config_data['external_apis'] = []
                                
                                # Handle character colors (preserve them)
                                has_character_colors = (
                                    config_data.get('use_character_colors', False) and
                                    config_data.get('character_primary_color', '') and
                                    config_data.get('character_secondary_color', '')
                                )
                                
                                # Add export metadata for import processing
                                config_data['_export_info'] = {
                                    'exported_by': 'Character Chat System',
                                    'export_date': datetime.now().isoformat(),
                                    'original_api_config': original_api_config,
                                    'has_character_colors': has_character_colors,
                                    'character_colors_info': {
                                        'primary': config_data.get('character_primary_color', ''),
                                        'secondary': config_data.get('character_secondary_color', ''),
                                        'enabled': config_data.get('use_character_colors', False)
                                    } if has_character_colors else None,
                                    'export_version': '1.1',  # Updated version
                                    'has_interactions': len(interactions) > 0,  # NEW: Track interactions
                                    'interactions_count': len(interactions),     # NEW: Count interactions
                                    'notes': [
                                        'API config cleared for compatibility',
                                        'All character features preserved',
                                        'Character colors preserved' if has_character_colors else 'No character colors',
                                        f'External APIs: {len(config_data.get("external_apis", []))} included',
                                        f'Interactions: {len(interactions)} included',  # NEW
                                        'Typography settings preserved',
                                        'Transparency settings preserved'
                                    ]
                                }
                                
                                # Write modified config to zip
                                arcname = file_path.relative_to(char_dir)
                                zipf.writestr(str(arcname), json.dumps(config_data, indent=2))
                            else:
                                # Regular file (including interaction files) - copy as-is
                                arcname = file_path.relative_to(char_dir)
                                zipf.write(file_path, arcname)
                
                # Enhanced success message with interactions info
                success_msg = f"Character '{display_name}' exported successfully!"
                
                # Add API config info
                if hasattr(self.current_character, 'api_config_name') and self.current_character.api_config_name:
                    success_msg += f"\n\n📡 API Configuration: Cleared for compatibility"
                
                # Add character colors info
                if (hasattr(self.current_character, 'use_character_colors') and 
                    self.current_character.use_character_colors and
                    self.current_character.character_primary_color and
                    self.current_character.character_secondary_color):
                    success_msg += f"\n\n🎨 Character Colors: Included in export"
                    success_msg += f"\n   Primary: {self.current_character.character_primary_color}"
                    success_msg += f"\n   Secondary: {self.current_character.character_secondary_color}"
                else:
                    success_msg += f"\n\n🎨 Character Colors: Using global colors"
                
                # Add external APIs info
                if hasattr(self.current_character, 'external_apis') and self.current_character.external_apis:
                    api_count = len(self.current_character.external_apis)
                    success_msg += f"\n\n🔗 External APIs: {api_count} included"
                
                # Add interactions info - NEW
                if interactions:
                    success_msg += f"\n\n⚡ Interactions: {len(interactions)} included"
                    for interaction in interactions[:3]:  # Show first 3
                        success_msg += f"\n   • {interaction.name}"
                    if len(interactions) > 3:
                        success_msg += f"\n   ... and {len(interactions) - 3} more"
                else:
                    success_msg += f"\n\n⚡ Interactions: None"
                
                # Add typography info
                success_msg += f"\n\n📝 Typography: All settings preserved"
                success_msg += f"\n💫 Transparency: Bubble settings preserved"
                
                success_msg += f"\n\n💾 Exported to: {export_path}"
                
                QMessageBox.information(self, "Export Successful", success_msg)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")






    def _open_external_apis(self):
        """Open external APIs manager"""
        if not self.current_character:
            QMessageBox.warning(self, "No Character", "Please load a character first.")
            return
        
        dialog = ExternalAPIManager(self, self.current_character)
        if dialog.exec():
            # Reload character to get updated APIs
            updated_character = self.character_manager.load_character(self.current_character.folder_name)
            if updated_character:
                self.current_character = updated_character
                print(f"✅ Updated character with external APIs")
    # REPLACE the existing _import_character method in MainApplication class (around line 3720)

    def _import_character(self):
        """Enhanced import character with all features including interactions"""
        import_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Character Package",
            "",
            "ZIP files (*.zip)"
        )
        
        if import_path:
            try:
                import zipfile
                
                # Create dialog to get names and color preferences
                dialog = CharacterImportDialog(self, import_path)
                if not dialog.exec():
                    return
                
                folder_name = dialog.folder_name
                display_name = dialog.display_name
                color_choice = dialog.color_choice
                
                app_data_dir = get_app_data_dir()
                char_dir = app_data_dir / "characters" / folder_name
                
                if char_dir.exists():
                    QMessageBox.critical(self, "Error", "Character folder name already exists!")
                    return
                
                # Extract zip - this will include the interactions directory automatically
                with zipfile.ZipFile(import_path, 'r') as zipf:
                    zipf.extractall(char_dir)
                
                # Process and fix the config after extraction
                config_file = char_dir / "config.json"
                if config_file.exists():
                    with open(config_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Store original export info
                    export_info = data.get('_export_info', {})
                    has_character_colors = export_info.get('has_character_colors', False)
                    original_colors = export_info.get('character_colors_info', {})
                    has_interactions = export_info.get('has_interactions', False)
                    interactions_count = export_info.get('interactions_count', 0)
                    
                    # Update to new naming system
                    data['folder_name'] = folder_name
                    data['display_name'] = display_name
                    
                    # Remove old 'name' field if it exists
                    if 'name' in data:
                        del data['name']
                    
                    # Handle API config (always clear for safety)
                    original_api_config = export_info.get('original_api_config')
                    data['api_config_name'] = None
                    
                    # Handle character colors based on user choice
                    if color_choice == "preserve" and has_character_colors:
                        # Preserve original character colors
                        data['use_character_colors'] = True
                        data['character_primary_color'] = original_colors.get('primary', '')
                        data['character_secondary_color'] = original_colors.get('secondary', '')
                        print(f"✅ Preserved character colors: {original_colors.get('primary')} / {original_colors.get('secondary')}")
                    elif color_choice == "global" or not has_character_colors:
                        # Use global colors
                        data['use_character_colors'] = False
                        data['character_primary_color'] = ''
                        data['character_secondary_color'] = ''
                        print(f"✅ Set to use global colors")
                    
                    # Add any missing fields with current defaults
                    missing_fields = {
                        'bubble_transparency': 0,
                        'user_bubble_transparency': 0,
                        'text_font': 'Arial',
                        'text_size': 11,
                        'text_color': '#1976D2',
                        'user_text_color': '#333333',
                        'quote_color': '#666666',
                        'emphasis_color': '#0D47A1',
                        'strikethrough_color': '#757575',
                        'code_bg_color': 'rgba(0,0,0,0.1)',
                        'code_text_color': '#D32F2F',
                        'link_color': '#1976D2',
                        'bubble_color': '#E3F2FD',
                        'user_bubble_color': '#F0F0F0',
                        'external_apis': [],
                    }
                    
                    # Add missing fields
                    for field, default_value in missing_fields.items():
                        if field not in data:
                            data[field] = default_value
                            print(f"✅ Added missing field: {field}")
                    
                    # Handle external APIs - ensure proper format
                    if 'external_apis' in data and data['external_apis']:
                        # Make sure all APIs have all required fields
                        fixed_apis = []
                        for api in data['external_apis']:
                            if isinstance(api, dict):
                                # Ensure all fields exist
                                fixed_api = {
                                    'name': api.get('name', ''),
                                    'url': api.get('url', ''),
                                    'method': api.get('method', 'GET'),
                                    'headers': api.get('headers', {}),
                                    'params': api.get('params', {}),
                                    'enabled': api.get('enabled', True),
                                    'description': api.get('description', ''),
                                    'timeout': api.get('timeout', 10),
                                }
                                fixed_apis.append(fixed_api)
                        data['external_apis'] = fixed_apis
                        print(f"✅ Fixed {len(fixed_apis)} external APIs")
                    
                    # Clean up export metadata
                    if '_export_info' in data:
                        del data['_export_info']
                    
                    # Save the cleaned config
                    with open(config_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=2)
                    
                    # NEW: Verify interactions were imported correctly
                    interactions_dir = char_dir / "interactions"
                    imported_interactions = []
                    if interactions_dir.exists():
                        for interaction_folder in interactions_dir.iterdir():
                            if interaction_folder.is_dir():
                                interaction_config = interaction_folder / "config.json"
                                if interaction_config.exists():
                                    try:
                                        with open(interaction_config, 'r', encoding='utf-8') as f:
                                            interaction_data = json.load(f)
                                            imported_interactions.append(interaction_data.get('name', interaction_folder.name))
                                    except:
                                        imported_interactions.append(interaction_folder.name)
                    
                    # Enhanced success message
                    success_msg = f"Character '{display_name}' imported successfully!"
                    
                    # API config info
                    if original_api_config:
                        success_msg += f"\n\n📡 API: Original config '{original_api_config}' was cleared"
                        success_msg += f"\n   You can set a new API config in the API menu"
                    
                    # Character colors info
                    if color_choice == "preserve" and has_character_colors:
                        success_msg += f"\n\n🎨 Colors: Character colors preserved"
                        success_msg += f"\n   Primary: {original_colors.get('primary', 'Unknown')}"
                        success_msg += f"\n   Secondary: {original_colors.get('secondary', 'Unknown')}"
                    elif has_character_colors:
                        success_msg += f"\n\n🎨 Colors: Using your global colors instead"
                        success_msg += f"\n   Original colors were discarded by your choice"
                    else:
                        success_msg += f"\n\n🎨 Colors: Using your global colors"
                        success_msg += f"\n   Character had no custom colors"
                    
                    # External APIs info
                    if 'external_apis' in data and data['external_apis']:
                        api_count = len(data['external_apis'])
                        success_msg += f"\n\n🔗 External APIs: {api_count} imported and configured"
                    else:
                        success_msg += f"\n\n🔗 External APIs: None found"
                    
                    # NEW: Interactions info
                    if imported_interactions:
                        success_msg += f"\n\n⚡ Interactions: {len(imported_interactions)} imported"
                        for interaction_name in imported_interactions[:3]:  # Show first 3
                            success_msg += f"\n   • {interaction_name}"
                        if len(imported_interactions) > 3:
                            success_msg += f"\n   ... and {len(imported_interactions) - 3} more"
                    elif has_interactions:
                        success_msg += f"\n\n⚡ Interactions: Expected {interactions_count} but found 0"
                        success_msg += f"\n   ⚠️ Interactions may not have imported correctly"
                    else:
                        success_msg += f"\n\n⚡ Interactions: None found in package"
                    
                    success_msg += f"\n\n📝 All typography and visual settings preserved"
                    
                    QMessageBox.information(self, "Import Successful", success_msg)
                
                self._update_characters_menu()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Import failed: {str(e)}")










    def _edit_character_names(self):
        """Edit current character's names with enhanced error handling"""
        if not self.current_character:
            return
        
        dialog = CharacterNameEditDialog(self, self.current_character)
        if dialog.exec() and dialog.result:
            result = dialog.result
            
            # Show warning if folder name is changing
            if result["folder_changed"]:
                reply = QMessageBox.question(
                    self, 
                    "Confirm Folder Rename",
                    "Changing the folder name will move all character files.\n"
                    "A backup will be created for safety.\n"
                    "This may take a moment. Continue?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Show progress dialog for folder operations
            if result["folder_changed"]:
                progress = QProgressDialog("Renaming character folder safely...", "Cancel", 0, 0, self)
                progress.setWindowModality(Qt.WindowModal)
                progress.show()
                QApplication.processEvents()
            
            # SAFE: Close any open chat window for this character BEFORE renaming
            old_name = self.current_character.folder_name
            if old_name in self.chat_windows:
                try:
                    chat_window = self.chat_windows[old_name]
                    chat_window.close()
                    print(f"🔒 Closed chat window for {old_name}")
                except (RuntimeError, AttributeError) as e:
                    print(f"⚠️ Chat window already closed: {e}")
                
                # SAFE: Remove from tracking if it still exists
                if old_name in self.chat_windows:
                    del self.chat_windows[old_name]
                    print(f"🗑️ Removed {old_name} from chat_windows tracking")
            
            # Perform the rename
            success = self.character_manager.rename_character(
                self.current_character.folder_name,
                result["folder_name"],
                result["display_name"]
            )
            
            if result["folder_changed"]:
                progress.close()
            
            if success:
                # Reload the character with new name
                self._load_character(result["folder_name"])
                self._update_characters_menu()
                
                QMessageBox.information(self, "Success", 
                    f"✅ Character successfully renamed!\n"
                    f"📁 Folder: {result['folder_name']}\n"
                    f"📝 Display: {result['display_name']}")
            else:
                QMessageBox.critical(self, "Error", 
                    "❌ Failed to rename character.\n"
                    "All original files have been preserved.\n"
                    "Check the console for details.")


    # 2. In MainApplication class (around line 3500):
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging"""
        if event.button() == Qt.LeftButton:
            # Check if click is on title bar
            if event.position().y() <= 30:
                self.drag_position = event.globalPosition().toPoint() - self.pos()
        
        # Check if click is on character
        if self.current_character and not self.editor_mode:
            view_pos = self.character_view.mapFromGlobal(event.globalPosition().toPoint())
            scene_pos = self.character_view.mapToScene(view_pos)
            
            # Check interaction icons first
            for icon in self.interaction_icons:
                if icon.geometry().contains(view_pos):
                    return
            
            # Check if click is within character bounds
            if self.scene.sceneRect().contains(scene_pos):
                self._open_or_focus_chat()
    
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.drag_position = None
        self._save_state()
    
    def _toggle_menu_bar(self):
        """Toggle menu bar visibility"""
        if self.menu_visible:
            self.menu_frame.hide()
            self.menu_visible = False
        else:
            self.menu_frame.show()
            self.menu_visible = True
        
        # Update window size
        if self.current_character:
            self._update_window_size()
        
        # Save the state immediately when toggled
        self._save_state()

    def _toggle_always_on_top(self):
        """Toggle always on top state for the main window"""
        try:
            self.always_on_top = not self.always_on_top
            
            if self.always_on_top:
                # Set window to stay on top
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            else:
                # Remove stay on top flag
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            
            # Always show after changing flags
            self.show()
            
            # Save state (MainApplication uses _save_state, not _save_window_state)
            self._save_state()
            
            # Update colors (MainApplication doesn't have _update_pin_button_appearance)
            self.update_colors()
            
        except Exception as e:
            print(f"Error toggling always on top: {e}")
            # Revert state on error
            self.always_on_top = not self.always_on_top



    def _keep_window_on_top(self):
        """Keep main application window on top by raising it when needed"""
        if (self.always_on_top and 
            self.isVisible() and 
            not self.isMinimized() and 
            QApplication.activeWindow() != self):
            
            self.raise_()

    def _minimize_window(self):
        """Minimize the main application window"""
        self.showMinimized()
    
    
    def _reset_window(self):
        """Reset window to default position and size"""
        self.move(100, 100)
        self.resize(400, 400)
        self._save_state()
    
    def _open_color_editor(self):
        """Open enhanced color editor dialog"""
        dialog = EnhancedColorDialog(self)
        dialog.exec()
    
    def _refresh_all_colors(self):
        """Refresh all colors in the application"""
        self.update_colors()
    
    def _update_characters_menu(self):
        """Update the characters menu with display names"""
        self.characters_menu.clear()
        
        characters = self.character_manager.get_characters()
        if not characters:
            self.characters_menu.addAction("(No characters)").setEnabled(False)
        else:
            for folder_name in characters:
                # Load character to get display name
                character = self.character_manager.load_character(folder_name)
                if character:
                    display_name = getattr(character, 'display_name', character.name)
                    menu_text = f"{display_name}"
                    if display_name != folder_name:
                        menu_text += f" ({folder_name})"
                    
                    self.characters_menu.addAction(menu_text, lambda c=folder_name: self._load_character(c))
                else:
                    # Fallback if character can't be loaded
                    self.characters_menu.addAction(folder_name, lambda c=folder_name: self._load_character(c))
    
    def _new_character(self):
        """Create a new character"""
        dialog = CharacterCreationDialog(self)
        if dialog.exec():
            success = self.character_manager.create_character(
                dialog.result["folder_name"],
                dialog.result["display_name"],
                dialog.result["image_path"],
                dialog.result["personality"]
            )
            
            if success:
                self._update_characters_menu()
                self._load_character(dialog.result["folder_name"])  # Use folder_name for loading
                QMessageBox.information(self, "Success", f"Character '{dialog.result['display_name']}' created successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to create character. Folder name may already exist.")
    

    def _apply_character_colors(self):
        """Apply character-specific colors if enabled - FIXED to not overwrite global colors"""
        if (self.current_character and 
            hasattr(self.current_character, 'use_character_colors') and 
            self.current_character.use_character_colors):
            
            # Character colors are enabled - but DON'T overwrite global colors
            # The update_colors() method will read character colors when needed
            print(f"✅ Character colors enabled for {self.current_character.display_name}")
            
        else:
            # Character colors disabled - use global colors
            print("ℹ️ Using global colors")
        
        # Trigger UI update without changing global color storage
        self.update_colors()

    def _open_character_colors(self):
        """Open character color customization dialog"""
        if not self.current_character:
            QMessageBox.warning(self, "No Character", "Please load a character first.")
            return
        
        dialog = CharacterColorDialog(self, self.current_character)
        dialog.exec()


    def _load_character(self, name: str):
        """Load and display a character - OPTIMIZED"""
        character = self.character_manager.load_character(name)
        if not character:
            QMessageBox.critical(self, "Error", f"Failed to load character '{name}'")
            return
        
        # Temporarily disconnect color signals to prevent spam
        if hasattr(self, 'current_character') and self.current_character:
            try:
                app_colors.colors_changed.disconnect(self.update_colors)
            except:
                pass
        
        self.current_character = character
        
        # Clear existing interactions
        self._clear_interactions()
        
        # Load animation
        width, height = self.animator.load_animation(character.base_image)
        
        # Store dimensions
        self.current_image_width = width
        self.current_image_height = height
        
        # Update window size
        self._update_window_size()
        
        # Start animation
        self.animator.start_animation()
        
        # Load interactions
        self._load_interactions()
        
        # Apply character colors once
        self._apply_character_colors()
        
        # Reconnect color signal
        app_colors.colors_changed.connect(self.update_colors)
        
        # Enable menu items
        self.add_interaction_action.setEnabled(True)
        self.edit_image_action.setEnabled(True)
        self.edit_personality_action.setEnabled(True)
        self.edit_names_action.setEnabled(True)
        self.character_colors_action.setEnabled(True)
        self.editor_mode_action.setEnabled(True)
        self.delete_character_action.setEnabled(True)
        self.export_character_action.setEnabled(True)
        self.external_apis_action.setEnabled(True)
        
        self._save_state()
        
        # Single update call at the end
        QTimer.singleShot(50, self.update_colors)
        
        print(f"🔧 Loaded character '{character.display_name}'")


    def _update_colors_for_character_only(self):
        """Update colors for character preview without affecting global colors - NEW METHOD"""
        # This method updates UI without touching global app_colors
        try:
            # Determine colors to use for UI update
            if (self.current_character and 
                getattr(self.current_character, 'use_character_colors', False)):
                primary = getattr(self.current_character, 'character_primary_color', app_colors.PRIMARY)
                secondary = getattr(self.current_character, 'character_secondary_color', app_colors.SECONDARY)
            else:
                primary = app_colors.PRIMARY
                secondary = app_colors.SECONDARY
            
            # Update UI elements directly with these colors
            self._apply_colors_to_ui(primary, secondary)
            
        except Exception as e:
            print(f"Error in isolated character color update: {e}")

    def _apply_colors_to_ui(self, primary, secondary):
        """Apply colors directly to UI elements without changing global storage - NEW METHOD"""
        try:
            # Update title bar
            if hasattr(self, 'title_bar') and self.title_bar:
                self.title_bar.setStyleSheet(f"background-color: {primary};")
            
            # Update character view only in editor mode
            if hasattr(self, 'character_view') and self.character_view:
                if hasattr(self, 'editor_mode') and self.editor_mode:
                    self.character_view.setStyleSheet("background-color: #FFE0E0; border: none;")
                # Don't change character view background for normal mode
            
            # Update control buttons
            self._update_all_control_buttons_with_colors(primary, secondary)
            
            # Update chat windows
            if hasattr(self, 'chat_windows'):
                for name, window in list(self.chat_windows.items()):
                    try:
                        if window and hasattr(window, 'update_colors'):
                            window.update_colors()
                    except (RuntimeError, AttributeError):
                        if name in self.chat_windows:
                            del self.chat_windows[name]
            
        except Exception as e:
            print(f"Error applying colors to UI: {e}")






    def _update_window_size(self):
        """Update window size based on image and menu visibility"""
        title_height = 30
        menu_height = 25 if self.menu_visible else 0
        
        window_width = self.current_image_width
        window_height = self.current_image_height + title_height + menu_height
        
        self.setFixedSize(window_width, window_height)
        
        # Update scene size
        self.scene.setSceneRect(0, 0, self.current_image_width, self.current_image_height)
        self.character_view.setFixedSize(self.current_image_width, self.current_image_height)
    
    def _clear_interactions(self):
        """Clear all interaction icons"""
        for icon in self.interaction_icons:
            icon.deleteLater()
        self.interaction_icons.clear()
    
    def _load_interactions(self):
        """Load and display character interactions"""
        if not self.current_character:
            return
            
        interactions = self.character_manager.get_interactions(self.current_character.name)
        
        for interaction in interactions:
            self._create_interaction_icon(interaction)
    
    def _create_interaction_icon(self, interaction: Interaction):
        """Create an interaction icon"""
        icon = InteractionIcon(self.character_view, interaction, self.editor_mode)
        icon.clicked.connect(lambda i: self._run_interaction(i))
        icon.position_updated.connect(self._handle_interaction_position_update)
        icon.context_menu_requested.connect(self._handle_interaction_context_menu)
        self.interaction_icons.append(icon)
        icon.show()
    
    def _handle_interaction_position_update(self, interaction: Interaction, event_type: str):
        """Handle interaction position update"""
        self.character_manager.save_interaction(self.current_character.name, interaction)
    
    def _handle_interaction_context_menu(self, interaction: Interaction, event_type: str):
        """Handle interaction context menu events"""
        if event_type == "edit":
            self._edit_interaction(interaction)
        elif event_type == "delete":
            self._delete_interaction(interaction)
    
    def _force_cleanup_interaction(self):
        """Force cleanup of any existing interaction state"""
        try:
            print("Forcing interaction cleanup")
            
            # Stop and cleanup any existing timer
            if self.current_interaction_timer:
                self.current_interaction_timer.stop()
                self.current_interaction_timer.deleteLater()
                self.current_interaction_timer = None
            
            # Reset flags
            self.interaction_in_progress = False
            
            # Stop current animation
            self.animator.stop_animation()
            
            print("Interaction cleanup completed")
            
        except Exception as e:
            print(f"Error during force cleanup: {e}")


    def _send_interaction_to_chat_if_open(self, interaction: Interaction):
        """Send interaction to chat if window is open (AI-aware)"""
        if not self.current_character:
            return

        char_name = self.current_character.name
        if char_name in self.chat_windows:
            try:
                chat_window = self.chat_windows[char_name]

                # Block if AI is writing (works for both streaming and non-streaming)
                if getattr(chat_window, 'is_ai_writing', False):
                    print("❌ BLOCKED INTERACTION - AI is writing!")
                    return

                # Check if window is accessible (visible or minimized UI showing)
                if chat_window.isVisible() or (
                    hasattr(chat_window, 'minimize_bar') and
                    chat_window.minimize_bar and
                    chat_window.minimize_bar.isVisible()
                ):
                    self._send_interaction_to_chat(chat_window, interaction)

            except (RuntimeError, AttributeError) as e:
                print(f"Chat window no longer valid: {e}")
                del self.chat_windows[char_name]



    def _restore_original_animation(self):
        """Restore original character animation seamlessly"""
        try:
            # Clean up timer
            if self.current_interaction_timer:
                self.current_interaction_timer.stop()
                self.current_interaction_timer.deleteLater()
                self.current_interaction_timer = None
            
            # Reset state
            self.interaction_in_progress = False
            
            # Seamlessly restore original animation
            if self._original_image_path and os.path.exists(self._original_image_path):
                self.animator.seamless_load_animation(self._original_image_path)
                
        except Exception as e:
            print(f"Error restoring original animation: {e}")
            self.interaction_in_progress = False


    def _add_interaction(self):
        """Add a new interaction"""
        if not self.current_character:
            return
            
        dialog = InteractionEditDialog(self)
        if dialog.exec():
            if self.character_manager.save_interaction(self.current_character.name, dialog.result):
                self._load_character(self.current_character.name)
                QMessageBox.information(self, "Success", "Interaction added successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to add interaction.")
    
    def _edit_interaction(self, interaction: Interaction):
        """Edit an existing interaction with proper cache clearing"""
        # Store original data for cache clearing
        original_name = interaction.name
        original_base_image = interaction.base_image_path
        
        dialog = InteractionEditDialog(self, interaction)
        if dialog.exec() and dialog.result:
            try:
                # Clear animation cache BEFORE saving
                print("🧹 Clearing animation cache before saving interaction...")
                
                # Clear cache for the old interaction
                self.animator.clear_interaction_cache(self.current_character.name, original_name)
                
                # Also clear any cache for the specific image path
                if original_base_image and os.path.exists(original_base_image):
                    self.animator.clear_animation_cache(original_base_image)
                
                # Clear Qt's pixmap cache too
                QPixmapCache.clear()
                
                # If name changed, handle the transition carefully
                if original_name != dialog.result.name:
                    print(f"Interaction name changed from '{original_name}' to '{dialog.result.name}'")
                    
                    # Save the new interaction first
                    if self.character_manager.save_interaction(self.current_character.name, dialog.result):
                        # Delete the old interaction after successful save
                        self.character_manager.delete_interaction(self.current_character.name, original_name)
                        print(f"Cleaned up old interaction folder: {original_name}")
                    else:
                        QMessageBox.critical(self, "Error", "Failed to save updated interaction.")
                        return
                else:
                    # Name didn't change, just update in place
                    if not self.character_manager.save_interaction(self.current_character.name, dialog.result):
                        QMessageBox.critical(self, "Error", "Failed to update interaction.")
                        return
                
                # IMPORTANT: Clear cache for the NEW interaction too
                print("🧹 Clearing cache for new interaction data...")
                self.animator.clear_interaction_cache(self.current_character.name, dialog.result.name)
                
                # Force refresh the interaction if it's currently displayed
                if hasattr(self, '_original_image_path') and self._original_image_path:
                    try:
                        # Get the updated interaction
                        updated_interactions = self.character_manager.get_interactions(self.current_character.name)
                        updated_interaction = next((i for i in updated_interactions if i.name == dialog.result.name), None)
                        
                        if updated_interaction and updated_interaction.base_image_path:
                            # If this interaction's base image is currently showing, force reload
                            if (hasattr(self, 'current_interaction_timer') and 
                                self.current_interaction_timer and 
                                self.current_interaction_timer.isActive()):
                                print("🔄 Interaction currently active - forcing reload of new image")
                                self.animator.force_reload_animation(updated_interaction.base_image_path)
                                
                    except Exception as e:
                        print(f"⚠️ Could not force reload current interaction: {e}")
                
                # Use the new refresh method instead of full reload
                self.refresh_interaction_animations(dialog.result.name)
                QMessageBox.information(self, "Success", "Interaction updated successfully! No restart needed.")
                
            except Exception as e:
                print(f"Error during interaction edit: {e}")
                QMessageBox.critical(self, "Error", f"Failed to update interaction: {str(e)}")


    def _delete_interaction(self, interaction: Interaction):
        """Delete an interaction"""
        reply = QMessageBox.question(self, "Delete Interaction", 
                                   f"Are you sure you want to delete '{interaction.name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.character_manager.delete_interaction(self.current_character.name, interaction.name):
                self._load_character(self.current_character.name)
                QMessageBox.information(self, "Success", "Interaction deleted successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete interaction.")
    
    def _toggle_editor_mode(self):
        """Toggle editor mode for positioning interactions"""
        self.editor_mode = not self.editor_mode
        self.editor_mode_action.setChecked(self.editor_mode)

        if self.editor_mode:
            self.character_view.setStyleSheet("background-color: #FFE0E0; border: none;")
            QMessageBox.information(self, "Editor Mode", 
                                  "Editor mode enabled. You can now drag interaction icons to reposition them.")
        else:
            self.character_view.setStyleSheet(f"background-color: {app_colors.SECONDARY}; border: none;")
            QMessageBox.information(self, "Editor Mode", 
                                  "Editor mode disabled. Click interactions to activate them.")
        
        # Reload interactions with new mode
        self._clear_interactions()
        self._load_interactions()
    





    def _edit_character_image(self):
        """Edit current character's image with ISOLATED refresh (no chat window interference)"""
        if not self.current_character:
            return
            
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select New Character Image",
            "",
            "Image files (*.gif *.png *.jpg *.jpeg);;All files (*.*)"
        )
        
        if filename:
            print(f"🖼️ Updating character image to: {filename}")
            
            # Use the SAFE update method
            if self.character_manager.update_character_image(self.current_character.name, filename):
                
                # ISOLATED REFRESH: Only update the character display, NOT chat windows
                self.refresh_character_display()
                
                QMessageBox.information(self, "Success", 
                    "Character image updated successfully!\n"
                    "Chat windows and interactions remain unaffected.")
            else:
                QMessageBox.critical(self, "Error", 
                    "Failed to update character image.\n"
                    "All original files have been preserved.")







    def _edit_personality(self):
        """Edit current character's personality"""
        if not self.current_character:
            return
            
        # Create edit dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit Personality")
        dialog.setFixedSize(500, 450)
        dialog.setModal(True)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Text editor
        text_edit = QTextEdit()
        text_edit.setPlainText(self.current_character.personality)
        layout.addWidget(text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(lambda: self._save_personality(dialog, text_edit.toPlainText()))
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def _save_personality(self, dialog, new_personality):
        """Save updated personality"""
        new_personality = new_personality.strip()
        if new_personality:
            self.current_character.personality = new_personality
            
            # Save to file
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / getattr(self.current_character, 'folder_name', self.current_character.name)
            with open(char_dir / "personality.txt", 'w', encoding='utf-8') as f:
                f.write(new_personality)
            
            # Update config
            with open(char_dir / "config.json", 'w', encoding='utf-8') as f:
                json.dump(asdict(self.current_character), f, indent=2)
            
            QMessageBox.information(self, "Success", "Personality updated successfully!")
            dialog.accept()
        
    def _delete_character(self):
        """Delete current character"""
        if not self.current_character:
            return
            
        reply = QMessageBox.question(self, "Delete Character", 
                                f"Are you sure you want to delete '{self.current_character.name}'?",
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Close chat window if open
            char_name = self.current_character.name  # Store the name first
            if char_name in self.chat_windows:
                try:
                    self.chat_windows[char_name].close()
                    del self.chat_windows[char_name]
                    print(f"Closed and removed chat window for {char_name}")
                except (KeyError, RuntimeError):
                    # Window might already be closed/removed
                    print(f"Chat window for {char_name} was already removed")
            
            # Clean up any temp files for this character
            try:
                app_data_dir = get_app_data_dir()
                char_dir = app_data_dir / "characters" / char_name
                for temp_file in char_dir.glob("temp_bg_*.png"):
                    temp_file.unlink()
                
                # Clean up profile selection file
                profile_file = char_dir / "selected_profile.json"
                if profile_file.exists():
                    profile_file.unlink()
                    
            except Exception as e:
                print(f"Error during cleanup: {e}")
            
            # Delete character
            if self.character_manager.delete_character(char_name):
                self.animator.stop_animation()
                self.scene.clear()
                self._clear_interactions()
                self.current_character = None
                
                # Disable menu items
                self.add_interaction_action.setEnabled(False)
                self.edit_image_action.setEnabled(False)
                self.edit_personality_action.setEnabled(False)
                self.edit_names_action.setEnabled(False)
                self.editor_mode_action.setEnabled(False)
                self.delete_character_action.setEnabled(False)
                self.export_character_action.setEnabled(False) 
                
                self._update_characters_menu()
                self._save_state()
                
                # Reset to default size
                self.current_image_width = 400
                self.current_image_height = 400
                self._update_window_size()
                
                QMessageBox.information(self, "Success", "Character deleted successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to delete character.")
    
    def _open_or_focus_chat(self):
        """Open or focus chat window for current character"""
        if not self.current_character:
            return
            
        char_name = self.current_character.name
        
        # Check if window exists and is still valid
        if char_name in self.chat_windows:
            chat_window = self.chat_windows[char_name]
            
            # Check if window still exists and is valid
            try:
                # Test if the window object still exists
                if chat_window.isVisible():
                    # Window is visible, bring to front
                    chat_window.raise_()
                    chat_window.activateWindow()
                    return
                elif hasattr(chat_window, 'minimize_bar') and chat_window.minimize_bar and chat_window.minimize_bar.isVisible():
                    # Window is minimized, restore it
                    chat_window._restore_window()
                    return
                else:
                    # Window exists but is hidden, show it
                    chat_window.show()
                    chat_window.raise_()
                    chat_window.activateWindow()
                    return
            except (RuntimeError, AttributeError):
                # Window was destroyed, remove from tracking
                print(f"Removing invalid chat window for {char_name}")
                del self.chat_windows[char_name]
        
        # Create new window
        self._create_new_chat_window(None)


    def _create_new_chat_window(self, scheduled_reminder=None):
        """Create a new chat window with correct colors from start - NO FLICKER"""
        if not self.current_character:
            return
            
        char_name = self.current_character.name
        print(f"Creating new chat window for {char_name}")
        
        # Remove any existing reference
        if char_name in self.chat_windows:
            print(f"Removing existing window reference for {char_name}")
            del self.chat_windows[char_name]
        
        # 🔧 LOAD FRESH CHARACTER DATA BEFORE CREATING WINDOW
        fresh_character = self.character_manager.load_character(char_name)
        if fresh_character:
            self.current_character = fresh_character
            print(f"🎨 Pre-loaded character colors: use_colors={getattr(fresh_character, 'use_character_colors', False)}")
            
            if (hasattr(fresh_character, 'use_character_colors') and 
                fresh_character.use_character_colors and
                hasattr(fresh_character, 'character_primary_color') and
                hasattr(fresh_character, 'character_secondary_color')):
                print(f"🎨 Character colors: {fresh_character.character_primary_color}, {fresh_character.character_secondary_color}")
            else:
                print(f"🎨 Will use global colors: {app_colors.PRIMARY}, {app_colors.SECONDARY}")
        
        # Create new window with pre-loaded character data
        chat_window = ChatWindow(self, self.current_character, self.ai_interface, scheduled_reminder)
        self.chat_windows[char_name] = chat_window
        
        print(f"Chat window created and tracked for {char_name}")
        chat_window.show()
        return chat_window
    
    def _initialize_character_colors(self):
        """Initialize character colors on window creation - NEW METHOD"""
        try:
            print(f"🎨 Initializing colors for chat window: {self.character.display_name}")
            
            # Check if character has specific colors
            if (hasattr(self.character, 'use_character_colors') and 
                self.character.use_character_colors and
                hasattr(self.character, 'character_primary_color') and
                hasattr(self.character, 'character_secondary_color') and
                self.character.character_primary_color and
                self.character.character_secondary_color):
                
                print(f"🎨 Using character colors: {self.character.character_primary_color}, {self.character.character_secondary_color}")
            else:
                print(f"🎨 Using global colors: {app_colors.PRIMARY}, {app_colors.SECONDARY}")
            
            # Trigger color update to apply the correct colors
            self.update_colors()
            
            # Force a repaint to ensure colors are applied
            self.repaint()
            
        except Exception as e:
            print(f"Error initializing character colors: {e}")




    def _save_state(self):
        """Save application state including menu toggle state"""
        state = {
            "geometry": {
                "x": self.x(),
                "y": self.y(),
                "width": self.width(),
                "height": self.height()
            },
            "always_on_top": self.always_on_top,
            "current_character": self.current_character.name if self.current_character else None,
            "menu_visible": self.menu_visible  # Add this line to save menu state
        }
        
        try:
            app_data_dir = get_app_data_dir()
            state_file = app_data_dir / "app_state.json"
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    def _load_state(self):
        """Load application state including menu toggle state"""
        try:
            app_data_dir = get_app_data_dir()
            state_file = app_data_dir / "app_state.json"
            
            with open(state_file, 'r') as f:
                state = json.load(f)
                
            if "geometry" in state:
                self.move(state["geometry"]["x"], state["geometry"]["y"])
                
            if "always_on_top" in state and state["always_on_top"]:
                self._toggle_always_on_top()
                
            if "current_character" in state and state["current_character"]:
                QTimer.singleShot(100, lambda: self._load_character(state["current_character"]))
                
            # Load menu visibility state
            if "menu_visible" in state:
                self.menu_visible = state["menu_visible"]
                # Apply the menu state after UI is loaded
                QTimer.singleShot(150, self._apply_saved_menu_state)
                
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"Error loading state: {e}")

    def _apply_saved_menu_state(self):
        """Apply the saved menu visibility state"""
        if hasattr(self, 'menu_frame'):  # Your menu widget is called menu_frame
            if self.menu_visible:
                self.menu_frame.show()
            else:
                self.menu_frame.hide()



    def refresh_interaction_animations(self, interaction_name: str = None):
        """Refresh interaction animations after editing - no restart needed"""
        try:
            if not self.current_character:
                return
                
            print(f"🔄 Refreshing interaction animations for character: {self.current_character.name}")
            
            # Clear all caches
            print("🧹 Clearing animation caches...")
            
            # Clear Qt pixmap cache
            QPixmapCache.clear()
            
            # Clear animator cache
            if interaction_name:
                self.animator.clear_interaction_cache(self.current_character.name, interaction_name)
            else:
                self.animator.clear_interaction_cache(self.current_character.name)
            
            # Clear any additional internal caches
            if hasattr(self.animator, 'preloaded_animations'):
                # Clear interaction-related entries from preloaded cache
                paths_to_remove = []
                for path in self.animator.preloaded_animations.keys():
                    if f"/{self.current_character.name}/interactions/" in path:
                        if not interaction_name or f"/{interaction_name}/" in path:
                            paths_to_remove.append(path)
                
                for path in paths_to_remove:
                    del self.animator.preloaded_animations[path]
                    print(f"🧹 Removed from preloaded cache: {path}")
            
            # Force reload current interactions
            print("🔄 Reloading interaction icons...")
            self._clear_interactions()
            self._load_interactions()
            
            # If an interaction is currently running, handle it properly
            if (hasattr(self, 'interaction_in_progress') and self.interaction_in_progress and
                hasattr(self, 'current_interaction_timer') and self.current_interaction_timer and
                self.current_interaction_timer.isActive()):
                
                print("⚠️ Interaction currently running - will refresh after completion")
                # The interaction will naturally return to the original image when timer ends
                # The cache clearing ensures the next interaction run will use fresh data
            
            print("✅ Interaction animations refreshed successfully")
            
        except Exception as e:
            print(f"❌ Error refreshing interaction animations: {e}")

    def force_refresh_all_caches(self):
        """Nuclear option - clear ALL caches and reload everything"""
        try:
            print("🚨 FORCE REFRESH: Clearing all caches and reloading...")
            
            # Clear all Qt caches
            QPixmapCache.clear()
            
            # Clear animator caches
            if hasattr(self.animator, 'preloaded_animations'):
                self.animator.preloaded_animations.clear()
            
            # Stop any current animation
            if hasattr(self.animator, 'stop_animation'):
                self.animator.stop_animation()
            
            # Reload the entire character
            if self.current_character:
                character_name = self.current_character.name
                self._load_character(character_name)
                
            print("✅ Force refresh completed")
            
        except Exception as e:
            print(f"❌ Error in force refresh: {e}")

    def closeEvent(self, event):
        """Handle application closing with proper cleanup"""
        print("Closing main application")
        
        # Force cleanup any running interactions
        self._force_cleanup_interaction()
        
        # Stop animator
        if hasattr(self, 'animator') and self.animator:
            self.animator.stop_animation()
        
        # Close all chat windows
        for window in list(self.chat_windows.values()):
            try:
                window.close()
            except:
                pass
        
        # Save state
        self._save_state()
        
        # Accept the close event
        event.accept()


class ChatWindow(QMainWindow):
    """Chat window with tree-based conversation support"""
    # Define signals for thread-safe communication
    add_bubble_signal = Signal(object)  # Now accepts ChatMessage object
    add_streaming_bubble_signal = Signal()
    update_streaming_bubble_signal = Signal(str)
    finalize_streaming_bubble_signal = Signal()
    save_chat_history_signal = Signal()
    refresh_display_signal = Signal()
    flash_window_signal = Signal()
    window_ready_signal = Signal()
    stop_streaming_signal = Signal()
    ai_start_processing_signal = Signal()
    ai_finish_processing_signal = Signal()

    def __init__(self, parent, character: CharacterConfig, ai_interface, scheduled_reminder=None, is_checkin=False): 

        super().__init__(parent)  # Keep parent for communication
        self.character = character
        self.ai_interface = ai_interface
        self.chat_tree = ChatTree()  # Use tree structure
        self.scheduled_dialogs: List[ScheduledDialog] = []
        self.streaming_enabled = True
        self.streaming_active = False
        self.always_on_top = False
        self._background_applied = False
        self._applying_background = False
        self._current_bg_file = None
        self.streaming_text = ""
        self.streaming_bubble = None
        self.messages_per_page = 25  # Number of messages to load at once
        self.loaded_message_ids = set()  # Track which messages are loaded
        self.oldest_loaded_timestamp = None  # Track oldest loaded message
        self.is_loading_messages = False  # Prevent concurrent loads
        self.loader_widget = None  # Loading indicator widget
        self.cancel_non_streaming = False  # Add this flag

        # Connect scroll event

        
        self.selected_user_profile = None  # Will use global profile if None
        self.current_streaming_parent_id = None
        self.is_ai_writing = False
        self.streaming_stopped = False
        self.current_streaming_content = ""  # For stop functionality
        self.force_stop_streaming = False 
        
        # Connect the stop signal

        self.icon_cache = {}
        self.pending_scheduled_reminder = scheduled_reminder
        self.is_checkin_window = is_checkin  # 🆕 NEW: Track if this is a check-in window

        # Connect signals to slots

        app_colors.colors_changed.connect(self.update_colors)
        self.add_bubble_signal.connect(self._add_bubble)
        self.add_streaming_bubble_signal.connect(self._add_streaming_bubble)
        self.update_streaming_bubble_signal.connect(self._update_streaming_bubble)
        self.finalize_streaming_bubble_signal.connect(self._finalize_streaming_bubble)
        self.add_streaming_bubble_signal.connect(self._on_ai_start_writing)
        self.finalize_streaming_bubble_signal.connect(self._on_ai_finish_writing)
        self.save_chat_history_signal.connect(self._save_chat_history)
        self.refresh_display_signal.connect(self._refresh_display)
        self.flash_window_signal.connect(self.flash_window_for_scheduled_message)
        self.stop_streaming_signal.connect(self._handle_stop_streaming)  # ONLY ONCE
        self.ai_start_processing_signal.connect(self._on_ai_start_writing)
        self.ai_finish_processing_signal.connect(self._on_ai_finish_writing)
        self._load_selected_profile()

        self.transparency_timer = QTimer()
        self.transparency_timer.timeout.connect(self._apply_transparency)
        self.transparency_timer.setSingleShot(True)
        self.is_transparent = False
        self.original_opacity = 1.0


        self.bubble_widgets: Dict[str, ChatBubble] = {}  # message_id -> widget
        self.last_message_count = 0
        self.update_in_progress = False
        
        # PERFORMANCE: Scroll optimization
        self.scroll_timer = QTimer()
        self.scroll_timer.setSingleShot(True)
        self.scroll_timer.timeout.connect(self._apply_scroll_update)
        self.pending_scroll_action = None

        
        # Window setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool)  # ✅ Use Qt.Tool instead
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(350, 600)

        # Set initial position to avoid sticking to top
        self._center_on_screen()
        self._init_checkin_system()

        
        # IMPORTANT: Load chat settings FIRST before accessing them
        self.chat_settings = self._load_chat_settings()
        
        # Fix empty background colors
        if not self.chat_settings.background_color or self.chat_settings.background_color.strip() == "":
            self.chat_settings.background_color = "#F0F4F8"
        
        # NOW load positioned icons (after chat_settings is loaded)
        self.user_icon = self._load_icon(
            self.chat_settings.user_icon_path,
            getattr(self.chat_settings, 'user_icon_scale', 1.0),
            getattr(self.chat_settings, 'user_icon_offset_x', 0),
            getattr(self.chat_settings, 'user_icon_offset_y', 0)
        )
        self.character_icon = self._load_icon(
            self.chat_settings.character_icon_path,
            getattr(self.chat_settings, 'character_icon_scale', 1.0),
            getattr(self.chat_settings, 'character_icon_offset_x', 0),
            getattr(self.chat_settings, 'character_icon_offset_y', 0)
        )

        # Message queue for threading
        self.message_queue = queue.Queue()
        
        self._setup_ui()
        self._apply_chat_background()
        self._load_chat_history()
        self._load_window_state()
        self._apply_window_settings()
        self.chat_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        app_colors.colors_changed.connect(self.update_colors)

        self._load_scheduled_dialogs()
        QTimer.singleShot(1000, self._debug_profile_system)
        QTimer.singleShot(500, self._setup_transparency)
        QTimer.singleShot(200, self._load_window_state)
        # Schedule timer

        print(f"✅ Schedule timer started for {self.character.name}")

        
        # Start message processing thread
        self.processing_thread = threading.Thread(target=self._process_messages, daemon=True)
        self.processing_thread.start()
        
        # ADD THIS LINE:
        self.setup_flash_animation()
        
        
        # For window dragging
        self.drag_position = None
        if scheduled_reminder:
            # Flash immediately for scheduled reminder
            QTimer.singleShot(1, self.flash_window_signal.emit)
            # Start processing the reminder immediately
            QTimer.singleShot(1, lambda: self._send_reminder_as_character(scheduled_reminder))
        
        # 🆕 NEW: Handle check-in auto-send with flash
        if is_checkin:
            # Flash immediately for check-in
            QTimer.singleShot(1, self.flash_window_signal.emit)
            # Send check-in message after short delay
            QTimer.singleShot(500, self._send_auto_checkin)
        self.update_colors()
        
        # Force immediate UI update to prevent any flicker
        self.repaint()

    def _send_auto_checkin(self):
        """Send automatic check-in message when window auto-opens"""
        try:
            if not hasattr(self, 'checkin_settings'):
                self._init_checkin_system()
            
            # Generate check-in prompt
            prompt = self._generate_checkin_prompt()
            
            # Send as character
            self._send_reminder_as_character(prompt, is_checkin=True)
            
            print(f"✅ Sent auto check-in message")
            
        except Exception as e:
            print(f"❌ Error sending auto check-in: {e}")











    def _create_loader_widget(self):
        """Create an animated loading indicator widget"""
        loader = QWidget()
        loader.setFixedHeight(50)
        loader.setObjectName("messageLoader")
        
        layout = QHBoxLayout(loader)
        layout.setAlignment(Qt.AlignCenter)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Create container for dots
        dots_container = QWidget()
        dots_layout = QHBoxLayout(dots_container)
        dots_layout.setSpacing(8)
        
        # Create three animated dots
        self.loader_dots = []
        for i in range(3):
            dot = QLabel("●")
            dot.setObjectName(f"loaderDot{i}")
            dot.setStyleSheet(f"""
                QLabel {{
                    color: {app_colors.PRIMARY};
                    font-size: 9pt;
                    padding: 0px;
                }}
            """)
            dots_layout.addWidget(dot)
            self.loader_dots.append(dot)
        
        # Loading text
        loading_label = QLabel("Loading older messages")
        loading_label.setStyleSheet(f"""
            QLabel {{
                color: {app_colors.PRIMARY};
                font-size: 8pt;
                padding: 0px 10px;
            }}
        """)
        
        layout.addWidget(loading_label)
        layout.addWidget(dots_container)
        
        # Create animation
        self._setup_loader_animation()
        
        return loader

    def _setup_loader_animation(self):
        """Setup the loading dots animation"""
        if not hasattr(self, 'loader_dots'):
            return
            
        self.loader_timer = QTimer()
        self.loader_timer.timeout.connect(self._animate_loader_dots)
        self.loader_timer.start(300)  # Update every 300ms
        self.loader_animation_step = 0

    def _animate_loader_dots(self):
        """Animate the loading dots"""
        if not hasattr(self, 'loader_dots'):
            return
            
        for i, dot in enumerate(self.loader_dots):
            if i == self.loader_animation_step:
                dot.setStyleSheet(f"""
                    QLabel {{
                        color: {app_colors.PRIMARY};
                        font-size: 18pt;
                        padding: 0px;
                    }}
                """)
            else:
                dot.setStyleSheet("""
                    QLabel {
                        color: #666666;
                        font-size: 16pt;
                        padding: 0px;
                    }
                """)
        
        self.loader_animation_step = (self.loader_animation_step + 1) % 3














# Add scroll event handler:
    def _on_scroll(self, value):
        """Handle scroll events for infinite loading"""
        if self.is_loading_messages:
            return
            
        scroll_bar = self.chat_area.verticalScrollBar()
        
        # Check if scrolled to top (within 100 pixels)
        if value <= 100:
            # Load more messages if available
            self._load_more_messages()

# Add method to load more messages:
    def _load_more_messages(self):
        """Load older messages when scrolling up"""
        if self.is_loading_messages:
            return
            
        self.is_loading_messages = True
        
        try:
            # Get all messages sorted by timestamp
            all_messages = self._collect_all_active_messages()
            all_messages.sort(key=lambda msg: msg.timestamp)
            
            # Find messages older than currently loaded
            older_messages = []
            for msg in all_messages:
                if msg.id not in self.loaded_message_ids:
                    if self.oldest_loaded_timestamp is None or msg.timestamp < self.oldest_loaded_timestamp:
                        older_messages.append(msg)
            
            if not older_messages:
                self.is_loading_messages = False
                return
                
            # Show loader
            if not self.loader_widget:
                self.loader_widget = self._create_loader_widget()
            
            # Insert loader at top
            self.chat_layout.insertWidget(0, self.loader_widget)
            
            # Save scroll position
            scroll_bar = self.chat_area.verticalScrollBar()
            old_max = scroll_bar.maximum()
            old_value = scroll_bar.value()
            
            # Simulate loading delay (remove in production)
            QTimer.singleShot(300, lambda: self._finish_loading_messages(older_messages, old_max, old_value))
            
        except Exception as e:
            print(f"Error loading more messages: {e}")
            self.is_loading_messages = False

    def _finish_loading_messages(self, messages_to_load, old_scroll_max, old_scroll_value):
        """Finish loading older messages"""
        try:
            # Stop animation
            if hasattr(self, 'loader_timer'):
                self.loader_timer.stop()
                
            # Remove loader
            if self.loader_widget and self.loader_widget.parent():
                self.chat_layout.removeWidget(self.loader_widget)
                self.loader_widget.deleteLater()
                self.loader_widget = None
            # Remove loader

            
            # Load up to messages_per_page older messages
            messages_to_add = messages_to_load[-self.messages_per_page:]
            
            # Add messages at the top
            for i, msg in enumerate(messages_to_add):
                self._add_bubble_at_position(msg, i)
                self.loaded_message_ids.add(msg.id)
                
                # Update oldest timestamp
                if self.oldest_loaded_timestamp is None or msg.timestamp < self.oldest_loaded_timestamp:
                    self.oldest_loaded_timestamp = msg.timestamp
            
            # Restore scroll position to maintain view
            def restore_scroll():
                scroll_bar = self.chat_area.verticalScrollBar()
                new_max = scroll_bar.maximum()
                height_added = new_max - old_scroll_max
                scroll_bar.setValue(old_scroll_value + height_added)
            
            QTimer.singleShot(10, restore_scroll)
            
        finally:
            self.is_loading_messages = False




    def _add_bubble_at_position(self, message_obj: ChatMessage, position: int):
        """Add bubble at specific position in layout"""
        # Create bubble (similar to existing _add_bubble logic)
        bubble = self._create_chat_bubble(message_obj)
        self.bubble_widgets[message_obj.id] = bubble
        self.chat_layout.insertWidget(position, bubble)

    def _show_checkin_settings(self):
        """Show proactive check-in settings dialog"""
        # Make sure check-in system is initialized
        if not hasattr(self, 'checkin_settings'):
            self._init_checkin_system()
        
        # Create and show the settings dialog
        dialog = CheckInSettingsDialog(self.checkin_settings, self)
        if dialog.exec_() == QDialog.Accepted:
            # User clicked Save - update settings
            self.checkin_settings = dialog.get_settings()
            self._save_checkin_settings()
            print(f"✅ Check-in settings updated for {self.character.display_name}")

    def _init_checkin_system(self):
        """Initialize proactive check-in system - ENHANCED VERSION"""
        self.checkin_settings = CheckInSettings()
        self.last_user_message_time: Optional[datetime] = None
        self.last_checkin_time: Optional[datetime] = None
        
        # Load check-in settings
        self._load_checkin_settings()
        
        # 🆕 NEW: Try to load last user message time from chat history
        self._load_last_user_message_time()





    def _load_last_user_message_time(self):
        """Load the last user message time from chat history"""
        try:
            if not hasattr(self, 'chat_tree') or not self.chat_tree.messages:
                return
                
            # Find the most recent user message
            latest_user_msg = None
            for msg in self.chat_tree.messages.values():
                if msg.role == "user":
                    if not latest_user_msg or msg.timestamp > latest_user_msg.timestamp:
                        latest_user_msg = msg
            
            if latest_user_msg:
                try:
                    self.last_user_message_time = datetime.strptime(latest_user_msg.timestamp, "%Y-%m-%d %H:%M:%S")
                    print(f"🕐 Loaded last user message time: {self.last_user_message_time}")
                except:
                    pass
                    
        except Exception as e:
            print(f"Error loading last user message time: {e}")





    def _load_checkin_settings(self):
        """Load check-in settings from file"""
        try:
            app_data_dir = get_app_data_dir()
            settings_file = app_data_dir / "characters" / self.character.name / "checkin_settings.json"
            
            if settings_file.exists():
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.checkin_settings = CheckInSettings.from_dict(data)
                    print(f"✅ Loaded check-in settings for {self.character.name}")
        except Exception as e:
            print(f"Error loading check-in settings: {e}")

    def _save_checkin_settings(self):
        """Save check-in settings to file"""
        try:
            app_data_dir = get_app_data_dir()
            settings_file = app_data_dir / "characters" / self.character.name / "checkin_settings.json"
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkin_settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving check-in settings: {e}")

    def _record_user_message(self):
        """Record that user sent a message (call this in your _send_message method)"""
        self.last_user_message_time = datetime.now()
        print(f"🕐 User message recorded at {self.last_user_message_time}")

    def _is_quiet_hours(self) -> bool:
        """Check if current time is within quiet hours"""
        if not hasattr(self, 'checkin_settings'):
            return False
            
        if not self.checkin_settings.quiet_hours_start or not self.checkin_settings.quiet_hours_end:
            return False
            
        now = datetime.now().time()
        try:
            start = datetime.strptime(self.checkin_settings.quiet_hours_start, "%H:%M").time()
            end = datetime.strptime(self.checkin_settings.quiet_hours_end, "%H:%M").time()
            
            # 🆕 SPECIAL CASE: 00:00 to 00:00 means "always quiet" (block all messages)
            if start == end and start.hour == 0 and start.minute == 0:
                print(f"🔇 Always quiet hours detected (00:00-00:00) - blocking all messages")
                return True
            
            if start <= end:
                return start <= now <= end
            else:  # Quiet hours span midnight
                return now >= start or now <= end
        except:
            return False

    def _should_check_in(self) -> bool:
        """Determine if character should check in - FIXED VERSION"""
        if not hasattr(self, 'checkin_settings') or not self.checkin_settings.enabled:
            print(f"🚫 Check-in disabled or settings missing")
            return False
            
        if self._is_quiet_hours():
            print(f"🔇 In quiet hours")
            return False
        
        # 🆕 Don't check in if user is actively chatting
        if self._is_user_actively_chatting():
            print(f"🚫 User is actively chatting")
            return False
            
        now = datetime.now()
        
        # 🆕 NEW: Check if enough time has passed since last check-in
        if hasattr(self, 'last_checkin_time') and self.last_checkin_time:
            time_since_last_checkin = now - self.last_checkin_time
            if time_since_last_checkin < timedelta(minutes=self.checkin_settings.interval_minutes):
                print(f"🕐 Too soon since last check-in ({time_since_last_checkin.total_seconds()/60:.1f} min ago)")
                return False
        
        # 🆕 FIXED: For proactive check-ins, we have two scenarios:
        
        # Scenario 1: User has sent messages before - check timing
        if hasattr(self, 'last_user_message_time') and self.last_user_message_time:
            time_since_last_message = now - self.last_user_message_time
            
            # Don't check if user was active very recently (less than interval)
            if time_since_last_message < timedelta(minutes=self.checkin_settings.interval_minutes):
                print(f"🕐 User message too recent ({time_since_last_message.total_seconds()/60:.1f} min ago)")
                return False
                
            # Don't check if too much time has passed (user might be away)
            if time_since_last_message > timedelta(hours=self.checkin_settings.max_idle_hours):
                print(f"⏰ User idle too long ({time_since_last_message.total_seconds()/3600:.1f} hours)")
                return False
                
            print(f"✅ User message timing good ({time_since_last_message.total_seconds()/60:.1f} min ago)")
            return True
        
        # 🆕 Scenario 2: No user messages yet - check if enough time since character creation/last check-in
        else:
            # For new characters or those without user interaction, 
            # check if we should send an initial greeting check-in
            
            # If we've never checked in, allow initial check-in after a short delay
            if not hasattr(self, 'last_checkin_time') or not self.last_checkin_time:
                print(f"✅ No previous check-in - allowing initial check-in")
                return True
                
            # Otherwise, use normal interval timing for subsequent check-ins
            time_since_last_checkin = now - self.last_checkin_time
            if time_since_last_checkin >= timedelta(minutes=self.checkin_settings.interval_minutes):
                print(f"✅ Time for follow-up check-in ({time_since_last_checkin.total_seconds()/60:.1f} min since last)")
                return True
            
            print(f"🕐 Too soon for follow-up check-in ({time_since_last_checkin.total_seconds()/60:.1f} min since last)")
            return False



    def _is_user_actively_chatting(self) -> bool:
        """Check if user is actively chatting (sent message in last 2 minutes)"""
        if not hasattr(self, 'last_user_message_time') or not self.last_user_message_time:
            return False
        
        now = datetime.now()
        time_since_last = now - self.last_user_message_time
        
        # Consider user "actively chatting" if they sent a message in the last 2 minutes
        active_threshold = timedelta(minutes=2)
        is_active = time_since_last < active_threshold
        
        if is_active:
            print(f"👤 User is actively chatting (last message {time_since_last.total_seconds():.0f}s ago)")
        
        return is_active





    def _generate_checkin_prompt(self):
        """Generate context-aware check-in prompt"""
        base_prompt = "You haven't heard from the user in a while. Check on them proactively in your personality."
        
        if not hasattr(self, 'checkin_settings') or not self.checkin_settings.personalized_responses:
            return base_prompt
            
        try:
            # Get recent message context
            recent_messages = self._get_recent_checkin_context()
            
            if recent_messages:
                context_prompt = f"""The user hasn't messaged you in a while. Based on your recent conversations, check on them in a caring, personalized way that matches your personality.

    Recent conversation context:
    {recent_messages}

    Reach out to them naturally, referencing your previous conversations if appropriate. Show that you care and are thinking about them. Keep it brief but warm - they might be busy."""
                return context_prompt
            else:
                return "You haven't heard from the user in a while. Reach out and check on them in a caring way that matches your personality."
                
        except Exception as e:
            print(f"Error generating personalized check-in: {e}")
            return base_prompt












    def _apply_window_settings(self):
        """Apply all window settings immediately after initialization"""
        # Apply pin status
        self._apply_pin_status()
        
        # Apply transparency settings
        self._setup_transparency()
        
        # Update pin button appearance
        self._update_pin_button_appearance()

    def _apply_pin_status(self):
        """Apply the pin status from saved state"""
        if self.always_on_top:
            # Set window to stay on top
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            self.show()  # Need to show again after changing flags
        else:
            # Ensure stay on top flag is not set
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            self.show()

    def _update_pin_button_appearance(self):
        """Update pin button appearance based on current state"""
        if hasattr(self, 'pin_btn'):
            if self.always_on_top:
                # Highlighted appearance when pinned
                self.pin_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {app_colors.PRIMARY};
                        color: white;
                        border: none;
                        font-size: 11pt;
                        border-radius: 3px;
                    }}
                """)
            else:
                # Normal appearance when not pinned
                self.pin_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: transparent;
                        color: {app_colors.SECONDARY};
                        border: none;
                        font-size: 11pt;
                        border-radius: 3px;
                    }}
                """)





    def _center_on_screen(self):
        """Center the chat window on the screen"""
        try:
            # Get screen geometry
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            
            # Get window size
            window_size = self.size()
            
            # Calculate center position
            x = (screen_geometry.width() - window_size.width()) // 2
            y = (screen_geometry.height() - window_size.height()) // 2
            
            # Move to center
            self.move(x, y)
            
        except Exception as e:
            print(f"Error centering window: {e}")
            # Fallback to a reasonable position
            self.move(200, 100)


    # Add these methods to ChatWindow class:

    def _process_external_api_command(self, command: str) -> bool:
        """Process external API commands like /use API_NAME param=value"""
        if not command.startswith("/use "):
            return False
        
        try:
            # Parse command: /use WeatherAPI location=Paris key=mykey
            parts = command[5:].split()  # Remove "/use "
            if not parts:
                self._add_system_message("Usage: /use API_NAME param1=value1 param2=value2")
                return True
            
            api_name = parts[0]
            
            # Parse parameters
            args_dict = {}
            for part in parts[1:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    args_dict[key.strip()] = value.strip()
            
            # Find API in character's external APIs
            target_api = None
            for api in self.character.external_apis:
                if api.name == api_name and api.enabled:
                    target_api = api
                    break
            
            if not target_api:
                enabled_apis = [api.name for api in self.character.external_apis if api.enabled]
                if enabled_apis:
                    self._add_system_message(f"API '{api_name}' not found. Available APIs: {', '.join(enabled_apis)}")
                else:
                    self._add_system_message("No external APIs configured or enabled for this character.")
                return True
            
            # Execute API call in background thread
            self._execute_external_api_call(target_api, args_dict)
            return True
            
        except Exception as e:
            self._add_system_message(f"Error processing API command: {str(e)}")
            return True

    def _execute_external_api_call(self, api: ExternalAPI, args_dict: Dict[str, str]):
        """Execute external API call in background thread with LLM summarization"""
        def run_api_call():
            try:
                import requests
                
                # Replace parameters in URL and params
                url = api.url
                params = {}
                headers = api.headers.copy()
                
                # Replace {param} placeholders
                for key, value in api.params.items():
                    if value.startswith("{") and value.endswith("}"):
                        param_name = value[1:-1]  # Remove { and }
                        if param_name in args_dict:
                            params[key] = args_dict[param_name]
                        else:
                            params[key] = value  # Keep original if no replacement
                    else:
                        params[key] = value
                
                # Replace placeholders in URL
                for param_name, param_value in args_dict.items():
                    url = url.replace(f"{{{param_name}}}", param_value)
                    # Also replace in headers
                    for header_key, header_value in headers.items():
                        headers[header_key] = header_value.replace(f"{{{param_name}}}", param_value)
                
                # Make API request
                response = requests.request(
                    api.method,
                    url,
                    headers=headers,
                    params=params if api.method == "GET" else None,
                    json=params if api.method in ["POST", "PUT"] else None,
                    timeout=api.timeout
                )
                
                # Handle response
                if response.status_code == 200:
                    try:
                        # Get the raw response
                        raw_data = response.text
                        
                        # Create a summarization prompt
                        summarization_prompt = f"""Please analyze and summarize this API response from {api.name} in a clear, user-friendly way:

    API Response:
    {raw_data}

    IMPORTANT REQUIREMENTS:
    - Provide COMPLETE information - don't cut off mid-sentence
    - Include all URLs and links from the response so users can access them
    - For updates/patches, include specific details about what changed
    - Make sure all information is clear and actionable

    Please provide:
    1. A brief summary of what this data shows
    2. The key information extracted in an easy-to-read format with COMPLETE details
    3. Any important details or highlights
    4. Include all relevant URLs/links from the response

    Format your response to be helpful for a regular user, not technical JSON. Make it conversational, complete, and useful."""

                        # Use the AI interface to summarize
                        api_config_name = getattr(self.character, 'api_config_name', None)
                        
                        # Create a simple conversation for the summarization
                        summary_messages = [{"role": "user", "content": summarization_prompt}]
                        
                        # Get AI summary
                        ai_summary = self.ai_interface.get_response(
                            summary_messages, 
                            f"You are a helpful assistant that summarizes API responses clearly and concisely. Focus on extracting the most useful information for the user.",
                            api_config_name
                        )
                        
                        # Format the final result
                        result_text = f"✅ **{api.name} Results:**\n\n{ai_summary}"
                        
                    except Exception as e:
                        # Fallback to raw response if LLM summarization fails
                        print(f"LLM summarization failed: {e}")
                        try:
                            # Try to format as JSON if possible
                            json_data = response.json()
                            formatted_response = json.dumps(json_data, indent=2)
                            result_text = f"✅ {api.name} API Result:\n```json\n{formatted_response}\n```"
                        except:
                            # Ultimate fallback to plain text
                            result_text = f"✅ {api.name} API Result:\n{response.text[:1000]}{'...' if len(response.text) > 1000 else ''}"
                else:
                    result_text = f"❌ {api.name} API Error (Status {response.status_code}):\n{response.text[:300]}{'...' if len(response.text) > 300 else ''}"
                
                # Add result to chat
                self._add_system_message(result_text)
                
            except requests.exceptions.Timeout:
                self._add_system_message(f"❌ {api.name} API timeout after {api.timeout} seconds")
            except requests.exceptions.RequestException as e:
                self._add_system_message(f"❌ {api.name} API request failed: {str(e)}")
            except Exception as e:
                self._add_system_message(f"❌ {api.name} API error: {str(e)}")
        
        # Run in background thread
        threading.Thread(target=run_api_call, daemon=True).start()

    # Optional: Add a method to handle different types of API responses with custom prompts
    def _get_api_summarization_prompt(self, api_name: str, raw_data: str) -> str:
        """Get a custom summarization prompt based on API type"""
        
        api_name_lower = api_name.lower()
        
        if "steam" in api_name_lower or "news" in api_name_lower:
            return f"""Please summarize this gaming news API response from {api_name}:

    {raw_data}

    IMPORTANT REQUIREMENTS:
    - Include the complete summary for each news item - don't cut off mid-sentence
    - Always include the actual URLs/links so users can read the full articles
    - For updates/patches, explain what specific changes were made
    - Present all information clearly and completely

    Extract and present:
    - The most interesting news items (top 3-5) with COMPLETE descriptions
    - Headlines and FULL summaries (don't truncate)
    - Authors and dates where available
    - The actual URLs/links for each article
    - For game updates: specific changes, features, bug fixes
    - Make it engaging and informative for a gamer

    Format as a friendly news update with clickable links."""
        
        elif "weather" in api_name_lower:
            return f"""Please summarize this weather API response from {api_name}:

    {raw_data}

    Extract and present:
    - Current temperature and conditions
    - Location information
    - Any forecasts or additional details
    - Make it conversational and easy to understand

    Format as a friendly weather update."""
        
        elif "stock" in api_name_lower or "finance" in api_name_lower:
            return f"""Please summarize this financial API response from {api_name}:

    {raw_data}

    Extract and present:
    - Key financial metrics
    - Stock prices, changes, or trends
    - Important financial data
    - Make it understandable for someone checking investments

    Format as a clear financial summary."""
        
        else:
            # Generic prompt for unknown API types
            return f"""Please analyze and summarize this API response from {api_name}:

    {raw_data}

    Extract and present:
    - The most important information
    - Key data points in an organized way
    - Any notable details or insights
    - Make it easy to understand and useful

    Format as a clear, friendly summary."""

    # Optional: Add a method to handle different types of API responses with custom prompts
    def _get_api_summarization_prompt(self, api_name: str, raw_data: str) -> str:
        """Get a custom summarization prompt based on API type"""
        
        api_name_lower = api_name.lower()
        
        if "steam" in api_name_lower or "news" in api_name_lower:
            return f"""Please summarize this gaming news API response from {api_name}:

    {raw_data}

    Extract and present:
    - The most interesting news items (top 3-5)
    - Headlines and brief summaries
    - Authors and dates where available
    - Make it engaging for a gamer to read

    Format as a friendly news update."""
        
        elif "weather" in api_name_lower:
            return f"""Please summarize this weather API response from {api_name}:

    {raw_data}

    Extract and present:
    - Current temperature and conditions
    - Location information
    - Any forecasts or additional details
    - Make it conversational and easy to understand

    Format as a friendly weather update."""
        
        elif "stock" in api_name_lower or "finance" in api_name_lower:
            return f"""Please summarize this financial API response from {api_name}:

    {raw_data}

    Extract and present:
    - Key financial metrics
    - Stock prices, changes, or trends
    - Important financial data
    - Make it understandable for someone checking investments

    Format as a clear financial summary."""
        
        else:
            # Generic prompt for unknown API types
            return f"""Please analyze and summarize this API response from {api_name}:

    {raw_data}

    Extract and present:
    - The most important information
    - Key data points in an organized way
    - Any notable details or insights
    - Make it easy to understand and useful

    Format as a clear, friendly summary."""


    def _update_messages_incrementally(self, target_messages: List[ChatMessage]):
        """Update only changed messages instead of recreating everything"""
        target_ids = [msg.id for msg in target_messages]
        existing_ids = set(self.bubble_widgets.keys())
        target_id_set = set(target_ids)
        
        # Remove widgets for messages that are no longer active
        to_remove = existing_ids - target_id_set
        for msg_id in to_remove:
            if msg_id in self.bubble_widgets:
                widget = self.bubble_widgets[msg_id]
                self.chat_layout.removeWidget(widget)
                widget.deleteLater()
                del self.bubble_widgets[msg_id]
        
        # Add or update messages
        for i, message in enumerate(target_messages):
            if message.id in self.bubble_widgets:
                # Update existing widget if content changed
                widget = self.bubble_widgets[message.id]
                if widget.message_obj.content != message.content:
                    # Update content without recreating widget
                    formatted_content = widget._format_text(message.content)
                    widget.bubble_label.setText(formatted_content)
                    widget.message_obj.content = message.content
                
                # Update opacity if active state changed
                if widget.message_obj.is_active != message.is_active:
                    opacity = 1.0 if message.is_active else 0.6
                    style = widget.bubble_label.styleSheet()
                    # Simple opacity update
                    new_style = re.sub(r'opacity:\s*[\d.]+;', f'opacity: {opacity};', style)
                    if 'opacity:' not in style:
                        new_style = style.rstrip('}') + f' opacity: {opacity}; }}'
                    widget.bubble_label.setStyleSheet(new_style)
                    widget.message_obj.is_active = message.is_active
            else:
                # Create new widget only if needed
                self._add_single_bubble(message)


    def _add_single_bubble(self, message_obj: ChatMessage):
        """Add a single bubble at the correct position"""
        try:
            # If this is called during a refresh, just add to end
            # The refresh process will handle proper ordering
            if self.update_in_progress:
                return self._create_and_add_bubble(message_obj)
            
            # For individual adds, we need to find correct position
            all_active_messages = self._collect_all_active_messages()
            all_active_messages.sort(key=lambda msg: msg.timestamp)
            
            # Find where this message should be positioned
            target_position = None
            for i, msg in enumerate(all_active_messages):
                if msg.id == message_obj.id:
                    target_position = i
                    break
            
            if target_position is not None:
                # Create bubble
                bubble = self._create_bubble_widget(message_obj)
                
                # Insert at correct position
                self.chat_layout.insertWidget(target_position, bubble)
                self.bubble_widgets[message_obj.id] = bubble
                
                # Update indices for all widgets after this one
                self._update_widget_indices()
            else:
                # Fallback: add at end
                self._create_and_add_bubble(message_obj)
                
        except Exception as e:
            print(f"Error adding single bubble: {e}")
            # Fallback to simple add
            self._create_and_add_bubble(message_obj)

    def _update_widget_indices(self):
        """Update widget position tracking after insertions"""
        for msg_id, widget in self.bubble_widgets.items():
            index = self.chat_layout.indexOf(widget)
            if index >= 0:
                # Update any internal tracking if needed
                pass

    def _create_bubble_widget(self, message_obj: ChatMessage):
        """Create bubble widget without adding to layout - OPTIMIZED VERSION"""
        
        # ✅ PERFORMANCE: Check if we can reuse existing bubble
        if message_obj.id in self.bubble_widgets:
            existing_bubble = self.bubble_widgets[message_obj.id]
            if existing_bubble and hasattr(existing_bubble, 'message_obj'):
                # Update content if it changed, but reuse the widget
                if existing_bubble.message_obj.content != message_obj.content:
                    existing_bubble.message_obj = message_obj
                    formatted_content = existing_bubble._format_text(message_obj.content)
                    existing_bubble.bubble_label.setText(formatted_content)
                return existing_bubble
        
        # Get names for placeholder replacement
        character_name = getattr(self.character, 'display_name', 
                                getattr(self.character, 'folder_name', 'Assistant'))
        user_profile = self._get_effective_user_profile()
        user_name = user_profile.user_name if user_profile else "User"
        
        # Get siblings for navigation
        siblings = self.chat_tree.get_siblings(message_obj.id)
        has_siblings = len(siblings) > 1
        sibling_position = None
        
        if has_siblings:
            sibling_index = siblings.index(message_obj.id)
            sibling_position = (sibling_index, len(siblings))
        
        # Calculate indent level
        indent_level = 0
        if message_obj.parent_id:
            current_id = message_obj.parent_id
            while current_id and indent_level < 3:
                indent_level += 1
                parent = self.chat_tree.messages.get(current_id)
                current_id = parent.parent_id if parent else None
        
        # ✅ OPTIMIZED: Get colors with caching and smart logging
        if (getattr(self.character, 'use_character_colors', False) and
            hasattr(self.character, 'character_primary_color') and
            hasattr(self.character, 'character_secondary_color') and
            self.character.character_primary_color and
            self.character.character_secondary_color):
            primary_color = self.character.character_primary_color
            secondary_color = self.character.character_secondary_color
            color_source = "character"
        else:
            primary_color = app_colors.PRIMARY
            secondary_color = app_colors.SECONDARY
            color_source = "global"
        
        # ✅ SMART LOGGING: Only log when colors actually change
        current_color_state = (primary_color, secondary_color, color_source)
        if not hasattr(self, '_last_bubble_color_state') or self._last_bubble_color_state != current_color_state:
            self._last_bubble_color_state = current_color_state
            print(f"🎨 {self.character.display_name}: Switched to {color_source} colors ({primary_color}, {secondary_color})")
        
        # ✅ CREATE BUBBLE: Only when actually needed
        bubble = ChatBubble(
            message_obj=message_obj,
            config=self.character,
            user_icon=self.user_icon,
            character_icon=self.character_icon,
            has_siblings=has_siblings,
            sibling_position=sibling_position,
            indent_level=indent_level,
            character_name=character_name,
            user_name=user_name,
            primary_color=primary_color,
            secondary_color=secondary_color
        )
        
        # Connect signals
        bubble.edit_requested.connect(self._handle_edit_message)
        bubble.retry_requested.connect(self._handle_retry_message)
        bubble.delete_requested.connect(self._handle_delete_message)
        bubble.navigate_sibling.connect(self._handle_navigate_sibling)
        
        return bubble


    def _create_bubble_widget(self, message_obj: ChatMessage):
        """Create bubble widget with correct character colors - FIXED for interactions"""
        
        # Get names for placeholder replacement
        character_name = getattr(self.character, 'display_name', 
                                getattr(self.character, 'folder_name', 'Assistant'))
        user_profile = self._get_effective_user_profile()
        user_name = user_profile.user_name if user_profile else "User"
        
        # Get siblings for navigation
        siblings = self.chat_tree.get_siblings(message_obj.id)
        has_siblings = len(siblings) > 1
        sibling_position = None
        
        if has_siblings:
            sibling_index = siblings.index(message_obj.id)
            sibling_position = (sibling_index, len(siblings))
        
        # Calculate indent level
        indent_level = 0
        if message_obj.parent_id:
            current_id = message_obj.parent_id
            while current_id and indent_level < 3:
                indent_level += 1
                parent = self.chat_tree.messages.get(current_id)
                current_id = parent.parent_id if parent else None
        
        # ENHANCED: Always get character colors correctly
        print(f"🎨 Creating bubble for message: {message_obj.content[:30]}...")
        
        # Check character colors first
        if (getattr(self.character, 'use_character_colors', False) and
            hasattr(self.character, 'character_primary_color') and
            hasattr(self.character, 'character_secondary_color') and
            self.character.character_primary_color and
            self.character.character_secondary_color):
            
            primary_color = self.character.character_primary_color
            secondary_color = self.character.character_secondary_color
            color_source = "character"
            print(f"🎨 Using character colors: {primary_color} / {secondary_color}")
            
        else:
            primary_color = app_colors.PRIMARY
            secondary_color = app_colors.SECONDARY
            color_source = "global"
            print(f"🎨 Using global colors: {primary_color} / {secondary_color}")
        
        # Create the ChatBubble with the colors
        bubble = ChatBubble(
            message_obj,
            self.character, 
            self.user_icon, 
            self.character_icon,
            has_siblings,
            sibling_position,
            indent_level,
            character_name,
            user_name,
            primary_color,    # ← CRITICAL: Always pass these
            secondary_color   # ← CRITICAL: Always pass these
        )
        
        print(f"✅ ChatBubble created with {color_source} colors")
        
        # Connect signals
        bubble.edit_requested.connect(self._handle_edit_message)
        bubble.retry_requested.connect(self._handle_retry_message)
        bubble.delete_requested.connect(self._handle_delete_message)
        bubble.navigate_sibling.connect(self._handle_navigate_sibling)
        
        return bubble


    def _schedule_scroll_restore(self, was_at_bottom: bool, saved_position: int):
        """Schedule scroll position restoration with minimal delay"""
        if was_at_bottom:
            self.pending_scroll_action = 'bottom'
        elif saved_position is not None:
            self.pending_scroll_action = saved_position
        else:
            self.pending_scroll_action = None
        
        if self.pending_scroll_action is not None:
            self.scroll_timer.start(5)  # Very short delay

    def _apply_scroll_update(self):
        """Apply the pending scroll update"""
        if self.pending_scroll_action == 'bottom':
            scroll_bar = self.chat_area.verticalScrollBar()
            scroll_bar.setValue(scroll_bar.maximum())
        elif isinstance(self.pending_scroll_action, int):
            scroll_bar = self.chat_area.verticalScrollBar()
            scroll_bar.setValue(min(self.pending_scroll_action, scroll_bar.maximum()))
        
        self.pending_scroll_action = None

    def _refresh_display_simple(self):
        """Simple fallback refresh method for error recovery"""
        # Clear all bubbles
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.bubble_widgets.clear()
        
        # Re-add all active messages
        all_active_messages = self._collect_all_active_messages()
        all_active_messages.sort(key=lambda msg: msg.timestamp)
        
        for msg in all_active_messages:
            self._add_single_bubble(msg)

    def _remove_bubble_and_descendants(self, message_id: str):
        """Remove bubble and all its descendant bubbles"""
        message = self.chat_tree.messages.get(message_id)
        if not message:
            return
        
        # Remove this bubble
        if message_id in self.bubble_widgets:
            widget = self.bubble_widgets[message_id]
            self.chat_layout.removeWidget(widget)
            widget.deleteLater()
            del self.bubble_widgets[message_id]
        
        # Recursively remove children
        for child_id in message.children_ids:
            self._remove_bubble_and_descendants(child_id)


    def _update_single_bubble_color_debug(self, bubble: ChatBubble):
        """Update color of a single bubble without affecting others - DEBUG VERSION"""
        try:
            print(f"🔧 DEBUG: Starting single bubble color update...")
            
            # Check bubble attributes
            has_message = hasattr(bubble, 'message_obj') and bubble.message_obj is not None
            has_label = hasattr(bubble, 'bubble_label') and bubble.bubble_label is not None
            
            print(f"🔧 DEBUG: Bubble has message_obj: {has_message}")
            print(f"🔧 DEBUG: Bubble has bubble_label: {has_label}")
            
            if not has_label:
                print(f"❌ DEBUG: No bubble_label found, exiting")
                return
                
            if bubble.is_user:
                bg_color = self.character.user_bubble_color
                text_color = self.character.user_text_color
                transparency = getattr(self.character, 'user_bubble_transparency', 0)
                print(f"🔧 DEBUG: User bubble - bg: {bg_color}, text: {text_color}, trans: {transparency}")
            else:
                bg_color = self.character.bubble_color
                text_color = self.character.text_color
                transparency = getattr(self.character, 'bubble_transparency', 0)
                print(f"🔧 DEBUG: Character bubble - bg: {bg_color}, text: {text_color}, trans: {transparency}")
            
            if transparency > 0:
                from ..utils.helpers import hex_to_rgba
                bg_color = hex_to_rgba(bg_color, transparency)
                print(f"🔧 DEBUG: Applied transparency: {bg_color}")
            
            opacity = 1.0 if bubble.message_obj.is_active else 0.6
            print(f"🔧 DEBUG: Opacity: {opacity}")
            
            new_style = f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 10px;
                    border-radius: 12px;
                    font-family: {self.character.text_font};
                    font-size: {self.character.text_size}px;
                    opacity: {opacity};
                }}
            """
            
            print(f"🔧 DEBUG: New style: {new_style}")
            
            old_style = bubble.bubble_label.styleSheet()
            print(f"🔧 DEBUG: Old style: {old_style[:100]}...")
            
            bubble.bubble_label.setStyleSheet(new_style)
            
            # Force update
            bubble.bubble_label.update()
            bubble.bubble_label.repaint()
            
            print(f"✅ DEBUG: Style applied and widget updated")
            
        except Exception as e:
            print(f"❌ Error updating bubble color: {e}")
            import traceback
            traceback.print_exc()





    def _update_single_bubble_color(self, bubble: ChatBubble):
        """Update color of a single bubble without affecting others - OPTIMIZED VERSION"""
        try:
            # Quick validation
            if not (hasattr(bubble, 'bubble_label') and bubble.bubble_label and 
                    hasattr(bubble, 'message_obj') and bubble.message_obj):
                return
            
            # Update bubble's config reference
            bubble.config = self.character
                
            # Determine colors
            if bubble.is_user:
                bg_color = self.character.user_bubble_color
                text_color = self.character.user_text_color
                transparency = getattr(self.character, 'user_bubble_transparency', 0)
            else:
                bg_color = self.character.bubble_color
                text_color = self.character.text_color
                transparency = getattr(self.character, 'bubble_transparency', 0)
            
            # Apply transparency
            if transparency > 0:
                from ..utils.helpers import hex_to_rgba
                bg_color = hex_to_rgba(bg_color, transparency)
            
            # Calculate opacity
            opacity = 1.0 if bubble.message_obj.is_active else 0.6
            
            # CRITICAL: Reformat text content with new colors
            formatted_content = bubble._format_text(bubble.message_obj.content)
            bubble.bubble_label.setText(formatted_content)
            
            # Apply stylesheet
            new_style = f"""
                QLabel {{
                    background-color: {bg_color};
                    color: {text_color};
                    padding: 10px;
                    border-radius: 12px;
                    font-family: {self.character.text_font};
                    font-size: {self.character.text_size}px;
                    opacity: {opacity};
                }}
            """
            
            bubble.bubble_label.setStyleSheet(new_style)
            
        except Exception:
            pass  # Silent fail to prevent disrupting other bubbles



    def _add_system_message(self, message: str):
        """Add a system message to the chat"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        system_msg = ChatMessage("system", message, timestamp)
        
        # Add to tree
        self.chat_tree.add_message(system_msg)
        
        # Add bubble
        self.add_bubble_signal.emit(system_msg)
        self.save_chat_history_signal.emit()

    def update_colors(self):
        """Enhanced update_colors method for ChatWindow - SKIP BACKGROUND UPDATES"""
        # Debouncing: Prevent rapid repeated calls
        current_time = time.time()
        if hasattr(self, '_last_color_update_time'):
            if current_time - self._last_color_update_time < 0.1:  # 100ms debounce
                return
        self._last_color_update_time = current_time
        
        try:
            # Determine which colors to use
            if getattr(self.character, 'use_character_colors', False):
                primary = getattr(self.character, 'character_primary_color', app_colors.PRIMARY)
                secondary = getattr(self.character, 'character_secondary_color', app_colors.SECONDARY)
            else:
                primary = app_colors.PRIMARY
                secondary = app_colors.SECONDARY
            
            # Only update if colors actually changed
            if hasattr(self, '_last_applied_colors'):
                if self._last_applied_colors == (primary, secondary):
                    return  # No change, skip update
            
            self._last_applied_colors = (primary, secondary)
            
            # UPDATE TITLE BAR
            if hasattr(self, 'title_bar') and self.title_bar is not None:
                self.title_bar.setStyleSheet(f"background-color: {primary};")
            
            # UPDATE CHAT WINDOW TITLE TEXT
            if hasattr(self, 'title_bar') and self.title_bar is not None:
                title_labels = self.title_bar.findChildren(QLabel)
                for label in title_labels:
                    if label and label.text():
                        label.setStyleSheet(f"color: {secondary}; font-weight: bold; font-size: 10pt;")
            
            # UPDATE ALL TITLE BAR BUTTONS
            if hasattr(self, 'title_bar') and self.title_bar is not None:
                title_buttons = self.title_bar.findChildren(QPushButton)
                for btn in title_buttons:
                    if not btn:
                        continue
                        
                    button_text = btn.text()
                    
                    if button_text == "×":  # Close button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary};
                                border: none;
                                font-size: 14pt;
                                font-weight: bold;
                                border-radius: 3px;
                                padding: -3px 0px 0px 0px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 0, 0, 0.3);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 0, 0, 0.5);
                            }}
                        """)
                    elif button_text == "−":  # Minimize button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary};
                                border: none;
                                font-size: 12pt;
                                font-weight: bold;
                                border-radius: 3px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
                    elif button_text == "❖":  # Settings button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary};
                                border: none;
                                font-size: 11pt;
                                border-radius: 3px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
                    elif button_text == "📌":  # Pin button
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: transparent;
                                color: {secondary};
                                border: none;
                                font-size: 11pt;
                                border-radius: 3px;
                            }}
                            QPushButton:hover {{
                                background-color: rgba(255, 255, 255, 0.2);
                            }}
                            QPushButton:pressed {{
                                background-color: rgba(255, 255, 255, 0.3);
                            }}
                        """)
            
            # UPDATE SEND BUTTON
            if hasattr(self, 'send_btn') and self.send_btn is not None:
                self.send_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {secondary};
                        color: {primary};
                        border: none;
                        border-radius: 22px;
                        font-size: 16pt;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {primary};
                        color: {secondary};
                    }}
                    QPushButton:pressed {{
                        background-color: {secondary};
                        color: {primary};
                    }}
                    QPushButton:disabled {{
                        background-color: {secondary};
                        color: {primary};
                        border: none;
                    }}
                    QToolTip {{
                        color: {secondary};
                        background-color: {primary};
                        border: 1px solid {secondary};
                        padding: 5px;
                        border-radius: 3px;
                    }}
                """)
            
            # UPDATE CUSTOM SCROLLBAR COLORS
            if hasattr(self, 'scrollbar') and self.scrollbar is not None:
                try:
                    from ..utils.helpers import hex_to_rgba
                    
                    scrollbar_bg = hex_to_rgba(secondary, 100)
                    scrollbar_handle = hex_to_rgba(primary, 50)
                    scrollbar_handle_hover = hex_to_rgba(primary, 70)
                    
                    self.scrollbar.setStyleSheet(f"""
                        QScrollBar:vertical {{
                            background: {scrollbar_bg};
                            width: 8px;
                            border-radius: 4px;
                            margin: 0px;
                        }}
                        QScrollBar::handle:vertical {{
                            background: {scrollbar_handle};
                            border-radius: 4px;
                            min-height: 30px;
                        }}
                        QScrollBar::handle:vertical:hover {{
                            background: {scrollbar_handle_hover};
                        }}
                        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                            height: 0px;
                        }}
                        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                            background: transparent;
                        }}
                    """)
                except Exception:
                    pass
            
            # UPDATE INPUT CONTAINER - Add this back
            if hasattr(self, 'input_text') and self.input_text is not None:
                input_container = self.input_text.parent()
                if input_container:
                    input_container.setStyleSheet(f"""
                        QWidget {{
                            background-color: {secondary};
                            border-top: none;
                        }}
                    """)
            
            # UPDATE INPUT TEXT AREA - Add this back
            if hasattr(self, 'input_text') and self.input_text is not None:
                self.input_text.setStyleSheet(f"""
                    QTextEdit {{
                        background-color: {secondary};
                        border: none;
                        border-radius: 6px;
                        padding: 8px;
                        font-family: 'Segoe UI', Arial, sans-serif;
                        font-size: 10pt;
                        color: {primary}
                    }}
                    QTextEdit:focus {{
                        border: none;
                        background-color: none;
                    }}
                    QTextEdit:hover {{
                        border: none;
                    }}
                """)
            
            # Update bubble colors if they exist
            self._update_bubble_colors_only(primary, secondary)
            
            # 🚫 ONLY CHAT AREA background updates are skipped
            # Input areas will follow the color scheme, but chat background is preserved
            
            # Single clean log message
            print(f"🎨 {self.character.display_name}: Colors updated")
            
        except (AttributeError, RuntimeError):
            # Silent fail for cleanup
            pass




    def _update_bubble_colors_only(self, primary, secondary):
        """Update bubble button colors without recreating bubbles - PASS CORRECT COLORS"""
        try:
            for bubble in self.bubble_widgets.values():
                if bubble and hasattr(bubble, '_update_button_colors'):
                    # 🆕 UPDATE THE STORED COLORS FIRST
                    bubble.primary_color = primary
                    bubble.secondary_color = secondary
                    
                    # Then update the button colors
                    bubble._update_button_colors(primary, secondary)
        except Exception as e:
            print(f"Error updating bubble colors: {e}")


    def _refresh_all_chat_bubble_colors(self):
        """Refresh all chat bubble action button colors AND navigation arrows - ENHANCED VERSION"""
        if not hasattr(self, 'chat_layout') or self.chat_layout is None:
            return
            
        try:
            for i in range(self.chat_layout.count()):
                item = self.chat_layout.itemAt(i)
                if item and item.widget():
                    bubble = item.widget()
                    try:
                        # Update action buttons (Edit, Retry, Del) in bubble
                        action_buttons = bubble.findChildren(QPushButton)
                        for btn in action_buttons:
                            if btn and hasattr(btn, 'text'):
                                button_text = btn.text()
                                
                                # Update action buttons (Edit, Retry, Del)
                                if button_text in ["Edit", "Retry", "Del"]:
                                    # Check if button is enabled to apply correct styling
                                    if btn.isEnabled():
                                        btn.setStyleSheet(f"""
                                            QPushButton {{
                                                background-color: {app_colors.SECONDARY};
                                                color: {app_colors.PRIMARY};
                                                border: none;
                                                border-radius: 5px;
                                                font-size: 8pt;
                                                font-weight: bold;
                                            }}
                                            QPushButton:hover {{
                                                background-color: {app_colors.PRIMARY};
                                                color: {app_colors.SECONDARY};
                                            }}
                                            QPushButton:pressed {{
                                                background-color: {app_colors.PRIMARY};
                                            }}
                                        """)
                                    else:
                                        # Disabled button styling
                                        btn.setStyleSheet(f"""
                                            QPushButton {{
                                                background-color: #FFF3E0;
                                                color: #F57C00;
                                                border: 1px solid #FFCC02;
                                                border-radius: 5px;
                                                font-size: 8pt;
                                                font-weight: bold;
                                                opacity: 0.5;
                                            }}
                                        """)
                                
                                # FIX: Update navigation arrows (← →)
                                elif button_text in ["←", "→"]:
                                    # Check if button is enabled to apply correct styling
                                    if btn.isEnabled():
                                        btn.setStyleSheet(f"""
                                            QPushButton {{
                                                background-color: {app_colors.PRIMARY};
                                                border: none;
                                                border-radius: 3px;
                                                font-size: 8pt;
                                                font-weight: bold;
                                                color: {app_colors.SECONDARY};
                                            }}
                                            QPushButton:hover:enabled {{
                                                background-color: {app_colors.SECONDARY};
                                                color: {app_colors.PRIMARY};
                                            }}
                                            QPushButton:pressed {{
                                                background-color: {app_colors.PRIMARY};
                                            }}
                                        """)
                                    else:
                                        btn.setStyleSheet(f"""
                                            QPushButton {{
                                                color: #CCCCCC;
                                                background-color: {app_colors.PRIMARY};
                                                border: none;
                                                border-radius: 3px;
                                                font-size: 8pt;
                                                font-weight: bold;
                                            }}
                                        """)
                    except (AttributeError, RuntimeError):
                        continue
        except (AttributeError, RuntimeError):
            pass




    # 3. REPLACE ChatWindow.refresh_images_and_background method with immediate refresh
    def refresh_images_and_background(self):
        """Refresh all cached images and background with immediate UI update"""
        try:
            print("🔄 Refreshing chat window images and background...")
            
            # Clear ALL caches
            self.icon_cache.clear()
            QPixmapCache.clear()
            
            # Force reload icons with refresh flag
            self.user_icon = self._load_icon(
                self.chat_settings.user_icon_path,
                getattr(self.chat_settings, 'user_icon_scale', 1.0),
                getattr(self.chat_settings, 'user_icon_offset_x', 0),
                getattr(self.chat_settings, 'user_icon_offset_y', 0),
                force_refresh=True  # Force refresh
            )
            
            self.character_icon = self._load_icon(
                self.chat_settings.character_icon_path,
                getattr(self.chat_settings, 'character_icon_scale', 1.0),
                getattr(self.chat_settings, 'character_icon_offset_x', 0),
                getattr(self.chat_settings, 'character_icon_offset_y', 0),
                force_refresh=True  # Force refresh
            )
            
            # Completely reset the background
            self._complete_background_reset()
            
            # Refresh all message bubbles to show new icons
            self._refresh_all_message_bubbles()
            
            print("✅ Chat window completely refreshed")
            
        except Exception as e:
            print(f"❌ Error refreshing images: {e}")



    def _refresh_all_message_bubbles(self):
        """Refresh all message bubbles to show new icons"""
        try:
            # Get current scroll position
            scroll_bar = self.chat_area.verticalScrollBar()
            current_position = scroll_bar.value()
            
            # Clear all bubbles
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Process deletion
            QCoreApplication.processEvents()
            
            # Collect all active messages
            all_active_messages = self._collect_all_active_messages()
            all_active_messages.sort(key=lambda msg: msg.timestamp)
            
            # Re-render all messages with new icons
            for msg in all_active_messages:
                self._add_bubble(msg)
            
            # Restore scroll position
            QTimer.singleShot(50, lambda: scroll_bar.setValue(current_position))
            
            print("✅ All message bubbles refreshed")
            
        except Exception as e:
            print(f"❌ Error refreshing message bubbles: {e}")





    def _apply_fresh_image_background(self, image_path: str):
        """Apply image background with forced refresh"""
        try:
            # Force load image bypassing cache
            original_pixmap = force_reload_image(image_path)
            if original_pixmap.isNull():
                print(f"⚠️ Could not load background image: {image_path}")
                self._apply_background_color()
                return
            
            # Get chat area size
            chat_size = self.chat_area.size()
            if chat_size.width() <= 0 or chat_size.height() <= 0:
                chat_size = QSize(350, 500)
            
            # Add extra pixels to prevent gray lines
            bg_width = chat_size.width() + 10
            bg_height = chat_size.height() + 10
            
            # Calculate scaled dimensions
            scale = self.chat_settings.bg_image_scale
            scaled_width = int(original_pixmap.width() * scale)
            scaled_height = int(original_pixmap.height() * scale)
            
            # Scale the image
            scaled_pixmap = original_pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Create background pixmap
            bg_pixmap = QPixmap(bg_width, bg_height)
            bg_pixmap.fill(QColor(self.chat_settings.background_color))
            
            # Paint scaled image with offset
            painter = QPainter(bg_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate position with offset
            x = (bg_width - scaled_width) // 2 + self.chat_settings.bg_image_offset_x
            y = (bg_height - scaled_height) // 2 + self.chat_settings.bg_image_offset_y
            
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            

            timestamp = int(time.time() * 1000)
            app_data_dir = get_app_data_dir()
            temp_image_path = app_data_dir / "characters" / self.character.name / f"temp_bg_{timestamp}.png"
            temp_image_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Clean up old temp files
            try:
                for old_temp in temp_image_path.parent.glob("temp_bg_*.png"):
                    if old_temp.name != temp_image_path.name:
                        old_temp.unlink()
            except:
                pass
            
            # Save new background
            bg_pixmap.save(str(temp_image_path))
            
            # Apply with forced refresh
            bg_path = str(temp_image_path).replace('\\', '/')
            
            # Clear any previous styling
            self.chat_area.setStyleSheet("")
            self.chat_area.setAutoFillBackground(False)
            
            # Force update
            self.chat_area.update()
            QCoreApplication.processEvents()
            
            # Apply new background
            self.chat_area.setStyleSheet(f"""
                QScrollArea {{
                    background-image: url("{bg_path}");
                    background-position: center center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: rgba(102, 102, 102, 180);
                    min-height: 30px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: rgba(85, 85, 85, 200);
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
            
            # Force immediate update
            self.chat_area.update()
            self.chat_area.repaint()
            
            print(f"✅ Applied fresh background: {image_path}")
            
        except Exception as e:
            print(f"❌ Error applying fresh background: {e}")
            self._apply_background_color()

    def _apply_new_background(self):
        """Apply new background after complete reset"""
        try:
            # Apply background based on type
            if self.chat_settings.background_type == "image" and self.chat_settings.background_image_path:
                # Get full path
                if not os.path.isabs(self.chat_settings.background_image_path):
                    app_data_dir = get_app_data_dir()
                    char_dir = app_data_dir / "characters" / self.character.name
                    bg_path = str(char_dir / self.chat_settings.background_image_path)
                else:
                    bg_path = self.chat_settings.background_image_path
                
                if os.path.exists(bg_path):
                    self._apply_fresh_image_background(bg_path)
                else:
                    print(f"⚠️ Background image not found: {bg_path}")
                    self._apply_background_color()
            else:
                self._apply_background_color()
                
        except Exception as e:
            print(f"❌ Error applying new background: {e}")
            self._apply_background_color()


    # 4. ADD method to ChatWindow for complete background reset
    def _complete_background_reset(self):
        """Completely reset and reload the background"""
        try:
            # Remove any existing temp files
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.character.name
            for temp_file in char_dir.glob("temp_bg_*.png"):
                try:
                    temp_file.unlink()
                except:
                    pass
            
            # Clear widget completely
            self.chat_area.setStyleSheet("")
            self.chat_area.setAutoFillBackground(False)
            
            # Reset palette
            default_palette = QPalette()
            self.chat_area.setPalette(default_palette)
            
            # Force widget to clear any cached background
            self.chat_area.update()
            self.chat_area.repaint()
            
            # Process all pending events
            QCoreApplication.processEvents()
            
            # Small delay to ensure complete reset
            QTimer.singleShot(50, self._apply_new_background)
            
        except Exception as e:
            print(f"❌ Error in complete background reset: {e}")




    def _force_background_refresh(self):
        """Force a complete background refresh"""
        try:
            # Remove any existing temp files first
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.character.name
            for temp_file in char_dir.glob("temp_bg_*.png"):
                try:
                    temp_file.unlink()
                except:
                    pass
            
            # Clear the widget completely
            self.chat_area.setStyleSheet("")
            self.chat_area.setAutoFillBackground(False)
            self.chat_area.setPalette(QPalette())
            
            # Force widget update
            self.chat_area.update()
            QCoreApplication.processEvents()
            
            # Reapply background
            self._apply_chat_background()
            
        except Exception as e:
            print(f"⚠️ Error in force background refresh: {e}")


    def _add_bubble_with_scroll_control(self, message_obj: ChatMessage, was_at_bottom: bool, preserve_scroll_pos: int):
        """Add bubble with intelligent scroll behavior - UPDATED for user_name usage"""
        # Get names for placeholder replacement - USE USER NAME for {{user}}
        character_name = getattr(self.character, 'display_name', getattr(self.character, 'folder_name', 'Assistant'))
        user_profile = self._get_effective_user_profile()
        user_name = user_profile.user_name if user_profile else "User"  # USER NAME for {{user}} replacement
        
        # Get siblings for navigation
        siblings = self.chat_tree.get_siblings(message_obj.id)
        has_siblings = len(siblings) > 1
        sibling_position = None
        
        if has_siblings:
            sibling_index = siblings.index(message_obj.id)
            sibling_position = (sibling_index, len(siblings))
        
        # Calculate indent level
        indent_level = 0
        if message_obj.parent_id:
            current_id = message_obj.parent_id
            while current_id:
                indent_level += 1
                parent = self.chat_tree.messages.get(current_id)
                current_id = parent.parent_id if parent else None
        
        # Create bubble with user name for {{user}} replacement
        bubble = ChatBubble(
            message_obj, 
            self.character, 
            self.user_icon, 
            self.character_icon,
            has_siblings,
            sibling_position,
            indent_level,
            character_name,  # Character display name
            user_name        # USER NAME for {{user}} replacement
        )
        
        # Connect signals
        bubble.edit_requested.connect(self._handle_edit_message)
        bubble.retry_requested.connect(self._handle_retry_message)
        bubble.delete_requested.connect(self._handle_delete_message)
        bubble.navigate_sibling.connect(self._handle_navigate_sibling)
        
        self.chat_layout.addWidget(bubble)
        
        # Smart scroll behavior (unchanged)
        def apply_scroll():
            scroll_bar = self.chat_area.verticalScrollBar()
            if was_at_bottom:
                scroll_bar.setValue(scroll_bar.maximum())
            else:
                max_val = scroll_bar.maximum()
                if preserve_scroll_pos <= max_val:
                    scroll_bar.setValue(preserve_scroll_pos)
                else:
                    scroll_bar.setValue(max_val)
        
        QTimer.singleShot(10, apply_scroll)

    def _setup_transparency(self):
        """Setup transparency based on settings"""
        if not self.chat_settings.window_transparency_enabled:
            self._remove_transparency()
            return
        
        mode = self.chat_settings.window_transparency_mode
        
        if mode == "always":
            self._apply_transparency()
        elif mode == "time":
            self._start_transparency_timer()
        elif mode == "focus":
            # For focus mode, start with no transparency
            # Transparency will be applied only when focus is actually lost
            self._remove_transparency()


    def focusInEvent(self, event):
        """Handle focus in event"""
        super().focusInEvent(event)
        
        if self.chat_settings.window_transparency_enabled:
            mode = self.chat_settings.window_transparency_mode
            
            if mode == "focus":
                # Remove transparency when window gains focus
                self._remove_transparency()
            elif mode == "time":
                # Restart timer when window gains focus
                self._restart_transparency_timer()
    
    def changeEvent(self, event):
        """Handle window state changes"""
        super().changeEvent(event)
        
        if event.type() == QEvent.ActivationChange:
            if self.chat_settings.window_transparency_enabled and self.chat_settings.window_transparency_mode == "focus":
                if self.isActiveWindow():
                    # Window became active - remove transparency
                    self._remove_transparency()
                else:
                    # Window became inactive - apply transparency after delay
                    QTimer.singleShot(100, self._check_and_apply_focus_transparency)


    def focusOutEvent(self, event):
        """Handle focus out event"""
        super().focusOutEvent(event)
        
        if self.chat_settings.window_transparency_enabled:
            mode = self.chat_settings.window_transparency_mode
            
            if mode == "focus":
                # Apply transparency when window loses focus
                # Add small delay to ensure this isn't a temporary focus loss
                QTimer.singleShot(100, self._check_and_apply_focus_transparency)





    def _apply_transparency(self):
        """Apply transparency to the window"""
        if self.chat_settings.window_transparency_enabled:
            opacity = 1.0 - (self.chat_settings.window_transparency_value / 100.0)
            self.setWindowOpacity(opacity)
            self.is_transparent = True

    def _remove_transparency(self):
        """Remove transparency from the window"""
        self.setWindowOpacity(1.0)
        self.is_transparent = False
        self.transparency_timer.stop()

    def _start_transparency_timer(self):
        """Start the transparency timer"""
        if self.chat_settings.window_transparency_enabled and self.chat_settings.window_transparency_mode == "time":
            minutes = self.chat_settings.window_transparency_time
            self.transparency_timer.start(minutes * 60 * 1000)  # Convert to milliseconds

    def _restart_transparency_timer(self):
        """Restart the transparency timer"""
        if self.chat_settings.window_transparency_enabled and self.chat_settings.window_transparency_mode == "time":
            self._remove_transparency()
            self._start_transparency_timer()
   
    
    
    
    
    def resizeEvent(self, event):
        """Handle window resize to update background"""
        super().resizeEvent(event)
        
        # Only reapply background for images and only after a short delay
        if (hasattr(self, 'chat_settings') and 
            self.chat_settings.background_type == "image" and 
            self.chat_settings.background_image_path and 
            os.path.exists(self.chat_settings.background_image_path)):
            
            # Use a timer to avoid multiple rapid calls during resize
            if hasattr(self, '_resize_timer'):
                self._resize_timer.stop()
            
            self._resize_timer = QTimer()
            self._resize_timer.timeout.connect(self._apply_chat_background)
            self._resize_timer.setSingleShot(True)
            self._resize_timer.start(100)  # Wait 100ms after resize stops


    def _apply_positioned_background(self):
        """Apply background image with custom positioning"""
        try:
            # Load the original image
            original_pixmap = QPixmap(self.chat_settings.background_image_path)
            if original_pixmap.isNull():
                self._apply_background_color()
                return
            
            # Get chat area size
            chat_size = self.chat_area.size()
            
            # Calculate scaled dimensions using saved settings
            scale = self.chat_settings.bg_image_scale
            scaled_width = int(original_pixmap.width() * scale)
            scaled_height = int(original_pixmap.height() * scale)
            
            # Scale the image
            scaled_pixmap = original_pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Create final background pixmap
            bg_pixmap = QPixmap(chat_size)
            bg_pixmap.fill(QColor(self.chat_settings.background_color))
            
            # Paint scaled image with offset
            painter = QPainter(bg_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate position with offset - using saved offsets
            x = (chat_size.width() - scaled_width) // 2 + self.chat_settings.bg_image_offset_x
            y = (chat_size.height() - scaled_height) // 2 + self.chat_settings.bg_image_offset_y
            
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            
            # CLEAR STYLESHEET FIRST (this is the key fix)
            self.chat_area.setStyleSheet("")
            
            # Create a new palette instead of modifying existing
            new_palette = QPalette()
            new_palette.setBrush(QPalette.Window, QBrush(bg_pixmap))
            
            # Apply palette method
            self.chat_area.setPalette(new_palette)
            self.chat_area.setAutoFillBackground(True)
            
            # Force immediate update
            self.chat_area.repaint()
            
        except Exception as e:
            print(f"Error applying positioned background: {e}")
            self._apply_background_color()



    def _setup_ui(self):
        """Setup chat UI - Fixed version without transform properties"""
        # Central widget
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ===== TITLE BAR =====
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(30)
        self.title_bar.setStyleSheet(f"background-color: {app_colors.PRIMARY};")
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(8, 0, 5, 0)
        title_layout.setSpacing(5)
        
        # Title label
        character_display_name = getattr(self.character, 'display_name', self.character.name)
        
        # Get effective profile name for display - USE USER NAME
        effective_profile = self._get_effective_user_profile()
        if self.selected_user_profile:
            profile_indicator = f" ({self.selected_user_profile.user_name})"
        elif effective_profile:
            profile_indicator = f" (Global: {effective_profile.user_name})"
        else:
            profile_indicator = " (No Profile)"
        
        title_label = QLabel(f" Chat with {character_display_name}{profile_indicator}")
        title_label.setStyleSheet(f"color: {app_colors.SECONDARY}; font-weight: bold; font-size: 10pt;")
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        if hasattr(self, 'menu_bar'):
            checkin_action = QAction("Check-in Settings", self)
            checkin_action.triggered.connect(self._show_checkin_settings)     


        
        # Settings button
        settings_btn = QPushButton("❖")
        settings_btn.setFixedSize(28, 25)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 11pt;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        settings_btn.setToolTip("Settings")
        settings_btn.clicked.connect(self._show_settings_menu)
        title_layout.addWidget(settings_btn)
        



        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(28, 25)
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 11pt;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        self.pin_btn.setToolTip("Always on Top")
        self.pin_btn.clicked.connect(self._toggle_always_on_top)
        title_layout.addWidget(self.pin_btn)





        # Minimize button
        minimize_btn = QPushButton("−")
        minimize_btn.setFixedSize(28, 25)
        minimize_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        minimize_btn.setToolTip("Minimize")
        minimize_btn.clicked.connect(self._minimize_window)
        title_layout.addWidget(minimize_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(28, 25)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {app_colors.SECONDARY};
                border: none;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 3px;
                padding: -3px 0px 0px 0px;  /* Added padding adjustment */
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 0, 0, 0.5);
            }}
        """)
        close_btn.setToolTip("Close")
        close_btn.clicked.connect(self.close)
        title_layout.addWidget(close_btn)
        
        main_layout.addWidget(self.title_bar)
        
        # ===== CHAT AREA - FIXED FOR HORIZONTAL SCROLLING =====
        self.chat_area = QScrollArea()

        self.chat_area.setWidgetResizable(True)
        self.chat_area.verticalScrollBar().valueChanged.connect(self._on_scroll)

        # CRITICAL: Prevent horizontal scrolling completely
        self.chat_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set fixed width to prevent any expansion
        self.chat_area.setFixedWidth(350)
        
        # Custom modern scrollbar
        self.scrollbar = ModernScrollbar(Qt.Vertical)
        self.chat_area.setVerticalScrollBar(self.scrollbar)
        
        # Chat area styling
        self.chat_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollArea > QWidget > QWidget {
                background-color: transparent;
            }
        """)
        
        # ===== CHAT CONTENT WIDGET =====
        self.chat_content = QWidget()
        self.chat_content.setStyleSheet("background-color: transparent;")
        
        # CRITICAL: Set fixed width to prevent expansion
        self.chat_content.setFixedWidth(340)  # 10px less than chat_area
        
        # Chat layout with optimized spacing
        self.chat_layout = QVBoxLayout(self.chat_content)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(8)  # Reduced spacing
        self.chat_layout.setContentsMargins(2, 10, 2, 10)  # Minimal horizontal margins
        
        # Force layout to respect width constraints
        self.chat_layout.setSizeConstraint(QVBoxLayout.SetFixedSize)
        
        self.chat_area.setWidget(self.chat_content)
        main_layout.addWidget(self.chat_area)
        
        # ===== INPUT AREA =====
        input_container = QWidget()
        input_container.setObjectName("input_container")  # ADD THIS LINE
        input_container.setFixedHeight(70)
        input_container.setFixedWidth(350)  # Match window width
        input_container.setStyleSheet(f"""
            QWidget {{
                background-color: {app_colors.SECONDARY};
                border-top: none;
            }}
        """)
        
        input_layout = QVBoxLayout(input_container)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(0)
        
        # Input row
        input_row = QHBoxLayout()
        input_row.setSpacing(6)
        input_row.setContentsMargins(0, 0, 0, 0)
        
        # ===== TEXT INPUT =====
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(45)
        self.input_text.setFixedWidth(285)  # Fixed width
        self.input_text.setPlaceholderText("Type a message...")
        self.input_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {app_colors.SECONDARY};
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 10pt;
                color: {app_colors.PRIMARY}
            }}
            QTextEdit:focus {{
                border: none;
                background-color: none;
            }}
            QTextEdit:hover {{
                border: none;
            }}
        """)
        
        # Install event filter for Enter key handling
        self.input_text.installEventFilter(self)
        
        # Set text wrapping and scroll policies for input
        self.input_text.setWordWrapMode(QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.input_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.input_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        input_row.addWidget(self.input_text)
        
        # ===== SEND BUTTON - REMOVED TRANSFORM PROPERTIES =====
        self.send_btn = QPushButton("✦")
        self.send_btn.setFixedSize(45, 45)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {app_colors.SECONDARY};
                color: {app_colors.PRIMARY};
                border: none;
                border-radius: 22px;
                font-size: 16pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {app_colors.PRIMARY};
                color: {app_colors.SECONDARY};
            }}
            QPushButton:pressed {{
                background-color: {app_colors.SECONDARY};
                color: {app_colors.PRIMARY};
            }}
            QPushButton:disabled {{
                background-color: {app_colors.SECONDARY};
                color: {app_colors.PRIMARY};
                border: none;
            }}
            QToolTip {{
                color: {app_colors.SECONDARY};
                background-color: {app_colors.PRIMARY};
                border: 1px solid {app_colors.SECONDARY};
                padding: 5px;
                border-radius: 3px;
            }}
        """)

        self.send_btn.setToolTip("Send message (Enter)")
        self.send_btn.clicked.connect(self._handle_send_stop_button)
        
        input_row.addWidget(self.send_btn)
        
        # Add input row to input layout
        input_layout.addLayout(input_row)
        
        # Add input container to main layout
        main_layout.addWidget(input_container)
        
        # ===== FOCUS MANAGEMENT =====
        # Set initial focus to input
        self.input_text.setFocus()
        self.add_streaming_bubble_signal.connect(self._on_ai_start_writing)
        self.finalize_streaming_bubble_signal.connect(self._on_ai_finish_writing)



    def _stop_streaming_request(self):
        """Stop the streaming request at the AI interface level"""
        # Set the stop flag
        self.streaming_stopped = True
        
        # Try to interrupt the AI interface if it has a stop method
        if hasattr(self.ai_interface, 'stop_streaming'):
            try:
                self.ai_interface.stop_streaming()
            except Exception as e:
                print(f"Error stopping AI interface: {e}")
        
        # Force set a flag that the streaming callback can check
        if hasattr(self, 'force_stop_streaming'):
            self.force_stop_streaming = True

    def _stop_ai_writing(self):
        """Stop AI writing and ALWAYS send clean content, even if just 'Thinking...'"""
        print("🛑 Stopping AI writing...")
        
        # Stop streaming at multiple levels
        self.streaming_stopped = True
        self._stop_streaming_request()
        
        # ALWAYS send content - even if it's just "Thinking..."
        content_to_send = ""
        
        # Check what content we have available
        if hasattr(self, 'streaming_text') and self.streaming_text and self.streaming_text.strip():
            # We have actual streaming content
            content_to_send = self.streaming_text.strip()
            print(f"📤 Sending stopped streaming content: {content_to_send[:50]}...")
            
        elif hasattr(self, 'current_streaming_content') and self.current_streaming_content and self.current_streaming_content.strip():
            # We have content from current_streaming_content
            content_to_send = self.current_streaming_content.strip()
            print(f"📤 Sending stopped current content: {content_to_send[:50]}...")
            
        elif hasattr(self, 'streaming_bubble') and self.streaming_bubble and hasattr(self.streaming_bubble, 'bubble_label'):
            # Get content from the bubble itself and clean it
            bubble_text = self.streaming_bubble.bubble_label.text()
            if bubble_text and bubble_text.strip():
                # Clean HTML tags and get plain text
                cleaned_text = self._clean_html_content(bubble_text.strip())
                
                # Special case: if it's just "Thinking..." (with or without formatting), use plain text
                if "thinking" in cleaned_text.lower() and len(cleaned_text) < 20:
                    content_to_send = "Thinking..."
                    print(f"📤 Sending cleaned thinking content: {content_to_send}")
                else:
                    content_to_send = cleaned_text
                    print(f"📤 Sending cleaned bubble content: {content_to_send[:50]}...")
            else:
                # Fallback to "Thinking..." if bubble is empty or just whitespace
                content_to_send = "Thinking..."
                print(f"📤 Sending fallback content: {content_to_send}")
        else:
            # Ultimate fallback - always send something
            content_to_send = "Thinking..."
            print(f"📤 Sending ultimate fallback: {content_to_send}")
        
        # Create message with whatever content we have
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        assistant_msg = ChatMessage("assistant", content_to_send, timestamp)
        
        # Set parent_id on the message object before adding to tree
        parent_id = getattr(self, 'current_streaming_parent_id', None)
        if parent_id:
            assistant_msg.parent_id = parent_id
            assistant_msg.is_active = True
            
            # Add to tree
            assistant_msg_id = self.chat_tree.add_message(assistant_msg)
            
            # Clean up streaming bubble first
            self._finalize_streaming_bubble()
            
            # Add final bubble
            self.add_bubble_signal.emit(assistant_msg)
            
            # Save history
            self._save_chat_history()
            
            print(f"✅ Successfully sent stopped message: '{content_to_send}'")
            
        else:
            print("⚠️ No parent_id found, just cleaning up...")
            # Even without parent_id, clean up the streaming bubble
            self._finalize_streaming_bubble()
        
        # Force finish AI writing state
        self._on_ai_finish_writing()

    def _clean_html_content(self, html_text: str) -> str:
        """Clean HTML tags from text content"""
        if not html_text:
            return ""
        
        import re
        
        # Remove HTML tags
        clean_text = re.sub(r'<[^>]+>', '', html_text)
        
        # Clean up extra whitespace
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        
        # Special case: if it's essentially just "Thinking..." return plain text
        if clean_text.lower().strip() == "thinking...":
            return "Thinking..."
        
        return clean_text

    def _on_ai_start_writing(self):
        """Called when AI starts writing (streaming begins)"""
        self.is_ai_writing = True
        self.streaming_stopped = False
        self.current_streaming_content = ""
        self._disable_user_interactions()
        
    def _on_ai_finish_writing(self):
        """Called when AI finishes writing (streaming ends)"""
        self.is_ai_writing = False
        self.streaming_stopped = False
        self.current_streaming_content = ""
        self._enable_user_interactions()
        
    def _disable_user_interactions(self):
        """Disable interactions while AI is writing - KEEP YOUR STYLING"""
        try:
            # Change send button to cube symbol BUT keep your existing style
            if hasattr(self, 'send_btn'):
                self.send_btn.setText("■")  # Only change symbol, keep your style
                self.send_btn.setEnabled(True)  # Keep enabled for stopping
                self.send_btn.setToolTip("Stop writing")
                # DON'T change setStyleSheet - keep your existing styling
                
            # Keep input enabled for typing but prevent sending via Enter
            if hasattr(self, 'input_text'):
                self.input_text.setEnabled(True)  # Allow typing
                self.input_text.setPlaceholderText("AI is responding... (you can still type)")
                

            
            # Show visual indicator that AI is writing
            self._show_ai_writing_indicator()
            
        except Exception as e:
            print(f"Error disabling interactions: {e}")
            
    def _enable_user_interactions(self):
        """Re-enable all user interaction elements when AI finishes - KEEP YOUR STYLING"""
        try:
            # Restore send button to your original symbol and keep your styling
            if hasattr(self, 'send_btn'):
                # Change back to your original symbol (replace "YOUR_SYMBOL" with whatever you use)
                self.send_btn.setText("✦")  # Put your original symbol here
                self.send_btn.setEnabled(True)
                self.send_btn.setToolTip("Send message (Enter)")
                # DON'T change setStyleSheet - keep your existing styling
                
            if hasattr(self, 'input_text'):
                self.input_text.setEnabled(True)
                self.input_text.setPlaceholderText("Type a message...")
                
            # Your existing code for enabling bubble interactions
            
            # Hide AI writing indicator
            self._hide_ai_writing_indicator()
            
        except Exception as e:
            print(f"Error enabling interactions: {e}")

    def eventFilter(self, obj, event):
        """Override to prevent Enter key when AI is writing - MODIFIED"""
        if obj == self.input_text and event.type() == QEvent.KeyPress:
            if self.is_ai_writing:
                # Block Enter key when AI is writing, but allow other keys
                if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                    return True  # Block Enter/Return
                return False  # Allow other keys
                
            # Your existing Enter key handling when AI is not writing
            if event.key() in (Qt.Key_Return, Qt.Key_Enter):
                if event.modifiers() == Qt.ShiftModifier:
                    return False  # Allow Shift+Enter for new line
                else:
                    self._send_message()
                    return True
                    
        return super().eventFilter(obj, event)









    def _handle_send_stop_button(self):
        """Handle both send and stop functionality"""
        if self.is_ai_writing:
            if self.streaming_active:
                # Stop streaming (existing code)
                self._stop_ai_writing()
            else:
                # Set flag to cancel non-streaming
                self.cancel_non_streaming = True
                print("🛑 Cancelling non-streaming request...")
                # Could also show user feedback
                if hasattr(self, 'input_text'):
                    self.input_text.setPlaceholderText("Cancelling...")
        else:
            # Send message
            self._send_message()




        
      
    def _disable_all_bubble_interactions(self):
        """Disable all interaction buttons in chat bubbles"""
        for bubble_widget in self.bubble_widgets.values():
            if hasattr(bubble_widget, '_disable_interactions'):
                bubble_widget._disable_interactions()
            else:
                # Fallback: disable the widget entirely
                bubble_widget.setEnabled(False)
                
    def _enable_all_bubble_interactions(self):
        """Re-enable all interaction buttons in chat bubbles"""
        for bubble_widget in self.bubble_widgets.values():
            if hasattr(bubble_widget, '_enable_interactions'):
                bubble_widget._enable_interactions()
            else:
                # Fallback: re-enable the widget
                bubble_widget.setEnabled(True)
                
    def _show_ai_writing_indicator(self):
        """Show visual indicator that AI is writing"""
        # Optional: Add a subtle indicator like changing window title
        original_title = self.windowTitle()
        if not original_title.endswith(" - AI Writing..."):
            self.setWindowTitle(f"{original_title} - AI Writing...")
            
    def _hide_ai_writing_indicator(self):
        """Hide AI writing indicator"""
        # Remove the AI writing indicator from title
        title = self.windowTitle()
        if title.endswith(" - AI Writing..."):
            self.setWindowTitle(title.replace(" - AI Writing...", ""))
            


















    def _toggle_always_on_top(self):
        """Toggle always on top state for the chat window"""
        try:
            self.always_on_top = not self.always_on_top
            
            # Apply the pin status directly
            if self.always_on_top:
                self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
            else:
                self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
            
            # Always show after changing flags
            self.show()
            self.raise_()
            self.activateWindow()
            
            # Update appearance and save (ChatWindow HAS these methods)
            self._update_pin_button_appearance()
            self._save_window_state()
            
        except Exception as e:
            print(f"Error toggling always on top: {e}")
            # Revert state on error
            self.always_on_top = not self.always_on_top

    def _keep_window_on_top(self):
        """Keep chat window on top by raising it when needed"""
        if (self.always_on_top and 
            self.isVisible() and 
            not self.isMinimized() and 
            QApplication.activeWindow() != self):
            
            self.raise_()

    def _save_window_state(self):
        """Save chat window state including pin status (async to prevent lag)"""
        try:
            app_data_dir = get_app_data_dir()
            state_file = app_data_dir / "characters" / self.character.name / f"chat_window_state_{self.character.name}.json"
            
            state = {
                "geometry": {
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                },
                "always_on_top": getattr(self, 'always_on_top', False)
            }
            
            # ✅ Save asynchronously to prevent UI lag
            import threading
            def save_async():
                try:
                    with open(state_file, 'w') as f:
                        json.dump(state, f, indent=2)
                except Exception as e:
                    print(f"Error saving chat window state: {e}")
            
            threading.Thread(target=save_async, daemon=True).start()
                
        except Exception as e:
            print(f"Error preparing chat window state: {e}")

    def _load_window_state(self):
        """Load chat window state including pin status"""
        try:
            app_data_dir = get_app_data_dir()
            state_file = app_data_dir / "characters" / self.character.name / f"chat_window_state_{self.character.name}.json"
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                # Restore position
                if "geometry" in state:
                    self.move(state["geometry"]["x"], state["geometry"]["y"])
                    
                # FIXED: Don't toggle, just set and apply directly
                if "always_on_top" in state:
                    self.always_on_top = state["always_on_top"]
                    QTimer.singleShot(100, self._apply_pin_status)
                    QTimer.singleShot(150, self._update_pin_button_appearance)
                    
        except Exception as e:
            print(f"Error loading chat window state: {e}")





    def _get_background_cache_key(self):
        """Generate cache key for current background settings"""
        if not self.chat_settings.background_image_path:
            return None
        
        try:
            # Include image path, scale, offsets, and background color in key
            key_data = (
                self.chat_settings.background_image_path,
                self.chat_settings.bg_image_scale,
                self.chat_settings.bg_image_offset_x,  
                self.chat_settings.bg_image_offset_y,
                self.chat_settings.background_color,
                self.chat_area.width() if hasattr(self, 'chat_area') else 350,
                self.chat_area.height() if hasattr(self, 'chat_area') else 500
            )
            return str(key_data)
        except:
            return None



    def _apply_cached_background(self, cache_path):
        """Apply background from cache file (instant)"""
        try:
            # Simple path conversion for Qt
            bg_path = cache_path.replace('\\', '/')
            
            # Apply stylesheet
            self.chat_area.setStyleSheet(f"""
                QScrollArea {{
                    background-image: url("{bg_path}");
                    background-position: center center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: rgba(102, 102, 102, 180);
                    min-height: 30px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: rgba(85, 85, 85, 200);
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
            
            # Force update
            self.chat_area.update()
            QCoreApplication.processEvents()
            
        except Exception as e:
            print(f"❌ Error applying cached background: {e}")
            self._apply_background_color()

    def _apply_image_background_stylesheet(self):
        """Apply background image - IMPROVED MULTIPLE CALL PREVENTION"""
        
        # Enhanced prevention of multiple simultaneous applications
        if hasattr(self, '_applying_background') and self._applying_background:
            print("🔄 Background already being applied, skipping...")
            return
        
        # Check if background was recently applied (within last 2 seconds)
        current_time = time.time()
        if (hasattr(self, '_last_bg_apply_time') and 
            current_time - self._last_bg_apply_time < 2.0):
            print("🔄 Background recently applied, skipping...")
            return
        
        self._applying_background = True
        self._last_bg_apply_time = current_time
        
        try:
            # **STEP 1: Check if we can use existing background file**
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.character.name
            bg_file = char_dir / "current_background.png"
            
            # Check if background file exists and is current
            if (bg_file.exists() and 
                self._is_background_current(bg_file) and 
                not getattr(self, '_background_applied', False)):
                
                print("⚡ Using existing background file (instant)")
                self._apply_background_file_instant(str(bg_file))
                return
            
            # **STEP 2: Generate background only if needed**
            print("🔄 Generating background...")
            
            # Load image
            original_pixmap = QPixmap(self.chat_settings.background_image_path)
            if original_pixmap.isNull():
                print(f"❌ Failed to load: {self.chat_settings.background_image_path}")
                self._apply_background_color()
                return
            
            # Wait for chat area to be ready
            if not hasattr(self, 'chat_area') or not self.chat_area.isVisible():
                QTimer.singleShot(50, self._apply_image_background_stylesheet)
                return
            
            # Get chat area size
            chat_size = self.chat_area.size()
            if chat_size.width() <= 0 or chat_size.height() <= 0:
                chat_size = QSize(350, 500)
            
            # Create background
            bg_width = chat_size.width() + 10
            bg_height = chat_size.height() + 10
            
            scale = getattr(self.chat_settings, 'bg_image_scale', 1.0)
            scaled_width = int(original_pixmap.width() * scale)
            scaled_height = int(original_pixmap.height() * scale)
            
            scaled_pixmap = original_pixmap.scaled(
                scaled_width, scaled_height,
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            bg_pixmap = QPixmap(bg_width, bg_height)
            bg_pixmap.fill(QColor(self.chat_settings.background_color or "#F0F4F8"))
            
            painter = QPainter(bg_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            offset_x = getattr(self.chat_settings, 'bg_image_offset_x', 0)
            offset_y = getattr(self.chat_settings, 'bg_image_offset_y', 0)
            x = (bg_width - scaled_width) // 2 + offset_x
            y = (bg_height - scaled_height) // 2 + offset_y
            
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            
            # Save background
            char_dir.mkdir(parents=True, exist_ok=True)
            if bg_pixmap.save(str(bg_file)):
                print(f"✅ Background saved: {bg_file}")
                self._apply_background_file_instant(str(bg_file))
            else:
                print("❌ Failed to save background")
                self._apply_background_color()
            
        except Exception as e:
            print(f"❌ Background error: {e}")
            self._apply_background_color()
        finally:
            self._applying_background = False


    def _is_background_current(self, bg_file):
        """Check if background file is current (simple version)"""
        try:
            # Check if file is recent (within last hour) and source image exists
            if not bg_file.exists():
                return False
            
            # Check if source image still exists
            if not os.path.exists(self.chat_settings.background_image_path):
                return False
            
            # File exists and source exists - consider it current
            return True
            
        except:
            return False

    def _apply_background_file_instant(self, bg_path):
        """Apply background instantly without clearing first"""
        try:
            if not os.path.exists(bg_path):
                print(f"❌ Background file missing: {bg_path}")
                self._apply_background_color()
                return
            
            # **NO CLEARING - DIRECT APPLICATION**
            qt_path = bg_path.replace('\\', '/')
            
            # Apply stylesheet directly without clearing first
            self.chat_area.setStyleSheet(f"""
                QScrollArea {{
                    background-image: url("{qt_path}");
                    background-position: center center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: rgba(102, 102, 102, 180);
                    min-height: 30px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: rgba(85, 85, 85, 200);
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
            
            # Mark as applied
            self._background_applied = True
            self._current_bg_file = bg_path
            
            print(f"⚡ Background applied instantly!")
            
        except Exception as e:
            print(f"❌ Error applying background: {e}")
            self._apply_background_color()



    def _apply_background_file(self, bg_path):
        """Apply background from file - SIMPLE AND RELIABLE"""
        try:
            # Ensure file exists
            if not os.path.exists(bg_path):
                print(f"❌ Background file not found: {bg_path}")
                self._apply_background_color()
                return
            
            # Convert path for Qt (forward slashes)
            qt_path = bg_path.replace('\\', '/')
            
            print(f"🖼️ Applying background: {qt_path}")
            
            # Apply stylesheet
            self.chat_area.setStyleSheet(f"""
                QScrollArea {{
                    background-image: url("{qt_path}");
                    background-position: center center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: rgba(102, 102, 102, 180);
                    min-height: 30px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: rgba(85, 85, 85, 200);
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
            
            # Force immediate update
            self.chat_area.update()
            self.chat_area.repaint()
            QCoreApplication.processEvents()
            
            print(f"✅ Background applied successfully!")
            
        except Exception as e:
            print(f"❌ Error applying background file: {e}")
            self._apply_background_color()




    def _apply_background_file(self, bg_path):
        """Apply background from file - SIMPLE AND RELIABLE"""
        try:
            # Ensure file exists
            if not os.path.exists(bg_path):
                print(f"❌ Background file not found: {bg_path}")
                self._apply_background_color()
                return
            
            # Convert path for Qt (forward slashes)
            qt_path = bg_path.replace('\\', '/')
            
            print(f"🖼️ Applying background: {qt_path}")
            
            # Apply stylesheet
            self.chat_area.setStyleSheet(f"""
                QScrollArea {{
                    background-image: url("{qt_path}");
                    background-position: center center;
                    background-repeat: no-repeat;
                    background-attachment: fixed;
                    border: none;
                }}
                QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 0px;
                }}
                QScrollBar::handle:vertical {{
                    background: rgba(102, 102, 102, 180);
                    min-height: 30px;
                    border-radius: 4px;
                }}
                QScrollBar::handle:vertical:hover {{
                    background: rgba(85, 85, 85, 200);
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
                QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                    background: transparent;
                }}
            """)
            
            # Force immediate update
            self.chat_area.update()
            self.chat_area.repaint()
            QCoreApplication.processEvents()
            
            print(f"✅ Background applied successfully!")
            
        except Exception as e:
            print(f"❌ Error applying background file: {e}")
            self._apply_background_color()

    # ALSO UPDATE _apply_chat_background to be more reliable:

    def _apply_chat_background(self):
        """Apply background - PREVENT MULTIPLE CALLS VERSION"""
        # Prevent multiple calls during window setup
        if self._applying_background:
            print("🔄 Background application already in progress...")
            return
        
        try:
            if self.chat_settings.background_type == "image" and self.chat_settings.background_image_path:
                # Resolve path
                bg_path = self.chat_settings.background_image_path
                
                if not os.path.isabs(bg_path):
                    app_data_dir = get_app_data_dir()
                    char_dir = app_data_dir / "characters" / self.character.name
                    bg_path = str(char_dir / bg_path)
                
                if os.path.exists(bg_path):
                    self.chat_settings.background_image_path = bg_path
                    self._apply_image_background_stylesheet()
                else:
                    print(f"❌ Background not found: {bg_path}")
                    self._apply_background_color()
            else:
                self._apply_background_color()
                
        except Exception as e:
            print(f"❌ Error in background application: {e}")
            self._apply_background_color()


    def _setup_initial_background(self):
        """Apply background during window creation (called once)"""
        try:
            # Apply background immediately during setup
            if (hasattr(self, 'chat_settings') and 
                self.chat_settings.background_type == "image" and 
                self.chat_settings.background_image_path):
                
                print("🚀 Setting up initial background...")
                self._apply_chat_background()
            else:
                self._apply_background_color()
                
        except Exception as e:
            print(f"❌ Error setting up initial background: {e}")
            self._apply_background_color()


    def _apply_background_color(self):
        """Apply solid background color using stylesheet"""
        bg_color = self.chat_settings.background_color
        if not bg_color or bg_color == "":
            bg_color = "#F0F4F8"
        
        # Clear any palette settings
        self.chat_area.setAutoFillBackground(False)
        
        # Use stylesheet for color (consistent with version 02)
        self.chat_area.setStyleSheet(f"""
            QScrollArea {{
                background-color: {bg_color};
                border: none;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(102, 102, 102, 180);
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(85, 85, 85, 200);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)
        
        # Force update
        self.chat_area.repaint()








    def mousePressEvent(self, event):
        """Handle mouse press for window dragging - UPDATED"""
        if event.button() == Qt.LeftButton:
            # Check if click is on title bar
            if event.position().y() <= 30:
                self.drag_position = event.globalPosition().toPoint() - self.pos()
        
        # NEW: Handle transparency for both time and focus modes
        if self.chat_settings.window_transparency_enabled:
            if self.chat_settings.window_transparency_mode == "time":
                self._restart_transparency_timer()
            elif self.chat_settings.window_transparency_mode == "focus":
                # Remove transparency on click (user is interacting)
                self._remove_transparency()
            
    def mouseMoveEvent(self, event):
        """Handle window dragging"""
        if self.drag_position and event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        self.drag_position = None

    
    def _minimize_window(self):
        """Minimize window"""
        # Create minimize bar
        self.hide()
        self._create_minimize_bar()
    
    def _create_minimize_bar(self):
        """Create minimize bar with character-specific colors"""
        if hasattr(self, 'minimize_bar') and self.minimize_bar:
            self.minimize_bar.show()
            return
        
        # DETERMINE WHICH COLORS TO USE: Character-specific or Global
        primary_color = app_colors.PRIMARY
        secondary_color = app_colors.SECONDARY
        
        # Check if current character has custom colors enabled
        if (hasattr(self, 'character') and 
            self.character and 
            getattr(self.character, 'use_character_colors', False)):
            
            # Use character-specific colors
            char_primary = getattr(self.character, 'character_primary_color', '')
            char_secondary = getattr(self.character, 'character_secondary_color', '')
            
            if char_primary and char_secondary:
                primary_color = char_primary
                secondary_color = char_secondary
        
        self.minimize_bar = QWidget()
        self.minimize_bar.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.minimize_bar.setFixedSize(200, 40)
        self.minimize_bar.setStyleSheet(f"background-color: {primary_color};")
        
        # Position at same location as chat window
        self.minimize_bar.move(self.pos())
        
        # Layout
        layout = QHBoxLayout(self.minimize_bar)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Title
        title = QLabel(f" {self.character.name}")
        title.setStyleSheet(f"color: {secondary_color}; font-weight: bold; font-size: 9pt;")
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Restore button
        restore_btn = QPushButton("⛶")
        restore_btn.setFixedSize(25, 25)
        restore_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {secondary_color};
                border: none;
                font-size: 12pt;
                font-weight: bold;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 255, 255, 0.3);
            }}
        """)
        restore_btn.clicked.connect(self._restore_window)
        layout.addWidget(restore_btn)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(25, 25)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {secondary_color};
                border: none;
                font-size: 14pt;
                font-weight: bold;
                border-radius: 3px;
                padding: -3px 0px 0px 0px;  /* Added padding adjustment */
            }}
            QPushButton:hover {{
                background-color: rgba(255, 0, 0, 0.3);
            }}
            QPushButton:pressed {{
                background-color: rgba(255, 0, 0, 0.5);
            }}
        """)
        close_btn.clicked.connect(self._close_from_minimize)
        layout.addWidget(close_btn)
        
        # Make draggable
        self.minimize_bar.mousePressEvent = lambda e: setattr(self.minimize_bar, 'drag_pos', e.globalPosition().toPoint() - self.minimize_bar.pos())
        self.minimize_bar.mouseMoveEvent = lambda e: self.minimize_bar.move(e.globalPosition().toPoint() - self.minimize_bar.drag_pos) if hasattr(self.minimize_bar, 'drag_pos') else None
        self.minimize_bar.mouseReleaseEvent = lambda e: setattr(self.minimize_bar, 'drag_pos', None)
        
        self.minimize_bar.show()
    
    def _restore_window(self):
        """Restore from minimize"""
        if hasattr(self, 'minimize_bar'):
            self.minimize_bar.hide()
        self.show()
        self.raise_()
        self.activateWindow()
    
    def _close_from_minimize(self):
        """Close from minimize bar"""
        if hasattr(self, 'minimize_bar'):
            self.minimize_bar.close()
        self.close()

    def _show_settings_menu(self):
        """Show settings menu with user profile selector - UPDATED for user names"""
        menu = QMenu(self)
        
        menu.addAction("Chat Appearance", self._open_chat_settings)
        menu.addAction("Bubble Settings", self._open_bubble_settings)
        menu.addAction("Check-in Settings", self._show_checkin_settings)
        
        # User Profile Selection submenu with user name support
        profile_menu = menu.addMenu("👤 User Profile")
        
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'user_profile_manager'):
                manager = parent.user_profile_manager
                
                # Force reload settings
                manager.settings = manager._load_settings()
                profiles = manager.settings.profiles
                
                print(f"Building profile menu with {len(profiles)} profiles")
                
                if profiles:
                    # Global profile option
                    global_action = profile_menu.addAction("🌐 Use Global Profile")
                    global_action.setCheckable(True)
                    global_action.setChecked(self.selected_user_profile is None)
                    global_action.triggered.connect(lambda: self._select_user_profile(None))
                    
                    profile_menu.addSeparator()
                    
                    # Individual profiles - SHOW USER NAMES
                    for profile in profiles:
                        print(f"Adding profile to menu: {profile.user_name} ({profile.name})")
                        
                        # Display user name, but store full profile object
                        display_text = f"👤 {profile.user_name}"
                        if profile.user_name != profile.name:
                            display_text += f" ({profile.name})"
                        
                        action = profile_menu.addAction(display_text)
                        action.setCheckable(True)
                        
                        # Check if this profile is selected (compare by folder name)
                        is_checked = bool(
                            self.selected_user_profile and 
                            self.selected_user_profile.name == profile.name
                        )
                        action.setChecked(is_checked)
                        
                        # Pass the full profile object
                        action.triggered.connect(lambda checked=False, p=profile: self._select_user_profile(p))
                    
                    profile_menu.addSeparator()
                    profile_menu.addAction("Manage Profiles...", lambda: parent._open_user_profiles())
                else:
                    profile_menu.addAction("(No profiles available)").setEnabled(False)
                    profile_menu.addSeparator()
                    profile_menu.addAction("Create Profile...", lambda: parent._open_user_profiles())
            else:
                profile_menu.addAction("(Profile system not available)").setEnabled(False)
        except Exception as e:
            print(f"Error building profile menu: {e}")
            profile_menu.addAction("(Error loading profiles)").setEnabled(False)
        
        menu.addAction("Scheduled Messages", self._open_dialog_manager)

        menu.addSeparator()
        menu.addAction("Clear History", self._clear_history)
        menu.addAction("Export Chat", self._export_chat)
        

        
        # Get button position
        btn = self.sender()
        menu.exec(btn.mapToGlobal(QPoint(0, btn.height())))

    def _refresh_profile_display(self):
        """Refresh the profile display in title bar"""
        if hasattr(self, 'title_bar'):
            # Get the title label (you might need to store a reference to it)
            character_display_name = getattr(self.character, 'display_name', self.character.name)
            
            # Get effective profile name for display
            effective_profile = self._get_effective_user_profile()
            if self.selected_user_profile:
                profile_indicator = f" ({self.selected_user_profile.name})"
            elif effective_profile:
                profile_indicator = f" (Global: {effective_profile.name})"
            else:
                profile_indicator = " (No Profile)"
            
            # Update title label text
            new_title = f" Chat with {character_display_name}{profile_indicator}"
            
            # Find and update the title label
            for child in self.title_bar.children():
                if isinstance(child, QLabel):
                    child.setText(new_title)
                    break

    def _debug_profile_system(self):
        """Debug method to check profile system"""
        print("=== PROFILE DEBUG ===")
        print(f"Has parent: {self.parent() is not None}")
        if self.parent():
            print(f"Parent type: {type(self.parent())}")
            print(f"Has user_profile_manager: {hasattr(self.parent(), 'user_profile_manager')}")
            if hasattr(self.parent(), 'user_profile_manager'):
                manager = self.parent().user_profile_manager
                print(f"Manager profiles count: {len(manager.settings.profiles)}")
                print(f"Active profile name: {manager.settings.active_profile_name}")
                for i, profile in enumerate(manager.settings.profiles):
                    print(f"  Profile {i}: {profile.name} (active: {profile.is_active})")
        
        print(f"Selected user profile: {self.selected_user_profile}")
        effective = self._get_effective_user_profile()
        print(f"Effective profile: {effective.name if effective else None}")
        print("===================")
    
    def _save_selected_profile(self):
        """Save the selected user profile for this character"""
        try:
            app_data_dir = get_app_data_dir()
            profile_file = app_data_dir / "characters" / self.character.name / "selected_profile.json"
            profile_file.parent.mkdir(parents=True, exist_ok=True)
            
            profile_data = {
                "selected_profile_name": self.selected_user_profile.name if self.selected_user_profile else None
            }
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
                
            print(f"Saved selected profile for {self.character.name}: {profile_data['selected_profile_name']}")
            
        except Exception as e:
            print(f"Error saving selected profile: {e}")
            
    def _select_user_profile(self, profile: Optional[UserProfile]):
        """Select user profile for this chat - UPDATED for user names"""
        print(f"Selecting profile: {profile.user_name if profile else 'None'} (folder: {profile.name if profile else 'None'})")
        
        self.selected_user_profile = profile
        
        # Save the selection to file
        self._save_selected_profile()
        
        # Determine the message and profile display info

        

        
        # Update the window title immediately
        self._update_window_title()
        
        # Refresh display to update any visible names
        self._refresh_display()




    def _update_window_title(self):
        """Update the chat window title with current profile info - UPDATED for user names"""
        try:
            character_display_name = getattr(self.character, 'display_name', self.character.name)
            
            # Get effective profile name for display
            effective_profile = self._get_effective_user_profile()
            if self.selected_user_profile:
                profile_indicator = f" ({self.selected_user_profile.user_name})"
            elif effective_profile:
                profile_indicator = f" (Global: {effective_profile.user_name})"
            else:
                profile_indicator = " (No Profile)"
            
            new_title = f" Chat with {character_display_name}{profile_indicator}"
            
            # Find and update the title label in the title bar
            if hasattr(self, 'title_bar'):
                for child in self.title_bar.children():
                    if isinstance(child, QLabel) and " Chat with " in child.text():
                        child.setText(new_title)
                        break
            
            print(f"Updated window title to: {new_title}")
            
        except Exception as e:
            print(f"Error updating window title: {e}")


    def _get_effective_user_profile(self) -> Optional[UserProfile]:
        """Get the effective user profile (selected or global) with validation - UNCHANGED"""
        try:
            # First check if we have a selected profile for this chat
            if self.selected_user_profile:
                # Validate that the selected profile still exists
                parent = self.parent()
                if parent and hasattr(parent, 'user_profile_manager'):
                    manager = parent.user_profile_manager
                    for profile in manager.settings.profiles:
                        if profile.name == self.selected_user_profile.name:
                            return self.selected_user_profile
                    # Selected profile no longer exists, clear it
                    print(f"Selected profile '{self.selected_user_profile.name}' no longer exists, clearing")
                    self.selected_user_profile = None
            
            # Get global profile
            parent = self.parent()
            if parent and hasattr(parent, 'user_profile_manager'):
                manager = parent.user_profile_manager
                
                # Reload settings to ensure we have fresh data
                manager.settings = manager._load_settings()
                
                active_profile = manager.get_active_profile()
                if active_profile:
                    return active_profile
                elif manager.settings.profiles:
                    # No active profile set, but profiles exist - set first one as active
                    manager.set_active_profile(manager.settings.profiles[0].name)
                    return manager.settings.profiles[0]
            
            print("No effective profile found")
            return None
            
        except Exception as e:
            print(f"Error in _get_effective_user_profile: {e}")
            return None


# Add helper method to create chat bubble:
    def _create_chat_bubble(self, message_obj: ChatMessage) -> ChatBubble:
        """Create a chat bubble widget"""
        # Get character display name
        character_name = self.character.display_name if hasattr(self.character, 'display_name') else self.character.name
        
        # Get user profile
        user_profile = self._get_effective_user_profile()
        user_name = user_profile.user_name if user_profile else "User"
        
        # Get siblings for navigation
        siblings = self.chat_tree.get_siblings(message_obj.id)
        has_siblings = len(siblings) > 1
        sibling_position = None
        
        if has_siblings:
            sibling_index = siblings.index(message_obj.id)
            sibling_position = (sibling_index, len(siblings))
        
        # Calculate indent level
        indent_level = 0
        if message_obj.parent_id:
            current_id = message_obj.parent_id
            while current_id:
                indent_level += 1
                parent = self.chat_tree.messages.get(current_id)
                current_id = parent.parent_id if parent else None
        
        # Determine colors
        primary_color = app_colors.PRIMARY
        secondary_color = app_colors.SECONDARY
        
        if (getattr(self.character, 'use_character_colors', False) and
            hasattr(self.character, 'character_primary_color') and
            hasattr(self.character, 'character_secondary_color') and
            self.character.character_primary_color and
            self.character.character_secondary_color):
            primary_color = self.character.character_primary_color
            secondary_color = self.character.character_secondary_color
        
        # Create bubble
        bubble = ChatBubble(
            message_obj,
            self.character,
            self.user_icon,
            self.character_icon,
            has_siblings,
            sibling_position,
            indent_level,
            character_name,
            user_name,
            primary_color,
            secondary_color
        )
        
        # Connect signals
        bubble.edit_requested.connect(self._handle_edit_message)
        bubble.retry_requested.connect(self._handle_retry_message)
        bubble.delete_requested.connect(self._handle_delete_message)
        bubble.navigate_sibling.connect(self._handle_navigate_sibling)
        
        return bubble







        
    def _send_message(self):
        """Send user message without max history limit"""
        if self.is_ai_writing:
            return
            
        message = self.input_text.toPlainText().strip()
        if not message:
            return
        
        # Block check-ins while sending
        self._block_checkins_temporarily()
        
        # Check for external API commands
        if self._process_external_api_command(message):
            self.input_text.clear()
            return
        
        # Clear input
        self.input_text.clear()
        
        # Record user message for check-in system
        self._record_user_message()

        # Create user message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        user_msg = ChatMessage("user", message, timestamp)
        
        # Add to tree
        user_msg_id = self.chat_tree.add_message(user_msg)
        
        # NO MORE MAX HISTORY ENFORCEMENT!
        # Just add the bubble
        self._add_bubble(user_msg)
            
        if hasattr(self, 'input_text'):
            self.input_text.setPlaceholderText("AI is thinking...")
        
        # Queue for AI response
        self.message_queue.put((message, user_msg.id))
        
        # Save history
        self._save_chat_history()


    def _block_checkins_temporarily(self):
        """Temporarily block check-ins when user is actively sending messages"""
        # Set a flag to block check-ins for the next 3 minutes
        self._checkin_blocked_until = datetime.now() + timedelta(minutes=3)
        print(f"🚫 Check-ins blocked until {self._checkin_blocked_until.strftime('%H:%M:%S')}")

    def _send_checkin_message(self):
        """Send proactive check-in message with flash - FIXED VERSION"""
        try:
            # 🆕 CHECK IF CHECKINS ARE TEMPORARILY BLOCKED
            if hasattr(self, '_checkin_blocked_until'):
                if datetime.now() < self._checkin_blocked_until:
                    print(f"🚫 Check-in blocked - user recently active")
                    return
            
            # 🆕 DOUBLE-CHECK USER ISN'T ACTIVELY CHATTING
            if self._is_user_actively_chatting():
                print(f"🚫 Check-in cancelled - user is actively chatting")
                return
            
            prompt = self._generate_checkin_prompt()
            
            # Send as character with flash
            self._send_reminder_as_character(prompt, is_checkin=True)
            
            if hasattr(self, 'last_checkin_time'):
                self.last_checkin_time = datetime.now()
            
            # Flash the window
            self.flash_window_signal.emit()
            
            print(f"✅ Sent proactive check-in with flash")
            
        except Exception as e:
            print(f"❌ Error sending check-in message: {e}")
    def _get_recent_checkin_context(self) -> str:
        """Get recent message history for check-in context - FIXED VERSION"""
        try:
            messages = []
            
            # Get recent messages from chat tree (last 3 messages)
            if hasattr(self, 'chat_tree') and self.chat_tree:
                # Get active conversation path - this gives us all messages in order
                active_messages = self.chat_tree.get_active_conversation_path()
                
                # Get last 3 messages for context
                recent_messages = active_messages[-3:] if len(active_messages) >= 3 else active_messages
                
                for msg in recent_messages:
                    role_name = "User" if msg.role == "user" else self.character.name
                    messages.append(f"{role_name}: {msg.content[:100]}...")
            
            return "\n".join(messages) if messages else "No recent conversation"
            
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return "No recent conversation"

    def _get_conversation_history_for_ai(self, limit: int = 5) -> list:
        """Get recent conversation history for AI context - FIXED"""
        try:
            messages = []
            if hasattr(self, 'chat_tree') and self.chat_tree:
                # Use the proper chat tree structure
                active_messages = self.chat_tree.get_active_conversation_path()
                
                # Get recent messages up to limit
                recent_messages = active_messages[-limit:] if limit > 0 else active_messages
                
                for msg in recent_messages:
                    messages.append({
                        "role": msg.role,
                        "content": msg.content
                    })
            
            return messages
        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []







    def _check_and_apply_focus_transparency(self):
        """Check if window really lost focus and apply transparency"""
        if (self.chat_settings.window_transparency_enabled and 
            self.chat_settings.window_transparency_mode == "focus" and
            not self.isActiveWindow() and 
            not self.hasFocus()):
            self._apply_transparency()
 
    
    def _handle_input_activity(self):
        """Handle input field activity for transparency"""
        if self.chat_settings.window_transparency_enabled:
            if self.chat_settings.window_transparency_mode == "time":
                self._restart_transparency_timer()
            elif self.chat_settings.window_transparency_mode == "focus":
                # Remove transparency when user is typing
                self._remove_transparency()



    # Add these methods to your main_window.py file

    def _update_bubble_completely_silent(self, message):
        """Update existing bubble with ABSOLUTE ZERO flicker"""
        if message.id not in self.bubble_widgets:
            return
        
        bubble = self.bubble_widgets[message.id]
        
        # DISABLE all updates on the bubble widget itself
        bubble.setUpdatesEnabled(False)
        if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
            bubble.bubble_label.setUpdatesEnabled(False)
            bubble.bubble_label.blockSignals(True)
        
        try:
            # Check if content actually changed
            content_changed = (
                not hasattr(bubble, 'message_obj') or 
                bubble.message_obj.content != message.content
            )
            
            # Check if active state changed
            active_changed = (
                not hasattr(bubble, 'message_obj') or 
                bubble.message_obj.is_active != message.is_active
            )
            
            if content_changed:
                # Update the bubble's internal message reference
                bubble.message_obj = message
                
                # Format text only once
                formatted_text = bubble._format_text(message.content)
                
                # Update text WITHOUT triggering repaint
                if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
                    bubble.bubble_label.setText(formatted_text)
            
            if active_changed:
                # Update opacity without triggering style recalculation
                self._update_bubble_opacity_silent(bubble, message.is_active)
                # Update the message object
                bubble.message_obj.is_active = message.is_active
            
            # Update navigation if siblings changed
            siblings = self.chat_tree.get_siblings(message.id)
            if len(siblings) != getattr(bubble, '_last_sibling_count', 0):
                bubble._last_sibling_count = len(siblings)
                self._update_bubble_navigation_silent(bubble, message)
        
        except Exception as e:
            print(f"Error updating bubble {message.id}: {e}")
        finally:
            # Re-enable this bubble even if there was an error
            bubble.setUpdatesEnabled(True)
            if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
                bubble.bubble_label.setUpdatesEnabled(True)
                bubble.bubble_label.blockSignals(False)

    def _update_bubble_opacity_silent(self, bubble, is_active):
        """Update bubble opacity without any visual updates"""
        if not hasattr(bubble, 'bubble_label') or not bubble.bubble_label:
            return
        
        opacity = 1.0 if is_active else 0.6
        
        # Get current style and modify opacity without triggering updates
        current_style = bubble.bubble_label.styleSheet()
        
        # Use regex to replace existing opacity or add new one
        import re
        if 'opacity:' in current_style:
            new_style = re.sub(r'opacity:\s*[\d.]+;?', f'opacity: {opacity};', current_style)
        else:
            # Add opacity to existing style
            if current_style.strip().endswith('}'):
                new_style = current_style.rstrip('}').rstrip() + f' opacity: {opacity}; }}'
            else:
                new_style = current_style + f' opacity: {opacity};'
        
        # Block all signals and updates
        bubble.bubble_label.blockSignals(True)
        bubble.bubble_label.setUpdatesEnabled(False)
        bubble.bubble_label.setStyleSheet(new_style)
        bubble.bubble_label.blockSignals(False)

    def _update_bubble_navigation_silent(self, bubble, message):
        """Update navigation arrows silently"""
        siblings = self.chat_tree.get_siblings(message.id)
        has_siblings = len(siblings) > 1
        
        if has_siblings:
            sibling_index = siblings.index(message.id)
            sibling_position = (sibling_index, len(siblings))
            
            # Update bubble's navigation state without visual updates
            bubble.has_siblings = has_siblings
            bubble.sibling_position = sibling_position
            
            # If bubble has navigation controls, update them silently
            if hasattr(bubble, '_update_navigation_controls_silent'):
                bubble._update_navigation_controls_silent()
        else:
            bubble.has_siblings = False
            bubble.sibling_position = None
            
            # Remove navigation widget if it exists
            if hasattr(bubble, '_update_navigation_controls_silent'):
                bubble._update_navigation_controls_silent()

    def _recreate_single_bubble_silent(self, message):
        """Recreate a single bubble to fix navigation issues"""
        if message.id in self.bubble_widgets:
            # Remove old bubble
            old_bubble = self.bubble_widgets[message.id]
            self.chat_layout.removeWidget(old_bubble)
            old_bubble.deleteLater()
            del self.bubble_widgets[message.id]
            
            # Create new bubble with correct navigation
            self._add_single_bubble_completely_silent(message)

    def _add_single_bubble_completely_silent(self, message_obj):
        """Add bubble with ZERO visual updates during creation"""
        if message_obj.id in self.bubble_widgets:
            return
        
        # Create bubble using existing method
        bubble = self._create_bubble_widget(message_obj)
        
        # Disable updates BEFORE adding to layout
        bubble.setUpdatesEnabled(False)
        if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
            bubble.bubble_label.setUpdatesEnabled(False)
        
        # Add to layout and tracking
        self.chat_layout.addWidget(bubble)
        self.bubble_widgets[message_obj.id] = bubble
        
        # Note: Updates will be re-enabled by the calling function

    def _remove_bubble_completely_silent(self, message_id: str):
        """Remove bubble with ZERO visual disruption"""
        if message_id not in self.bubble_widgets:
            return
        
        bubble = self.bubble_widgets[message_id]
        
        # Disable all updates first
        bubble.setUpdatesEnabled(False)
        if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
            bubble.bubble_label.setUpdatesEnabled(False)
        
        # Hide immediately without triggering repaint
        bubble.setVisible(False)
        
        # Remove from layout silently
        self.chat_layout.removeWidget(bubble)
        
        # Schedule for deletion after refresh completes
        bubble.deleteLater()
        del self.bubble_widgets[message_id]

    def _smart_refresh_for_navigation(self, affected_messages):
        """Smart refresh that only updates affected bubbles during navigation"""
        try:
            # Save scroll position
            scroll_bar = self.chat_area.verticalScrollBar()
            was_at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 10
            saved_scroll = scroll_bar.value() if not was_at_bottom else None
            
            # Freeze updates
            self.setUpdatesEnabled(False)
            self.chat_area.setUpdatesEnabled(False)
            
            for message in affected_messages:
                if message.id in self.bubble_widgets:
                    # Just update the existing bubble
                    self._update_bubble_completely_silent(message)
                else:
                    # Add new bubble if it doesn't exist
                    self._add_single_bubble_completely_silent(message)
            
            # Remove bubbles that should no longer be visible
            current_active_ids = {msg.id for msg in self._collect_all_active_messages()}
            for msg_id in list(self.bubble_widgets.keys()):
                if msg_id not in current_active_ids:
                    self._remove_bubble_completely_silent(msg_id)
        
        finally:
            # Re-enable updates for all affected bubbles
            for message in affected_messages:
                if message.id in self.bubble_widgets:
                    bubble = self.bubble_widgets[message.id]
                    bubble.setUpdatesEnabled(True)
                    if hasattr(bubble, 'bubble_label') and bubble.bubble_label:
                        bubble.bubble_label.setUpdatesEnabled(True)
            
            # Re-enable main updates
            self.setUpdatesEnabled(True)
            self.chat_area.setUpdatesEnabled(True)
            
            # Force repaint
            self.chat_area.repaint()
            
            # Restore scroll position
            def restore_scroll():
                if was_at_bottom:
                    scroll_bar.setValue(scroll_bar.maximum())
                elif saved_scroll is not None:
                    scroll_bar.setValue(min(saved_scroll, scroll_bar.maximum()))
            
            QTimer.singleShot(1, restore_scroll)

    # MODIFIED HANDLER METHODS - Replace your existing methods with these:
    def _handle_navigate_sibling(self, message_obj: ChatMessage, direction: int):
        """TEST: Check if AI writing blocks work"""
        if self.is_ai_writing:
            print("❌ BLOCKED EDIT - AI is writing!")
            return
        print("✅ EDIT allowed")
        """OPTIMIZED: Handle sibling navigation with minimal updates"""
        siblings = self.chat_tree.get_siblings(message_obj.id)
        current_index = siblings.index(message_obj.id)
        new_index = current_index + direction
        
        if 0 <= new_index < len(siblings):
            # Collect affected messages before making changes
            old_branch_messages = self._collect_branch_messages(message_obj.id)
            
            # Activate new sibling branch
            new_sibling_id = siblings[new_index]
            self._activate_branch(new_sibling_id)
            
            # Collect new branch messages
            new_branch_messages = self._collect_branch_messages(new_sibling_id)
            
            # Combine affected messages using IDs to avoid duplicates
            affected_message_ids = set()
            affected_messages = []
            
            for msg in old_branch_messages + new_branch_messages:
                if msg.id not in affected_message_ids:
                    affected_message_ids.add(msg.id)
                    affected_messages.append(msg)
            
            # Use smart refresh instead of full refresh
            self._smart_refresh_for_navigation(affected_messages)
            self._save_chat_history()

    def _handle_edit_message(self, message_obj: ChatMessage):
        """TEST: Check if AI writing blocks work"""
        if self.is_ai_writing:
            print("❌ BLOCKED EDIT - AI is writing!")
            return
        print("✅ EDIT allowed")
        """OPTIMIZED: Handle message editing with individual bubble update"""
        dialog = MessageEditDialog(self, message_obj)
        if dialog.exec() and dialog.new_content:
            new_content = dialog.new_content.strip()
            
            # Create new branch
            new_message_id = self.chat_tree.edit_message(message_obj.id, new_content)
            
            # Reset bubble width cache for the new message
            new_message = self.chat_tree.messages.get(new_message_id)
            if new_message and hasattr(new_message, 'bubble_width'):
                new_message.bubble_width = None
            
            if message_obj.role == "user":
                # Collect ALL affected messages for user edits
                affected_messages = []
                
                # Add the new message
                if new_message:
                    affected_messages.append(new_message)
                
                # Add siblings for navigation update
                siblings = self.chat_tree.get_siblings(new_message_id)
                for sibling_id in siblings:
                    if sibling_id in self.chat_tree.messages:
                        affected_messages.append(self.chat_tree.messages[sibling_id])
                
                # If this message has children (assistant responses), we need to handle them
                if message_obj.children_ids:
                    # Deactivate old branch children
                    for child_id in message_obj.children_ids:
                        self._deactivate_message_and_descendants(child_id)
                    
                    # Remove old assistant response bubbles
                    for child_id in message_obj.children_ids:
                        if child_id in self.bubble_widgets:
                            self._remove_bubble_completely_silent(child_id)
                
                # Smart refresh only affected bubbles instead of full refresh
                self._smart_refresh_for_navigation(affected_messages)
                
                # Process with AI - use tuple format
                self.message_queue.put((new_content, new_message_id))
            else:
                # For assistant messages, just update the bubble
                if new_message:
                    affected_messages = [new_message]
                    
                    # Update siblings too
                    siblings = self.chat_tree.get_siblings(new_message_id)
                    for sibling_id in siblings:
                        if sibling_id in self.chat_tree.messages:
                            affected_messages.append(self.chat_tree.messages[sibling_id])
                    
                    self._smart_refresh_for_navigation(affected_messages)
            
            self._save_chat_history()

    def _handle_retry_message(self, message_obj: ChatMessage):
        """TEST: Check if AI writing blocks work"""
        if self.is_ai_writing:
            print("❌ BLOCKED EDIT - AI is writing!")
            return
        print("✅ EDIT allowed")
        """OPTIMIZED: Handle retry by creating a sibling response (like edit)"""
        if message_obj.role == "assistant":
            parent_id = message_obj.parent_id
            if parent_id:
                parent_message = self.chat_tree.messages.get(parent_id)
                if parent_message:
                    # Deactivate current response (but don't delete it)
                    message_obj.is_active = False
                    self.chat_tree._deactivate_branch(message_obj.id)
                    
                    # Collect affected messages for smart refresh
                    affected_messages = []
                    
                    # Update the current message bubble
                    if message_obj.id in self.bubble_widgets:
                        self._update_bubble_completely_silent(message_obj)
                        affected_messages.append(message_obj)
                    
                    # Update siblings for navigation
                    siblings = self.chat_tree.get_siblings(message_obj.id)
                    for sibling_id in siblings:
                        if sibling_id in self.chat_tree.messages:
                            sibling = self.chat_tree.messages[sibling_id]
                            affected_messages.append(sibling)
                            if sibling_id in self.bubble_widgets:
                                self._update_bubble_navigation_silent(
                                    self.bubble_widgets[sibling_id], 
                                    sibling
                                )
                    
                    # Smart refresh affected bubbles
                    if affected_messages:
                        self._smart_refresh_for_navigation(affected_messages)
                    
                    # Re-send to AI for a new sibling response
                    self.message_queue.put((parent_message.content, parent_id))
                    self._save_chat_history()

    def _handle_delete_message(self, message_obj: ChatMessage):
        """TEST: Check if AI writing blocks work"""
        if self.is_ai_writing:
            print("❌ BLOCKED EDIT - AI is writing!")
            return
        print("✅ EDIT allowed")
        """OPTIMIZED: Handle deletion with minimal refresh and preserved scroll"""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self, 
            "Delete Message", 
            f"Are you sure you want to delete this message?\n\n\"{message_obj.content[:100]}{'...' if len(message_obj.content) > 100 else ''}\"",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Save scroll position BEFORE any changes
            scroll_bar = self.chat_area.verticalScrollBar()
            saved_scroll = scroll_bar.value()
            
            # Get siblings before deletion
            siblings = self.chat_tree.get_siblings(message_obj.id)
            parent_id = message_obj.parent_id
            
            # 🔧 FIX: Remove the message and its descendants from UI FIRST
            self._remove_bubble_and_descendants(message_obj.id)
            
            # Delete the message from tree
            self.chat_tree.delete_message(message_obj.id)
            
            # 🔧 MAIN FIX: Collect affected messages INCLUDING their descendants
            affected_messages = []
            
            # Add remaining siblings AND all their descendants
            for sibling_id in siblings:
                if sibling_id != message_obj.id and sibling_id in self.chat_tree.messages:
                    # Add the sibling
                    sibling = self.chat_tree.messages[sibling_id]
                    affected_messages.append(sibling)
                    
                    # 🔧 CRITICAL: Add ALL descendants of this sibling
                    sibling_descendants = self._collect_branch_messages(sibling_id)
                    for descendant in sibling_descendants:
                        if descendant.id != sibling_id:  # Avoid duplicate
                            affected_messages.append(descendant)
            
            # Update parent if it exists
            if parent_id and parent_id in self.chat_tree.messages:
                parent = self.chat_tree.messages[parent_id]
                affected_messages.append(parent)  # Add parent to affected messages
                if parent_id in self.bubble_widgets:
                    parent_bubble = self.bubble_widgets[parent_id]
                    self._update_bubble_navigation_silent(parent_bubble, parent)
            
            # Only do smart refresh if there are affected messages
            if affected_messages:
                self._smart_refresh_for_navigation(affected_messages)
            else:
                # If no affected messages, just restore scroll immediately
                def restore():
                    scroll_bar.setValue(saved_scroll)
                QTimer.singleShot(1, restore)
            
            # Always restore scroll position after delete
            def final_restore():
                scroll_bar.setValue(saved_scroll)
            QTimer.singleShot(10, final_restore)
            
            self._save_chat_history()






    # Helper method to collect branch messages
    def _collect_branch_messages(self, message_id: str) -> List[ChatMessage]:
        """Collect all messages in a branch"""
        messages = []
        if message_id in self.chat_tree.messages:
            message = self.chat_tree.messages[message_id]
            messages.append(message)
            
            # Recursively collect children
            for child_id in message.children_ids:
                messages.extend(self._collect_branch_messages(child_id))
        
        return messages

    # Helper method to deactivate message and descendants
    def _deactivate_message_and_descendants(self, message_id: str):
        """Deactivate a message and all its descendants recursively"""
        message = self.chat_tree.messages.get(message_id)
        if not message:
            return
        
        # Deactivate this message
        message.is_active = False
        
        # Recursively deactivate all children
        for child_id in message.children_ids:
            self._deactivate_message_and_descendants(child_id)




















    def _add_bubble(self, message_obj: ChatMessage):
        """Add bubble for new message - works with infinite scroll"""
        try:
            # Check if bubble already exists
            if message_obj.id in self.bubble_widgets:
                return
            
            # Check if we should display this message
            # If we're at the bottom, always show new messages
            scroll_bar = self.chat_area.verticalScrollBar()
            is_at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 10
            
            if is_at_bottom or len(self.loaded_message_ids) < self.messages_per_page:
                # Create and add the bubble
                bubble = self._create_chat_bubble(message_obj)
                self.bubble_widgets[message_obj.id] = bubble
                self.chat_layout.addWidget(bubble)
                self.loaded_message_ids.add(message_obj.id)
                
                # Auto-scroll to bottom for new messages
                if is_at_bottom:
                    QTimer.singleShot(10, lambda: scroll_bar.setValue(scroll_bar.maximum()))
            
            # The message is still in chat_tree even if not displayed
            
        except Exception as e:
            print(f"Error adding bubble: {e}")
            import traceback
            traceback.print_exc()

    def _add_streaming_bubble(self):
        """Add streaming bubble placeholder - FIXED to start with plain text"""
        self.streaming_text = ""  # Reset streaming text
        self.streaming_active = True
        self.current_streaming_content = ""  # Reset current content
        
        # Create a temporary message object for streaming with PLAIN TEXT
        temp_msg = ChatMessage("assistant", "Thinking...", "")  # Plain text, no HTML
        
        # Get names for formatting
        user_profile = self._get_effective_user_profile()
        character_name = getattr(self.character, 'display_name', getattr(self.character, 'folder_name', 'Assistant'))
        user_name = user_profile.user_name if user_profile else "User"
        
        # Get character colors
        if (getattr(self.character, 'use_character_colors', False) and
            hasattr(self.character, 'character_primary_color') and
            hasattr(self.character, 'character_secondary_color') and
            self.character.character_primary_color and
            self.character.character_secondary_color):
            primary_color = self.character.character_primary_color
            secondary_color = self.character.character_secondary_color
        else:
            primary_color = app_colors.PRIMARY
            secondary_color = app_colors.SECONDARY
        
        # Create streaming bubble
        self.streaming_bubble = ChatBubble(
            temp_msg,
            self.character, 
            self.user_icon, 
            self.character_icon,
            False,  # is_user = False
            None,   # handler
            1,      # Indent for assistant message
            character_name,
            user_name,
            primary_color,
            secondary_color
        )
        
        self.chat_layout.addWidget(self.streaming_bubble)
        
        # Scroll to bottom
        QTimer.singleShot(10, lambda: self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()))

    def _update_streaming_bubble(self, new_token: str):
        """Update streaming bubble with new token - FIXED to use plain text"""
        if not self.streaming_active or not self.streaming_bubble:
            return
        
        # Check if streaming was stopped
        if self.streaming_stopped:
            return
        
        # Accumulate the text
        self.streaming_text += new_token
        self.current_streaming_content = self.streaming_text  # Keep track for stop functionality
        
        # Update the bubble display with PLAIN TEXT
        if hasattr(self.streaming_bubble, 'bubble_label') and self.streaming_bubble.bubble_label:
            # Show the accumulated text directly as plain text
            display_text = self.streaming_text if self.streaming_text.strip() else "Thinking..."
            
            # Update the label text (this should set it as plain text, not HTML)
            self.streaming_bubble.bubble_label.setText(display_text)
            
            # Auto-resize bubble width based on content
            if self.streaming_text.strip():
                max_bubble_width = min(600, self.chat_area.width() - 100)
                
                # Calculate text width
                font_metrics = self.streaming_bubble.bubble_label.fontMetrics()
                text_width = font_metrics.horizontalAdvance(self.streaming_text)
                padding = 40  # Account for padding
                new_width = min(text_width + padding, max_bubble_width)
                
                # Set minimum width
                new_width = max(new_width, 120)
                
                self.streaming_bubble.bubble_label.setFixedWidth(new_width)
        
        # Scroll to bottom to follow the conversation
        QTimer.singleShot(10, lambda: self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()))




    def _finalize_streaming_bubble(self):
        """Finalize streaming bubble - Clean removal only"""
        print("🧹 Finalizing streaming bubble...")
        
        self.streaming_active = False

        if self.streaming_bubble:
            try:
                self.chat_layout.removeWidget(self.streaming_bubble)
                self.streaming_bubble.deleteLater()
                print("✅ Streaming bubble removed")
            except Exception as e:
                print(f"Error removing streaming bubble: {e}")

        self.streaming_bubble = None
        
        # Small delay to ensure smooth transition
        QTimer.singleShot(50, lambda: self.chat_area.verticalScrollBar().setValue(
            self.chat_area.verticalScrollBar().maximum()))


    def _process_messages(self):
        """Background thread with enhanced name replacement and FIXED stop functionality"""
        while True:
            try:
                message, parent_id = self.message_queue.get(timeout=1)

                # Reset streaming state for fresh message
                self.streaming_stopped = False
                self.current_streaming_content = ""
                self.streaming_text = ""  # Also reset streaming_text
                self.force_stop_streaming = False  # Reset force stop flag
                
                print(f"🔄 Processing message: {message[:50]}...")

                # Get character's API config
                api_config_name = getattr(self.character, 'api_config_name', None)

                # Get effective user profile
                user_profile = self._get_effective_user_profile()

                # Prepare character and user names
                character_name = getattr(self.character, 'display_name', self.character.name)
                user_name = user_profile.user_name if user_profile else "User"

                # Build enhanced personality with user context
                if user_profile:
                    enhanced_personality = f"""You are {character_name} - {self.character.personality}

    User Profile:
    {user_name} is {user_profile.name}. {user_profile.personality}

    Important: Always refer to the user as {user_name} and yourself as {character_name} in your responses."""
                else:
                    enhanced_personality = f"""You are {character_name} - {self.character.personality}

    Important: Always refer to the user as {user_name} and yourself as {character_name} in your responses."""

                # Replace placeholders
                enhanced_personality = replace_name_placeholders(enhanced_personality, character_name, user_name)

                # Get API config
                config = self.ai_interface._get_config(api_config_name)

                # Prepare conversation history
                history = []
                active_messages = self.chat_tree.get_active_conversation_path()

                # Calculate optimal message count based on context size
                if config and hasattr(config, 'context_size'):
                    avg_message_tokens = 100
                    personality_tokens = estimate_tokens(enhanced_personality)
                    response_tokens = config.max_tokens if config else 150
                    available_tokens = config.context_size - personality_tokens - response_tokens - 500
                    max_messages = max(5, min(50, available_tokens // avg_message_tokens))
                else:
                    max_messages = 10

                # Build history with name replacement
                for msg in active_messages[-max_messages:]:
                    processed_content = replace_name_placeholders(msg.content, character_name, user_name)
                    history.append({"role": msg.role, "content": processed_content})

                # Determine if streaming should be used
                use_streaming = False
                if config and hasattr(config, 'streaming'):
                    use_streaming = config.streaming

                print(f"🎯 Using streaming: {use_streaming}")

                # STREAMING PATH
                if use_streaming:
                    self.current_streaming_parent_id = parent_id
                    self.add_streaming_bubble_signal.emit()

                    # Small delay to ensure UI is ready
                    import time
                    time.sleep(0.1)

                    full_response = ""
                    any_tokens_received = False  # Track if we got any tokens

                    def streaming_callback(token, is_finished):
                        nonlocal full_response, any_tokens_received

                        # CRITICAL: Check multiple stop conditions
                        if self.streaming_stopped or getattr(self, 'force_stop_streaming', False):
                            print("🛑 Streaming callback: User stopped, ignoring token")
                            return

                        if not is_finished:
                            # We received a token - mark that we got something
                            any_tokens_received = True
                            full_response += token
                            # Send individual token to update bubble
                            self.update_streaming_bubble_signal.emit(token)
                            
                        else:
                            # Streaming finished naturally
                            print("✅ Streaming completed naturally")
                            
                            # Only create final message if not stopped and we have content
                            if not self.streaming_stopped and not getattr(self, 'force_stop_streaming', False):
                                # Use full_response if we have it, otherwise use "Thinking..." 
                                final_content = full_response.strip() if full_response.strip() else "Thinking..."
                                
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                ai_msg = ChatMessage(
                                    role="assistant",
                                    content=final_content,
                                    timestamp=timestamp
                                )
                                ai_msg.parent_id = parent_id
                                ai_msg.is_active = True

                                # Add to chat tree
                                ai_msg_id = self.chat_tree.add_message(ai_msg)

                                # REMOVED: Max history enforcement
                                # No longer needed with infinite scroll

                                # Clean up streaming UI first
                                self.finalize_streaming_bubble_signal.emit()

                                # Add final bubble
                                self.add_bubble_signal.emit(ai_msg)

                                # Save history
                                self.save_chat_history_signal.emit()
                                
                            else:
                                # Was stopped - let the stop handler deal with it
                                print("🔄 Stream was stopped - stop handler will send content")

                    # Start streaming request
                    try:
                        self.ai_interface.get_streaming_response(
                            history,
                            enhanced_personality,
                            streaming_callback,
                            api_config_name
                        )
                    except Exception as e:
                        print(f"❌ Streaming error: {e}")
                        # Even on error, try to send something rather than nothing
                        if not self.streaming_stopped:
                            self._stop_ai_writing()  # This will send whatever content exists

                # NON-STREAMING PATH
                else:
                    print("📝 Using non-streaming response")
                    
                    # Show thinking bubble (NEW)
                    self.current_streaming_parent_id = parent_id
                    self.add_streaming_bubble_signal.emit()
                    
                    try:
                        response = self.ai_interface.get_response(
                            history,
                            enhanced_personality,
                            api_config_name
                        )

                        if response and response.strip():
                            self.streaming_text = response.strip()  # Set the text
                            
                            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            ai_msg = ChatMessage(
                                role="assistant", 
                                content=response.strip(), 
                                timestamp=timestamp
                            )
                            ai_msg.parent_id = parent_id
                            ai_msg.is_active = True

                            ai_msg_id = self.chat_tree.add_message(ai_msg)

                            # Remove thinking bubble (NEW)
                            self.finalize_streaming_bubble_signal.emit()

                            # Add real bubble
                            self.add_bubble_signal.emit(ai_msg)
                            self.save_chat_history_signal.emit()
                            
                        else:
                            print("⚠️ Empty response from AI")
                            self.finalize_streaming_bubble_signal.emit()  # Clean up
                            
                    except Exception as e:
                        print(f"❌ Non-streaming error: {e}")
                        self.finalize_streaming_bubble_signal.emit()  # Clean up
                    finally:
                        # Reset flag and re-enable UI
                        self.cancel_non_streaming = False
                        self.ai_finish_processing_signal.emit()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"💥 Critical error in message processing: {e}")
                import traceback
                traceback.print_exc()
                
                # Emergency cleanup - but try to send content if we were streaming
                try:
                    if hasattr(self, 'streaming_active') and self.streaming_active:
                        self._stop_ai_writing()  # Send whatever we have
                    else:
                        self.finalize_streaming_bubble_signal.emit()
                except:
                    pass


    def _handle_stop_streaming(self):
        """Handle stop streaming signal"""
        self._stop_ai_writing()

    
    def _activate_branch(self, message_id: str):
        """Activate a message branch and deactivate siblings"""
        message = self.chat_tree.messages.get(message_id)
        if not message:
            return
        
        # Deactivate all siblings
        siblings = self.chat_tree.get_siblings(message_id)
        for sibling_id in siblings:
            self.chat_tree.messages[sibling_id].is_active = False
            # Deactivate their children too
            self.chat_tree._deactivate_branch(sibling_id)
        
        # Activate this message and its active children
        message.is_active = True
        self._activate_children(message_id)
    
    def _activate_children(self, parent_id: str):
        """Recursively activate the first child of each level"""
        parent = self.chat_tree.messages.get(parent_id)
        if parent and parent.children_ids:
            # Activate the first child by default
            first_child_id = parent.children_ids[0]
            first_child = self.chat_tree.messages[first_child_id]
            first_child.is_active = True
            self._activate_children(first_child_id)
    



    def _refresh_display(self):
        """Display recent messages with infinite scroll support - KEEPS ALL DATA"""
        if self.update_in_progress:
            return
        
        self.update_in_progress = True
        
        # Save scroll position
        scroll_bar = self.chat_area.verticalScrollBar()
        was_at_bottom = scroll_bar.value() >= scroll_bar.maximum() - 10
        saved_scroll = scroll_bar.value() if not was_at_bottom else None
        
        try:
            # IMPORTANT: We get ALL messages but only DISPLAY some
            all_active_messages = self._collect_all_active_messages()
            all_active_messages.sort(key=lambda msg: msg.timestamp)
            
            # If this is the first refresh or we need to rebuild
            if not self.loaded_message_ids or len(self.bubble_widgets) == 0:
                # Clear current display only
                self.bubble_widgets.clear()
                self.loaded_message_ids.clear()
                self.oldest_loaded_timestamp = None
                
                while self.chat_layout.count():
                    item = self.chat_layout.takeAt(0)
                    if item.widget():
                        item.widget().deleteLater()
                
                # Load only recent messages for DISPLAY
                # But ALL messages still exist in chat_tree
                recent_messages = all_active_messages[-self.messages_per_page:] if len(all_active_messages) > self.messages_per_page else all_active_messages
                
                # Add recent messages to display
                for msg in recent_messages:
                    bubble = self._create_chat_bubble(msg)
                    self.bubble_widgets[msg.id] = bubble
                    self.chat_layout.addWidget(bubble)
                    self.loaded_message_ids.add(msg.id)
                    
                    # Track oldest loaded
                    if self.oldest_loaded_timestamp is None or msg.timestamp < self.oldest_loaded_timestamp:
                        self.oldest_loaded_timestamp = msg.timestamp
            else:
                # Smart refresh - only update what's needed
                current_message_ids = {msg.id for msg in all_active_messages}
                
                # Remove bubbles that shouldn't be displayed
                for msg_id in list(self.bubble_widgets.keys()):
                    if msg_id not in current_message_ids:
                        bubble = self.bubble_widgets[msg_id]
                        self.chat_layout.removeWidget(bubble)
                        bubble.deleteLater()
                        del self.bubble_widgets[msg_id]
                        self.loaded_message_ids.discard(msg_id)
                
                # Add new messages that should be displayed
                for msg in all_active_messages:
                    if msg.id not in self.bubble_widgets and msg.id in self.loaded_message_ids:
                        # This message should be displayed
                        bubble = self._create_chat_bubble(msg)
                        self.bubble_widgets[msg.id] = bubble
                        
                        # Find correct position
                        position = 0
                        for i in range(self.chat_layout.count()):
                            widget = self.chat_layout.itemAt(i).widget()
                            if hasattr(widget, 'message_obj') and widget.message_obj.timestamp < msg.timestamp:
                                position = i + 1
                            else:
                                break
                        
                        self.chat_layout.insertWidget(position, bubble)
            
            # Update tracking
            self.last_message_count = len(all_active_messages)
            
        finally:
            self.update_in_progress = False
            
            # Restore scroll position
            def restore():
                if was_at_bottom:
                    scroll_bar.setValue(scroll_bar.maximum())
                elif saved_scroll is not None:
                    scroll_bar.setValue(min(saved_scroll, scroll_bar.maximum()))
            
            QTimer.singleShot(10, restore)





    def _reorder_bubbles_silently(self, sorted_messages):
        """Reorder bubbles with ZERO intermediate visual updates"""
        current_order = []
        for i in range(self.chat_layout.count()):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and hasattr(item.widget(), 'message_obj'):
                current_order.append(item.widget().message_obj.id)
        
        expected_order = [msg.id for msg in sorted_messages]
        
        # Only reorder if actually different
        if current_order != expected_order:
            # Disable updates on all widgets during reordering
            all_widgets = []
            for msg_id in expected_order:
                if msg_id in self.bubble_widgets:
                    widget = self.bubble_widgets[msg_id]
                    widget.setUpdatesEnabled(False)
                    if hasattr(widget, 'bubble_label') and widget.bubble_label:
                        widget.bubble_label.setUpdatesEnabled(False)
                    all_widgets.append(widget)
            
            # Remove all widgets from layout without visual updates
            widgets_by_id = {}
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item and item.widget() and hasattr(item.widget(), 'message_obj'):
                    widget = item.widget()
                    widgets_by_id[widget.message_obj.id] = widget
            
            # Re-add in correct order - still with updates disabled
            for msg_id in expected_order:
                if msg_id in widgets_by_id:
                    self.chat_layout.addWidget(widgets_by_id[msg_id])








    # Simple helper method you can call anywhere
    def _print_counts(self):
        """Simple count printer"""
        active_msgs = len([msg for msg in self.chat_tree.messages.values() if msg.is_active])
        print(f"Bubbles: {len(self.bubble_widgets)} | Active: {active_msgs} | Total: {len(self.chat_tree.messages)}")




    def _restore_scroll_position_silent(self, was_at_bottom, saved_scroll):
        """Restore scroll position with minimal operations"""
        # Safety check for variables
        if was_at_bottom is None:
            was_at_bottom = False
        if saved_scroll is None:
            saved_scroll = 0
            
        def restore_scroll():
            try:
                scroll_bar = self.chat_area.verticalScrollBar()
                if was_at_bottom:
                    scroll_bar.setValue(scroll_bar.maximum())
                elif saved_scroll is not None:
                    scroll_bar.setValue(min(saved_scroll, scroll_bar.maximum()))
            except Exception as e:
                print(f"Error restoring scroll: {e}")
        
        # Use shortest possible delay
        QTimer.singleShot(1, restore_scroll)


    def _update_bubble_navigation_silent(self, bubble, message):
        """Update navigation arrows silently"""
        siblings = self.chat_tree.get_siblings(message.id)
        has_siblings = len(siblings) > 1
        
        if has_siblings:
            sibling_index = siblings.index(message.id)
            sibling_position = (sibling_index, len(siblings))
            
            # Update bubble's navigation state without visual updates
            bubble.has_siblings = has_siblings
            bubble.sibling_position = sibling_position
            
            # FORCE BUBBLE RECREATION for navigation update (temporary fix)
            if hasattr(bubble, '_force_navigation_refresh'):
                bubble._force_navigation_refresh()
            else:
                # Fallback: recreate the bubble entirely
                self._recreate_single_bubble_silent(message)
        else:
            bubble.has_siblings = False
            bubble.sibling_position = None

    def _recreate_single_bubble_silent(self, message):
        """Recreate a single bubble to fix navigation issues"""
        if message.id in self.bubble_widgets:
            # Remove old bubble
            old_bubble = self.bubble_widgets[message.id]
            self.chat_layout.removeWidget(old_bubble)
            old_bubble.deleteLater()
            del self.bubble_widgets[message.id]
            
            # Create new bubble with correct navigation
            self._add_single_bubble_completely_silent(message)


    def _emergency_refresh_silent(self):
        """Emergency fallback with minimal flicker"""
        try:
            # Hide all widgets first to minimize visual disruption
            for bubble in self.bubble_widgets.values():
                bubble.setUpdatesEnabled(False)
                bubble.setVisible(False)
            
            # Clear tracking
            self.bubble_widgets.clear()
            
            # Clear layout
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
            
            # Re-add all active messages with updates disabled
            all_active_messages = self._collect_all_active_messages()
            all_active_messages.sort(key=lambda msg: msg.timestamp)
            
            for msg in all_active_messages:
                self._add_single_bubble_completely_silent(msg)
                
        except Exception as e:
            print(f"Emergency fallback error: {e}")

    def _collect_all_active_messages(self) -> List[ChatMessage]:
        """Collect ALL active AND visible messages from the entire tree structure"""
        active_messages = []
        visited = set()
        
        # Start from all roots
        for root_id in self.chat_tree.roots:
            self._collect_active_recursive(root_id, active_messages, visited)
        
        # Filter out hidden messages
        return [msg for msg in active_messages if not getattr(msg, 'is_hidden', False)]

    # 5. Add method to get full conversation for AI (separate from display):
    def _get_full_conversation_for_ai(self) -> List[Dict[str, str]]:
        """Get the complete conversation history for AI context"""
        messages = []
        active_path = self.chat_tree.get_active_conversation_path()
        
        for msg in active_path:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        return messages
        
        return active_messages
    def _collect_active_recursive(self, message_id: str, result: List[ChatMessage], visited: set):
        """Recursively collect all active messages"""
        if message_id in visited or message_id not in self.chat_tree.messages:
            return
        
        visited.add(message_id)
        message = self.chat_tree.messages[message_id]
        
        # Add this message if it's active
        if message.is_active:
            result.append(message)
        
        # Recursively check all children (not just active ones)
        for child_id in message.children_ids:
            self._collect_active_recursive(child_id, result, visited)    
    def _save_chat_history(self):
        """Save chat tree to file"""
        app_data_dir = get_app_data_dir()
        history_file = app_data_dir / "characters" / self.character.name / "chat_history.json"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(history_file, 'w', encoding='utf-8') as f:
                # Save the entire tree structure
                data = {
                    "messages": {msg_id: asdict(msg) for msg_id, msg in self.chat_tree.messages.items()},
                    "roots": self.chat_tree.roots
                }
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def _load_chat_history(self):
        """Load chat tree from file"""
        app_data_dir = get_app_data_dir()
        history_file = app_data_dir / "characters" / self.character.name / "chat_history.json"
        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Reconstruct tree
                    if isinstance(data, dict) and "messages" in data:
                        # New tree format
                        for msg_id, msg_data in data["messages"].items():
                            msg = ChatMessage(**msg_data)
                            self.chat_tree.messages[msg_id] = msg
                        self.chat_tree.roots = data.get("roots", [])
                    else:
                        # Old format - convert to tree
                        for msg_data in data:
                            # Add default values for new fields
                            if 'id' not in msg_data:
                                msg_data['id'] = str(uuid.uuid4())
                            if 'parent_id' not in msg_data:
                                msg_data['parent_id'] = None
                            if 'children_ids' not in msg_data:
                                msg_data['children_ids'] = []
                            if 'sibling_index' not in msg_data:
                                msg_data['sibling_index'] = 0
                            if 'is_active' not in msg_data:
                                msg_data['is_active'] = True
                            
                            msg = ChatMessage(**msg_data)
                            self.chat_tree.add_message(msg)
            except Exception as e:
                print(f"Error loading history: {e}")
        
        # Render active conversation
        self._refresh_display()



    def _load_selected_profile(self):
        """Load the selected user profile for this character - UPDATED to load by folder name"""
        try:
            app_data_dir = get_app_data_dir()
            profile_file = app_data_dir / "characters" / self.character.name / "selected_profile.json"
            
            if profile_file.exists():
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                    
                selected_name = profile_data.get("selected_profile_name")
                if selected_name:
                    # Find the profile by folder name (name field)
                    parent = self.parent()
                    if parent and hasattr(parent, 'user_profile_manager'):
                        manager = parent.user_profile_manager
                        for profile in manager.settings.profiles:
                            if profile.name == selected_name:  # Match by folder name
                                self.selected_user_profile = profile
                                print(f"Loaded selected profile for {self.character.name}: {profile.title} ({profile.name})")
                                return
                        
                        print(f"Profile '{selected_name}' no longer exists, using default")
                        self.selected_user_profile = None
                else:
                    print(f"No specific profile selected for {self.character.name}, using global")
                    self.selected_user_profile = None
            else:
                print(f"No saved profile selection for {self.character.name}")
                self.selected_user_profile = None
                
        except Exception as e:
            print(f"Error loading selected profile: {e}")
            self.selected_user_profile = None


    def _load_selected_profile(self):
        """Load the selected user profile for this character"""
        try:
            app_data_dir = get_app_data_dir()
            profile_file = app_data_dir / "characters" / self.character.name / "selected_profile.json"
            
            if profile_file.exists():
                with open(profile_file, 'r', encoding='utf-8') as f:
                    profile_data = json.load(f)
                    
                selected_name = profile_data.get("selected_profile_name")
                if selected_name:
                    # Find the profile in the user profile manager
                    parent = self.parent()
                    if parent and hasattr(parent, 'user_profile_manager'):
                        manager = parent.user_profile_manager
                        for profile in manager.settings.profiles:
                            if profile.name == selected_name:
                                self.selected_user_profile = profile
                                print(f"Loaded selected profile for {self.character.name}: {selected_name}")
                                return
                        
                        print(f"Profile '{selected_name}' no longer exists, using default")
                        self.selected_user_profile = None
                else:
                    print(f"No specific profile selected for {self.character.name}, using global")
                    self.selected_user_profile = None
            else:
                print(f"No saved profile selection for {self.character.name}")
                self.selected_user_profile = None
                
        except Exception as e:
            print(f"Error loading selected profile: {e}")
            self.selected_user_profile = None


    def closeEvent(self, event):
        """Handle window close event with proper cleanup - FOR CHATWINDOW CLASS"""
        print(f"Closing chat window for {self.character.name}")
        
        # Save window state (ADD THIS LINE)
        self._save_window_state()
        
        # Stop the keep on top timer if it exists (ADD THIS)
        if hasattr(self, '_keep_on_top_timer') and self._keep_on_top_timer:
            self._keep_on_top_timer.stop()
        
        # Close minimize bar if it exists
        if hasattr(self, 'minimize_bar') and self.minimize_bar:
            self.minimize_bar.close()
        
        # Stop any running threads/timers
        if hasattr(self, 'schedule_timer') and self.schedule_timer:
            self.schedule_timer.stop()
        
        # Clear from parent's tracking immediately
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'chat_windows'):
                if self.character.name in parent.chat_windows:
                    del parent.chat_windows[self.character.name]
                    print(f"Removed {self.character.name} from chat_windows")
        except Exception as e:
            print(f"Error during cleanup: {e}")
        
        # Accept the close event
        event.accept()

    def _load_icon(self, icon_path, scale=1.0, offset_x=0, offset_y=0, force_refresh=False):
        """Load and create high-quality circular icon with force refresh option"""
        if not icon_path:
            return None
            
        # Resolve path
        if not os.path.isabs(icon_path):
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.character.name
            icon_path = str(char_dir / icon_path)
        
        if not os.path.exists(icon_path):
            print(f"⚠️ Icon not found: {icon_path}")
            return None
            
        try:
            # Force reload if requested or if this is a settings change
            if force_refresh:
                original_pixmap = force_reload_image(icon_path)
            else:
                original_pixmap = QPixmap(icon_path)
            
            if original_pixmap.isNull():
                return None
            
            # Target size for chat icons
            icon_size = 42
            
            # Calculate the area we want from the original image based on positioning
            preview_to_icon_ratio = icon_size / 180.0
            
            # Apply scale and offset to determine what part of image to use
            source_width = int(180 / scale)
            source_height = int(180 / scale)
            source_x = (original_pixmap.width() - source_width) // 2 - int(offset_x / scale)
            source_y = (original_pixmap.height() - source_height) // 2 - int(offset_y / scale)
            
            # Ensure source coordinates are within bounds
            source_x = max(0, min(source_x, original_pixmap.width() - source_width))
            source_y = max(0, min(source_y, original_pixmap.height() - source_height))
            source_width = min(source_width, original_pixmap.width() - source_x)
            source_height = min(source_height, original_pixmap.height() - source_y)
            
            # Extract the positioned portion
            positioned_pixmap = original_pixmap.copy(source_x, source_y, source_width, source_height)
            
            # Create circular icon at ultra-high quality
            render_size = icon_size * 16
            
            # Scale extracted portion to render size
            scaled_pixmap = positioned_pixmap.scaled(
                render_size,
                render_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Create circular mask at high resolution
            circular_pixmap = QPixmap(render_size, render_size)
            circular_pixmap.fill(Qt.transparent)
            
            painter = QPainter(circular_pixmap)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
            painter.setRenderHint(QPainter.LosslessImageRendering, True)
            
            # Create circular clipping
            path = QPainterPath()
            path.addEllipse(0, 0, render_size, render_size)
            painter.setClipPath(path)
            
            # Center and draw
            x = (render_size - scaled_pixmap.width()) // 2
            y = (render_size - scaled_pixmap.height()) // 2
            painter.drawPixmap(x, y, scaled_pixmap)
            
            painter.end()
            
            # Final downscale to icon size
            final_icon = circular_pixmap.scaled(
                icon_size,
                icon_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            return final_icon
            
        except Exception as e:
            print(f"Error loading positioned icon: {e}")
            return None


    def _load_chat_settings(self):
        """Load chat settings from file with path resolution"""
        app_data_dir = get_app_data_dir()
        settings_file = app_data_dir / "characters" / self.character.name / "chat_settings.json"
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Add default values for existing fields
                    if 'bg_image_scale' not in data:
                        data['bg_image_scale'] = 1.0
                    if 'bg_image_offset_x' not in data:
                        data['bg_image_offset_x'] = 0
                    if 'bg_image_offset_y' not in data:
                        data['bg_image_offset_y'] = 0
                        
                    # Icon positioning defaults
                    if 'user_icon_scale' not in data:
                        data['user_icon_scale'] = 1.0
                    if 'user_icon_offset_x' not in data:
                        data['user_icon_offset_x'] = 0
                    if 'user_icon_offset_y' not in data:
                        data['user_icon_offset_y'] = 0
                    if 'character_icon_scale' not in data:
                        data['character_icon_scale'] = 1.0
                    if 'character_icon_offset_x' not in data:
                        data['character_icon_offset_x'] = 0
                    if 'character_icon_offset_y' not in data:
                        data['character_icon_offset_y'] = 0
                    
                    # NEW: Transparency defaults
                    if 'window_transparency_enabled' not in data:
                        data['window_transparency_enabled'] = False
                    if 'window_transparency_value' not in data:
                        data['window_transparency_value'] = 50
                    if 'window_transparency_mode' not in data:
                        data['window_transparency_mode'] = "focus"
                    if 'window_transparency_time' not in data:
                        data['window_transparency_time'] = 3
                    
                    # NEW: Resolve relative paths to absolute paths
                    char_dir = app_data_dir / "characters" / self.character.name
                    
                    if 'user_icon_path' in data and data['user_icon_path']:
                        if not os.path.isabs(data['user_icon_path']):
                            data['user_icon_path'] = str(char_dir / data['user_icon_path'])
                    
                    if 'character_icon_path' in data and data['character_icon_path']:
                        if not os.path.isabs(data['character_icon_path']):
                            data['character_icon_path'] = str(char_dir / data['character_icon_path'])
                    
                    if 'background_image_path' in data and data['background_image_path']:
                        if not os.path.isabs(data['background_image_path']):
                            data['background_image_path'] = str(char_dir / data['background_image_path'])
                            
                    return ChatSettings(**data)
            except Exception as e:
                print(f"Error loading chat settings: {e}")
        
        return ChatSettings()

    def _load_scheduled_dialogs(self):
        """Load scheduled dialogs from file"""
        app_data_dir = get_app_data_dir()
        dialog_file = app_data_dir / "characters" / self.character.name / "scheduled_dialogs.json"
        if dialog_file.exists():
            try:
                with open(dialog_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.scheduled_dialogs = [ScheduledDialog(**d) for d in data]
            except Exception as e:
                print(f"Error loading dialogs: {e}")
    
    def _check_scheduled_reminders(self):
        """Check for scheduled dialogs AND proactive check-ins - WITH DEBUG"""
        now = datetime.now()
        now_str = now.strftime("%H:%M")
        
        # DEBUG: Print current time and character
        print(f"🕐 Checking schedule for {self.character.name} at {now_str}")
        print(f"📋 Found {len(self.scheduled_dialogs)} scheduled dialogs")

        # Existing scheduled dialog logic
        for dialog in self.scheduled_dialogs:
            if not dialog.enabled:
                print(f"⏸️ Dialog '{dialog.prompt[:30]}...' is disabled")
                continue

            should_trigger = False

            if dialog.date:
                try:
                    target_date = datetime.strptime(dialog.date, "%Y-%m-%d")
                    delta_days = (target_date.date() - now.date()).days
                    print(f"📅 Dialog with date: target={dialog.date}, days_until={delta_days}, target_advance={dialog.advance_days}")
                    if delta_days == dialog.advance_days and now_str == dialog.time:
                        should_trigger = True
                except ValueError:
                    print(f"❌ Invalid date format: {dialog.date}")
                    continue
            else:
                print(f"⏰ Time-only dialog: target={dialog.time}, current={now_str}")
                if now_str == dialog.time:
                    should_trigger = True

            if should_trigger:
                if not hasattr(dialog, "triggered") or not dialog.triggered:
                    print(f"🚀 TRIGGERING REMINDER: {dialog.prompt[:50]}...")
                    dialog.triggered = True
                    self._send_reminder_as_character(dialog.prompt)
                else:
                    print(f"⏭️ Dialog already triggered: {dialog.prompt[:30]}...")

        # Reset triggered flag if time has passed
        for dialog in self.scheduled_dialogs:
            if hasattr(dialog, "triggered") and now_str != dialog.time:
                dialog.triggered = False
        
        # NEW: Check for proactive check-ins with debug
        if hasattr(self, 'checkin_settings') and self._should_check_in():
            print(f"💬 TRIGGERING CHECK-IN for {self.character.name}")
            self._send_checkin_message()
        else:
            print(f"⏸️ No check-in needed for {self.character.name}")
            


    def _send_reminder_as_character(self, prompt_text: str, is_checkin: bool = False):
        """Send a scheduled message or check-in as the character - FIXED VERSION"""
        # Remove the nested 'run' function and thread - run directly instead
        try:
            if is_checkin:
                history = self._get_conversation_history_for_ai(limit=5)
                history.append({"role": "user", "content": prompt_text})
            else:
                history = [{"role": "user", "content": f"Remind me: {prompt_text}"}]
            
            # Get AI response
            response = self.ai_interface.get_response(history, self.character.personality)
            
            if response.strip():
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ai_msg = ChatMessage("assistant", response.strip(), timestamp)
                
                # Try to attach as sibling to existing assistant message
                last_assistant_msg = self._find_last_assistant_message()
                if last_assistant_msg:
                    # Sibling approach - same parent as last assistant
                    ai_msg.parent_id = last_assistant_msg.parent_id
                    message_id = self.chat_tree.add_message(ai_msg)
                    
                    # Deactivate previous assistant and its descendants
                    if last_assistant_msg.parent_id:
                        parent = self.chat_tree.messages[last_assistant_msg.parent_id]
                        for child_id in parent.children_ids:
                            if child_id != message_id:
                                child_msg = self.chat_tree.messages[child_id]
                                child_msg.is_active = False
                                self.chat_tree._deactivate_branch(child_id)
                else:
                    # No assistant response yet - treat as root or attach to last user msg
                    last_user_msg = self._find_last_user_message()
                    if last_user_msg:
                        ai_msg.parent_id = last_user_msg.id
                    message_id = self.chat_tree.add_message(ai_msg)
                
                # CRITICAL FIX: Use signals properly
                # First add the bubble
                self.add_bubble_signal.emit(ai_msg)
                
                # Force refresh to ensure visibility
                QTimer.singleShot(100, lambda: self.refresh_display_signal.emit())
                
                # Save chat history
                self.save_chat_history_signal.emit()
                
                if is_checkin:
                    print("✅ Sent check-in with hidden structure")
                else:
                    print(f"✅ Sent scheduled reminder: {prompt_text[:30]}...")
                    
        except Exception as e:
            print(f"❌ Error in _send_reminder_as_character: {e}")
            import traceback
            traceback.print_exc()



    def _find_last_assistant_message(self):
        """Find the most recent assistant message to use as sibling reference"""
        try:
            # Get all active messages in chronological order
            active_messages = []
            for msg in self.chat_tree.messages.values():
                if msg.is_active and msg.role == "assistant":
                    active_messages.append(msg)
            
            if not active_messages:
                return None
                
            # Sort by timestamp and return the most recent
            active_messages.sort(key=lambda m: m.timestamp)
            return active_messages[-1]
            
        except Exception as e:
            print(f"Error finding last assistant message: {e}")
            return None

    def test_flash(self):
        """Test flash animation immediately"""
        if hasattr(self, 'flash_animation_group'):
            # Force flash for testing (ignore focus state)
            self.flash_animation_group.start()
            print("Flash animation started!")
        else:
            print("Flash animation not set up!")


    def setup_flash_animation(self):
        """Setup the flash animation sequence for scheduled message notifications"""
        # Create animation group for smooth flashing
        self.flash_animation_group = QSequentialAnimationGroup()
        
        # First fade out animation
        self.flash_fade_out1 = QPropertyAnimation(self, b"windowOpacity")
        self.flash_fade_out1.setDuration(200)  # 200ms duration
        self.flash_fade_out1.setStartValue(1.0)
        self.flash_fade_out1.setEndValue(0.3)
        self.flash_fade_out1.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # First fade in animation
        self.flash_fade_in1 = QPropertyAnimation(self, b"windowOpacity")
        self.flash_fade_in1.setDuration(200)
        self.flash_fade_in1.setStartValue(0.3)
        self.flash_fade_in1.setEndValue(1.0)
        self.flash_fade_in1.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Second fade out animation
        self.flash_fade_out2 = QPropertyAnimation(self, b"windowOpacity")
        self.flash_fade_out2.setDuration(150)
        self.flash_fade_out2.setStartValue(1.0)
        self.flash_fade_out2.setEndValue(0.4)
        self.flash_fade_out2.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        # Final fade in animation
        self.flash_fade_in2 = QPropertyAnimation(self, b"windowOpacity")
        self.flash_fade_in2.setDuration(150)
        self.flash_fade_in2.setStartValue(0.4)
        self.flash_fade_in2.setEndValue(1.0)
        self.flash_fade_in2.setEasingCurve(QEasingCurve.Type.InQuad)
        
        # Add animations to sequence
        self.flash_animation_group.addAnimation(self.flash_fade_out1)
        self.flash_animation_group.addAnimation(self.flash_fade_in1)
        self.flash_animation_group.addAnimation(self.flash_fade_out2)
        self.flash_animation_group.addAnimation(self.flash_fade_in2)
        
        # Connect to finished signal
        self.flash_animation_group.finished.connect(self.on_flash_finished)

    def flash_window_for_scheduled_message(self):
        """Trigger the flash animation for scheduled message notification"""
        # Only flash if not already flashing and window is not focused
        if (not self.flash_animation_group.state() == QSequentialAnimationGroup.State.Running and
            not self.isActiveWindow()):
            
            # Store current opacity in case transparency is active
            self.pre_flash_opacity = self.windowOpacity()
            
            # Start the flash animation
            self.flash_animation_group.start()

    def on_flash_finished(self):
        """Called when flash animation is complete"""
        # Restore the appropriate opacity based on transparency settings
        if (hasattr(self, 'chat_settings') and 
            self.chat_settings.window_transparency_enabled and 
            hasattr(self, 'is_transparent') and self.is_transparent):
            # Restore transparency if it was active
            self._apply_transparency()
        else:
            # Ensure full opacity if no transparency should be active
            self.setWindowOpacity(1.0)




    def _clear_history(self):
        """Clear all chat history - FIXED to properly reset state"""
        reply = QMessageBox.question(self, "Clear History", 
                                "Are you sure you want to clear all chat history?",
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("🗑️ Clearing all chat history...")
            
            # Clear the chat tree
            self.chat_tree.messages.clear()
            self.chat_tree.roots.clear()
            
            # IMPORTANT: Clear the bubble widgets dictionary
            self.bubble_widgets.clear()
            
            # Clear the UI layout
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item and item.widget():
                    item.widget().deleteLater()
            
            # Reset any tracking variables
            if hasattr(self, 'last_message_count'):
                self.last_message_count = 0
            if hasattr(self, 'last_message_ids'):
                self.last_message_ids = set()
            
            # Clear any streaming state
            self.streaming_active = False
            self.streaming_bubble = None
            self.streaming_text = ""
            
            # Force a display refresh
            self._refresh_display()
            
            # Save the empty state
            self._save_chat_history()
            
            print("✅ Chat history cleared successfully")
    
    def _export_chat(self):
        """Export chat to text file"""
        filename, _ = QFileDialog.getSaveFileName(self, "Export Chat", "", "Text Files (*.txt)")
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    # Export active conversation path
                    active_messages = self.chat_tree.get_active_conversation_path()
                    for msg in active_messages:
                        role = "You" if msg.role == "user" else self.character.name
                        f.write(f"[{msg.timestamp}] {role}: {msg.content}\n\n")
                QMessageBox.information(self, "Export Complete", "Chat exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export: {str(e)}")




    def _copy_chat_settings(self, settings):
        """Create a copy of chat settings for comparison"""
        return {
            'user_icon_path': settings.user_icon_path,
            'character_icon_path': settings.character_icon_path,
            'user_icon_scale': getattr(settings, 'user_icon_scale', 1.0),
            'user_icon_offset_x': getattr(settings, 'user_icon_offset_x', 0),
            'user_icon_offset_y': getattr(settings, 'user_icon_offset_y', 0),
            'character_icon_scale': getattr(settings, 'character_icon_scale', 1.0),
            'character_icon_offset_x': getattr(settings, 'character_icon_offset_x', 0),
            'character_icon_offset_y': getattr(settings, 'character_icon_offset_y', 0),
            'background_type': settings.background_type,
            'background_color': settings.background_color,
            'background_image_path': settings.background_image_path,
            'bg_image_scale': getattr(settings, 'bg_image_scale', 1.0),
            'bg_image_offset_x': getattr(settings, 'bg_image_offset_x', 0),
            'bg_image_offset_y': getattr(settings, 'bg_image_offset_y', 0),
            'window_transparency_enabled': getattr(settings, 'window_transparency_enabled', False),
            'window_transparency_value': getattr(settings, 'window_transparency_value', 50),
            'window_transparency_mode': getattr(settings, 'window_transparency_mode', 'focus'),
            'window_transparency_time': getattr(settings, 'window_transparency_time', 3),
        }

    def _detect_chat_changes(self, old_settings, new_settings):
        """Detect exactly what changed between old and new chat settings"""
        changes = {}
        
        # Check user icon changes
        user_icon_changed = (
            old_settings['user_icon_path'] != new_settings.user_icon_path or
            old_settings['user_icon_scale'] != getattr(new_settings, 'user_icon_scale', 1.0) or
            old_settings['user_icon_offset_x'] != getattr(new_settings, 'user_icon_offset_x', 0) or
            old_settings['user_icon_offset_y'] != getattr(new_settings, 'user_icon_offset_y', 0)
        )
        changes['user_icon_changed'] = user_icon_changed
        
        # Check character icon changes
        character_icon_changed = (
            old_settings['character_icon_path'] != new_settings.character_icon_path or
            old_settings['character_icon_scale'] != getattr(new_settings, 'character_icon_scale', 1.0) or
            old_settings['character_icon_offset_x'] != getattr(new_settings, 'character_icon_offset_x', 0) or
            old_settings['character_icon_offset_y'] != getattr(new_settings, 'character_icon_offset_y', 0)
        )
        changes['character_icon_changed'] = character_icon_changed
        
        # Check background changes
        background_changed = (
            old_settings['background_type'] != new_settings.background_type or
            old_settings['background_color'] != new_settings.background_color or
            old_settings['background_image_path'] != new_settings.background_image_path or
            old_settings['bg_image_scale'] != getattr(new_settings, 'bg_image_scale', 1.0) or
            old_settings['bg_image_offset_x'] != getattr(new_settings, 'bg_image_offset_x', 0) or
            old_settings['bg_image_offset_y'] != getattr(new_settings, 'bg_image_offset_y', 0)
        )
        changes['background_changed'] = background_changed
        
        # Check transparency changes
        transparency_changed = (
            old_settings['window_transparency_enabled'] != getattr(new_settings, 'window_transparency_enabled', False) or
            old_settings['window_transparency_value'] != getattr(new_settings, 'window_transparency_value', 50) or
            old_settings['window_transparency_mode'] != getattr(new_settings, 'window_transparency_mode', 'focus') or
            old_settings['window_transparency_time'] != getattr(new_settings, 'window_transparency_time', 3)
        )
        changes['transparency_changed'] = transparency_changed
        
        return changes

    def _apply_selective_chat_refresh(self, changes):
        """Apply only the specific refreshes needed - SIMPLE VERSION"""
        try:
            icon_updated = False
            
            # Only refresh user icon if it changed
            if changes['user_icon_changed']:
                print("🔄 Refreshing user icon...")
                # Clear caches
                if hasattr(self, 'icon_cache'):
                    self.icon_cache.clear()
                QPixmapCache.clear()
                
                self.user_icon = self._load_icon(
                    self.chat_settings.user_icon_path,
                    getattr(self.chat_settings, 'user_icon_scale', 1.0),
                    getattr(self.chat_settings, 'user_icon_offset_x', 0),
                    getattr(self.chat_settings, 'user_icon_offset_y', 0),
                    force_refresh=True
                )
                icon_updated = True
                print("✅ User icon refreshed")
            
            # Only refresh character icon if it changed
            if changes['character_icon_changed']:
                print("🔄 Refreshing character icon...")
                if not changes['user_icon_changed']:  # Don't clear cache twice
                    if hasattr(self, 'icon_cache'):
                        self.icon_cache.clear()
                    QPixmapCache.clear()
                
                self.character_icon = self._load_icon(
                    self.chat_settings.character_icon_path,
                    getattr(self.chat_settings, 'character_icon_scale', 1.0),
                    getattr(self.chat_settings, 'character_icon_offset_x', 0),
                    getattr(self.chat_settings, 'character_icon_offset_y', 0),
                    force_refresh=True
                )
                icon_updated = True
                print("✅ Character icon refreshed")
            
            # Force immediate icon update
            if icon_updated:
                print("🔄 Forcing immediate bubble icon update...")
                self._force_update_bubble_icons_immediately(changes)
            
            # Only refresh background if it changed
            if changes['background_changed']:
                print("🔄 Background changed - refreshing...")
                # Simple refresh - no complex caching
                self._apply_chat_background()
                print("✅ Background refreshed")
            
        except Exception as e:
            print(f"❌ Error in selective refresh: {e}")
            # Simple fallback
            try:
                self._apply_chat_background()
            except:
                pass


    def _force_update_bubble_icons_immediately(self, changes):
        """Force immediate icon update by recreating icon widgets"""
        try:
            for bubble in self.bubble_widgets.values():
                try:
                    # Find and update icon labels more aggressively
                    for child in bubble.findChildren(QLabel):
                        # Look for the icon label (usually has a pixmap)
                        if child.pixmap() and not child.pixmap().isNull():
                            # This is likely an icon label
                            if hasattr(bubble, 'is_user'):
                                if bubble.is_user and changes.get('user_icon_changed'):
                                    if self.user_icon and not self.user_icon.isNull():
                                        child.setPixmap(self.user_icon)
                                        child.repaint()
                                elif not bubble.is_user and changes.get('character_icon_changed'):
                                    if self.character_icon and not self.character_icon.isNull():
                                        child.setPixmap(self.character_icon)
                                        child.repaint()
                            break  # Only update the first icon label found
                    
                except Exception as e:
                    print(f"Error updating bubble icon: {e}")
                    continue
            
            # Force complete repaint of chat area
            self.chat_area.update()
            self.chat_area.repaint()
            print("✅ Forced immediate icon update complete")
            
        except Exception as e:
            print(f"Error in force icon update: {e}")

    def _update_user_icon_bubbles_only(self):
        """Update ONLY user icon in existing bubbles - don't recreate bubbles"""
        try:
            for bubble in self.bubble_widgets.values():
                if hasattr(bubble, 'is_user') and bubble.is_user:
                    if hasattr(bubble, 'icon_label') and bubble.icon_label:
                        # Update icon without recreating bubble
                        if self.user_icon and not self.user_icon.isNull():
                            bubble.icon_label.setPixmap(self.user_icon)
        except Exception as e:
            print(f"Error updating user icons: {e}")

    def _update_character_icon_bubbles_only(self):
        """Update ONLY character icon in existing bubbles - don't recreate bubbles"""
        try:
            for bubble in self.bubble_widgets.values():
                if hasattr(bubble, 'is_user') and not bubble.is_user:
                    if hasattr(bubble, 'icon_label') and bubble.icon_label:
                        # Update icon without recreating bubble
                        if self.character_icon and not self.character_icon.isNull():
                            bubble.icon_label.setPixmap(self.character_icon)
        except Exception as e:
            print(f"Error updating character icons: {e}")






    def _open_chat_settings(self):
        """Open chat appearance settings with smart refresh - PREVENTS BUBBLE DISAPPEARING"""
        # Store old settings for comparison
        old_settings = self._copy_chat_settings(self.chat_settings)
        
        dialog = ChatSettingsDialog(self, self.character.name, self.chat_settings)
        if dialog.exec():
            # Update settings
            new_settings = dialog.settings
            self.chat_settings = new_settings
            
            print("💾 Applying chat settings with smart refresh...")
            
            # SMART: Only refresh what actually changed
            changes = self._detect_chat_changes(old_settings, new_settings)
            self._apply_selective_chat_refresh(changes)
            
            # Setup transparency (only if transparency settings changed)
            if changes.get('transparency_changed'):
                self._setup_transparency()
            
            print("✅ Chat settings applied with smart refresh")

    def _copy_settings(self, settings):
        """Create a copy of settings for comparison"""
        return {
            'user_icon_path': settings.user_icon_path,
            'character_icon_path': settings.character_icon_path,
            'user_icon_scale': getattr(settings, 'user_icon_scale', 1.0),
            'user_icon_offset_x': getattr(settings, 'user_icon_offset_x', 0),
            'user_icon_offset_y': getattr(settings, 'user_icon_offset_y', 0),
            'character_icon_scale': getattr(settings, 'character_icon_scale', 1.0),
            'character_icon_offset_x': getattr(settings, 'character_icon_offset_x', 0),
            'character_icon_offset_y': getattr(settings, 'character_icon_offset_y', 0),
            'background_type': settings.background_type,
            'background_color': settings.background_color,
            'background_image_path': settings.background_image_path,
            'bg_image_scale': getattr(settings, 'bg_image_scale', 1.0),
            'bg_image_offset_x': getattr(settings, 'bg_image_offset_x', 0),
            'bg_image_offset_y': getattr(settings, 'bg_image_offset_y', 0),
            'window_transparency_enabled': getattr(settings, 'window_transparency_enabled', False),
            'window_transparency_value': getattr(settings, 'window_transparency_value', 50),
            'window_transparency_mode': getattr(settings, 'window_transparency_mode', 'focus'),
            'window_transparency_time': getattr(settings, 'window_transparency_time', 3),
        }

    def _detect_changes(self, old_settings, new_settings):
        """Detect exactly what changed between old and new settings"""
        changes = {}
        
        # Check user icon changes
        user_icon_changed = (
            old_settings['user_icon_path'] != new_settings.user_icon_path or
            old_settings['user_icon_scale'] != getattr(new_settings, 'user_icon_scale', 1.0) or
            old_settings['user_icon_offset_x'] != getattr(new_settings, 'user_icon_offset_x', 0) or
            old_settings['user_icon_offset_y'] != getattr(new_settings, 'user_icon_offset_y', 0)
        )
        changes['user_icon_changed'] = user_icon_changed
        
        # Check character icon changes
        character_icon_changed = (
            old_settings['character_icon_path'] != new_settings.character_icon_path or
            old_settings['character_icon_scale'] != getattr(new_settings, 'character_icon_scale', 1.0) or
            old_settings['character_icon_offset_x'] != getattr(new_settings, 'character_icon_offset_x', 0) or
            old_settings['character_icon_offset_y'] != getattr(new_settings, 'character_icon_offset_y', 0)
        )
        changes['character_icon_changed'] = character_icon_changed
        
        # Check background changes
        background_changed = (
            old_settings['background_type'] != new_settings.background_type or
            old_settings['background_color'] != new_settings.background_color or
            old_settings['background_image_path'] != new_settings.background_image_path or
            old_settings['bg_image_scale'] != getattr(new_settings, 'bg_image_scale', 1.0) or
            old_settings['bg_image_offset_x'] != getattr(new_settings, 'bg_image_offset_x', 0) or
            old_settings['bg_image_offset_y'] != getattr(new_settings, 'bg_image_offset_y', 0)
        )
        changes['background_changed'] = background_changed
        
        # Check transparency changes
        transparency_changed = (
            old_settings['window_transparency_enabled'] != getattr(new_settings, 'window_transparency_enabled', False) or
            old_settings['window_transparency_value'] != getattr(new_settings, 'window_transparency_value', 50) or
            old_settings['window_transparency_mode'] != getattr(new_settings, 'window_transparency_mode', 'focus') or
            old_settings['window_transparency_time'] != getattr(new_settings, 'window_transparency_time', 3)
        )
        changes['transparency_changed'] = transparency_changed
        
        return changes

    def _apply_selective_refresh(self, changes):
        """Apply only the specific refreshes needed based on what changed"""
        try:
            refresh_bubbles = False
            
            # Only refresh user icon if it changed
            if changes['user_icon_changed']:
                print("🔄 Refreshing user icon...")
                self.icon_cache.clear()
                self.user_icon = self._load_icon(
                    self.chat_settings.user_icon_path,
                    getattr(self.chat_settings, 'user_icon_scale', 1.0),
                    getattr(self.chat_settings, 'user_icon_offset_x', 0),
                    getattr(self.chat_settings, 'user_icon_offset_y', 0),
                    force_refresh=True
                )
                refresh_bubbles = True
                print("✅ User icon refreshed")
            
            # Only refresh character icon if it changed
            if changes['character_icon_changed']:
                print("🔄 Refreshing character icon...")
                if not changes['user_icon_changed']:  # Don't clear cache twice
                    self.icon_cache.clear()
                self.character_icon = self._load_icon(
                    self.chat_settings.character_icon_path,
                    getattr(self.chat_settings, 'character_icon_scale', 1.0),
                    getattr(self.chat_settings, 'character_icon_offset_x', 0),
                    getattr(self.chat_settings, 'character_icon_offset_y', 0),
                    force_refresh=True
                )
                refresh_bubbles = True
                print("✅ Character icon refreshed")
            
            # Only refresh background if it changed
            if changes['background_changed']:
                print("🔄 Refreshing background...")
                self._apply_chat_background()
                print("✅ Background refreshed")
            
            # Only refresh message bubbles if icons changed
            if refresh_bubbles:
                print("🔄 Refreshing message bubbles...")
                self._refresh_all_message_bubbles()
                print("✅ Message bubbles refreshed")
            
            if not any(changes.values()):
                print("ℹ️ No changes detected - no refresh needed")
            
        except Exception as e:
            print(f"❌ Error in selective refresh: {e}")




    def showEvent(self, event):
        """Handle show event - minimal intervention"""
        super().showEvent(event)
        # Just update geometry, background will be handled by _apply_single_background_setup

    def _ensure_proper_sizing(self):
        """Ensure chat area has proper size - no background reapplication"""
        if hasattr(self, 'chat_area') and self.chat_area.isVisible():
            # Force layout update only
            self.chat_area.updateGeometry()


    def _open_bubble_settings(self):
        """Open bubble customization dialog - ORIGINAL BEHAVIOR (no live updates)"""
        dialog = BubbleSettingsDialog(self, self.character)
        # *** REMOVED: No signal connections for live updates ***
    
        if dialog.exec():
            # IMPORTANT: Update our character reference with the modified character
            self.character = dialog.character
        
            # Force refresh the display ONLY after dialog closes
            self._refresh_display()
        
            # Notify parent to update the character as well
            parent = self.parent()
            if parent and hasattr(parent, 'current_character'):
                if parent.current_character and parent.current_character.name == self.character.name:
                    parent.current_character = self.character
                    print(f"✅ Updated main character object")
    
    def _open_dialog_manager(self):
        """Open scheduled dialog manager"""
        dialog = DialogManagerWindow(self, self.character, self.scheduled_dialogs)
        dialog.exec()
    
