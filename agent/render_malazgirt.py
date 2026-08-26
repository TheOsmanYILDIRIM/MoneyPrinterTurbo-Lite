import asyncio
import os
import math
import shutil
import subprocess
import edge_tts
from PIL import Image, ImageDraw, ImageFont

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


def get_font(size=24, bold=False):
    candidates = [
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def create_malazgirt_hud_card():
    """Malazgirt Savaşı için şık, yüksek kontrastlı HUD bilgi kartı."""
    w, h = 660, 420
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    margin = 16
    # Glassmorphism Koyu Panel + Altın & Zümrüt Yeşili Çerçeve
    draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=24, fill=(15, 23, 42, 240), outline=(251, 191, 36, 240), width=3)

    # Başlık Rozeti
    badge_box = [margin + 20, margin + 20, margin + 20 + 200, margin + 60]
    draw.rounded_rectangle(badge_box, radius=12, fill=(6, 78, 59, 255), outline=(52, 211, 153, 220), width=2)
    draw.text((badge_box[0] + 16, badge_box[1] + 6), "⚔️ 26 AĞUSTOS 1071", fill=(251, 191, 36, 255), font=get_font(18, bold=True))

    draw.text((margin + 235, margin + 22), "MALAZGİRT MEYDAN MUHAREBESİ", fill=(248, 250, 252, 255), font=get_font(21, bold=True))

    # Bilgi & Taktik Kutusu
    info_box = [margin + 20, margin + 75, w - margin - 20, h - margin - 25]
    draw.rounded_rectangle(info_box, radius=16, fill=(30, 41, 59, 250), outline=(56, 189, 248, 200), width=1)

    t_font = get_font(21, bold=True)
    d_font = get_font(19, bold=False)

    # Satır 1: Komutan
    draw.text((info_box[0] + 20, info_box[1] + 20), "👑 Başkomutan:", fill=(251, 191, 36, 255), font=t_font)
    draw.text((info_box[0] + 175, info_box[1] + 20), "Büyük Selçuklu Sultanı Alparslan", fill=(241, 245, 249, 255), font=d_font)

    # Satır 2: Taktik
    draw.text((info_box[0] + 20, info_box[1] + 75), "🏹 Harp Taktiği:", fill=(56, 189, 248, 255), font=t_font)
    draw.text((info_box[0] + 175, info_box[1] + 75), "Turan / Hilal Taktiği (Kurt Kapanı)", fill=(241, 245, 249, 255), font=d_font)

    # Satır 3: Tarihsel Sonuç
    draw.text((info_box[0] + 20, info_box[1] + 130), "🚩 Tarihi Sonuç:", fill=(52, 211, 153, 255), font=t_font)
    draw.text((info_box[0] + 175, info_box[1] + 130), "Anadolu'nun kapıları Türklere açıldı", fill=(241, 245, 249, 255), font=d_font)

    # Satır 4: Vurgu Notu
    draw.text((info_box[0] + 20, info_box[1] + 195), "💡 Not: Bizans İmparatoru Romen Diyojen esir alındı.", fill=(203, 213, 225, 255), font=get_font(17, bold=False))

    card_path = os.path.join(SAMPLE_DIR, "malazgirt_hud_card.png")
    img.save(card_path, "PNG")
    return card_path


def create_malazgirt_animated_tactic():
    """Hilal / Turan Taktiğini gösteren hareketli GIF animasyonu."""
    w, h = 660, 440
    frames = []
    fps = 20
    total_frames = 40  # 2 saniye döngü

    for f in range(total_frames):
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 16
        draw.rounded_rectangle([margin, margin, w - margin, h - margin], radius=24, fill=(15, 23, 42, 245), outline=(56, 189, 248, 240), width=3)
        draw.text((margin + 25, margin + 20), "🏹 TURAN (HİLAL) TAKTİĞİ SİMÜLASYONU", fill=(251, 191, 36, 255), font=get_font(21, bold=True))

        # Animasyon ilerlemesi (0.0 -> 1.0)
        progress = f / total_frames

        center_x, center_y = w // 2, h // 2 + 30

        # Bizans Ordusu (Ortada İlerleyen Kırmızı Daireler)
        bizans_y = center_y + 40 - int(progress * 30)
        draw.rounded_rectangle([center_x - 70, bizans_y - 25, center_x + 70, bizans_y + 25], radius=12, fill=(225, 29, 72, 255), outline=(254, 205, 211, 255), width=2)
        draw.text((center_x - 55, bizans_y - 12), "BİZANS ORDUSU", fill=(255, 255, 255, 255), font=get_font(16, bold=True))

        # Selçuklu Hilali (Kapanan Kanatlar)
        # Sol Kanat
        left_angle = math.pi * 0.75 + progress * 0.45
        lx = center_x + int(math.cos(left_angle) * 160)
        ly = center_y + int(math.sin(left_angle) * 110)
        draw.ellipse([lx - 22, ly - 22, lx + 22, ly + 22], fill=(16, 185, 129, 255), outline=(251, 191, 36, 255), width=2)
        draw.text((lx - 12, ly - 10), "Sol", fill=(255, 255, 255, 255), font=get_font(14, bold=True))

        # Sağ Kanat
        right_angle = math.pi * 0.25 - progress * 0.45
        rx = center_x + int(math.cos(right_angle) * 160)
        ry = center_y + int(math.sin(right_angle) * 110)
        draw.ellipse([rx - 22, ry - 22, rx + 22, ry + 22], fill=(16, 185, 129, 255), outline=(251, 191, 36, 255), width=2)
        draw.text((rx - 12, ry - 10), "Sağ", fill=(255, 255, 255, 255), font=get_font(14, bold=True))

        # Merkez (Sahte Geri Çekilme)
        mx = center_x
        my = center_y - 80 + int(progress * 25)
        draw.rounded_rectangle([mx - 55, my - 20, mx + 55, my + 20], radius=10, fill=(16, 185, 129, 255), outline=(251, 191, 36, 255), width=2)
        draw.text((mx - 45, my - 10), "SELÇUKLU", fill=(255, 255, 255, 255), font=get_font(15, bold=True))

        # Açıklama
        phase_text = "1. Aşama: Sahte Ricat (Geri Çekilme)" if progress < 0.5 else "2. Aşama: Hilal Kapanı & Kuşatma"
        draw.text((margin + 25, h - margin - 35), f"▶ {phase_text}", fill=(226, 232, 240, 255), font=get_font(18, bold=False))

        frames.append(img)

    tactic_path = os.path.join(SAMPLE_DIR, "malazgirt_hilal_taktigi.gif")
    frames[0].save(tactic_path, format="GIF", save_all=True, append_images=frames[1:], duration=int(1000/fps), loop=0, disposal=2)
    return tactic_path


