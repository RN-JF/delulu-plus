"""UI Widgets"""
from ..common_imports import *
from ..models.character import CharacterConfig, Interaction
from ..models.chat_models import ChatMessage
from ..models.ui_models import app_colors
from ..utils.helpers import hex_to_rgba, replace_name_placeholders, get_darker_secondary_with_transparency
from PySide6.QtGui import QGuiApplication
from PySide6.QtCore import QTimer

class ChatBubble(QWidget):
    """Chat bubble widget - Fixed width and text alignment"""
    
    edit_requested = Signal(object)
    retry_requested = Signal(object)
    delete_requested = Signal(object)
    navigate_sibling = Signal(object, int)
    
    def __init__(self, message_obj: ChatMessage, config: CharacterConfig, 
                user_icon=None, character_icon=None, has_siblings=False, 
                sibling_position=None, indent_level=0, 
                character_name=None, user_name=None, 
                primary_color=None, secondary_color=None):  # 🆕 ADD THESE COLOR PARAMETERS
        super().__init__()
        self.message_obj = message_obj
        self.config = config
        self.bubble_label = None
        # 🆕 STORE THE PASSED COLORS
        self.primary_color = primary_color or app_colors.PRIMARY
        self.secondary_color = secondary_color or app_colors.SECONDARY
    
        self.is_user = message_obj.role == "user"
        self.has_siblings = has_siblings
        self.sibling_position = sibling_position
        self.indent_level = min(indent_level, 3)  # Max 3 levels of indentation
        
        # Store the names directly
        self.character_name = character_name
        self.user_name = user_name
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: transparent;")
        
        # Set fixed width to prevent expansion
        self.setMaximumWidth(340)
        self.setMinimumWidth(340)
        
        # Create main container
        self._create_bubble_layout(user_icon, character_icon)

    def _apply_chat_icon(self, icon_label: QLabel, icon_source, letter_fallback: str, fallback_color: str, size: int = 42):
        """Set a crisp circular icon and refresh after show to fix first-time DPR issues."""
        icon_label.setFixedSize(size, size)
        icon_label.setScaledContents(False)

        if icon_source:
            #  Prefer the icon_label screen DPR (more accurate than primaryScreen)
            screen = icon_label.screen() or self.screen() or QGuiApplication.primaryScreen()
            dpr = screen.devicePixelRatio() if screen else 1.0

            pm = self._create_circular_icon(icon_source, size, "#E0E0E0", 0, dpr=dpr)
            if pm:
                icon_label.setPixmap(pm)

                #  Re-apply after the widget is actually shown (DPR becomes stable)
                QTimer.singleShot(30,  lambda: self._refresh_icon_label(icon_label, icon_source, size))
                QTimer.singleShot(200, lambda: self._refresh_icon_label(icon_label, icon_source, size))


                return

        icon_label.setPixmap(self._create_default_circular_icon(letter_fallback, size, fallback_color))

    def _refresh_icon_label(self, icon_label: QLabel, icon_source, size: int):
        screen = icon_label.screen() or self.screen()
        dpr = screen.devicePixelRatio() if screen else 1.0
        pm = self._create_circular_icon(icon_source, size, "#E0E0E0", 0, dpr=dpr)
        if pm:
            icon_label.setPixmap(pm)


    def _format_text(self, text: str) -> str:
        """Convert markdown-like syntax to rich text formatting with name replacement"""
        
        # Use the names passed to the constructor, with fallbacks
        character_name = self.character_name or "Assistant"
        user_name = self.user_name or "User"
        
        # Replace name placeholders FIRST
        text = replace_name_placeholders(text, character_name, user_name)

        # Colors from config
        emphasis_color = getattr(self.config, "emphasis_color", "#0D47A1")
        quote_color = getattr(self.config, "quote_color", "#666666")
        strikethrough_color = getattr(self.config, "strikethrough_color", "#757575")
        code_bg_color = getattr(self.config, "code_bg_color", "rgba(0,0,0,0.1)")
        code_text_color = getattr(self.config, "code_text_color", "#D32F2F")
        link_color = getattr(self.config, "link_color", "#1976D2")

        # 1. Escape HTML characters first to prevent conflicts
        text = html.escape(text)

        # 2. Headers (convert to bold with color and larger size)
        text = re.sub(r'^#\s+(.+)$', lambda m: (
            f'<div style="font-size: 14px; font-weight: bold; color: {emphasis_color}; margin: 8px 0 4px 0;">{m.group(1)}</div>'
        ), text, flags=re.MULTILINE)

        # 3. Block quotes (enhanced styling with left border)
        def replace_blockquote(m):
            return f'<div style="border-left: 4px solid {quote_color}; padding-left: 12px; margin: 8px 0; color: {quote_color}; font-style: italic; background-color: rgba(128,128,128,0.1);">{m.group(1)}</div>'

        text = re.sub(r'^&gt;\s+(.+)$', replace_blockquote, text, flags=re.MULTILINE)

        # 4. Code blocks (triple backticks)
        def replace_code_block(m):
            return f'<div style="background-color: {code_bg_color}; color: {code_text_color}; padding: 8px; margin: 4px 0; border-radius: 4px; font-family: monospace; white-space: pre-wrap; font-size: 11px;">{m.group(1)}</div>'

        text = re.sub(r'```(.*?)```', replace_code_block, text, flags=re.DOTALL)

        # 5. Inline code (single backticks)
        def replace_inline_code(m):
            return f'<code style="background-color: {code_bg_color}; color: {code_text_color}; padding: 2px 4px; border-radius: 3px; font-family: monospace; font-size: 11px;">{m.group(1)}</code>'

        text = re.sub(r'`([^`]+?)`', replace_inline_code, text)

        # 6. REORDERED: Process bold and italic BEFORE quotes for better nesting
        # Bold (allows nested content)
        text = re.sub(r'\*\*((?:(?!\*\*).)+?)\*\*', lambda m: (
            f'<b style="color: {emphasis_color};">{m.group(1)}</b>'
        ), text)

        # Italic (allows nested content, avoids bold conflicts)
        text = re.sub(r'(?<!\*)\*((?:(?!\*).)+?)\*(?!\*)', lambda m: (
            f'<i style="color: {emphasis_color};">{m.group(1)}</i>'
        ), text)

        # 7. Quote handling - work with HTML escaped quotes (AFTER bold/italic)
        def replace_quotes(m):
            return f'<span style="color: {quote_color};">&quot;{m.group(1)}&quot;</span>'

        text = re.sub(r'&quot;((?:(?!&quot;).)*?)&quot;', replace_quotes, text)

        # 8. Strikethrough
        text = re.sub(r'~~([^~]+?)~~', lambda m: (
            f'<s style="color: {strikethrough_color};">{m.group(1)}</s>'
        ), text)

        def process_link(match):
            url = match.group(1)
            # Add protocol if missing
            if not url.startswith(('http://', 'https://')):
                href = f'http://{url}'
            else:
                href = url
            return f'<a href="{href}" style="color: {link_color}; text-decoration: underline;">{url}</a>'

        # Single comprehensive regex for all link types
        text = re.sub(r'\b((?:https?://|www\.)[^\s"\'<>\[\]]+|[a-zA-Z0-9-]+\.(?:com|org|net|edu|gov|io|co|ai|me|info)(?:/[^\s"\'<>\[\]]*)?)\b', 
                    process_link, text)

        # 9. Line breaks
        text = text.replace('\n', '<br>')

        # 10. Wrap in center div
        return f'<div style="text-align: center;">{text}</div>'


    def _create_bubble_layout(self, user_icon, character_icon):
        """Create the complete bubble layout - FIXED to prevent shifting"""
        # Main vertical layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 3, 0, 3)
        main_layout.setSpacing(4)
        self.setLayout(main_layout)
        
        # Bubble container with FIXED positioning
        bubble_container = QWidget()
        bubble_container.setMaximumWidth(340)
        bubble_container.setMinimumWidth(340)  # Ensure consistent width
        
        bubble_layout = QHBoxLayout(bubble_container)
        bubble_layout.setContentsMargins(8, 0, 8, 0)
        bubble_layout.setSpacing(10)
        
        # REMOVED: indent_pixels calculation completely - no more shifting!
        # The indent_level is still calculated for tree features but not used for positioning
        
        if self.is_user:
            self._create_user_bubble(bubble_layout, user_icon, 0)  # Always 0 indent
        else:
            self._create_character_bubble(bubble_layout, character_icon, 0)  # Always 0 indent
        
        main_layout.addWidget(bubble_container)
        
        # Action buttons container
        self._create_action_buttons(main_layout)


    def _create_default_circular_icon(self, text, size=32, bg_color="#4CAF50", text_color="#FFFFFF"):
        """Create a default circular icon with text"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        
        # Draw circle background
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        
        # Draw text
        painter.setPen(QColor(text_color))
        font = painter.font()
        font.setPointSize(size // 3)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(0, 0, size, size, Qt.AlignCenter, text)
        
        painter.end()
        return pixmap 
        
    def _create_circular_icon(self, icon_path_or_pixmap, size=42, border_color="#FFFFFF", border_width=2, dpr=None):
        """Create high-quality circular icon that stays sharp on 4K/HiDPI"""
        try:
            # Use the widget's screen DPR if possible (more correct than primaryScreen)
            if dpr is None:
                #  best effort: use this widget's screen if available, else default 1.0 (no wrong monitor)
                screen = self.screen()
                dpr = screen.devicePixelRatio() if screen else 1.0

            # Render at physical pixels
            physical_size = max(1, int(round(size * float(dpr))))

            # Load image using Pillow
            if isinstance(icon_path_or_pixmap, str):
                if not os.path.exists(icon_path_or_pixmap):
                    raise FileNotFoundError(f"File not found: {icon_path_or_pixmap}")
                img = Image.open(icon_path_or_pixmap).convert("RGBA")
            elif isinstance(icon_path_or_pixmap, QPixmap):
                buffer = QBuffer()
                buffer.open(QIODevice.ReadWrite)
                icon_path_or_pixmap.save(buffer, "PNG")
                img = Image.open(io.BytesIO(buffer.data())).convert("RGBA")
            else:
                raise ValueError("Unsupported icon format")

            # Resize to physical size (sharp on HiDPI)
            img = img.resize((physical_size, physical_size), Image.LANCZOS)

            # Circle mask
            aa = 4  # anti-alias factor (2–8). 4 is a good balance.
            mask_big = Image.new("L", (physical_size * aa, physical_size * aa), 0)
            draw_big = ImageDraw.Draw(mask_big)
            draw_big.ellipse((0, 0, physical_size * aa - 1, physical_size * aa - 1), fill=255)

            mask = mask_big.resize((physical_size, physical_size), Image.LANCZOS)
            img.putalpha(mask)

            # Convert to QPixmap
            qimage = ImageQt.ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)

            # Tell Qt DPR
            pixmap.setDevicePixelRatio(float(dpr))

            return pixmap

        except Exception as e:
            print(f"[ICON ERROR] {e}")
            return self._create_default_circular_icon("?", size, "#CCCCCC")



    def _calculate_bubble_width(self, text: str, available_width: int) -> int:
        """Calculate bubble width with caching to prevent size changes on edit"""

        # Check if we already have a cached width
        if hasattr(self.message_obj, 'bubble_width') and self.message_obj.bubble_width is not None:
            return min(self.message_obj.bubble_width, available_width)
        
        # Calculate width based on text length (one time only)
        text_length = len(text.strip())
        
        if text_length <= 5:
            width = 60
        elif text_length <= 15:
            width = 120
        elif text_length <= 30:
            width = 160
        elif text_length <= 60:
            width = 200
        else:
            width = 240
        
        # Cache and return
        final_width = min(width, available_width)
        if hasattr(self.message_obj, 'bubble_width'):
            self.message_obj.bubble_width = final_width
        
        return final_width



    def _calculate_streaming_width(self, text: str, available_width: int) -> int:
        """Calculate bubble width for streaming text - uses same logic as original but no caching"""
        text_length = len(text.strip())
        
        if text_length <= 5:
            width = 60
        elif text_length <= 15:
            width = 120
        elif text_length <= 30:
            width = 160
        elif text_length <= 60:
            width = 200
        else:
            width = 240
        
        return min(width, available_width)


    def _create_user_bubble(self, layout, user_icon, indent_pixels):
        """Create user message bubble with circular icon - FIXED positioning"""
        # Available width for bubble (no indent deduction here)
        available_width = 280 - (28 if self.has_siblings else 0)
        
        # Left stretch to push content right (ALWAYS add this first)
        layout.addStretch()
        
        # Navigation arrows (if needed)
        if self.has_siblings:
            nav_widget = self._create_navigation_arrows()
            layout.addWidget(nav_widget)
        
        # Calculate bubble width
        bubble_width = self._calculate_bubble_width(self.message_obj.content, available_width)
        
        # Create the text label
        self.bubble_label = QLabel()
        self.bubble_label.setTextFormat(Qt.TextFormat.RichText)
        formatted_content = self._format_text(self.message_obj.content)
        self.bubble_label.setText(formatted_content)
        self.bubble_label.setWordWrap(True)
        
        # Enable link clicking AND text selection
        self.bubble_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.bubble_label.setOpenExternalLinks(True)
        
        # Center the text block within bubble
        self.bubble_label.setAlignment(Qt.AlignCenter)
        
        # Set width and allow height to expand
        self.bubble_label.setFixedWidth(bubble_width)
        self.bubble_label.setMinimumHeight(32)
        self.bubble_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Styling with transparency support
        opacity_value = 1.0 if self.message_obj.is_active else 0.6
        
        # Use getattr for safe attribute access
        user_bubble_transparency = getattr(self.config, 'user_bubble_transparency', 0)
        if user_bubble_transparency > 0:
            bubble_bg_color = hex_to_rgba(self.config.user_bubble_color, user_bubble_transparency)
        else:
            bubble_bg_color = self.config.user_bubble_color
        
        self.bubble_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bubble_bg_color};
                color: {self.config.user_text_color};
                padding: 10px;
                border-radius: 12px;
                font-family: {self.config.text_font};
                font-size: {self.config.text_size}px;
                opacity: {opacity_value};
            }}
        """)
        
        layout.addWidget(self.bubble_label)
        
        # User icon with circular shape
        # User icon with circular shape
        icon_widget = QWidget()
        icon_widget.setFixedSize(42, 42)
        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        self._apply_chat_icon(icon_label, user_icon, "U", app_colors.SECONDARY, 42)

        icon_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        layout.addWidget(icon_widget)
        
        # NO indentation spacing at the end for user messages


    def _create_character_bubble(self, layout, character_icon, indent_pixels):
        """Create character message bubble with circular shape - FIXED positioning"""
        # Character icon with circular shape (ALWAYS first for character)
        # Character icon with circular shape (ALWAYS first for character)
        icon_widget = QWidget()
        icon_widget.setFixedSize(42, 42)
        icon_layout = QVBoxLayout(icon_widget)
        icon_layout.setContentsMargins(0, 0, 0, 0)

        icon_label = QLabel()
        self._apply_chat_icon(icon_label, character_icon, "C", app_colors.PRIMARY, 42)

        icon_layout.addWidget(icon_label, 0, Qt.AlignCenter)
        layout.addWidget(icon_widget)

        # Available width for bubble (no indent deduction here)
        available_width = 280 - (20 if self.has_siblings else 0)
        
        # Calculate bubble width
        bubble_width = self._calculate_bubble_width(self.message_obj.content, available_width)
        
        # Create the text label with rich text support
        self.bubble_label = QLabel()
        self.bubble_label.setTextFormat(Qt.TextFormat.RichText)
        formatted_content = self._format_text(self.message_obj.content)
        self.bubble_label.setText(formatted_content)
        self.bubble_label.setWordWrap(True)
        
        # Enable link clicking AND text selection
        self.bubble_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        self.bubble_label.setOpenExternalLinks(True)

        # Center the text block within bubble
        self.bubble_label.setAlignment(Qt.AlignCenter)
        
        # Set width and allow height to expand
        self.bubble_label.setFixedWidth(bubble_width)
        self.bubble_label.setMinimumHeight(32)
        self.bubble_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        
        # Styling with transparency support
        opacity_value = 1.0 if self.message_obj.is_active else 0.6
        
        # Use getattr for safe attribute access
        bubble_transparency = getattr(self.config, 'bubble_transparency', 0)
        if bubble_transparency > 0:
            bubble_bg_color = hex_to_rgba(self.config.bubble_color, bubble_transparency)
        else:
            bubble_bg_color = self.config.bubble_color
        
        self.bubble_label.setStyleSheet(f"""
            QLabel {{
                background-color: {bubble_bg_color};
                color: {self.config.text_color};
                padding: 10px;
                border-radius: 12px;
                font-family: {self.config.text_font};
                font-size: {self.config.text_size}px;
                opacity: {opacity_value};
            }}
        """)
        
        layout.addWidget(self.bubble_label)
        
        # Navigation arrows (if needed)
        if self.has_siblings:
            nav_widget = self._create_navigation_arrows()
            layout.addWidget(nav_widget)
        
        # Right stretch to keep content left-aligned (ALWAYS add this last)
        layout.addStretch()


    def _update_navigation_controls_silent(self):
        """Update navigation controls when sibling information changes"""
        try:
            # Find existing navigation widget
            nav_widget = None
            for i in range(self.layout().count()):
                item = self.layout().itemAt(i)
                if item and item.widget():
                    widget = item.widget()
                    # Check if this is a navigation widget (has the specific size we set)
                    if (hasattr(widget, 'size') and 
                        widget.size().width() == 26 and  # ← Change from 18 to 26
                        widget.size().height() == 60):
                        nav_widget = widget
                        break
            
            # Remove old navigation widget if it exists
            if nav_widget:
                nav_widget.setParent(None)
                nav_widget.deleteLater()
            
            # If we should have siblings, create new navigation widget
            if self.has_siblings:
                new_nav_widget = self._create_navigation_arrows()
                
                # Insert navigation widget in the correct position
                # (after the stretch but before the bubble content)
                if hasattr(self, 'message_obj') and self.message_obj.role == 'user':
                    # For user messages, add before the bubble (left side)
                    self.layout().insertWidget(1, new_nav_widget)
                else:
                    # For assistant messages, add after the bubble (right side)  
                    self.layout().insertWidget(self.layout().count() - 1, new_nav_widget)
                
            # Force layout update
            self.layout().update()
            
        except Exception as e:
            print(f"Error updating navigation controls: {e}")


    def _get_effective_colors(self):
        """Get the effective colors - USE STORED COLORS"""
        primary = getattr(self, 'primary_color', app_colors.PRIMARY)
        secondary = getattr(self, 'secondary_color', app_colors.SECONDARY)
        
        return primary, secondary


    # 4. IN widgets.py - MODIFY _create_navigation_arrows to use stored colors:

    def _create_navigation_arrows(self):
        """Create navigation arrows widget - USING STORED COLORS"""
        nav_widget = QWidget()
        nav_widget.setFixedSize(26, 60)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(1, 3, 1, 3)
        nav_layout.setSpacing(2)
        
        # 🆕 USE THE STORED COLORS
        primary_color = getattr(self, 'primary_color', app_colors.PRIMARY)
        secondary_color = getattr(self, 'secondary_color', app_colors.SECONDARY)
        
        # Previous button
        prev_btn = QPushButton("←")
        prev_btn.setFixedSize(16, 14)
        prev_btn.setEnabled(self.sibling_position[0] > 0 if self.sibling_position else False)
        prev_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary_color};
                border: none;
                border-radius: 3px;
                font-size: 8pt;
                font-weight: bold;
                color: {secondary_color};
            }}
            QPushButton:hover:enabled {{
                background-color: {secondary_color};
                color: {primary_color};
            }}
            QPushButton:disabled {{
                color: #CCCCCC;
                background-color: {primary_color};
            }}
        """)
        prev_btn.clicked.connect(lambda: self.navigate_sibling.emit(self.message_obj, -1))
        nav_layout.addWidget(prev_btn)
        
        # Position indicator
        if self.sibling_position:
            pos_label = QLabel(f"{self.sibling_position[0]+1}/{self.sibling_position[1]}")
            pos_label.setAlignment(Qt.AlignCenter)
            pos_label.setStyleSheet("""
                QLabel {
                    font-size: 7pt; 
                    color: #888888; 
                    font-weight: bold;
                    background-color: transparent;
                }
            """)
            nav_layout.addWidget(pos_label)
        
        # Next button
        next_btn = QPushButton("→")
        next_btn.setFixedSize(16, 14)
        next_btn.setEnabled(self.sibling_position[0] < self.sibling_position[1] - 1 if self.sibling_position else False)
        next_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {primary_color};
                border: none;
                border-radius: 3px;
                font-size: 8pt;
                font-weight: bold;
                color: {secondary_color};
            }}
            QPushButton:hover:enabled {{
                background-color: {secondary_color};
                color: {primary_color};
            }}
            QPushButton:disabled {{
                color: #CCCCCC;
                background-color: {primary_color};
            }}
        """)
        next_btn.clicked.connect(lambda: self.navigate_sibling.emit(self.message_obj, 1))
        nav_layout.addWidget(next_btn)
        
        nav_layout.addStretch()
        
        return nav_widget
    

    def _create_action_buttons(self, main_layout):
        """Create action buttons below the bubble - USING STORED COLORS"""
        if not self.message_obj.is_active:
            return
        
        button_container = QWidget()
        button_container.setMaximumWidth(340)
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(8, 2, 8, 2)
        button_layout.setSpacing(6)
        
        # 🆕 USE THE STORED COLORS INSTEAD OF LOOKING THEM UP
        primary = getattr(self, 'primary_color', app_colors.PRIMARY)
        secondary = getattr(self, 'secondary_color', app_colors.SECONDARY)
        
        if self.is_user:
            # User buttons on the right
            button_layout.addStretch()
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(45, 22)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {secondary};
                    color: {primary};
                    border: none;
                    border-radius: 5px;
                    font-size: 8pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {primary};
                    color: {secondary};
                }}
                QPushButton:pressed {{
                    background-color: {primary};
                }}
            """)
            edit_btn.clicked.connect(self._on_edit_clicked)
            button_layout.addWidget(edit_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(40, 22)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {secondary};
                    color: {primary};
                    border: none;
                    border-radius: 5px;
                    font-size: 8pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {primary};
                    color: {secondary};
                }}
                QPushButton:pressed {{
                    background-color: {primary};
                }}
            """)
            delete_btn.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(delete_btn)
            
            # Spacer for icon alignment
            spacer = QWidget()
            spacer.setFixedWidth(38)
            button_layout.addWidget(spacer)
            
        else:
            # Character buttons on the left
            spacer = QWidget()
            spacer.setFixedWidth(38)
            button_layout.addWidget(spacer)
            
            edit_btn = QPushButton("Edit")
            edit_btn.setFixedSize(45, 22)
            edit_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {secondary};
                    color: {primary};
                    border: none;
                    border-radius: 5px;
                    font-size: 8pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {primary};
                    color: {secondary};
                }}
                QPushButton:pressed {{
                    background-color: {primary};
                }}
            """)
            edit_btn.clicked.connect(self._on_edit_clicked)
            button_layout.addWidget(edit_btn)
            
            # RETRY BUTTON
            retry_btn = QPushButton("Retry")
            retry_btn.setFixedSize(45, 22)
            
            has_active_descendants = self._has_active_descendants()
            if not has_active_descendants:
                retry_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {secondary};
                        color: {primary};
                        border: none;
                        border-radius: 5px;
                        font-size: 8pt;
                        font-weight: bold;
                    }}
                    QPushButton:hover {{
                        background-color: {primary};
                        color: {secondary};
                    }}
                    QPushButton:pressed {{
                        background-color: {primary};
                    }}
                """)
            else:
                retry_btn.setEnabled(False)
                retry_btn.setStyleSheet(f"""
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
            
            retry_btn.clicked.connect(self._on_retry_clicked)
            button_layout.addWidget(retry_btn)
            
            delete_btn = QPushButton("Del")
            delete_btn.setFixedSize(40, 22)
            delete_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {secondary};
                    color: {primary};
                    border: none;
                    border-radius: 5px;
                    font-size: 8pt;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {primary};
                    color: {secondary};
                }}
                QPushButton:pressed {{
                    background-color: {primary};
                }}
            """)
            delete_btn.clicked.connect(self._on_delete_clicked)
            button_layout.addWidget(delete_btn)
            
            button_layout.addStretch()
        
        main_layout.addWidget(button_container)

    def _update_button_colors(self, primary, secondary):
        """Update button colors without recreating the widget"""
        try:
            # Find all buttons in this bubble
            buttons = self.findChildren(QPushButton)
            for btn in buttons:
                if not btn:
                    continue
                    
                button_text = btn.text()
                
                # Update action buttons (Edit, Retry, Del)
                if button_text in ["Edit", "Retry", "Del"]:
                    if btn.isEnabled():
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {secondary};
                                color: {primary};
                                border: none;
                                border-radius: 5px;
                                font-size: 8pt;
                                font-weight: bold;
                            }}
                            QPushButton:hover {{
                                background-color: {primary};
                                color: {secondary};
                            }}
                            QPushButton:pressed {{
                                background-color: {primary};
                            }}
                        """)
                    # Don't update disabled retry buttons (they have special styling)
                
                # Update navigation arrows
                elif button_text in ["←", "→"]:
                    if btn.isEnabled():
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                background-color: {primary};
                                border: none;
                                border-radius: 3px;
                                font-size: 8pt;
                                font-weight: bold;
                                color: {secondary};
                            }}
                            QPushButton:hover:enabled {{
                                background-color: {secondary};
                                color: {primary};
                            }}
                        """)
                    else:
                        btn.setStyleSheet(f"""
                            QPushButton {{
                                color: #CCCCCC;
                                background-color: {primary};
                                border: none;
                                border-radius: 3px;
                                font-size: 8pt;
                                font-weight: bold;
                            }}
                        """)
        except Exception as e:
            print(f"Error updating button colors: {e}")



    def _on_edit_clicked(self):
        """Handle edit request"""
        # Check if AI is writing
        if hasattr(self.parent(), 'is_ai_writing') and self.parent().is_ai_writing:
            print("❌ Edit blocked - AI is writing")
            return
        
        self.edit_requested.emit(self.message_obj)
    
    def _on_retry_clicked(self):
        """Handle retry request"""
        # Check if AI is writing
        if hasattr(self.parent(), 'is_ai_writing') and self.parent().is_ai_writing:
            print("❌ Retry blocked - AI is writing")
            return
            
        self.retry_requested.emit(self.message_obj)
    
    def _on_delete_clicked(self):
        """Handle delete request"""
        # Check if AI is writing
        if hasattr(self.parent(), 'is_ai_writing') and self.parent().is_ai_writing:
            print("❌ Delete blocked - AI is writing")
            return
            
        self.delete_requested.emit(self.message_obj)
    
    def _has_active_descendants(self) -> bool:
        """Check if this message has any active descendants"""
        if hasattr(self.parent(), 'chat_tree'):
            chat_tree = self.parent().chat_tree
            return self._check_descendants_recursive(self.message_obj.id, chat_tree)
        return False

    def _check_descendants_recursive(self, message_id: str, chat_tree) -> bool:
        """Recursively check if any descendants are active"""
        message = chat_tree.messages.get(message_id)
        if not message:
            return False
        
        for child_id in message.children_ids:
            child = chat_tree.messages.get(child_id)
            if child and child.is_active:
                return True
            if self._check_descendants_recursive(child_id, chat_tree):
                return True
        
        return False



