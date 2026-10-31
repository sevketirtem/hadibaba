"""Tezahürat videosu: "Mahalle Arasında" (Flow Music ile üretilen ses, kendi sözlerimiz).

Kullanım: python video/tezahurat_video.py <ses> <cikti.mp4> [bas_sn son_sn]
Satır/kelime zamanları aşağıda elle (Whisper + Gemini dinlemesinden) girildi.
Görüntü tamamen bizim: karakter avatarları, kelime kelime sarı karaoke, tribün zemini.
TEZAHURAT_SADE=1 → alan adı ve tanıtım yazısı yok (TikTok).
"""
import os, sys
from PIL import Image, ImageDraw, ImageFilter

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
import podcast_kesit as pk  # noqa: E402
from podcast_kesit import RENK, W, H, AD  # noqa: E402

# (kim, [(kelime, başlangıç sn), ...], satır sonu sn)
SATIRLAR = [
    ("hadi", [("Mahalle", 17.94), ("arasında", 18.82), ("başladı", 19.70), ("bu", 20.56), ("sevda,", 20.90)], 21.9),
    ("yuru", [("Taş", 21.96), ("kale,", 22.30), ("yamalı", 23.00), ("top,", 23.44), ("bir", 23.94), ("de", 24.24),
              ("bitmeyen", 24.48), ("kavga.", 25.16)], 25.9),
    ("hadi", [("Yağmur", 25.92), ("yağsa,", 26.42), ("kar", 27.0), ("yağsa,", 27.35), ("maç", 27.80), ("varsa", 27.98),
              ("oradaydık,", 28.40)], 29.6),
    ("yuru", [("Kaybettik", 29.72), ("mi?", 30.45), ("Kaybettik.", 30.88), ("Ama", 31.96), ("yine", 32.22), ("de", 32.70),
              ("bağırdık.", 32.98)], 34.1),
    ("hadi", [("Tribünde", 34.24), ("yer", 34.92), ("kalmasa", 35.20), ("ağaca", 35.96), ("çıkarız", 36.64), ("baba,", 37.42)], 38.0),
    ("yuru", [("Ağaçtan", 38.06), ("da", 38.62), ("düşersin,", 38.96), ("ben", 40.00), ("demiştim", 40.20), ("bak", 40.88),
              ("sana.", 41.22)], 41.9),
    ("ikisi", [("Bu", 42.00), ("sevdanın", 42.16), ("adı", 42.96), ("futbol,", 43.36), ("rengi", 44.02), ("yok,", 44.44),
               ("takımı", 45.04), ("yok,", 45.55)], 45.95),
    ("ikisi", [("Faturası", 46.00), ("çok", 46.92), ("ama", 47.24), ("vazgeçen", 48.00), ("tek", 48.82), ("kişi", 49.14),
               ("yok!", 49.42)], 49.8),
    ("hadi", [("HADİ", 49.84), ("BABA!", 50.36)], 52.0),
    ("yuru", [("YÜRÜ", 52.10), ("BABA!", 52.56)], 54.0),
    ("ikisi", [("HEY!", 54.06), ("HEY!", 55.2)], 57.8),
    ("hadi", [("HADİ", 57.94), ("BABA!", 58.28)], 60.0),
    ("yuru", [("YÜRÜ", 60.08), ("BABA!", 60.60)], 61.9),
    ("hadi", [("HADİ", 61.98), ("BABA!", 62.36)], 63.6),
    ("yuru", [("YÜRÜ", 63.66), ("BABA!", 64.34)], 66.0),
    # --- tam şarkı (66 sn sonrası) ---
    ("yuru", [("YÜRÜ", 79.84), ("BABA!", 80.50)], 81.6),
    ("hadi", [("Mahalle", 98.06), ("arasında", 98.86), ("başladı", 99.66), ("bu", 100.60), ("sevda,", 100.92)], 101.9),
    ("yuru", [("Taş", 102.00), ("kale,", 102.34), ("yamalı", 102.96), ("top,", 103.38), ("bir", 104.06), ("de", 104.20),
              ("bitmeyen", 104.52), ("kavga.", 105.20)], 105.7),
    ("ikisi", [("Bu", 105.72), ("sevdanın", 106.16), ("adı", 106.94), ("futbol,", 107.30), ("rengi", 107.96), ("yok,", 108.46),
               ("takımı", 108.88), ("yok,", 109.38)], 109.78),
    ("ikisi", [("vazgeçen", 109.80), ("tek", 110.80), ("kişi", 111.20), ("yok!", 111.48)], 111.84),
    ("ikisi", [("VAZGEÇEN", 111.86), ("TEK", 112.76), ("KİŞİ", 113.18), ("YOK!", 113.52)], 114.6),
    ("hadi", [("Mahalle", 130.12), ("arasında", 130.88), ("başladı", 131.64), ("bu", 132.54), ("sevda,", 132.90)], 133.9),
    ("yuru", [("Taş", 133.98), ("kale,", 134.30), ("yamalı", 135.04), ("top,", 135.42), ("bir", 136.08), ("de", 136.24),
              ("bitmeyen", 136.48), ("kavga.", 137.18)], 137.8),
    ("ikisi", [("Bu", 137.82), ("sevdanın...", 138.34)], 140.0),
    ("ikisi", [("...adı", 154.94), ("futbol,", 155.36), ("rengi", 156.00), ("yok,", 156.44), ("takımı", 156.92), ("yok,", 157.36)],
     157.96),
    ("ikisi", [("vazgeçen", 157.98), ("tek", 160.80), ("kişi", 161.14), ("yok!", 161.46)], 161.96),
    ("hadi", [("HADİ", 161.98), ("BABA!", 162.34)], 164.2),
    ("yuru", [("YÜRÜ", 164.24), ("BABA!", 164.58)], 165.0),
    ("hadi", [("HADİ", 165.06), ("BABA!", 165.84)], 168.0),
    ("yuru", [("YÜRÜ", 168.04), ("BABA!", 168.56)], 170.5),
]


