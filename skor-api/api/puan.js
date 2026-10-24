// Süper Lig puan durumu; 2 saat önbellek. Tek API-Football isteği.
import { LIG, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const r = await apiFootball("standings", { league: LIG, season: SEZON });
    const tablo = (r[0]?.league?.standings?.[0] || []).map((t) => ({
      sira: t.rank, takim: t.team.name, o: t.all.played, g: t.all.win, b: t.all.draw,
      m: t.all.lose, a: t.all.goals.for, y: t.all.goals.against, av: t.goalsDiff,
      p: t.points, form: t.form || "",
    }));
    onbellek(res, 7200);
    res.status(200).json({ guncellendi: new Date().toISOString(), sezon: SEZON, tablo });
  } catch (e) {
    hata(res, e);
  }
}
