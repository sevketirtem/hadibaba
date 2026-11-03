"""Dombra marka sesi (Hadi vs Yürü).

1) Bindirme — mevcut sesin üstüne dombra koyar; süre ve replik zamanları DEĞİŞMEZ:
     python scripts/dombra.py podcast <ses>   # açılışta giriş jingle'ı, sonda kapanış
     python scripts/dombra.py sting   <ses>   # başta kısa tıngırtı (Tahmin Ligi)
     python scripts/dombra.py fon     <ses>   # baştan sona çok kısık dombra fonu (atışma videosu)
   assets/ses/dombra-*.mp3 yoksa hiçbir şey yapmaz (çıkış kodu 0).

2) Jingle seçimi — Lyria çıktılarından en iyisini seçip parçalar:
     python scripts/dombra.py sec <aday1.wav> [aday2.wav ...]
   Her aday: faster-whisper ile vokal kontrolü (sözlü olan elenir) + Gemini dinleyip puanlar
   (dombra gibi mi, enstrümantal mı, jingle'a uygun mu). En iyisinden giris (6 sn), sting (2,5 sn),
   kapanis (5 sn), fon (30 sn, döngüye uygun) üretip assets/ses/'e yazar.
"""
import base64, json, os, re, subprocess, sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KLASOR = os.path.join(KOK, "assets", "ses")
DOSYA = {k: os.path.join(KLASOR, f"dombra-{k}.mp3") for k in ("giris", "sting", "kapanis", "fon")}


def sure(yol):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                                capture_output=True, text=True, check=True).stdout)


def _yaz(ses, girdiler, filtre):
    gecici = ses + ".dombra" + os.path.splitext(ses)[1]
    kodek = ["-c:a", "libmp3lame", "-b:a", "192k"] if ses.endswith(".mp3") else []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ses, *girdiler, "-filter_complex", filtre,
                    "-map", "[out]", *kodek, gecici], check=True)
    os.replace(gecici, ses)


def bindir(tur, ses):
    s = sure(ses)
    if tur == "podcast":
        if not (os.path.exists(DOSYA["giris"]) and os.path.exists(DOSYA["kapanis"])):
            return False
        k = sure(DOSYA["kapanis"])
        gecik = max(0, int((s - k) * 1000))
        _yaz(ses, ["-i", DOSYA["giris"], "-i", DOSYA["kapanis"]],
             "[1:a]volume=0.40[g];"
             f"[2:a]volume=0.35,adelay={gecik}|{gecik}[k];"
             f"[0:a][g][k]amix=inputs=3:duration=first:normalize=0,alimiter=limit=0.95,atrim=0:{s:.3f}[out]")
    elif tur == "sting":
        if not os.path.exists(DOSYA["sting"]):
            return False
        _yaz(ses, ["-i", DOSYA["sting"]],
             f"[1:a]volume=0.50[g];[0:a][g]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95,atrim=0:{s:.3f}[out]")
    elif tur == "fon":
        if not os.path.exists(DOSYA["fon"]):
            return False
        _yaz(ses, ["-stream_loop", "-1", "-i", DOSYA["fon"]],
             f"[1:a]atrim=0:{s:.3f},volume=0.10,afade=t=in:d=1,afade=t=out:st={max(0, s - 1.5):.3f}:d=1.5[f];"
             f"[0:a][f]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[out]")
    else:
        raise SystemExit(f"bilinmeyen tür: {tur}")
    return True


# ---------- Jingle seçimi ----------

def vokal_kelime(yol):
    try:
        import numpy as np
        from faster_whisper import WhisperModel
    except ImportError:
        return -1
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(ham, np.int16).astype(np.float32) / 32768.0
    segs, _ = m.transcribe(a, language="tr", vad_filter=True, beam_size=1)
    return sum(len(s.text.split()) for s in segs if s.no_speech_prob < 0.6)


