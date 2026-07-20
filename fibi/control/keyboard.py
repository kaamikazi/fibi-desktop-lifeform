# Keyboard control - safe typing only
import pyautogui
import time

def type_text(text):
    time.sleep(0.5)
    pyautogui.typewrite(text, interval=0.05)

def press_key(key):
    pyautogui.press(key)
