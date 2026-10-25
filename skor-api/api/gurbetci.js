// Yurt dışında oynayan milli oyuncular: milli kadrodaki her oyuncunun bu sezonki kulüp istatistikleri.
// 2 + kadro sayısı kadar istek (~28); 12 saat önbellek.
import { SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";
import { milliTakim } from "./milli.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const milli = await milliTakim();
    const kadro = (await apiFootball("players/squads", { team: milli.id }))[0]?.players || [];
    const oyuncular = await Promise.all(kadro.map((p) =>
      apiFootball("players", { id: p.id, season: SEZON }).then((r) => r[0]).catch(() => null)));
    const liste = [];
    for (const o of oyuncular) {
      if (!o) continue;
      // Kulüp istatistikleri: milli takım ve Türkiye ligleri dışında kalanlar
      const kulup = (o.statistics || []).filter((s) => s.team?.id !== milli.id && s.league?.country && s.league.country !== "Turkey" && s.league.country !== "World");
      if (!kulup.length) continue;
      const topla = (f) => kulup.reduce((t, s) => t + (f(s) || 0), 0);
      const ana = kulup.slice().sort((a, b) => (b.games?.minutes || 0) - (a.games?.minutes || 0))[0];
      liste.push({
        ad: o.player?.name, yas: o.player?.age, takim: ana.team?.name, ulke: ana.league?.country, lig: ana.league?.name,
        mac: topla((s) => s.games?.appearences), dakika: topla((s) => s.games?.minutes),
        gol: topla((s) => s.goals?.total), asist: topla((s) => s.goals?.assists),
        puan: ana.games?.rating ? Number(ana.games.rating).toFixed(2) : null,
      });
    }
    liste.sort((a, b) => b.dakika - a.dakika);
    onbellek(res, 12 * 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), sezon: SEZON, liste });
  } catch (e) {
    hata(res, e);
  }
}
