# Screen capture + OCR
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