async def generate_audio():
    script = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu, uyguladığı Turan taktiği ile Bizans ordusunu mağlup ederek Anadolu'nun kapılarını Türklere açtı."
    voice_file = os.path.join(SAMPLE_DIR, "malazgirt_voice.mp3")
    comm = edge_tts.Communicate(script, "tr-TR-AhmetNeural", rate="+5%")
    await comm.save(voice_file)
    return voice_file


def compile_malazgirt_video():
    print("🎬 1. Kartlar ve Taktik Animasyonu Çiziliyor...")
    card_path = create_malazgirt_hud_card()
    tactic_path = create_malazgirt_animated_tactic()

    print("🎙️ 2. Edge-TTS ile Seslendirme Alınıyor...")
    voice_path = asyncio.run(generate_audio())

    print("🎥 3. FFmpeg ile 720p Sinematik Video Derleniyor (Android Uyumlu)...")
    out_mp4 = os.path.join(SAMPLE_DIR, "malazgirt_savasi_ders.mp4")

    # Çözünürlük: 720x1280 (9:16 Dikey Shorts/Reels standardı, tam mobil uyumlu)
    # 0. Saniye - 4.5 Saniye arası HUD Kartı süzülerek gelir, 4.5 - 9.0 Saniye arası Hareketli Hilal Taktiği Simülasyonu gösterilir.
    
    ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"

    # FFmpeg Komutu:
    # Input 0: Sinematik Koyu Arka Plan (Gradients / Color)
    # Input 1: HUD Bilgi Kartı (PNG)
    # Input 2: Hareketli Hilal Taktiği (GIF)
    # Input 3: Seslendirme (MP3)
    
    filter_complex = (
        "[0:v]scale=720:1280[bg];"
        "[1:v]scale=660:420,fade=in:st=0.5:d=0.4:alpha=1,fade=out:st=4.5:d=0.4:alpha=1[card];"
        "[2:v]scale=660:440,fade=in:st=4.8:d=0.4:alpha=1,fade=out:st=9.5:d=0.4:alpha=1[tactic];"
        "[bg][card]overlay=x='(W-w)/2':y='(H-h)/2 - 80':enable='between(t,0.5,4.9)'[v1];"
        "[v1][tactic]overlay=x='(W-w)/2':y='(H-h)/2 - 80':enable='between(t,4.8,9.9)'[outv]"
    )

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "color=c=0x090d16:s=720x1280:d=10:r=30",
        "-loop", "1", "-i", card_path,
        "-ignore_loop", "0", "-i", tactic_path,
        "-i", voice_path,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "3:a",
        "-c:v", "libx264", "-profile:v", "high", "-level:v", "4.1",
        "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
        "-movflags", "+faststart",
        "-t", "10",
        out_mp4
    ]

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("FFmpeg Hatası:", res.stderr)
        return False

    print("✅ Video Başarıyla Derlendi:", out_mp4)
    # Belgeler klasörüne kopyala
    dest_path = os.path.join(SHARED_DIR, "malazgirt_savasi_ders.mp4")
    shutil.copy2(out_mp4, dest_path)
    shutil.copy2(card_path, os.path.join(SHARED_DIR, "malazgirt_hud_card.png"))
    shutil.copy2(tactic_path, os.path.join(SHARED_DIR, "malazgirt_hilal_taktigi.gif"))
    print("📁 Dosyalar Belgeler Klasörüne Kopyalandı:", dest_path)
    return True


if __name__ == "__main__":
    compile_malazgirt_video()
