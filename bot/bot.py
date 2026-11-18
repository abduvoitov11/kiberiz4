import os
import io
import html
import logging
import zipfile
import threading
import subprocess
import json
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image, ExifTags, ImageStat
import pytesseract
import pillow_heif

# Register HEIF/HEIC support for Apple iPhone photos
pillow_heif.register_heif_opener()

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
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

# Load BOT_TOKEN from environment variable or local gitignored .env file
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    env_file = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_file):
        env_file = os.path.join(BASE_DIR, "../.env")
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith("BOT_TOKEN="):
                    BOT_TOKEN = line.strip().split("=", 1)[1].strip("\"' ")

def resolve_path(candidates):
    for c in candidates:
        if os.path.exists(c):
            return c
    return candidates[0]

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

# Main persistent reply keyboard with Telegram Premium icon custom emojis
MAIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        [
            KeyboardButton("Suratni tekshirish (OSINT)", icon_custom_emoji_id=E["SEARCH"]),
            KeyboardButton("5 daqiqalik Chek-list", icon_custom_emoji_id=E["SHIELD"])
        ],
        [
            KeyboardButton("\"Raqamli Iz\" Testi", icon_custom_emoji_id=E["TEST"]),
            KeyboardButton("Real keyslar: 3 ta xavf", icon_custom_emoji_id=E["WARNING"])
        ],
        [
            KeyboardButton("Anonim SOS / Yordam", icon_custom_emoji_id=E["SOS"]),
            KeyboardButton("Veb-Platforma havolasi", icon_custom_emoji_id=E["GLOBE"])
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
        f"{p('INFO', 'ℹ️')} Botga istalgan formatdagi fotosuratni yuboring:\n"
        f"• <b>Oddiy rasm yoki Hujjat (JPG, PNG, WEBP)</b>;\n"
        f"• <b>Apple iPhone formatidagi (.HEIC) fotosuratlar</b>;\n"
        f"• <b>.ZIP arxivdagi fotosuratlar to‘plami</b>!\n\n"
        f"🧪 <i>Sinov uchun GPS-li tayyor rasm olish: /sample buyrug‘ini bosing.</i>"
    )
    
    if os.path.exists(LOGO_PATH):
        with open(LOGO_PATH, "rb") as photo:
            await update.message.reply_photo(
                photo=photo,
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=MAIN_KEYBOARD
            )
    else:
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
        f"{p('SOS', '🚨')} <b>ANONIM SOS VA YORDAM MARKAZI</b>\n\n"
        f"Agar siz ijtimoiy tarmoqda:\n"
        f"• {p('WARNING', '⚠️')} Kiberbulling yoki haqoratga uchragan bo‘lsangiz;\n"
        f"• {p('WARNING', '⚠️')} Shaxsiy rasmlaringiz bilan shantaj qilishayotgan bo‘lsa;\n"
        f"• {p('WARNING', '⚠️')} Akkauntingiz buzilib, pul talab qilishayotgan bo‘lsa — <b>HECH QACHON QO‘RQMANG VA YASHIRMANG!</b>\n\n"
        f"{p('CALL', '📞')} <b>Tezkor ishonch raqamlari:</b>\n"
        f"• Maktab psixologi kabineti: 4-maktab 2-qavat, 204-xona\n"
        f"• O‘zbekiston Kiberxavfsizlik markazi: <b>1133</b>\n"
        f"• Bolalar ishonch telefoni: <b>1111</b>\n\n"
        f"{p('CHAT', '💬')} Istalgan vaqtda muammoingizni shu botga yozib qoldirishingiz mumkin (shaxsingiz to‘liq sir saqlanadi)."
    )
    await update.message.reply_text(sos_text, parse_mode="HTML")

