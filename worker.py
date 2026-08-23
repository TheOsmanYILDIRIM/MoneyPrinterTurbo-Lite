import os
import threading
import time
from typing import Optional

from loguru import logger

import task_store
from lite_engine import build_lecture_video, resolve_video_dimensions, TaskCancelled

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_DIR = os.path.join(BASE_DIR, "storage", "tasks")

_wake = threading.Event()
_thread: Optional[threading.Thread] = None
_current_lock = threading.Lock()

# İptal istenen görev kimlikleri
CANCEL_FLAGS: set = set()


def current_task_id() -> Optional[str]:
    return getattr(_thread, "running_task_id", None)


def enqueue(task_id: str) -> bool:
    """Görevi kuyruğa alır (state=queued) ve worker'ı uyandırır."""
    task = task_store.get_task(task_id)
    if not task:
        return False
    CANCEL_FLAGS.discard(task_id)
    task_store.update_task(
        task_id,
        state="queued",
        progress=5,
        step_text="Kuyrukta bekliyor...",
        error=None,
        log_message="Kuyruğa alındı"
    )
    _wake.set()
    return True


def cancel_task(task_id: str) -> bool:
    """Kuyruktaki veya işlenen görevi iptal eder."""
    task = task_store.get_task(task_id)
    if not task:
        return False
    state = task.get("state")
    if state == "queued":
        CANCEL_FLAGS.discard(task_id)
        task_store.update_task(
            task_id,
            state="interrupted",
            progress=0,
            step_text="İptal edildi",
            error=None,
            log_message="Kullanıcı tarafından iptal edildi"
        )
        return True
    if state == "processing":
        CANCEL_FLAGS.add(task_id)
        proc = None
        try:
            from lite_engine import _active_ffmpeg
            proc = _active_ffmpeg.get(task_id)
        except Exception:
            pass
        if proc is not None:
            try:
                proc.terminate()
            except Exception:
                pass
        task_store.update_task(
            task_id,
            step_text="İptal ediliyor...",
            log_message="İptal isteği alındı"
        )
        return True
    return False


def _run_task(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        return

    task_dir = os.path.join(TASKS_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    subject = task.get("subject", "Ders")
    aspect = task.get("aspect", "9:16")
    resolution = task.get("resolution", "720p")
    w, h = resolve_video_dimensions(aspect, resolution)
    filename = f"final_{resolution}_{h}p.mp4"

    task_store.update_task(
        task_id,
        state="processing",
        progress=10,
        step_text="İşlem başlatılıyor...",
        video_url=None,
        file_path=None,
        file_size_mb=None,
        error=None
    )

    def on_progress(p: int, text: str):
        task_store.update_task(task_id, progress=p, step_text=text)

    is_cancelled = lambda: task_id in CANCEL_FLAGS

    # Varyant görevlerinde orijinal zamanlamaları koru
    reuse_cues = os.path.join(task_dir, "subtitle_cues.json")
    parent = task.get("parent_task_id")
    if parent and task.get("regenerate_mode") in ("visuals", "subtitles"):
        cand = os.path.join(TASKS_DIR, parent, "subtitle_cues.json")
        if os.path.exists(cand):
            reuse_cues = cand

    try:
        bg_style = task.get("bg_style", "chalkboard")
        pexels_query = task.get("pexels_query") or (subject if bg_style == "pexels" else None)

        video_file = build_lecture_video(
            subject=subject,
            script=task.get("script", ""),
            voice_name=task.get("voice", "tr-TR-AhmetNeural"),
            voice_rate=float(task.get("voice_rate") or 1.0),
            voice_volume=float(task.get("voice_volume") or 1.0),
            aspect=aspect,
            resolution=resolution,
            bg_style=bg_style,
            pexels_query=pexels_query,
            custom_bg_media=task.get("custom_bg_media"),
            custom_audio=task.get("custom_audio"),
            reuse_cues_path=reuse_cues,
            subtitle_enabled=bool(task.get("subtitle_enabled", True)),
            sub_color=task.get("sub_color", "#FFFFFF"),
            sub_pos=task.get("sub_pos", "bottom"),
            sub_size=int(task.get("sub_size") or 18),
            sub_box=bool(task.get("sub_box", False)),
            sub_bold=bool(task.get("sub_bold", True)),
            sub_font=task.get("sub_font", "Roboto"),
            outline_color=task.get("outline_color", "#000000"),
            bgm_path=task.get("bgm_path"),
            bgm_mode=task.get("bgm_mode", "none"),
            bgm_volume=float(task.get("bgm_volume") or 0.15),
            transition=task.get("transition", "none"),
            transition_dur=float(task.get("transition_dur") or 0.5),
            output_dir=task_dir,
            filename=filename,
            progress_callback=on_progress,
            task_id=task_id,
            cancel_requested=is_cancelled,
            source_video_path=task.get("source_video")
        )

        file_size_mb = 0.0
        if os.path.exists(video_file):
            file_size_mb = round(os.path.getsize(video_file) / (1024 * 1024), 2)

        task_store.update_task(
            task_id,
            state="completed",
            progress=100,
            step_text="Tamamlandı",
            video_url=f"/tasks/{task_id}/{filename}",
            file_path=video_file,
            file_size_mb=file_size_mb
        )
        logger.success(f"Görev {task_id} tamamlandı: {video_file} ({file_size_mb} MB)")
    except TaskCancelled:
        task_store.update_task(
            task_id,
            state="interrupted",
            progress=0,
            step_text="İptal edildi",
            error=None
        )
        logger.info(f"Görev {task_id} kullanıcı tarafından iptal edildi.")
    except Exception as e:
        task_store.update_task(
            task_id,
            state="failed",
            step_text=f"Hata: {str(e)[:200]}",
            error=str(e)
        )
        logger.exception(f"Görev {task_id} hatası: {e}")


def _worker_loop():
    while True:
        _wake.wait(timeout=1.5)
        _wake.clear()
        while True:
            nxt = task_store.get_next_queued()
            if not nxt:
                break
            tid = nxt["task_id"]
            setattr(_thread, "running_task_id", tid)
            try:
                _run_task(tid)
            except Exception as e:
                logger.exception(f"Worker beklenmeyen hata ({tid}): {e}")
                task_store.update_task(tid, state="failed", error=str(e),
                                       step_text=f"Beklenmeyen hata: {str(e)[:200]}")
            finally:
                setattr(_thread, "running_task_id", None)
                CANCEL_FLAGS.discard(tid)


def start_worker():
    global _thread
    if _thread and _thread.is_alive():
        return
    task_store.mark_interrupted_on_startup()
    _thread = threading.Thread(target=_worker_loop, name="job-worker", daemon=True)
    _thread.start()
    _wake.set()
    logger.info("Worker başlatıldı (tek iş parçacığı, kalıcı kuyruk)")
