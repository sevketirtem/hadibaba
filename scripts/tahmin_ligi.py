"""TAHMİN LİGİ · TAM SKOR! — tam skor bilindiğinde aynı formatta dikey Shorts üretir.

Kullanım: python scripts/tahmin_ligi.py video/tahmin-ligi/<anahtar>.json <çıkış klasörü>
Girdi JSON:
  {"tarih": "tahmin-ligi-1", "seri_no": 1, "mac": "Fenerbahçe - Göztepe", "skor": "1-2", "bilen": "yuru",
   "puan": {"yuru": 3, "hadi": 2}, "replikler": [{"kim": "hadi", "metin": "...", "duygu": "uzgun"}, ...],
   "aciklama": "...", "yt_baslik": "..."}
  İsteğe bağlı (sonuç bilindiğinde): "etiket": "SONUÇ BİLDİ!", "kart_ust": "YÜRÜ 1-1 DEDİ · BERABERLİK BİLDİ", "puan_etiket": "+1 PUAN"
Ses: Gemini TTS (podcast_ses: yönetmen notu, Hadi coşkulu / Yürü alaycı). Görüntü: hareketli avatarlar + skor kartı.
Çıktı: <klasör>/dikey.mp4 ve sade.mp4 (TikTok taslağı için aynı video).
"""
import array, json, math, os, shutil, subprocess, sys, tempfile, textwrap
from concurrent.futures import ThreadPoolExecutor
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import podcast_ses  # noqa: E402
from hareketli_avatar import HareketliAvatar  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = os.path.join(KOK, "assets", "kart", "ArchivoBlack.ttf")
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W, H, FPS = 1080, 1920, 24
TURUNCU, LACI, SARI = (226, 88, 44), (30, 46, 82), (255, 204, 64)
AD = {"hadi": "HADİ", "yuru": "YÜRÜ"}
RENK = {"hadi": TURUNCU, "yuru": (52, 88, 140)}


def f(boy, yol=FONT):
    return ImageFont.truetype(yol, boy)


def ses_uret(bilgi, klasor):
    model = podcast_ses.tts_modeli()
    wavlar = [os.path.join(klasor, f"r{i:02d}.wav") for i in range(len(bilgi["replikler"]))]
    with ThreadPoolExecutor(4) as ex:
        list(ex.map(lambda a: podcast_ses._tek_replik(model, *a), zip(bilgi["replikler"], wavlar)))
    ses = os.path.join(klasor, "ses.mp3")
    podcast_ses.birlestir(wavlar, bilgi, ses, f"Gemini {model}")
    return ses, json.load(open(ses + ".zaman.json", encoding="utf-8"))


def arka_plan():
    im = Image.new("RGB", (W, H), LACI)
    d = ImageDraw.Draw(im)
    for y in range(H):  # üstten laciverte, alttan koyuya
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(30 - 12 * k), int(46 - 20 * k), int(82 - 34 * k)))
    isik = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    di = ImageDraw.Draw(isik)
    for x, r in ((150, 260), (930, 260)):  # stadyum ışığı gibi iki parıltı (logo/arma yok)
        di.ellipse([x - r, -r, x + r, r], fill=(255, 240, 200, 60))
    isik = isik.filter(ImageFilter.GaussianBlur(90))
    im = Image.alpha_composite(im.convert("RGBA"), isik)
    return im


def zarf_hesapla(ses, n):
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", ses, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    orn = array.array("h", ham)
    adim = 16000 // FPS
    z = [(sum(x * x for x in orn[k:k + adim:8]) / max(1, len(orn[k:k + adim:8]))) ** 0.5 for k in range(0, len(orn), adim)]
    tepe = sorted(z)[int(len(z) * 0.95)] if z else 1
    return [min(1.0, v / (tepe or 1)) for v in z] + [0.0] * n


