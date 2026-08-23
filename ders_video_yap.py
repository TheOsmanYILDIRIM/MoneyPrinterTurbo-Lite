#!/usr/bin/env python3
import sys
import argparse
import os
from lite_engine import build_lecture_video

def main():
    parser = argparse.ArgumentParser(description="720p Lite Ders Videosu Oluşturucu (0 Whisper)")
    parser.add_argument("subject", nargs="?", default="KPSS Ders Notu", help="Ders veya Konu Başlığı")
    parser.add_argument("script", nargs="?", default=None, help="Okunacak ders metni")
    parser.add_argument("--file", "-f", help="Metnin okunacağı dosya (.txt)")
    parser.add_argument("--voice", "-v", default="tr-TR-AhmetNeural", help="EdgeTTS Ses Kodu (Varsayılan: tr-TR-AhmetNeural, Kadın: tr-TR-EmelNeural)")
    parser.add_argument("--aspect", "-a", default="9:16", choices=["9:16", "16:9", "1:1"], help="Format: 9:16 (Dikey Shorts), 16:9 (Yatay Ders), 1:1 (Kare)")
    parser.add_argument("--theme", "-t", default="dark_slate", choices=["dark_slate", "chalkboard", "warm_study"], help="Arka plan tahta teması")
    parser.add_argument("--output", "-o", default="/data/data/com.termux/files/home/MoneyPrinterTurbo/output", help="Çıktı klasörü")
    parser.add_argument("--name", "-n", default="ders_video_720p.mp4", help="Çıktı video dosya adı")

    args = parser.parse_args()

    script_text = args.script
    if args.file and os.path.exists(args.file):
        with open(args.file, "r", encoding="utf-8") as f:
            script_text = f.read()

    if not script_text:
        script_text = "Merhaba! Bu video Android üzerinde Termux ve Edge TTS kullanılarak tamamen yerel ve hafif bir şekilde 720p çözünürlükte üretilmiştir."

    print(f"🎬 Başlık: {args.subject}")
    print(f"🎙️ Ses: {args.voice}")
    print(f"📐 Format: {args.aspect} (720p)")
    print(f"📝 Metin: {script_text[:60]}...")
    print("⏳ Üretim başlıyor...")

    output_file = build_lecture_video(
        subject=args.subject,
        script=script_text,
        voice_name=args.voice,
        aspect=args.aspect,
        bg_style=args.theme,
        output_dir=args.output,
        filename=args.name
    )

    print(f"\n🎉 Tebrikler! Video hazırlandı:")
    print(f"📁 Dosya: {output_file}\n")

if __name__ == "__main__":
    main()
