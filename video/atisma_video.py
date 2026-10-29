"""Hadi vs Yürü atışma videosu.

Kullanım: python3 video/atisma_video.py video/senaryolar/2026-10-29.json cikti.mp4
Dikey 1080x1920, 30 fps; kendi avatarlarımız + konuşma balonları + seslendirme
(GOOGLE_TTS_KEY varsa Google Cloud Text-to-Speech; yoksa yalnızca efekt sesleri).
"""
import json, math, subprocess, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
KOK = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(KOK)
FONT_BASLIK = f"{REPO}/assets/kart/ArchivoBlack.ttf"
FONT_METIN = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

RENK = {
    "zemin": (17, 22, 34), "zemin2": (28, 36, 54),
    "hadi": (232, 90, 44), "hadi_acik": (255, 217, 204),
    "yuru": (31, 58, 96), "yuru_acik": (184, 203, 227),
    "beyaz": (250, 248, 244), "gri": (150, 160, 178), "sari": (255, 204, 64),
}


def font(yol, boy):
    return ImageFont.truetype(yol, boy)


def ease_out_back(t):
    c1, c3 = 1.70158, 2.70158
    t = min(max(t, 0), 1)
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2


def ease_out(t):
    t = min(max(t, 0), 1)
    return 1 - (1 - t) ** 3


def daire_avatar(yol, boy):
    im = Image.open(yol).convert("RGBA").resize((boy, boy), Image.LANCZOS)
    maske = Image.new("L", (boy, boy), 0)
    ImageDraw.Draw(maske).ellipse((0, 0, boy - 1, boy - 1), fill=255)
    im.putalpha(maske)
    return im


def satirla(metin, f, genislik, d):
    kelimeler, satirlar, sat = metin.split(), [], ""
    for k in kelimeler:
        dene = (sat + " " + k).strip()
        if d.textlength(dene, font=f) <= genislik:
            sat = dene
        else:
            satirlar.append(sat)
            sat = k
    if sat:
        satirlar.append(sat)
    return satirlar


