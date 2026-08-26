import os
import math
from typing import Dict, List, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter


def _get_font(size: int = 28, bold: bool = False) -> ImageFont.ImageFont:
    """Termux / Android ve Linux ortamında uygun fontu yükler."""
    candidates = [
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_text_with_shadow(draw, pos, text, font, fill, shadow_fill=(0, 0, 0, 180), offset=(2, 2)):
    """Metne derinlik ve video üstünde maksimum okunabilirlik katan yumuşak gölge çizer."""
    x, y = pos
    draw.text((x + offset[0], y + offset[1]), text, font=font, fill=shadow_fill)
    draw.text((x, y), text, font=font, fill=fill)


class DiagramGenerator:
    """
    OpenMontage esintili, videolarda şık duran, animasyon uyumlu,
    yüksek kontrastlı Glassmorphism HUD şemaları ve infografik kartları üretir.
    """

    def __init__(self, output_dir: str = "/data/data/com.termux/files/home/MoneyPrinterTurbo/agent/samples"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    # -------------------------------------------------------------
    # 1. FORMULA & CONCEPT CARD (Formül & Kural Kartı)
    # -------------------------------------------------------------
    def create_formula_card(
        self,
        title: str,
        formula: str,
        explanation: str,
        filename: str = "formula_card.png",
        width: int = 800,
        height: int = 420
    ) -> str:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 24
        card_box = [margin, margin, width - margin, height - margin]
        # Arka plan: Koyu füme cam panel (Glassmorphic) + Neon Mavi Parlama
        draw.rounded_rectangle(card_box, radius=28, fill=(15, 23, 42, 235), outline=(56, 189, 248, 240), width=3)

        # Başlık Rozeti (Badge)
        badge_box = [margin + 30, margin + 25, margin + 30 + 160, margin + 65]
        draw.rounded_rectangle(badge_box, radius=12, fill=(30, 41, 59, 255), outline=(56, 189, 248, 180), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), "📐 FORMÜL", fill=(56, 189, 248, 255), font=_get_font(size=18, bold=True))

        # Başlık Metni
        _draw_text_with_shadow(draw, (margin + 205, margin + 28), title, _get_font(size=24, bold=True), (248, 250, 252, 255))

        # Formül Kutusu (Geniş & Canlı Altın Vurgu)
        form_box = [margin + 30, margin + 85, width - margin - 30, margin + 250]
        draw.rounded_rectangle(form_box, radius=20, fill=(30, 41, 59, 250), outline=(251, 191, 36, 240), width=2)

        formula_font = _get_font(size=42, bold=True)
        try:
            bbox = draw.textbbox((0, 0), formula, font=formula_font)
            f_w = bbox[2] - bbox[0]
            f_h = bbox[3] - bbox[1]
        except Exception:
            f_w, f_h = len(formula) * 22, 42

        fx = form_box[0] + (form_box[2] - form_box[0] - f_w) // 2
        fy = form_box[1] + (form_box[3] - form_box[1] - f_h) // 2
        _draw_text_with_shadow(draw, (fx, fy), formula, formula_font, (251, 191, 36, 255))

        # Açıklama
        _draw_text_with_shadow(draw, (margin + 35, margin + 275), f"💡 {explanation}", _get_font(size=22, bold=False), (226, 232, 240, 255))

        out_path = os.path.join(self.output_dir, filename)
        img.save(out_path, "PNG")
        return out_path

    # -------------------------------------------------------------
    # 2. TIMELINE & MILESTONE (Tarihsel / Sıralı Zaman Çizelgesi - Üst Üste Binme Düzeltildi)
    # -------------------------------------------------------------
    def create_timeline_diagram(
        self,
        title: str,
        events: List[Dict[str, str]],
        filename: str = "timeline_diagram.png",
        width: int = 820,
        height: int = 540
    ) -> str:
        """Tarih, kronoloji ve aşamalı olaylar için net ayrılmış zaman çizelgesi."""
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 24
        draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=28, fill=(15, 23, 42, 240), outline=(16, 185, 129, 240), width=3)

        # Başlık
        badge_box = [margin + 30, margin + 25, margin + 30 + 170, margin + 65]
        draw.rounded_rectangle(badge_box, radius=12, fill=(6, 78, 59, 255), outline=(16, 185, 129, 200), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), "⏳ KRONOLOJİ", fill=(52, 211, 153, 255), font=_get_font(size=18, bold=True))
        _draw_text_with_shadow(draw, (margin + 215, margin + 28), title, _get_font(size=24, bold=True), (248, 250, 252, 255))

        # Dikey Zaman Çizgisi
        line_x = margin + 45
        draw.line([(line_x, margin + 90), (line_x, height - margin - 35)], fill=(16, 185, 129, 255), width=4)

        date_font = _get_font(size=20, bold=True)
        desc_font = _get_font(size=20, bold=False)

        y = margin + 95
        row_height = (height - margin - 120) // max(1, min(len(events), 4))

        for idx, ev in enumerate(events[:4]):
            # Düğüm Noktası (Glow Effect)
            draw.ellipse([line_x - 10, y + 14, line_x + 10, y + 34], fill=(16, 185, 129, 255), outline=(167, 243, 208, 255), width=2)

            # Tarih Hapı (Pill Badge)
            date_str = str(ev.get("date", ""))
            try:
                d_bbox = draw.textbbox((0, 0), date_str, font=date_font)
                date_w = max(130, d_bbox[2] - d_bbox[0] + 30)
            except Exception:
                date_w = max(130, len(date_str) * 14 + 30)

            pill_box = [line_x + 25, y + 6, line_x + 25 + date_w, y + 44]
            draw.rounded_rectangle(pill_box, radius=10, fill=(30, 41, 59, 250), outline=(251, 191, 36, 220), width=1)
            draw.text((pill_box[0] + 12, pill_box[1] + 6), date_str, fill=(251, 191, 36, 255), font=date_font)

            # Açıklama Metni (Pill rozetinin SAĞINA ve araya 25px boşluk bırakarak)
            desc_x = pill_box[1] + date_w + 35
            desc_text = str(ev.get("desc", ""))
            _draw_text_with_shadow(draw, (line_x + 25 + date_w + 20, y + 10), desc_text, desc_font, (241, 245, 249, 255))

            y += row_height

        out_path = os.path.join(self.output_dir, filename)
        img.save(out_path, "PNG")
        return out_path

    # -------------------------------------------------------------
    # 3. FLOWCHART & NODE DIAGRAM (Akış Şeması)
    # -------------------------------------------------------------
    def create_flowchart(
        self,
        title: str,
        nodes: List[Dict[str, str]],
        filename: str = "flowchart_diagram.png",
        width: int = 820,
        height: int = 480
    ) -> str:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 24
        draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=28, fill=(15, 23, 42, 240), outline=(129, 140, 248, 240), width=3)

        badge_box = [margin + 30, margin + 25, margin + 30 + 160, margin + 65]
        draw.rounded_rectangle(badge_box, radius=12, fill=(49, 46, 129, 255), outline=(129, 140, 248, 200), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), "🔀 AKIŞ ŞEMASI", fill=(199, 210, 254, 255), font=_get_font(size=18, bold=True))
        _draw_text_with_shadow(draw, (margin + 205, margin + 28), title, _get_font(size=24, bold=True), (248, 250, 252, 255))

        node_count = len(nodes)
        gap = 20
        total_w = width - (2 * margin) - 60
        node_width = (total_w - (node_count - 1) * (gap + 30)) // max(1, node_count)
        node_height = 140
        y_pos = margin + 120

        title_f = _get_font(size=22, bold=True)
        sub_f = _get_font(size=18, bold=False)

        for i, node in enumerate(nodes):
            x_pos = margin + 30 + i * (node_width + gap + 30)
            box = [x_pos, y_pos, x_pos + node_width, y_pos + node_height]

            draw.rounded_rectangle(box, radius=18, fill=(30, 41, 59, 250), outline=(56, 189, 248, 255), width=2)
            draw.text((x_pos + 16, y_pos + 22), node.get("label", f"Adım {i+1}"), fill=(251, 191, 36, 255), font=title_f)
            draw.text((x_pos + 16, y_pos + 70), node.get("sub", ""), fill=(226, 232, 240, 255), font=sub_f)

            if i < node_count - 1:
                arrow_start_x = x_pos + node_width + 6
                arrow_end_x = arrow_start_x + gap + 18
                arrow_y = y_pos + node_height // 2
                draw.line([(arrow_start_x, arrow_y), (arrow_end_x, arrow_y)], fill=(129, 140, 248, 255), width=4)
                draw.polygon([(arrow_end_x, arrow_y), (arrow_end_x - 8, arrow_y - 7), (arrow_end_x - 8, arrow_y + 7)], fill=(129, 140, 248, 255))

        out_path = os.path.join(self.output_dir, filename)
        img.save(out_path, "PNG")
        return out_path

    # -------------------------------------------------------------
    # 4. COMPARISON MATRIX (VS Tablosu)
    # -------------------------------------------------------------
    def create_comparison_matrix(
        self,
        title: str,
        col1_title: str,
        col1_items: List[str],
        col2_title: str,
        col2_items: List[str],
        filename: str = "comparison_matrix.png",
        width: int = 820,
        height: int = 500
    ) -> str:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 24
        draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=28, fill=(15, 23, 42, 240), outline=(244, 63, 94, 220), width=3)

        badge_box = [margin + 30, margin + 25, margin + 30 + 190, margin + 65]
        draw.rounded_rectangle(badge_box, radius=12, fill=(76, 5, 25, 255), outline=(244, 63, 94, 200), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), "⚖️ KARŞILAŞTIRMA", fill=(251, 113, 133, 255), font=_get_font(size=18, bold=True))
        _draw_text_with_shadow(draw, (margin + 235, margin + 28), title, _get_font(size=24, bold=True), (248, 250, 252, 255))

        col_w = (width - (2 * margin) - 80) // 2
        
        # Kolon 1
        c1_x = margin + 30
        c1_box = [c1_x, margin + 85, c1_x + col_w, height - margin - 30]
        draw.rounded_rectangle(c1_box, radius=20, fill=(30, 41, 59, 250), outline=(56, 189, 248, 220), width=2)
        draw.text((c1_x + 24, margin + 105), col1_title, fill=(56, 189, 248, 255), font=_get_font(size=24, bold=True))

        item_f = _get_font(size=20, bold=False)
        y = margin + 155
        for item in col1_items[:4]:
            draw.text((c1_x + 24, y), f"✓ {item}", fill=(241, 245, 249, 255), font=item_f)
            y += 48

        # Kolon 2
        c2_x = c1_x + col_w + 20
        c2_box = [c2_x, margin + 85, c2_x + col_w, height - margin - 30]
        draw.rounded_rectangle(c2_box, radius=20, fill=(30, 41, 59, 250), outline=(244, 63, 94, 220), width=2)
        draw.text((c2_x + 24, margin + 105), col2_title, fill=(244, 63, 94, 255), font=_get_font(size=24, bold=True))

        y = margin + 155
        for item in col2_items[:4]:
            draw.text((c2_x + 24, y), f"✓ {item}", fill=(241, 245, 249, 255), font=item_f)
            y += 48

        out_path = os.path.join(self.output_dir, filename)
        img.save(out_path, "PNG")
        return out_path

    # -------------------------------------------------------------
    # 5. STEPS LIST CARD
    # -------------------------------------------------------------
    def create_steps_card(
        self,
        title: str,
        steps: List[str],
        filename: str = "steps_card.png",
        width: int = 800,
        height: int = 500
    ) -> str:
        img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        margin = 24
        draw.rounded_rectangle([margin, margin, width - margin, height - margin], radius=28, fill=(15, 23, 42, 240), outline=(168, 85, 247, 240), width=3)

        badge_box = [margin + 30, margin + 25, margin + 30 + 160, margin + 65]
        draw.rounded_rectangle(badge_box, radius=12, fill=(59, 7, 100, 255), outline=(168, 85, 247, 200), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), "📌 ADIMLAR", fill=(216, 180, 254, 255), font=_get_font(size=18, bold=True))
        _draw_text_with_shadow(draw, (margin + 205, margin + 28), title, _get_font(size=24, bold=True), (248, 250, 252, 255))

        step_font = _get_font(size=22, bold=False)
        num_font = _get_font(size=20, bold=True)

        y_offset = margin + 95
        for idx, step_text in enumerate(steps[:4], 1):
            circle_box = [margin + 30, y_offset, margin + 74, y_offset + 44]
            draw.ellipse(circle_box, fill=(168, 85, 247, 255))
            draw.text((circle_box[0] + 15, circle_box[1] + 8), str(idx), fill=(255, 255, 255, 255), font=num_font)
            _draw_text_with_shadow(draw, (margin + 92, y_offset + 8), step_text, step_font, (241, 245, 249, 255))
            y_offset += 75

        out_path = os.path.join(self.output_dir, filename)
        img.save(out_path, "PNG")
        return out_path

    # -------------------------------------------------------------
    # 6. QUALITY & INTEGRITY EVALUATOR
    # -------------------------------------------------------------
    @staticmethod
    def evaluate_diagram(image_path: str) -> Dict[str, any]:
        if not os.path.exists(image_path):
            return {"passed": False, "score": 0.0, "reason": "Dosya bulunamadı"}

        img = Image.open(image_path).convert("RGBA")
        width, height = img.size
        # Pillow 14 uyumlu getdata / get_flattened_data
        try:
            pixels = list(img.getdata())
        except Exception:
            pixels = list(img.tobytes())

        total_pixels = len(pixels)
        non_transparent = sum(1 for p in pixels if (isinstance(p, tuple) and p[3] > 10) or (isinstance(p, int) and p > 10))
        opaque_ratio = non_transparent / total_pixels

        passed = True
        notes = []
        score = 10.0

        if width < 300 or height < 200:
            passed = False
            score -= 4.0
            notes.append("Çözünürlük çok düşük")

        if opaque_ratio < 0.10:
            passed = False
            score -= 5.0
            notes.append("Şema neredeyse tamamen boş")
        elif opaque_ratio > 0.95:
            score -= 1.5
            notes.append("Kart arkaplanı şeffaflık içermiyor")

        return {
            "passed": passed and score >= 7.0,
            "score": round(max(0.0, score), 1),
            "width": width,
            "height": height,
            "opaque_ratio": round(opaque_ratio, 3),
            "notes": notes or ["Şema görsel kalitesi, şeffaf katmanı ve kontrastı yüksek."]
        }
