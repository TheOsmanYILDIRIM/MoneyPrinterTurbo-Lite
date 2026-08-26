import asyncio
import os
import shutil
import subprocess
import requests
import edge_tts
from loguru import logger
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import settings_manager
import lite_engine
from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool
from agent.tools.manifest_builder import ManifestBuilderTool

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


async def generate_full_voice_and_cues():
    full_script = (
        "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu, "
        "uyguladığı Turan taktiği ile Bizans ordusunu kıskaca alarak bozguna uğrattı. "
        "Ve bu tarihi zaferle, Anadolu'nun kapıları Türklere tamamen açıldı."
    )
    voice_path = os.path.join(SAMPLE_DIR, "malazgirt_multiscene_voice.mp3")
    _, cues = await lite_engine.generate_speech_edge(full_script, voice_path, voice="tr-TR-AhmetNeural", rate=1.05)
    total_dur = lite_engine.get_audio_duration(voice_path)
    return full_script, voice_path, cues, total_dur


def curate_and_download_3_scenes():
    stock_tool = StockSearchTool()
    vision_tool = VisionInspectorTool()

    scenes_plan = [
        {
            "id": 1,
            "title": "Süvari Hücumu",
            "text": "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu,",
            "keywords": "running horses galloping dust cavalry",
            "duration": 3.8
        },
        {
            "id": 2,
            "title": "Turan Taktiği & Çarpışma",
            "text": "uyguladığı Turan taktiği ile Bizans ordusunu kıskaca alarak bozguna uğrattı.",
            "keywords": "medieval sword combat warrior armor fight",
            "duration": 4.0
        },
        {
            "id": 3,
            "title": "Zafer & Anadolu Kapıları",
            "text": "Ve bu tarihi zaferle, Anadolu'nun kapıları Türklere tamamen açıldı.",
            "keywords": "ancient castle fortress sunrise landscape epic mountains",
            "duration": 3.8
        }
    ]

    downloaded_clips = []
    w, h = 720, 1280

    for sc in scenes_plan:
        print(f"\n🔍 Sahne {sc['id']}: '{sc['title']}' için canlı Pexels taraması...")
        best_visual, logs = vision_tool.curate_best_visual(
            scene_text=sc["text"],
            initial_keywords=sc["keywords"],
            search_tool=stock_tool,
            max_retries=2
        )
        print(f"   -> Seçilen Video ID: {best_visual.get('video_id')}")
        print(f"   -> Video Başlığı: '{best_visual.get('video_title')}'")
        if logs:
            print(f"   -> Skor: {logs[0]['score']}/10")

        # İndirme linkini bul
        files = best_visual.get("available_files", [])
        dl_url = None
        for f in files:
            if f.get("quality") == "hd" or (f.get("width", 0) >= 720):
                dl_url = f.get("link")
                break
        if not dl_url and files:
            dl_url = files[0].get("link")

        clip_path = os.path.join(SAMPLE_DIR, f"scene_{sc['id']}_{best_visual.get('video_id')}.mp4")
        if dl_url:
            print(f"   -> Klip indiriliyor: {clip_path}...")
            with requests.get(dl_url, stream=True, timeout=25) as r:
                r.raise_for_status()
                with open(clip_path, "wb") as f_out:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f_out.write(chunk)
            downloaded_clips.append(clip_path)

    return downloaded_clips


def compile_3_scene_montage():
    print("🎙️ 1. Tam Metin Seslendirmesi ve Zamanlamaları Üretiliyor...")
    script, voice_path, cues, total_dur = asyncio.run(generate_full_voice_and_cues())
    print(f"   -> Toplam Ses Süresi: {total_dur:.1f} saniye")

    print("\n🎬 2. 3 Ayrı Sahne İçin Gerçek Pexels Klipleri Çekiliyor...")
    clips = curate_and_download_3_scenes()

    print("\n🎥 3. Klipler Crossfade Geçişi ile Birleştiriliyor...")
    bg_video_path = os.path.join(SAMPLE_DIR, "malazgirt_3scene_background.mp4")
    lite_engine.build_cycling_background(clips, total_dur, bg_video_path, 720, 1280, transition="crossfade", transition_dur=0.4)

    print("\n📝 4. Dinamik Kelime Vurgulu (.ass) Altyazı Derleniyor...")
    ass_path = os.path.join(SAMPLE_DIR, "malazgirt_multiscene.ass")
    lite_engine.write_ass_subtitles(
        cues=cues,
        path=ass_path,
        width=720,
        height=1280,
        sub_color="#FFFFFF",
        sub_pos="bottom",
        sub_size=24,
        boxed=False,
        is_bold=True,
        font_name="Roboto",
        outline_color="#000000",
        outline_width=3,
        highlight_words=["Sultan Alparslan", "1071'de", "Turan taktiği", "Bizans", "Anadolu'nun kapıları", "zaferle"],
        highlight_color="#FBBF24"
    )

    print("\n⚡ 5. FFmpeg ile 720p 9:16 Çok Sahneli Sinematik Video Derleniyor...")
    final_output = os.path.join(SAMPLE_DIR, "malazgirt_3_sahneli_sinematik_montaj.mp4")
    
    res = lite_engine.render_video_ffmpeg(
        background_media=bg_video_path,
        audio_path=voice_path,
        subtitle_path=ass_path,
        output_video=final_output,
        aspect="9:16",
        resolution="720p",
        is_video_bg=True,
        subtitle_enabled=True
    )

    if res and os.path.exists(res):
        dest_path = os.path.join(SHARED_DIR, "malazgirt_3_sahneli_sinematik_montaj.mp4")
        shutil.copy2(res, dest_path)
        print(f"\n🎉 [BAŞARILI] 3 Sahneli Sinematik Video Tamamlandı: {dest_path}")
        return dest_path
    else:
        print("❌ Render başarısız!")
        return None


if __name__ == "__main__":
    compile_3_scene_montage()
