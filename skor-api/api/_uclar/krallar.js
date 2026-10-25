// Süper Lig gol ve asist krallığı (ilk 20). İki API-Football isteği, 6 saat önbellek.
import { LIG, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

function liste(r, alan) {
  return r.slice(0, 20).map((x, i) => {
    const s = x.statistics?.[0] || {};
    return {
      sira: i + 1,
      oyuncu: x.player?.name,
      takim: s.team?.name,
      mac: s.games?.appearences ?? 0,
      dakika: s.games?.minutes ?? 0,
      gol: s.goals?.total ?? 0,
      asist: s.goals?.assists ?? 0,
      penalti: s.penalty?.scored ?? 0,
      sayi: alan === "gol" ? (s.goals?.total ?? 0) : (s.goals?.assists ?? 0),
    };
  });
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const [g, a] = await Promise.all([
      apiFootball("players/topscorers", { league: LIG, season: SEZON }),
      apiFootball("players/topassists", { league: LIG, season: SEZON }),
    ]);
    onbellek(res, 6 * 3600);
    res.status(200).json({
      guncellendi: new Date().toISOString(), sezon: SEZON,
      gol: liste(g, "gol"), asist: liste(a, "asist"),
    });
  } catch (e) {
    hata(res, e);
  }
}
