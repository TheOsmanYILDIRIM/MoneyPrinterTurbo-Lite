import asyncio
import json
import os
import re
import subprocess
import requests
import random
from typing import List, Tuple, Optional, Callable
import edge_tts
from loguru import logger
from PIL import Image, ImageDraw, ImageFont
import settings_manager

RESOLUTIONS = {
    "9:16": (720, 1280),   # Dikey Shorts/Reels/TikTok
    "16:9": (1280, 720),   # Yatay YouTube/Ders
    "1:1": (720, 720),     # Kare
}

# İptal desteği: çalışan ffmpeg süreçlerini görev kimliğiyle izleriz.
class TaskCancelled(Exception):
    pass

_active_ffmpeg: dict = {}

DEFAULT_FONT_PATH = "/system/fonts/Roboto-Regular.ttf"
if not os.path.exists(DEFAULT_FONT_PATH):
    local_font = os.path.join(os.path.dirname(__file__), "resource", "fonts", "Roboto-Regular.ttf")
    if os.path.exists(local_font):
        DEFAULT_FONT_PATH = local_font

SONGS_DIR = os.path.join(os.path.dirname(__file__), "resource", "songs")
BGM_EXTENSIONS = (".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus")


def pick_random_bgm() -> Optional[str]:
    """resource/songs/ klasorunden rastgele muzik secer; bos ise None doner."""
    try:
        files = [os.path.join(SONGS_DIR, f) for f in os.listdir(SONGS_DIR)
                 if f.lower().endswith(BGM_EXTENSIONS)]
    except OSError:
        return None
    if not files:
        logger.warning("Rastgele müzik için resource/songs/ boş")
        return None
    chosen = random.choice(files)
    logger.info(f"Rastgele BGM seçildi: {os.path.basename(chosen)}")
    return chosen


def format_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def format_ass_time(seconds: float) -> str:
    cs = int(round(max(0.0, seconds) * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


# sub_size etiketleri -> min(w,h) yuzdesi olarak font boyutu
FONT_SCALE = {14: 0.052, 18: 0.066, 22: 0.080, 28: 0.094}
DEFAULT_FONT_SCALE = 0.066


def compute_subtitle_metrics(width: int, height: int, sub_size: int,
                             boxed: bool) -> dict:
    """Ekrana sigdirma metriklerini hesaplar."""
    base = min(width, height)
    fontsize = max(16, round(base * FONT_SCALE.get(int(sub_size or 18), DEFAULT_FONT_SCALE)))
    # Ortalama karakter genisligi ~ fontsize*0.52 (Roboto); guvenli genislik %88
    usable_width = width * 0.88
    chars_per_line = max(10, int(usable_width / (fontsize * 0.52)))
    return {
        "fontsize": fontsize,
        "chars_per_line": chars_per_line,
        "max_chars": chars_per_line * 2,   # en fazla 2 satir
        "margin_lr": round(width * 0.06),
        "outline": max(2, round(fontsize * 0.06)),
        "border_style": 3 if boxed else 1
    }


ASS_COLOR_MAP = {"#FFFFFF": "&H00FFFFFF", "#FFD700": "&H0000D7FF",
                 "#38BDF8": "&H00F8BD38", "#4ADE80": "&H0080DE4A"}


def write_ass_subtitles(cues: List[Tuple[float, float, str]], path: str,
                        width: int, height: int, sub_color: str = "#FFFFFF",
                        sub_pos: str = "bottom", sub_size: int = 18,
                        boxed: bool = False) -> str:
    """Video cozunurlugune tam oturan .ass altyazi uretir."""
    m = compute_subtitle_metrics(width, height, sub_size, boxed)

    c = (sub_color or "#FFFFFF").lstrip("#")
    primary = ASS_COLOR_MAP.get(f"#{c.upper()}",
                                f"&H00{c[4:6]}{c[2:4]}{c[0:2]}" if len(c) == 6 else "&H00FFFFFF")

    if sub_pos == "top":
        alignment, margin_v = 8, round(height * 0.07)
    elif sub_pos == "center":
        alignment, margin_v = 5, 0
    else:
        alignment = 2
        margin_v = round(height * (0.10 if height > width else 0.08))

    if boxed:
        outline_color = "&H96000000"  # yari saydam siyah kutu
        outline_w = round(m["fontsize"] * 0.22)
        shadow_w = 0
    else:
        outline_color = "&H00000000"
        outline_w = m["outline"]
        shadow_w = 1

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Roboto,{m['fontsize']},{primary},&H000000FF,{outline_color},&H80000000,0,0,0,0,100,100,0,0,{m['border_style']},{outline_w},{shadow_w},{alignment},{m['margin_lr']},{m['margin_lr']},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in cues:
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},"
                     f"Sub,,0,0,0,,{text}\n")
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return path


