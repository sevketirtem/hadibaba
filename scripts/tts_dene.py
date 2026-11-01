"""Gemini TTS üslup denemesi: aynı repliği farklı istem biçimleriyle üretir, Whisper ile kontrol eder.
Talimat sesli okunuyor mu, konuşma hızı ne, hangisi daha canlı — annotation olarak yazar, wav'ları tts-dene dalına koyar."""
import base64, json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
import gapi

MODEL = "models/gemini-3.8-flash-tts"
HADI = "Ama önce manşet! Ben söylemek zorundayım: Yürü, Fenerbahçe Göztepe maçını tam skor bildi. Bire iki!"
YURU = "Borcum yok. Akşam bire bir bitince sen bana borçlu olacaksın, sakin ol."

PROFIL = {
    "hadi": ("Hadi", "Bir futbol podcastinde coşkulu, kıpır kıpır, heyecandan yerinde duramayan genç Türk taraftar. "
             "Hızlı konuşur, sesini yükseltir, arada güler, her şeye heyecanlanır.",
             "Style: very excited, energetic, joyful, laughing between words, almost shouting. Pace: fast. Accent: Istanbul Turkish."),
    "yuru": ("Yürü", "Aynı podcastte Hadi'nin ağır abi arkadaşı. Kuru, alaycı, istifini bozmayan, iğneleyici.",
             "Style: dry, deadpan, sarcastic, unimpressed older brother, slight smirk in the voice. Pace: slow and calm. Accent: Istanbul Turkish."),
}


def yonetmen(kim, metin):
    ad, profil, notlar = PROFIL[kim]
    return (f"# AUDIO PROFILE: {ad}\n{profil}\n\n## THE SCENE\nTwo friends banter and tease each other in a lively Turkish football podcast.\n\n"
            f"### DIRECTOR'S NOTES\n{notlar}\n\n#### TRANSCRIPT\n{metin}")


def varyantlar():
    v = []
    for ses in ("Fenrir", "Puck", "Umbriel"):
        v.append(("hadi", f"yonetmen-{ses}", ses, yonetmen("hadi", HADI)))
    v.append(("hadi", "etiket-Fenrir", "Fenrir", "[excited] [laughing] " + HADI))
    v.append(("hadi", "turkce-Fenrir", "Fenrir", "Çok heyecanlı ve coşkulu, gülerek söyle: " + HADI))
    for ses in ("Algenib", "Charon"):
        v.append(("yuru", f"yonetmen-{ses}", ses, yonetmen("yuru", YURU)))
    v.append(("yuru", "etiket-Algenib", "Algenib", "[sarcastic] " + YURU))
    return v


def wav(parca, yol):
    oran = int((re.search(r"rate=(\d+)", parca.get("mimeType", "")) or [0, 24000])[1])
    ham = tempfile.mktemp(suffix=".pcm")
    open(ham, "wb").write(base64.b64decode(parca["data"]))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "s16le", "-ar", str(oran), "-ac", "1", "-i", ham, yol], check=True)


def sure(y):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", y],
                                capture_output=True, text=True).stdout)


def main():
    import numpy as np
    from faster_whisper import WhisperModel
    wm = WhisperModel("small", device="cpu", compute_type="int8")
    os.makedirs("tts-dene", exist_ok=True)
    for kim, ad, ses, istem in varyantlar():
        yol = f"tts-dene/{kim}-{ad}.wav"
        govde = {"contents": [{"role": "user", "parts": [{"text": istem}]}],
                 "generationConfig": {"responseModalities": ["AUDIO"],
                                      "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": ses}}}}}
        try:
            y = gapi.istek(f"{MODEL}:generateContent", govde, 300)
            wav(y["candidates"][0]["content"]["parts"][0]["inlineData"], yol)
        except Exception as e:
            print(f"::warning title=TTS {kim}-{ad}::{str(e)[:300]}")
            continue
        ham = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(ham, np.int16).astype(np.float32) / 32768
        segs, _ = wm.transcribe(a, language=None, beam_size=5)
        yazi = " ".join(s.text.strip() for s in segs)
        print(f"::notice title=TTS {kim}-{ad} ({sure(yol):.1f} sn)::{yazi[:400]}")


main()
