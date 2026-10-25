// Bu haftanın (bugün -3 / +4 gün) maçları (?lig=204 → 1. Lig); canlı maç varken 6 dk,
// yoksa 60 dk önbellek. Tek API-Football isteği.
import { ligSec, SEZON, cors, onbellek, apiFootball, hata, macOzet, gun } from "./_ortak.js";

const CANLI = new Set(["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"]);
const BITTI = new Set(["FT", "AET", "PEN"]);


export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const liste = await apiFootball("fixtures", {
      league: ligSec(req), season: SEZON, from: gun(-3), to: gun(4), timezone: "Europe/Istanbul",
    });
    const maclar = liste.map(macOzet).sort((a, b) => a.tarih.localeCompare(b.tarih));
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
