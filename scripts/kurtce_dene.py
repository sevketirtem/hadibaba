"""Kurmancî (Kürtçe) TTS denemesi: Hadi (Fenrir) ve Yürü (Algenib) Kurmancî konuşabiliyor mu?

Whisper Kürtçeyi tanımıyor → kontrolü Gemini yapar: sesi dinler, yazıya döker, Kurmancî telaffuzu puanlar.
Çıktı: kurtce-dene/*.wav + rapor.json → kurtce-dene-cikti dalı.
"""
import base64, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import gapi

TTS = "models/gemini-3.8-flash-tts"
METIN = f"models/{os.environ.get('GEMINI_METIN_MODEL', 'gemini-3.8-flash')}"

REPLIKLER = {
    "hadi": "Silav hevalno! Vê şemiyê Amed li Stenbolê ye. Ez pir kêfxweş im, dilê min lê dixe! Werin em bi hev re temaşe bikin!",
    "yuru": "Hêdî hêdî Hadî. Maç hê dest pê nekiriye, tu ji niha ve gol davêjî.",
    # Türkçe içine Kurmancî serpiştirme (atışmalarda en olası kullanım)
    "hadi-karisik": "Yürü, bu akşam Amed taraftarına bir selam verelim mi? Silav li we be, Amedî! Bi xêr hatin!",
}

PROFIL = {
    "hadi": ("Hadi", "Fenrir", "A very excited, joyful, restless young football fan.",
             "Style: very excited, energetic, laughing. Pace: fast."),
    "yuru": ("Yürü", "Algenib", "Hadi's dry, sarcastic, unimpressed older friend.",
             "Style: dry, deadpan, sarcastic. Pace: slow and calm."),
}


def yonetmen(kim, metin, aksan):
    ad, _, profil, notlar = PROFIL[kim]
    return (f"# AUDIO PROFILE: {ad}\n{profil}\n\n## THE SCENE\nTwo friends banter in a lively football podcast.\n\n"
            f"### DIRECTOR'S NOTES\n{notlar} {aksan}\n\n#### TRANSCRIPT\n{metin}")


def varyantlar():
    ku = "Language: Northern Kurdish (Kurmanji). Accent: native Kurmanji speaker from Diyarbakır (Amed)."
    karisik = "Language: Turkish, with the Kurmanji Kurdish sentences spoken by a native Kurmanji speaker from Diyarbakır."
    v = []
    for kim, anahtar in (("hadi", "hadi"), ("yuru", "yuru")):
        v.append((anahtar, "yonetmen", kim, yonetmen(kim, REPLIKLER[anahtar], ku)))
        v.append((anahtar, "duz", kim, REPLIKLER[anahtar]))
    v.append(("hadi-karisik", "yonetmen", "hadi", yonetmen("hadi", REPLIKLER["hadi-karisik"], karisik)))
    return v


def wav(parca, yol):
    oran = int((re.search(r"rate=(\d+)", parca.get("mimeType", "")) or [0, 24000])[1])
    ham = tempfile.mktemp(suffix=".pcm")
    open(ham, "wb").write(base64.b64decode(parca["data"]))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(oran), "-ac", "1", "-i", ham, yol], check=True)


def sure(y):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", y],
                                capture_output=True, text=True).stdout)


def dinle(yol, beklenen):
    mp3 = yol + ".mp3"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", yol, "-ac", "1", "-b:a", "64k", mp3], check=True)
    istem = ("Listen to this speech clip. Expected text (may mix Turkish and Northern Kurdish/Kurmanji):\n"
             f"{beklenen}\n\nAnswer ONLY JSON: {{\"duyulan\": \"exact transcription\", "
             "\"dil\": \"languages you hear\", \"kurmanci_puan\": 0-10 (how natural/intelligible the Kurmanji is to a "
             "native speaker from Diyarbakır; 0 if no Kurmanji), \"turk_aksani\": true/false, "
             "\"talimat_okundu\": true/false (did it read stage directions aloud), \"not\": \"short note in Turkish\"}")
    govde = {"contents": [{"parts": [{"inline_data": {"mime_type": "audio/mpeg",
                                                      "data": base64.b64encode(open(mp3, "rb").read()).decode()}},
                                     {"text": istem}]}],
             "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    y = gapi.istek(f"{METIN}:generateContent", govde, 180)
    return json.loads(re.search(r"\{.*\}", "".join(p.get("text", "") for p in y["candidates"][0]["content"]["parts"]), re.S)[0])


def main():
    os.makedirs("kurtce-dene", exist_ok=True)
    rapor = []
    for anahtar, ad, kim, istem in varyantlar():
        ses = PROFIL[kim][1]
        yol = f"kurtce-dene/{anahtar}-{ad}-{ses}.wav"
        kayit = {"dosya": yol, "replik": REPLIKLER[anahtar]}
        govde = {"contents": [{"role": "user", "parts": [{"text": istem}]}],
                 "generationConfig": {"responseModalities": ["AUDIO"],
                                      "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": ses}}}}}
        try:
            y = gapi.istek(f"{TTS}:generateContent", govde, 300)
            wav(y["candidates"][0]["content"]["parts"][0]["inlineData"], yol)
            kayit["sure"] = round(sure(yol), 1)
            kayit["gemini"] = dinle(yol, REPLIKLER[anahtar])
        except Exception as e:  # noqa: BLE001
            kayit["hata"] = str(e)[:400]
        print(f"::notice title=Kurmancî {anahtar}-{ad}::{json.dumps(kayit, ensure_ascii=False)[:900]}")
        rapor.append(kayit)
    json.dump(rapor, open("kurtce-dene/rapor.json", "w"), ensure_ascii=False, indent=1)


main()
