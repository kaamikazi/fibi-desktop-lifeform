# Open/close apps - whitelisted only
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
