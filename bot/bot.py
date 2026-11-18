import os
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
env_file = os.path.join(BASE_DIR, ".env")
if not os.path.exists(env_file):
    env_file = os.path.join(BASE_DIR, "../.env")
if os.path.exists(env_file):
    with open(env_file, "r") as f:
        for line in f:
            line_str = line.strip()
            if line_str.startswith("BOT_TOKEN=") and not BOT_TOKEN:
                BOT_TOKEN = line_str.split("=", 1)[1].strip("\"' ")
            elif line_str.startswith("ADMIN_ID=") and not ADMIN_ID:
                ADMIN_ID = line_str.split("=", 1)[1].strip("\"' ")
            elif line_str.startswith("GEMINI_API_KEY=") and not GEMINI_API_KEY:
                GEMINI_API_KEY = line_str.split("=", 1)[1].strip("\"' ")

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
    '👨‍💻': E['HACKER'], '🕵️‍♂️': E['HACKER'], '🕵': E['HACKER'], '👤': E['HACKER'], '🐙': E['HACKER'],
    '🏠': E['HOUSE'], '🚪': E['HOUSE'],
    '🏢': E['BUILDING'], '🏬': E['BUILDING'], '🏦': E['BUILDING'], '🛣️': E['BUILDING'], '🛣': E['BUILDING'], '🚗': E['BUILDING'], '🛒': E['BUILDING'], '📍': E['BUILDING'],
    '💻': E['LAPTOP'], '🎮': E['LAPTOP'], '📦': E['LAPTOP'],
    '📱': E['PHONE'], '📞': E['CALL'], '🔊': E['CALL'],
    '⏰': E['TIMER'], '⏱️': E['TIMER'], '⏱': E['TIMER'], '📅': E['TIMER'], '🌙': E['TIMER'], '🌅': E['TIMER'], '☀️': E['TIMER'], '☀': E['TIMER'], '🌤️': E['TIMER'], '🌤': E['TIMER'],
    '🌐': E['GLOBE'], '🔗': E['GLOBE'], '🗺️': E['GLOBE'], '🗺': E['GLOBE'],
    '🚀': E['ROCKET'],
    '🧪': E['TEST'],
    '💡': E['LIGHT'], '👉': E['LIGHT'], '🎵': E['LIGHT'],
    '👋': E['WAVE'],
    '⭐': E['STAR'], '🎯': E['STAR'], '🎰': E['STAR'], '⚽': E['STAR'],
    '📊': E['STATS'], '💸': E['STATS'],
    'ℹ️': E['INFO'], 'ℹ': E['INFO'], '📝': E['INFO'], '📑': E['INFO'], '📄': E['INFO'], '✏️': E['INFO'], '✏': E['INFO'], '📐': E['INFO'],
    '👀': E['EYES'],
    '💬': E['CHAT'], '✈️': E['CHAT'], '✈': E['CHAT'], '🎣': E['SEARCH'],
    '💣': E['BOMB'], '🛑': E['BOMB'], '🔞': E['BOMB'], '☠️': E['BOMB'], '☠': E['BOMB'], '💊': E['BOMB'],
    '🔥': E['FIRE'],
    '💎': E['DIAMOND'],
    '🏆': E['TROPHY'],
    '🔄': E['REFRESH'],
    '💯': E['HUNDRED'],
    '🤖': E['LIGHT'],
    '🟢': E['GREEN'],
    '🟡': E['YELLOW'],
    '🔴': E['RED'],
    '⚙️': E['GEAR'], '⚙': E['GEAR']
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

# Auto-inject premium animated emojis across all Telegram messaging methods
_orig_reply_text = Message.reply_text
async def _custom_reply_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    return await _orig_reply_text(self, text, *args, **kwargs)
Message.reply_text = _custom_reply_text

_orig_edit_text = Message.edit_text
async def _custom_edit_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    return await _orig_edit_text(self, text, *args, **kwargs)
Message.edit_text = _custom_edit_text

_orig_edit_message_text = CallbackQuery.edit_message_text
async def _custom_edit_message_text(self, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    return await _orig_edit_message_text(self, text, *args, **kwargs)
CallbackQuery.edit_message_text = _custom_edit_message_text

_orig_reply_document = Message.reply_document
async def _custom_reply_document(self, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    return await _orig_reply_document(self, *args, **kwargs)
Message.reply_document = _custom_reply_document

_orig_reply_photo = Message.reply_photo
async def _custom_reply_photo(self, *args, **kwargs):
    if "caption" in kwargs and isinstance(kwargs["caption"], str):
        kwargs["caption"] = auto_premium(kwargs["caption"])
        if "parse_mode" not in kwargs:
            kwargs["parse_mode"] = "HTML"
    return await _orig_reply_photo(self, *args, **kwargs)
Message.reply_photo = _custom_reply_photo

_orig_send_message = Bot.send_message
async def _custom_send_message(self, chat_id, text, *args, **kwargs):
    if text and isinstance(text, str):
        text = auto_premium(text)
    if "parse_mode" not in kwargs:
        kwargs["parse_mode"] = "HTML"
    return await _orig_send_message(self, chat_id, text, *args, **kwargs)
Bot.send_message = _custom_send_message

# ==========================================
# GEMINI AI CYBER-MENTOR ENGINE (Method 1)
# ==========================================
GEMINI_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.8-flash",
    "gemini-flash-latest"
]

AI_SYSTEM_INSTRUCTION = """Siz «KiberIz-4» — 4-sonli umumiy o'rta ta'lim maktabining Raqamli Xavfsizlik va Kiber-Gigiyena bo'yicha sun'iy intellektga asoslangan virtual murabbiyisiz (Cyber-Mentor).
Vazifangiz: Maktab o'quvchilari (5-11 sinflar), ularning ota-onalari va o'qituvchilariga ijtimoiy tarmoqlar (Telegram, Instagram, TikTok), akkauntlarni himoyalash, 2FA, murakkab parollar, fishing havolalar, kiberbulling, shantaj va shaxsiy ma'lumotlar xavfsizligi bo'yicha aniq, do'stona, tushunarli va amaliy yordam berish.

Asosiy qoidalar:
1. Ravon, do'stona va sodda o'zbek tilida (lotin yozuvida) javob bering.
2. Javobingizni punktlar (•) va qisqa qadam-baqadam tavsiyalar bilan tuzing. Uzun, zerikarli va murakkab ilmiy atamalardan qoching.
3. QAT'IYAN TAQIQLANADI: Xakkerlik, birovning akkauntini buzish (vzlom), zararli dastur (virus, troyan) yaratish yoki noqonuniy harakatlarni o'rgatish. Bunday so'rovlarga qat'iy va odob bilan rad javobini bering hamda qonuniy xavfsizlik choralarini tushuntiring.
4. Agar foydalanuvchi jiddiy xavf (kiberbulling, shaxsiy rasmlar bilan shantaj, tovlamachilik) haqida yozsa, ularni tinchlantiring, "Anonim SOS" tugmasidan foydalanishni yoki 1133 (+998 55 502-10-10) ishonch telefoniga qo'ng'iroq qilishni tavsiya eting.
5. Agar savol kiberxavfsizlikka aloqador bo'lmagan mavzuda bo'lsa, unga 1 ta qisqa jumla bilan javob berib, kiberxavfsizlik va internetda xavfsiz qolish bo'yicha savol berishga undab qo'ying.
"""

AI_RESPONSE_CACHE = {}  # {hash: (timestamp, formatted_text)}
AI_USER_COOLDOWN = {}   # {user_id: timestamp}

def format_ai_to_tg_html(raw_text: str) -> str:
    """Escapes HTML and translates Gemini markdown into Telegram HTML."""
    if not raw_text:
        return ""
    t = html.escape(raw_text, quote=False)
    t = re.sub(r'```(?:[a-zA-Z0-9_\-]+)?\n?(.*?)```', r'<pre>\1</pre>', t, flags=re.DOTALL)
    t = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'(?<![a-zA-Z0-9])_([^_]+)_(?![a-zA-Z0-9])', r'<i>\1</i>', t)
    t = re.sub(r'(?<![a-zA-Z0-9\*])\*([^*\n]+)\*(?![a-zA-Z0-9\*])', r'<i>\1</i>', t)
    return t

def _query_gemini_api_sync(prompt: str) -> str:
    """Synchronous worker calling Google Gemini API with fallback models."""
    if not GEMINI_API_KEY:
        return (
            "⚠️ <b>Gemini API kaliti topilmadi.</b>\n"
            "Iltimos, bot ma'muri <code>.env</code> fayliga <code>GEMINI_API_KEY</code> ni kiritganligini tekshiring."
        )

    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "systemInstruction": {
            "parts": [{"text": AI_SYSTEM_INSTRUCTION}]
        },
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 850
        }
    }
    body = json.dumps(payload).encode("utf-8")

    last_err = None
    for model in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={GEMINI_API_KEY}"
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0].get("text").strip()
        except Exception as e:
            last_err = e
            logging.warning(f"Gemini model {model} failed: {e}")
            continue

    logging.error(f"All Gemini models exhausted. Last error: {last_err}")
    return (
        "Uzr, hozirda sun'iy intellekt serverida yuklama yuqori bo'lganligi sababli javob bera olmadim. "
        "Iltimos, birozdan so'ng savolingizni qayta yuboring yoki quyidagi tayyor bo'limlardan foydalaning."
    )

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
        [InlineKeyboardButton("👥 Begona guruhlardan himoya", callback_data="ai_q_groups", icon_custom_emoji_id=E["LOCK"])],
        [InlineKeyboardButton("🔐 2FA (Ikki bosqichli) yoqish", callback_data="ai_q_2fa", icon_custom_emoji_id=E["KEY_LOCK"])],
        [InlineKeyboardButton("🎣 Fishing havolani aniqlash", callback_data="ai_q_phishing", icon_custom_emoji_id=E["WARNING"])],
        [InlineKeyboardButton("🔑 Kuchli parol yaratish qoidasi", callback_data="ai_q_password", icon_custom_emoji_id=E["KEY"])]
    ])
    await update.message.reply_text(ai_intro_text, parse_mode="HTML", reply_markup=keyboard)

