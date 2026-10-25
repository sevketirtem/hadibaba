# superlig-veri (Vercel)

hadibaba.com ve yurubaba.com'daki canlı skor / puan durumu kutularının veri kaynağı.
API-Football Pro planı (günde 7.500 istek; 25 Ekim 2026'dan itibaren, 1 aylık) ziyaretçi sayısından bağımsız kalsın diye
yanıtlar Vercel CDN'de önbelleğe alınır:

| Uç | İçerik | Önbellek |
|---|---|---|
| `/api/maclar` | bugün −3 / +4 gün maçları (canlı skor, dakika) | canlı maç varken 6 dk, yoksa 60 dk |
| `/api/puan` | puan durumu | 2 saat |
| `/api/mac?id=` | tek maç: olaylar, ilk 11'ler, istatistik (yalnızca Süper Lig maçları) | canlı 1 dk, başlamaya <2 saat 5 dk, yoksa 1 saat, bitmiş 1 gün |
| `/api/krallar` | gol ve asist krallığı (ilk 20) | 6 saat |
| `/api/durum` | kalan kota (kotadan düşmez) | yok |

En kötü gün tahmini: canlı 6 saat × 10 + 18 saat × 1 + puan 12 ≈ 90 istek.

## Kurulum
1. dashboard.api-football.com → ücretsiz hesap → API anahtarı.
2. Vercel → Add New → Project → `sevketirtem/hadibaba` deposunu seç →
   **Root Directory: `skor-api`** → Framework: Other.
3. Environment Variables: `APIFOOTBALL_KEY` = anahtar (isteğe bağlı: `SEZON`, `LIG`).
4. Deploy → adres (ör. `https://superlig-veri.vercel.app`) iki sitenin hugo.toml'unda `skorAPI`.
