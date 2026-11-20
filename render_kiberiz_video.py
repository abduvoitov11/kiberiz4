#!/usr/bin/env python3
"""
KiberIz-4 Official Vertical Promo Video Generator (9:16 - 1080x1920)
Features:
- Dynamic pacing (2.3s per scene, continuous smooth zoom/push-in motion)
- Zero tofu boxes / zero emojis: clean, crisp typography
- Cyber-themed background styling
- Simple, minimalist outro (no garish colors)
- Synced cyber bass soundtrack (INSTINCT.404) & Corporate variant
"""

import os
import sys
import subprocess
import shutil

WORKDIR = "/home/torabek/KiberIz4"
OUTDIR = "/home/torabek/Videos"
TEMPDIR = "/tmp/kiberiz_render"
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
MUSIC_CYBER = "/home/torabek/Downloads/Telegram Desktop/INSTINCT.404 (Slowed)   nightfxrce.m4a"
MUSIC_CORP = "/tmp/upbeat_corporate.mp3"

# Scene definitions: (image_path, duration, caption, is_fullscreen_or_card)
SCENES = [
    # 1. Hook
    ("/tmp/kiberiz_slides/slide-01.png", 2.3, "Internet hech narsani unutmaydi!", "card"),
    # 2. Problem
    ("/tmp/kiberiz_slides/slide-02.png", 2.3, "Har bir post raqamli iz qoldiradi", "card"),
    # 3. OSINT
    ("/tmp/kiberiz_slides/slide-03.png", 2.3, "Bitta fotosurat nimalarni fosh qiladi?", "card"),
    # 4. School & class leaked
    ("/tmp/kiberiz_slides/slide-04.png", 2.3, "Maktab va sinf 1 daqiqada aniqlanadi", "card"),
    # 5. Home location leaked
    ("/tmp/kiberiz_slides/slide-05.png", 2.3, "Yashirin GPS va aniq uy manzili", "card"),
    # 6. Real GPS sample
    ("/home/torabek/KiberIz4/bot/sample_gps_school4.jpg", 2.3, "EXIF orqali geolokatsiya auditi", "photo"),
    # 7. Radar Web
    ("/tmp/kiber_radar.png", 2.3, "Fishing va soxta havolalar radari", "web"),
    # 8. Solution
    ("/tmp/kiberiz_slides/slide-07.png", 2.3, "Yechim: KiberIz-4 Ekotizimi", "card"),
    # 9. Bot features
    ("/tmp/kiberiz_slides/slide-08.png", 2.3, "Aqlli Telegram Bot: @kiberiz_bot", "card"),
    # 10. Checklist
    ("/tmp/kiberiz_slides/slide-09.png", 2.3, "5 daqiqada profilingizni himoyalang", "card"),
    # 11. Results
    ("/tmp/kiberiz_slides/slide-11.png", 2.3, "Xavfsiz profil — xavfsiz kelajak", "card"),
]

def run_cmd(cmd, check=True):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if check and res.returncode != 0:
        print(f"Error: {' '.join(cmd)}", file=sys.stderr)
        print(res.stderr, file=sys.stderr)
        sys.exit(1)
    return res

def prepare_dirs():
    os.makedirs(TEMPDIR, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

def render_segment(index, img_path, duration, caption, style):
    out_file = os.path.join(TEMPDIR, f"seg_{index:02d}.mp4")
    esc_caption = caption.replace(":", "\\:").replace("'", "\\'")

    drawtext = (
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{esc_caption}':"
        f"fontcolor=white:"
        f"fontsize=44:"
        f"box=1:boxcolor=black@0.75:boxborderw=22:"
        f"x=(w-text_w)/2:y=h*0.84"
    )

    if style == "card":
        # 16:9 slide on blurred cyber background with slow zoompan push-in
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.35[bg];"
            f"[0:v]scale=1040:-2,zoompan=z='min(zoom+0.0006,1.05)':d=70:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1040x585:fps=30[card];"
            f"[bg][card]overlay=(W-w)/2:(H-h)/2-40,{drawtext},fps=30[v]"
        )
    elif style == "photo":
        # Real photo full-bleed with zoompan
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:5,eq=brightness=-0.25[bg];"
            f"[0:v]scale=960:-2,zoompan=z='min(zoom+0.0008,1.06)':d=70:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=960x720:fps=30[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2-40,{drawtext},fps=30[v]"
        )
    else: # web
        filter_complex = (
            f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,zoompan=z='min(zoom+0.0006,1.05)':d=70:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30,{drawtext},fps=30[v]"
        )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", img_path,
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        out_file
    ]
    print(f"[{index+1}/{len(SCENES)+1}] Rendering {os.path.basename(img_path)} ({duration}s)...")
    run_cmd(cmd)
    return out_file

