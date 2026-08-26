import asyncio
import os
import shutil
import sys
from loguru import logger

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import lite_engine
from agent.tools.manifest_builder import ManifestBuilderTool

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)


def run_comprehensive_mpt_variable_tests():
    print("🚀 [Test Başlangıcı] MoneyPrinterTurbo Değişken ve Dinamik Zamanlama Testleri (480p)...")

    # 1. Temel 1.0x Manifestini Oluştur
    builder = ManifestBuilderTool(output_dir=SAMPLE_DIR)
    script = "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu Turan taktiği ile Bizans'ı mağlup etti."
    
    # 2 sahne (Pexels'ten daha önce indirilen yerel klipleri referans alarak internet harcamaz)
    scenes = [
        {
            "title": "Süvari Hücumu",
            "text": "26 Ağustos 1071'de Sultan Alparslan komutasındaki Selçuklu ordusu",
            "duration": 4.5,
            "provider": "pexels",
            "video_id": "9466654"
        },
        {
            "title": "Turan Taktiği",
            "text": "Turan taktiği ile Bizans'ı mağlup etti.",
            "duration": 4.0,
            "provider": "pexels",
            "video_id": "9466137"
        }
    ]

    base_manifest = builder.build_manifest(
        title="Malazgirt Test Paketi",
        script=script,
        scenes=scenes,
        voice_name="tr-TR-AhmetNeural",
        voice_rate=1.0,
        highlight_words=["Sultan Alparslan", "1071'de", "Turan taktiği", "Bizans'ı"],
        target_resolution="480p",
        aspect_ratio="9:16",
        project_id="test_mpt_vars"
    )
    manifest_file = base_manifest["_file_path"]
    print(f"📄 [1.0x Temel Manifest]: {manifest_file}")

    test_cases = [
        {
            "name": "01_hizli_konusma_1.30x",
            "desc": "Konuşma Hızı 1.30x (%30 Hızlı) - Zaman Çizelgesi Otomatik Daraltma",
            "kwargs": {"voice_rate_override": 1.30, "target_resolution": "480p"}
        },
        {
            "name": "02_yavas_konusma_0.85x",
            "desc": "Konuşma Hızı 0.85x (%15 Yavaş) - Zaman Çizelgesi Otomatik Genişletme",
            "kwargs": {"voice_rate_override": 0.85, "target_resolution": "480p"}
        },
        {
            "name": "03_altyazi_ust_konum",
            "desc": "Altyazı Üst Konumda (sub_pos='top')",
            "kwargs": {"sub_pos_override": "top", "target_resolution": "480p"}
        },
        {
            "name": "04_altyazi_orta_konum",
            "desc": "Altyazı Orta Konumda (sub_pos='center')",
            "kwargs": {"sub_pos_override": "center", "target_resolution": "480p"}
        },
        {
            "name": "05_neon_mavi_kutulu_stil",
            "desc": "Neon Mavi Vurgu + Kutulu Altyazı (highlight_color='#38BDF8', boxed=True)",
            "kwargs": {"highlight_color_override": "#38BDF8", "boxed_override": True, "target_resolution": "480p"}
        },
        {
            "name": "06_yatay_16x9_format",
            "desc": "Yatay 16:9 Format (aspect_override='16:9')",
            "kwargs": {"aspect_override": "16:9", "target_resolution": "480p"}
        }
    ]

    results = []
    for tc in test_cases:
        print(f"\n🧪 Test: {tc['name']} -> {tc['desc']}")
        out_video = os.path.join(SAMPLE_DIR, f"{tc['name']}_480p.mp4")
        res = lite_engine.render_from_manifest(
            manifest_data=manifest_file,
            output_path=out_video,
            **tc["kwargs"]
        )

        if res and os.path.exists(res) and os.path.getsize(res) > 1024:
            dest = os.path.join(SHARED_DIR, f"{tc['name']}_480p.mp4")
            shutil.copy2(res, dest)
            size_kb = os.path.getsize(res) // 1024
            dur = lite_engine.get_audio_duration(res)
            print(f"   ✅ [BAŞARILI] {dest} ({size_kb} KB, {dur:.1f}s)")
            results.append({"name": tc["name"], "status": "PASS", "duration": dur, "file": dest})
        else:
            print(f"   ❌ [BAŞARISIZ] {tc['name']}")
            results.append({"name": tc["name"], "status": "FAIL"})

    print("\n" + "="*60)
    print("📊 TEST SONUÇLARI ÖZETİ:")
    for r in results:
        status_icon = "✅" if r["status"] == "PASS" else "❌"
        print(f"{status_icon} {r['name']}: {r.get('file', 'N/A')} (Süre: {r.get('duration', 0):.1f}s)")
    print("="*60)
    return results


if __name__ == "__main__":
    run_comprehensive_mpt_variable_tests()
