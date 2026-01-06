#!/usr/bin/env python3
"""
FAST launcher for Delulu+ v0.3.0 with lazy loading and optimizations
Updated for current project structure with src/ modules
Loads modules only when needed for lightning-fast startup
"""

import sys
import os
from pathlib import Path

# Show startup message immediately
print(" Starting Delulu+ v0.3.0...")

def get_smart_app_data_dir():
    """Fast data directory setup for v0.3.0 local storage"""
    if getattr(sys, 'frozen', False):
        # Running as executable
        exe_dir = Path(sys.executable).parent
        app_dir = exe_dir / "Delulu+_Data"
    else:
        # Running from source - use project-local data directory
        launcher_path = Path(__file__).parent
        project_root = launcher_path
        
        # Find project root by looking for src/ directory
        for parent in [launcher_path] + list(launcher_path.parents):
            if (parent / "src").exists():
                project_root = parent
                break
        
        # Use local data directory (v2.1 feature)
        app_dir = project_root / "data"
    
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir

def setup_module_environment():
    """Minimal path setup for current project structure"""
    if getattr(sys, 'frozen', False):
        # Running as executable
        bundle_dir = Path(sys.executable).parent
        if str(bundle_dir) not in sys.path:
            sys.path.insert(0, str(bundle_dir))
    else:
        # Running from source
        launcher_dir = Path(__file__).parent
        if str(launcher_dir) not in sys.path:
            sys.path.insert(0, str(launcher_dir))

def patch_data_directory_fast():
    """Fast patching for v0.3.0 local storage system"""
    try:
        # Import and patch the file_manager for local storage
        import src.utils.file_manager
        src.utils.file_manager.get_app_data_dir = get_smart_app_data_dir
        print("✅ Local storage system configured")
    except ImportError:
        print("⚠️  Could not patch file manager (continuing anyway)")
    except Exception as e:
        print(f"⚠️  Patching warning: {e}")

def verify_project_structure():
    """Quick verification of project structure"""
    try:
        # Check if we can find the main modules
        if getattr(sys, 'frozen', False):
            # In executable, check for bundled src
            bundle_dir = Path(sys.executable).parent
            src_check = bundle_dir / "src"
        else:
            # In source, check for src directory
            project_root = Path(__file__).parent
            src_check = project_root / "src"
        
        if src_check.exists():
            print(f"✅ Project structure verified: {src_check}")
            return True
        else:
            print(f"⚠️  Source directory not found: {src_check}")
            return False
            
    except Exception as e:
        print(f"⚠️  Structure check failed: {e}")
        return False

def main():
    """Optimized main entry point for v2.1"""
    
    print("⚡ Setting up environment...")
    setup_module_environment()
    
    print("🔍 Verifying project structure...")
    if not verify_project_structure():
        print("⚠️  Continuing despite structure warnings...")
    
    print("📁 Configuring local data storage...")
    patch_data_directory_fast()
    
    try:
        print("🎯 Loading Delulu+ v2.1...")
        
        # OPTIMIZATION: Import the main module directly
        # This allows the main module to handle all its own imports
        import src.__main__
        
        print("✅ Starting Delulu+ v2.1...")
        print("🎭 Character animation system ready")
        print("🌳 Chat tree system ready") 
        print("💾 Local storage system ready")
        
        # Run the application
        src.__main__.main()
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        
        # Enhanced debugging for v2.1
        print(f"🔍 Python version: {sys.version}")
        print(f"📂 Working directory: {os.getcwd()}")
        print(f"🛤️  Python path (first 3): {sys.path[:3]}")
        
        if getattr(sys, 'frozen', False):
            bundle_dir = Path(sys.executable).parent
            print(f"📦 Bundle directory: {bundle_dir}")
            
            # Check for expected v2.1 structure
            expected_items = ['src', 'assets']
            for item in expected_items:
                item_path = bundle_dir / item
                if item_path.exists():
                    print(f"✅ Found: {item}")
                    if item == 'src':
                        # Check main modules
                        main_modules = ['__main__.py', 'common_imports.py', 'models', 'ui', 'core', 'utils']
                        for module in main_modules:
                            module_path = item_path / module
                            if module_path.exists():
                                print(f"   ✅ {module}")
                            else:
                                print(f"   ❌ {module}")
                else:
                    print(f"❌ Missing: {item}")
        else:
            # Source mode debugging
            project_root = Path(__file__).parent
            print(f"📁 Project root: {project_root}")
            src_path = project_root / "src"
            if src_path.exists():
                print("✅ src/ directory found")
                # List main modules
                modules = list(src_path.glob("*.py"))
                subdirs = [d for d in src_path.iterdir() if d.is_dir()]
                print(f"📄 Python files: {[m.name for m in modules]}")
                print(f"📁 Subdirectories: {[d.name for d in subdirs]}")
            else:
                print("❌ src/ directory not found!")
        
        raise
    
    except Exception as e:
        print(f"❌ Runtime Error: {e}")
        
        # Enhanced error reporting for v2.1
        if '--debug' in sys.argv or '-v' in sys.argv:
            import traceback
            print("\n🔍 Full traceback:")
            traceback.print_exc()
        else:
            print("💡 Run with --debug for full traceback")
        
        # v2.1 specific checks
        try:
            import PySide6
            print(f"✅ PySide6 available: {PySide6.__version__}")
        except ImportError:
            print("❌ PySide6 not available - this is required for v2.1!")
            
        try:
            import requests
            print(f"✅ requests available: {requests.__version__}")
        except ImportError:
            print("❌ requests not available - AI providers won't work!")
            
        try:
            import PIL
            print(f"✅ Pillow available: {PIL.__version__}")
        except ImportError:
            print("❌ Pillow not available - character animations won't work!")
        
        raise

if __name__ == "__main__":
    print(" Delulu+ v0.3.0 Launcher")
    print("=" * 40)
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Fatal error: {e}")
        sys.exit(1)