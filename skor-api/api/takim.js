// Takım sayfası verisi: kulüp bilgisi, son 5 ve sıradaki 3 maç, kadro, sakat/cezalılar.
// /api/takim?id=<takım no>. Beş API-Football isteği; 3 saat önbellek (canlı maç varken 5 dk).
import { SEZON, cors, onbellek, apiFootball, hata, macOzet, sayi, CANLI } from "./_ortak.js";

const MEVKI = { Goalkeeper: "Kaleci", Defender: "Defans", Midfielder: "Orta saha", Attacker: "Forvet" };

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  const id = sayi(req.query?.id);
  if (!id) { onbellek(res, 86400); return res.status(400).json({ hata: "Geçersiz takım numarası" }); }
  try {
    const tz = "Europe/Istanbul";
    const [bilgi, son, sonraki, kadro, sakat] = await Promise.all([
      apiFootball("teams", { id }),
      apiFootball("fixtures", { team: id, last: 5, timezone: tz }),
      apiFootball("fixtures", { team: id, next: 3, timezone: tz }),
      apiFootball("players/squads", { team: id }).catch(() => []),
      apiFootball("injuries", { team: id, season: SEZON, timezone: tz }).catch(() => []),
    ]);
    const t = bilgi[0];
    if (!t || t.team?.country !== "Turkey") {
      onbellek(res, 86400);
      return res.status(404).json({ hata: "Takım bulunamadı" });
    }
    const simdi = Date.now();
    // Sakatlık kaydı maç başına tutulur; yalnızca henüz oynanmamış (ya da bugünkü) maçlar
    const goruldu = new Set();
    const sakatlar = sakat
      .filter((s) => new Date(s.fixture?.date).getTime() > simdi - 12 * 3600e3)
      .sort((a, b) => a.fixture.date.localeCompare(b.fixture.date))
      .filter((s) => !goruldu.has(s.player?.id) && goruldu.add(s.player?.id))
      .map((s) => ({ oyuncu: s.player?.name, tur: s.player?.type, sebep: s.player?.reason, mac: s.fixture?.date }));
    const oyuncular = (kadro[0]?.players || []).map((p) => ({
      ad: p.name, no: p.number, yas: p.age, mevki: MEVKI[p.position] || p.position,
    }));
    const sonMaclar = son.map(macOzet).sort((a, b) => b.tarih.localeCompare(a.tarih));
    const sonrakiler = sonraki.map(macOzet);
    const canli = [...sonMaclar, ...sonrakiler].some((m) => CANLI.has(m.durum));
    onbellek(res, canli ? 300 : 3 * 3600);
    res.status(200).json({
      guncellendi: new Date().toISOString(),
      takim: { id: t.team.id, ad: t.team.name, kurulus: t.team.founded },
      stat: t.venue ? { ad: t.venue.name, sehir: t.venue.city, kapasite: t.venue.capacity } : null,
      son: sonMaclar, sonraki: sonrakiler, kadro: oyuncular, sakatlar,
    });
  } catch (e) {
    hata(res, e);
  }
}
