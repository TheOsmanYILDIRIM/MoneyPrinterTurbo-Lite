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
from agent.tools.stock_search import StockSearchTool
from agent.tools.vision_inspector import VisionInspectorTool
from agent.tools.layout_engine import DynamicCardRenderer
from agent.render_integrated_malazgirt import create_3d_tactical_battle_compass

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


def live_curate_and_download_pexels():
    print("🌐 1. Canlı Pexels API ile Tarihsel Savaş / Süvari Videoları Aranıyor...")
    stock_tool = StockSearchTool()
    vision_tool = VisionInspectorTool()

    scene_text = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu Turan taktiği ile Bizans'ı mağlup etti."
    keywords = "medieval battlefield soldiers horses armor"

    best_visual, logs = vision_tool.curate_best_visual(
        scene_text=scene_text,
        initial_keywords=keywords,
        search_tool=stock_tool,
        max_retries=2
    )

    print(f"   -> [Vision Onayı] Seçilen Video ID: {best_visual.get('video_id')}")
    print(f"   -> Video Başlığı: '{best_visual.get('video_title')}'")
    print(f"   -> Thumbnail URL: {best_visual.get('thumbnail_url')}")
    if logs:
        print(f"   -> Uygunluk Skoru: {logs[0]['score']}/10 | Sebep: {logs[0]['reasoning']}")

    # Thumbnail'i cihaza kaydet
    if best_visual.get("thumbnail_url"):
        try:
            t_res = requests.get(best_visual["thumbnail_url"], timeout=10)
            if t_res.status_code == 200:
                t_path = os.path.join(SHARED_DIR, "secilen_pexels_thumbnail.jpg")
                with open(t_path, "wb") as f:
                    f.write(t_res.content)
                print(f"   -> Thumbnail Önizlemesi Kaydedildi: {t_path}")
        except Exception as e:
            logger.warning(f"Thumbnail kaydedilemedi: {e}")

    # En uygun çözünürlükteki indirme linkini bul (720p veya HD)
    available_files = best_visual.get("available_files", [])
    download_url = None
    # 720p veya dikey portrait dosyasını seç
    for vf in available_files:
        if vf.get("quality") == "hd" or (vf.get("width", 0) >= 720):
            download_url = vf.get("link")
            break
    if not download_url and available_files:
        download_url = available_files[0].get("link")

    if not download_url:
        raise ValueError("Pexels videosu için indirme linki bulunamadı!")

    print(f"📥 2. Seçilen Gerçek Savaş Videosu İndiriliyor (~720p)...")
    downloaded_video_path = os.path.join(SAMPLE_DIR, "pexels_real_battle.mp4")
    with requests.get(download_url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(downloaded_video_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    print(f"   -> Video İndirildi ({os.path.getsize(downloaded_video_path) // 1024} KB): {downloaded_video_path}")
    return downloaded_video_path, best_visual


async def generate_speech():
    text = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu, uyguladığı Turan taktiği ile Bizans ordusunu mağlup ederek Anadolu'nun kapılarını Türklere açtı."
    voice_path = os.path.join(SAMPLE_DIR, "malazgirt_voice.mp3")
    comm = edge_tts.Communicate(text, "tr-TR-AhmetNeural", rate="+5%")
    await comm.save(voice_path)
    return voice_path


def render_live_malazgirt_production():
    # 1. Pexels Arama & Gerçek Video İndirme
    real_video_path, visual_meta = live_curate_and_download_pexels()

    # 2. Dinamik Çakışmasız HUD Kartı
    print("🎨 3. Çakışmasız Dinamik HUD Bilgi Kartı Çiziliyor...")
    card_img = DynamicCardRenderer.draw_hud_info_card(
        badge_text="⚔️ 1071 MALAZGİRT",
        title="BÜYÜK SELÇUKLU ZAFERİ",
        rows=[
            ("👑 Başkomutan & Hükümdar", "Büyük Selçuklu Devleti Sultanı Muhammed Alparslan"),
            ("🏹 Uygulanan Askeri Taktik", "Turan / Hilal Taktiği (Sahte Ricat ve Kurt Kapanı Çemberi)"),
            ("🚩 Tarihsel Önemi & Sonuç", "Bizans ordusu bozguna uğratıldı, Anadolu'nun kapıları Türklere tamamen açıldı.")
        ],
        note="Bizans İmparatoru IV. Romen Diyojen Selçuklulara esir düşmüştür.",
        width=680,
        padding=20
    )
    card_path = os.path.join(SAMPLE_DIR, "malazgirt_clean_hud.png")
    card_img.save(card_path, "PNG")

    # 3. 3D Dönen Savaş Pusulası Animasyonu
    print("🛡️ 4. 3D Dönen Savaş Pusulası & Canlı Taktik Animasyonu Hazırlanıyor...")
    anim_path = create_3d_tactical_battle_compass()

    # 4. Seslendirme
    print("🎙️ 5. Türkçe Edge-TTS Seslendirme Üretiliyor...")
    voice_path = asyncio.run(generate_speech())

    # 5. FFmpeg Derleme
    print("🎥 6. FFmpeg ile Canlı Pexels Videosu + 3D Animasyon + HUD Kartı Derleniyor...")
    out_mp4 = os.path.join(SAMPLE_DIR, "malazgirt_savasi_gercek_ders.mp4")
    ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"

    # FFmpeg Filtre Grafiği:
    # 720x1280 dikey boyuta uyarla + sinematik kontrast
    # 0.5s - 4.8s arası Çakışmasız HUD Kartı
    # 4.8s - 10.0s arası 3D Dönen Pusula
    filter_complex = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,eq=brightness=-0.15:contrast=1.15[bg];"
        "[1:v]scale=680:-1,fade=in:st=0.5:d=0.4:alpha=1,fade=out:st=4.5:d=0.4:alpha=1[hud_card];"
        "[2:v]scale=680:-1,fade=in:st=4.8:d=0.4:alpha=1,fade=out:st=9.5:d=0.4:alpha=1[3d_anim];"
        "[bg][hud_card]overlay=x='(W-w)/2':y='(H-h)/2 - 60':enable='between(t,0.5,4.8)'[v1];"
        "[v1][3d_anim]overlay=x='(W-w)/2':y='(H-h)/2 - 60':enable='between(t,4.8,9.9)'[outv]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-stream_loop", "-1", "-i", real_video_path,
        "-loop", "1", "-i", card_path,
        "-ignore_loop", "0", "-i", anim_path,
        "-i", voice_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
        "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        "-t", "9.8",
        out_mp4
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Hatası:", res.stderr)
        return False

    print("✅ Gerçek Pexels Video Derlemesi Tamamlandı:", out_mp4)
    dest_path = os.path.join(SHARED_DIR, "malazgirt_savasi_gercek_ders.mp4")
    shutil.copy2(out_mp4, dest_path)
    shutil.copy2(card_path, os.path.join(SHARED_DIR, "malazgirt_clean_hud.png"))
    shutil.copy2(anim_path, os.path.join(SHARED_DIR, "malazgirt_3d_compass.gif"))
    print("📁 Nihai Video ve Tüm Varlıklar Belgeler Klasörüne Kopyalandı:", dest_path)
    return True


if __name__ == "__main__":
    render_live_malazgirt_production()
