"""Podcast kesitini paylaşır: YouTube Shorts (+ TikTok, TIKTOK_* secret'ları gelince).

Kullanım: python scripts/kesit_paylas.py <senaryo.json> <kesit.mp4> <kesit.json> [bölüm_youtube_id]
Kayıt: podcast/kesit_kayit.txt içine "<tarih> <platform>" (aynı kesit bir platforma iki kez gitmez).
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import youtube_yukle  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYIT = os.path.join(KOK, "podcast", "kesit_kayit.txt")


def kayitli(anahtar):
    return os.path.exists(KAYIT) and anahtar in {x.strip() for x in open(KAYIT, encoding="utf-8")}


def kaydet(anahtar):
    with open(KAYIT, "a", encoding="utf-8") as f:
        f.write(anahtar + "\n")


def aciklama(s, meta, yt_id, etiketler):
    tam = f"Tam bölüm: https://youtu.be/{yt_id}" if yt_id else "Tam bölüm kanalda: Hadi vs Yürü podcast'i"
    return "\n\n".join([
        s.get("aciklama", ""), tam,
        "Coşkulu taraftar Hadi Baba ile alaycı abi Yürü Baba her gün Süper Lig'i tartışıyor. "
        "Tahmininizi yorumlara yazın: skor, kupon değil. Burada bahis yok.",
        "Spotify'da \"Hadi vs Yürü\" · hadibaba.com · yurubaba.com",
        "Sesler ve görseller yapay zekâ ile üretilmiştir; karakterler hayalîdir.", etiketler])


def youtube(s, video, meta, yt_id):
    anahtar = f"{s['tarih']} youtube"
    if not os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        youtube_yukle.notice("Kesit YouTube", "anahtar yok, atlandı")
        return
    if kayitli(anahtar):
        youtube_yukle.notice("Kesit YouTube", f"{s['tarih']} zaten yüklenmiş")
        return
    baslik = f"{meta['baslik']} #Shorts"[:100]
    govde = {
        "snippet": {"title": baslik, "description": aciklama(s, meta, yt_id, "#Shorts #futbol #süperlig #podcast")[:4900],
                    "categoryId": "17", "defaultLanguage": "tr", "defaultAudioLanguage": "tr",
                    "tags": ["shorts", "futbol", "süper lig", "podcast", "Hadi Baba", "Yürü Baba"]},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }
    sonuc = youtube_yukle.yukle(video, govde)
    kaydet(anahtar)
    youtube_yukle.notice("Kesit YouTube Shorts'ta", f"https://youtube.com/shorts/{sonuc['id']} — {baslik}")


def tiktok(s, video, meta):
    if not os.environ.get("TIKTOK_REFRESH_TOKEN"):
        youtube_yukle.notice("Kesit TikTok", "anahtar yok, atlandı")
        return
    import tiktok_yukle
    anahtar = f"{s['tarih']} tiktok"
    if kayitli(anahtar):
        youtube_yukle.notice("Kesit TikTok", f"{s['tarih']} zaten gönderilmiş")
        return
    metin = f"{meta['baslik']} #futbol #süperlig #podcast #hadibaba #yurubaba"
    sonuc = tiktok_yukle.gonder(video, metin)
    kaydet(anahtar)
    youtube_yukle.notice("Kesit TikTok'a gönderildi", f"{sonuc} — {meta['baslik']}")


def main():
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    video, meta = sys.argv[2], json.load(open(sys.argv[3], encoding="utf-8"))
    yt_id = sys.argv[4].strip() if len(sys.argv) > 4 else ""
    hata = 0
    for ad, is_ in (("YouTube", lambda: youtube(s, video, meta, yt_id)), ("TikTok", lambda: tiktok(s, video, meta))):
        try:
            is_()
        except SystemExit:
            hata += 1
        except Exception as e:  # noqa: BLE001
            print(f"::warning title=Kesit {ad}::{str(e)[:400]}", flush=True)
            hata += 1
    sys.exit(1 if hata == 2 else 0)


if __name__ == "__main__":
    main()
