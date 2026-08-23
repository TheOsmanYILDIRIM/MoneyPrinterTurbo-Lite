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

# -----------------------------------------------------------------------------
# Çözünürlük ve Boyut Matrisi (480p'den 4K UHD'ye Kadar Tam Destek)
# -----------------------------------------------------------------------------
RESOLUTIONS = {
    # 720p (HD - Varsayılan mobil / hızlı render)
    "9:16_720p": (720, 1280),
    "16:9_720p": (1280, 720),
    "1:1_720p": (720, 720),
    
    # 1080p (Full HD - YouTube / Shorts Yüksek Kalite)
    "9:16_1080p": (1080, 1920),
    "16:9_1080p": (1920, 1080),
    "1:1_1080p": (1080, 1080),
    
    # 1440p (2K Quad HD)
    "9:16_2k": (1440, 2560),
    "16:9_2k": (2560, 1440),
    "1:1_2k": (1440, 1440),
    
    # 2160p (4K Ultra HD)
    "9:16_4k": (2160, 3840),
    "16:9_4k": (3840, 2160),
    "1:1_4k": (2160, 2160),
    
    # 480p (SD - Ultra Hızlı Taslak)
    "9:16_480p": (480, 854),
    "16:9_480p": (854, 480),
    "1:1_480p": (480, 480),

    # Geriye dönük uyumluluk (Eski doğrudan aspect çağrıları için)
    "9:16": (720, 1280),
    "16:9": (1280, 720),
    "1:1": (720, 720),
}

def resolve_video_dimensions(aspect: str = "9:16", resolution: str = "720p") -> Tuple[int, int]:
    """Format (9:16, 16:9, 1:1) ve Çözünürlük (480p, 720p, 1080p, 2k, 4k) ikilisini çözümler."""
    res_clean = (resolution or "720p").lower().replace(" ", "").replace("fhd", "1080p").replace("hd", "720p").replace("uhd", "4k").replace("qhd", "2k")
    key = f"{aspect}_{res_clean}"
    if key in RESOLUTIONS:
        return RESOLUTIONS[key]
    if aspect in RESOLUTIONS:
        return RESOLUTIONS[aspect]
    return (720, 1280)


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
    """resource/songs/ klasöründen rastgele müzik seçer; boş ise None döner."""
    try:
        if not os.path.isdir(SONGS_DIR):
            return None
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


# sub_size etiketleri -> min(w,h) yüzdesi olarak font boyutu
FONT_SCALE = {12: 0.045, 14: 0.052, 18: 0.066, 22: 0.080, 28: 0.094, 34: 0.110, 40: 0.130}
DEFAULT_FONT_SCALE = 0.066


def compute_subtitle_metrics(width: int, height: int, sub_size: int,
                             boxed: bool) -> dict:
    """Ekrana sığdırma metriklerini çözünürlüğe göre dinamik hesaplar."""
    base = min(width, height)
    scale = FONT_SCALE.get(int(sub_size or 18), DEFAULT_FONT_SCALE)
    fontsize = max(16, round(base * scale))
    usable_width = width * 0.88
    chars_per_line = max(10, int(usable_width / (fontsize * 0.52)))
    return {
        "fontsize": fontsize,
        "chars_per_line": chars_per_line,
        "max_chars": chars_per_line * 2,
        "margin_lr": round(width * 0.06),
        "outline": max(2, round(fontsize * 0.07)),
        "border_style": 3 if boxed else 1
    }


def hex_to_ass_color(hex_str: str, alpha_hex: str = "00") -> str:
    """#RRGGBB formatını ASS &HAABBGGRR formatına çevirir."""
    if not hex_str:
        return "&H00FFFFFF"
    c = hex_str.strip().lstrip("#")
    if len(c) == 3:
        c = "".join([x * 2 for x in c])
    if len(c) == 6:
        r, g, b = c[0:2], c[2:4], c[4:6]
        return f"&H{alpha_hex}{b}{g}{r}"
    return "&H00FFFFFF"


