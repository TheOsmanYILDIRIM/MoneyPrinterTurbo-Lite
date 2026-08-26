#!/usr/bin/env python3
"""
MoneyPrinterTurbo Agentic Director CLI (Çok Sahneli Sinematik Sürüm)
- Sahne sahne Pexels thumbnail kürasyonu
- Ayarlanabilir konuşma hızı (voice_rate)
- Çözünürlükten bağımsız standart manifest JSON üretimi
- İsteğe bağlı anında render desteği
"""
import argparse
import asyncio
import os
import shutil
import sys
import json
import re
from typing import List, Dict
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import lite_engine
from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool
from agent.tools.manifest_builder import ManifestBuilderTool


def segment_script_into_scenes(script: str, default_keywords: str = "") -> List[Dict]:
    """Metni noktalama ve anlamsal bloklara göre 3-5 saniyelik sahne parçalarına böler."""
    sentences = [s.strip() for s in re.split(r"[.!?\n]+", script) if len(s.strip()) > 5]
    if not sentences:
        sentences = [script.strip()]

    scenes = []
    for idx, s in enumerate(sentences, 1):
        # Sahneye özel anahtar kelime türet
        words = [w.lower().strip(".,!?:;'\"") for w in s.split() if len(w) > 3]
        scene_kw = f"{default_keywords} {' '.join(words[:3])}".strip()
        scenes.append({
            "title": f"Sahne {idx}",
            "text": s,
            "keywords": scene_kw,
            "duration": max(3.0, min(6.0, len(s.split()) * 0.45))
        })
    return scenes


async def produce_multiscene_manifest(
    title: str,
    script: str,
    keywords: str = "history medieval battlefield",
    highlight_words: str = "",
    voice_name: str = "tr-TR-AhmetNeural",
    voice_rate: float = 1.10,
    voice_volume: float = 1.0,
    resolution: str = "720p",
    aspect: str = "9:16",
    render_now: bool = False,
    output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
) -> str:
    print(f"\n🎬 [Director] Çok Sahneli Sinematik Prodüksiyon: '{title}'")
    print(f"🎙️ [Ayarlar] Ses: {voice_name} | Konuşma Hızı: {voice_rate}x | Çözünürlük: {resolution} ({aspect})")
    os.makedirs(output_dir, exist_ok=True)

    # 1. Sahne Segmentasyonu
    scene_blocks = segment_script_into_scenes(script, keywords)
    print(f"📋 [Senaryo] Metin {len(scene_blocks)} ayrı sahneye ayrıştırıldı.")

    # 2. Pexels Canlı Thumbnail Küratörü & Vision Feedback Loop
    stock_tool = StockSearchTool()
    vision_tool = VisionInspectorTool()
    curated_scenes = []

    for sc_idx, sc in enumerate(scene_blocks, 1):
        print(f"\n🔍 [Sahne {sc_idx}/{len(scene_blocks)}] '{sc['text'][:40]}...' için görsel aranıyor...")
        best_visual, logs = vision_tool.curate_best_visual(
            scene_text=sc["text"],
            initial_keywords=sc["keywords"],
            search_tool=stock_tool,
            max_retries=2
        )
        print(f"   -> Seçilen Video ID: {best_visual.get('video_id')}")
        print(f"   -> Başlık: '{best_visual.get('video_title')}'")
        if logs:
            print(f"   -> Skor: {logs[0]['score']}/10")

        curated_scenes.append({
            "title": sc["title"],
            "text": sc["text"],
            "duration": sc["duration"],
            "keywords": sc["keywords"],
            "provider": best_visual.get("provider", "pexels"),
            "video_id": best_visual.get("video_id"),
            "video_title": best_visual.get("video_title"),
            "thumbnail_url": best_visual.get("thumbnail_url"),
            "curation_score": logs[0]["score"] if logs else 8.5
        })

    # 3. Vurgu Kelimelerini Belirle
    hl_list = [w.strip() for w in highlight_words.split(",") if w.strip()]
    if not hl_list:
        hl_list = [w.strip(".,!?;:") for w in script.split() if w[0].isupper() and len(w) > 3][:8]

    # 4. Manifest JSON Derle
    manifest_tool = ManifestBuilderTool(output_dir=output_dir)
    manifest = manifest_tool.build_manifest(
        title=title,
        script=script,
        scenes=curated_scenes,
        voice_name=voice_name,
        voice_rate=voice_rate,
        voice_volume=voice_volume,
        highlight_words=hl_list,
        target_resolution=resolution,
        aspect_ratio=aspect,
        transition="crossfade",
        transition_dur=0.4
    )

    manifest_path = manifest["_file_path"]
    print(f"\n✅ [Manifest Hazır] Reçete Dosyası: {manifest_path}")

    # 5. İsteğe Bağlı Anında Render
    if render_now:
        print("\n🚀 [Render] MoneyPrinterTurbo Lite motoru ile render başlatılıyor...")
        out_video = lite_engine.render_from_manifest(manifest_path, target_resolution=resolution)
        if out_video:
            print(f"🎉 [Tamamlandı] Nihai Video: {out_video}\n")
            shutil.copy2(out_video, os.path.join("/sdcard/Documents/MoneyPrinterTurbo_Samples", os.path.basename(out_video)))

    return manifest_path


def main():
    parser = argparse.ArgumentParser(description="MoneyPrinterTurbo Agentic Director (Çok Sahneli Sinematik)")
    parser.add_argument("--title", type=str, default="Malazgirt Zaferi", help="Video Başlığı")
    parser.add_argument("--script", type=str, default="26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu Turan taktiği ile Bizans'ı mağlup etti. Bu zaferle Anadolu kapıları açıldı.", help="Metin")
    parser.add_argument("--keywords", type=str, default="medieval battlefield horses soldiers", help="Arama Terimleri")
    parser.add_argument("--highlight", type=str, default="", help="Vurgulanacak Kelimeler (virgülle ayırın)")
    parser.add_argument("--voice", type=str, default="tr-TR-AhmetNeural", help="Seslendirmen")
    parser.add_argument("--voice_rate", type=float, default=1.15, help="Konusma Hizi Carpani (1.0 = normal, 1.15 = 15 hizli, 1.25 = 25 hizli)")
    parser.add_argument("--resolution", type=str, default="720p", help="Cozunurluk (480p, 720p, 1080p)")
    parser.add_argument("--aspect", type=str, default="9:16", help="Format (9:16, 16:9)")
    parser.add_argument("--render", action="store_true", help="Manifest oluşturulduktan sonra hemen render et")

    args = parser.parse_args()
    asyncio.run(produce_multiscene_manifest(
        title=args.title,
        script=args.script,
        keywords=args.keywords,
        highlight_words=args.highlight,
        voice_name=args.voice,
        voice_rate=args.voice_rate,
        resolution=args.resolution,
        aspect=args.aspect,
        render_now=args.render
    ))


if __name__ == "__main__":
    main()
