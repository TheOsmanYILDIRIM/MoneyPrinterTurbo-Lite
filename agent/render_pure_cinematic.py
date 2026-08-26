import asyncio
import os
import shutil
import subprocess
import edge_tts

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


async def generate_audio_and_srt():
    script = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu, uyguladığı Turan taktiği ile Bizans'ı mağlup ederek Anadolu'nun kapılarını Türklere açtı."
    voice_path = os.path.join(SAMPLE_DIR, "malazgirt_pure_voice.mp3")
    srt_path = os.path.join(SAMPLE_DIR, "malazgirt_pure.srt")
    
    comm = edge_tts.Communicate(script, "tr-TR-AhmetNeural", rate="+5%")
    submaker = edge_tts.SubMaker()
    
    with open(voice_path, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)
                
    srt_content = submaker.get_srt()
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
        
    return voice_path, srt_path


def render_cardless_cinematic_video():
    print("🎙️ 1. Ses ve Altyazı Üretiliyor...")
    voice_path, srt_path = asyncio.run(generate_audio_and_srt())

    real_video_path = os.path.join(SAMPLE_DIR, "pexels_real_battle.mp4")
    out_mp4 = os.path.join(SAMPLE_DIR, "malazgirt_kartsiz_sinematik.mp4")
    ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"

    print("🎥 2. Kartsız, Tam Ekran Sinematik Video ve Dinamik Altyazı Derleniyor...")
    
    # ASS / SRT Altyazı filtresi (Modern sarı vurgulu, kutusuz, doğrudan video üstü)
    # FFmpeg subtitles filtresi ile şık altyazı gömme
    sub_filter = f"subtitles='{srt_path}':force_style='Fontsize=22,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=2,Shadow=1,Alignment=2,MarginV=60'"

    filter_complex = (
        f"[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
        f"eq=brightness=-0.05:contrast=1.1,{sub_filter}[outv]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-stream_loop", "-1", "-i", real_video_path,
        "-i", voice_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "1:a",
        "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
        "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        "-t", "9.8",
        out_mp4
    ]

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ Kartsız Sinematik Video Başarıyla Derlendi:", out_mp4)

    dest_path = os.path.join(SHARED_DIR, "malazgirt_kartsiz_sinematik.mp4")
    shutil.copy2(out_mp4, dest_path)
    print("📁 Belgeler Klasörüne Kopyalandı:", dest_path)


if __name__ == "__main__":
    render_cardless_cinematic_video()