async def web_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_text = (
        f"{p('GLOBE', '🌐')} <b>«KIBERIZ-4» INTERAKTIV VEB-PLATFORMASI</b>\n\n"
        f"Loyihaning to‘liq interaktiv veb-platformasida siz:\n"
        f"• {p('EXIF_PHOTO', '🖼️')} O‘z suratingizning EXIF metama’lumotlarini onlayn tekshirishingiz;\n"
        f"• {p('LOCK', '🔒')} Interaktiv parol mustahkamligi kalkulyatoridan foydalanishingiz;\n"
        f"• {p('TROPHY', '🏆')} 4-maktab sinflari reytingini jonli kuzatishingiz mumkin!\n\n"
        f"Platformani ochish uchun quyidagi tugmani bosing:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Veb-Platformani ochish", url="https://abduvoitov11.github.io/kiberiz4/", icon_custom_emoji_id=E["ROCKET"])]
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
        
    await msg.reply_chat_action("typing")
    
    is_doc = bool(msg.document)
    is_video = bool(msg.video)
    file_bytes = None
    file_name = "fayl"
    
    video_exts = (".mp4", ".mov", ".avi", ".mkv", ".3gp", ".webm", ".m4v")
    img_exts = (".jpg", ".jpeg", ".png", ".tiff", ".heic", ".heif", ".webp")
    
    if is_doc:
        doc = msg.document
        file_name = doc.file_name or "hujjat"
        mime = (doc.mime_type or "").lower()
        valid_exts = img_exts + video_exts + (".zip",)
        if not (mime.startswith("image/") or mime.startswith("video/") or "zip" in mime or any(file_name.lower().endswith(ext) for ext in valid_exts)):
            await msg.reply_text(
                f"{p('WARNING', '⚠️')} Iltimos, tahlil qilish uchun <b>fotosurat</b> (JPG, PNG, HEIC), <b>video</b> (MP4, MOV) yoki <b>ZIP arxiv</b> yuboring.",
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
            f"{p('HACKER', '🕵️‍♂️')} <b>VIDEODAGI MAXSUS OSINT VA FON XAVFLARI:</b>\n"
            f"1. {p('CALL', '🔊')} <b>Ovoz tahlili (Audio OSINT):</b> Orqa fondagi suhbatlar, maktab qo‘ng‘irog‘i, metro bekati e’loni yoki ko‘cha shovqini orqali joylashuvingiz bilib olinadi.\n"
            f"2. {p('SCHOOL', '🏫')} <b>Harakatdagi kadrlar:</b> Kamera burilganda ko‘rinib qolgan xona raqami, o‘qituvchi, deraza orqasidagi do‘kon nomi yoki avtomobil davlat raqami.\n"
            f"3. {p('TIMER', '☀️')} <b>Soya va yorug‘lik (Chronolocation):</b> Quyosh tushish burchagi orqali video olingan aniq soat va dunyo tomoni (Shimol/Janub) hisoblanadi.\n\n"
            f"{p('SHIELD', '🛡️')} <b>Maslahat:</b> Ijtimoiy tarmoqqa video yuklashdan avval orqa fondagi shaxsiy obyektlarni tekshiring va audio yo‘lakdagi begona gaplarni o‘chiring!"
        )
        
        await msg.reply_text(analysis_msg, parse_mode="HTML", disable_web_page_preview=True)
        if coords:
            lat_val, lon_val = coords
            await msg.reply_location(latitude=lat_val, longitude=lon_val)
        return

    # Process Single Image (JPG, PNG, HEIC, WEBP, TIFF)
    details, coords, err = parse_single_image_exif(file_bytes, file_name)
    
    if err:
        await msg.reply_text(
            f"{p('WARNING', '⚠️')} Rasmni ochishda xatolik yuz berdi ({html.escape(err)}). Iltimos, boshqa surat yuboring.",
            parse_mode="HTML"
        )
        return
        
    analysis_msg = f"{p('SEARCH', '🔍')} <b>OSINT TAHLIL NATIJASI ({html.escape(file_name)}):</b>\n\n"
    
    # Real Visual OSINT Analysis (Chronolocation & OCR)
    visual_info = analyze_visual_osint(file_bytes)
    
    # Calculate composite Cyber Risk Score (0-100%)
    risk_score = 15
    if coords:
        risk_score += 55
    elif details:
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
    
    # Reverse Search & Warning
    analysis_msg += (
        f"{p('GLOBE', '🌐')} <b>4. TESKARI QIDIRUV (REVERSE SEARCH) XAVFI:</b>\n"
        f"Firibgarlar ushbu suratni <b>Google Lens</b> yoki <b>Yandex Images</b> orqali qidirib, "
        f"boshqa tarmoqlardagi (VK, Telegram, Facebook) akkauntlaringizni fosh qilishi mumkin!\n\n"
        f"{p('SHIELD', '🛡️')} <b>Tavsiya:</b> Instagram/Telegram profilingizni «Private» qiling va deraza/maktab foni ko‘ringan suratlarni yuklamang!"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Google Lens orqali qidirish", url="https://lens.google.com/", icon_custom_emoji_id=E["SEARCH"])],
        [InlineKeyboardButton("Yandex Images orqali qidirish", url="https://yandex.com/images/search?rpt=imageview", icon_custom_emoji_id=E["GLOBE"])],
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
    text = update.message.text
    if "Suratni tekshirish" in text or "OSINT" in text:
        await update.message.reply_text(
            f"{p('EXIF_PHOTO', '🖼️')} Iltimos, tahlil qilish uchun botga <b>istalgan fotosuratni</b> yuboring:\n"
            f"• <b>JPG, PNG, WEBP</b> (fayl yoki rasm holida);\n"
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
    elif "Veb-Platforma" in text:
        await web_command(update, context)
    else:
        await update.message.reply_text(
            f"{p('INFO', 'ℹ️')} Iltimos, pastdagi menyu tugmalaridan birini tanlang yoki tahlil uchun fotosurat yuboring.",
            parse_mode="HTML",
            reply_markup=MAIN_KEYBOARD
        )

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
    
    app.add_handler(CallbackQueryHandler(quiz_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, photo_or_doc_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    
    print("Bot is successfully polling!")
    app.run_polling()

if __name__ == "__main__":
    main()