def render(bilgi, ses, zaman, cikti):
    ha = HareketliAvatar(taban=420)
    sure = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", ses],
                                capture_output=True, text=True).stdout) + 1.2
    n = int(sure * FPS)
    zarf = zarf_hesapla(ses, n)
    bg = arka_plan()
    bilen, kaybeden = bilgi["bilen"], ("hadi" if bilgi["bilen"] == "yuru" else "yuru")
    puan = bilgi["puan"]
    ev, dep = [s.strip() for s in bilgi["mac"].split("-", 1)] if "-" in bilgi["mac"] else (bilgi["mac"], "")
    s1, s2 = bilgi["skor"].split("-")
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", ses, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
                           "-af", "apad", "-t", f"{sure:.2f}", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    halka = {}

    def cerceve(boy, aktif):
        k = (boy, aktif)
        if k not in halka:
            c = Image.new("RGBA", (boy + 120, boy + 120), (0, 0, 0, 0))
            dc = ImageDraw.Draw(c)
            if aktif:
                dc.ellipse([30, 30, boy + 90, boy + 90], fill=SARI + (150,))
                c = c.filter(ImageFilter.GaussianBlur(20))
                dc = ImageDraw.Draw(c)
            dc.ellipse([46, 46, boy + 74, boy + 74], fill=SARI + (255,) if aktif else (235, 235, 240, 255))
            halka[k] = c
        return halka[k]

    yum = 0.0
    for i in range(n):
        t = i / FPS
        yum = yum * 0.6 + zarf[i] * 0.4
        aktif = next((z for z in zaman if z["bas"] - 0.15 <= t <= z["son"] + 0.2), None)
        im = bg.copy()
        d = ImageDraw.Draw(im)
        # Başlık rozeti
        d.rounded_rectangle([290, 70, 790, 140], 35, fill=TURUNCU)
        d.text((W // 2, 105), f"TAHMİN LİGİ · #{bilgi.get('seri_no', 1)}", font=f(40), fill="white", anchor="mm")
        # TAM SKOR! — ilk 1 sn büyüyerek gelir, sonra hafif nabız
        olc = min(1.0, t / 0.6) * (1 + 0.04 * (1 + math.sin(t * 6)))
        etiket = bilgi.get("etiket", "TAM SKOR!")
        fs = max(10, int(118 * min(1.0, 9 / max(9, len(etiket))) * olc))
        d.text((W // 2, 235), etiket, font=f(fs), fill=SARI, anchor="mm", stroke_width=6, stroke_fill=(20, 24, 40))
        # Skor kartı
        d.rounded_rectangle([90, 330, 990, 560], 30, fill=(255, 255, 255))
        d.text((W // 2, 375), bilgi.get("kart_ust", f"{AD[bilen]} BİLDİ"), font=f(34), fill=RENK[bilen], anchor="mm")
        d.text((250, 470), ev, font=f(44 if len(ev) < 12 else 34), fill=LACI, anchor="mm")
        d.text((830, 470), dep, font=f(44 if len(dep) < 12 else 34), fill=LACI, anchor="mm")
        d.text((W // 2, 470), f"{s1}-{s2}", font=f(96), fill=TURUNCU, anchor="mm")
        # Avatarlar: bilen solda büyük
        for kim, cx, cy, taban in ((bilen, 330, 860, 400), (kaybeden, 790, 900, 300)):
            konusan = aktif is not None and aktif["kim"] == kim
            boy = int(taban * ((0.98 + 0.06 * yum) if konusan else 0.86))
            c = cerceve(boy, konusan)
            im.alpha_composite(c, (cx - c.width // 2, cy - c.height // 2))
            duygu = (aktif.get("duygu") if konusan else None) or ("sevinc" if kim == bilen else "uzgun")
            yuz = ha.kare(kim, konusan, t, boy, duygu) if ha.var else None
            if yuz is not None:
                im.alpha_composite(yuz, (cx - boy // 2, cy - boy // 2))
            if kim == bilen:
                d.text((cx, cy - boy // 2 - 50), bilgi.get("puan_etiket", "+3 PUAN"), font=f(40), fill=SARI, anchor="mm",
                       stroke_width=4, stroke_fill=(20, 24, 40))
        # Altyazı
        if aktif is not None:
            d.rounded_rectangle([W // 2 - 90, 1150, W // 2 + 90, 1200], 24, fill=RENK[aktif["kim"]])
            d.text((W // 2, 1175), AD[aktif["kim"]], font=f(32), fill="white", anchor="mm")
            sat = textwrap.wrap(aktif["metin"], 30)[:4]
            d.multiline_text((W // 2, 1222), "\n".join(sat), font=f(50, BOLD), fill="white", anchor="ma", align="center",
                             stroke_width=5, stroke_fill=(15, 18, 30), spacing=10)
        # Puan durumu (çubuklar büyüyerek)
        d.text((W // 2, 1560), "PUAN DURUMU", font=f(36), fill=(220, 225, 235), anchor="mm")
        enc = max(puan.values()) or 1
        buy = min(1.0, max(0.0, (t - 1.0) / 1.5))
        for j, kim in enumerate(sorted(puan, key=lambda k: -puan[k])):
            y = 1610 + j * 80
            d.text((120, y + 30), AD[kim], font=f(38), fill="white", anchor="lm")
            uz = int(560 * puan[kim] / enc * buy)
            d.rounded_rectangle([290, y + 6, 290 + max(40, uz), y + 54], 24, fill=RENK[kim])
            d.text((290 + max(40, uz) + 25, y + 30), str(puan[kim]), font=f(42), fill=SARI, anchor="lm")
        d.text((W // 2, 1850), "hadibaba.com · yurubaba.com", font=f(34, BOLD), fill=(230, 230, 235), anchor="mm")
        ff.stdin.write(im.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg başarısız")


def main():
    bilgi = json.load(open(sys.argv[1], encoding="utf-8"))
    klasor = sys.argv[2]
    os.makedirs(klasor, exist_ok=True)
    tmp = tempfile.mkdtemp()
    ses, zaman = ses_uret(bilgi, tmp)
    try:  # başta kısa dombra tıngırtısı (marka sesi)
        import dombra
        dombra.bindir("sting", ses)
    except Exception as e:  # noqa: BLE001
        print(f"::warning title=Dombra::{e}")
    dikey = os.path.join(klasor, "dikey.mp4")
    render(bilgi, ses, zaman, dikey)
    shutil.copy(dikey, os.path.join(klasor, "sade.mp4"))
    print(f"::notice title=Tahmin Ligi::{bilgi['tarih']} · {os.path.getsize(dikey) // 1024} KB, {zaman[-1]['son']:.1f} sn", flush=True)


if __name__ == "__main__":
    main()
