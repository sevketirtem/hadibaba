# Hadi Baba ⚽

**Coşkunun adresi. Yaparız baba!** → [hadibaba.com](https://hadibaba.com)

Süper Lig'i ve futbolu coşkuyla yorumlayan statik site. Sahnedeki rakibi: [Yürü Baba](https://github.com/sevketirtem/yurubaba2027).

## Teknik yapı

| Parça | Ne işe yarıyor |
|---|---|
| [Hugo](https://gohugo.io) | Markdown yazıları HTML sayfalara çeviren statik site oluşturucu |
| `layouts/` + `assets/css/` | Kendi yazdığımız tema (dış tema bağımlılığı yok). Yürü Baba ile aynı iskelet, renkler `hugo.toml`'dan gelir |
| `.github/workflows/hugo.yml` | Her push'ta ve saatte bir siteyi derleyip GitHub Pages'e yayınlar |
| `static/CNAME` | Alan adı: hadibaba.com |

## Yeni yazı

```bash
hugo new content posts/derbi-oncesi.md   # şablon: archetypes/posts.md
hugo server --buildDrafts                # http://localhost:1313
```

Yazının üst kısmında `kategoriler` (mac-onu, mac-sonu, transfer-kulisi, yuruye-cevap) ve `kaynaklar` doldurulur. `draft: false` yapılıp `main` dalına push edilince yayına girer. İleri tarihli yazılar, saatlik derlemede zamanı gelince otomatik yayınlanır.

## Yol haritası

- [x] Hugo iskeleti, kendi tema, otomatik yayın
- [ ] GoDaddy DNS → GitHub Pages bağlantısı
- [ ] Yorumlar (Cusdis)
- [x] Bluesky'a otomatik paylaşım (GitHub Actions; `.github/workflows/bluesky.yml`, secret'lar: BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)
- [ ] İstatistik kutusu (`hadibaba-istatistik` deposundan)
- [ ] Ortak temayı ayrı depoya taşıma (Hugo Module)

## Kurallar

Skor, puan ve transfer bilgisi kaynaklı yazılır; söylenti "iddia" diye etiketlenir. Gerçek kişilere hakaret yok, bahis/iddaa yok, telifli görsel yok.