def render_outro_segment(index):
    """Clean, minimalist, high-end outro on the cyber shield art."""
    art_path = os.path.join(WORKDIR, "assets/kiberiz_art.jpg")
    out_file = os.path.join(TEMPDIR, f"seg_{index:02d}.mp4")
    duration = 3.2

    drawtexts = [
        f"drawtext=fontfile='{FONT_PATH}':text='KIBERIZ-4':fontcolor=white:fontsize=84:x=(w-text_w)/2:y=(h-text_h)/2-120",
        f"drawtext=fontfile='{FONT_PATH}':text='O\\‘z raqamli izingni boshqar!':fontcolor=white:fontsize=46:x=(w-text_w)/2:y=(h-text_h)/2-20",
        f"drawtext=fontfile='{FONT_PATH}':text='Telegram\\: @kiberiz_bot':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.7:boxborderw=18:x=(w-text_w)/2:y=(h-text_h)/2+70",
        "fade=t=out:st=2.4:d=0.8"
    ]
    vf_str = ",".join(drawtexts)

    filter_complex = (
        f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:5,eq=brightness=-0.4[bg];"
        f"[bg]{vf_str},fps=30[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", art_path,
        "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        out_file
    ]
    print(f"[{index+1}/{len(SCENES)+1}] Rendering minimalist outro ({duration}s)...")
    run_cmd(cmd)
    return out_file

def mix_music(raw_video, music_path, out_path, total_dur, vol=1.05):
    fade_out_st = total_dur - 1.8
    filter_complex = (
        f"[1:a]afade=t=in:st=0:d=0.5,afade=t=out:st={fade_out_st:.2f}:d=1.8,volume={vol}[music]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", raw_video,
        "-ss", "00:00:00",
        "-i", music_path,
        "-filter_complex", filter_complex,
        "-map", "0:v", "-map", "[music]",
        "-t", str(total_dur),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "256k",
        "-movflags", "+faststart",
        out_path
    ]
    run_cmd(cmd)

def main():
    print("=== KiberIz-4 Vertical Promo Video Generation Started ===")
    prepare_dirs()

    segment_files = []
    for idx, (img, dur, caption, style) in enumerate(SCENES):
        seg = os.path.join(TEMPDIR, f"seg_{idx:02d}.mp4")
        if not os.path.exists(seg):
            seg = render_segment(idx, img, dur, caption, style)
        segment_files.append(seg)

    outro = render_outro_segment(len(SCENES))
    segment_files.append(outro)

    concat_list_path = os.path.join(TEMPDIR, "concat.txt")
    with open(concat_list_path, "w") as f:
        for seg in segment_files:
            f.write(f"file '{seg}'\n")

    raw_concat = os.path.join(TEMPDIR, "raw_concat.mp4")
    print("\nConcatenating segments...")
    run_cmd([
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        raw_concat
    ])

    probe_cmd = [
        "ffprobe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        raw_concat
    ]
    total_dur = float(subprocess.check_output(probe_cmd).decode().strip())
    print(f"Total video duration: {total_dur:.2f} seconds.")

    # Primary Render: Cyber Bass (INSTINCT.404)
    out_cyber = os.path.join(OUTDIR, "kiberiz_promo_reels.mp4")
    print(f"\nMixing with Cyber soundtrack: {out_cyber}...")
    mix_music(raw_concat, MUSIC_CYBER, out_cyber, total_dur, vol=1.0)

    # Variant 2: Upbeat Corporate
    out_corp = os.path.join(OUTDIR, "kiberiz_promo_corporate.mp4")
    print(f"Mixing with Corporate soundtrack: {out_corp}...")
    mix_music(raw_concat, MUSIC_CORP, out_corp, total_dur, vol=1.05)

    print("\nSUCCESS! All KiberIz-4 videos created successfully.")

if __name__ == "__main__":
    main()
