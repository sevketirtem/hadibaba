// Süper Lig takımlarının Avrupa kupası maçları (bugün -7 / +14 gün) ve lig aşaması sıraları.
// Süper Lig takımları. 7 API-Football isteği; canlı maç varken 5 dk, yoksa 3 saat.
import { LIG, SEZON, AVRUPA, CANLI, cors, onbellek, apiFootball, hata, macOzet, gun } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const tablo = await apiFootball("standings", { league: LIG, season: SEZON });
    const turk = new Set((tablo[0]?.league?.standings?.[0] || []).map((t) => t.team.id));
    const kupalar = await Promise.all(Object.entries(AVRUPA).map(async ([id, ad]) => {
      const [fikstur, sira] = await Promise.all([
        apiFootball("fixtures", { league: id, season: SEZON, from: gun(-7), to: gun(14), timezone: "Europe/Istanbul" }).catch(() => []),
        apiFootball("standings", { league: id, season: SEZON }).catch(() => []),
      ]);
      const maclar = fikstur.filter((m) => turk.has(m.teams.home.id) || turk.has(m.teams.away.id))
        .map(macOzet).sort((a, b) => a.tarih.localeCompare(b.tarih));
      // Lig aşaması tek tablo (36 takım); Süper Lig takımlarının satırları
      const satirlar = (sira[0]?.league?.standings || []).flat()
        .filter((t) => turk.has(t.team.id))
        .map((t) => ({ sira: t.rank, takim: t.team.name, id: t.team.id, o: t.all.played, g: t.all.win,
          b: t.all.draw, m: t.all.lose, av: t.goalsDiff, p: t.points, grup: t.group }));
      const toplam = (sira[0]?.league?.standings || []).flat().length;
      return { id, ad, maclar, siralar: satirlar, takimSayisi: toplam };
    }));
    const canli = kupalar.some((k) => k.maclar.some((m) => CANLI.has(m.durum)));
    onbellek(res, canli ? 300 : 3 * 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), kupalar });
  } catch (e) {
    hata(res, e);
  }
}
