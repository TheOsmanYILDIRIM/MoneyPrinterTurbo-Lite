import hmac
import http.server
import json
import mimetypes
import os
import re
import shutil
import socketserver
import subprocess
import sys
import time
import urllib.request
import uuid
import zipfile
from urllib.parse import urlparse, parse_qs

from loguru import logger

import batch_engine
import llm_service
import settings_manager
import task_store
import worker

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = os.path.join(BASE_DIR, "storage", "tasks")
UPLOADS_DIR = os.path.join(BASE_DIR, "storage", "uploads")
STATIC_DIR = os.path.join(BASE_DIR, "webui", "static")
SONGS_DIR = os.path.join(BASE_DIR, "resource", "songs")
PREVIEWS_DIR = os.path.join(BASE_DIR, "storage", "previews")
VOICES_FILE = os.path.join(BASE_DIR, "storage", "all_voices.json")
os.makedirs(TASKS_DIR, exist_ok=True)
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(SONGS_DIR, exist_ok=True)
os.makedirs(PREVIEWS_DIR, exist_ok=True)

VOICE_PREVIEW_TEXT = "Merhaba, bu ses ile ders anlatımı videosu hazırlayacağız."

BGM_EXTENSIONS = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")

PORT = int(os.getenv("PORT", "8080"))
MAX_UPLOAD_BYTES = 200 * 1024 * 1024  # 200MB

_ngrok_proc: subprocess.Popen | None = None


# ---------------------------------------------------------------- helpers

def safe_join(base: str, *parts: str) -> str | None:
    """Path traversal korumali birlestirme."""
    path = os.path.normpath(os.path.join(base, *parts))
    base_abs = os.path.abspath(base)
    path_abs = os.path.abspath(path)
    if path_abs != base_abs and not path_abs.startswith(base_abs + os.sep):
        return None
    return path_abs


def sanitize_filename(name: str) -> str:
    name = os.path.basename(str(name or "file"))
    name = re.sub(r"[^\w.\- ]+", "_", name).strip()
    return name[:80] or "file"


def parse_multipart(body: bytes, boundary: bytes):
    fields = {}
    files = {}
    file_list = []
    for part in body.split(b"--" + boundary):
        if not part or part in (b"--\r\n", b"--", b"--\r\n\r\n"):
            continue
        if b"\r\n\r\n" not in part:
            continue
        header_part, content = part.split(b"\r\n\r\n", 1)
        if content.endswith(b"\r\n"):
            content = content[:-2]
        header_text = header_part.decode("utf-8", errors="ignore")

        name_match = re.search(r'name="([^"]+)"', header_text)
        filename_match = re.search(r'filename="([^"]*)"', header_text)

        if name_match:
            name = name_match.group(1)
            if filename_match is not None:
                file_obj = {"name": name, "filename": filename_match.group(1), "content": content}
                files[name] = file_obj
                file_list.append(file_obj)
            else:
                fields[name] = content.decode("utf-8", errors="ignore")
    return fields, files, file_list


def save_upload(data: dict, kind: str) -> str:
    ext = os.path.splitext(sanitize_filename(data.get("filename", "")))[1] or ""
    save_path = os.path.join(UPLOADS_DIR, f"{uuid.uuid4().hex}_{kind}{ext}")
    with open(save_path, "wb") as f:
        f.write(data["content"])
    return save_path


