import unittest
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from agent.tools.manifest_builder import ManifestBuilderTool


class TestManifestBuilder(unittest.TestCase):

    def setUp(self):
        self.sample_dir = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
        self.builder = ManifestBuilderTool(output_dir=self.sample_dir)

    def test_build_manifest(self):
        """Manifest dosyasının doğru şema ile oluşturulduğunu doğrular."""
        scenes = [
            {
                "start_time": 0.0,
                "end_time": 4.0,
                "duration": 4.0,
                "text": "Üslü sayılarda kural çok basittir.",
                "provider": "pexels",
                "video_id": "test_101",
                "thumbnail_url": "https://img.pexels.com/101.jpg",
                "curation_score": 8.8,
                "overlay_diagram": {
                    "type": "formula_card",
                    "file": "test_formula_card.png",
                    "position": "center"
                }
            }
        ]
        audio_info = {
            "audio_file": "samples/test_voice.mp3",
            "voice": "tr-TR-AhmetNeural",
            "total_duration": 4.0,
            "srt_file": "samples/test.srt"
        }
        manifest = self.builder.build_manifest(
            title="Üslü Sayılar Dersi",
            script="Üslü sayılarda kural çok basittir.",
            scenes=scenes,
            audio_info=audio_info,
            target_resolution="480p"  # Düşük çözünürlük testi
        )
        self.assertEqual(manifest["target_resolution"], "480p")
        self.assertEqual(len(manifest["timeline"]), 1)
        self.assertTrue(os.path.exists(manifest["_file_path"]))


if __name__ == "__main__":
    unittest.main()
