import json
import os
import shutil
import time
from typing import Dict, List, Optional
from loguru import logger


class DriveQueueManager:
    """
    Termux ile Google Colab / Kaggle arasında sıfır-dokunuşla çalışan
    Google Drive Kuyruk Yöneticisi (Cloud Queue Manager).
    """

    def __init__(self, base_drive_dir: Optional[str] = None):
        # Varsayılan olarak SD kart altındaki paylaşımlı Google Drive klasörü veya Samples dizini
        self.base_dir = base_drive_dir or os.environ.get(
            "MPT_DRIVE_DIR",
            "/sdcard/Documents/MoneyPrinterTurbo_DriveQueue"
        )
        self.input_queue_dir = os.path.join(self.base_dir, "Input_Queue")
        self.processing_dir = os.path.join(self.base_dir, "Processing")
        self.output_videos_dir = os.path.join(self.base_dir, "Output_Videos")
        self.completed_manifests_dir = os.path.join(self.base_dir, "Completed_Manifests")

        for d in [self.input_queue_dir, self.processing_dir, self.output_videos_dir, self.completed_manifests_dir]:
            os.makedirs(d, exist_ok=True)

    def submit_manifest_to_queue(self, manifest_path: str) -> str:
        """Telefonda hazırlanan JSON reçetesini Drive kuyruğuna gönderir."""
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Manifest bulunamadı: {manifest_path}")

        filename = os.path.basename(manifest_path)
        dest_path = os.path.join(self.input_queue_dir, filename)
        shutil.copy2(manifest_path, dest_path)
        logger.info(f"📤 Manifest Drive Kuyruğuna Eklendi: {dest_path}")
        return dest_path

    def check_queue_status(self) -> Dict[str, List[str]]:
        """Kuyruktaki, işlenen ve tamamlanan video durumlarını listeler."""
        return {
            "pending": os.listdir(self.input_queue_dir) if os.path.exists(self.input_queue_dir) else [],
            "processing": os.listdir(self.processing_dir) if os.path.exists(self.processing_dir) else [],
            "completed_videos": os.listdir(self.output_videos_dir) if os.path.exists(self.output_videos_dir) else []
        }
