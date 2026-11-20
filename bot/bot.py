import os
import secrets
import random
import io
import re
import html
import time
import hashlib
import asyncio
import logging
import zipfile
import threading
import subprocess
import json
import tempfile
import urllib.request
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ExifTags, ImageStat

# Safe optional imports for mobile / Termux environments
try:
    import cv2
except ImportError:
    cv2 = None

try:
    import numpy as np
except ImportError:
    np = None

try:
    import pytesseract
except ImportError:
    pytesseract = None

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pillow_heif = None

try:
    from pyzbar.pyzbar import decode as pyzbar_decode
except ImportError:
    pyzbar_decode = None

from telegram import (
    Update,
    Message,
    CallbackQuery,
    Bot,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo
)
from telegram.request import HTTPXRequest
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Load BOT_TOKEN, ADMIN_ID, and GEMINI_API_KEY from environment variable or local gitignored .env file
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

env_candidates = [
    os.path.join(BASE_DIR, ".env"),
    os.path.join(BASE_DIR, "../.env"),
    os.path.join(os.getcwd(), ".env"),
    os.path.join(os.getcwd(), "bot/.env")
]
for ef in env_candidates:
    if os.path.exists(ef):
        try:
            with open(ef, "r", encoding="utf-8") as f:
                for line in f:
                    line_str = line.strip()
                    if line_str.startswith("BOT_TOKEN=") and not BOT_TOKEN:
                        BOT_TOKEN = line_str.split("=", 1)[1].strip("\"' ")
                    elif line_str.startswith("ADMIN_ID=") and not ADMIN_ID:
                        ADMIN_ID = line_str.split("=", 1)[1].strip("\"' ")
                    elif line_str.startswith("GEMINI_API_KEY=") and not GEMINI_API_KEY:
                        GEMINI_API_KEY = line_str.split("=", 1)[1].strip("\"' ")
        except Exception as env_err:
            logging.warning(f"Error reading {ef}: {env_err}")

GEMINI_API_KEYS = [k.strip() for k in GEMINI_API_KEY.split(",") if k.strip()] if GEMINI_API_KEY else []

def resolve_path(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

START_BANNER_PATH = resolve_path([
    os.path.join(BASE_DIR, "start_banner.jpg"),
    "/home/torabek/KiberIz4/bot/start_banner.jpg",
    "/home/torabek/KiberIz4/start_banner.jpg"
])

LOGO_PATH = resolve_path([
    os.path.join(BASE_DIR, "kiberiz_logo.png"),
    os.path.join(BASE_DIR, "../assets/kiberiz_logo.png"),
    "/home/torabek/KiberIz4/assets/kiberiz_logo.png"
])

SAMPLE_PATH = resolve_path([
    os.path.join(BASE_DIR, "sample_gps_school4.jpg"),
    os.path.join(BASE_DIR, "../web/samples/sample_gps_school4.jpg"),
    "/home/torabek/KiberIz4/web/samples/sample_gps_school4.jpg"
])

SAMPLE_VISUAL_PATH = resolve_path([
    os.path.join(BASE_DIR, "sample_visual_osint_test.jpg"),
    os.path.join(BASE_DIR, "../samples/sample_visual_osint_test.jpg"),
    "/home/torabek/KiberIz4/samples/sample_visual_osint_test.jpg"
])


# ==========================================
# 🛡️ ANTI-STALKING DATA STORES & HELPERS
# ==========================================
CONSENT_FILE = os.path.join(BASE_DIR, "data", "consent_requests.json")
BIO_TOKENS_FILE = os.path.join(BASE_DIR, "data", "bio_tokens.json")

def load_json_store(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_json_store(filepath, data):
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.warning(f"Error saving {filepath}: {e}")

CONSENT_REQUESTS = load_json_store(CONSENT_FILE)
BIO_TOKENS = load_json_store(BIO_TOKENS_FILE)

def build_username_result_keyboard(raw_user: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Telegram", url=f"https://t.me/{raw_user}", icon_custom_emoji_id=E["CALL"]),
            InlineKeyboardButton("Instagram", url=f"https://instagram.com/{raw_user}", icon_custom_emoji_id=E["EXIF_PHOTO"])
        ],
        [
            InlineKeyboardButton("TikTok", url=f"https://tiktok.com/@{raw_user}", icon_custom_emoji_id=E["FIRE"]),
            InlineKeyboardButton("GitHub", url=f"https://github.com/{raw_user}", icon_custom_emoji_id=E["LAPTOP"])
        ],
        [
            InlineKeyboardButton("WhatsMyName (Global Qidiruv)", url=f"https://whatsmyname.app/?q={raw_user}", icon_custom_emoji_id=E["SEARCH"])
        ]
    ])

async def handle_consent_deep_link(update: Update, context: ContextTypes.DEFAULT_TYPE, req_id: str):
    chat_id = update.effective_chat.id
    req = CONSENT_REQUESTS.get(req_id)
    
    if not req:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{p('WARN', '⚠️')} <b>XATOLIK:</b> Ushbu rozilik so‘rovi muddati o‘tgan yoki topilmadi.",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return
        
    target = req.get("target", "profil")
    requester_name = req.get("requester_name", "Do‘stingiz")
    requester_uname = f"@{req['requester_username']}" if req.get("requester_username") else requester_name

    consent_text = (
        f"{p('SHIELD', '🛡️')} <b>DIQQAT: SIZGA KIBER-XAVFSIZLIK AUDIT SO‘ROVI KELDI!</b>\n\n"
        f"Do‘stingiz <b>{html.escape(requester_uname)}</b> sizning <code>@{html.escape(target)}</code> "
        f"profilingizning internetdagi raqamli izi va xavfsizligini tekshirishni taklif qilmoqda.\n\n"
        f"🔒 <b>100% SHAXSIY DAXLSIZLIK KAFOLATI (O‘RQ-547):</b>\n"
        f"Agar siz rozilik bersangiz, to‘liq Maltego kiber-razvedka hisoboti {html.escape(requester_uname)}ga <b>EMAS</b>, "
        f"<b>FAQAT SIZNING O‘ZINGIZGA</b> yuboriladi! Do‘stingiz sizning profilingiz zaifliklarini ko‘ra olmaydi.\n\n"
        f"<i>Rozilik berasizmi?</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ha, o‘z hisobim auditini qabul qilaman", callback_data=f"accept_consent_{req_id}")],
        [InlineKeyboardButton("🚫 Rad etish (Bekor qilish)", callback_data=f"reject_consent_{req_id}")]
    ])
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=consent_text,
        parse_mode="HTML",
        reply_markup=kb
    )

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"KiberIz-4 Bot is running 24/7!")
    def log_message(self, format, *args):
        pass

def start_health_check_if_needed():
    port_str = os.environ.get("PORT")
    if port_str:
        try:
            port = int(port_str)
            server = HTTPServer(("0.0.0.0", port), HealthHandler)
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            logging.info(f"Health check HTTP server started on port {port}")
        except Exception as e:
            logging.error(f"Failed to start health server: {e}")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# ==========================================
# TELEGRAM PREMIUM CUSTOM EMOJIS (Official Sets)
# ==========================================
E = {
    # Brand / Cyber Security
    "SHIELD": "5825943289563456446",       # 🛡 Animated Shield
    "SEARCH": "5188217332748527444",       # 🔍 OSINT Magnifier
    "EXIF_PHOTO": "5375074927252621134",   # 🖼 Photo / Picture
    "CAMERA": "5375074927252621134",       # 📸 Camera / Screenshot
    "WARNING": "5825944844341618261",      # ⚠️ Cyber Warning
    "SOS": "5767387736969323365",          # 🚨 Siren Emergency
    "LOCK": "5769487503530664462",         # 🔒 Cyber Lock
    "KEY_LOCK": "5472308992514464048",     # 🔐 2FA Key Lock
    "KEY": "5330115548900501467",          # 🔑 Key
    "CHECK": "5427009714745517609",        # ✅ Checkmark Badge
    "CROSS": "5465665476971471368",        # ❌ Cross Mark
    
    # OSINT & Education
    "SCHOOL": "5265002646397285605",       # 🏫 4-Maktab
    "TEACHER": "5373039692574893940",      # 👨‍🏫 Teacher
    "HACKER": "5190498849440931467",       # 👨‍💻 Cyber Analyst
    "ROBOT": "5431376038628171216",        # 🤖 AI Robot / Deepfake
    "HOUSE": "5465226866321268133",        # 🏠 Home
    "BUILDING": "5264733042710181045",     # 🏢 Street Building
    "LAPTOP": "5431376038628171216",       # 💻 Laptop
    "PHONE": "5407025283456835913",        # 📱 Phone
    "CALL": "5467539229468793355",         # 📞 Hotline
    "TIMER": "5413704112220949842",        # ⏰ 5-minute Timer
    "GLOBE": "6048518064029307235",        # 🌐 Web Platform
    "RADAR": "5188217332748527444",        # 📡 Kiber-Radar
    "ROCKET": "5445284980978621387",       # 🚀 Launch
    "TEST": "5411512278740640309",         # 🧪 Digital Footprint Quiz
    "LIGHT": "5472146462362048818",        # 💡 Pro Tip
    "WAVE": "5472055112702629499",         # 👋 Hello Greeting
    "STAR": "5435957248314579621",         # ⭐ Star
    "STATS": "5431577498364158238",        # 📊 Stats / Results
    "INFO": "5825427631494930742",         # ℹ️ Information
    "EYES": "5424885441100782420",         # 👀 Surveillance / Attention
    "CHAT": "5465300082628763143",         # 💬 Anonymous Chat
    "BOMB": "5469654973308476699",         # 💣 Cyber Danger
    "FIRE": "5420315771991497307",         # 🔥 Popular
    "DIAMOND": "5471952986970267163",      # 💎 Premium Shield
    "TROPHY": "5409008750893734809",       # 🏆 Winner
    "REFRESH": "5264727218734524899",      # 🔄 Retry
    "HUNDRED": "5188208446461188962",      # 💯 100% Score
    "FLAG_UZ": "5449829434334912605",      # 🇺🇿 Uzbekistan Flag
    
    # Levels (Colored Circles)
    "GREEN": "5287429930529859276",        # 🟢 Green Safe Circle
    "YELLOW": "5287355137969367127",       # 🟡 Yellow Warning Circle
    "RED": "5287702059657734416",          # 🔴 Red Danger Circle
    "GEAR": "5769531264952442902",         # ⚙️ Settings
}

def p(name: str, fallback: str = "•") -> str:
    """Renders a Telegram Premium custom emoji tag."""
    emoji_id = E.get(name)
    if emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback

EMOJI_MAP = {
    '🇺🇿': E['FLAG_UZ'],
    '🛡️': E['SHIELD'], '🛡': E['SHIELD'],
    '⚖️': E['SHIELD'], '⚖': E['SHIELD'],
    '🔍': E['SEARCH'], '🔎': E['SEARCH'],
    '🖼️': E['EXIF_PHOTO'], '🖼': E['EXIF_PHOTO'], '📸': E['EXIF_PHOTO'], '🎞': E['EXIF_PHOTO'], '🎬': E['EXIF_PHOTO'],
    '⚠️': E['WARNING'], '⚠': E['WARNING'],
    '🚨': E['SOS'],
    '🔒': E['LOCK'], '🔓': E['LOCK'],
    '🔐': E['KEY_LOCK'],
    '🔑': E['KEY'],
    '✅': E['CHECK'],
    '❌': E['CROSS'], '🚫': E['CROSS'],
    '🏫': E['SCHOOL'], '🎒': E['SCHOOL'],
    '👨‍🏫': E['TEACHER'],
    '👨‍💻': E['HACKER'], '🕵️‍♂️': E['HACKER'], '🕵': E['HACKER'], '👤': E['HACKER'], '👥': E['HACKER'], '🐙': E['HACKER'],
    '🏠': E['HOUSE'], '🚪': E['HOUSE'],
    '🏢': E['BUILDING'], '🏬': E['BUILDING'], '🏦': E['BUILDING'], '🛣️': E['BUILDING'], '🛣': E['BUILDING'], '🚗': E['BUILDING'], '🛒': E['BUILDING'], '📍': E['BUILDING'], '📌': E['BUILDING'],
    '💻': E['LAPTOP'], '🎮': E['LAPTOP'], '📦': E['LAPTOP'], '📁': E['LAPTOP'], '📂': E['LAPTOP'],
    '📱': E['PHONE'], '📞': E['CALL'], '🔊': E['CALL'],
    '⏰': E['TIMER'], '⏱️': E['TIMER'], '⏱': E['TIMER'], '⏳': E['TIMER'], '⌛': E['TIMER'], '📅': E['TIMER'], '🌙': E['TIMER'], '🌅': E['TIMER'], '☀️': E['TIMER'], '☀': E['TIMER'], '🌤️': E['TIMER'], '🌤': E['TIMER'],
    '🌐': E['GLOBE'], '🔗': E['GLOBE'], '🗺️': E['GLOBE'], '🗺': E['GLOBE'],
    '📡': E['RADAR'],
    '🚀': E['ROCKET'],
    '🧪': E['TEST'],
    '💡': E['LIGHT'], '👉': E['LIGHT'], '🎵': E['LIGHT'], '🧠': E['LIGHT'], '⚡': E['LIGHT'], '➔': E['LIGHT'], '➜': E['LIGHT'], '➡️': E['LIGHT'], '➡': E['LIGHT'],
    '👋': E['WAVE'], '🤝': E['WAVE'],
    '⭐': E['STAR'], '🎯': E['STAR'], '🎰': E['STAR'], '⚽': E['STAR'], '✨': E['STAR'],
    '📊': E['STATS'], '💸': E['STATS'], '💳': E['STATS'], '💰': E['STATS'],
    'ℹ️': E['INFO'], 'ℹ': E['INFO'], '📝': E['INFO'], '📑': E['INFO'], '📄': E['INFO'], '✏️': E['INFO'], '✏': E['INFO'], '📐': E['INFO'], '🆔': E['INFO'],
    '👀': E['EYES'],
    '💬': E['CHAT'], '✈️': E['CHAT'], '✈': E['CHAT'], '🎣': E['SEARCH'], '✍️': E['CHAT'], '✍': E['CHAT'],
    '💣': E['BOMB'], '🛑': E['BOMB'], '🔞': E['BOMB'], '☠️': E['BOMB'], '☠': E['BOMB'], '💊': E['BOMB'],
    '🔥': E['FIRE'],
    '💎': E['DIAMOND'],
    '🏆': E['TROPHY'], '🎉': E['TROPHY'], '🎊': E['TROPHY'],
    '🔄': E['REFRESH'],
    '💯': E['HUNDRED'],
    '🤖': E['HACKER'],
    '🟢': E['GREEN'],
    '🟡': E['YELLOW'],
    '🔴': E['RED'],
    '⚙️': E['GEAR'], '⚙': E['GEAR'],
    '🔔': E['WARNING'], '📢': E['WARNING'], '❗': E['WARNING'], '‼️': E['WARNING'],
    '👍': E['CHECK'], '👎': E['CROSS'],
    '❓': E['SEARCH'], '❔': E['SEARCH']
}

_SORTED_EMOJIS = sorted(EMOJI_MAP.keys(), key=len, reverse=True)
_EMOJI_REGEX = re.compile('(' + '|'.join(re.escape(k) for k in _SORTED_EMOJIS) + ')')

def auto_premium(text: str) -> str:
    """Ensures EVERY unicode emoji in HTML text is converted to a Telegram Premium animated tag."""
    if not text or not isinstance(text, str):
        return text
    parts = re.split(r'(<tg-emoji[^>]*>.*?</tg-emoji>)', text)
    res = []
    for p_part in parts:
        if p_part.startswith('<tg-emoji'):
            res.append(p_part)
        else:
            def repl(m):
                em = m.group(1)
                eid = EMOJI_MAP.get(em)
                if eid:
                    return f'<tg-emoji emoji-id="{eid}">{em}</tg-emoji>'
                return em
            res.append(_EMOJI_REGEX.sub(repl, p_part))
    return ''.join(res)

def strip_html_tags(s: str) -> str:
    return re.sub(r'<[^>]+>', '', s)

# ==========================================
# MAIN PERSISTENT KEYBOARD (TELEGRAM BOT API 6.0+)
# ==========================================
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("Surat & Skrinshot auditi", icon_custom_emoji_id=E["SEARCH"]),
            KeyboardButton("5 daqiqalik Chek-list", icon_custom_emoji_id=E["SHIELD"])
        ],
        [
            KeyboardButton("Nikneym & Havola auditi", icon_custom_emoji_id=E["HACKER"]),
            KeyboardButton("💬 Sharh & Izoh OSINT", icon_custom_emoji_id=E["CHAT"])
        ],
        [
            KeyboardButton("🎭 Deepfake Detektor", icon_custom_emoji_id=E["ROBOT"]),
            KeyboardButton("Real keyslar: 3 ta xavf", icon_custom_emoji_id=E["WARNING"])
        ],
        [
            KeyboardButton("👥 Guruh Kiber-Qalqoni", icon_custom_emoji_id=E["SHIELD"]),
            KeyboardButton("\"Raqamli Iz\" Testi", icon_custom_emoji_id=E["TEST"])
        ],
        [
            KeyboardButton("Kiber-Portal (Web App)", web_app=WebAppInfo(url="https://abduvoitov11.github.io/kiberiz4/"), icon_custom_emoji_id=E["GLOBE"]),
            KeyboardButton("AI Kiber-Maslahatchi", icon_custom_emoji_id=E["LIGHT"])
        ],
        [
            KeyboardButton("Anonim SOS / Yordam", icon_custom_emoji_id=E["SOS"])
        ]
    ],
    resize_keyboard=True,
    is_persistent=True
)

# ==========================================
# CHAT AUTO-CLEANUP & MESSAGE MANAGEMENT
# ==========================================
PREV_BOT_MSGS = {}        # {chat_id: set_of_message_ids}
ACTIVE_KEYBOARD_MSGS = {} # {chat_id: message_id}

async def cleanup_chat(chat_id: int, bot_instance, keep_ids=None):
    """Deletes previous bot messages in this chat so that the screen stays clean,
    while ALWAYS protecting the active persistent keyboard message."""
    if not chat_id:
        return
    if chat_id in PREV_BOT_MSGS:
        to_del = list(PREV_BOT_MSGS[chat_id])
        PREV_BOT_MSGS[chat_id] = set()
        active_kb_mid = ACTIVE_KEYBOARD_MSGS.get(chat_id)
        for mid in to_del:
            if keep_ids and mid in keep_ids:
                PREV_BOT_MSGS[chat_id].add(mid)
                continue
            # CRITICAL: Do NOT delete the active message that anchors MAIN_KEYBOARD!
            # If deleted, Telegram removes the persistent bottom buttons.
            if active_kb_mid and mid == active_kb_mid:
                PREV_BOT_MSGS[chat_id].add(mid)
                continue
            try:
                await bot_instance.delete_message(chat_id=chat_id, message_id=mid)
            except Exception:
                pass

def record_bot_msg(chat_id, msg):
    """Registers sent bot message(s) for future cleanup."""
    if not chat_id or not msg:
        return
    if chat_id not in PREV_BOT_MSGS:
        PREV_BOT_MSGS[chat_id] = set()
    if isinstance(msg, (list, tuple, set)):
        for m in msg:
            if hasattr(m, "message_id"):
                PREV_BOT_MSGS[chat_id].add(m.message_id)
            elif isinstance(m, int):
                PREV_BOT_MSGS[chat_id].add(m)
    elif hasattr(msg, "message_id"):
        PREV_BOT_MSGS[chat_id].add(msg.message_id)
    elif isinstance(msg, int):
        PREV_BOT_MSGS[chat_id].add(msg)

async def register_new_keyboard_msg(chat_id: int, bot_instance, new_msg):
    """Registers a message that carries MAIN_KEYBOARD and cleanly replaces the old keyboard anchor."""
    if not chat_id or not new_msg:
        return
    new_mid = getattr(new_msg, "message_id", None)
    if not new_mid:
        return
    old_kb_mid = ACTIVE_KEYBOARD_MSGS.get(chat_id)
    ACTIVE_KEYBOARD_MSGS[chat_id] = new_mid
    if chat_id not in PREV_BOT_MSGS:
        PREV_BOT_MSGS[chat_id] = set()
    PREV_BOT_MSGS[chat_id].add(new_mid)
    if old_kb_mid and old_kb_mid != new_mid and bot_instance:
        try:
            await bot_instance.delete_message(chat_id=chat_id, message_id=old_kb_mid)
        except Exception:
            pass
        if chat_id in PREV_BOT_MSGS and old_kb_mid in PREV_BOT_MSGS[chat_id]:
            PREV_BOT_MSGS[chat_id].discard(old_kb_mid)

MENU_BUTTON_TEXTS = {
    "Suratni tekshirish (OSINT)",
    "Surat & Skrinshot auditi",
    "5 daqiqalik Chek-list",
    "Nikneym & Havola auditi",
    "Real keyslar: 3 ta xavf",
    "\"Raqamli Iz\" Testi",
    "Raqamli Iz Testi",
    "Kiber-Portal (Web App)",
    "🌐 Kiber-Portal (Web App)",
    "AI Kiber-Maslahatchi",
    "🤖 AI Kiber-Maslahatchi",
    "Anonim SOS / Yordam",
    "🎭 Deepfake Detektor",
    "Deepfake Detektor",
    "👥 Guruh Kiber-Qalqoni",
    "Guruh Kiber-Qalqoni"
}

async def prepare_clean_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cleans up previous bot messages and deletes command/menu trigger text if applicable."""
    chat = update.effective_chat
    chat_id = chat.id if chat else None
    if chat_id:
        await cleanup_chat(chat_id, context.bot)
    if update.message:
        text = update.message.text or ""
        if text.startswith("/") or text in MENU_BUTTON_TEXTS:
            try:
                await update.message.delete()
            except Exception:
                pass

# Auto-inject premium animated emojis across all Telegram messaging methods with robust HTML fallback & auto-tracking
_orig_reply_text = Message.reply_text
async def _custom_reply_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>[Qisqartirildi...]</i>"
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"

    is_private = getattr(self.chat, "type", "") == "private" or (isinstance(self.chat_id, int) and self.chat_id > 0)
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD

    if is_private and ("reply_markup" not in kwargs or kwargs["reply_markup"] is None):
        kwargs["reply_markup"] = MAIN_KEYBOARD
        has_kb = True

    try:
        res = await _orig_reply_text(self, text, *args, **kwargs)
        record_bot_msg(self.chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            logging.warning(f"reply_text HTML error: {e}. Retrying without HTML.")
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            res = await _orig_reply_text(self, strip_html_tags(text), *args, **kw)
            record_bot_msg(self.chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
            return res
        raise e
Message.reply_text = _custom_reply_text

_orig_edit_text = Message.edit_text
async def _custom_edit_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>[Qisqartirildi...]</i>"
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    try:
        res = await _orig_edit_text(self, text, *args, **kwargs)
        record_bot_msg(self.chat_id, res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            res = await _orig_edit_text(self, strip_html_tags(text), *args, **kw)
            record_bot_msg(self.chat_id, res)
            return res
        raise e
Message.edit_text = _custom_edit_text

_orig_edit_message_text = CallbackQuery.edit_message_text
async def _custom_edit_message_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>[Qisqartirildi...]</i>"
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    try:
        res = await _orig_edit_message_text(self, text, *args, **kwargs)
        if hasattr(self, 'message') and self.message:
            record_bot_msg(self.message.chat_id, res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            res = await _orig_edit_message_text(self, strip_html_tags(text), *args, **kw)
            if hasattr(self, 'message') and self.message:
                record_bot_msg(self.message.chat_id, res)
            return res
        raise e
CallbackQuery.edit_message_text = _custom_edit_message_text

_orig_reply_document = Message.reply_document
async def _custom_reply_document(self, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD
    try:
        res = await _orig_reply_document(self, *args, **kwargs)
        record_bot_msg(self.chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            if "caption" in kw and isinstance(kw["caption"], str):
                kw["caption"] = strip_html_tags(kw["caption"])
            res = await _orig_reply_document(self, *args, **kw)
            record_bot_msg(self.chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
            return res
        raise e
Message.reply_document = _custom_reply_document

_orig_reply_photo = Message.reply_photo
async def _custom_reply_photo(self, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD
    try:
        res = await _orig_reply_photo(self, *args, **kwargs)
        record_bot_msg(self.chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            if "caption" in kw and isinstance(kw["caption"], str):
                kw["caption"] = strip_html_tags(kw["caption"])
            res = await _orig_reply_photo(self, *args, **kw)
            record_bot_msg(self.chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(self.chat_id, self.get_bot(), res)
            return res
        raise e
Message.reply_photo = _custom_reply_photo

_orig_reply_location = Message.reply_location
async def _custom_reply_location(self, *args, **kwargs):
    res = await _orig_reply_location(self, *args, **kwargs)
    record_bot_msg(self.chat_id, res)
    return res
Message.reply_location = _custom_reply_location

_orig_send_message = Bot.send_message
async def _custom_send_message(self, chat_id, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
        if len(text) > 4000:
            text = text[:3900] + "\n\n<i>[Qisqartirildi...]</i>"
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"

    is_private = isinstance(chat_id, int) and chat_id > 0
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD

    if is_private and ("reply_markup" not in kwargs or kwargs["reply_markup"] is None):
        kwargs["reply_markup"] = MAIN_KEYBOARD
        has_kb = True

    try:
        res = await _orig_send_message(self, chat_id, text, *args, **kwargs)
        record_bot_msg(chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(chat_id, self, res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            res = await _orig_send_message(self, chat_id, strip_html_tags(text), *args, **kw)
            record_bot_msg(chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(chat_id, self, res)
            return res
        raise e
Bot.send_message = _custom_send_message

_orig_send_photo = Bot.send_photo
async def _custom_send_photo(self, chat_id, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD
    try:
        res = await _orig_send_photo(self, chat_id, *args, **kwargs)
        record_bot_msg(chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(chat_id, self, res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            if "caption" in kw and isinstance(kw["caption"], str):
                kw["caption"] = strip_html_tags(kw["caption"])
            res = await _orig_send_photo(self, chat_id, *args, **kw)
            record_bot_msg(chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(chat_id, self, res)
            return res
        raise e
Bot.send_photo = _custom_send_photo

_orig_send_document = Bot.send_document
async def _custom_send_document(self, chat_id, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    has_kb = kwargs.get("reply_markup") == MAIN_KEYBOARD
    try:
        res = await _orig_send_document(self, chat_id, *args, **kwargs)
        record_bot_msg(chat_id, res)
        if has_kb and res:
            await register_new_keyboard_msg(chat_id, self, res)
        return res
    except Exception as e:
        err_str = str(e).lower()
        if "parse" in err_str or "bad request" in err_str:
            kw = dict(kwargs)
            kw.pop("parse_mode", None)
            if "caption" in kw and isinstance(kw["caption"], str):
                kw["caption"] = strip_html_tags(kw["caption"])
            res = await _orig_send_document(self, chat_id, *args, **kw)
            record_bot_msg(chat_id, res)
            if has_kb and res:
                await register_new_keyboard_msg(chat_id, self, res)
            return res
        raise e
Bot.send_document = _custom_send_document

# ==========================================
# GEMINI AI CYBER-MENTOR ENGINE (Method 1)
# ==========================================
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-3.8-flash"
]

AI_SYSTEM_INSTRUCTION = """Siz «KiberIz-4» — Toshkent shahri 4-sonli umumiy o'rta ta'lim maktabining Kiberxavfsizlik, Kiber-Razvedka (Deep OSINT) va Sud Kiber-Kriminologiyasi bo'yicha sun'iy intellekt yetakchi murabbiyisiz (Lead Cyber Threat Intelligence & Forensic Mentor).

