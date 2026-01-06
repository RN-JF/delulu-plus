#  Delulu+ Chatbot v0.3.0
Python chatbot application with advanced character management, seamless animations, chat tree branching, and multi-AI provider support. Built with PySide6 for a sleek, responsive interface.

##  Key Features

###  Advanced Character System
- **Dual Naming System** - Separate folder names and display names for better organization
- **Seamless GIF Animations** - Smooth character animations with preloading and caching
- **Character-Specific Colors** - Custom bubble colors, text colors, and transparency settings
- **Rich Character Profiles** - Detailed personalities, external API integrations, and interaction systems
- **Interactive Avatars** - Clickable character interactions with custom animations

###  Multi-AI Provider Support
- **OpenAI** - GPT-3.5, GPT-4, GPT-4o (streaming supported depending on model)
- **Anthropic** - Claude 3 family with advanced context handling
- **Google** - Gemini Pro and Flash models
- **DeepSeek** - Chat and Coder models with streaming
- **Groq** - Ultra-fast inference models
- **Custom APIs** - Support for OpenAI-compatible endpoints

###  Smart Chat Management
- **Chat Tree System** - Branching conversations with message threading
- **Context-Aware Truncation** - Intelligent conversation history management
- **Message Retry/Regenerate** - Easy message regeneration and branching
- **Real-time Streaming** - Live AI response streaming for supported providers
- **Scheduled Dialogs** - Automated character check-ins and reminders

###  Enhanced UI/UX
- **Modern Interface** - Clean, responsive design with drag-and-drop support
- **Custom Bubble Styling** - Per-character bubble colors and transparency
- **Rich Text Support** - Markdown rendering, code highlighting, and emoji support
- **Smooth Animations** - Character transitions and UI effects
- **Window Customization** - Resizable, draggable chat windows with state persistence

###  Local Data Storage
- **Project-Based Storage** - All data stored locally in project `/data` folder
- **Import/Export System** - Share characters with compatibility handling
- **Backup-Friendly** - Easy to backup and transfer between machines
- **No System Dependencies** - Self-contained data management

⚠️ The `data/` folder is ignored by Git and should never be committed.

##  Quick Start

### Prerequisites
- **Python 3.8+** (Python 3.9+ recommended)
- **Operating System**: Windows 10+, macOS 10.14+, or Linux
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 500MB free space for application and data

### Installation Methods

#### Option 1: Development Setup (Recommended)
```bash
# Clone the repository
git clone <your-repo-url>
cd delulu-plus

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt


# Run the application
python -m src
```



#### Option 3: Standalone Executable (Optional)
Use the provided build scripts to create a standalone executable:
```bash

# using PyInstaller spec
pyinstaller Delulu+.spec 
```

##  Project Structure

```
delulu-plus/
├── src/                        # Source code
│   ├── __init__.py            # Package initialization
│   ├── __main__.py            # Application entry point  
│   ├── common_imports.py      # Centralized imports
│   ├── models/                # Data models
│   │   ├── __init__.py
│   │   ├── api_config.py      # AI provider configurations
│   │   ├── character.py       # Character models with dual naming
│   │   ├── user_profile.py    # User settings and profiles
│   │   ├── chat_models.py     # Chat messages and settings
│   │   └── ui_models.py       # UI-specific models
│   ├── ui/                    # User interface
│   │   ├── __init__.py
│   │   ├── main_window.py     # Main application window with animations
│   │   ├── dialogs.py         # Configuration and management dialogs
│   │   └── widgets.py         # Custom UI components
│   ├── core/                  # Business logic
│   │   ├── __init__.py
│   │   ├── ai_interface.py    # AI provider integration
│   │   └── chat_manager.py    # Chat tree and conversation management
│   └── utils/                 # Utilities
│       ├── __init__.py
│       ├── file_manager.py    # Local file operations
│       └── helpers.py         # Helper functions
├── src/assets/                # Application assets
│   └── icon.PNG               # Application icon 
├── data/                       # Local data storage (created at runtime)
│   ├── characters/            # Character configs and chat history
│   ├── api_configs/           # AI provider settings
│   └── user_profiles/         # User preferences
├── launcher_fast.py           # Fast startup launcher
├── Delulu+.spec              # PyInstaller spec file
├── pyproject.toml            # Modern Python packaging
├── requirements.txt          # Dependencies
└── README.md                 # This file
```

##  AI Provider Configuration

### Supported Providers & Streaming

| Provider | Streaming | Context Size | Popular Models |
|----------|-----------|--------------|-----------------|
| **OpenAI** | ✅ Full | 4K - 128K | GPT-3.5, GPT-4, GPT-4o |
| **Anthropic** | ⚠️ Fallback | 200K | Claude 3 Haiku, Sonnet, Opus |
| **Google** | ⚠️ Fallback | 32K - 1M | Gemini Pro, Flash |
| **DeepSeek** | ✅ Full | 32K | Chat, Coder models |
| **Groq** | ⚠️ Fallback | 8K - 32K | Ultra-fast inference |
| **Custom** | ⚠️ Varies | Varies | OpenAI-compatible APIs |

*✅ = Full streaming support, ⚠️ = Non-streaming fallback*
Streaming support depends on provider and model.


### Setup Process
1. **API Configuration**: Add API keys via the API menu
2. **Model Selection**: Choose appropriate models for your use case
3. **Character Assignment**: Assign AI configs to specific characters
4. **Test Connections**: Use built-in connection testing

##  Data Management

### Local Storage Benefits
- **No Cloud Dependencies**: All data stays on your machine
- **Easy Backups**: Simply copy the `/data` folder
- **Portable**: Move between computers easily
- **Privacy**: Complete data control and privacy

### Data Structure
```
data/
├── characters/
│   └── character_folder_name/
│       ├── config.json        # Character configuration
│       ├── personality.txt    # Character personality
│       ├── base_image.gif     # Character avatar
│       ├── chat_history.json  # Conversation history
│       └── interactions/      # Custom interactions
├── api_configs/
│   └── *.json                 # AI provider configurations
└── user_profiles/
    └── user_settings.json     # Global user preferences
```

##  Character Features

### Advanced Character System
- **Dual Naming**: Separate folder names (for organization) and display names (for chat)
- **Rich Personalities**: Detailed character descriptions and behaviors
- **Custom Colors**: Per-character bubble colors, text colors, and transparency
- **Animated Avatars**: GIF support with smooth transitions and caching
- **External APIs**: Character-specific API configurations and external integrations

### Interaction System
- **Custom Interactions**: Create clickable character interactions
- **Animation Triggers**: Special animations for interactions
- **Positioning Control**: Precise control over interaction placement
- **Duration Settings**: Configurable interaction durations

## Development

Install dependencies for development:

```bash
pip install -r requirements.txt
```

### Building Executables

#### Using PyInstaller Spec
```bash
pyinstaller Delulu+.spec
```

The executable will be created in the `dist/` directory.


## Contributing
Contributions and suggestions are welcome, have fun!.


### Code Guidelines
- Use `black` for code formatting
- Follow PEP 8 style guidelines
- Include type hints where appropriate
- Add docstrings for public functions
- Test your changes thoroughly

##  License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ for AI enthusiasts and character creators**
*First project — bugs are features in disguise*
