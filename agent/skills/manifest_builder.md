# Production Manifest Builder Skill (Sinematik Kartsız Standart)

Bu beceri, Colab ve MoneyPrinterTurbo render motoruna gidecek nihai `production_manifest.json` dosyasını standartlaştırır.

## 🎯 Standartlar
- **Görsel Alan:** Tam ekran 9:16 veya 16:9 sinematik stok videolar (Büyük kapatıcı kartlar/kutucuklar içermez).
- **Altyazı:** Dinamik kelime vurgulu (`highlight_words`), modern `.ass` formatında doğrudan video üstüne gömülü altyazı.
- **Timeline:** Saniye bazlı sahne geçişleri, Pexels video kimlikleri ve indirme referansları.
- **Taşınabilirlik:** Telefonda sadece JSON olarak saklanır; Colab veya yerel işçi istediği çözünürlükte (480p, 720p, 1080p, 4K) tek tıkla derler.
