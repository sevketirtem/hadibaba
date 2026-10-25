// Tek maçın ayrıntısı: skor, olaylar (gol/kart/değişiklik), ilk 11'ler, maç istatistikleri.
// /api/mac?id=<fixture id>. Tek API-Football isteği (fixtures?id= hepsini birlikte verir).
// Önbellek: canlıyken 1 dk, başlamaya 2 saatten az kaldıysa 5 dk (ilk 11'ler ~1 saat önce gelir),
// daha uzaksa 1 saat, bitmişse 1 gün.
import { LIG, cors, onbellek, apiFootball, hata } from "./_ortak.js";

const CANLI = new Set(["1H", "HT", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"]);
const BITTI = new Set(["FT", "AET", "PEN", "AWD", "WO", "CANC", "ABD"]);

// İstatistik adları (API İngilizce verir); sıralama da buradaki gibi.
const ISTATISTIK = [
  ["Ball Possession", "Topla oynama"],
  ["expected_goals", "Gol beklentisi (xG)"],
  ["Total Shots", "Toplam şut"],
  ["Shots on Goal", "İsabetli şut"],
  ["Corner Kicks", "Korner"],
  ["Offsides", "Ofsayt"],
  ["Fouls", "Faul"],
  ["Yellow Cards", "Sarı kart"],
  ["Red Cards", "Kırmızı kart"],
  ["Goalkeeper Saves", "Kaleci kurtarışı"],
  ["Total passes", "Pas"],
  ["Passes %", "Pas isabeti"],
];

function oyuncu(o) {
  const p = o.player || {};
  return { ad: p.name, no: p.number, mevki: p.pos };
}

export default async function handler(req, res) {
  cors(req, res);
  if (req.method === "OPTIONS") return res.status(204).end();
  const id = String(req.query?.id || "");
  if (!/^\d{1,10}$/.test(id)) {
    onbellek(res, 86400);
    return res.status(400).json({ hata: "Geçersiz maç numarası" });
  }
  try {
    const r = await apiFootball("fixtures", { id, timezone: "Europe/Istanbul" });
    const m = r[0];
    // Yalnızca bizim ligimizin maçları (başkaları kotamızı harcamasın diye)
    if (!m || String(m.league?.id) !== String(LIG)) {
      onbellek(res, 86400);
      return res.status(404).json({ hata: "Maç bulunamadı" });
    }
    const evId = m.teams.home.id;
    const durum = m.fixture.status.short;

    const olaylar = (m.events || []).map((e) => ({
      dk: e.time?.elapsed, ek: e.time?.extra || null,
      taraf: e.team?.id === evId ? "ev" : "dep",
      tur: e.type, detay: e.detail, oyuncu: e.player?.name || null, yardimci: e.assist?.name || null,
    }));

    const kadro = {};
    for (const l of m.lineups || []) {
      kadro[l.team?.id === evId ? "ev" : "dep"] = {
        dizilis: l.formation || null, hoca: l.coach?.name || null,
        ilk11: (l.startXI || []).map(oyuncu), yedek: (l.substitutes || []).map(oyuncu),
      };
    }

    const sayi = {};
    for (const s of m.statistics || []) {
      const taraf = s.team?.id === evId ? "ev" : "dep";
      for (const x of s.statistics || []) (sayi[x.type] ||= {})[taraf] = x.value;
    }
    const istatistik = ISTATISTIK.filter(([k]) => sayi[k]).map(([k, ad]) => ({
      ad, ev: sayi[k].ev ?? 0, dep: sayi[k].dep ?? 0,
    }));

    const baslama = new Date(m.fixture.date).getTime();
    const kalan = baslama - Date.now();
    onbellek(res, CANLI.has(durum) ? 60 : BITTI.has(durum) ? 86400 : kalan < 2 * 3600e3 ? 300 : 3600);
    res.status(200).json({
      guncellendi: new Date().toISOString(),
      id: m.fixture.id, tarih: m.fixture.date, durum, dakika: m.fixture.status.elapsed,
      hafta: (m.league.round || "").replace("Regular Season - ", ""),
      stat: m.fixture.venue?.name || null, sehir: m.fixture.venue?.city || null,
      hakem: m.fixture.referee || null,
      ev: m.teams.home.name, dep: m.teams.away.name,
      evGol: m.goals.home, depGol: m.goals.away,
      iy: m.score?.halftime || null,
      olaylar, kadro, istatistik,
    });
  } catch (e) {
    hata(res, e);
  }
}
