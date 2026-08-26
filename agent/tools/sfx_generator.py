import math
import os
import struct
import wave


def generate_whoosh_sfx(output_path: str, duration: float = 0.6, sample_rate: int = 44100):
    """Sinematik sahne geçişi için rüzgar/whoosh ses efekti üretir (WAV)."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    num_samples = int(duration * sample_rate)
    with wave.open(output_path, "w") as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            # Frekans yükselip alçalır (120 Hz -> 600 Hz -> 150 Hz)
            env = math.sin(math.pi * (t / duration)) ** 2
            freq = 150 + 450 * math.sin(math.pi * (t / duration))
            # Beyaz gürültü + sinüs harmanı
            noise = (math.sin(2 * math.pi * 37 * t) + math.sin(2 * math.pi * freq * t)) * 0.5
            val = int(noise * env * 12000)
            val = max(-32767, min(32767, val))
            wav.writeframes(struct.pack("<h", val))
    return output_path


def generate_sub_impact_sfx(output_path: str, duration: float = 1.0, sample_rate: int = 44100):
    """Video başlangıcı için derin sinematik bas darbesi (Sub Impact) üretir."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    num_samples = int(duration * sample_rate)
    with wave.open(output_path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-4.5 * t)  # Hızlı patlama, yavaş sönümleme
            freq = 75 * math.exp(-3.0 * t) + 35  # 110Hz'den 35Hz'e düşen bas
            val = int(math.sin(2 * math.pi * freq * t) * env * 22000)
            val = max(-32767, min(32767, val))
            wav.writeframes(struct.pack("<h", val))
    return output_path


def generate_pop_ding_sfx(output_path: str, duration: float = 0.35, sample_rate: int = 44100):
    """Vurgulu kelime belirme efekti için parlak 'pop/ding' sesi üretir."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    num_samples = int(duration * sample_rate)
    with wave.open(output_path, "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        for i in range(num_samples):
            t = i / sample_rate
            env = math.exp(-12.0 * t)
            # 880 Hz ve 1760 Hz harmonik kristal tınısı
            val = int((math.sin(2 * math.pi * 880 * t) * 0.7 + math.sin(2 * math.pi * 1760 * t) * 0.3) * env * 16000)
            val = max(-32767, min(32767, val))
            wav.writeframes(struct.pack("<h", val))
    return output_path


def ensure_default_sfx(sfx_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/resource/sfx") -> dict:
    os.makedirs(sfx_dir, exist_ok=True)
    whoosh = os.path.join(sfx_dir, "whoosh.wav")
    impact = os.path.join(sfx_dir, "impact.wav")
    pop = os.path.join(sfx_dir, "pop.wav")

    if not os.path.exists(whoosh):
        generate_whoosh_sfx(whoosh)
    if not os.path.exists(impact):
        generate_sub_impact_sfx(impact)
    if not os.path.exists(pop):
        generate_pop_ding_sfx(pop)

    return {"whoosh": whoosh, "impact": impact, "pop": pop}
