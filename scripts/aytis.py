"""FUTBOL AYTISI — Hadi ile Yürü dombra eşliğinde kafiyeli düello (Kazak aytıs geleneği gibi), dikey Shorts.

Kullanım: python scripts/aytis.py video/aytis/aytis-<N>.json <çıkış klasörü>
Girdi JSON:
  {"tarih": "aytis-1", "seri_no": 1, "konu": "Kasımpaşa 2-2 Beşiktaş", "alt": "Süper Lig · 10. hafta",
   "kitalar": [{"kim": "hadi", "satirlar": ["...", "...", "...", "..."]}, {"kim": "yuru", ...}, ...],
   "nakarat": ["...", "..."] (isteğe bağlı, ikisi birlikte),
   "aciklama": "...", "yt_ek": "Seri: #FutbolAytısı", "yt_baslik": "..."}
Müzik + söz: Lyria 3.5 (Vertex deneme kredisi). Kontrol: faster-whisper sözleri dinler; sözlerle uyuşma
yetersizse yeniden üretir (en fazla AYTIS_DENEME, vars. 3); hiçbiri tutmazsa video ÇIKMAZ (hata).
Çıktı: <klasör>/dikey.mp4 ve sade.mp4.
"""
import difflib, json, os, re, shutil, subprocess, sys, tempfile, textwrap
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tahmin_ligi import AD, BOLD, FPS, H, LACI, RENK, SARI, TURUNCU, W, arka_plan, f, zarf_hesapla  # noqa: E402
from hareketli_avatar import HareketliAvatar  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESIK_IYI, ESIK_MIN, MAKS_SN = 0.50, 0.30, 95.0

SES = {"hadi": "a bright, excited, high-energy male tenor", "yuru": "a dry, calm, deadpan low male baritone"}


def istem(b):
    # Not: Lyria 3 Pro, köşeli etiketlerde karakter adı görünce istemi reddedebiliyor → etiketler adsız,
    # kim söyleyecek talimatta kıta numarasıyla verilir.
    parcalar, atama = [], []
    for i, k in enumerate(b["kitalar"], 1):
        parcalar.append(f"[Verse {i}]\n" + "\n".join(k["satirlar"]))
        atama.append(f"verse {i}: {SES[k['kim']]}")
    if b.get("nakarat"):
        parcalar.append("[Outro]\n" + "\n".join(b["nakarat"]))
        atama.append("outro: both voices together")
    return (
        "Kazakh folk song in the style of a playful sung duel between two friends: they take turns, each answering "
        "the other with a witty rhymed verse, accompanied by a solo Kazakh dombra (fast bright strumming, steppe feel) "
        "and a light frame drum. Cheerful, cheeky, energetic, about 112 BPM. Short dombra intro of at most 3 seconds, "
        "then the verses back to back with a short dombra riff between verses. Two clearly different voices: "
        + "; ".join(atama) + ". Lyrics are in Turkish; sing them clearly in Turkish. Use exactly these lyrics, in this "
        "order, do not add, repeat or drop any words. Original melody. Total length about 60 to 80 seconds, end with "
        "one final dombra strum.\n\n" + "\n\n".join(parcalar))


def norm(s):
    s = s.lower().replace("i̇", "i")
    return re.findall(r"[a-zçğıöşü0-9]+", s)


def satirlar(b):
    """[(kim, satır_metni, kıta_no)] — nakarat 'ikisi' olarak."""
    out = [(k["kim"], s, i) for i, k in enumerate(b["kitalar"]) for s in k["satirlar"]]
    out += [("ikisi", s, len(b["kitalar"])) for s in b.get("nakarat", [])]
    return out