def split_sentence_to_cues(sentence_text: str, start_time: float, end_time: float, max_words=5, max_chars=26) -> List[Tuple[float, float, str]]:
    words = sentence_text.strip().split()
    if not words:
        return []
    if len(words) <= max_words and len(sentence_text) <= max_chars:
        return [(start_time, end_time, sentence_text)]

    total_chars = sum(len(w) for w in words)
    duration = max(0.5, end_time - start_time)
    chunks = []
    curr = []
    curr_len = 0

    for w in words:
        curr.append(w)
        curr_len += len(w) + 1
        if len(curr) >= max_words or curr_len >= max_chars:
            chunks.append(" ".join(curr))
            curr = []
            curr_len = 0
    if curr:
        chunks.append(" ".join(curr))

    cues = []
    curr_t = start_time
    for chunk in chunks:
        chunk_chars = sum(len(w) for w in chunk.split())
        chunk_dur = duration * (chunk_chars / max(1, total_chars))
        cues.append((curr_t, curr_t + chunk_dur, chunk))
        curr_t += chunk_dur
    return cues


def clean_search_term(raw_query: str) -> str:
    # Türkçe karakterleri ve gereksiz noktalama işaretlerini temizle
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    cleaned = raw_query.translate(tr_map)
    terms = [k.strip() for k in re.split(r"[,;]+", cleaned) if k.strip()]
    if not terms:
        return "education study blackboard"
    return " ".join(terms[:4])


