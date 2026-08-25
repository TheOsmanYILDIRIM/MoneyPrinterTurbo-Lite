import os
import threading
import time
from typing import Optional

from loguru import logger

import task_store
import settings_manager
from lite_engine import build_lecture_video, resolve_video_dimensions, downgrade_video_to_480p, TaskCancelled

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_tasks_dir() -> str:
    return task_store.get_tasks_dir()


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


def cancel_all() -> int:
    """Tüm aktif (kuyrukta veya işlenen) görevleri iptal eder."""
    tasks = task_store.get_all_tasks()
    cancelled_count = 0
    for t in tasks:
        tid = t.get("task_id")
        if t.get("state") in ("queued", "processing"):
            if cancel_task(tid):
                cancelled_count += 1
    return cancelled_count


def cancel_and_delete_all() -> int:
    """Önce tüm görevleri iptal eder sonra veritabanı ve dosyalardan temizler."""
    cancel_all()
    return task_store.delete_all_tasks()



def _run_task(task_id: str):
    task = task_store.get_task(task_id)
    if not task:
        return

    tasks_base = get_tasks_dir()
    task_dir = os.path.join(tasks_base, task_id)
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
        cand = os.path.join(tasks_base, parent, "subtitle_cues.json")
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
            highlight_words=task.get("highlight_words"),
            highlight_color=task.get("highlight_color"),
            highlight_size=task.get("highlight_size"),
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
        video_480p_file = None
        file_size_480p_mb = None
        video_url_480p = None

        if os.path.exists(video_file):
            file_size_mb = round(os.path.getsize(video_file) / (1024 * 1024), 2)

            # 480p Düşük Boyutlu Kopya Oluşturma (Ayar veya görev bazlı)
            save_480p = bool(task.get("save_480p", False) or settings_manager.get_setting("prod_save_480p", False))
            if save_480p and resolution != "480p":
                try:
                    task_store.update_task(task_id, step_text="480p düşük boyutlu kopya oluşturuluyor...")
                    w480, h480 = resolve_video_dimensions(aspect, "480p")
                    out_480p_name = f"final_480p_{h480}p.mp4"
                    out_480p_path = os.path.join(task_dir, out_480p_name)
                    downgraded = downgrade_video_to_480p(video_file, out_480p_path, aspect=aspect, task_id=task_id)
                    if downgraded and os.path.exists(downgraded):
                        video_480p_file = downgraded
                        file_size_480p_mb = round(os.path.getsize(downgraded) / (1024 * 1024), 2)
                        video_url_480p = f"/tasks/{task_id}/{out_480p_name}"
                        logger.info(f"Görev {task_id} için 480p kopya hazır: {video_480p_file} ({file_size_480p_mb} MB)")
                except Exception as down_err:
                    logger.warning(f"480p downgrade hatası ({task_id}): {down_err}")

            # Drive/outputs ve Drive/downgraded_outputs klasörlerine kopyala (toplu görevleri klasörle)
            storage_dir = task_store.get_storage_dir()
            outputs_dir = os.environ.get("OUTPUTS_DIR", os.path.join(storage_dir, "outputs"))
            downgraded_dir = os.environ.get("DOWNGRADED_OUTPUTS_DIR", os.path.join(storage_dir, "downgraded_outputs"))
            batch_id = task.get("batch_id")
            try:
                import re
                import shutil
                clean_subject = re.sub(r'[^\w\-_ ]+', '_', subject)[:40].strip()

                # HD/Orijinal video klasörleme
                target_out_dir = os.path.join(outputs_dir, batch_id) if batch_id else outputs_dir
                os.makedirs(target_out_dir, exist_ok=True)
                out_copy_name = f"{clean_subject}_{task_id[:6]}.mp4"
                out_copy_path = os.path.join(target_out_dir, out_copy_name)
                shutil.copy2(video_file, out_copy_path)

                # 480p video klasörleme (downgraded_outputs klasörüne)
                if video_480p_file and os.path.exists(video_480p_file):
                    target_down_dir = os.path.join(downgraded_dir, batch_id) if batch_id else downgraded_dir
                    os.makedirs(target_down_dir, exist_ok=True)
                    out_copy_480p_name = f"{clean_subject}_{task_id[:6]}_480p.mp4"
                    out_copy_480p_path = os.path.join(target_down_dir, out_copy_480p_name)
                    shutil.copy2(video_480p_file, out_copy_480p_path)
            except Exception as copy_err:
                logger.debug(f"Outputs kopyalama atlandı: {copy_err}")

        task_store.update_task(
            task_id,
            state="completed",
            progress=100,
            step_text="Tamamlandı",
            video_url=f"/tasks/{task_id}/{filename}",
            thumbnail_url=f"/tasks/{task_id}/thumb.jpg",
            file_path=video_file,
            file_size_mb=file_size_mb,
            video_url_480p=video_url_480p,
            file_path_480p=video_480p_file,
            file_size_480p_mb=file_size_480p_mb
        )
        logger.success(f"Görev {task_id} tamamlandı: {video_file} ({file_size_mb} MB){f' [480p: {file_size_480p_mb} MB]' if file_size_480p_mb else ''}")
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


def start_worker(auto_resume: bool = False):
    global _thread
    if _thread and _thread.is_alive():
        return
    task_store.mark_interrupted_on_startup()
    if auto_resume or os.environ.get("AUTO_RESUME", "").lower() in ("1", "true", "yes"):
        resumed = task_store.resume_interrupted_tasks()
        if resumed > 0:
            logger.info(f"Yarım kalan / bekleyen {resumed} görev otomatik olarak tekrar kuyruğa alındı.")
    _thread = threading.Thread(target=_worker_loop, name="job-worker", daemon=True)
    _thread.start()
    _wake.set()
    logger.info("Worker başlatıldı (tek iş parçacığı, kalıcı kuyruk)")