def whisper_kelime(yol):
    import numpy as np
    from faster_whisper import WhisperModel
    m = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    ham = subprocess.run(["ffmpeg", "-v", "error", "-i", yol, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(ham, np.int16).astype(np.float32) / 32768.0
    segs, _ = m.transcribe(a, language="tr", word_timestamps=True, vad_filter=False, beam_size=5,
                           initial_prompt="Futbol aytısı, Hadi ile Yürü atışıyor.")
    return [(w2, w.start) for s in segs for w in (s.words or []) for w2 in norm(w.word)]


def hizala(b, kelimeler):
    """Her satırın başlama saniyesi + uyuşma oranı (sözlerin ne kadarı duyuldu)."""
    sat = satirlar(b)
    soz, sahip = [], []
    for j, (_, metin, _) in enumerate(sat):
        for w in norm(metin):
            soz.append(w)
            sahip.append(j)
    duy = [w for w, _ in kelimeler]
    sm = difflib.SequenceMatcher(None, soz, duy, autojunk=False)
    zaman = {}
    eslesen = 0
    for blk in sm.get_matching_blocks():
        for d in range(blk.size):
            zaman.setdefault(sahip[blk.a + d], []).append(kelimeler[blk.b + d][1])
            eslesen += 1
    oran = eslesen / max(1, len(soz))
    bas = [min(zaman[j]) if j in zaman else None for j in range(len(sat))]
    # Eksikleri komşulardan doğrusal doldur
    bilinen = [(j, t) for j, t in enumerate(bas) if t is not None]
    if not bilinen:
        return [], oran
    for j in range(len(bas)):
        if bas[j] is None:
            once = [(i, t) for i, t in bilinen if i < j]
            sonra = [(i, t) for i, t in bilinen if i > j]
            if once and sonra:
                (i0, t0), (i1, t1) = once[-1], sonra[0]
                bas[j] = t0 + (t1 - t0) * (j - i0) / (i1 - i0)
            elif once:
                bas[j] = once[-1][1] + 2.5 * (j - once[-1][0])
            else:
                bas[j] = max(0.0, sonra[0][1] - 2.5 * (sonra[0][0] - j))
    for j in range(1, len(bas)):  # sıralı olsun
        bas[j] = max(bas[j], bas[j - 1] + 0.3)
    return bas, oran


def muzik_uret(b, klasor):
    ist = os.path.join(klasor, "istem.txt")
    open(ist, "w", encoding="utf-8").write(istem(b))
    en = None
    for i in range(int(os.environ.get("AYTIS_DENEME", "3"))):
        hedef = os.path.join(klasor, f"aday-{i}.wav")
        r = subprocess.run([sys.executable, os.path.join(KOK, "scripts", "lyria_muzik.py"), ist, hedef])
        if r.returncode != 0:
            continue
        if not os.path.exists(hedef):
            hedef = hedef[:-4] + ".mp3"
        bas, oran = hizala(b, whisper_kelime(hedef))
        print(f"::notice title=Aytıs aday {i + 1}::sözlerin %{oran * 100:.0f}'i duyuldu", flush=True)
        if bas and (en is None or oran > en[1]):
            en = (hedef, oran, bas)
        if oran >= ESIK_IYI:
            break
    if en is None or en[1] < ESIK_MIN:
        raise SystemExit(f"::error title=Aytıs::Lyria sözleri net söylemedi (en iyi %{(en[1] if en else 0) * 100:.0f}); video çıkmadı")
    return en


def sure(yol):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", yol],
                                capture_output=True, text=True).stdout)


