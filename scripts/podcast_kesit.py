"""Podcast bölümünden dikey (1080x1920) kesit: en komik 40–60 sn'yi seçer, kelime kelime altyazılı video üretir.

Kullanım: python scripts/podcast_kesit.py <senaryo.json> <bolum.mp3> <kesit.mp4> [hadi.png] [yuru.png]
Çıktı yanında <kesit>.json: {"bas","son","baslik","sure","zamanlama"}.

1) Zamanlama: faster-whisper (yerel, ücretsiz) bölüm sesindeki kelimelerin zamanını çıkarır; senaryo
   metniyle hizalanır → her replik ve kelimenin başlangıç/bitiş saniyesi. Whisper yoksa/başarısızsa
   replikler karakter sayısına göre orantılı dağıtılır (altyazı yaklaşık olur).
2) Seçim: Gemini (GEMINI_API_KEY; model GEMINI_METIN_MODEL, varsayılan gemini-3.8-flash) ardışık
   replikleri seçer ve kısa bir Shorts başlığı yazar. Anahtar/yanıt yoksa süreye göre seçilir.
   Gemini ayrıca ilk ~2 sn ekranda büyük görünen bir "kanca" cümlesi yazar (izleyici kaydırmasın diye).
   KESIT_SADE=1: alttaki "Tam bölüm" ve alan adı yazıları konmaz (TikTok kuralı).
3) Video: bölümün gerçek sesi; konuşan karakter büyür ve sesle nabız atar; altyazıda o an söylenen
   kelime sarı; altta ilerleme çubuğu ve "Tam bölüm" çağrısı.
"""
import array, difflib, json, os, re, subprocess, sys, tempfile, textwrap, urllib.error, urllib.request
from PIL import Image, ImageDraw, ImageFilter, ImageFont

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
from podcast_ses import okunus  # noqa: E402

W, H, FPS = 1080, 1920, 30
FONT_B = os.path.join(KOK, "assets", "kart", "ArchivoBlack.ttf")
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
RENK = {"hadi": (232, 90, 44), "yuru": (52, 88, 140), "zemin": (17, 22, 34), "sari": (255, 204, 64),
        "beyaz": (250, 248, 244), "gri": (120, 130, 150), "hadi_acik": (255, 217, 204), "yuru_acik": (184, 203, 227)}
AD = {"hadi": "HADİ BABA", "yuru": "YÜRÜ BABA"}
MIN_SN, MAX_SN, HEDEF_SN = 40.0, 60.0, 52.0


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def uyari(b, m):
    print(f"::warning title={b}::{m}", flush=True)


