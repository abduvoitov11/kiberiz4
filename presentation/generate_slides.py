import os
import subprocess
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE

out_dir = "/home/torabek/KiberIz4/presentation"
out_pptx = os.path.join(out_dir, "KiberIz_Taqdimot.pptx")
out_pdf = os.path.join(out_dir, "KiberIz_Taqdimot.pdf")
png_dir = os.path.join(out_dir, "slides_png")

os.makedirs(out_dir, exist_ok=True)
os.makedirs(png_dir, exist_ok=True)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
blank_layout = prs.slide_layouts[6]

# ==========================================
# JIDDIY VA BIZNES / AKADEMIK RANGLAR PALITRASI
# ==========================================
BG_DARK = RGBColor(11, 17, 32)          # #0B1120 To'q ko'k / grafit
CARD_BG = RGBColor(19, 29, 51)          # #131D33 Navy karta foni
CARD_LINE = RGBColor(37, 99, 235)       # #2563EB Moviy chiziq
CARD_TOP_BAR = RGBColor(56, 189, 248)   # #38BDF8 Karta tepasidagi nozik chiziq

COLOR_PRIMARY = RGBColor(56, 189, 248)  # #38BDF8 Steel Blue
COLOR_ACCENT = RGBColor(37, 99, 235)    # #2563EB Royal Blue
COLOR_SUCCESS = RGBColor(16, 185, 129)  # #10B981 Zumrad yashil
COLOR_WARNING = RGBColor(225, 29, 72)   # #E11D48 Klassik qizil
COLOR_AMBER = RGBColor(217, 119, 6)     # #D97706 Oltin/jigarrang

TEXT_WHITE = RGBColor(255, 255, 255)   # #FFFFFF
TEXT_LIGHT = RGBColor(226, 232, 240)   # #E2E8F0 Och kulrang
TEXT_MUTED = RGBColor(148, 163, 184)   # #94A3B8 Neytral matn

def set_slide_bg(slide):
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = BG_DARK
    bg.line.fill.background()
    return bg

