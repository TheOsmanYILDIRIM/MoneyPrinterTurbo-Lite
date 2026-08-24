# ⚡ MoneyPrinterTurbo Lite

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite/blob/main/MoneyPrinterTurbo_Colab.ipynb)
[![Kaggle](https://kaggle.com/static/images/open-in-kaggle.svg)](MoneyPrinterTurbo_Kaggle.ipynb)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Termux%20%7C%20Linux%20%7C%20Colab%20%7C%20Kaggle-brightgreen.svg)]()

> **Termux (Android Linux), ARM64, Google Colab, Kaggle GPU ve Düşük Kaynaklı Ortamlar için Optimize Edilmiş Ultra Hafif AI Video Üretim Stüdyosu & Motoru**

MoneyPrinterTurbo Lite, orijinal MoneyPrinterTurbo'nun ağır bağımlılıklarından arındırılmış, mobil cihazlarda (Termux), bulutta (Google Colab, Kaggle) ve düşük donanımlı sunucularda minimum CPU ve RAM tüketimiyle çalışan, yüksek performanslı ve tam otomatik bir yapay zeka video üretim motorudur.

---

## 🌟 Öne Çıkan Özellikler

- 🚀 **Ultra Hafif & Hızlı:** Starlette & Uvicorn tabanlı hafif mimari. Ağır kütüphaneler yerine optimize MoviePy/FFmpeg pipeline'ı.
- 📺 **4K Ultra HD & Çoklu Çözünürlük:** 4K UHD (2160p), 2K QHD (1440p), 1080p Full HD, 720p HD ve 480p SD çözünürlük desteği (9:16 Dikey, 16:9 Yatay, 1:1 Kare).
- 📱 **Mobil & Termux Uyumlu:** Android Termux üzerinde sıfır çökme, düşük bellek kullanımı ve donanım dostu hızlı video render.
- ☁️ **Google Colab & Kaggle Desteği:** `MoneyPrinterTurbo_Colab.ipynb` ve `MoneyPrinterTurbo_Kaggle.ipynb` ile Ngrok / Cloudflare tünelleri üzerinden tek tıkla GPU destekli çalıştırma.
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
├── MoneyPrinterTurbo_Kaggle.ipynb  # Kaggle GPU çalıştırma notebook'u
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

### 1. Google Colab veya Kaggle ile Çalıştırma (Bulut & GPU)
- **Google Colab:** [`MoneyPrinterTurbo_Colab.ipynb`](MoneyPrinterTurbo_Colab.ipynb) notebook'unu açın ve hücreleri sırayla çalıştırın.
- **Kaggle GPU:** [`MoneyPrinterTurbo_Kaggle.ipynb`](MoneyPrinterTurbo_Kaggle.ipynb) notebook'unu Kaggle'a yükleyin (GPU T4/P100 & Internet On) ve çalıştırın.

---

### 2. Termux (Android) Kurulumu & Çalıştırma

**Gereksinimler:** Python 3.10+ ve FFmpeg (`pkg install ffmpeg -y`)

```bash
# Depoyu klonlayın
git clone https://github.com/TheOsmanYILDIRIM/MoneyPrinterTurbo-Lite.git
cd MoneyPrinterTurbo-Lite

# Bağımlılıkları yükleyin
pip install -r requirements-lite.txt

# Başlatın
chmod +x start.sh
./start.sh
```

---

### 3. Uzak Sunucu (VPS / Cloud / Linux Server) Kurulumu ve WebUI Uzaktan Erişim

MoneyPrinterTurbo Lite, uzak bir sunucuda (Ubuntu, Debian, CentOS, AWS, Hetzner, DigitalOcean vb.) headless veya arka plan servisi olarak çalıştırıldığında WebUI arayüzüne ve tüm fonksiyonlara uzaktan erişmek için birden çok yöntem sunar.

#### 🌐 Yöntem A: Cloudflare Tunnel ile Sıfır Yapılandırmalı Genel Erişim (Önerilen)
Hiçbir port açmaya veya statik IP'ye gerek kalmadan, tek komutla dünya genelinden erişilebilir güvenli bir `https://*.trycloudflare.com` bağlantısı alabilirsiniz.

```bash
# 1. Cloudflared kurun (Ubuntu/Debian)
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cloudflared.deb

# 2. Sunucuyu Cloudflare Tüneli ile başlatın
./start.sh --tunnel cloudflare
# veya
./server.sh start --tunnel
```
*Terminalde üretilen `https://xyz.trycloudflare.com/?token=YOUR_TOKEN` bağlantısına tıklayarak doğrudan WebUI'a erişin.*

---

#### ⚡ Yöntem B: Ngrok Tunnel ile Erişim
```bash
# Ngrok ile başlatma
./start.sh --tunnel ngrok
# veya
./server.sh start -t ngrok
```
*WebUI üzerinden **Ayarlar** sekmesinden Ngrok Authtoken'ınızı kaydedebilir veya `config.toml` dosyasında belirtebilirsiniz.*

---

#### 🔌 Yöntem C: Doğrudan Sunucu IP'si ve Port (Direct IP)
Sunucunuzun 8080 portunu güvenlik duvarından (UFW / Cloud Firewall) açarak doğrudan bağlanabilirsiniz:

```bash
# UFW güvenlik duvarında porta izin verin
sudo ufw allow 8080/tcp

# Sunucuyu başlatın
./server.sh start
```
*Tarayıcınızdan `http://SUNUCU_IP_ADRESI:8080/?token=YOUR_AUTH_TOKEN` adresine gidin.*

---

#### 🔒 Yöntem D: SSH Tüneli (SSH Port Forwarding)
Portları dışarıya açmak istemiyorsanız yerel bilgisayarınızdan SSH tüneli kurarak `localhost` gibi bağlanabilirsiniz:

```bash
# Yerel bilgisayarınızın terminalinde çalıştırın:
ssh -N -L 8080:127.0.0.1:8080 kullanici@sunucu_ip
```
*Ardından yerel tarayıcınızda `http://127.0.0.1:8080/?token=YOUR_AUTH_TOKEN` adresini açın.*

---

#### 🛡️ Yöntem E: Nginx Reverse Proxy & SSL (Domain ile Erişim)
Kendi domain adınız ile çalıştırmak için örnek Nginx konfigürasyonu:

```nginx
server {
    server_name video.alanadiniz.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 250M;
    }
}
```

---

#### 🔄 Yöntem F: Systemd ile 7/24 Arka Planda Servis Olarak Çalıştırma
Sunucu yeniden başladığında otomatik çalışması için:

`/etc/systemd/system/moneyprinter.service`:
```ini
[Unit]
Description=MoneyPrinter Turbo Lite Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/MoneyPrinterTurbo-Lite
ExecStart=/usr/bin/python3 /home/ubuntu/MoneyPrinterTurbo-Lite/lite_server.py --host 0.0.0.0 --port 8080 --tunnel cloudflare
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now moneyprinter
sudo systemctl status moneyprinter
```

---

## 🛠️ Sunucu Yönetim Komutları (`server.sh`)

Sunucunuzda süreçleri kolayca yönetmek için `server.sh` scriptini kullanabilirsiniz:

```bash
./server.sh start          # Sunucuyu arka planda başlatır
./server.sh start --tunnel # Sunucuyu Cloudflare tüneli ile başlatır
./server.sh stop           # Sunucuyu ve tüm tünelleri durdurur
./server.sh restart        # Sunucuyu yeniden başlatır
./server.sh status         # Aktif URL'leri, yerel/sunucu IP'lerini ve tünel durumunu gösterir
./server.sh logs           # Canlı sunucu loglarını görüntüler
./server.sh tunnel         # Çalışan sunucuya dinamik olarak tünel bağlar
./server.sh tunnel-stop    # Aktif tüneli kapatır
```

---

## 🖥️ WebUI Özellikleri & Uzaktan Yapılabilen Tüm İşlemler

Uzak sunucudaki WebUI arayüzü üzerinden aşağıdaki tüm işlemler eksiksiz yapılabilir:

1. 🎬 **Tekli Video Üretimi (`tab-create`):**
   - Konu / Senaryo girişi veya AI (Gemini, DeepSeek, OpenAI, Claude, Groq) ile tek tıkla senaryo & arama terimleri üretimi.
   - 4K UHD, 2K QHD, 1080p, 720p çözünürlük ve 9:16, 16:9, 1:1 en-boy oranı seçimi.
   - Pexels otomatik çoklu stok video indirme ve sahne eşleme.
   - Özel arka plan görseli/videosu veya özel ses dosyası yükleme.
   - Gelişmiş altyazı renkleri, font boyutu, kalınlık (bold), çerçeve (stroke), arka plan kutusu ve vurgulu kelime efektleri.
   - Arka plan müziği (BGM) ses seviyesi ve geçiş efektleri (crossfade).

2. ⚡ **Toplu Video Üretimi (`tab-batch`):**
   - Çoklu ders veya konu listesini JSON formatında veya metin kutusuna girerek tek tıkla kuyruğa alma.
   - Otomatik ses havuzu (Voice Pool) ile her videoda farklı Türkçe/Yabancı ses kullanabilme.
   - Görevleri sırayla işleme, hata durumunda kaldığı yerden devam edebilme (Resume).

3. 📜 **Görev Geçmişi & Medya Yönetimi (`tab-history`):**
   - Tamamlanan videoları tarayıcıda doğrudan oynatma ve canlı önizleme.
   - Tek tek video indirme veya tüm günün/tüm üretilen videoları **Tek Tıkla ZIP Olarak İndirme**.
   - Yeniden render alma, ses/görüntü varyantı üretme, görevi iptal etme veya silme.

4. ⚙️ **Ayarlar & Kimlik Doğrulama (`tab-settings`):**
   - API anahtarlarını (OpenAI, Gemini, DeepSeek, Groq, Pexels, ElevenLabs, Azure) tarayıcıdan güvenle tanımlama ve kaydetme.
   - Dahili seslendirme önizleme çaları (Voice Preview) ile sesleri test etme.
   - Arka plan müzikleri (BGM) yükleme ve silme.
   - **Canlı Tünel Kontrolü:** WebUI içerisinden tek tıkla Cloudflare veya Ngrok tünelini başlatma/durdurma, tokenlı genel erişim bağlantısını kopyalama.

---

## ⚙️ REST API & Entegrasyon

`lite_server.py` HTTP REST API uçları:

- **GET `/api/tunnel/status`**: Aktif tünel durumu, sunucu IP'leri ve tokenlı bağlantıları döner.
- **POST `/api/tunnel/start`**: `{"provider": "cloudflare"|"ngrok"}` ile dinamik tünel başlatır.
- **POST `/api/tunnel/stop`**: Aktif tüneli durdurur.
- **POST `/api/generate`**: Tekli video üretim görevi başlatır.
- **POST `/api/batch`**: Toplu video üretim görevi başlatır.
- **GET `/api/tasks`**: Tüm görevlerin durumunu listeler.
- **GET `/api/tasks/{task_id}`**: Tekil görev durumunu döner.
- **GET `/api/tasks/download-all-zip`**: Tüm tamamlanmış videoları tek bir ZIP arşivi olarak indirir.
- **POST `/api/llm/generate`**: LLM ile otomatik senaryo üretir.

---

## 📜 Lisans

Bu proje [MIT Lisansı](LICENSE) ile lisanslanmıştır. Orijinal MoneyPrinterTurbo projesine ve açık kaynak topluluğuna teşekkür ederiz.
