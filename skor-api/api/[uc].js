// Tek giriş noktası: /api/<uç> → _uclar/<uç>.js. Vercel ücretsiz planı proje başına 12 fonksiyonla
// sınırlı; bütün uçlar tek fonksiyonda toplanır (adresler aynı kalır: /api/puan, /api/mac?id=…).
import durum from "./_uclar/durum.js";
import puan from "./_uclar/puan.js";
import maclar from "./_uclar/maclar.js";
import mac from "./_uclar/mac.js";
import krallar from "./_uclar/krallar.js";
import takim from "./_uclar/takim.js";
import sakat from "./_uclar/sakat.js";
import avrupa from "./_uclar/avrupa.js";
import h2h from "./_uclar/h2h.js";
import fikstur from "./_uclar/fikstur.js";
import milli from "./_uclar/milli.js";
import gurbetci from "./_uclar/gurbetci.js";
import transferler from "./_uclar/transferler.js";
import { cors } from "./_uclar/_ortak.js";

const UCLAR = { durum, puan, maclar, mac, krallar, takim, sakat, avrupa, h2h, fikstur, milli, gurbetci, transferler };

export default async function handler(req, res) {
  const uc = UCLAR[String(req.query?.uc || "")];
  if (!uc) {
    cors(req, res);
    res.setHeader("Cache-Control", "public, max-age=3600");
    return res.status(404).json({ hata: "Böyle bir uç yok", uclar: Object.keys(UCLAR) });
  }
  return uc(req, res);
}
