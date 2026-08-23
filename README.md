# ⚡ MoneyPrinterTurbo Lite

> **Termux (Android Linux), ARM64 ve Düşük Kaynaklı Ortamlar için Optimize Edilmiş Ultra Hafif AI Video Üretim Stüdyosu & Motoru**

MoneyPrinterTurbo Lite, orijinal MoneyPrinterTurbo'nun ağır bağımlılıklarından arındırılmış, mobil cihazlarda (Termux) ve düşük donanımlı sunucularda minimum CPU ve RAM tüketimiyle çalışan, yüksek performanslı ve tam otomatik bir yapay zeka video üretim motorudur.

---

## 🌟 Öne Çıkan Özellikler

- 🚀 **Ultra Hafif & Hızlı:** Starlette & Uvicorn tabanlı hafif mimari. Ağır kütüphaneler yerine optimize MoviePy/FFmpeg pipeline'ı.
- 📱 **Mobil & Termux Uyumlu:** Android Termux üzerinde sıfır çökme, düşük bellek kullanımı ve donanım dostu 720p / 1080p video render.
- 🎙️ **Dahili Edge TTS:** Çoklu dil ve doğal ses seçenekleriyle (Türkçe dahil yüzlerce ses) ücretsiz, yüksek kaliteli seslendirme.
- 🧠 **Çoklu LLM Entegrasyonu:** OpenAI, DeepSeek, Google Gemini, Anthropic Claude, Groq ve yerel modeller ile tam otomatik senaryo ve görsel arama terimi üretimi.
- 🎬 **Akıllı Montaj & Altyazı:** Otomatik altyazı senkronizasyonu, fon müziği (BGM) karıştırma, geçiş efektleri ve telifsiz video/görsel eşleştirme (Pexels, Pixabay vb.).
- 🌐 **Modern Web Stüdyosu:** Mobil uyumlu, responsive ve modern WebUI arayüzü.
- ⚡ **Toplu Video Üretimi (Batch Processing):** Tek seferde birden fazla ders veya içerik videosunu kuyruğa alarak ardışık üretme desteği (`batch_engine.py`).
- 🔐 **Token Tabanlı Güvenlik:** Web arayüzü ve API için dahili token doğrulaması.

---

## 📂 Dizin Yapısı

```
MoneyPrinterTurbo-Lite/
├── app/                  # Temel modüller, servisler ve API uçları
├── resource/             # Dahili fontlar ve arka plan müzikleri (BGM)
├── webui/                # Web stüdyosu arayüzü ve dil dosyaları
├── lite_engine.py        # Optimize video render ve derleme motoru
├── lite_server.py        # Starlette tabanlı REST API ve web sunucusu
├── batch_engine.py       # Toplu video işleme motoru
├── worker.py             # Arka plan görev işleyicisi (Worker)
├── task_store.py         # Görev durumu ve kalıcılık yöneticisi
├── settings_manager.py   # Ayarlar ve kimlik doğrulama yöneticisi
├── llm_service.py        # LLM servis entegrasyonu
├── start.sh              # Tek tıkla başlatma betiği
├── requirements-lite.txt # Minimal bağımlılık listesi
├── config.example.toml   # Örnek yapılandırma şablonu
└── README.md
```

---

## 🚀 Hızlı Başlangıç

### 1. Gereksinimler

- **Python:** 3.10+
- **FFmpeg:** Sistemde kurulu olmalıdır (`pkg install ffmpeg` veya `apt install ffmpeg`).

### 2. Kurulum

```bash
# Depoyu klonlayın
git clone https://github.com/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite.git
cd MoneyPrinterTurbo-Lite

# Bağımlılıkları yükleyin
pip install -r requirements-lite.txt
```

### 3. Yapılandırma

```bash
# Örnek yapılandırmayı kopyalayın
cp config.example.toml config.toml
```

`config.toml` dosyasında LLM API anahtarınızı (Gemini, DeepSeek, OpenAI vb.) ve video sağlayıcı anahtarlarınızı (örn. Pexels) tanımlayın.

### 4. Çalıştırma

**Termux / Linux Tek Tıkla Başlatma:**
```bash
chmod +x start.sh
./start.sh
```

Sunucu başladığında terminalde tokenlı erişim bağlantısı gösterilecek ve otomatik olarak tarayıcınızda açılacaktır:
```
http://127.0.0.1:8080/?token=YOUR_AUTH_TOKEN
```

---

## ⚙️ REST API & Kullanım

`lite_server.py` üzerinden video üretim görevleri başlatılabilir:

- **POST `/api/v1/tasks`**: Yeni video üretim görevi oluşturur.
- **GET `/api/v1/tasks/{task_id}`**: Görev durumunu, ilerleme yüzdesini ve tamamlanan video URL'sini döner.
- **GET `/api/v1/tasks`**: Tüm görevlerin listesini döner.

---

## 📜 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Orijinal MoneyPrinterTurbo projesine ve topluluğuna katkıları için teşekkürler.
