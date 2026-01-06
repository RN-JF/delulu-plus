"""UI Dialogs"""
from ..common_imports import *
from ..models.api_config import APIConfig, ExternalAPI
from ..models.character import CharacterConfig, IconSettings, BackgroundImageSettings, Interaction
from ..models.user_profile import UserProfile, UserSettings
from ..models.chat_models import ChatMessage, ChatSettings, ScheduledDialog
from ..models.ui_models import AppColors, app_colors
from ..utils.file_manager import get_app_data_dir, CharacterManager, UserProfileManager
from ..utils.helpers import hex_to_rgba, safe_copy_file, force_reload_image
from ..core.ai_interface import EnhancedAIInterface, get_context_size_for_model

class APIConfigManager(QDialog):
    """Dialog for managing API configurations"""
    
    def __init__(self, parent, ai_interface):
        super().__init__(parent)
        self.ai_interface = ai_interface
        self.setWindowTitle("API Configuration Manager")
        self.setFixedSize(900, 600)
        self.setModal(True)
        
        self._setup_ui()
        self._load_configs()
    
    def _setup_ui(self):
        """Setup the UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title
        title = QLabel("🔧 API Configuration Manager")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 10px;")
        layout.addWidget(title)
        
        # Toolbar
        toolbar = QHBoxLayout()
        
        self.add_btn = QPushButton("➕ Add New")
        self.add_btn.clicked.connect(self._add_config)
        toolbar.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("✏️ Edit")
        self.edit_btn.clicked.connect(self._edit_config)
        toolbar.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("🗑️ Delete")
        self.delete_btn.clicked.connect(self._delete_config)
        toolbar.addWidget(self.delete_btn)
        
        self.test_btn = QPushButton("🧪 Test")
        self.test_btn.clicked.connect(self._test_config)
        toolbar.addWidget(self.test_btn)
        
        toolbar.addStretch()
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._load_configs)
        toolbar.addWidget(self.refresh_btn)
        
        layout.addLayout(toolbar)
        
        # Config list
        self.config_list = QTreeWidget()
        self.config_list.setHeaderLabels([
            "Name", "Provider", "Model", "Temperature", "Max Tokens", "Status"
        ])
        layout.addWidget(self.config_list)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _load_configs(self):
        """Load configurations into the list"""
        self.config_list.clear()
        self.ai_interface.load_all_configs()
        
        for name, config in self.ai_interface.api_configs.items():
            item = QTreeWidgetItem([
                config.name,
                config.provider.upper(),
                config.model,
                f"{config.temperature}",
                f"{config.max_tokens}",
                "✅ Enabled" if config.enabled else "❌ Disabled"
            ])
            
            if name == self.ai_interface.default_config:
                for col in range(6):
                    item.setBackground(col, QColor("#070000"))
            
            self.config_list.addTopLevelItem(item)
    
    def _add_config(self):
        """Add new configuration"""
        dialog = APIConfigDialog(self, None)
        if dialog.exec():
            config = dialog.get_config()
            self._save_config(config)
            self._load_configs()
    
    def _edit_config(self):
        """Edit selected configuration"""
        current = self.config_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a configuration to edit.")
            return
        
        config_name = current.text(0)
        config_file = self.ai_interface.configs_dir / f"{config_name}.json"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                config = APIConfig(**data)
            
            dialog = APIConfigDialog(self, config)
            if dialog.exec():
                new_config = dialog.get_config()
                
                # Delete old config file if name changed
                if new_config.name != config_name:
                    config_file.unlink()
                
                self._save_config(new_config)
                self._load_configs()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading configuration: {str(e)}")
    
    def _delete_config(self):
        """Delete selected configuration"""
        current = self.config_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a configuration to delete.")
            return
        
        config_name = current.text(0)
        
        reply = QMessageBox.question(self, "Delete Configuration",
                                   f"Are you sure you want to delete '{config_name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            config_file = self.ai_interface.configs_dir / f"{config_name}.json"
            if config_file.exists():
                config_file.unlink()
                self._load_configs()
    
    def _test_config(self):
        """Test selected configuration"""
        current = self.config_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a configuration to test.")
            return
        
        config_name = current.text(0)
        
        # Create progress dialog
        progress = QProgressDialog("Testing API configuration...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            test_messages = [{"role": "user", "content": "Hello, please respond with 'Test successful'"}]
            response = self.ai_interface.get_response(test_messages, "You are a helpful assistant.", config_name)
            
            progress.close()
            
            if "error" in response.lower():
                QMessageBox.critical(self, "Test Failed", f"❌ Test failed!\n\nResponse: {response}")
            else:
                QMessageBox.information(self, "Test Result", f"✅ Test successful!\n\nResponse: {response[:200]}{'...' if len(response) > 200 else ''}")
            
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Test Failed", f"❌ Test failed!\n\nError: {str(e)}")
    
    def _save_config(self, config: APIConfig):
        """Save configuration to file"""
        config_file = self.ai_interface.configs_dir / f"{config.name}.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(config), f, indent=2)


class AboutDialog(QDialog):
    """About / Welcome dialog shown on startup (optional)."""

    def __init__(self, parent=None, *, show_on_startup: bool = True):
        super().__init__(parent)
        self.setWindowTitle("About Delulu+")
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header (icon + title)
        header = QHBoxLayout()
        header.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("border-radius: 8px;")
        try:
            # icon.png lives in src/assets/
            assets_dir = Path(__file__).resolve().parent.parent / "assets"
            icon_path = assets_dir / "icon.png"
            if icon_path.exists():
                pix = QPixmap(str(icon_path))
                icon_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        except Exception:
            pass

        header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title = QLabel("Delulu+")
        title.setStyleSheet("font-size: 16pt; font-weight: bold;")
        subtitle = QLabel("A character chat / assistant app")
        subtitle.setStyleSheet("opacity: 0.85;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        title_box.addStretch(1)

        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        # Body text (EDIT THIS)
        body = QLabel(
            "Hi, I’m <b>RN</b>.<br>"
            "This app helps you chat with your characters, manage profiles, and schedule Reminders.<br><br>"
            "Support the project:"
            " <a href='https://ko-fi.com/rn_jf'>Ko-fi link</a>"
        )
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setOpenExternalLinks(True)
        layout.addWidget(body)

        # Startup checkbox
        self.dont_show_checkbox = QCheckBox("Don’t show this again on startup")
        self.dont_show_checkbox.setChecked(not bool(show_on_startup))
        layout.addWidget(self.dont_show_checkbox)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

    @property
    def show_on_startup(self) -> bool:
        return not self.dont_show_checkbox.isChecked()
















class InteractionEditDialog(QDialog):
    """Dialog for editing interactions"""
    def __init__(self, parent, interaction: Optional[Interaction] = None):
        super().__init__(parent)
        
        self.interaction = interaction
        self.result = None
        
        # Initialize paths with validation
        self.icon_path = None
        self.base_image_path = None
        
        if interaction:
            # Validate and resolve paths when editing existing interaction
            if interaction.icon_path:
                # Try to resolve the icon path
                resolved_path = self._resolve_interaction_path(interaction.icon_path, interaction.name, "icon")
                if resolved_path and os.path.exists(resolved_path):
                    self.icon_path = resolved_path
                    print(f"✅ Resolved icon path: {resolved_path}")
                else:
                    print(f"⚠️ Could not resolve icon path: {interaction.icon_path}")
            
            if interaction.base_image_path:
                # Try to resolve the base image path
                resolved_path = self._resolve_interaction_path(interaction.base_image_path, interaction.name, "base")
                if resolved_path and os.path.exists(resolved_path):
                    self.base_image_path = resolved_path
                    print(f"✅ Resolved base image path: {resolved_path}")
                else:
                    print(f"⚠️ Could not resolve base image path: {interaction.base_image_path}")
        
        self.setWindowTitle("Edit Interaction" if interaction else "New Interaction")
        self.setFixedSize(400, 350)
        self.setModal(True)
        
        self._setup_ui()
    


    def _resolve_interaction_path(self, original_path: str, interaction_name: str, image_type: str) -> str:
        """Resolve interaction image path using multiple strategies"""
        
        # Strategy 1: Use original path if it exists and is absolute
        if os.path.isabs(original_path) and os.path.exists(original_path):
            return original_path
        
        # Strategy 2: Try relative to interaction directory
        try:
            interaction_dir = self.parent().character_manager.characters_dir / self.parent().current_character.name / "interactions" / interaction_name
            
            # Try original filename in interaction directory
            relative_path = interaction_dir / os.path.basename(original_path)
            if relative_path.exists():
                return str(relative_path)
            
            # Try standard naming convention
            for ext in ['.png', '.jpg', '.jpeg', '.gif']:
                standard_path = interaction_dir / f"{image_type}{ext}"
                if standard_path.exists():
                    return str(standard_path)
                    
        except Exception as e:
            print(f"Error resolving path: {e}")
        
        # Strategy 3: Try the original path as-is (might be relative)
        if os.path.exists(original_path):
            return os.path.abspath(original_path)
        
        return None




    def _setup_ui(self):
        """Create the interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit(self.interaction.name if self.interaction else "")
        form_layout.addRow("Name:", self.name_edit)
        
        # Icon
        icon_layout = QHBoxLayout()
        self.icon_label = QLabel("No icon selected")
        self.icon_label.setFixedSize(100, 50)
        self.icon_label.setStyleSheet("background-color: none; border: 1px solid #ddd;")
        self.icon_label.setAlignment(Qt.AlignCenter)
        icon_layout.addWidget(self.icon_label)
        
        icon_btn = QPushButton("Select")
        icon_btn.clicked.connect(self._select_icon)
        icon_layout.addWidget(icon_btn)
        icon_layout.addStretch()
        
        form_layout.addRow("Icon:", icon_layout)
        
        # Base Image
        image_layout = QHBoxLayout()
        self.image_label = QLabel("No image selected")
        self.image_label.setFixedSize(100, 50)
        self.image_label.setStyleSheet("background-color: none; border: 1px solid #ddd;")
        self.image_label.setAlignment(Qt.AlignCenter)
        image_layout.addWidget(self.image_label)
        
        image_btn = QPushButton("Select")
        image_btn.clicked.connect(self._select_base_image)
        image_layout.addWidget(image_btn)
        image_layout.addStretch()
        
        form_layout.addRow("Base Image:", image_layout)
        
        # Duration
        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 60)
        self.duration_spin.setValue(self.interaction.duration if self.interaction else 3)
        self.duration_spin.setSuffix(" seconds")
        form_layout.addRow("Duration:", self.duration_spin)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._save)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Load existing previews
        if self.interaction:
            self._load_previews()
    
    def _save(self):
        """Save the interaction"""
        name = self.name_edit.text().strip()
        duration = self.duration_spin.value()
        
        if not name:
            QMessageBox.critical(self, "Error", "Please enter an interaction name.")
            return
            
        if not self.icon_path:
            QMessageBox.critical(self, "Error", "Please select an icon image.")
            return
            
        if not self.base_image_path:
            QMessageBox.critical(self, "Error", "Please select a base image.")
            return
        
        # Validate that files exist
        if not os.path.exists(self.icon_path):
            QMessageBox.critical(self, "Error", f"Icon file not found: {self.icon_path}")
            return
            
        if not os.path.exists(self.base_image_path):
            QMessageBox.critical(self, "Error", f"Base image file not found: {self.base_image_path}")
            return
        
        # Create result
        position = self.interaction.position if self.interaction else (50, 50)
        
        self.result = Interaction(
            name=name,
            icon_path=self.icon_path,
            base_image_path=self.base_image_path,
            duration=duration,
            position=position
        )
        
        self.accept()

    def _select_base_image(self):
        """Select base image for interaction - IMPROVED VERSION"""
        # Start from current directory if image exists
        start_dir = ""
        if self.base_image_path and os.path.exists(self.base_image_path):
            start_dir = os.path.dirname(self.base_image_path)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Base Image",
            start_dir,
            "Image files (*.png *.jpg *.jpeg *.gif);;All files (*.*)"
        )
        
        if filename:
            # Validate the file exists and is readable
            try:
                if filename.lower().endswith('.gif'):
                    # Test GIF loading
                    test_image = Image.open(filename)
                    test_image.close()
                else:
                    test_pixmap = QPixmap(filename)
                    if test_pixmap.isNull():
                        QMessageBox.critical(self, "Error", "Invalid image file or corrupted.")
                        return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot read image file: {str(e)}")
                return
                
            self.base_image_path = filename
            self.image_label.setText(os.path.basename(filename))
            print(f"Selected base image: {filename}")

    def _load_previews(self):
        """Load existing icon and image previews with better path resolution"""
        
        # Handle icon path
        if self.icon_path:
            # Try multiple path resolution strategies
            paths_to_try = [
                self.icon_path,  # Original path
                os.path.abspath(self.icon_path),  # Absolute version
            ]
            
            # If interaction exists, try relative to interaction directory
            if self.interaction:
                interaction_dir = self.parent().character_manager.characters_dir / self.parent().current_character.name / "interactions" / self.interaction.name
                paths_to_try.append(str(interaction_dir / os.path.basename(self.icon_path)))
                paths_to_try.append(str(interaction_dir / "icon.png"))
                paths_to_try.append(str(interaction_dir / "icon.jpg"))
                paths_to_try.append(str(interaction_dir / "icon.jpeg"))
            
            icon_found = False
            for path in paths_to_try:
                if path and os.path.exists(path):
                    try:
                        pixmap = QPixmap(path)
                        if not pixmap.isNull():
                            scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                            self.icon_label.setPixmap(scaled)
                            self.icon_label.setText("")
                            self.icon_path = path  # Update to working path
                            print(f"✅ Icon loaded from: {path}")
                            icon_found = True
                            break
                    except Exception as e:
                        print(f"⚠️ Failed to load icon from {path}: {e}")
                        continue
            
            if not icon_found:
                print(f"❌ Icon not found. Tried paths: {paths_to_try}")
                self.icon_label.setText("No icon selected")
                self.icon_path = None
        
        # Handle base image path
        if self.base_image_path:
            paths_to_try = [
                self.base_image_path,  # Original path
                os.path.abspath(self.base_image_path),  # Absolute version
            ]
            
            # If interaction exists, try relative to interaction directory
            if self.interaction:
                interaction_dir = self.parent().character_manager.characters_dir / self.parent().current_character.name / "interactions" / self.interaction.name
                paths_to_try.append(str(interaction_dir / os.path.basename(self.base_image_path)))
                paths_to_try.append(str(interaction_dir / "base.png"))
                paths_to_try.append(str(interaction_dir / "base.jpg"))
                paths_to_try.append(str(interaction_dir / "base.jpeg"))
                paths_to_try.append(str(interaction_dir / "base.gif"))
            
            base_found = False
            for path in paths_to_try:
                if path and os.path.exists(path):
                    try:
                        # Test if it's a valid image
                        if path.lower().endswith('.gif'):
                            test_image = Image.open(path)
                            test_image.close()
                        else:
                            test_pixmap = QPixmap(path)
                            if test_pixmap.isNull():
                                continue
                        
                        self.image_label.setText(os.path.basename(path))
                        self.base_image_path = path  # Update to working path
                        print(f"✅ Base image loaded from: {path}")
                        base_found = True
                        break
                    except Exception as e:
                        print(f"⚠️ Failed to load base image from {path}: {e}")
                        continue
            
            if not base_found:
                print(f"❌ Base image not found. Tried paths: {paths_to_try}")
                self.image_label.setText("No image selected")
                self.base_image_path = None



    def _select_icon(self):
        """Select interaction icon - IMPROVED VERSION"""
        # Start from current directory if icon exists
        start_dir = ""
        if self.icon_path and os.path.exists(self.icon_path):
            start_dir = os.path.dirname(self.icon_path)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Icon Image",
            start_dir,
            "Image files (*.png *.jpg *.jpeg *.gif);;All files (*.*)"
        )
        
        if filename:
            # Validate the file exists and is readable
            try:
                test_pixmap = QPixmap(filename)
                if test_pixmap.isNull():
                    QMessageBox.critical(self, "Error", "Invalid image file or corrupted.")
                    return
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Cannot read image file: {str(e)}")
                return
                
            self.icon_path = filename
            print(f"Selected icon: {filename}")
            
            try:
                pixmap = QPixmap(filename)
                scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.icon_label.setPixmap(scaled)
                self.icon_label.setText("")
            except Exception as e:
                print(f"Error displaying preview: {e}")
                self.icon_label.setText("Preview failed")