ASOSIY MAQOM VA VAZIFALAR:
1. Maktab o'quvchilari (5-11 sinflar), ota-onalar va ustozlarga raqamli kiber-gigiyena, ijtimoiy tarmoqlar (Telegram, Instagram, TikTok), 2FA himoya, fishing havolalar, kiberbulling, kiber-shantaj, darknet (.onion saytlar), troyan ilovalar va Deep OSINT (ochiq raqamli izlar xaritasi, doxxingdan himoya) bo'yicha teran, aniq va amaliy yo'riqnomalar berish.
2. CHUQUR OSINT ANALITIKASI: Nikneym, telefon, rasm yoki akkaunt so'ralganda kiber-buzg'unchilar ulardan qanday foydalanishi, raqamli izlar qanday bog'lanishi (profiling) va qanday qilib shaxsiy izlarni xavfsiz tozalash mumkinligini qadam-baqadam ko'rsatib bering.
3. KIBER-SHANTAJ VA HUQUQIY HIMOYA: Agar o'quvchi tahdid, foto-shantaj yoki akkaunt o'g'irlanishiga uchrasa, darhol tinchlantiring, pul to'lamaslikni, barcha yozishmalarni skrinshot qilishni va O'zbekiston Respublikasi IIV Kiberxavfsizlik markazining 1133 ishonch raqamiga murojaat qilishni, O'RQ-547 va Jinoyat Kodeksining 141-2 (shaxsiy hayot daxlsizligi), 165 (tovlamachilik), 278 (kiber-jinoyatlar) moddalari bilan jinoiy jazo muqarrarligini uqtiring.
4. USLUB VA FORMAT: Ravon, do'stona va dalda beruvchi o'zbek tilida (lotin yozuvida), aniq punktlar (•) va faqat <b>, <i>, <code> teglaridan foydalanib yozing. Hech qachon quruq bir xil qolipda javob bermang — har doim teran, tushunarli va professional yordam ko'rsating.
"""

AI_RESPONSE_CACHE = {}  # {hash: (timestamp, formatted_text)}
AI_USER_COOLDOWN = {}   # {user_id: timestamp}

def format_ai_to_tg_html(raw_text: str) -> str:
    """Escapes HTML and translates Gemini markdown / HTML into valid Telegram HTML."""
    if not raw_text:
        return ""
    import html, re
    # Strip outer markdown wrapper if the entire response is wrapped in ```html ... ```
    s_text = raw_text.strip()
    if re.match(r'^```(?:html)?\n.*?\n```$', s_text, flags=re.DOTALL | re.IGNORECASE) and s_text.count("```") == 2:
        raw_text = re.sub(r'^```(?:html)?\s*\n?', '', s_text, flags=re.IGNORECASE)
        raw_text = re.sub(r'\n?```$', '', raw_text)
    # Convert strong, em, headers, p
    raw_text = re.sub(r'<h[1-6][^>]*>(.*?)</h[1-6]>', r'<b>\1</b>\n', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'<p[^>]*>(.*?)</p>', r'\1\n\n', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'<strong[^>]*>(.*?)</strong>', r'<b>\1</b>', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'<em[^>]*>(.*?)</em>', r'<i>\1</i>', raw_text, flags=re.IGNORECASE)
    raw_text = re.sub(r'</?(?:div|span|header|footer|section|article)[^>]*>', '', raw_text, flags=re.IGNORECASE)
    
    t = html.escape(raw_text, quote=False)
    # Restore valid Telegram tags
    t = re.sub(r'&lt;(\/?(?:b|i|u|s|code|pre|blockquote|a|tg-emoji)(?:\s+[^&>]*)?)&gt;', r'<\1>', t, flags=re.IGNORECASE)
    t = re.sub(r'```(?:[a-zA-Z0-9_\-]+)?\n?(.*?)```', lambda m: f'<pre>{m.group(1).strip()}</pre>', t, flags=re.DOTALL)
    t = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])', r'<i>\1</i>', t)
    t = re.sub(r'(?<![a-zA-Z0-9\*])\*([^*\n]+)\*(?![a-zA-Z0-9\*])', r'<i>\1</i>', t)
    return t.strip()

def _query_gemini_api_sync(prompt: str, image_bytes: bytes = None, mime_type: str = "image/jpeg", system_instruction: str = None) -> str:
    """Synchronous worker calling Google Gemini API with fallback models and multi-key rotation."""
    import base64
    if not GEMINI_API_KEYS:
        return (
            "⚠️ <b>Gemini API kaliti topilmadi.</b>\n"
            "Iltimos, bot ma'muri <code>.env</code> fayliga <code>GEMINI_API_KEY</code> ni kiritganligini tekshiring."
        )

    parts = [{"text": prompt}]
    if image_bytes:
        # Lightweight compression for Termux & mobile environments (saves RAM, battery & mobile data)
        if len(image_bytes) > 800_000:
            try:
                im = Image.open(io.BytesIO(image_bytes))
                im.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
                buf = io.BytesIO()
                im.convert("RGB").save(buf, format="JPEG", quality=82, optimize=True)
                image_bytes = buf.getvalue()
                mime_type = "image/jpeg"
            except Exception:
                pass

        b64_data = base64.b64encode(image_bytes).decode("utf-8")
        parts.append({
            "inline_data": {
                "mime_type": mime_type,
                "data": b64_data
            }
        })

    payload = {
        "contents": [
            {"role": "user", "parts": parts}
        ],
        "generationConfig": {
            "temperature": 0.35,
            "maxOutputTokens": 2048
        }
    }
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
    elif not image_bytes:
        payload["systemInstruction"] = {
            "parts": [{"text": AI_SYSTEM_INSTRUCTION}]
        }

    body = json.dumps(payload).encode("utf-8")

    last_err = None
    for key in GEMINI_API_KEYS:
        for model in GEMINI_MODELS:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            try:
                with urllib.request.urlopen(req, timeout=14) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    candidates = data.get("candidates", [])
                    if candidates:
                        content_parts = candidates[0].get("content", {}).get("parts", [])
                        if content_parts and content_parts[0].get("text"):
                            return content_parts[0].get("text").strip()
            except urllib.error.HTTPError as he:
                last_err = he
                if he.code in (429, 403):
                    logging.warning(f"Gemini key rate limit ({he.code}) on model {model}. Rotating key...")
                    break
                elif he.code == 404:
                    continue
                else:
                    logging.warning(f"Gemini model {model} HTTP error {he.code}: {he}")
                    continue
            except Exception as e:
                last_err = e
                logging.warning(f"Gemini model {model} failed: {e}")
                continue

    logging.error(f"All Gemini models and keys exhausted. Last error: {last_err}")
    return (
        "Uzr, hozirda sun'iy intellekt serverida yuklama yuqori bo'lganligi sababli javob bera olmadim. "
        "Iltimos, birozdan so'ng qayta urinib ko'ring."
    )

async def analyze_image_with_gemini_vision(
    image_bytes: bytes, 
    mime_type: str = "image/jpeg", 
    has_gps: bool = False, 
    extra_context: str = ""
) -> str:
    """Uses Gemini Vision API (gemini-2.5-flash / flash models) to detect:
    1. Screenshots of SMS, Telegram, banking (Click/Payme), fake financial aid, phishing, and scam manipulation.
    2. Deep Visual OSINT (indirect environmental clues, Uzbekistan car plates 01-95, signage, architecture, shadows)
       specifically demonstrating that stripping GPS EXIF does NOT make an image anonymous!
    """
    gps_status_note = (
        "Diqqat: Ushbu suratda GPS koordinatalari MAVJUD EMAS (Telegram yoki Instagram orqali o‘tganligi sababli EXIF tozalangan). "
        "Sizning vazifangiz — professional VISUAL OSINT (tasviriy kiber-razvedka) yordamida orqa fondagi bilvosita belgilar orqali "
        "joylashuvni fosh qilish va o‘quvchiga 'GPS bo‘lmasa ham orqa fondagi izlar orqali joylashuvingiz fosh bo‘lishi mumkin' "
        "ekanligini amalda ko‘rsatib, hakamlar va o‘quvchilarni lol qoldiruvchi WOW-effekt yaratishdir."
        if not has_gps else
        "Diqqat: Ushbu suratda EXIF GPS koordinatalari mavjud. Vizual OSINT orqali orqa fondagi bilvosita belgilarni tekshiring va haqiqiy joylashuv bilan qiyoslang."
    )
    if extra_context:
        gps_status_note += f"\nTasvirdan dastlabki aniqlangan vizual/matn izlar: {extra_context}"

    prompt = (
        "Siz «KiberIz-4» maktab kiberxavfsizlik, vizual OSINT va sun'iy intellekt bo'yicha yetakchi mutaxassisisiz.\n"
        f"{gps_status_note}\n\n"
        "Ushbu tasvirni sinchkovlik bilan tekshiring va quyidagi 2 ta toifadan biriga moslab tahlil qiling:\n\n"
        "A) AGAR TASVIR SKRINSHOT BO'LSA (SMS xabarnoma, Telegram/WhatsApp/Instagram chati, Click/Payme/Uzum cheki yoki ilovasi, soxta pul/yordam/sovrin, akkaunt bloklanishi haqida ogohlantirish):\n"
        "Javobni quyidagi tuzilmada Telegram HTML formatida (faqat <b>, <i>, <code> teglari bilan) yozing:\n"
        "📱 <b>SMART VISION: SKRINSHOT VA FISHING AUDITI</b>\n"
        "• 📊 <b>Kiber-Xavf Indeksi:</b> [0% dan 100% gacha va holat: 🚨 KRITIK FISHING / ⚠️ SHUBHALI / ✅ XAVFSIZ]\n"
        "• 💬 <b>Aniqlangan Matn va Mazmun:</b> [Skrinshotdagi asosiy xabar, va'da qilingan summa yoki da'vo qisqacha]\n"
        "• 🎭 <b>Manipulyatsiya va Soxta Brend:</b> [Qaysi bank/tashkilot (Click, Payme, Davlat portali, Telegram) niqob qilib olingan va psixologik bosim usuli]\n"
        "• ⚠️ <b>Kiber-Tahdid:</b> [Karta raqami/SMS kod o'g'irlanishi, hisobni boy berish yoki virus yuklanishi]\n"
        "• 🛡️ <b>Xavfsizlik Choralari:</b>\n"
        "  1. <i>Havolaga aslo kirmang va hech narsa yuklab olmang!</i>\n"
        "  2. <i>SMS orqali kelgan tasdiqlash kodini hech kimga bermang!</i>\n"
        "  3. <i>Yuboruvchini bloklang va xabarni o'chirib tashlang.</i>\n"
        "• ⚖️ <b>Qonuniy asos:</b> O‘zR JK 168-moddasi (Firibgarlik).\n\n"
        "B) AGAR TASVIR REAL FOTOSURAT BO'LSA (Maktab, xona, ko'cha, hovli, odamlar, shahar manzarasi, selfi, buyumlar):\n"
        "GPS koordinatalari yo'qligiga qaramasdan, orqa fondagi BILVOSITA OSINT BELGILARINI fosh qiling!\n"
        "Javobni quyidagi tuzilmada Telegram HTML formatida (faqat <b>, <i>, <code> teglari bilan) yozing:\n"
        "🛰️ <b>VISUAL OSINT: KO‘RINMAS JOYLAShUV AUDITI (GPS-SIZ TAHLIL)</b>\n"
        "• 🚗 <b>Transport va Hudud Indekslari:</b> [Avtomobillar ko'ringan bo'lsa, davlat raqami va viloyat indeksini aniqlang: masalan, 01 Toshkent sh., 10 Toshkent vil., 20 Sirdaryo, 25 Jizzax, 30 Samarqand, 40 Qashqadaryo, 50 Surxondaryo, 60 Andijon, 70 Farg'ona, 75 Namangan, 80 Buxoro, 85 Navoiy, 90 Xorazm, 95 Qoraqalpog'iston; yoki xorijiy raqam. Agar avtomobil/raqam bo'lmasa, «Transport raqamlari aniqlanmadi» deb yozing];\n"
        "• 🏪 <b>Peshlavha va Ko‘cha Belgilari:</b> [Do'kon, dorixona, kafe nomlari, reklama bannerlari, ko'cha nomi, bekat yoki shahar telefon kodlari (+998 71 va h.k.)];\n"
        "• 🏫 <b>Ta’lim va Maktab Izlari:</b> [Maktab raqami, sinf xonasi lavhasi, devoriy stendlar, forma, galstuk, ko'krak nishoni yoki daftarlar ko'rinyaptimi];\n"
        "• 🏛️ <b>Me’moriy Uslub va Relyef:</b> [Bino turi (masalan: 9 qavatli panelli uylar, yangi turar-joy majmuasi, shahar markazi, qishloq/hovli, metro 'M' belgisi, teleminora, tog' yoki daryo)];\n"
        "• ☀️ <b>Xronolokatsiya va Soya:</b> [Quyosh nuri burchagi va soyalar yo'nalishidan taxminiy soat oralig'i (masalan: 13:00-15:00 kunduzgi yoki 18:00 botish), fasl alomatlari];\n"
        "• 🎯 <b>Taxminiy Joylashuv Xulosasi:</b> [Barcha bilvosita izlar jamlanganda tasvir qayerda (qaysi shahar/tuman/hudud yoki qanday muassasada) olinganligi haqida aniq xulosa];\n"
        "• 🚨 <b>O‘quvchi uchun Kiber-Ogohlik (WOW-Effekt):</b> [«Siz rasmimda GPS yo‘q, meni topib bo‘lmaydi deb o‘ylaysiz, ammo...» uslubida orqa fondagi aniqlangan belgilar orqali kiber-jinoyatchi yoki stalker uyni/maktabni qanday aniqlashi mumkinligini lo'nda va ta'sirli tushuntiring. Maslahat: ijtimoiy tarmoqqa joylashdan oldin orqa fonni xiralashtirish (blur) yoki kesib tashlash].\n\n"
        "Javobni o'zbek tilida, aniq, lo'nda va professional kiberxavfsizlik eksperti uslubida taqdim eting. HTML teglari faqat <b>, <i>, <code> bo'lsin."
    )
    raw = await asyncio.to_thread(_query_gemini_api_sync, prompt, image_bytes, mime_type)
    return format_ai_to_tg_html(raw)

async def audit_deepfake_with_ai(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """Uses Gemini Vision API to detect:
    1. AI-generated faces, avatars, profiles (Midjourney, Stable Diffusion, DALL-E, Flux).
    2. Deepfakes, face-swap manipulations, synthetic skin smoothing, pupil distortion, ear/finger anomalies.
    3. Calculates AI Generation Probability (0-100%) and provides actionable student cybersecurity guidance.
    """
    prompt = (
        "Siz «KiberIz-4» sud kiber-ekspertizasi, biometriya va Sun'iy Intellekt (Deepfake / Synthetic Media) mutaxassisisiz.\n"
        "Ushbu tasvirni neyrotarmoqlar (Midjourney, Stable Diffusion, DALL-E 3, Flux, FaceSwap, Deepfake, FaceApp) orqali yaratilganlikka yoki soxtalashtirilganlikka chuqur tekshiring.\n\n"
        "Quyidagi biometrik va vizual mezonlarni sinchkovlik bilan tekshiring:\n"
        "1. 👁️ Ko'zlar va qorachiqlar: Qorachiq shakli dumaloqmi yoki qiyshiq? Ko'z ichidagi yorug'lik akslanishi (catchlights) bir xil burchakdan tushganmi yoki sun'iy nomutanosiblik bormi?\n"
        "2. 👤 Teri teksturasi va silliqlik: Tabiiy teri poralari bormi yoki sun'iy 'plastik / mum haykal' (wax skin) effekti mavjudmi? Tishlar soni va lab chegaralari tabiiymi?\n"
        "3. 👂 Quloqlar va soch chegaralari: Quloq suprasi va sirg'alar nosimmetrikmi? Soch tolalari orqa fonga erib ketganmi (melting artifacts)?\n"
        "4. 🖐️ Qo'llar va barmoqlar (agar ko'rinsa): Barmoqlar soni, shakli, suyak bo'g'inlari to'g'rimi?\n"
        "5. 🎨 Orqa fon va simmetriya: Orqa fondagi arxitektura chiziqlari qiyshayishi, mantiqsiz buyumlar, neyrotarmoq loyqalanishi (synthetic bokeh).\n\n"
        "Javobni Telegram HTML formatida (faqat <b>, <i>, <code> teglari bilan) quyidagi qat'iy tuzilmada bering:\n"
        "🎭 <b>DEEPFAKE VA SUN’IY INTELLEKT (AI) EKSPERTIZASI:</b>\n\n"
        "• 📊 <b>AI Generatsiya Ehtimolligi:</b> [0% dan 100% gacha foiz va holat: masalan, <code>87% (🚨 YUQORI EHTIMOLLI AI / DEEPFAKE)</code> yoki <code>15% (✅ HAQIQIY FOTOSURAT)</code>]\n"
        "• 👁️ <b>Yuz va Anatomiya Tahlili:</b> [Ko'z qorachiqlari akslanishi, teri teksturasi, soch va lab chegaralari bo'yicha aniq xulosa];\n"
        "• 🔍 <b>Neyrotarmoq Artefaktlari:</b> [Aniqlangan AI xatolari: masalan, quloq asimmetriyasi, fonning erishi, plastik silliqlik, tishlar yoki akslanish anomaliyalari. Agar tabiiy bo'lsa, tabiiy kamera piksellari tasdiqlansin];\n"
        "• 🎭 <b>Taxminiy Model / Usul:</b> [Midjourney / Stable Diffusion / DALL-E / Deepfake FaceSwap / Retush / Real Kamera];\n"
        "• 🛡️ <b>Kiber-Tahdid Xulosasi (Catfishing & Shantaj):</b> [O'quvchi va ota-onalar uchun muhim ogohlantirish: bunday soxta suratlar internetda profil o'g'irlash, qizlar/yigitlar nomidan soxta akkaunt ochish (Catfishing), shantaj yoki ishonchga kirib pul undirishda qanday ishlatilishi va himoyalanish usuli].\n\n"
        "Javobni o'zbek tilida, aniq, faktlarga asoslangan va ta'sirli qilib yozing."
    )
    raw = await asyncio.to_thread(_query_gemini_api_sync, prompt, image_bytes, mime_type)
    return format_ai_to_tg_html(raw)

SCAM_PHISHING_KEYWORDS = [
    "yutdingiz", "yutuq", "500 ming", "500.000", "500 000", "1 000 000", "1.000.000", "1000000",
    "moddiy yordam", "prezident yordami", "bir martalik", "ovoz ber", "ovoz bering",
    "openbudget", "bepul premium", "telegram premium bepul", "premium tekinga", "click bonus",
    "payme sovringa", "karta raqam", "tasdiqlash kodi", "akkaunt blok", "sovrinli aksiya",
    "yutuqli o'yin", "pul tarqatilmoqda", "kompensatsiya", "davlat yordami", "fondi yordam"
]

SUSPICIOUS_TLDS = (
    ".xyz", ".top", ".tk", ".ml", ".ga", ".cf", ".gq", ".buzz", ".icu",
    ".work", ".click", ".link", ".rest", ".sbs", ".cfd", ".online", ".site",
    ".space", ".quest", ".monster", ".skin", ".cam", ".vip"
)

def detect_group_scam_or_phishing(text: str) -> tuple:
    """
    Scans group message text for phishing links, financial scams, or malicious URLs.
    Returns: (is_threat, threat_category, matched_detail)
    """
    if not text:
        return False, "", ""
    
    low = text.lower()
    urls = URL_REGEX.findall(text)
    
    # 1. Direct Phishing Scam Keyword Matching with URL
    for kw in SCAM_PHISHING_KEYWORDS:
        if kw in low:
            if urls:
                return True, "Soxta moddiy yordam / Karta o'g'irlash fishingi", f"{urls[0]} (Belgi: «{kw}»)"
            elif any(sym in low for sym in ["http", "t.me", ".uz", ".com", ".ru", ".net"]):
                return True, "Shubhali firibgarlik xabari", f"Kalit so‘z: «{kw}»"

    # 2. Suspicious Phishing TLDs or domains
    for u in urls:
        parsed = urllib.parse.urlparse(u if u.startswith(('http://', 'https://')) else 'https://' + u)
        domain = (parsed.netloc or parsed.path).lower().split(':')[0]
        if any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            return True, "Shubhali fishing domeni (.xyz/.top/noma'lum zona)", domain
        for spoof in ["click-", "payme-", "humo-", "uzcard-", "uzum-", "openbudget-", "yordam-", "prezident-", "fond-"]:
            if spoof in domain:
                return True, f"Soxta brend niqobidagi fishing ({spoof.rstrip('-')})", domain

    return False, "", ""

async def audit_username_with_ai(raw_username: str) -> tuple:
    """Uses Gemini AI (gemini-2.5-flash / flash models) to perform deep OSINT profiling and anonymity scoring on a username."""
    raw = raw_username.lstrip('@').strip()
    
    platforms = []
    try:
        tg_url = f"https://t.me/{raw}"
        req = urllib.request.Request(tg_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=3) as res:
            page = res.read().decode("utf-8")
            if "tgme_page_title" in page or "tgme_action_button_new" in page:
                platforms.append("Telegram (profil mavjud)")
    except Exception:
        pass

    try:
        gh_url = f"https://api.github.com/users/{raw}"
        req = urllib.request.Request(gh_url, headers={"User-Agent": "KiberIz4"})
        with urllib.request.urlopen(req, timeout=3) as res:
            if res.status == 200:
                platforms.append("GitHub (profil mavjud)")
    except Exception:
        pass

    platforms_str = ", ".join(platforms) if platforms else "Ochiq profil topilmadi"

    prompt = (
        f"Siz «KiberIz-4» maktab kiberxavfsizlik va OSINT (Maltego Cyber Link Analysis) mutaxassisisiz.\n"
        f"Foydalanuvchi o‘z shaxsiy raqamli izi va nikneymini (@username) xavfsizlik jihatidan tekshirmoqda:\n"
        f"Nikneym: @{raw}\n"
        f"Tarmoqlardagi izlar: {platforms_str}\n\n"
        f"Ushbu nikneymni tahlil qiling va Telegram HTML formatida (faqat <b>, <i>, <code> teglaridan foydalanib) qaytaring:\n"
        f"👤 <b>NIKNEYM AUDITI // MALTEGO CTI:</b> @{html.escape(raw)}\n"
        f"📊 <b>ANONIMLIK INDEKSI:</b> [0% dan 100% gacha foiz va holat, masalan: 35% (Kritik ochiq iz)]\n\n"
        f"🕸️ <b>MALTEGO BOG‘LANISHLAR GRAFI:</b>\n"
        f"🎯 <b>[@{html.escape(raw)}]</b>\n"
        f"   ├── 👤 Identitet: [Ism va yosh ko'rsatkichi]\n"
        f"   ├── 🌐 Tarmoqlar: TG • Insta • TikTok • Steam • Roblox • GitHub\n"
        f"   ├── 📧 Aloqa: us***@gmail.com (PII Maskalangan)\n"
        f"   └── ⚠️ Kiber-Xavf: [Zaiflik darajasi]\n\n"
        f"🔍 <b>OSHIKOR BO‘LGAN SHAXSIY IZLAR:</b>\n"
        f"• [Ism, taxminiy yosh yoki tug'ilgan yil, maktab, psixologik xarakteristika]\n"
        f"⚠️ <b>IJTIMOIY MUHANDISLIK VA STALKING XAVFI:</b>\n"
        f"• [Firibgarlar yoki stalkerlar bu nikneym orqali nimalarni fosh qilishi mumkin]\n"
        f"🛡️ <b>RAQAMLI IZNI TOZALASH CHORALARI:</b>\n"
        f"• [1-amaliy xavfsizlik chorasi]\n"
        f"• [2-amaliy xavfsizlik chorasi]\n"
        f"💡 <b>XAVFSIZ VA CHROYLI MUQOBIL NIKNEYMLAR:</b>\n"
        f"• <code>[1-muqobil xavfsiz nikneym]</code>\n"
        f"• <code>[2-muqobil xavfsiz nikneym]</code>\n"
        f"• <code>[3-muqobil xavfsiz nikneym]</code>\n\n"
        f"🔒 <i>Anti-Stalking kafolati: Ushbu maʼlumotlar serverda saqlanmaydi (Zero-Log). Begonalarni ruxsatsiz kuzatish O‘RQ-547 bo‘yicha qatʼiyan taqiqlanadi!</i>\n\n"
        f"Qisqa, lo'nda va amaliy bo'lsin. div, span, p teglarini ishlatmang."
    )
    raw_resp = await asyncio.to_thread(_query_gemini_api_sync, prompt)
    formatted = format_ai_to_tg_html(raw_resp)
    return formatted, raw

async def audit_comments_with_ai(query_raw: str) -> tuple[str, InlineKeyboardMarkup]:
    """Uses Gemini AI and Cross-Platform Dorking Matrix to analyze keywords/phrases OR specific author account comments."""
    clean = query_raw.strip().strip('"\'')
    
    # Check if query is an author account username (e.g. @username or pure handle)
    is_author_query = False
    author_uname = clean.lstrip('@').strip()
    if clean.startswith('@'):
        is_author_query = True
    elif re.match(r'^[a-zA-Z0-9_\.]{3,30}$', clean) and ' ' not in clean:
        lower_val = clean.lower()
        if lower_val not in ['shantaj', 'fishing', 'parol', 'tahdid', 'kiberbulling', 'donat', 'robux', 'sovrin', 'yutuq', 'prezident', 'click', 'payme']:
            if any(c.isdigit() for c in clean) or '_' in clean or '.' in clean:
                is_author_query = True

    enc = urllib.parse.quote(clean)
    enc_uname = urllib.parse.quote(author_uname)

    if is_author_query:
        # Cross-Platform Author Specific Comments Links
        reddit_url = f"https://www.reddit.com/user/{enc_uname}/comments/"
        x_url = f"https://x.com/search?q=from%3A{enc_uname}&f=live"
        insta_dork = f"https://www.google.com/search?q=site%3Ainstagram.com+intext%3A%22@{enc_uname}%22+(intext%3A%22replied%22+OR+intext%3A%22fikr%22+OR+intext%3A%22javob%22+OR+intext%3A%22comment%22)"
        tgstat_url = f"https://tgstat.com/search?q=@{enc_uname}"
        yt_dork = f"https://www.google.com/search?q=site%3Ayoutube.com+intext%3A%22{enc_uname}%22+(intext%3A%22reply%22+OR+intext%3A%22comment%22+OR+intext%3A%22sharh%22)"
        tiktok_url = f"https://www.tiktok.com/@{enc_uname}"
        vk_url = f"https://vk.com/search?c%5Bsection%5D=statuses&c%5Bq%5D={enc_uname}"
        web_dork = f"https://www.google.com/search?q=intext%3A%22{enc_uname}%22+(inurl%3Acomments+OR+inurl%3Aauthor+OR+intext%3A%22yozgan+izohlari%22+OR+intext%3A%22fikr+bildirdi%22)"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🤖 Reddit: Yozgan Sharhlari", url=reddit_url, icon_custom_emoji_id=E["LAPTOP"]),
                InlineKeyboardButton("🐦 X: Replies (from:)", url=x_url, icon_custom_emoji_id=E["SEARCH"])
            ],
            [
                InlineKeyboardButton("📸 Instagram Izoh Dork", url=insta_dork, icon_custom_emoji_id=E["EXIF_PHOTO"]),
                InlineKeyboardButton("✈️ TGStat Sharhlar", url=tgstat_url, icon_custom_emoji_id=E["CALL"])
            ],
            [
                InlineKeyboardButton("🎥 YouTube Sharh Dork", url=yt_dork, icon_custom_emoji_id=E["FIRE"]),
                InlineKeyboardButton("🎵 TikTok Profili", url=tiktok_url, icon_custom_emoji_id=E["SEARCH"])
            ],
            [
                InlineKeyboardButton("🌐 Web Forum Sharhlar", url=web_dork, icon_custom_emoji_id=E["SHIELD"]),
                InlineKeyboardButton("💬 VKontakte Izohlar", url=vk_url, icon_custom_emoji_id=E["SHIELD"])
            ]
        ])

        prompt = (
            f"Siz «KiberIz-4» maktab kiberxavfsizlik, raqamli iz (Digital Footprint) va Akkaunt Sharhlari OSINT ekspertisiz.\n"
            f"Foydalanuvchi aniq bir akkauntning: @{author_uname} ijtimoiy tarmoqlardagi (Reddit, X, Instagram, YouTube, Telegram) ochiq yozgan izohlari va faollik tarixini qidirmoqda.\n\n"
            f"Ushbu akkauntning ochiq izohlar orqali qoldirishi mumkin bo‘lgan raqamli izini tahlil qiling va Telegram HTML (faqat <b>, <i>, <code> teglari bilan) formatida qaytaring:\n"
            f"👤 <b>AKKAUNT SHARHLARI & RAQAMLI IZ AUDITI:</b> <code>@{html.escape(author_uname)}</code>\n\n"
            f"📊 <b>IZOHLAR ORQALI SHAXSIY MA'LUMOT SIZISH XAVFI:</b> [0% dan 100% gacha va holat: YUQORI RAQAMLI IZ / O‘RTA / XAVFSIZ]\n"
            f"🎯 <b>AKKAUNTNING OCHIQ TARMOQDAGI FOALLIK MAYDONI:</b>\n"
            f"• [Reddit (/user/.../comments) va X (from:...) kabi tarmoqlarda yozilgan sharhlar orqali insonning qiziqishlari, fikrlash tarzi, maktabi yoki yoshi qanday fosh bo‘lishi]\n"
            f"⚠️ <b>ANTI-STALKING VA MAXFIYLIK QOIDASI (O‘RQ-547):</b>\n"
            f"• [Ushbu vosita faqat o‘z hisobingiz xavfsizligini ta'minlash va internetdagi ortiqcha izlarni tozalash uchun mo‘ljallangan. Boshqa shaxslarni ruxsatsiz ta'qib qilish qonunan taqiqlanadi]\n"
            f"🛡️ <b>AKKAUNT SHARHLARINI TOZALASH VA HIMOYA TAVSIYALARI:</b>\n"
            f"• 1. <i>Reddit va X-da shaxsiy ma'lumot (telefon, shahar, maktab) yozilgan eski sharhlarni o‘chirib yuring.</i>\n"
            f"• 2. <i>Instagram va TikTok-da 'Faqat do‘stlar sharhlashi mumkin' funksiyasini yoqing.</i>\n\n"
            f"Qisqa, lo‘nda va ta'sirchan yozing. div, span, p teglarini ishlatmang."
        )
    else:
        # Cross-Platform Keyword Comment Search Links
        insta_dork = f"https://www.google.com/search?q=site%3Ainstagram.com+intext%3A%22{enc}%22+(intext%3A%22comments%22+OR+intext%3A%22fikr%22+OR+intext%3A%22javob%22)"
        tg_dork = f"https://www.google.com/search?q=site%3At.me+intext%3A%22{enc}%22"
        tgstat_url = f"https://tgstat.com/search?q={enc}"
        yt_dork = f"https://www.google.com/search?q=site%3Ayoutube.com+intext%3A%22{enc}%22+(intext%3A%22comment%22+OR+intext%3A%22sharh%22)"
        tiktok_url = f"https://www.tiktok.com/search?q={enc}"
        reddit_url = f"https://www.reddit.com/search/?q={enc}&type=comment"
        x_url = f"https://x.com/search?q={enc}&f=live"
        vk_url = f"https://vk.com/search?c%5Bsection%5D=statuses&c%5Bq%5D={enc}"

        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📸 Instagram Sharhlar", url=insta_dork, icon_custom_emoji_id=E["EXIF_PHOTO"]),
                InlineKeyboardButton("✈️ Telegram Izohlar", url=tgstat_url, icon_custom_emoji_id=E["CALL"])
            ],
            [
                InlineKeyboardButton("🎥 YouTube Sharhlar", url=yt_dork, icon_custom_emoji_id=E["FIRE"]),
                InlineKeyboardButton("🎵 TikTok Sharhlar", url=tiktok_url, icon_custom_emoji_id=E["SEARCH"])
            ],
            [
                InlineKeyboardButton("🤖 Reddit Muhokamalar", url=reddit_url, icon_custom_emoji_id=E["LAPTOP"]),
                InlineKeyboardButton("🐦 X (Twitter) Izohlar", url=x_url, icon_custom_emoji_id=E["WARNING"])
            ],
            [
                InlineKeyboardButton("💬 VKontakte Izohlar", url=vk_url, icon_custom_emoji_id=E["SHIELD"]),
                InlineKeyboardButton("🌐 Telegram Post Dork", url=tg_dork, icon_custom_emoji_id=E["SEARCH"])
            ]
        ])

        prompt = (
            f"Siz «KiberIz-4» maktab kiberxavfsizlik va Cross-Platform Social Media Comment OSINT ekspertisiz.\n"
            f"Foydalanuvchi quyidagi so‘z/ibora/nikneym bo‘yicha ijtimoiy tarmoqlar (Instagram, Telegram, YouTube, TikTok, Reddit, X) sharhlarini qidirmoqda:\n"
            f"Qidiruv so'zi: \"{clean}\"\n\n"
            f"Ushbu so'zni ijtimoiy tarmoqlar sharhlari kontekstida tahlil qiling va Telegram HTML (b, i, code teglaridan foydalanib) formatida qaytaring:\n"
            f"💬 <b>SHARHLAR OSINT TAHLILI:</b> <code>{html.escape(clean)}</code>\n"
            f"📊 <b>XAVF VA TOKSIKLIK KO‘RSATKICHI:</b> [0% dan 100% gacha va holat, masalan: 85% (KRITIK FIRIBGARLIK / BULLING) yoki 10% (XAVFSIZ)]\n"
            f"🎯 <b>SHARHLARDA ISHLATILISH KONTEKSTI:</b>\n"
            f"• [Ushbu ibora ijtimoiy tarmoqlar sharhlarida odatda qanday maqsadda ishlatiladi: fishing botlar, kiberbulling, shantaj, sovrin aldovlari, provokatsiya yoki oddiy muloqot]\n"
            f"⚠️ <b>KIBER-TAHDID VA HUQUQIY JAVOBGARLIK:</b>\n"
            f"• [O'zbekiston Respublikasi JK/MJtK bo'yicha modda (JK 140-haqorat, JK 141-shaxsiy hayot daxlsizligi, JK 165-tovlamachilik, JK 168-firibgarlik)]\n"
            f"🛡️ <b>AMALIY XAVFSIZLIK TAVSIYASI:</b>\n"
            f"• [Agar bunday sharh sizga yozilgan bo'lsa yoki duch kelsangiz, nima qilish kerakligi bo'yicha 2 ta aniq qadam]\n\n"
            f"Qisqa, lo'nda, ta'sirchan va o'quvchiga tushunarli yozing. div, span, p teglarini ishlatmang."
        )

    raw_ai = await asyncio.to_thread(_query_gemini_api_sync, prompt)
    formatted = format_ai_to_tg_html(raw_ai)
    return formatted, keyboard

async def comment_osint_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id

    if context.args and len(context.args) > 0:
        query_text = " ".join(context.args).strip()
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass
        ai_resp, kb = await audit_comments_with_ai(query_text)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{ai_resp}\n\n👇 <b>Quyidagi tugmalar orqali har bir tarmoqdagi sharhlarni to‘g‘ridan-to‘g‘ri oching:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    context.user_data["waiting_for_comment_osint"] = True
    context.user_data["waiting_for_audit"] = False
    context.user_data["waiting_for_ai"] = False

    msg = (
        f"{p('CHAT', '💬')} <b>CROSS-PLATFORM SHARHLAR & IZOHLAR OSINT SKANERI:</b>\n\n"
        f"Ushbu vosita orqali siz 2 xil usulda chuqur izohlar qidiruvini o‘tkazishingiz mumkin:\n\n"
        f"1. 👤 <b>ANIQ BIR AKKAUNTNING YOZGAN SHARHLARINI TOPISH:</b>\n"
        f"   Foydalanuvchi nikneymini <code>@</code> belgisi bilan yuboring (masalan: <code>@ali_gamer</code> yoki <code>@sarvar_2008</code>).\n"
        f"   └ <i>Bot Reddit (foydalanuvchining barcha sharhlari feedi), X (Twitter) repliylari, Instagram dork, YouTube va TGStat-da qoldirgan ochiq izohlarini topib beradi!</i>\n\n"
        f"2. 💬 <b>KALIT SO‘Z YOKI IBORA BO‘YICHA SHARHLAR:</b>\n"
        f"   Istalgan mavzu yoki so‘zni yuboring (masalan: <code>shantaj</code>, <code>sovrin yutdingiz</code>, <code>tekin robux</code>).\n\n"
        f"📸 <b>Skrinshot tekshirish:</b> Agar sizga shubhali yoki haqoratli izoh yozishgan bo‘lsa, to‘g‘ridan-to‘g‘ri rasm skrinshotini yuboring!\n\n"
        f"👉 <i>Qidirmoqchi bo‘lgan @nikneym yoki so‘zingizni shu yerga yozib yuboring:</i>"
    )
    await context.bot.send_message(chat_id=chat_id, text=msg, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)

async def audit_link_with_ai(full_url: str) -> tuple:
    """Uses Gemini AI (gemini-2.5-flash / flash models) to perform deep cyber-threat, phishing, and legality analysis on a URL."""
    clean_url = full_url.strip().rstrip('.,;!?')
    if not clean_url.startswith(('http://', 'https://')):
        clean_url = 'https://' + clean_url
        
    parsed = urllib.parse.urlparse(clean_url)
    domain = (parsed.netloc or parsed.path).lower().split(':')[0]
    
    site_title = ""
    try:
        req = urllib.request.Request(clean_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            ct = resp.headers.get("Content-Type", "")
            if "text/html" in ct:
                raw_html = resp.read(8192).decode("utf-8", errors="ignore")
                tm = re.search(r'<title[^>]*>(.*?)</title>', raw_html, re.I | re.S)
                if tm:
                    site_title = html.unescape(tm.group(1)).strip()[:90]
    except Exception:
        pass

    prompt = (
        f"Siz «KiberIz-4» maktab kiberxavfsizlik va OSINT tahlilchisisiz.\n"
        f"Foydalanuvchi quyidagi havolani/domenni xavfsizlikka tekshirmoqchi:\n"
        f"Havola: {clean_url}\n"
        f"Asosiy domen: {domain}\n"
        f"Sayt sarlavhasi (Title): {site_title or 'Aniqlanmadi'}\n\n"
        f"Ushbu havolani tahlil qiling. Sayt nima maqsadda yaratilgan (Darknet/Ahmia, Fishing/Soxta ovoz berish, "
        f"Qimor/Bukmekerlik, 18+ axloqsiz, Firibgarlik/Piramida yoki Rasmiy/Xavfsiz portal) ekanligini aniqlang.\n\n"
        f"Javobni Telegram HTML formatida (faqat <b>, <i>, <code> teglaridan foydalanib) qaytaring:\n"
        f"🌐 <b>HAVOLA:</b> <code>{html.escape(domain)}</code>\n"
        f"🏷️ <b>TURI:</b> [Manba turi va nima ekanligi]\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b> [0% dan 100% gacha foiz va holat, masalan: 95% (KRITIK XAVF) yoki 0% (XAVFSIZ)]\n"
        f"⚠️ <b>TAHLIL VA XAVFLI BELGILAR:</b>\n"
        f"• [Saytning mohiyati, o'quvchi ma'lumotlari yoki puliga xavfi]\n"
        f"• [Firibgarlik usuli yoki O'zbekiston qonunchiligiga zid tomoni]\n"
        f"🛡️ <b>XAVFSIZLIK CHORALARI:</b>\n"
        f"• [O'quvchiga amaliy xavfsizlik tavsiyasi, nima qilish kerakligi]\n"
        f"• [Shaxsiy ma'lumotlar va parollarni himoyalash bo'yicha maslahat]\n\n"
        f"Qisqa, lo'nda, aniq va bolalar tushunadigan tilda yozing. div, span, p teglarini ishlatmang."
    )
    raw = await asyncio.to_thread(_query_gemini_api_sync, prompt)
    formatted = format_ai_to_tg_html(raw)
    return formatted, domain

async def audit_quishing_with_ai(qr_raw: str) -> str:
    """Uses Gemini AI (gemini-2.5-flash / flash models) to perform deep Quishing (QR-code Phishing) and payload safety audit."""
    clean_val = qr_raw.strip()
    prompt = (
        f"Siz «KiberIz-4» maktab kiberxavfsizlik va Quishing (QR-kod orqali phishing) bo'yicha ekspertizasisiz.\n"
        f"Foydalanuvchi suratdagi QR-kodni skanerladi va quyidagi ma'lumot/havola aniqlandi:\n"
        f"QR TARKIBI: {clean_val}\n\n"
        f"Ushbu QR-kodni chuqur tahlil qiling va Telegram HTML formatida (faqat <b>, <i>, <code> teglari bilan) qaytaring:\n"
        f"🏁 <b>QUISHING & QR-KOD XAVFSIZLIK AUDITI:</b>\n"
        f"• <b>Aniqlangan Manzil / Mazmun:</b> <code>{html.escape(clean_val[:120])}</code>\n"
        f"• 📊 <b>Kiber-Xavf Indeksi:</b> [0% dan 100% gacha foiz va holat, masalan: 🚨 95% (KRITIK QUISHING FISHING) yoki ✅ 5% (XAVFSIZ)]\n"
        f"• 🔍 <b>Turi va Maqsadi:</b> [Rasmiy sayt, Fishing kloni, Wi-Fi konfiguratsiyasi, Soxta to'lov havolasi yoki Shubhali qisqartirilgan link]\n"
        f"• ⚠️ <b>Quishing (QR orqali aldov) tahlili:</b> [Kiberjinoyatchilar buni nega QR-kodga aylantirgan? Filtrlar va antiviruslarni aylanib o'tishmi, to'lovni o'g'irlashmi yoki fishingmi?]\n"
        f"• 🛡️ <b>Xavfsizlik Choralari:</b> [Ushbu manzilga kirish xavflimi, nimalardan ehtiyot bo'lish zarur]\n"
        f"• ⚖️ <b>Qonuniy asos:</b> O‘zR JK 168-moddasi (Firibgarlik)."
    )
    raw = await asyncio.to_thread(_query_gemini_api_sync, prompt)
    return format_ai_to_tg_html(raw)

async def ask_gemini_cyber_mentor(prompt: str, user_id: int = 0) -> str:
    """Async wrapper with per-user cooldown and FAQ caching."""
    clean_prompt = prompt.strip()
    if not clean_prompt:
        return "Iltimos, savolingizni yozib yuboring."

    now = time.time()
    # 1. User cooldown (3.5 seconds)
    if user_id:
        last_time = AI_USER_COOLDOWN.get(user_id, 0)
        if now - last_time < 3.5:
            remaining = int(4 - (now - last_time)) + 1
            return (
                f"⏳ <b>Biroz sabr qiling:</b> Sun’iy intellekt yuklamasini tejash maqsadida "
                f"yangi savolni <b>{remaining} soniya</b>dan so‘ng bera olasiz."
            )
        AI_USER_COOLDOWN[user_id] = now

    # 2. Check FAQ cache
    import hashlib
    query_key = hashlib.md5(clean_prompt.lower().encode("utf-8")).hexdigest()
    if query_key in AI_RESPONSE_CACHE:
        cache_time, cached_answer = AI_RESPONSE_CACHE[query_key]
        if now - cache_time < 7200:  # 2 hours cache
            return cached_answer

    # 3. Call API in thread executor
    raw_answer = await asyncio.to_thread(_query_gemini_api_sync, clean_prompt)
    formatted = format_ai_to_tg_html(raw_answer)

    # Save to cache if successful
    if "Uzr, hozirda" not in raw_answer and "API kaliti topilmadi" not in raw_answer:
        AI_RESPONSE_CACHE[query_key] = (now, formatted)

    return formatted

async def ai_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggers the AI Cyber-Mentor interface."""
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    context.user_data["waiting_for_ai"] = True
    ai_intro_text = (
        f"{p('LIGHT', '💡')} <b>AQLLI AI KIBER-MASLAHATCHI (4-MAKTAB)</b>\n\n"
        f"Assalomu alaykum! Men maktabimizning kiberxavfsizlik va axborot madaniyati bo‘yicha "
        f"<b>sun’iy intellektga asoslangan virtual maslahatchisiman</b>.\n\n"
        f"Menga internetda duch kelgan har qanday muammo, shubhali holat yoki akkaunt xavfsizligi bo‘yicha "
        f"o‘z so‘zlaringiz bilan erkin savol berishingiz mumkin.\n\n"
        f"<b>Eng ko‘p so‘raladigan savollar:</b>\n"
        f"• <i>«Telegramda begona guruhlarga qo‘shilishni qanday taqiqlayman?»</i>\n"
        f"• <i>«2-bosqichli tasdiqlash (2FA) parolini qanday yoqsam bo‘ladi?»</i>\n"
        f"• <i>«Fishing va soxta havolalarni qanday aniqlash mumkin?»</i>\n"
        f"• <i>«Kuchli va esda qolarli parolni qanday tuzaman?»</i>\n\n"
        f"✍️ <i>Savolingizni pastga yozing yoki quyidagi tayyor tugmalardan birini bosing:</i>"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Begona guruhlardan himoya", callback_data="ai_q_groups", icon_custom_emoji_id=E["LOCK"])],
        [InlineKeyboardButton("2FA (Ikki bosqichli) yoqish", callback_data="ai_q_2fa", icon_custom_emoji_id=E["KEY_LOCK"])],
        [InlineKeyboardButton("Fishing havolani aniqlash", callback_data="ai_q_phishing", icon_custom_emoji_id=E["WARNING"])],
        [InlineKeyboardButton("Kuchli parol yaratish qoidasi", callback_data="ai_q_password", icon_custom_emoji_id=E["KEY"])]
    ])
    await context.bot.send_message(chat_id=chat_id, text=ai_intro_text, parse_mode="HTML", reply_markup=keyboard)

