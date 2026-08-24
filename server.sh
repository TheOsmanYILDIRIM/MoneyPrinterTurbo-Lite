#!/data/data/com.termux/files/usr/bin/env bash

# ==============================================================================
# MoneyPrinter Turbo Lite - Production Server Management Script
# ==============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$DIR}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || command -v python || echo /data/data/com.termux/files/usr/bin/python)}"
LOG_FILE="$BASE_DIR/storage/server.log"
PORT="${PORT:-8080}"
HOST="${HOST:-0.0.0.0}"

cd "$BASE_DIR" || exit 1
mkdir -p "$BASE_DIR/storage"

get_token() {
    $PYTHON_BIN -c "
import sys; sys.path.insert(0, '$BASE_DIR')
import settings_manager
print(settings_manager.get_auth_token())
"
}

case "$1" in
    start)
        echo "🚀 MoneyPrinter Lite Studio başlatılıyor..."
        fuser -k "${PORT}/tcp" 2>/dev/null || true
        pkill -9 -f "lite_server.py" 2>/dev/null || true
        sleep 0.5
        
        TUNNEL_ARG="none"
        if [ "$2" = "--tunnel" ] || [ "$2" = "-t" ]; then
            TUNNEL_ARG="${3:-cloudflare}"
        fi
        
        $PYTHON_BIN -c "
import subprocess, sys
log_file = open('$LOG_FILE', 'w')
cmd = ['$PYTHON_BIN', '$BASE_DIR/lite_server.py', '--host', '$HOST', '--port', '$PORT', '--tunnel', '$TUNNEL_ARG']
subprocess.Popen(cmd, stdout=log_file, stderr=log_file, start_new_session=True)
"
        
        for i in {1..20}; do
            if curl -s "http://127.0.0.1:${PORT}/" >/dev/null 2>&1; then
                break
            fi
            sleep 0.5
        done
        
        TOKEN=$(get_token)
        echo "================================================================="
        echo "✅ Sunucu Başarıyla Başlatıldı!"
        echo "================================================================="
        echo "📍 Yerel Bağlantı:      http://127.0.0.1:${PORT}/?token=${TOKEN}"
        
        $PYTHON_BIN -c "
import sys, time, urllib.request, json
time.sleep(1.2)
try:
    with urllib.request.urlopen('http://127.0.0.1:$PORT/api/tunnel/status?token=$TOKEN', timeout=4) as r:
        d = json.loads(r.read().decode())
        for u in d.get('local_urls', []):
            print(f'🌐 Sunucu / Ağ IP:       {u}')
        if d.get('running') and d.get('public_url'):
            pub = d.get('auth_url') or f\"{d.get('public_url')}/?token=$TOKEN\"
            print(f'🌍 Genel Tünel ({d.get(\"provider\")}): {pub}')
except Exception:
    pass
"
        echo "================================================================="
        echo "Logları izlemek için: ./server.sh logs"
        ;;
        
    stop)
        echo "🛑 Sunucu ve tüm tüneller durduruluyor..."
        fuser -k "${PORT}/tcp" 2>/dev/null || true
        pkill -9 -f "lite_server.py" 2>/dev/null || true
        pkill -9 -f "cloudflared tunnel" 2>/dev/null || true
        pkill -9 -f "ngrok http" 2>/dev/null || true
        echo "✅ Başarıyla durduruldu."
        ;;
        
    restart)
        $0 stop
        sleep 1
        $0 start "${@:2}"
        ;;
        
    status)
        TOKEN=$(get_token)
        if curl -s "http://127.0.0.1:${PORT}/?token=${TOKEN}" >/dev/null 2>&1; then
            echo "🟢 MoneyPrinter Lite Studio ÇALIŞIYOR (Port: $PORT)"
            echo "📍 Yerel URL: http://127.0.0.1:${PORT}/?token=${TOKEN}"
            $PYTHON_BIN -c "
import sys, urllib.request, json
try:
    with urllib.request.urlopen('http://127.0.0.1:$PORT/api/tunnel/status?token=$TOKEN', timeout=3) as r:
        d = json.loads(r.read().decode())
        for u in d.get('local_urls', []):
            print(f'🌐 Sunucu / Ağ: {u}')
        if d.get('running') and d.get('public_url'):
            print(f'🌍 Tünel ({d.get(\"provider\")}): {d.get(\"auth_url\") or d.get(\"public_url\")}')
except Exception:
    pass
"
        else
            echo "🔴 Sunucu şu anda ÇALIŞMIYOR."
        fi
        ;;
        
    logs)
        tail -f "$LOG_FILE"
        ;;
        
    tunnel)
        PROVIDER="${2:-cloudflare}"
        TOKEN=$(get_token)
        echo "🌐 $PROVIDER tüneli başlatılıyor..."
        curl -s -X POST "http://127.0.0.1:${PORT}/api/tunnel/start?token=${TOKEN}" \
             -H "Content-Type: application/json" \
             -d "{\"provider\":\"$PROVIDER\"}" | python3 -m json.tool 2>/dev/null || true
        ;;
        
    tunnel-stop)
        TOKEN=$(get_token)
        echo "🛑 Tünel durduruluyor..."
        curl -s -X POST "http://127.0.0.1:${PORT}/api/tunnel/stop?token=${TOKEN}" | python3 -m json.tool 2>/dev/null || true
        ;;

    *)
        echo "Kullanım: ./server.sh {start|stop|restart|status|logs|tunnel|tunnel-stop}"
        echo ""
        echo "Örnekler:"
        echo "  ./server.sh start                 # Standart sunucuyu başlat"
        echo "  ./server.sh start --tunnel        # Cloudflare tüneli ile başlat"
        echo "  ./server.sh start -t ngrok        # Ngrok tüneli ile başlat"
        echo "  ./server.sh status                # Durum ve bağlantıları listele"
        echo "  ./server.sh logs                  # Canlı logları izle"
        echo "  ./server.sh stop                  # Sunucuyu durdur"
        exit 1
        ;;
esac
