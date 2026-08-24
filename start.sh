#!/data/data/com.termux/files/usr/bin/env bash

# MoneyPrinter Turbo Lite - Universal Startup Script
# Compatible with Termux (Android Linux), Ubuntu, Debian, CentOS, macOS, and Cloud Servers

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$DIR}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || echo /data/data/com.termux/files/usr/bin/python)}"

cd "$BASE_DIR" || exit 1
mkdir -p "$BASE_DIR/storage"

PORT="8080"
HOST="0.0.0.0"
TUNNEL="none"
ACTION="start"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --port|-p)
            PORT="$2"
            shift 2
            ;;
        --host|-h)
            HOST="$2"
            shift 2
            ;;
        --tunnel|-t)
            if [[ -n "$2" && "$2" != --* ]]; then
                TUNNEL="$2"
                shift 2
            else
                TUNNEL="cloudflare"
                shift 1
            fi
            ;;
        --stop)
            ACTION="stop"
            shift 1
            ;;
        --status)
            ACTION="status"
            shift 1
            ;;
        --restart)
            ACTION="restart"
            shift 1
            ;;
        --help)
            echo "Kullanım: ./start.sh [SEÇENEKLER]"
            echo ""
            echo "Seçenekler:"
            echo "  --port, -p <PORT>       Port numarası (Varsayılan: 8080)"
            echo "  --host, -h <HOST>       Bağlanacak Host IP (Varsayılan: 0.0.0.0)"
            echo "  --tunnel, -t [provider] Otomatik tünel başlat (cloudflare / ngrok / auto)"
            echo "  --stop                  Çalışan sunucuyu ve tünelleri durdur"
            echo "  --restart               Sunucuyu yeniden başlat"
            echo "  --status                Sunucu ve tünel durumunu göster"
            echo "  --help                  Bu yardım mesajını göster"
            exit 0
            ;;
        *)
            shift 1
            ;;
    esac
done

stop_server() {
    echo "🛑 Sunucu ve tüneller durduruluyor..."
    fuser -k "${PORT}/tcp" 2>/dev/null || true
    pkill -9 -f "lite_server.py" 2>/dev/null || true
    pkill -9 -f "cloudflared tunnel" 2>/dev/null || true
    pkill -9 -f "ngrok http" 2>/dev/null || true
    echo "✅ İşlemler durduruldu."
}

show_status() {
    $PYTHON_BIN -c "
import sys, urllib.request, json
sys.path.insert(0, '$BASE_DIR')
import settings_manager
token = settings_manager.get_auth_token()
try:
    with urllib.request.urlopen('http://127.0.0.1:$PORT/?token=' + token, timeout=2) as r:
        pass
    print(f'🟢 MoneyPrinter Lite Studio ÇALIŞIYOR (Port: $PORT)')
    print(f'📍 Yerel URL: http://127.0.0.1:$PORT/?token={token}')
    try:
        with urllib.request.urlopen('http://127.0.0.1:$PORT/api/tunnel/status?token=' + token, timeout=3) as r:
            d = json.loads(r.read().decode())
            for u in d.get('local_urls', []):
                print(f'🌐 Ağ / Sunucu URL: {u}')
            if d.get('running') and d.get('public_url'):
                print(f'🌍 Genel Tünel ({d.get(\"provider\")}): {d.get(\"auth_url\") or d.get(\"public_url\")}')
    except Exception:
        pass
except Exception:
    print('🔴 Sunucu şu anda ÇALIŞMIYOR.')
"
}

if [ "$ACTION" = "stop" ]; then
    stop_server
    exit 0
elif [ "$ACTION" = "status" ]; then
    show_status
    exit 0
elif [ "$ACTION" = "restart" ]; then
    stop_server
    sleep 1
fi

# Temizle ve Başlat
fuser -k "${PORT}/tcp" 2>/dev/null || true
pkill -9 -f "lite_server.py" 2>/dev/null || true
sleep 0.5

echo "🚀 MoneyPrinter Lite Studio başlatılıyor..."
$PYTHON_BIN -c "
import subprocess, sys
log_file = open('$BASE_DIR/storage/server.log', 'w')
cmd = [sys.executable, '$BASE_DIR/lite_server.py', '--host', '$HOST', '--port', '$PORT', '--tunnel', '$TUNNEL']
subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True)
"

# Sunucu yanıt verene kadar bekle
for i in {1..20}; do
    if curl -s "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# Bilgileri ekrana yaz
$PYTHON_BIN -c "
import sys, time, urllib.request, json
sys.path.insert(0, '$BASE_DIR')
import settings_manager
token = settings_manager.get_auth_token()

print('=' * 65)
print('✅ MoneyPrinter Lite Studio Başarıyla Başlatıldı!')
print('=' * 65)
print(f'📍 Yerel Giriş Bağlantısı:')
print(f'   http://127.0.0.1:$PORT/?token={token}')

try:
    time.sleep(1.2)
    with urllib.request.urlopen('http://127.0.0.1:$PORT/api/tunnel/status?token=' + token, timeout=4) as r:
        d = json.loads(r.read().decode())
        urls = d.get('local_urls', [])
        if urls:
            print('\n🌐 Sunucu / Yerel Ağ Giriş Bağlantıları:')
            for u in urls:
                print(f'   {u}')
        if d.get('running') and d.get('public_url'):
            pub = d.get('auth_url') or f\"{d.get('public_url')}/?token={token}\"
            print(f'\n🌍 Genel Tünel Bağlantısı ({d.get(\"provider\", \"Cloudflare\")}):')
            print(f'   {pub}')
except Exception:
    pass

print('=' * 65)
print('💡 İpucu: Arka planda çalışıyor. Logları izlemek için: tail -f storage/server.log')
print('=' * 65)
"

# Termux ortamında doğrudan aç (SSH olmayan yerel oturumlarda)
AUTH_URL=$($PYTHON_BIN -c "
import sys; sys.path.insert(0, '$BASE_DIR')
import settings_manager
print(f'http://127.0.0.1:$PORT/?token={settings_manager.get_auth_token()}')
")

if command -v termux-open-url >/dev/null 2>&1 && [ -z "$SSH_CLIENT" ] && [ -z "$SSH_TTY" ]; then
    termux-open-url "$AUTH_URL" 2>/dev/null || true
fi