def gemini_puan(yol):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gapi
    if not gapi.var_mi():
        return 5, "gemini yok"
    mp3 = yol + ".kontrol.mp3"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", yol, "-t", "40", "-ac", "1", "-b:a", "64k", mp3], check=True)
    istem = ("Bu müzik parçasını dinle. Bir futbol podcast'i için marka jingle'ı olacak. Puanla (0-10): "
             "baskın çalgı Kazak dombrası (ya da çok benzeri iki telli tezene çalgısı) gibi mi, tamamen enstrümantal mi "
             "(insan sesi/şarkı sözü varsa 0), neşeli ve akılda kalıcı mı, ilk 6 saniyesi giriş olarak kullanılabilir mi. "
             'Yalnızca JSON: {"puan": <0-10>, "dombra": true/false, "vokal": true/false, "not": "kısa"}')
    govde = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mpeg",
                                                      "data": base64.b64encode(open(mp3, "rb").read()).decode()}},
                                     {"text": istem}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2}}
    try:
        y = gapi.istek(f"models/{os.environ.get('GEMINI_METIN_MODEL', 'gemini-3.8-flash')}:generateContent", govde, 180)
        c = json.loads(re.search(r"\{.*\}", "".join(p.get("text", "") for p in y["candidates"][0]["content"]["parts"]), re.S)[0])
        p = float(c.get("puan", 0))
        if c.get("vokal"):
            p = 0
        if not c.get("dombra", True):
            p = min(p, 3)
        return p, c.get("not", "")
    except Exception as e:  # noqa: BLE001
        return 5, f"gemini hata: {str(e)[:120]}"


def guclu_an(yol, bas, bit):
    """bas–bit aralığında en yüksek enerjili 0,25 sn'nin başı (sting için)."""
    import array
    ham = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(bas), "-t", str(bit - bas), "-i", yol,
                          "-f", "s16le", "-ac", "1", "-ar", "8000", "-"], capture_output=True, check=True).stdout
    o = array.array("h", ham)
    adim = 2000
    en, t = -1, bas
    for k in range(0, max(1, len(o) - adim), 400):
        e = sum(abs(x) for x in o[k:k + adim:4])
        if e > en:
            en, t = e, bas + k / 8000
    return max(0.0, t - 0.15)


def kes(kaynak, hedef, bas, uz, giris=0.05, cikis=0.6):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{bas:.2f}", "-t", f"{uz:.2f}", "-i", kaynak,
                    "-af", f"afade=t=in:d={giris},afade=t=out:st={max(0, uz - cikis):.2f}:d={cikis},loudnorm=I=-16:TP=-1.5",
                    "-ac", "2", "-ar", "44100", "-b:a", "192k", hedef], check=True)


def sec(adaylar):
    sonuc = []
    for a in adaylar:
        if not os.path.exists(a) or sure(a) < 15:
            continue
        v = vokal_kelime(a)
        p, notu = gemini_puan(a)
        if v > 6:
            p = 0
        print(f"::notice title=Dombra aday::{os.path.basename(a)} · {sure(a):.0f} sn · whisper kelime {v} · Gemini {p} · {notu}")
        sonuc.append((p, a))
    sonuc.sort(reverse=True)
    if not sonuc or sonuc[0][0] < 5:
        raise SystemExit("::error title=Dombra::Uygun aday yok (vokal var ya da dombraya benzemiyor); assets/ses değişmedi")
    en = sonuc[0][1]
    s = sure(en)
    os.makedirs(KLASOR, exist_ok=True)
    kes(en, DOSYA["giris"], 0, 6, cikis=1.5)
    kes(en, DOSYA["sting"], guclu_an(en, 2, min(s - 3, 20)), 2.5, cikis=0.8)
    kes(en, DOSYA["kapanis"], max(0, s - 5.5), 5, giris=0.4, cikis=1.2)
    kes(en, DOSYA["fon"], min(8, s / 4), min(30, s - 10), giris=0.8, cikis=0.8)
    print(f"::notice title=Dombra seçildi::{os.path.basename(en)} → assets/ses/dombra-*.mp3")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    if sys.argv[1] == "sec":
        sec(sys.argv[2:])
    else:
        try:
            ok = bindir(sys.argv[1], sys.argv[2])
            print(f"::notice title=Dombra::{sys.argv[1]} {'eklendi' if ok else 'dosya yok, atlandı'}")
        except Exception as e:  # noqa: BLE001  (dombra süs; asıl sesi asla bozmasın)
            print(f"::warning title=Dombra::{sys.argv[1]} eklenemedi: {str(e)[:200]}")