def extract_task_params(fields: dict, files: dict) -> tuple[dict, str | None, str | None, str | None]:
    custom_bg = None
    custom_audio = None
    bgm_path = None

    if "bg_file" in files and files["bg_file"]["content"]:
        custom_bg = save_upload(files["bg_file"], "bg")
    if "audio_file" in files and files["audio_file"]["content"]:
        custom_audio = save_upload(files["audio_file"], "audio")
    if "bgm_file" in files and files["bgm_file"]["content"]:
        bgm_path = save_upload(files["bgm_file"], "bgm")

    # Üretim Tercihleri (Ayarlar sekmesi) global varsayılanları; istekte gelmeyen
    # alanlar için buradan düşülür (sunucu tarafı güvenlik ağı).
    prod = settings_manager.load_settings()

    def _val(key: str, prod_key: str, default):
        v = fields.get(key)
        if v in ("", None):
            return prod.get(prod_key, default)
        return v

    voice = str(_val("voice", "prod_voice", "tr-TR-AhmetNeural")).strip() or "tr-TR-AhmetNeural"
    voice_rate = max(0.5, min(2.0, float(_val("voice_rate", "prod_voice_rate", 1.0) or 1.0)))
    voice_volume = max(0.1, min(3.0, float(_val("voice_volume", "prod_voice_volume", 1.0) or 1.0)))
    aspect = fields.get("aspect") if fields.get("aspect") in ("9:16", "16:9", "1:1") \
        else (prod.get("prod_aspect") if prod.get("prod_aspect") in ("9:16", "16:9", "1:1") else "9:16")
    resolution = str(_val("resolution", "prod_resolution", "720p")).strip().lower() or "720p"
    bg_style = str(_val("bg_style", "prod_bg_style", "chalkboard")) or "chalkboard"
    sub_color = str(_val("sub_color", "prod_sub_color", "#FFFFFF")) or "#FFFFFF"
    sub_pos = fields.get("sub_pos") if fields.get("sub_pos") in ("bottom", "center", "top") \
        else (prod.get("prod_sub_pos") if prod.get("prod_sub_pos") in ("bottom", "center", "top") else "bottom")
    sub_size = max(12, min(40, int(_val("sub_size", "prod_sub_size", 18) or 18)))
    sub_box = str(_val("sub_box", "prod_sub_box", "false")).lower() in ("true", "1", "yes")
    sub_bold = str(_val("sub_bold", "prod_sub_bold", "true")).lower() in ("true", "1", "yes")
    sub_font = str(_val("sub_font", "prod_sub_font", "Roboto")).strip() or "Roboto"
    outline_color = str(_val("outline_color", "prod_outline_color", "#000000")).strip() or "#000000"
    subtitle_enabled = str(_val("subtitle_enabled", "prod_subtitle_enabled", "true")).lower() in ("true", "1", "yes")
    highlight_color = str(_val("highlight_color", "prod_highlight_color", "#FFD700")).strip() or "#FFD700"
    highlight_words = fields.get("highlight_words") or fields.get("sub_highlight_words") or prod.get("prod_highlight_words", "")
    raw_hl_size = fields.get("highlight_size") or fields.get("sub_highlight_size")
    highlight_size = int(raw_hl_size) if raw_hl_size else None
    bgm_source = fields.get("bgm_source") or prod.get("prod_bgm_mode", "none")
    bgm_volume = max(0.0, min(1.0, float(_val("bgm_volume", "prod_bgm_volume", 0.15) or 0.15)))
    transition = str(_val("transition", "prod_transition", "none")) or "none"
    transition_dur = max(0.1, min(2.0, float(_val("transition_dur", "prod_transition_dur", 0.5) or 0.5)))

    params = {
        "subject": str(fields.get("subject") or fields.get("video_subject") or "").strip() or "Ders Notu",
        "script": str(fields.get("script") or fields.get("video_script") or "").strip(),
        "voice": voice,
        "voice_rate": voice_rate,
        "voice_volume": voice_volume,
        "aspect": aspect,
        "resolution": resolution,
        "bg_style": bg_style,
        "pexels_query": str(fields.get("pexels_query") or "").strip(),
        "subtitle_enabled": subtitle_enabled,
        "sub_color": sub_color,
        "sub_pos": sub_pos,
        "sub_size": sub_size,
        "sub_box": sub_box,
        "sub_bold": sub_bold,
        "sub_font": sub_font,
        "outline_color": outline_color,
        "highlight_words": highlight_words,
        "highlight_color": highlight_color,
        "highlight_size": highlight_size,
        "bgm_mode": "random" if bgm_source == "random" else "none",
        "bgm_volume": bgm_volume,
        "transition": transition,
        "transition_dur": transition_dur,
    }
    return params, custom_bg, custom_audio, bgm_path


LOGIN_HTML = """<!DOCTYPE html>
<html lang="tr"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Giriş - MoneyPrinter Studio</title>
<style>body{font-family:sans-serif;background:#090d16;color:#f8fafc;display:flex;
justify-content:center;align-items:center;height:100vh;margin:0}
.c{background:#131b2e;padding:28px;border-radius:14px;width:320px;text-align:center;border:1px solid #1e293b}
input{width:100%;padding:10px;border-radius:8px;background:#090d16;border:1px solid #334155;color:#fff;margin-top:12px;box-sizing:border-box}
button{width:100%;padding:11px;margin-top:12px;background:#6366f1;color:#fff;border:none;border-radius:8px;font-weight:700}</style></head>
<body><div class="c"><h2>⚡ MoneyPrinter Studio</h2>
<p style="color:#94a3b8;font-size:.85rem">Erişim bağlantısı ile giriş yapılır.<br>Token'ınız varsa girin:</p>
<form onsubmit="location='/?token='+encodeURIComponent(this.t.value);return false">
<input name="t" placeholder="Erişim token" autofocus>
<button>Giriş Yap</button></form></div></body></html>"""


