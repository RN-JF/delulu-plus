"""UI-related Models"""
from ..common_imports import *

class AppColors(QObject):
    """Global color manager with dynamic updates"""
    
    # Signal emitted when colors change
    colors_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self._primary = "#2196F3"
        self._secondary = "#F5F5F5"
    
    @property
    def PRIMARY(self):
        return self._primary
    
    @PRIMARY.setter
    def PRIMARY(self, value):
        if self._primary != value:
            self._primary = value
            self.colors_changed.emit()
    
    @property
    def SECONDARY(self):
        return self._secondary
    
    @SECONDARY.setter
    def SECONDARY(self, value):
        if self._secondary != value:
            self._secondary = value
            self.colors_changed.emit()
    
    def set_colors(self, primary, secondary):
        """Set both colors at once (emits signal only once)"""
        old_primary = self._primary
        old_secondary = self._secondary
        
        self._primary = primary
        self._secondary = secondary
        
        if old_primary != primary or old_secondary != secondary:
            self.colors_changed.emit()
    
    def load_colors(self):
        """Load colors from file"""
        try:
            colors_file = Path("app_colors.json")
            if colors_file.exists():
                with open(colors_file, 'r') as f:
                    data = json.load(f)
                    primary = data.get('primary', "#2196F3")
                    secondary = data.get('secondary', "#F5F5F5")
                    self.set_colors(primary, secondary)
        except Exception as e:
            print(f"Error loading colors: {e}")
    
    def save_colors(self):
        """Save colors to file"""
        try:
            colors_file = Path("app_colors.json")
            data = {
                'primary': self._primary,
                'secondary': self._secondary
            }
            with open(colors_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving colors: {e}")

# Create global instance AFTER the class definition
app_colors = AppColors()