def replikler():
    rp = []
    for kim, kel, son in SATIRLAR:
        ks = [(k, b, kel[n + 1][1] if n + 1 < len(kel) else son) for n, (k, b) in enumerate(kel)]
        rp.append({"kim": kim, "bas": kel[0][1], "son": son, "kelimeler": ks, "metin": " ".join(k for k, _ in kel)})
    return rp


class TezahuratCizer(pk.Cizer):
    def _zemin(self, baslik):
        im = Image.new("RGB", (W, H), (10, 13, 24))
        d = ImageDraw.Draw(im)
        # Gece gökyüzü + tribün ışıkları
        for y in range(0, 1010):
            c = int(18 + 22 * y / 1010)
            d.line([(0, y), (W, y)], fill=(c // 2, c // 2 + 2, c + 14))
        isik = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        di = ImageDraw.Draw(isik)
        for x in (140, 540, 940):
            di.ellipse([x - 120, 230, x + 120, 330], fill=(255, 240, 200, 120))
        isik = isik.filter(ImageFilter.GaussianBlur(40))
        im = Image.alpha_composite(im.convert("RGBA"), isik).convert("RGB")
        d = ImageDraw.Draw(im)
        for x in (140, 540, 940):
            d.rectangle([x - 4, 290, x + 4, 520], fill=(40, 46, 64))
            d.rounded_rectangle([x - 60, 262, x + 60, 300], 8, fill=(255, 246, 220))
        # Tribün basamakları (kendi çizimimiz, arma/yazı yok)
        for k in range(7):
            y = 560 + k * 64
            d.rectangle([0, y, W, y + 6], fill=(34, 40, 58))
        d.text((W // 2, 120), "HADİ vs YÜRÜ", font=self.f_ust, fill="white", anchor="mm",
               stroke_width=5, stroke_fill=(20, 20, 30))
        d.rounded_rectangle([W // 2 - 150, 172, W // 2 + 150, 222], 25, fill=RENK["hadi"])
        d.text((W // 2, 197), "TEZAHÜRAT", font=self.f_etiket, fill="white", anchor="mm")
        d.rectangle([0, 1080, W, H], fill=(10, 13, 24))
        from PIL import ImageFont
        d.text((W // 2, 1765), "♪ Mahalle Arasında ♪", font=ImageFont.truetype(pk.FONT_M, 46), fill=RENK["sari"],
               anchor="mm")
        if not os.environ.get("TEZAHURAT_SADE"):
            d.text((W // 2, H - 100), "hadibaba.com · yurubaba.com", font=self.f_kucuk,
                   fill=RENK["yuru_acik"], anchor="mm")
        return im

    def _kalabalik(self, im, t, zarf):
        """Zıplayan taraftar siluetleri + turuncu/lacivert atkılar (logosuz)."""
        d = ImageDraw.Draw(im)
        import math
        for sira in range(4):
            y0 = 900 + sira * 50
            for n in range(14):
                x = n * 82 + (sira % 2) * 41 - 20
                faz = (n * 1.7 + sira * 0.9)
                zip_ = int((10 + 26 * zarf) * max(0.0, math.sin(t * 7.5 + faz)))
                y = y0 - zip_
                ton = 26 + sira * 6
                d.ellipse([x - 22, y - 70, x + 22, y - 26], fill=(ton, ton + 4, ton + 14))
                d.rounded_rectangle([x - 32, y - 28, x + 32, y + 60], 18, fill=(ton, ton + 4, ton + 14))
                if (n + sira) % 3 == 0:  # havaya kalkan atkı
                    renk = RENK["hadi"] if (n + sira) % 2 else RENK["yuru_acik"]
                    sal = int(14 * math.sin(t * 6 + faz))
                    d.polygon([(x - 6, y - 40), (x + 6, y - 40), (x + 40 + sal, y - 120), (x + 24 + sal, y - 126)],
                              fill=renk)

    def kare(self, t, zarf, ilerleme):
        im = self.zemin.copy().convert("RGBA")
        self._kalabalik(im, t, zarf)
        d = ImageDraw.Draw(im)
        rp = self.rp[self.i:self.j + 1]
        aktif = next((r for r in rp if r["bas"] - 0.2 <= t <= r["son"] + 0.1), None)
        if aktif is None:
            aktif = max((r for r in rp if r["bas"] <= t), key=lambda r: r["bas"], default=rp[0])
        if t < rp[0]["bas"] - 0.2 or t > aktif["son"] + 1.2:  # giriş / müzik arası: söz yok, ikisi de coşar
            aktif = {"kim": "ikisi", "kelimeler": [], "sayfalar": [], "bas": 0}
        for kim, cx, cy in (("hadi", 290, 560), ("yuru", 790, 640)):
            konusan = aktif["kim"] in (kim, "ikisi")
            olcek = (0.82 + 0.10 * zarf) if konusan else 0.62
            a = self._avatar(kim, olcek, konusan)
            im.alpha_composite(a, (cx - a.width // 2, cy - a.height // 2))
        d = ImageDraw.Draw(im)
        if aktif["kelimeler"]:
            if aktif["kim"] == "ikisi":
                ad, renk = "HEP BİRLİKTE + TRİBÜN", (200, 60, 70)
            else:
                ad, renk = AD[aktif["kim"]], RENK[aktif["kim"]]
            gen = d.textlength(ad, font=self.f_ad) + 60
            d.rounded_rectangle([W // 2 - gen / 2, 1150, W // 2 + gen / 2, 1214], 32, fill=renk)
            d.text((W // 2, 1182), ad, font=self.f_ad, fill="white", anchor="mm")
            ks = aktif["kelimeler"]
            simdiki = max((n for n, (_, b, _) in enumerate(ks) if b <= t), default=0)
            sayfa = next((s for s in aktif["sayfalar"] if any(n == simdiki for sat in s for _, _, n in sat)),
                         aktif["sayfalar"][0])
            y = 1300
            for sat in sayfa:
                metin = " ".join(k for k, _, _ in sat)
                x = W // 2 - d.textlength(metin, font=self.f_alt) / 2
                for k, _, n in sat:
                    b = ks[n][1]
                    c = RENK["sari"] if n == simdiki and b <= t else (RENK["beyaz"] if b < t else (175, 182, 198))
                    d.text((x, y), k, font=self.f_alt, fill=c, stroke_width=4, stroke_fill=(10, 12, 20))
                    x += d.textlength(k + " ", font=self.f_alt)
                y += 96
        d.rectangle([0, H - 30, W, H], fill=(40, 48, 66))
        d.rectangle([0, H - 30, int(W * ilerleme), H], fill=RENK["sari"])
        rel = t - self.bas
        if self.kanca and rel < self.KANCA_SN:
            self._kanca_ciz(im, rel)
        return im.convert("RGB")


def main():
    ses, cikti = sys.argv[1], sys.argv[2]
    bas = float(sys.argv[3]) if len(sys.argv) > 3 else 14.0
    son = float(sys.argv[4]) if len(sys.argv) > 4 else 66.5
    rp = replikler()
    pk.Cizer = TezahuratCizer  # pk.video() bu sınıfı kullansın
    # pk.video başlangıcı ilk replikten alır; giriş için sahte erken replik yerine bas'ı doğrudan veriyoruz
    sure = son - bas
    zarf = pk.ses_zarfi(ses, bas, sure)
    c = TezahuratCizer({"baslik": ""}, rp, 0, len(rp) - 1, "", os.path.join(KOK, "video", "hadi.png"),
                       os.path.join(KOK, "video", "yuru.png"), os.environ.get("TEZAHURAT_KANCA", "Hadi ile Yürü'nün tezahüratı!"), bas)
    import subprocess
    n = int(sure * pk.FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(pk.FPS), "-i", "-", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", ses,
        "-af", f"afade=t=in:d=0.6,afade=t=out:st={max(0, sure - 1.2):.3f}:d=1.2",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    yumusak = 0.0
    for k in range(n):
        z = zarf[k] if k < len(zarf) else 0
        yumusak = yumusak * 0.6 + z * 0.4
        ff.stdin.write(c.kare(bas + k / pk.FPS, yumusak, k / n).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg başarısız")
    print(f"{cikti}: {sure:.1f} sn")


if __name__ == "__main__":
    main()
