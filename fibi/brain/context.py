# Builds context from screen for Fibi
from . import screen

def get_context():
    text = screen.read_screen_text()
    return f"User screen content:\n{text[:500]}"  # limit to 500 chars
