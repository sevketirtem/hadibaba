// A Milli Takım: son 5 ve sıradaki 3 maç, kadro. 4 API-Football isteği, 6 saat (canlıda 5 dk).
import { cors, onbellek, apiFootball, hata, macOzet, CANLI } from "./_ortak.js";

const MEVKI = { Goalkeeper: "Kaleci", Defender: "Defans", Midfielder: "Orta saha", Attacker: "Forvet" };

// API-Football adı zamanla "Turkey" → "Türkiye" olabiliyor; sırayla dener, en son aramaya geçer.
export async function milliTakim() {
  const deneme = [{ name: "Türkiye" }, { name: "Turkey" }, { search: "Turk" }, { country: "Turkey" }];
  for (const q of deneme) {
    const r = await apiFootball("teams", q).catch(() => []);
    const t = r.find((x) => x.team?.national && /^t[üu]rk/i.test(x.team?.name || "")) || r.find((x) => x.team?.national);
    if (t) return t.team;
  }
  throw new Error("Milli takım bulunamadı");
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const takim = await milliTakim();
    const tz = "Europe/Istanbul";
    const [son, sonraki, kadro] = await Promise.all([
      apiFootball("fixtures", { team: takim.id, last: 5, timezone: tz }),
      apiFootball("fixtures", { team: takim.id, next: 3, timezone: tz }),
      apiFootball("players/squads", { team: takim.id }).catch(() => []),
    ]);
    const s = son.map(macOzet).sort((a, b) => b.tarih.localeCompare(a.tarih)), n = sonraki.map(macOzet);
    onbellek(res, [...s, ...n].some((m) => CANLI.has(m.durum)) ? 300 : 6 * 3600);
    res.status(200).json({
      guncellendi: new Date().toISOString(), takim: { id: takim.id, ad: takim.name },
      son: s, sonraki: n,
      kadro: (kadro[0]?.players || []).map((p) => ({ id: p.id, ad: p.name, no: p.number, yas: p.age, mevki: MEVKI[p.position] || p.position })),
    });
  } catch (e) {
    hata(res, e);
  }
}
