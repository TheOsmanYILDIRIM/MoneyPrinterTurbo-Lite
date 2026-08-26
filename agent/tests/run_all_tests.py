import os
import sys
import unittest
import json
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from agent.tools.diagram_generator import DiagramGenerator
from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool
from agent.tools.manifest_builder import ManifestBuilderTool


def run_full_pipeline_verification():
    print("================================================================")
    print("🔬 AGENTIC PIPELINE & QUALITY VERIFICATION SUITE")
    print("================================================================")

    sample_dir = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
    os.makedirs(sample_dir, exist_ok=True)

    # 1. Aşama: Şema Üretimi ve İzole Değerlendirme
    print("\n[1/4] 📐 Şema Üretimi ve İzole Kalite Değerlendirmesi...")
    diagram_gen = DiagramGenerator(output_dir=sample_dir)
    card_path = diagram_gen.create_formula_card(
        title="Temel Matematik Özdeşliği",
        formula="(a + b)² = a² + 2ab + b²",
        explanation="Birinci ile ikincinin çarpımının iki katı eklenir.",
        filename="sample_verified_formula.png"
    )
    eval_card = DiagramGenerator.evaluate_diagram(card_path)
    print(f"  -> Dosya: {card_path}")
    print(f"  -> Şema Kalite Skoru: {eval_card['score']}/10 (Geçti: {eval_card['passed']})")
    print(f"  -> Şeffaflık/Dolu Alan Oranı: %{int(eval_card['opaque_ratio']*100)}")

    # 2. Aşama: Hafif Thumbnail Arama & Vision Feedback Loop
    print("\n[2/4] 👁️ Thumbnail Arama & Çok Modlu Vision Feedback Loop...")
    stock_tool = StockSearchTool()
    vision_tool = VisionInspectorTool()
    best_visual, logs = vision_tool.curate_best_visual(
        scene_text="Tam kare açılımında terimlerin kareleri ve çarpımlarının iki katı toplanır.",
        initial_keywords="blackboard math algebra formula",
        search_tool=stock_tool,
        max_retries=2
    )
    print(f"  -> Seçilen Video ID: {best_visual.get('video_id')}")
    print(f"  -> Yapılan Deneme Sayısı: {len(logs)}")
    for log in logs:
        print(f"     [Döngü {log['attempt']}] Terim: '{log['query']}' | Puan: {log['score']}/10 | Sebep: {log['reasoning']}")

    # 3. Aşama: Manifest Derleme (480p Tasarruflu Mod)
    print("\n[3/4] 📦 Production Manifest Oluşturma (480p Test Modu)...")
    manifest_tool = ManifestBuilderTool(output_dir=sample_dir)
    scenes = [
        {
            "start_time": 0.0,
            "end_time": 4.5,
            "duration": 4.5,
            "text": "Tam kare açılımında terimlerin kareleri ve çarpımlarının iki katı toplanır.",
            "provider": best_visual.get("provider", "pexels"),
            "video_id": best_visual.get("video_id"),
            "thumbnail_url": best_visual.get("thumbnail_url"),
            "curation_score": logs[0]["score"] if logs else 8.5,
            "overlay_diagram": {
                "type": "formula_card",
                "file": "sample_verified_formula.png",
                "position": "center",
                "animation": "fade_in"
            }
        }
    ]
    audio_info = {
        "audio_file": "samples/sample_voice.mp3",
        "voice": "tr-TR-AhmetNeural",
        "total_duration": 4.5,
        "srt_file": "samples/sample.srt"
    }
    manifest = manifest_tool.build_manifest(
        title="Tam Kare Özdeşliği Dersi",
        script="Tam kare açılımında terimlerin kareleri ve çarpımlarının iki katı toplanır.",
        scenes=scenes,
        audio_info=audio_info,
        target_resolution="480p",
        project_id="test_verification_run"
    )
    print(f"  -> Manifest Kaydedildi: {manifest['_file_path']}")

    # 4. Aşama: Standart Unit Testleri Çalıştır
    print("\n[4/4] 🧪 Standart Birim Testlerini Çalıştırma (PyTest / Unittest)...")
    loader = unittest.TestLoader()
    suite = loader.discover(os.path.dirname(__file__), pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n================================================================")
    if result.wasSuccessful() and eval_card["passed"]:
        print("✅ TÜM AŞAMALAR VE İZOLE DEĞERLENDİRMELER BAŞARIYLA GEÇTİ!")
    else:
        print("❌ BAZI TESTLER VEYA KALİTE KAPILARI BAŞARISIZ OLDU!")
    print("================================================================")


if __name__ == "__main__":
    run_full_pipeline_verification()
