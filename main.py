import time
import random
import logging
import sys
import re
import html
import threading
import requests
from pathlib import Path
from camoufox.sync_api import Camoufox


from utils import SELECTORS, timing
from captcha_solver import CaptchaSolver
from config import CONFIG

_file_lock = threading.Lock()
_success_count = 0
_verify_count = 0
_counter_lock = threading.Lock()

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))

root_logger.handlers = [console_handler]

logger = logging.getLogger(__name__)


FIRST_NAMES = [
    'James', 'Mary', 'Robert', 'Patricia', 'John', 'Jennifer', 'Michael', 'Linda',
    'David', 'Elizabeth', 'William', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
    'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Margaret',
    'Matthew', 'Lisa', 'Anthony', 'Betty', 'Mark', 'Sandra', 'Donald', 'Ashley',
    'Steven', 'Kimberly', 'Paul', 'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle',
    'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Dorothy', 'George', 'Melissa',
    'Edward', 'Deborah', 'Ronald', 'Stephanie', 'Timothy', 'Rebecca', 'Jason', 'Sharon',
    'Jeffrey', 'Laura', 'Ryan', 'Cynthia', 'Jacob', 'Kathleen', 'Gary', 'Amy',
    'Nicholas', 'Shirley', 'Eric', 'Angela', 'Jonathan', 'Helen', 'Stephen', 'Anna',
    'Larry', 'Brenda', 'Justin', 'Pamela', 'Scott', 'Nicole', 'Brandon', 'Emma',
    'Benjamin', 'Samantha', 'Samuel', 'Katherine', 'Gregory', 'Christine', 'Frank', 'Debra',
    'Alexander', 'Rachel', 'Raymond', 'Catherine', 'Patrick', 'Carolyn', 'Jack', 'Janet',
    'Dennis', 'Ruth', 'Jerry', 'Maria', 'Tyler', 'Heather', 'Aaron', 'Diane',
    'Henry', 'Virginia', 'Douglas', 'Julie', 'Jose', 'Joyce', 'Peter', 'Victoria',
    'Adam', 'Olivia', 'Nathan', 'Kelly', 'Zachary', 'Christina', 'Walter', 'Lauren',
    'Kyle', 'Joan', 'Harold', 'Evelyn', 'Carl', 'Judith', 'Arthur', 'Andrea',
    'Gerald', 'Hannah', 'Roger', 'Megan', 'Keith', 'Cheryl', 'Jeremy', 'Jacqueline',
    'Terry', 'Martha', 'Lawrence', 'Gloria', 'Sean', 'Teresa', 'Christian', 'Ann',
    'Ethan', 'Sara', 'Austin', 'Madison', 'Joe', 'Frances', 'Albert', 'Kathryn',
    'Jesse', 'Janice', 'Willie', 'Jean', 'Billy', 'Abigail', 'Bryan', 'Alice',
    'Bruce', 'Judy', 'Jordan', 'Sophia', 'Dylan', 'Grace', 'Noah', 'Denise',
    'Alan', 'Amber', 'Ralph', 'Doris', 'Gabriel', 'Marilyn', 'Logan', 'Danielle',
    'Wayne', 'Beverly', 'Vincent', 'Isabella', 'Eugene', 'Theresa', 'Randy', 'Diana',
    'Harry', 'Natalie', 'Philip', 'Brittany', 'Louis', 'Charlotte', 'Bobby', 'Marie',
    'Johnny', 'Kayla', 'Mason', 'Alexis', 'Eduardo', 'Lori',
]

LAST_NAMES = [
    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
    'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
    'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
    'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
    'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
    'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
    'Mitchell', 'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz',
    'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris', 'Morales',
    'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Morgan', 'Cooper', 'Peterson',
    'Bailey', 'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim', 'Cox', 'Ward',
    'Richardson', 'Watson', 'Brooks', 'Chavez', 'Wood', 'James', 'Bennett', 'Gray',
    'Mendoza', 'Ruiz', 'Hughes', 'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel',
    'Myers', 'Long', 'Ross', 'Foster', 'Jimenez', 'Powell', 'Jenkins', 'Perry',
    'Russell', 'Sullivan', 'Bell', 'Coleman', 'Butler', 'Henderson', 'Barnes', 'Gonzales',
    'Fisher', 'Vasquez', 'Simmons', 'Romero', 'Jordan', 'Patterson', 'Alexander', 'Hamilton',
    'Graham', 'Reynolds', 'Griffin', 'Wallace', 'Moreno', 'West', 'Cole', 'Hayes',
    'Bryant', 'Herrera', 'Gibson', 'Ellis', 'Tran', 'Medina', 'Aguilar', 'Stevens',
    'Murray', 'Ford', 'Castro', 'Marshall', 'Owens', 'Harrison', 'Fernandez', 'Mcdonald',
    'Woods', 'Washington', 'Kennedy', 'Wells', 'Vargas', 'Henry', 'Chen', 'Freeman',
    'Webb', 'Tucker', 'Guzman', 'Burns', 'Crawford', 'Olson', 'Simpson', 'Porter',
    'Hunter', 'Gordon', 'Mendez', 'Silva', 'Shaw', 'Snyder', 'Mills', 'Pearson',
]


