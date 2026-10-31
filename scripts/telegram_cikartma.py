"""Telegram hareketli çıkartma paketi (video sticker, WEBM VP9) — @hadiyuru_bot ile.

Kullanım:
  python scripts/telegram_cikartma.py kimlik            # bota yazan kişilerin kullanıcı kimliklerini listeler
  python scripts/telegram_cikartma.py olustur <user_id> # paketi oluşturur (varsa eksik çıkartmaları ekler)
Ortam: TELEGRAM_BOT_TOKEN. Liste: video/cikartma/liste.json
"""
import json, os, sys, uuid, urllib.error, urllib.request

T = os.environ["TELEGRAM_BOT_TOKEN"]
AD = "hadivsyuru_by_hadiyuru_bot"
BASLIK = "Hadi vs Yürü"


def api(yontem, alanlar=None, dosyalar=None):
    if not alanlar and not dosyalar:
        try:
            with urllib.request.urlopen(f"https://api.telegram.org/bot{T}/{yontem}", timeout=60) as r:
                return json.loads(r.read())["result"]
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"{yontem}: HTTP {e.code} {e.read()[:300]!r}") from None
    sinir = uuid.uuid4().hex
    govde = []
    for k, v in (alanlar or {}).items():
        govde.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, yol in (dosyalar or {}).items():
        govde.append(f'--{sinir}\r\nContent-Disposition: form-data; name="{k}"; filename="{os.path.basename(yol)}"\r\n'
                     f'Content-Type: video/webm\r\n\r\n'.encode())
        govde.append(open(yol, "rb").read())
        govde.append(b"\r\n")
    govde.append(f"--{sinir}--\r\n".encode())
    req = urllib.request.Request(f"https://api.telegram.org/bot{T}/{yontem}", data=b"".join(govde),
                                 headers={"Content-Type": f"multipart/form-data; boundary={sinir}"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())["result"]
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{yontem}: HTTP {e.code} {e.read()[:300]!r}") from None


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def main():
    if sys.argv[1] == "kimlik":
        gorulen = {}
        for u in api("getUpdates"):
            m = u.get("message") or u.get("edited_message") or {}
            k = m.get("from")
            if k and m.get("chat", {}).get("type") == "private":
                gorulen[k["id"]] = f"{k.get('first_name', '')} @{k.get('username', '-')} : {m.get('text', '')[:40]}"
        if not gorulen:
            notice("Çıkartma", "Bota özelden yazan kimse bulunamadı (t.me/hadiyuru_bot → Başlat)")
        for i, s in gorulen.items():
            notice("Bota yazan", f"{i} — {s}")
        return
    kullanici = sys.argv[2]
    liste = json.load(open("video/cikartma/liste.json", encoding="utf-8"))
    try:
        mevcut = api("getStickerSet", {"name": AD})
        var = len(mevcut["stickers"])
    except RuntimeError:
        mevcut, var = None, 0
    if mevcut is None:
        ilk = liste[:50]
        stickers = [{"sticker": f"attach://f{i}", "format": "video", "emoji_list": [s["emoji"]]} for i, s in enumerate(ilk)]
        api("createNewStickerSet", {"user_id": kullanici, "name": AD, "title": BASLIK,
                                    "stickers": json.dumps(stickers, ensure_ascii=False)},
            {f"f{i}": s["dosya"] for i, s in enumerate(ilk)})
        notice("Çıkartma paketi oluşturuldu", f"https://t.me/addstickers/{AD} ({len(ilk)} çıkartma)")
    else:
        for s in liste[var:]:
            api("addStickerToSet", {"user_id": kullanici, "name": AD,
                                    "sticker": json.dumps({"sticker": "attach://f0", "format": "video", "emoji_list": [s["emoji"]]},
                                                          ensure_ascii=False)}, {"f0": s["dosya"]})
        notice("Çıkartma paketi güncellendi", f"https://t.me/addstickers/{AD} ({max(0, len(liste) - var)} yeni)")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"::error title=Çıkartma::{str(e)[:800]}", flush=True)
        sys.exit(1)