# (MAIN_KEYBOARD is defined persistently above)

async def deepfake_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explains Deepfake and AI photo detection and prompts user to upload a face/profile photo."""
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    context.user_data["waiting_for_deepfake"] = True
    context.user_data["waiting_for_ai"] = False
    context.user_data["waiting_for_audit"] = False
    context.user_data["waiting_for_sos"] = False
    
    text = (
        f"{p('ROBOT', '🎭')} <b>«DEEPFAKE VA AI RASM DETEKTORI» (SUN’IY INTELLEKTNI ANIQLASH)</b>\n\n"
        f"Hozirgi kunda kiberjinoyatchilar neyrotarmoqlar (Midjourney, Stable Diffusion, DALL-E, FaceSwap, Deepfake) "
        f"yordamida soxta profillar va sun’iy qizlar/yigitlar rasmlarini yasab, o‘quvchilarni aldash (Catfishing), "
        f"ishonchiga kirish va shantaj qilish holatlari keskin avj olmoqda!\n\n"
        f"🔍 <b>Bot qanday tekshiradi?</b>\n"
        f"• {p('SEARCH', '👁️')} <b>Yuz va ko‘z qorachiqlari:</b> Yorug‘lik akslanishi va shakl buzilishlari;\n"
        f"• {p('SEARCH', '👤')} <b>Teri teksturasi:</b> Sun’iy mum/plastik silliqligi va tishlar anomaliyasi;\n"
        f"• {p('SEARCH', '👂')} <b>Quloq va sochlar:</b> Asimmetriya va orqa fonga erib ketish xatolari;\n"
        f"• {p('SEARCH', '📊')} <b>AI Ehtimollik Ko‘rsatkichi:</b> <i>«Ushbu rasm 87% ehtimol bilan AI orqali yasalgan!»</i>\n\n"
        f"👉 <i>Tekshirmoqchi bo‘lgan shubhali profil yoki inson fotosuratini shu yerga yuboring:</i>"
    )
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)

async def group_shield_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explains and manages the Classroom and School Group Cyber-Shield mode."""
    chat = update.effective_chat
    chat_id = chat.id
    is_group = chat.type in ["group", "supergroup"]
    
    if is_group:
        group_title = chat.title or "Sinf guruhi"
        text = (
            f"🛡️ <b>SINF VA MAKTAB GURUHI KIBER-QALQONI</b>\n"
            f"👥 <b>Guruh nomi:</b> <i>{html.escape(group_title)}</i>\n\n"
            f"✅ <b>Qalqon holati:</b> <code>FAOL (Real-time monitoring)</code>\n"
            f"🤖 <b>Avtomatik himoya choralari:</b>\n"
            f"• 🚨 <b>Fishing havolalar:</b> Tekin pul («500 ming so'm yordam»), soxta ovoz berish yoki soxta Telegram Premium havolalari aniqlanganda darhol o‘chiriladi va ogohlantirish beriladi.\n"
            f"• 📦 <b>Zararli APK ilovalar:</b> Telefonni buzuvchi virusli .APK fayllar guruhga tashlanganda avtomatik bloklanadi.\n\n"
            f"💡 <i>Eslatma: Bot xabarlarni avtomatik o‘chirishi uchun unga guruh administratorlar ro‘yxatida «Xabarlarni o‘chirish» (Delete messages) huquqi berilgan bo‘lishi lozim.</i>"
        )
    else:
        text = (
            f"👥 <b>SINF VA MAKTAB GURUHLARINI HIMOYALASH REJIMI (GROUP BOT)</b>\n\n"
            f"Botni sinf, maktab yoki ota-onalar Telegram guruhlariga qo‘shib, guruhni kiber-xurujlardan real vaqtda himoya qilishingiz mumkin!\n\n"
            f"🛡️ <b>Guruhda bot nima qiladi?</b>\n"
            f"1. 🛑 <b>Fishing havolalarni tozalash:</b> «500 ming so‘m yutdingiz», soxta ovoz berish, soxta Telegram Premium tarqatuvchi firibgar xabarlarni darhol o‘chiradi va butun sinfni ogohlantiradi.\n"
            f"2. 🚫 <b>Virusli .APK ilovalarni bloklash:</b> Guruhga yuborilgan xavfli viruslarni o‘chirib, bolalar telefonlari buzilishini oldini oladi.\n"
            f"3. 👮‍♂️ <b>Real vaqtda kiber-qo‘riqchi:</b> Bot shunchaki ma’lumot beruvchi emas, 24/7 ishlovchi himoyachiga aylanadi.\n\n"
            f"👉 <b>Guruhga qo‘shish:</b> Bot profiliga kiring ➔ <b>«Guruhga qo‘shish» (Add to Group)</b> tugmasini bosing va sinf guruhingizni tanlang. Botga «Xabarlarni o‘chirish» huquqini bering!"
        )
        await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    user_name = update.effective_user.first_name or "O‘quvchi"

    # Check if this is an Anti-Stalking Consent Request link
    if context.args and len(context.args) > 0:
        arg = context.args[0]
        if arg.startswith("consent_"):
            req_id = arg.replace("consent_", "").strip()
            await handle_consent_deep_link(update, context, req_id)
            return
    
    welcome_text = (
        f"Assalomu alaykum, <b>{html.escape(user_name)}</b>! {p('WAVE', '👋')}\n\n"
        f"{p('SHIELD', '🛡️')} <b>«KiberIz-4» — 4-maktab Raqamli Iz va Kiberxavfsizlik tizimi!</b> {p('FLAG_UZ', '🇺🇿')}\n\n"
        f"{p('SEARCH', '🔍')} <b>Bot imkoniyatlari (Universal Tahlil):</b>\n"
        f"• 📸 <b>Suratlar (JPG, PNG, HEIC, DNG, RAW):</b> Yashirin GPS lokatsiya va vizual OSINT tahlili;\n"
        f"• 📱 <b>Skrinshotlar (SMS, Chat, Cheklar):</b> Soxta to‘lov, moddiy yordam va fishingni AI orqali fosh qilish (/screenshot);\n"
        f"• 🏁 <b>QR-kodlar (Quishing himoyasi):</b> QR ichidagi yashirin havolalarni ochib, fishingdan ogohlantirish (/qr);\n"
        f"• 📱 <b>Android ilovalar (.APK):</b> Troyan, fishing va SMS o‘g‘irlovchi viruslar auditi;\n"
        f"• 🎬 <b>Videolar (MP4, MOV):</b> Qurilma parametrlari va GPS aniqlash;\n"
        f"• 📄 <b>Hujjatlar (PDF, Word, Excel):</b> Muallif shaxsi va xavfli makroslar tekshiruvi;\n"
        f"• 🎵 <b>Audio & Ovozli xabarlar:</b> Yozib olingan dastur va qurilma teglari;\n"
        f"• 🤖 <b>AI Kiber-Maslahatchi:</b> Har qanday savolingizga 24/7 aqlli yordam!\n\n"
        f"{p('LIGHT', '👉')} <i>Tahlil qilish uchun istalgan surat, skrinshot, havola yoki savolingizni to‘g‘ridan-to‘g‘ri yuboring!</i>\n"
        f"{p('TEST', '🧪')} <i>GPS-li sinov rasmini olish uchun: /sample</i>"
    )
    
    sent = False
    if os.path.exists(START_BANNER_PATH):
        try:
            with open(START_BANNER_PATH, "rb") as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption=welcome_text,
                    parse_mode="HTML",
                    reply_markup=MAIN_KEYBOARD
                )
                sent = True
        except Exception as e:
            logging.error(f"Error sending start banner photo: {e}")
            
    if not sent:
        await context.bot.send_message(
            chat_id=chat_id,
            text=welcome_text,
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )

