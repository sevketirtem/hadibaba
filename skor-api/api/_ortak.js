// Ortak yardımcılar: API-Football çağrısı, CORS, önbellek başlıkları.
// Ortam değişkenleri (Vercel → Settings → Environment Variables):
//   APIFOOTBALL_KEY  (zorunlu) dashboard.api-football.com'dan ücretsiz anahtar
//   LIG              Süper Lig = 203 (varsayılan)
//   SEZON            2026 (2026-27 sezonu; varsayılan)
//   IZINLI_KOKENLER  virgülle: https://hadibaba.com,https://yurubaba.com (varsayılan bunlar)

const API = "https://v3.football.api-sports.io";
export const LIG = process.env.LIG || "203";
export const SEZON = process.env.SEZON || "2026";
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
  onbellek(res, 300); // hata da 5 dk önbellekte kalsın, kota boşa gitmesin
  res.status(502).json({ hata: String(e.message || e) });
}
