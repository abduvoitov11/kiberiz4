#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for KiberIz-4 Telegram Bot
Tests all modules, parsers, AI engines, helpers, and state machines.
"""

import os
import sys
import json
import asyncio

# Ensure bot package is in path
sys.path.insert(0, '/home/torabek/KiberIz4/bot')

from bot import (
    E,
    p,
    auto_premium,
    strip_html_tags,
    format_ai_to_tg_html,
    convert_image_to_jpeg_bytes,
    parse_single_image_exif,
    parse_raw_image_exif,
    parse_apk_metadata,
    parse_audio_metadata,
    parse_document_metadata,
    parse_binary_or_script_metadata,
    analyze_visual_osint,
    scan_qr_code,
    get_human_address,
    QUIZ_QUESTIONS,
    MAIN_KEYBOARD,
    MENU_BUTTON_TEXTS
)

def test_emojis_and_html():
    print(">>> 1. Testing Premium Emojis & HTML Utilities...")
    # Test p()
    rendered_shield = p("SHIELD", "fallback")
    assert "<tg-emoji" in rendered_shield and "fallback" in rendered_shield, "p() failed to render tg-emoji"

    # Test auto_premium
    text = "Xavfsizlik 🛡️ va xavf ⚠️ tekshiruvi ✅"
    prem = auto_premium(text)
    assert '<tg-emoji emoji-id="' in prem, "auto_premium failed to convert emojis"

    # Test strip_html_tags
    stripped = strip_html_tags("<b>Salom</b> <a href='#'>havola</a>")
    assert stripped == "Salom havola", f"strip_html_tags failed: {stripped}"

    # Test format_ai_to_tg_html
    sample_ai = "**Kiber-Xavf:** Yuqori!\n*Maslahat:* Parolni `12345` qilmang.\n```python\nprint(1)\n```"
    tg_html = format_ai_to_tg_html(sample_ai)
    assert "<b>Kiber-Xavf:</b>" in tg_html, "Markdown bold not converted"
    assert "<code>12345</code>" in tg_html, "Markdown inline code not converted"
    assert "<pre>print(1)</pre>" in tg_html, "Markdown codeblock not converted"
    print("    [PASSED] Emojis and HTML utilities.")

def test_heic_and_image_parsing():
    print(">>> 2. Testing HEIC & Image OSINT Engine...")
    heic_path = "/home/torabek/Pictures/test.heic"
    assert os.path.exists(heic_path), f"File {heic_path} does not exist"
    with open(heic_path, "rb") as f:
        heic_bytes = f.read()

    # 1. Parse EXIF & GPS
    details, coords, err = parse_single_image_exif(heic_bytes, "test.heic")
    assert err is None, f"parse_single_image_exif failed with error: {err}"
    assert coords is not None, "GPS coordinates should be extracted from test.heic"
    lat, lon = coords
    assert lat == 41.0223 and lon == 69.352432, f"Coordinates mismatch: {coords}"
    assert any("samsung Galaxy A15" in d for d in details), "Device model missing from details"

    # 2. Convert to JPEG
    jpeg_bytes = convert_image_to_jpeg_bytes(heic_bytes, "test.heic")
    assert jpeg_bytes.startswith(b"\xff\xd8\xff"), "Converted file is not valid JPEG"

    # 3. Visual OSINT
    v_info = analyze_visual_osint(jpeg_bytes)
    assert v_info is not None and "brightness" in v_info, "analyze_visual_osint failed"

    # 4. Reverse Geocoding
    addr = get_human_address(lat, lon)
    assert addr and "Nurafshon" in addr, f"Reverse geocoding failed: {addr}"
    print(f"    [PASSED] HEIC Engine: Device Samsung A15, Lat: {lat}, Lon: {lon}, Addr: {addr}.")

def test_apk_analysis():
    print(">>> 3. Testing Android Malware & APK Engine...")
    apk_path = "/home/torabek/Downloads/Telegram Desktop/Rasmlar(4.png) 2026.apk"
    assert os.path.exists(apk_path), f"File {apk_path} does not exist"
    with open(apk_path, "rb") as f:
        apk_bytes = f.read()

    apk_info = parse_apk_metadata(apk_bytes, os.path.basename(apk_path))
    assert apk_info["package_name"] == "top.silk.starry", f"Package name mismatch: {apk_info['package_name']}"
    assert "READ_SMS" in apk_info["dangerous_perms"], "READ_SMS should be flagged as dangerous"
    assert "RECEIVE_SMS" in apk_info["dangerous_perms"], "RECEIVE_SMS should be flagged as dangerous"
    assert apk_info["dex_count"] >= 1, "DEX count should be >= 1"
    assert apk_info["file_size_mb"] > 0, "File size should be > 0"
    print(f"    [PASSED] APK Engine: Pkg: {apk_info['package_name']}, Dangerous perms: {apk_info['dangerous_perms']}.")

def test_audio_metadata():
    print(">>> 4. Testing Audio & Voice Analysis Engine...")
    audio_path = "/home/torabek/video_project/audio/sad.mp3"
    assert os.path.exists(audio_path), f"File {audio_path} does not exist"
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    details, _ = parse_audio_metadata(audio_bytes, "sad.mp3")
    assert len(details) > 0, "Audio details should not be empty"
    assert any("Kevin MacLeod" in d for d in details), "Artist name missing from audio details"
    assert any("320 kbps" in d for d in details), "Bitrate missing from audio details"
    print(f"    [PASSED] Audio Engine: Extracted {len(details)} metadata fields successfully.")

def test_document_metadata():
    print(">>> 5. Testing Document & Macro Analysis Engine...")
    doc_path = "/home/torabek/Rasxod_Oktyabr_1.xlsx"
    assert os.path.exists(doc_path), f"File {doc_path} does not exist"
    with open(doc_path, "rb") as f:
        doc_bytes = f.read()

    details, has_macro = parse_document_metadata(doc_bytes, "Rasxod_Oktyabr_1.xlsx")
    assert len(details) > 0, "Document details should not be empty"
    assert has_macro is False, "Standard xlsx should not have macros"
    print(f"    [PASSED] Document Engine: Extracted {len(details)} fields (has_macro={has_macro}).")

def test_binary_metadata():
    print(">>> 6. Testing Executable & Script Hashing...")
    sample_script = b"#!/bin/bash\necho test\n"
    meta = parse_binary_or_script_metadata(sample_script, "test.sh")
    assert meta["md5"] and len(meta["md5"]) == 32, "MD5 hash length invalid"
    assert meta["sha256"] and len(meta["sha256"]) == 64, "SHA256 hash length invalid"
    print("    [PASSED] Binary Hashing Engine.")

def test_quiz_structure():
    print(">>> 7. Testing Quiz Questions & Options...")
    assert len(QUIZ_QUESTIONS) == 5, f"Expected 5 questions, found {len(QUIZ_QUESTIONS)}"
    for idx, q in enumerate(QUIZ_QUESTIONS, 1):
        assert "q" in q and q["q"], f"Question {idx} has no text"
        assert "options" in q and len(q["options"]) >= 2, f"Question {idx} has invalid options"
        for opt_text, score in q["options"]:
            assert isinstance(score, int), f"Option score must be int in question {idx}"
    print("    [PASSED] Quiz Structure.")

def test_keyboards_and_menu_matching():
    print(">>> 8. Testing Keyboard Buttons & Clean-up Sync...")
    keyboard_buttons = set()
    for row in MAIN_KEYBOARD.keyboard:
        for btn in row:
            keyboard_buttons.add(btn.text)

    for btn_text in keyboard_buttons:
        assert btn_text in MENU_BUTTON_TEXTS, f"Button '{btn_text}' missing from MENU_BUTTON_TEXTS"
    print("    [PASSED] Keyboards and clean-up synchronization.")

async def test_ai_integration():
    print(">>> 9. Testing Live Gemini AI Cyber-Mentor...")
    from bot import ask_gemini_cyber_mentor, audit_link_with_ai, audit_username_with_ai

    # Test 1: General question
    mentor_resp = await ask_gemini_cyber_mentor("Parolni qanday kuchli qilish kerak?", user_id=999)
    print("    AI Mentor resp length:", len(mentor_resp))
    assert mentor_resp and len(mentor_resp) > 30, f"AI mentor response too short: {mentor_resp}"

    await asyncio.sleep(2.0)

    # Test 2: Username audit
    u_resp, u_raw = await audit_username_with_ai("@malika_2008")
    print("    Username audit resp length:", len(u_resp))
    assert u_raw == "malika_2008", f"Raw username mismatch: {u_raw}"
    assert u_resp and len(u_resp) > 30, f"Username audit response too short: {u_resp}"

    await asyncio.sleep(2.0)

    # Test 3: Link audit
    l_resp, l_dom = await audit_link_with_ai("http://click-sovrin-bonus.xyz")
    print("    Link audit resp length:", len(l_resp))
    assert "click-sovrin-bonus.xyz" in l_dom, f"Domain mismatch: {l_dom}"
    assert l_resp and len(l_resp) > 30, f"Link audit response too short: {l_resp}"
    print("    [PASSED] Live Gemini AI Cyber-Mentor, Link Audit, and Username OSINT.")

def run_all():
    print("==================================================")
    print("STARTING KIBERIZ-4 COMPLETE RIGOROUS TEST SUITE")
    print("==================================================")
    test_emojis_and_html()
    test_heic_and_image_parsing()
    test_apk_analysis()
    test_audio_metadata()
    test_document_metadata()
    test_binary_metadata()
    test_quiz_structure()
    test_keyboards_and_menu_matching()
    asyncio.run(test_ai_integration())
    print("==================================================")
    print("ALL TESTS PASSED 100% WITH ZERO ERRORS!")
    print("==================================================")

if __name__ == "__main__":
    run_all()