def _download_pexels_clip(url: str, output_path: str, w: int, h: int, timeout: int = 25) -> bool:
    """Tek bir Pexels videosunu indirir ve hedef çözünürlüğe ölçekler."""
    tmp_path = output_path + ".raw.mp4"
    try:
        v_res = requests.get(url, timeout=timeout, stream=True)
        v_res.raise_for_status()
        with open(tmp_path, "wb") as f:
            for chunk in v_res.iter_content(chunk_size=1024 * 64):
                if chunk:
                    f.write(chunk)
        if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) < 1024:
            return False
        # Hedef çözünürlüğe ölçekle ki birleştirme (concat) sorunsuz olsun.
        cmd = [
            "ffmpeg", "-y", "-i", tmp_path,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1024
    except Exception as e:
        logger.warning(f"Pexels indirme hatası: {e}")
        return False


def fetch_pexels_clips(query: str, orientation: str = "portrait", outdir: str = ".",
                       w: int = 720, h: int = 1280, max_clips: int = 6) -> List[str]:
    """Sorguya uyan birden fazla Pexels videosunu indirir (orijinal projedeki gibi).

    Tekrarlı (döngüsel) tek video yerine, birden çok farklı klip indirip
    bunları süreye göre birleştirmek için kullanılır.
    """
    api_key = settings_manager.get_setting("pexels_api_keys", "").split(",")[0].strip()
    if not api_key:
        logger.warning("Pexels API anahtarı tanımlı değil (Ayarlar'dan ekleyin)")
        return []

    search_query = clean_search_term(query)
    headers = {"Authorization": api_key}
    url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(search_query)}&per_page=12&orientation={orientation}"

    try:
        res = requests.get(url, headers=headers, timeout=8)
        data = res.json() if res.status_code == 200 else {}
        videos = data.get("videos", [])

        if not videos:
            # Genel terimle dene
            fallback_terms = ["study library", "blackboard education", "office work", "nature landscape"]
            fb_q = random.choice(fallback_terms)
            fb_url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(fb_q)}&per_page=8&orientation={orientation}"
            r_fb = requests.get(fb_url, headers=headers, timeout=8)
            if r_fb.status_code == 200:
                videos = r_fb.json().get("videos", [])

        if not videos:
            return []

        # Farklı videoları karıştır, en fazla max_clips kadar indir.
        random.shuffle(videos)
        clips: List[str] = []
        for idx, video in enumerate(videos):
            if len(clips) >= max_clips:
                break
            video_files = video.get("video_files", [])

            best_url = None
            for vf in video_files:
                if vf.get("width") == 720 or vf.get("height") == 1280 or vf.get("quality") == "hd":
                    best_url = vf.get("link")
                    break
            if not best_url and video_files:
                best_url = video_files[0].get("link")
            if not best_url:
                continue

            out_path = os.path.join(outdir, f"pexels_{idx}.mp4")
            if _download_pexels_clip(best_url, out_path, w, h):
                clips.append(out_path)

        if clips:
            logger.info(f"{len(clips)} Pexels videosu indirildi: {search_query}")
        return clips
    except Exception as e:
        logger.warning(f"Pexels hatası: {e}")
        return []