class Video:
    def __init__(self, s):
        self.s = s
        self.av = {
            "hadi": daire_avatar(f"{KOK}/hadi.png", 170),
            "yuru": daire_avatar(f"{KOK}/yuru.png", 170),
        }
        self.av_buyuk = {
            "hadi": daire_avatar(f"{KOK}/hadi.png", 330),
            "yuru": daire_avatar(f"{KOK}/yuru.png", 330),
        }
        self.f_mesaj = font(FONT_METIN, 50)
        self.f_ad = font(FONT_BASLIK, 34)
        self.f_bas = font(FONT_BASLIK, 92)
        self.f_alt = font(FONT_METIN, 42)
        self.f_kucuk = font(FONT_METIN, 36)
        self.zemin = self._zemin()
        olcu = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        self.mesajlar = []
        for m in s["mesajlar"]:
            sat = satirla(m["metin"], self.f_mesaj, 640, olcu)
            yuk = 60 + len(sat) * 64 + 50
            self.mesajlar.append({**m, "satirlar": sat, "yuk": yuk})

    def _zemin(self):
        z = Image.new("RGB", (W, H), RENK["zemin"])
        d = ImageDraw.Draw(z)
        # Hadi ışınları (sol üst) ve Yürü ızgarası (sağ alt), soluk
        for i in range(18):
            a = math.radians(i * 20)
            d.polygon([(0, 0), (1600 * math.cos(a), 1600 * math.sin(a)),
                       (1600 * math.cos(a + 0.17), 1600 * math.sin(a + 0.17))],
                      fill=(40, 30, 34))
        for x in range(0, W, 60):
            d.line([(x, 1150), (x, H)], fill=(24, 32, 50), width=2)
        for y in range(1150, H, 60):
            d.line([(0, y), (W, y)], fill=(24, 32, 50), width=2)
        return z.filter(ImageFilter.GaussianBlur(1))

    # ---- sahneler ----
    def kare(self, t):
        im = self.zemin.copy()
        d = ImageDraw.Draw(im, "RGBA")
        bitis = self.s["bitis_karti"]["bas"]
        if t < 2.0:
            self.giris(im, d, t)
        elif t < bitis:
            self.sohbet(im, d, t)
            self.baslik(d, 1.0)
            self.alt_bant(d)
        else:
            self.bitis(im, d, t - bitis)
        return im

    def ortala(self, d, y, metin, f, renk):
        w = d.textlength(metin, font=f)
        d.text(((W - w) / 2, y), metin, font=f, fill=renk)

    def giris(self, im, d, t):
        k = ease_out_back(t / 0.6)
        for kim, x0, gecikme in (("hadi", 80, 0.0), ("yuru", 670, 0.25)):
            p = ease_out_back((t - gecikme) / 0.6)
            if p <= 0:
                continue
            boy = max(1, int(330 * p))
            a = self.av_buyuk[kim].resize((boy, boy), Image.LANCZOS)
            im.paste(a, (x0 + (330 - boy) // 2, 620 + (330 - boy) // 2), a)
        if t > 0.5:
            p = ease_out_back((t - 0.5) / 0.5)
            f = font(FONT_BASLIK, max(10, int(140 * p)))
            self.ortala(d, 740 - 70 * p, "VS", f, RENK["sari"])
        if t > 0.8:
            a = int(255 * ease_out((t - 0.8) / 0.5))
            self.ortala(d, 1030, "HADİ BABA", self.f_bas, RENK["hadi"] + (a,))
            self.ortala(d, 1140, "YÜRÜ BABA", self.f_bas, RENK["yuru_acik"] + (a,))
            self.ortala(d, 1290, self.s["mac"], self.f_alt, RENK["beyaz"] + (a,))
            self.ortala(d, 1350, self.s["mac_alt"], self.f_kucuk, RENK["gri"] + (a,))

    def baslik(self, d, a):
        d.rectangle((0, 0, W, 260), fill=(10, 13, 22, 255))
        d.rectangle((0, 252, W // 2, 260), fill=RENK["hadi"])
        d.rectangle((W // 2, 252, W, 260), fill=RENK["yuru_acik"])
        self.ortala(d, 70, self.s["mac"], font(FONT_BASLIK, 62), RENK["beyaz"])
        self.ortala(d, 160, self.s["mac_alt"], self.f_kucuk, RENK["gri"])

    def sohbet(self, im, d, t):
        gorunen = [m for m in self.mesajlar if t >= m["bas"]]
        if not gorunen:
            return
        # aşağıdan yukarı yerleşim: en yeni en altta
        alt = 1600
        konumlar = []
        y = alt
        for m in reversed(gorunen):
            y -= m["yuk"] + 40
            konumlar.append((m, y))
        # kaydırma animasyonu: yeni mesaj gelince eskiler yukarı kayar
        son = gorunen[-1]
        kay = (1 - ease_out((t - son["bas"]) / 0.35)) * (son["yuk"] + 40)
        for m, y in konumlar:
            yy = y + kay
            if m is son:
                yy = y
            if yy + m["yuk"] < 270:
                continue
            self.balon(im, d, m, yy, t)

    def balon(self, im, d, m, y, t):
        hadi = m["kim"] == "hadi"
        yas = t - m["bas"]
        p = ease_out_back(yas / 0.4)
        renk = RENK["hadi"] if hadi else RENK["yuru"]
        cerceve = RENK["hadi_acik"] if hadi else RENK["yuru_acik"]
        bw = 700
        bx = 230 if hadi else W - 230 - bw
        ax = 40 if hadi else W - 40 - 170
        # konuşurken avatar zıplar (Hadi) / hafif sallanır (Yürü)
        konusuyor = yas < m.get("sure", 3.6)
        dy = 0
        if konusuyor:
            dy = -abs(math.sin(yas * 9)) * 18 if hadi else math.sin(yas * 4) * 6
        av = self.av[m["kim"]]
        if p < 1:
            boy = max(1, int(170 * min(1, p)))
            av = av.resize((boy, boy), Image.LANCZOS)
        im.paste(av, (ax + (170 - av.width) // 2, int(y + dy)), av)
        if yas < 0.08:
            return
        # balon (ölçekli giriş)
        s = min(1.05, max(0.01, p))
        cx = bx if hadi else bx + bw
        x0 = cx + (bx - cx) * s
        x1 = cx + (bx + bw - cx) * s
        y1 = y + m["yuk"] * s
        d.rounded_rectangle((x0, y, x1, y1), radius=38, fill=renk + (245,),
                            outline=cerceve, width=4)
        kuy = [(bx, y + 40), (bx - 34, y + 70), (bx, y + 95)] if hadi else \
              [(bx + bw, y + 40), (bx + bw + 34, y + 70), (bx + bw, y + 95)]
        d.polygon(kuy, fill=renk)
        if s < 0.95:
            return
        ad = "HADİ" if hadi else "YÜRÜ"
        d.text((bx + 36, y + 22), ad, font=self.f_ad, fill=cerceve)
        # daktilo efekti
        toplam = sum(len(x) for x in m["satirlar"])
        yazma = max(1.1, min(2.4, m.get("sure", 1.5) * 0.7))
        gorunur = int(toplam * min(1, (yas - 0.3) / yazma)) if yas > 0.3 else 0
        kalan = gorunur
        for i, sat in enumerate(m["satirlar"]):
            parca = sat[:max(0, kalan)]
            kalan -= len(sat)
            d.text((bx + 36, y + 76 + i * 64), parca, font=self.f_mesaj, fill=RENK["beyaz"])

    def alt_bant(self, d):
        d.rectangle((0, 1680, W, H), fill=(10, 13, 22, 235))
        self.ortala(d, 1720, self.s["tablo"], self.f_alt, RENK["sari"])
        self.ortala(d, 1790, "hadibaba.com  ·  yurubaba.com", self.f_kucuk, RENK["gri"])

    def bitis(self, im, d, t):
        b = self.s["bitis_karti"]
        a = int(255 * ease_out(t / 0.4))
        self.ortala(d, 300, b.get("baslik", "TAHMİNLER"), font(FONT_BASLIK, 100), RENK["sari"] + (a,))
        self.ortala(d, 430, self.s["mac"], self.f_alt, RENK["beyaz"] + (a,))
        for i, (kim, skor, gecikme) in enumerate((("hadi", b["hadi"], 0.2), ("yuru", b["yuru"], 0.45))):
            p = ease_out_back((t - gecikme) / 0.5)
            if p <= 0:
                continue
            x = 120 if i == 0 else 600
            boy = max(1, int(330 * min(p, 1.05)))
            av = self.av_buyuk[kim].resize((boy, boy), Image.LANCZOS)
            im.paste(av, (x + (330 - boy) // 2, 560 + (330 - boy) // 2), av)
            f = font(FONT_BASLIK, 130)
            w = d.textlength(skor, font=f)
            renk = RENK["hadi"] if kim == "hadi" else RENK["yuru_acik"]
            d.text((x + 165 - w / 2, 930), skor, font=f, fill=renk)
            ad = "HADİ" if kim == "hadi" else "YÜRÜ"
            w = d.textlength(ad, font=self.f_ad)
            d.text((x + 165 - w / 2, 1100), ad, font=self.f_ad, fill=RENK["gri"])
            soz = b.get(f"{kim}_soz")
            soz_bas = next((z["bas"] for z in b.get("sozler", []) if z["kim"] == kim), None)
            mutlak = t + b["bas"]
            if soz and (soz_bas is None and t > 1.0 or soz_bas is not None and mutlak >= soz_bas):
                f = self.f_kucuk
                w = d.textlength(f"“{soz}”", font=f)
                d.text((x + 165 - w / 2, 1150), f"“{soz}”", font=f, fill=renk)
        if t > 0.9:
            p = ease_out_back((t - 0.9) / 0.5)
            f = font(FONT_BASLIK, max(10, int(84 * p)))
            self.ortala(d, 1270, b.get("soru", "SEN NE DİYORSUN?"), f, RENK["beyaz"])
        if t > 1.3:
            aa = int(255 * ease_out((t - 1.3) / 0.4))
            self.ortala(d, 1420, b.get("alt", "Skor tahminini yoruma yaz"), self.f_alt, RENK["gri"] + (aa,))
            self.ortala(d, 1600, self.s["tablo"], self.f_alt, RENK["sari"] + (aa,))
            self.ortala(d, 1680, "hadibaba.com  ·  yurubaba.com", self.f_kucuk, RENK["gri"] + (aa,))


def efektler(s, sure, cikti):
    """Sentetik efekt sesleri: giriş 'whoosh', her mesajda 'pop', bitişte 'ding'."""
    girdiler, filtreler = [], []
    pop_h = "aevalsrc='0.35*sin(2*PI*(500+900*t)*t)*exp(-14*t)':d=0.25:s=44100"
    pop_y = "aevalsrc='0.35*sin(2*PI*(320+200*t)*t)*exp(-12*t)':d=0.3:s=44100"
    woosh = "anoisesrc=d=0.7:c=pink:a=0.2:r=44100,afade=t=in:d=0.3,afade=t=out:st=0.35:d=0.35,lowpass=f=1800"
    ding = "aevalsrc='0.3*(sin(2*PI*880*t)+0.6*sin(2*PI*1320*t))*exp(-3*t)':d=1.2:s=44100"
    olaylar = [(woosh, 0.0), (ding, 0.5)]
    for m in s["mesajlar"]:
        olaylar.append((pop_h if m["kim"] == "hadi" else pop_y, m["bas"] + 0.05))
    olaylar.append((woosh, s["bitis_karti"]["bas"]))
    olaylar.append((ding, s["bitis_karti"]["bas"] + 0.9))
    for m in s["mesajlar"]:
        if m.get("ses_dosyasi"):
            olaylar.append((m["ses_dosyasi"], m["bas"] + 0.35))
    for z in s["bitis_karti"].get("sozler", []):
        olaylar.append((z["dosya"], z["bas"]))
    for i, (kaynak, bas) in enumerate(olaylar):
        if kaynak.startswith("/") or kaynak.endswith((".mp3", ".wav")):
            girdiler += ["-i", kaynak]
        else:
            girdiler += ["-f", "lavfi", "-i", kaynak]
        ms = int(bas * 1000)
        filtreler.append(f"[{i}]aresample=44100,aformat=channel_layouts=stereo,adelay={ms}|{ms}[a{i}]")
    karis = "".join(f"[a{i}]" for i in range(len(olaylar)))
    filtre = ";".join(filtreler) + f";{karis}amix=inputs={len(olaylar)}:normalize=0,alimiter=limit=0.95,apad,atrim=0:{sure}[out]"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *girdiler, "-filter_complex", filtre,
                    "-map", "[out]", "-c:a", "aac", "-b:a", "160k", "-ar", "44100", cikti], check=True)


def sure_olc(dosya):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dosya],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def zamanla(s, klasor):
    """Mesajları seslendirir (anahtar varsa) ve başlangıç sürelerini ses uzunluğuna göre hesaplar."""
    import seslendir
    t = 2.2
    for i, m in enumerate(s["mesajlar"]):
        m["bas"] = t
        dosya = seslendir.seslendir(m.get("ses") or m["metin"], m["kim"], f"{klasor}/m{i}.mp3")
        if dosya:
            m["ses_dosyasi"] = dosya
            uzunluk = sure_olc(dosya)
            m["sure"] = uzunluk + 0.35
            t += max(3.2, uzunluk + 0.9)
        else:
            t += 4.0
    b = s["bitis_karti"]
    b["bas"] = t + 0.1
    # Bitiş kartında imza sözleri: önce Hadi, sonra Yürü
    b.setdefault("hadi_soz", "Yaparız baba!")
    b.setdefault("yuru_soz", "Görürüz baba.")
    son = b["bas"] + 1.6
    b["sozler"] = []
    for kim in ("hadi", "yuru"):
        dosya = seslendir.seslendir(b[f"{kim}_soz"], kim, f"{klasor}/soz_{kim}.mp3")
        if dosya:
            b["sozler"].append({"kim": kim, "bas": son, "dosya": dosya})
            son += sure_olc(dosya) + 0.35
    s["sure"] = round(max(b["bas"] + 4.2, son + 1.2), 2)
    return s


def main():
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    cikti = sys.argv[2]
    klasor = cikti + ".parcalar"
    os.makedirs(klasor, exist_ok=True)
    sys.path.insert(0, KOK)
    s = zamanla(s, klasor)
    sure = s["sure"]
    v = Video(s)
    sessiz = cikti + ".video.mp4"
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                          "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264",
                          "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", sessiz],
                         stdin=subprocess.PIPE)
    for i in range(int(sure * FPS)):
        p.stdin.write(v.kare(i / FPS).tobytes())
    p.stdin.close()
    p.wait()
    sesdosya = cikti + ".ses.m4a"
    efektler(s, sure, sesdosya)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", sessiz, "-i", sesdosya, "-c:v", "copy",
                    "-c:a", "copy", "-shortest", "-movflags", "+faststart", cikti], check=True)
    os.remove(sessiz)
    os.remove(sesdosya)
    sesli = any(m.get("ses_dosyasi") for m in s["mesajlar"])
    print(f"Video hazır: {cikti} ({sure:.1f} sn, {'seslendirmeli' if sesli else 'yalnızca efekt sesi'})")


if __name__ == "__main__":
    main()