class StudioHandler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    # ---------------------------------------------------------- auth

    def _get_token(self) -> str:
        try:
            return settings_manager.get_auth_token()
        except Exception:
            return ""

    def _authorized(self) -> bool:
        expected = self._get_token()
        if not expected:
            return True
        cookie = self.headers.get("Cookie", "")
        m = re.search(r'(?:^|;\s*)auth=([A-Za-z0-9_\-]+)', cookie)
        if m and hmac.compare_digest(m.group(1), expected):
            return True
        qs = parse_qs(urlparse(self.path).query)
        supplied = (qs.get("token") or [""])[0]
        return bool(supplied) and hmac.compare_digest(supplied, expected)

    def _set_auth_cookie(self):
        qs = parse_qs(urlparse(self.path).query)
        supplied = (qs.get("token") or [""])[0]
        expected = self._get_token()
        if supplied and expected and hmac.compare_digest(supplied, expected):
            self.send_header("Set-Cookie",
                             f"auth={expected}; Path=/; Max-Age=31536000; SameSite=Lax; HttpOnly")

    # ---------------------------------------------------------- senders

    def _send_bytes(self, body: bytes, ctype: str, status: int = 200,
                    extra_headers: dict | None = None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._set_auth_cookie()
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, data: dict, status: int = 200):
        self._send_bytes(json.dumps(data, ensure_ascii=False).encode("utf-8"),
                         "application/json; charset=utf-8", status)

    def _send_file_stream(self, file_path: str, download_name: str | None = None):
        file_size = os.path.getsize(file_path)
        mime, _ = mimetypes.guess_type(file_path)
        range_header = self.headers.get("Range")

        status = 200
        start, end = 0, file_size - 1
        extra = {"Accept-Ranges": "bytes"}
        if download_name:
            extra["Content-Disposition"] = f'attachment; filename="{download_name}"'

        if range_header:
            m = re.search(r"bytes=(\d+)-(\d*)", range_header)
            if m:
                start = int(m.group(1))
                if m.group(2):
                    end = min(int(m.group(2)), file_size - 1)
                status = 206
                extra["Content-Range"] = f"bytes {start}-{end}/{file_size}"

        length = end - start + 1
        self.send_response(status)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(length))
        for k, v in extra.items():
            self.send_header(k, v)
        self.end_headers()
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk = f.read(min(1024 * 64, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    # ---------------------------------------------------------- routing

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _guard(self) -> bool:
        if self._authorized():
            return True
        if urlparse(self.path).path.startswith("/api/"):
            self.send_json({"error": "Yetkisiz erişim"}, 401)
        else:
            self._send_bytes(LOGIN_HTML.encode("utf-8"), "text/html; charset=utf-8", 401)
        return False

    def do_GET(self):
        if not self._guard():
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path == "/":
            return self._serve_static("index.html")

        if path.startswith("/static/"):
            return self._serve_static(path[len("/static/"):])

        if path == "/api/tasks":
            tasks = []
            for t in task_store.get_all_tasks():
                t = dict(t)
                t["queue_position"] = task_store.queue_position(t["task_id"])
                t.pop("script", None)
                t.pop("logs", None)
                tasks.append(t)
            return self.send_json({
                "tasks": tasks,
                "running": worker.current_task_id(),
                "auth_url": f"http://{self.headers.get('Host', 'localhost')}:{PORT}/?token={self._get_token()}"
            })

        if path in ("/api/tasks/download-zip", "/api/gallery/download-zip"):
            return self._handle_download_zip(parse_qs(parsed.query))

        if path.startswith("/api/tasks/"):
            parts = path.split("/")
            if len(parts) >= 5 and parts[4] == "logs":
                task = task_store.get_task(parts[3])
                if not task:
                    return self.send_json({"error": "Görev bulunamadı"}, 404)
                return self.send_json({"logs": task.get("logs", [])})
            task = task_store.get_task(parts[3])
            if not task:
                return self.send_json({"error": "Görev bulunamadı"}, 404)
            return self.send_json(task)

        if path == "/api/settings":
            return self.send_json({"settings": settings_manager.get_masked_settings()})

        if path == "/api/voices":
            voices = []
            if os.path.exists(VOICES_FILE):
                try:
                    with open(VOICES_FILE, "r", encoding="utf-8") as f:
                        voices = json.load(f)
                except Exception:
                    voices = []
            return self.send_json({"voices": voices})

        if path == "/api/llm/providers":
            return self.send_json({"providers": llm_service.available_providers()})

        if path == "/api/models":
            qs = parse_qs(parsed.query)
            provider = (qs.get("provider") or [""])[0]
            try:
                return self.send_json({"models": llm_service.list_models(provider)})
            except Exception as e:
                return self.send_json({"error": str(e)}, 400)

        if path == "/api/tunnel/status":
            return self.send_json(self._tunnel_status())

        if path == "/api/songs":
            songs = []
            try:
                for f in sorted(os.listdir(SONGS_DIR)):
                    fp = os.path.join(SONGS_DIR, f)
                    if os.path.isfile(fp) and f.lower().endswith(BGM_EXTENSIONS):
                        size_mb = round(os.path.getsize(fp) / (1024 * 1024), 1)
                        songs.append({"name": f, "size_mb": size_mb})
            except OSError:
                pass
            return self.send_json({"songs": songs})

        if path == "/api/voice_preview":
            return self._handle_voice_preview(parse_qs(parsed.query))

        if path.startswith("/tasks/"):
            rel = path[len("/tasks/"):]
            fp = safe_join(TASKS_DIR, rel)
            if fp and os.path.isfile(fp):
                qs = parse_qs(parsed.query)
                dl_name = None
                if qs.get("download"):
                    raw_name = sanitize_filename(qs["download"][0])
                    base = os.path.basename(rel)
                    ext = os.path.splitext(base)[1] or ".mp4"
                    dl_name = (raw_name + ext) if not raw_name.endswith(ext) else raw_name
                return self._send_file_stream(fp, download_name=dl_name)
            return self.send_error(404, "File Not Found")

        self.send_error(404, "Not Found")

    def do_POST(self):
        if not self._guard():
            return
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/generate":
            return self._handle_generate()

        if path == "/api/batch":
            return self._handle_batch()

        if path == "/api/settings":
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
                saved = settings_manager.save_settings(data)
                return self.send_json({"success": True,
                                       "settings": settings_manager.get_masked_settings()})
            except Exception as e:
                return self.send_json({"success": False, "error": str(e)}, 400)

        if path == "/api/tunnel/start":
            return self.send_json(self._tunnel_start())

        if path == "/api/songs":
            return self._handle_song_upload()

        if path == "/api/llm/generate":
            try:
                data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
                result = llm_service.generate_script(
                    provider=data.get("provider", "gemini"),
                    model=str(data.get("model", "")),
                    subject=str(data.get("subject", "")).strip(),
                    language=str(data.get("language", "")).strip(),
                    paragraph_number=int(data.get("paragraph_number") or 1),
                    extra_requirements=str(data.get("extra_requirements", ""))[:2000],
                    gen_terms=bool(data.get("gen_terms", True))
                )
                return self.send_json({"success": True, **result})
            except Exception as e:
                logger.warning(f"LLM script üretimi hatası: {e}")
                return self.send_json({"error": str(e)[:300]}, 400)

        if path == "/api/tasks/cancel-all":
            cancelled = worker.cancel_all()
            return self.send_json({"success": True, "count": cancelled})

        if path == "/api/tasks/delete-all":
            deleted = worker.cancel_and_delete_all()
            return self.send_json({"success": True, "count": deleted})

        m = re.match(r"^/api/tasks/([\w\-]+)/resume$", path)
        if m:
            task_id = m.group(1)
            task = task_store.get_task(task_id)
            if not task:
                return self.send_json({"error": "Görev bulunamadı"}, 404)
            if task["state"] in ("processing",):
                return self.send_json({"error": "Görev zaten işleniyor"}, 400)
            ok = worker.enqueue(task_id)
            return self.send_json({"success": ok, "task_id": task_id})

        m = re.match(r"^/api/tasks/([\w\-]+)/cancel$", path)
        if m:
            ok = worker.cancel_task(m.group(1))
            return self.send_json({"success": ok})

        m = re.match(r"^/api/tasks/([\w\-]+)/regenerate$", path)
        if m:
            return self._handle_regenerate(m.group(1))

        self.send_error(404, "Endpoint Not Found")

    def do_DELETE(self):
        if not self._guard():
            return
        path = urlparse(self.path).path.rstrip("/")
        if path in ("/api/tasks", "/api/tasks/all"):
            deleted = worker.cancel_and_delete_all()
            return self.send_json({"success": True, "count": deleted})
        m = re.match(r"^/api/batches/([\w\-]+)$", path)
        if m:
            count = task_store.delete_batch(m.group(1))
            return self.send_json({"success": True, "count": count})
        m = re.match(r"^/api/tasks/([\w\-]+)$", path)
        if m:
            ok = task_store.delete_task(m.group(1))
            return self.send_json({"success": ok})
        m = re.match(r"^/api/songs/(.+)$", path)
        if m:
            fp = safe_join(SONGS_DIR, sanitize_filename(m.group(1)))
            if not fp or not os.path.isfile(fp):
                return self.send_json({"error": "Dosya bulunamadı"}, 404)
            try:
                os.remove(fp)
                return self.send_json({"success": True})
            except OSError as e:
                return self.send_json({"error": str(e)}, 500)
        self.send_error(404)

    # ---------------------------------------------------------- handlers

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_UPLOAD_BYTES:
            raise ValueError(f"Dosya çok büyük (maks {MAX_UPLOAD_BYTES // (1024*1024)} MB)")
        return self.rfile.read(length)

    def _parse_request(self):
        content_type = self.headers.get("Content-Type", "")
        body = self._read_body()
        if "multipart/form-data" in content_type:
            boundary = content_type.split("boundary=", 1)[1].split(";")[0].strip().encode()
            return parse_multipart(body, boundary)
        data = json.loads(body.decode("utf-8")) if body else {}
        return {k: str(v) for k, v in data.items()}, {}, []

    def _handle_generate(self):
        try:
            fields, files, _ = self._parse_request()
        except Exception as e:
            return self.send_json({"error": f"İstek okunamadı: {e}"}, 400)

        params, custom_bg, custom_audio, bgm_path = extract_task_params(fields, files)
        if not params["script"] and not custom_audio:
            return self.send_json({"error": "Lütfen bir ders scripti girin."}, 400)

        task_id = uuid.uuid4().hex
        task_store.create_task(task_id=task_id, custom_bg_media=custom_bg,
                               custom_audio=custom_audio, bgm_path=bgm_path,
                               **params)
        worker.enqueue(task_id)
        return self.send_json({"code": 0, "task_id": task_id, "status": "queued"})

    def _handle_batch(self):
        try:
            fields, files, _ = self._parse_request()
        except Exception as e:
            return self.send_json({"error": f"İstek okunamadı: {e}"}, 400)

        raw_text = ""
        if "batch_file" in files and files["batch_file"]["content"]:
            raw_text = files["batch_file"]["content"].decode("utf-8", errors="ignore")
        raw_text = raw_text or fields.get("batch_text", "")

        items = batch_engine.parse_batch_input(raw_text)
        if not items:
            return self.send_json({"error": "Geçerli ders scripti bulunamadı."}, 400)

        prod = settings_manager.load_settings()
        raw_voices = fields.get("voices") or fields.get("voice") or prod.get("prod_voice", "tr-TR-AhmetNeural")
        if isinstance(raw_voices, str) and "," in raw_voices:
            voices_list = [v.strip() for v in raw_voices.split(",") if v.strip()]
        elif isinstance(raw_voices, list):
            voices_list = [str(v).strip() for v in raw_voices if str(v).strip()]
        elif isinstance(raw_voices, str) and raw_voices.strip():
            voices_list = [raw_voices.strip()]
        else:
            voices_list = ["tr-TR-AhmetNeural"]

        batch_id = str(fields.get("batch_id") or "").strip() or f"batch_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        task_ids = batch_engine.create_batch_tasks(
            items,
            batch_id=batch_id,
            voice=voices_list[0] if voices_list else "tr-TR-AhmetNeural",
            voices=voices_list,
            voice_rate=float(fields.get("voice_rate") or prod.get("prod_voice_rate", 1.0)),
            voice_volume=float(fields.get("voice_volume") or prod.get("prod_voice_volume", 1.0)),
            aspect=fields.get("aspect") if fields.get("aspect") in ("9:16", "16:9", "1:1")
            else prod.get("prod_aspect", "9:16"),
            resolution=str(fields.get("resolution") or prod.get("prod_resolution", "720p")).strip().lower(),
            bg_style=fields.get("bg_style") or prod.get("prod_bg_style", "chalkboard"),
            subtitle_enabled=str(fields.get("subtitle_enabled") or prod.get("prod_subtitle_enabled", "true")).lower() in ("true", "1", "yes"),
            sub_color=fields.get("sub_color") or prod.get("prod_sub_color", "#FFFFFF"),
            sub_pos=fields.get("sub_pos") if fields.get("sub_pos") in ("bottom", "center", "top")
            else prod.get("prod_sub_pos", "bottom"),
            sub_size=max(12, min(40, int(fields.get("sub_size") or prod.get("prod_sub_size", 18)))),
            sub_box=str(fields.get("sub_box") or prod.get("prod_sub_box", "false")).lower() in ("true", "1", "yes"),
            sub_bold=str(fields.get("sub_bold") or prod.get("prod_sub_bold", "true")).lower() in ("true", "1", "yes"),
            sub_font=str(fields.get("sub_font") or prod.get("prod_sub_font", "Roboto")).strip() or "Roboto",
            outline_color=str(fields.get("outline_color") or prod.get("prod_outline_color", "#000000")).strip() or "#000000",
            highlight_words=fields.get("highlight_words") or prod.get("prod_highlight_words", ""),
            highlight_color=fields.get("highlight_color") or prod.get("prod_highlight_color", "#FFD700"),
            highlight_size=int(fields.get("highlight_size")) if fields.get("highlight_size") else None,
            bgm_mode="random" if (fields.get("bgm_source") or prod.get("prod_bgm_mode", "none")) == "random" else "none",
            transition=fields.get("transition") or prod.get("prod_transition", "none"),
            transition_dur=float(fields.get("transition_dur") or prod.get("prod_transition_dur", 0.5)),
        )
        return self.send_json({"code": 0, "batch_id": batch_id, "count": len(task_ids),
                               "task_ids": task_ids, "status": "queued"})

    def _handle_regenerate(self, task_id: str):
        """Bitmiş bir görevden varyant üretir (ses / görüntü / altyazı yeniden)."""
        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            data = json.loads(body.decode("utf-8")) if body else {}
        except Exception as e:
            return self.send_json({"error": f"İstek okunamadı: {e}"}, 400)

        src = task_store.get_task(task_id)
        if not src:
            return self.send_json({"error": "Görev bulunamadı"}, 404)
        if src.get("state") not in ("completed", "failed", "interrupted"):
            return self.send_json({"error": "Yalnızca bitmiş görevlerde varyant üretilebilir"}, 400)

        mode = str(data.get("mode", "all"))
        if mode not in ("voice", "visuals", "subtitles", "all"):
            return self.send_json({"error": "Geçersiz mod"}, 400)

        src_dir = os.path.join(TASKS_DIR, task_id)
        saved_audio = os.path.join(src_dir, "audio.mp3")
        saved_bg = os.path.join(src_dir, "background.mp4")

        params = {
            "subject": src.get("subject", "Ders"),
            "script": src.get("script", ""),
            "voice": src.get("voice", "tr-TR-AhmetNeural"),
            "voice_rate": max(0.5, min(2.0, float(src.get("voice_rate") or 1.0))),
            "voice_volume": max(0.1, min(3.0, float(src.get("voice_volume") or 1.0))),
            "aspect": src.get("aspect", "9:16"),
            "bg_style": src.get("bg_style", "chalkboard"),
            "pexels_query": src.get("pexels_query") or "",
            "subtitle_enabled": bool(src.get("subtitle_enabled", True)),
            "sub_color": src.get("sub_color", "#FFFFFF"),
            "sub_pos": src.get("sub_pos", "bottom"),
            "sub_size": max(12, min(36, int(src.get("sub_size") or 18))),
            "sub_box": bool(src.get("sub_box", False)),
            "bgm_mode": src.get("bgm_mode", "none"),
            "bgm_volume": max(0.0, min(1.0, float(src.get("bgm_volume") or 0.15))),
            "transition": src.get("transition", "none"),
            "transition_dur": max(0.1, min(2.0, float(src.get("transition_dur") or 0.5))),
        }
        custom_audio = src.get("custom_audio")
        custom_bg_media = src.get("custom_bg_media")

        if mode == "voice":
            if data.get("voice"):
                params["voice"] = str(data["voice"]).strip()
            if data.get("voice_rate") is not None:
                params["voice_rate"] = max(0.5, min(2.0, float(data["voice_rate"])))
            if data.get("voice_volume") is not None:
                params["voice_volume"] = max(0.1, min(3.0, float(data["voice_volume"])))
            # Görüntü aynı kalsın (pexels arka plan varsa onu kullan)
            custom_bg_media = saved_bg if os.path.exists(saved_bg) else src.get("custom_bg_media")
            custom_audio = None  # TTS yeniden üretilir
        elif mode == "visuals":
            if data.get("pexels_query") is not None:
                params["pexels_query"] = str(data["pexels_query"]).strip()
            if src.get("bg_style") == "pexels":
                custom_bg_media = None
                if not params["pexels_query"]:
                    params["pexels_query"] = src.get("subject", "")
            else:
                import random
                choices = [s for s in ("chalkboard", "dark_slate", "warm_study", "midnight_purple")
                           if s != src.get("bg_style")]
                params["bg_style"] = random.choice(choices) if choices else "chalkboard"
                custom_bg_media = None
                params["pexels_query"] = ""
            # Ses aynı kalsın
            custom_audio = saved_audio if os.path.exists(saved_audio) else src.get("custom_audio")
        elif mode == "subtitles":
            if data.get("sub_color"):
                params["sub_color"] = str(data["sub_color"])
            if data.get("sub_pos"):
                params["sub_pos"] = str(data["sub_pos"])
            if data.get("sub_size") is not None:
                params["sub_size"] = max(12, min(36, int(data["sub_size"])))
            if data.get("sub_box") is not None:
                params["sub_box"] = bool(data["sub_box"])
            if data.get("subtitle_enabled") is not None:
                params["subtitle_enabled"] = bool(data["subtitle_enabled"])
            # Ses ve görüntü aynı; orijinal cümle zamanlamaları korunur
            custom_audio = saved_audio if os.path.exists(saved_audio) else src.get("custom_audio")
            custom_bg_media = saved_bg if os.path.exists(saved_bg) else src.get("custom_bg_media")
        else:  # all
            if data.get("voice"):
                params["voice"] = str(data["voice"]).strip()
            if data.get("voice_rate") is not None:
                params["voice_rate"] = max(0.5, min(2.0, float(data["voice_rate"])))
            if data.get("sub_color"):
                params["sub_color"] = str(data["sub_color"])
            if data.get("sub_pos"):
                params["sub_pos"] = str(data["sub_pos"])
            if data.get("sub_size") is not None:
                params["sub_size"] = max(12, min(36, int(data["sub_size"])))
            if data.get("sub_box") is not None:
                params["sub_box"] = bool(data["sub_box"])
            custom_audio = None
            custom_bg_media = None

        new_id = uuid.uuid4().hex
        task_store.create_task(task_id=new_id, custom_bg_media=custom_bg_media,
                               custom_audio=custom_audio, bgm_path=src.get("bgm_path"),
                               **params)
        task_store.update_task(new_id, parent_task_id=task_id, regenerate_mode=mode,
                               source_video=src.get("file_path"),
                               log_message=f"Varyant üretiliyor ({mode})")
        worker.enqueue(new_id)
        return self.send_json({"code": 0, "task_id": new_id, "status": "queued", "mode": mode})

    def _handle_song_upload(self):
        """Multipart gonderiyi resource/songs/ icine kaydeder (coklu dosya destekli)."""
        try:
            _, _, file_list = self._parse_request()
        except Exception as e:
            return self.send_json({"error": f"Yükleme okunamadı: {e}"}, 400)

        saved, skipped = [], []
        for item in file_list:
            name = sanitize_filename(item.get("filename", ""))
            base, ext = os.path.splitext(name)
            if ext.lower() not in BGM_EXTENSIONS:
                skipped.append(name or "(isimsiz)")
                continue
            dest = os.path.join(SONGS_DIR, f"{base}{ext.lower()}")
            counter = 1
            while os.path.exists(dest):
                dest = os.path.join(SONGS_DIR, f"{base}_{counter}{ext.lower()}")
                counter += 1
            try:
                with open(dest, "wb") as f:
                    f.write(item["content"])
                saved.append(os.path.basename(dest))
            except OSError as e:
                return self.send_json({"error": f"Kaydedilemedi: {e}"}, 500)

        result = {"success": True, "saved": saved}
        if skipped:
            result["skipped"] = skipped
            result["message"] = (f"{len(saved)} dosya eklendi. "
                                 f"Desteklenmeyen format atlandı: {', '.join(skipped)}")
        else:
            result["message"] = f"{len(saved)} müzik eklendi."
        return self.send_json(result)

    def _handle_voice_preview(self, qs: dict):
        """Secilen sesle kisa ornek cumlesi uretir (onbellekli) ve mp3 dondurur."""
        voice = (qs.get("voice") or [""])[0].strip()
        if not voice or len(voice) > 80 or not re.match(r"^[\w\-]+$", voice):
            return self.send_json({"error": "Geçersiz ses adı"}, 400)

        preview_file = os.path.join(PREVIEWS_DIR, f"{voice}.mp3")
        if not os.path.exists(preview_file):
            try:
                import asyncio
                import edge_tts
                async def _gen():
                    com = edge_tts.Communicate(text=VOICE_PREVIEW_TEXT, voice=voice)
                    await com.save(preview_file)
                asyncio.run(_gen())
            except Exception as e:
                logger.warning(f"Ses önizleme hatası ({voice}): {e}")
                return self.send_json({"error": f"Önizleme üretilemedi: {str(e)[:150]}"}, 500)

        if not os.path.exists(preview_file) or os.path.getsize(preview_file) < 200:
            return self.send_json({"error": "Önizleme üretilemedi"}, 500)
        return self._send_file_stream(preview_file)

    def _handle_download_zip(self, qs: dict):
        """Toplu baslatma grubu, secili gorevler veya tum tamamlanmis videolari SIKISTIRMASIZ (ZIP_STORED) ZIP arsivi olarak sunar."""
        batch_id_param = (qs.get("batch_id") or [""])[0].strip()
        task_ids_param = (qs.get("task_ids") or [""])[0].strip()
        date_param = (qs.get("date") or [""])[0].strip()
        is_all = bool(qs.get("all") or date_param.lower() == "all" or (not batch_id_param and not task_ids_param and not date_param))

        target_task_ids = set([x.strip() for x in task_ids_param.split(",") if x.strip()]) if task_ids_param else set()

        tasks = task_store.get_all_tasks()
        completed = []
        for t in tasks:
            if t.get("state") != "completed":
                continue
            fp = t.get("file_path")
            if not fp or not os.path.isfile(fp):
                continue

            if is_all:
                completed.append(t)
            elif target_task_ids:
                if t.get("task_id") in target_task_ids:
                    completed.append(t)
            elif batch_id_param:
                if t.get("batch_id") == batch_id_param:
                    completed.append(t)
            elif date_param:
                t_date = (t.get("created_at_str") or "")[:10]
                if t_date == date_param:
                    completed.append(t)
                else:
                    try:
                        c_date = time.strftime("%Y-%m-%d", time.localtime(t.get("created_at", 0)))
                        if c_date == date_param:
                            completed.append(t)
                    except Exception:
                        pass

        if not completed:
            return self.send_json({"error": "İndirilecek tamamlanmış video bulunamadı."}, 404)

        # Videoları sırala (batch_index veya created_at artan sırayla)
        completed.sort(key=lambda x: (x.get("batch_index") or 0, x.get("created_at", 0)))

        temp_zip_dir = os.path.join(BASE_DIR, "storage", "temp_zips")
        os.makedirs(temp_zip_dir, exist_ok=True)

        # 1 saatten eski geçici zip dosyalarını temizle
        try:
            now = time.time()
            for f in os.listdir(temp_zip_dir):
                zp = os.path.join(temp_zip_dir, f)
                if os.path.isfile(zp) and now - os.path.getmtime(zp) > 3600:
                    os.remove(zp)
        except Exception:
            pass

        zip_id = uuid.uuid4().hex[:8]
        timestamp_tag = time.strftime("%Y%m%d_%H%M%S")

        if batch_id_param:
            clean_bname = sanitize_filename(batch_id_param)
            dl_display_name = f"MoneyPrinter_{clean_bname}.zip"
            zip_filename = f"mpt_{clean_bname}_{zip_id}.zip"
        elif is_all:
            dl_display_name = f"MoneyPrinter_tum_videolar_{timestamp_tag}.zip"
            zip_filename = f"mpt_tum_videolar_{timestamp_tag}_{zip_id}.zip"
        elif target_task_ids:
            dl_display_name = f"MoneyPrinter_secili_videolar_{timestamp_tag}.zip"
            zip_filename = f"mpt_secili_{timestamp_tag}_{zip_id}.zip"
        else:
            dl_display_name = f"MoneyPrinter_videolar_{date_param or timestamp_tag}.zip"
            zip_filename = f"mpt_videolar_{date_param or timestamp_tag}_{zip_id}.zip"

        zip_path = os.path.join(temp_zip_dir, zip_filename)

        used_arcnames = set()
        # Sıkıştırmasız ZIP (ZIP_STORED): Videolar zaten h264/aac sıkıştırmalı olduğu için sıfır CPU, anında byte kopyalama
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
            for idx, t in enumerate(completed, 1):
                raw_title = t.get("subject") or f"video_{idx}"
                safe_title = sanitize_filename(raw_title).replace(" ", "_")
                b_idx = t.get("batch_index")
                num_prefix = f"{b_idx:02d}_" if b_idx is not None else f"{idx:02d}_"

                if not safe_title.lower().endswith(".mp4"):
                    arcname = f"{num_prefix}{safe_title}.mp4"
                else:
                    arcname = f"{num_prefix}{safe_title}"

                base_arc, ext_arc = os.path.splitext(arcname)
                counter = 1
                while arcname in used_arcnames:
                    arcname = f"{base_arc}_{counter}{ext_arc}"
                    counter += 1
                used_arcnames.add(arcname)
                zf.write(t["file_path"], arcname=arcname)

        return self._send_file_stream(zip_path, download_name=dl_display_name)

    # ---------------------------------------------------------- tunnel

    def _tunnel_status(self) -> dict:
        global _ngrok_proc
        running = bool(_ngrok_proc and _ngrok_proc.poll() is None)
        public_url = None
        try:
            req = urllib.request.Request("http://127.0.0.1:4040/api/tunnels")
            with urllib.request.urlopen(req, timeout=2) as r:
                data = json.loads(r.read().decode())
                tunnels = data.get("tunnels", [])
                if tunnels:
                    public_url = tunnels[0].get("public_url")
        except Exception:
            pass
        return {"running": running, "public_url": public_url}

    def _tunnel_start(self) -> dict:
        global _ngrok_proc
        if _ngrok_proc and _ngrok_proc.poll() is None:
            return {**self._tunnel_status(), "message": "Tunnel zaten çalışıyor"}

        ngrok_bin = shutil.which("ngrok")
        if not ngrok_bin:
            return {"running": False, "public_url": None,
                    "error": "ngrok bulunamadı. Kurulum: pkg install ngrok"}

        token = str(settings_manager.get_setting("ngrok_authtoken", "")).strip()
        if token:
            os.system(f"'{ngrok_bin}' config add-authtoken '{token}' >/dev/null 2>&1")

        # Eski/takili kalan ngrok surecleri yeni tunnel'i engeller; temizle.
        os.system("pkill -f 'ngrok http' >/dev/null 2>&1")
        time.sleep(1)

        ngrok_log = open(os.path.join(BASE_DIR, "storage", "ngrok.log"), "w")
        try:
            _ngrok_proc = subprocess.Popen(
                [ngrok_bin, "http", str(PORT)],
                stdout=ngrok_log, stderr=ngrok_log,
                start_new_session=True
            )
        except Exception as e:
            ngrok_log.close()
            return {"running": False, "public_url": None, "error": str(e)}

        for _ in range(12):
            time.sleep(1)
            st = self._tunnel_status()
            if st.get("public_url"):
                ngrok_log.close()
                st["message"] = "Tunnel başlatıldı"
                return st
            if _ngrok_proc.poll() is not None:
                break  # surec olmus, logdan oku

        ngrok_log.close()
        try:
            with open(os.path.join(BASE_DIR, "storage", "ngrok.log"), "r") as f:
                lines = [l for l in f.read().strip().splitlines() if l.strip()]
            err_tail = lines[-1] if lines else ""
        except OSError:
            err_tail = ""
        return {**st, "error": f"Tunnel başlatılamadı. {err_tail[:200]}"}

    # ---------------------------------------------------------- static

    def _serve_static(self, rel_path: str):
        fp = safe_join(STATIC_DIR, rel_path)
        if not fp or not os.path.isfile(fp):
            return self.send_error(404, "Not Found")
        mime, _ = mimetypes.guess_type(fp)
        with open(fp, "rb") as f:
            body = f.read()
        extra = {}
        if rel_path.startswith("examples/"):
            extra["Content-Disposition"] = f'attachment; filename="{os.path.basename(fp)}"'
        self._send_bytes(body, mime or "application/octet-stream", extra_headers=extra)

    def log_message(self, format, *args):
        pass


def main():
    sys.path.insert(0, BASE_DIR)
    task_store.migrate_legacy_batches()
    token = settings_manager.get_auth_token()
    worker.start_worker()

    socketserver.TCPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("0.0.0.0", PORT), StudioHandler)

    logger.info("=" * 60)
    logger.info(f"🚀 MoneyPrinter Lite Studio: http://127.0.0.1:{PORT}")
    logger.info(f"🔗 Erişim bağlantısı: http://127.0.0.1:{PORT}/?token={token}")
    logger.info("=" * 60)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


if __name__ == "__main__":
    main()