def render(b, muzik, bas, cikti):
    sat = satirlar(b)
    toplam = sure(muzik)
    son = min(toplam, bas[-1] + 7.0, MAKS_SN)
    ses = cikti + ".ses.m4a"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", muzik, "-t", f"{son:.2f}",
                    "-af", f"afade=t=out:st={max(0, son - 2):.2f}:d=2,loudnorm=I=-14:TP=-1.5", "-c:a", "aac", "-b:a", "192k", ses],
                   check=True)
    n = int(son * FPS)
    zarf = zarf_hesapla(ses, n)
    ha = HareketliAvatar(taban=420)
    bg = arka_plan()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", ses, "-map", "0:v", "-map", "1:a", "-c:v", "libx264",
                           "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p", "-c:a", "copy",
                           "-t", f"{son:.2f}", "-movflags", "+faststart", cikti], stdin=subprocess.PIPE)
    yum = 0.0
    for i in range(n):
        t = i / FPS
        yum = yum * 0.6 + zarf[i] * 0.4
        j = max([k for k in range(len(bas)) if bas[k] - 0.2 <= t] or [-1])
        kim = sat[j][0] if j >= 0 else None
        im = bg.copy()
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([270, 70, 810, 140], 35, fill=TURUNCU)
        d.text((W // 2, 105), f"FUTBOL AYTISI · #{b.get('seri_no', 1)}", font=f(40), fill="white", anchor="mm")
        d.text((W // 2, 215), "HADİ vs YÜRÜ", font=f(96), fill=SARI, anchor="mm", stroke_width=6, stroke_fill=(20, 24, 40))
        d.text((W // 2, 300), b.get("kz_baslik", "Футбол айтысы · dombra düellosu"), font=f(40, BOLD), fill=(230, 232, 240), anchor="mm")
        d.rounded_rectangle([90, 350, 990, 500], 30, fill=(255, 255, 255))
        d.text((W // 2, 405), b["konu"], font=f(52 if len(b["konu"]) < 26 else 40), fill=LACI, anchor="mm")
        d.text((W // 2, 465), b.get("alt", ""), font=f(30, BOLD), fill=(90, 100, 120), anchor="mm")
        for k, cx in (("hadi", 290), ("yuru", 790)):
            soyluyor = kim in (k, "ikisi")
            boy = int((360 if soyluyor else 290) * ((0.98 + 0.06 * yum) if soyluyor else 0.92))
            cy = 790
            if soyluyor:
                hal = Image.new("RGBA", (boy + 140, boy + 140), (0, 0, 0, 0))
                ImageDraw.Draw(hal).ellipse([30, 30, boy + 110, boy + 110], fill=SARI + (170,))
                im.alpha_composite(hal, (cx - (boy + 140) // 2, cy - (boy + 140) // 2))
            ImageDraw.Draw(im).ellipse([cx - boy // 2 - 14, cy - boy // 2 - 14, cx + boy // 2 + 14, cy + boy // 2 + 14],
                                       fill=SARI if soyluyor else (235, 235, 240))
            yuz = ha.kare(k, soyluyor, t, boy, "sevinc" if soyluyor and k == "hadi" else None) if ha.var else None
            if yuz is not None:
                im.alpha_composite(yuz, (cx - boy // 2, cy - boy // 2))
            d = ImageDraw.Draw(im)
            d.rounded_rectangle([cx - 90, cy + boy // 2 + 30, cx + 90, cy + boy // 2 + 80], 24, fill=RENK[k])
            d.text((cx, cy + boy // 2 + 55), AD[k], font=f(32), fill="white", anchor="mm")
        # Kıta: o anki kıtanın satırları, söylenen satır sarı
        if j >= 0:
            kita = sat[j][2]
            grup = [(m, s) for m, (_, s, q) in enumerate(sat) if q == kita]
            y = 1180
            for m, s in grup:
                parca = textwrap.wrap(s, 30)[:2]
                renk = SARI if m == j else (235, 238, 245)
                for p in parca:
                    d.text((W // 2, y), p, font=f(50 if m == j else 44, BOLD), fill=renk, anchor="ma",
                           stroke_width=5, stroke_fill=(15, 18, 30))
                    y += 66
                y += 14
        else:
            d.text((W // 2, 1300), "Dombra hazır… atış başlıyor!", font=f(52, BOLD), fill="white", anchor="mm",
                   stroke_width=5, stroke_fill=(15, 18, 30))
        d.text((W // 2, 1850), "hadibaba.com · yurubaba.com", font=f(34, BOLD), fill=(230, 230, 235), anchor="mm")
        ff.stdin.write(im.convert("RGB").tobytes())
    ff.stdin.close()
    if ff.wait() != 0:
        raise RuntimeError("ffmpeg başarısız")
    os.remove(ses)
    return son


def main():
    b = json.load(open(sys.argv[1], encoding="utf-8"))
    klasor = sys.argv[2]
    os.makedirs(klasor, exist_ok=True)
    tmp = tempfile.mkdtemp()
    muzik, oran, bas = muzik_uret(b, tmp)
    dikey = os.path.join(klasor, "dikey.mp4")
    son = render(b, muzik, bas, dikey)
    shutil.copy(dikey, os.path.join(klasor, "sade.mp4"))
    shutil.copy(muzik, os.path.join(klasor, "muzik" + os.path.splitext(muzik)[1]))
    print(f"::notice title=Futbol Aytısı::{b['tarih']} · {son:.1f} sn · sözlerin %{oran * 100:.0f}'i duyuldu · "
          f"{os.path.getsize(dikey) // 1024} KB", flush=True)


if __name__ == "__main__":
    main()
