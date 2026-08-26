import json
import os
import secrets
import threading
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_storage_dir() -> str:
    path = os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "storage"))
    if os.path.islink(path) and not os.path.exists(path):
        try:
            os.unlink(path)
        except Exception:
            pass
    os.makedirs(path, exist_ok=True)
    return path


def get_settings_file() -> str:
    return os.environ.get("SETTINGS_FILE", os.path.join(get_storage_dir(), "settings.json"))


# Geriye dönük uyumluluk için değişkenler
STORAGE_DIR = get_storage_dir()
SETTINGS_FILE = get_settings_file()
_lock = threading.RLock()

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Stok Medya
    "pexels_api_keys": "",
    "pixabay_api_keys": "",
    "coverr_api_keys": "",

    # LLM
    "openai_api_key": "",
    "openai_base_url": "https://api.openai.com/v1",
    "openai_model_name": "gpt-4o-mini",
    "gemini_api_key": "",
    "groq_api_key": "",
    "deepseek_api_key": "",

    # TTS
    "azure_speech_key": "",
    "azure_speech_region": "eastus",
    "elevenlabs_api_key": "",

    # Erisim & Tunnel
    "auth_token": "",
    "ngrok_authtoken": "",

    # --- Üretim Tercihleri (Tekli/Toplu için global varsayılanlar) ---
    "prod_voice": "tr-TR-AhmetNeural",
    "prod_voice_rate": 1.0,
    "prod_voice_volume": 1.0,
    "prod_aspect": "9:16",
    "prod_resolution": "720p",
    "prod_save_480p": False,
    "prod_bg_style": "chalkboard",
    "prod_subtitle_enabled": True,
    "prod_sub_color": "#FFFFFF",
    "prod_sub_pos": "bottom",
    "prod_sub_size": 18,
    "prod_sub_box": False,
    "prod_sub_bold": True,
    "prod_sub_font": "Roboto",
    "prod_outline_color": "#000000",
    "prod_highlight_color": "#FFD700",
    "prod_highlight_words": "",
    "prod_highlight_size": 24,
    "prod_bgm_mode": "none",
    "prod_bgm_volume": 0.15,
    "prod_transition": "none",
    "prod_transition_dur": 0.5,

    # --- FFmpeg Video & Ses Sıkıştırma / Hızlandırma Ayarları ---
    "ffmpeg_cq_gpu": 23,
    "ffmpeg_preset_gpu": "p4",
    "ffmpeg_crf_cpu": 23,
    "ffmpeg_preset_cpu": "ultrafast",
    "ffmpeg_audio_bitrate": "128k",
    "ffmpeg_threads": "2"
}

SECRET_KEYS = {
    "pexels_api_keys", "pixabay_api_keys", "coverr_api_keys",
    "openai_api_key", "gemini_api_key", "groq_api_key",
    "deepseek_api_key", "azure_speech_key", "elevenlabs_api_key",
    "auth_token", "ngrok_authtoken"
}


def load_settings() -> Dict[str, Any]:
    with _lock:
        settings_file = get_settings_file()
        if not os.path.exists(settings_file):
            # Dosya yoksa varsayılan ayarlarla otomatik oluştur
            try:
                os.makedirs(os.path.dirname(settings_file), exist_ok=True)
                with open(settings_file, "w", encoding="utf-8") as f:
                    json.dump(DEFAULT_SETTINGS, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Uyarı: settings.json oluşturulamadı: {e}")
            return DEFAULT_SETTINGS.copy()
        else:
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            res = DEFAULT_SETTINGS.copy()
            if isinstance(data, dict):
                # Mevcut tüm ayarları koru ve yeni varsayılanları ekle (geriye dönük tam uyum)
                res.update(data)
            return res


def save_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        current = load_settings()
        for key, value in new_settings.items():
            if isinstance(value, str):
                value = value.strip()
                if key in SECRET_KEYS and not value:
                    continue
            current[key] = value

        settings_file = get_settings_file()
        os.makedirs(os.path.dirname(settings_file), exist_ok=True)
        tmp_path = settings_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, settings_file)

        ngrok_token = str(current.get("ngrok_authtoken", "")).strip()
        if ngrok_token:
            os.system(f"ngrok config add-authtoken '{ngrok_token}' >/dev/null 2>&1")

        return current


def mask_secret(value: Any) -> str:
    s = str(value or "")
    return f"{s[:4]}...{s[-4:]}" if len(s) > 8 else ("*" * len(s) if s else "")



def get_masked_settings() -> Dict[str, Any]:
    s = load_settings()
    return {k: (mask_secret(v) if k in SECRET_KEYS else v) for k, v in s.items()}


def get_auth_token() -> str:
    token = str(load_settings().get("auth_token", "")).strip()
    if not token:
        token = secrets.token_urlsafe(24)
        save_settings({"auth_token": token})
    return token


def get_setting(key: str, default: Any = None) -> Any:
    return load_settings().get(key, default)