class DialogManagerWindow(QDialog):
    """Window for managing scheduled dialogs"""
    def __init__(self, parent, character: CharacterConfig, dialogs: List[ScheduledDialog]):
        super().__init__(parent)
        
        self.character = character
        self.dialogs = dialogs
        
        self.setWindowTitle(f"Scheduled Dialogs - {character.name}")
        self.resize(600, 400)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_list()
    
    def _setup_ui(self):
        """Create the dialog manager interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Name", "Time", "Prompt", "Enabled"])
        self.tree.setColumnWidth(0, 150)
        self.tree.setColumnWidth(1, 80)
        self.tree.setColumnWidth(2, 250)
        self.tree.setColumnWidth(3, 80)
        layout.addWidget(self.tree)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_dialog)
        button_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self._edit_dialog)
        button_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self._delete_dialog)
        button_layout.addWidget(delete_btn)
        
        toggle_btn = QPushButton("Toggle")
        toggle_btn.clicked.connect(self._toggle_dialog)
        button_layout.addWidget(toggle_btn)
        
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_dialogs)
        button_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _populate_list(self):
        """Populate the tree widget with dialogs"""
        self.tree.clear()
        
        for dialog in self.dialogs:
            item = QTreeWidgetItem([
                dialog.name,
                dialog.time,
                dialog.prompt[:50] + "..." if len(dialog.prompt) > 50 else dialog.prompt,
                "Yes" if dialog.enabled else "No"
            ])
            self.tree.addTopLevelItem(item)
    
    def _add_dialog(self):
        """Add a new scheduled dialog"""
        dialog = DialogEditWindow(self, None)
        if dialog.exec():
            self.dialogs.append(dialog.result)
            self._populate_list()
    
    def _edit_dialog(self):
        """Edit selected dialog"""
        current = self.tree.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a dialog to edit.")
            return
        
        index = self.tree.indexOfTopLevelItem(current)
        dialog = DialogEditWindow(self, self.dialogs[index])
        if dialog.exec():
            self.dialogs[index] = dialog.result
            self._populate_list()
    
    def _delete_dialog(self):
        """Delete selected dialog"""
        current = self.tree.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a dialog to delete.")
            return
        
        reply = QMessageBox.question(self, "Delete Dialog", 
                                   "Are you sure you want to delete this dialog?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            index = self.tree.indexOfTopLevelItem(current)
            del self.dialogs[index]
            self._populate_list()
    
    def _toggle_dialog(self):
        """Toggle enabled state of selected dialog"""
        current = self.tree.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a dialog to toggle.")
            return
        
        index = self.tree.indexOfTopLevelItem(current)
        self.dialogs[index].enabled = not self.dialogs[index].enabled
        self._populate_list()
    
    def _save_dialogs(self):
        """Save dialogs to file"""
        app_data_dir = get_app_data_dir()
        dialog_file = app_data_dir / "characters" / self.character.name / "scheduled_dialogs.json"
        dialog_file.parent.mkdir(parents=True, exist_ok=True)
        dialog_file.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(dialog_file, 'w', encoding='utf-8') as f:
                data = [asdict(d) for d in self.dialogs]
                json.dump(data, f, indent=2)
            QMessageBox.information(self, "Success", "Dialogs saved successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save dialogs: {str(e)}")

class DialogEditWindow(QDialog):
    """Window for editing a single dialog"""
    def __init__(self, parent, dialog: Optional[ScheduledDialog]):
        super().__init__(parent)
        
        self.dialog = dialog
        self.result = None
        
        self.setWindowTitle("Edit Dialog" if dialog else "New Dialog")
        self.setFixedSize(400, 400)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the edit interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Name
        self.name_edit = QLineEdit(self.dialog.name if self.dialog else "")
        form_layout.addRow("Name:", self.name_edit)
        
        # Time
        self.time_edit = QLineEdit(self.dialog.time if self.dialog else "")
        self.time_edit.setPlaceholderText("HH:MM")
        form_layout.addRow("Time:", self.time_edit)
        
        # Prompt
        self.prompt_edit = QTextEdit()
        if self.dialog:
            self.prompt_edit.setPlainText(self.dialog.prompt)
        form_layout.addRow("Prompt:", self.prompt_edit)
        
        layout.addLayout(form_layout)
        
        # Specific date checkbox
        self.use_date_check = QCheckBox("Schedule on specific date")
        self.use_date_check.setChecked(bool(self.dialog and self.dialog.date))
        self.use_date_check.toggled.connect(self._toggle_date_fields)
        layout.addWidget(self.use_date_check)
        
        # Date fields
        self.date_widget = QWidget()
        date_layout = QFormLayout()
        
        self.date_edit = QLineEdit(self.dialog.date if self.dialog and self.dialog.date else "")
        self.date_edit.setPlaceholderText("YYYY-MM-DD")
        date_layout.addRow("Specific Date:", self.date_edit)
        
        self.advance_spin = QSpinBox()
        self.advance_spin.setRange(0, 30)
        self.advance_spin.setValue(self.dialog.advance_days if self.dialog else 0)
        date_layout.addRow("Remind Days Before:", self.advance_spin)
        
        self.date_widget.setLayout(date_layout)
        layout.addWidget(self.date_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._save)
        button_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initial visibility
        self._toggle_date_fields()
    
    def _toggle_date_fields(self):
        """Show/hide date fields"""
        self.date_widget.setVisible(self.use_date_check.isChecked())
    
    def _save(self):
        """Save the dialog"""
        name = self.name_edit.text().strip()
        time = self.time_edit.text().strip()
        prompt = self.prompt_edit.toPlainText().strip()
        
        if not name or not time or not prompt:
            QMessageBox.critical(self, "Error", "Name, time, and prompt are required.")
            return
        
        date = None
        advance_days = 0
        
        if self.use_date_check.isChecked():
            date = self.date_edit.text().strip()
            advance_days = self.advance_spin.value()
            
            if date:
                try:
                    datetime.strptime(date, "%Y-%m-%d")
                except ValueError:
                    QMessageBox.critical(self, "Error", "Invalid date format. Use YYYY-MM-DD.")
                    return
        
        self.result = ScheduledDialog(
            name=name,
            prompt=prompt,
            time=time,
            enabled=self.dialog.enabled if self.dialog else True,
            date=date,
            advance_days=advance_days
        )
        
        self.accept()




class ChatSettingsDialog(QDialog):
    """Dialog for chat appearance settings - UPDATED"""
    def __init__(self, parent, character_name: str, current_settings: ChatSettings):
        super().__init__(parent)
        
        self.character_name = character_name
        self.settings = current_settings
        
        # Fix empty background color
        if not self.settings.background_color or self.settings.background_color == "":
            self.settings.background_color = "#F0F4F8"
        
        self.setWindowTitle("Chat Settings")
        self.setFixedSize(520, 700)  # Increased height for transparency section
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the settings interface - UPDATED"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Create tab widget for better organization
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # ===== APPEARANCE TAB =====
        appearance_widget = QWidget()
        appearance_layout = QVBoxLayout()
        
        # Icons section
        icons_group = QGroupBox("Profile Icons")
        icons_layout = QGridLayout()
        
        # User icon
        icons_layout.addWidget(QLabel("User Icon:"), 0, 0)
        user_icon_layout = QHBoxLayout()
        self.user_icon_label = QLabel("No icon selected")
        self.user_icon_label.setFixedSize(100, 50)
        self.user_icon_label.setStyleSheet("background-color: #F0F0F0; border: 1px solid #ddd;")
        self.user_icon_label.setAlignment(Qt.AlignCenter)
        user_icon_layout.addWidget(self.user_icon_label)
        
        user_icon_btn = QPushButton("Select")
        user_icon_btn.clicked.connect(lambda: self._select_icon("user"))
        user_icon_layout.addWidget(user_icon_btn)
        user_icon_layout.addStretch()
        
        icons_layout.addLayout(user_icon_layout, 0, 1)
        
        # Character icon
        icons_layout.addWidget(QLabel("Character Icon:"), 1, 0)
        char_icon_layout = QHBoxLayout()
        self.char_icon_label = QLabel("No icon selected")
        self.char_icon_label.setFixedSize(100, 50)
        self.char_icon_label.setStyleSheet("background-color: #F0F0F0; border: 1px solid #ddd;")
        self.char_icon_label.setAlignment(Qt.AlignCenter)
        char_icon_layout.addWidget(self.char_icon_label)
        
        char_icon_btn = QPushButton("Select")
        char_icon_btn.clicked.connect(lambda: self._select_icon("character"))
        char_icon_layout.addWidget(char_icon_btn)
        char_icon_layout.addStretch()
        
        icons_layout.addLayout(char_icon_layout, 1, 1)
        
        icons_group.setLayout(icons_layout)
        appearance_layout.addWidget(icons_group)
        
        # Background section
        bg_group = QGroupBox("Chat Background")
        bg_layout = QVBoxLayout()
        
        # Background type
        self.bg_type_color = QRadioButton("Solid Color")
        self.bg_type_image = QRadioButton("Background Image")
        
        if self.settings.background_type == "color":
            self.bg_type_color.setChecked(True)
        else:
            self.bg_type_image.setChecked(True)
        
        self.bg_type_color.toggled.connect(self._toggle_background_options)
        
        type_layout = QHBoxLayout()
        type_layout.addWidget(self.bg_type_color)
        type_layout.addWidget(self.bg_type_image)
        type_layout.addStretch()
        bg_layout.addLayout(type_layout)
        
        # Color option
        self.color_widget = QWidget()
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Background Color:"))
        
        self.color_label = QLabel()
        self.color_label.setFixedSize(60, 30)
        self.color_label.setStyleSheet(f"background-color: {self.settings.background_color}; border: 1px solid black;")
        color_layout.addWidget(self.color_label)
        
        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self._choose_color)
        color_layout.addWidget(color_btn)
        color_layout.addStretch()
        
        self.color_widget.setLayout(color_layout)
        bg_layout.addWidget(self.color_widget)
        
        # Image option
        self.image_widget = QWidget()
        image_layout = QHBoxLayout()
        self.bg_image_label = QLabel("No image selected")
        self.bg_image_label.setFixedSize(150, 30)
        self.bg_image_label.setStyleSheet("background-color: #F0F0F0; border: 1px solid #ddd;")
        self.bg_image_label.setAlignment(Qt.AlignCenter)
        image_layout.addWidget(self.bg_image_label)

        image_btn = QPushButton("Select Image")
        image_btn.clicked.connect(self._select_background_image)
        image_layout.addWidget(image_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_background_image)
        image_layout.addWidget(clear_btn)

        image_layout.addStretch()
        
        self.image_widget.setLayout(image_layout)
        bg_layout.addWidget(self.image_widget)
        
        bg_group.setLayout(bg_layout)
        appearance_layout.addWidget(bg_group)
        
        # Preview section
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel("Background preview will appear here")
        self.preview_label.setFixedHeight(60)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet(f"background-color: {self.settings.background_color}; border: 1px solid #ddd;")
        preview_layout.addWidget(self.preview_label)
        
        preview_group.setLayout(preview_layout)
        appearance_layout.addWidget(preview_group)
        
        appearance_widget.setLayout(appearance_layout)
        tabs.addTab(appearance_widget, "Appearance")
        
        # ===== NEW TRANSPARENCY TAB =====
        transparency_widget = QWidget()
        transparency_layout = QVBoxLayout()
        
        # Window transparency section
        transparency_group = QGroupBox("Window Transparency")
        transparency_group_layout = QVBoxLayout()
        
        # Enable transparency checkbox
        self.transparency_enabled_check = QCheckBox("Enable Chat Window Transparency")
        self.transparency_enabled_check.setChecked(self.settings.window_transparency_enabled)
        self.transparency_enabled_check.toggled.connect(self._toggle_transparency_options)
        transparency_group_layout.addWidget(self.transparency_enabled_check)
        
        # Transparency options container
        self.transparency_options = QWidget()
        options_layout = QVBoxLayout()
        
        # Transparency value slider
        transparency_value_layout = QHBoxLayout()
        transparency_value_layout.addWidget(QLabel("Transparency Level:"))
        
        self.transparency_slider = QSlider(Qt.Horizontal)
        self.transparency_slider.setRange(10, 90)  # 10% to 90% transparency
        self.transparency_slider.setValue(self.settings.window_transparency_value)
        self.transparency_slider.valueChanged.connect(self._update_transparency_label)
        transparency_value_layout.addWidget(self.transparency_slider)
        
        self.transparency_value_label = QLabel(f"{self.settings.window_transparency_value}%")
        self.transparency_value_label.setFixedWidth(40)
        transparency_value_layout.addWidget(self.transparency_value_label)
        
        options_layout.addLayout(transparency_value_layout)
        
        options_layout.addSpacing(10)
        
        # Transparency mode options
        mode_label = QLabel("Transparency Mode:")
        mode_label.setStyleSheet("font-weight: bold;")
        options_layout.addWidget(mode_label)
        
        # Focus mode
        self.focus_mode_radio = QRadioButton("Transparent when window loses focus")
        self.focus_mode_radio.setChecked(self.settings.window_transparency_mode == "focus")
        options_layout.addWidget(self.focus_mode_radio)
        
        # Time mode
        time_mode_layout = QHBoxLayout()
        self.time_mode_radio = QRadioButton("Transparent after")
        self.time_mode_radio.setChecked(self.settings.window_transparency_mode == "time")
        time_mode_layout.addWidget(self.time_mode_radio)
        
        self.time_spin = QSpinBox()
        self.time_spin.setRange(1, 60)
        self.time_spin.setValue(self.settings.window_transparency_time)
        self.time_spin.setSuffix(" minutes")
        time_mode_layout.addWidget(self.time_spin)
        
        time_mode_layout.addWidget(QLabel("of inactivity"))
        time_mode_layout.addStretch()
        
        options_layout.addLayout(time_mode_layout)
        
        # Always mode
        self.always_mode_radio = QRadioButton("Always transparent")
        self.always_mode_radio.setChecked(self.settings.window_transparency_mode == "always")
        options_layout.addWidget(self.always_mode_radio)
        
        options_layout.addSpacing(10)
        
        # Info label
        info_label = QLabel("Note: Transparency will be removed when clicking or typing in the window.")
        info_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic;")
        info_label.setWordWrap(True)
        options_layout.addWidget(info_label)
        
        self.transparency_options.setLayout(options_layout)
        transparency_group_layout.addWidget(self.transparency_options)
        
        transparency_group.setLayout(transparency_group_layout)
        transparency_layout.addWidget(transparency_group)
        
        transparency_layout.addStretch()
        
        transparency_widget.setLayout(transparency_layout)
        tabs.addTab(transparency_widget, "Transparency")
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Load existing settings and setup initial state
        self._load_current_settings()
        self._toggle_background_options()
        self._toggle_transparency_options()
        self._update_preview()


    def _toggle_transparency_options(self):
        """Show/hide transparency options based on checkbox"""
        enabled = self.transparency_enabled_check.isChecked()
        self.transparency_options.setVisible(enabled)
        self.settings.window_transparency_enabled = enabled

    def _update_transparency_label(self, value):
        """Update transparency label"""
        self.transparency_value_label.setText(f"{value}%")
        self.settings.window_transparency_value = value



    def _clear_background_image(self):
        """Clear the current background image"""
        reply = QMessageBox.question(self, "Clear Background", 
                                "Remove the current background image?",
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.background_image_path = ""
            self.settings.bg_image_scale = 1.0
            self.settings.bg_image_offset_x = 0
            self.settings.bg_image_offset_y = 0
            self.bg_image_label.setText("No image selected")
            self._update_preview()
    def _toggle_background_options(self):
        """Show/hide background options based on selection"""
        if self.bg_type_color.isChecked():
            self.color_widget.show()
            self.image_widget.hide()
            self.settings.background_type = "color"
        else:
            self.color_widget.hide()
            self.image_widget.show()
            self.settings.background_type = "image"
        
        self._update_preview()
    

    def _update_preview(self):
        """Update preview"""
        if self.settings.background_type == "image" and self.settings.background_image_path:
            if os.path.exists(self.settings.background_image_path):
                try:
                    # Load original image
                    original_pixmap = QPixmap(self.settings.background_image_path)
                    
                    # Get preview size
                    preview_size = self.preview_label.size()
                    
                    # Calculate scaled dimensions for preview
                    scale = self.settings.bg_image_scale * 0.3  # Scale down for preview
                    scaled_width = int(original_pixmap.width() * scale)
                    scaled_height = int(original_pixmap.height() * scale)
                    
                    # Scale the image
                    scaled_pixmap = original_pixmap.scaled(
                        scaled_width,
                        scaled_height,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation
                    )
                    
                    # Create preview pixmap
                    preview_pixmap = QPixmap(preview_size)
                    preview_pixmap.fill(QColor(self.settings.background_color))
                    
                    # Paint with offset (scaled for preview)
                    painter = QPainter(preview_pixmap)
                    x = (preview_size.width() - scaled_width) // 2 + int(self.settings.bg_image_offset_x * 0.3)
                    y = (preview_size.height() - scaled_height) // 2 + int(self.settings.bg_image_offset_y * 0.3)
                    painter.drawPixmap(x, y, scaled_pixmap)
                    painter.end()
                    
                    self.preview_label.setPixmap(preview_pixmap)
                    self.preview_label.setText("")
                except:
                    self.preview_label.setText("Error loading image")
                    self.preview_label.setStyleSheet("background-color: #FFCCCC; border: 1px solid #ddd;")
            else:
                self.preview_label.setText("Image not found")
                self.preview_label.setStyleSheet("background-color: #FFCCCC; border: 1px solid #ddd;")
        else:
            bg_color = self.settings.background_color or "#F0F4F8"
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Color Background Preview")
            self.preview_label.setStyleSheet(f"background-color: {bg_color}; border: 1px solid #ddd;")
    # Add these methods to your ChatSettingsDialog class after the existing methods:
    def _clear_background_image(self):
        """Clear the current background image"""
        reply = QMessageBox.question(self, "Clear Background", 
                                "Remove the current background image?",
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.background_image_path = ""
            self.settings.bg_image_scale = 1.0
            self.settings.bg_image_offset_x = 0
            self.settings.bg_image_offset_y = 0
            self.bg_image_label.setText("No image selected")
            self._update_preview()


    
    # 5. ADD this new method to ChatSettingsDialog class
    def _save_settings(self):
        """Save settings with proper error handling and path validation"""
        try:
            # Update transparency settings
            self.settings.window_transparency_enabled = self.transparency_enabled_check.isChecked()
            self.settings.window_transparency_value = self.transparency_slider.value()
            self.settings.window_transparency_time = self.time_spin.value()
            
            # Determine transparency mode
            if self.focus_mode_radio.isChecked():
                self.settings.window_transparency_mode = "focus"
            elif self.time_mode_radio.isChecked():
                self.settings.window_transparency_mode = "time"
            else:
                self.settings.window_transparency_mode = "always"
            
            # Validate paths before saving
            app_data_dir = get_app_data_dir()
            char_dir = app_data_dir / "characters" / self.character_name
            
            # Validate that referenced files exist
            validation_errors = []
            
            if self.settings.user_icon_path:
                user_icon_full_path = self._resolve_image_path(self.settings.user_icon_path)
                if not os.path.exists(user_icon_full_path):
                    validation_errors.append(f"User icon not found: {user_icon_full_path}")
            
            if self.settings.character_icon_path:
                char_icon_full_path = self._resolve_image_path(self.settings.character_icon_path)
                if not os.path.exists(char_icon_full_path):
                    validation_errors.append(f"Character icon not found: {char_icon_full_path}")
            
            if (self.settings.background_type == "image" and 
                self.settings.background_image_path):
                bg_full_path = self._resolve_image_path(self.settings.background_image_path)
                if not os.path.exists(bg_full_path):
                    validation_errors.append(f"Background image not found: {bg_full_path}")
            
            if validation_errors:
                error_msg = "File validation errors:\n" + "\n".join(validation_errors)
                reply = QMessageBox.question(
                    self, 
                    "File Validation Errors", 
                    f"{error_msg}\n\nSave anyway? (Missing files will be ignored)",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Save to file
            settings_file = char_dir / "chat_settings.json"
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a clean copy of settings for saving
            settings_dict = asdict(self.settings)
            
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_dict, f, indent=2)
            
            print(f"✅ Chat settings saved to: {settings_file}")
            self.accept()
            
        except Exception as e:
            error_msg = f"Failed to save settings: {str(e)}"
            print(f"❌ {error_msg}")
            QMessageBox.critical(self, "Save Error", error_msg)



    # 3. FIX ChatSettingsDialog._select_background_image method (around line 2900)
    def _select_background_image(self):
        """Select background image with improved handling"""
        # Start with current settings if they exist
        current_settings = None
        if (self.settings.background_image_path and 
            os.path.exists(self._resolve_image_path(self.settings.background_image_path))):
            current_settings = BackgroundImageSettings(
                image_path=self._resolve_image_path(self.settings.background_image_path),
                scale=getattr(self.settings, 'bg_image_scale', 1.0),
                offset_x=getattr(self.settings, 'bg_image_offset_x', 0),
                offset_y=getattr(self.settings, 'bg_image_offset_y', 0)
            )
        
        # Open the background selector dialog
        dialog = BackgroundImageDialog(self, current_settings)
        
        if dialog.exec() and dialog.settings:
            try:
                # Create backgrounds directory
                app_data_dir = get_app_data_dir()
                char_dir = app_data_dir / "characters" / self.character_name
                backgrounds_dir = char_dir / "backgrounds"
                backgrounds_dir.mkdir(exist_ok=True)
                
                # Prepare target path
                source_path = dialog.settings.image_path
                file_ext = os.path.splitext(source_path)[1]
                target_filename = f"background{file_ext}"
                target_path = backgrounds_dir / target_filename
                
                # Use safe copy function
                if safe_copy_file(source_path, str(target_path)):
                    # Store relative path and settings
                    relative_path = f"backgrounds/{target_filename}"
                    self.settings.background_image_path = relative_path
                    self.settings.bg_image_scale = dialog.settings.scale
                    self.settings.bg_image_offset_x = dialog.settings.offset_x
                    self.settings.bg_image_offset_y = dialog.settings.offset_y
                    
                    self.bg_image_label.setText(os.path.basename(source_path))
                    self._update_preview()
                else:
                    QMessageBox.critical(self, "Error", "Failed to save background image.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to set background: {str(e)}")


    def _resolve_image_path(self, path: str) -> str:
        """Convert relative path to absolute path with validation"""
        if not path:
            return ""
            
        if os.path.isabs(path):
            return path
        
        # Resolve relative to character directory
        app_data_dir = get_app_data_dir()
        char_dir = app_data_dir / "characters" / self.character_name
        resolved_path = str(char_dir / path)
        
        # Validate the resolved path exists
        if not os.path.exists(resolved_path):
            print(f"⚠️ Resolved path does not exist: {resolved_path}")
        
        return resolved_path

    def _load_current_settings(self):
        """Load current settings with path resolution"""
        # Resolve paths before displaying
        user_icon_path = self._resolve_image_path(self.settings.user_icon_path) if self.settings.user_icon_path else ""
        char_icon_path = self._resolve_image_path(self.settings.character_icon_path) if self.settings.character_icon_path else ""
        bg_image_path = self._resolve_image_path(self.settings.background_image_path) if self.settings.background_image_path else ""
        
        if user_icon_path and os.path.exists(user_icon_path):
            try:
                pixmap = QPixmap(user_icon_path)
                scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.user_icon_label.setPixmap(scaled)
                self.user_icon_label.setText("")
            except:
                pass
        
        if char_icon_path and os.path.exists(char_icon_path):
            try:
                pixmap = QPixmap(char_icon_path)
                scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.char_icon_label.setPixmap(scaled)
                self.char_icon_label.setText("")
            except:
                pass
        
        if bg_image_path:
            self.bg_image_label.setText(os.path.basename(bg_image_path))

    def _select_icon(self, icon_type):
        """Select icon image with improved file handling"""
        # Get current settings for this icon type
        current_settings = None
        if icon_type == "user":
            if (self.settings.user_icon_path and 
                os.path.exists(self._resolve_image_path(self.settings.user_icon_path))):
                current_settings = IconSettings(
                    image_path=self._resolve_image_path(self.settings.user_icon_path),
                    scale=getattr(self.settings, 'user_icon_scale', 1.0),
                    offset_x=getattr(self.settings, 'user_icon_offset_x', 0),
                    offset_y=getattr(self.settings, 'user_icon_offset_y', 0)
                )
        else:  # character
            if (self.settings.character_icon_path and 
                os.path.exists(self._resolve_image_path(self.settings.character_icon_path))):
                current_settings = IconSettings(
                    image_path=self._resolve_image_path(self.settings.character_icon_path),
                    scale=getattr(self.settings, 'character_icon_scale', 1.0),
                    offset_x=getattr(self.settings, 'character_icon_offset_x', 0),
                    offset_y=getattr(self.settings, 'character_icon_offset_y', 0)
                )
        
        # Open positioning dialog
        dialog = IconPositioningDialog(self, current_settings, icon_type)
        
        if dialog.exec() and dialog.settings:
            try:
                # Create icons directory in character folder
                app_data_dir = get_app_data_dir()
                char_dir = app_data_dir / "characters" / self.character_name
                icons_dir = char_dir / "icons"
                icons_dir.mkdir(exist_ok=True)
                
                # Generate target path
                source_path = dialog.settings.image_path
                file_ext = os.path.splitext(source_path)[1]
                target_filename = f"{icon_type}_icon{file_ext}"
                target_path = icons_dir / target_filename
                
                # Use safe copy function
                if safe_copy_file(source_path, str(target_path)):
                    # Store relative path in settings
                    relative_path = f"icons/{target_filename}"
                    
                    if icon_type == "user":
                        self.settings.user_icon_path = relative_path
                        self.settings.user_icon_scale = dialog.settings.scale
                        self.settings.user_icon_offset_x = dialog.settings.offset_x
                        self.settings.user_icon_offset_y = dialog.settings.offset_y
                        label = self.user_icon_label
                    else:
                        self.settings.character_icon_path = relative_path
                        self.settings.character_icon_scale = dialog.settings.scale
                        self.settings.character_icon_offset_x = dialog.settings.offset_x
                        self.settings.character_icon_offset_y = dialog.settings.offset_y
                        label = self.char_icon_label
                    
                    # Update preview
                    try:
                        pixmap = QPixmap(str(target_path))
                        scaled = pixmap.scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        label.setPixmap(scaled)
                        label.setText("")
                    except Exception as preview_error:
                        print(f"Preview update failed: {preview_error}")
                        label.setText("Icon set")
                else:
                    QMessageBox.critical(self, "Error", "Failed to save icon file.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to set up icon: {str(e)}")



    def _choose_color(self):
        """Choose background color"""
        initial_color = self.settings.background_color or "#F0F4F8"
        color = QColorDialog.getColor(QColor(initial_color), self, "Select Background Color")
        
        if color.isValid():
            self.settings.background_color = color.name()
            self.color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
 
class IconPositioningDialog(QDialog):
    """Dialog for selecting and positioning chat icons"""
    def __init__(self, parent, current_settings: Optional[IconSettings] = None, icon_type: str = "user"):
        super().__init__(parent)
        
        self.settings = current_settings
        self.icon_type = icon_type
        self.image_path = current_settings.image_path if current_settings else None
        self.original_pixmap = None
        self.scale = current_settings.scale if current_settings else 1.0
        self.offset_x = current_settings.offset_x if current_settings else 0
        self.offset_y = current_settings.offset_y if current_settings else 0
        
        self.setWindowTitle(f"{icon_type.title()} Icon Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        self._setup_ui()
        
        # Load image if exists
        if self.image_path and os.path.exists(self.image_path):
            self._load_image(self.image_path)
    
    def _setup_ui(self):
        """Create the interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Instructions
        instructions = QLabel(f"Select and adjust your {self.icon_type} icon")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("font-size: 12pt; padding: 10px;")
        layout.addWidget(instructions)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(200, 200)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 2px dashed #CCCCCC;
                border-radius: 100px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Select an icon\nto preview")
        self.preview_label.setScaledContents(False)

        preview_layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
                
        # Size preview
        size_layout = QHBoxLayout()
        size_layout.addWidget(QLabel("Chat size preview:"))
        
        self.chat_preview = QLabel()
        self.chat_preview.setFixedSize(42, 42)
        self.chat_preview.setStyleSheet("border: 1px solid #ddd; background-color: #f0f0f0;;")
        size_layout.addWidget(self.chat_preview)
        size_layout.addStretch()
        
        preview_layout.addLayout(size_layout)
        preview_group.setLayout(preview_layout)
        content_layout.addWidget(preview_group)
        
        # Right side - Controls
        controls_group = QGroupBox("Adjustments")
        controls_layout = QVBoxLayout()
        
        # Image selection
        select_layout = QHBoxLayout()
        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("background-color: #070000; padding: 5px;")
        select_layout.addWidget(self.image_label)
        
        select_btn = QPushButton("Select Image")
        select_btn.clicked.connect(self._select_image)
        select_layout.addWidget(select_btn)
        controls_layout.addLayout(select_layout)
        
        controls_layout.addSpacing(20)
        
        # Zoom control
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(0, 400)  # 0.25x to 4x zoom
        self.zoom_slider.setValue(int(self.scale * 50))
        self.zoom_slider.valueChanged.connect(self._update_zoom)
        controls_layout.addWidget(self.zoom_slider)
        
        self.zoom_value_label = QLabel(f"{self.scale:.1f}x")
        controls_layout.addWidget(self.zoom_value_label)
        
        controls_layout.addSpacing(20)
        
        # Position controls
        position_label = QLabel("Position:")
        controls_layout.addWidget(position_label)
        
        # Position buttons in a grid
        position_grid = QGridLayout()
        
        # Arrow buttons for positioning
        up_btn = QPushButton("↑")
        up_btn.clicked.connect(lambda: self._move_image(0, -5))
        position_grid.addWidget(up_btn, 0, 1)
        
        left_btn = QPushButton("←")
        left_btn.clicked.connect(lambda: self._move_image(-5, 0))
        position_grid.addWidget(left_btn, 1, 0)
        
        center_btn = QPushButton("⊙")
        center_btn.setToolTip("Center image")
        center_btn.clicked.connect(self._center_image)
        position_grid.addWidget(center_btn, 1, 1)
        
        right_btn = QPushButton("→")
        right_btn.clicked.connect(lambda: self._move_image(5, 0))
        position_grid.addWidget(right_btn, 1, 2)
        
        down_btn = QPushButton("↓")
        down_btn.clicked.connect(lambda: self._move_image(0, 5))
        position_grid.addWidget(down_btn, 2, 1)
        
        controls_layout.addLayout(position_grid)
        
        controls_layout.addSpacing(20)
        
        # Preset options
        preset_label = QLabel("Presets:")
        controls_layout.addWidget(preset_label)
        
        fit_btn = QPushButton("Fit to Circle")
        fit_btn.clicked.connect(self._fit_to_circle)
        controls_layout.addWidget(fit_btn)
        
        fill_btn = QPushButton("Fill Circle")
        fill_btn.clicked.connect(self._fill_circle)
        controls_layout.addWidget(fill_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_position)
        controls_layout.addWidget(reset_btn)
        
        controls_layout.addStretch()
        
        # Info label
        info_label = QLabel("Tip: Use arrow buttons or drag the preview to position")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-size: 9pt;")
        controls_layout.addWidget(info_label)
        
        controls_group.setLayout(controls_layout)
        content_layout.addWidget(controls_group)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        button_layout.addWidget(self.apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Enable mouse dragging on preview
        self._setup_dragging()
    


    def _update_chat_preview(self):
        """Update the small chat-size preview"""
        if not self.original_pixmap:
            # Clear chat preview if no image
            self.chat_preview.setPixmap(QPixmap())
            return
        
        try:
            # Chat icon size (this should match what's used in actual chat)
            chat_size = 42
            
            # Create circular icon at chat size
            chat_pixmap = QPixmap(chat_size, chat_size)
            chat_pixmap.fill(Qt.transparent)
            
            painter = QPainter(chat_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create circular clipping path
            path = QPainterPath()
            path.addEllipse(0, 0, chat_size, chat_size)
            painter.setClipPath(path)
            
            # Calculate scale conversion from preview (180px) to chat (42px)
            # The preview circle is 180px, chat icon is 42px
            scale_conversion = chat_size / 180.0
            
            # Apply the same scale and offset as preview, but converted for chat size
            scaled_width = int(self.original_pixmap.width() * self.scale * scale_conversion)
            scaled_height = int(self.original_pixmap.height() * self.scale * scale_conversion)
            
            scaled_pixmap = self.original_pixmap.scaled(
                scaled_width, 
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Convert offsets to chat size
            offset_x_chat = int(self.offset_x * scale_conversion)
            offset_y_chat = int(self.offset_y * scale_conversion)
            
            # Position the image
            x = (chat_size - scaled_width) // 2 + offset_x_chat
            y = (chat_size - scaled_height) // 2 + offset_y_chat
            
            painter.drawPixmap(x, y, scaled_pixmap)
            painter.end()
            
            # Set to preview label
            self.chat_preview.setPixmap(chat_pixmap)
            
        except Exception as e:
            print(f"⚠️ Chat preview error: {e}")
            # Clear on error
            self.chat_preview.setPixmap(QPixmap())   
# FIND your _setup_dragging method and REPLACE it with this:

    def _setup_dragging(self):
        """Setup mouse dragging for preview"""
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.preview_label.installEventFilter(self)  # Changed from preview_container to preview_label

    # ALSO FIND your eventFilter method and REPLACE it with this:

    def eventFilter(self, obj, event):
        """Handle mouse events for dragging"""
        if obj == self.preview_label:  # Changed from preview_container to preview_label
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.dragging = True
                self.drag_start_pos = event.position().toPoint()
                self.drag_start_offset_x = self.offset_x
                self.drag_start_offset_y = self.offset_y
                return True
            
            elif event.type() == QEvent.MouseMove and self.dragging:
                delta = event.position().toPoint() - self.drag_start_pos
                self.offset_x = self.drag_start_offset_x + delta.x()
                self.offset_y = self.drag_start_offset_y + delta.y()
                self._update_preview()
                return True
            
            elif event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
                return True
        
        return super().eventFilter(obj, event)
    
    def _select_image(self):
        """Select icon image"""
        # Show recommendation dialog
        QMessageBox.information(
            self, 
            "Image Quality Tip", 
            "For best quality, use images that are at least 256x256 pixels or larger."
        )
        
        start_dir = ""
        if self.image_path and os.path.exists(self.image_path):
            start_dir = os.path.dirname(self.image_path)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            f"Select {self.icon_type.title()} Icon",
            start_dir,
            "Image files (*.png *.jpg *.jpeg *.gif *.bmp);;All files (*.*)"
        )
        
        if filename:
            self._load_image(filename)
    
    def _load_image(self, filename):
        """Load image and update preview"""
        try:
            self.original_pixmap = QPixmap(filename)
            if self.original_pixmap.isNull():
                QMessageBox.critical(self, "Error", "Failed to load image")
                return
            
            self.image_path = filename
            self.image_label.setText(filename.split('/')[-1])
            self.apply_btn.setEnabled(True)
            
            # Smart fit for new images
            if not (hasattr(self, 'settings') and self.settings and filename == self.settings.image_path):
                self._smart_fit_to_circle()
            else:
                self._update_preview()  # Update preview for existing settings
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading image: {str(e)}")

    


    def _smart_fit_to_circle(self):
        """Smart initial fitting for circular display"""
        if not self.original_pixmap:
            return
        
        # Fit to circle (use smaller dimension)
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        preview_size = 180  # Preview circle diameter
        
        scale = preview_size / max(img_width, img_height)
        self.scale = max(0.1, min(4.0, scale))
        
        self.offset_x = 0
        self.offset_y = 0
        
        self.zoom_slider.setValue(int(self.scale * 100))
        self.zoom_value_label.setText(f"{self.scale:.1f}x")
        self._update_preview()
    
    def _update_zoom(self, value):
        """Update zoom level"""
        self.scale = value / 100.0
        self.zoom_value_label.setText(f"{self.scale:.1f}x")
        self._update_preview()
    
    def _move_image(self, dx, dy):
        """Move image by offset"""
        self.offset_x += dx
        self.offset_y += dy
        self._update_preview()
    
    def _center_image(self):
        """Center the image"""
        self.offset_x = 0
        self.offset_y = 0
        self._update_preview()
    
    def _fit_to_circle(self):
        """Fit image to circle maintaining aspect ratio"""
        self._smart_fit_to_circle()
    
    def _fill_circle(self):
        """Fill circle with image (may crop)"""
        if not self.original_pixmap:
            return
        
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        preview_size = 180
        
        scale = preview_size / min(img_width, img_height)
        self.scale = max(0.1, min(4.0, scale))
        
        self.zoom_slider.setValue(int(self.scale * 100))
        self.offset_x = 0
        self.offset_y = 0
        self._update_preview()
    
    def _reset_position(self):
        """Reset to original settings"""
        if self.settings:
            self.scale = self.settings.scale
            self.offset_x = self.settings.offset_x
            self.offset_y = self.settings.offset_y
            self.zoom_slider.setValue(int(self.scale * 100))
        else:
            self._center_image()
        self._update_preview()
    

    def _draw_sample_bubbles(self, painter, width, height):
        """Draw sample chat bubbles on the preview"""
        try:
            # Sample bubble positions and sizes
            bubbles = [
                {"text": "Hello! How are you?", "x": 20, "y": 50, "width": 180, "user": True},
                {"text": "I'm doing great, thanks for asking!", "x": 150, "y": 120, "width": 180, "user": False},
                {"text": "That's wonderful to hear!", "x": 20, "y": 190, "width": 160, "user": True},
            ]
            
            for bubble in bubbles:
                # Set bubble color
                if bubble["user"]:
                    painter.fillRect(
                        bubble["x"], bubble["y"], bubble["width"], 35,
                        QColor("#F0F0F0")  # User bubble color
                    )
                    text_color = QColor("#333333")
                else:
                    painter.fillRect(
                        bubble["x"], bubble["y"], bubble["width"], 35,
                        QColor("#E3F2FD")  # Character bubble color  
                    )
                    text_color = QColor("#1976D2")
                
                # Draw text
                painter.setPen(text_color)
                painter.setFont(QFont("Arial", 9))
                painter.drawText(
                    bubble["x"] + 10, bubble["y"] + 5, 
                    bubble["width"] - 20, 25,
                    Qt.AlignLeft | Qt.AlignVCenter,
                    bubble["text"]
                )
                
        except Exception as e:
            print(f"⚠️ Could not draw sample bubbles: {e}")


    # 2. Replace your _update_preview method with this simple version:
    def _update_preview(self):
        """Simple preview using QLabel - much more reliable"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            # No image - show placeholder
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Select an image to preview")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #F5F5F5;
                    border: 2px dashed #CCCCCC;
                    border-radius: 5px;
                }
            """)
            self.preview_info.setText("No image loaded")
            return
        
        try:
            # Create preview image
            preview_width = 350
            preview_height = 450
            
            # Create background canvas
            preview_pixmap = QPixmap(preview_width, preview_height)
            preview_pixmap.fill(QColor("#F0F4F8"))  # Light blue chat background
            
            # Calculate scaled image dimensions
            scaled_width = int(self.original_pixmap.width() * self.scale)
            scaled_height = int(self.original_pixmap.height() * self.scale)
            
            # Scale the original image
            scaled_image = self.original_pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Paint the scaled image onto the background
            painter = QPainter(preview_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate position (center + offset)
            x = (preview_width - scaled_width) // 2 + self.offset_x
            y = (preview_height - scaled_height) // 2 + self.offset_y
            
            # Draw the background image
            painter.drawPixmap(x, y, scaled_image)
            
            # Draw sample chat bubbles on top
            self._draw_sample_bubbles(painter, preview_width, preview_height)
            
            painter.end()
            
            # Apply the preview image directly to the QLabel
            self.preview_label.setPixmap(preview_pixmap)
            self.preview_label.setText("")  # Clear any text
            self.preview_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #CCCCCC;
                    border-radius: 5px;
                }
            """)
            
            # Update info
            self.preview_info.setText(f"Scale: {self.scale:.1f}x | Offset: ({self.offset_x}, {self.offset_y})")
            
            print(f"✅ Preview updated successfully: scale={self.scale:.1f}x, offset=({self.offset_x}, {self.offset_y})")
            
        except Exception as e:
            print(f"❌ Preview update failed: {e}")
            # Show error state
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"Preview Error:\n{str(e)}")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #FFEEEE;
                    border: 2px solid #FF6666;
                    border-radius: 5px;
                    color: #CC0000;
                }
            """)


    def _cleanup_temp_file(self, temp_path):
        """Enhanced cleanup with retry logic"""
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                if os.path.exists(temp_path):
                    # Clear from Qt cache first
                    QPixmapCache.remove(temp_path)
                    
                    # Try to remove file
                    os.remove(temp_path)
                    print(f"✅ Cleaned up temp file: {temp_path}")
                    return True
            except (OSError, PermissionError) as e:
                attempt += 1
                if attempt < max_attempts:
                    print(f"⚠️ Cleanup attempt {attempt} failed for {temp_path}: {e}")
                    QThread.msleep(100)  # Wait 100ms before retry
                else:
                    print(f"❌ Failed to cleanup temp file after {max_attempts} attempts: {temp_path}")
        
        return False

    def _apply_temp_image_to_stylesheet(self, temp_path, widget, max_wait_ms=500):
        """Safely apply temporary image to stylesheet with verification"""
    
        start_time = time.time() * 1000  # Current time in milliseconds
        
        while True:
            # Check if file exists and has content
            if os.path.exists(temp_path):
                try:
                    # Verify file has content (not empty)
                    if os.path.getsize(temp_path) > 0:
                        # Convert to absolute path and normalize slashes for Qt
                        abs_path = os.path.abspath(temp_path).replace('\\', '/')
                        
                        widget.setStyleSheet(f"""
                            QWidget {{
                                background-image: url("file:///{abs_path}");
                                background-position: center;
                                background-repeat: no-repeat;
                                border: 1px solid #ccc;
                            }}
                        """)
                        print(f"✅ Successfully applied temp image: {temp_path}")
                        return True
                except OSError:
                    pass  # File might be locked, continue waiting
            
            # Check if we've exceeded max wait time
            current_time = time.time() * 1000
            if current_time - start_time > max_wait_ms:
                print(f"❌ Timeout waiting for temp file: {temp_path}")
                return False
            
            # Wait 10ms before checking again
            QThread.msleep(10)
            QCoreApplication.processEvents()

        return False
    
    def _update_preview(self):
        """Update icon preview with safe QLabel approach"""
        if not self.original_pixmap:
            # No image - show placeholder
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Select an icon\nto preview")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #F5F5F5;
                    border: 2px dashed #CCCCCC;
                    border-radius: 100px;
                    color: #999999;
                }
            """)
            return
        
        try:
            # Create circular preview
            preview_size = 180  # Slightly smaller than the 200px container for border
            
            # Create circular preview pixmap
            preview_pixmap = QPixmap(preview_size, preview_size)
            preview_pixmap.fill(Qt.transparent)
            
            # Setup painter with antialiasing
            painter = QPainter(preview_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Create circular clipping path
            path = QPainterPath()
            path.addEllipse(0, 0, preview_size, preview_size)
            painter.setClipPath(path)
            
            # Calculate scaled dimensions
            scaled_width = int(self.original_pixmap.width() * self.scale)
            scaled_height = int(self.original_pixmap.height() * self.scale)
            
            # Scale the image
            scaled_pixmap = self.original_pixmap.scaled(
                scaled_width, 
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Calculate position with offset (center in preview)
            x = (preview_size - scaled_width) // 2 + self.offset_x
            y = (preview_size - scaled_height) // 2 + self.offset_y
            
            # Draw the scaled image
            painter.drawPixmap(x, y, scaled_pixmap)
            
            # Draw circular border
            painter.setClipping(False)
            painter.setPen(QPen(QColor("#CCCCCC"), 3))
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(1, 1, preview_size - 2, preview_size - 2)
            
            painter.end()
            
            # Apply the preview directly to QLabel (no temp files!)
            self.preview_label.setPixmap(preview_pixmap)
            self.preview_label.setText("")  # Clear any placeholder text
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: white;
                    border: 1px solid #CCCCCC;
                    border-radius: 100px;
                }
            """)
            
            # Update chat size preview
            self._update_chat_preview()
            
            print(f"✅ Icon preview updated: scale={self.scale:.1f}x, offset=({self.offset_x}, {self.offset_y})")
            
        except Exception as e:
            print(f"❌ Icon preview error: {e}")
            # Show error state
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText(f"Preview Error:\n{str(e)[:30]}...")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #FFEEEE;
                    border: 2px solid #FF6666;
                    border-radius: 100px;
                    color: #CC0000;
                }
            """)


    def _apply(self):
        """Apply settings and close"""
        if self.image_path:
            self.settings = IconSettings(
                image_path=self.image_path,
                scale=self.scale,
                offset_x=self.offset_x,
                offset_y=self.offset_y
            )
            self.accept()

class EnhancedColorDialog(QDialog):
    """Enhanced color editor dialog with live preview and real-time updates - IMPROVED"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.setWindowTitle("Edit App Colors")
        self.setFixedSize(500, 500)
        self.setModal(True)
        
        # Store original colors for cancel functionality
        self.original_primary = app_colors.PRIMARY
        self.original_secondary = app_colors.SECONDARY
        
        self._setup_ui()
        
        # Connect to color changes for real-time preview updates
        app_colors.colors_changed.connect(self._on_colors_changed)
        
    def _setup_ui(self):
        """Create enhanced color editor interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header info
        info_label = QLabel("🎨 Customize app colors. Live preview updates all windows instantly!")
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 8px; background: #f0f0f0; border-radius: 3px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Primary color sectionW
        primary_group = QGroupBox("Primary Color (Buttons, Title Bar)")
        primary_layout = QHBoxLayout()
        
        self.primary_label = QLabel()
        self.primary_label.setFixedSize(100, 40)
        self.primary_label.setStyleSheet(f"background-color: {app_colors.PRIMARY}; border: 2px solid black; border-radius: 5px;")
        primary_layout.addWidget(self.primary_label)
        
        primary_info = QLabel(f"Current: {app_colors.PRIMARY}")
        primary_info.setStyleSheet("font-family: monospace; color: #666;")
        primary_layout.addWidget(primary_info)
        self.primary_info_label = primary_info
        
        primary_layout.addStretch()
        
        primary_btn = QPushButton("Change Color")
        primary_btn.setMinimumWidth(100)
        primary_btn.clicked.connect(self._change_primary)
        primary_layout.addWidget(primary_btn)
        
        primary_group.setLayout(primary_layout)
        layout.addWidget(primary_group)
        
        # Secondary color section
        secondary_group = QGroupBox("Secondary Color (Backgrounds, Text)")
        secondary_layout = QHBoxLayout()
        
        self.secondary_label = QLabel()
        self.secondary_label.setFixedSize(100, 40)
        self.secondary_label.setStyleSheet(f"background-color: {app_colors.SECONDARY}; border: 2px solid black; border-radius: 5px;")
        secondary_layout.addWidget(self.secondary_label)
        
        secondary_info = QLabel(f"Current: {app_colors.SECONDARY}")
        secondary_info.setStyleSheet("font-family: monospace; color: #666;")
        secondary_layout.addWidget(secondary_info)
        self.secondary_info_label = secondary_info
        
        secondary_layout.addStretch()
        
        secondary_btn = QPushButton("Change Color")
        secondary_btn.setMinimumWidth(100)
        secondary_btn.clicked.connect(self._change_secondary)
        secondary_layout.addWidget(secondary_btn)
        
        secondary_group.setLayout(secondary_layout)
        layout.addWidget(secondary_group)
        
        # Live preview checkbox
        self.live_preview_check = QCheckBox("🔄 Live Preview (Updates all windows instantly)")
        self.live_preview_check.setChecked(True)  # Enable by default
        self.live_preview_check.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        layout.addWidget(self.live_preview_check)
        
        # Preview section
        preview_group = QGroupBox("Color Preview:")
        preview_layout = QVBoxLayout()
        
        # Create sample UI elements
        sample_layout = QHBoxLayout()
        
        self.preview_primary = QPushButton("Primary Sample Button")
        self.preview_primary.setFixedHeight(35)
        self.preview_primary.setEnabled(False)  # Just for preview
        sample_layout.addWidget(self.preview_primary)
        
        self.preview_secondary = QLabel("Secondary Background Sample")
        self.preview_secondary.setAlignment(Qt.AlignCenter)
        self.preview_secondary.setFixedHeight(35)
        self.preview_secondary.setStyleSheet("border: 1px solid #ccc; border-radius: 3px; padding: 5px;")
        sample_layout.addWidget(self.preview_secondary)
        
        preview_layout.addLayout(sample_layout)
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Warning about character colors
        warning_label = QLabel("⚠️ Note: Character-specific colors will override these global colors when enabled.")
        warning_label.setStyleSheet("color: #ff6b35; font-size: 8pt; padding: 5px; background: #fff3e0; border-radius: 3px;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)
        
        self._update_preview()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        apply_btn = QPushButton("✅ Apply & Save")
        apply_btn.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        apply_btn.clicked.connect(self._apply_colors)
        button_layout.addWidget(apply_btn)
        
        reset_btn = QPushButton("🔄 Reset to Default")
        reset_btn.clicked.connect(self._reset_default)
        button_layout.addWidget(reset_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self._cancel)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _change_primary(self):
        """Change primary color with enhanced live preview - FIXED"""
        current_color = QColor(app_colors.PRIMARY)
        color = QColorDialog.getColor(current_color, self, "Select Primary Color")
        
        if color.isValid():
            color_name = color.name()
            self.primary_label.setStyleSheet(f"background-color: {color_name}; border: 2px solid black; border-radius: 5px;")
            self.primary_info_label.setText(f"Current: {color_name}")
            
            # FIXED: Don't apply to global colors during preview - just update UI
            if self.live_preview_check.isChecked():
                # Store preview colors temporarily without changing global storage
                self._preview_primary = color_name
                self._apply_preview_colors()
                print(f"🎨 Global color preview - PRIMARY={color_name}")
            
            self._update_preview()

    def _change_secondary(self):
        """Change secondary color with enhanced live preview - FIXED"""
        current_color = QColor(app_colors.SECONDARY)
        color = QColorDialog.getColor(current_color, self, "Select Secondary Color")
        
        if color.isValid():
            color_name = color.name()
            self.secondary_label.setStyleSheet(f"background-color: {color_name}; border: 2px solid black; border-radius: 5px;")
            self.secondary_info_label.setText(f"Current: {color_name}")
            
            # FIXED: Don't apply to global colors during preview
            if self.live_preview_check.isChecked():
                self._preview_secondary = color_name
                self._apply_preview_colors()
                print(f"🎨 Global color preview - SECONDARY={color_name}")
            
            self._update_preview()

    def _apply_preview_colors(self):
        """Apply preview colors without changing global storage - NEW METHOD"""
        # Get colors to preview
        primary = getattr(self, '_preview_primary', app_colors.PRIMARY)
        secondary = getattr(self, '_preview_secondary', app_colors.SECONDARY)
        
        # Temporarily override app_colors for preview (but don't save)
        old_primary = app_colors._primary
        old_secondary = app_colors._secondary
        
        # Set temporarily for preview
        app_colors._primary = primary
        app_colors._secondary = secondary
        
        # Trigger UI update
        app_colors.colors_changed.emit()
        
        # Store original colors to restore on cancel
        self._temp_original_primary = old_primary
        self._temp_original_secondary = old_secondary

    def _apply_colors(self):
        """Apply and save colors - FIXED"""
        try:
            # Get colors from labels (what user selected)
            primary_color = self.primary_label.styleSheet().split("background-color: ")[1].split(";")[0]
            secondary_color = self.secondary_label.styleSheet().split("background-color: ")[1].split(";")[0]
            
            # Apply to global colors (this is correct for global color editor)
            app_colors.set_colors(primary_color, secondary_color)
            print(f"🎨 Applied GLOBAL colors: {primary_color}, {secondary_color}")
            
            # Save to file
            app_colors.save_colors()
            
            # Show success message
            QMessageBox.information(self, "Colors Applied", 
                                f"✅ Global colors applied and saved!\n\n"
                                f"Primary: {primary_color}\n"
                                f"Secondary: {secondary_color}")
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply colors: {str(e)}")

    def _cancel(self):
        """Cancel changes and restore original colors if live preview was used - FIXED"""
        if self.live_preview_check.isChecked():
            # Restore original global colors if they were changed during preview
            if (hasattr(self, '_temp_original_primary') and 
                hasattr(self, '_temp_original_secondary')):
                
                app_colors.set_colors(self._temp_original_primary, self._temp_original_secondary)
                print("🎨 Restored original global colors after preview cancel")
        
        self.reject()









    def _update_preview(self):
        """Update preview elements to show current color selection"""
        try:
            # Get colors from labels (these show the selected colors, not necessarily the applied ones)
            primary_color = self.primary_label.styleSheet().split("background-color: ")[1].split(";")[0]
            secondary_color = self.secondary_label.styleSheet().split("background-color: ")[1].split(";")[0]
            
            # Update preview button
            self.preview_primary.setStyleSheet(f"""
                QPushButton {{
                    background-color: {primary_color};
                    color: {secondary_color};
                    border: none;
                    border-radius: 5px;
                    font-weight: bold;
                    padding: 8px;
                }}
            """)
            
            # Update preview background
            self.preview_secondary.setStyleSheet(f"""
                QLabel {{
                    background-color: {secondary_color};
                    color: {primary_color};
                    border: 2px solid {primary_color};
                    border-radius: 3px;
                    padding: 5px;
                    font-weight: bold;
                }}
            """)
            
        except Exception as e:
            print(f"Preview update error: {e}")
    
    def _on_colors_changed(self):
        """Handle external color changes (from live preview)"""
        # Update our display when colors change from outside
        self.primary_label.setStyleSheet(f"background-color: {app_colors.PRIMARY}; border: 2px solid black; border-radius: 5px;")
        self.secondary_label.setStyleSheet(f"background-color: {app_colors.SECONDARY}; border: 2px solid black; border-radius: 5px;")
        
        self.primary_info_label.setText(f"Current: {app_colors.PRIMARY}")
        self.secondary_info_label.setText(f"Current: {app_colors.SECONDARY}")
        
        self._update_preview()
    
    def _reset_default(self):
        """Reset to default colors"""
        reply = QMessageBox.question(self, "Reset Colors", 
                                   "Reset to default colors (#2196F3 blue and #F5F5F5 light gray)?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # Update the visual labels
            self.primary_label.setStyleSheet("background-color: #2196F3; border: 2px solid black; border-radius: 5px;")
            self.secondary_label.setStyleSheet("background-color: #F5F5F5; border: 2px solid black; border-radius: 5px;")
            
            self.primary_info_label.setText("Current: #2196F3")
            self.secondary_info_label.setText("Current: #F5F5F5")
            
            # Apply immediately if live preview is on
            if self.live_preview_check.isChecked():
                app_colors.set_colors("#2196F3", "#F5F5F5")
                print("🎨 Reset to default colors with live preview")
            
            self._update_preview()
    

    def closeEvent(self, event):
        """Cleanup when dialog closes"""
        try:
            app_colors.colors_changed.disconnect(self._on_colors_changed)
        except:
            pass
        super().closeEvent(event)

class APIConfigDialog(QDialog):
    """Dialog for editing API configuration with context size - FIXED VERSION"""
    
    def __init__(self, parent, config: Optional[APIConfig]):
        super().__init__(parent)
        
        self.config = config
        
        self.setWindowTitle("Edit API Configuration" if config else "New API Configuration")
        self.setFixedSize(600, 650)
        self.setModal(True)
        
        # Initialize format combo reference
        self.format_combo = None
        self.system_template_edit = None
        self.chain_of_thought_check = None
        self.examples_check = None
        self.output_format_edit = None
        self.conversation_style_combo = None

        
        self._setup_ui()
        
        if config:
            self._load_config()
    
    def _setup_ui(self):
        """Setup UI with fixed format combo handling"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tabs
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Basic settings tab
        basic_widget = QWidget()
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        basic_layout.addRow("Configuration Name:", self.name_edit)
        
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "openai", "google", "deepseek", "anthropic", "groq", "local", "custom"
        ])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        basic_layout.addRow("Provider:", self.provider_combo)
        
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        basic_layout.addRow("API Key:", self.api_key_edit)
        
        self.base_url_edit = QLineEdit()
        basic_layout.addRow("Base URL:", self.base_url_edit)
        
        self.model_edit = QLineEdit()
        self.model_edit.textChanged.connect(self._on_model_changed)
        basic_layout.addRow("Model:", self.model_edit)
        
        # Context Size Control
        context_layout = QHBoxLayout()
        self.context_size_spin = QSpinBox()
        self.context_size_spin.setRange(512, 2000000)
        self.context_size_spin.setValue(4096)
        self.context_size_spin.setSuffix(" tokens")
        context_layout.addWidget(self.context_size_spin)
        
        self.auto_context_btn = QPushButton("Auto")
        self.auto_context_btn.setFixedWidth(50)
        self.auto_context_btn.setToolTip("Auto-detect context size for this model")
        self.auto_context_btn.clicked.connect(self._auto_detect_context_size)
        context_layout.addWidget(self.auto_context_btn)
        
        context_widget = QWidget()
        context_widget.setLayout(context_layout)
        basic_layout.addRow("Context Size:", context_widget)
        
        # Context size info label
        self.context_info_label = QLabel("💡 Context size determines how much conversation history can be included")
        self.context_info_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic;")
        self.context_info_label.setWordWrap(True)
        basic_layout.addRow("", self.context_info_label)
        
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        basic_layout.addRow("Enabled:", self.enabled_check)
        
        basic_widget.setLayout(basic_layout)
        tabs.addTab(basic_widget, "Basic")
        
        # Parameters tab
        params_widget = QWidget()
        params_layout = QFormLayout()
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setValue(0.7)
        params_layout.addRow("Temperature:", self.temperature_spin)
        
        # Enhanced max tokens with context validation
        max_tokens_layout = QHBoxLayout()
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(1, 8192)
        self.max_tokens_spin.setValue(150)
        self.max_tokens_spin.valueChanged.connect(self._validate_context_ratio)
        max_tokens_layout.addWidget(self.max_tokens_spin)
        
        self.context_ratio_label = QLabel("(~4% of context)")
        self.context_ratio_label.setStyleSheet("color: gray; font-size: 9pt;")
        max_tokens_layout.addWidget(self.context_ratio_label)
        
        max_tokens_widget = QWidget()
        max_tokens_widget.setLayout(max_tokens_layout)
        params_layout.addRow("Max Tokens:", max_tokens_widget)
        
        self.top_p_spin = QDoubleSpinBox()
        self.top_p_spin.setRange(0.0, 1.0)
        self.top_p_spin.setSingleStep(0.1)
        self.top_p_spin.setValue(1.0)
        params_layout.addRow("Top P:", self.top_p_spin)
        
        self.freq_penalty_spin = QDoubleSpinBox()
        self.freq_penalty_spin.setRange(-2.0, 2.0)
        self.freq_penalty_spin.setSingleStep(0.1)
        self.freq_penalty_spin.setValue(0.0)
        params_layout.addRow("Frequency Penalty:", self.freq_penalty_spin)
        
        self.presence_penalty_spin = QDoubleSpinBox()
        self.presence_penalty_spin.setRange(-2.0, 2.0)
        self.presence_penalty_spin.setSingleStep(0.1)
        self.presence_penalty_spin.setValue(0.0)
        params_layout.addRow("Presence Penalty:", self.presence_penalty_spin)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 300)
        self.timeout_spin.setValue(30)
        params_layout.addRow("Timeout (seconds):", self.timeout_spin)
        
        # Streaming
        streaming_layout = QHBoxLayout()
        self.streaming_check = QCheckBox()
        self.streaming_check.setChecked(False)
        streaming_layout.addWidget(self.streaming_check)
        
        self.test_streaming_btn = QPushButton("Test")
        self.test_streaming_btn.setFixedSize(50, 25)
        self.test_streaming_btn.clicked.connect(self._test_streaming_support)
        streaming_layout.addWidget(self.test_streaming_btn)
        streaming_layout.addStretch()
        
        streaming_widget = QWidget()
        streaming_widget.setLayout(streaming_layout)
        params_layout.addRow("Streaming:", streaming_widget)
        
        self.streaming_status_label = QLabel("")
        self.streaming_status_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic;")
        params_layout.addRow("", self.streaming_status_label)
        
        params_widget.setLayout(params_layout)
        tabs.addTab(params_widget, "Parameters")
        
        # ===== PROMPTS TAB - FIXED TO USE SINGLE COMBO =====
        prompts_widget = QWidget()
        prompts_layout = QVBoxLayout()
        
        # Prompt Structure Group
        prompt_group = QGroupBox("Prompt Structure")
        prompt_form = QFormLayout()
        
        # FIXED: Create single instruction format combo
        self.format_combo = QComboBox()
        self.format_combo.addItems(["default", "alpaca", "chatml", "vicuna", "llama"])
        prompt_form.addRow("Instruction Format:", self.format_combo)
        
        # System Message Template
        self.system_template_edit = QTextEdit()
        self.system_template_edit.setMaximumHeight(100)
        self.system_template_edit.setPlainText("You are {character_name}. {personality}")
        prompt_form.addRow("System Template:", self.system_template_edit)
        
        # Conversation Style
        self.conversation_style_combo = QComboBox()
        self.conversation_style_combo.addItems(["natural", "formal", "creative", "technical"])
        prompt_form.addRow("Conversation Style:", self.conversation_style_combo)
        
        prompt_group.setLayout(prompt_form)
        prompts_layout.addWidget(prompt_group)
        
        # Advanced Options Group
        advanced_group = QGroupBox("Advanced Options")
        advanced_form = QFormLayout()

        # Chain of Thought
        self.chain_of_thought_check = QCheckBox("Enable step-by-step reasoning")
        advanced_form.addRow("Chain of Thought:", self.chain_of_thought_check)

        # Use Examples
        self.examples_check = QCheckBox("Include conversation examples")
        advanced_form.addRow("Use Examples:", self.examples_check)

        # Output Format (FIXED - using QTextEdit)
        self.output_format_edit = QTextEdit()
        self.output_format_edit.setMaximumHeight(100)  # Now this works!
        self.output_format_edit.setPlaceholderText("e.g., 'Respond in character with natural dialogue.\nUse markdown for emphasis when appropriate.\nKeep responses conversational and engaging.'")
        advanced_form.addRow("Output Format:", self.output_format_edit)


        advanced_group.setLayout(advanced_form)
        prompts_layout.addWidget(advanced_group)
        
        
        prompts_layout.addStretch()
        
        prompts_widget.setLayout(prompts_layout)
        tabs.addTab(prompts_widget, "Prompts")
        
        # Custom parameters tab
        custom_widget = QWidget()
        custom_layout = QVBoxLayout()
        
        custom_layout.addWidget(QLabel("Custom Parameters (JSON format):"))
        
        self.custom_params_edit = QTextEdit()
        self.custom_params_edit.setPlainText("{}")
        custom_layout.addWidget(self.custom_params_edit)
        
        custom_widget.setLayout(custom_layout)
        tabs.addTab(custom_widget, "Custom")
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        test_btn = QPushButton("Test")
        test_btn.clicked.connect(self._test_config)
        button_layout.addWidget(test_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Set initial values
        self._on_provider_changed()
    



    def _create_format_combo(self):
        """Create instruction format combo"""
        self.format_combo = QComboBox()
        self.format_combo.addItems(["default", "alpaca", "chatml", "vicuna"])
        return self.format_combo

    def _create_system_template(self):
        """Create system message template editor"""
        self.system_template_edit = QTextEdit()
        self.system_template_edit.setMaximumHeight(60)
        self.system_template_edit.setPlainText("You are {character_name}. {personality}")
        return self.system_template_edit

    def _create_prompt_options(self):
        """Create prompt options checkboxes"""
        options_widget = QWidget()
        options_layout = QHBoxLayout()
        
        self.chain_of_thought_check = QCheckBox("Chain of Thought")
        self.examples_check = QCheckBox("Include Examples")
        
        options_layout.addWidget(self.chain_of_thought_check)
        options_layout.addWidget(self.examples_check)
        options_layout.addStretch()
        
        options_widget.setLayout(options_layout)
        return options_widget

    def _test_streaming_support(self):
        """Test if the current API configuration supports streaming"""
        # Get current form values to create temp config
        temp_config = self.get_config()
        if not temp_config:
            QMessageBox.critical(self, "Error", "Please fill in all required fields first.")
            return
        
        # Show progress dialog
        progress = QProgressDialog("Testing streaming support...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        QApplication.processEvents()
        
        try:
            # Create test interface with temp config
            test_interface = EnhancedAIInterface()
            test_interface.api_configs[temp_config.name] = temp_config
            
            test_messages = [{"role": "user", "content": "Hello, please respond with exactly: Test successful"}]
            test_personality = "You are a helpful assistant. Respond exactly as requested."
            
            # Test 1: Try streaming
            streaming_works = False
            streaming_error = ""
            
            if temp_config.provider.lower() in ["openai", "deepseek"]:  # Only test streaming for supported providers
                try:
                    # Test streaming with callback
                    streaming_response = ""
                    streaming_finished = False
                    streaming_error_occurred = False
                    
                    def streaming_callback(token, is_finished):
                        nonlocal streaming_response, streaming_finished, streaming_error_occurred
                        if not is_finished:
                            streaming_response += token
                        else:
                            streaming_finished = True
                    
                    # Create a copy of config with streaming enabled
                    streaming_config = APIConfig(**asdict(temp_config))
                    streaming_config.streaming = True
                    test_interface.api_configs[streaming_config.name] = streaming_config
                    
                    # Try streaming request
                    test_interface.get_streaming_response(
                        test_messages, 
                        test_personality, 
                        streaming_callback,
                        streaming_config.name
                    )
                    
                    # Wait a bit for response
                    import time
                    timeout = 0
                    while not streaming_finished and timeout < 10:  # 10 second timeout
                        QApplication.processEvents()
                        time.sleep(0.1)
                        timeout += 0.1
                    
                    if streaming_finished and streaming_response.strip():
                        streaming_works = True
                    else:
                        streaming_error = "Streaming timeout or no response"
                        
                except Exception as e:
                    streaming_error = str(e)
            else:
                streaming_error = f"Provider '{temp_config.provider}' doesn't support streaming"
            
            # Test 2: Try non-streaming (as fallback verification)
            non_streaming_works = False
            non_streaming_error = ""
            
            try:
                # Create a copy of config with streaming disabled
                non_streaming_config = APIConfig(**asdict(temp_config))
                non_streaming_config.streaming = False
                test_interface.api_configs[non_streaming_config.name] = non_streaming_config
                
                response = test_interface.get_response(
                    test_messages, 
                    test_personality,
                    non_streaming_config.name
                )
                
                if response and response.strip() and "error" not in response.lower():
                    non_streaming_works = True
                else:
                    non_streaming_error = response if response else "No response"
                    
            except Exception as e:
                non_streaming_error = str(e)
            
            progress.close()
            
            # Show results
            if streaming_works and non_streaming_works:
                self.streaming_status_label.setText("✅ Streaming: Supported")
                self.streaming_status_label.setStyleSheet("color: green; font-size: 9pt;")
                QMessageBox.information(self, "Streaming Test Result", 
                                    "✅ Success!\n\n"
                                    "• Streaming: SUPPORTED\n"
                                    "• Non-streaming: SUPPORTED\n\n"
                                    "This API configuration works perfectly with streaming enabled.")
            
            elif not streaming_works and non_streaming_works:
                self.streaming_status_label.setText("⚠️ Streaming: Not supported")
                self.streaming_status_label.setStyleSheet("color: orange; font-size: 9pt;")
                
                # Automatically disable streaming
                self.streaming_check.setChecked(False)
                
                QMessageBox.warning(self, "Streaming Test Result", 
                                "⚠️ Streaming Not Supported\n\n"
                                f"• Streaming: FAILED ({streaming_error})\n"
                                "• Non-streaming: SUPPORTED\n\n"
                                "Streaming has been automatically disabled. "
                                "This API will work fine without streaming.")
            
            elif streaming_works and not non_streaming_works:
                self.streaming_status_label.setText("✅ Streaming: Supported (non-streaming failed)")
                self.streaming_status_label.setStyleSheet("color: blue; font-size: 9pt;")
                QMessageBox.information(self, "Streaming Test Result", 
                                    "✅ Streaming Works!\n\n"
                                    "• Streaming: SUPPORTED\n"
                                    f"• Non-streaming: FAILED ({non_streaming_error})\n\n"
                                    "This API only works with streaming enabled.")
            
            else:
                self.streaming_status_label.setText("❌ Both modes failed")
                self.streaming_status_label.setStyleSheet("color: red; font-size: 9pt;")
                QMessageBox.critical(self, "Streaming Test Result", 
                                "❌ API Test Failed\n\n"
                                f"• Streaming: FAILED ({streaming_error})\n"
                                f"• Non-streaming: FAILED ({non_streaming_error})\n\n"
                                "Please check your API configuration settings.")
        
        except Exception as e:
            progress.close()
            self.streaming_status_label.setText("❌ Test failed")
            self.streaming_status_label.setStyleSheet("color: red; font-size: 9pt;")
            QMessageBox.critical(self, "Test Failed", f"❌ Test failed!\n\nError: {str(e)}")



    def _on_provider_changed(self):
        """Handle provider change with context size defaults"""
        provider = self.provider_combo.currentText()
        
        # Provider defaults with context sizes
        provider_defaults = {
            "openai": {
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-3.5-turbo",
                "context_size": 4096
            },
            "google": {
                "base_url": "https://generativelanguage.googleapis.com",
                "model": "gemini-pro",
                "context_size": 32768
            },
            "deepseek": {
                "base_url": "https://api.deepseek.com/v1",
                "model": "deepseek-chat",
                "context_size": 32768
            },
            "anthropic": {
                "base_url": "https://api.anthropic.com/v1",
                "model": "claude-3-sonnet-20240229",
                "context_size": 200000
            },
            "groq": {
                "base_url": "https://api.groq.com/openai/v1",
                "model": "llama-3.1-8b-instant",
                "context_size": 8192
            },
            "local": {
                "base_url": "http://localhost:1234/v1",
                "model": "local-model",
                "context_size": 4096
            }
        }
        
        if provider in provider_defaults:
            defaults = provider_defaults[provider]
            self.base_url_edit.setText(defaults["base_url"])
            self.model_edit.setText(defaults["model"])
            self.context_size_spin.setValue(defaults["context_size"])
            
            if provider == "local":
                self.api_key_edit.setText("not-needed")
        
        self._validate_context_ratio()
    
    def _on_model_changed(self):
        """Auto-update context size when model changes"""
        model_name = self.model_edit.text().strip()
        if model_name:
            suggested_context = get_context_size_for_model(model_name)
            if suggested_context != self.context_size_spin.value():
                self.context_size_spin.setValue(suggested_context)
                self._validate_context_ratio()
    
    def _auto_detect_context_size(self):
        """Auto-detect context size for current model"""
        model_name = self.model_edit.text().strip()
        if model_name:
            suggested_context = get_context_size_for_model(model_name)
            self.context_size_spin.setValue(suggested_context)
            self._validate_context_ratio()
            
            # Show info about the detection
            QMessageBox.information(self, "Context Size", 
                                  f"Set context size to {suggested_context:,} tokens for model: {model_name}")
    
    def _validate_context_ratio(self):
        """Validate max tokens vs context size ratio"""
        max_tokens = self.max_tokens_spin.value()
        context_size = self.context_size_spin.value()
        
        if context_size > 0:
            ratio = (max_tokens / context_size) * 100
            self.context_ratio_label.setText(f"(~{ratio:.1f}% of context)")
            
            # Color coding for the ratio
            if ratio > 50:
                self.context_ratio_label.setStyleSheet("color: red; font-size: 9pt;")
                self.context_info_label.setText("⚠️ Max tokens is very high compared to context size")
            elif ratio > 25:
                self.context_ratio_label.setStyleSheet("color: orange; font-size: 9pt;")
                self.context_info_label.setText("💡 Consider leaving more space for conversation history")
            else:
                self.context_ratio_label.setStyleSheet("color: gray; font-size: 9pt;")
                self.context_info_label.setText("✅ Good balance between response length and conversation history")
    

    def _load_config(self):
        """Load existing configuration - FIXED VERSION"""
        if not self.config:
            return
        
        # Basic Configuration
        self.name_edit.setText(self.config.name)
        self.provider_combo.setCurrentText(self.config.provider)
        self.api_key_edit.setText(self.config.api_key)
        self.base_url_edit.setText(self.config.base_url)
        self.model_edit.setText(self.config.model)
        self.enabled_check.setChecked(self.config.enabled)
        
        # Context size
        context_size = getattr(self.config, 'context_size', 4096)
        self.context_size_spin.setValue(context_size)
        
        # Parameters
        self.temperature_spin.setValue(self.config.temperature)
        self.max_tokens_spin.setValue(self.config.max_tokens)
        self.top_p_spin.setValue(self.config.top_p)
        self.freq_penalty_spin.setValue(self.config.frequency_penalty)
        self.presence_penalty_spin.setValue(self.config.presence_penalty)
        self.timeout_spin.setValue(self.config.timeout)
        self.streaming_check.setChecked(self.config.streaming)
        
        # Custom Parameters
        self.custom_params_edit.setPlainText(json.dumps(self.config.custom_params, indent=2))
        
        # FIXED: Prompt Structure Settings
        if self.format_combo:
            instruction_format = getattr(self.config, 'instruction_format', 'default')
            self.format_combo.setCurrentText(instruction_format)
        
        if self.system_template_edit:
            system_template = getattr(self.config, 'system_message_template', 'You are {character_name}. {personality}')
            self.system_template_edit.setPlainText(system_template)
        
        if self.conversation_style_combo:
            conversation_style = getattr(self.config, 'conversation_style', 'natural')
            self.conversation_style_combo.setCurrentText(conversation_style)
        
        if self.chain_of_thought_check:
            chain_of_thought = getattr(self.config, 'use_chain_of_thought', False)
            self.chain_of_thought_check.setChecked(chain_of_thought)
        
        if self.examples_check:
            use_examples = getattr(self.config, 'use_examples', True)
            self.examples_check.setChecked(use_examples)
        
        if self.output_format_edit:
            output_format = getattr(self.config, 'output_format_instruction', '')
            self.output_format_edit.setText(output_format)

        
        # Validate context ratio after loading
        self._validate_context_ratio()


    def _test_config(self):
        """Test the configuration"""
        try:
            # Create temporary config from current form values
            temp_config = self.get_config()
            if not temp_config:
                return
            
            # Create temporary AI interface for testing
            test_interface = EnhancedAIInterface()
            test_interface.api_configs[temp_config.name] = temp_config
            
            # Test with simple message
            test_messages = [{"role": "user", "content": "Hello, please respond with 'Test successful'"}]
            
            progress = QProgressDialog("Testing API configuration...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()
            
            response = test_interface.get_response(test_messages, "You are a helpful assistant.", temp_config.name)
            
            progress.close()
            
            if "error" in response.lower():
                QMessageBox.critical(self, "Test Failed", f"❌ Test failed!\n\nResponse: {response}")
            else:
                QMessageBox.information(self, "Test Result", f"✅ Test successful!\n\nResponse: {response[:200]}{'...' if len(response) > 200 else ''}")
            
        except Exception as e:
            if 'progress' in locals():
                progress.close()
            QMessageBox.critical(self, "Test Failed", f"❌ Test failed!\n\nError: {str(e)}")
    
    def _save(self):
        """Save configuration with context size"""
        config = self.get_config()
        if config:
            self.config = config
            self.accept()


    def get_config(self):
        """Get configuration from form with validation - UPDATED FOR QTextEdit"""
        try:
            # Validate custom parameters
            custom_params = json.loads(self.custom_params_edit.toPlainText())
            
            # Get instruction format
            instruction_format = "default"
            if hasattr(self, 'format_combo') and self.format_combo:
                instruction_format = self.format_combo.currentText()
            
            # Get system message template
            system_template = "You are {character_name}. {personality}"
            if hasattr(self, 'system_template_edit') and self.system_template_edit:
                template_text = self.system_template_edit.toPlainText().strip()
                if template_text:
                    system_template = template_text
            
            # Get conversation style
            conversation_style = "natural"
            if hasattr(self, 'conversation_style_combo') and self.conversation_style_combo:
                conversation_style = self.conversation_style_combo.currentText()
            
            # Get chain of thought setting
            use_chain_of_thought = False
            if hasattr(self, 'chain_of_thought_check') and self.chain_of_thought_check:
                use_chain_of_thought = self.chain_of_thought_check.isChecked()
            
            # Get use examples setting
            use_examples = True
            if hasattr(self, 'examples_check') and self.examples_check:
                use_examples = self.examples_check.isChecked()
            
            # UPDATED: Get output format instruction (QTextEdit)
            output_format = ""
            if hasattr(self, 'output_format_edit') and self.output_format_edit:
                output_format = self.output_format_edit.toPlainText().strip()  # Changed from .text() to .toPlainText()
            
            
            # Get max examples (if you have this field)
            max_examples = 3
            if hasattr(self, 'max_examples_spin') and self.max_examples_spin:
                max_examples = self.max_examples_spin.value()
            
            # Get role context setting (if you have this field)
            use_role_context = True
            if hasattr(self, 'use_role_context_check') and self.use_role_context_check:
                use_role_context = self.use_role_context_check.isChecked()
            
            # Create config object with all prompt structure fields
            config = APIConfig(
                name=self.name_edit.text().strip(),
                provider=self.provider_combo.currentText(),
                api_key=self.api_key_edit.text().strip(),
                base_url=self.base_url_edit.text().strip(),
                model=self.model_edit.text().strip(),
                enabled=self.enabled_check.isChecked(),
                temperature=self.temperature_spin.value(),
                max_tokens=self.max_tokens_spin.value(),
                top_p=self.top_p_spin.value(),
                frequency_penalty=self.freq_penalty_spin.value(),
                presence_penalty=self.presence_penalty_spin.value(),
                context_size=self.context_size_spin.value(),
                timeout=self.timeout_spin.value(),
                streaming=self.streaming_check.isChecked(),
                custom_params=custom_params,
                
                # Prompt Structure Settings
                instruction_format=instruction_format,
                system_message_template=system_template,
                conversation_style=conversation_style,
                use_chain_of_thought=use_chain_of_thought,
                use_examples=use_examples,
                output_format_instruction=output_format,  # Now from QTextEdit
                max_examples=max_examples,  # Added if you have this field
                use_role_context=use_role_context  # Added if you have this field
            )
            
            # Validation
            if not config.name:
                QMessageBox.critical(self, "Error", "Configuration name is required.")
                return None
            
            if not config.api_key and config.provider != "local":
                QMessageBox.critical(self, "Error", "API key is required.")
                return None
            
            if not config.base_url:
                QMessageBox.critical(self, "Error", "Base URL is required.")
                return None
            
            if not config.model:
                QMessageBox.critical(self, "Error", "Model is required.")
                return None
            
            # Context size validation
            if config.max_tokens >= config.context_size:
                QMessageBox.critical(self, "Error", 
                                f"Max tokens ({config.max_tokens}) must be less than context size ({config.context_size}).")
                return None
            
            return config
            
        except json.JSONDecodeError:
            QMessageBox.critical(self, "Error", "Invalid JSON in custom parameters.")
            return None
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error creating configuration: {str(e)}")
            return None


class CharacterNameEditDialog(QDialog):
    """Dialog for editing character names after creation"""
    def __init__(self, parent, character: CharacterConfig):
        super().__init__(parent)
        
        self.character = character
        self.result = None
        
        self.setWindowTitle("Edit Character Names")
        self.setFixedSize(400, 200)
        self.setModal(True)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info label
        info_label = QLabel("Note: Folder name changes are not recommended as they affect file organization.")
        info_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Folder name (read-only by default)
        self.folder_name_edit = QLineEdit(self.character.folder_name)
        self.folder_name_edit.setReadOnly(True)
        form_layout.addRow("Folder Name:", self.folder_name_edit)
        
        # Display name (editable)
        self.display_name_edit = QLineEdit(getattr(self.character, 'display_name', self.character.name))
        form_layout.addRow("Display Name:", self.display_name_edit)
        
        # Allow folder name editing checkbox
        self.allow_folder_edit = QCheckBox("Allow folder name editing (Advanced)")
        self.allow_folder_edit.toggled.connect(self._toggle_folder_edit)
        form_layout.addRow("", self.allow_folder_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _toggle_folder_edit(self):
        """Toggle folder name editing"""
        self.folder_name_edit.setReadOnly(not self.allow_folder_edit.isChecked())
        if self.allow_folder_edit.isChecked():
            self.folder_name_edit.setStyleSheet("background-color: #FFF3CD; border: 1px solid #FFEAA7;")
        else:
            self.folder_name_edit.setStyleSheet("")
    
    def _save(self):
        """Save the changes"""
        new_folder_name = self.folder_name_edit.text().strip()
        new_display_name = self.display_name_edit.text().strip()
        
        if not new_folder_name or not new_display_name:
            QMessageBox.critical(self, "Error", "Both names are required.")
            return
        
        # Validate folder name
        if re.search(r'[<>:"/\\|?*]', new_folder_name):
            QMessageBox.critical(self, "Error", "Folder name contains invalid characters.")
            return
        
        self.result = {
            "folder_name": new_folder_name,
            "display_name": new_display_name,
            "folder_changed": new_folder_name != self.character.folder_name
        }
        
        self.accept()


class UserProfileDialog(QDialog):
    """Dialog for managing user profiles with user name display"""
    def __init__(self, parent, profile_manager: UserProfileManager):
        super().__init__(parent)
        
        self.profile_manager = profile_manager
        
        self.setWindowTitle("User Profiles")
        self.setFixedSize(750, 500)  # Increased width for user name column
        self.setModal(True)
        
        self._setup_ui()
        self._load_profiles()
    
    def _setup_ui(self):
        """Setup UI with user name support"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Active profile section
        active_layout = QHBoxLayout()
        active_layout.addWidget(QLabel("Active Profile:"))
        
        self.active_combo = QComboBox()
        self.active_combo.currentTextChanged.connect(self._change_active_profile)
        active_layout.addWidget(self.active_combo)
        active_layout.addStretch()
        
        layout.addLayout(active_layout)
        
        # Profiles list with columns
        self.profiles_list = QListWidget()
        self.profiles_list.currentRowChanged.connect(self._on_profile_selected)
        layout.addWidget(self.profiles_list)
        
        # Info label
        info_label = QLabel("💡 Folder Name: Used for file organization\n💡 User Name: Replaces {{user}} in chat conversations")
        info_label.setStyleSheet("color: gray; font-size: 9pt; font-style: italic; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Profile")
        add_btn.clicked.connect(self._add_profile)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit Profile")
        edit_btn.clicked.connect(self._edit_profile)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete Profile")
        delete_btn.clicked.connect(self._delete_profile)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 Save Global")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self._save_profiles)
        btn_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)
    
    def _load_profiles(self):
        """Load profiles into UI showing user names"""
        # Store current active profile before clearing
        current_active = self.profile_manager.settings.active_profile_name
        
        # Block signals while updating UI
        self.active_combo.blockSignals(True)
        
        self.active_combo.clear()
        self.profiles_list.clear()
        
        for profile in self.profile_manager.settings.profiles:
            # Show user name in combo box, but store folder name as data
            display_text = f"{profile.user_name}"
            if profile.user_name != profile.name:
                display_text += f" ({profile.name})"
            
            self.active_combo.addItem(display_text, profile.name)  # Store folder name as data
            
            # Show both user name and folder name in list
            list_text = f"📁 {profile.name} | 👤 {profile.user_name} | {profile.personality[:40]}..."
            self.profiles_list.addItem(list_text)
        
        # Set active profile without triggering signals
        if current_active:
            # Find by stored data (folder name), not display text
            for i in range(self.active_combo.count()):
                if self.active_combo.itemData(i) == current_active:
                    self.active_combo.setCurrentIndex(i)
                    break
            else:
                # Active profile not found, use first profile
                if self.active_combo.count() > 0:
                    self.active_combo.setCurrentIndex(0)
                    first_profile_name = self.active_combo.itemData(0)
                    self.profile_manager.set_active_profile(first_profile_name)
        elif self.active_combo.count() > 0:
            # No active profile set, default to first
            self.active_combo.setCurrentIndex(0)
            first_profile_name = self.active_combo.itemData(0)
            self.profile_manager.set_active_profile(first_profile_name)
        
        # Re-enable signals
        self.active_combo.blockSignals(False)
    
    def _change_active_profile(self, display_text):
        """Change active profile using stored folder name data"""
        current_index = self.active_combo.currentIndex()
        if current_index >= 0:
            profile_folder_name = self.active_combo.itemData(current_index)
            if profile_folder_name:
                success = self.profile_manager.set_active_profile(profile_folder_name)
                if success:
                    print(f"✅ Active profile changed to: {profile_folder_name}")
                else:
                    print(f"⚠️ Failed to set active profile: {profile_folder_name}")
    
    def _on_profile_selected(self, row):
        """Handle profile selection"""
        pass
    
    def _add_profile(self):
        """Add new profile"""
        dialog = UserProfileEditDialog(self, None)
        if dialog.exec() and dialog.result:
            if self.profile_manager.add_profile(dialog.result):
                self._load_profiles()
                QMessageBox.information(self, "Success", "Profile added successfully!")
            else:
                QMessageBox.critical(self, "Error", "Profile folder name already exists!")
    
    def _edit_profile(self):
        """Edit selected profile"""
        row = self.profiles_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a profile to edit.")
            return
        
        profile = self.profile_manager.settings.profiles[row]
        dialog = UserProfileEditDialog(self, profile)
        if dialog.exec() and dialog.result:
            if self.profile_manager.update_profile(profile.name, dialog.result):
                self._load_profiles()
                QMessageBox.information(self, "Success", "Profile updated successfully!")
    
    def _delete_profile(self):
        """Delete selected profile"""
        row = self.profiles_list.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a profile to delete.")
            return
        
        if len(self.profile_manager.settings.profiles) <= 1:
            QMessageBox.warning(self, "Cannot Delete", "You must have at least one profile.")
            return
        
        profile = self.profile_manager.settings.profiles[row]
        reply = QMessageBox.question(self, "Delete Profile",
                                   f"Delete profile '{profile.user_name}' ({profile.name})?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            if self.profile_manager.delete_profile(profile.name):
                self._load_profiles()
                QMessageBox.information(self, "Success", "Profile deleted successfully!")

    def _save_profiles(self):
        """Save all profiles to file"""
        try:
            # Ensure the current combo box selection is saved
            current_index = self.active_combo.currentIndex()
            if current_index >= 0:
                selected_folder_name = self.active_combo.itemData(current_index)
                if selected_folder_name:
                    self.profile_manager.set_active_profile(selected_folder_name)
            
            # Force save to disk
            self.profile_manager.save_settings()
            
            # Verify save by reloading
            self.profile_manager.settings = self.profile_manager._load_settings()
            
            # Get active profile for display
            active_profile = self.profile_manager.get_active_profile()
            active_display = f"{active_profile.user_name} ({active_profile.name})" if active_profile else "None"
            
            QMessageBox.information(self, "Success", 
                f"✅ All user profiles saved successfully!\n\nActive Profile: {active_display}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"❌ Failed to save profiles: {str(e)}")

class BubbleSettingsDialog(QDialog):
    """Dialog for customizing chat bubble appearance with live editing and cancel restore"""
    def __init__(self, parent, character: CharacterConfig):
        super().__init__(parent)
        
        self.character = character
        
        # *** STORE ORIGINAL STATE FOR CANCEL FUNCTIONALITY ***
        self._store_original_state()
        
        self.setWindowTitle("Bubble Settings")
        self.setFixedSize(500, 650)
        self.setModal(True)
        
        self._setup_ui()
    
    def _store_original_state(self):
        """Store original character state to restore on cancel"""
        import copy
        self.original_state = {
            # Typography settings
            'text_font': self.character.text_font,
            'text_size': self.character.text_size,
            
            # Bubble settings
            'bubble_color': self.character.bubble_color,
            'user_bubble_color': self.character.user_bubble_color,
            'bubble_transparency': getattr(self.character, 'bubble_transparency', 0),
            'user_bubble_transparency': getattr(self.character, 'user_bubble_transparency', 0),
            
            # Text colors
            'text_color': self.character.text_color,
            'user_text_color': self.character.user_text_color,
            'quote_color': getattr(self.character, 'quote_color', '#666666'),
            'emphasis_color': getattr(self.character, 'emphasis_color', '#0D47A1'),
            'strikethrough_color': getattr(self.character, 'strikethrough_color', '#757575'),
            'code_bg_color': getattr(self.character, 'code_bg_color', 'rgba(0,0,0,0.1)'),
            'code_text_color': getattr(self.character, 'code_text_color', '#D32F2F'),
            'link_color': getattr(self.character, 'link_color', '#1976D2'),
            
            # External APIs (deep copy)
            'external_apis': copy.deepcopy(getattr(self.character, 'external_apis', []))
        }
    
    def _setup_ui(self):
        """Create the settings interface with live editing"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Tab widget
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # ===== BUBBLE STYLE TAB =====
        bubble_widget = QWidget()
        bubble_layout = QGridLayout()
            
        # Character bubble color
        bubble_layout.addWidget(QLabel("Character Bubble Color:"), 0, 0)
        char_color_layout = QHBoxLayout()

        self.bubble_color_label = QLabel()
        self.bubble_color_label.setFixedSize(100, 30)
        self.bubble_color_label.setStyleSheet(f"background-color: {self.character.bubble_color}; border: 1px solid black;")
        char_color_layout.addWidget(self.bubble_color_label)

        char_color_btn = QPushButton("Choose Color")
        char_color_btn.clicked.connect(self._choose_bubble_color)
        char_color_layout.addWidget(char_color_btn)
        char_color_layout.addStretch()

        bubble_layout.addLayout(char_color_layout, 0, 1)

        # Character bubble transparency - LIVE UPDATE
        bubble_layout.addWidget(QLabel("Character Bubble Transparency:"), 1, 0)
        char_transparency_layout = QHBoxLayout()

        self.char_transparency_slider = QSlider(Qt.Horizontal)
        self.char_transparency_slider.setRange(0, 100)
        self.char_transparency_slider.setValue(getattr(self.character, 'bubble_transparency', 0))
        self.char_transparency_slider.valueChanged.connect(self._live_update_char_transparency)
        char_transparency_layout.addWidget(self.char_transparency_slider)

        self.char_transparency_label = QLabel(f"{getattr(self.character, 'bubble_transparency', 0)}%")
        self.char_transparency_label.setFixedWidth(40)
        char_transparency_layout.addWidget(self.char_transparency_label)

        bubble_layout.addLayout(char_transparency_layout, 1, 1)

        # User bubble color
        bubble_layout.addWidget(QLabel("User Bubble Color:"), 2, 0)
        user_color_layout = QHBoxLayout()

        self.user_bubble_color_label = QLabel()
        self.user_bubble_color_label.setFixedSize(100, 30)
        self.user_bubble_color_label.setStyleSheet(f"background-color: {self.character.user_bubble_color}; border: 1px solid black;")
        user_color_layout.addWidget(self.user_bubble_color_label)

        user_color_btn = QPushButton("Choose Color")
        user_color_btn.clicked.connect(self._choose_user_bubble_color)
        user_color_layout.addWidget(user_color_btn)
        user_color_layout.addStretch()

        bubble_layout.addLayout(user_color_layout, 2, 1)

        # User bubble transparency - LIVE UPDATE
        bubble_layout.addWidget(QLabel("User Bubble Transparency:"), 3, 0)
        user_transparency_layout = QHBoxLayout()

        self.user_transparency_slider = QSlider(Qt.Horizontal)
        self.user_transparency_slider.setRange(0, 100)
        self.user_transparency_slider.setValue(getattr(self.character, 'user_bubble_transparency', 0))
        self.user_transparency_slider.valueChanged.connect(self._live_update_user_transparency)
        user_transparency_layout.addWidget(self.user_transparency_slider)

        self.user_transparency_label = QLabel(f"{getattr(self.character, 'user_bubble_transparency', 0)}%")
        self.user_transparency_label.setFixedWidth(40)
        user_transparency_layout.addWidget(self.user_transparency_label)

        bubble_layout.addLayout(user_transparency_layout, 3, 1)
        
        bubble_widget.setLayout(bubble_layout)
        tabs.addTab(bubble_widget, "Bubble Style")
        
        # ===== TEXT STYLE TAB =====
        text_style_widget = QWidget()
        text_style_layout = QGridLayout()
        
        # Normal text colors
        text_style_layout.addWidget(QLabel("Character Text Color:"), 0, 0)
        char_text_layout = QHBoxLayout()
        
        self.text_color_label = QLabel()
        self.text_color_label.setFixedSize(100, 30)
        self.text_color_label.setStyleSheet(f"background-color: {self.character.text_color}; border: 1px solid black;")
        char_text_layout.addWidget(self.text_color_label)
        
        char_text_btn = QPushButton("Choose Color")
        char_text_btn.clicked.connect(self._choose_text_color)
        char_text_layout.addWidget(char_text_btn)
        char_text_layout.addStretch()
        
        text_style_layout.addLayout(char_text_layout, 0, 1)
        
        text_style_layout.addWidget(QLabel("User Text Color:"), 1, 0)
        user_text_layout = QHBoxLayout()
        
        self.user_text_color_label = QLabel()
        self.user_text_color_label.setFixedSize(100, 30)
        self.user_text_color_label.setStyleSheet(f"background-color: {self.character.user_text_color}; border: 1px solid black;")
        user_text_layout.addWidget(self.user_text_color_label)
        
        user_text_btn = QPushButton("Choose Color")
        user_text_btn.clicked.connect(self._choose_user_text_color)
        user_text_layout.addWidget(user_text_btn)
        user_text_layout.addStretch()
        
        text_style_layout.addLayout(user_text_layout, 1, 1)
        
        # Formatting colors
        text_style_layout.addWidget(QLabel("Quote Color (\"text\"):"), 2, 0)
        quote_color_layout = QHBoxLayout()
        
        self.quote_color_label = QLabel()
        self.quote_color_label.setFixedSize(100, 30)
        quote_color = getattr(self.character, 'quote_color', '#666666')
        self.quote_color_label.setStyleSheet(f"background-color: {quote_color}; border: 1px solid black;")
        quote_color_layout.addWidget(self.quote_color_label)
        
        quote_color_btn = QPushButton("Choose Color")
        quote_color_btn.clicked.connect(self._choose_quote_color)
        quote_color_layout.addWidget(quote_color_btn)
        quote_color_layout.addStretch()
        
        text_style_layout.addLayout(quote_color_layout, 2, 1)
        
        text_style_layout.addWidget(QLabel("Emphasis Color (**bold**, *italic*):"), 3, 0)
        emphasis_color_layout = QHBoxLayout()
        
        self.emphasis_color_label = QLabel()
        self.emphasis_color_label.setFixedSize(100, 30)
        emphasis_color = getattr(self.character, 'emphasis_color', '#0D47A1')
        self.emphasis_color_label.setStyleSheet(f"background-color: {emphasis_color}; border: 1px solid black;")
        emphasis_color_layout.addWidget(self.emphasis_color_label)
        
        emphasis_color_btn = QPushButton("Choose Color")
        emphasis_color_btn.clicked.connect(self._choose_emphasis_color)
        emphasis_color_layout.addWidget(emphasis_color_btn)
        emphasis_color_layout.addStretch()
        
        text_style_layout.addLayout(emphasis_color_layout, 3, 1)
        
        text_style_layout.addWidget(QLabel("Strikethrough Color (~~text~~):"), 4, 0)
        strike_color_layout = QHBoxLayout()
        
        self.strikethrough_color_label = QLabel()
        self.strikethrough_color_label.setFixedSize(100, 30)
        strike_color = getattr(self.character, 'strikethrough_color', '#757575')
        self.strikethrough_color_label.setStyleSheet(f"background-color: {strike_color}; border: 1px solid black;")
        strike_color_layout.addWidget(self.strikethrough_color_label)
        
        strike_color_btn = QPushButton("Choose Color")
        strike_color_btn.clicked.connect(self._choose_strikethrough_color)
        strike_color_layout.addWidget(strike_color_btn)
        strike_color_layout.addStretch()
        
        text_style_layout.addLayout(strike_color_layout, 4, 1)
        
        text_style_layout.addWidget(QLabel("Code Text Color (`code`):"), 5, 0)
        code_text_layout = QHBoxLayout()
        
        self.code_text_color_label = QLabel()
        self.code_text_color_label.setFixedSize(100, 30)
        code_text_color = getattr(self.character, 'code_text_color', '#D32F2F')
        self.code_text_color_label.setStyleSheet(f"background-color: {code_text_color}; border: 1px solid black;")
        code_text_layout.addWidget(self.code_text_color_label)
        
        code_text_btn = QPushButton("Choose Color")
        code_text_btn.clicked.connect(self._choose_code_text_color)
        code_text_layout.addWidget(code_text_btn)
        code_text_layout.addStretch()
        
        text_style_layout.addLayout(code_text_layout, 5, 1)
        
        # Link color
        text_style_layout.addWidget(QLabel("Link Color (URLs):"), 6, 0)
        link_color_layout = QHBoxLayout()
        
        self.link_color_label = QLabel()
        self.link_color_label.setFixedSize(100, 30)
        link_color = getattr(self.character, 'link_color', '#1976D2')
        self.link_color_label.setStyleSheet(f"background-color: {link_color}; border: 1px solid black;")
        link_color_layout.addWidget(self.link_color_label)
        
        link_color_btn = QPushButton("Choose Color")
        link_color_btn.clicked.connect(self._choose_link_color)
        link_color_layout.addWidget(link_color_btn)
        link_color_layout.addStretch()
        
        text_style_layout.addLayout(link_color_layout, 6, 1)
        
        # Text formatting preview
        text_style_layout.addWidget(QLabel("Preview:"), 7, 0, Qt.AlignTop)
        preview_widget = QWidget()
        preview_widget.setStyleSheet("background-color: white; border: 1px solid #ddd; padding: 10px;")
        preview_layout = QVBoxLayout(preview_widget)
        
        self.text_preview = QLabel()
        self.text_preview.setWordWrap(True)
        self.text_preview.setTextFormat(Qt.RichText)
        self.text_preview.setOpenExternalLinks(True)
        self.text_preview.setTextInteractionFlags(Qt.LinksAccessibleByMouse)
        preview_layout.addWidget(self.text_preview)
        
        text_style_layout.addWidget(preview_widget, 7, 1)
        
        text_style_widget.setLayout(text_style_layout)
        tabs.addTab(text_style_widget, "Text Style")
        
        # ===== TYPOGRAPHY TAB - WITH LIVE UPDATES =====
        typography_widget = QWidget()
        typography_layout = QGridLayout()
        
        # Font family - LIVE UPDATE
        typography_layout.addWidget(QLabel("Font Family:"), 0, 0)
        self.font_combo = QComboBox()
        self.font_combo.addItems([
            "Arial", "Segoe UI", "Helvetica", "Times New Roman",
            "Georgia", "Verdana", "Tahoma", "Calibri", "Comic Sans MS"
        ])
        self.font_combo.setCurrentText(self.character.text_font)
        self.font_combo.currentTextChanged.connect(self._live_update_typography)
        typography_layout.addWidget(self.font_combo, 0, 1)
        
        # Font size - LIVE UPDATE
        typography_layout.addWidget(QLabel("Font Size:"), 1, 0)
        self.size_slider = QSlider(Qt.Horizontal)
        self.size_slider.setRange(8, 20)
        self.size_slider.setValue(self.character.text_size)
        self.size_slider.valueChanged.connect(self._live_update_typography)
        
        size_layout = QHBoxLayout()
        size_layout.addWidget(self.size_slider)
        self.size_label = QLabel(f"{self.character.text_size}px")
        self.size_label.setFixedWidth(40)
        size_layout.addWidget(self.size_label)
        
        typography_layout.addLayout(size_layout, 1, 1)
        

        # Basic preview (without formatting)
        typography_layout.addWidget(QLabel("Basic Preview:"), 3, 0, Qt.AlignTop)
        basic_preview_widget = QWidget()
        basic_preview_widget.setStyleSheet("background-color: white; border: 1px solid #ddd;")
        basic_preview_layout = QVBoxLayout(basic_preview_widget)
        
        self.char_preview = QLabel("Character: Hello there!")
        self.char_preview.setWordWrap(True)
        basic_preview_layout.addWidget(self.char_preview)
        
        self.user_preview = QLabel("User: Hi! How are you?")
        self.user_preview.setWordWrap(True)
        self.user_preview.setAlignment(Qt.AlignRight)
        basic_preview_layout.addWidget(self.user_preview)
        
        typography_layout.addWidget(basic_preview_widget, 3, 1)
        
        typography_widget.setLayout(typography_layout)
        tabs.addTab(typography_widget, "Typography")

        # ===== EXTERNAL APIS TAB - WITH LIVE UPDATES =====
        external_apis_widget = QWidget()
        external_apis_layout = QVBoxLayout()

        external_apis_label = QLabel("External APIs")
        external_apis_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        external_apis_layout.addWidget(external_apis_label)

        # API toggles with LIVE updates
        self.api_toggles_layout = QVBoxLayout()
        self._setup_api_toggles_with_live_update()
        external_apis_layout.addLayout(self.api_toggles_layout)

        # Manage APIs button
        manage_apis_btn = QPushButton("🔧 Manage APIs")
        manage_apis_btn.clicked.connect(self._open_external_apis_manager)
        external_apis_layout.addWidget(manage_apis_btn)

        external_apis_layout.addStretch()
        external_apis_widget.setLayout(external_apis_layout)
        tabs.addTab(external_apis_widget, "External APIs")
        
        # *** ONLY OK AND CANCEL BUTTONS ***
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Reset button
        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_defaults)
        button_layout.addWidget(reset_btn)
        
        # OK button - keeps all changes
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)
        
        # Cancel button - restores original state
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self._cancel_and_restore)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Update preview initially
        self._update_preview()
    
    # ===== LIVE UPDATE METHODS =====
    
    def _live_update_typography(self):
        """Live update typography settings"""
        # Update character object immediately
        self.character.text_font = self.font_combo.currentText()
        self.character.text_size = self.size_slider.value()
        
        # Update size label
        self.size_label.setText(f"{self.character.text_size}px")
        
        # Update preview
        self._update_preview()
        
        # Save immediately to file
        self._save_character_config_silent()
        
        # Update live chat bubbles if window is open
        self._update_live_chat_bubbles()
    

    
    def _live_update_char_transparency(self, value):
        """Live update character transparency"""
        self.char_transparency_label.setText(f"{value}%")
        self.character.bubble_transparency = value
        
        # Update preview
        self._update_preview()
        
        # Save immediately to file
        self._save_character_config_silent()
        
        # Update live chat bubbles
        self._update_live_chat_bubbles()
    
    def _live_update_user_transparency(self, value):
        """Live update user transparency"""
        self.user_transparency_label.setText(f"{value}%")
        self.character.user_bubble_transparency = value
        
        # Update preview
        self._update_preview()
        
        # Save immediately to file
        self._save_character_config_silent()
        
        # Update live chat bubbles
        self._update_live_chat_bubbles()
        
    
    def _live_update_api_toggle(self, api_obj, checked):
        """Live update external API toggle"""
        # Find and update the API in character's external_apis list
        for api in self.character.external_apis:
            if (isinstance(api, dict) and api.get('name') == api_obj.name) or \
               (hasattr(api, 'name') and api.name == api_obj.name):
                if isinstance(api, dict):
                    api['enabled'] = checked
                else:
                    api.enabled = checked
                break
        
        # Save immediately to file
        self._save_character_config_silent()
        
    
    # ===== COLOR CHOOSER METHODS WITH LIVE UPDATES =====
    def _choose_bubble_color(self):
        color = QColorDialog.getColor(QColor(self.character.bubble_color), self)
        if color.isValid():
            self.character.bubble_color = color.name()
            self.bubble_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_user_bubble_color(self):
        color = QColorDialog.getColor(QColor(self.character.user_bubble_color), self)
        if color.isValid():
            self.character.user_bubble_color = color.name()
            self.user_bubble_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_text_color(self):
        color = QColorDialog.getColor(QColor(self.character.text_color), self)
        if color.isValid():
            self.character.text_color = color.name()
            self.text_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_user_text_color(self):
        color = QColorDialog.getColor(QColor(self.character.user_text_color), self)
        if color.isValid():
            self.character.user_text_color = color.name()
            self.user_text_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_quote_color(self):
        current_color = getattr(self.character, 'quote_color', '#666666')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.character.quote_color = color.name()
            self.quote_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_emphasis_color(self):
        current_color = getattr(self.character, 'emphasis_color', '#0D47A1')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.character.emphasis_color = color.name()
            self.emphasis_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_strikethrough_color(self):
        current_color = getattr(self.character, 'strikethrough_color', '#757575')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.character.strikethrough_color = color.name()
            self.strikethrough_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_code_text_color(self):
        current_color = getattr(self.character, 'code_text_color', '#D32F2F')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.character.code_text_color = color.name()
            self.code_text_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    def _choose_link_color(self):
        current_color = getattr(self.character, 'link_color', '#1976D2')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            self.character.link_color = color.name()
            self.link_color_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
    
    # ===== EXTERNAL APIs METHODS =====
    def _setup_api_toggles_with_live_update(self):
        """Setup API toggles with LIVE UPDATE functionality"""
        # Clear existing toggles
        while self.api_toggles_layout.count():
            child = self.api_toggles_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Convert external_apis dictionaries to objects if needed
        if hasattr(self.character, 'external_apis') and self.character.external_apis:
            converted_apis = []
            for api in self.character.external_apis:
                if isinstance(api, dict):
                    try:
                        api_obj = ExternalAPI(**api)
                        converted_apis.append(api_obj)
                    except Exception as e:
                        print(f"⚠️ Error converting external API in dialog: {e}")
                        continue
                else:
                    converted_apis.append(api)
            self.character.external_apis = converted_apis
        
        # Create toggles for each API
        if hasattr(self.character, 'external_apis') and self.character.external_apis:
            for api in self.character.external_apis:
                api_layout = QHBoxLayout()
                
                # Toggle checkbox with LIVE UPDATE
                toggle = QCheckBox()
                toggle.setChecked(api.enabled)
                toggle.toggled.connect(lambda checked, api_obj=api: self._live_update_api_toggle(api_obj, checked))
                api_layout.addWidget(toggle)
                
                # API info
                api_info = QLabel(f"{api.name} - {api.method} {api.url}")
                api_layout.addWidget(api_info)
                
                api_layout.addStretch()
                
                # Test button
                test_btn = QPushButton("Test")
                test_btn.clicked.connect(lambda checked=False, a=api: self._test_external_api(a))
                api_layout.addWidget(test_btn)
                
                widget = QWidget()
                widget.setLayout(api_layout)
                self.api_toggles_layout.addWidget(widget)
        
        if not hasattr(self.character, 'external_apis') or not self.character.external_apis:
            no_apis_label = QLabel("No external APIs configured")
            no_apis_label.setStyleSheet("color: #666; font-style: italic;")
            self.api_toggles_layout.addWidget(no_apis_label)
    
    def _test_external_api(self, api: ExternalAPI):
        """Test external API from settings with parameter replacement"""
        if not api.enabled:
            QMessageBox.warning(self, "API Disabled", "Please enable the API first.")
            return
        
        try:
            import requests
            
            progress = QProgressDialog("Testing API...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()
            
            # Handle parameter replacement for testing
            test_params = {}
            
            for key, value in api.params.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    param_name = value[1:-1]
                    
                    # Provide default test values for common parameters
                    if param_name == "game_id":
                        test_params[key] = "730"
                    elif param_name == "api_key":
                        test_params[key] = "YOUR_API_KEY_HERE"
                    elif param_name == "count" or param_name == "news_count":
                        test_params[key] = "3"
                    elif param_name == "maxlength" or param_name == "max_length":
                        test_params[key] = "300"
                    else:
                        test_params[key] = f"test_{param_name}"
                else:
                    test_params[key] = value
            
            response = requests.request(
                api.method,
                api.url,
                headers=api.headers,
                params=test_params,
                timeout=api.timeout
            )
            
            progress.close()
            
            if response.status_code == 200:
                QMessageBox.information(self, "Test Success", 
                                    f"✅ {api.name} test successful!\n\nStatus: {response.status_code}")
            else:
                QMessageBox.warning(self, "Test Failed", 
                                f"❌ {api.name} returned status {response.status_code}")
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Test Error", f"❌ Test failed:\n{str(e)}")
    
    def _open_external_apis_manager(self):
        """Open external APIs manager and refresh toggles"""
        dialog = ExternalAPIManager(self, self.character)
        if dialog.exec():
            # Refresh the API toggles after managing APIs
            self._setup_api_toggles_with_live_update()
    
    # ===== UTILITY METHODS =====
    def _save_character_config_silent(self):
        """Save character configuration to file silently (no messages)"""
        try:       
            folder_name = getattr(self.character, 'folder_name', self.character.name)
            app_data_dir = get_app_data_dir()
            config_file = app_data_dir / "characters" / folder_name / "config.json"
            
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert character to dict
            char_data = asdict(self.character)
            
            # Save to file
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(char_data, f, indent=2)
                    
        except Exception:
            pass  # Silent fail
    
    def _update_live_chat_bubbles(self):
        """Update chat bubbles in real-time WITHOUT LAG"""
        try:
            parent_window = self.parent()
            if parent_window and hasattr(parent_window, 'bubble_widgets'):
                
                # ✅ SOLUTION: Disable updates for ALL bubbles first
                parent_window.setUpdatesEnabled(False)
                if hasattr(parent_window, 'chat_area'):
                    parent_window.chat_area.setUpdatesEnabled(False)
                
                # Disable individual bubble updates
                for bubble in parent_window.bubble_widgets.values():
                    bubble.setUpdatesEnabled(False)
                    if hasattr(bubble, 'bubble_label'):
                        bubble.bubble_label.setUpdatesEnabled(False)
                
                # ✅ SOLUTION: Update all bubbles WITHOUT triggering repaints
                for bubble in parent_window.bubble_widgets.values():
                    try:
                        if hasattr(parent_window, '_update_single_bubble_color'):
                            parent_window._update_single_bubble_color(bubble)
                        elif hasattr(parent_window, '_update_single_bubble_style'):
                            parent_window._update_single_bubble_style(bubble)
                    except:
                        pass
                
                # ✅ SOLUTION: Re-enable updates for ALL bubbles (single repaint)
                for bubble in parent_window.bubble_widgets.values():
                    bubble.setUpdatesEnabled(True)
                    if hasattr(bubble, 'bubble_label'):
                        bubble.bubble_label.setUpdatesEnabled(True)
                
                parent_window.chat_area.setUpdatesEnabled(True)
                parent_window.setUpdatesEnabled(True)
                
        except Exception as e:
            print(f"Error updating live chat bubbles: {e}")
    

    
    def _update_parent_character_references_with_reload(self):
        """Update parent window character references by RELOADING from file"""
        try:
            parent_window = self.parent()
            
            # For ChatWindow - RELOAD from file like the original code
            if hasattr(parent_window, 'character_manager'):
                reloaded_char = parent_window.character_manager.load_character(self.character.name)
                if reloaded_char:
                    parent_window.character = reloaded_char
                    # Also update our dialog's character reference
                    self.character = reloaded_char
                    print(f"✅ Reloaded chat window character")

            
            # Also update main application if accessible
            main_app = parent_window.parent() if hasattr(parent_window, 'parent') else None
            if main_app and hasattr(main_app, 'current_character'):
                if main_app.current_character and main_app.current_character.name == self.character.name:
                    if hasattr(main_app, 'character_manager'):
                        reloaded_char = main_app.character_manager.load_character(self.character.name)
                        if reloaded_char:
                            main_app.current_character = reloaded_char
                            print(f"✅ Updated main app character")
                    else:
                        main_app.current_character = self.character
                        print(f"✅ Updated main app character")
                    
        except Exception as e:
            print(f"Error updating parent character references with reload: {e}")
    
    def _update_preview(self):
        """Update all previews with transparency and text formatting"""
        font_family = self.font_combo.currentText()
        font_size = self.size_slider.value()
        
        # Character bubble with transparency
        char_transparency = getattr(self.character, 'bubble_transparency', 0)
        if char_transparency > 0:
            char_bg_color = hex_to_rgba(self.character.bubble_color, char_transparency)
        else:
            char_bg_color = self.character.bubble_color
        
        # User bubble with transparency
        user_transparency = getattr(self.character, 'user_bubble_transparency', 0)
        if user_transparency > 0:
            user_bg_color = hex_to_rgba(self.character.user_bubble_color, user_transparency)
        else:
            user_bg_color = self.character.user_bubble_color
        
        # Get text formatting colors with defaults
        quote_color = getattr(self.character, 'quote_color', '#666666')
        emphasis_color = getattr(self.character, 'emphasis_color', '#0D47A1')
        strikethrough_color = getattr(self.character, 'strikethrough_color', '#757575')
        code_bg_color = getattr(self.character, 'code_bg_color', 'rgba(0,0,0,0.1)')
        code_text_color = getattr(self.character, 'code_text_color', '#D32F2F')
        link_color = getattr(self.character, 'link_color', '#1976D2')
        
        # Update character bubble preview
        char_style = f"""
            background-color: {char_bg_color};
            color: {self.character.text_color};
            padding: 10px;
            border-radius: 12px;
            font-family: {font_family};
            font-size: {font_size}px;
            margin: 5px;
        """
        self.char_preview.setStyleSheet(char_style)
        
        # Update user bubble preview
        user_style = f"""
            background-color: {user_bg_color};
            color: {self.character.user_text_color};
            padding: 10px;
            border-radius: 12px;
            font-family: {font_family};
            font-size: {font_size}px;
            margin: 5px;
        """
        self.user_preview.setStyleSheet(user_style)
        
        # Create rich text preview if text_preview exists
        if hasattr(self, 'text_preview'):
            preview_text = f"""
            <div style="font-family: {font_family}; font-size: {font_size}px; color: {self.character.text_color};">
                <p>This is <strong style="color: {emphasis_color};">bold text</strong> and <em style="color: {emphasis_color};">italic text</em>.</p>
                
                <blockquote style="border-left: 4px solid {quote_color}; margin: 10px 0; padding-left: 10px; color: {quote_color};">
                    This is a quoted text block that shows the quote formatting.
                </blockquote>
                
                <p>Here's some <del style="color: {strikethrough_color};">strikethrough text</del> for comparison.</p>
                
                <code style="background-color: {code_bg_color}; color: {code_text_color}; font-family: monospace; padding: 1px 4px; border-radius: 3px;">Code text</code><br>
                
                <hr style="border: none; height: 2px; background-color: #ddd; margin: 10px 0;">
                
                <a href="https://example.com" style="color: {link_color}; text-decoration: underline;">https://example.com</a><br>
                Visit <a href="http://www.google.com" style="color: {link_color}; text-decoration: underline;">www.google.com</a> for more info
            </div>
            """
            self.text_preview.setText(preview_text)
    
    def _reset_defaults(self):
        """Reset all settings to defaults with live updates"""
        reply = QMessageBox.question(
            self, 
            "Reset to Defaults", 
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset bubble colors
            self.character.bubble_color = "#E3F2FD"
            self.character.user_bubble_color = "#F0F0F0"
            self.character.bubble_transparency = 0
            self.character.user_bubble_transparency = 0
            
            # Reset text colors
            self.character.text_color = "#1976D2"
            self.character.user_text_color = "#333333"
            self.character.quote_color = "#666666"
            self.character.emphasis_color = "#0D47A1"
            self.character.strikethrough_color = "#757575"
            self.character.code_bg_color = "rgba(0,0,0,0.1)"
            self.character.code_text_color = "#D32F2F"
            self.character.link_color = "#1976D2"
            
            # Reset typography
            self.character.text_font = "Arial"
            self.character.text_size = 11

            
            # Update UI elements
            self.bubble_color_label.setStyleSheet(f"background-color: {self.character.bubble_color}; border: 1px solid black;")
            self.user_bubble_color_label.setStyleSheet(f"background-color: {self.character.user_bubble_color}; border: 1px solid black;")
            self.text_color_label.setStyleSheet(f"background-color: {self.character.text_color}; border: 1px solid black;")
            self.user_text_color_label.setStyleSheet(f"background-color: {self.character.user_text_color}; border: 1px solid black;")
            self.quote_color_label.setStyleSheet(f"background-color: {self.character.quote_color}; border: 1px solid black;")
            self.emphasis_color_label.setStyleSheet(f"background-color: {self.character.emphasis_color}; border: 1px solid black;")
            self.strikethrough_color_label.setStyleSheet(f"background-color: {self.character.strikethrough_color}; border: 1px solid black;")
            self.code_text_color_label.setStyleSheet(f"background-color: {self.character.code_text_color}; border: 1px solid black;")
            self.link_color_label.setStyleSheet(f"background-color: {self.character.link_color}; border: 1px solid black;")
            
            self.font_combo.setCurrentText(self.character.text_font)
            self.size_slider.setValue(self.character.text_size)
            self.char_transparency_slider.setValue(0)
            self.user_transparency_slider.setValue(0)
            self.char_transparency_label.setText("0%")
            self.user_transparency_label.setText("0%")
            self.size_label.setText("11px")
            
            # Save and update
            self._update_preview()
            self._save_character_config_silent()
            self._update_live_chat_bubbles()
            self._update_parent_character_references_with_reload()
            
            print("🔄 Reset all settings to defaults")
    
    def _cancel_and_restore(self):
        """Cancel changes and restore original state"""
        reply = QMessageBox.question(
            self, 
            "Cancel Changes", 
            "Are you sure you want to cancel all changes and restore original settings?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            import copy
            
            # Restore all original values
            self.character.text_font = self.original_state['text_font']
            self.character.text_size = self.original_state['text_size']
            
            self.character.bubble_color = self.original_state['bubble_color']
            self.character.user_bubble_color = self.original_state['user_bubble_color']
            self.character.bubble_transparency = self.original_state['bubble_transparency']
            self.character.user_bubble_transparency = self.original_state['user_bubble_transparency']
            
            self.character.text_color = self.original_state['text_color']
            self.character.user_text_color = self.original_state['user_text_color']
            self.character.quote_color = self.original_state['quote_color']
            self.character.emphasis_color = self.original_state['emphasis_color']
            self.character.strikethrough_color = self.original_state['strikethrough_color']
            self.character.code_bg_color = self.original_state['code_bg_color']
            self.character.code_text_color = self.original_state['code_text_color']
            self.character.link_color = self.original_state['link_color']
            
            # Restore external APIs
            self.character.external_apis = copy.deepcopy(self.original_state['external_apis'])
            
            # Save restored state to file
            self._save_character_config_silent()
            
            # Update parent references with reload
            self._update_parent_character_references_with_reload()
            
            # Update live chat bubbles
            self._update_live_chat_bubbles()
            
            print("🔄 Restored all settings to original state")
            
            self.reject()
    
    # ===== REMOVE OLD METHODS - NOT NEEDED ANYMORE =====
    # _apply_settings, _save_settings, _update_character_settings are replaced by live updates

class BackgroundImageDialog(QDialog):
    """Dialog for selecting and positioning chat background image"""
    def __init__(self, parent, current_settings: Optional[BackgroundImageSettings] = None):
        super().__init__(parent)
        
        self.settings = current_settings
        self.image_path = current_settings.image_path if current_settings else None
        self.original_pixmap = None
        self.scale = current_settings.scale if current_settings else 1.0
        self.offset_x = current_settings.offset_x if current_settings else 0
        self.offset_y = current_settings.offset_y if current_settings else 0
        
        self.setWindowTitle("Background Image Settings")
        self.setModal(True)
        self.resize(800, 600)
        
        self._setup_ui()
        
        # Load image if exists - no validation warnings
        if self.image_path and os.path.exists(self.image_path):
            self._load_image(self.image_path)
    
    def _setup_ui(self):
        """Create the interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Instructions
        instructions = QLabel("Select and adjust your chat background image")
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setStyleSheet("font-size: 12pt; padding: 10px;")
        layout.addWidget(instructions)
        
        # Main content area
        content_layout = QHBoxLayout()
        
        # Left side - Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout()
        
        # Preview widget with chat simulation
        self.preview_label = QLabel()
        self.preview_label.setFixedSize(350, 450)
        self.preview_label.setStyleSheet("""
            QLabel {
                background-color: #F5F5F5;
                border: 2px dashed #CCCCCC;
                border-radius: 5px;
            }
        """)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setText("Select an image to preview")
        
        preview_layout.addWidget(self.preview_label, alignment=Qt.AlignCenter)
        
        # Add status label
        self.preview_info = QLabel("No image loaded")
        self.preview_info.setStyleSheet("color: #666; font-size: 9pt;")
        self.preview_info.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_info)
        
        preview_group.setLayout(preview_layout)
        content_layout.addWidget(preview_group)
        
        # Right side - Controls (keep this unchanged)
        controls_group = QGroupBox("Adjustments")
        controls_layout = QVBoxLayout()
        
        # Image selection
        select_layout = QHBoxLayout()
        self.image_label = QLabel("No image selected")
        self.image_label.setStyleSheet("background-color: #f0f0f0; padding: 5px;")
        select_layout.addWidget(self.image_label)
        
        select_btn = QPushButton("Select Image")
        select_btn.clicked.connect(self._select_image)
        select_layout.addWidget(select_btn)
        controls_layout.addLayout(select_layout)
        
        controls_layout.addSpacing(20)
        
        # Zoom control
        zoom_label = QLabel("Zoom:")
        controls_layout.addWidget(zoom_label)
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(0, 400)  # Changed from (50, 300) to allow 0.25x to 4x zoom
        self.zoom_slider.setValue(int(self.scale * 100))
        self.zoom_slider.valueChanged.connect(self._update_zoom)
        controls_layout.addWidget(self.zoom_slider)
        
        self.zoom_value_label = QLabel(f"{self.scale:.1f}x")
        controls_layout.addWidget(self.zoom_value_label)
        
        controls_layout.addSpacing(20)
        
        # Position controls
        position_label = QLabel("Position:")
        controls_layout.addWidget(position_label)
        
        # Position buttons in a grid
        position_grid = QGridLayout()
        
        # Arrow buttons for positioning
        up_btn = QPushButton("↑")
        up_btn.clicked.connect(lambda: self._move_image(0, -10))
        position_grid.addWidget(up_btn, 0, 1)
        
        left_btn = QPushButton("←")
        left_btn.clicked.connect(lambda: self._move_image(-10, 0))
        position_grid.addWidget(left_btn, 1, 0)
        
        self.center_btn = QPushButton("⊙")
        self.center_btn.setToolTip("Center image")
        self.center_btn.clicked.connect(self._center_image)
        position_grid.addWidget(self.center_btn, 1, 1)
        
        right_btn = QPushButton("→")
        right_btn.clicked.connect(lambda: self._move_image(10, 0))
        position_grid.addWidget(right_btn, 1, 2)
        
        down_btn = QPushButton("↓")
        down_btn.clicked.connect(lambda: self._move_image(0, 10))
        position_grid.addWidget(down_btn, 2, 1)
        
        controls_layout.addLayout(position_grid)
        
        controls_layout.addSpacing(20)
        
        # Preset options
        preset_label = QLabel("Presets:")
        controls_layout.addWidget(preset_label)
        
        fit_btn = QPushButton("Fit to Window")
        fit_btn.clicked.connect(self._fit_to_window)
        controls_layout.addWidget(fit_btn)
        
        fill_btn = QPushButton("Fill Window")
        fill_btn.clicked.connect(self._fill_window)
        controls_layout.addWidget(fill_btn)
        
        reset_btn = QPushButton("Reset")
        reset_btn.clicked.connect(self._reset_position)
        controls_layout.addWidget(reset_btn)
        
        controls_layout.addStretch()
        
        # Info label
        self.info_label = QLabel("Tip: Use arrow buttons or drag the preview to position")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: gray; font-size: 9pt;")
        controls_layout.addWidget(self.info_label)
        
        controls_group.setLayout(controls_layout)
        content_layout.addWidget(controls_group)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply)
        button_layout.addWidget(self.apply_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Enable mouse dragging on preview
        self._setup_dragging()
    # Add this method to BackgroundImageDialog class to constrain offsets

    def _constrain_offsets(self):
        """Remove restrictive offset constraints for preview"""
        # Allow much larger offsets for preview
        if not self.original_pixmap:
            return
        
        # Get dimensions
        scaled_width = int(self.original_pixmap.width() * self.scale)
        scaled_height = int(self.original_pixmap.height() * self.scale)
        
        # Allow offsets up to the full image size (much more permissive)
        max_offset_x = scaled_width
        max_offset_y = scaled_height
        
        # Only constrain if offsets are extremely large
        self.offset_x = max(-max_offset_x, min(max_offset_x, self.offset_x))
        self.offset_y = max(-max_offset_y, min(max_offset_y, self.offset_y))
    
    def _create_sample_chat(self):
        """Create sample chat bubbles for preview"""
        # Create overlay widget for chat bubbles
        overlay = QWidget(self.preview_widget)
        overlay.setGeometry(0, 0, 350, 450)
        overlay.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        overlay_layout = QVBoxLayout(overlay)
        overlay_layout.setContentsMargins(10, 10, 10, 10)
        overlay_layout.setSpacing(10)
        
        # Sample messages
        messages = [
            ("Hello! How are you?", True),  # True = user message
            ("I'm doing great, thanks!", False),
            ("That's wonderful to hear!", True)
        ]
        
        for text, is_user in messages:
            bubble_container = QWidget()
            bubble_container.setMaximumHeight(60)
            
            bubble_layout = QHBoxLayout(bubble_container)
            bubble_layout.setContentsMargins(0, 0, 0, 0)
            
            if is_user:
                bubble_layout.addStretch()
            
            bubble = QLabel(text)
            bubble.setWordWrap(True)
            bubble.setMaximumWidth(200)
            bubble.setStyleSheet(f"""
                background-color: {'#F0F0F0' if is_user else '#E3F2FD'};
                color: {'#333333' if is_user else '#1976D2'};
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #ddd;
            """)
            
            bubble_layout.addWidget(bubble)
            
            if not is_user:
                bubble_layout.addStretch()
            
            overlay_layout.addWidget(bubble_container)
        
        overlay_layout.addStretch()
        
        # Keep reference
        self.chat_overlay = overlay
    
    def _setup_dragging(self):
        """Setup mouse dragging for preview"""
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.preview_label.installEventFilter(self)  # Changed from preview_container to preview_label

    # FIND your BackgroundImageDialog.eventFilter method and REPLACE it:

    def eventFilter(self, obj, event):
        """Handle mouse events for dragging"""
        if obj == self.preview_label:  # Changed from preview_container to preview_label
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self.dragging = True
                self.drag_start_pos = event.position().toPoint()
                self.drag_start_offset_x = self.offset_x
                self.drag_start_offset_y = self.offset_y
                return True
            
            elif event.type() == QEvent.MouseMove and self.dragging:
                delta = event.position().toPoint() - self.drag_start_pos
                self.offset_x = self.drag_start_offset_x + delta.x()
                self.offset_y = self.drag_start_offset_y + delta.y()
                self._update_preview()
                return True
            
            elif event.type() == QEvent.MouseButtonRelease:
                self.dragging = False
                return True
        
        return super().eventFilter(obj, event)
    
    def _select_image(self):
        """Select background image with better file dialog"""
        # Start from the directory of current image if it exists
        start_dir = ""
        if self.image_path and os.path.exists(self.image_path):
            start_dir = os.path.dirname(self.image_path)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Background Image",
            start_dir,  # Start from current image directory
            "Image files (*.png *.jpg *.jpeg *.gif *.bmp);;All files (*.*)"
        )
        
        if filename:
            self._load_image(filename)

        # Update the _load_image method to validate loaded settings
    def _load_image(self, filename):
        """Load and display image with proper preview scaling"""
        try:
            self.original_pixmap = QPixmap(filename)
            if self.original_pixmap.isNull():
                QMessageBox.critical(self, "Error", "Failed to load image")
                return
            
            self.image_path = filename
            self.image_label.setText(filename.split('/')[-1])
            self.apply_btn.setEnabled(True)
            
            # If we have existing settings for this exact image, use them
            if (hasattr(self, 'settings') and self.settings and 
                filename == self.settings.image_path):
                print(f"Using existing settings: scale={self.scale}")
                self.zoom_slider.setValue(int(self.scale * 100))
                self.zoom_value_label.setText(f"{self.scale:.1f}x")
                self._update_preview()
            else:
                # New image - smart fit to ensure it's visible
                self._smart_fit_to_preview()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error loading image: {str(e)}")

    def _smart_fit_to_preview(self):
        """Smart initial fitting that ensures image is visible"""
        if not self.original_pixmap:
            return
        
        # Get dimensions
        img_width = self.original_pixmap.width()
        img_height = self.original_pixmap.height()
        preview_width = self.preview_label.width()
        preview_height = self.preview_label.height()
        
        # Calculate scale to fit in preview with margin
        scale_x = (preview_width * 0.8) / img_width
        scale_y = (preview_height * 0.8) / img_height
        
        # Use smaller scale to ensure image fits
        self.scale = min(scale_x, scale_y)
        self.scale = max(0.05, min(4.0, self.scale))  # Reasonable bounds
        
        # Center the image
        self.offset_x = 0
        self.offset_y = 0
        
        # Update UI
        self.zoom_slider.setValue(int(self.scale * 100))
        self.zoom_value_label.setText(f"{self.scale:.1f}x")
        self._update_preview()
    def _update_zoom(self, value):
        """Update zoom level and refresh preview"""
        self.scale = value / 100.0
        self.zoom_value_label.setText(f"{self.scale:.1f}x")
        self._update_preview()  # Make sure this is called

    def _move_image(self, dx, dy):
        """Move image by offset and refresh preview"""
        self.offset_x += dx
        self.offset_y += dy
        self._constrain_offsets()
        self._update_preview()  # Make sure this is called

    def _center_image(self):
        """Center the image and refresh preview"""
        self.offset_x = 0
        self.offset_y = 0
        self.scale = 1.0
        self.zoom_slider.setValue(100)
        self._update_preview()  # Make sure this is called
    
    def _fit_to_window(self):
        """Fit image to window maintaining aspect ratio"""
        if not self.original_pixmap:
            return
        
        # Calculate scale to fit
        widget_size = self.preview_label.size()
        image_size = self.original_pixmap.size()
        
        scale_x = widget_size.width() / image_size.width()
        scale_y = widget_size.height() / image_size.height()
        
        self.scale = min(scale_x, scale_y)
        self.zoom_slider.setValue(int(self.scale * 100))
        self.offset_x = 0
        self.offset_y = 0
        self._update_preview()
    
    def _fill_window(self):
        """Fill window with image (may crop)"""
        if not self.original_pixmap:
            return
        
        # Calculate scale to fill
        widget_size = self.preview_label.size()
        image_size = self.original_pixmap.size()
        
        scale_x = widget_size.width() / image_size.width()
        scale_y = widget_size.height() / image_size.height()
        
        self.scale = max(scale_x, scale_y)
        self.zoom_slider.setValue(int(self.scale * 100))
        self.offset_x = 0
        self.offset_y = 0
        self._update_preview()
    
    def _reset_position(self):
        """Reset to original settings"""
        if self.settings:
            self.scale = self.settings.scale
            self.offset_x = self.settings.offset_x
            self.offset_y = self.settings.offset_y
            self.zoom_slider.setValue(int(self.scale * 100))
        else:
            self._center_image()
        self._update_preview()
    
    def _update_preview(self):
        """Super lightweight background preview using direct QLabel (no temp files)"""
        if not self.original_pixmap or self.original_pixmap.isNull():
            # No image - show placeholder
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Select an image to preview")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #F5F5F5;
                    border: 2px dashed #CCCCCC;
                    border-radius: 5px;
                    color: #999999;
                }
            """)
            if hasattr(self, 'preview_info'):
                self.preview_info.setText("No image loaded")
            return
        
        try:
            # Create preview image (same size as preview label)
            preview_width = 350
            preview_height = 450
            
            # Create background canvas
            preview_pixmap = QPixmap(preview_width, preview_height)
            preview_pixmap.fill(QColor("#F0F4F8"))  # Light blue chat background
            
            # Calculate scaled image dimensions
            scaled_width = int(self.original_pixmap.width() * self.scale)
            scaled_height = int(self.original_pixmap.height() * self.scale)
            
            # Scale the original image
            scaled_image = self.original_pixmap.scaled(
                scaled_width,
                scaled_height,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            # Paint the scaled image onto the background
            painter = QPainter(preview_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Calculate position (center + offset)
            x = (preview_width - scaled_width) // 2 + self.offset_x
            y = (preview_height - scaled_height) // 2 + self.offset_y
            
            # Draw the background image
            painter.drawPixmap(x, y, scaled_image)
            
            # Draw simple sample bubbles (optional - you can remove this call)
            self._draw_simple_bubbles(painter, preview_width, preview_height)
            
            painter.end()
            
            # **DIRECT APPLICATION TO QLABEL (NO TEMP FILES!)**
            self.preview_label.setPixmap(preview_pixmap)
            self.preview_label.setText("")  # Clear any text
            self.preview_label.setStyleSheet("""
                QLabel {
                    border: 1px solid #CCCCCC;
                    border-radius: 5px;
                }
            """)
            
            # Update info label if it exists
            if hasattr(self, 'preview_info'):
                self.preview_info.setText(f"Scale: {self.scale:.1f}x | Offset: ({self.offset_x}, {self.offset_y})")
            
            # Simple success log (no spam)
            # print(f"✅ BG Preview: {self.scale:.1f}x, ({self.offset_x}, {self.offset_y})")
            
        except Exception as e:
            print(f"❌ BG Preview error: {e}")
            # Show error state
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Preview Error")
            self.preview_label.setStyleSheet("""
                QLabel {
                    background-color: #FFEEEE;
                    border: 2px solid #FF6666;
                    border-radius: 5px;
                    color: #CC0000;
                }
            """)




    def _draw_simple_bubbles(self, painter, width, height):
        """Draw simple sample chat bubbles (lightweight version)"""
        try:
            # Simple bubbles - just rectangles with text
            bubbles = [
                {"text": "Hello!", "x": 20, "y": 50, "width": 100, "user": True},
                {"text": "Hi there!", "x": 230, "y": 120, "width": 100, "user": False},
                {"text": "Nice!", "x": 20, "y": 200, "width": 80, "user": True},
            ]
            
            painter.setFont(QFont("Arial", 9))
            
            for bubble in bubbles:
                # Draw simple bubble background
                if bubble["user"]:
                    painter.fillRect(bubble["x"], bubble["y"], bubble["width"], 25, QColor(240, 240, 240, 200))  # Semi-transparent
                    painter.setPen(QColor("#333333"))
                else:
                    painter.fillRect(bubble["x"], bubble["y"], bubble["width"], 25, QColor(227, 242, 253, 200))  # Semi-transparent
                    painter.setPen(QColor("#1976D2"))
                
                # Draw text
                painter.drawText(
                    bubble["x"] + 5, bubble["y"] + 5, 
                    bubble["width"] - 10, 15,
                    Qt.AlignLeft | Qt.AlignVCenter,
                    bubble["text"]
                )
        except:
            pass  # Ignore bubble drawing errors




    def _apply_preview_palette(self, preview_pixmap):
        """Fallback method using QPalette"""
        try:
            palette = QPalette()
            palette.setBrush(QPalette.Window, QBrush(preview_pixmap))
            self.preview_label.setPalette(palette)
            self.preview_label.setAutoFillBackground(True)
            self.preview_label.setStyleSheet("border: 1px solid #CCCCCC;")
            print("✅ Applied preview using palette method")
        except Exception as e:
            print(f"❌ Palette preview failed: {e}")

    def _cleanup_preview_temp(self, temp_path):
        """Clean up preview temp file"""
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                print(f"🧹 Cleaned preview temp: {temp_path}")
        except Exception as e:
            print(f"⚠️ Could not clean preview temp: {e}")

    def _apply(self):
        """Apply settings and close"""
        if self.image_path:
            self.settings = BackgroundImageSettings(
                image_path=self.image_path,
                scale=self.scale,
                offset_x=self.offset_x,
                offset_y=self.offset_y
            )
            print(f"Saving background settings: scale={self.scale}, offset_x={self.offset_x}, offset_y={self.offset_y}")
            self.accept()



class ExternalAPIDialog(QDialog):
    """Dialog for adding/editing external API"""
    def __init__(self, parent, api: Optional[ExternalAPI]):
        super().__init__(parent)
        self.api = api
        
        self.setWindowTitle("Edit API" if api else "Add API")
        self.setFixedSize(500, 500)
        self.setModal(True)
        
        self._setup_ui()
        if api:
            self._load_api()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form
        form_layout = QFormLayout()
        
        self.name_edit = QLineEdit()
        form_layout.addRow("Name:", self.name_edit)
        
        self.url_edit = QLineEdit()
        form_layout.addRow("URL:", self.url_edit)
        
        self.method_combo = QComboBox()
        self.method_combo.addItems(["GET", "POST", "PUT", "DELETE"])
        form_layout.addRow("Method:", self.method_combo)
        
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        form_layout.addRow("Description:", self.description_edit)
        
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(True)
        form_layout.addRow("Enabled:", self.enabled_check)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 60)
        self.timeout_spin.setValue(10)
        self.timeout_spin.setSuffix(" seconds")
        form_layout.addRow("Timeout:", self.timeout_spin)
        
        layout.addLayout(form_layout)
        
        # Headers section
        headers_group = QGroupBox("Headers")
        headers_layout = QVBoxLayout()
        
        self.headers_table = QTableWidget(0, 2)
        self.headers_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.headers_table.horizontalHeader().setStretchLastSection(True)
        headers_layout.addWidget(self.headers_table)
        
        headers_btn_layout = QHBoxLayout()
        add_header_btn = QPushButton("Add Header")
        add_header_btn.clicked.connect(self._add_header_row)
        headers_btn_layout.addWidget(add_header_btn)
        
        remove_header_btn = QPushButton("Remove Header")
        remove_header_btn.clicked.connect(self._remove_header_row)
        headers_btn_layout.addWidget(remove_header_btn)
        headers_btn_layout.addStretch()
        
        headers_layout.addLayout(headers_btn_layout)
        headers_group.setLayout(headers_layout)
        layout.addWidget(headers_group)
        
        # Parameters section
        params_group = QGroupBox("Parameters (use {param_name} for replaceable values)")
        params_layout = QVBoxLayout()
        
        self.params_table = QTableWidget(0, 2)
        self.params_table.setHorizontalHeaderLabels(["Key", "Value"])
        self.params_table.horizontalHeader().setStretchLastSection(True)
        params_layout.addWidget(self.params_table)
        
        params_btn_layout = QHBoxLayout()
        add_param_btn = QPushButton("Add Parameter")
        add_param_btn.clicked.connect(self._add_param_row)
        params_btn_layout.addWidget(add_param_btn)
        
        remove_param_btn = QPushButton("Remove Parameter")
        remove_param_btn.clicked.connect(self._remove_param_row)
        params_btn_layout.addWidget(remove_param_btn)
        params_btn_layout.addStretch()
        
        params_layout.addLayout(params_btn_layout)
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        dialog_buttons.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        
        layout.addLayout(dialog_buttons)
    
    def _add_header_row(self):
        row = self.headers_table.rowCount()
        self.headers_table.insertRow(row)
        self.headers_table.setItem(row, 0, QTableWidgetItem(""))
        self.headers_table.setItem(row, 1, QTableWidgetItem(""))
    
    def _remove_header_row(self):
        current_row = self.headers_table.currentRow()
        if current_row >= 0:
            self.headers_table.removeRow(current_row)
    
    def _add_param_row(self):
        row = self.params_table.rowCount()
        self.params_table.insertRow(row)
        self.params_table.setItem(row, 0, QTableWidgetItem(""))
        self.params_table.setItem(row, 1, QTableWidgetItem(""))
    
    def _remove_param_row(self):
        current_row = self.params_table.currentRow()
        if current_row >= 0:
            self.params_table.removeRow(current_row)
    
    def _load_api(self):
        if not self.api:
            return
        
        self.name_edit.setText(self.api.name)
        self.url_edit.setText(self.api.url)
        self.method_combo.setCurrentText(self.api.method)
        self.description_edit.setPlainText(self.api.description)
        self.enabled_check.setChecked(self.api.enabled)
        self.timeout_spin.setValue(self.api.timeout)
        
        # Load headers
        for key, value in self.api.headers.items():
            row = self.headers_table.rowCount()
            self.headers_table.insertRow(row)
            self.headers_table.setItem(row, 0, QTableWidgetItem(key))
            self.headers_table.setItem(row, 1, QTableWidgetItem(value))
        
        # Load parameters
        for key, value in self.api.params.items():
            row = self.params_table.rowCount()
            self.params_table.insertRow(row)
            self.params_table.setItem(row, 0, QTableWidgetItem(key))
            self.params_table.setItem(row, 1, QTableWidgetItem(value))
    
    def get_api(self) -> ExternalAPI:
        # Collect headers
        headers = {}
        for row in range(self.headers_table.rowCount()):
            key_item = self.headers_table.item(row, 0)
            value_item = self.headers_table.item(row, 1)
            if key_item and value_item and key_item.text().strip():
                headers[key_item.text().strip()] = value_item.text().strip()
        
        # Collect parameters
        params = {}
        for row in range(self.params_table.rowCount()):
            key_item = self.params_table.item(row, 0)
            value_item = self.params_table.item(row, 1)
            if key_item and value_item and key_item.text().strip():
                params[key_item.text().strip()] = value_item.text().strip()
        
        return ExternalAPI(
            name=self.name_edit.text().strip(),
            url=self.url_edit.text().strip(),
            method=self.method_combo.currentText(),
            headers=headers,
            params=params,
            enabled=self.enabled_check.isChecked(),
            description=self.description_edit.toPlainText().strip(),
            timeout=self.timeout_spin.value()
        )

class ExternalAPIManager(QDialog):
    """Dialog for managing external APIs"""
    def __init__(self, parent, character: CharacterConfig):
        super().__init__(parent)
        self.character = character
        
        self.setWindowTitle(f"External APIs - {character.display_name}")
        self.setFixedSize(700, 500)
        self.setModal(True)
        
        self._setup_ui()
        self._populate_list()
    
    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        header = QLabel("Manage External APIs for this Character")
        header.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # API list
        list_layout = QHBoxLayout()
        
        self.api_list = QListWidget()
        self.api_list.itemSelectionChanged.connect(self._on_selection_changed)
        list_layout.addWidget(self.api_list)
        
        # Buttons
        btn_layout = QVBoxLayout()
        
        self.add_btn = QPushButton("Add API")
        self.add_btn.clicked.connect(self._add_api)
        btn_layout.addWidget(self.add_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.clicked.connect(self._edit_api)
        self.edit_btn.setEnabled(False)
        btn_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton("Delete")
        self.delete_btn.clicked.connect(self._delete_api)
        self.delete_btn.setEnabled(False)
        btn_layout.addWidget(self.delete_btn)
        
        self.test_btn = QPushButton("Test API")
        self.test_btn.clicked.connect(self._test_api)
        self.test_btn.setEnabled(False)
        btn_layout.addWidget(self.test_btn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        layout.addLayout(list_layout)
        
        # Usage info
        info_label = QLabel("Usage in chat: /use API_NAME param1=value1 param2=value2")
        info_label.setStyleSheet("color: #666; font-style: italic; margin-top: 10px;")
        layout.addWidget(info_label)
        
        # Dialog buttons
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_and_close)
        dialog_buttons.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        dialog_buttons.addWidget(cancel_btn)
        
        layout.addLayout(dialog_buttons)
    
# In your ExternalAPIManager._populate_list method, add this safety check:

    def _populate_list(self):
        self.api_list.clear()
        
        # *** ADD THIS SAFETY CHECK ***
        # Convert external_apis dictionaries to objects if needed
        if hasattr(self.character, 'external_apis') and self.character.external_apis:
            converted_apis = []
            for api in self.character.external_apis:
                if isinstance(api, dict):
                    try:
                        api_obj = ExternalAPI(**api)
                        converted_apis.append(api_obj)
                    except Exception as e:
                        print(f"⚠️ Error converting external API in manager: {e}")
                        continue
                else:
                    converted_apis.append(api)
            self.character.external_apis = converted_apis
        # *** END SAFETY CHECK ***
        
        for api in self.character.external_apis:
            status = "✅" if api.enabled else "❌"
            item_text = f"{status} {api.name} - {api.method} {api.url}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, api)
            self.api_list.addItem(item)
    
    def _on_selection_changed(self):
        has_selection = bool(self.api_list.selectedItems())
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.test_btn.setEnabled(has_selection)
    
    def _add_api(self):
        dialog = ExternalAPIDialog(self, None)
        if dialog.exec():
            new_api = dialog.get_api()
            self.character.external_apis.append(new_api)
            self._populate_list()
    
    def _edit_api(self):
        current = self.api_list.currentItem()
        if not current:
            return
        
        api = current.data(Qt.UserRole)
        dialog = ExternalAPIDialog(self, api)
        if dialog.exec():
            updated_api = dialog.get_api()
            # Replace the API in the list
            index = self.character.external_apis.index(api)
            self.character.external_apis[index] = updated_api
            self._populate_list()
    
    def _delete_api(self):
        current = self.api_list.currentItem()
        if not current:
            return
        
        api = current.data(Qt.UserRole)
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Delete API '{api.name}'?",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.character.external_apis.remove(api)
            self._populate_list()
    
    def _test_api(self):
        """Test selected configuration with parameter replacement"""
        current = self.api_list.currentItem()
        if not current:
            QMessageBox.warning(self, "No Selection", "Please select a configuration to test.")
            return
        
        api = current.data(Qt.UserRole)
        
        # Simple test request
        try:
            import requests
            
            progress = QProgressDialog("Testing API...", "Cancel", 0, 0, self)
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            QApplication.processEvents()
            
            # FIXED: Handle parameter replacement for testing
            test_params = {}
            test_url = api.url
            
            for key, value in api.params.items():
                if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                    param_name = value[1:-1]  # Remove { and }
                    
                    # Provide default test values for common parameters
                    if param_name == "game_id":
                        test_params[key] = "730"  # Counter-Strike 2
                    elif param_name == "api_key":
                        test_params[key] = "YOUR_API_KEY_HERE"
                    elif param_name == "count" or param_name == "news_count":
                        test_params[key] = "3"
                    elif param_name == "maxlength" or param_name == "max_length":
                        test_params[key] = "300"
                    else:
                        # For unknown parameters, ask user or use placeholder
                        test_params[key] = f"test_{param_name}"
                else:
                    test_params[key] = value
            
            print(f"🔍 Testing API with params: {test_params}")
            
            response = requests.request(
                api.method,
                test_url,
                headers=api.headers,
                params=test_params,
                timeout=api.timeout
            )
            
            progress.close()
            
            if response.status_code == 200:
                QMessageBox.information(self, "Test Success", 
                                    f"✅ API test successful!\n\nStatus: {response.status_code}\nResponse: {response.text[:200]}...")
            else:
                QMessageBox.warning(self, "Test Failed", 
                                f"❌ API returned status {response.status_code}\nResponse: {response.text[:200]}...")
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(self, "Test Error", f"❌ Test failed:\n{str(e)}")
    
    def _save_and_close(self):
        # Save character config
        self._save_character_config()
        self.accept()
    
    def _save_character_config(self):
        """Save character configuration to file"""
        app_data_dir = get_app_data_dir()
        config_file = app_data_dir / "characters" / self.character.folder_name / "config.json"
        
        try:
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.character), f, indent=2)
            print(f"✅ Saved external APIs for character '{self.character.folder_name}'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save configuration: {str(e)}")


class CharacterCreationDialog(QDialog):
    """Dialog for creating a new character with separate naming"""
    def __init__(self, parent):
        super().__init__(parent)
        
        self.setWindowTitle("Create New Character")
        self.setFixedSize(500, 650)  # Increased height for new field
        self.setModal(True)
        
        self.image_path = None
        self.result = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create the character creation interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Form layout
        form_layout = QFormLayout()
        
        # Folder Name (for file system)
        self.folder_name_edit = QLineEdit()
        self.folder_name_edit.setPlaceholderText("Used for file organization (no spaces/special chars)")
        self.folder_name_edit.textChanged.connect(self._validate_folder_name)
        form_layout.addRow("Folder Name:", self.folder_name_edit)
        
        # Display Name (for chat)
        self.display_name_edit = QLineEdit()
        self.display_name_edit.setPlaceholderText("Name shown in chat (can have spaces)")
        form_layout.addRow("Display Name:", self.display_name_edit)
        
        # Auto-sync checkbox
        self.sync_names_check = QCheckBox("Auto-sync names")
        self.sync_names_check.setChecked(True)
        self.sync_names_check.toggled.connect(self._toggle_name_sync)
        form_layout.addRow("", self.sync_names_check)
        
        # Connect display name to folder name when syncing
        self.display_name_edit.textChanged.connect(self._sync_names_if_enabled)
        
        # Image (unchanged)
        image_layout = QVBoxLayout()
        self.image_label = QLabel("No image selected")
        self.image_label.setFixedSize(300, 200)
        self.image_label.setStyleSheet("background-color: #F0F0F0; border: 1px solid #ddd;")
        self.image_label.setAlignment(Qt.AlignCenter)
        image_layout.addWidget(self.image_label, alignment=Qt.AlignCenter)
        
        select_btn = QPushButton("Select Image")
        select_btn.clicked.connect(self._select_image)
        image_layout.addWidget(select_btn)
        
        form_layout.addRow("Character Image:", image_layout)
        
        # Personality (with updated template)
        self.personality_edit = QTextEdit()
        self.personality_edit.setMinimumHeight(150)
        template = """You are {{character}}, a [description of character].

Key traits:
- [Trait 1]
- [Trait 2]
- [Trait 3]

Speaking style: [How they talk]
Background: [Brief background]
Goals: [What they want]

Always respond in character and maintain consistency with these traits. 
Address the user as {{user}} in conversations."""
        self.personality_edit.setPlainText(template)
        form_layout.addRow("Personality:", self.personality_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        create_btn = QPushButton("Create")
        create_btn.clicked.connect(self._create)
        button_layout.addWidget(create_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)

    def _validate_folder_name(self):
        """Validate folder name (no special characters)"""
        text = self.folder_name_edit.text()
        # Remove invalid characters for folder names
        valid_text = re.sub(r'[<>:"/\\|?*\s]', '_', text)
        if text != valid_text:
            self.folder_name_edit.blockSignals(True)
            self.folder_name_edit.setText(valid_text)
            self.folder_name_edit.blockSignals(False)

    def _toggle_name_sync(self):
        """Toggle automatic name synchronization"""
        if self.sync_names_check.isChecked():
            self._sync_names_if_enabled()

    def _sync_names_if_enabled(self):
        """Sync folder name with display name if enabled"""
        if self.sync_names_check.isChecked():
            display_name = self.display_name_edit.text()
            # Convert display name to valid folder name
            folder_name = re.sub(r'[<>:"/\\|?*\s]', '_', display_name)
            self.folder_name_edit.blockSignals(True)
            self.folder_name_edit.setText(folder_name)
            self.folder_name_edit.blockSignals(False)
    
    def _select_image(self):
        """Select character image"""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Character Image",
            "",
            "Image files (*.gif *.png *.jpg *.jpeg);;All files (*.*)"
        )
        
        if filename:
            self.image_path = filename
            
            # Show preview
            try:
                pixmap = QPixmap(filename)
                scaled = pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled)
                self.image_label.setText("")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to load image: {str(e)}")
    
    def _create(self):
        """Create the character"""
        folder_name = self.folder_name_edit.text().strip()
        display_name = self.display_name_edit.text().strip()
        personality = self.personality_edit.toPlainText().strip()
        
        # Validate
        if not folder_name:
            QMessageBox.critical(self, "Error", "Please enter a folder name.")
            return
            
        if not display_name:
            QMessageBox.critical(self, "Error", "Please enter a display name.")
            return
            
        if not self.image_path:
            QMessageBox.critical(self, "Error", "Please select a character image.")
            return
            
        if not personality:
            QMessageBox.critical(self, "Error", "Please enter a personality description.")
            return
        
        # Create result
        self.result = {
            "folder_name": folder_name,
            "display_name": display_name,
            "image_path": self.image_path,
            "personality": personality
        }
        
        self.accept()



class CharacterImportDialog(QDialog):
    """Dialog for importing character with name and color settings"""
    def __init__(self, parent, zip_path):
        super().__init__(parent)
        
        self.zip_path = zip_path
        self.folder_name = ""
        self.display_name = ""
        self.color_choice = "preserve"  # NEW: preserve, global, or custom
        
        self.setWindowTitle("Import Character")
        self.setFixedSize(550, 730)  # Increased height for color options and features
        self.setModal(True)

        # Try to extract character info from zip
        self.original_config = self._read_config_from_zip()
        
        self._setup_ui()


    def _detect_package_features(self, import_path):
        """Detect what features are in the import package - UPDATED for interactions"""
        try:
            import zipfile
            import json
            with zipfile.ZipFile(import_path, 'r') as zipf:
                config_data = json.loads(zipf.read('config.json'))
                export_info = config_data.get('_export_info', {})
                
                features_list = []
                
                # Check for character colors
                has_colors = export_info.get('has_character_colors', False)
                if has_colors:
                    colors_info = export_info.get('character_colors_info', {})
                    primary = colors_info.get('primary', 'Unknown')
                    secondary = colors_info.get('secondary', 'Unknown')
                    features_list.append(f"🎨 Custom Colors: {primary} / {secondary}")
                else:
                    features_list.append("🎨 Colors: Uses global settings")
                
                # Check for external APIs
                apis = config_data.get('external_apis', [])
                if apis:
                    enabled_count = sum(1 for api in apis if api.get('enabled', True))
                    features_list.append(f"🔗 External APIs: {len(apis)} total ({enabled_count} enabled)")
                else:
                    features_list.append("🔗 External APIs: None")
                
                # NEW: Check for interactions using zipfile listing
                interaction_files = [f for f in zipf.namelist() if '/interactions/' in f and f.endswith('config.json')]
                interactions_count = len(interaction_files)
                if interactions_count > 0:
                    features_list.append(f"⚡ Interactions: {interactions_count} found")
                    # Try to list interaction names
                    interaction_names = []
                    for int_file in interaction_files[:3]:  # First 3
                        try:
                            int_data = json.loads(zipf.read(int_file))
                            name = int_data.get('name', 'Unknown')
                            interaction_names.append(name)
                        except:
                            # Extract name from path
                            parts = int_file.split('/')
                            if len(parts) >= 3:
                                interaction_names.append(parts[-2])
                    
                    if interaction_names:
                        features_list.append(f"   • {', '.join(interaction_names)}")
                        if interactions_count > 3:
                            features_list.append(f"   • ... and {interactions_count - 3} more")
                else:
                    features_list.append("⚡ Interactions: None")
                
                # Check for typography features
                has_custom_typography = any(
                    config_data.get(field) for field in [
                        'text_color', 'quote_color', 'emphasis_color', 
                        'code_text_color', 'link_color'
                    ]
                )
                if has_custom_typography:
                    features_list.append("📝 Typography: Custom text colors and styles")
                else:
                    features_list.append("📝 Typography: Standard settings")
                
                # Check for transparency
                has_transparency = (
                    config_data.get('bubble_transparency', 0) > 0 or 
                    config_data.get('user_bubble_transparency', 0) > 0
                )
                if has_transparency:
                    features_list.append("💫 Transparency: Custom bubble transparency")
                
                # Version info
                version = export_info.get('export_version', '1.0')
                export_date = export_info.get('export_date', 'Unknown')
                if export_date != 'Unknown':
                    try:
                        from datetime import datetime
                        date_obj = datetime.fromisoformat(export_date.replace('Z', '+00:00'))
                        export_date = date_obj.strftime('%Y-%m-%d')
                    except:
                        pass
                
                features_list.append(f"📦 Package: v{version} (exported {export_date})")
                
                return "\n".join(features_list)
                
        except Exception as e:
            return f"⚠️ Could not read package information: {str(e)}"


    def _read_config_from_zip(self):
        """Read config.json from the zip file"""
        try:
            import zipfile
            import json
            with zipfile.ZipFile(self.zip_path, 'r') as zipf:
                config_data = zipf.read('config.json')
                return json.loads(config_data)
        except Exception as e:
            print(f"Could not read config from zip: {e}")
            return None
    
    def _setup_ui(self):
        """Create enhanced import dialog interface with full feature detection"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Title section
        title_label = QLabel("Import Character Package")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #2C3E50;")
        layout.addWidget(title_label)
        
        # Enhanced Package Contents Section
        package_group = QGroupBox("📦 Package Contents")
        package_layout = QVBoxLayout()
        
        # Get package features
        features_text = self._detect_package_features(self.zip_path)
        features_label = QLabel(features_text)
        features_label.setStyleSheet("""
            background-color: #F8F9FA; 
            padding: 12px; 
            border: 1px solid #DEE2E6; 
            border-radius: 5px;
            font-family: 'Consolas', monospace;
            line-height: 1.4;
        """)
        features_label.setWordWrap(True)
        package_layout.addWidget(features_label)
        
        package_group.setLayout(package_layout)
        layout.addWidget(package_group)
        
        # Character info section - Enhanced
        if self.original_config:
            # Handle both old and new naming systems
            if 'display_name' in self.original_config:
                suggested_display = self.original_config['display_name']
                suggested_folder = self.original_config.get('folder_name', suggested_display)
            elif 'name' in self.original_config:
                suggested_display = self.original_config['name']
                suggested_folder = self.original_config['name']
            else:
                suggested_display = "Imported Character"
                suggested_folder = "imported_character"
            
            # Check for character colors and other features
            export_info = self.original_config.get('_export_info', {})
            has_character_colors = export_info.get('has_character_colors', False)
            
            # Count features for summary
            feature_count = 0
            if has_character_colors:
                feature_count += 1
            if self.original_config.get('external_apis'):
                feature_count += len(self.original_config['external_apis'])
            if self.original_config.get('icon_settings'):
                feature_count += 1
            if self.original_config.get('background_settings'):
                feature_count += 1
            if self.original_config.get('interactions'):
                feature_count += 1
                
        else:
            suggested_display = "Imported Character"
            suggested_folder = "imported_character"
            has_character_colors = False
            feature_count = 0
        
        # Name input section - Enhanced
        name_group = QGroupBox("⚙️ Character Configuration")
        form_layout = QFormLayout()
        
        # Folder name with real-time validation
        self.folder_name_edit = QLineEdit()
        safe_folder_name = re.sub(r'[<>:"/\\|?*\s]', '_', suggested_folder.lower())
        self.folder_name_edit.setText(safe_folder_name)
        self.folder_name_edit.setPlaceholderText("Used for file organization (must be unique)")
        self.folder_name_edit.textChanged.connect(self._validate_folder_name)
        form_layout.addRow("📁 Folder Name:", self.folder_name_edit)
        
        # Folder name validation feedback
        self.folder_validation_label = QLabel("✅ Folder name looks good")
        self.folder_validation_label.setStyleSheet("color: #28A745; font-size: 9pt; margin-left: 20px;")
        form_layout.addRow("", self.folder_validation_label)
        
        # Display name
        self.display_name_edit = QLineEdit()
        self.display_name_edit.setText(suggested_display)
        self.display_name_edit.setPlaceholderText("Name shown in chat and UI")
        form_layout.addRow("💬 Display Name:", self.display_name_edit)
        
        # Auto-sync option with better styling
        self.sync_names_check = QCheckBox("🔄 Auto-sync folder name with display name")
        self.sync_names_check.setChecked(True)
        self.sync_names_check.setStyleSheet("color: #6C757D; font-size: 10pt;")
        self.sync_names_check.toggled.connect(self._toggle_sync)
        form_layout.addRow("", self.sync_names_check)
        
        # Connect for auto-sync
        self.display_name_edit.textChanged.connect(self._sync_if_enabled)
        
        name_group.setLayout(form_layout)
        layout.addWidget(name_group)
        
        # Enhanced Character Colors Section
        colors_group = QGroupBox("🎨 Character Colors")
        colors_layout = QVBoxLayout()
        
        if has_character_colors:
            # Character has colors - give import options
            self.preserve_colors_radio = QRadioButton("✨ Preserve original character colors")
            self.preserve_colors_radio.setChecked(True)
            self.preserve_colors_radio.setStyleSheet("font-weight: bold; color: #007BFF;")
            self.preserve_colors_radio.toggled.connect(self._update_color_choice)
            colors_layout.addWidget(self.preserve_colors_radio)
            
            # Show color preview
            if self.original_config and '_export_info' in self.original_config:
                color_info = self.original_config['_export_info'].get('character_colors_info', {})
                primary_color = color_info.get('primary', '#000000')
                secondary_color = color_info.get('secondary', '#000000')
                
                preview_widget = QWidget()
                preview_layout = QHBoxLayout(preview_widget)
                preview_layout.setContentsMargins(25, 5, 5, 5)
                
                # Color swatches
                primary_swatch = QLabel("●")
                primary_swatch.setStyleSheet(f"color: {primary_color}; font-size: 16px;")
                secondary_swatch = QLabel("●")
                secondary_swatch.setStyleSheet(f"color: {secondary_color}; font-size: 16px;")
                
                preview_text = QLabel(f"Primary: {primary_color}  Secondary: {secondary_color}")
                preview_text.setStyleSheet("color: #666; font-size: 10pt; font-family: monospace;")
                
                preview_layout.addWidget(primary_swatch)
                preview_layout.addWidget(secondary_swatch)
                preview_layout.addWidget(preview_text)
                preview_layout.addStretch()
                
                colors_layout.addWidget(preview_widget)
            
            # Global colors option
            self.use_global_colors_radio = QRadioButton("🌐 Use my global color settings instead")
            self.use_global_colors_radio.setChecked(False)
            
        else:
            # No character colors - inform user
            no_colors_info = QLabel("ℹ️ This character will use your global color settings")
            no_colors_info.setStyleSheet("""
                background-color: #E3F2FD; 
                color: #1976D2; 
                padding: 8px; 
                border-radius: 4px; 
                font-style: italic;
            """)
            colors_layout.addWidget(no_colors_info)
            
            # Create radio buttons but disable preserve option
            self.preserve_colors_radio = QRadioButton("Preserve original colors (none found)")
            self.preserve_colors_radio.setEnabled(False)
            self.preserve_colors_radio.setStyleSheet("color: #999;")
            
            self.use_global_colors_radio = QRadioButton("✅ Use my global color settings")
            self.use_global_colors_radio.setChecked(True)
            self.use_global_colors_radio.setStyleSheet("font-weight: bold; color: #28A745;")
        
        self.use_global_colors_radio.toggled.connect(self._update_color_choice)
        colors_layout.addWidget(self.use_global_colors_radio)
        
        if has_character_colors:
            colors_layout.addWidget(self.preserve_colors_radio)
        
        colors_group.setLayout(colors_layout)
        layout.addWidget(colors_group)
        
        # External APIs Section (if present)
        if self.original_config and self.original_config.get('external_apis'):
            apis_group = QGroupBox("🔗 External APIs")
            apis_layout = QVBoxLayout()
            
            api_count = len(self.original_config['external_apis'])
            apis_info = QLabel(f"This character includes {api_count} external API configuration(s)")
            apis_info.setStyleSheet("margin-bottom: 5px;")
            apis_layout.addWidget(apis_info)
            
            # Show first few APIs
            for i, api in enumerate(self.original_config['external_apis'][:3]):
                api_name = api.get('name', f'API {i+1}')
                api_enabled = api.get('enabled', False)
                status_icon = "✅" if api_enabled else "🔴"
                api_label = QLabel(f"   {status_icon} {api_name}")
                api_label.setStyleSheet("font-size: 10pt; color: #666;")
                apis_layout.addWidget(api_label)
            
            if api_count > 3:
                more_label = QLabel(f"   ... and {api_count - 3} more")
                more_label.setStyleSheet("font-size: 10pt; color: #999; font-style: italic;")
                apis_layout.addWidget(more_label)
            
            apis_note = QLabel("💡 All API configurations will be imported and can be managed after import")
            apis_note.setStyleSheet("color: #17A2B8; font-size: 9pt; font-style: italic; margin-top: 5px;")
            apis_note.setWordWrap(True)
            apis_layout.addWidget(apis_note)
            
            apis_group.setLayout(apis_layout)
            layout.addWidget(apis_group)
        
        # Warning and info section - Enhanced
        info_group = QGroupBox("ℹ️ Important Information")
        info_layout = QVBoxLayout()
        
        # Folder name warning
        name_warning = QLabel("⚠️ Make sure the folder name doesn't conflict with existing characters")
        name_warning.setStyleSheet("color: #DC3545; font-size: 10pt; margin-bottom: 5px;")
        name_warning.setWordWrap(True)
        info_layout.addWidget(name_warning)
        
        # Security note
        security_note = QLabel("🔒 API configurations are cleared during export for security - you can reassign them after import")
        security_note.setStyleSheet("color: #FD7E14; font-size: 10pt; margin-bottom: 5px;")
        security_note.setWordWrap(True)
        info_layout.addWidget(security_note)
        
        # Feature summary
        if feature_count > 0:
            feature_summary = QLabel(f"✨ This import will preserve all {feature_count} detected features")
            feature_summary.setStyleSheet("color: #28A745; font-size: 10pt; font-weight: bold;")
            info_layout.addWidget(feature_summary)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Buttons section - Enhanced
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #6C757D;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5A6268;
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        # Import button
        import_btn = QPushButton("📥 Import Character")
        import_btn.setStyleSheet("""
            QPushButton {
                background-color: #28A745;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1E7E34;
            }
        """)
        import_btn.clicked.connect(self._import)
        button_layout.addWidget(import_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize states
        self._update_color_choice()
        self._validate_folder_name()

    def _validate_folder_name(self):
        """Validate folder name in real-time"""
        folder_name = self.folder_name_edit.text().strip()
        
        if not folder_name:
            self.folder_validation_label.setText("❌ Folder name cannot be empty")
            self.folder_validation_label.setStyleSheet("color: #DC3545; font-size: 9pt; margin-left: 20px;")
            return False
        
        # Check for invalid characters
        invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
        if any(char in folder_name for char in invalid_chars):
            self.folder_validation_label.setText("❌ Contains invalid characters")
            self.folder_validation_label.setStyleSheet("color: #DC3545; font-size: 9pt; margin-left: 20px;")
            return False
        
        # Check length
        if len(folder_name) > 50:
            self.folder_validation_label.setText("⚠️ Very long folder name")
            self.folder_validation_label.setStyleSheet("color: #FD7E14; font-size: 9pt; margin-left: 20px;")
            return True
        
        # All good
        self.folder_validation_label.setText("✅ Folder name looks good")
        self.folder_validation_label.setStyleSheet("color: #28A745; font-size: 9pt; margin-left: 20px;")
        return True
    
    def _sync_if_enabled(self):
        """Sync folder name with display name if auto-sync is enabled"""
        if hasattr(self, 'sync_names_check') and self.sync_names_check.isChecked():
            display_name = self.display_name_edit.text()
            # Convert to safe folder name
            safe_name = re.sub(r'[<>:"/\\|?*\s]', '_', display_name.lower())
            self.folder_name_edit.setText(safe_name)

    def _toggle_sync(self, enabled):
        """Toggle auto-sync functionality"""
        if enabled:
            self._sync_if_enabled()

    def _update_color_choice(self):
        """Update color choice based on radio button selection"""
        if hasattr(self, 'preserve_colors_radio') and self.preserve_colors_radio.isChecked():
            self.color_choice = "preserve"
        else:
            self.color_choice = "global"
    
    def _import(self):
        """Handle import button click with enhanced validation"""
        self.folder_name = self.folder_name_edit.text().strip()
        self.display_name = self.display_name_edit.text().strip()
        
        # Validate inputs
        if not self.folder_name or not self.display_name:
            QMessageBox.warning(self, "Invalid Input", 
                            "Please enter both folder name and display name.")
            return
        
        # Validate folder name
        if not self._validate_folder_name():
            QMessageBox.warning(self, "Invalid Folder Name", 
                            "Please fix the folder name before importing.")
            return
        
        # Set color choice
        self._update_color_choice()
        
        # Show confirmation with summary
        feature_count = 0
        if self.original_config:
            if self.original_config.get('_export_info', {}).get('has_character_colors'):
                feature_count += 1
            if self.original_config.get('external_apis'):
                feature_count += len(self.original_config['external_apis'])
            if self.original_config.get('icon_settings'):
                feature_count += 1
            if self.original_config.get('background_settings'):
                feature_count += 1
            if self.original_config.get('interactions'):
                feature_count += 1
        
        confirm_msg = f"Ready to import '{self.display_name}'?\n\n"
        confirm_msg += f"📁 Folder: {self.folder_name}\n"
        confirm_msg += f"🎨 Colors: {'Preserve original' if self.color_choice == 'preserve' else 'Use global'}\n"
        if feature_count > 0:
            confirm_msg += f"✨ Features: {feature_count} will be imported\n"
        
        reply = QMessageBox.question(self, "Confirm Import", confirm_msg,
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.Yes)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.accept()

# ===== REPLACE CharacterColorDialog CLASS IN dialogs.py =====

class CharacterColorDialog(QDialog):
    """Dialog for per-character color customization - FIXED LIVE PREVIEW"""
    def __init__(self, parent, character: CharacterConfig):
        super().__init__(parent)
        self.character = character
        self.setWindowTitle(f"Character Colors - {character.display_name}")
        self.setFixedSize(450, 400)
        self.setModal(True)
        
        # Store original character colors for cancel functionality
        self.original_use_character_colors = getattr(character, 'use_character_colors', False)
        self.original_primary = getattr(character, 'character_primary_color', '')
        self.original_secondary = getattr(character, 'character_secondary_color', '')
        
        self._setup_ui()
        self._load_current_colors()
    
    def _setup_ui(self):
        """Create the character color interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info section
        info_label = QLabel("🎨 Character-specific colors override global app colors when enabled")
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 8px; background: #f0f0f0; border-radius: 3px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Enable character colors checkbox
        self.use_character_colors = QCheckBox("Use custom colors for this character")
        self.use_character_colors.setChecked(self.character.use_character_colors)
        self.use_character_colors.toggled.connect(self._toggle_character_colors)
        self.use_character_colors.toggled.connect(self._apply_live_preview)  # Add live preview trigger
        layout.addWidget(self.use_character_colors)
        
        # Color selection widgets
        self.color_options = QWidget()
        options_layout = QVBoxLayout()
        
        # Primary color picker
        primary_layout = QHBoxLayout()
        primary_layout.addWidget(QLabel("Primary Color:"))
        self.primary_label = QLabel()
        self.primary_label.setFixedSize(100, 30)
        self.primary_label.setStyleSheet(f"background-color: {app_colors.PRIMARY}; border: 1px solid black;")
        primary_layout.addWidget(self.primary_label)
        
        primary_btn = QPushButton("Change")
        primary_btn.clicked.connect(self._change_primary)
        primary_layout.addWidget(primary_btn)
        options_layout.addLayout(primary_layout)
        
        # Secondary color picker
        secondary_layout = QHBoxLayout()
        secondary_layout.addWidget(QLabel("Secondary Color:"))
        self.secondary_label = QLabel()
        self.secondary_label.setFixedSize(100, 30)
        self.secondary_label.setStyleSheet(f"background-color: {app_colors.SECONDARY}; border: 1px solid black;")
        secondary_layout.addWidget(self.secondary_label)
        
        secondary_btn = QPushButton("Change")
        secondary_btn.clicked.connect(self._change_secondary)
        secondary_layout.addWidget(secondary_btn)
        options_layout.addLayout(secondary_layout)
        
        # Live preview checkbox
        self.live_preview_check = QCheckBox("🔄 Live Preview (Updates character windows instantly)")
        self.live_preview_check.setChecked(True)  # Enable by default
        self.live_preview_check.setStyleSheet("font-weight: bold; color: #2196F3; padding: 5px;")
        options_layout.addWidget(self.live_preview_check)
        
        self.color_options.setLayout(options_layout)
        layout.addWidget(self.color_options)
        
        # Buttons
        button_layout = QHBoxLayout()
        apply_btn = QPushButton("✅ Apply & Save")
        apply_btn.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        apply_btn.clicked.connect(self._apply_colors)
        button_layout.addWidget(apply_btn)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.clicked.connect(self._cancel)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        self._toggle_character_colors()
    
    def _toggle_character_colors(self):
        """Enable/disable character color options"""
        enabled = self.use_character_colors.isChecked()
        self.color_options.setEnabled(enabled)
    
    def _change_primary(self):
        """Change primary color with live preview"""
        current = self.primary_label.styleSheet().split("background-color: ")[1].split(";")[0]
        color = QColorDialog.getColor(QColor(current), self, "Select Primary Color")
        if color.isValid():
            self.primary_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            if self.live_preview_check.isChecked():
                self._apply_live_preview()
    
    def _change_secondary(self):
        """Change secondary color with live preview"""
        current = self.secondary_label.styleSheet().split("background-color: ")[1].split(";")[0]
        color = QColorDialog.getColor(QColor(current), self, "Select Secondary Color")
        if color.isValid():
            self.secondary_label.setStyleSheet(f"background-color: {color.name()}; border: 1px solid black;")
            if self.live_preview_check.isChecked():
                self._apply_live_preview()
    
    def _apply_live_preview(self):
        """Apply live preview of character colors - COMPLETELY ISOLATED"""
        if not self.live_preview_check.isChecked():
            return
        
        try:
            if self.use_character_colors.isChecked():
                # Get colors from UI
                primary = self.primary_label.styleSheet().split("background-color: ")[1].split(";")[0]
                secondary = self.secondary_label.styleSheet().split("background-color: ")[1].split(";")[0]
                
                # Apply to character ONLY - NEVER touch global colors
                self.character.use_character_colors = True
                self.character.character_primary_color = primary
                self.character.character_secondary_color = secondary
                
                print(f"🎨 Character preview: PRIMARY={primary}, SECONDARY={secondary}")
            else:
                # Disable character colors temporarily
                self.character.use_character_colors = False
                print(f"🎨 Character preview: Using global colors")
            
            # Update windows with character-specific logic ONLY
            self._update_character_windows_isolated()
            
        except Exception as e:
            print(f"Error in character color live preview: {e}")

    def _update_character_windows_isolated(self):
        """Update character windows in complete isolation from global colors"""
        try:
            # Get main application window
            main_app = self.parent()
            while main_app and not hasattr(main_app, 'chat_windows'):
                main_app = main_app.parent()
            
            if not main_app:
                return
            
            # Update main window character reference
            if (hasattr(main_app, 'current_character') and 
                main_app.current_character and 
                main_app.current_character.name == self.character.name):
                
                # Update character reference
                main_app.current_character = self.character
                
                # Trigger ISOLATED color update (not global update)
                main_app._update_colors_for_character_only()
            
            # Update chat windows AND their minimize bars
            if hasattr(main_app, 'chat_windows'):
                for window_name, chat_window in main_app.chat_windows.items():
                    if (chat_window and 
                        hasattr(chat_window, 'character') and 
                        chat_window.character.name == self.character.name):
                        
                        # Update character reference
                        chat_window.character = self.character
                        
                        # Trigger isolated update for main chat window
                        chat_window.update_colors()
                        
                        # 🆕 NEW: Update minimize bar if it exists
                        if (hasattr(chat_window, 'minimize_bar') and 
                            chat_window.minimize_bar and 
                            not chat_window.minimize_bar.isHidden()):
                            
                            self._update_minimize_bar_colors(chat_window)
                    
        except Exception as e:
            print(f"Error updating character windows: {e}")





    def _update_minimize_bar_colors(self, chat_window):
        """Update minimize bar colors for live preview"""
        try:
            # Determine which colors to use
            primary_color = app_colors.PRIMARY
            secondary_color = app_colors.SECONDARY
            
            # Check if character has custom colors enabled
            if (hasattr(chat_window.character, 'use_character_colors') and 
                chat_window.character.use_character_colors):
                
                char_primary = getattr(chat_window.character, 'character_primary_color', '')
                char_secondary = getattr(chat_window.character, 'character_secondary_color', '')
                
                if char_primary and char_secondary:
                    primary_color = char_primary
                    secondary_color = char_secondary
            
            # Update minimize bar background
            chat_window.minimize_bar.setStyleSheet(f"background-color: {primary_color};")
            
            # Update all child widgets in the minimize bar
            for child in chat_window.minimize_bar.findChildren(QWidget):
                if isinstance(child, QLabel):
                    # Update title label
                    child.setStyleSheet(f"color: {secondary_color}; font-weight: bold; font-size: 9pt;")
                elif isinstance(child, QPushButton):
                    button_text = child.text()
                    if button_text == "⛶":  # Restore button
                        child.setStyleSheet(f"""
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
                        child.setStyleSheet(f"""
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
            
            print(f"🎨 Updated minimize bar colors: {primary_color}, {secondary_color}")
            
        except Exception as e:
            print(f"Error updating minimize bar colors: {e}")





    def _update_character_windows(self):
        """Update all windows that use this character - ENHANCED VERSION"""
        try:
            # Get main application window
            main_app = self.parent()
            while main_app and not hasattr(main_app, 'chat_windows'):
                main_app = main_app.parent()
            
            if not main_app:
                print("Could not find main application")
                return
            
            # UPDATE MAIN WINDOW CHARACTER REFERENCE AND TRIGGER UPDATE
            if (hasattr(main_app, 'current_character') and 
                main_app.current_character and 
                main_app.current_character.name == self.character.name):
                
                # IMPORTANT: Update the main window's character reference
                main_app.current_character = self.character
                
                if hasattr(main_app, 'update_colors'):
                    main_app.update_colors()
                    print(f"🎨 Updated main window for character: {self.character.name}")
            
            # Update chat windows for this character
            if hasattr(main_app, 'chat_windows'):
                for window_name, chat_window in main_app.chat_windows.items():
                    if (chat_window and 
                        hasattr(chat_window, 'character') and 
                        chat_window.character.name == self.character.name):
                        
                        # Update the chat window's character reference
                        chat_window.character = self.character
                        
                        # Trigger color update
                        if hasattr(chat_window, 'update_colors'):
                            chat_window.update_colors()
                            print(f"🎨 Updated chat window for character: {self.character.name}")
                    
        except Exception as e:
            print(f"Error updating character windows: {e}")

    
    def _apply_colors(self):
        """Apply and save character colors"""
        try:
            # Apply current settings to character
            self.character.use_character_colors = self.use_character_colors.isChecked()
            
            if self.character.use_character_colors:
                self.character.character_primary_color = self.primary_label.styleSheet().split("background-color: ")[1].split(";")[0]
                self.character.character_secondary_color = self.secondary_label.styleSheet().split("background-color: ")[1].split(";")[0]
            else:
                self.character.character_primary_color = ""
                self.character.character_secondary_color = ""
            
            # Save to file
            self._save_character_config()
            
            # Update UI
            self._update_character_windows()
            
            QMessageBox.information(self, "Success", "Character colors saved and applied!")
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save character colors: {str(e)}")
    
    def _cancel(self):
        """Cancel changes and restore original colors if live preview was used"""
        if self.live_preview_check.isChecked():
            # Restore original character colors
            if (self.character.use_character_colors != self.original_use_character_colors or
                getattr(self.character, 'character_primary_color', '') != self.original_primary or
                getattr(self.character, 'character_secondary_color', '') != self.original_secondary):
                
                reply = QMessageBox.question(self, "Revert Changes", 
                                           "Revert character color changes made during live preview?",
                                           QMessageBox.Yes | QMessageBox.No)
                
                if reply == QMessageBox.Yes:
                    # Restore original values
                    self.character.use_character_colors = self.original_use_character_colors
                    self.character.character_primary_color = self.original_primary
                    self.character.character_secondary_color = self.original_secondary
                    
                    # Update windows with restored colors
                    self._update_character_windows()
                    print(f"🎨 Reverted character colors for: {self.character.name}")
        
        self.reject()
    
    def _save_character_config(self):
        """Save character configuration to file"""
        app_data_dir = get_app_data_dir()
        config_file = app_data_dir / "characters" / self.character.folder_name / "config.json"
        
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.character), f, indent=2)
    
    def _load_current_colors(self):
        """Load current character colors"""
        if self.character.use_character_colors:
            primary = self.character.character_primary_color or app_colors.PRIMARY
            secondary = self.character.character_secondary_color or app_colors.SECONDARY
        else:
            primary = app_colors.PRIMARY
            secondary = app_colors.SECONDARY
        
        self.primary_label.setStyleSheet(f"background-color: {primary}; border: 1px solid black;")
        self.secondary_label.setStyleSheet(f"background-color: {secondary}; border: 1px solid black;")

class UserProfileEditDialog(QDialog):
    """Dialog for editing user profile with folder name and user name"""
    def __init__(self, parent, profile: Optional[UserProfile]):
        super().__init__(parent)
        
        self.profile = profile
        self.result = None
        
        self.setWindowTitle("Edit Profile" if profile else "New Profile")
        self.setFixedSize(500, 450)
        self.setModal(True)
        
        self._setup_ui()
        
    def _setup_ui(self):
        """Setup UI with folder name and user name fields"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Info section
        info_label = QLabel("📁 Folder Name: Internal identifier for file organization\n👤 User Name: Replaces {{user}} in chat conversations")
        info_label.setStyleSheet(f"background-color: #070000; padding: 8px; border: 1px solid #B0C4DE; border-radius: 3px; font-size: 9pt;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Form
        form_layout = QFormLayout()
        
        # Folder Name (identifier)
        self.name_edit = QLineEdit(self.profile.name if self.profile else "")
        self.name_edit.setPlaceholderText("user_folder_name (no spaces)")
        self.name_edit.textChanged.connect(self._validate_folder_name)
        form_layout.addRow("📁 Folder Name:", self.name_edit)
        
        # User Name (for {{user}} replacement)
        self.user_name_edit = QLineEdit(self.profile.user_name if self.profile else "")
        self.user_name_edit.setPlaceholderText("User Name (for {{user}})")
        form_layout.addRow("👤 User Name:", self.user_name_edit)
        
        # Auto-sync option
        self.sync_check = QCheckBox("Auto-sync folder name to user name")
        self.sync_check.setChecked(not self.profile)  # Default checked for new profiles
        self.sync_check.toggled.connect(self._toggle_sync)
        form_layout.addRow("", self.sync_check)
        
        # Connect for auto-sync
        self.user_name_edit.textChanged.connect(self._sync_if_enabled)
        
        # Personality
        self.personality_edit = QTextEdit()
        if self.profile:
            self.personality_edit.setPlainText(self.profile.personality)
        else:
            self.personality_edit.setPlainText("I am a friendly and helpful person who enjoys conversations.")
        form_layout.addRow("Personality:", self.personality_edit)
        
        layout.addLayout(form_layout)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        save_btn = QPushButton("💾 Save")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
    
    def _validate_folder_name(self):
        """Validate and clean folder name"""
        text = self.name_edit.text()
        clean_text = re.sub(r'[<>:"/\\|?*\s]', '_', text.lower())
        if text != clean_text:
            self.name_edit.blockSignals(True)
            self.name_edit.setText(clean_text)
            self.name_edit.blockSignals(False)
    
    def _toggle_sync(self):
        """Toggle name synchronization"""
        if self.sync_check.isChecked():
            self._sync_if_enabled()
    
    def _sync_if_enabled(self):
        """Sync folder name with user name if enabled"""
        if self.sync_check.isChecked():
            user_name = self.user_name_edit.text()
            folder_name = re.sub(r'[<>:"/\\|?*\s]', '_', user_name.lower())
            self.name_edit.blockSignals(True)
            self.name_edit.setText(folder_name)
            self.name_edit.blockSignals(False)
    
    def _save(self):
        """Save profile"""
        name = self.name_edit.text().strip()
        user_name = self.user_name_edit.text().strip()
        personality = self.personality_edit.toPlainText().strip()
        
        if not name or not user_name or not personality:
            QMessageBox.critical(self, "Error", "Folder name, user name, and personality are required.")
            return
        
        self.result = UserProfile(
            name=name, 
            user_name=user_name, 
            personality=personality
        )
        self.accept()

@dataclass
class CheckInSettings:
    """Settings for proactive character check-ins"""
    enabled: bool = False
    interval_minutes: int = 180  # Default 3 hours
    max_idle_hours: int = 24    # Stop checking after 24 hours of inactivity
    personalized_responses: bool = True  # Use message history for context
    quiet_hours_start: Optional[str] = "22:00"  # Don't check during quiet hours
    quiet_hours_end: Optional[str] = "08:00"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'enabled': self.enabled,
            'interval_minutes': self.interval_minutes,
            'max_idle_hours': self.max_idle_hours,
            'personalized_responses': self.personalized_responses,
            'quiet_hours_start': self.quiet_hours_start,
            'quiet_hours_end': self.quiet_hours_end
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CheckInSettings':
        return cls(**data)

class CheckInSettingsDialog(QDialog):
    """Dialog for configuring proactive check-in settings"""
    
    def __init__(self, settings: CheckInSettings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Proactive Check-in Settings")
        self.setModal(True)
        self.resize(400, 300)
        
        self._setup_ui()
        self._load_current_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Enable/disable check-ins
        self.enabled_check = QCheckBox("Enable proactive check-ins")
        layout.addWidget(self.enabled_check)
        
        # Settings group
        settings_group = QGroupBox("Check-in Settings")
        form_layout = QFormLayout(settings_group)
        
        # Interval
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 1440)  # 1 minute to 24 hours
        self.interval_spin.setSuffix(" minutes")
        form_layout.addRow("Check interval:", self.interval_spin)
        
        # Max idle time
        self.max_idle_spin = QSpinBox()
        self.max_idle_spin.setRange(1, 168)  # 1 hour to 1 week
        self.max_idle_spin.setSuffix(" hours")
        form_layout.addRow("Stop checking after:", self.max_idle_spin)
        
        # Personalized responses
        self.personalized_check = QCheckBox("Use conversation history for personalized check-ins")
        form_layout.addRow("", self.personalized_check)
        
        # Quiet hours
        quiet_layout = QHBoxLayout()
        self.quiet_start_edit = QTimeEdit()
        self.quiet_start_edit.setDisplayFormat("HH:mm")
        self.quiet_end_edit = QTimeEdit()
        self.quiet_end_edit.setDisplayFormat("HH:mm")
        
        quiet_layout.addWidget(QLabel("From:"))
        quiet_layout.addWidget(self.quiet_start_edit)
        quiet_layout.addWidget(QLabel("To:"))
        quiet_layout.addWidget(self.quiet_end_edit)
        
        form_layout.addRow("Quiet hours:", quiet_layout)
        
        layout.addWidget(settings_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_current_settings(self):
        """Load current settings into UI"""
        self.enabled_check.setChecked(self.settings.enabled)
        self.interval_spin.setValue(self.settings.interval_minutes)
        self.max_idle_spin.setValue(self.settings.max_idle_hours)
        self.personalized_check.setChecked(self.settings.personalized_responses)
        
        if self.settings.quiet_hours_start:
            time = QTime.fromString(self.settings.quiet_hours_start, "HH:mm")
            self.quiet_start_edit.setTime(time)
        
        if self.settings.quiet_hours_end:
            time = QTime.fromString(self.settings.quiet_hours_end, "HH:mm")
            self.quiet_end_edit.setTime(time)
    
    def get_settings(self) -> CheckInSettings:
        """Get settings from UI"""
        return CheckInSettings(
            enabled=self.enabled_check.isChecked(),
            interval_minutes=self.interval_spin.value(),
            max_idle_hours=self.max_idle_spin.value(),
            personalized_responses=self.personalized_check.isChecked(),
            quiet_hours_start=self.quiet_start_edit.time().toString("HH:mm"),
            quiet_hours_end=self.quiet_end_edit.time().toString("HH:mm")
        )