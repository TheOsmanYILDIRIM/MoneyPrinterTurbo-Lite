import asyncio
import os
import shutil
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import lite_engine
from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool, DynamicSceneIntentAnalyzer
from agent.tools.manifest_builder import ManifestBuilderTool

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples/geography_test"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


def run_geography_production_test():
    print("🌍 [Coğrafya Prodüksiyon Testi] Dinamik Senaryo ve Sahne Analizi Başlatılıyor...")

    topic = "KPSS Coğrafya: Pamukkale Travertenleri ve Karstik Şekiller"
    scenes_script = [
        {
            "id": 1,
            "title": "Pamukkale Travertenleri",
            "text": "Denizli'de bulunan Pamukkale travertenleri, kalsiyum bikarbonatlı termal suların çökelmesiyle oluşan karstik bir birikim şeklidir.",
            "duration": 4.5
        },
        {
            "id": 2,
            "title": "Karstik Kanyonlar & Mağaralar",
            "text": "Akdeniz'in kalkerli arazilerinde yer altı sularının aşındırmasıyla derin kanyon vadiler ve sarkıtlı mağaralar meydana gelir.",
            "duration": 4.2
        },
        {
            "id": 3,
            "title": "Doğal Zenginlik & Jeotermal",
            "text": "Bu karstik kaynaklar, zengin mineralli sularıyla Türkiye'nin en değerli doğal mirasları arasında yer alır.",
            "duration": 4.0
        }
    ]

    stock_tool = StockSearchTool()
    vision_tool = VisionInspectorTool()

    curated_scenes = []
    print("\n🔍 Sahne Sahne Dinamik Görsel Analiz ve Pexels Taraması:")

    for sc in scenes_script:
        intent = DynamicSceneIntentAnalyzer.analyze_scene_intent(sc["text"], topic)
        print(f"\n📌 [Sahne {sc['id']}: {sc['title']}]")
        print(f"   -> Metin: '{sc['text']}'")
        print(f"   -> Dinamik Pozitif Hedefler: {intent['positive_targets']}")
        print(f"   -> Otomatik Arama Terimi: '{intent['search_query']}'")

        best_visual, logs = vision_tool.curate_best_visual(
            scene_text=sc["text"],
            topic_context=topic,
            search_tool=stock_tool,
            max_retries=2
        )

        print(f"   ✅ [Seçilen Video ID]: {best_visual.get('video_id')}")
        print(f"   -> Başlık: '{best_visual.get('video_title')}'")
        if logs:
            print(f"   -> {logs[0]['reasoning']}")

        curated_scenes.append({
            "title": sc["title"],
            "text": sc["text"],
            "duration": sc["duration"],
            "keywords": intent["search_query"],
            "provider": "pexels",
            "video_id": best_visual.get("video_id"),
            "video_title": best_visual.get("video_title"),
            "thumbnail_url": best_visual.get("thumbnail_url"),
            "curation_score": logs[0]["score"] if logs else 8.5
        })

    # Manifest oluştur
    full_script = " ".join([s["text"] for s in scenes_script])
    manifest_tool = ManifestBuilderTool(output_dir=SAMPLE_DIR)
    manifest = manifest_tool.build_manifest(
        title="KPSS Coğrafya - Pamukkale ve Karstik Şekiller",
        script=full_script,
        scenes=curated_scenes,
        voice_name="tr-TR-AhmetNeural",
        voice_rate=1.15,
        highlight_words=["Pamukkale", "travertenleri", "karstik", "kalkerli", "kanyon", "mineralli", "Akdeniz"],
        target_resolution="480p",
        aspect_ratio="9:16",
        project_id="kpss_cografya_karstik"
    )

    manifest_file = manifest["_file_path"]
    print(f"\n📄 [Manifest Hazır]: {manifest_file}")

    # Render Et
    print("🚀 [Render] 480p Coğrafya Videosu Derleniyor...")
    out_video = os.path.join(SAMPLE_DIR, "10_kpss_cografya_karstik_sekiller_480p.mp4")
    res = lite_engine.render_from_manifest(
        manifest_data=manifest_file,
        output_path=out_video,
        target_resolution="480p",
        work_dir=SAMPLE_DIR
    )

    if res and os.path.exists(res):
        dest = os.path.join(SHARED_DIR, "10_kpss_cografya_karstik_sekiller_480p.mp4")
        shutil.copy2(res, dest)
        size_kb = os.path.getsize(res) // 1024
        print(f"\n🎉 [BAŞARILI] Coğrafya Dersi Videosu Tamamlandı: {dest} ({size_kb} KB)")
        return dest
    else:
        print("❌ Render başarısız!")
        return None


if __name__ == "__main__":
    run_geography_production_test()
