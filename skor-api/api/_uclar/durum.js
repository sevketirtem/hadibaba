// Kota kontrolü (API-Football /status kotadan düşmez). Önbelleksiz.
import { cors, apiFootball } from "./_ortak.js";

export default async function handler(req, res) {
  cors(req, res);
  res.setHeader("Cache-Control", "no-store");
  try {
    const r = await apiFootball("status", {});
    const s = Array.isArray(r) ? r[0] : r;
    res.status(200).json({ plan: s?.subscription?.plan, istek: s?.requests });
  } catch (e) {
    res.status(502).json({ hata: String(e.message || e) });
  }
}
