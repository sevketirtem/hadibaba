"""TikTok'a video gönderir: Content Posting API "Upload" (taslak → TikTok uygulamasındaki gelen kutusu).

Taslak akışı seçildi çünkü denetimden (audit) geçmemiş uygulamaların "Direct Post" gönderileri yalnızca
"Sadece ben" görünür. Taslakta video telefona bildirim olarak düşer; sahibi açıp açıklamayı yapıştırır ve
herkese açık paylaşır. TikTok kuralı: 24 saatte en fazla 5 bekleyen taslak.

Ortam: TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_REFRESH_TOKEN (scope video.upload; 365 gün geçerli).
Kullanım (deneme): python scripts/tiktok_yukle.py <video.mp4> "<açıklama>"
"""
import json, os, sys, time, urllib.error, urllib.parse, urllib.request

API = "https://open.tiktokapis.com/v2"


def _istek(url, veri=None, baslik=None, yontem=None):
    req = urllib.request.Request(url, data=veri, headers=baslik or {}, method=yontem)
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            govde = r.read()
            return json.loads(govde) if govde else {}
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"TikTok HTTP {e.code}: {e.read()[:400]!r}") from None


def erisim_anahtari():
    veri = urllib.parse.urlencode({
        "client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "grant_type": "refresh_token", "refresh_token": os.environ["TIKTOK_REFRESH_TOKEN"]}).encode()
    y = _istek(f"{API}/oauth/token/", veri, {"Content-Type": "application/x-www-form-urlencoded"}, "POST")
    if "access_token" not in y:
        raise RuntimeError(f"TikTok anahtar yenilenemedi: {str(y)[:300]}")
    if y.get("refresh_expires_in", 1e9) < 30 * 86400:
        print(f"::warning title=TikTok::Yenileme anahtarının süresi {y['refresh_expires_in'] // 86400} gün sonra doluyor; "
              "yeniden izin alınmalı.", flush=True)
    return y["access_token"]


def gonder(video, aciklama=""):
    anahtar = erisim_anahtari()
    yetki = {"Authorization": f"Bearer {anahtar}", "Content-Type": "application/json; charset=UTF-8"}
    boyut = os.path.getsize(video)
    y = _istek(f"{API}/post/publish/inbox/video/init/", json.dumps({"source_info": {
        "source": "FILE_UPLOAD", "video_size": boyut, "chunk_size": boyut, "total_chunk_count": 1}}).encode(), yetki, "POST")
    if y.get("error", {}).get("code") not in (None, "ok"):
        raise RuntimeError(f"TikTok init: {y['error']}")
    yayin_id, yukleme = y["data"]["publish_id"], y["data"]["upload_url"]
    with open(video, "rb") as f:
        _istek(yukleme, f.read(), {"Content-Type": "video/mp4", "Content-Length": str(boyut),
                                   "Content-Range": f"bytes 0-{boyut - 1}/{boyut}"}, "PUT")
    durum = "?"
    for _ in range(30):
        time.sleep(10)
        s = _istek(f"{API}/post/publish/status/fetch/", json.dumps({"publish_id": yayin_id}).encode(), yetki, "POST")
        durum = s.get("data", {}).get("status", "?")
        if durum in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
            break
        if durum == "FAILED":
            raise RuntimeError(f"TikTok işleyemedi: {s['data'].get('fail_reason')}")
    print(f"::notice title=TikTok açıklaması (kopyala-yapıştır)::{aciklama}", flush=True)
    return f"taslak gönderildi ({durum}); telefonda TikTok bildirimini açıp paylaşın"


if __name__ == "__main__":
    print(gonder(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else ""))
