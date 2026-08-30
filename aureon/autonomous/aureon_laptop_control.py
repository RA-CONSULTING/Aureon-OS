"""
aureon_laptop_control.py - Aureon Queen Laptop Hardware Abstraction Layer

Complete hardware control for Windows 11. Every capability a human has
with the physical laptop, the Queen can invoke programmatically.

All methods return: {"success": bool, "result": any, "error": str}
"""

import os
import sys
import json
import time
import glob as glob_mod
import socket
import struct
import datetime
import pathlib
import traceback

# ---------------------------------------------------------------------------
# Repo sys.path setup
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ---------------------------------------------------------------------------
# State directories
# ---------------------------------------------------------------------------
_STATE_DIR = _REPO_ROOT / "state"
_SCREENSHOT_DIR = _STATE_DIR / "screenshots"
_CAMERA_DIR = _STATE_DIR / "camera"
_LOG_PATH = _STATE_DIR / "laptop_control_log.jsonl"

for _d in (_SCREENSHOT_DIR, _CAMERA_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Optional library imports with availability flags
# ---------------------------------------------------------------------------
try:
    import pyautogui
    # Keep the physical corner failsafe enabled even for this legacy HAL.  New
    # autonomous mutation paths must route through the governed desktop gateway.
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    HAS_PYAUTOGUI = True
except ImportError:
    pyautogui = None
    HAS_PYAUTOGUI = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    cv2 = None
    HAS_CV2 = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    Image = None
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    pytesseract = None
    HAS_TESSERACT = False

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    pyttsx3 = None
    HAS_PYTTSX3 = False

try:
    import speech_recognition as sr
    HAS_SPEECH = True
except ImportError:
    sr = None
    HAS_SPEECH = False

try:
    import pyperclip
    HAS_PYPERCLIP = True
except ImportError:
    pyperclip = None
    HAS_PYPERCLIP = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

try:
    import ctypes
    import ctypes.wintypes
    HAS_CTYPES = True
except ImportError:
    ctypes = None
    HAS_CTYPES = False

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    winsound = None
    HAS_WINSOUND = False

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    winreg = None
    HAS_WINREG = False

try:
    import keyboard as keyboard_lib
    HAS_KEYBOARD = True
except ImportError:
    keyboard_lib = None
    HAS_KEYBOARD = False

try:
    import mouse as mouse_lib
    HAS_MOUSE = True
except ImportError:
    mouse_lib = None
    HAS_MOUSE = False

try:
    from screeninfo import get_monitors
    HAS_SCREENINFO = True
except ImportError:
    get_monitors = None
    HAS_SCREENINFO = False

try:
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    HAS_PYCAW = True
except ImportError:
    HAS_PYCAW = False

try:
    import sounddevice
    HAS_SOUNDDEVICE = True
except ImportError:
    sounddevice = None
    HAS_SOUNDDEVICE = False

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    pyaudio = None
    HAS_PYAUDIO = False

import subprocess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ts():
    """Timestamp string for filenames."""
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _ok(result=None):
    return {"success": True, "result": result, "error": None}


def _fail(error):
    return {"success": False, "result": None, "error": str(error)}


def _log_action(method: str, args: dict, result: dict):
    """Append a line to the JSONL action log."""
    try:
        entry = {
            "ts": datetime.datetime.now().isoformat(),
            "method": method,
            "args": {k: str(v)[:200] for k, v in args.items()},
            "success": result.get("success"),
        }
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------
class LaptopControl:
    """Full laptop hardware abstraction layer for Aureon Queen."""

    # -----------------------------------------------------------------------
    # 1. SCREEN & VISION
    # -----------------------------------------------------------------------

    def screenshot(self, region=None, save_path=None) -> dict:
        """Take screenshot. region=(x,y,w,h) or None for full screen.
        Returns path to saved image."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            img = pyautogui.screenshot(region=region)
            if save_path is None:
                save_path = str(_SCREENSHOT_DIR / f"screenshot_{_ts()}.png")
            img.save(save_path)
            r = _ok(save_path)
            _log_action("screenshot", {"region": region, "save_path": save_path}, r)
            return r
        except Exception as e:
            r = _fail(f"screenshot failed: {e}")
            _log_action("screenshot", {"region": region}, r)
            return r

    def read_screen(self, region=None) -> dict:
        """Take screenshot and OCR it. Returns all text visible on screen."""
        try:
            if not HAS_PYAUTOGUI or not HAS_TESSERACT:
                return _fail("pyautogui or pytesseract not available")
            img = pyautogui.screenshot(region=region)
            text = pytesseract.image_to_string(img)
            r = _ok(text.strip())
            _log_action("read_screen", {"region": region}, r)
            return r
        except Exception as e:
            r = _fail(f"read_screen failed: {e}")
            _log_action("read_screen", {"region": region}, r)
            return r

    def read_screen_at(self, x, y, width, height) -> dict:
        """Read text from a specific screen region."""
        return self.read_screen(region=(x, y, width, height))

    def find_on_screen(self, text) -> dict:
        """Find text on screen via OCR, return its center coordinates."""
        try:
            if not HAS_PYAUTOGUI or not HAS_TESSERACT:
                return _fail("pyautogui or pytesseract not available")
            img = pyautogui.screenshot()
            data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
            n = len(data["text"])
            text_lower = text.lower()
            # Try single-word match first
            for i in range(n):
                if text_lower in str(data["text"][i]).lower():
                    x = data["left"][i] + data["width"][i] // 2
                    y = data["top"][i] + data["height"][i] // 2
                    r = _ok({"x": x, "y": y, "text": data["text"][i]})
                    _log_action("find_on_screen", {"text": text}, r)
                    return r
            # Try multi-word match across consecutive words
            words = text_lower.split()
            if len(words) > 1:
                for i in range(n - len(words) + 1):
                    match = True
                    for j, w in enumerate(words):
                        if w not in str(data["text"][i + j]).lower():
                            match = False
                            break
                    if match:
                        x1 = data["left"][i]
                        y1 = data["top"][i]
                        x2 = data["left"][i + len(words) - 1] + data["width"][i + len(words) - 1]
                        y2 = max(data["top"][i + k] + data["height"][i + k] for k in range(len(words)))
                        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                        r = _ok({"x": cx, "y": cy, "text": text})
                        _log_action("find_on_screen", {"text": text}, r)
                        return r
            r = _fail(f"Text '{text}' not found on screen")
            _log_action("find_on_screen", {"text": text}, r)
            return r
        except Exception as e:
            r = _fail(f"find_on_screen failed: {e}")
            _log_action("find_on_screen", {"text": text}, r)
            return r

    def find_image_on_screen(self, image_path, confidence=0.8) -> dict:
        """Find an image/icon on screen. Returns center coordinates."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location is None:
                r = _fail(f"Image not found on screen: {image_path}")
            else:
                center = pyautogui.center(location)
                r = _ok({"x": center.x, "y": center.y, "region": {
                    "left": location.left, "top": location.top,
                    "width": location.width, "height": location.height
                }})
            _log_action("find_image_on_screen", {"image_path": image_path}, r)
            return r
        except Exception as e:
            r = _fail(f"find_image_on_screen failed: {e}")
            _log_action("find_image_on_screen", {"image_path": image_path}, r)
            return r

    def get_screen_size(self) -> dict:
        """Get screen resolution for all monitors."""
        try:
            if HAS_SCREENINFO:
                monitors = get_monitors()
                info = [{"name": m.name, "width": m.width, "height": m.height,
                         "x": m.x, "y": m.y, "is_primary": m.is_primary}
                        for m in monitors]
                return _ok(info)
            elif HAS_PYAUTOGUI:
                w, h = pyautogui.size()
                return _ok([{"width": w, "height": h, "is_primary": True}])
            else:
                return _fail("No screen library available")
        except Exception as e:
            return _fail(f"get_screen_size failed: {e}")

    def get_pixel_color(self, x, y) -> dict:
        """Get RGB color of pixel at coordinates."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            r, g, b = pyautogui.pixel(x, y)
            res = _ok({"r": r, "g": g, "b": b, "hex": f"#{r:02x}{g:02x}{b:02x}"})
            _log_action("get_pixel_color", {"x": x, "y": y}, res)
            return res
        except Exception as e:
            return _fail(f"get_pixel_color failed: {e}")

    # -----------------------------------------------------------------------
    # 2. MOUSE
    # -----------------------------------------------------------------------

    def mouse_move(self, x, y, duration=0.3) -> dict:
        """Move mouse to absolute coordinates."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.moveTo(x, y, duration=duration)
            r = _ok({"x": x, "y": y})
            _log_action("mouse_move", {"x": x, "y": y}, r)
            return r
        except Exception as e:
            return _fail(f"mouse_move failed: {e}")

    def mouse_click(self, x=None, y=None, button="left", clicks=1) -> dict:
        """Click at position. If no coords, click current position."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.click(x=x, y=y, button=button, clicks=clicks)
            pos = pyautogui.position()
            r = _ok({"x": pos.x, "y": pos.y, "button": button, "clicks": clicks})
            _log_action("mouse_click", {"x": x, "y": y, "button": button}, r)
            return r
        except Exception as e:
            return _fail(f"mouse_click failed: {e}")

    def mouse_double_click(self, x=None, y=None) -> dict:
        """Double-click at position."""
        return self.mouse_click(x=x, y=y, button="left", clicks=2)

    def mouse_right_click(self, x=None, y=None) -> dict:
        """Right-click at position."""
        return self.mouse_click(x=x, y=y, button="right", clicks=1)

    def mouse_drag(self, start_x, start_y, end_x, end_y, duration=0.5) -> dict:
        """Drag from start to end."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.moveTo(start_x, start_y)
            pyautogui.drag(end_x - start_x, end_y - start_y, duration=duration)
            r = _ok({"from": [start_x, start_y], "to": [end_x, end_y]})
            _log_action("mouse_drag", {"start": [start_x, start_y], "end": [end_x, end_y]}, r)
            return r
        except Exception as e:
            return _fail(f"mouse_drag failed: {e}")

    def mouse_scroll(self, clicks, x=None, y=None) -> dict:
        """Scroll wheel. Positive=up, negative=down."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            if x is not None and y is not None:
                pyautogui.moveTo(x, y)
            pyautogui.scroll(clicks)
            r = _ok({"clicks": clicks})
            _log_action("mouse_scroll", {"clicks": clicks, "x": x, "y": y}, r)
            return r
        except Exception as e:
            return _fail(f"mouse_scroll failed: {e}")

    def mouse_position(self) -> dict:
        """Get current mouse position."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pos = pyautogui.position()
            return _ok({"x": pos.x, "y": pos.y})
        except Exception as e:
            return _fail(f"mouse_position failed: {e}")

    def click_text(self, text) -> dict:
        """Find text on screen via OCR and click its center."""
        try:
            found = self.find_on_screen(text)
            if not found["success"]:
                return found
            x, y = found["result"]["x"], found["result"]["y"]
            return self.mouse_click(x=x, y=y)
        except Exception as e:
            return _fail(f"click_text failed: {e}")

    # -----------------------------------------------------------------------
    # 3. KEYBOARD
    # -----------------------------------------------------------------------

    def type_text(self, text, interval=0.02) -> dict:
        """Type text. Uses clipboard for non-ASCII characters."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            # Check if text is pure ASCII
            try:
                text.encode("ascii")
                pyautogui.typewrite(text, interval=interval)
            except UnicodeEncodeError:
                return self.type_unicode(text)
            r = _ok({"typed": text[:100]})
            _log_action("type_text", {"length": len(text)}, r)
            return r
        except Exception as e:
            return _fail(f"type_text failed: {e}")

    def press_key(self, key) -> dict:
        """Press and release a key (enter, tab, escape, f1-f12, etc.)."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.press(key)
            r = _ok({"key": key})
            _log_action("press_key", {"key": key}, r)
            return r
        except Exception as e:
            return _fail(f"press_key failed: {e}")

    def hotkey(self, *keys) -> dict:
        """Press key combination. E.g. hotkey('ctrl', 'c')."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.hotkey(*keys)
            r = _ok({"keys": list(keys)})
            _log_action("hotkey", {"keys": list(keys)}, r)
            return r
        except Exception as e:
            return _fail(f"hotkey failed: {e}")

    def key_down(self, key) -> dict:
        """Hold a key down."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.keyDown(key)
            r = _ok({"key": key, "state": "down"})
            _log_action("key_down", {"key": key}, r)
            return r
        except Exception as e:
            return _fail(f"key_down failed: {e}")

    def key_up(self, key) -> dict:
        """Release a held key."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.keyUp(key)
            r = _ok({"key": key, "state": "up"})
            _log_action("key_up", {"key": key}, r)
            return r
        except Exception as e:
            return _fail(f"key_up failed: {e}")

    def type_unicode(self, text) -> dict:
        """Type any unicode text via clipboard paste."""
        try:
            if not HAS_PYPERCLIP or not HAS_PYAUTOGUI:
                return _fail("pyperclip or pyautogui not available")
            # Preserve existing clipboard
            try:
                old_clip = pyperclip.paste()
            except Exception:
                old_clip = None
            pyperclip.copy(text)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.1)
            # Restore clipboard
            if old_clip is not None:
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass
            r = _ok({"typed_unicode": text[:100]})
            _log_action("type_unicode", {"length": len(text)}, r)
            return r
        except Exception as e:
            return _fail(f"type_unicode failed: {e}")

    # -----------------------------------------------------------------------
    # 4. CLIPBOARD
    # -----------------------------------------------------------------------

    def clipboard_copy(self, text) -> dict:
        """Copy text to clipboard."""
        try:
            if not HAS_PYPERCLIP:
                return _fail("pyperclip not available")
            pyperclip.copy(text)
            r = _ok({"copied_length": len(text)})
            _log_action("clipboard_copy", {"length": len(text)}, r)
            return r
        except Exception as e:
            return _fail(f"clipboard_copy failed: {e}")

    def clipboard_paste(self) -> dict:
        """Paste from clipboard (ctrl+v)."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.hotkey("ctrl", "v")
            r = _ok({"action": "pasted"})
            _log_action("clipboard_paste", {}, r)
            return r
        except Exception as e:
            return _fail(f"clipboard_paste failed: {e}")

    def clipboard_read(self) -> dict:
        """Read current clipboard contents."""
        try:
            if not HAS_PYPERCLIP:
                return _fail("pyperclip not available")
            content = pyperclip.paste()
            return _ok(content)
        except Exception as e:
            return _fail(f"clipboard_read failed: {e}")

    def clipboard_copy_selection(self) -> dict:
        """Copy current selection (ctrl+c) and return clipboard content."""
        try:
            if not HAS_PYAUTOGUI or not HAS_PYPERCLIP:
                return _fail("pyautogui or pyperclip not available")
            pyautogui.hotkey("ctrl", "c")
            time.sleep(0.15)
            content = pyperclip.paste()
            r = _ok(content)
            _log_action("clipboard_copy_selection", {}, r)
            return r
        except Exception as e:
            return _fail(f"clipboard_copy_selection failed: {e}")

    # -----------------------------------------------------------------------
    # 5. CAMERA
    # -----------------------------------------------------------------------

    def camera_capture(self, camera_index=0, save_path=None) -> dict:
        """Capture a photo from the webcam. Returns path to saved image."""
        try:
            if not HAS_CV2:
                return _fail("cv2 (opencv-python) not available")
            cap = cv2.VideoCapture(camera_index)
            if not cap.isOpened():
                return _fail(f"Cannot open camera index {camera_index}")
            # Allow camera to warm up
            for _ in range(5):
                cap.read()
            ret, frame = cap.read()
            cap.release()
            if not ret:
                return _fail("Failed to capture frame from camera")
            if save_path is None:
                save_path = str(_CAMERA_DIR / f"capture_{_ts()}.png")
            cv2.imwrite(save_path, frame)
            r = _ok(save_path)
            _log_action("camera_capture", {"camera_index": camera_index}, r)
            return r
        except Exception as e:
            return _fail(f"camera_capture failed: {e}")

    def camera_list(self) -> dict:
        """List available cameras by probing indices 0-4."""
        try:
            if not HAS_CV2:
                return _fail("cv2 (opencv-python) not available")
            cameras = []
            for i in range(5):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cameras.append({"index": i, "width": w, "height": h})
                    cap.release()
            return _ok(cameras)
        except Exception as e:
            return _fail(f"camera_list failed: {e}")

    def camera_read_text(self, camera_index=0) -> dict:
        """Capture from camera and OCR it."""
        try:
            if not HAS_CV2 or not HAS_TESSERACT:
                return _fail("cv2 or pytesseract not available")
            cap_result = self.camera_capture(camera_index=camera_index)
            if not cap_result["success"]:
                return cap_result
            img = cv2.imread(cap_result["result"])
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            text = pytesseract.image_to_string(gray)
            return _ok({"image_path": cap_result["result"], "text": text.strip()})
        except Exception as e:
            return _fail(f"camera_read_text failed: {e}")

    # -----------------------------------------------------------------------
    # 6. AUDIO & VOLUME
    # -----------------------------------------------------------------------

    def volume_get(self) -> dict:
        """Get current system volume (0-100)."""
        try:
            if not HAS_PYCAW:
                return _fail("pycaw not available")
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            level = volume.GetMasterVolumeLevelScalar()
            return _ok({"volume": round(level * 100)})
        except Exception as e:
            return _fail(f"volume_get failed: {e}")

    def volume_set(self, level) -> dict:
        """Set system volume (0-100)."""
        try:
            if not HAS_PYCAW:
                return _fail("pycaw not available")
            level = max(0, min(100, int(level)))
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            r = _ok({"volume": level})
            _log_action("volume_set", {"level": level}, r)
            return r
        except Exception as e:
            return _fail(f"volume_set failed: {e}")

    def volume_mute(self) -> dict:
        """Mute system audio."""
        try:
            if not HAS_PYCAW:
                return _fail("pycaw not available")
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMute(True, None)
            r = _ok({"muted": True})
            _log_action("volume_mute", {}, r)
            return r
        except Exception as e:
            return _fail(f"volume_mute failed: {e}")

    def volume_unmute(self) -> dict:
        """Unmute system audio."""
        try:
            if not HAS_PYCAW:
                return _fail("pycaw not available")
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = interface.QueryInterface(IAudioEndpointVolume)
            volume.SetMute(False, None)
            r = _ok({"muted": False})
            _log_action("volume_unmute", {}, r)
            return r
        except Exception as e:
            return _fail(f"volume_unmute failed: {e}")

    def play_sound(self, frequency=440, duration_ms=500) -> dict:
        """Play a tone at given frequency (Hz) for duration (ms)."""
        try:
            if not HAS_WINSOUND:
                return _fail("winsound not available")
            winsound.Beep(int(frequency), int(duration_ms))
            return _ok({"frequency": frequency, "duration_ms": duration_ms})
        except Exception as e:
            return _fail(f"play_sound failed: {e}")

    def speak(self, text) -> dict:
        """Text to speech via pyttsx3."""
        try:
            if not HAS_PYTTSX3:
                return _fail("pyttsx3 not available")
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            r = _ok({"spoken": text[:200]})
            _log_action("speak", {"length": len(text)}, r)
            return r
        except Exception as e:
            return _fail(f"speak failed: {e}")

    def listen(self, timeout=5) -> dict:
        """Listen via microphone and return recognized speech."""
        try:
            if not HAS_SPEECH:
                return _fail("speech_recognition not available")
            recognizer = sr.Recognizer()
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout)
            text = recognizer.recognize_google(audio)
            r = _ok({"text": text})
            _log_action("listen", {"timeout": timeout}, r)
            return r
        except sr.WaitTimeoutError:
            return _fail("Listening timed out - no speech detected")
        except sr.UnknownValueError:
            return _fail("Could not understand audio")
        except Exception as e:
            return _fail(f"listen failed: {e}")

    # -----------------------------------------------------------------------
    # 7. BLUETOOTH & WIFI
    # -----------------------------------------------------------------------

    def bluetooth_status(self) -> dict:
        """Check bluetooth adapter status."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-PnpDevice -Class Bluetooth | Select-Object Status, Name | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return _fail(f"PowerShell error: {result.stderr.strip()}")
            data = json.loads(result.stdout) if result.stdout.strip() else []
            if not isinstance(data, list):
                data = [data]
            return _ok(data)
        except Exception as e:
            return _fail(f"bluetooth_status failed: {e}")

    def bluetooth_devices(self) -> dict:
        """List paired bluetooth devices."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "Get-PnpDevice -Class Bluetooth | Where-Object {$_.Status -eq 'OK'} "
                 "| Select-Object Name, InstanceId, Status | ConvertTo-Json"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return _fail(f"PowerShell error: {result.stderr.strip()}")
            data = json.loads(result.stdout) if result.stdout.strip() else []
            if not isinstance(data, list):
                data = [data]
            return _ok(data)
        except Exception as e:
            return _fail(f"bluetooth_devices failed: {e}")

    def wifi_status(self) -> dict:
        """Get WiFi connection status."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return _fail(f"netsh error: {result.stderr.strip()}")
            lines = result.stdout.strip().split("\n")
            info = {}
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if key:
                        info[key] = val
            return _ok(info)
        except Exception as e:
            return _fail(f"wifi_status failed: {e}")

    def wifi_networks(self) -> dict:
        """List available WiFi networks."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "show", "networks", "mode=bssid"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return _fail(f"netsh error: {result.stderr.strip()}")
            networks = []
            current = {}
            for line in result.stdout.split("\n"):
                line = line.strip()
                if line.startswith("SSID") and "BSSID" not in line:
                    if current:
                        networks.append(current)
                    current = {}
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current["ssid"] = parts[1].strip()
                elif "Signal" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current["signal"] = parts[1].strip()
                elif "Authentication" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        current["authentication"] = parts[1].strip()
            if current:
                networks.append(current)
            return _ok(networks)
        except Exception as e:
            return _fail(f"wifi_networks failed: {e}")

    def wifi_connect(self, ssid, password=None) -> dict:
        """Connect to a WiFi network."""
        try:
            if password:
                # Create a temporary profile XML
                profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig><SSID><name>{ssid}</name></SSID></SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM><security>
        <authEncryption><authentication>WPA2PSK</authentication>
        <encryption>AES</encryption><useOneX>false</useOneX></authEncryption>
        <sharedKey><keyType>passPhrase</keyType>
        <protected>false</protected><keyMaterial>{password}</keyMaterial></sharedKey>
    </security></MSM>
