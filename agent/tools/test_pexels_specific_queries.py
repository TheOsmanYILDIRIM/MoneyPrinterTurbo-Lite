import json
import os
import shutil
import requests
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import settings_manager

SAMPLE_DIR = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples/pexels_query_test"
SHARED_DIR = "/sdcard/Documents/MoneyPrinterTurbo_Samples/pexels_arama_testi"
os.makedirs(SAMPLE_DIR, exist_ok=True)
os.makedirs(SHARED_DIR, exist_ok=True)

API_KEY = settings_manager.get_setting("pexels_api_keys", "").split(",")[0].strip()


def test_query(query: str, category_name: str, max_results: int = 4):
    print(f"\n🔍 Arama: '{query}' ({category_name})")
    headers = {"Authorization": API_KEY}
    url = f"https://api.pexels.com/videos/search?query={requests.utils.quote(query)}&per_page={max_results}&orientation=portrait"
    
    res = requests.get(url, headers=headers, timeout=12)
    if res.status_code != 200:
        print(f"❌ Pexels API Hatası ({res.status_code}): {res.text}")
        return []

    data = res.json()
    videos = data.get("videos", [])
    total_results = data.get("total_results", 0)
    print(f"   -> Toplam Bulunan Video Sayısı: {total_results} adet (İlk {len(videos)} inceleniyor)")

    cat_folder = os.path.join(SHARED_DIR, category_name.replace(" ", "_"))
    os.makedirs(cat_folder, exist_ok=True)

    results_info = []
    for idx, v in enumerate(videos, 1):
        v_id = v.get("id")
        v_url = v.get("url", "")
        # URL'den başlık slug'ı çıkar
        slug = v_url.split("/video/")[-1].split("/")[0] if "/video/" in v_url else "video"
        title = slug.replace("-", " ")
        image_url = v.get("image", "")
        duration = v.get("duration", 0)

        # Thumbnail'i indir
        t_path = os.path.join(cat_folder, f"{idx}_{v_id}_{slug[:25]}.jpg")
        try:
            t_res = requests.get(image_url, timeout=8)
            if t_res.status_code == 200:
                with open(t_path, "wb") as f:
                    f.write(t_res.content)
        except Exception:
            t_path = "indirilemedi"

        info = {
            "index": idx,
            "id": v_id,
            "title": title,
            "duration": f"{duration}s",
            "thumbnail_file": t_path
        }
        results_info.append(info)
        print(f"      [{idx}] ID: {v_id} | Süre: {duration}s | Başlık: '{title}'")
        print(f"          🖼️ Küçük Resim: {t_path}")

    return results_info


def run_all_pexels_tests():
    queries = [
        # Sahne 1 Adayları: Ordu / Karşılaşma / Savaş Alanı
        ("ancient battlefield soldiers", "01_Savas_Alani"),
        ("medieval armor swords army", "01_Zirh_ve_Kilic_Ordusu"),
        
        # Sahne 2 Adayları: Atlı Süvari / Hücum / Toz Duman
        ("cavalry charge horses galloping", "02_Suvari_Hucumu"),
        ("running horses dust storm", "02_Kosan_Atlar_Toz_Duman"),
        
        # Sahne 3 Adayları: Tarihi Kale / Gün Batımı / Zafer Ovasi
        ("ancient fortress sunrise landscape", "03_Tarihi_Kale_Gun_Dogumu"),
        ("epic medieval castle mountain landscape", "03_Dramatik_Kale_ve_Daglari")
    ]

    summary = {}
    for q, cat in queries:
        summary[cat] = test_query(q, cat, max_results=3)

    summary_file = os.path.join(SHARED_DIR, "arama_sonuclari_raporu.json")
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"\n📁 Tüm arama sonuçları ve küçük resimler kaydedildi: {SHARED_DIR}")


if __name__ == "__main__":
    run_all_pexels_tests()
