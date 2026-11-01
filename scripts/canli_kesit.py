"""Canlı yayın kaydından (Hadi vs Yürü Canlı) dikey kesitler üretir.

Kullanım: python scripts/canli_kesit.py <yayin.mp4> <cikti_klasoru> [adet]
1) Whisper (faster-whisper small) Türkçe döküm + kelime zamanları.
2) Gemini (gapi: Vertex önce) dökümü okuyup en iyi 30–60 sn'lik bölümleri, başlık ve kancayı seçer.
3) Her bölüm için 1080x1920 video: bulanık zemin + yayın görüntüsü ortada, ilk 2,5 sn kanca,
   altta satır satır altyazı, üstte "HADİ vs YÜRÜ CANLI", altta alan adları (KESIT_SADE=1 → alan adı yok).
Çıktı: <klasör>/kesit-<n>.mp4, kesit-<n>-sade.mp4, kesitler.json, doküm.txt
"""
import json, os, re, subprocess, sys, textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gapi  # noqa: E402

F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def dokum(mp4):
    import numpy as np
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", mp4, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    ses = np.frombuffer(ham, np.int16).astype(np.float32) / 32768.0
    segs, _ = m.transcribe(ses, language="tr", word_timestamps=True, vad_filter=True, beam_size=1)
    out = []
    for s in segs:
        out.append({"bas": round(s.start, 2), "son": round(s.end, 2), "metin": s.text.strip(),
                    "kelimeler": [[round(w.start, 2), round(w.end, 2), w.word.strip()] for w in (s.words or [])]})
    return out


def sec(segs, adet):
    satirlar = "\n".join(f"[{s['bas']:.0f}-{s['son']:.0f}] {s['metin']}" for s in segs)
    istem = (
        "Aşağıda Türkçe bir futbol canlı yayınının dökümü var (köşeli parantezde saniye). Yayında iki kişi var: "
        "coşkulu 'Hadi' ve alaycı 'Yürü' rolündeki iki arkadaş. YouTube Shorts / Reels / TikTok için kendi başına anlaşılan, "
        f"en ilgi çekici, en komik ya da en tartışmalı {adet} bölüm seç. Her biri 30–60 saniye, cümle ortasında başlayıp bitmesin. "
        "Bahis/kupon/oran içeren, gerçek kişiye hakaret ya da doğrulanmamış suçlama içeren bölümleri SEÇME. "
        "Her bölüm için kısa Türkçe başlık (en fazla 60 karakter) ve ilk 2 saniyede ekranda yazacak kanca (2–6 kelime, en fazla 36 karakter) yaz. "
        'Yalnızca JSON döndür: {"kesitler":[{"bas":sn,"son":sn,"baslik":"...","kanca":"...","neden":"..."}]}\n\n' + satirlar[:180000])
    y = gapi.istek(f"models/{os.environ.get('GEMINI_METIN_MODEL', 'gemini-3.8-flash')}:generateContent",
                   {"contents": [{"role": "user", "parts": [{"text": istem}]}],
                    "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4}}, 300)
    metin = "".join(p.get("text", "") for p in y["candidates"][0]["content"]["parts"])
    return json.loads(re.search(r"\{.*\}", metin, re.S)[0])["kesitler"]


def esc(t):
    return t.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")


def render(mp4, k, segs, cikti, sade, klasor, n):
    bas, son = float(k["bas"]), float(k["son"])
    sure = son - bas
    p = [f"drawtext=fontfile={F}:text='HADİ vs YÜRÜ CANLI':fontcolor=white:fontsize=46:borderw=4:bordercolor=0x0A0C14:x=(w-tw)/2:y=230"]
    kanca = "\n".join(textwrap.wrap(k.get("kanca", "").upper(), 16))
    if kanca:
        open(f"{klasor}/k{n}.txt", "w").write(kanca)
        p.append(f"drawtext=fontfile={F}:textfile={klasor}/k{n}.txt:text_align=C:fontcolor=0xFFCC40:fontsize=96:line_spacing=14:"
                 f"borderw=8:bordercolor=0x0A0C14:x=(w-tw)/2:y=(h-th)/2:enable='lt(t,2.5)'")
    i = 0
    for s in segs:
        if s["son"] < bas or s["bas"] > son:
            continue
        a, b = max(0, s["bas"] - bas), min(sure, s["son"] - bas)
        t = "\n".join(textwrap.wrap(s["metin"], 30)[:3])
        open(f"{klasor}/a{n}_{i}.txt", "w").write(t)
        p.append(f"drawtext=fontfile={F}:textfile={klasor}/a{n}_{i}.txt:text_align=C:fontcolor=white:fontsize=58:line_spacing=12:"
                 f"borderw=6:bordercolor=0x0A0C14:x=(w-tw)/2:y=1330:enable='between(t,{a:.2f},{b:.2f})*gte(t,2.5)'")
        i += 1
    if not sade:
        p.append(f"drawtext=fontfile={F}:text='hadibaba.com · yurubaba.com':fontcolor=0xB8CBE3:fontsize=38:borderw=3:"
                 f"bordercolor=0x0A0C14:x=(w-tw)/2:y=h-110")
    fs = ("[0:v]split[a][b];[a]scale=-2:1920,crop=1080:1920,boxblur=30:2,eq=brightness=-0.3[bg];[b]scale=1080:-2[fg];"
          "[bg][fg]overlay=0:(H-h)/2-200," + ",".join(p) + "[v]")
    open(f"{klasor}/f{n}{'s' if sade else ''}.txt", "w").write(fs)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{bas:.2f}", "-t", f"{sure:.2f}", "-i", mp4,
                    "-filter_complex_script", f"{klasor}/f{n}{'s' if sade else ''}.txt", "-map", "[v]", "-map", "0:a:0",
                    "-af", "loudnorm=I=-15:TP=-1.5", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
                    "-pix_fmt", "yuv420p", "-r", "30", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", cikti],
                   check=True)


def main():
    mp4, klasor = sys.argv[1], sys.argv[2]
    adet = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    os.makedirs(klasor, exist_ok=True)
    segs = dokum(mp4)
    open(f"{klasor}/dokum.txt", "w").write("\n".join(f"[{s['bas']:.0f}-{s['son']:.0f}] {s['metin']}" for s in segs))
    notice("Döküm", f"{len(segs)} parça, son {segs[-1]['son']:.0f} sn" if segs else "boş")
    ks = sec(segs, adet)
    json.dump(ks, open(f"{klasor}/kesitler.json", "w"), ensure_ascii=False, indent=1)
    for n, k in enumerate(ks, 1):
        try:
            render(mp4, k, segs, f"{klasor}/kesit-{n}.mp4", False, klasor, n)
            render(mp4, k, segs, f"{klasor}/kesit-{n}-sade.mp4", True, klasor, n)
            notice(f"Kesit {n}", f"{k['bas']}-{k['son']} sn · {k.get('baslik')} · kanca: {k.get('kanca')}")
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Kesit {n}::{e}")
    for f in os.listdir(klasor):
        if f.endswith(".txt") and f != "dokum.txt":
            os.remove(os.path.join(klasor, f))


if __name__ == "__main__":
    main()