def sure_olc(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def kucuk(k):
    k = k.replace("I", "ı").replace("İ", "i").lower()
    return re.sub(r"[^\wçğıöşü]", "", k)


# ---------------------------------------------------------------- 1) zamanlama
def replik_kelimeleri(senaryo):
    return [okunus(r["metin"]).split() for r in senaryo["replikler"]]


def whisper_kelimeler(mp3):
    from faster_whisper import WhisperModel
    model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    import numpy as np
    # Sesi ffmpeg ile kendimiz çözüyoruz (faster-whisper'ın PyAV okuyucusu bazı sürümlerde hata veriyor)
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", mp3, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    ses = np.frombuffer(ham, np.int16).astype(np.float32) / 32768.0
    parcalar, _ = model.transcribe(ses, language="tr", word_timestamps=True, vad_filter=False, beam_size=1)
    return [(w.word.strip(), w.start, w.end) for p in parcalar for w in (p.words or []) if w.word.strip()]


def hizala(kelimeler_r, whisper):
    """Senaryo kelimelerine whisper zamanlarını eşler; eşleşmeyenler komşulardan doldurulur."""
    duz = [(i, k) for i, ks in enumerate(kelimeler_r) for k in ks]
    a = [kucuk(k) for _, k in duz]
    b = [kucuk(w[0]) for w in whisper]
    zaman = [None] * len(duz)
    for blok in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for j in range(blok.size):
            w = whisper[blok.b + j]
            zaman[blok.a + j] = [w[1], w[2]]
    eslesen = sum(z is not None for z in zaman)
    # boşlukları doğrusal doldur
    bilinen = [i for i, z in enumerate(zaman) if z]
    if not bilinen:
        raise RuntimeError("hiç kelime eşleşmedi")
    for i in range(len(zaman)):
        if zaman[i]:
            continue
        once = max((k for k in bilinen if k < i), default=None)
        sonra = min((k for k in bilinen if k > i), default=None)
        if once is None:
            t = zaman[sonra][0]
            zaman[i] = [t, t]
        elif sonra is None:
            t = zaman[once][1]
            zaman[i] = [t, t + 0.3]
        else:
            t0, t1 = zaman[once][1], zaman[sonra][0]
            oran = (i - once) / (sonra - once)
            zaman[i] = [t0 + (t1 - t0) * oran, t0 + (t1 - t0) * oran + 0.05]
    return duz, zaman, eslesen / len(duz)


def orantili(kelimeler_r, toplam):
    duz = [(i, k) for i, ks in enumerate(kelimeler_r) for k in ks]
    boy = [len(k) + 1 for _, k in duz]
    bosluk = 0.4 * (len(kelimeler_r) - 1)
    olcek = (toplam - bosluk - 0.5) / sum(boy)
    zaman, t, onceki = [], 0.3, 0
    for (i, _), n in zip(duz, boy):
        if i != onceki:
            t += 0.4
            onceki = i
        zaman.append([t, t + n * olcek])
        t += n * olcek
    return duz, zaman


def zamanla(senaryo, mp3):
    kr = replik_kelimeleri(senaryo)
    yontem = "orantılı"
    try:
        duz, zaman, oran = hizala(kr, whisper_kelimeler(mp3))
        if oran < 0.6:
            raise RuntimeError(f"eşleşme düşük (%{oran * 100:.0f})")
        yontem = f"whisper (%{oran * 100:.0f} eşleşme)"
    except Exception as e:  # noqa: BLE001
        uyari("Kesit zamanlama", f"Whisper kullanılamadı, orantılı zamanlama: {str(e)[:200]}")
        duz, zaman = orantili(kr, sure_olc(mp3))
    replikler = []
    for i, r in enumerate(senaryo["replikler"]):
        ks = [(k, z[0], z[1]) for (j, k), z in zip(duz, zaman) if j == i]
        replikler.append({"kim": r["kim"], "metin": r["metin"], "kelimeler": ks,
                          "bas": ks[0][1] if ks else 0, "son": ks[-1][2] if ks else 0})
    return replikler, yontem


# ---------------------------------------------------------------- 2) seçim
def pencere_suresi(rp, i, j):
    return rp[j]["son"] - rp[i]["bas"]


def sec_sureyle(rp):
    en_iyi, puan = (0, len(rp) - 1), 1e9
    for i in range(1, len(rp)):  # açılış selamını atla
        for j in range(i, len(rp)):
            s = pencere_suresi(rp, i, j)
            if s > MAX_SN:
                break
            if s < MIN_SN:
                continue
            p = abs(s - HEDEF_SN) - (3 if rp[j]["kim"] == "yuru" else 0)  # Yürü'nün iğnesiyle bitmek iyi
            if p < puan:
                en_iyi, puan = (i, j), p
    return en_iyi


def sec_gemini(senaryo, rp):
    anahtar = os.environ.get("GEMINI_API_KEY")
    if not anahtar:
        raise RuntimeError("GEMINI_API_KEY yok")
    satirlar = "\n".join(f"[{i}] ({r['son'] - r['bas']:.1f} sn) {'Hadi' if r['kim'] == 'hadi' else 'Yürü'}: {r['metin']}"
                         for i, r in enumerate(rp))
    istem = (
        "Aşağıda Türkçe bir futbol podcast'inin replikleri var (köşeli parantezde sıra no, parantezde süre). "
        "Hadi coşkulu taraftar, Yürü alaycı abi. YouTube Shorts / TikTok için EN KOMİK, kendi başına anlaşılan "
        f"ardışık bir bölüm seç: toplam süre {MIN_SN:.0f}–{MAX_SN:.0f} saniye (replikler arası ~0,4 sn boşluk say). "
        "Açılış selamı ve kapanış vedasıyla başlama; güçlü bir laf sokma ya da espriyle bitir. "
        "Ayrıca bu kesit için en fazla 60 karakterlik, merak uyandıran ama yanıltmayan Türkçe bir başlık yaz "
        "(bahis/kupon çağrışımı yok, gerçek kişiye hakaret yok). "
        "Son olarak videonun ilk 2 saniyesinde ekranda kocaman yazacak bir KANCA yaz: 2–6 kelime, en fazla "
        "36 karakter, izleyiciyi kaydırmadan durduracak merak ya da gerilim (ör. \"Yürü bu sefer fena yakalandı!\"). "
        "Kanca seçtiğin replikleri doğru anlatmalı, başlığı tekrar etmemeli; emoji, bahis, hakaret yok. "
        'Yalnızca JSON döndür: {"bas": <ilk no>, "son": <son no>, "baslik": "...", "kanca": "..."}\n\n' + satirlar)
    model = os.environ.get("GEMINI_METIN_MODEL", "gemini-3.8-flash")
    govde = {"contents": [{"parts": [{"text": istem}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(govde).encode(), method="POST",
        headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            y = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:200]!r}") from None
    metin = "".join(p.get("text", "") for p in y["candidates"][0]["content"]["parts"])
    c = json.loads(re.search(r"\{.*\}", metin, re.S)[0])
    i, j = int(c["bas"]), int(c["son"])
    if not (0 <= i <= j < len(rp)):
        raise RuntimeError(f"geçersiz aralık {i}-{j}")
    s = pencere_suresi(rp, i, j)
    # Süre tutmuyorsa kenarlardan düzelt
    while s > MAX_SN and j > i:
        j -= 1
        s = pencere_suresi(rp, i, j)
    while s < MIN_SN and (j + 1 < len(rp) or i > 1):
        if j + 1 < len(rp) and pencere_suresi(rp, i, j + 1) <= MAX_SN:
            j += 1
        elif i > 1 and pencere_suresi(rp, i - 1, j) <= MAX_SN:
            i -= 1
        else:
            break
        s = pencere_suresi(rp, i, j)
    kanca = re.sub(r"\s+", " ", str(c.get("kanca", ""))).strip()
    if len(kanca) > 44:
        kanca = ""
    return i, j, str(c.get("baslik", "")).strip()[:70], kanca, model


# ---------------------------------------------------------------- 3) video
def daire(yol, boy):
    a = Image.open(yol).convert("RGBA")
    k = min(a.size)
    a = a.crop(((a.width - k) // 2, (a.height - k) // 2, (a.width + k) // 2, (a.height + k) // 2))
    a = a.resize((boy, boy), Image.LANCZOS)
    m = Image.new("L", (boy * 4, boy * 4), 0)
    ImageDraw.Draw(m).ellipse((0, 0, boy * 4 - 1, boy * 4 - 1), fill=255)
    a.putalpha(m.resize((boy, boy), Image.LANCZOS))
    return a


def ses_zarfi(mp3, bas, sure):
    """Kare başına ses yüksekliği (0–1)."""
    ham = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", mp3,
                          "-f", "s16le", "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
    s = array.array("h", ham)
    adim = 16000 // FPS
    deger = []
    for k in range(0, len(s), adim):
        p = s[k:k + adim]
        deger.append((sum(x * x for x in p[::4]) / max(1, len(p[::4]))) ** 0.5 if p else 0)
    tepe = sorted(deger)[int(len(deger) * 0.95)] or 1
    return [min(1.0, d / tepe) for d in deger]


class Cizer:
    KANCA_SN = 2.2  # kancanın ekranda kalma süresi

    def __init__(self, senaryo, rp, i, j, baslik, hadi, yuru, kanca="", bas=0.0):
        self.rp, self.i, self.j = rp, i, j
        self.bas = bas
        self.kanca = self._kanca_hazirla(kanca.replace("i", "İ").upper() if kanca else "")
        self.f_ust = ImageFont.truetype(FONT_B, 64)
        self.f_etiket = ImageFont.truetype(FONT_B, 30)
        self.f_baslik = ImageFont.truetype(FONT_B, 46)
        self.f_ad = ImageFont.truetype(FONT_B, 40)
        self.f_alt = ImageFont.truetype(FONT_M, 64)
        self.f_kucuk = ImageFont.truetype(FONT_M, 34)
        self.av = {"hadi": daire(hadi, 380), "yuru": daire(yuru, 380)}
        self.onbellek = {}
        self.zemin = self._zemin(baslik or senaryo["baslik"])
        olcu = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        # Her replik için altyazı sayfaları (en fazla 3 satır)
        for r in rp[i:j + 1]:
            satirlar, sat = [], []
            for n, (k, _, _) in enumerate(r["kelimeler"]):
                dene = " ".join(x[0] for x in sat + [(k, 0, n)])
                if sat and olcu.textlength(dene, font=self.f_alt) > 960:
                    satirlar.append(sat)
                    sat = []
                sat.append((k, 0, n))
            if sat:
                satirlar.append(sat)
            r["sayfalar"] = [satirlar[k:k + 3] for k in range(0, len(satirlar), 3)]

    def _kanca_hazirla(self, metin):
        """Kancayı 960 px'e sığacak en büyük yazı boyuyla en fazla 3 satıra böler."""
        if not metin:
            return None
        olcu = ImageDraw.Draw(Image.new("RGB", (1, 1)))
        for boy in (124, 112, 100, 88, 78, 68):
            f = ImageFont.truetype(FONT_B, boy)
            satirlar, sat = [], ""
            for k in metin.split():
                dene = f"{sat} {k}".strip()
                if sat and olcu.textlength(dene, font=f) > 960:
                    satirlar.append(sat)
                    sat = k
                else:
                    sat = dene
            satirlar.append(sat)
            if len(satirlar) <= 3 and all(olcu.textlength(x, font=f) <= 980 for x in satirlar):
                return {"font": f, "boy": boy, "satirlar": satirlar}
        return None

    def _kanca_ciz(self, im, rel):
        """İlk ~2 sn: ekran kararır, kanca büyüyerek gelir, sonra söner."""
        k = self.kanca
        sonme = max(0.0, min(1.0, (self.KANCA_SN - rel) / 0.35))
        gelis = min(1.0, rel / 0.25)
        olcek = 0.6 + 0.4 * min(1.0, rel / 0.18) + 0.06 * max(0.0, 1 - abs(rel - 0.22) / 0.12)
        ort = Image.new("RGBA", (W, H), (8, 10, 18, int(175 * sonme * gelis)))
        im.alpha_composite(ort)
        f = ImageFont.truetype(FONT_B, max(10, int(k["boy"] * olcek)))
        d = ImageDraw.Draw(im)
        satir_y = int(k["boy"] * olcek * 1.18)
        y = 760 - satir_y * len(k["satirlar"]) // 2
        a = int(255 * sonme)
        for n, sat in enumerate(k["satirlar"]):
            renk = RENK["sari"] if n == len(k["satirlar"]) - 1 else RENK["beyaz"]
            d.text((W // 2, y + n * satir_y), sat, font=f, fill=renk + (a,), anchor="ma",
                   stroke_width=max(4, int(8 * olcek)), stroke_fill=(10, 12, 20, a))

    def _zemin(self, baslik):
        im = Image.new("RGB", (W, H), RENK["zemin"])
        d = ImageDraw.Draw(im)
        d.polygon([(0, 0), (W, 0), (W, 380), (0, 560)], fill=RENK["hadi"])
        d.polygon([(0, 560), (W, 380), (W, 1010), (0, 1010)], fill=RENK["yuru"])
        for k in range(9):  # Yürü'nün soluk istatistik sütunları
            h = 80 + (k * 97) % 260
            x = 600 + k * 52
            d.rectangle([x, 1000 - h, x + 30, 1000], fill=(66, 102, 156))
        d.text((W // 2, 120), "HADİ vs YÜRÜ", font=self.f_ust, fill="white", anchor="mm",
               stroke_width=5, stroke_fill=(20, 20, 30))
        d.rounded_rectangle([W // 2 - 170, 172, W // 2 + 170, 222], 25, fill=(20, 20, 30))
        d.text((W // 2, 197), "PODCAST KESİTİ", font=self.f_etiket, fill=RENK["sari"], anchor="mm")
        satir = textwrap.wrap(baslik, 30)[:2]
        d.multiline_text((W // 2, 255), "\n".join(satir), font=self.f_baslik, fill="white", anchor="ma",
                         align="center", stroke_width=4, stroke_fill=(20, 20, 30), spacing=8)
        d.rectangle([0, 1010, W, H], fill=RENK["zemin"])
        if os.environ.get("KESIT_SADE"):  # TikTok: API ile gönderilen videoda bağlantı/tanıtım yazısı olmamalı
            return im
        d.text((W // 2, H - 150), "Tam bölüm: YouTube · Spotify — \"Hadi vs Yürü\"", font=self.f_kucuk,
               fill=RENK["hadi_acik"], anchor="mm")
        d.text((W // 2, H - 100), "hadibaba.com · yurubaba.com", font=self.f_kucuk, fill=RENK["yuru_acik"], anchor="mm")
        return im

    def _avatar(self, kim, olcek, aktif):
        anahtar = (kim, round(olcek, 2), aktif)
        if anahtar not in self.onbellek:
            boy = int(380 * olcek)
            a = self.av[kim].resize((boy, boy), Image.LANCZOS)
            if not aktif:
                koyu = Image.new("RGBA", a.size, (17, 22, 34, 120))
                koyu.putalpha(Image.eval(a.getchannel("A"), lambda v: v * 120 // 255))
                a = Image.alpha_composite(a, koyu)
            cerceve = Image.new("RGBA", (boy + 28, boy + 28), (0, 0, 0, 0))
            dc = ImageDraw.Draw(cerceve)
            dc.ellipse([0, 0, boy + 27, boy + 27], fill=RENK["sari"] if aktif else (230, 230, 235))
            cerceve.alpha_composite(a, (14, 14))
            if aktif:
                isik = Image.new("RGBA", (boy + 108, boy + 108), (0, 0, 0, 0))
                ImageDraw.Draw(isik).ellipse([30, 30, boy + 78, boy + 78], fill=RENK["sari"] + (150,))
                isik = isik.filter(ImageFilter.GaussianBlur(22))
                isik.alpha_composite(cerceve, (40, 40))
                cerceve = isik
            self.onbellek[anahtar] = cerceve
        return self.onbellek[anahtar]

    def kare(self, t, zarf, ilerleme):
        """t: bölüm içindeki mutlak saniye."""
        im = self.zemin.copy().convert("RGBA")
        d = ImageDraw.Draw(im)
        aktif = None
        for r in self.rp[self.i:self.j + 1]:
            if r["bas"] - 0.25 <= t <= r["son"] + 0.35:
                aktif = r
        if aktif is None:  # replik arası: son konuşanı göster
            aktif = max((r for r in self.rp[self.i:self.j + 1] if r["bas"] <= t), key=lambda r: r["bas"],
                        default=self.rp[self.i])
        for kim, cx, cy in (("hadi", 290, 640), ("yuru", 790, 800)):
            konusan = aktif["kim"] == kim
            olcek = (0.95 + 0.07 * zarf) if konusan else 0.72
            a = self._avatar(kim, olcek, konusan)
            im.alpha_composite(a, (cx - a.width // 2, cy - a.height // 2))
        # Konuşan adı
        renk = RENK[aktif["kim"]]
        ad = AD[aktif["kim"]]
        gen = d.textlength(ad, font=self.f_ad) + 60
        d.rounded_rectangle([W // 2 - gen / 2, 1100, W // 2 + gen / 2, 1164], 32, fill=renk)
        d.text((W // 2, 1132), ad, font=self.f_ad, fill="white", anchor="mm")
        # Altyazı: o anki sayfa
        ks = aktif["kelimeler"]
        simdiki = max((n for n, (_, b, _) in enumerate(ks) if b <= t), default=0)
        sayfa = next((s for s in aktif["sayfalar"] if any(n == simdiki for sat in s for _, _, n in sat)),
                     aktif["sayfalar"][0])
        y = 1240
        for sat in sayfa:
            metin = " ".join(k for k, _, _ in sat)
            x = W // 2 - d.textlength(metin, font=self.f_alt) / 2
            for k, _, n in sat:
                b, s = ks[n][1], ks[n][2]
                if b <= t <= max(s, b + 0.15) or (n == simdiki and t < ks[min(n + 1, len(ks) - 1)][1]):
                    c = RENK["sari"]
                elif b < t:
                    c = RENK["beyaz"]
                else:
                    c = (175, 182, 198)
                d.text((x, y), k, font=self.f_alt, fill=c, stroke_width=4, stroke_fill=(10, 12, 20))
                x += d.textlength(k + " ", font=self.f_alt)
            y += 96
        # İlerleme çubuğu
        d.rectangle([0, H - 30, W, H], fill=(40, 48, 66))
        d.rectangle([0, H - 30, int(W * ilerleme), H], fill=RENK["sari"])
        rel = t - self.bas
        if self.kanca and rel < self.KANCA_SN:
            self._kanca_ciz(im, rel)
        return im.convert("RGB")


def video(senaryo, mp3, cikti, rp, i, j, baslik, hadi, yuru, kanca=""):
    bas = max(0.0, rp[i]["bas"] - 0.2)
    son = min(sure_olc(mp3), rp[j]["son"] + 0.5)
    sure = son - bas
    zarf = ses_zarfi(mp3, bas, sure)
    c = Cizer(senaryo, rp, i, j, baslik, hadi, yuru, kanca, bas)
    n = int(sure * FPS)
    ff = subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
        "-r", str(FPS), "-i", "-", "-ss", f"{bas:.3f}", "-t", f"{sure:.3f}", "-i", mp3,
        "-af", f"afade=t=in:d=0.15,afade=t=out:st={max(0, sure - 0.4):.3f}:d=0.4",
        "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    yumusak = 0.0
    for k in range(n):
        z = zarf[k] if k < len(zarf) else 0
        yumusak = yumusak * 0.6 + z * 0.4
        ff.stdin.write(c.kare(bas + k / FPS, yumusak, k / n).tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg başarısız")
    return sure


def main():
    senaryo = json.load(open(sys.argv[1], encoding="utf-8"))
    mp3, cikti = sys.argv[2], sys.argv[3]
    hadi = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else os.path.join(KOK, "video", "hadi.png")
    yuru = sys.argv[5] if len(sys.argv) > 5 and os.path.exists(sys.argv[5]) else os.path.join(KOK, "video", "yuru.png")
    rp, yontem = zamanla(senaryo, mp3)
    try:
        i, j, baslik, kanca, model = sec_gemini(senaryo, rp)
        secim = f"Gemini {model}"
    except Exception as e:  # noqa: BLE001
        uyari("Kesit seçimi", f"Gemini seçemedi, süreye göre seçildi: {str(e)[:200]}")
        (i, j), baslik, kanca, secim = sec_sureyle(rp), "", "", "süre"
    sure = video(senaryo, mp3, cikti, rp, i, j, baslik, hadi, yuru, kanca)
    sade = os.environ.get("KESIT_SADE_CIKTI")  # aynı kesitin yazısız (TikTok) kopyası
    if sade:
        os.environ["KESIT_SADE"] = "1"
        video(senaryo, mp3, sade, rp, i, j, baslik, hadi, yuru, kanca)
        os.environ.pop("KESIT_SADE")
    meta = {"tarih": senaryo["tarih"], "bas": i, "son": j, "baslik": baslik or senaryo["baslik"], "sure": round(sure, 1),
            "zamanlama": yontem, "secim": secim, "kanca": kanca}
    json.dump(meta, open(os.path.splitext(cikti)[0] + ".json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    notice("Podcast kesiti", f"{os.path.basename(cikti)}: replik {i}–{j}, {sure:.0f} sn, seçim {secim}, "
                             f"zamanlama {yontem} — {meta['baslik']}" + (f" · kanca: {kanca}" if kanca else ""))


if __name__ == "__main__":
    main()
