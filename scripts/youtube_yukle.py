"""Podcast videosunu YouTube'a yükler (YouTube Data API v3, OAuth yenileme anahtarı; yalnızca standart kütüphane).

Kullanım: python scripts/youtube_yukle.py <senaryo.json> <video.mp4>
Ortam: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN (kanal sahibinin bir defalık izniyle alınır).
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def erisim_anahtari():
    veri = urllib.parse.urlencode({
        "client_id": os.environ["YOUTUBE_CLIENT_ID"], "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=veri, timeout=60) as r:
        return json.loads(r.read())["access_token"]


def main():
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    video = sys.argv[2]
    bolumler = json.load(open("podcast/bolumler.json", encoding="utf-8")) if os.path.exists("podcast/bolumler.json") else []
    no = next((b["no"] for b in bolumler if b["tarih"] == s["tarih"]), None)
    baslik = f"{s['baslik']} | Hadi vs Yürü" + (f" #{no}" if no else "")
    yazilar = "\n".join(f"• {u}" for u in s.get("yazilar", {}).values())
    aciklama = (f"{s['aciklama']}\n\nCoşkulu taraftar Hadi Baba ile alaycı abi Yürü Baba her gün Türk futbolunu tartışıyor. "
                f"Tahmininizi yorumlara yazın (skor, kupon değil; burada bahis yok).\n\n{yazilar}\n\n"
                "Podcast: Spotify'da \"Hadi vs Yürü\" · RSS: https://hadibaba.com/podcast/feed.xml\n"
                "Sesler ve görseller yapay zekâ ile üretilmiştir; karakterler hayalîdir.\n"
                "#futbol #süperlig #podcast")
    govde = {
        "snippet": {"title": baslik[:100], "description": aciklama[:4900], "categoryId": "17",
                    "defaultLanguage": "tr", "defaultAudioLanguage": "tr",
                    "tags": ["futbol", "süper lig", "podcast", "Hadi Baba", "Yürü Baba", "maç yorumu"]},
        "status": {"privacyStatus": os.environ.get("YOUTUBE_GIZLILIK", "public"),
                   "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }
    anahtar = erisim_anahtari()
    boyut = os.path.getsize(video)
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
        data=json.dumps(govde).encode(), method="POST",
        headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(boyut)})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            yukleme_url = r.headers["Location"]
        with open(video, "rb") as f:
            req2 = urllib.request.Request(yukleme_url, data=f.read(), method="PUT",
                                          headers={"Authorization": f"Bearer {anahtar}", "Content-Type": "video/mp4"})
        with urllib.request.urlopen(req2, timeout=900) as r:
            sonuc = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"::error title=YouTube::HTTP {e.code}: {e.read()[:500]!r}", flush=True)
        sys.exit(1)
    notice("YouTube'a yüklendi", f"https://youtu.be/{sonuc['id']} — {baslik}")


if __name__ == "__main__":
    main()
