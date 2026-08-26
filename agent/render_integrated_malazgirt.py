import asyncio
import os
import math
import shutil
import subprocess
import edge_tts
from PIL import Image, ImageDraw, ImageFont
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from agent.tools.layout_engine import DynamicCardRenderer, get_font

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


def create_clean_hud_card():
    """Dinamik Layout Motoru ile çizilen ve yazıları ASLA üst üste binmeyen Malazgirt HUD kartı."""
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
    out_path = os.path.join(SAMPLE_DIR, "malazgirt_clean_hud.png")
    card_img.save(out_path, "PNG")
    return out_path


def create_3d_tactical_battle_compass():
    """
    Video ile iç içe geçen 3D Dönen Savaş Pusulası ve Hilal Taktiği Animasyonu.
    """
    w, h = 680, 460
    frames = []
    fps = 24
    total_frames = 48  # 2 saniye tam döngü

    title_f = get_font(21, bold=True)
    hud_f = get_font(16, bold=True)
    sub_f = get_font(17, bold=False)

    for f in range(total_frames):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 16
        # Yarı Şeffaf Glassmorphism Arka Plan
        draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=24, fill=(15, 23, 42, 230), outline=(56, 189, 248, 240), width=3)
        draw.text((margin + 20, margin + 18), "🛡️ 3D TAKTİK HARP SİMÜLASYONU", fill=(251, 191, 36, 255), font=title_f)

        progress = f / total_frames
        angle = progress * 2 * math.pi

        # 3D Dönen Pusula Çemberi (Sol Taraf)
        c_x, c_y = margin + 160, h // 2 + 30
        radius_x = 90
        radius_y = 45  # 3D Eğimli Perspektif

        # 3D Halka Çizimi
        draw.ellipse([c_x - radius_x, c_y - radius_y, c_x + radius_x, c_y + radius_y], outline=(56, 189, 248, 200), width=3)

        # 3D Dönen 4 Tepe Noktası (North, East, South, West)
        points = [0, math.pi / 2, math.pi, 3 * math.pi / 2]
        labels = ["K", "D", "G", "B"]
        for p_idx, p_ang in enumerate(points):
            cur_ang = p_ang + angle
            px = c_x + int(math.cos(cur_ang) * radius_x)
            py = c_y + int(math.sin(cur_ang) * radius_y)
            draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(251, 191, 36, 255), outline=(255, 255, 255, 255))
            draw.text((px - 5, py - 7), labels[p_idx], fill=(15, 23, 42, 255), font=get_font(12, bold=True))

        # Merkez Hilal Sembolü
        draw.arc([c_x - 35, c_y - 35, c_x + 35, c_y + 35], start=45, end=315, fill=(251, 191, 36, 255), width=4)

        # Sağ Taraftaki Taktiksel Canlı Bilgi Paneli
        info_x = c_x + radius_x + 35
        info_w = w - info_x - margin - 15
        info_box = [info_x, margin + 70, info_x + info_w, h - margin - 25]
        draw.rounded_rectangle(info_box, radius=16, fill=(30, 41, 59, 240), outline=(52, 211, 153, 220), width=1)

        draw.text((info_x + 16, margin + 85), "⚔️ Savaş Dinamikleri", fill=(52, 211, 153, 255), font=get_font(19, bold=True))

        # Canlı Faz İlerlemesi
        phase_txt = "1. Aşama: Sahte Ricat (Merkez Geri Çekilme)" if progress < 0.5 else "2. Aşama: Hilal Kuşatması (Çember)"
        draw.text((info_x + 16, margin + 130), phase_txt, fill=(241, 245, 249, 255), font=get_font(17, bold=True))

        draw.text((info_x + 16, margin + 175), "• Selçuklu Süvarileri: ~50.000\n• Bizans Kuvvetleri: ~100.000\n• Çözülme: Peçenek/Uz Boyları", fill=(203, 213, 225, 255), font=sub_f)

        # Canlı İlerleme Çubuğu (Progress Bar)
        bar_box = [info_x + 16, h - margin - 55, info_x + info_w - 16, h - margin - 40]
        draw.rounded_rectangle(bar_box, radius=6, fill=(15, 23, 42, 255))
        bar_fill_w = int((bar_box[2] - bar_box[0]) * progress)
        if bar_fill_w > 0:
            draw.rounded_rectangle([bar_box[0], bar_box[1], bar_box[0] + bar_fill_w, bar_box[3]], radius=6, fill=(251, 191, 36, 255))

        frames.append(img)

    anim_path = os.path.join(SAMPLE_DIR, "malazgirt_3d_compass.gif")
    frames[0].save(anim_path, format="GIF", save_all=True, append_images=frames[1:], duration=int(1000/fps), loop=0, disposal=2)
    return anim_path


