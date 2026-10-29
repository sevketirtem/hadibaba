"""podcast/bolumler.json → static/podcast/feed.xml (Spotify, Apple, YouTube vb. için RSS).

Bölüm sesleri GitHub Releases'ta durur (podcast-<tarih> etiketi); besleme hadibaba.com/podcast/feed.xml.
"""
import email.utils, datetime as dt, json, os
from xml.sax.saxutils import escape

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://hadibaba.com"
GOSTERI = {
    "baslik": "Hadi vs Yürü",
    "aciklama": ("Süper Lig'in en tatlı atışması: coşkulu taraftar Hadi Baba ile alaycı abi Yürü Baba her gün "
                 "maçları, gündemi ve tahminleri tartışıyor. Kısa, eğlenceli, bahissiz. "
                 "Yazılar hadibaba.com ve yurubaba.com'da."),
    "yazar": "Hadi vs Yürü",
    "eposta": "sevketirtem+hadi@gmail.com",
    "kapak": f"{SITE}/podcast/kapak.jpg",
}


def temiz(t):
    return escape((t or "").replace("<", "").replace(">", ""))


def main():
    bolumler = json.load(open(os.path.join(KOK, "podcast", "bolumler.json"), encoding="utf-8"))
    ogeler = []
    for b in sorted(bolumler, key=lambda x: x["tarih"], reverse=True):
        zaman = dt.datetime.fromisoformat(b["yayin"])
        sn = int(b["sure"])
        aciklama = b["aciklama"]
        if b.get("yazilar"):
            aciklama += " Yazılar: " + " · ".join(b["yazilar"].values())
        ogeler.append(f"""    <item>
      <title>{temiz(b['baslik'])}</title>
      <description>{temiz(aciklama)}</description>
      <itunes:summary>{temiz(aciklama)}</itunes:summary>
      <pubDate>{email.utils.format_datetime(zaman)}</pubDate>
      <guid isPermaLink="false">hadi-vs-yuru-{b['tarih']}</guid>
      <enclosure url="{escape(b['ses_url'])}" length="{b['boyut']}" type="audio/mpeg"/>
      <itunes:duration>{sn // 60}:{sn % 60:02d}</itunes:duration>
      <itunes:episode>{b['no']}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>false</itunes:explicit>
      <itunes:image href="{GOSTERI['kapak']}"/>
    </item>""")
    g = GOSTERI
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>{temiz(g['baslik'])}</title>
    <link>{SITE}/</link>
    <atom:link href="{SITE}/podcast/feed.xml" rel="self" type="application/rss+xml"/>
    <language>tr</language>
    <description>{temiz(g['aciklama'])}</description>
    <itunes:summary>{temiz(g['aciklama'])}</itunes:summary>
    <itunes:author>{temiz(g['yazar'])}</itunes:author>
    <itunes:owner><itunes:name>{temiz(g['yazar'])}</itunes:name><itunes:email>{g['eposta']}</itunes:email></itunes:owner>
    <itunes:image href="{g['kapak']}"/>
    <image><url>{g['kapak']}</url><title>{temiz(g['baslik'])}</title><link>{SITE}/</link></image>
    <itunes:category text="Sports"><itunes:category text="Soccer"/></itunes:category>
    <itunes:explicit>false</itunes:explicit>
    <itunes:type>episodic</itunes:type>
{chr(10).join(ogeler)}
  </channel>
</rss>
"""
    os.makedirs(os.path.join(KOK, "static", "podcast"), exist_ok=True)
    with open(os.path.join(KOK, "static", "podcast", "feed.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"::notice title=Podcast RSS::{len(ogeler)} bölüm", flush=True)


if __name__ == "__main__":
    main()