slides_data = [
    # ----------------------------------------------------
    # 1. TITUL SLAYDI (HERO DASHBOARD)
    # ----------------------------------------------------
    {
        "type": "hero",
        "badge": "4-SONLI UMUMTAʼLIM MAKTABI • ILG‘OR KIBERXAVFSIZLIK TIZIMI",
        "title": "KIBERIZ-4",
        "subtitle": "Maktab O‘quvchilari Uchun Raqamli Iz va Kiberxavfsizlik Tizimi",
        "desc": "Ijtimoiy tarmoqlardagi xatarlarni tahlil qilish, Visual OSINT va sun’iy intellekt orqali profilaktika qilish ekotizimi",
        "pills": [
            ("🛰️ Visual OSINT", COLOR_PRIMARY),
            ("🎭 Deepfake Detektor", COLOR_ACCENT),
            ("🛡️ Guruh Qalqoni", COLOR_SUCCESS),
            ("🚨 Anonim SOS Markazi", COLOR_AMBER)
        ],
        "footer": "Toshkent • 2026 | Telegram: @kiberiz_bot | Veb-Platforma: abduvoitov11.github.io/kiberiz4/"
    },

    # ----------------------------------------------------
    # 2. DOLZARB MUAMMO
    # ----------------------------------------------------
    {
        "type": "cards",
        "badge": "DOLZARB MUAMMO VA STATISTIKA",
        "title": "Mavjud Muammo: Internet Hech Narsani Unutmaydi",
        "desc": "O‘quvchilar tomonidan ehtiyotsizlik bilan joylangan har bir rasm va ma’lumot jiddiy xatarlarga olib kelmoqda:",
        "cards": [
            (
                "Ochiq Profillar va 2FA Yo‘qligi",
                "85% profil himoyalanmagan",
                "O‘quvchilarning aksariyati shaxsiy ma’lumotlarini ochiq qoldirgan. Ikki bosqichli parol (2FA) yo‘qligi sababli akkauntlar osongina o‘g‘irlanmoqda.",
                COLOR_WARNING
            ),
            (
                "Suratdagi 3 ta Katta Xavf",
                "Maktab, uy va shaxsiy vaqt foshligi",
                "Maktab formasi, deraza manzarasi va 'uyda yolg‘izman' postlari orqali o‘quvchining qayerda ekanligi va yashash manzili 1 daqiqada hisoblab topiladi.",
                COLOR_AMBER
            ),
            (
                "Shantaj va Kiberbulling",
                "Ruhiy bosim va firibgarlik",
                "Tarmoqdan olingan fotosuratlar firibgarlar tomonidan montaj qilinib, bolalarni aldash, shantaj qilish va pul talab qilish holatlari ko‘paymoqda.",
                COLOR_PRIMARY
            )
        ]
    },

    # ----------------------------------------------------
    # 3. YECHIM: KIBERIZ-4 EKOTIZIMI
    # ----------------------------------------------------
    {
        "type": "cards",
        "badge": "YAGONA MAJMUAVIY YECHIM",
        "title": "«KiberIz-4» — 3 Bo‘g‘inli Milliy Kiber-Qalqon",
        "desc": "Quruq ma’ruzalar o‘rniga har bir o‘quvchi telefoni ichida real vaqtda ishlovchi interaktiv vositalar:",
        "cards": [
            (
                "Telegram Bot (@kiberiz_bot)",
                "24/7 Aqlli Kiber-Maslahatchi",
                "Suratlar, skrinshotlar, QR-kodlar, .APK ilovalar va havolalarni sun’iy intellekt (Gemini AI) orqali soniyalarda tekshirib, xavflarni ko‘rsatadi.",
                COLOR_PRIMARY
            ),
            (
                "Interaktiv Veb-Platforma",
                "Kiber-Radar va Maktab Reytingi",
                "Havola va domenlarni onlayn skanerlash, parol mustahkamligi kalkulyatori hamda maktab sinflarining kiber-savodxonlik reytingi.",
                COLOR_SUCCESS
            ),
            (
                "5 Daqiqalik «Xavfsiz Profil»",
                "Amaliy kiber-gigiyena ko‘nikmasi",
                "O‘quvchilar o‘z smartfoni va akkauntini 99% kiberhujumlardan yopish bo‘yicha 5 ta aniq, bosqichma-bosqich qoidani o‘rganadi.",
                COLOR_ACCENT
            )
        ]
    },

    # ----------------------------------------------------
    # 4. ASOSIY INNOVATSIYALAR (WOW-FUNKSIYALAR)
    # ----------------------------------------------------
    {
        "type": "cards",
        "badge": "ILG‘OR TEXNOLOGIYALAR VA INNOVATSIYA",
        "title": "Asosiy Yangiliklar: 3 ta Eksklyuziv Imkoniyat",
        "desc": "Loyiha doirasida ishlab chiqilgan va amaliyotga joriy etilgan noyob funksional modullar:",
        "cards": [
            (
                "Visual OSINT (GPS-siz Fosh)",
                "Orqa fondagi bilvosita belgilar",
                "Suratda GPS o‘chiq bo‘lsa ham, fondagi avtomobil raqami (01, 10), dorixona, do‘kon peshlavhasi va telefon kodi orqali manzil fosh etiladi.",
                COLOR_PRIMARY
            ),
            (
                "Deepfake & AI Rasm Detektori",
                "Neyrotarmoq yolg‘onlarini aniqlash",
                "Midjourney/Deepfake orqali yasalgan soxta profillar ko‘z qorachig‘i aksi, mum-tekstura va biometriya orqali tekshirilib, aniq foiz (0-100%) beriladi.",
                COLOR_ACCENT
            ),
            (
                "Sinf Guruhlari Kiber-Qalqoni",
                "Real vaqtda guruhlarni tozalash",
                "Sinf va ota-onalar guruhiga tushgan fishing havolalar («500 ming pul») va virusli .APK fayllar avtomatik o‘chirilib, ogohlantirish yuboriladi.",
                COLOR_SUCCESS
            )
        ]
    },

    # ----------------------------------------------------
    # 5. AMALIY NATIJALAR VA JAVOBGARLIK
    # ----------------------------------------------------
    {
        "type": "cards",
        "badge": "SAMARADORLIK VA HUQUQIY MADANIYAT",
        "title": "Amaliy Natijalar (KPI) va Qonuniy Javobgarlik",
        "desc": "4-maktabda loyihaning joriy etilishi natijasida erishilgan ijobiy siljishlar va huquqiy asos:",
        "cards": [
            (
                "95% 2FA Ko‘rsatkichi",
                "Akkauntlar himoyasi keskin oshdi",
                "5–11-sinf o‘quvchilarining 95 foizida ikki bosqichli parol faollashtirildi. Fishing tuzoqlariga tushish holatlari 85 foizga kamaydi.",
                COLOR_SUCCESS
            ),
            (
                "Anonim SOS va Ishonch Markazi",
                "100% maxfiy psixologik ko‘mak",
                "Kiberbulling yoki shantajga uchragan o‘quvchilar shaxsi sir saqlangan holda maktab inspektori va psixologiga dalillar bilan murojaat qila oladi.",
                COLOR_PRIMARY
            ),
            (
                "Huquqiy Savodxonlik (Qonun)",
                "MJtK 40, 41 va JK 168-moddalar",
                "Internetda tuhmat, haqorat va birovning suratini ruxsatsiz tarqatish uchun belgilangan ma’muriy va jinoiy javobgarlik bo‘yicha tushuntirish berildi.",
                COLOR_AMBER
            )
        ]
    },

    # ----------------------------------------------------
    # 6. YAKUNIY XULOSA (RESTRUCTURED DASHBOARD - NO OVERLAP!)
    # ----------------------------------------------------
    {
        "type": "conclusion_dashboard",
        "badge": "YAKUNIY XULOSA VA KELAJAK REJALARI",
        "title": "Xavfsiz Raqamli Maktab — Mas’uliyatli Avlod!",
        "subtitle": "«KiberIz-4» tizimini Toshkent shahri va Respublika maktablariga tatbiq etish strategiyasi",
        "cards": [
            (
                "🏛️ Maktablar Uchun Tayyor Yechim",
                "0 So‘m Byudjet • Ochiq Kodli",
                "Loyiha to‘liq sinovdan o‘tgan va tekin infratuzilmada ishlaydi. Qo‘shimcha davlat mablag‘i talab qilmaydi, 24/7 mustaqil xizmat ko‘rsatadi.",
                COLOR_PRIMARY
            ),
            (
                "🚀 1 Kunda Joriy Etish (Plug & Play)",
                "Tezkor Qamrov va Masshtablash",
                "Istalgan maktab, sinf yoki ota-onalar Telegram guruhiga botni 1 daqiqada ulash va o‘quvchilarni real vaqtda kiber-qalqon bilan qamrab olish imkoniyati.",
                COLOR_SUCCESS
            ),
            (
                "🤖 AI Kiber-Maslahatchi",
                "24/7 Sun’iy Intellekt Himoyasi",
                "• 24/7 Raqamli Kiber-Mentor\n• Shaxsiy va guruh xavfsizligi\n• Telegram Bot: @kiberiz_bot",
                COLOR_AMBER
            )
        ],
        "footer": "Toshkent shahar 4-sonli umumtaʼlim maktabi • 2026"
    }
]