def generate_human_name() -> str:
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    return f"{first} {last}"


JUNK_RESOURCES = [
    'fonts.gstatic.com',
    'fonts.googleapis.com',
    'google-analytics.com',
    'googletagmanager.com',
    'googleadservices.com',
    'doubleclick.net',
    'facebook.net',
    '.fbcdn.net',
    'mc.yandex',
    'hotjar.com',
    'clarity.ms',
    'mixpanel',
    'sentry.io',
    'play.google.com/log',
]


def _route_handler(route):
    url = route.request.url.lower()
    if any(j in url for j in JUNK_RESOURCES):
        route.abort()
    else:
        route.continue_()


class Worker:

    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.lock = threading.RLock()
        self._fox = None
        self.browser = None
        self._owner_tid = None

    def _check_thread(self):
        tid = threading.get_ident()
        if self._owner_tid is not None and self._owner_tid != tid:
            raise RuntimeError(
                f"Worker {self.worker_id}: Camoufox browser is locked to thread "
                f"{self._owner_tid} but accessed from thread {tid}. "
                "Each worker thread must own its own browser."
            )

    def ensure_browser(self):
        with self.lock:
            self._check_thread()
            if self.browser is None:
                logger.info(f"[w{self.worker_id}] launching browser...")
                self._owner_tid = threading.get_ident()
                self._fox = Camoufox(
                    headless=CONFIG.get('headless', False),
                    os='windows',
                    locale='en-US',
                )
                self.browser = self._fox.__enter__()
            return self.browser

    def close(self):
        with self.lock:
            if self._fox is not None:
                try:
                    self._fox.__exit__(None, None, None)
                except Exception:
                    pass
                self.browser = None
                self._fox = None


def extract_token(page) -> str:
    try:
        token = page.evaluate("""
            () => {
                const cookies = document.cookie.split(';');
                for (const c of cookies) {
                    const [name, ...rest] = c.trim().split('=');
                    if (name === 'token') {
                        const val = rest.join('=');
                        if (val && val.length > 50) return val;
                    }
                }
                const keys = ['token', 'active_token', 'access_token', 'auth_token', 'jwt', 'accessToken'];
                for (const key of keys) {
                    let val = localStorage.getItem(key);
                    if (val && val.length > 50) return val;
                    val = sessionStorage.getItem(key);
                    if (val && val.length > 50) return val;
                }
                for (let i = 0; i < localStorage.length; i++) {
                    const key = localStorage.key(i);
                    const val = localStorage.getItem(key);
                    if (val && val.length > 80 && val.split('.').length === 3) return val;
                }
                return null;
            }
        """)
        if token and len(token) > 50:
            return token
    except Exception:
        pass

    try:
        cookies = page.context.cookies('https://chat.qwen.ai')
        for c in cookies:
            if c['name'] == 'token' and c['value'] and len(c['value']) > 50:
                return c['value']
    except Exception:
        pass

    return None


