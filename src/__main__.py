"""Main entry point for Delulu+ Chatbot"""
from .common_imports import *
from .utils.file_manager import get_app_data_dir
from .models.api_config import APIConfig
from .ui.main_window import MainApplication

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


def set_application_icon(app):
    """Set application icon with Windows taskbar support - PyQt6 compatible"""
    
    # Multiple potential icon locations
    icon_locations = [
        Path(__file__).parent / "assets" / "icon.ico",
        Path(__file__).parent / "assets" / "icon.png",
        Path(__file__).parent / "icon.ico",
        Path(__file__).parent / "icon.png",
        Path(__file__).parent.parent / "assets" / "icon.ico",
        Path(__file__).parent.parent / "assets" / "icon.png",
        Path(__file__).parent.parent / "icon.ico",
        Path(__file__).parent.parent / "icon.png",
    ]
    
    icon_found = False
    
    for icon_path in icon_locations:
        if icon_path.exists():
            try:
                # Create QIcon
                icon = QIcon(str(icon_path))
                
                # Verify icon loaded properly
                if not icon.isNull():
                    # Set for the application (this affects taskbar)
                    app.setWindowIcon(icon)
                    
                    print(f"✅ Application icon set from: {icon_path}")
                    icon_found = True
                    break
                    
            except Exception as e:
                print(f"⚠️ Failed to load icon from {icon_path}: {e}")
                continue
    
    if not icon_found:
        print("❌ No valid icon found")
    
    return icon_found

def setup_windows_properties():
    """Set Windows-specific properties for better taskbar integration"""
    try:
        if os.name == 'nt':  # Windows only
            try:
                import ctypes
                # Set the application user model ID for Windows taskbar grouping
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Delulu.Plus.App")
                print("✅ Windows App ID set for taskbar grouping")
            except Exception as e:
                print(f"⚠️ Could not set Windows App ID: {e}")
    except Exception as e:
        print(f"❌ Error setting Windows properties: {e}")

def setup_api_system():
    """Initialize the API configuration system"""
    try:
        app_data_dir = get_app_data_dir()
        configs_dir = app_data_dir / "api_configs"
        configs_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if we need to create example configs
        if not any(configs_dir.glob("*.json")):
            print("🔧 Creating example API configurations...")
            create_example_configs(configs_dir)
        
        print(f"✅ API system initialized: {configs_dir}")
        
    except Exception as e:
        print(f"❌ Error setting up API system: {e}")

def create_example_configs(configs_dir: Path):
    """Create example API configuration files"""
    
    # OpenAI config
    openai_config = {
        "name": "OpenAI GPT-4",
        "provider": "openai",
        "model": "gpt-4",
        "system_prompt": "You are {character_name}. {personality}\n\nKey Instructions:\n- Stay in character at all times\n- Respond naturally and conversationally\n- Show personality through your responses",
        "use_chain_of_thought": True,
        "use_examples": True,
        "output_format_instruction": "Respond in character with natural dialogue. Use markdown for emphasis when appropriate.",
        "api_key": "sk-your-openai-api-key-here",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": 150,
        "context_size": 8192,
        "enabled": False
    }
    
    # OpenRouter config
    openrouter_config = {
        "name": "OpenRouter Claude",
        "provider": "openrouter", 
        "model": "anthropic/claude-3-sonnet",
        "system_prompt": "You are {character_name}. {personality}\n\nKey Instructions:\n- Stay in character at all times\n- Respond naturally and conversationally\n- Show personality through your responses",
        "use_chain_of_thought": True,
        "use_examples": True,
        "output_format_instruction": "Respond in character with natural dialogue. Use markdown for emphasis when appropriate.",
        "api_key": "sk-or-your-openrouter-key-here",
        "base_url": "https://openrouter.ai/api/v1",
        "temperature": 0.7,
        "max_tokens": 150,
        "context_size": 200000,
        "enabled": False
    }
    
    # Anthropic config
    anthropic_config = {
        "name": "Anthropic Claude",
        "provider": "anthropic",
        "model": "claude-3-sonnet-20240229",
        "system_prompt": "You are {character_name}. {personality}\n\nKey Instructions:\n- Stay in character at all times\n- Respond naturally and conversationally\n- Show personality through your responses",
        "use_chain_of_thought": True,
        "use_examples": True,
        "output_format_instruction": "Respond in character with natural dialogue. Use markdown for emphasis when appropriate.",
        "api_key": "sk-ant-your-anthropic-key-here",
        "base_url": "https://api.anthropic.com",
        "temperature": 0.7,
        "max_tokens": 150,
        "context_size": 200000,
        "enabled": False
    }
    
    # GPT-4o config
    gpt4_config = {
        "name": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
        "system_prompt": "You are {character_name}. {personality}\n\nKey Instructions:\n- Stay in character at all times\n- Respond naturally and conversationally\n- Show personality through your responses",
        "use_chain_of_thought": True,
        "use_examples": True,
        "output_format_instruction": "Respond in character with natural dialogue. Use markdown for emphasis when appropriate.",
        "api_key": "sk-your-openai-api-key-here",
        "base_url": "https://api.openai.com/v1",
        "temperature": 0.7,
        "max_tokens": 150,
        "context_size": 8192,
        "enabled": False
    }
    
    # Save example configs
    configs = [openai_config, openrouter_config, anthropic_config, gpt4_config]
    for config in configs:
        filename = f"{config['name'].replace(' ', '_').lower()}.json"
        config_path = configs_dir / filename
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2)
            print(f"✅ Created example config: {filename}")
        except Exception as e:
            print(f"❌ Error creating config {filename}: {e}")

def setup_global_error_handling():
    """Setup global error handling for PyQt"""
    def exception_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        print(f"💥 Unhandled exception: {exc_type.__name__}: {exc_value}")
        import traceback
        traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = exception_hook

def main():
    """Main application entry point"""
    try:
        # Setup error handling
        setup_global_error_handling()
        
        # IMPORTANT: Set Windows properties BEFORE creating QApplication
        setup_windows_properties()
        
        # Set application properties BEFORE creating QApplication
        QApplication.setApplicationName("Delulu+")
        QApplication.setApplicationDisplayName("Delulu+")
        QApplication.setApplicationVersion("0.3.0")
        QApplication.setOrganizationName("Delulu")
        QApplication.setOrganizationDomain("delulu.app")
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        # Create application
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        
        # Set application icon IMMEDIATELY after creating app
        set_application_icon(app)
        
        # Setup API system
        setup_api_system()
        
        # Create and show main window
        window = MainApplication()
        
        # IMPORTANT: Set icon on main window too
        if not app.windowIcon().isNull():
            window.setWindowIcon(app.windowIcon())
        
        window.show()
        
        # Start event loop
        sys.exit(app.exec())
        
    except Exception as e:
        print(f"💥 Fatal error in main(): {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()