import json
import os
import uuid
from typing import Dict, List, Optional


class ManifestBuilderTool:
    """
    Çok sahneli (Multi-Scene), ayarlanabilir konuşma hızlı,
    tam ekran sinematik Production Manifest (reçete) derleyicisi.
    """

    def __init__(self, output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def build_manifest(
        self,
        title: str,
        script: str,
        scenes: List[Dict],
        voice_name: str = "tr-TR-AhmetNeural",
        voice_rate: float = 1.10,
        voice_volume: float = 1.0,
        highlight_words: Optional[List[str]] = None,
        target_resolution: str = "720p",
        aspect_ratio: str = "9:16",
        transition: str = "crossfade",
        transition_dur: float = 0.4,
        project_id: Optional[str] = None
    ) -> Dict:
        """Deterministik, çok sahneli sinematik JSON reçetesi oluşturur."""
        pid = project_id or f"proj_{uuid.uuid4().hex[:8]}"

        total_duration = sum(sc.get("duration", 4.0) for sc in scenes)

        manifest = {
            "version": "2.0-multiscene-cinematic",
            "project_id": pid,
            "title": title,
            "aspect_ratio": aspect_ratio,
            "target_resolution": target_resolution,
            "transition": transition,
            "transition_duration": transition_dur,
            "full_script": script,
            "audio": {
                "voice_name": voice_name,
                "voice_rate": voice_rate,
                "voice_volume": voice_volume,
                "total_duration": total_duration,
                "bgm": {
                    "enabled": True,
                    "type": "ambient_cinematic",
                    "volume": 0.15
                }
            },
            "subtitles": {
                "enabled": True,
                "style": "kinetic_highlight",
                "font_name": "Roboto",
                "font_size": 24,
                "sub_color": "#FFFFFF",
                "highlight_color": "#FBBF24",
                "highlight_words": highlight_words or [],
                "position": "bottom",
                "outline_width": 3,
                "outline_color": "#000000"
            },
            "timeline": []
        }

        current_time = 0.0
        for idx, sc in enumerate(scenes):
            dur = sc.get("duration", 4.0)
            scene_item = {
                "scene_index": idx + 1,
                "scene_title": sc.get("title", f"Sahne {idx+1}"),
                "start_time": round(current_time, 2),
                "end_time": round(current_time + dur, 2),
                "duration": round(dur, 2),
                "text": sc.get("text", ""),
                "search_keywords": sc.get("keywords", ""),
                "visual_source": {
                    "provider": sc.get("provider", "pexels"),
                    "video_id": sc.get("video_id"),
                    "video_title": sc.get("video_title", ""),
                    "thumbnail_url": sc.get("thumbnail_url", ""),
                    "curation_score": sc.get("curation_score", 8.5),
                    "download_url": sc.get("download_url")
                }
            }
            manifest["timeline"].append(scene_item)
            current_time += dur

        manifest["audio"]["total_duration"] = round(current_time, 2)

        out_path = os.path.join(self.output_dir, f"{pid}_manifest.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)

        manifest["_file_path"] = out_path
        return manifest
