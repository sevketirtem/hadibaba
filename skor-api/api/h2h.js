// İki takımın son 5 karşılaşması. /api/h2h?a=<takım no>&b=<takım no>. 12 saat önbellek.
import { cors, onbellek, apiFootball, hata, macOzet, sayi } from "./_ortak.js";

const BITTI = new Set(["FT", "AET", "PEN"]);

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  const a = sayi(req.query?.a), b = sayi(req.query?.b);
  if (!a || !b || a === b) { onbellek(res, 86400); return res.status(400).json({ hata: "Geçersiz takımlar" }); }
  // Önbellek anahtarı sıraya bağlı olmasın
  const [x, y] = [a, b].sort();
  try {
    const r = await apiFootball("fixtures/headtohead", { h2h: `${x}-${y}`, last: 10, timezone: "Europe/Istanbul" });
    const maclar = r.map(macOzet).filter((m) => BITTI.has(m.durum))
      .sort((p, q) => q.tarih.localeCompare(p.tarih)).slice(0, 5);
    onbellek(res, 12 * 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), maclar });
  } catch (e) {
    hata(res, e);
  }
}
