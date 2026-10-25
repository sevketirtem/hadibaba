// Süper Lig sakat ve cezalı listesi: her oyuncunun sıradaki maçı için en son kaydı.
// Tek API-Football isteği (injuries?league&season), 3 saat önbellek.
import { LIG, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const r = await apiFootball("injuries", { league: LIG, season: SEZON, timezone: "Europe/Istanbul" });
    const simdi = Date.now();
    const goruldu = new Set();
    const liste = r
      .filter((s) => {
        const t = new Date(s.fixture?.date).getTime();
        return t > simdi - 12 * 3600e3 && t < simdi + 10 * 86400e3; // bugün ve önümüzdeki 10 gün
      })
      .sort((a, b) => a.fixture.date.localeCompare(b.fixture.date))
      .filter((s) => !goruldu.has(s.player?.id) && goruldu.add(s.player?.id))
      .map((s) => ({
        oyuncu: s.player?.name, takim: s.team?.name, takimId: s.team?.id,
        tur: s.player?.type, sebep: s.player?.reason, mac: s.fixture?.date, macId: s.fixture?.id,
      }));
    onbellek(res, 3 * 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), liste });
  } catch (e) {
    hata(res, e);
  }
}
