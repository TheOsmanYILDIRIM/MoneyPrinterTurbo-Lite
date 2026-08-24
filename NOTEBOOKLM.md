# 📘 MoneyPrinter Turbo Lite - NotebookLM Kapsamlı Bilgi Tabanı ve Sistem Kılavuzu

Bu belge, **MoneyPrinter Turbo Lite** projesinin mimarisi, uzak sunucu (VPS/Cloud) dağıtımı, tünelleme mekanizmaları, WebUI özellikleri, REST API uçları, toplu üretim motoru ve sorun giderme yöntemleri dahil olmak üzere tüm teknik ve operasyonel detaylarını içeren tam kaynak dokümandır. Google NotebookLM'e kaynak olarak yüklenmeye uygun şekilde yapılandırılmıştır.

---

## 1. Proje Genel Bakışı ve Temel Hedefler

MoneyPrinter Turbo Lite; mobil cihazlarda (Android Termux), bulut ortamlarında (Google Colab, AWS, GCP, DigitalOcean, Hetzner) ve düşük kaynaklı sunucularda (VPS) minimum CPU ve RAM tüketimiyle çalışan, yüksek performanslı ve tam otomatik bir yapay zeka video üretim motorudur.

### Temel Prensipler
- **Hafif Mimari (Ultra-Lite):** Ağır harici kütüphaneler yerine optimize MoviePy ve doğrudan FFmpeg pipeline'ı kullanılır.
- **Çoklu Çözünürlük ve 4K Desteği:** 4K UHD (2160p), 2K QHD (1440p), 1080p FHD, 720p HD ve 480p SD seçenekleri; 9:16 (Dikey Reels/Shorts/TikTok), 16:9 (Yatay YouTube) ve 1:1 (Kare) en-boy oranları.
- **Uzaktan WebUI Erişimi (Remote Access):** Sunucuda çalışırken Cloudflare Tüneli, Ngrok, SSH Port Forwarding veya Doğrudan IP üzerinden tarayıcıdan tam erişim.
- **Güvenlik (Token Tabanlı):** URL ve çerez tabanlı şifreli token doğrulama mekanizmasıyla yetkisiz erişimlerin engellenmesi.
- **Çoklu LLM Desteği:** OpenAI, DeepSeek, Google Gemini, Anthropic Claude, Groq ve yerel LLM modelleri.
- **Ücretsiz & Yüksek Kaliteli TTS:** Dahili Edge TTS entegrasyonuyla yüzlerce doğal ses (Türkçe Ahmet, Emel vb. dahil).

---

## 2. Sistem Mimarisi ve Modül Yapısı

```
MoneyPrinterTurbo-Lite/
├── lite_server.py         # HTTP REST API, statik WebUI sunucusu ve tünel yöneticisi
├── lite_engine.py         # FFmpeg / MoviePy tabanlı 4K video render motoru
├── batch_engine.py        # Toplu video üretim motoru ve ses havuzu yöneticisi
├── worker.py              # Arka plan görev işleyicisi (Task Queue Worker)
├── task_store.py          # Görev kalıcılığı, durum yönetimi ve JSON veritabanı
├── settings_manager.py    # Yapılandırma, API anahtarları ve token yönetimi
├── llm_service.py         # Çoklu LLM sağlayıcı entegrasyonu ve senaryo üretimi
├── start.sh               # Evrensel başlatıcı script (Termux, Linux, macOS)
├── server.sh              # Üretim ortamı sunucu yönetim scripti (Daemon, Tünel, Log)
├── MoneyPrinterTurbo_Colab.ipynb # Google Colab tek tıkla çalıştırma notebook'u
├── resource/              # Dahili fontlar ve arka plan müzikleri (BGM)
└── webui/                 # Modern responsive WebUI arayüzü (HTML5/CSS3/Vanilla JS)
```

### Temel Modüllerin İşlevleri

1. **`lite_server.py`:**
   - Standart Python `http.server.ThreadingHTTPServer` tabanlı hafif web sunucusu.
   - Cloudflare Quick Tunnel (`cloudflared`) ve Ngrok (`ngrok`) süreçlerini dinamik olarak yönetir, dış dünyaya açılan tünel URL'sini yakalar ve istemciye iletir.
   - Token tabanlı oturum yönetimi (`Set-Cookie` ve `?token=` sorgu parametresi).
   - Video streaming (`Range` header destekli HTTP 206 Partial Content).

2. **`lite_engine.py`:**
   - Senaryoyu cümle/paragraf bazında Edge TTS ile sese dönüştürür.
   - Pexels API üzerinden senaryodaki anahtar kelimelere göre çoklu stok video indirir.
   - Çözünürlüğe ve en-boy oranına göre altyazıları otomatik boyutlandırır, stroke (kontur) ve kutu modu uygular.
   - Sahne geçişlerinde yumuşak Crossfade efektleri uygular.
   - FFmpeg `libx264` ve `aac` kodekleriyle donanım dostu render alır.

