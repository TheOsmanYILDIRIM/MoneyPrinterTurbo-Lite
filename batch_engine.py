import json
import os
import glob
import random
import re
import uuid
from typing import Dict, List, Optional

from loguru import logger

import task_store
import worker

KEYWORD_PREFIXES = (
    "keywords:", "keyword:", "anahtar kelimeler:", "anahtar kelime:",
    "etiketler:", "etiket:", "terms:", "tags:"
)
TITLE_PREFIXES = ("başlık:", "ders:", "konu:", "title:")
VOICE_PREFIXES = ("ses:", "voice:", "seslendirmen:", "speaker:", "ses_modeli:")
HIGHLIGHT_PREFIXES = ("highlight:", "vurgu:", "highlight_words:", "vurgulanan:", "vurgu_kelimeleri:")
COLOR_PREFIXES = ("highlight_color:", "vurgu_renk:", "renk:")


def parse_batch_text(content: str) -> List[Dict[str, str]]:
    """
    '---' veya '===' ile ayrılmış çoklu ders metinlerini ayrıştırır.

    Desteklenen format:
        # 1. Ders: Üslü Sayılar
        Keywords: math study blackboard
        Ses: tr-TR-AhmetNeural
        Vurgu: tabanlar, toplanır, üsler
        Üslü sayılarda tabanlar aynı iken üsler toplanır...
        ---
        # 2. Ders: Kurtuluş Savaşı
        Etiketler: history vintage library
        Ses: tr-TR-EmelNeural
        Amasya Genelgesi milli mücadelenin...
    """
    items = []
    blocks = [b.strip() for b in re.split(r"\n\s*[-=]{3,}\s*\n", content.strip()) if b.strip()]

    for idx, block in enumerate(blocks, 1):
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            continue

        subject = f"Ders {idx}"
        pexels_query = ""
        voice = ""
        highlight_words = ""
        highlight_color = ""
        script_lines = []

        for line in lines:
            low = line.lower()
            if line.startswith("#") or any(low.startswith(p) for p in TITLE_PREFIXES):
                subject = line.lstrip("#").strip()
                for p in TITLE_PREFIXES:
                    if low.startswith(p):
                        subject = line[len(p):].strip()
                        break
            elif any(low.startswith(p) for p in VOICE_PREFIXES):
                for p in VOICE_PREFIXES:
                    if low.startswith(p):
                        voice = line[len(p):].strip()
                        break
            elif any(low.startswith(p) for p in KEYWORD_PREFIXES):
                for p in KEYWORD_PREFIXES:
                    if low.startswith(p):
                        pexels_query = line[len(p):].strip()
                        break
            elif any(low.startswith(p) for p in HIGHLIGHT_PREFIXES):
                for p in HIGHLIGHT_PREFIXES:
                    if low.startswith(p):
                        highlight_words = line[len(p):].strip()
                        break
            elif any(low.startswith(p) for p in COLOR_PREFIXES):
                for p in COLOR_PREFIXES:
                    if low.startswith(p):
                        highlight_color = line[len(p):].strip()
                        break
            else:
                script_lines.append(line)

        script = " ".join(script_lines).strip()
        if script:
            item_dict = {
                "subject": subject,
                "script": script,
                "pexels_query": pexels_query or subject
            }
            if voice:
                item_dict["voice"] = voice
            if highlight_words:
                item_dict["highlight_words"] = highlight_words
            if highlight_color:
                item_dict["highlight_color"] = highlight_color
            items.append(item_dict)

    return items


def _normalize_item(item: Dict[str, str]) -> Dict[str, str]:
    """Ana projenin alan adlarini da kabul eder (video_subject, video_script...)."""
    low = {str(k).lower(): (", ".join(str(x) for x in v) if isinstance(v, list) else str(v)) for k, v in item.items()}
    return {
        "subject": (low.get("subject") or low.get("video_subject") or low.get("title") or "").strip(),
        "script": (low.get("script") or low.get("video_script") or low.get("text") or "").strip(),
        "voice": (low.get("voice") or low.get("ses") or low.get("speaker") or low.get("seslendirmen") or "").strip(),
        "pexels_query": (low.get("pexels_query") or low.get("video_terms") or low.get("keywords") or low.get("terms") or low.get("tags") or "").strip(),

        "highlight_words": low.get("highlight_words") or low.get("highlight") or low.get("vurgu") or low.get("vurgulanan") or "",
        "highlight_color": low.get("highlight_color") or low.get("vurgu_renk") or "",
        "highlight_size": low.get("highlight_size") or ""
    }