def build_cycling_background(clips: List[str], target_duration: float,
                             output_path: str, w: int, h: int,
                             transition: str = "none",
                             transition_dur: float = 0.5) -> Optional[str]:
    """İndirilen farklı klipleri döngüsel olarak birleştirir.

    Her klip yalnızca bir kez (veya süre yetene kadar) kullanılır; aynı klip
    ardışık tekrarlanmaz. Tek klip indirilebildiyse onu olduğu gibi döndürür
    (render aşaması döngüye alır).

    transition="crossfade" ise klipler arası yumuşak geçiş (xfade) uygulanır.
    """
    if not clips:
        return None

    if len(clips) == 1:
        try:
            import shutil
            shutil.copy(clips[0], output_path)
            return output_path
        except Exception:
            return clips[0]

    # Klipleri karıştır, süre yeterli olana kadar döngüsel ekle.
    pool = list(clips)
    random.shuffle(pool)
    ordered: List[str] = []
    total = 0.0
    i = 0
    max_repeats = max(3, len(pool) * 2)
    while total < target_duration + 1.0 and (len(ordered) < max_repeats):
        c = pool[i % len(pool)]
        try:
            d = get_audio_duration(c)
        except Exception:
            d = 5.0
        ordered.append(c)
        total += d
        i += 1
        if len(pool) == 1 and total >= target_duration:
            break

    if not ordered:
        return None

    use_xfade = (transition == "crossfade" and len(ordered) >= 2)

    # xfade, herhangi bir klip süresi geçiş süresinden kısa ise bozulur;
    # o durumda güvenli tara olarak sadece concat'a düş.
    if use_xfade:
        try:
            min_dur = min(get_audio_duration(c) for c in ordered)
        except Exception:
            min_dur = 5.0
        if min_dur <= transition_dur + 0.05:
            use_xfade = False

    inputs: List[str] = []
    fparts: List[str] = []
    for idx, c in enumerate(ordered):
        inputs += ["-i", c]
        fparts.append(
            f"[{idx}:v]scale={w}:{h}:force_original_aspect_ratio=increase,"
            f"crop={w}:{h},setsar=1[v{idx}]"
        )

    if use_xfade:
        # Ardışık xfade zinciri: offset'ler kümülatif süreden (n-1)*td düşülerek hesaplanır.
        try:
            durations = [get_audio_duration(c) for c in ordered]
        except Exception:
            durations = [5.0] * len(ordered)
        td = transition_dur
        prev = "v0"
        for idx in range(1, len(ordered)):
            offset = sum(durations[:idx]) - idx * td
            fparts.append(
                f"[{prev}][v{idx}]xfade=transition=fade:duration={td:.2f}"
                f":offset={offset:.2f}[x{idx}]"
            )
            prev = f"x{idx}"
        filter_chain = ";".join(fparts)
        map_out = f"[{prev}]"
    else:
        concat_filter = "".join(f"[v{idx}]" for idx in range(len(ordered)))
        concat_filter += f"concat=n={len(ordered)}:v=1[v]"
        filter_chain = ";".join(fparts) + ";" + concat_filter
        map_out = "[v]"

    cmd = [
        "ffmpeg", "-y"
    ] + inputs + [
        "-filter_complex", filter_chain,
        "-map", map_out,
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an",
        "-t", f"{target_duration + 0.2:.2f}",
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception as e:
        logger.warning(f"Döngüsel arka plan birleştirme hatası: {e}")
        return None

    return output_path if (os.path.exists(output_path) and os.path.getsize(output_path) > 1024) else None


def fetch_pexels_video(query: str, orientation: str = "portrait", output_path: str = "pexels_bg.mp4") -> Optional[str]:
    """Geriye dönük uyumluluk: tek bir Pexels videosu indirir."""
    w, h = (720, 1280) if orientation == "portrait" else (1280, 720)
    clips = fetch_pexels_clips(query, orientation, os.path.dirname(output_path) or ".", w, h, max_clips=1)
    if clips:
        try:
            import shutil
            shutil.copy(clips[0], output_path)
            return output_path
        except Exception:
            return clips[0]
    return None


async def generate_audio_and_subtitles_async(
    text: str,
    voice_name: str = "tr-TR-AhmetNeural",
    output_audio: str = "audio.mp3",
    max_words: int = 8,
    max_chars: int = 60,
    rate: str = "+0%",
    volume: str = "+0%",
) -> List[Tuple[float, float, str]]:
    """Sesi uretir ve ekrana sigacak sekilde bolunmus altyazi cues dondurur."""
    sentences = []
    success = False

    try:
        communicate = edge_tts.Communicate(text=text, voice=voice_name, rate=rate, volume=volume)
        with open(output_audio, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    start_s = chunk["offset"] / 10_000_000
                    dur_s = chunk["duration"] / 10_000_000
                    sentences.append((start_s, start_s + dur_s, chunk.get("text", "")))
        if os.path.exists(output_audio) and os.path.getsize(output_audio) > 500:
            success = True
    except Exception as e:
        logger.warning(f"Ses '{voice_name}' hata verdi ({e}), Türkçe Ahmet sesine geçiliyor...")

    # Fallback: tr-TR-AhmetNeural
    if not success:
        sentences = []
        communicate = edge_tts.Communicate(text=text, voice="tr-TR-AhmetNeural", rate=rate, volume=volume)
        with open(output_audio, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    start_s = chunk["offset"] / 10_000_000
                    dur_s = chunk["duration"] / 10_000_000
                    sentences.append((start_s, start_s + dur_s, chunk.get("text", "")))

    duration = get_audio_duration(output_audio)

    all_cues = []
    if sentences:
        for s_start, s_end, s_text in sentences:
            all_cues.extend(split_sentence_to_cues(s_text, s_start, s_end,
                                                   max_words=max_words, max_chars=max_chars))
    else:
        all_cues = split_sentence_to_cues(text, 0.1, duration,
                                          max_words=max_words, max_chars=max_chars)
    return all_cues


def get_audio_duration(audio_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audio_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as e:
        raise RuntimeError(f"Ses süresi okunamadı ({audio_path}): {e}")


def wrap_text(text: str, font: ImageFont.FreeTypeFont, max_width: int, draw: ImageDraw.ImageDraw) -> List[str]:
    words = text.split()
    if not words:
        return []
    lines = []
    current_line = []
    for word in words:
        test_line = " ".join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_w = bbox[2] - bbox[0]
        if line_w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
    if current_line:
        lines.append(" ".join(current_line))
    return lines


def create_lecture_background(
    width: int,
    height: int,
    subject: str = "",
    bg_style: str = "dark_slate",
    output_path: str = "background.png"
) -> str:
    if bg_style == "chalkboard":
        top_color = (20, 42, 30)
        bottom_color = (12, 28, 20)
    elif bg_style == "warm_study":
        top_color = (36, 26, 20)
        bottom_color = (18, 14, 12)
    elif bg_style == "midnight_purple":
        top_color = (30, 20, 45)
        bottom_color = (16, 10, 24)
    else:
        top_color = (18, 24, 38)
        bottom_color = (10, 14, 22)

    img = Image.new("RGB", (width, height), top_color)
    draw = ImageDraw.Draw(img)

    for y in range(height):
        factor = y / height
        r = int(top_color[0] * (1 - factor) + bottom_color[0] * factor)
        g = int(top_color[1] * (1 - factor) + bottom_color[1] * factor)
        b = int(top_color[2] * (1 - factor) + bottom_color[2] * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    margin = 24
    # RGB modda alfa yok sayilirak beyaz cizilmesin; koyu ton cerceve
    frame_color = tuple(min(255, int(c * 1.6)) for c in top_color)
    draw.rectangle(
        [(margin, margin), (width - margin, height - margin)],
        outline=frame_color,
        width=2
    )

    if subject:
        title_font_size = 36 if width > height else 30
        try:
            title_font = ImageFont.truetype(DEFAULT_FONT_PATH, title_font_size)
        except Exception:
            title_font = ImageFont.load_default()

        title_lines = wrap_text(subject, title_font, width - 100, draw)
        title_y = 50
        for tline in title_lines:
            bbox = draw.textbbox((0, 0), tline, font=title_font)
            tw = bbox[2] - bbox[0]
            tx = (width - tw) // 2
            draw.text((tx + 2, title_y + 2), tline, font=title_font, fill=(0, 0, 0, 160))
            draw.text((tx, title_y), tline, font=title_font, fill=(255, 215, 0))
            title_y += (bbox[3] - bbox[1]) + 8

        line_w = int(width * 0.5)
        line_x = (width - line_w) // 2
        draw.line([(line_x, title_y + 4), (line_x + line_w, title_y + 4)], fill=(255, 215, 0, 120), width=2)

    img.save(output_path, "PNG")
    return output_path


def render_video_with_subtitles(
    background_media: str,
    audio_path: str,
    subtitle_path: str,
    output_video: str,
    aspect: str = "9:16",
    is_video_bg: bool = False,
    subtitle_enabled: bool = True,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.15,
    task_id: Optional[str] = None,
    cancel_requested: Optional[Callable[[], bool]] = None
) -> str:
    width, height = RESOLUTIONS.get(aspect, (720, 1280))
    duration = get_audio_duration(audio_path)

    work_dir = os.path.dirname(os.path.abspath(subtitle_path))
    rel_subs = os.path.relpath(subtitle_path, work_dir)
    rel_bg = os.path.relpath(background_media, work_dir)
    rel_audio = os.path.relpath(audio_path, work_dir)
    rel_output = os.path.relpath(output_video, work_dir)

    vf_filters = [f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}"]
    has_subs = (subtitle_enabled and os.path.exists(subtitle_path)
                and os.path.getsize(subtitle_path) > 0)
    if has_subs:
        # .ass dosyasi PlayResX/Y ile video cozunurlugune gore olceklenir;
        # ekstra force_style gerekmez.
        fonts_dir = os.path.join(os.path.dirname(__file__), "resource", "fonts")
        if os.path.isdir(fonts_dir):
            vf_filters.append(f"subtitles={rel_subs}:fontsdir='{fonts_dir}'")
        else:
            vf_filters.append(f"subtitles={rel_subs}")

    vf_str = ",".join(vf_filters)

    cmd = ["ffmpeg", "-y"]

    if is_video_bg:
        cmd.extend(["-stream_loop", "-1", "-i", rel_bg])
    else:
        cmd.extend(["-loop", "1", "-i", rel_bg])

    cmd.extend(["-i", rel_audio])

    if bgm_path and os.path.exists(bgm_path):
        rel_bgm = os.path.relpath(bgm_path, work_dir)
        cmd.extend(["-stream_loop", "-1", "-i", rel_bgm])
        cmd.extend(["-filter_complex", f"[1:a]volume=1.0[v1];[2:a]volume={bgm_volume}[v2];[v1][v2]amix=inputs=2:duration=first[aout]"])
        cmd.extend(["-map", "0:v", "-map", "[aout]"])
    else:
        cmd.extend(["-map", "0:v", "-map", "1:a"])

    cmd.extend([
        "-vf", vf_str,
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage" if not is_video_bg else "film",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-threads", "2",
        "-shortest",
        "-t", f"{duration + 0.2:.2f}",
        rel_output
    ])

    logger.info(f"FFmpeg render ({aspect})...")

    def _run(proc_cmd: list):
        proc = subprocess.Popen(proc_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work_dir)
        if task_id:
            _active_ffmpeg[task_id] = proc
        try:
            if cancel_requested and cancel_requested():
                proc.terminate()
                raise TaskCancelled()
            _, _ = proc.communicate()
        finally:
            if task_id:
                _active_ffmpeg.pop(task_id, None)
        if cancel_requested and cancel_requested():
            raise TaskCancelled()
        return proc.returncode

    try:
        returncode = _run(cmd)
    except TaskCancelled:
        raise
    if returncode != 0:
        logger.warning(f"FFmpeg fallback tetikleniyor (rc={returncode})")
        fb_cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-i", rel_bg,
            "-i", rel_audio,
            "-c:v", "libx264", "-preset", "ultrafast", "-c:a", "aac",
            "-b:a", "128k", "-pix_fmt", "yuv420p", "-threads", "2",
            "-shortest", "-t", f"{duration + 0.2:.2f}",
            rel_output
        ]
        try:
            _run(fb_cmd)
        except TaskCancelled:
            raise

    return output_video


def remux_audio_into_video(video_path: str, audio_path: str, output_path: str,
                           task_id: Optional[str] = None,
                           cancel_requested: Optional[Callable[[], bool]] = None) -> str:
    """Mevcut videonun goruntu akisini YENIDEN KODLAMADAN kopyalar ve yeni sesi
    enjekte eder. Ses degisimi gibi islemlerde cok hizlidir (saniyeler)."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path, "-i", audio_path,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart", output_path
    ]
    logger.info("FFmpeg hizli ses degisimi (stream copy, yeniden kodlama yok)...")

    def _run(proc_cmd: list):
        proc = subprocess.Popen(proc_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if task_id:
            _active_ffmpeg[task_id] = proc
        try:
            if cancel_requested and cancel_requested():
                proc.terminate()
                raise TaskCancelled()
            _, _ = proc.communicate()
        finally:
            if task_id:
                _active_ffmpeg.pop(task_id, None)
        if cancel_requested and cancel_requested():
            raise TaskCancelled()
        return proc.returncode

    try:
        rc = _run(cmd)
    except TaskCancelled:
        raise
    if rc != 0:
        raise RuntimeError(f"FFmpeg ses degisimi basarisiz (rc={rc})")
    return output_path


def build_lecture_video(
    subject: str,
    script: str,
    voice_name: str = "tr-TR-AhmetNeural",
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    aspect: str = "9:16",
    bg_style: str = "chalkboard",
    pexels_query: Optional[str] = None,
    custom_bg_media: Optional[str] = None,
    custom_audio: Optional[str] = None,
    subtitle_enabled: bool = True,
    sub_color: str = "#FFFFFF",
    sub_pos: str = "bottom",
    sub_size: int = 18,
    sub_box: bool = False,
    bgm_path: Optional[str] = None,
    bgm_mode: str = "none",
    bgm_volume: float = 0.15,
    output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/output",
    filename: str = "ders_video.mp4",
    progress_callback: Optional[Callable[[int, str], None]] = None,
    task_id: Optional[str] = None,
    cancel_requested: Optional[Callable[[], bool]] = None,
    reuse_cues_path: Optional[str] = None,
    source_video_path: Optional[str] = None,
    transition: str = "none",
    transition_dur: float = 0.5
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    if cancel_requested and cancel_requested():
        raise TaskCancelled()
    # Kalıcı ara ürünler: varyant (ses/görüntü/altyazı) yeniden üretiminde kullanılır.
    audio_path = os.path.join(output_dir, "audio.mp3")
    subtitle_path = os.path.join(output_dir, "subtitle.ass")
    cues_path = os.path.join(output_dir, "subtitle_cues.json")
    final_output = os.path.join(output_dir, filename)

    w, h = RESOLUTIONS.get(aspect, (720, 1280))

    # Ekrana sigdirma metrikleri (cozunurluge gore dinamik satir uzunlugu)
    metrics = compute_subtitle_metrics(w, h, sub_size, sub_box)

    bg_media: Optional[str] = None
    is_video = False
    bg_error: List[str] = []

    need_pexels = (not custom_bg_media) and (bg_style == "pexels" or bool(pexels_query))
    pexels_dir = output_dir

    if cancel_requested and cancel_requested():
        raise TaskCancelled()

    if custom_audio and os.path.exists(custom_audio):
        if progress_callback:
            progress_callback(20, "Özel ses dosyası işleniyor...")
        audio_path = custom_audio
        # Varyant (örn. altyazı) yeniden üretiminde orijinal cümle zamanlamaları korunur.
        if reuse_cues_path and os.path.exists(reuse_cues_path):
            try:
                with open(reuse_cues_path, "r", encoding="utf-8") as f:
                    cues = [(float(a), float(b), str(c)) for a, b, c in json.load(f)]
            except Exception:
                cues = None
        else:
            cues = None
        if cues is None:
            dur = get_audio_duration(audio_path)
            cues = [(0.1, max(1.0, dur - 0.1), script or subject)]
    else:
        if progress_callback:
            progress_callback(20, "Ses ve altyazılar üretiliyor...")

        rate_pct = int((voice_rate - 1.0) * 100)
        rate_str = f"{rate_pct:+d}%"
        vol_pct = int((voice_volume - 1.0) * 100)
        vol_str = f"{vol_pct:+d}%"

        cues = asyncio.run(generate_audio_and_subtitles_async(
            text=script,
            voice_name=voice_name,
            output_audio=audio_path,
            max_words=max(6, metrics["chars_per_line"] // 6),
            max_chars=metrics["max_chars"],
            rate=rate_str,
            volume=vol_str
        ))

    # Cümle zamanlamalarını sonraki varyantlar için sakla.
    try:
        with open(cues_path, "w", encoding="utf-8") as f:
            json.dump([[a, b, c] for a, b, c in cues], f, ensure_ascii=False)
    except Exception:
        pass

    write_ass_subtitles(
        cues, subtitle_path, width=w, height=h,
        sub_color=sub_color, sub_pos=sub_pos,
        sub_size=sub_size, boxed=sub_box
    )

    # Hizli ses degisimi: altyazisiz ses varyantinda mevcut videonun goruntusu
    # yeniden kodlanmadan kopyalanir, yalnizca yeni ses enjekte edilir.
    # (Kaynak video zaten altyazisiz oldugundan zamanlama sorunu olusmaz.)
    if source_video_path and os.path.exists(source_video_path) and not subtitle_enabled:
        if cancel_requested and cancel_requested():
            raise TaskCancelled()
        if progress_callback:
            progress_callback(80, "Ses hızlıca değiştiriliyor (yeniden kodlama yok)...")
        remux_audio_into_video(
            video_path=source_video_path,
            audio_path=audio_path,
            output_path=final_output,
            task_id=task_id,
            cancel_requested=cancel_requested
        )
        cleanup_temp_files(output_dir, keep=[final_output])
        if progress_callback:
            progress_callback(100, "Tamamlandı!")
        return final_output

    if progress_callback:
        progress_callback(55, "Arka plan materyalleri hazır...")

    # Önce ses süresini hesapla, sonra o süreyi kapatacak kadar Pexels klibi indir
    # (gereksiz indirmeyi önlemek için).
    audio_dur = 30.0
    try:
        audio_dur = get_audio_duration(audio_path)
    except Exception:
        pass

    if custom_bg_media and os.path.exists(custom_bg_media):
        bg_media = custom_bg_media
        is_video = custom_bg_media.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm"))
    elif need_pexels:
        if cancel_requested and cancel_requested():
            raise TaskCancelled()
        query = pexels_query or subject or "education blackboard study"
        orientation = "portrait" if aspect == "9:16" else "landscape"
        # Ortalama ~15 sn'lik klip varsayımıyla süreye yetecek sayıyı hesapla.
        needed = max(2, min(8, int(audio_dur // 15) + 1))
        bg_clips = fetch_pexels_clips(
            query=query, orientation=orientation, outdir=pexels_dir,
            w=w, h=h, max_clips=needed
        )
        if bg_clips:
            cycling = os.path.join(output_dir, "background.mp4")
            built = build_cycling_background(
                bg_clips, audio_dur, cycling, w, h,
                transition=transition, transition_dur=transition_dur
            )
            if built and os.path.exists(built):
                bg_media = built
                is_video = True
            else:
                # Yedek: ilk clip'i döngüye al.
                bg_media = bg_clips[0]
                is_video = True
        else:
            bg_error.append("Pexels'ten görüntü alınamadı")

    if bg_error:
        logger.warning(f"Arka plan uyarısı: {bg_error[0]}")

    if not bg_media:
        bg_path = os.path.join(output_dir, "temp_bg.png")
        create_lecture_background(
            width=w,
            height=h,
            subject=subject,
            bg_style=bg_style if bg_style != "pexels" else "chalkboard",
            output_path=bg_path
        )
        bg_media = bg_path
        is_video = False

    if progress_callback:
        progress_callback(75, "720p video render ediliyor...")

    effective_bgm = bgm_path
    if not effective_bgm and bgm_mode == "random":
        effective_bgm = pick_random_bgm()

    render_video_with_subtitles(
        background_media=bg_media,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        output_video=final_output,
        aspect=aspect,
        is_video_bg=is_video,
        subtitle_enabled=subtitle_enabled,
        bgm_path=effective_bgm,
        bgm_volume=bgm_volume,
        task_id=task_id,
        cancel_requested=cancel_requested
    )

    cleanup_temp_files(output_dir, keep=[final_output])

    if progress_callback:
        progress_callback(100, "Tamamlandı!")

    return final_output


def cleanup_temp_files(directory: str, keep: List[str]):
    """Render sonrasi gecici dosyalari temizler."""
    keep_abs = {os.path.abspath(k) for k in keep}
    try:
        for fname in os.listdir(directory):
            fpath = os.path.join(directory, fname)
            if os.path.abspath(fpath) in keep_abs:
                continue
            if fname.startswith("temp_") or fname.startswith("pexels_"):
                try:
                    os.remove(fpath)
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Temp temizleme hatası ({directory}): {e}")