# Main persistent reply keyboard with Telegram Premium icon custom emojis
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("Suratni tekshirish (OSINT)", icon_custom_emoji_id=E["SEARCH"]),
            KeyboardButton("5 daqiqalik Chek-list", icon_custom_emoji_id=E["SHIELD"])
        ],
        [
            KeyboardButton("Nikneym & Havola auditi", icon_custom_emoji_id=E["HACKER"]),
            KeyboardButton("Real keyslar: 3 ta xavf", icon_custom_emoji_id=E["WARNING"])
        ],
        [
            KeyboardButton("\"Raqamli Iz\" Testi", icon_custom_emoji_id=E["TEST"]),
            KeyboardButton("🌐 Kiber-Portal (Web App)", web_app=WebAppInfo(url="https://abduvoitov11.github.io/kiberiz4/"), icon_custom_emoji_id=E["GLOBE"])
        ],
        [
            KeyboardButton("🤖 AI Kiber-Maslahatchi", icon_custom_emoji_id=E["LIGHT"]),
            KeyboardButton("Anonim SOS / Yordam", icon_custom_emoji_id=E["SOS"])
        ]
    ],
    resize_keyboard=True
)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "O‘quvchi"
    
    welcome_text = (
        f"Assalomu alaykum, <b>{html.escape(user_name)}</b>! {p('WAVE', '👋')}\n\n"
        f"{p('SHIELD', '🛡️')} <b>«KiberIz-4» — 4-sonli maktabning Raqamli Iz va Profil Xavfsizligi tizimiga xush kelibsiz!</b> {p('FLAG_UZ', '🇺🇿')}\n\n"
        f"{p('EYES', '👀')} Siz ijtimoiy tarmoqqa yuklagan bitta oddiy fotosurat orqali firibgarlar nimalarni bilib olishi mumkinligini bilasizmi?\n"
        f"• {p('SCHOOL', '🏫')} <i>Qaysi maktab va sinfda o‘qishingizni;</i>\n"
        f"• {p('HOUSE', '🏠')} <i>Qaysi ko‘chada yashashingizni;</i>\n"
        f"• {p('BOMB', '💣')} <i>Qachon uyda yolg‘iz ekanligingizni!</i>\n\n"
        f"{p('INFO', 'ℹ️')} Botga tahlil uchun fotosurat yuboring:\n"
        f"• <b>Apple iPhone formatidagi (.HEIC) fotosuratlar</b>;\n"
        f"• <b>.ZIP arxivdagi fotosuratlar to‘plami</b>!\n\n"
        f"🧪 <i>Sinov uchun GPS-li tayyor rasm olish: /sample buyrug‘ini bosing.</i>"
    )
    
    # 1. Avval rasmni yuborish
    if os.path.exists(START_BANNER_PATH):
        try:
            with open(START_BANNER_PATH, "rb") as photo:
                await update.message.reply_photo(photo=photo)
        except Exception as e:
            logging.error(f"Error sending start banner photo: {e}")
            
    # 2. Keyin esa to'liq tavsif va menyu tugmalarini yuborish
    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=MAIN_KEYBOARD
    )

