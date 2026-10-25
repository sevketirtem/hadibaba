// Süper Lig kulüplerinin bu sezonki (1 Haziran'dan beri) transferleri. 1 + 18 istek; 12 saat önbellek.
import { LIG, SEZON, cors, onbellek, apiFootball, hata } from "./_ortak.js";

export function transferListesi(r, takimId, baslangic) {
  const out = [];
  for (const o of r) {
    for (const t of o.transfers || []) {
      if (!t.date || t.date < baslangic) continue;
      const gelen = t.teams?.in?.id === takimId;
      out.push({ oyuncu: o.player?.name, tarih: t.date, tur: t.type || "", yon: gelen ? "gelen" : "giden",
        takim: gelen ? t.teams?.in?.name : t.teams?.out?.name, karsi: gelen ? t.teams?.out?.name : t.teams?.in?.name });
    }
  }
  return out.sort((a, b) => b.tarih.localeCompare(a.tarih));
}

export const SEZON_BASI = `${SEZON}-06-01`;

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  try {
    const tablo = await apiFootball("standings", { league: LIG, season: SEZON });
    const takimlar = (tablo[0]?.league?.standings?.[0] || []).map((t) => t.team);
    const hepsi = await Promise.all(takimlar.map((t) =>
      apiFootball("transfers", { team: t.id }).then((r) => transferListesi(r, t.id, SEZON_BASI)).catch(() => [])));
    // Aynı transfer iki Süper Lig kulübünde de görünür: bir kez say
    const goruldu = new Set();
    const liste = hepsi.flat().filter((t) => {
      const k = `${t.oyuncu}|${t.tarih}`;
      if (goruldu.has(k)) return false;
      goruldu.add(k);
      return true;
    }).sort((a, b) => b.tarih.localeCompare(a.tarih));
    onbellek(res, 12 * 3600);
    res.status(200).json({ guncellendi: new Date().toISOString(), baslangic: SEZON_BASI, liste });
  } catch (e) {
    hata(res, e);
  }
}