def _wait_for_token(page, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        token = extract_token(page)
        if token and len(token) > 50:
            return token
        time.sleep(1)
    return None


class TempMailBase:

    name = 'base'
    PASSWORD = 'Passw0rd!123'

    LINK_PATTERNS = [
        r'https://chat\.qwen\.ai/api/v1/auths/activate\?[^\s"\'<>]+',
        r'https://chat\.qwen\.ai/auth/verify_email\?[^\s"\'<>]+',
        r'https://chat\.qwen\.ai/verify[^\s"\'<>]+',
        r'https://[^\s"\'<>]*qwen[^\s"\'<>]*activat[^\s"\'<>]+',
        r'https://[^\s"\'<>]*qwen[^\s"\'<>]*verify[^\s"\'<>]+',
    ]

    def __init__(self):
        self.email = None
        self.token = None
        self.ready = threading.Event()
        self.session = requests.Session()
        self._seen_log = set()

    def _log_new_email(self, msg_id, message=None):
        if msg_id in self._seen_log:
            return
        self._seen_log.add(msg_id)
        if message:
            logger.info(message)

    def create_account(self):
        raise NotImplementedError

    def fetch_messages(self):
        raise NotImplementedError

    def get_verification_link(self, timeout=60):
        logger.info(f"Waiting for verification email ({self.name}, timeout: {timeout}s)...")

        start_time = time.time()
        seen_ids = set()
        poll_count = 0
        last_error = ''
        while time.time() - start_time < timeout:
            poll_count += 1
            try:
                messages = self.fetch_messages()
            except Exception as e:
                if poll_count % 5 == 1 or str(e) != last_error:
                    logger.warning(f"Poll #{poll_count}: error {e}")
                last_error = str(e)
                time.sleep(2)
                continue

            if not messages:
                time.sleep(2)
                continue

            logger.info(f"Poll #{poll_count}: got {len(messages)} message(s) from {self.name}")

            for msg_id, text_content, html_content in messages:
                if not msg_id or msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                combined = (html_content or '') + ' ' + (text_content or '')

                for pattern in self.LINK_PATTERNS:
                    matches = re.findall(pattern, combined)
                    if matches:
                        link = html.unescape(matches[0])
                        logger.info(f"Verification link found: {link[:80]}...")
                        return link

                if any(w in combined.lower() for w in ('verify', 'activation', 'activate', 'confirm', 'qwen')):
                    logger.warning(
                        f"  Verification email found but no link extracted "
                        f"(html len={len(html_content or '')}, text len={len(text_content or '')})"
                    )
                    if text_content:
                        logger.warning(f"  Text: {(text_content or '')[:300]}")
                    if html_content:
                        logger.warning(f"  HTML: {(html_content or '')[:300]}")
                else:
                    logger.info("  Non-verification email, skipping")

            time.sleep(2)

        logger.warning(f"Timeout waiting for verification email ({self.name})")
        return None


class MailTmLike(TempMailBase):

    name = 'mailtm'
    BASE = 'https://api.mail.tm'

    def create_account(self):
        for attempt in range(5):
            try:
                resp = self.session.get(f'{self.BASE}/domains', timeout=20)
                if resp.status_code == 429:
                    wait = 3 + attempt * 3 + random.uniform(0, 2)
                    logger.warning(f"{self.name} domains rate limited, waiting {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    logger.warning(f"{self.name} offline (GET /domains {resp.status_code}), skipping")
                    return False
                domains = resp.json().get('hydra:member', [])
                if not domains:
                    continue
                domain = domains[0]['domain']

                addr = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=12))
                self.email = f'{addr}@{domain}'

                resp = self.session.post(f'{self.BASE}/accounts', json={
                    'address': self.email,
                    'password': self.PASSWORD,
                }, timeout=20)
                if resp.status_code in [200, 201]:
                    logger.info(f"Created {self.name} account: {self.email}")
                    return self._login()
                elif resp.status_code == 422:
                    logger.warning("Account may already exist, trying login...")
                    return self._login()
                elif resp.status_code == 429:
                    wait = 5 + attempt * 3 + random.uniform(0, 3)
                    logger.warning(f"{self.name} create rate limited, waiting {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                else:
                    logger.warning(f"{self.name} account create failed: {resp.status_code}, skipping")
                    return False
            except Exception as e:
                logger.error(f"Error creating {self.name} account: {e}")
                return False
        return False

    def _login(self):
        try:
            resp = self.session.post(f'{self.BASE}/token', json={
                'address': self.email,
                'password': self.PASSWORD,
            }, timeout=20)
            if resp.status_code in [200, 201]:
                self.token = resp.json().get('token')
                if self.token:
                    self.session.headers['Authorization'] = f'Bearer {self.token}'
                    self.ready.set()
                    logger.info(f"Logged into {self.name} as {self.email}")
                    return True
            logger.warning(f"{self.name} login failed: {resp.status_code}")
            return False
        except Exception as e:
            logger.error(f"{self.name} login error: {e}")
            return False

    def fetch_messages(self):
        resp = self.session.get(f'{self.BASE}/messages', timeout=20)
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        messages = data.get('hydra:member', []) if isinstance(data, dict) else []

        out = []
        for msg_summary in messages:
            msg_id = msg_summary.get('id', '')
            subject = msg_summary.get('subject', '') or ''
            sender = msg_summary.get('from', '') or ''
            self._log_new_email(msg_id, f"  New email: subject='{subject}' from='{sender}'")

            try:
                full_msg = self.session.get(f'{self.BASE}/messages/{msg_id}', timeout=20).json()
            except Exception as e:
                logger.warning(f"  Error fetching message: {e}")
                continue

            text_content = full_msg.get('text', '') or full_msg.get('body', '') or ''
            html_content = full_msg.get('html', '')
            if isinstance(html_content, list):
                html_content = ' '.join(html_content)
            out.append((msg_id, subject + '\n' + text_content, html_content))
        return out


class DrafterMail(TempMailBase):

    name = 'drafter'
    BASE = 'https://mail.drafterplus.nl'

    def create_account(self):
        for attempt in range(5):
            try:
                resp = self.session.post(
                    f'{self.BASE}/api/new',
                    json={'domain': 'drafterplus.nl'},
                    timeout=20,
                )
                if resp.status_code == 429:
                    wait = 2 + attempt * 2
                    logger.warning(f"drafter rate limited, waiting {wait:.0f}s...")
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    logger.warning(f"drafter offline (/api/new {resp.status_code}), skipping")
                    return False
                data = resp.json()
                if not data.get('ok'):
                    err = data.get('error', 'unknown')
                    if err == 'rate_limited':
                        wait = 2 + attempt * 2
                        logger.warning(f"drafter rate limited, waiting {wait:.0f}s...")
                        time.sleep(wait)
                        continue
                    logger.warning(f"drafter create failed: {err}, skipping")
                    return False
                self.email = data.get('email')
                self.token = data.get('token') or 'drafter'
                if self.email:
                    self.ready.set()
                    logger.info(f"Created drafter inbox: {self.email}")
                    return True
            except Exception as e:
                logger.error(f"Error creating drafter inbox: {e}")
                return False
        return False

    def fetch_messages(self):
        if not self.email or '@' not in self.email:
            return []

        resp = self.session.get(
            f'{self.BASE}/api/inbox/{self.email}?limit=80',
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        messages = data.get('messages', []) if isinstance(data, dict) else []
        if not isinstance(messages, list):
            return []

        out = []
        for msg_summary in messages:
            msg_id = str(msg_summary.get('id', '') or msg_summary.get('message_id', ''))
            if not msg_id:
                continue
            subject = msg_summary.get('subject', '') or ''
            sender = msg_summary.get('from', '') or ''
            if subject or sender:
                self._log_new_email(msg_id, f"  New email: subject='{subject}' from='{sender}'")

            try:
                resp2 = self.session.get(
                    f'{self.BASE}/api/message/{msg_id}?raw=1',
                    timeout=20,
                )
            except Exception:
                continue
            if resp2.status_code != 200:
                continue
            out.append((msg_id, subject + '\n' + (resp2.text or ''), ''))
        return out


class GuerrillaMail(TempMailBase):

    name = 'guerrilla'
    BASE = 'https://api.guerrillamail.com/ajax.php'

    def create_account(self):
        for attempt in range(5):
            try:
                resp = self.session.get(
                    self.BASE,
                    params={'f': 'get_email_address'},
                    timeout=20,
                )
                if resp.status_code != 200:
                    logger.warning(f"guerrilla offline ({resp.status_code}), skipping")
                    return False
                data = resp.json()
                self.email = data.get('email_addr')
                self.sid_token = data.get('sid_token')
                if self.email and self.sid_token:
                    self.token = self.sid_token
                    self.ready.set()
                    return True
            except Exception:
                return False
            time.sleep(1.5)
        return False

    def fetch_messages(self):
        resp = self.session.get(
            self.BASE,
            params={'f': 'get_email_list', 'sid_token': self.sid_token, 'offset': '0', 'seq': '0'},
            timeout=20,
        )
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        if not isinstance(data, dict):
            return []

        out = []
        for msg_summary in data.get('list', []):
            msg_id = str(msg_summary.get('mail_id', ''))
            if not msg_id:
                continue
            subject = msg_summary.get('mail_subject', '') or ''
            sender = msg_summary.get('mail_from', '') or ''
            logger.info(f"  New email: subject='{subject}' from='{sender}'")

            text = msg_summary.get('mail_body') or msg_summary.get('mail_excerpt') or ''
            html = msg_summary.get('mail_html') or ''
            out.append((msg_id, subject + '\n' + text, html))
        return out


class MailDrop(TempMailBase):

    name = 'maildrop'
    BASE = 'https://maildrop.cc/api/inbox'

    def create_account(self):
        addr = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=10))
        self.email = f'{addr}@maildrop.cc'
        self.token = 'maildrop'
        self.ready.set()
        return True

    def fetch_messages(self):
        box = self.email.rsplit('@', 1)[0]

        resp = self.session.get(f'{self.BASE}/{box}', timeout=20)
        if resp.status_code != 200:
            return []
        try:
            data = resp.json()
        except Exception:
            return []
        if isinstance(data, dict):
            data = data.get('messages', [])

        out = []
        for msg_summary in data:
            msg_id = str(msg_summary.get('id', ''))
            subject = msg_summary.get('subj', '') or msg_summary.get('subject', '') or ''

            try:
                resp2 = self.session.get(f'{self.BASE}/{box}/{msg_id}', timeout=20)
            except Exception as e:
                logger.warning(f"  Error fetching message: {e}")
                continue
            if resp2.status_code != 200:
                continue

            text = ''
            html = ''
            try:
                payload = resp2.json()
                if isinstance(payload, dict) and 'data' in payload:
                    payload = payload['data']
                if isinstance(payload, dict):
                    text = payload.get('text') or payload.get('body') or ''
                    html = payload.get('html') or ''
            except Exception:
                text = resp2.text or ''
            out.append((msg_id, subject + '\n' + text, html))
        return out