3. **`batch_engine.py` & `worker.py`:**
   - Toplu video isteklerini (`batch`) sıraya alır ve ardışık olarak işler.
   - Görev durumlarını (`queued`, `running`, `completed`, `failed`, `cancelled`) anlık günceller.
   - Görev hata verdiğinde veya sunucu kapandığında kaldığı yerden devam ettirme (`resume`) yeteneğine sahiptir.

---

## 3. Uzak Sunucu (VPS / Cloud) Dağıtımı ve Uzaktan Erişim Yolları

MoneyPrinter Turbo Lite'ı uzak bir sunucuda çalıştırırken WebUI arayüzüne ve tüm fonksiyonlara erişmek için 6 farklı yöntem desteklenir:

### Yöntem 1: Cloudflare Quick Tunnel (Sıfır Yapılandırma - Önerilen)
- **Avantajı:** Port açmaya, statik IP'ye, alan adına veya Cloudflare hesabı açmaya gerek yoktur. Tek komutla global, güvenli bir `https://*.trycloudflare.com` bağlantısı üretir.
- **Kurulum & Çalıştırma:**
  ```bash
  # Cloudflared paketini indirin ve kurun
  curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
  sudo dpkg -i cloudflared.deb

  # Sunucuyu Cloudflare Tüneli ile başlatın
  ./server.sh start --tunnel
  # veya
  python3 lite_server.py --host 0.0.0.0 --port 8080 --tunnel cloudflare
  ```
- **Erişim:** Terminalde gösterilen veya `./server.sh status` komutuyla alınan `https://xyz.trycloudflare.com/?token=YOUR_TOKEN` bağlantısı üzerinden doğrudan bağlanılır.

### Yöntem 2: Ngrok Tunnel
- **Avantajı:** Özel domain veya sabit ngrok adresi tanımlayabilme.
- **Çalıştırma:**
  ```bash
  ./server.sh start -t ngrok
  ```
- *Authtoken bilgisi WebUI Ayarlar sekmesinden veya `config.toml` üzerinden girilebilir.*

### Yöntem 3: Doğrudan Sunucu IP'si (Direct IP & Port)
- **Avantajı:** Aracı tünel olmadan doğrudan sunucu hızında maksimum veri transferi.
- **Yapılandırma:**
  ```bash
  sudo ufw allow 8080/tcp
  ./server.sh start
  ```
- **Erişim:** `http://<SUNUCU_IP_ADRESI>:8080/?token=YOUR_TOKEN`

### Yöntem 4: SSH Port Forwarding (Güvenli Yerel Tünel)
- **Avantajı:** Sunucunun hiçbir portunu dışarı açmadan yerel bilgisayar üzerinden tam şifreli erişim.
- **Komut (Yerel Terminalde):**
  ```bash
  ssh -N -L 8080:127.0.0.1:8080 kullanici@sunucu_ip
  ```
- **Erişim:** `http://127.0.0.1:8080/?token=YOUR_TOKEN`

### Yöntem 5: Nginx Reverse Proxy & Let's Encrypt SSL
- **Örnek Nginx Bloğu:**
  ```nginx
  server {
      server_name video.siteniz.com;
      location / {
          proxy_pass http://127.0.0.1:8080;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          client_max_body_size 300M;
      }
  }
  ```

