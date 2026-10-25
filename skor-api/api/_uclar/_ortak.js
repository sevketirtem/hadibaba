// Ortak yardımcılar: API-Football çağrısı, CORS, önbellek başlıkları.
// Ortam değişkenleri (Vercel → Settings → Environment Variables):
//   APIFOOTBALL_KEY  (zorunlu) dashboard.api-football.com'dan ücretsiz anahtar
//   LIG              Süper Lig = 203 (varsayılan)
//   SEZON            2026 (2026-27 sezonu; varsayılan)
//   IZINLI_KOKENLER  virgülle: https://hadibaba.com,https://yurubaba.com (varsayılan bunlar)

const API = "https://v3.football.api-sports.io";
export const LIG = process.env.LIG || "203";
export const SEZON = process.env.SEZON || "2026";
// ?lig= ile seçilebilen ligler: Süper Lig (203), 1. Lig (204). Başka değer → Süper Lig.
const LIGLER = { "203": "Süper Lig", "204": "1. Lig" };
export function ligSec(req) {
  const l = String(req.query?.lig || "");
  return LIGLER[l] ? l : LIG;
}
// Avrupa kupaları: Şampiyonlar Ligi, Avrupa Ligi, Konferans Ligi
export const AVRUPA = { "2": "Şampiyonlar Ligi", "3": "Avrupa Ligi", "848": "Konferans Ligi" };
export const CANLI = new Set(["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"]);

// Fikstür kaydını sadeleştirir (maclar, takim, avrupa, h2h ortak)
export function macOzet(m) {
  return {
    id: m.fixture.id, tarih: m.fixture.date, durum: m.fixture.status.short, dakika: m.fixture.status.elapsed,
    lig: m.league?.name, ligId: m.league?.id, hafta: (m.league?.round || "").replace("Regular Season - ", ""),
    ev: m.teams.home.name, dep: m.teams.away.name, evId: m.teams.home.id, depId: m.teams.away.id,
    evGol: m.goals.home, depGol: m.goals.away,
  };
}

// İstanbul tarihi (UTC+3), bugünden fark gün
export function gun(fark) {
  return new Date(Date.now() + 3 * 3600e3 + fark * 86400e3).toISOString().slice(0, 10);
}

export function sayi(v, enFazla = 1e9) {
  const s = String(v || "");
  return /^\d{1,9}$/.test(s) && Number(s) <= enFazla ? s : null;
}
const KOKENLER = (process.env.IZINLI_KOKENLER ||
  "https://hadibaba.com,https://www.hadibaba.com,https://yurubaba.com,https://www.yurubaba.com,http://localhost:1313")
  .split(",").map((s) => s.trim());

export function cors(req, res) {
  const origin = req.headers.origin;
  if (origin && KOKENLER.includes(origin)) {
    res.setHeader("Access-Control-Allow-Origin", origin);
    res.setHeader("Vary", "Origin");
  }
  res.setHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
}

// Vercel CDN önbelleği: aynı yanıt "saniye" boyunca tüm ziyaretçilere verilir;
// API-Football'a ancak süre dolunca yeni istek gider (ücretsiz plan: günde 100).
export function onbellek(res, saniye) {
  const deger = `public, s-maxage=${saniye}, stale-while-revalidate=${saniye * 2}`;
  res.setHeader("Cache-Control", "public, max-age=60");
  res.setHeader("CDN-Cache-Control", deger);
  res.setHeader("Vercel-CDN-Cache-Control", deger);
}

export async function apiFootball(yol, params) {
  const key = process.env.APIFOOTBALL_KEY;
  if (!key) throw new Error("APIFOOTBALL_KEY tanımlı değil");
  const url = `${API}/${yol}?${new URLSearchParams(params)}`;
  const r = await fetch(url, { headers: { "x-apisports-key": key } });
  if (!r.ok) throw new Error(`API-Football HTTP ${r.status}`);
  const j = await r.json();
  const hatalar = j.errors && (Array.isArray(j.errors) ? j.errors : Object.values(j.errors));
  if (hatalar && hatalar.length) throw new Error(`API-Football: ${hatalar.join("; ")}`);
  return j.response || [];
}

export function hata(res, e) {
  onbellek(res, 30); // hata kısa süre önbellekte kalsın (Pro planda kota rahat), sonra yeniden denensin
  res.status(502).json({ hata: String(e.message || e) });
}