PROVIDERS = [DrafterMail, MailTmLike, MailDrop]

_provider_rotate_lock = threading.Lock()
_provider_rotate = 0


def _create_temp_mail():
    global _provider_rotate

    with _provider_rotate_lock:
        start = _provider_rotate % len(PROVIDERS)
        _provider_rotate += 1

    for i in range(len(PROVIDERS)):
        provider = PROVIDERS[(start + i) % len(PROVIDERS)]()
        thread = threading.Thread(target=provider.create_account, daemon=True)
        thread.start()
        deadline = time.time() + 50
        while not provider.ready.is_set():
            if not thread.is_alive():
                break
            if time.time() > deadline:
                break
            time.sleep(0.5)
        if provider.ready.is_set():
            return provider
        logger.warning(f"Temp-mail provider {provider.name} failed, trying next...")
    return None


def _gen_password():
    pw_chars = list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')
    pw = [
        random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ'),
        random.choice('0123456789'),
    ] + random.choices(pw_chars, k=14)
    random.shuffle(pw)
    return ''.join(pw)


def signup(browser, password, mail):
    timing.start('total_signup')

    context = browser.new_context(
        viewport={'width': CONFIG['viewport_width'], 'height': CONFIG['viewport_height']},
        locale='en-US',
        timezone_id='America/New_York',
    )
    context.route('**/*', _route_handler)
    page = context.new_page()

    try:
        timing.start('page_load')
        page.goto('https://chat.qwen.ai/auth', timeout=CONFIG['timeout'])
        timing.end('page_load')
        logger.info("Page loaded, waiting for React app...")

        page.wait_for_selector('.qwenchat-auth-pc, .qwenchat-auth-mobile, [class*="auth"]',
                               timeout=15000)
        logger.info("Auth page ready")

        signup_link = None
        for sel in [
            '.qwenchat-auth-pc-switch-button:has-text("Sign up")',
            '.qwenchat-auth-pc-switch-button:has-text("Register")',
            'button:has-text("Sign up")',
            'a:has-text("Sign up")',
        ]:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                signup_link = loc.first
                logger.info(f"Found signup link: {sel}")
                break

        if signup_link:
            signup_link.click()
            logger.info("Clicked signup toggle")
        else:
            logger.info("No explicit signup toggle found, checking if form present")
            try:
                page.wait_for_selector(
                    'input[placeholder="Enter Your Full Name"], input[name="username"]',
                    timeout=3000)
            except Exception:
                logger.warning("No signup link found")
                return None

        name = generate_human_name()
        logger.info(f"Using name: {name}")

        name_filled = False
        for sel in [
            'input[placeholder="Enter Your Full Name"]',
            'input[name="username"]',
            '.qwenchat-auth-pc-input-item input',
        ]:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.fill(name)
                name_filled = True
                logger.info(f"Filled name via: {sel}")
                break
        if not name_filled:
            logger.error("Could not find name input")
            return None

        if not mail or not mail.email or not mail.token:
            logger.error("Temp email not ready")
            return None
        email = mail.email
        logger.info(f"Email: {email}")

        email_filled = False
        for sel in [
            'input[placeholder="Enter Your Email"]',
            'input[name="email"]',
            'input[type="email"]',
        ]:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.fill(email)
                email_filled = True
                logger.info(f"Filled email via: {sel}")
                break
        if not email_filled:
            logger.error("Could not find email input")
            return None

        pw_filled = False
        for sel in [
            'input[placeholder="Enter Your Password"]',
            'input[name="password"]',
            'input[type="password"]',
        ]:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                loc.first.fill(password)
                pw_filled = True
                logger.info(f"Filled password via: {sel}")
                break
        if not pw_filled:
            logger.error("Could not find password input")
            return None

        confirm_filled = False
        for sel in [
            'input[placeholder="Enter Your Password Again"]',
            'input[name="checkPassword"]',
        ]:
            try:
                loc = page.locator(sel)
                loc.first.wait_for(state='visible', timeout=5000)
                if loc.count() > 0:
                    loc.first.fill(password)
                    confirm_filled = True
                    logger.info(f"Filled confirm password via: {sel}")
                    break
            except Exception:
                continue
        if not confirm_filled:
            logger.warning("Confirm password field not found via selectors")

        try:
            policy_area = page.locator('.qwenchat-auth-pc-register-policy')
            if policy_area.count() > 0 and policy_area.first.is_visible():
                cb = policy_area.locator('input[type="checkbox"]')
                if cb.count() > 0:
                    if not cb.first.is_checked():
                        cb.first.click(force=True)
                        logger.info("Checked policy checkbox")
                else:
                    checked_state = None
                    try:
                        checked_state = policy_area.locator(
                            'span[role="checkbox"]'
                        ).first.get_attribute('aria-checked')
                    except Exception:
                        pass

                    checkbox_span = policy_area.locator(
                        '.qwenchat-auth-pc-register-policy-checkbox, span[role="checkbox"]'
                    )
                    if checkbox_span.count() > 0:
                        checkbox_span.first.click()
                        logger.info("Clicked policy checkbox span")
                    elif checked_state != 'true':
                        label = policy_area.locator('.ant-checkbox-wrapper, label')
                        if label.count() > 0:
                            label.first.click()
                            logger.info("Clicked antd checkbox wrapper")
                        else:
                            policy_area.first.click()
                            logger.info("Clicked policy area div")
        except Exception:
            pass

        submit_btn = None
        for sel in [
            'button:has-text("Create Account")',
            '.qwenchat-auth-pc-submit-button',
            'button[type="submit"]',
        ]:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                submit_btn = loc.first
                logger.info(f"Found submit button: {sel}")
                break

        if submit_btn:
            submit_btn.click()
        else:
            logger.error("No submit button found")
            return None

        logger.info("Waiting for Aliyun captcha to initialize...")
        captcha_ready = False
        for wait_attempt in range(60):
            try:
                captcha_ready = page.evaluate("""
                    () => {
                        const slider = document.querySelector('#aliyunCaptcha-sliding-slider');
                        const bg = document.querySelector('#aliyunCaptcha-img');
                        const popup = document.querySelector('#aliyunCaptcha-popup') ||
                                      document.querySelector('.aliyunCaptcha-container') ||
                                      document.querySelector('[class*="aliyunCaptcha-show"]');
                        return !!(slider || bg || popup);
                    }
                """)
                if captcha_ready:
                    break
            except Exception:
                pass

            if wait_attempt % 5 == 4:
                try:
                    page.evaluate("""
                        () => {
                            const text = document.querySelector('#aliyunCaptcha-captcha-text');
                            if (text) text.click();
                            const verify = document.querySelector('[class*="aliyunCaptcha"]');
                            if (verify) verify.click();
                            const allDivs = document.querySelectorAll('div');
                            for (const d of allDivs) {
                                if (d.innerText && d.innerText.includes('Access Verification') && d.children.length < 5) {
                                    d.click();
                                    break;
                                }
                            }
                        }
                    """)
                except Exception:
                    pass

            time.sleep(0.5)

        if not captcha_ready:
            logger.warning("Aliyun captcha elements not found after 15s, checking for iframe...")
            try:
                frames = page.frames
                for frame in frames:
                    if 'aliyun' in (frame.url or '').lower() or 'captcha' in (frame.url or '').lower():
                        logger.info(f"Found captcha iframe: {frame.url[:80]}")
                        captcha_ready = True
                        break
            except Exception:
                pass

        if not captcha_ready:
            logger.error("Captcha never initialized")
            page.screenshot(path=f'output/no_captcha_{email.split("@")[0]}.png')
            return None

        logger.info("Captcha elements found, waiting for images to load...")
        images_loaded = False
        for _ in range(40):
            try:
                images_loaded = page.evaluate("""
                    () => {
                        const bg = document.querySelector('#aliyunCaptcha-img');
                        const puzzle = document.querySelector('#aliyunCaptcha-puzzle');
                        if (!bg || !puzzle) return false;
                        return bg.naturalWidth > 50 && puzzle.naturalWidth > 10;
                    }
                """)
                if images_loaded:
                    break
            except Exception:
                pass
            time.sleep(0.5)

        if not images_loaded:
            logger.warning("Captcha images didn't load, refreshing...")
            try:
                refresh_btn = page.locator('#aliyunCaptcha-btn-refresh')
                if refresh_btn.count() > 0 and refresh_btn.is_visible():
                    refresh_btn.click()
                    time.sleep(2)
                    for _ in range(20):
                        try:
                            images_loaded = page.evaluate("""
                                () => {
                                    const bg = document.querySelector('#aliyunCaptcha-img');
                                    const puzzle = document.querySelector('#aliyunCaptcha-puzzle');
                                    if (!bg || !puzzle) return false;
                                    return bg.naturalWidth > 50 && puzzle.naturalWidth > 10;
                                }
                            """)
                            if images_loaded:
                                break
                        except Exception:
                            pass
                        time.sleep(0.3)
            except Exception:
                pass

        if not images_loaded:
            logger.error("Captcha images failed to load after refresh")
            page.screenshot(path=f'output/grey_captcha_{email.split("@")[0]}.png')
            return None

        logger.info(f"Captcha images loaded successfully")

        solver = CaptchaSolver(logger, CONFIG)
        url_before_captcha = page.url
        result = solver.solve(page)

        if not result:
            logger.error("Captcha failed")
            return None

        if isinstance(result, str) and len(result) > 20:
            logger.info(f"Captcha solved, got verification token")
        else:
            logger.warning(f"Captcha solver returned non-token result: {str(result)[:80]}")

        time.sleep(0.5)

        current_url = page.url
        page_redirected = current_url != url_before_captcha

        if page_redirected:
            logger.info(f"Page already redirected after captcha: {current_url}")
        else:
            try:
                page.wait_for_selector('#aliyunCaptcha-popup', state='hidden', timeout=5000)
                logger.info("Captcha popup confirmed hidden")
            except Exception:
                try:
                    page.keyboard.press("Escape")
                    time.sleep(0.3)
                except Exception:
                    pass

            try:
                page.evaluate("""
                    () => {
                        const popup = document.querySelector('#aliyunCaptcha-popup');
                        if (popup) popup.style.display = 'none';
                        const containers = document.querySelectorAll('.aliyunCaptcha-container, [class*="aliyunCaptcha"]');
                        containers.forEach(el => { if (el) el.style.display = 'none'; });
                    }
                """)
            except Exception:
                pass

            time.sleep(0.3)

            create_btn = page.locator(SELECTORS['create_account_button'])
            if create_btn.count() > 0 and create_btn.is_visible():
                try:
                    create_btn.click()
                    logger.info("Clicked Create Account button")
                except Exception:
                    try:
                        page.keyboard.press("Enter")
                    except Exception:
                        pass
            else:
                page.keyboard.press("Enter")

            try:
                page.wait_for_function(
                    """() => window.location.href !== document.referrer""",
                    timeout=10000
                )
            except Exception:
                pass

            current_url = page.url
            page_redirected = current_url != url_before_captcha
            if page_redirected:
                logger.info(f"Page redirected after Create Account: {current_url}")

        logger.info("Captcha solved, checking for verification email...")
        time.sleep(0.5)

        if mail:
            logger.info("Polling temp email for verification link...")
            verification_link = mail.get_verification_link(timeout=CONFIG.get('verify_timeout', 90))

            if verification_link:
                logger.info(f"Got verification link: {verification_link[:80]}...")

                try:
                    page.goto(verification_link, timeout=30000)
                except Exception:
                    pass
                time.sleep(1)

                logger.info("Verification link visited, force-navigating to chat...")
                try:
                    page.goto('https://chat.qwen.ai/', timeout=30000)
                except Exception:
                    pass

                stored_token = _wait_for_token(page)

                if stored_token:
                    logger.info(f"Valid auth token found after verification!")
                    return stored_token

                logger.warning("Email verified but no token found after navigating to chat")
            else:
                logger.warning("No verification link received from temp email")

        try:
            page.goto('https://chat.qwen.ai/', timeout=30000)
        except Exception:
            pass

        stored_token = _wait_for_token(page)

        if stored_token:
            logger.info(f"Valid auth token found in storage")
            return stored_token

        logger.warning(f"No token found. Current URL: {page.url}")

        try:
            page.screenshot(path=f'output/debug_{email.split("@")[0]}.png')
        except Exception:
            pass

        page_text = page.evaluate("() => (document.body?.innerText || '').substring(0, 500)")
        logger.warning(f"Page text snippet: {page_text[:200]}")

        return None

    except Exception as e:
        logger.error(f"Error: {e}")
        return None
    finally:
        try:
            context.close()
        except Exception:
            pass