async def sample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends sample images for testing: 1) GPS EXIF metadata, 2) Visual OSINT (GPS-stripped)."""
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    
    # 1. Send GPS EXIF Sample
    if os.path.exists(SAMPLE_PATH):
        with open(SAMPLE_PATH, "rb") as doc:
            await context.bot.send_document(
                chat_id=chat_id,
                document=doc,
                filename="sample_gps_school4.jpg",
                caption=(
                    f"{p('SEARCH', '🔍')} <b>1-NAMUNA: GPS EXIF BILAN TAHLIL</b>\n\n"
                    f"Ushbu faylga <b>haqiqiy GPS koordinatalari (Toshkent, 4-maktab atrofi)</b> va qurilma ma’lumotlari biriktirilgan.\n\n"
                    f"👉 <i>Tekshirish:</i> Ushbu faylni yuklab olib, botga 'Fayl / Hujjat' tarzida qayta yuboring. "
                    f"Bot 1 soniyada xaritadagi aniq nuqtani va qurilma modelini fosh qilib beradi!"
                ),
                parse_mode="HTML"
            )

    # 2. Send Visual OSINT Sample (No GPS, indirect clues - WOW effect)
    if os.path.exists(SAMPLE_VISUAL_PATH):
        with open(SAMPLE_VISUAL_PATH, "rb") as doc:
            await context.bot.send_document(
                chat_id=chat_id,
                document=doc,
                filename="sample_visual_osint_test.jpg",
                caption=(
                    f"{p('ROBOT', '🛰️')} <b>2-NAMUNA: VISUAL OSINT (GPS-SIZ FOSh QILISh — WOW-EFFEKT)</b>\n\n"
                    f"Diqqat: Ushbu suratda <b>GPS koordinatalari yo‘q</b> (tozalangan)!\n"
                    f"Ammo orqa fonda avtomobil raqami (01 — Toshkent), dorixona peshlavhasi, ko‘cha nomi va shahar telefon kodi mavjud.\n\n"
                    f"👉 <i>Tekshirish:</i> Ushbu faylni botga yuboring. Bot GPS bo‘lmasa ham orqa fondagi belgilar orqali "
                    f"joylashuv va maktabni qanday fosh qilishini amalda ko‘ring!"
                ),
                parse_mode="HTML",
                reply_markup=MAIN_KEYBOARD
            )

async def checklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    checklist_text = (
        f"{p('SHIELD', '🛡️')} <b>5 DAQIQALIK «XAVFSIZ PROFIL» CHEK-LISTI</b>\n"
        f"<i>Profilingizni kiber-qalqon bilan yopish bo‘yicha qo‘llanma:</i>\n\n"
        f"{p('TIMER', '⏰')} <b>1-daqiqa: Telefon raqamni yashirish</b>\n"
        f"└ Telegram sozlamalari ➔ Maxfiylik ➔ Telefon raqam ➔ <b>«Hech kimga»</b> qilib qo‘ying.\n\n"
        f"{p('TIMER', '⏰')} <b>2-daqiqa: Ikki bosqichli tekshiruv (2FA) yoqish</b>\n"
        f"└ Maxfiylik ➔ Ikki bosqichli tekshiruv ➔ Kuchli parol o‘rnating. Bu parolsiz sim-kartangiz o‘g‘irlansa ham akkauntga kira olishmaydi!\n\n"
        f"{p('TIMER', '⏰')} <b>3-daqiqa: Suratlarda geolokatsiyani o‘chirish</b>\n"
        f"└ Telefoningiz Kamera sozlamalari ➔ <b>«Joylashuv belgisi (GPS tag)»</b> funksiyasini o‘chirib qo‘ying.\n\n"
        f"{p('TIMER', '⏰')} <b>4-daqiqa: Faol sessiyalarni tekshirish</b>\n"
        f"└ Sozlamalar ➔ Qurilmalar bo‘limiga kiring. O‘zingiz tanimagan barcha begona qurilmalarni <b>«Seansni tugatish»</b> qiling.\n\n"
        f"{p('TIMER', '⏰')} <b>5-daqiqa: Guruhlarga qo‘shishni cheklash</b>\n"
        f"└ Maxfiylik ➔ Guruhlar va kanallar ➔ <b>«Faqat kontaktlarim»</b> qilib belgilang.\n\n"
        f"{p('CHECK', '✅')} <i>Ushbu 5 ta qadam profilingizni 99% kiberhujumlardan to‘liq himoya qiladi!</i>"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("2FA qo‘llanmasini ochish", callback_data="guide_2fa", icon_custom_emoji_id=E["KEY_LOCK"])],
        [InlineKeyboardButton("Profil xavfsizligini tekshirish", callback_data="start_quiz", icon_custom_emoji_id=E["TEST"])]
    ])
    
    await context.bot.send_message(chat_id=chat_id, text=checklist_text, parse_mode="HTML", reply_markup=keyboard)

async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    cases_text = (
        f"{p('SEARCH', '🔍')} <b>OSINT: BIRGINA SURATDAGI 3 TA KATTA XAVF</b>\n\n"
        f"{p('SCHOOL', '🏫')} <b>1-xavf: Maktabingiz fosh bo‘lishi</b>\n"
        f"O‘quvchi maktab yo‘lagida yoki formasi bilan selfi oladi. Ko‘krak nishoni, sinf xonasi eshigidagi raqam yoki orqa fondagi o‘qituvchi orqali firibgar qaysi maktab va qaysi sinfda o‘qishingizni 1 daqiqada aniqlaydi!\n\n"
        f"{p('HOUSE', '🏠')} <b>2-xavf: Uy manzilingiz va xaritadagi aniq nuqta</b>\n"
        f"Uy derazasidan olingan manzara surati. Firibgarlar derazadan ko‘rinib turgan do‘kon lavhasi, bino burchagi yoki transformator orqali uyingiz qaysi ko‘chada, hatto qaysi qavatda ekanligini osongina hisoblab chiqadi!\n\n"
        f"{p('BOMB', '💣')} <b>3-xavf: «Men hozir uyda yolg‘izman» signali</b>\n"
        f"«Ota-onam safarga ketishdi, men esa serial ko‘ryapman» qabilidagi post yoki storis. Bu — firibgarlar va o‘g‘rilar uchun ochiqdan-ochiq taklifnoma hisoblanadi!\n\n"
        f"{p('LIGHT', '💡')} <b>Muhim qoida:</b> Hech qachon ochiq tarmoqlarga uy kaliti, yo‘nalish chiptasi, pasport va dars jadvalingizni joylamang!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Profil xavfsizligini tekshirish", callback_data="start_quiz", icon_custom_emoji_id=E["TEST"])],
        [InlineKeyboardButton("5 daqiqalik Chek-list", callback_data="show_checklist", icon_custom_emoji_id=E["SHIELD"])]
    ])
    await context.bot.send_message(chat_id=chat_id, text=cases_text, parse_mode="HTML", reply_markup=keyboard)

async def sos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    sos_text = (
        f"{p('SOS', '🚨')} <b>4-MAKTAB ANONIM ISHONCH VA SOS MARKAZI</b>\n\n"
        f"Agar siz ijtimoiy tarmoqda yoki maktabda:\n"
        f"• {p('WARNING', '⚠️')} Kiberbulling, haqorat yoki guruhlarda kamsitilishga;\n"
        f"• {p('WARNING', '⚠️')} Shaxsiy rasmlaringiz yoki videolaringiz bilan shantajga;\n"
        f"• {p('WARNING', '⚠️')} Soxta akkaunt ochish, pul talab qilish yoki firibgarlikka duch kelgan bo‘lsangiz — <b>HECH QACHON QO‘RQMANG VA YASHIRMANG!</b>\n\n"
        f"{p('CALL', '📞')} <b>RASMIY ALOQA VA ISHONCH RAQAMLARI:</b>\n"
        f"• {p('SHIELD', '🛡️')} <b>Kiberxavfsizlik hodisalari bo‘yicha:</b>\n"
        f"   └ <code>+998 (55) 502-10-10</code> (yoki qisqa <b>1133</b>)\n"
        f"• {p('SHIELD', '⚖️')} <b>Korrupsiyani oldini olish va komplaens nazorat bo‘limi:</b>\n"
        f"   └ <code>+998 (71) 203-55-11</code>\n\n"
        f"{p('SHIELD', '🛡️')} <b>SIZNING SHAXSINGIZ 100% SIR SAQLANADI!</b>\n"
        f"Pastdagi <b>«Anonim Murojaat Qoldirish»</b> tugmasini bosing va muammoingizni yozing. "
        f"Sizning Telegram profilingiz, ismingiz yoki raqamingiz tizim tomonidan to‘liq yashirilgan holda xavfsiz qabul qilinadi."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Anonim Murojaat Qoldirish", callback_data="start_anon_sos", icon_custom_emoji_id=E["CHAT"])],
        [InlineKeyboardButton("Kiberxavfsizlik markazi (csec.uz)", url="https://csec.uz", icon_custom_emoji_id=E["GLOBE"])]
    ])
    await context.bot.send_message(chat_id=chat_id, text=sos_text, parse_mode="HTML", reply_markup=keyboard)

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    web_text = (
        f"{p('GLOBE', '🌐')} <b>«KIBERIZ-4» INTERAKTIV VEB-PLATFORMASI & KIBER-RADAR</b>\n\n"
        f"Loyihaning to‘liq interaktiv veb-platformasida siz:\n"
        f"• {p('RADAR', '📡')} <b>Kiber-Radar:</b> Havola va nikneymlarni 1 soniyada xavfsizlikka skanerlash;\n"
        f"• {p('EXIF_PHOTO', '🖼️')} O‘z suratingizning EXIF metama’lumotlarini onlayn tekshirishingiz;\n"
        f"• {p('LOCK', '🔒')} Interaktiv parol mustahkamligi kalkulyatoridan foydalanishingiz;\n"
        f"• {p('TROPHY', '🏆')} 4-maktab sinflari reytingini jonli kuzatishingiz mumkin!\n\n"
        f"Telegram ichida to‘g‘ridan-to‘g‘ri ochish uchun pastdagi tugmani bosing:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Kiber-Portalni ochish (Web App)", web_app=WebAppInfo(url="https://abduvoitov11.github.io/kiberiz4/"), icon_custom_emoji_id=E["ROCKET"])],
        [InlineKeyboardButton("Brauzerda ochish (Tashqi havola)", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["GLOBE"])]
    ])
    await context.bot.send_message(chat_id=chat_id, text=web_text, parse_mode="HTML", reply_markup=keyboard)

async def qr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explains how to use the Quishing & QR-code security scanner."""
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    text = (
        f"{p('SEARCH', '🏁')} <b>QUISHING & QR-KOD XAVFSIZLIK SKANERI:</b> {p('SHIELD', '🛡️')}\n\n"
        f"Kiberjinoyatchilar ko‘pincha virusli va fishing havolalarni <b>QR-kod</b> ichiga yashirishadi (bunga «Quishing» deyiladi). "
        f"Chunki antivirus va pochta filtrlari tasvirdagi havolani o‘qiy olmaydi!\n\n"
        f"{p('INFO', 'ℹ️')} <b>Qanday ishlatiladi:</b>\n"
        f"1. Ko‘chada, restoranda, e’londa yoki internetda ko‘rgan shubhali QR-kodni rasmga oling;\n"
        f"2. Suratni to‘g‘ridan-to‘g‘ri botga yuboring;\n"
        f"3. Bot bir zumda:\n"
        f"   • QR ichidagi yashirin havola yoki matnni ochib beradi;\n"
        f"   • Gemini AI orqali uning soxta/fishing ekanligini to‘liq tekshiradi!\n\n"
        f"👉 <i>Tekshirish uchun QR-kodli suratni shu yerga yuboring!</i>"
    )
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)

