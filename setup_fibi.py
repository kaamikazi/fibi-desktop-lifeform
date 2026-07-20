import os

# All folders to create
folders = [
    "fibi/brain",
    "fibi/control",
    "fibi/voice",
    "fibi/ui/assets",
]

# All files to create with starter content
files = {
    "fibi/main.py": '''# Fibi - Main Entry Point
print("🌸 Starting Fibi...")
''',

    "fibi/brain/ai.py": '''# AI Brain - Ollama connection
import requests

FAST_MODEL = "qwen:3b"      # GPU - real-time chat
SMART_MODEL = "deepseek:7b" # CPU - code analysis

def ask(prompt, smart=False):
    model = SMART_MODEL if smart else FAST_MODEL
    response = requests.post("http://localhost:11434/api/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    return response.json().get("response", "")
''',

    "fibi/brain/screen.py": '''# Screen capture + OCR
import mss
import pytesseract
from PIL import Image

def capture_screen():
    with mss.mss() as sct:
        screenshot = sct.grab(sct.monitors[1])
        return Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")

def read_screen_text():
    img = capture_screen()
    return pytesseract.image_to_string(img)
''',

    "fibi/brain/context.py": '''# Builds context from screen for Fibi
from . import screen

def get_context():
    text = screen.read_screen_text()
    return f"User screen content:\\n{text[:500]}"  # limit to 500 chars
''',

    "fibi/control/apps.py": '''# Open/close apps - whitelisted only
import subprocess

ALLOWED_APPS = [
    "notepad",
    "chrome",
    "code",       # VS Code
    "explorer",
    "spotify",
]

def open_app(name):
    if name.lower() in ALLOWED_APPS:
        subprocess.Popen(name)
        return f"Opening {name}!"
    return f"Sorry, {name} is not in my allowed list."

def close_app(name):
    if name.lower() in ALLOWED_APPS:
        subprocess.call(["taskkill", "/f", "/im", f"{name}.exe"])
        return f"Closed {name}!"
    return f"Sorry, {name} is not in my allowed list."
''',

    "fibi/control/keyboard.py": '''# Keyboard control - safe typing only
import pyautogui
import time

def type_text(text):
    time.sleep(0.5)
    pyautogui.typewrite(text, interval=0.05)

def press_key(key):
    pyautogui.press(key)
''',

    "fibi/control/browser.py": '''# Web search
import webbrowser

def search(query):
    url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
    webbrowser.open(url)
    return f"Searching for: {query}"
''',

    "fibi/voice/listen.py": '''# Speech to text using faster-whisper
# pip install faster-whisper sounddevice numpy

def listen():
    print("🎙️ Listening... (placeholder)")
    # TODO: integrate faster-whisper
    return ""
''',

    "fibi/voice/speak.py": '''# Text to speech using edge-tts
# pip install edge-tts

import asyncio
import edge_tts
import pygame
import tempfile
import os

VOICE = "en-US-AriaNeural"

async def _speak(text):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        path = f.name
    tts = edge_tts.Communicate(text, VOICE)
    await tts.save(path)
    pygame.mixer.init()
    pygame.mixer.music.load(path)
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)
    os.remove(path)

def speak(text):
    asyncio.run(_speak(text))
''',

    "fibi/ui/window.py": '''# PyQt6 transparent overlay window
# (Phase 1 - to be built next)
''',

    "fibi/ui/avatar.py": '''# Avatar animation + expression logic
# Expressions: idle, happy, thinking, surprised, focused
# (Phase 1 - to be built next)
''',

    "fibi/config.json": '''{
    "name": "Fibi",
    "fast_model": "qwen:3b",
    "smart_model": "deepseek:7b",
    "ollama_url": "http://localhost:11434",
    "voice": "en-US-AriaNeural",
    "wake_word": "hey fibi",
    "allowed_apps": ["notepad", "chrome", "code", "explorer", "spotify"]
}
''',

    "fibi/requirements.txt": '''PyQt6
requests
mss
pytesseract
Pillow
pyautogui
edge-tts
pygame
faster-whisper
sounddevice
numpy
'''
}

# Create folders
for folder in folders:
    os.makedirs(folder, exist_ok=True)
    print(f"📁 Created: {folder}")

# Create files
for path, content in files.items():
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📄 Created: {path}")

print("\n✅ Fibi project structure ready!")
print("👉 Next: cd fibi && pip install -r requirements.txt")