async def generate_speech():
    text = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu, uyguladığı Turan taktiği ile Bizans ordusunu mağlup ederek Anadolu'nun kapılarını Türklere açtı."
    voice_path = os.path.join(SAMPLE_DIR, "malazgirt_clean_voice.mp3")
    comm = edge_tts.Communicate(text, "tr-TR-AhmetNeural", rate="+5%")
    await comm.save(voice_path)
    return voice_path


def render_real_video_composite():
    print("🎨 1. Dinamik Çakışmasız HUD Kartı ve 3D Taktik Pusulası Çiziliyor...")
    card_path = create_clean_hud_card()
    anim_path = create_3d_tactical_battle_compass()

    print("🎙️ 2. Edge-TTS Ses Dosyası Hazırlanıyor...")
    voice_path = asyncio.run(generate_speech())

    print("🎥 3. Gerçek Stok Video ile 3D Katmanlar FFmpeg ile Birleştiriliyor...")
    
    # Gerçek Arka Plan Videosu
    bg_video = "/data/data/com.termux/files/home/MoneyPrinterTurbo/output/kpss_pexels_test.mp4"
    if not os.path.exists(bg_video):
        bg_video = "/data/data/com.termux/files/home/MoneyPrinterTurbo/output/temp_pexels.mp4"

    out_mp4 = os.path.join(SAMPLE_DIR, "malazgirt_savasi_ders.mp4")
    ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"

    # FFmpeg Filtresi:
    # 1. Gerçek videoyu al, 720x1280 dikey boyuta uyarla ve sinematik hafif karartma uygula
    # 2. 0.5s - 4.8s arası Çakışmasız Temiz HUD Kartını süzülerek göster
    # 3. 4.8s - 10.0s arası Dönen 3D Savaş Pusulası & Canlı Taktik Grafiğini göster
    # 4. Türkçe seslendirmeyi bağla
    
    filter_complex = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,eq=brightness=-0.15:contrast=1.1[bg];"
        "[1:v]scale=680:-1,fade=in:st=0.5:d=0.4:alpha=1,fade=out:st=4.5:d=0.4:alpha=1[hud_card];"
        "[2:v]scale=680:-1,fade=in:st=4.8:d=0.4:alpha=1,fade=out:st=9.5:d=0.4:alpha=1[3d_anim];"
        "[bg][hud_card]overlay=x='(W-w)/2':y='(H-h)/2 - 60':enable='between(t,0.5,4.8)'[v1];"
        "[v1][3d_anim]overlay=x='(W-w)/2':y='(H-h)/2 - 60':enable='between(t,4.8,9.9)'[outv]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-stream_loop", "-1", "-i", bg_video,
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

    print("✅ Gerçek Video ile 3D Animasyon Başarıyla Derlendi:", out_mp4)
    # Belgeler klasörüne kopyala
    dest_path = os.path.join(SHARED_DIR, "malazgirt_savasi_ders.mp4")
    shutil.copy2(out_mp4, dest_path)
    shutil.copy2(card_path, os.path.join(SHARED_DIR, "malazgirt_clean_hud.png"))
    shutil.copy2(anim_path, os.path.join(SHARED_DIR, "malazgirt_3d_compass.gif"))
    print("📁 Dosyalar Belgeler Klasörüne Aktarıldı:", dest_path)
    return True


if __name__ == "__main__":
    render_real_video_composite()
