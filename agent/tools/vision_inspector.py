import os
import re
from typing import Dict, List, Tuple, Optional
from loguru import logger
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import settings_manager


class DynamicSceneIntentAnalyzer:
    """
    Herhangi bir kategorizasyona bağımlı kalmadan, senaryo metnini doğrudan analiz ederek
    o sahneye özel 'Pozitif Görsel Hedefler' ve 'Yasaklı Negatif Unsurlar' türeten dinamik motor.
    """

    # Evrensel görsel gürültü / istenmeyen genel modern unsurlar
    UNIVERSAL_NEGATIVE_DEFAULTS = ["party", "nightclub", "supermarket", "traffic jam", "car interior"]

    @classmethod
    def analyze_scene_intent(cls, scene_text: str, topic_context: str = "") -> Dict:
        """Metinden doğrudan sahnenin görsel sözleşmesini (Visual Contract) çıkarır."""
        clean_text = scene_text.lower()
        combined = f"{topic_context} {scene_text}".lower()

        # 1. Pozitif Görsel İpuçlarını Çıkar
        # Türkçe anahtar kavramları İngilizce karşılıklarıyla zenginleştir
        concept_map = {
            "traverten": ["travertine terraces", "white mineral pools", "thermal springs"],
            "karstik": ["limestone canyon", "cave formations", "natural mineral water"],
            "kanyon": ["deep canyon", "rocky gorge", "river canyon"],
            "vadi": ["green valley", "river valley landscape"],
            "akdeniz": ["mediterranean coast", "turquoise sea", "sunny coastal mountains"],
            "karadeniz": ["cloudy green mountains", "tea plantation", "lush misty forest"],
            "dağ": ["majestic mountain peaks", "snowy alpine range", "mountain ridge"],
            "volkan": ["volcano peak", "crater lake", "basalt rocks"],
            "şelale": ["waterfall cascade", "forest waterfall", "rushing stream"],
            "fay": ["earth fault line", "geological rock layers", "tectonic landscape"],
            "baraj": ["hydroelectric dam", "reservoir water lake"],
            "tarım": ["aerial farmland", "golden wheat field", "green crop fields"],
            "göç": ["migrating birds", "caravan trail", "aerial road travel"],
            "deprem": ["seismograph", "earthquake simulation", "rock debris"],
            "anayasa": ["constitution book", "law gavel", "justice scale"],
            "meclis": ["parliament chamber", "national assembly", "capitol dome"],
            "seçim": ["voting ballot box", "election vote", "democracy polling"],
            "mahkeme": ["courtroom interior", "judge gavel on desk", "scales of justice"],
            "hakim": ["judge in court", "gavel striking block"],
            "savaş": ["ancient battlefield", "smoke and dust", "medieval combat"],
            "süvari": ["galloping horses", "cavalry charge in field", "horses dust"],
            "kale": ["ancient fortress", "castle on mountain", "stone citadel"],
            "fetih": ["citadel sunrise", "victory monument", "historic banner"],
            "matematik": ["blackboard chalk equations", "geometric shapes drawing", "math formulas"],
            "asal": ["numbers on blackboard", "math calculations"],
            "geometri": ["compass ruler drawing", "geometric 3d shapes", "architectural blueprint"],
            "deney": ["laboratory tubes", "scientist with microscope", "chemical reaction"],
            "uzay": ["galaxy cosmos", "nebula stars", "telescope view planets"],
            "hücre": ["microscopic cell biology", "dna double helix structure"]
        }

        positive_targets = []
        for kw, targets in concept_map.items():
            if kw in combined:
                positive_targets.extend(targets)

        # Eğer özel kavram bulunamazsa metindeki en uzun kelimeleri arama terimi yap
        if not positive_targets:
            words = [w.strip(".,!?:;'\"") for w in scene_text.split() if len(w) > 3]
            positive_targets = [" ".join(words[:3]), "cinematic documentary landscape"]

        # 2. Negatif Kısıtlamaları Çıkar (Sahne neye aitse onun zıttı yasaklanır)
        negatives = list(cls.UNIVERSAL_NEGATIVE_DEFAULTS)
        
        # Doğa/Coğrafya ise ofis ve savaş yasak
        if any(w in combined for w in ["dağ", "ova", "kanyon", "traverten", "akarsu", "vadi", "göl", "orman", "deniz", "iklim"]):
            negatives.extend(["office meeting", "sword battle", "gun", "laptop typing", "indoor studio"])

        # Hukuk/Vatandaşlık ise savaş, plaj, vahşi doğa yasak
        if any(w in combined for w in ["anayasa", "mahkeme", "tbmm", "hukuk", "yargı", "kanun", "seçim"]):
            negatives.extend(["battle", "sword", "gun", "beach party", "wild animals", "jungle"])

        # Tarih ise modern teknolojiler yasak
        if any(w in combined for w in ["savaş", "selçuklu", "osmanlı", "alparslan", "ortaçağ", "fetih", "kale"]):
            negatives.extend(["modern car", "skyscraper", "smartphone", "gun rifle", "traffic"])

        return {
            "scene_text": scene_text,
            "positive_targets": positive_targets[:4],
            "search_query": positive_targets[0] if positive_targets else "scenic nature",
            "negative_constraints": list(set(negatives))
        }


