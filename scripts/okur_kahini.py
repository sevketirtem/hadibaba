"""OKUR KÂHİNİ — YouTube yorumlarındaki skor tahminlerini okur, maçın skorunu tam bilenleri bulur.

Kullanım:
  python scripts/okur_kahini.py tani
      Anahtarın izinlerini (scope) ve kanalı gösterir; yorum okunabiliyor mu dener.
  python scripts/okur_kahini.py tara "<Ev>" "<Deplasman>" <ev_gol>-<dep_gol> <başlama, ISO, ör. 2026-11-08T21:00:00+03:00> [gün=7]
      Kanalın son <gün> günde yüklenen videolarının yorumlarını tarar. Maç BAŞLAMADAN önce yazılmış,
      skoru tam tutan yorumları bulur; okur-kahini/<ev>-<dep>-<tarih>.json dosyasına yazar.
Ortam: tara → YOUTUBE_API_KEY (YouTube Data API v3'e izinli API anahtarı; herkese açık yorumları okur).\n      tani → ayrıca YOUTUBE_CLIENT_ID/SECRET/REFRESH_TOKEN (yalnızca izin kontrolü).

Kurallar: bir yorumcu yalnızca bir kez sayılır (maçtan önceki SON tahmini geçerlidir; maçtan sonra yazılan/düzenlenen yorum sayılmaz).
Yorumcunun adı yalnızca kanal adı (authorDisplayName) olarak saklanır; başka kişisel bilgi tutulmaz.
"""
import datetime as dt, json, os, re, sys, unicodedata, urllib.error, urllib.parse, urllib.request

API = "https://www.googleapis.com/youtube/v3/"


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def anahtar():
    veri = urllib.parse.urlencode({
        "client_id": os.environ["YOUTUBE_CLIENT_ID"], "client_secret": os.environ["YOUTUBE_CLIENT_SECRET"],
        "refresh_token": os.environ["YOUTUBE_REFRESH_TOKEN"], "grant_type": "refresh_token"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=veri, timeout=60) as r:
        return json.loads(r.read())["access_token"]


def cagir(tok, yol, **p):
    url = API + yol + "?" + urllib.parse.urlencode(p)
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {tok}"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{yol}: HTTP {e.code} {e.read()[:300]!r}")