def _write_account(email, password, token=None, needs_verification=False):
    with _file_lock:
        if needs_verification:
            with open('output/accounts.txt', 'a') as f:
                f.write(f"{email}:{password}:VERIFICATION_NEEDED\n")
        else:
            with open('output/accounts.txt', 'a') as f:
                f.write(f"{email}:{password}\n")
            if token:
                with open('output/tokens.txt', 'a') as f:
                    f.write(f"{token}\n")


def _create_account(worker, index):
    global _success_count, _verify_count

    with worker.lock:
        logger.info(f"\nAccount {index}")

        time.sleep(random.uniform(0, 1))

        password = _gen_password()
        mail = _create_temp_mail()
        if not mail:
            logger.error("All temp-mail providers failed")
            return None

        browser = worker.ensure_browser()
        result = signup(browser, password, mail)

        if result:
            email = mail.email or 'unknown'
            if isinstance(result, dict) and result.get('needs_verification'):
                with _counter_lock:
                    _verify_count += 1
                _write_account(email, password, needs_verification=True)
                logger.info(f"Account {index} needs verification: {email}")
            else:
                token = result if isinstance(result, str) else "SUCCESS"
                with _counter_lock:
                    _success_count += 1
                _write_account(email, password, token)
                token_display = token[:50] + "..." if len(token) > 50 else token
                logger.info(f"Account {index} created with token: {token_display}")


