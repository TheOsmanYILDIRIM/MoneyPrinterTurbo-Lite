#!/usr/bin/env python3
"""
Google Colab / Kaggle Cloud GPU Worker
Google Drive 'Input_Queue' klasörünü izler, yeni gelen manifest JSON'larını
T4/A100 GPU hızlandırmasıyla 1080p/4K videolara derleyip 'Output_Videos' klasörüne yükler.
"""
import json
import os
import shutil
import sys
import time
from loguru import logger

# Ana proje dizinini ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import lite_engine
import settings_manager


def run_cloud_worker(drive_base_dir: str, target_resolution: str = "1080p", poll_interval: int = 5, run_once: bool = False):
    input_dir = os.path.join(drive_base_dir, "Input_Queue")
    proc_dir = os.path.join(drive_base_dir, "Processing")
    output_dir = os.path.join(drive_base_dir, "Output_Videos")
    done_dir = os.path.join(drive_base_dir, "Completed_Manifests")

    for d in [input_dir, proc_dir, output_dir, done_dir]:
        os.makedirs(d, exist_ok=True)

    print(f"🚀 [Colab/Kaggle GPU Worker] Başlatıldı!")
    print(f"📂 İzlenen Drive Dizini: {drive_base_dir}")
    print(f"⚡ GPU Hızlandırma: {lite_engine.get_video_encoder_config()['name']} | Çözünürlük: {target_resolution}")

    while True:
        manifest_files = [f for f in os.listdir(input_dir) if f.endswith(".json")]
        if not manifest_files:
            if run_once:
                print("Kuyrukta bekleyen iş yok.")
                break
            time.sleep(poll_interval)
            continue

        for mf in sorted(manifest_files):
            in_path = os.path.join(input_dir, mf)
            proc_path = os.path.join(proc_dir, mf)

            try:
                # 1. İşleniyor durumuna taşı
                shutil.move(in_path, proc_path)
                with open(proc_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)

                title = manifest.get("title", "Video").replace(" ", "_")
                pid = manifest.get("project_id", "proj")
                out_filename = f"{title}_{pid}_{target_resolution}.mp4"
                final_out = os.path.join(output_dir, out_filename)

                print(f"\n🎬 [İşleniyor] '{title}' ({pid}) -> {target_resolution} GPU Render...")

                # 2. GPU ile Render Et
                res_path = lite_engine.render_from_manifest(
                    manifest_data=proc_path,
                    output_path=final_out,
                    target_resolution=target_resolution
                )

                if res_path and os.path.exists(res_path):
                    size_mb = os.path.getsize(res_path) / (1024 * 1024)
                    print(f"✅ [Tamamlandı] {out_filename} ({size_mb:.2f} MB)")
                    # 3. Arşive taşı
                    shutil.move(proc_path, os.path.join(done_dir, mf))
                else:
                    print(f"❌ [Hata] Render başarısız oldu: {mf}")

            except Exception as e:
                logger.exception(f"Worker işlem hatası: {e}")

        if run_once:
            break


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="MoneyPrinterTurbo Cloud GPU Queue Worker")
    parser.add_argument("--drive_dir", type=str, default="/sdcard/Documents/MoneyPrinterTurbo_DriveQueue", help="Google Drive veya Yerel Kuyruk Dizini")
    parser.add_argument("--resolution", type=str, default="1080p", help="Çıktı Çözünürlüğü (720p, 1080p, 4k)")
    parser.add_argument("--once", action="store_true", help="Kuyruktaki işleri bir kez işleyip çık")
    args = parser.parse_args()

    run_cloud_worker(args.drive_dir, target_resolution=args.resolution, run_once=args.once)
