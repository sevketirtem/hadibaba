"""Hadi vs Yürü podcast bölümünü seslendirir → MP3.

Kullanım: python scripts/podcast_ses.py <senaryo.json> <çıktı.mp3> [gemini|google]
  gemini: Gemini TTS, iki konuşmacılı tek seferde (GEMINI_API_KEY). Sesler: Hadi=Umbriel, Yürü=Algenib.
  google: Google Cloud TTS (Chirp 3 HD), replik replik + birleştirme (GOOGLE_TTS_KEY; video/seslendir.py).
Senaryo biçimi: {"tarih","baslik","aciklama","replikler":[{"kim":"hadi|yuru","metin":"..."}]}
"""
import base64, json, os, re, subprocess, sys, tempfile, urllib.error, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "video"))
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
    req = urllib.request.Request(f"{API}/{yol}", data=json.dumps(govde).encode(), method="POST",
                                 headers={"Content-Type": "application/json",
                                          "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Gemini TTS HTTP {e.code}: {e.read()[:300]!r}") from None


def tts_modeli():
    istenen = os.environ.get("GEMINI_TTS_MODEL", "").strip()
    if istenen:
        return istenen if istenen.startswith("models/") else "models/" + istenen
    req = urllib.request.Request(f"{API}/models?pageSize=1000",
                                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        adlar = [m["name"] for m in json.loads(r.read()).get("models", []) if "tts" in m["name"]]
    if not adlar:
        raise RuntimeError("TTS modeli bulunamadı")
    notice("Gemini TTS modelleri", ", ".join(adlar))
    adlar.sort(key=lambda n: ("flash" not in n, "lite" in n, "preview" in n, n))
    return adlar[0]


def gemini_ses(senaryo, cikti):
    model = tts_modeli()
    satirlar = "\n".join(f"{AD[r['kim']]}: {okunus(r['metin'])}" for r in senaryo["replikler"])
    metin = ("Aşağıdaki Türkçe futbol podcast'ini iki kişi seslendirsin. "
             "Hadi: coşkulu taraftar; hızlı, enerjik, gülerek ve ünlemle konuşur. "
             "Yürü: alaycı abi; sakin, ağır, kuru ve iğneleyici konuşur, acele etmez.\n\n" + satirlar)
    govde = {
        "contents": [{"parts": [{"text": metin}]}],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": [
                {"speaker": AD[k], "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": SES[k]}}}
                for k in ("hadi", "yuru")]}},
        },
    }
    y = _gemini(f"{model}:generateContent", govde)
    parca = y["candidates"][0]["content"]["parts"][0]["inlineData"]
    oran = int((re.search(r"rate=(\d+)", parca.get("mimeType", "")) or [0, 24000])[1])
    with tempfile.NamedTemporaryFile(suffix=".pcm", delete=False) as f:
        f.write(base64.b64decode(parca["data"]))
        ham = f.name
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(oran), "-ac", "1", "-i", ham,
                    "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-b:a", "128k", cikti], check=True)
    os.remove(ham)
    notice("Podcast sesi", f"{os.path.basename(cikti)} (Gemini {model}, {SES['hadi']}/{SES['yuru']})")


def google_ses(senaryo, cikti):
    import seslendir
    d = tempfile.mkdtemp()
    liste = os.path.join(d, "liste.txt")
    sus = os.path.join(d, "sus.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                    "-t", "0.35", sus], check=True)
    with open(liste, "w") as lf:
        for i, r in enumerate(senaryo["replikler"]):
            wav = seslendir.seslendir(r["metin"], r["kim"], os.path.join(d, f"{i:03d}.mp3"))
            if not wav:
                raise RuntimeError("GOOGLE_TTS_KEY yok")
            norm = os.path.join(d, f"{i:03d}n.wav")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1", "-ar", "44100", norm], check=True)
            lf.write(f"file '{norm}'\nfile '{sus}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", liste,
                    "-af", "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-b:a", "128k", cikti], check=True)
    notice("Podcast sesi", f"{os.path.basename(cikti)} (Google Chirp3-HD)")


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