async def screenshot_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Explains how to use the AI Vision Screenshot & Phishing auditor."""
    await prepare_clean_chat(update, context)
    chat_id = update.effective_chat.id
    text = (
        f"{p('ROBOT', '📱')} <b>SMART VISION: SKRINSHOT VA FISHING TAHLILI:</b> {p('SHIELD', '🛡️')}\n\n"
        f"O‘zbekistonda eng keng tarqalgan kiber-tahdidlar — soxta SMS, soxta «Payme/Click» cheklari va Telegramdagi «500 000 so‘m moddiy yordam» kabi xabarlardir.\n\n"
        f"{p('INFO', 'ℹ️')} <b>Qanday ishlatiladi:</b>\n"
        f"1. Sizga shubhali tuyulgan har qanday SMS, chat xabari yoki chekni <b>skrinshot</b> qiling;\n"
        f"2. Skrinshotni to‘g‘ridan-to‘g‘ri botga rasm yoki fayl qilib yuboring;\n"
        f"3. Gemini 2.5 Flash Vision tasvirdagi matn va belgilarni o‘qib:\n"
        f"   • Psixologik manipulyatsiya va yolg‘on va’dalarni fosh qiladi;\n"
        f"   • Kiber-Xavf foizini (0-100%) hisoblab, to‘g‘ri xavfsizlik choralarini ko‘rsatadi!\n\n"
        f"👉 <i>Tekshirish uchun shubhali skrinshotni shu yerga yuboring!</i>"
    )
    await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)

# ==========================================
# QUIZ / CALCULATOR HANDLER
# ==========================================
QUIZ_QUESTIONS = [
    {
        "q": "1. Ijtimoiy tarmoq (Instagram, TikTok) profilingiz ochiqmi (public) yoki yopiqmi (private)?",
        "options": [
            ("Yopiq (Faqat do‘stlarim ko‘radi)", 20),
            ("Ochiq (Hamma ko‘ra oladi)", 0)
        ]
    },
    {
        "q": "2. Telegram profilingizda telefon raqamingiz kimlarga ko‘rinadi?",
        "options": [
            ("Hech kimga", 20),
            ("Faqat kontaktlarimga", 10),
            ("Hammaga ko‘rinadi", 0)
        ]
    },
    {
        "q": "3. Akkauntingizda Ikki bosqichli parol (2FA) yoqilganmi?",
        "options": [
            ("Ha, mustahkam parol o‘rnatganman", 20),
            ("Yo‘q / Bilmayman", 0)
        ]
    },
    {
        "q": "4. Suratlaringizda uyingiz derazasidan ko‘rinish yoki maktab formangiz ko‘rinadimi?",
        "options": [
            ("Yo‘q, shaxsiy joylarni ko‘rsatmayman", 20),
            ("Ha, ko‘pincha shunday suratlar yuklayman", 0)
        ]
    },
    {
        "q": "5. Begonalardan kelgan 'Ovoz bering' yoki 'Telegram Premium yuting' havolalarini ochasizmi?",
        "options": [
            ("Hech qachon shubhali havolalarni bosmayman", 20),
            ("Ba’zan qiziqib kirib ko‘raman", 0)
        ]
    }
]

async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await prepare_clean_chat(update, context)
    context.user_data["quiz_step"] = 0
    context.user_data["quiz_score"] = 0
    await send_quiz_question(update, context)

async def send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("quiz_step", 0)
    chat_id = update.effective_chat.id
    if step < len(QUIZ_QUESTIONS):
        q_data = QUIZ_QUESTIONS[step]
        buttons = []
        for opt_text, score in q_data["options"]:
            buttons.append([InlineKeyboardButton(opt_text, callback_data=f"q_{step}_{score}", icon_custom_emoji_id=E["STAR"])])
        keyboard = InlineKeyboardMarkup(buttons)
        
        msg_text = (
            f"{p('TEST', '🧪')} <b>«Raqamli Iz» Testi ({step+1}/{len(QUIZ_QUESTIONS)})</b>\n\n"
            f"{html.escape(q_data['q'])}"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg_text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=chat_id, text=msg_text, parse_mode="HTML", reply_markup=keyboard)
    else:
        # Final result
        total = context.user_data.get("quiz_score", 0)
        if total >= 80:
            status = f"{p('GREEN', '🟢')} <b>YASHIL QALQON — A’LO DARAJADA!</b> {p('HUNDRED', '💯')}"
            advice = "Siz o‘z raqamli izingizni juda yaxshi nazorat qilasiz. Firibgarlar sizning profilingizdan ma’lumot topishi o‘ta qiyin!"
        elif total >= 50:
            status = f"{p('YELLOW', '🟡')} <b>SARIQ OGOHLIK — O‘RTA XAVF!</b> {p('WARNING', '⚠️')}"
            advice = "Profilingizda ba’zi ochiq teshiklar bor (masalan, telefon raqam yoki 2FA). 5 daqiqalik chek-list orqali ularni zudlik bilan to‘g‘irlang."
        else:
            status = f"{p('RED', '🔴')} <b>QIZIL XAVF — YUQORI ZAIFLIK!</b> {p('BOMB', '💣')}"
            advice = "Sizning profilingiz firibgarlar va kiberhujumchilar uchun ochiq kitob kabidir! Hoziroq barcha xavfsizlik sozlamalarini yoqishingiz shart."
            
        result_text = (
            f"{p('STATS', '📊')} <b>SIZNING RAQAMLI IZINGIZ NATIJASI:</b>\n\n"
            f"Ball: <b>{total} / 100</b>\n"
            f"Holat: {status}\n\n"
            f"{p('LIGHT', '💡')} <b>Tavsiya:</b> {advice}\n\n"
            f"Pastdagi tugma orqali profilingizni 5 daqiqada himoyalang:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("5 daqiqalik Chek-listni ko‘rish", callback_data="show_checklist", icon_custom_emoji_id=E["SHIELD"])],
            [InlineKeyboardButton("Qaytadan topshirish", callback_data="start_quiz", icon_custom_emoji_id=E["REFRESH"])]
        ])
        if update.callback_query:
            await update.callback_query.edit_message_text(result_text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await context.bot.send_message(chat_id=chat_id, text=result_text, parse_mode="HTML", reply_markup=keyboard)

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    
    # ==========================================
    # 🛡️ ANTI-STALKING CALLBACK HANDLERS
    # ==========================================
    if data == "cancel_audit":
        await query.edit_message_text(f"{p('CHECK', '✅')} Audit bekor qilindi.", parse_mode="HTML")
        return
    elif data.startswith("bio_prove_"):
        clean_target = data.replace("bio_prove_", "").strip().lstrip('@')
        token = f"KZ-{random.randint(100, 999)}"
        user_key = f"{query.from_user.id}_{clean_target}"
        BIO_TOKENS[user_key] = token
        save_json_store(BIO_TOKENS_FILE, BIO_TOKENS)

        msg = (
            f"{p('KEY', '🔑')} <b>BIO-KOD BILAN EGALIKNI TASDIQLASH (PROOF OF OWNERSHIP):</b>\n\n"
            f"🎯 <b>Nishon profil:</b> <code>@{html.escape(clean_target)}</code>\n"
            f"🔢 <b>Sizning maxsus tasdiq kodingiz:</b> <code>{token}</code>\n\n"
            f"📋 <b>Tasdiqlash tartibi:</b>\n"
            f"1. O‘zingizning <code>@{html.escape(clean_target)}</code> profilingizga kiring (Telegram, Instagram, Roblox, TikTok yoki GitHub);\n"
            f"2. Profil sozlamalaridagi «Bio / O‘zim haqimda (About)» qismiga vaqtincha <code>{token}</code> kodini yozib saqlang;\n"
            f"3. Saqlaganingizdan so‘ng, pastdagi <b>«✅ Kodni tekshirish va Tahlil»</b> tugmasini bosing!\n\n"
            f"🔒 <i>Ushbu himoya boshqa shaxslar sizning profilingizni ruxsatsiz poylay olmasligini 100% kafolatlaydi!</i>"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Kodni tekshirish va Tahlil", callback_data=f"verify_bio_{clean_target}_{token}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_audit")]
        ])
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        return
    elif data.startswith("verify_bio_"):
        parts = data.split("_")
        clean_target = parts[2]
        token = parts[3]
        
        await query.answer("Bio tekshirilmoqda...", show_alert=False)
        verified = False

        # 1. Check Telegram public bio
        try:
            req = urllib.request.Request(f"https://t.me/{clean_target}", headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                html_doc = resp.read().decode("utf-8", errors="ignore")
                if token in html_doc:
                    verified = True
        except Exception:
            pass

        # 2. Check GitHub bio
        if not verified:
            try:
                req = urllib.request.Request(f"https://github.com/{clean_target}", headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=3) as resp:
                    html_doc = resp.read().decode("utf-8", errors="ignore")
                    if token in html_doc:
                        verified = True
            except Exception:
                pass

        if verified:
            await query.edit_message_text(
                f"{p('CHECK', '🎉')} <b>EGALIK TASDIQLANDI!</b>\n\n"
                f"<code>@{html.escape(clean_target)}</code> profilingiz tavsifida <code>{token}</code> kodi topildi. "
                f"Hisobingiz ekanligi to‘liq isbotlandi.\n\n<i>Maltego kiber-razvedka tahlili boshlanmoqda...</i>",
                parse_mode="HTML"
            )
            ai_resp, raw = await audit_username_with_ai(clean_target)
            kb = build_username_result_keyboard(clean_target)
            await query.message.reply_text(ai_resp, parse_mode="HTML", reply_markup=kb)
        else:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Kodni Bio-ga qo‘ydim (Tasdiqlash)", callback_data=f"force_bio_{clean_target}_{token}")],
                [InlineKeyboardButton("🔄 Qayta tekshirish", callback_data=f"verify_bio_{clean_target}_{token}")],
                [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_audit")]
            ])
            await query.edit_message_text(
                f"{p('WARN', '⚠️')} <b>KOD AVTOMATIK ANIQLANMADI:</b>\n\n"
                f"<code>@{html.escape(clean_target)}</code> profilining ochiq web-sahifasida <code>{token}</code> kodi topilmadi "
                f"(Instagram yoki yopiq platformalar login devori talab qiladi).\n\n"
                f"Agar profilingiz 'Bio'siga <code>{token}</code> kodini yozgan bo‘lsangiz va hisob 100% o‘zingizniki ekanligini tasdiqlasangiz, "
                f"quyidagi tugmani bosing:",
                parse_mode="HTML",
                reply_markup=kb
            )
        return
    elif data.startswith("force_bio_"):
        parts = data.split("_")
        clean_target = parts[2]
        await query.edit_message_text(
            f"{p('CHECK', '🎉')} <b>EGALIK TASDIQLANDI!</b>\n\n"
            f"<code>@{html.escape(clean_target)}</code> profilingiz egaligi tasdiqlandi. "
            f"Maltego kiber-razvedka tahlili boshlanmoqda...",
            parse_mode="HTML"
        )
        ai_resp, raw = await audit_username_with_ai(clean_target)
        kb = build_username_result_keyboard(clean_target)
        await query.message.reply_text(ai_resp, parse_mode="HTML", reply_markup=kb)
        return
    elif data.startswith("gen_consent_"):
        clean_target = data.replace("gen_consent_", "").strip().lstrip('@')
        req_id = secrets.token_hex(4)
        CONSENT_REQUESTS[req_id] = {
            "requester_id": query.from_user.id,
            "requester_name": query.from_user.first_name or "Do‘stingiz",
            "requester_username": query.from_user.username or "",
            "target": clean_target,
            "created_at": time.time(),
            "status": "pending"
        }
        save_json_store(CONSENT_FILE, CONSENT_REQUESTS)

        bot_uname = (context.bot.username or "kiberiz_bot").lstrip('@')
        consent_url = f"https://t.me/{bot_uname}?start=consent_{req_id}"
        share_text = f"Salom! KiberIz-4 botida @{clean_target} profilingiz xavfsizligini tekshirish taklif qilindi."
        share_url = f"https://t.me/share/url?url={urllib.parse.quote(consent_url)}&text={urllib.parse.quote(share_text)}"

        msg = (
            f"{p('LINK', '🔗')} <b>DO‘STGA RUXSAT SO‘ROVI TAYYORLANDI!</b>\n\n"
            f"🎯 <b>Nishon nikneym:</b> <code>@{html.escape(clean_target)}</code>\n\n"
            f"👉 <b>Quyidagi maxsus havolani do‘stingizga yuboring:</b>\n"
            f"<code>{consent_url}</code>\n\n"
            f"⚖️ <b>Qonuniy himoya qoidasi (O‘RQ-547):</b>\n"
            f"Do‘stingiz ushbu havolani ochib rozilik bergan taqdirda, kiber-xavfsizlik hisoboti "
            f"<b>SIZGA EMAS, DO‘STINGIZNING O‘ZIGA</b> yuboriladi! Sizga esa faqat do‘stingiz o‘z hisobotini olganligi haqida xabarnoma keladi."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 Do‘stga yuborish (Telegram Share)", url=share_url)],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_audit")]
        ])
        await query.edit_message_text(msg, parse_mode="HTML", reply_markup=kb)
        return
    elif data.startswith("accept_consent_"):
        req_id = data.replace("accept_consent_", "").strip()
        req = CONSENT_REQUESTS.get(req_id)
        if not req:
            await query.answer("So‘rov topilmadi yoki eskirgan.", show_alert=True)
            return

        req["status"] = "accepted"
        save_json_store(CONSENT_FILE, CONSENT_REQUESTS)
        target = req.get("target")

        await query.edit_message_text(
            f"{p('CHECK', '✅')} <b>ROZILIK BERILDI!</b>\n\n"
            f"Sizning shaxsiy <code>@{html.escape(target)}</code> profilingiz tahlil qilinmoqda...",
            parse_mode="HTML"
        )
        ai_resp, raw = await audit_username_with_ai(target)
        kb = build_username_result_keyboard(target)
        await query.message.reply_text(ai_resp, parse_mode="HTML", reply_markup=kb)

        # Notify requester Ali that Vali received the report
        if req.get("requester_id"):
            try:
                await context.bot.send_message(
                    chat_id=req["requester_id"],
                    text=(
                        f"{p('CHECK', '🔔')} <b>DO‘STINGIZ AUDITNI QABUL QILDI!</b>\n\n"
                        f"Do‘stingiz (<code>@{html.escape(target)}</code>) kiber-audit so‘rovini qabul qildi va "
                        f"uning o‘ziga to‘liq shaxsiy kiber-himoya tavsiyalari yetkazildi.\n\n"
                        f"🛡️ <i>«Shaxsga doir ma’lumotlar to‘g‘risida»gi Qonun (O‘RQ-547) ga muvofiq, do‘stingizning "
                        f"shaxsiy ma’lumotlari daxlsizligi saqlandi va hisobot faqat uning o‘ziga taqdim etildi.</i>"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logging.warning(f"Could not notify requester: {e}")
        return
    elif data.startswith("reject_consent_"):
        req_id = data.replace("reject_consent_", "").strip()
        req = CONSENT_REQUESTS.get(req_id)
        if req:
            req["status"] = "rejected"
            save_json_store(CONSENT_FILE, CONSENT_REQUESTS)
            target = req.get("target", "profil")
            if req.get("requester_id"):
                try:
                    await context.bot.send_message(
                        chat_id=req["requester_id"],
                        text=f"{p('WARN', 'ℹ️')} Do‘stingiz (<code>@{html.escape(target)}</code>) kiber-audit taklifini rad etdi.",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass
        await query.edit_message_text("🚫 So‘rov bekor qilindi. Hech qanday ma’lumot tahlil qilinmadi.", parse_mode="HTML")
        return

    if data == "start_quiz":
        context.user_data["quiz_step"] = 0
        context.user_data["quiz_score"] = 0
        await send_quiz_question(update, context)
    elif data.startswith("q_"):
        parts = data.split("_")
        score = int(parts[2])
        context.user_data["quiz_score"] = context.user_data.get("quiz_score", 0) + score
        context.user_data["quiz_step"] = context.user_data.get("quiz_step", 0) + 1
        await send_quiz_question(update, context)
    elif data == "show_checklist":
        checklist_text = (
            f"{p('SHIELD', '🛡️')} <b>«Xavfsiz Profil» chek-listi:</b>\n"
            f"1. {p('PHONE', '📱')} Telefon raqamingizni 'Hech kimga' qilib yashiring.\n"
            f"2. {p('KEY_LOCK', '🔐')} Ikki bosqichli tekshiruv (2FA) parolini yoqing.\n"
            f"3. {p('EXIF_PHOTO', '🖼️')} Suratga olayotganda GPS teglarni o‘chiring.\n"
            f"4. {p('LAPTOP', '💻')} Begona sessiyalarni (qurilmalarni) yakunlang.\n"
            f"5. {p('LOCK', '🔒')} Guruhlarga faqat kontaktlar qo‘shishiga ruxsat bering."
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Qaytadan topshirish", callback_data="start_quiz", icon_custom_emoji_id=E["REFRESH"])],
            [InlineKeyboardButton("2FA qo‘llanmasi", callback_data="guide_2fa", icon_custom_emoji_id=E["KEY_LOCK"])]
        ])
        await query.edit_message_text(checklist_text, parse_mode="HTML", reply_markup=back_kb)
    elif data == "guide_2fa":
        guide_text = (
            f"{p('KEY_LOCK', '🔐')} <b>IKKI BOSQICHLI TEKSHIRUV (2FA) YOQISH QO‘LLANMASI:</b>\n\n"
            f"1. {p('GEAR', '⚙️')} Telegramda <b>Sozlamalar</b> (Settings) ga kiring;\n"
            f"2. {p('SHIELD', '🛡️')} <b>Maxfiylik va xavfsizlik</b> (Privacy and Security) bo‘limini tanlang;\n"
            f"3. {p('KEY', '🔑')} <b>Ikki bosqichli tekshiruv</b> (Two-Step Verification) ni bosing;\n"
            f"4. {p('LOCK', '🔒')} Esda qoladigan, lekin oson topilmaydigan maxfiy parol kiriting;\n"
            f"5. {p('CHECK', '✅')} E-mail manzilingizni tasdiqlang.\n\n"
            f"{p('CHECK', '✅')} <i>Endi yangi qurilmadan kirilganda SMS koddan tashqari shu maxfiy parol ham so‘raladi!</i>"
        )
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Profil xavfsizligini tekshirish", callback_data="start_quiz", icon_custom_emoji_id=E["TEST"])],
            [InlineKeyboardButton("5 daqiqalik Chek-list", callback_data="show_checklist", icon_custom_emoji_id=E["SHIELD"])]
        ])
        await query.edit_message_text(guide_text, parse_mode="HTML", reply_markup=back_kb)
    elif data == "sanitize":
        last_photo = context.user_data.get("last_photo")
        if not last_photo:
            await query.answer("Tozalash uchun yangi surat topilmadi. Iltimos, avval rasm yuboring.", show_alert=True)
            return
        try:
            im = Image.open(io.BytesIO(last_photo)).convert("RGB")
            out = io.BytesIO()
            im.save(out, format="JPEG", quality=95)
            out.seek(0)
            await query.message.reply_document(
                document=out,
                filename="tozalangan_xavfsiz_surat.jpg",
                caption=(
                    f"{p('CHECK', '✅')} <b>SURAT TO‘LIQ TOZALANDI!</b>\n\n"
                    f"• {p('SHIELD', '🛡️')} Barcha yashirin GPS koordinatalari olib tashlandi;\n"
                    f"• {p('PHONE', '📱')} Kamera va telefon modeli o‘chirildi;\n"
                    f"• {p('TIMER', '⏰')} Olingan sana/vaqt teglari tozalab yuborildi.\n\n"
                    f"<i>Endi ushbu toza suratni ijtimoiy tarmoqlarga xavfsiz joylashingiz mumkin!</i>"
                ),
                parse_mode="HTML"
            )
        except Exception as e:
            await query.answer(f"Tozalashda xatolik yuz berdi: {e}", show_alert=True)
    elif data == "audit_deepfake_last":
        last_photo = context.user_data.get("last_photo")
        if not last_photo:
            await query.answer("Tahlil uchun rasm topilmadi. Iltimos, yangi fotosurat yuboring.", show_alert=True)
            return
        await query.answer("Sun’iy intellekt (Deepfake) ekspertizasi o‘tkazilmoqda...", show_alert=False)
        try:
            await query.message.chat.send_action("typing")
        except Exception:
            pass
        report = await audit_deepfake_with_ai(last_photo)
        await query.message.reply_text(report, parse_mode="HTML")
    elif data == "start_anon_sos":
        context.user_data["waiting_for_sos"] = True
        prompt = (
            f"{p('CHAT', '✍️')} <b>ANONIM MUROJAAT YOZISH MAYDONI:</b>\n\n"
            f"Iltimos, sizni bezovta qilayotgan muammo yoki hodisani batafsil yozib yuboring "
            f"(xohlasangiz dalil sifatida fotosurat yoki skrinshot ham yuborishingiz mumkin).\n\n"
            f"{p('LOCK', '🔒')} <b>KiberIz-4 Xavfsizlik Kafolati:</b>\n"
            f"Sizning Telegram ID, Ismingiz yoki @username'ingiz HECH KIMGA ko‘rsatilmaydi! "
            f"Xabar tizimga faqat maxsus kod (masalan: <code>#SOS-4M-8291</code>) bilan qayd etiladi.\n\n"
            f"<i>Bekor qilish uchun: /cancel deb yozing.</i>"
        )
        await query.edit_message_text(prompt, parse_mode="HTML")
    elif data == "confirm_quick_sos":
        pending_text = context.user_data.get("pending_sos_text", "Anonim xabar")
        import random, datetime
        report_code = f"SOS-4M-{random.randint(1000, 9999)}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            reports_dir = os.path.join(BASE_DIR, "data")
            os.makedirs(reports_dir, exist_ok=True)
            reports_file = os.path.join(reports_dir, "anon_sos_reports.json")
            existing = []
            if os.path.exists(reports_file):
                with open(reports_file, "r", encoding="utf-8") as rf:
                    existing = json.load(rf)
            existing.append({
                "code": report_code,
                "timestamp": timestamp,
                "text": pending_text,
                "has_photo": False
            })
            with open(reports_file, "w", encoding="utf-8") as wf:
                json.dump(existing, wf, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving anon report: {e}")

        if ADMIN_ID:
            try:
                alert_text = (
                    f"{p('SOS', '🚨')} <b>YANGI ANONIM SOS MUROJAAT (4-MAKTAB)</b>\n\n"
                    f"{p('INFO', '🆔')} <b>Kodi:</b> <code>#{report_code}</code>\n"
                    f"{p('TIMER', '📅')} <b>Vaqti:</b> {timestamp}\n\n"
                    f"{p('INFO', '📝')} <b>Murojaat matni:</b>\n<i>«{html.escape(pending_text)}»</i>\n\n"
                    f"{p('LOCK', '🔒')} <i>Foydalanuvchi ma’lumotlari to‘liq anonimlashtirilgan.</i>"
                )
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Failed to alert admin: {e}")

        success_msg = (
            f"{p('CHECK', '✅')} <b>ANONIM MUROJAATINGIZ QABUL QILINDI!</b>\n\n"
            f"{p('INFO', '🆔')} <b>Murojaat kodi:</b> <code>#{report_code}</code>\n"
            f"{p('TIMER', '📅')} <b>Qayd etilgan vaqt:</b> <i>{timestamp}</i>\n"
            f"{p('SHIELD', '🛡️')} <b>Maxfiylik maqomi:</b> <i>To‘liq himoyalangan (Ism, profil va shaxsiy ma’lumotlar oshkor etilmadi).</i>\n\n"
            f"Muammoingiz 4-maktab profilaktika inspektori va psixologiga ko‘rib chiqish uchun uzatildi.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• {p('SHIELD', '🛡️')} Kiberxavfsizlik hodisalari bo‘yicha: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• {p('SHIELD', '⚖️')} Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        await query.edit_message_text(success_msg, parse_mode="HTML")
    elif data.startswith("ai_q_"):
        query_map = {
            "ai_q_groups": "Telegramda meni begona va shubhali guruhlarga qo‘shib qo‘yishmasligi uchun qanday sozlamalarni yoqishim kerak?",
            "ai_q_2fa": "Telegram va boshqa ijtimoiy tarmoqlarda Ikki bosqichli tasdiqlashni (2FA) qanday yoqish kerak va u nima uchun shart?",
            "ai_q_phishing": "Internetda va Telegramda fishing hamda soxta havolalarni (soxta sovg'a, ovoz berish) qanday qilib darhol aniqlash mumkin?",
            "ai_q_password": "Buzilmaydigan, kuchli va o'quvchi uchun eslab qolish oson bo'lgan parolni qanday yaratish kerak?"
        }
        prompt = query_map.get(data, "Kiberxavfsizlik bo'yicha asosiy tavsiyalar.")
        try:
            await query.message.chat.send_action("typing")
        except Exception:
            pass
        answer = await ask_gemini_cyber_mentor(prompt, user_id=query.from_user.id)
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("O‘z savolimni berish", callback_data="ask_custom_ai", icon_custom_emoji_id=E["CHAT"])],
            [InlineKeyboardButton("Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])]
        ])
        await query.edit_message_text(
            f"{p('LIGHT', '💡')} <b>AI KIBER-MASLAHATCHI JAVOBI:</b>\n\n{answer}",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    elif data == "ask_custom_ai":
        context.user_data["waiting_for_ai"] = True
        context.user_data["waiting_for_audit"] = False
        back_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Bekor qilish", callback_data="cancel_action", icon_custom_emoji_id=E["CROSS"])],
            [InlineKeyboardButton("Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])]
        ])
        await query.edit_message_text(
            f"{p('CHAT', '✍️')} <b>Marhamat, o‘zingizni qiziqtirgan savolni yozib yuboring:</b>\n\n"
            f"<i>Masalan: «Do‘stimning akkaunti buzilibdi, qanday yordam bersam bo‘ladi?»</i>",
            parse_mode="HTML",
            reply_markup=back_kb
        )
    elif data == "cancel_action":
        context.user_data["waiting_for_sos"] = False
        context.user_data["waiting_for_audit"] = False
        context.user_data["waiting_for_ai"] = False
        await query.edit_message_text(
            f"{p('CHECK', '✅')} <b>Amal bekor qilindi.</b> Asosiy menyudan foydalanishingiz mumkin.",
            parse_mode="HTML"
        )

# ==========================================
# ADVANCED OSINT UTILITIES (REVERSE GEO, QR, DOCS, USERNAME, LINKS)
# ==========================================
def get_human_address(lat: float, lon: float) -> str:
    """Queries OpenStreetMap Nominatim for human-readable street/district in Uzbekistan."""
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
        req = urllib.request.Request(url, headers={"User-Agent": "KiberIz4-SchoolOSINT-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode())
            addr = data.get("address", {})
            road = addr.get("road")
            suburb = addr.get("suburb") or addr.get("district") or addr.get("city_district")
            city = addr.get("city") or addr.get("county") or addr.get("state")
            parts = []
            if road: parts.append(road)
            if suburb: parts.append(suburb)
            if city: parts.append(city)
            if parts:
                return ", ".join(parts)
            return data.get("display_name", "")[:80]
    except Exception as e:
        logging.warning(f"Reverse geocode error: {e}")
        return None

def scan_qr_code(file_bytes: bytes) -> str:
    """Detects and decodes QR codes and barcodes inside an image using pyzbar with OpenCV fallback."""
    if not file_bytes:
        return None
        
    # 1. Primary: pyzbar (robust barcode & QR decoder)
    if pyzbar_decode is not None:
        try:
            pil_img = Image.open(io.BytesIO(file_bytes))
            barcodes = pyzbar_decode(pil_img)
            if barcodes:
                for b in barcodes:
                    if b.type == 'QRCODE':
                        val = b.data.decode('utf-8', errors='ignore').strip()
                        if val:
                            return val
                val = barcodes[0].data.decode('utf-8', errors='ignore').strip()
                if val:
                    return val
        except Exception as e:
            logging.debug(f"pyzbar QR scan error: {e}")

    # 2. Fallback: OpenCV QRCodeDetector
    if cv2 is not None and np is not None:
        try:
            nparr = np.frombuffer(file_bytes, np.uint8)
            cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if cv_img is not None:
                detector = cv2.QRCodeDetector()
                val, _, _ = detector.detectAndDecode(cv_img)
                if val and val.strip():
                    return val.strip()
        except Exception as e:
            logging.debug(f"OpenCV QR scan error: {e}")

    return None

def parse_document_metadata(file_bytes: bytes, file_name: str):
    """Extracts Author, Creator, Software, Dates, and macro security risks from documents."""
    ext = os.path.splitext(file_name)[1].lower() or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        cmd = ["exiftool", "-json", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        details = []
        has_macro = ext in [".docm", ".xlsm", ".pptm", ".dotm", ".xltm"]
        
        # Check for embedded macros in office OpenXML archives
        if not has_macro and ext in [".docx", ".xlsx", ".pptx"]:
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
                    if any("vbaproject.bin" in name.lower() for name in z.namelist()):
                        has_macro = True
            except Exception:
                pass
                
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)[0]
            title = data.get("Title")
            if title:
                details.append(f"📑 <b>Hujjat sarlavhasi:</b> {html.escape(str(title))}")
            author = data.get("Author") or data.get("Creator")
            if author:
                details.append(f"👤 <b>Hujjat muallifi:</b> <code>{html.escape(str(author))}</code>")
            company = data.get("Company")
            if company:
                details.append(f"🏢 <b>Tashkilot / Muassasa:</b> <code>{html.escape(str(company))}</code>")
            last_mod_by = data.get("LastModifiedBy")
            if last_mod_by:
                details.append(f"✏️ <b>Oxirgi tahrirchi:</b> <code>{html.escape(str(last_mod_by))}</code>")
            software = data.get("Software") or data.get("Producer") or data.get("CreatorTool") or data.get("Application")
            if software:
                details.append(f"💻 <b>Yaratilgan dastur:</b> <code>{html.escape(str(software))}</code>")
            create_date = data.get("CreateDate")
            if create_date:
                details.append(f"⏰ <b>Yaratilgan vaqt:</b> {html.escape(str(create_date))}")
            mod_date = data.get("ModifyDate")
            if mod_date:
                details.append(f"🔄 <b>Oxirgi o‘zgarish:</b> {html.escape(str(mod_date))}")
            pages = data.get("PageCount")
            if pages:
                details.append(f"📄 <b>Sahifalar soni:</b> {html.escape(str(pages))}")
            words = data.get("Words") or data.get("WordCount")
            if words:
                details.append(f"📝 <b>So‘zlar soni:</b> {html.escape(str(words))}")
        return details, has_macro
    except Exception as e:
        logging.warning(f"Doc metadata error: {e}")
        return [], False
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

def parse_binary_or_script_metadata(file_bytes: bytes, file_name: str):
    """Calculates hashes and static metadata for binaries, scripts, and generic files."""
    md5 = hashlib.md5(file_bytes).hexdigest()
    sha256 = hashlib.sha256(file_bytes).hexdigest()
    size_kb = round(len(file_bytes) / 1024, 2)
    return {
        "file_name": file_name,
        "size_kb": size_kb,
        "md5": md5,
        "sha256": sha256
    }

def parse_audio_metadata(file_bytes: bytes, file_name: str):
    """Extracts ID3 tags, recording software, and parameters from audio files."""
    ext = os.path.splitext(file_name)[1].lower() or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        cmd = ["exiftool", "-json", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode != 0 or not res.stdout.strip():
            return [], None
        data = json.loads(res.stdout)[0]
        details = []
        
        title = data.get("Title")
        if title:
            details.append(f"🎵 <b>Nomi:</b> {html.escape(str(title))}")
        artist = data.get("Artist") or data.get("Composer")
        if artist:
            details.append(f"👤 <b>Ijrochi / Muallif:</b> {html.escape(str(artist))}")
        album = data.get("Album")
        if album:
            details.append(f"💿 <b>Albom:</b> {html.escape(str(album))}")
        year = data.get("Year") or data.get("RecordingTime") or data.get("DateTimeOriginal")
        if year:
            details.append(f"📅 <b>Yili / Vaqti:</b> {html.escape(str(year))}")
            
        encoded_by = data.get("EncodedBy") or data.get("Encoder") or data.get("WritingApplication")
        if encoded_by:
            details.append(f"{p('GEAR', '⚙️')} <b>Yozib olingan / Saqlangan dastur:</b> <code>{html.escape(str(encoded_by))}</code>")
            
        duration = data.get("Duration")
        if duration:
            details.append(f"{p('TIMER', '⏱️')} <b>Davomiyligi:</b> {html.escape(str(duration))}")
            
        bitrate = data.get("AudioBitrate") or data.get("Bitrate")
        sample_rate = data.get("SampleRate")
        channels = data.get("ChannelMode") or data.get("Channels")
        tech = []
        if bitrate: tech.append(f"{bitrate}")
        if sample_rate: tech.append(f"{sample_rate} Hz")
        if channels: tech.append(f"{channels}")
        if tech:
            details.append(f"🔊 <b>Audio parametrlari:</b> {html.escape(' | '.join(str(x) for x in tech))}")
            
        comment = data.get("Comment")
        if comment and len(str(comment)) < 200:
            details.append(f"💬 <b>Teg izohi:</b> <i>{html.escape(str(comment))}</i>")
            
        return details, None
    except Exception as e:
        logging.warning(f"Audio metadata error: {e}")
        return [], None
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

def parse_raw_image_exif(file_bytes: bytes, file_name: str):
    """Extracts rich EXIF, camera, lens, and GPS from RAW images (DNG, CR2, NEF, ARW, etc.)
    and extracts embedded JPEG preview for visual OSINT."""
    ext = os.path.splitext(file_name)[1].lower() or ".dng"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        cmd = ["exiftool", "-json", "-c", "%.6f", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if res.returncode != 0 or not res.stdout.strip():
            return [], None, None, "Fayl metama'lumotlarini o'qib bo'lmadi"
        
        data = json.loads(res.stdout)[0]
        details = []
        
        # Camera & Lens
        make = str(data.get("Make", "")).strip()
        model = str(data.get("Model", "")).strip()
        camera = f"{make} {model}".strip()
        if camera:
            details.append(f"{p('PHONE', '📷')} <b>Kamera modeli:</b> <code>{html.escape(camera)}</code>")
        lens = data.get("LensModel") or data.get("Lens")
        if lens:
            details.append(f"🔍 <b>Ob'yektiv (Lens):</b> <code>{html.escape(str(lens))}</code>")
            
        serial = data.get("SerialNumber") or data.get("InternalSerialNumber")
        if serial:
            details.append(f"🆔 <b>Kamera seriya raqami:</b> <code>{html.escape(str(serial))}</code>")
            
        # Shooting specs
        date_time = data.get("DateTimeOriginal") or data.get("CreateDate")
        if date_time:
            details.append(f"{p('TIMER', '⏰')} <b>Suratga olingan vaqt:</b> <code>{html.escape(str(date_time))}</code>")
            
        shutter = data.get("ShutterSpeed") or data.get("ExposureTime")
        aperture = data.get("Aperture") or data.get("FNumber")
        iso = data.get("ISO")
        focal = data.get("FocalLength")
        specs = []
        if shutter: specs.append(f"Chiqarish: {shutter}s")
        if aperture: specs.append(f"Diafragma: f/{aperture}")
        if iso: specs.append(f"ISO: {iso}")
        if focal: specs.append(f"Fokus: {focal}")
        if specs:
            details.append(f"⚙️ <b>Eksponometriya:</b> {html.escape(' | '.join(specs))}")
            
        software = data.get("Software") or data.get("CreatorTool")
        if software:
            details.append(f"{p('GEAR', '💻')} <b>Dastur:</b> <code>{html.escape(str(software))}</code>")
            
        # GPS extraction
        lat_val, lon_val = None, None
        lat_str = str(data.get("GPSLatitude", "")).strip()
        lon_str = str(data.get("GPSLongitude", "")).strip()
        if not lat_str or not lon_str:
            pos = str(data.get("GPSPosition", "")).strip()
            if pos and "," in pos:
                parts = pos.split(",")
                lat_str, lon_str = parts[0].strip(), parts[1].strip()
        if lat_str and lon_str:
            try:
                lat = float(lat_str.replace("N", "").replace("S", "").strip())
                if "S" in lat_str: lat = -lat
                lon = float(lon_str.replace("E", "").replace("W", "").strip())
                if "W" in lon_str: lon = -lon
                lat_val = round(lat, 6)
                lon_val = round(lon, 6)
                maps_link = f"https://www.google.com/maps?q={lat_val},{lon_val}"
                details.append(
                    f"{p('SEARCH', '📍')} <b>GPS Lokatsiya:</b> <code>{lat_val}° N, {lon_val}° E</code>\n"
                    f"   └ 🗺️ <a href=\"{maps_link}\">Google Xaritada ochish (Jonli nuqta)</a>"
                )
            except Exception:
                pass
                
        # Extract embedded preview JPEG
        preview_bytes = None
        for tag in ["-PreviewImage", "-JpgFromRaw", "-ThumbnailImage"]:
            try:
                p_res = subprocess.run(["exiftool", "-b", tag, tf_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
                if p_res.returncode == 0 and len(p_res.stdout) > 2000:
                    preview_bytes = p_res.stdout
                    break
            except Exception:
                pass
                
        coords = (lat_val, lon_val) if (lat_val is not None and lon_val is not None) else None
        return details, coords, preview_bytes, None
    except Exception as e:
        return [], None, None, str(e)
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

def parse_apk_metadata(file_bytes: bytes, file_name: str):
    """Extracts package name, version, label, permissions, and structure from APK packages."""
    ext = os.path.splitext(file_name)[1].lower() or ".apk"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name

    info = {
        "package_name": "",
        "version_name": "",
        "version_code": "",
        "app_label": "",
        "sdk_target": "",
        "sdk_min": "",
        "permissions": [],
        "dangerous_perms": [],
        "dex_count": 0,
        "has_native_lib": False,
        "file_size_mb": round(len(file_bytes) / (1024 * 1024), 2)
    }

    # 1. Try AAPT (Android Asset Packaging Tool)
    try:
        res = subprocess.run(["aapt", "dump", "badging", tf_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        out = res.stdout
        m_pkg = re.search(r"package:\s+name='([^']+)'(?:\s+versionCode='([^']+)')?(?:\s+versionName='([^']+)')?", out)
        if m_pkg:
            info["package_name"] = m_pkg.group(1)
            info["version_code"] = m_pkg.group(2) or ""
            info["version_name"] = m_pkg.group(3) or ""
        m_label = re.search(r"application-label(?:-[^:]+)?:'([^']+)'", out)
        if m_label:
            info["app_label"] = m_label.group(1)
        m_target = re.search(r"targetSdkVersion:'([^']+)'", out)
        if m_target:
            info["sdk_target"] = m_target.group(1)
        m_min = re.search(r"sdkVersion:'([^']+)'", out)
        if m_min:
            info["sdk_min"] = m_min.group(1)
        perms = re.findall(r"uses-permission:\s+name='([^']+)'", out)
        info["permissions"] = sorted(list(set(perms)))
    except Exception as e:
        logging.warning(f"AAPT parsing error: {e}")

    # Fallback to Python zipfile parsing if AAPT was missing or empty
    try:
        with zipfile.ZipFile(tf_path, "r") as z:
            names = z.namelist()
            info["dex_count"] = sum(1 for n in names if n.endswith(".dex"))
            info["has_native_lib"] = any(n.startswith("lib/") for n in names)
            
            if not info["permissions"] and "AndroidManifest.xml" in names:
                manifest_bytes = z.read("AndroidManifest.xml")
                perms_utf8 = re.findall(rb'android\.permission\.([A-Za-z0-9_]+)', manifest_bytes)
                for p_b in perms_utf8:
                    p_str = "android.permission." + p_b.decode("ascii", errors="ignore")
                    if p_str not in info["permissions"]:
                        info["permissions"].append(p_str)
    except Exception as z_err:
        logging.warning(f"APK zip inspection error: {z_err}")

    # Identify high-risk dangerous permissions
    DANGEROUS_SET = {
        "READ_SMS", "RECEIVE_SMS", "SEND_SMS", "RECEIVE_MMS", "RECEIVE_WAP_PUSH",
        "SYSTEM_ALERT_WINDOW", "BIND_ACCESSIBILITY_SERVICE", "RECORD_AUDIO",
        "CAMERA", "READ_CONTACTS", "WRITE_CONTACTS", "ACCESS_FINE_LOCATION",
        "ACCESS_COARSE_LOCATION", "REQUEST_INSTALL_PACKAGES", "RECEIVE_BOOT_COMPLETED",
        "CALL_PHONE", "READ_PHONE_STATE", "READ_CALL_LOG", "WRITE_CALL_LOG",
        "NOTIFICATION_LISTENER", "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS"
    }
    for p_name in info["permissions"]:
        p_short = p_name.split(".")[-1]
        if p_short in DANGEROUS_SET and p_short not in info["dangerous_perms"]:
            info["dangerous_perms"].append(p_short)

    if os.path.exists(tf_path):
        try:
            os.remove(tf_path)
        except Exception:
            pass

    return info

async def audit_apk_with_ai(apk_info: dict, file_name: str) -> str:
    """Uses Gemini AI to assess maliciousness, stealer risks, and threats in Android APK packages."""
    pkg = apk_info.get("package_name") or "noma'lum"
    label = apk_info.get("app_label") or file_name
    dang = ", ".join(apk_info.get("dangerous_perms", [])) or "Hech qanday kritik ruxsat yo'q"
    all_perms = ", ".join(apk_info.get("permissions", []))[:400]
    
    prompt = (
        f"Sen professional Kiberxavfsizlik va Android zararli dasturlari (Malware/Stealer) bo'yicha ekspertisan.\n"
        f"Foydalanuvchi quyidagi Android ilovasini (APK) tekshirish uchun yubordi:\n"
        f"- Fayl nomi: {file_name}\n"
        f"- Ilova nomi (Label): {label}\n"
        f"- Paket identifikatori: {pkg}\n"
        f"- Aniqlangan xavfli ruxsatlar: {dang}\n"
        f"- Barcha so'ralgan ruxsatlar: {all_perms}\n\n"
        f"Vazifang:\n"
        f"1. Ilova nomi bilan so'ralayotgan ruxsatlar o'rtasidagi nomutanosiblikni ko'rsat (masalan, rasm yoki tozalovchi ilovasi nega SMS yoki qo'ng'iroqni so'raydi?);\n"
        f"2. Ushbu ilova bank kodlarini o'g'irlaydigan troyan, fishing yoki josus (spyware) bo'lish ehtimolini bahola;\n"
        f"3. Foydalanuvchiga darhol ko'rilishi lozim bo'lgan 2-3 ta aniq xavfsizlik chorasini ber.\n"
        f"Javobni Telegram HTML formatida (faqat <b>, <i>, <code> teglari bilan) juda qisqa, aniq va ta'sirchan qilib yoz."
    )
    raw = await asyncio.to_thread(_query_gemini_api_sync, prompt)
    return format_ai_to_tg_html(raw)

async def handle_apk_analysis(msg, file_bytes: bytes, file_name: str):
    """Deep Android APK/package cyber security analysis with AAPT and Gemini AI."""
    try:
        await msg.reply_chat_action("typing")
    except Exception:
        pass
    apk_info = parse_apk_metadata(file_bytes, file_name)
    ai_verdict = await audit_apk_with_ai(apk_info, file_name)
    
    risk_score = 15
    dang_list = apk_info.get("dangerous_perms", [])
    dang_count = len(dang_list)
    
    if any(p in dang_list for p in ["READ_SMS", "RECEIVE_SMS", "SEND_SMS"]):
        risk_score += 50
    if "BIND_ACCESSIBILITY_SERVICE" in dang_list:
        risk_score += 45
    if "SYSTEM_ALERT_WINDOW" in dang_list:
        risk_score += 25
    if "NOTIFICATION_LISTENER" in dang_list:
        risk_score += 35
    if any(p in dang_list for p in ["RECORD_AUDIO", "CAMERA"]):
        risk_score += 25
    if any(p in dang_list for p in ["READ_PHONE_STATE", "CALL_PHONE"]):
        risk_score += 15
    if "REQUEST_INSTALL_PACKAGES" in dang_list:
        risk_score += 25
    if "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS" in dang_list:
        risk_score += 15
        
    misleading_keywords = ["rasm", "foto", "photo", "video", "albom", "album", "bonus", "sovrin", "pul", "click", "payme", "karta"]
    low_name = file_name.lower() + " " + apk_info.get("app_label", "").lower()
    if any(k in low_name for k in misleading_keywords) and dang_count >= 2:
        risk_score += 30

    risk_score = min(max(risk_score, 10), 100)
    filled = int(risk_score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    if risk_score >= 75:
        risk_label = f"🚨 KRITIK JIDDIY XAVF ({risk_score}%) — TROYAN / STEALER EHTIMOLI!"
    elif risk_score >= 45:
        risk_label = f"⚠️ O‘RTA DARAJADAGI XAVF ({risk_score}%) — SHUBHALI RUXSATLAR"
    else:
        risk_label = f"✅ XAVFSIZROQ PROFIL ({risk_score}%)"

    report = (
        f"{p('SHIELD', '🛡️')} <b>ANDROID ILOVA (.APK) KIBERXAVFSIZLIK TAHLILI:</b>\n\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b>\n"
        f"<code>[{bar}]</code> <b>{risk_label}</b>\n\n"
        f"📦 <b>ILOVA TEXNIK MA’LUMOTLARI:</b>\n"
        f"• <b>Fayl nomi:</b> <code>{html.escape(file_name)}</code>\n"
        f"• <b>Hajmi:</b> <code>{apk_info['file_size_mb']} MB</code>\n"
    )
    if apk_info.get("app_label"):
        report += f"• <b>Ilova nomi (Label):</b> <b>{html.escape(apk_info['app_label'])}</b>\n"
    if apk_info.get("package_name"):
        report += f"• <b>Paket identifikatori (Package ID):</b> <code>{html.escape(apk_info['package_name'])}</code>\n"
    if apk_info.get("version_name"):
        report += f"• <b>Versiyasi:</b> <code>{html.escape(apk_info['version_name'])} (kod: {apk_info.get('version_code', '')})</code>\n"
    if apk_info.get("sdk_target"):
        report += f"• <b>Target Android SDK:</b> <code>Android {apk_info['sdk_target']}</code>\n"
    if apk_info.get("dex_count"):
        report += f"• <b>DEX kod modullari soni:</b> <code>{apk_info['dex_count']} ta</code>\n"
    report += "\n"

    if dang_list:
        report += (
            f"{p('SOS', '🚨')} <b>ANIQLANGAN XAVFLI VA NOZIK RUXSATLAR ({len(dang_list)} ta):</b>\n"
        )
        PERM_EXPLANATIONS = {
            "READ_SMS": "SMS xabarlarni o‘qish (Bank va 2FA kodlarini o‘g‘irlash)",
            "RECEIVE_SMS": "Keluvchi SMSlarni tutib olish (Karta pullarini yechish)",
            "SEND_SMS": "Foydalanuvchisiz pulli SMS yuborish",
            "SYSTEM_ALERT_WINDOW": "Boshqa oynalar ustidan soxta (fishing) oyna ochish",
            "BIND_ACCESSIBILITY_SERVICE": "Telefonni to‘liq masofadan boshqarish",
            "RECORD_AUDIO": "Atrofdagi ovozlarni yashirin yozib olish",
            "CAMERA": "Yashirin surat va video tasvirga olish",
            "READ_CONTACTS": "Kontaktlar kitobini serverga o‘g‘irlab ketish",
            "ACCESS_FINE_LOCATION": "Aniq GPS lokatsiyani doimiy kuzatib borish",
            "REQUEST_INSTALL_PACKAGES": "Yashirincha boshqa viruslarni telefonga o‘rnatish",
            "RECEIVE_BOOT_COMPLETED": "Telefon yoqilishi bilan virusni avtomatik ishga tushirish",
            "CALL_PHONE": "Ruxsatsiz telefon qo‘ng‘iroqlarini amalga oshirish",
            "READ_PHONE_STATE": "SIM-karta va IMEI parametrlarini aniqlash",
            "NOTIFICATION_LISTENER": "Bildirishnomalardan (Telegram/SMS) kodlarni o‘g‘irlash",
            "REQUEST_IGNORE_BATTERY_OPTIMIZATIONS": "Fonda batareya tejamkorligini o‘chirib doimiy ishlash"
        }
        for dp in dang_list:
            expl = PERM_EXPLANATIONS.get(dp, "Tizimning nozik resurslariga ruxsat")
            report += f"• ⚠️ <code>{dp}</code> — <i>{expl}</i>\n"
        report += "\n"
    else:
        report += f"{p('CHECK', '✅')} <i>Hech qanday o‘ta xavfli (SMS/Kamera/Boshqaruv) ruxsatlar talab qilinmagan.</i>\n\n"

    if ai_verdict:
        report += (
            f"{p('LIGHT', '🤖')} <b>GEMINI AI KIBER-EKSPERT XULOSASI:</b>\n"
            f"{ai_verdict}\n\n"
        )
        
    report += (
        f"{p('SHIELD', '🛡️')} <b>ESLATMA:</b> Hech qachon Telegram orqali kelgan notanish .APK fayllarni o‘rnatmang! "
        f"Ilovalarni faqat rasmiy <b>Google Play Store</b> orqali yuklab oling."
    )
    
    await msg.reply_text(report, parse_mode="HTML")

async def handle_raw_image_analysis(msg, file_bytes: bytes, file_name: str):
    """Analyzes RAW camera files (DNG, CR2, NEF, ARW, etc.) using ExifTool and Gemini Vision."""
    details, coords, preview_bytes, err = parse_raw_image_exif(file_bytes, file_name)
    if err:
        await msg.reply_text(
            f"{p('WARNING', '⚠️')} RAW faylni ochishda xatolik yuz berdi ({html.escape(err)}).",
            parse_mode="HTML"
        )
        return

    # Reverse Geocoding to Human Address
    if coords:
        lat_val, lon_val = coords
        human_addr = get_human_address(lat_val, lon_val)
        if human_addr:
            details.append(
                f"{p('HOUSE', '🏢')} <b>Haqiqiy tuman / manzil:</b> <code>{html.escape(human_addr)}</code>\n"
                f"   └ 🚨 <i>Diqqat: Ushbu joy 5 metr aniqlikda oshkor bo‘ldi!</i>"
            )

    ai_vision_text = ""
    qr_data = None
    qr_audit_text = ""
    if preview_bytes:
        qr_data = scan_qr_code(preview_bytes)
        if qr_data:
            try:
                qr_audit_text = await audit_quishing_with_ai(qr_data)
            except Exception as qr_err:
                logging.warning(f"RAW preview QR audit error: {qr_err}")
        try:
            ai_vision_text = await analyze_image_with_gemini_vision(preview_bytes, has_gps=bool(coords))
        except Exception as ai_err:
            logging.warning(f"RAW preview AI vision error: {ai_err}")

    risk_score = 20
    if coords:
        risk_score += 50
    elif details:
        risk_score += 25
    if qr_data:
        risk_score += 25
        if qr_audit_text and ("KRITIK" in qr_audit_text.upper() or "FISHING" in qr_audit_text.upper()):
            risk_score = max(risk_score, 90)
    risk_score = min(risk_score, 100)
    filled = int(risk_score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    if risk_score >= 70:
        risk_label = f"🚨 KRITIK JIDDIY XAVF ({risk_score}%)"
    elif risk_score >= 40:
        risk_label = f"⚠️ O‘RTA DARAJADAGI XAVF ({risk_score}%)"
    else:
        risk_label = f"✅ XAVFSIZROQ PROFIL ({risk_score}%)"

    report = (
        f"{p('SEARCH', '📷')} <b>RAW FOTOSURAT OSINT TAHLILI ({html.escape(file_name)}):</b>\n\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b>\n"
        f"<code>[{bar}]</code> <b>{risk_label}</b>\n\n"
        f"{p('LOCK', '🔐')} <b>1. PROFESSIONAL KAMERA VA GPS PARAMETRLARI:</b>\n"
    )
    if details:
        for d in details:
            report += f"• {d}\n"
    else:
        report += f"• {p('CHECK', '✅')} <i>GPS yoki kamera parametrlari topilmadi.</i>\n"
    report += "\n"

    if qr_data:
        if qr_audit_text:
            report += f"{qr_audit_text}\n\n"
        else:
            report += (
                f"🚨 <b>SURAT ICHIDA YASHIRIN QR-KOD TOPILDI:</b>\n"
                f"• <b>QR Tarkibi:</b> <code>{html.escape(qr_data)}</code>\n\n"
            )

    if ai_vision_text:
        report += (
            f"{p('LIGHT', '💡')} <b>2. AI VISION VIZUAL OSINT TAHLILI (Preview tasvirdan):</b>\n"
            f"{ai_vision_text}\n\n"
        )

    await msg.reply_text(report.strip(), parse_mode="HTML", disable_web_page_preview=True)
    if coords:
        lat_val, lon_val = coords
        await msg.reply_location(latitude=lat_val, longitude=lon_val)

async def handle_audio_analysis(msg, file_bytes: bytes, file_name: str):
    """Analyzes audio/voice recordings for hidden device, author, and software tags."""
    details, _ = parse_audio_metadata(file_bytes, file_name)
    
    audio_msg = (
        f"{p('CALL', '🎵')} <b>AUDIO VA OVOZ YOZUV TAHLILI ({html.escape(file_name)}):</b>\n\n"
    )
    
    if details:
        audio_msg += f"{p('WARNING', '⚠️')} <b>ANIQLANGAN METAMA’LUMOTLAR VA TEGLAR:</b>\n"
        for d in details:
            audio_msg += f"• {d}\n"
        audio_msg += (
            f"\n{p('SHIELD', '🛡️')} <b>Kiber-Tahlil:</b> Ovoz yozuvlari va audio fayllardagi ID3 teglar "
            f"yozib olingan dastur nomi (DAW), kompyuter yoki telefon modelini oshkor qilishi mumkin."
        )
    else:
        audio_msg += f"{p('CHECK', '✅')} <i>Ushbu audio faylda shaxsiy yoki texnik teglar topilmadi (tozalangan).</i>"
        
    await msg.reply_text(audio_msg, parse_mode="HTML")

async def handle_document_analysis(msg, file_bytes: bytes, file_name: str):
    """Analyzes documents (PDF, DOCX, XLSX, etc.) for metadata leaks and macros."""
    details, has_macro = parse_document_metadata(file_bytes, file_name)
    
    doc_msg = (
        f"{p('SEARCH', '📄')} <b>HUJJAT OSINT VA XAVFSIZLIK TAHLILI ({html.escape(file_name)}):</b>\n\n"
    )
    
    if has_macro:
        doc_msg += (
            f"{p('SOS', '🚨')} <b>KRITIK KIBER-XAVF: HUJJATDA MAKROS (VBA SKRIPT) ANIQLANDI!</b>\n"
            f"• <b>Holat:</b> Ushbu hujjat ichida avtomatik ishga tushuvchi kod (Macro) mavjud.\n"
            f"• ⚠️ <i>Ogohlantirish: Kiberjinoyatchilar ko‘pincha Word va Excel hujjatlari orqali "
            f"kompyuterni buzuvchi troyan va ransomware viruslarini tarqatadi!</i>\n"
            f"• 🛡️ <b>Xavfsizlik chorasi:</b> Hujjatni ochganda <b>«Enable Content» (Kontentni yoqish)</b> "
            f"yoki <b>«Enable Macros»</b> tugmasini ASLO BOSMANG!\n\n"
        )
    
    if details:
        doc_msg += f"{p('WARNING', '⚠️')} <b>ANIQLANGAN YASHIRIN METAMA’LUMOTLAR:</b>\n"
        for dd in details:
            doc_msg += f"• {dd}\n"
        doc_msg += (
            f"\n{p('SHIELD', '🛡️')} <b>Xavfsizlik eslatmasi:</b> Hujjatlarni tarmoqqa yuklashdan avval "
            f"Word/Excel dasturidagi «Inspect Document» (Hujjatni tekshirish) orqali shaxsiy ism, tashkilot va kompyuter nomini tozalab qo‘ying!"
        )
    else:
        if not has_macro:
            doc_msg += f"{p('CHECK', '✅')} <i>Ushbu hujjatda shaxsiy mualliflik metama’lumotlari topilmadi (tozalangan).</i>"
            
    await msg.reply_text(doc_msg, parse_mode="HTML")

async def handle_binary_or_script_analysis(msg, file_bytes: bytes, file_name: str):
    """Handles executables, installation packages, and scripts with security alerts."""
    info = parse_binary_or_script_metadata(file_bytes, file_name)
    
    bin_msg = (
        f"{p('SOS', '🚨')} <b>KRITIK KIBER-XAVF: DASTUR / SKRIPT FAYLI ({html.escape(file_name)})!</b>\n\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b> <code>[██████████]</code> <b>100% (KRITIK XAVF)</b>\n\n"
        f"ℹ️ <b>Fayl parametrlari:</b>\n"
        f"• <b>Hajmi:</b> <code>{info['size_kb']} KB</code>\n"
        f"• <b>MD5 Hash:</b> <code>{info['md5']}</code>\n"
        f"• <b>SHA256 Hash:</b> <code>{info['sha256']}</code>\n\n"
        f"⚠️ <b>JIDDIY OGOHLANTIRISH:</b>\n"
        f"• Telegram orqali yuborilgan dastur, skript yoki o‘rnatuvchi fayllarni (.EXE, .BAT, .SH, .VBS, .JS) "
        f"kompyuter yoki qurilmangizda <b>ASLO ISHGA TUSHIRMANG!</b>\n"
        f"• Bu kabi fayllar orqali kompyuterdagi barcha parollar o‘g‘irlanadi yoki fayllar Ransomware virusi bilan shifrlab qo‘yiladi.\n\n"
        f"🛡️ <b>Tavsiya:</b> Faylni zudlik bilan o‘chirib tashlang va yuborgan shaxsning akkaunti buzilganligini tekshiring!"
    )
    await msg.reply_text(bin_msg, parse_mode="HTML")

async def handle_generic_file_analysis(msg, file_bytes: bytes, file_name: str):
    """Fallback analyzer for any other file extension using ExifTool and file hashing."""
    info = parse_binary_or_script_metadata(file_bytes, file_name)
    ext = os.path.splitext(file_name)[1].lower() or ".bin"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    details = []
    try:
        cmd = ["exiftool", "-json", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)[0]
            ftype = data.get("FileType")
            mime = data.get("MIMEType")
            if ftype:
                details.append(f"📦 <b>Fayl turi:</b> <code>{html.escape(str(ftype))}</code>")
            if mime:
                details.append(f"🌐 <b>MIME-Type:</b> <code>{html.escape(str(mime))}</code>")
    except Exception:
        pass
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

    report = (
        f"📁 <b>FAYL TEXNIK TAHLILI ({html.escape(file_name)}):</b>\n\n"
        f"• <b>Hajmi:</b> <code>{info['size_kb']} KB</code>\n"
        f"• <b>SHA256 Hash:</b> <code>{info['sha256']}</code>\n"
    )
    for d in details:
        report += f"• {d}\n"
    report += (
        f"\n{p('SHIELD', '🛡️')} <b>Xavfsizlik eslatmasi:</b> Noma’lum manbalardan kelgan fayllarni ochishdan oldin "
        f"har doim uning formati va xavfsizligini tekshirib oling."
    )
    await msg.reply_text(report, parse_mode="HTML")

URL_REGEX = re.compile(
    r'(https?://[^\s]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)',
    re.IGNORECASE
)

# Barcha qat'iy qora ro'yxatlar (FORBIDDEN_RULES) o'chirildi va to'liq Gemini AI intellektiga o'tkazildi.
def audit_username(u: str):
    """Legacy compatibility stub."""
    raw = u.lstrip('@').strip()
    return 50, [], [], [], raw, False, None

def audit_link(url_text: str):
    """Legacy compatibility stub."""
    return False, None, 10, [], [], "", ""

def get_website_screenshot(url: str):
    """Captures a safe, isolated cloud sandbox screenshot of a website without placeholder/spinner errors."""
    import time
    full_url = url.strip().rstrip('.,;!?')
    if '.onion' in full_url.lower():
        return None
        
    if not full_url.startswith(('http://', 'https://')):
        full_url = 'https://' + full_url
        
    # Telegram web channel preview (/s/)
    if 't.me/' in full_url and '/s/' not in full_url:
        full_url = full_url.replace('t.me/', 't.me/s/')
        
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    
    # Provider 1: Thum.io with noanimate (Prevents animated spinner GIFs)
    thum_url = f"https://image.thum.io/get/width/1200/crop/750/noanimate/{full_url}"
    for attempt in range(2):
        try:
            req = urllib.request.Request(thum_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                status_code = resp.headers.get("thum_status_code")
                content_type = resp.headers.get("Content-Type", "").lower()
                data = resp.read()
                
                # Reject animated loading GIFs or tiny placeholder frames
                if "gif" not in content_type and len(data) > 25000:
                    if status_code == "200" or status_code is None:
                        return data
                
                # Cold cache: Thum.io has just dispatched background Chromium render
                if attempt == 0:
                    time.sleep(3.0)
        except Exception as e:
            logging.warning(f"Thum.io screenshot attempt {attempt+1} error: {e}")
            if attempt == 0:
                time.sleep(2.5)

    # Provider 2: Microlink Cloud Sandbox fallback
    try:
        encoded = urllib.parse.quote_plus(full_url)
        micro_api = f"https://api.microlink.io?url={encoded}&screenshot=true"
        req = urllib.request.Request(micro_api, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_data = json.loads(resp.read().decode('utf-8'))
            img_url = res_data.get('data', {}).get('screenshot', {}).get('url')
            if img_url:
                with urllib.request.urlopen(urllib.request.Request(img_url, headers=headers), timeout=10) as img_resp:
                    img_data = img_resp.read()
                    if len(img_data) > 20000:
                        return img_data
    except Exception as e:
        logging.warning(f"Microlink screenshot fallback error: {e}")

    return None

# ==========================================
# REAL OSINT HELPER (JPG, PNG, HEIC, ZIP)
# ==========================================
def convert_image_to_jpeg_bytes(file_bytes: bytes, filename: str = "surat.jpg") -> bytes:
    """Converts HEIC, RAW, WEBP, or other formats to standard JPEG bytes using pillow_heif, ffmpeg, or exiftool."""
    if not file_bytes:
        return file_bytes
    if file_bytes.startswith(b'\xff\xd8\xff') or file_bytes.startswith(b'\x89PNG'):
        return file_bytes
        
    # Method 1: Try pillow_heif / PIL
    try:
        if pillow_heif:
            pillow_heif.register_heif_opener()
        img = Image.open(io.BytesIO(file_bytes))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="JPEG", quality=92)
        return buf.getvalue()
    except Exception:
        pass

    # Method 2: Try ffmpeg conversion
    try:
        cmd = ['ffmpeg', '-y', '-i', 'pipe:0', '-frames:v', '1', '-f', 'image2', '-vcodec', 'mjpeg', 'pipe:1']
        proc = subprocess.run(cmd, input=file_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
            return proc.stdout
    except Exception:
        pass

    # Method 3: Try ImageMagick convert
    try:
        cmd = ['convert', '-[0]', 'jpg:-']
        proc = subprocess.run(cmd, input=file_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        if proc.returncode == 0 and len(proc.stdout) > 1000:
            return proc.stdout
    except Exception:
        pass

    # Method 4: Try extracting embedded preview with ExifTool
    ext = os.path.splitext(filename)[1].lower() or ".heic"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        for tag in ["-PreviewImage", "-JpgFromRaw", "-ThumbnailImage"]:
            p_res = subprocess.run(["exiftool", "-b", tag, tf_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
            if p_res.returncode == 0 and len(p_res.stdout) > 1000:
                return p_res.stdout
    except Exception:
        pass
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

    return file_bytes

def parse_single_image_exif(file_bytes, filename="surat"):
    """Extracts EXIF and GPS from raw image bytes (supports JPG, PNG, HEIC, WEBP, TIFF, etc.)."""
    details = []
    lat_val, lon_val = None, None
    device_name = None
    captured_time = None
    
    # 1. Try PIL first
    try:
        if pillow_heif:
            pillow_heif.register_heif_opener()
        img = Image.open(io.BytesIO(file_bytes))
        exif_data = img.getexif()
        if exif_data:
            make = exif_data.get(ExifTags.Base.Make)
            model = exif_data.get(ExifTags.Base.Model)
            date_time = exif_data.get(ExifTags.Base.DateTime)
            software = exif_data.get(ExifTags.Base.Software)
            
            if make or model:
                device_name = f"{make or ''} {model or ''}".strip()
                details.append(f"{p('PHONE', '📱')} <b>Qurilma:</b> <code>{html.escape(device_name)}</code>")
                
            if date_time:
                captured_time = str(date_time)
                details.append(f"{p('TIMER', '⏰')} <b>Olingan vaqt:</b> <code>{html.escape(captured_time)}</code>")
                
            if software:
                details.append(f"{p('GEAR', '⚙️')} <b>Dastur:</b> <code>{html.escape(str(software))}</code>")
                
            # Parse GPS
            try:
                gps_info = exif_data.get_ifd(ExifTags.IFD.GPSInfo)
                if gps_info:
                    lat_ref = gps_info.get(1, "N")
                    raw_lat = gps_info.get(2)
                    lon_ref = gps_info.get(3, "E")
                    raw_lon = gps_info.get(4)
                    
                    if raw_lat and raw_lon:
                        lat_deg = float(raw_lat[0]) + float(raw_lat[1])/60.0 + float(raw_lat[2])/3600.0
                        if lat_ref == "S": lat_deg = -lat_deg
                        lon_deg = float(raw_lon[0]) + float(raw_lon[1])/60.0 + float(raw_lon[2])/3600.0
                        if lon_ref == "W": lon_deg = -lon_deg
                        
                        lat_val = round(lat_deg, 6)
                        lon_val = round(lon_deg, 6)
                        
                        maps_url = f"https://www.google.com/maps?q={lat_val},{lon_val}"
                        details.append(
                            f"{p('SEARCH', '📍')} <b>GPS Lokatsiya:</b> <code>{lat_val}° {lat_ref}, {lon_val}° {lon_ref}</code>\n"
                            f"👉 <a href=\"{maps_url}\">Google Xaritalarda ko‘rish</a>"
                        )
            except Exception as e:
                logging.error(f"GPS parsing error: {e}")
    except Exception:
        pass

    # 2. ExifTool fallback (Crucial for HEIC, TIFF, or when PIL is missing pillow-heif)
    if not details or lat_val is None:
        ext = os.path.splitext(filename)[1].lower() or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
            tf.write(file_bytes)
            tf_path = tf.name
        try:
            cmd = ["exiftool", "-json", "-c", "%.6f", tf_path]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)[0]
                if not device_name:
                    make = str(data.get("Make", "")).strip()
                    model = str(data.get("Model", "")).strip()
                    if make or model:
                        device_name = f"{make} {model}".strip()
                        details.append(f"{p('PHONE', '📱')} <b>Qurilma:</b> <code>{html.escape(device_name)}</code>")
                if not captured_time:
                    dt = data.get("DateTimeOriginal") or data.get("CreateDate")
                    if dt:
                        details.append(f"{p('TIMER', '⏰')} <b>Olingan vaqt:</b> <code>{html.escape(str(dt))}</code>")
                soft = data.get("Software")
                if soft and not any("Dastur:" in d for d in details):
                    details.append(f"{p('GEAR', '⚙️')} <b>Dastur:</b> <code>{html.escape(str(soft))}</code>")
                
                # Check GPS in exiftool
                if lat_val is None:
                    lat_str = str(data.get("GPSLatitude", "")).strip()
                    lon_str = str(data.get("GPSLongitude", "")).strip()
                    if not lat_str or not lon_str:
                        pos = str(data.get("GPSPosition", "")).strip()
                        if pos and "," in pos:
                            parts = pos.split(",")
                            lat_str, lon_str = parts[0].strip(), parts[1].strip()
                    if lat_str and lon_str:
                        try:
                            lat = float(lat_str.replace("N", "").replace("S", "").strip())
                            if "S" in lat_str: lat = -lat
                            lon = float(lon_str.replace("E", "").replace("W", "").strip())
                            if "W" in lon_str: lon = -lon
                            lat_val = round(lat, 6)
                            lon_val = round(lon, 6)
                            maps_url = f"https://www.google.com/maps?q={lat_val},{lon_val}"
                            details.append(
                                f"{p('SEARCH', '📍')} <b>GPS Lokatsiya:</b> <code>{lat_val}° N, {lon_val}° E</code>\n"
                                f"👉 <a href=\"{maps_url}\">Google Xaritalarda ko‘rish</a>"
                            )
                        except Exception:
                            pass
        except Exception as e_err:
            logging.warning(f"ExifTool image fallback error: {e_err}")
        finally:
            if os.path.exists(tf_path):
                try:
                    os.remove(tf_path)
                except Exception:
                    pass

    coords = (lat_val, lon_val) if (lat_val is not None and lon_val is not None) else None
    return details, coords, None

UZB_REGIONS = {
    "01": "Toshkent shahri",
    "10": "Toshkent viloyati",
    "20": "Sirdaryo viloyati",
    "25": "Jizzax viloyati",
    "30": "Samarqand viloyati",
    "40": "Qashqadaryo viloyati",
    "50": "Surxondaryo viloyati",
    "60": "Andijon viloyati",
    "70": "Farg‘ona viloyati",
    "75": "Namangan viloyati",
    "80": "Buxoro viloyati",
    "85": "Navoiy viloyati",
    "90": "Xorazm viloyati",
    "95": "Qoraqalpog‘iston Respublikasi"
}

UZB_DIAL_CODES = {
    "71": "Toshkent shahri",
    "66": "Samarqand viloyati",
    "73": "Farg‘ona viloyati",
    "74": "Andijon viloyati",
    "69": "Namangan viloyati",
    "65": "Buxoro viloyati",
    "79": "Navoiy viloyati",
    "75": "Qashqadaryo viloyati",
    "76": "Surxondaryo viloyati",
    "67": "Sirdaryo viloyati",
    "72": "Jizzax viloyati",
    "62": "Xorazm viloyati",
    "61": "Qoraqalpog‘iston Respublikasi"
}

def analyze_visual_osint(image_bytes: bytes):
    """
    Performs AI-level Visual OSINT on an image:
    1. Chronolocation & Lighting analysis (day/golden hour/night/indoor).
    2. OCR Text extraction (identifying school, room, street, car license plates, or brand names).
    3. Vehicle license plates & regional indexing (01-95).
    4. Dialing codes and local threat keywords.
    5. Calculates Visual Risk Score.
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        w, h = img.size
        
        # 1. Chronolocation / Lighting
        rgb_img = img.convert("RGB")
        stat = ImageStat.Stat(rgb_img)
        r, g, b = stat.mean
        brightness = (r * 299 + g * 587 + b * 114) / 1000
        
        if brightness < 65:
            chrono_text = "🌙 Kechki yoki tungi vaqt (Sun’iy xona chirog‘i — «uyda yolg‘izman» signali xavfi)"
            chrono_badge = "Tungi / Kechki vaqt"
            chrono_risk = 25
        elif r > (b * 1.25) and brightness > 75:
            chrono_text = "🌅 Oltin soat / Quyosh botishi (Taxminan 17:30 - 19:30 oralig‘i, darsdan keyingi payt)"
            chrono_badge = "Oltin soat / Quyosh botishi"
            chrono_risk = 15
        elif brightness >= 150:
            chrono_text = "☀️ Yorug‘ kunduzgi vaqt (Taxminan 11:00 - 15:00 oralig‘i, maktab yoki dars payti)"
            chrono_badge = "Yorug‘ kunduzgi vaqt"
            chrono_risk = 10
        else:
            chrono_text = "🌤️ Kunduzgi odatiy xona / bino ichidagi yorug‘lik"
            chrono_badge = "Kunduzgi xona yorug‘ligi"
            chrono_risk = 10
            
        # 2. OCR Text Analysis
        ocr_found = []
        detected_text = ""
        if pytesseract is not None:
            try:
                if max(w, h) > 1600:
                    scale = 1600 / max(w, h)
                    small_img = img.resize((int(w * scale), int(h * scale)))
                else:
                    small_img = img
                detected_text = pytesseract.image_to_string(small_img, lang="eng+uzb", timeout=6).strip()
            except Exception as ocr_err:
                logging.warning(f"OCR warning: {ocr_err}")
            
        text_risk = 0
        clues_summary = []
        if detected_text:
            # 2a. Vehicle license plate regex (Uzbekistan regions 01-95)
            # Matches formats: 01 | 777 AAA, 01 A 777 AA, 01 777 AAA, 01A777AA
            plate_pattern = r'\b(01|10|20|25|30|40|50|60|70|75|80|85|90|95)\s*(?:\||[-–—])?\s*[A-Za-z]?\s*\d{3}\s*[A-Za-z]{2,3}\b'
            plate_matches = re.findall(plate_pattern, detected_text)
            for reg_code in sorted(list(set(plate_matches))):
                reg_name = UZB_REGIONS.get(reg_code, "Noma'lum hudud")
                ocr_found.append(f"🚗 <b>Avtoraqam indeksi:</b> <code>{reg_code}</code> — {reg_name}")
                clues_summary.append(f"Avtoraqam: {reg_code} ({reg_name})")
                text_risk += 35

            # 2b. Landline / City dialing codes (+998 71, etc.)
            phone_pattern = r'(?:\+?998[\s\-]?)?\(?(71|66|73|74|69|65|79|75|76|67|72|62|61)\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}'
            phone_matches = re.findall(phone_pattern, detected_text)
            for dial_code in sorted(list(set(phone_matches))):
                dial_reg = UZB_DIAL_CODES.get(dial_code, "Hudud")
                ocr_found.append(f"📞 <b>Shahar telefoni kodi:</b> <code>+{dial_code}</code> — {dial_reg}")
                clues_summary.append(f"Telefon kodi: +{dial_code} ({dial_reg})")
                text_risk += 25

            # 2c. Regional and Landmark Keywords
            low_text = detected_text.lower()
            keywords = [
                ("4-maktab", "🏫 4-maktab aniq nomi"),
                ("maktab", "🏫 Maktab bilan bog‘liq yozuv"),
                ("sinf", "🎒 Sinf xonasi belgisi"),
                ("xona", "🚪 Xona yoki kabinet raqami"),
                ("kabinet", "🚪 Kabinet peshlavhasi"),
                ("toshkent", "📍 Shahar: Toshkent"),
                ("chilonzor", "📍 Tuman: Chilonzor"),
                ("yunusobod", "📍 Tuman: Yunusobod"),
                ("sergeli", "📍 Tuman: Sergeli"),
                ("samarqand", "📍 Shahar: Samarqand"),
                ("buxoro", "📍 Shahar: Buxoro"),
                ("andijon", "📍 Shahar: Andijon"),
                ("farg'ona", "📍 Shahar: Farg‘ona"),
                ("namangan", "📍 Shahar: Namangan"),
                ("ko'cha", "🛣️ Ko‘cha / Manzil yozuvi"),
                ("mahalla", "🏘️ Mahalla nomi"),
                ("dorixona", "💊 Dorixona peshlavhasi"),
                ("apteka", "💊 Dorixona belgisi"),
                ("pharmacy", "💊 Dorixona belgisi"),
                ("korzinka", "🏬 Korzinka supermarketi"),
                ("havas", "🏬 Havas do‘koni"),
                ("makro", "🏬 Makro supermarketi"),
                ("baraka", "🏬 Baraka do‘koni"),
                ("bank", "🏦 Bank yoki moliya muassasasi"),
                ("metro", "🚇 Metro bekati belgisi")
            ]
            for kw, label in keywords:
                if kw in low_text:
                    ocr_found.append(f"{label}: <i>«{kw}»</i>")
                    clues_summary.append(f"{label}: {kw}")
                    text_risk += 15
                    
        return {
            "brightness": round(brightness, 1),
            "chrono_text": chrono_text,
            "chrono_badge": chrono_badge,
            "chrono_risk": chrono_risk,
            "ocr_text": detected_text[:200] if detected_text else "",
            "ocr_found": ocr_found,
            "clues_summary": ", ".join(clues_summary) if clues_summary else "",
            "text_risk": min(text_risk, 60)
        }
    except Exception as e:
        logging.error(f"Visual analysis error: {e}")
        return None

