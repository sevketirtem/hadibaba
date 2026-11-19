"""Hadi vs Yürü komedi filmi: Veo (sessiz sahneler) + Gemini TTS (sesler) + ffmpeg → TR ve EN, yatay ve dikey.
Kullanım: python scripts/komedi_film.py video/film/<ad>.json <cikti_klasoru>
Ortam: GOOGLE_VERTEX_TOKEN (Veo + TTS). Sesler yalnızca Gemini TTS (sahibinin kuralı)."""
import json, os, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
sys.path.insert(0, os.path.join(KOK, "video"))
import veo_video, podcast_ses

REF_HADI, REF_YURU = f"{KOK}/assets/kart/ref-hadi.png", f"{KOK}/assets/kart/ref-yuru.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
EN_PROFIL = {
    "hadi": ("Hadi", "Cheerful, excitable sailor on a lookout post in a comedy short film. Loud, panicky, easily thrilled.",
             "Style: very excited, energetic, almost shouting. Pace: fast. Accent: light Turkish accent in English."),
    "yuru": ("Yuru", "The ship's deadpan captain in a comedy short film. Dry, sarcastic, unimpressed.",
             "Style: dry, deadpan, weary. Pace: slow and calm. Accent: light Turkish accent in English."),
}
DUYGU = {"cagir": " Right now: bellowing at the top of his lungs up to a lookout far above, cupped hands, gruff captain voice, long drawn-out last syllable, very loud and projected.", "sakin": " Right now: perfectly calm, flat.", "bagir": " Right now: shouting at the top of his lungs in sudden panic, stretching the long vowels.",
         "uzgun": " Right now: very tired, sighing, resigned.", "kikir": " Right now: nervous giggling, guilty, defensive, fast."}


def sh(*a):
    subprocess.run(a, check=True)


def sure(y):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", y],
                                capture_output=True, text=True).stdout)


def sahne_uret(s, stil, d):
    yol = f"{d}/sahne-{s['ad']}.mp4"
    if os.path.exists(yol):
        return yol
    for deneme in range(3):
        try:
            os.environ["VEO_EK_REFERANS"] = REF_HADI
            if deneme >= 1:
                os.environ["VEO_COZUNURLUK"] = "720p"  # referans + 1080p desteklenmezse
            veo_video.vertex_veo(REF_YURU, yol, f"{s['istem']} Style: {stil}")
            return yol
        except RuntimeError as e:
            print(f"::warning title=Veo {s['ad']} deneme {deneme+1}::{str(e)[:300]}", flush=True)
    raise SystemExit(f"Sahne {s['ad']} üretilemedi")


def tek(model, r, yol):
    for deneme in range(5):
        try:
            return podcast_ses._tek_replik(model, r, yol)
        except Exception as e:  # zaman aşımı dahil
            print(f"::warning title=TTS deneme {deneme+1}::{str(e)[:200]}", flush=True)
    raise SystemExit("TTS üretilemedi")


def seslendir(dil, replikler, d):
    podcast_ses.DUYGU_NOT.update(DUYGU)
    if dil == "en":
        def yon(kim, metin, duygu=None):
            ad, profil, notlar = EN_PROFIL[kim]
            return (f"# AUDIO PROFILE: {ad}\n{profil}\n\n## THE SCENE\nA short slapstick comedy on a cargo ship.\n\n"
                    f"### DIRECTOR'S NOTES\n{notlar}{DUYGU.get(duygu or '', '')}\n\n#### TRANSCRIPT\n{metin}")
        podcast_ses.yonetmen = yon
    model = podcast_ses.tts_modeli()
    yollar = [f"{d}/{dil}-{i}.wav" for i in range(len(replikler))]
    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(lambda ir: tek(model, ir[1], yollar[ir[0]]), enumerate(replikler)))
    return yollar


def birlestir(dil, sahneler, klipler, replikler, sesler, baslangic, d, cikti):
    # 1) sahneleri kes ve birleştir (1280x720 ya da 1920x1080 olduğu gibi)
    liste = f"{d}/liste.txt"
    with open(liste, "w") as f:
        for s, k in zip(sahneler, klipler):
            kes = f"{d}/kes-{s['ad']}.mp4"
            sh("ffmpeg", "-y", "-v", "error", "-i", k, "-t", str(s["sure"]), "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
               "-r", "24", "-vf", "scale=1920:1080:flags=lanczos", kes)
            f.write(f"file '{kes}'\n")
    sessiz = f"{d}/sessiz.mp4"
    sh("ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", liste, "-c", "copy", sessiz)
    # 2) sesleri zamanla
    girdiler, filtre, etiket = [], [], []
    for i, (r, w) in enumerate(zip(replikler, sesler)):
        ms = int((baslangic[r["sahne"]] + r["bas"]) * 1000)
        girdiler += ["-i", w]
        filtre.append(f"[{i+1}:a]adelay={ms}|{ms},volume=1.6[a{i}]")
        etiket.append(f"[a{i}]")
    filtre.append("".join(etiket) + f"amix=inputs={len(sesler)}:normalize=0,loudnorm=I=-14:TP=-1.5[ses]")
    ses = f"{d}/ses-{dil}.m4a"
    sh("ffmpeg", "-y", "-v", "error", "-i", sessiz, *girdiler, "-filter_complex", ";".join(filtre), "-map", "[ses]",
       "-c:a", "aac", "-b:a", "160k", ses)
    # 3) altyazı (yatay ve dikey)
    ad = {"hadi": "HADİ", "yuru": "YÜRÜ"}
    for bicim, vf0, boy in (("yatay", "", 52), ("dikey", "crop=ih*9/16:ih,scale=1080:1920:flags=lanczos,", 56)):
        dr = []
        for i, r in enumerate(replikler):
            tf = f"{d}/yazi-{dil}-{bicim}-{i}.txt"
            open(tf, "w").write(f"{ad[r['kim']]}: {r['metin']}")
            t0 = baslangic[r["sahne"]] + r["bas"]
            t1 = t0 + sure(sesler[i]) + 0.4
            dr.append(f"drawtext=fontfile={FONT}:textfile={tf}:fontsize={boy}:fontcolor=white:borderw=4:bordercolor=black:"
                      f"x=(w-text_w)/2:y=h-h/7:enable='between(t,{t0:.2f},{t1:.2f})'")
        sh("ffmpeg", "-y", "-v", "error", "-i", sessiz, "-i", ses, "-vf", vf0 + ",".join(dr), "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", f"{cikti}/{dil}-{bicim}.mp4")


def main():
    spec = json.load(open(sys.argv[1]))
    cikti = sys.argv[2]
    d = os.path.join(cikti, "ara")
    os.makedirs(d, exist_ok=True)
    os.environ["VEO_ORAN"] = "16:9"
    os.environ["VEO_COZUNURLUK"] = "1080p"
    with ThreadPoolExecutor(max_workers=3) as ex:
        klipler = list(ex.map(lambda s: sahne_uret(s, spec["stil"], d), spec["sahneler"]))
    baslangic, t = {}, 0.0
    for s in spec["sahneler"]:
        baslangic[s["ad"]] = t
        t += s["sure"]
    for dil, replikler in spec["replikler"].items():
        sesler = seslendir(dil, replikler, d)
        birlestir(dil, spec["sahneler"], klipler, replikler, sesler, baslangic, d, cikti)
    json.dump(spec["baslik"], open(f"{cikti}/baslik.json", "w"), ensure_ascii=False)
    print("::notice title=Komedi film::bitti")


main()
