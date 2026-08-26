import os
import math
from typing import List, Tuple, Dict, Optional
from PIL import Image, ImageDraw, ImageFont
import subprocess
import shutil


def _get_font(size: int = 24, bold: bool = False) -> ImageFont.ImageFont:
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


class MotionAnimator:
    """
    OpenMontage esintili, dinamik ve 3D animasyonlu görsel katmanlar üretir.
    - 3D Dönen Geometrik Modeller (Wireframe Cube / Coordinate Axes)
    - Adım Adım Kendiliğinden Çizilen Formül & Ok Animasyonları (Progressive Reveal)
    - Şeffaf Alpha Channel Animasyonlu WebP / MP4 çıktıları
    """

    def __init__(self, output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # -------------------------------------------------------------
    # 1. 3D ROTATING WIREFRAME (3D Dönen Geometri & Koordinat Sistemi)
    # -------------------------------------------------------------
    def render_3d_rotating_cube(
        self,
        title: str = "3D Geometrik Dönüşüm",
        formula: str = "V = a³",
        duration_sec: float = 3.0,
        fps: int = 24,
        filename: str = "dynamic_3d_cube.webp",
        width: int = 640,
        height: int = 480
    ) -> str:
        """
        Matematiksel 3D projeksiyon ile dönen şık şeffaf wireframe küp ve formül kartı üretir.
        """
        frames = []
        total_frames = int(duration_sec * fps)
        
        # 3D Küp Köşeleri (Vertices)
        vertices = [
            [-1, -1, -1], [1, -1, -1], [1, 1, -1], [-1, 1, -1],
            [-1, -1,  1], [1, -1,  1], [1, 1,  1], [-1, 1,  1]
        ]
        # Kenarlar (Edges)
        edges = [
            (0, 1), (1, 2), (2, 3), (3, 0),
            (4, 5), (5, 6), (6, 7), (7, 4),
            (0, 4), (1, 5), (2, 6), (3, 7)
        ]

        title_font = _get_font(22, bold=True)
        formula_font = _get_font(28, bold=True)

        for f in range(total_frames):
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # Arka plan yumuşak cam kutu
            margin = 16
            draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=24, fill=(15, 23, 42, 235), outline=(56, 189, 248, 220), width=2)
            draw.text((margin + 25, margin + 20), f"🎲 {title}", fill=(248, 250, 252, 255), font=title_font)

            # 3D Açı Dönüşümü (X and Y axis rotation)
            angle_y = (f / total_frames) * (2 * math.pi)
            angle_x = math.sin((f / total_frames) * math.pi) * 0.4 + 0.3

            # 3D -> 2D Projeksiyon
            projected = []
            center_x = width // 2 - 100
            center_y = height // 2 + 30
            scale = 75

            for v in vertices:
                # Rotasyon Y
                x1 = v[0] * math.cos(angle_y) + v[2] * math.sin(angle_y)
                y1 = v[1]
                z1 = -v[0] * math.sin(angle_y) + v[2] * math.cos(angle_y)

                # Rotasyon X
                x2 = x1
                y2 = y1 * math.cos(angle_x) - z1 * math.sin(angle_x)
                z2 = y1 * math.sin(angle_x) + z1 * math.cos(angle_x)

                # Perspektif
                fov = 3.5
                pz = fov / (fov + z2 + 2.0)
                px = int(center_x + x2 * scale * pz)
                py = int(center_y + y2 * scale * pz)
                projected.append((px, py))

            # Kenarları Çiz (Neon Mavi ve Mor gradyan)
            for edge in edges:
                p1 = projected[edge[0]]
                p2 = projected[edge[1]]
                draw.line([p1, p2], fill=(56, 189, 248, 255), width=3)

            # Köşe Noktalarını Parlat
            for p in projected:
                draw.ellipse([p[0] - 4, p[1] - 4, p[0] + 4, p[1] + 4], fill=(251, 191, 36, 255))

            # Sağ Tarafta Formül & Bilgi Kutusu
            info_box = [width - 240, margin + 80, width - margin - 25, height - margin - 35]
            draw.rounded_rectangle(info_box, radius=16, fill=(30, 41, 59, 240), outline=(251, 191, 36, 200), width=1)
            draw.text((info_box[0] + 20, info_box[1] + 25), "Hacim Formülü", fill=(148, 163, 184, 255), font=_get_font(18, bold=False))
            draw.text((info_box[0] + 20, info_box[1] + 65), formula, fill=(251, 191, 36, 255), font=formula_font)
            draw.text((info_box[0] + 20, info_box[1] + 120), "• 6 Yüzey\n• 8 Köşe\n• 12 Ayrıt", fill=(226, 232, 240, 255), font=_get_font(18, bold=False))

            frames.append(img)

        out_path = os.path.join(self.output_dir, filename)
        if filename.endswith(".gif"):
            frames[0].save(
                out_path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0,
                disposal=2
            )
        else:
            frames[0].save(
                out_path,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0,
                quality=90
            )
        return out_path

    # -------------------------------------------------------------
    # 2. PROGRESSIVE FORMULA & STEP REVEAL (Kendiliğinden Çizilen Formül)
    # -------------------------------------------------------------
    def render_progressive_steps_reveal(
        self,
        title: str,
        steps: List[str],
        duration_sec: float = 3.5,
        fps: int = 24,
        filename: str = "dynamic_steps_reveal.gif",
        width: int = 720,
        height: int = 460
    ) -> str:
        frames = []
        total_frames = int(duration_sec * fps)
        step_count = len(steps)
        frames_per_step = total_frames / max(1, step_count)

        title_font = _get_font(24, bold=True)
        step_font = _get_font(21, bold=False)
        num_font = _get_font(20, bold=True)

        for f in range(total_frames):
            img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            margin = 20
            draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=24, fill=(15, 23, 42, 235), outline=(168, 85, 247, 220), width=3)
            draw.text((margin + 25, margin + 22), f"⚡ {title}", fill=(243, 244, 246, 255), font=title_font)

            current_active = int(f / frames_per_step)

            y_offset = margin + 80
            for idx in range(min(step_count, 4)):
                if idx <= current_active:
                    is_new = (idx == current_active)
                    circle_color = (251, 191, 36, 255) if is_new else (168, 85, 247, 255)
                    text_color = (255, 255, 255, 255) if is_new else (226, 232, 240, 255)

                    circle_box = [margin + 25, y_offset, margin + 65, y_offset + 40]
                    draw.ellipse(circle_box, fill=circle_color)
                    draw.text((circle_box[0] + 13, circle_box[1] + 7), str(idx + 1), fill=(15, 23, 42, 255) if is_new else (255, 255, 255, 255), font=num_font)
                    draw.text((margin + 80, y_offset + 8), steps[idx], fill=text_color, font=step_font)

                y_offset += 68

            frames.append(img)

        out_path = os.path.join(self.output_dir, filename)
        if filename.endswith(".gif"):
            frames[0].save(
                out_path,
                format="GIF",
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0,
                disposal=2
            )
        else:
            frames[0].save(
                out_path,
                format="WEBP",
                save_all=True,
                append_images=frames[1:],
                duration=int(1000 / fps),
                loop=0,
                quality=90
            )
        return out_path

    # -------------------------------------------------------------
    # 3. FULL VIDEO COMPOSITE DEMO (480p Animasyonlu Video Render Testi)
    # -------------------------------------------------------------
    def render_demo_video(
        self,
        script_text: str = "Küpün hacmi bir ayrıtının küpü alınarak hesaplanır.",
        overlay_anim_path: Optional[str] = None,
        filename: str = "sample_animated_kpss_lesson.mp4"
    ) -> str:
        """
        Arka plan videosu + 3D dinamik animasyon + Edge-TTS ses ve altyazıyı
        birleştirip gerçek bir 480p örnek MP4 video derler.
        """
        out_mp4 = os.path.join(self.output_dir, filename)
        
        if not overlay_anim_path or not os.path.exists(overlay_anim_path):
            overlay_anim_path = self.render_3d_rotating_cube(filename="dynamic_3d_cube.gif")

        voice_mp3 = os.path.join(self.output_dir, "demo_voice.mp3")
        try:
            import edge_tts, asyncio
            async def _make_tts():
                comm = edge_tts.Communicate(script_text, "tr-TR-AhmetNeural")
                await comm.save(voice_mp3)
            asyncio.run(_make_tts())
        except Exception:
            pass

        ffmpeg_bin = shutil.which("ffmpeg") or "/data/data/com.termux/files/usr/bin/ffmpeg"
        
        # FFmpeg: 480x854 dikey koyu gradyan + GIF animasyon + Ses
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "color=c=0x0f172a:s=480x854:d=4:r=24",
            "-ignore_loop", "0", "-i", overlay_anim_path
        ]
        
        if os.path.exists(voice_mp3):
            cmd.extend(["-i", voice_mp3])
            filter_complex = "[0:v][1:v]overlay=x='(W-w)/2':y='(H-h)/2 - 50':shortest=1[outv]"
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]", "-map", "2:a",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-t", "4",
                out_mp4
            ])
        else:
            filter_complex = "[0:v][1:v]overlay=x='(W-w)/2':y='(H-h)/2 - 50':shortest=1[outv]"
            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[outv]",
                "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                "-t", "4",
                out_mp4
            ])

        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return out_mp4
