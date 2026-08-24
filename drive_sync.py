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
    uploads_dir = os.path.join(drive_dir, "uploads")
    batch_inputs_dir = os.path.join(drive_dir, "batch_inputs")
    settings_file = os.path.join(drive_dir, "settings.json")
    tasks_db_file = os.path.join(drive_dir, "tasks_db.json")

    # Klasörleri oluştur
    os.makedirs(drive_dir, exist_ok=True)
    os.makedirs(tasks_dir, exist_ok=True)
    os.makedirs(outputs_dir, exist_ok=True)
    os.makedirs(uploads_dir, exist_ok=True)
    os.makedirs(batch_inputs_dir, exist_ok=True)

    # Ortam değişkenlerini ata
    os.environ["STORAGE_DIR"] = drive_dir
    os.environ["TASKS_DIR"] = tasks_dir
    os.environ["OUTPUTS_DIR"] = outputs_dir
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

    print("=" * 65)
    print("✅ GOOGLE DRIVE ENTEGRASYONU TAMAMLANDI!")
    print(f"📁 Ana Drive Klasörü:   {drive_dir}")
    print(f"⚙️ Ayarlar & API Keys:  {settings_file}")
    print(f"📋 Görevler Veritabanı: {tasks_db_file}")
    print(f"🎬 Biten Videolar:      {outputs_dir}")
    print(f"📝 Toplu Ders Girişi:   {batch_inputs_dir}")
    print("=" * 65)

    return {
        "drive_dir": drive_dir,
        "tasks_dir": tasks_dir,
        "outputs_dir": outputs_dir,
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


def print_drive_status():
    """Google Drive'daki mevcut görevlerin durumunu ve biten videoları listeler."""
    import task_store
    tasks = task_store.get_all_tasks()
    if not tasks:
        print("ℹ️ Google Drive üzerinde henüz kayıtlı bir görev bulunmuyor.")
        return

    completed = [t for t in tasks if t.get("state") == "completed"]
    queued = [t for t in tasks if t.get("state") == "queued"]
    interrupted = [t for t in tasks if t.get("state") in ("interrupted", "processing")]
    failed = [t for t in tasks if t.get("state") == "failed"]

    print("\n" + "=" * 65)
    print(f"📊 GOOGLE DRIVE GÖREV DURUM RAPORU (Toplam: {len(tasks)})")
    print(f"   ✅ Tamamlanan:   {len(completed)}")
    print(f"   ⏳ Kuyrukta:     {len(queued)}")
    print(f"   ⏸️ Yarım Kalan:  {len(interrupted)} (Tek tıkla devam ettirilebilir)")
    print(f"   ❌ Hatalı:       {len(failed)}")
    print("-" * 65)

    if completed:
        print("🎬 Tamamlanan ve Drive'da Hazır Videolar:")
        for idx, t in enumerate(completed[:15], 1):
            subj = t.get("subject", "İsimsiz Ders")
            size = t.get("file_size_mb") or 0.0
            dt = t.get("created_at_str") or ""
            print(f"   {idx}. {subj} ({size} MB) - {dt}")
        if len(completed) > 15:
            print(f"   ... ve {len(completed) - 15} adet daha video outputs klasöründe mevcut.")

    if interrupted:
        print("\n⏸️ Yarım Kalan / Duraklatılan Görevler:")
        for t in interrupted[:5]:
            print(f"   - [{t.get('task_id')[:8]}] {t.get('subject')}: {t.get('step_text', '')}")

    print("=" * 65 + "\n")


def resume_all_interrupted_tasks() -> int:
    """Yarım kalan tüm görevleri kuyruğa alarak işlemeye hazır hale getirir."""
    import task_store
    count = task_store.resume_interrupted_tasks()
    print(f"🔄 Google Drive'daki {count} adet yarım kalan görev kuyruğa alındı.")
    return count


if __name__ == "__main__":
    init_drive_environment()
    print_drive_status()