class InteractionIcon(QLabel):
    """Clickable interaction icon with improved responsiveness"""
    clicked = Signal(object)
    position_updated = Signal(object, str)
    context_menu_requested = Signal(object, str)
    
    def __init__(self, parent, interaction: Interaction, editor_mode: bool = False):
        super().__init__(parent)
        
        self.interaction = interaction
        self.editor_mode = editor_mode
        self.dragging = False
        self.drag_start_pos = QPoint()
        self.last_click_time = 0
        self.click_debounce_ms = 200  # Reduced for better responsiveness
        
        # Load icon image
        try:
            icon_image = Image.open(interaction.icon_path)
            icon_image.thumbnail((50, 50))
            data = icon_image.convert('RGBA').tobytes('raw', 'RGBA')
            qimg = QImage(data, icon_image.width, icon_image.height, QImage.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimg)
            self.setPixmap(pixmap)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setStyleSheet("background: transparent; border: none;")
        except Exception as e:
            print(f"Error loading icon: {e}")
            self.setText("?")
            self.setFixedSize(50, 30)
            self.setStyleSheet("border: none;")
        
        # Position the icon
        self.move(interaction.position[0], interaction.position[1])
        
        # Set cursor
        if not editor_mode:
            self.setCursor(Qt.PointingHandCursor)
    
    def mousePressEvent(self, event):
        if self.editor_mode:
            if event.button() == Qt.LeftButton:
                self.dragging = True
                self.drag_start_pos = event.position().toPoint()
            elif event.button() == Qt.RightButton:
                self._show_context_menu(event.globalPosition().toPoint())
        else:
            if event.button() == Qt.LeftButton:
                # Quick debounce for better responsiveness
                current_time = QDateTime.currentMSecsSinceEpoch()
                if current_time - self.last_click_time >= self.click_debounce_ms:
                    self.last_click_time = current_time
                    self.clicked.emit(self.interaction)
    
    def mouseMoveEvent(self, event):
        if self.dragging and self.editor_mode:
            new_pos = self.pos() + event.position().toPoint() - self.drag_start_pos
            self.move(new_pos)
            self.interaction.position = (new_pos.x(), new_pos.y())
    
    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            self.position_updated.emit(self.interaction, "position_updated")
    
    def _show_context_menu(self, pos):
        """Show right-click context menu"""
        menu = QMenu(self)
        edit_action = menu.addAction("Edit")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec(pos)
        if action == edit_action:
            self.context_menu_requested.emit(self.interaction, "edit")
        elif action == delete_action:
            self.context_menu_requested.emit(self.interaction, "delete")



