# 🛡️ «KiberIz-4» — Raqamli Iz va Profil Auditi Tizimi
> **4-sonli umumta’lim maktabi maxsus kiberxavfsizlik va ijtimoiy tarmoq mas’uliyati loyihasi**  
> *"Internet hech narsani unutmaydi: O‘z raqamli izingni boshqar!"*

[![Telegram Bot](https://img.shields.io/badge/Telegram-@kiberiz__bot-blue?style=for-the-badge&logo=telegram)](https://t.me/kiberiz_bot)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-emerald.svg?style=for-the-badge)](LICENSE)

---

## 📌 Loyiha Haqida

**«KiberIz-4»** — maktab o‘quvchilari va o‘smirlarning ijtimoiy tarmoqlardagi xavfsizligini ta’minlash, ularga **OSINT (Ochiq manbalar tahlili)** orqali bitta fotosurat orqali qanday ma’lumotlar fosh bo‘lishini ko‘rsatish va **5 daqiqada profilni to‘liq himoyalash** imkonini beruvchi innovatsion ekotizimdir.

### 🎯 2 ta Asosiy Yo‘nalish:
1. **OSINT Laboratoriyasi:** O‘quvchi ijtimoiy tarmoqqa joylagan bitta fotosurat orqali firibgarlar uning:
   * Qaysi maktab va sinfda o‘qishini;
   * Qaysi ko‘chada yashashini (deraza manzarasi yoki orqa fondagi belgilar);
   * Qachon uyda yolg‘iz ekanligini qanday topib olishini ko‘rsatib beradi.
2. **«Xavfsiz Profil» 5 daqiqalik Chek-listi:** Har bir o‘quvchiga 5 daqiqada profilini kiber-qalqon bilan yopish bo‘yicha amaliy qo‘llanma (telefon raqamni yashirish, 2FA yoqish, GPS teglarni o‘chirish, begona sessiyalarni yopish).

---

## 📂 Loyiha Tuzilmasi

```
KiberIz4/
├── assets/                  # Brend logotiplari (SVG, PNG) va kontseptual san'at
├── bot/                     # Telegram Bot (@kiberiz_bot)
│   ├── bot.py               # Real OSINT EXIF/GPS tahlilchi va viktorina boti
│   ├── custom_emojis.json   # Telegram Premium rasmiy emojilar xaritasi
│   ├── requirements.txt     # Python kutubxonalari
│   └── sample_gps_school4.jpg # Test uchun GPS koordinatali fotosurat
├── presentation/            # Hakamlar uchun 12 slaydli professional taqdimot
│   ├── KiberIz_Taqdimot.pdf # PDF formatdagi tayyor slaydlar
│   ├── KiberIz_Taqdimot.pptx# PowerPoint formati
│   └── generate_slides.py   # Avtomatik slayd generatori
├── web/                     # Interaktiv Kiber-Platforma
│   ├── index.html           # Real vaqtda EXIF/GPS tahlilchi dashboard
│   ├── exif.min.js          # Brauzer ichidagi EXIF o‘quvchi
│   ├── samples/             # Sinov namuna suratlari
│   └── vercel.json          # Vercel deploy konfiguratsiyasi
└── render.yaml              # Render.com Background Worker & Web Service avtomatizatsiyasi
```

---

## 🚀 O‘rnatish va Ishga Tushirish

### 1. Telegram Botni Mahalliy Ishga Tushirish
```bash
git clone https://github.com/abduvoitov11/kiberiz4.git
cd kiberiz4
pip install -r bot/requirements.txt
python bot/bot.py
```

### 2. Veb-Platformani Ochish
```bash
python3 -m http.server 8080 --directory web
```
Brauzerda `http://localhost:8080` manzilini oching.

---

## ☁️ Serverga Joylash (Deploy)

### A) Render.com (Bot uchun - 24/7 Bepul):
1. [Render.com](https://render.com) ga kiring va ushbu repozitoriyni ulang.
2. **Background Worker** (yoki **Web Service**) ni tanlang.
3. Build Command: `pip install -r bot/requirements.txt`
4. Start Command: `python bot/bot.py`
5. Environment Variable: `BOT_TOKEN` = `sizning_telegram_bot_tokeningiz`

### B) Vercel (Veb-sayt uchun):
1. [Vercel.com](https://vercel.com) ga kiring va repozitoriyni ulang.
2. **Root Directory:** `web` qilib belgilang.
3. **Deploy** tugmasini bosing!

---

## 👨‍💻 Muallif va Rahmatlar
* **Tashabbus:** 4-sonli umumta’lim maktabi
* **Mavzu:** *"Ijtimoiy tarmoqlarda xavfsizlik va mas’uliyat"*
* **Telegram Bot:** [@kiberiz_bot](https://t.me/kiberiz_bot)
