"""Hadi ve Yürü için Türkçe seslendirme (Google Cloud Text-to-Speech, REST + API anahtarı).

Ortam değişkenleri:
  GOOGLE_TTS_KEY   Google Cloud API anahtarı (yalnızca Text-to-Speech API'ye izinli). Yoksa seslendirme atlanır.
  SES_HADI / SES_YURU   İsteğe bağlı ses adı (ör. tr-TR-Chirp3-HD-Puck). Boşsa listeden uygun erkek ses seçilir.

Ücretsiz kota: Chirp 3 HD ayda 1 milyon, WaveNet/Standard ayda 4 milyon karakter; günlük video ~300 karakter.
"""
import base64, json, os, re, urllib.error, urllib.request

API = "https://texttospeech.googleapis.com/v1"
SAYI = ["sıfır", "bir", "iki", "üç", "dört", "beş", "altı", "yedi", "sekiz", "dokuz"]
# Skor okunuşu: "1-2" → "bire iki" (ilk sayı yönelme hâlinde)
YONELME = ["sıfıra", "bire", "ikiye", "üçe", "dörde", "beşe", "altıya", "yediye", "sekize", "dokuza"]

# Karakter → tercih edilen sesler (sırayla denenir; listede olmayan atlanır)
# Sahibinin seçimi (29 Ekim 2026, ses kataloğu): Hadi 15 = Umbriel, Yürü 2 = Algenib
TERCIH = {
    "hadi": ["tr-TR-Chirp3-HD-Umbriel", "tr-TR-Chirp3-HD-Puck", "tr-TR-Wavenet-B", "tr-TR-Standard-B"],
    "yuru": ["tr-TR-Chirp3-HD-Algenib", "tr-TR-Chirp3-HD-Charon", "tr-TR-Wavenet-E", "tr-TR-Standard-E"],
}
# Seslendirmeden sonra uygulanan perde kaydırma (tempo korunur): Hadi daha ince, Yürü daha kalın.
# 1.09 ≈ +1,5 yarım ton; 1.0 = değişiklik yok
PERDE_CARPANI = {"hadi": 1.09, "yuru": 1.0}  # Yürü: sahibinin isteğiyle doğal perde
# Chirp 3 HD perde ayarı kabul etmez; hız ayarı her seste var
AYAR = {"hadi": {"speakingRate": 1.12}, "yuru": {"speakingRate": 0.95}}
AYAR_PERDE = {"hadi": 2.0, "yuru": -2.5}

_sesler = None


def _istek(yol, govde=None):
    anahtar = os.environ["GOOGLE_TTS_KEY"]
    url = f"{API}/{yol}{'&' if '?' in yol else '?'}key={anahtar}"
    veri = json.dumps(govde).encode() if govde is not None else None
    req = urllib.request.Request(url, data=veri, headers={"Content-Type": "application/json"},
                                 method="POST" if veri else "GET")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try:
            mesaj = json.loads(e.read()).get("error", {}).get("message", "")
        except Exception:  # noqa: BLE001
            mesaj = ""
        raise RuntimeError(f"Text-to-Speech {yol.split('?')[0]} -> HTTP {e.code}: {mesaj}") from None


def turkce_sesler():
    global _sesler
    if _sesler is None:
        liste = _istek("voices?languageCode=tr-TR").get("voices", [])
        _sesler = {v["name"]: v.get("ssmlGender") for v in liste}
    return _sesler


def ses_sec(kim):
    istenen = os.environ.get("SES_HADI" if kim == "hadi" else "SES_YURU", "").strip()
    sesler = turkce_sesler()
    if istenen and istenen in sesler:
        return istenen
    for ad in TERCIH[kim]:
        if ad in sesler:
            return ad
    erkekler = sorted(a for a, g in sesler.items() if g == "MALE")
    if not erkekler:
        raise RuntimeError("Türkçe erkek ses bulunamadı")
    return erkekler[0] if kim == "hadi" else erkekler[-1]


def okunus(metin):
    """Skorları doğal okunacak hâle getirir: 1-2 → 'bire iki', 1-1 → 'bire bir'."""
    metin = re.sub(r"\b(\d)\s*[-–]\s*(\d)\b", lambda m: f"{YONELME[int(m[1])]} {SAYI[int(m[2])]}", metin)
    metin = metin.replace("·", ",")
    return metin


def seslendir(metin, kim, cikti):
    if not os.environ.get("GOOGLE_TTS_KEY"):
        return None
    ad = ses_sec(kim)
    ayar = {"audioEncoding": "MP3", "sampleRateHertz": 44100, **AYAR[kim]}
    if "Chirp3" not in ad:
        ayar["pitch"] = AYAR_PERDE[kim]
    govde = {"input": {"text": okunus(metin)},
             "voice": {"languageCode": "tr-TR", "name": ad},
             "audioConfig": ayar}
    try:
        r = _istek("text:synthesize", govde)
    except RuntimeError:
        govde["audioConfig"] = {"audioEncoding": "MP3"}  # ayar kabul edilmezse sade dene
        r = _istek("text:synthesize", govde)
    ham = cikti + ".ham.mp3"
    with open(ham, "wb") as f:
        f.write(base64.b64decode(r["audioContent"]))
    k = float(os.environ.get("SES_PERDE_" + kim.upper(), PERDE_CARPANI[kim]))
    wav = os.path.splitext(cikti)[0] + ".wav"
    import subprocess
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", ham, "-af",
                    f"asetrate={int(44100 * k)},aresample=44100,atempo={1 / k:.5f}", wav], check=True)
    os.remove(ham)
    print(f"  ses: {kim} → {ad} (perde ×{k}, {len(metin)} karakter)")
    return wav
