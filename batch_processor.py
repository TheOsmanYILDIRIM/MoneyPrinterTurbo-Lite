#!/usr/bin/env python3
"""
MoneyPrinter Turbo - Google Colab Headless Batch Processor
Web arayüzüne ihtiyaç duymadan Google Drive'daki ders metinlerini okur,
kuyruğa ekler ve arka planda/ön planda sırayla render ederek Drive'a kaydeder.
Colab koptuğunda veya durdurulduğunda tekrar çalıştırıldığında kaldığı yerden devam eder!
"""

import os
import sys
import glob
import time
import argparse
from loguru import logger

import drive_sync
import task_store
import batch_engine
import worker
import settings_manager


def run_batch_pipeline(input_path: str = None, auto_resume: bool = True, wait_completion: bool = True):
    drive_info = drive_sync.init_drive_environment()
    batch_dir = drive_info["batch_inputs_dir"]

    # 1. Yarım kalan görevleri kontrol et ve devam ettir
    if auto_resume:
        resumed = task_store.resume_interrupted_tasks()
        if resumed > 0:
            print(f"🔄 Önceki oturumdan kalan {resumed} adet görev devam ettiriliyor...")

    # 2. Eğer yeni bir dosya veya klasör belirtilmişse kuyruğa ekle
    target_input = input_path or batch_dir
    if os.path.exists(target_input):
        txt_files = glob.glob(os.path.join(target_input, "*.txt")) + glob.glob(os.path.join(target_input, "*.md")) if os.path.isdir(target_input) else [target_input]
        new_items = []
        for tf in txt_files:
            # Örnek dosyayı atla veya kullan
            items = batch_engine.parse_batch_input(tf)
            if items:
                new_items.extend(items)
        
        if new_items:
            # Mevcut görevlerle mükerrer kontrolü (script veya subject eşleşmesi)
            existing_tasks = task_store.get_all_tasks()
            existing_subjects = {t.get("subject", "").strip().lower() for t in existing_tasks}
            
            to_queue = []
            for item in new_items:
                subj = (item.get("subject") or "").strip().lower()
                # Eğer daha önce tamamlanmış veya kuyrukta ise atla
                if subj not in existing_subjects:
                    to_queue.append(item)
                else:
                    logger.debug(f"Zaten mevcut, atlanıyor: {item.get('subject')}")

            if to_queue:
                print(f"📥 {len(to_queue)} yeni ders görevi Google Drive kuyruğuna ekleniyor...")
                s = settings_manager.load_settings()
                batch_engine.create_batch_tasks(
                    items=to_queue,
                    voice=s.get("prod_voice", "tr-TR-AhmetNeural"),
                    aspect=s.get("prod_aspect", "9:16"),
                    resolution=s.get("prod_resolution", "720p"),
                    save_480p=s.get("prod_save_480p", False),
                    bg_style=s.get("prod_bg_style", "chalkboard"),
                    subtitle_enabled=s.get("prod_subtitle_enabled", True),
                    sub_color=s.get("prod_sub_color", "#FFFFFF"),
                    sub_pos=s.get("prod_sub_pos", "bottom"),
                    sub_size=s.get("prod_sub_size", 18),
                    sub_box=s.get("prod_sub_box", False),
                    sub_bold=s.get("prod_sub_bold", True),
                    sub_font=s.get("prod_sub_font", "Roboto"),
                    outline_color=s.get("prod_outline_color", "#000000"),
                    highlight_color=s.get("prod_highlight_color", "#FFD700"),
                    bgm_mode=s.get("prod_bgm_mode", "none"),
                    transition=s.get("prod_transition", "none"),
                    transition_dur=float(s.get("prod_transition_dur", 0.5))
                )
            else:
                print("ℹ️ Eklenecek yeni ders bulunamadı (Tüm dersler daha önce işlenmiş veya kuyrukta).")

    # 3. Worker'ı başlat
    worker.start_worker(auto_resume=True)

    if not wait_completion:
        print("🚀 Worker arka planda başlatıldı.")
        return

    # 4. İlerlemeyi canlı olarak ekrana bas
    print("\n🎬 Video Üretim Kuyruğu İşleniyor (Durdurmak için Ctrl+C)...")
    last_status_time = 0
    try:
        while True:
            tasks = task_store.get_all_tasks()
            active = [t for t in tasks if t.get("state") in ("queued", "processing")]
            if not active:
                print("\n🎉 Tebrikler! Kuyruktaki tüm görevler başarıyla tamamlandı.")
                drive_sync.print_drive_status()
                break

            current_tid = worker.current_task_id()
            if current_tid:
                cur = task_store.get_task(current_tid)
                if cur:
                    subj = cur.get("subject", "Ders")
                    prog = cur.get("progress", 0)
                    step = cur.get("step_text", "")
                    sys.stdout.write(f"\r⏳ [{prog}%] {subj[:30]} -> {step[:45]:<45}")
                    sys.stdout.flush()

            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\n⏸️ Kullanıcı tarafından durduruldu. Görevler Google Drive'da güvenle saklandı.")
        print("💡 Yeniden çalıştırdığınızda otomatik olarak kaldığı yerden devam edecektir.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MoneyPrinter Turbo Colab Headless Batch Processor")
    parser.add_argument("--input", "-i", default=None, help="Toplu derslerin bulunduğu metin dosyası veya klasör")
    parser.add_argument("--no-wait", action="store_true", help="Kuyruğa ekleyip arka planda çalışmaya bırak")
    args = parser.parse_args()

    run_batch_pipeline(input_path=args.input, wait_completion=not args.no_wait)
