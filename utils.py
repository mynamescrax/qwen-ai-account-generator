import time
import base64
import logging
import random
import math
import threading
import requests
from pathlib import Path

logger = logging.getLogger(__name__)

SELECTORS = {
    'continue_with_email': 'button:has-text("Log in with Email")',
    'continue_with_google': 'button:has-text("Continue with Google")',
    'continue_with_github': 'button:has-text("Continue with Github")',
    'skip_for_now': 'button:has-text("Skip for now")',
    'email_input': 'input[name="email"]',
    'password_input': 'input[type="password"]',
    'confirm_password_input': 'input[name="checkPassword"]',
    'name_input': 'input[name="username"]',
    'signup_button': 'button:has-text("Sign up")',
    'create_account_button': 'button:has-text("Create Account")',
    'signin_button': 'button:has-text("Sign in")',
    'forgot_password': 'a:has-text("Forget password"), button:has-text("Forget password")',
    'policy_checkbox': '.qwenchat-auth-pc-register-policy input[type="checkbox"], .qwenchat-auth-pc-register-policy',
    'slider': '#aliyunCaptcha-sliding-slider',
    'shadow_image': '#aliyunCaptcha-puzzle',
    'background_image': '#aliyunCaptcha-img',
    'question': '#aliyunCaptcha-question',
    'verify_param': '#aliyunCaptcha-verify-param',
    'refresh': '#aliyunCaptcha-btn-refresh',
    'close': '#aliyunCaptcha-btn-close',
    'success': '.aliyunCaptcha-verify-success',
    'error': '.aliyunCaptcha-verify-error',
    'captcha_start': '#aliyunCaptcha-captcha-text',
    'sliding_track': '#aliyunCaptcha-sliding-track',
}


def fetch_image(url, referer='https://chat.qwen.ai/'):
    if url.startswith('data:image'):
        try:
            return base64.b64decode(url.split(',')[1])
        except Exception:
            return None
    try:
        r = requests.get(url, timeout=5, headers={'Referer': referer})
        return r.content if r.status_code == 200 else None
    except Exception:
        return None


def save_debug_images(shadow_bytes, bg_bytes, prefix="captcha"):
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    timestamp = int(time.time())
    shadow_path = output_dir / f"{prefix}_shadow_{timestamp}.png"
    bg_path = output_dir / f"{prefix}_bg_{timestamp}.png"

    with open(shadow_path, 'wb') as f:
        f.write(shadow_bytes)
    with open(bg_path, 'wb') as f:
        f.write(bg_bytes)

    return str(shadow_path), str(bg_path)


def take_screenshot(page, name="screenshot"):
    screenshot_dir = Path('output')
    screenshot_dir.mkdir(exist_ok=True)

    timestamp = int(time.time())
    path = screenshot_dir / f"{name}_{timestamp}.png"
    page.screenshot(path=str(path))
    return str(path)


class TimingTracker:

    def __init__(self):
        self.timings = {}
        self.current = {}
        self._lock = threading.Lock()

    def start(self, name):
        with self._lock:
            self.current[name] = time.time()

    def end(self, name):
        with self._lock:
            if name in self.current:
                elapsed = time.time() - self.current[name]
                self.timings[name] = elapsed
                del self.current[name]
                return elapsed
            return None

    def summary(self):
        with self._lock:
            if not self.timings:
                return "No timings recorded"

            lines = ["\nTiming Summary:"]
            total = 0
            for name, elapsed in self.timings.items():
                lines.append(f"  {name}: {elapsed*1000:.1f}ms")
                total += elapsed
            lines.append(f"  ")
            lines.append(f"  TOTAL: {total*1000:.1f}ms")
            return "\n".join(lines)


timing = TimingTracker()