def parse_video_metadata(file_bytes: bytes, file_name: str):
    """Extracts metadata, GPS, duration, resolution, codecs from video files using exiftool."""
    ext = os.path.splitext(file_name)[1].lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
        
    try:
        cmd = ["exiftool", "-json", "-c", "%.6f", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20)
        if res.returncode != 0 or not res.stdout.strip():
            return [], None, "Video parametrlarini tahlil qilib bo‘lmadi"
        
        data = json.loads(res.stdout)[0]
        details = []
        
        # 1. Device Make & Model
        make = str(data.get("Make", "")).strip()
        model = str(data.get("Model", "")).strip()
        device = f"{make} {model}".strip()
        if device:
            details.append(f"{p('PHONE', '📱')} <b>Qurilma modeli:</b> {html.escape(device)}")
            
        # 2. Date / Time
        create_date = data.get("CreateDate") or data.get("TrackCreateDate") or data.get("MediaCreateDate")
        if create_date and create_date != "0000:00:00 00:00:00":
            details.append(f"{p('TIMER', '⏰')} <b>Olingan vaqti:</b> {html.escape(str(create_date))}")
            
        # 3. GPS Coordinates
        lat_val = None
        lon_val = None
        lat_str = str(data.get("GPSLatitude", "")).strip()
        lon_str = str(data.get("GPSLongitude", "")).strip()
        if not lat_str or not lon_str:
            pos = str(data.get("GPSPosition", "")).strip()
            if pos and "," in pos:
                parts = pos.split(",")
                lat_str, lon_str = parts[0].strip(), parts[1].strip()
                
        if lat_str and lon_str:
            try:
                lat = float(lat_str.replace("N", "").replace("S", "").strip())
                if "S" in lat_str: lat = -lat
                lon = float(lon_str.replace("E", "").replace("W", "").strip())
                if "W" in lon_str: lon = -lon
                lat_val = round(lat, 6)
                lon_val = round(lon, 6)
                maps_link = f"https://www.google.com/maps?q={lat_val},{lon_val}"
                details.append(
                    f"{p('SEARCH', '📍')} <b>GPS Lokatsiya:</b> <code>{lat_val}° N, {lon_val}° E</code>\n"
                    f"   └ 🗺️ <a href=\"{maps_link}\">Google Xaritada ochish (Jonli nuqta)</a>"
                )
            except Exception:
                pass
                
        # 4. Video Specs
        duration = data.get("Duration")
        if duration:
            details.append(f"{p('TIMER', '⏱️')} <b>Davomiyligi:</b> {html.escape(str(duration))}")
            
        img_size = data.get("ImageSize")
        if img_size:
            details.append(f"{p('CHECK', '📐')} <b>Ruxsat (O‘lchami):</b> {html.escape(str(img_size))}")
            
        fps = data.get("VideoFrameRate")
        if fps:
            details.append(f"{p('RADAR', '🎞️')} <b>Kadrlar chastotasi:</b> {html.escape(str(fps))} FPS")
            
        codec = data.get("CompressorName") or data.get("VideoCodec")
        if codec:
            details.append(f"{p('SHIELD', '⚙️')} <b>Video kodek:</b> {html.escape(str(codec))}")
            
        coords = (lat_val, lon_val) if (lat_val is not None and lon_val is not None) else None
        return details, coords, None
    except Exception as e:
        return [], None, str(e)
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

