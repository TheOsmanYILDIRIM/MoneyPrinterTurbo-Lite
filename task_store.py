import json
import os
import threading
import time
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "storage", "tasks_db.json")
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
_lock = threading.RLock()

ACTIVE_STATES = ("queued", "processing")
TERMINAL_STATES = ("completed", "failed", "interrupted")


def _load_db() -> Dict[str, dict]:
    with _lock:
        if not os.path.exists(DB_FILE):
            return {}
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Hata task_store load: {e}")
            return {}


def _save_db(data: Dict[str, dict]):
    with _lock:
        tmp_path = DB_FILE + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, DB_FILE)
        except Exception as e:
            print(f"Hata task_store save: {e}")


def create_task(task_id: str, subject: str = "Ders", script: str = "", voice: str = "tr-TR-AhmetNeural",
                aspect: str = "9:16", resolution: str = "720p", bg_style: str = "chalkboard", pexels_query: str = "",
                voice_rate: float = 1.0, voice_volume: float = 1.0,
                subtitle_enabled: bool = True, sub_color: str = "#FFFFFF",
                sub_pos: str = "bottom", sub_size: int = 18,
                sub_box: bool = False, sub_bold: bool = True,
                sub_font: str = "Roboto", outline_color: str = "#000000",
                custom_bg_media: Optional[str] = None,
                custom_audio: Optional[str] = None,
                bgm_path: Optional[str] = None, bgm_mode: str = "none",
                bgm_volume: float = 0.15,
                transition: str = "none",
                transition_dur: float = 0.5,
                batch_index: Optional[int] = None,
                batch_total: Optional[int] = None,
                **kwargs) -> dict:
    tasks = _load_db()
    task = {
        "task_id": task_id,
        "created_at": time.time(),
        "created_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "subject": subject,
        "script": script,
        "voice": voice,
        "voice_rate": voice_rate,
        "voice_volume": voice_volume,
        "aspect": aspect,
        "resolution": resolution or "720p",
        "bg_style": bg_style,
        "pexels_query": pexels_query,
        "subtitle_enabled": subtitle_enabled,
        "sub_color": sub_color,
        "sub_pos": sub_pos,
        "sub_size": sub_size,
        "sub_box": sub_box,
        "sub_bold": sub_bold,
        "sub_font": sub_font,
        "outline_color": outline_color,
        "custom_bg_media": custom_bg_media,
        "custom_audio": custom_audio,
        "bgm_path": bgm_path,
        "bgm_mode": bgm_mode if bgm_mode in ("none", "random") else "none",
        "bgm_volume": bgm_volume,
        "transition": transition if transition in ("none", "crossfade") else "none",
        "transition_dur": max(0.1, min(2.0, float(transition_dur or 0.5))),
        "batch_index": batch_index,
        "batch_total": batch_total,
        "state": "queued",
        "progress": 5,
        "step_text": "Kuyrukta bekliyor...",
        "video_url": None,
        "file_path": None,
        "file_size_mb": None,
        "error": None,
        "logs": []
    }
    tasks[task_id] = task
    _save_db(tasks)
    return task


def update_task(task_id: str, log_message: Optional[str] = None, **kwargs) -> Optional[dict]:
    with _lock:
        tasks = _load_db()
        if task_id not in tasks:
            return None
        task = tasks[task_id]
        task.update(kwargs)
        if log_message:
            logs = task.setdefault("logs", [])
            logs.append(f"[{time.strftime('%H:%M:%S')}] {log_message}")
            task["logs"] = logs[-50:]
        _save_db(tasks)
        return task


def get_task(task_id: str) -> Optional[dict]:
    return _load_db().get(task_id)


def get_all_tasks() -> List[dict]:
    tasks = _load_db()
    return sorted(list(tasks.values()), key=lambda x: x.get("created_at", 0), reverse=True)


def get_next_queued() -> Optional[dict]:
    """FIFO: en eski kuyruktaki gorevi dondurur."""
    tasks = _load_db()
    queued = [t for t in tasks.values() if t.get("state") == "queued"]
    if not queued:
        return None
    return min(queued, key=lambda x: x.get("created_at", 0))


def queue_position(task_id: str) -> int:
    """Gorevin kuyruktaki sirasi (1 tabanli). Islenmiyorsa -1."""
    task = get_task(task_id)
    if not task or task.get("state") != "queued":
        return -1
    tasks = _load_db()
    created = task.get("created_at", 0)
    ahead = sum(1 for t in tasks.values()
                if t.get("state") == "queued" and t.get("created_at", 0) < created)
    return ahead + 1


def mark_interrupted_on_startup():
    """Sunucu yeniden baslatildiginda yarim kalan isleri 'interrupted' yapar.
    Otomatik fail etmez; kullanici 'Devam Et' ile tekrar kuyruga alabilir."""
    tasks = _load_db()
    changed = False
    for t in tasks.values():
        if t.get("state") in ACTIVE_STATES:
            t["state"] = "interrupted"
            t["step_text"] = "Sunucu yeniden başlatıldı, görev duraklatıldı"
            changed = True
    if changed:
        _save_db(tasks)


def delete_task(task_id: str) -> bool:
    tasks = _load_db()
    if task_id not in tasks:
        return False
    task_data = tasks.pop(task_id)
    _save_db(tasks)
    file_path = task_data.get("file_path")
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass
    task_dir = os.path.join(BASE_DIR, "storage", "tasks", task_id)
    if os.path.isdir(task_dir):
        try:
            for fname in os.listdir(task_dir):
                try:
                    os.remove(os.path.join(task_dir, fname))
                except Exception:
                    pass
            os.rmdir(task_dir)
        except Exception:
            pass
    return True
