"""Türkçe erkek seslerin numaralı kataloğu (dinleyip seçmek için).

Kullanım: GOOGLE_TTS_KEY=... python3 video/ses_katalogu.py cikti.mp4
Her ses aynı cümleyi söyler; ekranda numara ve ses adı yazar. Sonuç tek bir dikey video.
"""
import os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seslendir  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
F_B = f"{KOK}/assets/kart/ArchivoBlack.ttf"
F_M = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CUMLE = "Bu hafta şampiyon Beşiktaş! Kasımpaşa'da bire iki alırız, yaparız baba!"


def kart(no, ad, yol):
    im = Image.new("RGB", (1080, 1920), (17, 22, 34))
    d = ImageDraw.Draw(im)
    f1, f2 = ImageFont.truetype(F_B, 420), ImageFont.truetype(F_M, 52)
    for metin, f, y, renk in ((str(no), f1, 560, (255, 204, 64)), (ad.replace("tr-TR-", ""), f2, 1120, (250, 248, 244))):
        w = d.textlength(metin, font=f)
        d.text(((1080 - w) / 2, y), metin, font=f, fill=renk)
    im.save(yol)


def main():
    cikti = sys.argv[1]
    tmp = cikti + ".parca"
    os.makedirs(tmp, exist_ok=True)
    sesler = seslendir.turkce_sesler()
    erkek = sorted(a for a, g in sesler.items() if g == "MALE" and "Studio" not in a)
    # önce en doğal (Chirp3-HD), sonra diğerleri
    erkek.sort(key=lambda a: (0 if "Chirp3" in a else 1 if "Wavenet" in a or "Neural" in a else 2, a))
    liste, parcalar = [], []
    for i, ad in enumerate(erkek, 1):
        mp3 = f"{tmp}/{i}.mp3"
        r = seslendir._istek("text:synthesize", {"input": {"text": f"{i}. {CUMLE}"},
                                                 "voice": {"languageCode": "tr-TR", "name": ad},
                                                 "audioConfig": {"audioEncoding": "MP3", "sampleRateHertz": 44100}})
        import base64
        open(mp3, "wb").write(base64.b64decode(r["audioContent"]))
        png = f"{tmp}/{i}.png"
        kart(i, ad, png)
        mp4 = f"{tmp}/{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", png, "-i", mp3,
                        "-af", "apad=pad_dur=0.6", "-shortest", "-c:v", "libx264", "-preset", "veryfast",
                        "-tune", "stillimage", "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-ar", "44100",
                        "-ac", "2", mp4], check=True)
        parcalar.append(mp4)
        liste.append(f"{i}. {ad}")
    with open(f"{tmp}/liste.txt", "w") as f:
        f.writelines(f"file '{os.path.abspath(p)}'\n" for p in parcalar)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{tmp}/liste.txt",
                    "-c", "copy", "-movflags", "+faststart", cikti], check=True)
    print("::notice title=Ses kataloğu::" + " | ".join(liste))


if __name__ == "__main__":
    main()
