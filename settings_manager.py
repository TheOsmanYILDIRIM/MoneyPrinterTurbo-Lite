import json
import os
import secrets
import threading
from typing import Any, Dict

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "storage", "settings.json")
_lock = threading.RLock()

DEFAULT_SETTINGS: Dict[str, Any] = {
    # Stok Medya
    "pexels_api_keys": "",
    "pixabay_api_keys": "",
    "coverr_api_keys": "",

    # LLM (gelecek genisletme icin)
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
    "prod_bg_style": "chalkboard",
    "prod_subtitle_enabled": True,
    "prod_sub_color": "#FFFFFF",
    "prod_sub_pos": "bottom",
    "prod_sub_size": 18,
    "prod_sub_box": False,
    "prod_highlight_color": "#FFD700",
    "prod_highlight_words": "",
    "prod_bgm_mode": "none",
    "prod_bgm_volume": 0.15,
    "prod_transition": "none",
    "prod_transition_dur": 0.5
}

SECRET_KEYS = {
    "pexels_api_keys", "pixabay_api_keys", "coverr_api_keys",
    "openai_api_key", "gemini_api_key", "groq_api_key",
    "deepseek_api_key", "azure_speech_key", "elevenlabs_api_key",
    "auth_token", "ngrok_authtoken"
}


def load_settings() -> Dict[str, Any]:
    with _lock:
        if not os.path.exists(SETTINGS_FILE):
            data = {}
        else:
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        res = DEFAULT_SETTINGS.copy()
        res.update({k: v for k, v in data.items() if k in res})
        return res


def save_settings(new_settings: Dict[str, Any]) -> Dict[str, Any]:
    with _lock:
        current = load_settings()
        for key, value in new_settings.items():
            if key not in current:
                continue
            if isinstance(value, str):
                value = value.strip()
                if key in SECRET_KEYS and not value:
                    continue
            current[key] = value

        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        tmp_path = SETTINGS_FILE + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, SETTINGS_FILE)

        ngrok_token = str(current.get("ngrok_authtoken", "")).strip()
        if ngrok_token:
            os.system(f"ngrok config add-authtoken '{ngrok_token}' >/dev/null 2>&1")

        return current


def mask_secret(value: Any) -> str:
    s = str(value or "")
    if len(s) <= 8:
        return "*" * len(s) if s else ""
    return f"{s[:4]}...{s[-4:]}"


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
