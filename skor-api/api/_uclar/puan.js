// Puan durumu (?lig=204 → 1. Lig, varsayılan Süper Lig); 2 saat önbellek. Tek API-Football isteği.
import { ligSec, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const lig = ligSec(req);
    const r = await apiFootball("standings", { league: lig, season: SEZON });
    const tablo = (r[0]?.league?.standings?.[0] || []).map((t) => ({
      sira: t.rank, takim: t.team.name, id: t.team.id, o: t.all.played, g: t.all.win, b: t.all.draw,
      m: t.all.lose, a: t.all.goals.for, y: t.all.goals.against, av: t.goalsDiff,
      p: t.points, form: t.form || "",
    }));
    onbellek(res, 7200);
    res.status(200).json({ guncellendi: new Date().toISOString(), sezon: SEZON, lig, tablo });
  } catch (e) {
    hata(res, e);
  }
}
