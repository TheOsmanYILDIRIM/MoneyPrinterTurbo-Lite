import asyncio
import os
import re
from typing import Dict, List, Tuple
import edge_tts


class AudioTimerTool:
    """
    Edge-TTS ile seslendirme üretir ve cümle/sahne seviyesinde
    hassas zaman damgaları (timestamps / SRT) çıkarır.
    """

    def __init__(self, output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    async def generate_speech_and_timing(
        self,
        script: str,
        voice: str = "tr-TR-AhmetNeural",
        rate: str = "+0%",
        output_prefix: str = "task_sample"
    ) -> Dict:
        """Edge-TTS ile MP3 üretir ve zaman damgalarını yakalar."""
        audio_file = os.path.join(self.output_dir, f"{output_prefix}_voice.mp3")
        srt_file = os.path.join(self.output_dir, f"{output_prefix}.srt")

        communicate = edge_tts.Communicate(script, voice, rate=rate)
        submaker = edge_tts.SubMaker()

        with open(audio_file, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        srt_content = submaker.get_srt()
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        # Cümle zaman damgalarını ayrıştır
        sentences = [s.strip() for s in re.split(r"[.!?]+", script) if s.strip()]
        total_duration = self._estimate_duration(audio_file)

        return {
            "audio_file": audio_file,
            "srt_file": srt_file,
            "srt_content": srt_content,
            "total_duration": total_duration,
            "sentences_count": len(sentences)
        }

    @staticmethod
    def _estimate_duration(audio_file: str) -> float:
        """Ses dosyasının yaklaşık süresini döner."""
        if not os.path.exists(audio_file):
            return 5.0
        size_bytes = os.path.getsize(audio_file)
        # Edge TTS 24kHz mono MP3 ortalama ~6 KB/saniye
        return round(max(2.0, size_bytes / 6000.0), 2)
