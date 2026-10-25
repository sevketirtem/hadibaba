// Sezonun bütün maçları (sade liste). ?lig=204 → 1. Lig. Tek API-Football isteği.
// Derleme betiği (scripts/veri_cek.py) maç sayfalarını bundan üretir. Canlı maç varken 5 dk, yoksa 1 saat.
import { ligSec, SEZON, CANLI, cors, onbellek, apiFootball, hata, macOzet } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const lig = ligSec(req);
    const r = await apiFootball("fixtures", { league: lig, season: SEZON, timezone: "Europe/Istanbul" });
    const maclar = r.map((m) => ({ ...macOzet(m), stat: m.fixture.venue?.name || null, sehir: m.fixture.venue?.city || null,
      hakem: (m.fixture.referee || "").replace(/,.*$/, "") || null })).sort((a, b) => a.tarih.localeCompare(b.tarih));
    onbellek(res, maclar.some((m) => CANLI.has(m.durum)) ? 300 : 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), lig, sezon: SEZON, maclar });
  } catch (e) {
    hata(res, e);
  }
}
