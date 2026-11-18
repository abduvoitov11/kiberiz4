import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

out_pptx = "/home/torabek/KiberIz4/presentation/KiberIz_Taqdimot.pptx"
os.makedirs(os.path.dirname(out_pptx), exist_ok=True)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# Theme Colors
BG_DARK = RGBColor(7, 11, 20)
CARD_BG = RGBColor(15, 23, 42)
NEON_CYAN = RGBColor(0, 242, 254)
NEON_GREEN = RGBColor(67, 233, 123)
TEXT_WHITE = RGBColor(255, 255, 255)
TEXT_MUTED = RGBColor(148, 163, 184)
ACCENT_RED = RGBColor(244, 63, 94)
ACCENT_AMBER = RGBColor(245, 158, 11)

def set_slide_bg(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()
    return bg

slides_data = [
    # 1. TITLE SLIDE
    {
        "type": "title",
        "badge": "4-SONLI UMUMTAʼLIM MAKTABI MAXSUS LOYIHASI",
        "title": "KIBERIZ-4",
        "subtitle": "Raqamli Iz va Profil Auditi: Ijtimoiy Tarmoqlarda Xavfsizlik va Masʼuliyat Ekotizimi",
        "footer": "Toshkent • 2026 | Telegram: @kiberiz_bot"
    },
    # 2. PROBLEM
    {
        "type": "content",
        "badge": "MAVJUD DOLZARB MUAMMO",
        "title": "Raqamli Iz: Internet Hech Qachon Unutmaydi!",
        "desc": "O‘quvchilar ijtimoiy tarmoqqa joylagan har bir fotosurat, izoh va belgi o‘chirilmaydigan 'raqamli iz' qoldiradi.",
        "cards": [
            ("📱 98% O‘quvchilarda Smartfon", "Har kuni o‘rtacha 3.5 soat ijtimoiy tarmoqda vaqt o‘tkaziladi.", ACCENT_AMBER),
            ("⚠️ 85% Ochiq Profillar", "Shaxsiy hayot, oila va maktab maʼlumotlari begonalarga ochiq turadi.", ACCENT_RED),
            ("🔒 40% Parolsiz Qolgan Akkauntlar", "Ikki bosqichli tekshiruv (2FA) yoqilmaganligi sababli akkauntlar o‘g‘irlanadi.", NEON_CYAN)
        ]
    },
    # 3. OSINT EXPLANATION
    {
        "type": "content",
        "badge": "TEXNOLOGIK ASOS",
        "title": "OSINT (Ochiq Manbalar Tahlili) Qanday Ishlaydi?",
        "desc": "Firibgarlar va kiberhujumchilar qimmatbaho dasturlardan emas, siz o‘zingiz tarmoqqa joylagan maʼlumotlardan foydalanadi.",
        "cards": [
            ("📸 Bitta Oddiy Fotosurat", "Siz shunchaki yangi rasmingizni yuklaysiz, ammo rasm ichida EXIF fayl va fon belgilari yashiringan bo‘ladi.", NEON_CYAN),
            ("🔍 Detallarni Yig‘ish (Profiling)", "Kiyimdagi logotip, dars jadvali, deraza orqasidagi binolar birlashtirilib shaxsiy dosye tuziladi.", NEON_GREEN),
            ("🎯 Aniq Hujum Nuqtasi", "Sizning qachon va qayerda bo‘lishingizni bilgan holda fishing, shantaj yoki kiberbulling uyushtiriladi.", ACCENT_RED)
        ]
    },
    # 4. CASE 1
    {
        "type": "content",
        "badge": "1-XAVF KEYS-TAHLILI",
        "title": "1. Maktabingiz va Sinfingiz Qanday Fosh Bo‘ladi?",
        "desc": "Maktab yo‘lagida, sinf xonasida yoki maktab hovlisida olingan selfilarning xavfi:",
        "cards": [
            ("🏫 Emblema va Formadagi Belgilar", "Ko‘krak nishoni yoki maktab raqami orqali qaysi maktabda o‘qishingiz 1 daqiqada topiladi.", NEON_CYAN),
            ("🚪 Sinf Xonasi Eshigi va Parta", "Xona raqami va yo‘nalishi orqali o‘quvchining nechanchi sinf ekani aniqlanadi.", ACCENT_AMBER),
            ("⚠️ Xavf Oqibati", "Begona shaxslar maktab chiqishida kutib olishi yoki maktabdosh nomidan soxta akkaunt ochishi mumkin.", ACCENT_RED)
        ]
    },
    # 5. CASE 2
    {
        "type": "content",
        "badge": "2-XAVF KEYS-TAHLILI",
        "title": "2. Uy Manzili va Xaritadagi Aniq Nuqta",
        "desc": "Uy derazasidan yoki balkonidan olingan chiroyli manzara surati:",
        "cards": [
            ("📍 Orqa Fondagi Binolar", "Ko‘rinib turgan do‘kon peshlavhasi, apteka, masjid yoki yo‘l belgisi geolokatsiyani ochadi.", NEON_CYAN),
            ("📐 Ko‘rish Burchagi va Qavat", "Chiroq ustunlari va daraxtlarning balandligiga qarab uyingiz nechanchi qavatda ekanligi hisoblanadi.", ACCENT_AMBER),
            ("⚠️ Xavf Oqibati", "Firibgarlar sizning aniq yashash manzilingizni bilib, oilangizga tahdid qilishi mumkin.", ACCENT_RED)
        ]
    },
    # 6. CASE 3
    {
        "type": "content",
        "badge": "3-XAVF KEYS-TAHLILI",
        "title": "3. «Men Uyda Yolg‘izman» Signali",
        "desc": "Ko‘pchilik bilmasdan ijtimoiy tarmoqda joylaydigan eng xavfli postlar:",
        "cards": [
            ("✈️ 'Oila aʼzolarim safarga ketishdi'", "Bu kabi storislar o‘g‘rilar va firibgarlar uchun ochiqdan-ochiq chaqiruv hisoblanadi.", ACCENT_RED),
            ("🕒 Vaqt va Dars Rejimi", "'Ertaga soat 14:00 gacha darsdaman' deb eʼlon qilish — uy bo‘sh qoladigan vaqtni ko‘rsatib beradi.", ACCENT_AMBER),
            ("💡 Qoida: Xavfsiz Harakat", "Safardan qaytgandan so‘ng rasm joylash va shaxsiy rejalarni ommaga oshkor qilmaslik kerak.", NEON_GREEN)
        ]
    },
    # 7. THE SOLUTION: KIBERIZ-4
    {
        "type": "content",
        "badge": "YAGONA EKOTIZIM",
        "title": "Innovatsion Yechim: «KiberIz-4» Tizimi",
        "desc": "Quruq maʼruzalar o‘rniga har bir o‘quvchi telefoni ichida ishlovchi 3 ta amaliy vosita:",
        "cards": [
            ("🤖 Telegram Bot (@kiberiz_bot)", "Suratni 1 soniyada tekshirib, EXIF va fon xavflarini aniqlovchi aqlli yordamchi.", NEON_CYAN),
            ("🌐 Veb-Platforma & Laboratoriya", "Interaktiv fotosurat skaneri va sinflar bo‘yicha kiber-savodxonlik reytingi.", NEON_GREEN),
            ("🛡️ 5 Daqiqalik 'Xavfsiz Profil'", "Har bir o‘quvchiga o‘z profilini kiber-qalqon bilan yopish bo‘yicha aniq algoritm.", ACCENT_AMBER)
        ]
    },
    # 8. TELEGRAM BOT DETAILS
    {
        "type": "content",
        "badge": "AMALIY DEMO",
        "title": "Telegram Bot (@kiberiz_bot) Imkoniyatlari",
        "desc": "Bugun to‘liq ishga tushirilgan va sinovdan o‘tgan aqlli modul:",
        "cards": [
            ("📸 OSINT Skaner Moduli", "Surat yuborilganda undagi GPS koordinatalar, kamera modeli va fon xavflari fosh etiladi.", NEON_CYAN),
            ("🧪 'Raqamli Iz' Testi", "5 ta savol orqali foydalanuvchining shaxsiy xavfsizlik balini (0-100%) hisoblab beradi.", NEON_GREEN),
            ("🚨 Anonim SOS Tugmasi", "Kiberbulling yoki shantajga uchragan o‘quvchilar tezkor ishonch xizmatlariga murojaat qilishi mumkin.", ACCENT_RED)
        ]
    },
    # 9. 5-MINUTE CHECKLIST
    {
        "type": "content",
        "badge": "AMALIY KO‘NIKMA",
        "title": "5 Daqiqalik «Xavfsiz Profil» Chek-listi",
        "desc": "Ushbu 5 ta qadam profilingizni 99% kiberhujumlardan himoya qiladi:",
        "cards": [
            ("1. Telefon Raqamni Yashirish", "Telegram sozlamalari ➔ Maxfiylik ➔ Telefon raqam ➔ 'Hech kimga'.", NEON_CYAN),
            ("2. Ikki Bosqichli Parol (2FA)", "Maxfiylik ➔ Ikki bosqichli tekshiruv ➔ Kuchli harfli-raqamli parol.", NEON_GREEN),
            ("3. GPS Teglarni O‘chirish", "Kamera sozlamalari ➔ Joylashuv belgisi (Location Tag) ni o‘chirish.", ACCENT_AMBER)
        ]
    },
    # 10. LEGAL RESPONSIBILITY
    {
        "type": "content",
        "badge": "HUQUQIY SAVODXONLIK",
        "title": "Raqamli Odob va Qonuniy Masʼuliyat",
        "desc": "Internetdagi har bir so‘z va harakat uchun O‘zbekiston Respublikasi qonunlarida belgilangan javobgarlik:",
        "cards": [
            ("MJtK 40-modda: Tuhmat", "Ijtimoiy tarmoqda yolg‘on tarqatish uchun 20 dan 60 BHM gacha jarima.", ACCENT_AMBER),
            ("MJtK 41-modda: Haqorat Qilish", "Guruhlarda kamsitish va haqoratlash uchun 20 dan 40 BHM gacha jarima.", ACCENT_RED),
            ("MJtK 46-1-modda: Shaxsiy Sir", "Birovning suratini ruxsatsiz tarqatish uchun 10 dan 40 BHM gacha jarima.", NEON_CYAN)
        ]
    },
    # 11. RESULTS & IMPACT
    {
        "type": "content",
        "badge": "SAMARADORLIK VA QAMROV",
        "title": "Kutilayotgan Natijalar (KPI)",
        "desc": "4-maktabda loyihaning joriy etilishi natijasida erishiladigan aniq ko‘rsatkichlar:",
        "cards": [
            ("🛡️ 95% 2FA Ulushi", "Barcha 5–11-sinf o‘quvchilari o‘z akkauntlariga ikki bosqichli himoyani o‘rnatadi.", NEON_GREEN),
            ("📉 80% Ga Kamayish", "Fishing tuzoqlariga tushish va akkaunt o‘g‘irlanishi holatlari 80% ga qisqaradi.", NEON_CYAN),
            ("💰 0 So‘m Byudjet", "Loyiha to‘liq ochiq kodli va tekin infratuzilma asosida 24/7 rejimda ishlaydi.", ACCENT_AMBER)
        ]
    },
    # 12. CONCLUSION
    {
        "type": "title",
        "badge": "KIBERIZ-4 LOYIHASI XULOSASI",
        "title": "XAVFSIZ INTERNET — MASʼULIYATLI AVLOD!",
        "subtitle": "Telegram botimizni hoziroq sinab ko‘ring: @kiberiz_bot\nEʼtiboringiz uchun rahmat!",
        "footer": "4-sonli umumtaʼlim maktabi • 2026"
    }
]

for s_idx, s_data in enumerate(slides_data):
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    
    if s_data["type"] == "title":
        # Badge
        tx_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(11.333), Inches(0.6))
        tf = tx_box.text_frame
        p = tf.paragraphs[0]
        p.text = s_data["badge"]
        p.font.size = Pt(14)
        p.font.bold = True
        p.font.color.rgb = NEON_CYAN
        p.alignment = PP_ALIGN.CENTER
        
        # Main Title
        tx_box2 = slide.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(1.8))
        tf2 = tx_box2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = s_data["title"]
        p2.font.size = Pt(56)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE
        p2.alignment = PP_ALIGN.CENTER
        
        # Subtitle
        tx_box3 = slide.shapes.add_textbox(Inches(1.5), Inches(4.2), Inches(10.333), Inches(1.5))
        tf3 = tx_box3.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = s_data["subtitle"]
        p3.font.size = Pt(22)
        p3.font.color.rgb = TEXT_MUTED
        p3.alignment = PP_ALIGN.CENTER
        
        # Footer
        tx_box4 = slide.shapes.add_textbox(Inches(1.0), Inches(6.2), Inches(11.333), Inches(0.8))
        tf4 = tx_box4.text_frame
        p4 = tf4.paragraphs[0]
        p4.text = s_data["footer"]
        p4.font.size = Pt(14)
        p4.font.color.rgb = NEON_GREEN
        p4.alignment = PP_ALIGN.CENTER

    else:
        # Header Badge
        b_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.6), Inches(11.333), Inches(0.4))
        bp = b_box.text_frame.paragraphs[0]
        bp.text = s_data["badge"]
        bp.font.size = Pt(12)
        bp.font.bold = True
        bp.font.color.rgb = NEON_GREEN
        
        # Slide Title
        t_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.95), Inches(11.333), Inches(0.8))
        tp = t_box.text_frame.paragraphs[0]
        tp.text = s_data["title"]
        tp.font.size = Pt(32)
        tp.font.bold = True
        tp.font.color.rgb = TEXT_WHITE
        
        # Slide Description
        d_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(11.333), Inches(0.6))
        dp = d_box.text_frame.paragraphs[0]
        dp.text = s_data["desc"]
        dp.font.size = Pt(15)
        dp.font.color.rgb = TEXT_MUTED
        
        # 3 Cards Layout
        card_w = Inches(3.55)
        card_h = Inches(4.2)
        start_y = Inches(2.5)
        gap = Inches(0.34)
        
        for c_i, (c_title, c_text, c_color) in enumerate(s_data["cards"]):
            c_x = Inches(1.0) + c_i * (card_w + gap)
            
            # Card background shape
            c_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_x, start_y, card_w, card_h)
            c_shape.fill.solid()
            c_shape.fill.fore_color.rgb = CARD_BG
            c_shape.line.color.rgb = c_color
            c_shape.line.width = Pt(1.5)
            
            # Card text frame
            cf = c_shape.text_frame
            cf.word_wrap = True
            cf.margin_left = Inches(0.25)
            cf.margin_right = Inches(0.25)
            cf.margin_top = Inches(0.4)
            
            # Card title
            cp1 = cf.paragraphs[0]
            cp1.text = c_title
            cp1.font.size = Pt(18)
            cp1.font.bold = True
            cp1.font.color.rgb = c_color
            cp1.space_after = Pt(16)
            
            # Card content
            cp2 = cf.add_paragraph()
            cp2.text = c_text
            cp2.font.size = Pt(14)
            cp2.font.color.rgb = TEXT_MUTED

prs.save(out_pptx)
print("Successfully generated 12-slide presentation at:", out_pptx)
