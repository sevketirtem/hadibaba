"""Gemini API ile Veo: başlangıç görselinden kısa video üretir.

Kullanım: python scripts/veo_video.py <baslangic.jpg> <cikti.mp4> "<istem>"
Ortam: GEMINI_API_KEY, VEO_MODEL (boşsa mevcut modellerden en uygun veo seçilir), VEO_ORAN (16:9 / 9:16).
"""
import base64, json, os, sys, time, urllib.error, urllib.request

API = "https://generativelanguage.googleapis.com/v1beta"
KEY = os.environ["GEMINI_API_KEY"]


def istek(yol, govde=None, tam=None):
    url = tam or f"{API}/{yol}"
    req = urllib.request.Request(url, data=json.dumps(govde).encode() if govde is not None else None,
                                 method="POST" if govde is not None else "GET",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read()[:600]!r}") from None


def model_sec():
    if os.environ.get("VEO_MODEL"):
        return os.environ["VEO_MODEL"]
    adlar, sayfa = [], ""
    while True:
        y = json.loads(istek(f"models?pageSize=200{'&pageToken=' + sayfa if sayfa else ''}"))
        hepsi = y.get("models", [])
        adlar += [m["name"].split("/")[-1] for m in hepsi if "veo" in m["name"].lower()]
        print("::notice title=Tüm modeller::" + ", ".join(m["name"].split("/")[-1] for m in hepsi)[:3000])
        sayfa = y.get("nextPageToken")
        if not sayfa:
            break
    print(f"::notice title=Veo modelleri::{', '.join(adlar)}")
    for tercih in ("veo-3.1-fast", "veo-3.1", "veo-3.0-fast", "veo-3"):
        for a in adlar:
            if a.startswith(tercih) and "lite" not in a:
                return a
    if not adlar:
        raise RuntimeError("Veo modeli bulunamadı")
    return adlar[0]


def main():
    resim, cikti, istem = sys.argv[1], sys.argv[2], sys.argv[3]
    model = model_sec()
    govde = {"instances": [{"prompt": istem, "image": {
                "bytesBase64Encoded": base64.b64encode(open(resim, "rb").read()).decode(),
                "mimeType": "image/jpeg"}}],
             "parameters": {"aspectRatio": os.environ.get("VEO_ORAN", "16:9"), "sampleCount": 1,
                            "personGeneration": "allow_adult"}}
    try:
        op = json.loads(istek(f"models/{model}:predictLongRunning", govde))
    except RuntimeError as e:
        if "personGeneration" in str(e) or "allow_adult" in str(e):
            del govde["parameters"]["personGeneration"]
            op = json.loads(istek(f"models/{model}:predictLongRunning", govde))
        else:
            raise
    ad = op["name"]
    print(f"::notice title=Veo::{model} başladı ({ad})")
    for _ in range(90):
        time.sleep(10)
        op = json.loads(istek(ad))
        if op.get("done"):
            break
    if not op.get("done"):
        raise RuntimeError("15 dakikada bitmedi")
    if "error" in op:
        raise RuntimeError(f"Veo hatası: {op['error']}")
    yanit = op.get("response", {})
    ornekler = (yanit.get("generateVideoResponse", {}).get("generatedSamples")
                or yanit.get("generatedVideos") or yanit.get("videos") or [])
    if not ornekler:
        raise RuntimeError(f"Video yok (güvenlik filtresi olabilir): {json.dumps(yanit)[:600]}")
    v = ornekler[0].get("video", ornekler[0])
    if v.get("bytesBase64Encoded"):
        open(cikti, "wb").write(base64.b64decode(v["bytesBase64Encoded"]))
    else:
        uri = v["uri"]
        open(cikti, "wb").write(istek(None, tam=uri + ("&" if "?" in uri else "?") + "alt=media"))
    print(f"::notice title=Veo bitti::{cikti} ({os.path.getsize(cikti)} bayt, {model})")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Veo::{str(e)[:900]}", flush=True)
        sys.exit(1)