def parse_batch_input(input_path_or_content: str) -> List[Dict[str, str]]:
    if os.path.isdir(input_path_or_content):
        items = []
        txt_files = sorted(glob.glob(os.path.join(input_path_or_content, "*.txt"))
                           + glob.glob(os.path.join(input_path_or_content, "*.md")))
        for fpath in txt_files:
            fname = os.path.splitext(os.path.basename(fpath))[0]
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read().strip()
            if content:
                parsed = parse_batch_text(content)
                if parsed:
                    items.extend(parsed)
                else:
                    items.append({"subject": fname.replace("_", " ").title(),
                                  "script": content,
                                  "pexels_query": fname})
        return items

    if os.path.isfile(input_path_or_content):
        with open(input_path_or_content, "r", encoding="utf-8", errors="ignore") as f:
            raw = f.read().strip()
        if input_path_or_content.endswith(".json"):
            try:
                data = json.loads(raw)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict):
                    return [data]
            except Exception:
                pass
        return parse_batch_text(raw)

    stripped = input_path_or_content.strip()
    if stripped.startswith(("[", "{")):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                data = data.get("videos") or data.get("items") or [data]
            if isinstance(data, list):
                items = [_normalize_item(x) for x in data if isinstance(x, dict)]
                return [x for x in items if x["script"]]
        except Exception:
            pass

    return parse_batch_text(input_path_or_content)


def create_batch_tasks(items: List[Dict[str, str]],
                       voice: str = "tr-TR-AhmetNeural",
                       voices: Optional[List[str]] = None,
                       voice_rate: float = 1.0,
                       voice_volume: float = 1.0,
                       aspect: str = "9:16",
                       resolution: str = "720p",
                       bg_style: str = "chalkboard",
                       subtitle_enabled: bool = True,
                       sub_color: str = "#FFFFFF",
                       sub_pos: str = "bottom",
                       sub_size: int = 18,
                       sub_box: bool = False,
                       sub_bold: bool = True,
                       sub_font: str = "Roboto",
                       outline_color: str = "#000000",
                       highlight_words: Optional[any] = None,
                       highlight_color: Optional[str] = None,
                       highlight_size: Optional[int] = None,
                       bgm_mode: str = "none",
                       transition: str = "none",
                       transition_dur: float = 0.5,
                       save_480p: bool = False,
                       batch_id: Optional[str] = None) -> List[str]:
    """Her ders için kuyrukta bekleyen bir görev oluşturur ve worker'ı uyandırır."""
    import time
    total = len(items)
    task_ids = []
    actual_batch_id = batch_id or f"batch_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

    # Çoklu ses havuzu analizi
    voice_pool: List[str] = []
    if voices and isinstance(voices, list):
        voice_pool = [str(v).strip() for v in voices if str(v).strip()]
    elif voice and ("," in voice or isinstance(voice, str)):
        voice_pool = [v.strip() for v in voice.split(",") if v.strip()]

    if voice_pool and len(voice_pool) > 1:
        logger.info(f"Toplu üretim ({actual_batch_id}): {total} görev kuyruğa alınıyor. Çoklu ses havuzu ({len(voice_pool)} ses): {', '.join(voice_pool)}")
    else:
        logger.info(f"Toplu üretim ({actual_batch_id}): {total} görev kuyruğa alınıyor... Varsayılan ses: {voice}")

    for i, item in enumerate(items, 1):
        norm = _normalize_item(item)
        item_hl_words = norm.get("highlight_words") or highlight_words
        item_hl_color = norm.get("highlight_color") or highlight_color
        item_hl_size = int(norm.get("highlight_size")) if norm.get("highlight_size") else highlight_size

        # Ses seçimi: Eğer script özelinde ses varsa onu kullan; yoksa ve çoklu ses havuzu varsa rastgele seç; aksi halde tekli sesi kullan
        if norm.get("voice"):
            task_voice = norm.get("voice")
        elif voice_pool:
            task_voice = random.choice(voice_pool)
        else:
            task_voice = voice or "tr-TR-AhmetNeural"

        task_id = task_store.create_task(
            task_id=uuid.uuid4().hex,
            batch_id=actual_batch_id,
            subject=norm.get("subject") or f"Ders {i}",
            script=norm.get("script", ""),
            voice=task_voice,
            aspect=norm.get("aspect", aspect),
            resolution=norm.get("resolution", resolution),
            save_480p=bool(norm.get("save_480p", save_480p)),
            bg_style=norm.get("bg_style", bg_style),
            pexels_query=norm.get("pexels_query", ""),
            voice_rate=float(norm.get("voice_rate", voice_rate)),
            voice_volume=float(norm.get("voice_volume", voice_volume)),
            subtitle_enabled=subtitle_enabled,
            sub_color=sub_color,
            sub_pos=sub_pos,
            sub_size=sub_size,
            sub_box=sub_box,
            sub_bold=sub_bold,
            sub_font=sub_font,
            outline_color=outline_color,
            highlight_words=item_hl_words,
            highlight_color=item_hl_color,
            highlight_size=item_hl_size,
            bgm_mode=bgm_mode,
            transition=transition,
            transition_dur=transition_dur,
            batch_index=i,
            batch_total=total
        )["task_id"]
        task_ids.append(task_id)

    worker._wake.set()
    return task_ids

