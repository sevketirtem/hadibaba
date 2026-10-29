"""Günlük dikey atışma videosunu YouTube Shorts olarak "Hadi vs Yürü" kanalına yükler.

Kullanım: python scripts/youtube_shorts.py <video/senaryolar/tarih.json> <static/video/tarih.mp4>
Kayıt: video/paylasildi.txt içine "<tarih> youtube" (aynı gün ikinci kez yüklenmez).
Ortam: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import youtube_yukle  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KAYIT = os.path.join(KOK, "video", "paylasildi.txt")


def main():
    if not os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        youtube_yukle.notice("YouTube Shorts", "anahtar yok, atlandı")
        return
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    anahtar = f"{s['tarih']} youtube"
    if os.path.exists(KAYIT) and anahtar in {x.strip() for x in open(KAYIT, encoding="utf-8")}:
        youtube_yukle.notice("YouTube Shorts", f"{s['tarih']} zaten yüklenmiş")
        return
    konu = s.get("mac") or "Günün atışması"
    baslik = f"{konu}: Hadi mi haklı, Yürü mü? #Shorts"[:100]
    y = s.get("yazilar", {})
    aciklama = "\n\n".join(p for p in (
        s.get("aciklama", ""),
        "\n".join(f"• {u}" for u in y.values()),
        "Uzun bölüm her gün kanalda: Hadi vs Yürü podcast'i. Burada bahis yok, skor tahmini var.",
        "Sesler ve görseller yapay zekâ ile üretilmiştir; karakterler hayalîdir.",
        "#Shorts #futbol #süperlig") if p)
    govde = {
        "snippet": {"title": baslik, "description": aciklama[:4900], "categoryId": "17",
                    "defaultLanguage": "tr", "defaultAudioLanguage": "tr",
                    "tags": ["shorts", "futbol", "süper lig", "Hadi Baba", "Yürü Baba"]},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False, "containsSyntheticMedia": True},
    }
    sonuc = youtube_yukle.yukle(sys.argv[2], govde)
    with open(KAYIT, "a", encoding="utf-8") as f:
        f.write(anahtar + "\n")
    youtube_yukle.notice("Video youtube paylaşıldı", f"https://youtube.com/shorts/{sonuc['id']} — {baslik}")


if __name__ == "__main__":
    main()