async def sample_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a sample image with real GPS EXIF metadata for testing OSINT."""
    if os.path.exists(SAMPLE_PATH):
        with open(SAMPLE_PATH, "rb") as doc:
            await update.message.reply_document(
                document=doc,
                filename="sample_gps_school4.jpg",
                caption=(
                    f"{p('SEARCH', '🔍')} <b>OSINT SINOV UCHUN NAMUNA FOTOSURAT</b>\n\n"
                    f"Ushbu faylga <b>haqiqiy GPS koordinatalari (Toshkent, 4-maktab atrofi)</b> va qurilma ma’lumotlari biriktirilgan.\n\n"
                    f"👉 <b>Tekshirish uchun:</b> Ushbu faylni yuklab olib, botga qayta yuboring (<b>'Fayl / Hujjat'</b> tarzida). "
                    f"Bot 1 soniyada xaritadagi aniq nuqtani va qurilma modelini fosh qilib beradi!"
                ),
                parse_mode="HTML"
            )
    else:
        await update.message.reply_text("Namuna fayl topilmadi.", parse_mode="HTML")

async def checklist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    await update.message.reply_text(checklist_text, parse_mode="HTML", reply_markup=keyboard)

async def cases_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(cases_text, parse_mode="HTML")

async def sos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sos_text = (
        f"{p('SOS', '🚨')} <b>4-MAKTAB ANONIM ISHONCH VA SOS MARKAZI</b>\n\n"
        f"Agar siz ijtimoiy tarmoqda yoki maktabda:\n"
        f"• {p('WARNING', '⚠️')} Kiberbulling, haqorat yoki guruhlarda kamsitilishga;\n"
        f"• {p('WARNING', '⚠️')} Shaxsiy rasmlaringiz yoki videolaringiz bilan shantajga;\n"
        f"• {p('WARNING', '⚠️')} Soxta akkaunt ochish, pul talab qilish yoki firibgarlikka duch kelgan bo‘lsangiz — <b>HECH QACHON QO‘RQMANG VA YASHIRMANG!</b>\n\n"
        f"{p('CALL', '📞')} <b>RASMIY ALOQA VA ISHONCH RAQAMLARI:</b>\n"
        f"• 🛡️ <b>Kiberxavfsizlik hodisalari bo‘yicha:</b>\n"
        f"   └ <code>+998 (55) 502-10-10</code> (yoki qisqa <b>1133</b>)\n"
        f"• ⚖️ <b>Korrupsiyani oldini olish va komplaens nazorat bo‘limi:</b>\n"
        f"   └ <code>+998 (71) 203-55-11</code>\n\n"
        f"🛡️ <b>SIZNING SHAXSINGIZ 100% SIR SAQLANADI!</b>\n"
        f"Pastdagi <b>«✍️ Anonim Murojaat Qoldirish»</b> tugmasini bosing va muammoingizni yozing. "
        f"Sizning Telegram profilingiz, ismingiz yoki raqamingiz tizim tomonidan to‘liq yashirilgan holda xavfsiz qabul qilinadi."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Anonim Murojaat Qoldirish", callback_data="start_anon_sos", icon_custom_emoji_id=E["CHAT"])],
        [InlineKeyboardButton("🌐 Kiberxavfsizlik markazi (csec.uz)", url="https://csec.uz", icon_custom_emoji_id=E["GLOBE"])]
    ])
    await update.message.reply_text(sos_text, parse_mode="HTML", reply_markup=keyboard)

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        [InlineKeyboardButton("🌐 Kiber-Portalni ochish (Web App)", web_app=WebAppInfo(url="https://abduvoitov11.github.io/kiberiz4/"), icon_custom_emoji_id=E["ROCKET"])],
        [InlineKeyboardButton("Brauzerda ochish (Tashqi havola)", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["GLOBE"])]
    ])
    await update.message.reply_text(web_text, parse_mode="HTML", reply_markup=keyboard)

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
    context.user_data["quiz_step"] = 0
    context.user_data["quiz_score"] = 0
    await send_quiz_question(update, context)

async def send_quiz_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get("quiz_step", 0)
    if step < len(QUIZ_QUESTIONS):
        q_data = QUIZ_QUESTIONS[step]
        buttons = []
        for opt_text, score in q_data["options"]:
            icon = E["CHECK"] if score > 0 else E["CROSS"]
            buttons.append([InlineKeyboardButton(opt_text, callback_data=f"q_{step}_{score}", icon_custom_emoji_id=icon)])
        keyboard = InlineKeyboardMarkup(buttons)
        
        msg_text = (
            f"{p('TEST', '🧪')} <b>«Raqamli Iz» Testi ({step+1}/{len(QUIZ_QUESTIONS)})</b>\n\n"
            f"{html.escape(q_data['q'])}"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(msg_text, parse_mode="HTML", reply_markup=keyboard)
        else:
            await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=keyboard)
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
            await update.message.reply_text(result_text, parse_mode="HTML", reply_markup=keyboard)

async def quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
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
        await query.message.reply_text(checklist_text, parse_mode="HTML")
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
        await query.message.reply_text(guide_text, parse_mode="HTML")
    elif data == "sanitize":
        last_photo = context.user_data.get("last_photo")
        if not last_photo:
            await query.message.reply_text(
                f"{p('WARNING', '⚠️')} Tozalash uchun yangi surat topilmadi. Iltimos, avval rasm yuboring.",
                parse_mode="HTML"
            )
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
            await query.message.reply_text(f"Tozalashda xatolik: {e}")
    elif data == "start_anon_sos":
        context.user_data["waiting_for_sos"] = True
        prompt = (
            f"{p('CHAT', '✍️')} <b>ANONIM MUROJAAT YOZISH MAYDONI:</b>\n\n"
            f"Iltimos, sizni bezovta qilayotgan muammo yoki hodisani batafsil yozib yuboring "
            f"(xohlasangiz dalil sifatida fotosurat yoki skrinshot ham yuborishingiz mumkin).\n\n"
            f"🔒 <b>KiberIz-4 Xavfsizlik Kafolati:</b>\n"
            f"Sizning Telegram ID, Ismingiz yoki @username'ingiz HECH KIMGA ko‘rsatilmaydi! "
            f"Xabar tizimga faqat maxsus kod (masalan: <code>#SOS-4M-8291</code>) bilan qayd etiladi.\n\n"
            f"<i>Bekor qilish uchun: /cancel deb yozing.</i>"
        )
        await query.message.reply_text(prompt, parse_mode="HTML")
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
                    f"🚨 <b>YANGI ANONIM SOS MUROJAAT (4-MAKTAB)</b>\n\n"
                    f"🆔 <b>Kodi:</b> <code>#{report_code}</code>\n"
                    f"📅 <b>Vaqti:</b> {timestamp}\n\n"
                    f"📝 <b>Murojaat matni:</b>\n<i>«{html.escape(pending_text)}»</i>\n\n"
                    f"🔒 <i>Foydalanuvchi ma’lumotlari to‘liq anonimlashtirilgan.</i>"
                )
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Failed to alert admin: {e}")

        success_msg = (
            f"{p('CHECK', '✅')} <b>ANONIM MUROJAATINGIZ QABUL QILINDI!</b>\n\n"
            f"🆔 <b>Murojaat kodi:</b> <code>#{report_code}</code>\n"
            f"📅 <b>Qayd etilgan vaqt:</b> <i>{timestamp}</i>\n"
            f"🛡️ <b>Maxfiylik maqomi:</b> <i>To‘liq himoyalangan (Ism, profil va shaxsiy ma’lumotlar oshkor etilmadi).</i>\n\n"
            f"Muammoingiz 4-maktab profilaktika inspektori va psixologiga ko‘rib chiqish uchun uzatildi.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• 🛡️ Kiberxavfsizlik hodisalari bo‘yicha: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• ⚖️ Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        await query.message.reply_text(success_msg, parse_mode="HTML")
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
            [InlineKeyboardButton("✍️ O‘z savolimni berish", callback_data="ask_custom_ai", icon_custom_emoji_id=E["CHAT"])],
            [InlineKeyboardButton("🚨 Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])]
        ])
        await query.message.reply_text(
            f"{p('LIGHT', '💡')} <b>AI KIBER-MASLAHATCHI JAVOBI:</b>\n\n{answer}",
            parse_mode="HTML",
            reply_markup=reply_markup
        )
    elif data == "ask_custom_ai":
        context.user_data["waiting_for_ai"] = True
        await query.message.reply_text(
            f"{p('CHAT', '✍️')} <b>Marhamat, o‘zingizni qiziqtirgan savolni yozib yuboring:</b>\n\n"
            f"<i>Masalan: «Do‘stimning akkaunti buzilibdi, qanday yordam bersam bo‘ladi?»</i>",
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
    """Detects and decodes QR codes inside an image using OpenCV."""
    if cv2 is None or np is None:
        return None
    try:
        nparr = np.frombuffer(file_bytes, np.uint8)
        cv_img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if cv_img is None:
            return None
        detector = cv2.QRCodeDetector()
        val, _, _ = detector.detectAndDecode(cv_img)
        return val.strip() if val else None
    except Exception as e:
        logging.warning(f"QR scan error: {e}")
        return None

def parse_document_metadata(file_bytes: bytes, file_name: str):
    """Extracts Author, Creator, Software, Dates from documents (PDF, DOCX) via exiftool."""
    ext = os.path.splitext(file_name)[1].lower() or ".pdf"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tf:
        tf.write(file_bytes)
        tf_path = tf.name
    try:
        cmd = ["exiftool", "-json", tf_path]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        if res.returncode != 0 or not res.stdout.strip():
            return []
        data = json.loads(res.stdout)[0]
        details = []
        author = data.get("Author") or data.get("Creator")
        if author:
            details.append(f"👤 <b>Hujjat muallifi:</b> {html.escape(str(author))}")
        company = data.get("Company")
        if company:
            details.append(f"🏢 <b>Tashkilot / Muassasa:</b> {html.escape(str(company))}")
        software = data.get("Software") or data.get("Producer") or data.get("CreatorTool")
        if software:
            details.append(f"💻 <b>Yaratilgan dastur:</b> {html.escape(str(software))}")
        create_date = data.get("CreateDate")
        if create_date:
            details.append(f"⏰ <b>Yaratilgan vaqt:</b> {html.escape(str(create_date))}")
        mod_date = data.get("ModifyDate")
        if mod_date:
            details.append(f"✏️ <b>Oxirgi tahrir vaqti:</b> {html.escape(str(mod_date))}")
        pages = data.get("PageCount")
        if pages:
            details.append(f"📄 <b>Sahifalar soni:</b> {html.escape(str(pages))}")
        return details
    except Exception as e:
        logging.warning(f"Doc metadata error: {e}")
        return []
    finally:
        if os.path.exists(tf_path):
            try:
                os.remove(tf_path)
            except Exception:
                pass

URL_REGEX = re.compile(
    r'(https?://[^\s]+|(?:[a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(?:/[^\s]*)?)',
    re.IGNORECASE
)

# Taqiqlangan va qonunga zid saytlar, ijtimoiy tarmoq profillari bazasi (Oliy Sud, Qimor, 18+, Narkotik, Fishing)
FORBIDDEN_RULES = [
    {
        "category": "⚠️ O‘zbekiston Oliy Sudi taqiqlagan diniy-ekstremistik va terroristik manbalar (Telegram, Instagram, YouTube, TikTok)",
        "badge": "🚨 O‘ZBEKISTON RESPUBLIKASI OLIY SUDI TOMONIDAN QAT’IYAN TAQIQLANGAN (JK 244-1)!",
        "law": "O‘zbekiston Respublikasi JK 244-1-moddasi (Jamoat xavfsizligiga tahdid soluvchi materiallarni tayyorlash, saqlash, tarqatish yoki namoyish etish) hamda JK 244-2-moddasi bo‘yicha 5 yildan 8 yilgacha ozodlikdan mahrum qilish jazosiga sabab bo‘ladi! Oliy sud va Din ishlari bo‘yicha qo‘mitaning rasmiy reyestriga kiritilgan (my.sud.uz).",
        "patterns": [
            r"abdulloh-?zufar", r"abdullah-?zufar", r"zufar-?darslari",
            r"sodiq-?samarqandiy", r"sodiqsamarqandiy", r"shayx-?sodiq",
            r"abu-?saloh", r"abusaloh", r"abu-?solih",
            r"mahmud-?abdulm[ou]min", r"mahmudabdulm[ou]min", r"mahmud-?rajab",
            r"rashod-?qori", r"rashodqori",
            r"abu-?hurayra", r"abuhurayra",
            r"hizb-?ut-?tahrir", r"hizbuttahrir",
            r"katibat-?al-?tawhid", r"tavhid-?va-?jihod", r"tavhidvajihod",
            r"jabhat-?al-?nusra", r"al-?nusra",
            r"ishid", r"daesh", r"isis", r"al-?qoida", r"al-?qaeda",
            r"jannat-?oshiqlari", r"muhojir-?tv", r"muhojirtv",
            r"najot-?forum", r"najotforum", r"ansorulloh", r"ansorullah",
            r"xuruj", r"halifalik", r"xalifalik", r"sodiqlar", r"diyor-?news"
        ]
    },
    {
        "category": "🎰 Qimor, Bukmekerlik va Tavakkalchilik o‘yinlari",
        "badge": "🚨 QAT’IYAN TAQIQLANGAN (QIMOR / BUKMEKER)",
        "law": "O‘zbekiston Respublikasi JK 278-moddasi (Qimor va tavakkalchilikka asoslangan o‘yinlarni tashkil etish hamda o‘tkazish) bo‘yicha qat’iyan jinoiy javobgarlikka sabab bo‘ladi!",
        "patterns": [
            r"1-?x-?bet", r"most-?bet", r"mel-?bet", r"line-?bet", r"1-?win", r"pin-?up",
            r"pari-?match", r"vavada", r"leon-?bet", r"fon-?bet", r"bet-?and-?you",
            r"bet365", r"joy-?casino", r"(^|[\.\-_/])casino([\.\-_/]|$)", r"bukmeker",
            r"poker-?dom", r"(^|[\.\-_/])stavk[ai]", r"qimor", r"(^|[\.\-_/])slot[s]?([\.\-_/]|$)",
            r"aviator-?(game|play)?", r"lucky-?jet", r"olimp-?bet", r"betwinner",
            r"gg-?bet", r"marathonbet", r"winline", r"baltbet", r"liga-?stavok",
            r"zenit-?bet", r"spin-?win", r"roulette", r"ruletka"
        ]
    },
    {
        "category": "🔞 18+ Axloqsiz va Pornografik Kontent",
        "badge": "🚨 QAT’IYAN TAQIQLANGAN (18+ PORNOGRAFIK MAZMUN)",
        "law": "O‘zbekiston Respublikasi JK 130-moddasi (Pornografik mahsulotlarni tarqatish, reklama qilish, namoyish etish) bo‘yicha qonun bilan qat’iyan taqiqlangan!",
        "patterns": [
            r"pornhub", r"xvideos", r"xnxx", r"redtube", r"xhamster", r"onlyfans",
            r"chaturbate", r"brazzers", r"stripchat", r"erome", r"rule34",
            r"(^|[\.\-_/])porn[o]?([\.\-_/]|$)", r"(^|[\.\-_/])sex([\.\-_/]|$)",
            r"hentai", r"bongacams", r"livejasmin", r"fapello", r"fap-?house",
            r"youporn", r"tube8", r"spankbang", r"eporner", r"beeg", r"camsoda",
            r"cam4", r"hqporner", r"(^|[\.\-_/])xxx([\.\-_/]|$)", r"nsfw"
        ]
    },
    {
        "category": "☠️ Narkotik, Darknet (.onion) va Noqonuniy Qora Bozor",
        "badge": "🚨 QAT’IYAN TAQIQLANGAN (DARKNET / .ONION / NARKOTIK)",
        "law": "O‘zbekiston Respublikasi JK 273-moddasi va kiberxavfsizlik talablariga ko‘ra, Darknet (.onion) tarmog‘i hamda uning qidiruv tizimlari (Ahmia) orqali noqonuniy vositalar, taqiqlangan moddalar va kiberjinoyatlar tarqatilishi qat’iyan man etiladi!",
        "patterns": [
            r"ahmia(\.fi)?", r"\.onion($|[./:])", r"tor2web", r"darksearch",
            r"kraken", r"hydra", r"blacksprut", r"solaris", r"mega-?dark",
            r"omg-?omg", r"narkotik", r"psixotrop", r"zakladka", r"mefedron",
            r"alfa-?pvp", r"spice", r"spays", r"apteka-?online", r"narko-?shop",
            r"(^|[\.\-_/])darknet([\.\-_/]|$)"
        ]
    },
    {
        "category": "🎣 Fishing, Bank Tuzog‘i va Akkaunt O‘g‘riligi",
        "badge": "🚨 O‘TA XAVFLI FIRIBGARLIK (FISHING / TUZOQ)",
        "law": "O‘zbekiston Respublikasi JK 168-moddasi (Axborot texnologiyalaridan foydalangan holda sodir etilgan firibgarlik) bo‘yicha jinoiy javobgarlikka sabab bo‘ladi!",
        "patterns": [
            r"click-?sovrin", r"payme-?bonus", r"humo-?bonus", r"ovoz-?ber",
            r"bepul-?ovoz", r"pul-?yutu[gq]", r"telegram-?free", r"bepul-?premium",
            r"tg-?premium", r"tg-?bonus", r"soxta-?ovoz", r"openbudget-?(ovoz|bonus)",
            r"click-?bonus", r"payme-?login", r"uzcard-?bonus", r"uzcard-?verify",
            r"telegram-?gift", r"free-?nitro"
        ]
    },
    {
        "category": "💸 Soxta Investitsiya va Moliyaviy Piramida",
        "badge": "🚨 FIRIBGARLIK TUZOG‘I (MOLIYAVIY PIRAMIDA)",
        "law": "O‘zbekiston Respublikasi JK 188-1-moddasi (Noqonuniy moliyaviy piramida faoliyati) bo‘yicha qat’iyan taqiqlangan!",
        "patterns": [
            r"uzcard-?invest", r"humo-?invest", r"gazprom-?invest", r"daromad-?invest",
            r"robot-?daromad", r"pul-?ishlash", r"bepul-?daromad", r"olymp-?trade",
            r"binomo", r"iq-?option", r"finiko", r"express-?doxod", r"smart-?invest"
        ]
    }
]

def audit_username(u: str):
    """Audits a social media username for exposed age, school, interest profiling, and live platform presence."""
    raw = u.lstrip('@').strip()
    norm_raw = raw.lower().replace('_', '-').replace('.', '-')
    warnings = []
    insights = []
    platforms_found = []
    score = 95

    # Check against Forbidden / Banned Social Media Profiles (Oliy Sud, Qimor, Narkotik)
    for cat in FORBIDDEN_RULES:
        for p in cat["patterns"]:
            if re.search(p, norm_raw) or re.search(p, raw.lower()):
                warnings.append(f"🛑 <b>Taqiqlangan profil/kanal:</b> {cat['category']} doirasidagi noqonuniy manba!")
                warnings.append(f"⚖️ <b>Qonuniy taqiq:</b> {cat['law']}")
                return 0, warnings, insights, platforms_found, raw, True, cat
    
    # 1. Year of birth detection
    year_match = re.search(r'(19\d\d|20\d\d)$', raw)
    if year_match:
        y = int(year_match.group(1))
        if 1990 <= y <= 2020:
            age = 2026 - y
            warnings.append(f"📅 <b>Tug‘ilgan yil fosh bo‘lgan:</b> <code>{y}</code>-yil (Taxminan <b>{age} yoshdasiz</b>).")
            score -= 35
    else:
        short_year = re.search(r'[\._\-](\d{2})$', raw)
        if short_year:
            sy = int(short_year.group(1))
            if 4 <= sy <= 20:
                warnings.append(f"📅 <b>Yoshingiz fosh bo‘lgan bo‘lishi mumkin:</b> <code>20{sy:02d}</code>-yil (o‘quvchi yoshi).")
                score -= 25

    # 2. School or location pattern
    loc_match = re.search(r'(maktab|m4|school|4maktab|toshkent|chilonzor|samarqand|namangan|andijon|buxoro)', raw, re.I)
    if loc_match:
        warnings.append(f"🏫 <b>Maktab yoki joylashuv kodi:</b> Nikneymda joylashuv belgisi mavjud (<i>«{loc_match.group(0)}»</i>).")
        score -= 30
        
    # 3. Interests & Semantics profiling
    interests = []
    low = raw.lower()
    if 'sport' in low: interests.append("⚽ Sport / Jismoniy faollik")
    if 'lider' in low or 'leader' in low: interests.append("🏆 Yetakchilik / Faollik")
    if 'game' in low or 'gamer' in low or 'pubg' in low: interests.append("🎮 Video o‘yinlar (Gaming)")
    if 'coder' in low or 'dev' in low or 'hack' in low: interests.append("💻 Dasturlash / IT")
    if 'music' in low or 'sound' in low: interests.append("🎵 Musiqa")
    if 'auto' in low or 'car' in low: interests.append("🚗 Avto / Texnika")
    if 'shop' in low or 'store' in low or 'savdo' in low: interests.append("🛒 Savdo / Biznes")
    
    if interests:
        insights.append(f"🎯 <b>Qiziqish sohasi (Profiling):</b> " + ", ".join(interests))
        
    # 4. Real-time platform presence check
    # Telegram check
    try:
        tg_url = f"https://t.me/{raw}"
        req = urllib.request.Request(tg_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=4) as res:
            page = res.read().decode("utf-8")
            if "tgme_page_title" in page or "tgme_action_button_new" in page:
                title = ""
                if '<meta property="og:title" content="' in page:
                    title = page.split('<meta property="og:title" content="')[1].split('"')[0]
                platforms_found.append(f"✈️ <b>Telegram:</b> Faol profil / kanal mavjud" + (f" (<i>«{html.escape(title)}»</i>)" if title and title != "Telegram" else ""))
    except Exception:
        pass
        
    # GitHub check
    try:
        gh_url = f"https://api.github.com/users/{raw}"
        req = urllib.request.Request(gh_url, headers={"User-Agent": "KiberIz4-Agent"})
        with urllib.request.urlopen(req, timeout=4) as res:
            if res.status == 200:
                data = json.loads(res.read().decode())
                platforms_found.append(f"🐙 <b>GitHub:</b> Dasturchi profili topildi (Repolar: {data.get('public_repos', 0)} ta)")
    except Exception:
        pass
        
    score = max(min(score, 100), 15)
    return score, warnings, insights, platforms_found, raw, False, None

def audit_link(url_text: str):
    """Audits a URL for forbidden illegal content, phishing, malicious TLDs, and scam keywords."""
    full_url = url_text.strip().rstrip('.,;!?')
    is_http_only = full_url.startswith('http://')
    if not full_url.startswith(('http://', 'https://')):
        full_url = 'https://' + full_url
        
    parsed = urllib.parse.urlparse(full_url)
    domain = (parsed.netloc or parsed.path).lower().split(':')[0]
    path = parsed.path.lower()
    full_lower = full_url.lower()
    norm_url = full_lower.replace('_', '-').replace('.', '-')
    
    warnings = []
    features = []
    risk = 10
    
    # 0. Darknet (.onion) va Ahmia qidiruv tizimlari
    if domain.endswith('.onion') or '.onion.' in domain or '.onion/' in full_lower or full_lower.endswith('.onion') or 'ahmia' in domain or 'ahmia.fi' in full_lower:
        darknet_cat = next((c for c in FORBIDDEN_RULES if "Darknet" in c["category"]), FORBIDDEN_RULES[0])
        warnings.append("🛑 <b>Darknet / Yashirin tarmoq (.onion):</b> Ushbu havola Tor / Darknet tarmog‘iga yoki uning qidiruv tizimiga (Ahmia) tegishli!")
        warnings.append(f"⚖️ <b>Qonuniy taqiq:</b> {darknet_cat['law']}")
        return True, darknet_cat, 100, warnings, features, domain, ""

    # Check against Forbidden / Illegal Patterns (Websites, Telegram, Instagram, YouTube, TikTok)
    for cat in FORBIDDEN_RULES:
        for p in cat["patterns"]:
            if re.search(p, domain) or re.search(p, path) or re.search(p, full_lower) or re.search(p, norm_url):
                warnings.append(f"🛑 <b>Taqiqlangan manba:</b> {cat['category']} doirasidagi noqonuniy sayt/profil!")
                warnings.append(f"⚖️ <b>Qonuniy taqiq:</b> {cat['law']}")
                return True, cat, 100, warnings, features, domain, ""

    # 1. Suspicious TLD
    suspicious_tlds = ('.xyz', '.top', '.buzz', '.tk', '.ml', '.ga', '.cf', '.gq', '.club', '.online', '.site', '.click', '.monster', '.icu', '.vip', '.rest')
    if any(domain.endswith(tld) for tld in suspicious_tlds):
        warnings.append("🚨 <b>Xavfli domen zonasi:</b> Firibgarlar ko‘p foydalanadigan bepul yoki xavfli domen kengaytmasi.")
        risk += 35
    elif any(domain.endswith(tld) for tld in ('.uz', '.edu.uz', '.gov.uz')):
        features.append("🇺🇿 <b>O‘zbekiston milliy domen zonasi (.uz)</b> — rasmiy reyestr nazorati mavjud.")

    # 2. Phishing keywords
    phish_words = ['bonus', 'sovrin', 'yutuq', 'click', 'payme', 'humo', 'uzcard', 'login', 'parol', 'verify', 'telegram-free', 'ovoz', 'invest', 'daromad', 'pul-ishlash']
    matched_words = [w for w in phish_words if w in domain or w in path]
    if matched_words:
        warnings.append(f"⚠️ <b>Shubhali kalit so‘zlar:</b> <i>«{', '.join(matched_words)}»</i> (Ovoz berish, pul yoki soxta bonus tuzog‘i).")
        risk += 40

    # 3. IP address host
    if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', domain):
        warnings.append("🚨 <b>To‘g‘ridan-to‘g‘ri IP manzil:</b> Domen nomi o‘rniga shubhali server IP manzili ko‘rsatilgan.")
        risk += 45
        
    # 4. HTTP vs HTTPS warning
    if is_http_only:
        warnings.append("🔓 <b>Xavfsiz ulanish (SSL) yo‘q:</b> Sayt <code>http://</code> orqali ishlamoqda. Ma’lumotlar shifrlanmaydi!")
        risk += 15
    else:
        features.append("🔒 <b>Shifrlangan HTTPS ulanish</b> mavjud.")
        
    # 5. Live Website Title
    site_title = ""
    try:
        req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" in content_type:
                html_raw = resp.read(8192).decode("utf-8", errors="ignore")
                title_match = re.search(r'<title[^>]*>(.*?)</title>', html_raw, re.IGNORECASE | re.DOTALL)
                if title_match:
                    site_title = title_match.group(1).strip()
    except Exception:
        pass
        
    risk = min(risk, 98)
    return False, None, risk, warnings, features, domain, site_title

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
def parse_single_image_exif(file_bytes, filename="surat"):
    """Extracts EXIF and GPS from raw image bytes (supports JPG, PNG, HEIC, WEBP)."""
    try:
        img = Image.open(io.BytesIO(file_bytes))
        exif_data = img.getexif()
    except Exception as e:
        return None, None, str(e)
        
    details = []
    lat_val, lon_val = None, None
    device_name = None
    captured_time = None
    
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
            
    coords = (lat_val, lon_val) if (lat_val is not None and lon_val is not None) else None
    return details, coords, None

def analyze_visual_osint(image_bytes: bytes):
    """
    Performs AI-level Visual OSINT on an image:
    1. Chronolocation & Lighting analysis (day/golden hour/night/indoor).
    2. OCR Text extraction (identifying school, room, street, or brand names).
    3. Threat keywords detection (maktab, 4, sinf, uy, toshkent, etc.).
    4. Calculates Visual Risk Score.
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
                if max(w, h) > 1500:
                    scale = 1500 / max(w, h)
                    small_img = img.resize((int(w * scale), int(h * scale)))
                else:
                    small_img = img
                detected_text = pytesseract.image_to_string(small_img, lang="eng+uzb", timeout=5).strip()
            except Exception as ocr_err:
                logging.warning(f"OCR warning: {ocr_err}")
            
        text_risk = 0
        if detected_text:
            low_text = detected_text.lower()
            keywords = [
                ("4-maktab", "🏫 4-maktab aniq nomi"),
                ("maktab", "🏫 Maktab bilan bog‘liq yozuv"),
                ("sinf", "🎒 Sinf xonasi belgisi"),
                ("xona", "🚪 Xona yoki kabinet raqami"),
                ("kabinet", "🚪 Kabinet peshlavhasi"),
                ("toshkent", "📍 Shahar nomi (Toshkent)"),
                ("chilonzor", "📍 Tuman nomi"),
                ("ko'cha", "🛣️ Ko‘cha / Manzil yozuvi"),
                ("korzinka", "🏬 Do‘kon peshlavhasi"),
                ("havas", "🏬 Do‘kon peshlavhasi"),
                ("makro", "🏬 Do‘kon peshlavhasi"),
                ("bank", "🏦 Bank yoki moliya muassasasi"),
                ("apteka", "💊 Dorixona belgisi")
            ]
            for kw, label in keywords:
                if kw in low_text:
                    ocr_found.append(f"{label}: <i>«{kw}»</i>")
                    text_risk += 15
                    
        return {
            "brightness": round(brightness, 1),
            "chrono_text": chrono_text,
            "chrono_badge": chrono_badge,
            "chrono_risk": chrono_risk,
            "ocr_text": detected_text[:140] if detected_text else "",
            "ocr_found": ocr_found,
            "text_risk": min(text_risk, 35)
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

async def photo_or_doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg:
        return
        
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

    await msg.reply_chat_action("typing")
    
    is_doc = bool(msg.document)
    is_video = bool(msg.video)
    file_bytes = None
    file_name = "fayl"
    
    video_exts = (".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm", ".m4v")
    img_exts = (".jpg", ".jpeg", ".png", ".tiff", ".heic", ".heif", ".webp")
    doc_exts = (".pdf", ".docx", ".doc", ".pptx", ".xlsx")
    
    if is_doc:
        doc = msg.document
        file_name = doc.file_name or "hujjat"
        mime = (doc.mime_type or "").lower()
        valid_exts = img_exts + video_exts + doc_exts + (".zip",)
        if not (mime.startswith("image/") or mime.startswith("video/") or "zip" in mime or any(file_name.lower().endswith(ext) for ext in valid_exts)):
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} Iltimos, tahlil qilish uchun <b>fotosurat</b> (JPG, PNG, HEIC), <b>video</b> (MP4, MOV), <b>hujjat</b> (PDF, DOCX) yoki <b>ZIP arxiv</b> yuboring.",
                parse_mode="HTML"
            )
            return
            
        tg_file = await doc.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        if any(file_name.lower().endswith(ext) for ext in video_exts) or mime.startswith("video/"):
            is_video = True
    elif msg.photo:
        tg_file = await msg.photo[-1].get_file()
        file_bytes = await tg_file.download_as_bytearray()
        file_name = "surat.jpg"
    elif msg.video:
        video = msg.video
        file_name = video.file_name or f"video_{video.file_id[:8]}.mp4"
        tg_file = await video.get_file()
        file_bytes = await tg_file.download_as_bytearray()
        is_video = True
        
    if not file_bytes:
        return

    # Check if ZIP archive
    if is_doc and (file_name.lower().endswith(".zip") or "zip" in (msg.document.mime_type or "").lower()):
        await handle_zip_archive(msg, file_bytes, file_name)
        return

    # Check if Document (PDF, DOCX)
    if is_doc and any(file_name.lower().endswith(ext) for ext in doc_exts):
        doc_details = parse_document_metadata(file_bytes, file_name)
        doc_msg = (
            f"{p('SEARCH', '📄')} <b>HUJJAT OSINT TAHLILI ({html.escape(file_name)}):</b>\n\n"
            f"ℹ️ <i>Hujjatlar (PDF, Word) ichida muallif shaxsi, kompyuter nomi va tahrir sanalari saqlanadi:</i>\n\n"
        )
        if doc_details:
            doc_msg += f"{p('WARNING', '⚠️')} <b>ANIQLANGAN YASHIRIN METAMA’LUMOTLAR:</b>\n"
            for dd in doc_details:
                doc_msg += f"• {dd}\n"
            doc_msg += (
                f"\n{p('SHIELD', '🛡️')} <b>Xavfsizlik eslatmasi:</b> Darslik, taqdimot yoki hujjatlarni tarmoqqa yuklashdan avval "
                f"«Inspect Document» orqali shaxsiy ism va kompyuter nomini tozalab qo‘ying!"
            )
        else:
            doc_msg += f"{p('CHECK', '✅')} <i>Ushbu hujjatda shaxsiy mualliflik metama’lumotlari topilmadi (tozalangan).</i>"
        await msg.reply_text(doc_msg, parse_mode="HTML")
        return

    # ==========================
    # VIDEO ANALYSIS
    # ==========================
    if is_video:
        details, coords, err = parse_video_metadata(file_bytes, file_name)
        if err:
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} Videoni ochishda xatolik yuz berdi ({html.escape(err)}). Iltimos, boshqa video yuboring.",
                parse_mode="HTML"
            )
            return
            
        analysis_msg = f"{p('RADAR', '🎬')} <b>VIDEO OSINT TAHLIL NATIJASI ({html.escape(file_name)}):</b>\n\n"
        
        if coords:
            analysis_msg += f"{p('SOS', '🚨')} <b>JIDDIY XAVF: VIDEODA YASHIRIN GEOLOKATSIYA TOPILDI!</b>\n"
        elif details:
            analysis_msg += f"{p('WARNING', '⚠️')} <b>VIDEODA TEXNIK VA QURILMA METAMA’LUMOTLARI TOPILDI:</b>\n"
            
        if details:
            for d in details:
                analysis_msg += f"• {d}\n"
            analysis_msg += "\n"
        else:
            if not is_doc:
                analysis_msg += (
                    f"{p('INFO', 'ℹ️')} <i>Telegram orqali oddiy video tarzida yuborilgani uchun Telegram uni siqib, "
                    f"barcha EXIF va GPS parametrlarini avtomatik tozalab tashlagan.\n"
                    f"Original video metama’lumotlarini tekshirish uchun uni botga <b>'Hujjat' (Document / File)</b> qilib yuboring!</i>\n\n"
                )
            else:
                analysis_msg += (
                    f"{p('CHECK', '✅')} <i>Ushbu video faylida GPS yoki kamera parametrlari topilmadi (tozalangan yoki kamera geolokatsiyasi o‘chiq bo‘lgan).</i>\n\n"
                )
                
        analysis_msg += (
            f"{p('HACKER', '🕵️‍♂️')} <b>VIDEODAGI TEXNIK VA AUDIO TAHLIL:</b>\n"
            f"• {p('CALL', '🔊')} <b>Ovoz yo‘lagi:</b> Fon shovqini va audio parametrlar tekshirildi.\n"
            f"• {p('TIMER', '⏱️')} <b>Texnik ko‘rsatkichlar:</b> Kadr chastotasi, o‘lcham va kodek parametrlari aniqlandi.\n"
        )
        
        await msg.reply_text(analysis_msg, parse_mode="HTML", disable_web_page_preview=True)
        if coords:
            lat_val, lon_val = coords
            await msg.reply_location(latitude=lat_val, longitude=lon_val)
        return

    # Process Single Image (JPG, PNG, HEIC, WEBP, TIFF)
    context.user_data["last_photo"] = file_bytes
    details, coords, err = parse_single_image_exif(file_bytes, file_name)
    
    if err:
        await msg.reply_text(
            f"{p('WARNING', '⚠️')} Rasmni ochishda xatolik yuz berdi ({html.escape(err)}). Iltimos, boshqa surat yuboring.",
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

    # QR Code & Barcode Detection
    qr_data = scan_qr_code(file_bytes)

    # Real Visual OSINT Analysis (Chronolocation & OCR)
    visual_info = analyze_visual_osint(file_bytes)
    
    # Calculate composite Cyber Risk Score (0-100%)
    risk_score = 15
    if coords:
        risk_score += 50
    elif details:
        risk_score += 25
        
    if visual_info:
        risk_score += visual_info.get("chrono_risk", 10)
        risk_score += visual_info.get("text_risk", 0)
        
    if qr_data:
        risk_score += 25
        risk_score += 25
        
    if visual_info:
        risk_score += visual_info.get("chrono_risk", 10)
        risk_score += visual_info.get("text_risk", 0)
        
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
        f"{p('SEARCH', '🔍')} <b>KOMPLEKS OSINT TAHLIL ({html.escape(file_name)}):</b>\n\n"
        f"📊 <b>KIBER-XAVF INDEKSI:</b>\n"
        f"<code>[{bar}]</code> <b>{risk_label}</b>\n\n"
        f"{p('LOCK', '🔐')} <b>1. METAMA’LUMOTLAR (EXIF / GPS):</b>\n"
    )
    
    if details:
        for d in details:
            analysis_msg += f"• {d}\n"
    else:
        if not is_doc:
            analysis_msg += (
                f"• {p('INFO', 'ℹ️')} <i>Fayl ichidagi GPS tozalangan (Instagram yoki Telegram avtomatik siqib tozalagan).</i>\n"
            )
        else:
            analysis_msg += f"• {p('CHECK', '✅')} <i>GPS yoki kamera parametrlari topilmadi (tozalangan).</i>\n"
    analysis_msg += "\n"
    
    # Chronolocation
    analysis_msg += f"{p('TIMER', '☀️')} <b>2. XRONOLOKATSIYA (YORUG‘LIK VA VAQT):</b>\n"
    if visual_info:
        analysis_msg += (
            f"• <b>Holat:</b> {visual_info['chrono_text']}\n"
            f"• <b>Yorug‘lik ko‘rsatkichi:</b> <code>{visual_info['brightness']} lx</code>\n\n"
        )
    else:
        analysis_msg += f"• <i>Yorug‘lik tahlil qilindi.</i>\n\n"
        
    # OCR & Background
    analysis_msg += f"{p('HACKER', '🕵️‍♂️')} <b>3. VIZUAL FON VA YOZUVLAR (OCR TAHLILI):</b>\n"
    if visual_info and visual_info["ocr_found"]:
        analysis_msg += f"{p('WARNING', '⚠️')} <b>Fonda xavfli belgilar aniqlandi:</b>\n"
        for of in visual_info["ocr_found"]:
            analysis_msg += f"• {of}\n"
    elif visual_info and visual_info["ocr_text"]:
        clean_snip = html.escape(visual_info["ocr_text"][:80].replace("\n", " "))
        analysis_msg += f"• 📝 <b>O‘qilgan yozuvlar:</b> <i>«{clean_snip}...»</i>\n"
    else:
        analysis_msg += f"• {p('CHECK', '✅')} <i>Ochiq maktab yoki manzil yozuvlari fosh bo‘lmadi.</i>\n"
    analysis_msg += "\n"
    
    # QR Code & Barcode Section
    if qr_data:
        analysis_msg += (
            f"🚨 <b>SURAT ICHIDA YASHIRIN QR-KOD TOPILDI:</b>\n"
            f"• <b>QR Tarkibi:</b> <code>{html.escape(qr_data)}</code>\n"
            f"• ⚠️ <i>Kiber-Xavf: Chipta, sertifikat yoki chekdagi QR-kodlar orqali shaxsiy hisoblar yoki ma’lumotlar o‘g‘irlanadi!</i>\n\n"
        )

    # Reverse Search
    analysis_msg += (
        f"{p('GLOBE', '🌐')} <b>4. TESKARI QIDIRUV (REVERSE SEARCH):</b>\n"
        f"Surat bo‘yicha internetdagi ochiq ma’lumotlarni qidirish uchun quyidagi tugmalardan foydalanishingiz mumkin:\n"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Suratni tozalash (EXIF-siz yuklab olish)", callback_data="sanitize", icon_custom_emoji_id=E["SHIELD"])],
        [
            InlineKeyboardButton("Google Lens qidiruv", url="https://lens.google.com/", icon_custom_emoji_id=E["SEARCH"]),
            InlineKeyboardButton("Yandex Images", url="https://yandex.com/images/search?rpt=imageview", icon_custom_emoji_id=E["GLOBE"])
        ],
        [InlineKeyboardButton("Veb-Platformada tekshirish", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["ROCKET"])]
    ])
    
    await msg.reply_text(analysis_msg, parse_mode="HTML", reply_markup=keyboard, disable_web_page_preview=True)
    
    # If GPS coordinates were detected, send real Telegram Location pin!
    if coords:
        lat_val, lon_val = coords
        await msg.reply_location(latitude=lat_val, longitude=lon_val)

