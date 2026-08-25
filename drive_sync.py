#!/usr/bin/env python3
"""
MoneyPrinter Turbo - Google Drive Entegrasyon ve Checkpoint Yöneticisi
Google Colab ortamında Google Drive ile tam senkronizasyon, görev takibi,
otomatik ayar oluşturma ve kesintisiz kaldığı yerden devam etme işlevlerini sağlar.
"""

import os
import sys
import json
import time
import shutil
from typing import Dict, Any, Optional, List


def get_default_storage_dir() -> str:
    """Ortama göre varsayılan kalıcı depolama klasörünü belirler (Colab, Kaggle, Local)."""
    if os.environ.get("STORAGE_DIR"):
        return os.environ["STORAGE_DIR"]
    if os.path.exists("/content"):  # Google Colab
        return "/content/drive/MyDrive/MoneyPrinterTurbo"
    if os.path.exists("/kaggle"):   # Kaggle
        return "/kaggle/working/MoneyPrinterTurbo"
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(repo_dir, "storage")


DEFAULT_DRIVE_DIR = get_default_storage_dir()


def init_drive_environment(drive_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Google Drive / Kaggle / Yerel çalışma klasörlerini hazırlar,
    ortam değişkenlerini ayarlar ve storage dizinini bağlar.
    """
    if not drive_dir:
        drive_dir = get_default_storage_dir()
    drive_dir = os.path.abspath(drive_dir)
    tasks_dir = os.path.join(drive_dir, "tasks")
    outputs_dir = os.path.join(drive_dir, "outputs")
    downgraded_outputs_dir = os.path.join(drive_dir, "downgraded_outputs")
    uploads_dir = os.path.join(drive_dir, "uploads")
    batch_inputs_dir = os.path.join(drive_dir, "batch_inputs")
    settings_file = os.path.join(drive_dir, "settings.json")
    tasks_db_file = os.path.join(drive_dir, "tasks_db.json")

    # Klasörleri oluştur
    os.makedirs(drive_dir, exist_ok=True)
    os.makedirs(tasks_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(downgraded_outputs_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(batch_inputs_dir, exist_ok=True)

    # Ortam değişkenlerini ata
    os.environ["STORAGE_DIR"] = drive_dir
    os.environ["TASKS_DIR"] = tasks_dir
    os.environ["OUTPUTS_DIR"] = outputs_dir
    os.environ["DOWNGRADED_OUTPUTS_DIR"] = downgraded_outputs_dir
    os.environ["UPLOADS_DIR"] = uploads_dir
    os.environ["SETTINGS_FILE"] = settings_file
    os.environ["TASKS_DB_FILE"] = tasks_db_file

    # Yerel repo içindeki storage klasörünü Drive'a sembolik bağla (varsa yedekle)
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    local_storage = os.path.join(repo_dir, "storage")
    if drive_dir != local_storage:
        if os.path.exists(local_storage) and not os.path.islink(local_storage):
            try:
                # İçinde veri varsa Drive'a taşı/kopyala
                for item in os.listdir(local_storage):
                    src = os.path.join(local_storage, item)
                    dst = os.path.join(drive_dir, item)
                    if not os.path.exists(dst):
                        if os.path.isdir(src):
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                shutil.rmtree(local_storage, ignore_errors=True)
                os.symlink(drive_dir, local_storage)
            except Exception as e:
                print(f"Bilgi: Symlink oluşturulamadı ({e}), STORAGE_DIR ortam değişkeni kullanılacak.")
        elif not os.path.exists(local_storage):
            try:
                os.symlink(drive_dir, local_storage)
            except Exception:
                pass

    # Ayarlar dosyasını kontrol et ve yoksa oluştur
    _ensure_settings_file(settings_file)

    # Örnek toplu ders dosyası oluştur (eğer batch_inputs boşsa)
    _ensure_sample_batch_file(batch_inputs_dir)

    # Mevcut Drive ve çıktıları otomatik düzenle (480p'leri downgraded_outputs'a taşı ve toplu görevleri klasörle)
    organize_drive(drive_dir)

    print("=" * 65)
    print("✅ GOOGLE DRIVE ENTEGRASYONU TAMAMLANDI!")
    print(f"📁 Ana Drive Klasörü:       {drive_dir}")
    print(f"⚙️ Ayarlar & API Keys:      {settings_file}")
    print(f"📋 Görevler Veritabanı:     {tasks_db_file}")
    print(f"🎬 HD/Orijinal Videolar:    {outputs_dir}")
    print(f"📱 480p SD Videolar:        {downgraded_outputs_dir}")
    print(f"📝 Toplu Ders Girişi:       {batch_inputs_dir}")
    print("=" * 65)

    return {
        "drive_dir": drive_dir,
        "tasks_dir": tasks_dir,
        "outputs_dir": outputs_dir,
        "downgraded_outputs_dir": downgraded_outputs_dir,
        "uploads_dir": uploads_dir,
        "batch_inputs_dir": batch_inputs_dir,
        "settings_file": settings_file,
        "tasks_db_file": tasks_db_file
    }


def _ensure_settings_file(settings_path: str):
    """Eğer Drive'da settings.json yoksa varsayılan şablonu oluşturur."""
    if not os.path.exists(settings_path):
        import settings_manager
        defaults = settings_manager.DEFAULT_SETTINGS.copy()
        try:
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(defaults, f, ensure_ascii=False, indent=2)
            print(f"✨ Drive üzerinde yeni 'settings.json' şablonu oluşturuldu: {settings_path}")
        except Exception as e:
            print(f"Hata: settings.json oluşturulamadı: {e}")


def _ensure_sample_batch_file(batch_dir: str):
    """Kullanıcıya rehberlik etmesi için örnek bir toplu ders şablonu bırakır."""
    sample_path = os.path.join(batch_dir, "ornek_dersler.txt")
    if not os.path.exists(sample_path):
        content = (
            "# 1. Ders: Üslü Sayılar Temel Kurallar\n"
            "Keywords: mathematics chalkboard study\n"
            "Ses: tr-TR-AhmetNeural\n"
            "Vurgu: tabanlar aynıysa, üsler toplanır, pozitif\n"
            "Üslü sayılarda çarpma işlemi yapılırken tabanlar aynıysa üsler toplanır. Negatif bir sayının çift kuvveti her zaman pozitiftir.\n"
            "---\n"
            "# 2. Ders: Köklü Sayılar Özellikleri\n"
            "Keywords: algebra math classroom\n"
            "Ses: tr-TR-EmelNeural\n"
            "Vurgu: kök derecesi, sadeleştirme, mutlak değer\n"
            "Köklü ifadelerde kök derecesi çift olan bir sayının kök dışına çıkışı daima mutlak değer içinde gerçekleşir.\n"
        )
        try:
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass


def organize_drive(drive_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Drive üzerindeki çıktıları düzenler:
    1. 480p videoları 'downgraded_outputs' klasörüne taşır.
    2. Toplu görev videolarını ilgili batch_id klasörlerine gruplar (hem outputs hem downgraded_outputs altında).
    3. tasks_db ile senkronize eksik kopyaları tamamlar ve boş klasörleri temizler.
    """
    import re
    if not drive_dir:
        drive_dir = get_default_storage_dir()
    drive_dir = os.path.abspath(drive_dir)

    outputs_dir = os.path.join(drive_dir, "outputs")
    downgraded_dir = os.path.join(drive_dir, "downgraded_outputs")
    tasks_dir = os.path.join(drive_dir, "tasks")
    db_file = os.path.join(drive_dir, "tasks_db.json")

    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(downgraded_dir, exist_ok=True)

    tasks_dict: Dict[str, dict] = {}
    if os.path.isfile(db_file):
        try:
            with open(db_file, "r", encoding="utf-8") as f:
                tasks_dict = json.load(f)
        except Exception:
            tasks_dict = {}

    # Görev ID ve prefix eşleştirme tabloları
    prefix_to_task: Dict[str, dict] = {}
    for tid, t in tasks_dict.items():
        if isinstance(t, dict):
            prefix_to_task[tid[:6]] = t
            prefix_to_task[tid] = t

    def find_task_for_filename(fname: str) -> Optional[dict]:
        for prefix, t in prefix_to_task.items():
            if prefix in fname:
                return t
        return None

    stats = {
        "downgraded_moved": 0,
        "batch_grouped_outputs": 0,
        "batch_grouped_downgraded": 0,
        "restored_outputs": 0,
        "restored_downgraded": 0
    }

    # 1. outputs klasöründeki dosyaları tara
    if os.path.isdir(outputs_dir):
        for root, dirs, files in os.walk(outputs_dir):
            for f in files:
                if not f.lower().endswith((".mp4", ".mkv", ".mov")):
                    continue
                src_path = os.path.join(root, f)
                is_480p = "_480p" in f.lower() or f.lower().endswith("480p.mp4")
                matched_task = find_task_for_filename(f)
                batch_id = matched_task.get("batch_id") if matched_task else None

                # Eğer dosya zaten bir batch alt klasöründeyse klasör adını batch_id kabul et
                rel_dir = os.path.relpath(root, outputs_dir)
                if not batch_id and rel_dir != ".":
                    batch_id = rel_dir.split(os.sep)[0]

                if is_480p:
                    # 480p dosyasını downgraded_outputs klasörüne taşı
                    target_parent = os.path.join(downgraded_dir, batch_id) if batch_id else downgraded_dir
                    os.makedirs(target_parent, exist_ok=True)
                    target_path = os.path.join(target_parent, f)
                    if src_path != target_path:
                        try:
                            shutil.move(src_path, target_path)
                            stats["downgraded_moved"] += 1
                        except Exception:
                            pass
                else:
                    # Normal video, eğer bir batch'e aitse ve kök dizindeyse ilgili batch klasörüne taşı
                    if batch_id and root == outputs_dir:
                        target_parent = os.path.join(outputs_dir, batch_id)
                        os.makedirs(target_parent, exist_ok=True)
                        target_path = os.path.join(target_parent, f)
                        if src_path != target_path:
                            try:
                                shutil.move(src_path, target_path)
                                stats["batch_grouped_outputs"] += 1
                            except Exception:
                                pass

    # 2. downgraded_outputs klasöründeki kök dosyaları batch klasörlerine grupla
    if os.path.isdir(downgraded_dir):
        for f in os.listdir(downgraded_dir):
            src_path = os.path.join(downgraded_dir, f)
            if os.path.isfile(src_path) and f.lower().endswith((".mp4", ".mkv", ".mov")):
                matched_task = find_task_for_filename(f)
                batch_id = matched_task.get("batch_id") if matched_task else None
                if batch_id:
                    target_parent = os.path.join(downgraded_dir, batch_id)
                    os.makedirs(target_parent, exist_ok=True)
                    target_path = os.path.join(target_parent, f)
                    if src_path != target_path:
                        try:
                            shutil.move(src_path, target_path)
                            stats["batch_grouped_downgraded"] += 1
                        except Exception:
                            pass

    # 3. tasks_db.json içindeki bitmiş görevlerin kopyalarını senkronize et
    db_changed = False
    for tid, t in tasks_dict.items():
        if not isinstance(t, dict) or t.get("state") != "completed":
            continue

        subj = t.get("subject", "Ders")
        clean_subj = re.sub(r'[^\w\-_ ]+', '_', subj)[:40].strip()
        batch_id = t.get("batch_id")
        task_dir = os.path.join(tasks_dir, tid)

        # Orijinal/HD Video Kontrolü
        target_out_dir = os.path.join(outputs_dir, batch_id) if batch_id else outputs_dir
        expected_out_name = f"{clean_subj}_{tid[:6]}.mp4"
        expected_out_path = os.path.join(target_out_dir, expected_out_name)

        src_vid = t.get("file_path")
        if not src_vid or not os.path.isfile(src_vid):
            if os.path.isdir(task_dir):
                for f in os.listdir(task_dir):
                    if f.startswith("final_") and f.endswith(".mp4") and "_480p" not in f:
                        src_vid = os.path.join(task_dir, f)
                        t["file_path"] = src_vid
                        db_changed = True
                        break

        if src_vid and os.path.isfile(src_vid) and not os.path.exists(expected_out_path):
            try:
                os.makedirs(target_out_dir, exist_ok=True)
                shutil.copy2(src_vid, expected_out_path)
                stats["restored_outputs"] += 1
            except Exception:
                pass

        # 480p Video Kontrolü
        target_down_dir = os.path.join(downgraded_dir, batch_id) if batch_id else downgraded_dir
        expected_down_name = f"{clean_subj}_{tid[:6]}_480p.mp4"
        expected_down_path = os.path.join(target_down_dir, expected_down_name)

        src_480p = t.get("file_path_480p")
        if not src_480p or not os.path.isfile(src_480p):
            if os.path.isdir(task_dir):
                for f in os.listdir(task_dir):
                    if "_480p" in f and f.endswith(".mp4"):
                        src_480p = os.path.join(task_dir, f)
                        t["file_path_480p"] = src_480p
                        t["video_url_480p"] = f"/tasks/{tid}/{f}"
                        t["file_size_480p_mb"] = round(os.path.getsize(src_480p)/(1024*1024), 2)
                        db_changed = True
                        break

        if src_480p and os.path.isfile(src_480p) and not os.path.exists(expected_down_path):
            try:
                os.makedirs(target_down_dir, exist_ok=True)
                shutil.copy2(src_480p, expected_down_path)
                stats["restored_downgraded"] += 1
            except Exception:
                pass

    if db_changed:
        try:
            with open(db_file, "w", encoding="utf-8") as f:
                json.dump(tasks_dict, f, ensure_ascii=False)
        except Exception:
            pass

    # 4. Boş klasörleri temizle
    for base in (outputs_dir, downgraded_dir):
        if os.path.isdir(base):
            for root, dirs, files in os.walk(base, topdown=False):
                if root != base and not os.listdir(root):
                    try:
                        os.rmdir(root)
                    except Exception:
                        pass

    total_actions = sum(stats.values())
    if total_actions > 0:
        print(f"🧹 Drive Düzenlendi: {stats['downgraded_moved']} adet 480p video 'downgraded_outputs' klasörüne aktarıldı, "
              f"{stats['batch_grouped_outputs'] + stats['batch_grouped_downgraded']} adet toplu görev videosu klasörlendi.")

    return stats


def print_drive_status():
    """Google Drive'daki mevcut görevlerin durumunu ve biten videoları klasör kırılımıyla listeler."""
    import task_store
    tasks = task_store.get_all_tasks()
    storage_dir = task_store.get_storage_dir()
    outputs_dir = os.environ.get("OUTPUTS_DIR", os.path.join(storage_dir, "outputs"))
    downgraded_dir = os.environ.get("DOWNGRADED_OUTPUTS_DIR", os.path.join(storage_dir, "downgraded_outputs"))

    completed = [t for t in tasks if t.get("state") == "completed"]
    queued = [t for t in tasks if t.get("state") == "queued"]
    interrupted = [t for t in tasks if t.get("state") in ("interrupted", "processing")]
    failed = [t for t in tasks if t.get("state") == "failed"]

    print("\n" + "=" * 70)
    print(f"📊 GOOGLE DRIVE GÖREV & KLASÖR DURUM RAPORU")
    print(f"   📁 Ana Konum:    {storage_dir}")
    print(f"   ✅ Tamamlanan:   {len(completed)}")
    print(f"   ⏳ Kuyrukta:     {len(queued)}")
    print(f"   ⏸️ Yarım Kalan:  {len(interrupted)} (Tek tıkla devam ettirilebilir)")
    print(f"   ❌ Hatalı:       {len(failed)}")
    print("-" * 70)

    # outputs klasörünü tara (HD / Orijinal Videolar)
    print("🎬 HD / Orijinal Videolar (outputs/):")
    if os.path.isdir(outputs_dir):
        out_entries = sorted(os.listdir(outputs_dir))
        has_hd = False
        for entry in out_entries:
            ep = os.path.join(outputs_dir, entry)
            if os.path.isdir(ep):
                vids = [f for f in os.listdir(ep) if f.endswith(('.mp4', '.mkv', '.mov'))]
                if vids:
                    has_hd = True
                    total_mb = sum(os.path.getsize(os.path.join(ep, v)) for v in vids) / (1024 * 1024)
                    print(f"   📁 Toplu Görev [{entry}]: {len(vids)} video ({total_mb:.1f} MB)")
                    for v in vids[:3]:
                        print(f"      • {v}")
                    if len(vids) > 3:
                        print(f"      ... ve {len(vids) - 3} video daha")
            elif os.path.isfile(ep) and entry.endswith(('.mp4', '.mkv', '.mov')):
                has_hd = True
                size_mb = os.path.getsize(ep) / (1024 * 1024)
                print(f"   📄 {entry} ({size_mb:.1f} MB)")
        if not has_hd:
            print("   ℹ️ Henüz HD video çıktısı bulunmuyor.")
    else:
        print("   ℹ️ outputs klasörü boş.")

    # downgraded_outputs klasörünü tara (480p Videolar)
    print("\n📱 480p Düşük Boyutlu Videolar (downgraded_outputs/):")
    if os.path.isdir(downgraded_dir):
        down_entries = sorted(os.listdir(downgraded_dir))
        has_480p = False
        for entry in down_entries:
            ep = os.path.join(downgraded_dir, entry)
            if os.path.isdir(ep):
                vids = [f for f in os.listdir(ep) if f.endswith(('.mp4', '.mkv', '.mov'))]
                if vids:
                    has_480p = True
                    total_mb = sum(os.path.getsize(os.path.join(ep, v)) for v in vids) / (1024 * 1024)
                    print(f"   📁 Toplu Görev [{entry}]: {len(vids)} video ({total_mb:.1f} MB)")
                    for v in vids[:3]:
                        print(f"      • {v}")
                    if len(vids) > 3:
                        print(f"      ... ve {len(vids) - 3} video daha")
            elif os.path.isfile(ep) and entry.endswith(('.mp4', '.mkv', '.mov')):
                has_480p = True
                size_mb = os.path.getsize(ep) / (1024 * 1024)
                print(f"   📄 {entry} ({size_mb:.1f} MB)")
        if not has_480p:
            print("   ℹ️ Henüz 480p video çıktısı bulunmuyor.")
    else:
        print("   ℹ️ downgraded_outputs klasörü boş.")

    if interrupted:
        print("\n⏸️ Yarım Kalan / Duraklatılan Görevler:")
        for t in interrupted[:5]:
            print(f"   - [{t.get('task_id')[:8]}] {t.get('subject')}: {t.get('step_text', '')}")

    print("=" * 70 + "\n")


def resume_all_interrupted_tasks() -> int:
    """Yarım kalan tüm görevleri kuyruğa alarak işlemeye hazır hale getirir."""
    import task_store
    count = task_store.resume_interrupted_tasks()
    print(f"🔄 Google Drive'daki {count} adet yarım kalan görev kuyruğa alındı.")
    return count


if __name__ == "__main__":
    init_drive_environment()
    print_drive_status()

