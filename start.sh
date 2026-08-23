#!/data/data/com.termux/files/usr/bin/bash

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${BASE_DIR:-$DIR}"
PYTHON_BIN="${PYTHON_BIN:-$(which python || which python3)}"

cd "$BASE_DIR" || exit 1
mkdir -p "$BASE_DIR/storage"

# 8080 portunu temizle
fuser -k 8080/tcp 2>/dev/null || true
pkill -9 -f "lite_server.py" 2>/dev/null || true
sleep 0.8

echo "🚀 MoneyPrinter Lite Studio başlatılıyor..."
$PYTHON_BIN -c "
import subprocess, sys
log_file = open('$BASE_DIR/storage/server.log', 'w')
subprocess.Popen([sys.executable, '$BASE_DIR/lite_server.py'], stdout=log_file, stderr=log_file, start_new_session=True)
"

# Sunucu yanıt verene kadar bekle
for i in {1..15}; do
    if curl -s http://127.0.0.1:8080/ >/dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

AUTH_URL=$($PYTHON_BIN -c "
import sys; sys.path.insert(0, '$BASE_DIR')
import settings_manager
print(f'http://127.0.0.1:8080/?token={settings_manager.get_auth_token()}')
")

echo "✅ Sunucu hazır!"
echo "📱 Giriş bağlantısı (tokenlı):"
echo "   $AUTH_URL"
termux-open-url "$AUTH_URL" 2>/dev/null || true
