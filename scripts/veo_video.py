"""Gemini Omni Flash (Interactions API) ile başlangıç görselinden kısa video üretir.
(Veo modelleri Gemini API'de kaldırıldı; yerini gemini-omni-1.1-flash aldı.)

Kullanım: python scripts/veo_video.py <baslangic.jpg> <cikti.mp4> "<istem>"
Ortam: GEMINI_API_KEY, VEO_MODEL (varsayılan gemini-omni-1.1-flash), VEO_ORAN (16:9 / 9:16), VEO_COZUNURLUK (720p).
"""
import base64, json, os, sys, time, urllib.error, urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"


def istek(yol, govde=None):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import gapi  # Vertex (deneme kredisi) önce, AI Studio yedek
    try:
        return gapi.istek(yol, govde, 600)
    except gapi.HataHTTP as e:
        raise RuntimeError(str(e)) from None


def video_bul(o):
    """Yanıtın içinde video/mp4 parçasını (data ya da uri) arar."""
    if isinstance(o, dict):
        if str(o.get("mime_type", o.get("mimeType", ""))).startswith("video/") and (o.get("data") or o.get("uri")):
            return o
        for v in o.values():
            b = video_bul(v)
            if b:
                return b
    elif isinstance(o, list):
        for v in o:
            b = video_bul(v)
            if b:
                return b
    return None


def main():
    resim, cikti, istem = sys.argv[1], sys.argv[2], sys.argv[3]
    model = os.environ.get("VEO_MODEL") or "gemini-omni-1.1-flash"
    govde = {"model": model,
             "input": [{"type": "image", "data": base64.b64encode(open(resim, "rb").read()).decode(),
                        "mime_type": "image/jpeg"},
                       {"type": "text", "text": istem}],
             "response_format": {"type": "video", "aspect_ratio": os.environ.get("VEO_ORAN", "16:9"),
                                 "resolution": os.environ.get("VEO_COZUNURLUK", "720p")}}
    y = istek("interactions", govde)
    kimlik = y.get("id")
    print(f"::notice title=Omni::{model} · {kimlik} · {y.get('status')}")
    for _ in range(90):
        if y.get("status") in ("completed", "failed", "cancelled") or video_bul(y.get("steps")):
            break
        time.sleep(10)
        y = istek(f"interactions/{kimlik}")
    v = video_bul(y.get("steps", y))
    if not v:
        raise RuntimeError(f"Video yok, durum {y.get('status')}: {json.dumps(y)[:800]}")
    if v.get("data"):
        open(cikti, "wb").write(base64.b64decode(v["data"]))
    else:
        uri = v["uri"]
        b = {"Authorization": "Bearer " + os.environ["GOOGLE_VERTEX_TOKEN"]} if os.environ.get("GOOGLE_VERTEX_TOKEN") \
            else {"x-goog-api-key": os.environ.get("GEMINI_API_KEY", "")}
        req = urllib.request.Request(uri + ("&" if "?" in uri else "?") + "alt=media", headers=b)
        open(cikti, "wb").write(urllib.request.urlopen(req, timeout=300).read())
    print(f"::notice title=Video bitti::{cikti} ({os.path.getsize(cikti)} bayt, {model})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Omni::{str(e)[:900]}", flush=True)
        sys.exit(1)