class VisionInspectorTool:
    """
    Dinamik Senaryo ve Sahne İnceleyicisi.
    Metnin içeriğini analiz eder, sahneye özel görsel gereksinimleri çıkarır
    ve Pexels video adaylarını bu sözleşmeye göre puanlar.
    """

    def __init__(self):
        self.gemini_key = settings_manager.get_setting("gemini_api_keys", "") or os.environ.get("GEMINI_API_KEY")

    def inspect_visual_candidate(
        self,
        scene_text: str,
        video_metadata: Dict,
        topic_context: str = "",
        thumbnail_path_or_url: Optional[str] = None
    ) -> Tuple[float, str]:
        """Aday videoyu dinamik sahne sözleşmesine göre puanlar."""
        intent = DynamicSceneIntentAnalyzer.analyze_scene_intent(scene_text, topic_context)

        v_title = video_metadata.get("video_title", "").lower()
        v_tags = [str(t).lower() for t in video_metadata.get("tags", [])]
        combined_meta = f"{v_title} {' '.join(v_tags)}"

        # 1. Negatif Kısıt Kontrolü
        for neg in intent["negative_constraints"]:
            if re.search(rf"\b{re.escape(neg)}\b", combined_meta):
                return (
                    1.5,
                    f"❌ [İÇERİK DIŞI] Sahneye aykırı unsur tespit edildi: '{neg}' (Video: '{v_title}')"
                )

        # 2. Pozitif Hedef Eşleşmesi
        matched_targets = []
        for target in intent["positive_targets"]:
            for word in target.split():
                if len(word) > 3 and word in combined_meta:
                    matched_targets.append(word)

        matched_targets = list(dict.fromkeys(matched_targets))

        score = 5.0
        if matched_targets:
            score += min(4.5, len(matched_targets) * 1.5)
            reason = f"Görsel hedef eşleşti: {', '.join(matched_targets[:3])}"
        else:
            score += 1.0
            reason = "Genel görsel uyumu"

        final_score = min(10.0, max(1.0, round(score, 1)))
        return (final_score, f"✅ Skor: {final_score}/10 -> {reason}")

    def curate_best_visual(
        self,
        scene_text: str,
        initial_keywords: str = "",
        topic_context: str = "",
        search_tool: any = None,
        max_retries: int = 2
    ) -> Tuple[Dict, List[Dict]]:
        """Dinamik sahne analiziyle en doğru stok videoyu bulur ve seçer."""
        intent = DynamicSceneIntentAnalyzer.analyze_scene_intent(scene_text, topic_context)
        query = initial_keywords or intent["search_query"]

        if hasattr(search_tool, "search_pexels_thumbnails"):
            candidates = search_tool.search_pexels_thumbnails(query, per_page=6)
        else:
            candidates = search_tool.search_video_thumbnails(query, max_results=6)
        scored_list = []

        for cand in candidates:
            score, reason = self.inspect_visual_candidate(
                scene_text=scene_text,
                video_metadata=cand,
                topic_context=topic_context,
                thumbnail_path_or_url=cand.get("thumbnail_url")
            )
            scored_list.append({
                "candidate": cand,
                "score": score,
                "reasoning": reason
            })

        scored_list.sort(key=lambda x: x["score"], reverse=True)

        if scored_list and scored_list[0]["score"] >= 6.5:
            return scored_list[0]["candidate"], scored_list

        if max_retries > 0 and len(intent["positive_targets"]) > 1:
            alt_query = intent["positive_targets"][1]
            logger.info(f"Yetersiz skor, alternatif dinamik arama: '{alt_query}'")
            return self.curate_best_visual(scene_text, alt_query, topic_context, search_tool, max_retries - 1)

        fallback = candidates[0] if candidates else {"video_id": None, "video_title": "default"}
        return fallback, scored_list
