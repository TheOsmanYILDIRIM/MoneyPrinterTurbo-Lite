import json
import os
import shutil
import threading
import time
from typing import Dict, List, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_storage_dir() -> str:
    path = os.environ.get("STORAGE_DIR", os.path.join(BASE_DIR, "storage"))
    os.makedirs(path, exist_ok=True)
    return path


def get_db_file() -> str:
    return os.environ.get("TASKS_DB_FILE", os.path.join(get_storage_dir(), "tasks_db.json"))


def get_tasks_dir() -> str:
    path = os.environ.get("TASKS_DIR", os.path.join(get_storage_dir(), "tasks"))
    os.makedirs(path, exist_ok=True)
    return path


STORAGE_DIR = get_storage_dir()
DB_FILE = get_db_file()
TASKS_DIR = get_tasks_dir()
_lock = threading.RLock()

ACTIVE_STATES = ("queued", "processing")
TERMINAL_STATES = ("completed", "failed", "interrupted")


def _load_db() -> Dict[str, dict]:
    with _lock:
        db_file = get_db_file()
        if not os.path.exists(db_file):
            return {}
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Hata task_store load: {e}")
            return {}


def _save_db(data: Dict[str, dict]):
    with _lock:
        db_file = get_db_file()
        os.makedirs(os.path.dirname(db_file), exist_ok=True)
        tmp_path = db_file + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            os.replace(tmp_path, db_file)
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
                batch_id: Optional[str] = None,
                batch_index: Optional[int] = None,
                batch_total: Optional[int] = None,
                highlight_words: Optional[any] = None,
                highlight_color: Optional[str] = None,
                highlight_size: Optional[int] = None,
                **kwargs) -> dict:
    tasks = _load_db()
    task = {
        "task_id": task_id,
        "batch_id": batch_id or kwargs.get("batch_id"),
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
        "highlight_words": highlight_words,
        "highlight_color": highlight_color,
        "highlight_size": highlight_size,
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
    task.update(kwargs)
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


def resume_interrupted_tasks() -> int:
    """Yarım kalan (interrupted/processing) görevleri tekrar 'queued' durumuna alarak devam ettirir."""
    with _lock:
        tasks = _load_db()
        count = 0
        for t in tasks.values():
            if t.get("state") in ("interrupted", "processing"):
                t["state"] = "queued"
                t["progress"] = 5
                t["step_text"] = "Kaldığı yerden devam etmek üzere kuyruğa alındı"
                t["error"] = None
                count += 1
        if count > 0:
            _save_db(tasks)
        return count


def delete_task(task_id: str) -> bool:
    with _lock:
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
    shutil.rmtree(os.path.join(get_tasks_dir(), task_id), ignore_errors=True)
    return True


def delete_all_tasks() -> int:
    """Galerideki ve veritabanındaki tüm görevleri ve dosyalarını siler."""
    with _lock:
        task_ids = list(_load_db().keys())
    for tid in task_ids:
        delete_task(tid)
    return len(task_ids)


def delete_batch(batch_id: str) -> int:
    """Belirli bir batch_id'ye ait tüm görevleri ve dosyalarını siler."""
    with _lock:
        tasks = _load_db()
        matching_ids = [tid for tid, t in tasks.items() if t.get("batch_id") == batch_id]
        for tid in matching_ids:
            delete_task(tid)
        return len(matching_ids)


def get_tasks_by_batch(batch_id: str) -> List[dict]:
    """Belirli bir batch_id'ye ait tüm görevleri sıralı döndürür."""
    tasks = _load_db()
    batch_tasks = [t for t in tasks.values() if t.get("batch_id") == batch_id]
    return sorted(batch_tasks, key=lambda x: (x.get("batch_index") or 0, x.get("created_at", 0)))

