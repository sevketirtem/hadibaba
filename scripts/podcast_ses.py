"""Hadi vs Yürü podcast bölümünü seslendirir → MP3.

Kullanım: python scripts/podcast_ses.py <senaryo.json> <çıktı.mp3> [gemini|google]
  gemini: Gemini TTS, iki konuşmacılı tek seferde (GEMINI_API_KEY). Sesler: Hadi=Umbriel, Yürü=Algenib.
  google: Google Cloud TTS (Chirp 3 HD), replik replik + birleştirme (GOOGLE_TTS_KEY; video/seslendir.py).
Senaryo biçimi: {"tarih","baslik","aciklama","replikler":[{"kim":"hadi|yuru","metin":"..."}]}
"""
import base64, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "video"))
sys.path.insert(0, os.path.join(KOK, "scripts"))
API = "https://generativelanguage.googleapis.com/v1beta"
SES = {"hadi": os.environ.get("GEMINI_SES_HADI", "Umbriel"), "yuru": os.environ.get("GEMINI_SES_YURU", "Algenib")}
AD = {"hadi": "Hadi", "yuru": "Yürü"}
YONELME = ["sıfıra", "bire", "ikiye", "üçe", "dörde", "beşe", "altıya", "yediye", "sekize", "dokuza"]
SAYI = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def okunus(t):
    return re.sub(r"\b(\d)\s*[-–]\s*(\d)\b", lambda m: f"{YONELME[int(m[1])]} {SAYI[int(m[2])]}", t)


def _gemini(yol, govde):
    import gapi  # Vertex (deneme kredisi) önce, AI Studio yedek
    try:
        return gapi.istek(yol, govde, 600)
    except gapi.HataHTTP as e:
        raise RuntimeError(f"Gemini TTS {e}") from None


def tts_modeli():
    istenen = os.environ.get("GEMINI_TTS_MODEL", "").strip()
    if istenen:
        return istenen if istenen.startswith("models/") else "models/" + istenen
    import gapi
    adlar = [m["name"] for m in gapi.istek("models?pageSize=1000", None, 60).get("models", []) if "tts" in m["name"]]
    if not adlar:
        raise RuntimeError("TTS modeli bulunamadı")
    notice("Gemini TTS modelleri", ", ".join(adlar))
    adlar.sort(key=lambda n: ("flash" not in n, "lite" in n, "preview" in n, n))
    return adlar[0]


STIL = {
    "hadi": "Say in Turkish as an excited, fast, joyful football fan who laughs and shouts with enthusiasm",
    "yuru": "Say in Turkish slowly and calmly, in a dry, deadpan, sarcastic tone, like an unimpressed older brother",
}


def _tek_replik(model, r, yol):
    """Tek replik → wav (kendi sesi ve üslubuyla). İsimler okunmaz, her karakter kendi sesinde."""
    govde = {
        "contents": [{"role": "user", "parts": [{"text": f"{STIL[r['kim']]}: {okunus(r['metin'])}"}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": SES[r["kim"]]}}}},
    }
    for deneme in range(3):
        try:
            y = _gemini(f"{model}:generateContent", govde)
            parca = y["candidates"][0]["content"]["parts"][0]["inlineData"]
            break
        except (RuntimeError, KeyError, IndexError) as e:
            if deneme == 2:
                raise RuntimeError(f"replik TTS: {e}") from None
    oran = int((re.search(r"rate=(\d+)", parca.get("mimeType", "")) or [0, 24000])[1])
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
        f.write(base64.b64decode(parca["data"]))
        ham = f.name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(oran), "-ac", "1", "-i", ham,
                    "-af", "silenceremove=start_periods=1:start_threshold=-50dB,areverse,"
                          "silenceremove=start_periods=1:start_threshold=-50dB,areverse",
                    "-ar", "44100", "-ac", "1", yol], check=True)
    os.remove(ham)


def birlestir(wavlar, senaryo, cikti, motor):
    """Replik seslerini 0,35 sn araliklarla birleştirir; replik zamanlarını <çıktı>.zaman.json'a yazar."""
    d = tempfile.mkdtemp()
    sus = os.path.join(d, "sus.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", "0.35", sus], check=True)
    liste = os.path.join(d, "liste.txt")
    zaman, t = [], 0.0
    with open(liste, "w") as lf:
        for w, r in zip(wavlar, senaryo["replikler"]):
            sn = sure(w)
            zaman.append({"kim": r["kim"], "bas": round(t, 3), "son": round(t + sn, 3), "metin": r["metin"],
                          "duygu": r.get("duygu")})
            t += sn + 0.35
            lf.write(f"file '{w}'\nfile '{sus}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                    "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-b:a", "128k", cikti], check=True)
    json.dump(zaman, open(cikti + ".zaman.json", "w"), ensure_ascii=False)
    notice("Podcast sesi", f"{os.path.basename(cikti)} ({motor}; {len(wavlar)} replik, replik replik)")


def gemini_ses(senaryo, cikti):
    model = tts_modeli()
    d = tempfile.mkdtemp()
    from concurrent.futures import ThreadPoolExecutor
    wavlar = [os.path.join(d, f"{i:03d}.wav") for i in range(len(senaryo["replikler"]))]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda ir: _tek_replik(model, ir[1], wavlar[ir[0]]), enumerate(senaryo["replikler"])))
    birlestir(wavlar, senaryo, cikti, f"Gemini {model}, {SES['hadi']}/{SES['yuru']}")


def google_ses(senaryo, cikti):
    import seslendir
    d = tempfile.mkdtemp()
    wavlar = []
    for i, r in enumerate(senaryo["replikler"]):
        wav = seslendir.seslendir(r["metin"], r["kim"], os.path.join(d, f"{i:03d}.mp3"))
        if not wav:
            raise RuntimeError("GOOGLE_TTS_KEY yok")
        norm = os.path.join(d, f"{i:03d}n.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "44100", norm], check=True)
        wavlar.append(norm)
    birlestir(wavlar, senaryo, cikti, "Google Chirp3-HD")


def sure(yol):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


if __name__ == "__main__":
    senaryo = json.load(open(sys.argv[1], encoding="utf-8"))
    cikti, motor = sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "gemini")
    try:
        (gemini_ses if motor == "gemini" else google_ses)(senaryo, cikti)
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Podcast {motor} hatası::{str(e)[:600]}", flush=True)
        sys.exit(1)
    notice("Podcast süresi", f"{os.path.basename(cikti)}: {sure(cikti):.0f} sn")