total_slides = len(slides_data)

for s_idx, s_data in enumerate(slides_data, 1):
    slide = prs.slides.add_slide(blank_layout)
    set_slide_bg(slide)
    
    if s_data["type"] == "hero":
        # Top Badge
        tx_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.1), Inches(11.333), Inches(0.45))
        tf = tx_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"[ {s_data['badge']} ]"
        p.font.size = Pt(12)
        p.font.bold = True
        p.font.color.rgb = COLOR_PRIMARY
        p.alignment = PP_ALIGN.CENTER
        
        # Main Title (Precise spacing, zero overlap!)
        tx_box2 = slide.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(11.333), Inches(1.1))
        tf2 = tx_box2.text_frame
        p2 = tf2.paragraphs[0]
        p2.text = s_data["title"]
        p2.font.size = Pt(48)
        p2.font.bold = True
        p2.font.color.rgb = TEXT_WHITE
        p2.alignment = PP_ALIGN.CENTER
        
        # Subtitle
        tx_box3 = slide.shapes.add_textbox(Inches(1.5), Inches(3.0), Inches(10.333), Inches(0.7))
        tf3 = tx_box3.text_frame
        p3 = tf3.paragraphs[0]
        p3.text = s_data["subtitle"]
        p3.font.size = Pt(20)
        p3.font.bold = True
        p3.font.color.rgb = COLOR_PRIMARY
        p3.alignment = PP_ALIGN.CENTER

        # Detailed Description
        if "desc" in s_data:
            tx_box_d = slide.shapes.add_textbox(Inches(1.5), Inches(3.85), Inches(10.333), Inches(0.8))
            tf_d = tx_box_d.text_frame
            pd = tf_d.paragraphs[0]
            pd.text = s_data["desc"]
            pd.font.size = Pt(15)
            pd.font.color.rgb = TEXT_MUTED
            pd.alignment = PP_ALIGN.CENTER

        # Feature Pills at bottom
        if "pills" in s_data:
            pill_y = Inches(4.9)
            pills = s_data["pills"]
            num_pills = len(pills)
            pill_w = Inches(2.65)
            gap = Inches(0.24)
            total_w = num_pills * pill_w + (num_pills - 1) * gap
            start_x = (Inches(13.333) - total_w) / 2
            
            for p_i, (p_text, p_color) in enumerate(pills):
                px = start_x + p_i * (pill_w + gap)
                p_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, px, pill_y, pill_w, Inches(0.6))
                p_shape.fill.solid()
                p_shape.fill.fore_color.rgb = CARD_BG
                p_shape.line.color.rgb = CARD_LINE
                p_shape.line.width = Pt(1.2)
                
                ptf = p_shape.text_frame
                ptf.margin_top = Inches(0.12)
                pp = ptf.paragraphs[0]
                pp.text = p_text
                pp.font.size = Pt(12)
                pp.font.bold = True
                pp.font.color.rgb = p_color
                pp.alignment = PP_ALIGN.CENTER
        
        # Footer
        tx_box4 = slide.shapes.add_textbox(Inches(1.0), Inches(6.3), Inches(11.333), Inches(0.6))
        tf4 = tx_box4.text_frame
        p4 = tf4.paragraphs[0]
        p4.text = s_data["footer"]
        p4.font.size = Pt(13)
        p4.font.color.rgb = TEXT_MUTED
        p4.alignment = PP_ALIGN.CENTER

    else:
        # Header Badge & Counter
        b_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.55), Inches(8.0), Inches(0.35))
        bp = b_box.text_frame.paragraphs[0]
        bp.text = f"[ {s_data['badge']} ]"
        bp.font.size = Pt(11)
        bp.font.bold = True
        bp.font.color.rgb = COLOR_PRIMARY

        # Top-Right Slide Counter
        c_box = slide.shapes.add_textbox(Inches(9.5), Inches(0.55), Inches(2.833), Inches(0.35))
        cp = c_box.text_frame.paragraphs[0]
        cp.text = f"SLAYD {s_idx:02d} / {total_slides:02d} • KIBERIZ-4"
        cp.font.size = Pt(11)
        cp.font.bold = True
        cp.font.color.rgb = TEXT_MUTED
        cp.alignment = PP_ALIGN.RIGHT
        
        # Slide Title
        t_box = slide.shapes.add_textbox(Inches(1.0), Inches(0.92), Inches(11.333), Inches(0.65))
        tp = t_box.text_frame.paragraphs[0]
        tp.text = s_data["title"]
        tp.font.size = Pt(26)
        tp.font.bold = True
        tp.font.color.rgb = TEXT_WHITE
        
        # Slide Description / Subtitle
        desc_text = s_data.get("desc") or s_data.get("subtitle", "")
        d_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.60), Inches(11.333), Inches(0.55))
        dp = d_box.text_frame.paragraphs[0]
        dp.text = desc_text
        dp.font.size = Pt(13.5)
        dp.font.color.rgb = TEXT_MUTED
        
        # 3 Cards Layout (Structured, professional, left-aligned)
        card_w = Inches(3.55)
        card_h = Inches(4.5)
        start_y = Inches(2.35)
        gap = Inches(0.34)
        
        for c_i, (c_title, c_subtitle, c_text, c_color) in enumerate(s_data["cards"]):
            c_x = Inches(1.0) + c_i * (card_w + gap)
            
            # Card background shape
            c_shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, c_x, start_y, card_w, card_h)
            c_shape.fill.solid()
            c_shape.fill.fore_color.rgb = CARD_BG
            c_shape.line.color.rgb = CARD_LINE
            c_shape.line.width = Pt(1.2)
            
            # Card text frame
            cf = c_shape.text_frame
            cf.word_wrap = True
            cf.margin_left = Inches(0.28)
            cf.margin_right = Inches(0.28)
            cf.margin_top = Inches(0.32)
            cf.margin_bottom = Inches(0.25)
            
            # Card Title (Header)
            cp1 = cf.paragraphs[0]
            cp1.text = c_title
            cp1.font.size = Pt(16)
            cp1.font.bold = True
            cp1.font.color.rgb = c_color
            cp1.space_after = Pt(8)

            # Card Subtitle / Highlight
            cp_sub = cf.add_paragraph()
            cp_sub.text = f"• {c_subtitle}"
            cp_sub.font.size = Pt(12)
            cp_sub.font.bold = True
            cp_sub.font.color.rgb = TEXT_LIGHT
            cp_sub.space_after = Pt(12)
            
            # Card Detailed Explanation
            cp2 = cf.add_paragraph()
            cp2.text = c_text
            cp2.font.size = Pt(12.5)
            cp2.font.color.rgb = TEXT_MUTED

prs.save(out_pptx)
print(f"Successfully generated {total_slides}-slide concise presentation at: {out_pptx}")

# Convert to PDF using LibreOffice
print("Converting presentation to PDF via LibreOffice...")
cmd_pdf = ["libreoffice", "--headless", "--convert-to", "pdf", out_pptx, "--outdir", out_dir]
subprocess.run(cmd_pdf, check=True)
print(f"Successfully created PDF at: {out_pdf}")

# Clean old pngs and render new
subprocess.run(f"rm -f {png_dir}/*.png", shell=True)
print("Rendering slide PNG previews via pdftoppm...")
cmd_png = ["pdftoppm", "-png", "-r", "150", out_pdf, os.path.join(png_dir, "slide")]
subprocess.run(cmd_png, check=True)
png_files = sorted([f for f in os.listdir(png_dir) if f.endswith(".png")])
print(f"Successfully rendered {len(png_files)} PNG slide previews in: {png_dir}")
