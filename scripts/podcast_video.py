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


def arka_plan(senaryo, hadi, yuru, cikti, avatarsiz=False):
    im = Image.new("RGB", (W, H), LACIVERT)
    d = ImageDraw.Draw(im)
    d.polygon([(0, 0), (W // 2 + 120, 0), (W // 2 - 120, H), (0, H)], fill=TURUNCU)
    for k in range(10):  # Yürü tarafında soluk sütunlar
        h = 120 + (k * 131) % 380
        x = 1180 + k * 70
        d.rectangle([x, 860 - h, x + 44, 860], fill=(44, 68, 108))
    r = 300
    for yol, cx in (() if avatarsiz else ((hadi, 520), (yuru, 1400))):
        cy = 520
        d.ellipse([cx - r - 14, cy - r - 14, cx + r + 14, cy + r + 14], fill="white")
        a, m = daire(yol, r)
        im.paste(a, (cx - r, cy - r), m)
    f1 = ImageFont.truetype(FONT, 46)
    f2 = ImageFont.truetype(FONT, 34)
    d.text((W // 2, 70), "HADİ vs YÜRÜ", font=f1, fill="white", anchor="mm", stroke_width=4, stroke_fill=(20, 20, 30))
    baslik = "\n".join(textwrap.wrap(senaryo["baslik"], 70 if avatarsiz else 60))
    d.multiline_text((W // 2, 112 if avatarsiz else 948), baslik, font=f2, fill="white", anchor="ma", align="center",
                     stroke_width=3, stroke_fill=(20, 20, 30), spacing=10)
    d.text((W - 40, H - 30), "hadibaba.com · yurubaba.com", font=ImageFont.truetype(FONT, 24),
           fill=(255, 217, 204), anchor="rs")
    im.save(cikti)


def hareketli(senaryo, ses, cikti, bg_yol, zaman):
    """Konuşan karakterin yüzü hareket eder (assets/avatar klipleri), altta o anki replik yazılır."""
    import array
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from hareketli_avatar import HareketliAvatar
    ha = HareketliAvatar(taban=560)
    if not ha.var:
        return False
    FPS = 24
    sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ses],
                                capture_output=True, text=True).stdout.strip())
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", ses, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    orn = array.array("h", ham)
    adim = 16000 // FPS
    zarf = [(sum(x * x for x in orn[k:k + adim:8]) / max(1, len(orn[k:k + adim:8]))) ** 0.5 for k in range(0, len(orn), adim)]
    tepe = sorted(zarf)[int(len(zarf) * 0.95)] or 1
    zarf = [min(1.0, z / tepe) for z in zarf]
    bg = Image.open(bg_yol).convert("RGB")
    f_alt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
    f_ad = ImageFont.truetype(FONT, 30)
    halka = {}

    def cerceve(boy, aktif):
        k = (boy, aktif)
        if k not in halka:
            from PIL import ImageFilter
            c = Image.new("RGBA", (boy + 120, boy + 120), (0, 0, 0, 0))
            dc = ImageDraw.Draw(c)
            if aktif:
                dc.ellipse([30, 30, boy + 90, boy + 90], fill=(255, 204, 64, 150))
                c = c.filter(ImageFilter.GaussianBlur(20))
                dc = ImageDraw.Draw(c)
            dc.ellipse([46, 46, boy + 74, boy + 74], fill=(255, 204, 64, 255) if aktif else (235, 235, 240, 255))
            halka[k] = c
        return halka[k]

    n = int(sure * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", ses, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                           "-shortest", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    yumusak = 0.0
    for i in range(n):
        t = i / FPS
        yumusak = yumusak * 0.6 + (zarf[i] if i < len(zarf) else 0) * 0.4
        aktif = next((z for z in zaman if z["bas"] - 0.15 <= t <= z["son"] + 0.2), None)
        im = bg.copy().convert("RGBA")
        for kim, cx in (("hadi", 520), ("yuru", 1400)):
            konusan = aktif is not None and aktif["kim"] == kim
            boy = int(520 * ((0.97 + 0.06 * yumusak) if konusan else 0.84))
            c = cerceve(boy, konusan)
            im.alpha_composite(c, (cx - c.width // 2, 500 - c.height // 2))
            yuz = ha.kare(kim, konusan, t, boy, aktif.get("duygu") if konusan else None)
            if not konusan:
                koyu = Image.new("RGBA", yuz.size, (17, 22, 34, 90))
                koyu.putalpha(Image.eval(yuz.getchannel("A"), lambda v: v * 90 // 255))
                yuz = Image.alpha_composite(yuz, koyu)
            im.alpha_composite(yuz, (cx - boy // 2, 500 - boy // 2))
        d = ImageDraw.Draw(im)
        if aktif is not None:
            ad = "HADİ" if aktif["kim"] == "hadi" else "YÜRÜ"
            renk = TURUNCU if aktif["kim"] == "hadi" else (52, 88, 140)
            d.rounded_rectangle([W // 2 - 90, 790, W // 2 + 90, 836], 22, fill=renk)
            d.text((W // 2, 813), ad, font=f_ad, fill="white", anchor="mm")
            sat = textwrap.wrap(aktif["metin"], 70)[:2]
            d.multiline_text((W // 2, 850), "\n".join(sat), font=f_alt, fill="white", anchor="ma", align="center",
                             stroke_width=4, stroke_fill=(15, 18, 30), spacing=8)
        ff.stdin.write(im.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg başarısız")
    return True


def main():
    senaryo = json.load(open(sys.argv[1], encoding="utf-8"))
    ses, cikti = sys.argv[2], sys.argv[3]
    hadi = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else os.path.join(KOK, "assets/kart/ref-hadi.png")
    yuru = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else os.path.join(KOK, "assets/kart/ref-yuru.png")
    bg = os.path.join(tempfile.mkdtemp(), "bg.png")
    zaman_yol = ses + ".zaman.json"
    if os.path.exists(zaman_yol) and os.environ.get("PODCAST_DURAN") != "1":
        try:
            arka_plan(senaryo, hadi, yuru, bg, avatarsiz=True)
            # Başlık altyazıyla çakışmasın: hareketli sürümde başlık üstte
            if hareketli(senaryo, ses, cikti, bg, json.load(open(zaman_yol, encoding="utf-8"))):
                print(f"::notice title=Podcast videosu::{os.path.basename(cikti)} {os.path.getsize(cikti) // 1024} KB (hareketli)", flush=True)
                return
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Podcast videosu::hareketli olmadı, duran sürüm: {e}", flush=True)
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