### Yöntem 6: Systemd Servisi (7/24 Sürekli Çalışma)
- `/etc/systemd/system/moneyprinter.service`:
  ```ini
  [Unit]
  Description=MoneyPrinter Turbo Lite
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
- Servis komutları: `sudo systemctl enable --now moneyprinter`

---

## 4. WebUI Üzerinden Uzaktan Gerçekleştirilebilen Tüm İşlemler

Uzak sunucudaki WebUI arayüzü masaüstü ve mobil tarayıcılarla tam uyumludur:

1. **Tekli Video Üretimi (`tab-create`):**
   - Senaryo ve video konusu tanımlama.
   - LLM (Gemini, DeepSeek, GPT-4o-mini, Groq, Claude) ile otomatik senaryo ve görsel arama terimi üretimi.
   - Çözünürlük (4K, 2K, 1080p, 720p) ve format (9:16, 16:9, 1:1) seçimi.
   - Seslendirmen seçimi ve konuşma hızı/ses seviyesi ayarı.
   - Altyazı rengi, fontu, boyutu, kalınlığı (bold), çerçeve/kontur rengi ve kutu modu ayarları.
   - Özel ses veya özel arka plan yükleme.

2. **Toplu Video Üretimi (`tab-batch`):**
   - Birden çok ders/konuyu tek seferde kuyruğa ekleme.
   - Dinamik ses havuzu (Voice Pool): Her videoya havuzdan farklı ses atama.
   - Otomatik sıralı render ve hata toleransı.

3. **Görev Takibi ve Arşiv Yönetimi (`tab-history`):**
   - Canlı ilerleme yüzdesi ve işlem logları.
   - Tarayıcı içi video oynatma.
   - Tekil video indirme.
   - **Tüm Videoları ZIP Olarak İndirme:** Üretilen tüm MP4 dosyalarını tek tıkla arşivleyip indirme.
   - Varyant üretimi (aynı videonun farklı altyazı veya ses varyantını hızlıca üretme).
   - İptal etme, yeniden deneme ve silme.

4. **Ayarlar & Canlı Tünel Yönetimi (`tab-settings`):**
   - API anahtarlarını maskeli olarak görüntüleme ve güncelleme.
   - Dahili ses önizleme oynatıcısıyla seslendirmeleri dinleme.
   - Arka plan müzikleri (BGM) yükleme ve silme.
   - Web arayüzü içerisinden tek tıkla Cloudflare / Ngrok tüneli başlatma, durdurma ve erişim linkini kopyalama.

---

## 5. REST API Referansı

| Metot | Uç Nokta | Açıklama |
|---|---|---|
| `GET` | `/api/tunnel/status` | Tünel durumu, sunucu IP'leri ve erişim linklerini döner. |
| `POST` | `/api/tunnel/start` | `{"provider": "cloudflare"\|"ngrok"}` ile tünel başlatır. |
| `POST` | `/api/tunnel/stop` | Aktif tüneli durdurur. |
| `POST` | `/api/generate` | Yeni tekli video üretim görevi oluşturur. |
| `POST` | `/api/batch` | Yeni toplu video üretim görevi oluşturur. |
| `GET` | `/api/tasks` | Tüm görevlerin listesini ve durumlarını döner. |
| `GET` | `/api/tasks/{task_id}` | Belirli bir görevin detayını ve video bağlantısını döner. |
| `GET` | `/api/tasks/{task_id}/video` | Üretilen videoyu HTTP 206 akışı ile iletir. |
| `GET` | `/api/tasks/download-all-zip` | Tamamlanmış tüm videoları tek bir ZIP olarak indirir. |
| `POST` | `/api/tasks/{task_id}/cancel` | Çalışan görevi iptal eder. |
| `POST` | `/api/tasks/{task_id}/delete` | Görevi ve ilişkili dosyaları siler. |
| `POST` | `/api/llm/generate` | LLM ile otomatik senaryo ve terim üretir. |
| `GET` | `/api/settings` | Maskelenmiş sistem ayarlarını döner. |
| `POST` | `/api/settings` | Sistem ayarlarını günceller. |

---

## 6. CLI ve Komut Satırı Araçları

### `server.sh` Kullanımı
```bash
./server.sh start          # Arka planda başlatır
./server.sh start --tunnel # Cloudflare tüneli ile başlatır
./server.sh stop           # Sunucuyu ve tünelleri durdurur
./server.sh status         # Aktif URL ve durum bilgisi verir
./server.sh logs           # Canlı logları gösterir (tail -f)
./server.sh tunnel         # Çalışan sunucuya dinamik tünel bağlar
```

### `start.sh` Kullanımı
```bash
./start.sh --port 8080 --host 0.0.0.0 --tunnel cloudflare
```

---

## 7. Sık Karşılaşılan Sorunlar ve Çözümleri

1. **WebUI'a uzaktan bağlanırken "Yetkisiz Erişim" hatası alıyorum:**
   - **Çözüm:** Bağlantı adresinin sonuna `?token=YOUR_AUTH_TOKEN` parametresini eklediğinizden emin olun. Token bilgisini `./server.sh status` komutuyla veya `storage/settings.json` dosyasından öğrenebilirsiniz.
2. **Cloudflare tüneli başlamıyor:**
   - **Çözüm:** Sunucuda `cloudflared` binary'sinin kurulu olduğunu doğrulayın (`cloudflared --version`). Kurulu değilse `curl -L --output cf.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb && sudo dpkg -i cf.deb` komutunu çalıştırın.
3. **Pexels videoları indirilemiyor:**
   - **Çözüm:** WebUI Ayarlar sekmesinden geçerli bir Pexels API anahtarı girdiğinizden emin olun.
4. **4K render sırasında bellek yetersizliği oluşuyor:**
   - **Çözüm:** Düşük RAM'li ortamlarda (örneğin 2GB-4GB VPS) çözünürlüğü `1080p` veya `720p` olarak seçin. FFmpeg iş parçacığı sayısı sistem çekirdek sayısına göre otomatik optimize edilmektedir.

---
*Bu doküman MoneyPrinter Turbo Lite sürüm 2.0+ için günceldir.*