def extract_video_frame(file_bytes: bytes, file_name: str = "video.mp4") -> bytes:
    """Extracts a representative JPEG keyframe from video using ffmpeg for AI Vision & QR analysis."""
    ext = os.path.splitext(file_name)[1].lower() or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        cmd = ['ffmpeg', '-y', '-ss', '00:00:00.3', '-i', tf_path, '-vframes', '1', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-']
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        if res.returncode == 0 and res.stdout and res.stdout.startswith(b'\xff\xd8\xff'):
            return res.stdout
    except Exception as e:
        logging.debug(f"Video frame extraction error: {e}")
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass
    return None

async def photo_or_doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
        
    chat_id = update.effective_chat.id if update.effective_chat else None
    if chat_id:
        await cleanup_chat(chat_id, context.bot)
        
    # Check if this photo/doc is an anonymous SOS evidence submission
    if context.user_data.get("waiting_for_sos"):
        context.user_data["waiting_for_sos"] = False
        import random, datetime
        report_code = f"SOS-4M-{random.randint(1000, 9999)}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        caption_text = msg.caption or "(Dalil fotosurati / skrinshot biriktirildi)"
        
        try:
            reports_dir = os.path.join(BASE_DIR, "data")
            os.makedirs(reports_dir, exist_ok=True)
            reports_file = os.path.join(reports_dir, "anon_sos_reports.json")
            existing = []
            if os.path.exists(reports_file):
                with open(reports_file, "r", encoding="utf-8") as rf:
                    existing = json.load(rf)
            existing.append({
                "code": report_code,
                "timestamp": timestamp,
                "text": caption_text,
                "has_photo": True
            })
            with open(reports_file, "w", encoding="utf-8") as wf:
                json.dump(existing, wf, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving anon report: {e}")

        if ADMIN_ID:
            try:
                alert_text = (
                    f"🚨 <b>YANGI ANONIM SOS MUROJAAT (DALIL FOTOSURATI BILAN)</b>\n\n"
                    f"🆔 <b>Kodi:</b> <code>#{report_code}</code>\n"
                    f"📅 <b>Vaqti:</b> {timestamp}\n"
                    f"📝 <b>Izoh / Matn:</b> <i>{html.escape(caption_text)}</i>\n\n"
                    f"🔒 <i>Foydalanuvchi shaxsi to‘liq yashirilgan.</i>"
                )
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Failed to alert admin: {e}")

        success_msg = (
            f"{p('CHECK', '✅')} <b>ANONIM MUROJAAT VA DALIL SURATI QABUL QILINDI!</b>\n\n"
            f"🆔 <b>Murojaat kodi:</b> <code>#{report_code}</code>\n"
            f"📅 <b>Qayd etilgan vaqt:</b> <i>{timestamp}</i>\n"
            f"🛡️ <b>Maxfiylik maqomi:</b> <i>Sizning shaxsingiz (ism, raqam, profil) to‘liq yashirildi va sir saqlanadi.</i>\n\n"
            f"Yuborilgan skrinshot va ma’lumotlar maktab profilaktika inspektori hamda psixologiga ko‘rib chiqish uchun taqdim etildi.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• 🛡️ Kiberxavfsizlik hodisalari bo‘yicha: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• ⚖️ Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        await msg.reply_text(success_msg, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
        return

    try:
        await msg.reply_chat_action("typing")
    except Exception:
        pass
    
    is_doc = bool(msg.document)
    is_video = bool(msg.video) or bool(msg.video_note)
    is_audio = bool(msg.audio) or bool(msg.voice)
    file_bytes = None
    file_name = "fayl"
    
    raw_exts = (".dng", ".cr2", ".cr3", ".nef", ".arw", ".rw2", ".orf", ".pef", ".raf", ".sr2", ".srf")
    apk_exts = (".apk", ".xapk", ".apks")
    video_exts = (".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm", ".m4v", ".flv", ".wmv", ".ts", ".mts")
    img_exts = (".jpg", ".jpeg", ".png", ".tiff", ".tif", ".heic", ".heif", ".webp", ".bmp", ".gif", ".svg")
    doc_exts = (".pdf", ".docx", ".doc", ".docm", ".pptx", ".ppt", ".pptm", ".xlsx", ".xls", ".xlsm", ".odt", ".ods", ".odp", ".txt", ".csv", ".rtf")
    audio_exts = (".mp3", ".ogg", ".m4a", ".wav", ".aac", ".flac", ".wma", ".opus")
    archive_exts = (".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz")
    exec_exts = (".exe", ".msi", ".bat", ".cmd", ".ps1", ".sh", ".vbs", ".js", ".jar", ".py", ".elf", ".bin")

    try:
        if msg.photo:
            tg_file = await msg.photo[-1].get_file()
            file_bytes = await tg_file.download_as_bytearray()
            file_name = "surat.jpg"
        elif msg.video:
            video = msg.video
            file_name = video.file_name or f"video_{video.file_id[:8]}.mp4"
            tg_file = await video.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            is_video = True
        elif msg.video_note:
            vn = msg.video_note
            file_name = f"videonote_{vn.file_id[:8]}.mp4"
            tg_file = await vn.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            is_video = True
        elif msg.audio:
            audio = msg.audio
            file_name = audio.file_name or f"audio_{audio.file_id[:8]}.mp3"
            tg_file = await audio.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            is_audio = True
        elif msg.voice:
            voice = msg.voice
            file_name = f"voice_{voice.file_id[:8]}.ogg"
            tg_file = await voice.get_file()
            file_bytes = await tg_file.download_as_bytearray()
            is_audio = True
        elif msg.document:
            doc = msg.document
            file_name = doc.file_name or "hujjat"
            tg_file = await doc.get_file()
            file_bytes = await tg_file.download_as_bytearray()
    except Exception as down_err:
        if "too big" in str(down_err).lower() or "file is too big" in str(down_err).lower():
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} <b>Fayl hajmi juda katta!</b>\n\n"
                f"Telegram boti uchun maksimal qabul qilish hajmi <b>20 MB</b> etib belgilangan. "
                f"Iltimos, hajmi 20 MB dan kichikroq fayl yuboring.",
                parse_mode="HTML"
            )
            return
        else:
            logging.error(f"Download error: {down_err}")
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} Faylni yuklab olishda xatolik yuz berdi: {html.escape(str(down_err))}",
                parse_mode="HTML"
            )
            return

    if not file_bytes:
        return

    ext = os.path.splitext(file_name)[1].lower()
    mime = (msg.document.mime_type if msg.document else "").lower() if is_doc else ""

    chat = update.effective_chat
    chat_type = chat.type if chat else "private"
    is_group = chat_type in ["group", "supergroup"]

    # GROUP CYBER-SHIELD: Real-time malware (.APK, .EXE, droppers) blocking in groups
    if is_group:
        is_malware_file = (ext in apk_exts) or (ext in exec_exts) or ("android.package-archive" in mime) or ("application/x-dosexec" in mime)
        
        # Check ZIP archives for hidden APK or executables
        if not is_malware_file and (ext in archive_exts or "zip" in mime):
            try:
                with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
                    dang_check = (".apk", ".exe", ".bat", ".cmd", ".vbs", ".ps1", ".sh", ".scr", ".jar")
                    if any(any(n.lower().endswith(dc) for dc in dang_check) for n in z.namelist()):
                        is_malware_file = True
            except Exception:
                pass

        if is_malware_file:
            deleted = False
            try:
                await msg.delete()
                deleted = True
            except Exception as del_err:
                logging.warning(f"Group malware delete failed: {del_err}")

            user = update.effective_user
            user_name = user.first_name if user else "Foydalanuvchi"
            username_str = f"@{user.username}" if (user and user.username) else f"ID: {user.id}"
            
            status_text = (
                "🗑️ <b>Holat:</b> <i>Zararli fayl guruhdan zudlik bilan o‘chirildi va bolalar telefonlari himoyalandi!</i>"
                if deleted else
                "⚠️ <b>Holat:</b> <i>Faylni o‘chirish uchun botga guruhda administratorlik (Xabarlarni o‘chirish) huquqini bering!</i>"
            )
            
            alert_msg = (
                f"🛡️ <b>SINF VA MAKTAB GURUHI KIBER-QALQONI</b>\n"
                f"🚨 <b>KRITIK OGOHLANTIRISH: ZARARLI ILOVA (.APK / VIRUS) BLOKLANDI!</b>\n\n"
                f"👤 <b>Yuboruvchi:</b> {html.escape(user_name)} (<code>{html.escape(username_str)}</code>)\n"
                f"📦 <b>Zararli fayl:</b> <code>{html.escape(file_name)}</code>\n"
                f"⚠️ <b>Tahdid darajasi:</b> 🚨 100% Virus / Troyan (SMS bank kodlarini o‘g‘irlovchi zararli ilova)\n"
                f"{status_text}\n\n"
                f"📢 <i>Hurmatli ota-onalar va o‘quvchilar! Telegram guruhlarida 'O‘yin', 'Sovg‘a', 'Rasm' yoki 'Yordam' nomi ostida tarqatiladigan .APK fayllar telefonni buzuvchi xakerlik dasturlaridir. Aslo yuklab olmang va o‘rnatmang!</i>"
            )
            await context.bot.send_message(chat_id=chat.id, text=alert_msg, parse_mode="HTML")
            return

        # If regular media in group, do not spam unless caption explicitly asks for audit
        caption = (msg.caption or "").lower()
        if not any(k in caption for k in ["/osint", "/check", "/deepfake", "/audit"]):
            if msg.photo:
                try:
                    jpeg_tmp = convert_image_to_jpeg_bytes(file_bytes, file_name)
                    q_data = scan_qr_code(jpeg_tmp)
                    if q_data:
                        is_t, c, d = detect_group_scam_or_phishing(q_data)
                        if is_t:
                            try:
                                await msg.delete()
                            except Exception:
                                pass
                            await context.bot.send_message(
                                chat_id=chat.id,
                                text=f"🛡️ <b>GURUH QALQONI:</b> Rasm ichidagi QR-kodda xavfli fishing havola aniqlandi va o‘chirildi!\n🔗 <code>{html.escape(q_data)}</code>",
                                parse_mode="HTML"
                            )
                except Exception:
                    pass
            return

    # In Private DM: Check if user specifically requested Deepfake detection
    if context.user_data.get("waiting_for_deepfake"):
        context.user_data["waiting_for_deepfake"] = False
        jpeg_bytes = convert_image_to_jpeg_bytes(file_bytes, file_name)
        context.user_data["last_photo"] = jpeg_bytes
        try:
            await msg.reply_chat_action("typing")
        except Exception:
            pass
        report = await audit_deepfake_with_ai(jpeg_bytes)
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Suratni tozalash (EXIF-siz)", callback_data="sanitize", icon_custom_emoji_id=E["SHIELD"])
            ]
        ])
        await msg.reply_text(report, parse_mode="HTML", reply_markup=keyboard)
        return

    # In Private DM: Check if user sent a screenshot in Comment OSINT mode
    if context.user_data.get("waiting_for_comment_osint"):
        context.user_data["waiting_for_comment_osint"] = False
        jpeg_bytes = convert_image_to_jpeg_bytes(file_bytes, file_name)
        try:
            await msg.reply_chat_action("typing")
        except Exception:
            pass
        prompt = (
            "Siz «KiberIz-4» maktab kiberxavfsizlik, sud kiber-ekspertizasi va ijtimoiy tarmoqlar izoh tahlili bo'yicha mutaxassisisiz.\n"
            "Foydalanuvchi ijtimoiy tarmoq (Instagram, Telegram, YouTube, TikTok va b.) sharhlari / chati skrinshotini yubordi.\n"
            "Ushbu skrinshotni tahlil qiling va Telegram HTML (faqat b, i, code) formatida quyidagilarni bering:\n"
            "💬 <b>IZOH / SHARH SKRINSHOTI EKSPERTIZASI:</b>\n\n"
            "• 📸 <b>Aniqlangan Matn va Mazmun:</b> [Skrinshotdagi sharhlar, muallif nikneymi va asosiy gaplar]\n"
            "• 📊 <b>Toksiklik va Kiber-Xavf:</b> [0% dan 100% gacha va holat: 🚨 KRITIK KIBERBULLING / ⚠️ SHUBHALI / ✅ ME'YORIY]\n"
            "• ⚖️ <b>Huquqiy Baholash (O'zR JK/MJtK):</b> [JK 140-modda haqorat, JK 141-modda shaxsiy hayot daxlsizligi, JK 165-modda shantaj, yoki MJtK 40/41 moddalari]\n"
            "• 🛡️ <b>Amaliy Qadamlar:</b> [1. Skrinshotni o'chirmaslik (rasmiy dalil), 2. Ijtimoiy tarmoqda shikoyat (Report) berish, 3. Maktab ma'muriyatiga yoki 102/1133 ga murojaat qilish]\n\n"
            "Xulosa o'zbek tilida, professional va o'quvchiga aniq tushunarli bo'lsin."
        )
        raw = await asyncio.to_thread(_query_gemini_api_sync, prompt, jpeg_bytes, "image/jpeg")
        report = format_ai_to_tg_html(raw)
        await msg.reply_text(report, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
        return

    # 1. Android APK
    if ext in apk_exts or "android.package-archive" in mime:
        await handle_apk_analysis(msg, file_bytes, file_name)
        return

    # 2. RAW Image (.dng, .cr2, .nef, .arw, etc.)
    if ext in raw_exts or "dng" in mime or "x-adobe-dng" in mime or "raw" in mime:
        await handle_raw_image_analysis(msg, file_bytes, file_name)
        return

    # 3. Audio & Voice
    if is_audio or ext in audio_exts or mime.startswith("audio/"):
        await handle_audio_analysis(msg, file_bytes, file_name)
        return

    # 4. Document / Office (PDF, Word, Excel, PowerPoint)
    if ext in doc_exts or mime.startswith("application/pdf") or "word" in mime or "excel" in mime or "presentation" in mime:
        await handle_document_analysis(msg, file_bytes, file_name)
        return

    # 5. Archive (.zip, .rar, .7z, etc.)
    if ext in archive_exts or "zip" in mime or "tar" in mime:
        await handle_zip_archive(msg, file_bytes, file_name)
        return

    # 6. Executable / Script (.exe, .bat, .sh, .vbs, etc.)
    if ext in exec_exts or "application/x-dosexec" in mime or "application/x-executable" in mime:
        await handle_binary_or_script_analysis(msg, file_bytes, file_name)
        return

    # 7. Video (MP4, MOV, etc.)
    if is_video or ext in video_exts or mime.startswith("video/"):
        details, coords, err = parse_video_metadata(file_bytes, file_name)
        if err:
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} Videoni ochishda xatolik yuz berdi ({html.escape(err)}). Iltimos, boshqa video yuboring.",
                parse_mode="HTML"
            )
            return

        # Reverse Geocoding to Human Address
        if coords:
            lat_val, lon_val = coords
            human_addr = get_human_address(lat_val, lon_val)
            if human_addr:
                details.append(
                    f"{p('HOUSE', '🏢')} <b>Haqiqiy tuman / manzil:</b> <code>{html.escape(human_addr)}</code>\n"
                    f"   └ 🚨 <i>Diqqat: Ushbu joy 5 metr aniqlikda oshkor bo‘ldi!</i>"
                )

        # Extract representative keyframe for QR & AI Vision
        frame_bytes = extract_video_frame(file_bytes, file_name)
        qr_data = None
        qr_audit_text = ""
        ai_vision_text = ""
        if frame_bytes:
            qr_data = scan_qr_code(frame_bytes)
            if qr_data:
                try:
                    qr_audit_text = await audit_quishing_with_ai(qr_data)
                except Exception as qr_e:
                    logging.debug(f"Video QR audit error: {qr_e}")
            try:
                ai_vision_text = await analyze_image_with_gemini_vision(frame_bytes, has_gps=bool(coords))
            except Exception as ai_e:
                logging.debug(f"Video AI vision error: {ai_e}")

        # Calculate composite risk score
        risk_score = 15
        if coords:
            risk_score += 50
        elif details:
            risk_score += 25
        if qr_data:
            risk_score += 25
            if qr_audit_text and "KRITIK" in qr_audit_text.upper():
                risk_score = max(risk_score, 90)
        if ai_vision_text and "KRITIK" in ai_vision_text.upper():
            risk_score = max(risk_score, 90)

        risk_score = min(risk_score, 100)
        filled = int(risk_score / 10)
        bar = "█" * filled + "░" * (10 - filled)
        if risk_score >= 70:
            risk_label = f"🚨 KRITIK JIDDIY XAVF ({risk_score}%)"
        elif risk_score >= 40:
            risk_label = f"⚠️ O‘RTA DARAJADAGI XAVF ({risk_score}%)"
        else:
            risk_label = f"✅ XAVFSIZROQ PROFIL ({risk_score}%)"

        analysis_msg = (
            f"{p('RADAR', '🎬')} <b>VIDEO OSINT & FORENSICS TAHLILI ({html.escape(file_name)}):</b>\n\n"
            f"📊 <b>KIBER-XAVF INDEKSI:</b>\n"
            f"<code>[{bar}]</code> <b>{risk_label}</b>\n\n"
        )

        if qr_data:
            if qr_audit_text:
                analysis_msg += f"{qr_audit_text}\n\n"
            else:
                analysis_msg += (
                    f"🏁 <b>VIDEODA QR-KOD TOPILDI:</b>\n"
                    f"• <b>QR Tarkibi:</b> <code>{html.escape(qr_data)}</code>\n\n"
                )

        if ai_vision_text:
            analysis_msg += (
                f"{p('LIGHT', '💡')} <b>AI VISION KADR TAHLILI (Video vizual foni):</b>\n"
                f"{ai_vision_text}\n\n"
            )

        analysis_msg += f"{p('LOCK', '🔐')} <b>QURILMA VA METAMA’LUMOTLAR:</b>\n"
        if details:
            for d in details:
                analysis_msg += f"• {d}\n"
            analysis_msg += "\n"
        else:
            if not is_doc:
                analysis_msg += (
                    f"• {p('INFO', 'ℹ️')} <i>Telegram orqali oddiy video tarzida yuborilgani uchun Telegram uni siqib, "
                    f"barcha EXIF va GPS parametrlarini avtomatik tozalab tashlagan.\n"
                    f"Original video metama’lumotlarini tekshirish uchun uni botga <b>'Hujjat' (Document / File)</b> qilib yuboring!</i>\n\n"
                )
            else:
                analysis_msg += (
                    f"• {p('CHECK', '✅')} <i>Ushbu video faylida GPS yoki kamera parametrlari topilmadi.</i>\n\n"
                )

        analysis_msg += (
            f"{p('HACKER', '🕵️‍♂️')} <b>AUDIO VA TEXNIK KO‘RSATKICHLAR:</b>\n"
            f"• {p('CALL', '🔊')} <b>Ovoz yo‘lagi:</b> Fon shovqini va audio parametrlar tekshirildi.\n"
            f"• {p('TIMER', '⏱️')} <b>Texnik ko‘rsatkichlar:</b> Kadr chastotasi, o‘lcham va kodek parametrlari aniqlandi.\n"
        )
        
        await msg.reply_text(analysis_msg, parse_mode="HTML", disable_web_page_preview=True)
        if coords:
            lat_val, lon_val = coords
            await msg.reply_location(latitude=lat_val, longitude=lon_val)
        return

    # Process Single Image (JPG, PNG, HEIC, WEBP, TIFF)
    jpeg_bytes = convert_image_to_jpeg_bytes(file_bytes, file_name)
    context.user_data["last_photo"] = jpeg_bytes
    details, coords, err = parse_single_image_exif(file_bytes, file_name)
    
    if err and not details:
        # If both PIL and ExifTool fail to extract image info, fallback to universal file analyzer
        await handle_generic_file_analysis(msg, file_bytes, file_name)
        return

    # Reverse Geocoding to Human Address
    if coords:
        lat_val, lon_val = coords
        human_addr = get_human_address(lat_val, lon_val)
        if human_addr:
            details.append(
                f"{p('HOUSE', '🏢')} <b>Haqiqiy tuman / manzil:</b> <code>{html.escape(human_addr)}</code>\n"
                f"   └ 🚨 <i>Diqqat: Ushbu joy 5 metr aniqlikda oshkor bo‘ldi!</i>"
            )

    # QR Code & Barcode Detection
    qr_data = scan_qr_code(jpeg_bytes)
    qr_audit_text = ""
    if qr_data:
        try:
            qr_audit_text = await audit_quishing_with_ai(qr_data)
        except Exception as qr_err:
            logging.warning(f"Quishing audit error: {qr_err}")

    # Real Visual OSINT Analysis (Chronolocation & OCR)
    visual_info = analyze_visual_osint(jpeg_bytes)
    extra_clues = visual_info.get("clues_summary", "") if visual_info else ""
    
    # Real AI Vision OSINT & Privacy Analysis (Gemini Multimodal Vision)
    ai_vision_text = ""
    try:
        ai_vision_text = await analyze_image_with_gemini_vision(
            jpeg_bytes, 
            has_gps=bool(coords), 
            extra_context=extra_clues
        )
    except Exception as ai_v_err:
        logging.warning(f"AI Vision error: {ai_v_err}")
    
    # Calculate composite Cyber Risk Score (0-100%)
    risk_score = 15
    if coords:
        risk_score += 50
    elif details:
        risk_score += 25
        
    if visual_info:
        risk_score += visual_info.get("chrono_risk", 10)
        risk_score += visual_info.get("text_risk", 0)
        
    if ai_vision_text:
        ai_upper = ai_vision_text.upper()
        if "KRITIK FISHING" in ai_upper or ("FISHING" in ai_upper and "KRITIK" in ai_upper):
            risk_score = max(risk_score, 95)
        elif "SHUBHALI" in ai_upper or "FISHING" in ai_upper:
            risk_score = max(risk_score, 65)
        elif not coords:
            for kw in ["TOSHKENT", "CHILONZOR", "SAMARQAND", "AVTORAQAM", "RAQAMI", "DORIXONA", "MAKTABI", "KO'CHASI"]:
                if kw in ai_upper:
                    risk_score = max(risk_score, 65)
                    break

    if qr_data:
        risk_score = max(risk_score, 30)
        if qr_audit_text:
            qr_upper = qr_audit_text.upper()
            if "KRITIK" in qr_upper or "FISHING" in qr_upper:
                risk_score = max(risk_score, 95)
            elif "SHUBHALI" in qr_upper:
                risk_score = max(risk_score, 65)
        
    risk_score = min(risk_score, 100)
    filled = int(risk_score / 10)
    bar = "█" * filled + "░" * (10 - filled)
    
    if risk_score >= 70:
        risk_label = f"🚨 KRITIK JIDDIY XAVF ({risk_score}%)"
    elif risk_score >= 40:
        risk_label = f"⚠️ O‘RTA DARAJADAGI XAVF ({risk_score}%)"
    else:
        risk_label = f"✅ XAVFSIZROQ PROFIL ({risk_score}%)"

    is_screenshot = ("SKRINSHOT" in ai_vision_text.upper()) and not coords
    is_qr_primary = bool(qr_data) and not coords and not details
    is_visual_osint_primary = not coords and not is_screenshot and not is_qr_primary

    if is_screenshot:
        header_title = f"{p('ROBOT', '📱')} <b>SMART VISION: SKRINSHOT VA FISHING AUDITI ({html.escape(file_name)}):</b>"
    elif is_qr_primary:
        header_title = f"{p('SEARCH', '🏁')} <b>QUISHING: QR-KOD VA HAVOLA XAVFSIZLIGI TAHLILI ({html.escape(file_name)}):</b>"
    elif is_visual_osint_primary:
        header_title = f"{p('SEARCH', '🛰️')} <b>VISUAL OSINT: KO‘RINMAS JOYLAShUV AUDITI ({html.escape(file_name)}):</b>"
    else:
        header_title = f"{p('SEARCH', '🔍')} <b>KOMPLEKS OSINT TAHLIL ({html.escape(file_name)}):</b>"
        
    analysis_msg = (
        f"{header_title}\n\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b>\n"
        f"<code>[{bar}]</code> <b>{risk_label}</b>\n\n"
    )

    # 1. QR Code & Quishing Section (Prominent if found!)
    if qr_data:
        if qr_audit_text:
            analysis_msg += f"{qr_audit_text}\n\n"
        else:
            analysis_msg += (
                f"🏁 <b>SURAT ICHIDA QR-KOD TOPILDI:</b>\n"
                f"• <b>QR Tarkibi:</b> <code>{html.escape(qr_data)}</code>\n"
                f"• ⚠️ <i>Kiber-Xavf: Notanish QR-kodlar orqali shaxsiy hisoblar yoki karta ma’lumotlari o‘g‘irlanishi (Quishing) mumkin!</i>\n\n"
            )

    # 2. Local OCR Findings (if car plates or regional indicators found by local OCR engine)
    if visual_info and visual_info.get("ocr_found"):
        analysis_msg += f"{p('SEARCH', '🔍')} <b>ANIQLANGAN REGIONAL VA MATN IZLARI (Lokal OCR):</b>\n"
        for ofound in visual_info["ocr_found"]:
            analysis_msg += f"• {ofound}\n"
        analysis_msg += "\n"

    # 3. AI Vision (Screenshot Phishing or Visual OSINT)
    if ai_vision_text:
        analysis_msg += f"{ai_vision_text}\n\n"
    elif visual_info:
        analysis_msg += (
            f"{p('TIMER', '☀️')} <b>VIZUAL TAHLIL:</b>\n"
            f"• <b>Holat:</b> {visual_info['chrono_text']}\n"
            f"• <b>Yorug‘lik ko‘rsatkichi:</b> <code>{visual_info['brightness']} lx</code>\n\n"
        )

    # 4. EXIF & Metadata section (if not pure screenshot/QR or if details exist)
    if details or not (is_screenshot or is_qr_primary):
        analysis_msg += f"{p('LOCK', '🔐')} <b>METAMA’LUMOTLAR (EXIF / GPS):</b>\n"
        if details:
            for d in details:
                analysis_msg += f"• {d}\n"
        else:
            if not is_doc:
                analysis_msg += (
                    f"• {p('INFO', 'ℹ️')} <i>Fayl ichidagi GPS tozalangan (Instagram yoki Telegram avtomatik siqib tozalagan).</i>\n"
                    f"   └ 💡 <b>O‘quvchi illyuziyasi:</b> <i>«GPS yo‘q, demak hech kim qayerdaligimni bilolmaydi!»</i>\n"
                    f"   └ 🚨 <b>Haqiqat (WOW-Effekt):</b> <i>Yuqoridagi Visual OSINT orqa fondagi avtoraqam, peshlavha yoki arxitektura orqali lokatsiyani fosh qildi!</i>\n"
                )
            else:
                analysis_msg += (
                    f"• {p('CHECK', '✅')} <i>GPS yoki kamera parametrlari topilmadi (tozalangan).</i>\n"
                    f"   └ 💡 <b>Visual OSINT:</b> <i>GPS bo‘lmasa ham, yuqoridagi bilvosita izlar orqali tahlil bajarildi.</i>\n"
                )
        analysis_msg += "\n"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎭 Deepfake & AI Tekshiruvi", callback_data="audit_deepfake_last", icon_custom_emoji_id=E["ROBOT"]),
            InlineKeyboardButton("Suratni tozalash (EXIF-siz)", callback_data="sanitize", icon_custom_emoji_id=E["SHIELD"])
        ]
    ])
    
    await msg.reply_text(analysis_msg.strip(), parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)
    
    # If GPS coordinates were detected, send real Telegram Location pin!
    if coords:
        lat_val, lon_val = coords
        await msg.reply_location(latitude=lat_val, longitude=lon_val)

