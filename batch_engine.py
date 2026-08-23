import json
import os
import glob
import re
import uuid
from typing import Dict, List

from loguru import logger

import task_store
import worker

KEYWORD_PREFIXES = (
    "keywords:", "keyword:", "anahtar kelimeler:", "anahtar kelime:",
    "etiketler:", "etiket:", "terms:", "tags:"
)
TITLE_PREFIXES = ("başlık:", "ders:", "konu:", "title:")


def parse_batch_text(content: str) -> List[Dict[str, str]]:
    """
    '---' veya '===' ile ayrılmış çoklu ders metinlerini ayrıştırır.

    Desteklenen format:
        # 1. Ders: Üslü Sayılar
        Keywords: math study blackboard
        Üslü sayılarda tabanlar aynı iken üsler toplanır...
        ---
        # 2. Ders: Kurtuluş Savaşı
        Etiketler: history vintage library
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
        script_lines = []

        for line in lines:
            low = line.lower()
            if line.startswith("#") or any(low.startswith(p) for p in TITLE_PREFIXES):
                subject = line.lstrip("#").strip()
                for p in TITLE_PREFIXES:
                    if low.startswith(p):
                        subject = line[len(p):].strip()
                        break
            elif any(low.startswith(p) for p in KEYWORD_PREFIXES):
                for p in KEYWORD_PREFIXES:
                    if low.startswith(p):
                        pexels_query = line[len(p):].strip()
                        break
            else:
                script_lines.append(line)

        script = " ".join(script_lines).strip()
        if script:
            items.append({
                "subject": subject,
                "script": script,
                "pexels_query": pexels_query or subject
            })

    return items


def _normalize_item(item: Dict[str, str]) -> Dict[str, str]:
    """Ana projenin alan adlarini da kabul eder (video_subject, video_script...)."""
    low = {}
    for k, v in item.items():
        if isinstance(v, list):
            low[str(k).lower()] = ", ".join(str(x) for x in v)
        elif isinstance(v, (str, int, float)):
            low[str(k).lower()] = str(v)
    return {
        "subject": str(low.get("subject") or low.get("video_subject")
                       or low.get("title") or "").strip(),
        "script": str(low.get("script") or low.get("video_script")
                      or low.get("text") or "").strip(),
        "pexels_query": str(low.get("pexels_query") or low.get("video_terms")
                            or low.get("keywords") or low.get("terms") or "").strip()
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
                       bgm_mode: str = "none",
                       transition: str = "none",
                       transition_dur: float = 0.5) -> List[str]:
    """Her ders için kuyrukta bekleyen bir görev oluşturur ve worker'ı uyandırır."""
    total = len(items)
    task_ids = []
    logger.info(f"Toplu üretim: {total} görev kuyruğa alınıyor...")

    for i, item in enumerate(items, 1):
        item = _normalize_item(item)
        task_id = task_store.create_task(
            task_id=uuid.uuid4().hex,
            subject=item.get("subject") or f"Ders {i}",
            script=item.get("script", ""),
            voice=item.get("voice", voice),
            aspect=item.get("aspect", aspect),
            resolution=item.get("resolution", resolution),
            bg_style=item.get("bg_style", bg_style),
            pexels_query=item.get("pexels_query", ""),
            voice_rate=float(item.get("voice_rate", voice_rate)),
            voice_volume=float(item.get("voice_volume", voice_volume)),
            subtitle_enabled=subtitle_enabled,
            sub_color=sub_color,
            sub_pos=sub_pos,
            sub_size=sub_size,
            sub_box=sub_box,
            sub_bold=sub_bold,
            sub_font=sub_font,
            outline_color=outline_color,
            bgm_mode=bgm_mode,
            transition=transition,
            transition_dur=transition_dur,
            batch_index=i,
            batch_total=total
        )["task_id"]
        task_ids.append(task_id)

    _wake_worker()
    return task_ids


def _wake_worker():
    # dairesel importu onlemek icin gec cagri
    worker._wake.set()