class ModernScrollbar(QScrollBar):
    """Custom modern scrollbar with transparency"""
    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(orientation, parent)
        
        self.setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {hex_to_rgba(app_colors.SECONDARY, 30)};
                min-height: 30px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {get_darker_secondary_with_transparency(20)};
                width: 12px;
            }}
            QScrollBar::handle:vertical:pressed {{
                background: {hex_to_rgba(app_colors.PRIMARY, 10)};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

class MessageEditDialog(QDialog):
    """Dialog for editing messages"""
    def __init__(self, parent, message_obj: ChatMessage):
        super().__init__(parent)
        
        self.message_obj = message_obj
        self.new_content = None
        
        self.setWindowTitle(f"Edit {'Your' if message_obj.role == 'user' else 'Character'} Message")
        self.setModal(True)
        self.setFixedSize(500, 300)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create edit dialog UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Instructions
        role_text = "your message" if self.message_obj.role == "user" else "the character's message"
        if self.message_obj.role == "user":
            instruction = f"Edit {role_text}. All messages after this will be removed and the character will generate a new response."
        else:
            instruction = f"Edit {role_text}. This will replace the message in the chat history."
        
        instruction_label = QLabel(instruction)
        instruction_label.setWordWrap(True)
        instruction_label.setStyleSheet("color: gray; font-size: 9pt; padding: 10px;")
        layout.addWidget(instruction_label)
        
        # Text editor
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.message_obj.content)
        self.text_edit.setFocus()
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        save_btn = QPushButton("Save Changes")
        save_btn.clicked.connect(self._save_changes)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _save_changes(self):
        """Save the edited message"""
        self.new_content = self.text_edit.toPlainText().strip()
        if self.new_content:
            self.accept()
