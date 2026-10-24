// Bu haftanın (bugün -3 / +4 gün) Süper Lig maçları; canlı maç varken 6 dk,
// yoksa 60 dk önbellek. Tek API-Football isteği.
import { LIG, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

const CANLI = new Set(["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"]);
const BITTI = new Set(["FT", "AET", "PEN"]);

function gun(fark) {
  // İstanbul günü (UTC+3, yaz saati yok)
  const d = new Date(Date.now() + 3 * 3600e3 + fark * 86400e3);
  return d.toISOString().slice(0, 10);
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const liste = await apiFootball("fixtures", {
      league: LIG, season: SEZON, from: gun(-3), to: gun(4), timezone: "Europe/Istanbul",
    });
    const maclar = liste.map((m) => ({
      id: m.fixture.id,
      tarih: m.fixture.date,
      durum: m.fixture.status.short,
      dakika: m.fixture.status.elapsed,
      hafta: (m.league.round || "").replace("Regular Season - ", ""),
      ev: m.teams.home.name,
      dep: m.teams.away.name,
      evGol: m.goals.home,
      depGol: m.goals.away,
    })).sort((a, b) => a.tarih.localeCompare(b.tarih));
    const simdi = Date.now();
    const canliVar = maclar.some((m) => CANLI.has(m.durum) ||
      (m.durum === "NS" && Math.abs(new Date(m.tarih) - simdi) < 15 * 60e3));
    onbellek(res, canliVar ? 360 : 3600);
    res.status(200).json({
      guncellendi: new Date().toISOString(), canli: canliVar, maclar,
      bitti: [...BITTI], canliKodlar: [...CANLI],
    });
  } catch (e) {
    hata(res, e);
  }
}
