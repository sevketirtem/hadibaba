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


def vertex_veo(resim, cikti, istem):
    """Vertex AI Veo 3.1 Fast (deneme kredisi). Omni Vertex'te yok; Veo var (us-central1, predictLongRunning)."""
    model = os.environ.get("VERTEX_VIDEO_MODEL", "veo-3.1-fast-generate-001")
    taban = (f"https://us-central1-aiplatform.googleapis.com/v1/projects/{os.environ.get('VERTEX_PROJE', 'hadi-yuru-ses')}"
             f"/locations/us-central1/publishers/google/models/{model}")
    b = {"Authorization": "Bearer " + os.environ["GOOGLE_VERTEX_TOKEN"], "Content-Type": "application/json"}

    def post(url, govde):
        req = urllib.request.Request(url, data=json.dumps(govde).encode(), headers=b, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Veo HTTP {e.code}: {e.read()[:500]!r}") from None

    veri = base64.b64encode(open(resim, "rb").read()).decode()
    tip = "image/png" if resim.lower().endswith(".png") else "image/jpeg"
    ornek = {"prompt": istem}
    referans = "character reference" in istem.lower()
    if referans:  # görsel yalnızca karakter örneği: yeni sahne
        ornek["referenceImages"] = [{"image": {"bytesBase64Encoded": veri, "mimeType": tip}, "referenceType": "asset"}]
    else:         # görsel ilk kare: onu canlandır
        ornek["image"] = {"bytesBase64Encoded": veri, "mimeType": tip}
    oran = os.environ.get("VEO_ORAN", "16:9")
    coz = os.environ.get("VEO_COZUNURLUK", "720p")
    param = {"aspectRatio": oran, "sampleCount": 1, "durationSeconds": 8, "generateAudio": False,
             "resolution": "1080p" if coz == "1080p" else "720p", "personGeneration": "allow_all"}
    try:
        op = post(f"{taban}:predictLongRunning", {"instances": [ornek], "parameters": param})
    except RuntimeError as e:
        if "personGeneration" in str(e) or "allow_all" in str(e):
            param["personGeneration"] = "allow_adult"
            op = post(f"{taban}:predictLongRunning", {"instances": [ornek], "parameters": param})
        else:
            raise
    ad = op["name"]
    print(f"::notice title=Veo (Vertex)::{model} · {'referans' if referans else 'ilk kare'} · {ad.split('/')[-1]}", flush=True)
    for _ in range(90):
        time.sleep(10)
        y = post(f"{taban}:fetchPredictOperation", {"operationName": ad})
        if y.get("done"):
            break
    else:
        raise RuntimeError("Veo 15 dakikada bitmedi")
    if "error" in y:
        raise RuntimeError(f"Veo hatası: {y['error']}")
    vids = y.get("response", {}).get("videos", [])
    if not vids:
        raise RuntimeError(f"Video yok (güvenlik filtresi olabilir): {json.dumps(y.get('response', {}))[:500]}")
    open(cikti, "wb").write(base64.b64decode(vids[0]["bytesBase64Encoded"]))
    print(f"::notice title=Video bitti::{cikti} ({os.path.getsize(cikti)} bayt, {model}, Vertex)")


def main():
    resim, cikti, istem = sys.argv[1], sys.argv[2], sys.argv[3]
    if os.environ.get("GOOGLE_VERTEX_TOKEN") and not os.environ.get("VEO_MODEL"):
        return vertex_veo(resim, cikti, istem)
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