def zaman(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def sade(s):
    s = unicodedata.normalize("NFKD", s.lower().replace("ı", "i"))
    return "".join(c for c in s if not unicodedata.combining(c))


SKOR = re.compile(r"(?<!\d)(\d{1,2})\s*[-–:]\s*(\d{1,2})(?!\d)")


def tahmin_bul(metin, ev, dep):
    """Yorumdan (ev, dep) sıralı skor tahminini çıkarır. Birden çok farklı skor varsa None (kararsız)."""
    m = sade(metin)
    skorlar = {(int(a), int(b)) for a, b in SKOR.findall(m)}
    if len(skorlar) != 1:
        return None
    a, b = skorlar.pop()
    # "Fenerbahçe 1-2 Göztepe" sırası bozuksa ters çevir: yorumda deplasman adı ev sahibinden önce geçiyorsa
    e, d = sade(ev).split()[0], sade(dep).split()[0]
    ie, idd = m.find(e), m.find(d)
    if ie >= 0 and idd >= 0 and idd < ie:
        a, b = b, a
    return a, b


def anahtarla(yol, **p):
    """Herkese açık veriyi API anahtarıyla okur (OAuth gerekmez)."""
    p["key"] = os.environ["YOUTUBE_API_KEY"]
    try:
        with urllib.request.urlopen(API + yol + "?" + urllib.parse.urlencode(p), timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{yol}: HTTP {e.code} {e.read()[:300]!r}")


def tani_anahtar(video="Ap9oWA9ykS0"):
    try:
        v = anahtarla("videos", part="snippet", id=video)["items"][0]["snippet"]
        notice("Okur kâhini · anahtar/kanal", f"{v['channelTitle']} ({v['channelId']})")
        y = anahtarla("commentThreads", part="snippet", videoId=video, maxResults=5)
        notice("Okur kâhini · anahtarla yorum okuma", f"ÇALIŞIYOR — {len(y.get('items', []))} yorum")
    except Exception as e:  # noqa: BLE001
        notice("Okur kâhini · anahtarla yorum okuma", f"ÇALIŞMIYOR: {e}")


def tani():
    if os.environ.get("YOUTUBE_API_KEY"):
        tani_anahtar()
    tok = anahtar()
    with urllib.request.urlopen(f"https://oauth2.googleapis.com/tokeninfo?access_token={tok}", timeout=30) as r:
        bilgi = json.loads(r.read())
    notice("Okur kâhini · izinler", bilgi.get("scope", "?"))
    try:
        k = cagir(tok, "channels", part="id,snippet,contentDetails", mine="true")["items"][0]
        notice("Okur kâhini · kanal", f"{k['snippet']['title']} ({k['id']})")
        y = cagir(tok, "commentThreads", part="snippet", allThreadsRelatedToChannelId=k["id"], maxResults=5)
        notice("Okur kâhini · yorum okuma", f"ÇALIŞIYOR — son sayfada {len(y.get('items', []))} yorum")
    except Exception as e:  # noqa: BLE001
        notice("Okur kâhini · yorum okuma", f"ÇALIŞMIYOR: {e}")


def videolar(gun_sinir):
    """Kanalın son yüklemeleri (yükleme listesi UU...). Kanal kimliği bilinen bir videodan bulunur."""
    kanal = anahtarla("videos", part="snippet", id=os.environ.get("KANAL_ORNEK_VIDEO", "Ap9oWA9ykS0"))["items"][0]["snippet"]["channelId"]
    liste, sayfa = [], None
    while True:
        p = dict(part="contentDetails", playlistId="UU" + kanal[2:], maxResults=50)
        if sayfa:
            p["pageToken"] = sayfa
        r = anahtarla("playlistItems", **p)
        for it in r.get("items", []):
            yuk = zaman(it["contentDetails"].get("videoPublishedAt", "1970-01-01T00:00:00Z"))
            if yuk < gun_sinir:
                return liste
            liste.append(it["contentDetails"]["videoId"])
        sayfa = r.get("nextPageToken")
        if not sayfa:
            return liste


def yorumlar(video):
    sayfa = None
    while True:
        p = dict(part="snippet", videoId=video, maxResults=100, textFormat="plainText")
        if sayfa:
            p["pageToken"] = sayfa
        try:
            r = anahtarla("commentThreads", **p)
        except RuntimeError as e:
            if "commentsDisabled" in str(e):
                return
            raise
        for it in r.get("items", []):
            yield it["snippet"]["topLevelComment"]["snippet"], video
        sayfa = r.get("nextPageToken")
        if not sayfa:
            return


def tara(ev, dep, skor, basla, gun=7):
    hedef = tuple(int(x) for x in skor.split("-"))
    basla = zaman(basla)
    sinir = basla - dt.timedelta(days=gun)
    son = {}  # kişi -> (zaman, tahmin, snippet, video): maçtan önceki SON tahmini
    vids = videolar(sinir)
    e_ad, d_ad = sade(ev).split()[0], sade(dep).split()[0]
    basliklar = {}
    for i in range(0, len(vids), 50):
        for it in anahtarla("videos", part="snippet", id=",".join(vids[i:i + 50])).get("items", []):
            sn = it["snippet"]
            basliklar[it["id"]] = sade(sn.get("title", "") + " " + sn.get("description", "")[:300])
    for v in vids:
        video_bu_mac = e_ad in basliklar.get(v, "") or d_ad in basliklar.get(v, "")
        for s, vid in yorumlar(v):
            yazildi = zaman(s["publishedAt"])
            if yazildi >= basla or (s.get("updatedAt") and zaman(s["updatedAt"]) >= basla):
                continue  # maç başladıktan sonra yazılan/düzenlenen tahmin sayılmaz
            metin = s.get("textOriginal") or s.get("textDisplay", "")
            # Tahmin bu maça ait olmalı: yorumda takım adı geçmeli ya da video bu maçla ilgili olmalı
            if not (video_bu_mac or e_ad in sade(metin) or d_ad in sade(metin)):
                continue
            t = tahmin_bul(metin, ev, dep)
            if t is None:
                continue
            kim = s.get("authorChannelId", {}).get("value") or s.get("authorDisplayName")
            if kim not in son or yazildi > son[kim][0]:
                son[kim] = (yazildi, t, s, vid)
    bilenler = [{"ad": s.get("authorDisplayName", "?"), "yorum": (s.get("textOriginal") or "")[:200],
                 "zaman": s["publishedAt"], "video": vid}
                for (_, t, s, vid) in son.values() if t == hedef]
    sonuc = {"mac": f"{ev} - {dep}", "skor": skor, "basla": basla.isoformat(), "taranan_video": len(vids),
             "taranan_tahmin": len(son), "bilenler": bilenler,
             "not": "Kişi başı tek tahmin (maçtan önceki son yorumu). Maçtan sonra yazılan/düzenlenen yorum sayılmaz."}
    os.makedirs("okur-kahini", exist_ok=True)
    ad = re.sub(r"[^a-z0-9]+", "-", sade(f"{ev}-{dep}-{basla.date()}")).strip("-")
    yol = f"okur-kahini/{ad}.json"
    if os.path.exists(yol):  # yeniden taramada "anildi" bilgisi kaybolmasın
        eski = json.load(open(yol, encoding="utf-8"))
        if "anildi" in eski:
            sonuc["anildi"] = eski["anildi"]
    json.dump(sonuc, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    adlar = ", ".join(b["ad"] for b in bilenler) or "kimse"
    notice("Okur kâhini", f"{ev} {skor} {dep}: {len(vids)} video, {len(son)} tahmin tarandı; tam bilen {len(bilenler)}: {adlar} → {yol}")


if __name__ == "__main__":
    if sys.argv[1] == "tani":
        tani()
    else:
        tara(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6]) if len(sys.argv) > 6 else 7)
