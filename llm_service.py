"""Lite LLM servisi - ana projedeki promptlarla birebir ayni, saf REST cagrilari."""
import json
import re
from typing import Dict, List, Optional

import requests
from loguru import logger

import settings_manager

# Ana projeden (app/services/llm.py) birebir alinmis prompt:
DEFAULT_SCRIPT_SYSTEM_PROMPT = """
# Role: Video Script Generator

## Goals:
Generate a script for a video, depending on the subject of the video.

## Constrains:
1. the script is to be returned as a string with the specified number of paragraphs.
2. do not under any circumstance reference this prompt in your response.
3. get straight to the point, don't start with unnecessary things like, "welcome to this video".
4. you must not include any type of markdown or formatting in the script, never use a title.
5. only return the raw content of the script.
6. do not include "voiceover", "narrator" or similar indicators of what should be spoken at the beginning of each paragraph or line.
7. you must not mention the prompt, or anything about the script itself. also, never talk about the amount of paragraphs or lines. just write the script.
8. respond in the same language as the video subject.
""".strip()

PROVIDER_BASE_URLS = {
    "openai": ("https://api.openai.com/v1", "openai_api_key"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta", "gemini_api_key"),
    "groq": ("https://api.groq.com/openai/v1", "groq_api_key"),
    "deepseek": ("https://api.deepseek.com/v1", "deepseek_api_key"),
}


def _clean_script(response: str) -> str:
    """Ana projedeki format_response ile ayni temizlik."""
    response = response.replace("*", "").replace("#", "")
    response = re.sub(r"<think\b[^>]*>.*?</think>", "", response,
                      flags=re.IGNORECASE | re.DOTALL)
    response = re.sub(r"\[.*?\]", "", response)
    response = re.sub(r"\(.*?\)", "", response)
    return "\n\n".join(p for p in response.split("\n\n") if p.strip()).strip()


def build_script_prompt(video_subject: str, language: str = "",
                        paragraph_number: int = 1,
                        extra_requirements: str = "") -> str:
    prompt = DEFAULT_SCRIPT_SYSTEM_PROMPT
    prompt += f"""

# Initialization:
- video subject: {video_subject}
- number of paragraphs: {max(1, min(10, int(paragraph_number or 1)))}"""
    if language:
        prompt += f"\n- language: {language}"
    if extra_requirements:
        prompt += f"\n\n# Additional User Requirements:\n{extra_requirements}"
    return prompt


def _post_json(url: str, payload: dict, headers: dict, timeout: int = 90) -> dict:
    res = requests.post(url, json=payload, headers=headers, timeout=timeout)
    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")
    return res.json()


def chat_completion(provider: str, model: str, prompt: str) -> str:
    provider = (provider or "").lower().strip()
    if provider not in PROVIDER_BASE_URLS:
        raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")

    base_url, key_name = PROVIDER_BASE_URLS[provider]
    api_key = str(settings_manager.get_setting(key_name, "")).strip()
    if not api_key:
        raise ValueError(f"{key_name} tanımlı değil (Ayarlar'dan ekleyin)")

    if provider == "gemini":
        url = f"{base_url}/models/{model}:generateContent?key={requests.utils.quote(api_key)}"
        data = _post_json(url, {"contents": [{"parts": [{"text": prompt}]}]}, {})
        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise ValueError(f"[gemini] beklenmeyen yanıt: {str(data)[:200]}") from e
        return content

    url = f"{base_url}/chat/completions"
    data = _post_json(url, {
        "model": model,
        "messages": [{"role": "user", "content": prompt}]
    }, {"Authorization": f"Bearer {api_key}"})
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise ValueError(f"[{provider}] beklenmeyen yanıt: {str(data)[:200]}") from e
    return content


def generate_script(provider: str, model: str, subject: str, language: str = "",
                    paragraph_number: int = 1, extra_requirements: str = "",
                    gen_terms: bool = True) -> Dict[str, object]:
    """Ana projenin generate_script + generate_terms akisi."""
    if not subject.strip():
        raise ValueError("Konu boş olamaz")

    script_raw = chat_completion(provider, model,
                                 build_script_prompt(subject, language,
                                                     paragraph_number,
                                                     extra_requirements))
    script = _clean_script(script_raw)
    if not script:
        raise ValueError("Model boş script döndürdü")

    result: Dict[str, object] = {"script": script, "terms": []}
    if gen_terms:
        try:
            result["terms"] = generate_terms(provider, model, subject, script)
        except Exception as e:
            logger.warning(f"Terms üretilemedi: {e}")
            result["terms"] = []
    return result


def generate_terms(provider: str, model: str, video_subject: str,
                   video_script: str, amount: int = 5) -> List[str]:
    """Ana projedeki terms promptunun birebir kopyasi."""
    output_example = ('["search term 1", "search term 2", "search term 3",'
                      '"search term 4", "search term 5"]')
    prompt = f"""
# Role: Video Search Terms Generator

## Goals:
Generate {amount} search terms for stock videos, depending on the subject of a video.

## Constrains:
1. the search terms are to be returned as a json-array of strings.
2. each search term should consist of 1-3 words, always add the main subject of the video.
3. you must only return the json-array of strings. you must not return anything else. you must not return the script.
4. the search terms must be related to the subject of the video.
5. reply with english search terms only.

## Output Example:
{output_example}

## Context:
### Video Subject
{video_subject}

### Video Script
{video_script}

Please note that you must use English for generating video search terms; Chinese is not accepted.
""".strip()

    raw = chat_completion(provider, model, prompt)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-zA-Z0-9]*\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw).strip()
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end > start:
        raw = raw[start:end + 1]
    terms = json.loads(raw)
    return [str(t).strip() for t in terms if str(t).strip()][:amount]


def list_models(provider: str) -> List[Dict[str, str]]:
    """Saglayicidan kullanilabilir modelleri ceker."""
    provider = (provider or "").lower().strip()
    if provider not in PROVIDER_BASE_URLS:
        raise ValueError(f"Bilinmeyen sağlayıcı: {provider}")
    base_url, key_name = PROVIDER_BASE_URLS[provider]
    api_key = str(settings_manager.get_setting(key_name, "")).strip()
    if not api_key:
        raise ValueError(f"{key_name} tanımlı değil")

    if provider == "gemini":
        url = f"{base_url}/models?key={requests.utils.quote(api_key)}&pageSize=100"
        res = requests.get(url, timeout=20)
        if res.status_code != 200:
            raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")
        models = []
        for m in res.json().get("models", []):
            name = (m.get("name") or "").removeprefix("models/")
            if not name or "embedding" in name or "aqa" in name:
                continue
            methods = m.get("supportedGenerationMethods", [])
            if methods and "generateContent" not in methods:
                continue
            models.append({"id": name, "label": m.get("displayName") or name})
        return sorted(models, key=lambda x: x["id"])

    url = f"{base_url}/models"
    res = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
    if res.status_code != 200:
        raise RuntimeError(f"HTTP {res.status_code}: {res.text[:300]}")
    models = []
    for m in res.json().get("data", []):
        mid = m.get("id") or ""
        if mid and "embed" not in mid and "whisper" not in mid and "tts" not in mid \
                and "dall-e" not in mid and "moderation" not in mid:
            models.append({"id": mid, "label": mid})
    return sorted(models, key=lambda x: x["id"])


def available_providers() -> List[Dict[str, str]]:
    """Kayitli anahtari olan saglayicilar."""
    out = []
    for pid, (_, key_name) in PROVIDER_BASE_URLS.items():
        if str(settings_manager.get_setting(key_name, "")).strip():
            out.append({"id": pid, "key_field": key_name})
    return out
