"""Podcast bölümünden YouTube videosu (1920x1080): iki karakter sahnesi, başlık, ses dalgası.

Kullanım: python scripts/podcast_video.py <senaryo.json> <ses.mp3> <çıktı.mp4> [hadi_sahne.png] [yuru_sahne.png]
Sahne verilmezse assets/kart/ref-*.png kullanılır.
"""
import json, os, subprocess, sys, tempfile, textwrap
from PIL import Image, ImageDraw, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(KOK, "assets", "kart", "ArchivoBlack.ttf")
W, H = 1920, 1080
TURUNCU, LACIVERT = (229, 87, 48), (30, 50, 84)


def daire(yol, r):
    a = Image.open(yol).convert("RGBA")
    k = min(a.size)
    a = a.crop(((a.width - k) // 2, (a.height - k) // 2, (a.width + k) // 2, (a.height + k) // 2))
    a = a.resize((2 * r, 2 * r), Image.LANCZOS)
    m = Image.new("L", (8 * r, 8 * r), 0)
    ImageDraw.Draw(m).ellipse((0, 0, 8 * r, 8 * r), fill=255)
    return a, m.resize((2 * r, 2 * r), Image.LANCZOS)


def arka_plan(senaryo, hadi, yuru, cikti):
    im = Image.new("RGB", (W, H), LACIVERT)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (W // 2 + 120, 0), (W // 2 - 120, H), (0, H)], fill=TURUNCU)
    for k in range(10):  # Yürü tarafında soluk sütunlar
        h = 120 + (k * 131) % 380
        x = 1180 + k * 70
        d.rectangle([x, 860 - h, x + 44, 860], fill=(44, 68, 108))
    r = 300
    for yol, cx in ((hadi, 520), (yuru, 1400)):
        cy = 520
        d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill="white")
        a, m = daire(yol, r)
        im.paste(a, (cx - r, cy - r), m)
    f1 = ImageFont.truetype(FONT, 46)
    f2 = ImageFont.truetype(FONT, 34)
    d.text((W // 2, 70), "HADİ vs YÜRÜ", font=f1, fill="white", anchor="mm", stroke_width=4, stroke_fill=(20, 20, 30))
    baslik = "\n".join(textwrap.wrap(senaryo["baslik"], 60))
    d.multiline_text((W // 2, 948), baslik, font=f2, fill="white", anchor="ma", align="center",
                     stroke_width=3, stroke_fill=(20, 20, 30), spacing=10)
    d.text((W - 40, H - 30), "hadibaba.com · yurubaba.com", font=ImageFont.truetype(FONT, 24),
           fill=(255, 217, 204), anchor="rs")
    im.save(cikti)


def main():
    senaryo = json.load(open(sys.argv[1], encoding="utf-8"))
    ses, cikti = sys.argv[2], sys.argv[3]
    hadi = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else os.path.join(KOK, "assets/kart/ref-hadi.png")
    yuru = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else os.path.join(KOK, "assets/kart/ref-yuru.png")
    bg = os.path.join(tempfile.mkdtemp(), "bg.png")
    arka_plan(senaryo, hadi, yuru, bg)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-i", bg, "-i", ses,
        "-filter_complex",
        "[1:a]showwaves=s=1400x80:mode=cline:rate=25:colors=white@0.85[w];[0:v][w]overlay=260:852:shortest=1,format=yuv420p[v]",
        "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-tune", "stillimage", "-crf", "26",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", cikti], check=True)
    print(f"::notice title=Podcast videosu::{os.path.basename(cikti)} {os.path.getsize(cikti) // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
