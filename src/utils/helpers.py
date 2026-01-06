"""Helper utility functions"""
from ..common_imports import *
from ..models.ui_models import app_colors
from PySide6.QtCore import Signal, QTimer, QEvent, Qt
from PySide6.QtWidgets import QMainWindow, QPushButton, QApplication
from PySide6.QtGui import QPixmapCache, QKeyEvent

def hex_to_rgba(hex_color: str, transparency: int) -> str:
    """Convert hex color to RGBA with transparency (0-100)"""
    # Remove # if present
    hex_color = hex_color.lstrip('#')
    
    # Convert hex to RGB
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    
    # Convert transparency percentage to alpha (0-1)
    alpha = 1.0 - (transparency / 100.0)
    
    return f"rgba({r}, {g}, {b}, {alpha})"


def safe_copy_file(source_path: str, target_path: str) -> bool:
    """Safely copy a file, handling same-file scenarios"""
    try:
        import os
        import shutil
        
        # Resolve both paths to absolute paths
        source_abs = os.path.abspath(source_path)
        target_abs = os.path.abspath(target_path)
        
        # Check if they're the same file
        if source_abs == target_abs:
            print(f"ℹ️ Source and target are the same file: {source_abs}")
            return True  # Consider this a success since file is already in place
        
        # Check if target directory exists, create if not
        target_dir = os.path.dirname(target_abs)
        os.makedirs(target_dir, exist_ok=True)
        
        # Copy the file
        shutil.copy2(source_abs, target_abs)
        print(f"✅ Successfully copied: {source_abs} → {target_abs}")
        return True
        
    except Exception as e:
        print(f"❌ Error copying file: {e}")
        return False



def force_reload_image(image_path: str) -> QPixmap:
    """Force Qt to reload an image from disk, bypassing cache"""
    try:
        if not os.path.exists(image_path):
            print(f"⚠️ Image not found: {image_path}")
            return QPixmap()
        
        # Clear Qt's image cache for this file
        QPixmapCache.clear()
        
        # Read file with a unique parameter to force reload
        import time
        unique_path = f"{image_path}?t={int(time.time() * 1000)}"
        
        # Load image directly from bytes to bypass Qt caching
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        
        if pixmap.isNull():
            print(f"⚠️ Failed to load image: {image_path}")
            return QPixmap()
        
        print(f"✅ Force reloaded image: {image_path}")
        return pixmap
        
    except Exception as e:
        print(f"❌ Error force reloading image: {e}")
        return QPixmap()




def replace_name_placeholders(text: str, character_name: str, user_name: str) -> str:
    """Replace {{character}} and {{user}} placeholders with actual names"""
    if not text:
        return text
    
    # Replace official placeholders (case-insensitive)
    text = re.sub(r'\{\{character\}\}', character_name, text, flags=re.IGNORECASE)
    text = re.sub(r'\{\{user\}\}', user_name, text, flags=re.IGNORECASE)
    
    # OPTIONAL: Also handle common literal phrases
    # Replace "the user" with user name (be careful with context)
    text = re.sub(r'\bthe user\b', user_name, text, flags=re.IGNORECASE)
    
    # Replace "user" at the end of sentences or followed by punctuation
    text = re.sub(r'\buser(?=[.!?,:;]|\s|$)', user_name, text, flags=re.IGNORECASE)
    
    return text



def get_darker_secondary_with_transparency(transparency: int = 30) -> str:
    """Get darker secondary color with transparency using your hex_to_rgba function"""
    try:
        color = QColor(app_colors.SECONDARY)
        factor = 0.8  # 20% darker
        
        r = int(color.red() * factor)
        g = int(color.green() * factor)
        b = int(color.blue() * factor)
        
        # Convert back to hex then use your function
        darker_hex = f"#{r:02x}{g:02x}{b:02x}"
        return hex_to_rgba(darker_hex, transparency)
    except:
        return hex_to_rgba("#D0D0D0", transparency)  # Fallback