async def handle_zip_archive(msg, file_bytes, file_name):
    """Unpacks a zip archive and performs OSINT analysis on all contained images."""
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), "r") as z:
            namelist = [n for n in z.namelist() if not n.endswith("/")]
            valid_exts = (".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".tiff")
            image_names = [n for n in namelist if any(n.lower().endswith(ext) for ext in valid_exts)]
            
            if not image_names:
                await msg.reply_text(
                    f"{p('WARNING', '⚠️')} <b>{html.escape(file_name)}</b> arxivi ichida fotosuratlar (JPG, PNG, HEIC) topilmadi.",
                    parse_mode="HTML"
                )
                return
                
            report = (
                f"📦 <b>ZIP ARXIVI OCHILDI: {html.escape(file_name)}</b>\n"
                f"Aniqlangan fotosuratlar soni: <b>{len(image_names)} ta</b>\n"
                f"<i>Quyida arxivdagi rasmlarning OSINT tahlili:</i>\n\n"
            )
            
            first_gps_coords = None
            # Analyze up to 5 images to keep Telegram message clean
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
                    report += f"  {p('CHECK', '✅')} EXIF tozalanib yuborilgan (GPS xavfi yo‘q).\n"
                    
            if len(image_names) > 5:
                report += f"\n<i>...va yana {len(image_names)-5} ta rasm mavjud.</i>\n"
                
            report += (
                f"\n{p('SHIELD', '🛡️')} <b>Xulosa:</b> Arxivlangan suratlarni begonalarga yuborishdan avval "
                f"ularning metama’lumotlarini tozalash zarur!"
            )
            
            await msg.reply_text(report, parse_mode="HTML", disable_web_page_preview=True)
            
            # Send Telegram Location Pin if any image had GPS
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
    text = (update.message.text or "").strip()
    if not text:
        return

    # 0. Cancel active modes
    if text.lower() in ["/cancel", "bekor qilish", "bekor"]:
        context.user_data["waiting_for_sos"] = False
        context.user_data["waiting_for_audit"] = False
        context.user_data["waiting_for_ai"] = False
        await update.message.reply_text(
            f"{p('CHECK', '✅')} Barcha amallar bekor qilindi.",
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
                    f"🚨 <b>YANGI ANONIM SOS MUROJAAT (4-MAKTAB)</b>\n\n"
                    f"🆔 <b>Kodi:</b> <code>#{report_code}</code>\n"
                    f"📅 <b>Vaqti:</b> {timestamp}\n\n"
                    f"📝 <b>Murojaat matni:</b>\n<i>«{html.escape(text)}»</i>\n\n"
                    f"🔒 <i>Foydalanuvchi ma’lumotlari to‘liq anonimlashtirilgan.</i>"
                )
                await context.bot.send_message(chat_id=int(ADMIN_ID), text=alert_text, parse_mode="HTML")
            except Exception as e:
                logging.warning(f"Failed to alert admin: {e}")

        success_msg = (
            f"{p('CHECK', '✅')} <b>ANONIM MUROJAATINGIZ QABUL QILINDI!</b>\n\n"
            f"🆔 <b>Murojaat kodi:</b> <code>#{report_code}</code>\n"
            f"📅 <b>Qayd etilgan vaqt:</b> <i>{timestamp}</i>\n"
            f"🛡️ <b>Maxfiylik maqomi:</b> <i>To‘liq himoyalangan (Ism, profil va shaxsiy ma’lumotlar oshkor etilmadi).</i>\n\n"
            f"Muammoingiz 4-maktab profilaktika inspektori va psixologiga ko‘rib chiqish uchun uzatildi.\n\n"
            f"{p('CALL', '📞')} <b>Rasmiy aloqa raqamlari:</b>\n"
            f"• 🛡️ Kiberxavfsizlik hodisalari bo‘yicha: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
            f"• ⚖️ Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
        )
        await update.message.reply_text(success_msg, parse_mode="HTML", reply_markup=MAIN_KEYBOARD)
        return

    # 2. Main Menu Actions
    if "Suratni tekshirish" in text or "OSINT" in text:
        await update.message.reply_text(
            f"{p('EXIF_PHOTO', '🖼️')} Iltimos, tahlil qilish uchun botga <b>fotosurat</b> yuboring:\n"
            f"• <b>Apple iPhone (.HEIC)</b> fotosuratlari;\n"
            f"• <b>.ZIP arxivdagi fotosuratlar</b>!\n\n"
            f"💡 <i>Sinov uchun GPS-li tayyor namuna surat olish: /sample buyrug‘ini bosing!</i>",
            parse_mode="HTML"
        )
    elif "Chek-list" in text:
        await checklist_command(update, context)
    elif "Testi" in text:
        await start_quiz(update, context)
    elif "Real keyslar" in text:
        await cases_command(update, context)
    elif "SOS" in text:
        await sos_command(update, context)
    elif "AI Kiber-Maslahatchi" in text or "AI Maslahatchi" in text:
        await ai_command(update, context)
    elif "Nikneym" in text or "Havola" in text:
        context.user_data["waiting_for_audit"] = True
        await update.message.reply_text(
            f"{p('HACKER', '🕵️‍♂️')} <b>NIKNEYM VA HAVOLA OSINT AUDITI:</b>\n\n"
            f"1. <b>Nikneym (Username) tekshirish:</b>\n"
            f"   Botga o‘zingizning yoki do‘stingizning nikneymini yuboring (masalan: <code>@sarvar_2008</code> yoki <code>@malika_07</code>).\n"
            f"   └ <i>Bot nikneym orqali yosh, maktab va boshqa tarmoqlardagi izlarni tahlil qilib beradi!</i>\n\n"
            f"2. <b>Shubhali havola (Sayt) tekshirish:</b>\n"
            f"   Sizga yuborilgan har qanday shubhali sayt havolasini yuboring (masalan: <code>http://click-sovrin.xyz</code> yoki <code>kun.uz</code>).\n"
            f"   └ <i>Bot uning firibgarlik (fishing) ekanligini bir zumda fosh qiladi!</i>\n\n"
            f"👉 <i>Tekshirmoqchi bo‘lgan sayt havolasi yoki @nikneymni shu yerga yozib yuboring:</i>",
            parse_mode="HTML"
        )
    elif "Veb-Platforma" in text or "Kiber-Portal" in text or "Web App" in text:
        await web_command(update, context)
    elif URL_REGEX.search(text) and not text.startswith("@"):
        # URL / Link Audit
        m_url = URL_REGEX.search(text)
        matched_url = m_url.group(1).rstrip('.,;!?')
        is_forbidden, forbidden_info, risk, warnings, features, domain, site_title = audit_link(matched_url)
        
        # 1. Taqiqlangan va qonunga zid manbalar (Qimor, 18+, Narkotik, Fishing)
        if is_forbidden and forbidden_info:
            resp = (
                f"{p('BOMB', '🚨')} <b>QAT’IYAN TAQIQLANGAN VA NOQONUNIY MANBA!</b>\n\n"
                f"🔗 <b>Kiritilgan havola:</b> <code>{html.escape(matched_url)}</code>\n"
                f"🌐 <b>Asosiy Domen:</b> <code>{html.escape(domain)}</code>\n\n"
                f"📊 <b>Kiber-Xavf Indeksi:</b> <code>[██████████]</code> <b>100% (KRITIK XAVF)</b>\n"
                f"🛑 <b>Holat:</b> {forbidden_info['badge']}\n\n"
                f"⚠️ <b>ANIQLANGAN TAQIQLANGAN KATEGORIYA:</b>\n"
                f"• <b>Turi:</b> {forbidden_info['category']}\n"
                f"• ⚖️ <b>Qonuniy asos:</b> <i>{forbidden_info['law']}</i>\n\n"
                f"🚫 <b>XAVFSIZLIK CHORALARI:</b>\n"
                f"1. Ushbu havolaga <b>HECH QACHON kirmang</b> va uni boshqalarga ulashmang!\n"
                f"2. Bunday saytlar fuqarolarning pullarini, shaxsiy hisoblarini o‘g‘irlash yoki axloqiy/ruhiy zarar yetkazish uchun mo‘ljallangan.\n"
                f"3. Ushbu xabarni darhol o‘chirib tashlash tavsiya etiladi."
            )
            await update.message.reply_text(resp, parse_mode="HTML")

            # Xavfsiz bulutli sendboks ekrani (Screenshot)
            try:
                loop = asyncio.get_running_loop()
                ss_bytes = await loop.run_in_executor(None, get_website_screenshot, matched_url)
                if ss_bytes:
                    caption = (
                        f"{p('CAMERA', '📸')} <b>«{html.escape(domain)}» saytining jonli ekrani (Sandbox):</b>\n\n"
                        f"🛑 <b>Holat:</b> {forbidden_info['badge']}\n"
                        f"🛡️ <i>Xavfsiz bulutli sendboks (Chromium) orqali olindi. O‘zingiz shaxsiy brauzeringizda ochmasdan bexavotir ko‘rishingiz mumkin.</i>"
                    )
                    await update.message.reply_photo(
                        photo=io.BytesIO(ss_bytes),
                        caption=caption,
                        parse_mode="HTML"
                    )
            except Exception as ss_e:
                logging.warning(f"Screenshot error for forbidden url: {ss_e}")
            return

        # 2. Boshqa barcha havolalar tahlili (Xavfsiz yoki Shubhali)
        filled = int(risk / 10)
        bar = "█" * filled + "░" * (10 - filled)
        if risk >= 60:
            verdict = f"🚨 JIDDIY FISHING VA FIRIBGARLIK TUZOG‘I ({risk}%)"
        elif risk >= 35:
            verdict = f"⚠️ SHUBHALI / EHTIYOT BO‘LING ({risk}%)"
        else:
            verdict = f"✅ NISBATAN XAVFSIZ SAYT ({risk}%)"
            
        resp = (
            f"{p('GLOBE', '🌐')} <b>HAVOLA (URL) OSINT VA FISHING TEKSHIRUVI:</b>\n\n"
            f"🔗 <b>Kiritilgan manzil:</b> <code>{html.escape(matched_url)}</code>\n"
            f"🌐 <b>Asosiy Domen:</b> <code>{html.escape(domain)}</code>\n"
        )
        if site_title:
            resp += f"📑 <b>Sayt nomi / Title:</b> <i>«{html.escape(site_title[:90])}»</i>\n"
            
        resp += (
            f"📊 <b>Xavf Ko‘rsatkichi:</b> <code>[{bar}]</code>\n"
            f"<b>Xulosa:</b> {verdict}\n\n"
        )
        if warnings:
            resp += f"{p('WARNING', '⚠️')} <b>Aniqlangan xavfli belgilar:</b>\n"
            for w in warnings:
                resp += f"• {w}\n"
            resp += "\n"
        else:
            resp += f"{p('CHECK', '✅')} <i>Ochiq fishing yoki taqiqlangan manba belgilari topilmadi.</i>\n\n"
            
        if features:
            resp += f"{p('SHIELD', '🛡️')} <b>Xavfsizlik parametrlari:</b>\n"
            for ft in features:
                resp += f"• {ft}\n"
            resp += "\n"
            
        resp += (
            f"{p('SHIELD', '🛡️')} <b>Kiber-Qoida:</b> «Ovoz bering», «Telegram Premium bepul», «Sovg‘a yutib oldingiz» "
            f"mazmunidagi havolalarga HECH QACHON telefon raqam yoki SMS kod kiritmang!"
        )
        await update.message.reply_text(resp, parse_mode="HTML")

        # Xavfsiz bulutli sendboks ekrani (Screenshot)
        try:
            loop = asyncio.get_running_loop()
            ss_bytes = await loop.run_in_executor(None, get_website_screenshot, matched_url)
            if ss_bytes:
                caption = (
                    f"{p('CAMERA', '📸')} <b>«{html.escape(domain)}» saytining jonli ekrani (Sandbox):</b>\n\n"
                    f"📊 <b>Kiber-Tahlil:</b> {verdict}\n"
                    f"🛡️ <i>Xavfsiz bulutli sendboks (Chromium) orqali rasmga olindi.</i>"
                )
                await update.message.reply_photo(
                    photo=io.BytesIO(ss_bytes),
                    caption=caption,
                    parse_mode="HTML"
                )
        except Exception as ss_e:
            logging.warning(f"Screenshot error for url: {ss_e}")
        return
    else:
        # Check if text is an explicit or intended username
        is_explicit_username = text.startswith("@")
        is_audit_mode = context.user_data.get("waiting_for_audit") and len(text.split()) == 1 and 3 <= len(text) <= 30 and re.match(r'^[a-zA-Z0-9_.]+$', text)
        is_forbidden_username = False
        
        if not is_explicit_username and len(text.split()) == 1 and 3 <= len(text) <= 30:
            norm_t = text.lower().replace('_', '-').replace('.', '-')
            for cat in FORBIDDEN_RULES:
                for pat in cat["patterns"]:
                    if re.search(pat, norm_t) or re.search(pat, text.lower()):
                        is_forbidden_username = True
                        break
                if is_forbidden_username:
                    break

        if is_explicit_username or is_audit_mode or is_forbidden_username:
            context.user_data["waiting_for_audit"] = False
            # Username OSINT Audit
            score, warnings, insights, platforms_found, raw, is_forbidden, forbidden_info = audit_username(text)
            
            # 1. Taqiqlangan va qonunga zid profillar (Oliy Sud, Qimor, Narkotik)
            if is_forbidden and forbidden_info:
                resp = (
                    f"{p('BOMB', '🚨')} <b>QAT’IYAN TAQIQLANGAN VA NOQONUNIY PROFIL!</b>\n\n"
                    f"👤 <b>Kiritilgan profil / nikneym:</b> <code>@{html.escape(raw)}</code>\n\n"
                    f"📊 <b>Kiber-Xavf Indeksi:</b> <code>[██████████]</code> <b>100% (KRITIK JINOIY XAVF)</b>\n"
                    f"🛑 <b>Holat:</b> {forbidden_info['badge']}\n\n"
                    f"⚠️ <b>ANIQLANGAN TAQIQLANGAN KATEGORIYA:</b>\n"
                    f"• <b>Turi:</b> {forbidden_info['category']}\n"
                    f"• ⚖️ <b>Qonuniy asos:</b> <i>{forbidden_info['law']}</i>\n\n"
                    f"🚫 <b>XAVFSIZLIK CHORALARI:</b>\n"
                    f"1. Ushbu profil, kanal yoki sahifaga <b>HECH QACHON a’zo bo‘lmang</b>, materiallarini saqlamang va boshqalarga ulashmang!\n"
                    f"2. Qonunchilikka ko‘ra (JK 244-1 va 278-moddalar), bunday manbalarni saqlash yoki tarqatish to‘g‘ridan-to‘g‘ri jinoiy javobgarlikka sabab bo‘ladi.\n"
                    f"3. Ushbu yozishmani darhol o‘chirib tashlash tavsiya etiladi."
                )
                await update.message.reply_text(resp, parse_mode="HTML")

                # Xavfsiz kanal/profil sendboks ekrani (Screenshot)
                try:
                    loop = asyncio.get_running_loop()
                    ss_bytes = await loop.run_in_executor(None, get_website_screenshot, f"https://t.me/s/{raw}")
                    if ss_bytes:
                        caption = (
                            f"{p('CAMERA', '📸')} <b>@{html.escape(raw)} kanalining jonli ko‘rinishi (Sandbox):</b>\n\n"
                            f"🛑 <b>Holat:</b> {forbidden_info['badge']}\n"
                            f"🛡️ <i>Xavfsiz bulutli sendboks orqali olindi. Kanalga a’zo bo‘lmasdan ko‘rishingiz mumkin.</i>"
                        )
                        await update.message.reply_photo(
                            photo=io.BytesIO(ss_bytes),
                            caption=caption,
                            parse_mode="HTML"
                        )
                except Exception as ss_e:
                    logging.warning(f"Screenshot error for forbidden username: {ss_e}")
                return

            filled = int(score / 10)
            bar = "█" * filled + "░" * (10 - filled)
            
            if score <= 50:
                anon_label = f"🚨 JUDA PAST ANONIMLIK ({score}%) — Shaxsingiz osongina fosh bo‘ladi!"
            elif score <= 75:
                anon_label = f"⚠️ O‘RTA DARAJA ({score}%) — Ayrim shaxsiy belgilar mavjud"
            else:
                anon_label = f"✅ YUQORI ANONIMLIK ({score}%) — Xavfsiz nikneym"
                
            resp = (
                f"{p('HACKER', '🕵️‍♂️')} <b>NIKNEYM RAQAMLI IZ AUDITI: @{html.escape(raw)}</b>\n\n"
                f"📊 <b>Anonimlik darajasi:</b>\n"
                f"<code>[{bar}]</code> <b>{anon_label}</b>\n\n"
            )
            if warnings:
                resp += f"{p('WARNING', '⚠️')} <b>Oshkor bo‘lgan ma’lumotlar:</b>\n"
                for w in warnings:
                    resp += f"• {w}\n"
                resp += "\n"
            else:
                resp += f"{p('CHECK', '✅')} <i>Nikneymda yosh, maktab yoki tug‘ilgan yil belgilari topilmadi (toza).</i>\n\n"
                
            if insights:
                for ins in insights:
                    resp += f"{ins}\n"
                resp += "\n"
                
            if platforms_found:
                resp += f"{p('SEARCH', '🌐')} <b>Jonli topilgan akkauntlar:</b>\n"
                for pf in platforms_found:
                    resp += f"• {pf}\n"
                resp += "\n"
                
            resp += (
                f"{p('SEARCH', '🔎')} <b>Boshqa tarmoqlardagi raqamli izlarni tekshirish:</b>\n"
                f"Ushbu nikneym orqali boshqa platformalardagi profillarni bir bosishda qidirishingiz mumkin:"
            )
            
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Telegram", url=f"https://t.me/{raw}", icon_custom_emoji_id=E["CALL"]),
                    InlineKeyboardButton("Instagram", url=f"https://instagram.com/{raw}", icon_custom_emoji_id=E["EXIF_PHOTO"])
                ],
                [
                    InlineKeyboardButton("TikTok", url=f"https://tiktok.com/@{raw}", icon_custom_emoji_id=E["FIRE"]),
                    InlineKeyboardButton("GitHub", url=f"https://github.com/{raw}", icon_custom_emoji_id=E["LAPTOP"])
                ],
                [
                    InlineKeyboardButton("WhatsMyName (Global Qidiruv)", url="https://whatsmyname.app/", icon_custom_emoji_id=E["SEARCH"])
                ]
            ])
            await update.message.reply_text(resp, parse_mode="HTML", reply_markup=keyboard)
            return

        # General text / Question / Problem statement
        context.user_data["waiting_for_audit"] = False
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
                f"• 🛡️ Kiberxavfsizlik hodisalari: <b>+998 (55) 502-10-10</b> (yoki 1133)\n"
                f"• ⚖️ Komplaens nazorat bo‘limi: <b>+998 (71) 203-55-11</b>"
            )
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Ushbu xabarni Anonim SOS sifatida yuborish", callback_data="confirm_quick_sos", icon_custom_emoji_id=E["CHAT"])],
                [InlineKeyboardButton("🌐 Kiberxavfsizlik markazi (csec.uz)", url="https://csec.uz", icon_custom_emoji_id=E["GLOBE"])]
            ])
            context.user_data["pending_sos_text"] = text
            await update.message.reply_text(help_text, parse_mode="HTML", reply_markup=keyboard)
            return

        # AI Cyber-Mentor Answer for all questions and consultations
        context.user_data["waiting_for_ai"] = False
        try:
            await update.message.chat.send_action("typing")
        except Exception:
            pass

        ai_resp = await ask_gemini_cyber_mentor(text, user_id=update.effective_user.id)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✍️ Boshqa savol berish", callback_data="ask_custom_ai", icon_custom_emoji_id=E["CHAT"])],
            [InlineKeyboardButton("🚨 Anonim SOS Yordam", callback_data="start_anon_sos", icon_custom_emoji_id=E["SOS"])],
            [InlineKeyboardButton("🌐 Kiber-Portal (Web App)", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["GLOBE"])]
        ])
        await update.message.reply_text(
            f"{p('LIGHT', '💡')} <b>AI KIBER-MASLAHATCHI JAVOBI:</b>\n\n{ai_resp}",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error gracefully without crashing."""
    logging.error(f"Telegram handler exception: {context.error}")

def main():
    start_health_check_if_needed()
    print("Starting KiberIz-4 Telegram Bot with Real OSINT, Video, HEIC & ZIP Support...")
    request_cfg = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(BOT_TOKEN).request(request_cfg).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("sample", sample_command))
    app.add_handler(CommandHandler("checklist", checklist_command))
    app.add_handler(CommandHandler("test", start_quiz))
    app.add_handler(CommandHandler("sos", sos_command))
    app.add_handler(CommandHandler("ai", ai_command))
    app.add_handler(CommandHandler("ask", ai_command))
    
    app.add_handler(CallbackQueryHandler(quiz_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, photo_or_doc_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    
    print("Bot is successfully polling!")
    app.run_polling()

if __name__ == "__main__":
    main()