</WLANProfile>"""
                profile_path = str(_STATE_DIR / "wifi_temp_profile.xml")
                with open(profile_path, "w") as f:
                    f.write(profile_xml)
                subprocess.run(
                    ["netsh", "wlan", "add", "profile", f"filename={profile_path}"],
                    capture_output=True, text=True, timeout=10
                )
                os.remove(profile_path)
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}"],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                return _fail(f"Connection failed: {result.stderr.strip()}")
            r = _ok({"ssid": ssid, "output": result.stdout.strip()})
            _log_action("wifi_connect", {"ssid": ssid}, r)
            return r
        except Exception as e:
            return _fail(f"wifi_connect failed: {e}")

    def wifi_disconnect(self) -> dict:
        """Disconnect from WiFi."""
        try:
            result = subprocess.run(
                ["netsh", "wlan", "disconnect"],
                capture_output=True, text=True, timeout=10
            )
            r = _ok({"output": result.stdout.strip()})
            _log_action("wifi_disconnect", {}, r)
            return r
        except Exception as e:
            return _fail(f"wifi_disconnect failed: {e}")

    # -----------------------------------------------------------------------
    # 8. WINDOW MANAGEMENT
    # -----------------------------------------------------------------------

    def _enum_windows(self):
        """Internal: enumerate all visible windows with hwnd and title."""
        if not HAS_CTYPES:
            return []
        windows = []
        user32 = ctypes.windll.user32

        def callback(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                length = user32.GetWindowTextLengthW(hwnd)
                if length > 0:
                    buf = ctypes.create_unicode_buffer(length + 1)
                    user32.GetWindowTextW(hwnd, buf, length + 1)
                    title = buf.value
                    if title:
                        rect = ctypes.wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        windows.append({
                            "hwnd": hwnd,
                            "title": title,
                            "x": rect.left, "y": rect.top,
                            "width": rect.right - rect.left,
                            "height": rect.bottom - rect.top,
                        })
            return True

        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(WNDENUMPROC(callback), 0)
        return windows

    def _find_window(self, title_pattern):
        """Internal: find first window matching title pattern (case-insensitive)."""
        pattern = title_pattern.lower()
        for w in self._enum_windows():
            if pattern in w["title"].lower():
                return w
        return None

    def window_list(self) -> dict:
        """List all open windows with titles and positions."""
        try:
            windows = self._enum_windows()
            # Strip hwnd from output (not JSON-serializable as-is in some contexts)
            result = [{"title": w["title"], "x": w["x"], "y": w["y"],
                        "width": w["width"], "height": w["height"]} for w in windows]
            return _ok(result)
        except Exception as e:
            return _fail(f"window_list failed: {e}")

    def window_focus(self, title_pattern) -> dict:
        """Bring window to front by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            user32 = ctypes.windll.user32
            SW_RESTORE = 9
            user32.ShowWindow(w["hwnd"], SW_RESTORE)
            user32.SetForegroundWindow(w["hwnd"])
            r = _ok({"title": w["title"]})
            _log_action("window_focus", {"pattern": title_pattern}, r)
            return r
        except Exception as e:
            return _fail(f"window_focus failed: {e}")

    def window_minimize(self, title_pattern) -> dict:
        """Minimize a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            ctypes.windll.user32.ShowWindow(w["hwnd"], 6)  # SW_MINIMIZE
            r = _ok({"title": w["title"]})
            _log_action("window_minimize", {"pattern": title_pattern}, r)
            return r
        except Exception as e:
            return _fail(f"window_minimize failed: {e}")

    def window_maximize(self, title_pattern) -> dict:
        """Maximize a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            ctypes.windll.user32.ShowWindow(w["hwnd"], 3)  # SW_MAXIMIZE
            r = _ok({"title": w["title"]})
            _log_action("window_maximize", {"pattern": title_pattern}, r)
            return r
        except Exception as e:
            return _fail(f"window_maximize failed: {e}")

    def window_restore(self, title_pattern) -> dict:
        """Restore a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            ctypes.windll.user32.ShowWindow(w["hwnd"], 9)  # SW_RESTORE
            return _ok({"title": w["title"]})
        except Exception as e:
            return _fail(f"window_restore failed: {e}")

    def window_close(self, title_pattern) -> dict:
        """Close a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            WM_CLOSE = 0x0010
            ctypes.windll.user32.PostMessageW(w["hwnd"], WM_CLOSE, 0, 0)
            r = _ok({"title": w["title"]})
            _log_action("window_close", {"pattern": title_pattern}, r)
            return r
        except Exception as e:
            return _fail(f"window_close failed: {e}")

    def window_resize(self, title_pattern, width, height) -> dict:
        """Resize a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            ctypes.windll.user32.MoveWindow(w["hwnd"], w["x"], w["y"], width, height, True)
            r = _ok({"title": w["title"], "width": width, "height": height})
            _log_action("window_resize", {"pattern": title_pattern, "w": width, "h": height}, r)
            return r
        except Exception as e:
            return _fail(f"window_resize failed: {e}")

    def window_move(self, title_pattern, x, y) -> dict:
        """Move a window by title pattern."""
        try:
            w = self._find_window(title_pattern)
            if not w:
                return _fail(f"No window matching '{title_pattern}'")
            ctypes.windll.user32.MoveWindow(w["hwnd"], x, y, w["width"], w["height"], True)
            r = _ok({"title": w["title"], "x": x, "y": y})
            _log_action("window_move", {"pattern": title_pattern, "x": x, "y": y}, r)
            return r
        except Exception as e:
            return _fail(f"window_move failed: {e}")

    def window_get_active(self) -> dict:
        """Get the currently active/focused window title."""
        try:
            if not HAS_CTYPES:
                return _fail("ctypes not available")
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return _ok({"title": buf.value, "hwnd": hwnd})
        except Exception as e:
            return _fail(f"window_get_active failed: {e}")

    # -----------------------------------------------------------------------
    # 9. DISPLAY & POWER
    # -----------------------------------------------------------------------

    def brightness_get(self) -> dict:
        """Get screen brightness (0-100)."""
        try:
            result = subprocess.run(
                ["powershell", "-Command",
                 "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return _fail(f"PowerShell error: {result.stderr.strip()}")
            level = int(result.stdout.strip())
            return _ok({"brightness": level})
        except Exception as e:
            return _fail(f"brightness_get failed: {e}")

    def brightness_set(self, level) -> dict:
        """Set screen brightness (0-100)."""
        try:
            level = max(0, min(100, int(level)))
            result = subprocess.run(
                ["powershell", "-Command",
                 f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
                 f".WmiSetBrightness(1, {level})"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                return _fail(f"PowerShell error: {result.stderr.strip()}")
            r = _ok({"brightness": level})
            _log_action("brightness_set", {"level": level}, r)
            return r
        except Exception as e:
            return _fail(f"brightness_set failed: {e}")

    def battery_status(self) -> dict:
        """Get battery level and charging status."""
        try:
            if not HAS_PSUTIL:
                return _fail("psutil not available")
            battery = psutil.sensors_battery()
            if battery is None:
                return _fail("No battery detected (desktop PC?)")
            return _ok({
                "percent": battery.percent,
                "plugged_in": battery.power_plugged,
                "seconds_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
                "time_left": str(datetime.timedelta(seconds=battery.secsleft))
                             if battery.secsleft not in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN)
                             else "unlimited" if battery.secsleft == psutil.POWER_TIME_UNLIMITED else "unknown",
            })
        except Exception as e:
            return _fail(f"battery_status failed: {e}")

    def lock_screen(self) -> dict:
        """Lock the screen."""
        try:
            if not HAS_CTYPES:
                return _fail("ctypes not available")
            ctypes.windll.user32.LockWorkStation()
            r = _ok({"action": "screen_locked"})
            _log_action("lock_screen", {}, r)
            return r
        except Exception as e:
            return _fail(f"lock_screen failed: {e}")

    def sleep_computer(self) -> dict:
        """Put computer to sleep."""
        try:
            result = subprocess.run(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                capture_output=True, text=True, timeout=10
            )
            r = _ok({"action": "sleep_initiated"})
            _log_action("sleep_computer", {}, r)
            return r
        except Exception as e:
            return _fail(f"sleep_computer failed: {e}")

    # -----------------------------------------------------------------------
    # 10. FILE OPERATIONS
    # -----------------------------------------------------------------------

    def open_file(self, path) -> dict:
        """Open a file with its default application."""
        try:
            path = os.path.abspath(path)
            if not os.path.exists(path):
                return _fail(f"File not found: {path}")
            os.startfile(path)
            r = _ok({"opened": path})
            _log_action("open_file", {"path": path}, r)
            return r
        except Exception as e:
            return _fail(f"open_file failed: {e}")

    def open_folder(self, path) -> dict:
        """Open a folder in Explorer."""
        try:
            path = os.path.abspath(path)
            if not os.path.isdir(path):
                return _fail(f"Directory not found: {path}")
            subprocess.Popen(["explorer", path])
            r = _ok({"opened": path})
            _log_action("open_folder", {"path": path}, r)
            return r
        except Exception as e:
            return _fail(f"open_folder failed: {e}")

    def search_files(self, query, directory=None) -> dict:
        """Search for files by name pattern. query supports glob wildcards."""
        try:
            if directory is None:
                directory = os.path.expanduser("~")
            directory = os.path.abspath(directory)
            if not os.path.isdir(directory):
                return _fail(f"Directory not found: {directory}")
            matches = []
            pattern = os.path.join(directory, "**", query)
            for path in glob_mod.iglob(pattern, recursive=True):
                matches.append(path)
                if len(matches) >= 100:
                    break
            return _ok({"query": query, "directory": directory, "count": len(matches), "files": matches})
        except Exception as e:
            return _fail(f"search_files failed: {e}")

    def get_downloads(self, limit=10) -> dict:
        """List recent downloads sorted by modification time."""
        try:
            dl_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            if not os.path.isdir(dl_dir):
                return _fail("Downloads directory not found")
            files = []
            for entry in os.scandir(dl_dir):
                if entry.is_file():
                    stat = entry.stat()
                    files.append({
                        "name": entry.name,
                        "path": entry.path,
                        "size_bytes": stat.st_size,
                        "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
            files.sort(key=lambda f: f["modified"], reverse=True)
            return _ok(files[:limit])
        except Exception as e:
            return _fail(f"get_downloads failed: {e}")

    def get_desktop_files(self) -> dict:
        """List files on Desktop."""
        try:
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            if not os.path.isdir(desktop):
                return _fail("Desktop directory not found")
            files = []
            for entry in os.scandir(desktop):
                files.append({
                    "name": entry.name,
                    "path": entry.path,
                    "is_dir": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else 0,
                })
            return _ok(files)
        except Exception as e:
            return _fail(f"get_desktop_files failed: {e}")

    # -----------------------------------------------------------------------
    # 11. NOTIFICATIONS & DIALOGS
    # -----------------------------------------------------------------------

    def notify(self, title, message) -> dict:
        """Show a Windows toast notification."""
        try:
            ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$textNodes = $template.GetElementsByTagName('text')
$textNodes.Item(0).AppendChild($template.CreateTextNode('{title.replace("'", "''")}')) > $null
$textNodes.Item(1).AppendChild($template.CreateTextNode('{message.replace("'", "''")}')) > $null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
$notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('Aureon')
$notifier.Show($toast)
"""
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                # Fallback to MessageBox
                return self.alert(f"{title}\n\n{message}", title="Aureon Notification")
            r = _ok({"title": title, "message": message})
            _log_action("notify", {"title": title}, r)
            return r
        except Exception as e:
            # Fallback
            return self.alert(f"{title}\n\n{message}", title="Aureon Notification")

    def alert(self, message, title="Aureon") -> dict:
        """Show a popup alert dialog (MB_ICONINFORMATION)."""
        try:
            if not HAS_CTYPES:
                return _fail("ctypes not available")
            MB_OK = 0x00000000
            MB_ICONINFORMATION = 0x00000040
            ctypes.windll.user32.MessageBoxW(0, str(message), str(title),
                                             MB_OK | MB_ICONINFORMATION)
            r = _ok({"shown": True})
            _log_action("alert", {"title": title}, r)
            return r
        except Exception as e:
            return _fail(f"alert failed: {e}")

    def ask_yes_no(self, question, title="Aureon") -> dict:
        """Show a yes/no dialog. Returns 'yes' or 'no'."""
        try:
            if not HAS_CTYPES:
                return _fail("ctypes not available")
            MB_YESNO = 0x00000004
            MB_ICONQUESTION = 0x00000020
            IDYES = 6
            response = ctypes.windll.user32.MessageBoxW(0, str(question), str(title),
                                                        MB_YESNO | MB_ICONQUESTION)
            answer = "yes" if response == IDYES else "no"
            r = _ok({"answer": answer})
            _log_action("ask_yes_no", {"question": question[:100]}, r)
            return r
        except Exception as e:
            return _fail(f"ask_yes_no failed: {e}")

    # -----------------------------------------------------------------------
    # 12. SYSTEM CONTROL
    # -----------------------------------------------------------------------

    def installed_apps(self) -> dict:
        """List installed applications from the Windows registry."""
        try:
            if not HAS_WINREG:
                return _fail("winreg not available")
            apps = []
            paths = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
            ]
            for reg_path in paths:
                for hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                    try:
                        key = winreg.OpenKey(hive, reg_path)
                    except FileNotFoundError:
                        continue
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey = winreg.OpenKey(key, subkey_name)
                            try:
                                name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                            except FileNotFoundError:
                                continue
                            version = ""
                            try:
                                version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                            except FileNotFoundError:
                                pass
                            publisher = ""
                            try:
                                publisher = winreg.QueryValueEx(subkey, "Publisher")[0]
                            except FileNotFoundError:
                                pass
                            apps.append({"name": name, "version": version, "publisher": publisher})
                        except Exception:
                            continue
                    winreg.CloseKey(key)
            # Deduplicate by name
            seen = set()
            unique = []
            for app in apps:
                if app["name"] not in seen:
                    seen.add(app["name"])
                    unique.append(app)
            unique.sort(key=lambda a: a["name"].lower())
            return _ok(unique)
        except Exception as e:
            return _fail(f"installed_apps failed: {e}")

    def start_menu_search(self, query) -> dict:
        """Open Start menu and type a search query."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.press("win")
            time.sleep(0.5)
            pyautogui.typewrite(query, interval=0.03)
            r = _ok({"query": query})
            _log_action("start_menu_search", {"query": query}, r)
            return r
        except Exception as e:
            return _fail(f"start_menu_search failed: {e}")

    def task_manager(self) -> dict:
        """Open Task Manager."""
        try:
            if not HAS_PYAUTOGUI:
                return _fail("pyautogui not available")
            pyautogui.hotkey("ctrl", "shift", "escape")
            r = _ok({"action": "task_manager_opened"})
            _log_action("task_manager", {}, r)
            return r
        except Exception as e:
            return _fail(f"task_manager failed: {e}")

    def kill_process(self, name_or_pid) -> dict:
        """Kill a process by name or PID."""
        try:
            if isinstance(name_or_pid, int) or str(name_or_pid).isdigit():
                pid = int(name_or_pid)
                if HAS_PSUTIL:
                    proc = psutil.Process(pid)
                    proc_name = proc.name()
                    proc.kill()
                else:
                    proc_name = str(pid)
                    subprocess.run(["taskkill", "/PID", str(pid), "/F"],
                                   capture_output=True, text=True, timeout=10)
                r = _ok({"killed": proc_name, "pid": pid})
            else:
                name = str(name_or_pid)
                result = subprocess.run(
                    ["taskkill", "/IM", name, "/F"],
                    capture_output=True, text=True, timeout=10
                )
                r = _ok({"killed": name, "output": result.stdout.strip()})
            _log_action("kill_process", {"target": str(name_or_pid)}, r)
            return r
        except Exception as e:
            return _fail(f"kill_process failed: {e}")

    def set_wallpaper(self, image_path) -> dict:
        """Set desktop wallpaper."""
        try:
            if not HAS_CTYPES:
                return _fail("ctypes not available")
            image_path = os.path.abspath(image_path)
            if not os.path.exists(image_path):
                return _fail(f"Image not found: {image_path}")
            SPI_SETDESKWALLPAPER = 0x0014
            SPIF_UPDATEINIFILE = 0x01
            SPIF_SENDCHANGE = 0x02
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETDESKWALLPAPER, 0, image_path,
                SPIF_UPDATEINIFILE | SPIF_SENDCHANGE
            )
            r = _ok({"wallpaper": image_path})
            _log_action("set_wallpaper", {"path": image_path}, r)
            return r
        except Exception as e:
            return _fail(f"set_wallpaper failed: {e}")

    # -----------------------------------------------------------------------
    # INTROSPECTION
    # -----------------------------------------------------------------------

    def get_all_capabilities(self) -> dict:
        """Return a list of all available methods with descriptions and availability."""
        capabilities = []
        for name in sorted(dir(self)):
            if name.startswith("_"):
                continue
            method = getattr(self, name)
            if not callable(method):
                continue
            doc = (method.__doc__ or "").strip().split("\n")[0]
            capabilities.append({"method": name, "description": doc})
        return _ok(capabilities)

    def get_library_status(self) -> dict:
        """Return availability status of all hardware libraries."""
        return _ok({
            "pyautogui": HAS_PYAUTOGUI,
            "cv2": HAS_CV2,
            "PIL": HAS_PIL,
            "pytesseract": HAS_TESSERACT,
            "pyttsx3": HAS_PYTTSX3,
            "speech_recognition": HAS_SPEECH,
            "pyperclip": HAS_PYPERCLIP,
            "psutil": HAS_PSUTIL,
            "ctypes": HAS_CTYPES,
            "winsound": HAS_WINSOUND,
            "winreg": HAS_WINREG,
            "keyboard": HAS_KEYBOARD,
            "mouse": HAS_MOUSE,
            "screeninfo": HAS_SCREENINFO,
            "pycaw": HAS_PYCAW,
            "sounddevice": HAS_SOUNDDEVICE,
            "pyaudio": HAS_PYAUDIO,
        })


# ---------------------------------------------------------------------------
# Module-level convenience instance
# ---------------------------------------------------------------------------
laptop = LaptopControl()


if __name__ == "__main__":
    ctrl = LaptopControl()
    print("=== Aureon Laptop Control ===")
    print()

    # Show library availability
    status = ctrl.get_library_status()
    print("Library Status:")
    for lib, available in status["result"].items():
        marker = "OK" if available else "MISSING"
        print(f"  {lib:20s} {marker}")
    print()

    # Show all capabilities
    caps = ctrl.get_all_capabilities()
    print(f"Total capabilities: {len(caps['result'])}")
    for cap in caps["result"]:
        print(f"  {cap['method']:30s}  {cap['description']}")
    print()

    # Quick tests
    print("Screen size:", ctrl.get_screen_size())
    print("Mouse pos: ", ctrl.mouse_position())
    print("Battery:   ", ctrl.battery_status())
