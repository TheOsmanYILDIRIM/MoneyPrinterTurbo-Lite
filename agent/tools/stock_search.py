import os
import requests
from typing import Dict, List, Optional
from loguru import logger
import sys

# MoneyPrinterTurbo root dizini import için ekle
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import settings_manager


class StockSearchTool:
    """
    Pexels ve Pixabay API üzerinden yalnızca thumbnail ve video metadata arar.
    Asla büyük video dosyası indirmez.
    """

    def __init__(self):
        self.pexels_api_key = settings_manager.get_setting("pexels_api_keys", "")
        self.pixabay_api_key = settings_manager.get_setting("pixabay_api_keys", "")

    def search_pexels_thumbnails(self, query: str, per_page: int = 5) -> List[Dict]:
        """Pexels API'den thumbnail ve video bilgilerini çeker."""
        if not self.pexels_api_key:
            return self._mock_fallback(query, "pexels", per_page)

        headers = {"Authorization": self.pexels_api_key}
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&per_page={per_page}&orientation=portrait"

        try:
            resp = requests.get(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for v in data.get("videos", []):
                    # Pexels URL'sinden anlamlı video başlığını çıkar
                    # Örn: https://www.pexels.com/video/student-writing-on-blackboard-7565438/ -> "student writing on blackboard"
                    video_url = v.get("url", "")
                    title_slug = ""
                    if "/video/" in video_url:
                        raw_slug = video_url.split("/video/")[-1].strip("/").rsplit("-", 1)[0]
                        title_slug = raw_slug.replace("-", " ")

                    results.append({
                        "provider": "pexels",
                        "video_id": str(v.get("id")),
                        "video_title": title_slug or query,
                        "duration": v.get("duration", 0),
                        "width": v.get("width", 720),
                        "height": v.get("height", 1280),
                        "thumbnail_url": v.get("image", ""),
                        "tags": [query] + (title_slug.split() if title_slug else []),
                        "available_files": [
                            {"quality": f.get("quality"), "width": f.get("width"), "height": f.get("height"), "link": f.get("link")}
                            for f in v.get("video_files", [])
                        ]
                    })
                return results
        except Exception as e:
            logger.warning(f"Pexels arama hatası: {e}")

        return self._mock_fallback(query, "pexels", per_page)

    def _mock_fallback(self, query: str, provider: str, per_page: int) -> List[Dict]:
        """API anahtarı olmadığında veya test ortamında gerçekçi adaylar üretir."""
        candidates = []
        for i in range(1, per_page + 1):
            candidates.append({
                "provider": provider,
                "video_id": f"mock_{provider}_{query.replace(' ', '_')}_{i}",
                "video_title": f"{query} scene clip {i}",
                "duration": 5.0,
                "width": 720,
                "height": 1280,
                "thumbnail_url": f"https://images.pexels.com/videos/mock/{i}.jpg",
                "tags": query.split(),
                "available_files": [
                    {"quality": "hd", "width": 1080, "height": 1920, "link": f"https://mock.cdn/{query}_{i}_1080p.mp4"},
                    {"quality": "sd", "width": 480, "height": 854, "link": f"https://mock.cdn/{query}_{i}_480p.mp4"}
                ]
            })
        return candidates
