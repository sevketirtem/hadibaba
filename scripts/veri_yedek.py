#!/usr/bin/env python3
"""Kendi veri sistemimize geçiş: API-Football aboneliği (25 Kasım 2026) bitmeden sezonun verisini depoya kaydeder.

Yazdıkları (depoya commit'lenir, kendi-veri/ altında):
  fikstur.json   sezonun bütün Süper Lig maçları (/api/fikstur ile aynı biçim: id, tarih, hafta, ev, dep, gol, stat, hakem…)
  puan.json      o anki puan durumu (kendi hesaplamamızı doğrulamak için)
  krallar.json   gol/asist krallığı
  takimlar.json  18 takımın bilgi + kadro anlık görüntüsü (/api/takim)
  sonuclar.csv   tarih,hafta,ev,dep,ev_gol,dep_gol,durum,id — ELLE/GÖREVLE GÜNCELLENECEK ANA DOSYA
                 (ilk çalıştırmada oluşturulur; sonra yalnızca yeni biten maçların skoru doldurulur,
                  elle girilmiş satırlar ezilmez)

Ortam: SKOR_API (yoksa hugo.toml'daki skorAPI). Yalnızca Python standart kütüphanesi.
"""
import csv, json, os, re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import veri_cek  # noqa: E402  (getir, skor_api, takim_slug)

KOK = Path(__file__).resolve().parent.parent
HEDEF = KOK / "kendi-veri"
ALANLAR = ["tarih", "hafta", "ev", "dep", "ev_gol", "dep_gol", "durum", "id"]
BITTI = {"FT", "AET", "PEN"}


def notice(b, m):
    print(f"::notice title={b}::{m}", flush=True)


def yaz(ad, veri):
    (HEDEF / ad).write_text(json.dumps(veri, ensure_ascii=False, indent=1), encoding="utf-8")


def sonuclari_guncelle(maclar):
    yol = HEDEF / "sonuclar.csv"
    eski = {}
    if yol.exists():
        with open(yol, encoding="utf-8", newline="") as f:
            eski = {r["id"]: r for r in csv.DictReader(f)}
    yeni_skor = 0
    satirlar = []
    for m in maclar:
        k = str(m["id"])
        r = eski.get(k) or {"id": k}
        r.update({"tarih": m["tarih"][:16].replace("T", " "), "hafta": m.get("hafta") or "",
                  "ev": m["ev"], "dep": m["dep"]})
        if m.get("durum") in BITTI and m.get("evGol") is not None and not r.get("ev_gol"):
            r.update({"ev_gol": m["evGol"], "dep_gol": m["depGol"], "durum": "bitti"})
            yeni_skor += 1
        r.setdefault("durum", "")
        if not r.get("durum"):
            r["durum"] = "ertelendi" if m.get("durum") in ("PST", "CANC", "ABD") else ""
        satirlar.append(r)
    with open(yol, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALANLAR, extrasaction="ignore")
        w.writeheader()
        w.writerows(satirlar)
    return len(satirlar), sum(1 for r in satirlar if r.get("ev_gol") not in (None, "")), yeni_skor


def main():
    api = veri_cek.skor_api()
    if not api:
        sys.exit("skorAPI yok")
    HEDEF.mkdir(exist_ok=True)
    fikstur = veri_cek.getir(api, "/api/fikstur")
    if not fikstur or not fikstur.get("maclar"):
        sys.exit("::error::Fikstür alınamadı")
    yaz("fikstur.json", fikstur)
    toplam, biten, yeni = sonuclari_guncelle(fikstur["maclar"])
    notice("Veri yedeği fikstür", f"{toplam} maç, {biten} sonuçlu (bu çalıştırmada {yeni} yeni skor)")
    puan = veri_cek.getir(api, "/api/puan")
    if puan and puan.get("tablo"):
        yaz("puan.json", puan)
        lider = puan["tablo"][0]
        notice("Veri yedeği puan", f"{len(puan['tablo'])} takım; lider {lider['takim']} {lider['p']} puan ({lider['o']} maç)")
    krallar = veri_cek.getir(api, "/api/krallar")
    if krallar:
        yaz("krallar.json", krallar)
    takimlar = []
    for t in (puan or {}).get("tablo", []):
        d = veri_cek.getir(api, f"/api/takim?id={t['id']}")
        if d:
            takimlar.append({"id": t["id"], "takim": t["takim"], "slug": veri_cek.takim_slug(t["takim"]), "veri": d})
    if takimlar:
        yaz("takimlar.json", takimlar)
        notice("Veri yedeği takımlar", f"{len(takimlar)} takımın bilgi/kadro görüntüsü kaydedildi")


if __name__ == "__main__":
    main()
