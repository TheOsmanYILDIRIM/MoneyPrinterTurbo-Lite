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


def create_vertical_hud_card():
    """9:16 Dikey Formatla Birebir Uyumlu Uzun Hikaye Kartı (Vertical Story Card)."""
    card_img = DynamicCardRenderer.draw_vertical_story_card(
        badge_text="⚔️ 26 AĞUSTOS 1071",
        title="MALAZGİRT MEYDAN MUHAREBESİ",
        rows=[
            ("👑 Selçuklu Hükümdarı", "Sultan Muhammed Alparslan"),
            ("🏹 Uygulanan Askeri Taktik", "Turan / Hilal Taktiği (Sahte Ricat & Kurt Kapanı Kuşatması)"),
            ("🚩 Tarihsel Sonuç", "Bizans ordusu yenilgiye uğratıldı ve Anadolu'nun kapıları Türklere tamamen açıldı.")
        ],
        note="Bizans İmparatoru IV. Romen Diyojen esir alınmıştır.",
        width=640,
        padding=24
    )
    out_path = os.path.join(SAMPLE_DIR, "malazgirt_dikey_hud.png")
    card_img.save(out_path, "PNG")
    return out_path


def create_vertical_3d_tactical_compass():
    """9:16 Dikey format için dikey yerleşimli 3D Pusula ve Taktik Simülasyonu."""
    w, h = 640, 760
    frames = []
    fps = 24
    total_frames = 48  # 2 saniye döngü

    title_f = get_font(22, bold=True)
    hud_f = get_font(18, bold=True)
    sub_f = get_font(18, bold=False)

    for f in range(total_frames):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        padding = 24
        # Glassmorphic Dikey Koyu Panel
        draw.rounded_rectangle([padding, padding, w - padding, h - padding], radius=28, fill=(15, 23, 42, 235), outline=(56, 189, 248, 240), width=3)
        draw.text((padding + 20, padding + 22), "🛡️ 3D TAKTİK HARP SİMÜLASYONU", fill=(251, 191, 36, 255), font=title_f)
        draw.line([(padding + 20, padding + 60), (w - padding - 20, padding + 60)], fill=(56, 189, 248, 150), width=2)

        progress = f / total_frames
        angle = progress * 2 * math.pi

        # 1. ÜST BÖLÜM: 3D Dönen Pusula
        c_x, c_y = w // 2, padding + 190
        radius_x = 130
        radius_y = 65  # 3D Eğimli Çember

        draw.ellipse([c_x - radius_x, c_y - radius_y, c_x + radius_x, c_y + radius_y], outline=(56, 189, 248, 220), width=3)

        # Dönen 4 Tepe Noktası
        points = [0, math.pi / 2, math.pi, 3 * math.pi / 2]
        labels = ["K", "D", "G", "B"]
        for p_idx, p_ang in enumerate(points):
            cur_ang = p_ang + angle
            px = c_x + int(math.cos(cur_ang) * radius_x)
            py = c_y + int(math.sin(cur_ang) * radius_y)
            draw.ellipse([px - 10, py - 10, px + 10, py + 10], fill=(251, 191, 36, 255), outline=(255, 255, 255, 255))
            draw.text((px - 6, py - 8), labels[p_idx], fill=(15, 23, 42, 255), font=get_font(14, bold=True))

        # Merkez Hilal
        draw.arc([c_x - 45, c_y - 45, c_x + 45, c_y + 45], start=45, end=315, fill=(251, 191, 36, 255), width=5)

        # 2. ALT BÖLÜM: Canlı Askeri Taktik ve İlerleme Paneli
        info_box = [padding + 16, padding + 310, w - padding - 16, h - padding - 20]
        draw.rounded_rectangle(info_box, radius=18, fill=(30, 41, 59, 245), outline=(52, 211, 153, 220), width=1)

        draw.text((info_box[0] + 20, info_box[1] + 20), "⚔️ Savaş Dinamikleri & Kuvvetler", fill=(52, 211, 153, 255), font=hud_f)

        phase_txt = "▶ 1. Aşama: Sahte Ricat (Merkez Geri Çekilme)" if progress < 0.5 else "▶ 2. Aşama: Hilal Kuşatması (Çember Kapanı)"
        draw.text((info_box[0] + 20, info_box[1] + 65), phase_txt, fill=(251, 191, 36, 255), font=get_font(18, bold=True))

        draw.text((info_box[0] + 20, info_box[1] + 115), "• Selçuklu Hafif Süvarileri: ~50.000\n• Bizans Ağır Zırhlıları: ~100.000\n• Taktik Sonuç: Çember ve İmha", fill=(241, 245, 249, 255), font=sub_f)

        # İlerleme Çubuğu
        bar_box = [info_box[0] + 20, info_box[3] - 45, info_box[2] - 20, info_box[3] - 25]
        draw.rounded_rectangle(bar_box, radius=8, fill=(15, 23, 42, 255))
        bar_fill_w = int((bar_box[2] - bar_box[0]) * progress)
        if bar_fill_w > 0:
            draw.rounded_rectangle([bar_box[0], bar_box[1], bar_box[0] + bar_fill_w, bar_box[3]], radius=8, fill=(251, 191, 36, 255))

        frames.append(img)

    anim_path = os.path.join(SAMPLE_DIR, "malazgirt_dikey_3d_compass.gif")
    frames[0].save(anim_path, format="GIF", save_all=True, append_images=frames[1:], duration=int(1000/fps), loop=0, disposal=2)
    return anim_path