def write_ass_subtitles(cues: List[Tuple[float, float, str]], path: str,
                        width: int, height: int, sub_color: str = "#FFFFFF",
                        sub_pos: str = "bottom", sub_size: int = 18,
                        boxed: bool = False, is_bold: bool = True,
                        font_name: str = "Roboto", outline_color: str = "#000000",
                        outline_width: Optional[int] = None) -> str:
    """Video çözünürlüğüne (720p..4K) tam oturan zengin özelleştirmeli .ass altyazı üretir."""
    m = compute_subtitle_metrics(width, height, sub_size, boxed)

    primary = hex_to_ass_color(sub_color, "00")
    bold_flag = 1 if is_bold else 0

    if sub_pos == "top":
        alignment, margin_v = 8, round(height * 0.08)
    elif sub_pos == "center":
        alignment, margin_v = 5, 0
    else:
        alignment = 2
        margin_v = round(height * (0.10 if height > width else 0.08))

    if boxed:
        ass_outline_color = "&H96000000"  # yarı saydam siyah kutu
        ass_outline_w = round(m["fontsize"] * 0.22)
        shadow_w = 0
    else:
        ass_outline_color = hex_to_ass_color(outline_color or "#000000", "00")
        ass_outline_w = outline_width if outline_width is not None else m["outline"]
        shadow_w = 1

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{font_name},{m['fontsize']},{primary},&H000000FF,{ass_outline_color},&H80000000,{bold_flag},0,0,0,100,100,0,0,{m['border_style']},{ass_outline_w},{shadow_w},{alignment},{m['margin_lr']},{m['margin_lr']},{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for start, end, text in cues:
        text = text.replace("\n", " ").strip()
        if not text:
            continue
        lines.append(f"Dialogue: 0,{format_ass_time(start)},{format_ass_time(end)},Sub,,0,0,0,,{text}\n")
    
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


def extract_search_terms(raw_query: str) -> List[str]:
    """Sorguyu sahne bazlı temiz arama terimleri listesine ayırır."""
    if not raw_query:
        return ["education study blackboard"]
    tr_map = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    cleaned = raw_query.translate(tr_map)
    parts = [re.sub(r"[^a-zA-Z0-9\s]", " ", p).strip() for p in re.split(r"[,;\n\.]+", cleaned)]
    terms = [re.sub(r"\s+", " ", p).strip() for p in parts if len(p.strip()) > 1]
    return terms if terms else ["education study blackboard"]


def clean_search_term(raw_query: str) -> str:
    terms = extract_search_terms(raw_query)
    return terms[0] if terms else "education study blackboard"


def _download_pexels_clip(url: str, output_path: str, w: int, h: int, timeout: int = 30) -> bool:
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
        
        # Hedef çözünürlüğe ölçekle
        cmd = [
            "ffmpeg", "-y", "-i", tmp_path,
            "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-an",
            output_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        return os.path.exists(output_path) and os.path.getsize(output_path) > 1024
    except Exception as e:
        logger.warning(f"Pexels indirme hatası: {e}")
        return False


def select_best_pexels_file(video_files: list, target_w: int, target_h: int) -> Optional[str]:
    """Pexels video dosyaları arasından seçilen çözünürlüğe (4K, 2K, 1080p, 720p) en uygun olanı seçer."""
    if not video_files:
        return None

    target_pixels = target_w * target_h
    best_file = None
    best_diff = float("inf")

    # Öncelik 1: Hedef çözünürlüğü karşılayan veya ona en yakın olan
    for vf in video_files:
        vw = vf.get("width") or 0
        vh = vf.get("height") or 0
        link = vf.get("link")
        if not link or vw <= 0 or vh <= 0:
            continue

        pixels = vw * vh
        diff = abs(pixels - target_pixels)
        if diff < best_diff:
            best_diff = diff
            best_file = vf

    if best_file and best_file.get("link"):
        return best_file.get("link")

    # Fallback: uhd/hd veya ilk link
    for vf in video_files:
        if vf.get("quality") in ("uhd", "hd") and vf.get("link"):
            return vf.get("link")
    return video_files[0].get("link") if video_files else None


def fetch_pexels_clips(query: str, orientation: str = "portrait", outdir: str = ".",
                       w: int = 720, h: int = 1280, max_clips: int = 6) -> List[str]:
    """Çoklu sahne arama terimleri varsa her biri için ayrı video arar ve indirir.
    Böylece tüm video boyunca tek bir klip yerine sahneler değiştikçe zengin videolar kullanılır.
    """
    api_key = settings_manager.get_setting("pexels_api_keys", "").split(",")[0].strip()
    if not api_key:
        logger.warning("Pexels API anahtarı tanımlı değil (Ayarlar'dan ekleyin)")
        return []

    terms = extract_search_terms(query)
    headers = {"Authorization": api_key}
    clips: List[str] = []
    seen_ids = set()

    # Sahne başına düşen klip sayısı
    clips_per_term = max(1, max_clips // len(terms)) if len(terms) > 1 else max_clips

    for term in terms:
        if len(clips) >= max_clips:
            break
        search_q = " ".join(term.split()[:4])
        url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(search_q)}&per_page=8&orientation={orientation}"
        try:
            res = requests.get(url, headers=headers, timeout=8)
            videos = res.json().get("videos", []) if res.status_code == 200 else []
            if not videos:
                continue

            term_added = 0
            for video in videos:
                vid_id = video.get("id")
                if vid_id in seen_ids:
                    continue
                seen_ids.add(vid_id)
                video_files = video.get("video_files", [])

                best_url = select_best_pexels_file(video_files, w, h)
                if not best_url:
                    continue

                out_path = os.path.join(outdir, f"pexels_{len(clips)}.mp4")
                if _download_pexels_clip(best_url, out_path, w, h):
                    clips.append(out_path)
                    term_added += 1
                    if term_added >= clips_per_term or len(clips) >= max_clips:
                        break
        except Exception as e:
            logger.warning(f"Pexels terim '{search_q}' hatası: {e}")

    # Hiç klip bulunamadıysa genel fallback terimleri dene
    if not clips:
        fallback_terms = ["study library", "blackboard education", "office work", "nature landscape", "abstract background"]
        fb_q = random.choice(fallback_terms)
        fb_url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(fb_q)}&per_page=6&orientation={orientation}"
        try:
            r_fb = requests.get(fb_url, headers=headers, timeout=8)
            videos = r_fb.json().get("videos", []) if r_fb.status_code == 200 else []
            for video in videos:
                if len(clips) >= max_clips:
                    break
                video_files = video.get("video_files", [])
                best_url = select_best_pexels_file(video_files, w, h)
                if best_url:
                    out_path = os.path.join(outdir, f"pexels_{len(clips)}.mp4")
                    if _download_pexels_clip(best_url, out_path, w, h):
                        clips.append(out_path)
        except Exception as e:
            logger.warning(f"Pexels fallback hatası: {e}")

    if clips:
        logger.info(f"{len(clips)} Pexels videosu indirildi (Sahne Terimleri: {terms})")
    return clips


def build_cycling_background(clips: List[str], target_duration: float,
                             output_path: str, w: int, h: int,
                             transition: str = "none",
                             transition_dur: float = 0.5) -> Optional[str]:
    """İndirilen farklı klipleri döngüsel ve yumuşak geçişle birleştirir."""
    if not clips:
        return None

    if len(clips) == 1:
        try:
            import shutil
            shutil.copy(clips[0], output_path)
            return output_path
        except Exception:
            return clips[0]

    pool = list(clips)
    ordered: List[str] = []
    total = 0.0
    i = 0
    max_repeats = max(3, len(pool) * 3)
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


def fetch_pexels_video(query: str, orientation: str = "portrait", output_path: str = "pexels_bg.mp4",
                       w: int = 720, h: int = 1280) -> Optional[str]:
    clips = fetch_pexels_clips(query, orientation, os.path.dirname(output_path) or ".", w, h, max_clips=1)
    if clips:
        try:
            import shutil
            shutil.copy(clips[0], output_path)
            return output_path
        except Exception:
            return clips[0]
    return None


async def generate_speech_edge(
    text: str,
    output_path: str,
    voice: str = "tr-TR-AhmetNeural",
    rate: float = 1.0,
    volume: float = 1.0,
    cancel_requested: Optional[Callable[[], bool]] = None
) -> Tuple[str, List[Tuple[float, float, str]]]:
    """Edge-TTS ile ses ve kelime/cümle zamanlamalarını (cues) üretir."""
    if cancel_requested and cancel_requested():
        raise TaskCancelled()

    rate_str = f"{int((rate - 1.0) * 100):+d}%"
    vol_str = f"{int((volume - 1.0) * 100):+d}%"

    communicate = edge_tts.Communicate(text, voice, rate=rate_str, volume=vol_str)
    submaker = edge_tts.SubMaker()

    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if cancel_requested and cancel_requested():
                raise TaskCancelled()
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                submaker.feed(chunk)

    raw_cues = []
    for c in submaker.cues:
        start_s = c.start.total_seconds()
        end_s = c.end.total_seconds()
        raw_cues.append((start_s, end_s, c.value))

    # Cues boşsa süreye göre tahmini böl
    if not raw_cues:
        total_dur = get_audio_duration(output_path)
        words = text.split()
        if words:
            w_dur = total_dur / len(words)
            for i, w in enumerate(words):
                raw_cues.append((i * w_dur, (i + 1) * w_dur, w))

    # Cümleleri mantıklı bloklara birleştir
    refined_cues = []
    curr_words = []
    chunk_start = 0.0
    chunk_end = 0.0
    for s, e, w in raw_cues:
        if not curr_words:
            chunk_start = s
        curr_words.append(w)
        chunk_end = e
        if len(curr_words) >= 4 or len(" ".join(curr_words)) >= 24 or any(w.endswith(p) for p in [".", "!", "?", ","]):
            refined_cues.append((chunk_start, chunk_end, " ".join(curr_words)))
            curr_words = []
    if curr_words:
        refined_cues.append((chunk_start, chunk_end, " ".join(curr_words)))

    return output_path, refined_cues


def generate_background_card(
    subject: str,
    output_path: str,
    width: int = 720,
    height: int = 1280,
    bg_style: str = "chalkboard"
) -> str:
    """Temiz, modern ve şık arka plan görseli üretir."""
    img = Image.new("RGB", (width, height), color=(18, 30, 24))
    draw = ImageDraw.Draw(img)

    colors = {
        "chalkboard": ((16, 42, 31), (28, 68, 50)),
        "dark_slate": ((15, 23, 42), (30, 41, 59)),
        "warm_study": ((38, 24, 18), (68, 42, 30)),
        "midnight_purple": ((24, 16, 42), (48, 28, 78)),
    }
    c_top, c_bot = colors.get(bg_style, colors["chalkboard"])

    # Basit dikey gradyan
    for y in range(height):
        ratio = y / max(1, height)
        r = int(c_top[0] * (1 - ratio) + c_bot[0] * ratio)
        g = int(c_top[1] * (1 - ratio) + c_bot[1] * ratio)
        b = int(c_top[2] * (1 - ratio) + c_bot[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Dekoratif çerçeve ve başlık alanı
    margin = round(width * 0.04)
    draw.rectangle(
        [(margin, margin), (width - margin, height - margin)],
        outline=(255, 255, 255, 30),
        width=max(1, round(width * 0.003))
    )

    # Başlık metni
    try:
        font_size = max(24, round(width * 0.055))
        font = ImageFont.truetype(DEFAULT_FONT_PATH, font_size)
    except Exception:
        font = ImageFont.load_default()

    # Başlık satırlarını kır
    words = subject.split()
    lines = []
    cur = []
    for w in words:
        cur.append(w)
        if len(" ".join(cur)) > 18:
            lines.append(" ".join(cur))
            cur = []
    if cur:
        lines.append(" ".join(cur))

    title_y = round(height * 0.12)
    for line in lines[:3]:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        tx = (width - tw) // 2
        draw.text((tx, title_y), line, fill=(255, 215, 0), font=font)
        title_y += round(font_size * 1.3)

    img.save(output_path, quality=95)
    return output_path


def get_audio_duration(file_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        return float(res.stdout.strip())
    except Exception:
        return 10.0


def render_video_ffmpeg(
    background_media: str,
    audio_path: str,
    subtitle_path: str,
    output_video: str,
    aspect: str = "9:16",
    resolution: str = "720p",
    is_video_bg: bool = False,
    subtitle_enabled: bool = True,
    bgm_path: Optional[str] = None,
    bgm_volume: float = 0.15,
    task_id: Optional[str] = None,
    cancel_requested: Optional[Callable[[], bool]] = None
) -> str:
    width, height = resolve_video_dimensions(aspect, resolution)
    duration = get_audio_duration(audio_path)

    work_dir = os.path.dirname(os.path.abspath(subtitle_path))
    rel_subs = os.path.relpath(subtitle_path, work_dir)
    rel_bg = os.path.relpath(background_media, work_dir)
    rel_audio = os.path.relpath(audio_path, work_dir)
    rel_output = os.path.relpath(output_video, work_dir)

    vf_filters = [f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"]
    has_subs = (subtitle_enabled and os.path.exists(subtitle_path) and os.path.getsize(subtitle_path) > 0)
    if has_subs:
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

    logger.info(f"FFmpeg render ({aspect} @ {resolution} -> {width}x{height})...")

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


def build_lecture_video(
    subject: str,
    script: str,
    voice_name: str = "tr-TR-AhmetNeural",
    voice_rate: float = 1.0,
    voice_volume: float = 1.0,
    aspect: str = "9:16",
    resolution: str = "720p",
    bg_style: str = "chalkboard",
    pexels_query: Optional[str] = None,
    custom_bg_media: Optional[str] = None,
    custom_audio: Optional[str] = None,
    subtitle_enabled: bool = True,
    sub_color: str = "#FFFFFF",
    sub_pos: str = "bottom",
    sub_size: int = 18,
    sub_box: bool = False,
    sub_bold: bool = True,
    sub_font: str = "Roboto",
    outline_color: str = "#000000",
    bgm_path: Optional[str] = None,
    bgm_mode: str = "none",
    bgm_volume: float = 0.15,
    output_dir: Optional[str] = None,
    filename: str = "ders_video.mp4",
    progress_callback: Optional[Callable[[int, str], None]] = None,
    task_id: Optional[str] = None,
    cancel_requested: Optional[Callable[[], bool]] = None,
    reuse_cues_path: Optional[str] = None,
    source_video_path: Optional[str] = None,
    transition: str = "none",
    transition_dur: float = 0.5
) -> str:
    if not output_dir:
        output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    if cancel_requested and cancel_requested():
        raise TaskCancelled()

    audio_path = os.path.join(output_dir, "audio.mp3")
    subtitle_path = os.path.join(output_dir, "subtitle.ass")
    cues_path = os.path.join(output_dir, "subtitle_cues.json")
    final_output = os.path.join(output_dir, filename)

    w, h = resolve_video_dimensions(aspect, resolution)

    bg_media: Optional[str] = None
    is_video = False

    def notify(pct: int, msg: str):
        if progress_callback:
            progress_callback(pct, msg)

    # 1. Seslendirme (TTS)
    if custom_audio and os.path.exists(custom_audio):
        notify(15, "Özel ses dosyası kullanılıyor...")
        import shutil
        shutil.copy(custom_audio, audio_path)
        cues = []
        if reuse_cues_path and os.path.exists(reuse_cues_path):
            with open(reuse_cues_path, "r", encoding="utf-8") as f:
                cues = json.load(f)
        else:
            cues = split_sentence_to_cues(script, 0.0, get_audio_duration(audio_path))
    else:
        notify(15, "Seslendirme üretiliyor (Edge TTS)...")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            _, cues = loop.run_until_complete(
                generate_speech_edge(script, audio_path, voice_name, voice_rate, voice_volume, cancel_requested)
            )
        finally:
            loop.close()

    with open(cues_path, "w", encoding="utf-8") as f:
        json.dump(cues, f, ensure_ascii=False)

    if cancel_requested and cancel_requested():
        raise TaskCancelled()

    # 2. Altyazı (.ass)
    if subtitle_enabled and cues:
        notify(35, "Altyazılar senkronize ediliyor...")
        write_ass_subtitles(
            cues, subtitle_path, w, h,
            sub_color=sub_color, sub_pos=sub_pos, sub_size=sub_size,
            boxed=sub_box, is_bold=sub_bold, font_name=sub_font,
            outline_color=outline_color
        )

    # 3. Arka Plan Materyali
    need_pexels = (not custom_bg_media) and (bg_style == "pexels" or bool(pexels_query))
    pexels_dir = output_dir

    if custom_bg_media and os.path.exists(custom_bg_media):
        notify(50, "Özel arka plan materyali kullanılıyor...")
        bg_media = custom_bg_media
        is_video = bg_media.lower().endswith((".mp4", ".mov", ".mkv", ".webm"))
    elif need_pexels:
        notify(45, "Pexels stok videoları aranıyor ve indiriliyor...")
        orientation = "portrait" if aspect == "9:16" else ("square" if aspect == "1:1" else "landscape")
        query = pexels_query or subject or "education blackboard study"
        audio_dur = get_audio_duration(audio_path)

        bg_clips = fetch_pexels_clips(
            query=query, orientation=orientation, outdir=pexels_dir,
            w=w, h=h, max_clips=6
        )

        if bg_clips:
            notify(55, "Video sahneleri ve geçiş efektleri birleştiriliyor...")
            bg_target = os.path.join(output_dir, "background.mp4")
            bg_media = build_cycling_background(
                bg_clips, audio_dur, bg_target, w, h,
                transition=transition, transition_dur=transition_dur
            )
            if bg_media:
                is_video = True

        if not bg_media:
            notify(55, "Pexels bulunamadı, şablon arka plan üretiliyor...")
            bg_media = os.path.join(output_dir, "bg_card.png")
            generate_background_card(subject, bg_media, w, h, bg_style="chalkboard")
            is_video = False
    else:
        notify(50, "Ders şablonu arka planı hazırlanıyor...")
        bg_media = os.path.join(output_dir, "bg_card.png")
        generate_background_card(subject, bg_media, w, h, bg_style=bg_style)
        is_video = False

    if cancel_requested and cancel_requested():
        raise TaskCancelled()

    # 4. Müzik (BGM)
    active_bgm = None
    if bgm_mode == "random":
        active_bgm = pick_random_bgm()
    elif bgm_path and os.path.exists(bgm_path):
        active_bgm = bgm_path

    # 5. FFmpeg Render
    notify(70, f"Video render ediliyor ({w}x{h} @ {resolution})...")
    render_video_ffmpeg(
        background_media=bg_media,
        audio_path=audio_path,
        subtitle_path=subtitle_path,
        output_video=final_output,
        aspect=aspect,
        resolution=resolution,
        is_video_bg=is_video,
        subtitle_enabled=subtitle_enabled,
        bgm_path=active_bgm,
        bgm_volume=bgm_volume,
        task_id=task_id,
        cancel_requested=cancel_requested
    )

    notify(100, "Tamamlandı!")
    return final_output