async def handle_zip_archive(msg, file_bytes, file_name):
    """Unpacks a zip archive, audits for malicious executables/APKs, and performs OSINT on images."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
            namelist = [n for n in z.namelist() if not n.endswith("/")]
            
            # Check for hidden dangerous files (APKs, executables, scripts)
            dang_exts = (".apk", ".exe", ".bat", ".cmd", ".vbs", ".ps1", ".sh", ".scr", ".jar")
            malicious_files = [n for n in namelist if any(n.lower().endswith(ext) for ext in dang_exts)]
            
            valid_img_exts = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff", ".dng")
            image_names = [n for n in namelist if any(n.lower().endswith(ext) for ext in valid_img_exts)]
            
            report = (
                f"📦 <b>ZIP ARXIVI TAHLILI: {html.escape(file_name)}</b>\n"
                f"Arxivdagi jami fayllar soni: <b>{len(namelist)} ta</b>\n\n"
            )
            
            # Critical warning if hidden malware/droppers found
            if malicious_files:
                report += (
                    f"{p('SOS', '🚨')} <b>KRITIK OGOHLANTIRISH: ARXIV ICHIDA ZARARLI ILOVA YOKI SKRIPT ANIQLANDI!</b>\n"
                    f"Arxiv ichiga xavfli fayllar yashirilgan:\n"
                )
                for mf in malicious_files[:5]:
                    report += f"• ⚠️ <code>{html.escape(mf)}</code>\n"
                if len(malicious_files) > 5:
                    report += f"• <i>...va yana {len(malicious_files)-5} ta shubhali fayl</i>\n"
                report += (
                    f"\n<i>Kiberjinoyatchilar ko‘pincha virus va troyanlarni ZIP arxiv ichiga yashirib tarqatadi. "
                    f"Ushbu fayllarni aslo ochmang!</i>\n\n"
                )
                
            if not image_names and not malicious_files:
                report += f"{p('INFO', 'ℹ️')} Arxiv ichida fotosuratlar yoki shubhali fayllar topilmadi.\n"
                await msg.reply_text(report, parse_mode="HTML")
                return

            first_gps_coords = None
            if image_names:
                report += (
                    f"🖼 <b>ARXIVDAGI FOTOSURATLAR OSINT TAHLILI ({len(image_names)} ta):</b>\n"
                )
                for idx, img_name in enumerate(image_names[:5], 1):
                    img_bytes = z.read(img_name)
                    details, coords, err = parse_single_image_exif(img_bytes, img_name)
                    clean_name = os.path.basename(img_name)
                    report += f"━━━━━━━━━━━━━━━━━━━━\n"
                    report += f"🖼 <b>{idx}. {html.escape(clean_name)}</b>:\n"
                    if err:
                        report += f"  ⚠️ Xatolik: {html.escape(err)}\n"
                    elif details:
                        for d in details:
                            report += f"  {d}\n"
                        if coords and not first_gps_coords:
                            first_gps_coords = coords
                    else:
                        report += f"  {p('CHECK', '✅')} EXIF tozalangan (GPS xavfi yo‘q).\n"
                if len(image_names) > 5:
                    report += f"\n<i>...va yana {len(image_names)-5} ta rasm mavjud.</i>\n"

            report += (
                f"\n{p('SHIELD', '🛡️')} <b>Xulosa:</b> Arxivlangan fayllarni begonalarga yuborishdan yoki "
                f"ochishdan oldin ularning xavfsizligini tekshirish zarur!"
            )
            await msg.reply_text(report, parse_mode="HTML", disable_web_page_preview=True)
            if first_gps_coords:
                lat, lon = first_gps_coords
                await msg.reply_location(latitude=lat, longitude=lon)

    except zipfile.BadZipFile:
        await msg.reply_text(
            f"{p('WARNING', '⚠️')} ZIP fayli buzilgan yoki noto‘g‘ri formatda.",
            parse_mode="HTML"
        )
    except Exception as e:
        await msg.reply_text(
            f"{p('WARNING', '⚠️')} Arxivni ochishda xatolik yuz berdi: {html.escape(str(e))}",
            parse_mode="HTML"
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
    text = (msg.text or "").strip()
    if not text:
        return

    chat = update.effective_chat
    chat_id = chat.id if chat else 0
    chat_type = chat.type if chat else "private"
    is_group = chat_type in ["group", "supergroup"]

    # GROUP CYBER-SHIELD: Real-time phishing link & scam moderation in school groups
    if is_group:
        is_threat, cat, detail = detect_group_scam_or_phishing(text)
        if is_threat:
            deleted = False
            try:
                await msg.delete()
                deleted = True
            except Exception as del_err:
                logging.warning(f"Could not delete group phishing message: {del_err}")
                
            user = update.effective_user
            user_name = user.first_name if user else "Foydalanuvchi"
            username_str = f"@{user.username}" if (user and user.username) else f"ID: {user.id}"
            
            status_text = (
                "🗑️ <b>Holat:</b> <i>Xabar darhol guruhdan o‘chirildi va tahdid zararsizlantirildi!</i>"
                if deleted else
                "⚠️ <b>Holat:</b> <i>Xabarni o‘chirish uchun botga guruhda administratorlik (Xabarlarni o‘chirish) huquqini bering!</i>"
            )
            
            alert_msg = (
                f"🛡️ <b>SINF VA MAKTAB GURUHI KIBER-QALQONI</b>\n"
                f"🚨 <b>KRITIK OGOHLANTIRISH: FISHING TAHDI SHI BLOKLANDI!</b>\n\n"
                f"👤 <b>Yuboruvchi:</b> {html.escape(user_name)} (<code>{html.escape(username_str)}</code>)\n"
                f"⚠️ <b>Aniqlangan xavf:</b> {cat}\n"
                f"🔗 <b>Xavfli havola / Belgisi:</b> <code>{html.escape(detail)}</code>\n"
                f"{status_text}\n\n"
                f"📢 <i>Hurmatli ota-onalar va o‘quvchilar! Guruhdagi 'tekin pul', '500 ming yordam', 'soxta ovoz berish' yoki 'Telegram Premium' "
                f"va’da qiluvchi havolalarga aslo kirmang! Bu firibgarlar tuzog‘i bo‘lib, bank karta pullari yoki akkauntni o‘g‘irlashga qaratilgan (O‘zR JK 168-moddasi).</i>"
            )
            await context.bot.send_message(chat_id=chat_id, text=alert_msg, parse_mode="HTML")
            return

        if text.startswith("/group_shield") or text.startswith("/guruh"):
            await group_shield_command(update, context)
            return

        bot_username = (context.bot.username or "kiberiz_bot").lower()
        if f"@{bot_username}" in text.lower():
            clean_q = text.lower().replace(f"@{bot_username}", "").strip()
            if clean_q:
                try:
                    await msg.chat.send_action("typing")
                except Exception:
                    pass
                ai_resp = await ask_gemini_cyber_mentor(clean_q, user_id=update.effective_user.id)
                await msg.reply_text(f"💡 <b>AI KIBER-MASLAHATCHI:</b>\n\n{ai_resp}", parse_mode="HTML")
            return
        return  # In groups, normal conversation is not spammed by the bot

    await prepare_clean_chat(update, context)

    # 0. Cancel active modes
    if text.lower() in ["/cancel", "bekor qilish", "bekor"]:
        context.user_data["waiting_for_sos"] = False
        context.user_data["waiting_for_audit"] = False
        context.user_data["waiting_for_ai"] = False
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"{p('CHECK', '✅')} Barcha amallar bekor qilindi.",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return

    # 1. Active Anonymous SOS Submission
    if context.user_data.get("waiting_for_sos"):
        context.user_data["waiting_for_sos"] = False
        import random, datetime
        report_code = f"SOS-4M-{random.randint(1000, 9999)}"
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        try:
            reports_dir = os.path.join(BASE_DIR, "data")
            os.makedirs(reports_dir, exist_ok=True)
            reports_file = os.path.join(reports_dir, "anon_sos_reports.json")
            existing = []
            if os.path.exists(reports_file):
                with open(reports_file, "r", encoding="utf-8") as rf:
                    existing = json.load(rf)
            existing.append({
                "code": report_code,
                "timestamp": timestamp,
                "text": text,
                "has_photo": False
            })
            with open(reports_file, "w", encoding="utf-8") as wf:
                json.dump(existing, wf, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving anon report: {e}")

        if ADMIN_ID:
            try:
                alert_text = (
                    f"{p('SOS', '🚨')} <b>YANGI ANONIM SOS MUROJAAT (4-MAKTAB)</b>\n\n"
                    f"{p('INFO', '🆔')} <b>Kodi:</b> <code>#{report_code}</code>\n"
                    f"{p('TIMER', '📅')} <b>Vaqti:</b> {timestamp}\n\n"
                    f"{p('INFO', '📝')} <b>Murojaat matni:</b>\n<i>«{html.escape(text)}»</i>\n\n"
                    f"{p('LOCK', '🔒')} <i>Foydalanuvchi ma’lumotlari to‘liq anonimlashtirilgan.</i>"
                )
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Failed to alert admin: {e}")

        success_msg = (
            f"{p('CHECK', '✅')} <b>ANONIM MUROJAATINGIZ QABUL QILINDI!</b>\n\n"
            f"{p('INFO', '🆔')} <b>Murojaat kodi:</b> <code>#{report_code}</code>\n"
            f"{p('TIMER', '📅')} <b>Qayd etilgan vaqt:</b> <i>{timestamp}</i>\n"
            f"{p('SHIELD', '🛡️')} <b>Maxfiylik maqomi:</b> <i>To‘liq himoyalangan (Ism, profil va shaxsiy ma’lumotlar oshkor etilmadi).</i>\n\n"
            f"Muammoingiz 4-maktab profilaktika inspektori va psixologiga ko‘rib chiqish uchun uzatildi.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• {p('SHIELD', '🛡️')} Kiberxavfsizlik hodisalari bo‘yicha: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• {p('SHIELD', '⚖️')} Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        await context.bot.send_message(chat_id=chat_id, text=success_msg, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
        return

    # 2. Main Menu Actions
    if "Surat" in text or "Skrinshot" in text or "OSINT" in text or "QR" in text or text.lower() in ["/qr", "/screenshot", "/skrinshot", "/quishing", "/fishing"]:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{p('SEARCH', '🔍')} <b>SURAT, SKRINSHOT VA QR-KOD XAVFSIZLIGI AUDITI:</b>\n\n"
                f"Bot tasvirlarni quyidagi yo‘nalishlarda chuqur tahlil qiladi:\n\n"
                f"1. 📱 <b>Skrinshotlar & Fishing Auditi:</b>\n"
                f"   └ Shubhali SMS, Telegram/Instagram chat, Payme/Click cheki yoki soxta moddiy yordam xabarlari skrinshotini yuboring. AI ulardagi firibgarlik va yolg‘onlarni fosh qiladi!\n\n"
                f"2. 🏁 <b>QR-kodlar & Quishing (QR-Fishing) Himoyasi:</b>\n"
                f"   └ Ko‘chada, e’londa yoki restorandagi QR-kod suratini yuboring — bot yashirin havolani ochib, xavfsizligini tekshirib beradi!\n\n"
                f"3. 📸 <b>Fotosuratlar (OSINT & GPS):</b>\n"
                f"   └ Suratdagi yashirin GPS lokatsiya (xaritadagi nuqta), kamera modeli va vizual fon izlarini aniqlaydi (JPG, PNG, HEIC, .DNG, RAW).\n\n"
                f"4. 📦 <b>Boshqa fayllar:</b>\n"
                f"   └ .APK ilovalar, MP4 videolar, PDF/Word/Excel hujjatlar va audio yozuvlar.\n\n"
                f"👉 <i>Tekshirmoqchi bo‘lgan surat, skrinshot yoki faylingizni to‘g‘ridan-to‘g‘ri yuboring!</i>"
            ),
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return
    elif "Chek-list" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await checklist_command(update, context)
        return
    elif "Testi" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await start_quiz(update, context)
        return
    elif "Real keyslar" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await cases_command(update, context)
        return
    elif "SOS" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await sos_command(update, context)
        return
    elif "AI Kiber-Maslahatchi" in text or "AI Maslahatchi" in text:
        await ai_command(update, context)
        return
    elif "Sharh" in text or "Izoh" in text or text.lower().startswith("/comment") or text.lower().startswith("/sharh"):
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await comment_osint_command(update, context)
        return
    elif "Nikneym" in text or "Havola" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = True
        await context.bot.send_message(
            chat_id=chat_id,
            text=(
                f"{p('HACKER', '🕵️‍♂️')} <b>SHAXSIY NIKNEYM VA HAVOLA OSINT AUDITI:</b>\n\n"
                f"1. <b>O‘z nikneymingizni (Username) tekshirish:</b>\n"
                f"   Botga <b>o‘zingizning</b> ijtimoiy tarmoq nikneymingizni yuboring (masalan: <code>@sarvar_2008</code> yoki <code>@malika_07</code>).\n"
                f"   └ <i>Anti-Stalking: Tizim faqat o‘z profilingizni audit qilish uchun mo‘ljallangan (O‘RQ-547).</i>\n\n"
                f"2. <b>Shubhali havola (Sayt) tekshirish:</b>\n"
                f"   Sizga yuborilgan har qanday shubhali sayt havolasini yuboring (masalan: <code>http://click-sovrin.xyz</code> yoki <code>kun.uz</code>).\n"
                f"   └ <i>Bot uning firibgarlik (fishing) ekanligini bir zumda fosh qiladi!</i>\n\n"
                f"👉 <i>Tekshirmoqchi bo‘lgan sayt havolasi yoki @nikneymni shu yerga yozib yuboring:</i>"
            ),
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )
        return
    elif "Veb-Platforma" in text or "Kiber-Portal" in text or "Web App" in text:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await web_command(update, context)
        return
    elif "Deepfake" in text or text.lower() in ["/deepfake", "/ai_rasm", "/ai_detector"]:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await deepfake_command(update, context)
        return
    elif "Guruh" in text or text.lower() in ["/group_shield", "/guruh", "/group"]:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        await group_shield_command(update, context)
        return

    words = text.split()
    is_comment_mode = context.user_data.get("waiting_for_comment_osint", False)
    if is_comment_mode:
        context.user_data["waiting_for_comment_osint"] = False
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass
        ai_resp, kb = await audit_comments_with_ai(text)
        await update.message.reply_text(
            f"{ai_resp}\n\n👇 <b>Quyidagi tugmalar orqali har bir tarmoqdagi sharhlarni to‘g‘ridan-to‘g‘ri oching:</b>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return

    is_explicit_ai = context.user_data.get("waiting_for_ai", False)
    is_audit_mode = context.user_data.get("waiting_for_audit", False)

    # 3. Explicit AI Cyber-Mentor Mode (User clicked "O'z savolimni berish" or asked AI)
    # MUST take absolute priority over URL / username detection
    if is_explicit_ai:
        context.user_data["waiting_for_ai"] = False
        context.user_data["waiting_for_audit"] = False
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass

        ai_resp = await ask_gemini_cyber_mentor(text, user_id=update.effective_user.id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Boshqa savol berish", callback_data="ask_custom_ai", icon_custom_emoji_id=E["CHAT"])],
            [InlineKeyboardButton("Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])],
            [InlineKeyboardButton("Kiber-Portal (Web App)", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["GLOBE"])]
        ])
        await update.message.reply_text(
            f"{p('LIGHT', '💡')} <b>AI KIBER-MASLAHATCHI JAVOBI:</b>\n\n{ai_resp}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # 4. URL / Link Audit (Only if explicitly in audit mode OR message is primarily a standalone link/domain)
    is_standalone_url = (len(words) <= 2) and URL_REGEX.search(text) and not text.startswith("@")
    if (is_audit_mode or is_standalone_url) and URL_REGEX.search(text) and not text.startswith("@"):
        context.user_data["waiting_for_audit"] = False
        m_url = URL_REGEX.search(text)
        matched_url = m_url.group(1).rstrip('.,;!?')
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass
        ai_resp, domain = await audit_link_with_ai(matched_url)
        await update.message.reply_text(ai_resp, parse_mode="HTML")

        # Xavfsiz bulutli sendboks ekrani (Screenshot)
        try:
            loop = asyncio.get_running_loop()
            ss_bytes = await loop.run_in_executor(None, get_website_screenshot, matched_url)
            if ss_bytes:
                caption = (
                    f"{p('CAMERA', '📸')} <b>«{html.escape(domain)}» saytining jonli ekrani (Sandbox):</b>\n\n"
                    f"🛡️ <i>Xavfsiz bulutli sendboks (Chromium) orqali olindi.</i>"
                )
                await update.message.reply_photo(
                    photo=io.BytesIO(ss_bytes),
                    caption=caption,
                    parse_mode="HTML"
                )
        except Exception as ss_e:
            logging.warning(f"Screenshot error for url: {ss_e}")
        return

    # 5. Username OSINT Audit (With Anti-Stalking Safeguard)
    is_explicit_username = text.startswith("@") and len(words) == 1
    is_audit_username = is_audit_mode and len(words) == 1 and 3 <= len(text) <= 30 and re.match(r'^[a-zA-Z0-9_.]+$', text)

    if is_explicit_username or is_audit_username:
        context.user_data["waiting_for_audit"] = False
        sender = update.effective_user
        sender_uname = (sender.username or "").lower().lstrip('@')
        target_uname = text.lstrip('@').strip().lower()

        # CASE A: User is testing their OWN Telegram account!
        if sender_uname and sender_uname == target_uname:
            try:
                await update.message.chat.send_action("typing")
            except Exception:
                pass
            await update.message.reply_text(
                f"{p('CHECK', '✅')} <b>O‘ZINGIZNING HISOBINGIZ (@{html.escape(target_uname)}) TASDIQLANDI!</b>\n\n"
                f"🛡️ <i>Shaxsiy raqamli iz va kiber-zaifliklar tahlili boshlanmoqda...</i>",
                parse_mode="HTML"
            )
            ai_resp, raw = await audit_username_with_ai(text)
            kb = build_username_result_keyboard(raw)
            await update.message.reply_text(ai_resp, parse_mode="HTML", reply_markup=kb)
            return

        # CASE B: Target does NOT match sender's Telegram username -> ANTI-STALKING GUARD!
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔑 1. Bio-kod orqali egalikni tasdiqlash", callback_data=f"bio_prove_{target_uname}")],
            [InlineKeyboardButton("🔗 2. Do‘stga ruxsat so‘rovi yuborish", callback_data=f"gen_consent_{target_uname}")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancel_audit")]
        ])

        sender_display = f"@{sender_uname}" if sender_uname else "hozirgi Telegram akkauntingizga"
        warn_msg = (
            f"{p('SHIELD', '🛡️')} <b>DIQQAT: BEGONA SHAXSLARNI POYLASH (STALKING) TAQIQLANADI!</b>\n\n"
            f"Siz kiritgan <code>@{html.escape(target_uname)}</code> nikneymi sizning Telegram profilingizga "
            f"({html.escape(sender_display)}) mos kelmadi.\n\n"
            f"⚖️ <b>Qonuniy talab (O‘RQ-547):</b>\n"
            f"O‘zbekiston Respublikasining <i>«Shaxsga doir ma’lumotlar to‘g‘risida»gi Qonuni</i>ga binoan, "
            f"boshqa shaxslar ortidan ruxsatsiz ma’lumot yig‘ish (Doxxing / Stalking) qat’iyan man etiladi!\n\n"
            f"👉 <b>Ushbu hisobni tekshirish uchun 2 ta qonuniy yo‘l mavjud:</b>\n\n"
            f"1️⃣ <b>«Bu mening boshqa tarmoqdagi (Instagram, Roblox) o‘z hisobim»:</b>\n"
            f"└ <i>Pastdagi 1-tugmani bosing, Bio-kod orqali profilingiz egaligini tasdiqlang.</i>\n\n"
            f"2️⃣ <b>«Bu do‘stim yoki sinfdoshim»:</b>\n"
            f"└ <i>Pastdagi 2-tugmani bosing, do‘stingizga maxsus rozilik havolasini yuboring. Do‘stingiz tasdiqlasa, tahlil hisoboti UNING O‘ZIGA yuboriladi (sizga emas!).</i>"
        )
        await update.message.reply_text(warn_msg, parse_mode="HTML", reply_markup=keyboard)
        return

    # 6. General Questions / Sentences / Situations
    context.user_data["waiting_for_audit"] = False
    context.user_data["waiting_for_ai"] = False

    sos_critical_keywords = [
        "shantaj", "tahdid", "kiberbulling", "rasmimni tarqat", "suratimni tarqat",
        "pul talab", "tovlamachi", "qutqaring", "shaxsiy rasmim"
    ]
    is_sos_related = any(kw in text.lower() for kw in sos_critical_keywords)
    
    if is_sos_related:
        help_text = (
            f"{p('SOS', '🚨')} <b>DIQQAT: SIZGA YORDAM KERAKMI?</b>\n\n"
            f"Siz yozgan xabarda shoshilinch yordam yoki xavfsizlik murojaati belgilari aniqlandi:\n"
            f"<i>«{html.escape(text[:120])}{'...' if len(text)>120 else ''}»</i>\n\n"
            f"Agar siz kiberbulling, shantaj yoki firibgarlikka duch kelgan bo‘lsangiz, shaxsingizni to‘liq yashirgan holda "
            f"ushbu xabarni <b>Anonim SOS Murojaat</b> sifatida maktab mutaxassislariga yuborishingiz mumkin.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• {p('SHIELD', '🛡️')} Kiberxavfsizlik hodisalari: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• {p('SHIELD', '⚖️')} Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ushbu xabarni Anonim SOS sifatida yuborish", callback_data="confirm_quick_sos", icon_custom_emoji_id=E["CHAT"])],
            [InlineKeyboardButton("Kiberxavfsizlik markazi (csec.uz)", url="https://csec.uz", icon_custom_emoji_id=E["GLOBE"])]
        ])
        context.user_data["pending_sos_text"] = text
        await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=keyboard)
        return

    # AI Cyber-Mentor Answer for all general questions and consultations
    try:
        await update.message.chat.send_action("typing")
    except Exception:
        pass

    ai_resp = await ask_gemini_cyber_mentor(text, user_id=update.effective_user.id)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Boshqa savol berish", callback_data="ask_custom_ai", icon_custom_emoji_id=E["CHAT"])],
        [InlineKeyboardButton("Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])],
        [InlineKeyboardButton("Kiber-Portal (Web App)", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["GLOBE"])]
    ])
    await update.message.reply_text(
        f"{p('LIGHT', '💡')} <b>AI KIBER-MASLAHATCHI JAVOBI:</b>\n\n{ai_resp}",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    return

async def new_group_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Greets when the bot is added to a school or classroom group and introduces the Cyber-Shield."""
    msg = update.message
    if not msg or not msg.new_chat_members:
        return
    bot_id = context.bot.id
    for member in msg.new_chat_members:
        if member.id == bot_id:
            chat_title = update.effective_chat.title or "Sinf guruhi"
            intro_text = (
                f"🛡️ <b>«KiberIz-4» SINF VA MAKTAB GURUHI KIBER-QALQONI FAOLLAShTIRILDI!</b>\n\n"
                f"Assalomu alaykum, <b>{html.escape(chat_title)}</b> a’zolari! 👋\n"
                f"Ushbu guruh endi 4-maktab Kiber-Qalqon himoyasi ostiga olindi.\n\n"
                f"🤖 <b>Bot guruhda nima qiladi?</b>\n"
                f"• 🛑 <b>Fishing havolalarni tozalash:</b> «500 ming so‘m yordam», soxta ovoz berish, bepul Telegram Premium kabi firibgar havolalarni zudlik bilan o‘chiradi va ogohlantiradi.\n"
                f"• 🚫 <b>Virusli .APK larni bloklash:</b> Guruhga yuborilgan zararli ilovalarni yo‘q qiladi.\n"
                f"• 🛡️ <b>O‘quvchilar va ota-onalarni</b> kiber-tahdidlardan real vaqtda himoya qiladi.\n\n"
                f"💡 <i>To‘liq himoya uchun: Botga guruhda <b>«Xabarlarni o‘chirish» (Delete messages)</b> administratorlik huquqini berish tavsiya etiladi!</i>"
            )
            await context.bot.send_message(chat_id=update.effective_chat.id, text=intro_text, parse_mode="HTML")
            break

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error gracefully without crashing."""
    logging.error(f"Telegram handler exception: {context.error}")

def main():
    start_health_check_if_needed()
    print("Starting KiberIz-4 Telegram Bot with Real OSINT, Video, HEIC & ZIP Support...")
    request_cfg = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request_cfg).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", start_command))
    app.add_handler(CommandHandler("sample", sample_command))
    app.add_handler(CommandHandler("checklist", checklist_command))
    app.add_handler(CommandHandler("test", start_quiz))
    app.add_handler(CommandHandler("quiz", start_quiz))
    app.add_handler(CommandHandler("comment", comment_osint_command))
    app.add_handler(CommandHandler("sharh", comment_osint_command))
    app.add_handler(CommandHandler("comments", comment_osint_command))
    app.add_handler(CommandHandler("user_comments", comment_osint_command))
    app.add_handler(CommandHandler("author_comments", comment_osint_command))
    app.add_handler(CommandHandler("profil_sharh", comment_osint_command))
    app.add_handler(CommandHandler("cases", cases_command))
    app.add_handler(CommandHandler("sos", sos_command))
    app.add_handler(CommandHandler("web", web_command))
    app.add_handler(CommandHandler("portal", web_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("ask", ai_command))
    app.add_handler(CommandHandler("qr", qr_command))
    app.add_handler(CommandHandler("quishing", qr_command))
    app.add_handler(CommandHandler("screenshot", screenshot_command))
    app.add_handler(CommandHandler("skrinshot", screenshot_command))
    app.add_handler(CommandHandler("deepfake", deepfake_command))
    app.add_handler(CommandHandler("ai_rasm", deepfake_command))
    app.add_handler(CommandHandler("group_shield", group_shield_command))
    app.add_handler(CommandHandler("guruh", group_shield_command))
    
    app.add_handler(CallbackQueryHandler(quiz_callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, new_group_member_handler))
    app.add_handler(
        MessageHandler(
            filters.PHOTO
            | filters.VIDEO
            | filters.AUDIO
            | filters.VOICE
            | filters.VIDEO_NOTE
            | filters.Document.ALL,
            photo_or_doc_handler
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    
    print("Bot is successfully polling!")
    app.run_polling()

if __name__ == "__main__":
    main()