def render_vertical_final_video():
    print("🎨 1. 9:16 Dikey Story Kartı ve Dikey 3D Taktik Animasyonu Çiziliyor...")
    card_path = create_vertical_hud_card()
    anim_path = create_vertical_3d_tactical_compass()

    voice_path = os.path.join(SAMPLE_DIR, "malazgirt_voice.mp3")
    real_video_path = os.path.join(SAMPLE_DIR, "pexels_real_battle.mp4")
    out_mp4 = os.path.join(SAMPLE_DIR, "malazgirt_savasi_dikey_9x16.mp4")

    ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"

    print("🎥 2. FFmpeg ile 9:16 Dikey Gerçek Video Derleniyor...")
    # Dikey Kartlar 640x760 boyutunda, 720x1280 dikey ekranda tam ortalanır ve taşmaz
    filter_complex = (
        "[0:v]scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,eq=brightness=-0.15:contrast=1.15[bg];"
        "[1:v]scale=640:-1,fade=in:st=0.5:d=0.4:alpha=1,fade=out:st=4.5:d=0.4:alpha=1[v_card];"
        "[2:v]scale=640:-1,fade=in:st=4.8:d=0.4:alpha=1,fade=out:st=9.5:d=0.4:alpha=1[v_anim];"
        "[bg][v_card]overlay=x='(W-w)/2':y='(H-h)/2':enable='between(t,0.5,4.8)'[v1];"
        "[v1][v_anim]overlay=x='(W-w)/2':y='(H-h)/2':enable='between(t,4.8,9.9)'[outv]"
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

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("✅ 9:16 Dikey Video Başarıyla Derlendi:", out_mp4)
    
    # Belgeler Klasörüne Kopyala
    dest_path = os.path.join(SHARED_DIR, "malazgirt_savasi_dikey_9x16.mp4")
    shutil.copy2(out_mp4, dest_path)
    shutil.copy2(card_path, os.path.join(SHARED_DIR, "malazgirt_dikey_hud.png"))
    shutil.copy2(anim_path, os.path.join(SHARED_DIR, "malazgirt_dikey_3d_compass.gif"))
    print("📁 Dosyalar Belgeler Klasörüne Aktarıldı:", dest_path)


if __name__ == "__main__":
    render_vertical_final_video()
