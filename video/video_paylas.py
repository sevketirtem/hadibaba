"""Günün atışma videosunu paylaşır: Telegram (iki kanal), Instagram Reels, Facebook Sayfası, Threads.

Kullanım: python3 video/video_paylas.py <senaryo.json> <yerel_video.mp4> <yayındaki_video_adresi>
Her platform bağımsızdır; biri hata verirse diğerleri devam eder. Paylaşılanlar
video/paylasildi.txt dosyasına yazılır, aynı gün ikinci kez paylaşılmaz.
Ortam: TELEGRAM_BOT_TOKEN, TELEGRAM_KANALLAR (virgüllü), META_PAGE_TOKEN, META_SAYFA_ADI, THREADS_TOKEN,
       DRY_RUN=true ise hiçbir şey göndermez, sadece ne yapacağını yazar.
"""
import json, os, sys, time, uuid, urllib.error, urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(KOK, "scripts"))
import meta  # noqa: E402

KAYIT = os.path.join(KOK, "video", "paylasildi.txt")
ETIKETLER = "#futbol #süperlig #türkfutbolu #hadibaba #yurubaba"


def notice(baslik, mesaj, tur="notice"):
    print(f"::{tur} title={baslik}::{mesaj}", flush=True)


def kayitlar():
    if not os.path.exists(KAYIT):
        return set()
    return {s.strip() for s in open(KAYIT, encoding="utf-8") if s.strip()}


def kaydet(anahtar):
    with open(KAYIT, "a", encoding="utf-8") as f:
        f.write(anahtar + "\n")


def metin(s, uzun=True):
    y = s.get("yazilar", {})
    parcalar = [s.get("aciklama", s["mac"])]
    if uzun and y:
        parcalar.append("\n".join(x for x in (
            f"🔥 Hadi: {y['hadi']}" if y.get("hadi") else "",
            f"🧮 Yürü: {y['yuru']}" if y.get("yuru") else "") if x))
    parcalar.append(ETIKETLER)
    return "\n\n".join(p for p in parcalar if p)


# ---------------------------------------------------------------- Telegram (dosya yükleme)

def telegram_video(token, kanal, dosya, aciklama):
    sinir = uuid.uuid4().hex
    govde = []
    for ad, deger in (("chat_id", kanal), ("caption", aciklama[:1024]), ("supports_streaming", "true"),
                      ("width", "1080"), ("height", "1920")):
        govde.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{ad}"\r\n\r\n{deger}\r\n'.encode())
    govde.append(f'--{sinir}\r\nContent-Disposition: form-data; name="video"; filename="atisma.mp4"\r\n'
                 f'Content-Type: video/mp4\r\n\r\n'.encode())
    govde.append(open(dosya, "rb").read())
    govde.append(f"\r\n--{sinir}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendVideo", data=b"".join(govde),
                                 headers={"Content-Type": f"multipart/form-data; boundary={sinir}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["result"]["message_id"]
    except urllib.error.HTTPError as e:
        aciklama_ = json.loads(e.read() or b"{}").get("description", "")
        raise RuntimeError(f"Telegram sendVideo -> HTTP {e.code}: {aciklama_}") from None


# ---------------------------------------------------------------- Meta

def instagram_reels(page_token, ig_id, video_url, aciklama):
    kap = meta.istek("POST", f"{meta.GRAPH}/{ig_id}/media", {
        "media_type": "REELS", "video_url": video_url, "caption": aciklama[:2200],
        "share_to_feed": "true", "access_token": page_token,
    })["id"]
    meta._bekle(f"{meta.GRAPH}/{kap}", "status_code", page_token, sure=300)
    return meta.istek("POST", f"{meta.GRAPH}/{ig_id}/media_publish", {
        "creation_id": kap, "access_token": page_token,
    }).get("id")


def facebook_video(page_token, page_id, video_url, aciklama, baslik):
    return meta.istek("POST", f"https://graph-video.facebook.com/v25.0/{page_id}/videos", {
        "file_url": video_url, "description": aciklama, "title": baslik[:250], "access_token": page_token,
    }).get("id")


def threads_video(th_token, video_url, aciklama):
    kap = meta.istek("POST", f"{meta.THREADS}/me/threads", {
        "media_type": "VIDEO", "video_url": video_url, "text": aciklama[:meta.THREADS_SINIRI],
        "access_token": th_token,
    })["id"]
    meta._bekle(f"{meta.THREADS}/{kap}", "status", th_token, sure=300)
    return meta.istek("POST", f"{meta.THREADS}/me/threads_publish", {
        "creation_id": kap, "access_token": th_token,
    }).get("id")


def main():
    senaryo, dosya, video_url = sys.argv[1:4]
    s = json.load(open(senaryo, encoding="utf-8"))
    gun = s["tarih"]
    dry = os.environ.get("DRY_RUN", "false").lower() == "true"
    yapilan = kayitlar()
    sonuc = {}

    def calistir(platform, fonk):
        anahtar = f"{gun} {platform}"
        if anahtar in yapilan:
            notice(f"Video {platform}", "daha önce paylaşılmış, atlandı")
            return
        if dry:
            notice(f"Video {platform}", "DENEME: paylaşılacaktı")
            return
        try:
            kimlik = fonk()
            kaydet(anahtar)
            sonuc[platform] = kimlik
            notice(f"Video {platform}", f"paylaşıldı ({kimlik})")
        except Exception as e:  # noqa: BLE001
            notice(f"Video {platform}", f"gönderilemedi: {e}", "warning")

    tg = os.environ.get("TELEGRAM_BOT_TOKEN")
    for kanal in [k.strip() for k in os.environ.get("TELEGRAM_KANALLAR", "").split(",") if k.strip()]:
        if tg:
            calistir(f"telegram{kanal}", lambda k=kanal: telegram_video(tg, k, dosya, metin(s)))

    page_token = os.environ.get("META_PAGE_TOKEN")
    if page_token:
        try:
            k = meta.sayfa_kimlikleri(page_token, os.environ.get("META_SAYFA_ADI") or None)
        except Exception as e:  # noqa: BLE001
            notice("Video Meta", f"Sayfa bulunamadı: {e}", "warning")
            k = None
        if k:
            calistir("facebook", lambda: facebook_video(k["page_token"], k["page_id"], video_url, metin(s),
                                                        f"Hadi vs Yürü: {s['mac']}"))
            if k.get("ig_id"):
                calistir("instagram", lambda: instagram_reels(k["page_token"], k["ig_id"], video_url, metin(s, uzun=False)))
    th = os.environ.get("THREADS_TOKEN")
    if th:
        calistir("threads", lambda: threads_video(th, video_url, metin(s, uzun=False)))
    if not dry and not sonuc and not any(a.startswith(gun) for a in yapilan):
        notice("Video", "hiçbir platformda paylaşılamadı", "warning")


if __name__ == "__main__":
    main()
