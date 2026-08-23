# ⚡ MoneyPrinterTurbo Lite

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite/blob/main/MoneyPrinterTurbo_Colab.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Colab-brightgreen.svg)]()

> **Termux (Android Linux), ARM64, Google Colab ve Düşük Kaynaklı Ortamlar için Optimize Edilmiş Ultra Hafif AI Video Üretim Stüdyosu & Motoru**

MoneyPrinterTurbo Lite, orijinal MoneyPrinterTurbo'nun ağır bağımlılıklarından arındırılmış, mobil cihazlarda (Termux), bulutta (Google Colab) ve düşük donanımlı sunucularda minimum CPU ve RAM tüketimiyle çalışan, yüksek performanslı ve tam otomatik bir yapay zeka video üretim motorudur.

---

## 🌟 Öne Çıkan Özellikler

- 🚀 **Ultra Hafif & Hızlı:** Starlette & Uvicorn tabanlı hafif mimari. Ağır kütüphaneler yerine optimize MoviePy/FFmpeg pipeline'ı.
- 📺 **4K Ultra HD & Çoklu Çözünürlük:** 4K UHD (2160p), 2K QHD (1440p), 1080p Full HD, 720p HD ve 480p SD çözünürlük desteği (9:16 Dikey, 16:9 Yatay, 1:1 Kare).
- 📱 **Mobil & Termux Uyumlu:** Android Termux üzerinde sıfır çökme, düşük bellek kullanımı ve donanım dostu hızlı video render.
- ☁️ **Google Colab Desteği:** `MoneyPrinterTurbo_Colab.ipynb` ile Ngrok / Cloudflare tünelleri üzerinden tek tıkla GPU destekli çalıştırma.
- 🎙️ **Dahili Edge TTS:** Çoklu dil ve doğal ses seçenekleriyle (Türkçe dahil yüzlerce ses) ücretsiz, yüksek kaliteli seslendirme.
- 🧠 **Çoklu LLM Entegrasyonu:** OpenAI, DeepSeek, Google Gemini, Anthropic Claude, Groq ve yerel modeller ile tam otomatik senaryo ve görsel arama terimi üretimi.
- 🎬 **Akıllı Montaj & Çoklu Stok Video:** Sahne bazlı Pexels video arama motoru ile her sahneye uygun farklı videolar indirme ve yumuşak geçiş (Crossfade) efektleri.
- 📝 **Gelişmiş Altyazı Stüdyosu:** Kalın yazı tipi (Bold), geniş renk paletleri, kontur/çerçeve renkleri, yarı saydam kutu modu, konumlandırma ve çözünürlüğe duyarlı dinamik font ölçekleme.
- 🌐 **Modern Web Stüdyosu:** Mobil uyumlu, responsive ve modern WebUI arayüzü.
- ⚡ **Toplu Video Üretimi (Batch Processing):** Tek seferde birden fazla ders veya içerik videosunu kuyruğa alarak ardışık üretme desteği (`batch_engine.py`).
- 🔐 **Token Tabanlı Güvenlik:** Web arayüzü ve API için dahili token doğrulaması.

---

## 📂 Dizin Yapısı

```
MoneyPrinterTurbo-Lite/
├── app/                            # Temel modüller, servisler ve API uçları
├── resource/                       # Dahili fontlar ve arka plan müzikleri (BGM)
├── webui/                          # Web stüdyosu arayüzü ve dil dosyaları
├── MoneyPrinterTurbo_Colab.ipynb   # Google Colab çalıştırma notebook'u
├── lite_engine.py                  # 4K & çoklu video destekli render motoru
├── lite_server.py                  # Starlette tabanlı REST API ve web sunucusu
├── batch_engine.py                 # Toplu video işleme motoru
├── worker.py                       # Arka plan görev işleyicisi (Worker)
├── task_store.py                   # Görev durumu ve kalıcılık yöneticisi
├── settings_manager.py             # Ayarlar ve kimlik doğrulama yöneticisi
├── llm_service.py                  # LLM servis entegrasyonu
├── start.sh                        # Termux / Linux tek tıkla başlatıcı
├── requirements-lite.txt           # Minimal bağımlılık listesi
├── config.example.toml             # Örnek yapılandırma şablonu
└── README.md
```

---

## 🚀 Hızlı Başlangıç

### 1. Google Colab ile Çalıştırma (En Kolay & Hızlı)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite/blob/main/MoneyPrinterTurbo_Colab.ipynb) butonuna tıklayın ve hücreleri sırayla çalıştırın. Ngrok veya Cloudflare üzerinden anında erişin!

---

### 2. Termux & Linux Kurulumu

**Gereksinimler:** Python 3.10+ ve FFmpeg (`pkg install ffmpeg -y` veya `apt install ffmpeg -y`)

```bash
# Depoyu klonlayın
git clone https://github.com/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite.git
cd MoneyPrinterTurbo-Lite

# Bağımlılıkları yükleyin
pip install -r requirements-lite.txt

# Yapılandırmayı oluşturun
cp config.example.toml config.toml
```

`config.toml` dosyasında LLM API anahtarınızı (Gemini, DeepSeek, OpenAI vb.) ve Pexels API anahtarınızı tanımlayın.

**Çalıştırma:**
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

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Orijinal MoneyPrinterTurbo projesine ve açık kaynak topluluğuna teşekkür ederiz.