def _worker_loop(worker, indices):
    try:
        for index in indices:
            try:
                _create_account(worker, index)
            except Exception as e:
                logger.error(f"Account {index} crashed: {e}")
            time.sleep(1 + random.uniform(0, 1.5))
    finally:
        worker.close()


def main():
    global _success_count, _verify_count

    print("\n" + "="*50)
    print("Qwen Auto Signup with multi-provider temp mail")
    print("="*50)

    count = CONFIG.get('count', 1)
    threads = max(1, min(CONFIG.get('threads', 1), count))

    logger.info(f"Count: {count}")
    logger.info(f"Threads: {threads}")
    logger.info(f"Headless: {CONFIG.get('headless', False)}")
    logger.info("="*50)

    _success_count = 0
    _verify_count = 0
    Path('output').mkdir(exist_ok=True)

    workers = [Worker(i) for i in range(threads)]
    schedules = [[] for _ in range(threads)]
    for i in range(1, count + 1):
        schedules[(i - 1) % threads].append(i)

    runner_threads = []
    for worker, indices in zip(workers, schedules):
        if not indices:
            continue
        t = threading.Thread(target=_worker_loop, args=(worker, indices), daemon=True)
        runner_threads.append(t)
        t.start()

    for t in runner_threads:
        t.join()

    logger.info(f"\n{_success_count} fully created, {_verify_count} need verification")
    print(f"\n{_success_count} fully created")
    print(f"{_verify_count} need email verification")
    print(f"output/accounts.txt (email:password)")
    print(f"output/tokens.txt (tokens)")
    print(timing.summary())


if __name__ == "__main__":
    main()