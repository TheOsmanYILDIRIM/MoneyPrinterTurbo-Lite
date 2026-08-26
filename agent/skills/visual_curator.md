# Visual Curator & Vision Inspector Skill

Bu beceri, Pexels ve Pixabay gibi kaynaklardan video ararken düşük veri tüketimiyle (yalnızca thumbnail) en yüksek görsel isabetini sağlamak için çalışır.

## 🎯 Çalışma Mantığı
1. **Thumbnail-Only Fetch:** Asla video dosyası indirilmez; her adayın yalnızca küçük resim (thumbnail, ~20-40KB) ve meta etiketleri çekilir.
2. **Vision Feedback Loop:** Çok modlu LLM (Gemini Vision) thumbnail görselini sahne metniyle karşılaştırır:
   - "Görsel, konuyla ve sahne tonuyla uyumlu mu?" (Puan: 1 - 10)
   - "Kompozisyon, kontrast ve kalite yeterli mi?"
3. **İteratif Arama:** Eğer ilk 3 aday 7/10 puanın altında kalırsa, ajan arama kelimesini daraltıp/genişletip alternatif arama yapar (Maksimum 3 deneme).
4. **Çözünürlük Bağımsız Kayıt:** Seçilen videonun sadece sağlayıcısı (Pexels/Pixabay), video ID'si ve önizleme URL'si kaydedilir.
