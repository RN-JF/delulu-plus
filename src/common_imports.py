"""
Common imports file for Delulu+ Chatbot
Import this file in other modules to get all standard imports
"""

# ========== 1. STANDARD LIBRARY IMPORTS ==========
import sys
import os
import json
import uuid
import math
import shutil
import platform
import re
import html
import io
import time
import threading
import queue
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable, Union
from dataclasses import dataclass, asdict, field
import fnmatch
from datetime import datetime, timedelta

# ========== 2. PySide6 IMPORTS ==========
try:
    from PySide6.QtWidgets import *
    from PySide6.QtCore import *
    from PySide6.QtGui import *
except ImportError as e:
    print(f"Critical Error: PySide6 import failed: {e}")
    sys.exit(1)

# ========== 3. THIRD-PARTY IMPORTS ==========
try:
    import requests
except ImportError:
    requests = None
    print("Warning: requests not installed")

try:
    import aiohttp
    import asyncio
except ImportError:
    aiohttp = None
    asyncio = None
    print("Warning: aiohttp not installed")

try:
    from PIL import Image, ImageSequence, ImageFont, ImageDraw, ImageQt
except ImportError:
    Image = None
    print("Warning: PIL/Pillow not installed")

# ========== 4. UTILITY FUNCTIONS ==========
def get_timestamp():
    return datetime.now().isoformat()

def safe_json_load(file_path: str) -> Optional[Dict]:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

def safe_json_save(data: Dict, file_path: str) -> bool:
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False