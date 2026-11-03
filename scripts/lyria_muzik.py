"""Lyria 3.5 (Gemini API, Interactions) ile şarkı üretir.
Kullanım: python scripts/lyria_muzik.py <istem.txt> <cikti.wav|mp3>
Ortam: GEMINI_API_KEY, LYRIA_MODEL (varsayılan lyria-3.5)
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


def ses_bul(o):
    if isinstance(o, dict):
        if str(o.get("mime_type", o.get("mimeType", ""))).startswith("audio/") and (o.get("data") or o.get("uri")):
            return o
        for v in o.values():
            b = ses_bul(v)
            if b:
                return b
    elif isinstance(o, list):
        for v in o:
            b = ses_bul(v)
            if b:
                return b
    return None


def main():
    istem, cikti = open(sys.argv[1], encoding="utf-8").read(), sys.argv[2]
    # Vertex (deneme kredisi) Lyria 3.5'i Interactions'ta desteklemiyor → Lyria 3 Pro (vokal + söz, 3 dk'ya kadar).
    modeller = [m for m in (os.environ.get("LYRIA_MODEL"), "lyria-3.5", "lyria-3-pro-preview") if m]
    son_hata = None
    for model in dict.fromkeys(modeller):
        for bicim in (("liste", "metin") if "preview" in model else ("metin", "liste")):
            govde = {"model": model, "input": istem if bicim == "metin" else [{"type": "text", "text": istem}]}
            if cikti.endswith(".wav"):
                govde["response_format"] = {"type": "audio", "mime_type": "audio/wav"}
            try:
                try:
                    y = istek("interactions", govde)
                except RuntimeError as e:
                    if "response_format" not in str(e) and "bit_rate" not in str(e):
                        raise
                    del govde["response_format"]
                    y = istek("interactions", govde)
                break
            except RuntimeError as e:
                son_hata = e
                print(f"::warning title=Lyria {model} ({bicim})::{str(e)[:300]}", flush=True)
                y = None
        if y is not None:
            break
    if y is None:
        raise son_hata
    kimlik = y.get("id")
    for _ in range(90):
        if y.get("status") in ("completed", "failed", "cancelled") or ses_bul(y.get("steps")):
            break
        time.sleep(10)
        y = istek(f"interactions/{kimlik}")
    s = ses_bul(y.get("steps", y))
    if not s:
        raise RuntimeError(f"Ses yok, durum {y.get('status')}: {json.dumps(y)[:800]}")
    veri = base64.b64decode(s["data"]) if s.get("data") else urllib.request.urlopen(s["uri"]).read()
    if s.get("mime_type", "").endswith("mpeg") and cikti.endswith(".wav"):
        cikti = cikti[:-4] + ".mp3"
    open(cikti, "wb").write(veri)
    metin = " ".join(p.get("text", "") for st in y.get("steps", []) for p in (st.get("content") or []) if isinstance(p, dict))[:500]
    print(f"::notice title=Lyria bitti::{cikti} ({len(veri)} bayt, {model}) {metin}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Lyria::{str(e)[:900]}", flush=True)
        sys.exit(1)
