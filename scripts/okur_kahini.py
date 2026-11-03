"""OKUR KÂHİNİ — YouTube yorumlarındaki skor tahminlerini okur, maçın skorunu tam bilenleri bulur.

Kullanım:
  python scripts/okur_kahini.py tani
      Anahtarın izinlerini (scope) ve kanalı gösterir; yorum okunabiliyor mu dener.
  python scripts/okur_kahini.py tara "<Ev>" "<Deplasman>" <ev_gol>-<dep_gol> <başlama, ISO, ör. 2026-11-08T21:00:00+03:00> [gün=7]
      Kanalın son <gün> günde yüklenen videolarının yorumlarını tarar. Maç BAŞLAMADAN önce yazılmış,
      skoru tam tutan yorumları bulur; okur-kahini/<ev>-<dep>-<tarih>.json dosyasına yazar.
Ortam: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN.

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


def tani():
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


def tara(ev, dep, skor, basla, gun=7):
    hedef = tuple(int(x) for x in skor.split("-"))
    basla = zaman(basla)
    tok = anahtar()
    kanal = cagir(tok, "channels", part="id", mine="true")["items"][0]["id"]
    sinir = basla - dt.timedelta(days=gun)
    bilenler, gorulen, toplam, sayfa = {}, set(), 0, None
    while True:
        p = dict(part="snippet", allThreadsRelatedToChannelId=kanal, maxResults=100, order="time")
        if sayfa:
            p["pageToken"] = sayfa
        r = cagir(tok, "commentThreads", **p)
        bitti = False
        for it in r.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            yazildi = zaman(s["publishedAt"])
            if yazildi < sinir:
                bitti = True
                break
            if yazildi >= basla:
                continue  # maç başladıktan sonra yazılan tahmin sayılmaz
            if s.get("updatedAt") and zaman(s["updatedAt"]) >= basla:
                continue  # maçtan sonra düzenlenmiş
            kim = s.get("authorChannelId", {}).get("value") or s.get("authorDisplayName")
            if kim in gorulen:
                continue
            t = tahmin_bul(s.get("textOriginal") or s.get("textDisplay", ""), ev, dep)
            if t is None:
                continue
            gorulen.add(kim)
            toplam += 1
            if t == hedef:
                bilenler[kim] = {"ad": s.get("authorDisplayName", "?"), "yorum": (s.get("textOriginal") or "")[:200],
                                 "zaman": s["publishedAt"], "video": it["snippet"].get("videoId")}
        sayfa = r.get("nextPageToken")
        if bitti or not sayfa:
            break
    # Yorumlar yeniden eskiye gelir: kişinin ilk görülen yorumu = maçtan önceki son tahmini.
    sonuc = {"mac": f"{ev} - {dep}", "skor": skor, "basla": basla.isoformat(), "taranan_tahmin": toplam,
             "bilenler": list(bilenler.values()),
             "not": "Kişi başı tek tahmin (maçtan önceki son yorumu). Maçtan sonra yazılan/düzenlenen yorum sayılmaz."}
    os.makedirs("okur-kahini", exist_ok=True)
    ad = re.sub(r"[^a-z0-9]+", "-", sade(f"{ev}-{dep}-{basla.date()}")).strip("-")
    yol = f"okur-kahini/{ad}.json"
    json.dump(sonuc, open(yol, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    adlar = ", ".join(b["ad"] for b in sonuc["bilenler"]) or "kimse"
    notice("Okur kâhini", f"{ev} {skor} {dep}: {toplam} tahmin tarandı, tam bilen {len(bilenler)}: {adlar} → {yol}")


if __name__ == "__main__":
    if sys.argv[1] == "tani":
        tani()
    else:
        tara(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], int(sys.argv[6]) if len(sys.argv) > 6 else 7)
