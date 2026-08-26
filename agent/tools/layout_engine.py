import os
from typing import List, Tuple, Dict, Optional
from PIL import Image, ImageDraw, ImageFont


def get_font(size: int = 22, bold: bool = False) -> ImageFont.ImageFont:
    candidates = [
        "/system/fonts/Roboto-Bold.ttf" if bold else "/system/fonts/Roboto-Regular.ttf",
        "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans-Bold.ttf" if bold else "/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    """Metni piksel sınırını aşmayacak şekilde kelimelerden böler."""
    words = text.split()
    if not words:
        return []
    
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        try:
            bbox = draw.textbbox((0, 0), test_line, font=font)
            line_w = bbox[2] - bbox[0]
        except Exception:
            line_w = len(test_line) * 14
            
        if line_w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
                current_line = [word]
            else:
                lines.append(word)
                current_line = []
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


class DynamicCardRenderer:
    """
    9:16 Dikey (Shorts/Reels) ve 16:9 Yatay Formatlara tam uyumlu,
    mobil ekranda orantılı duran ve yazıları asla taşmayan kart motoru.
    """

    @staticmethod
    def draw_vertical_story_card(
        badge_text: str,
        title: str,
        rows: List[Tuple[str, str]],
        note: str = "",
        width: int = 640,
        padding: int = 24
    ) -> Image.Image:
        """9:16 Dikey Mobil Ekranlar İçin Orantılı Dikey Bilgi Kartı (Story Widget)."""
        dummy_img = Image.new("RGBA", (width, 100), (0, 0, 0, 0))
        dummy_draw = ImageDraw.Draw(dummy_img)

        title_f = get_font(24, bold=True)
        badge_f = get_font(17, bold=True)
        label_f = get_font(20, bold=True)
        val_f = get_font(19, bold=False)
        note_f = get_font(17, bold=False)

        max_content_w = width - (2 * padding) - 30

        # Dikey satırları hesapla
        processed_rows = []
        calc_y = padding + 85
        for label, val in rows:
            wrapped_val = wrap_text(dummy_draw, val, val_f, max_content_w)
            processed_rows.append((label, wrapped_val))
            calc_y += 34 + (len(wrapped_val) * 28) + 16

        if note:
            wrapped_note = wrap_text(dummy_draw, f"💡 {note}", note_f, max_content_w)
            calc_y += (len(wrapped_note) * 26) + 20

        total_height = max(720, calc_y + padding + 15)

        # Kart Çizimi
        card = Image.new("RGBA", (width, total_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(card)

        # Glassmorphic Dikey Koyu Panel + Altın & Zümrüt Neon Kenarlık
        draw.rounded_rectangle([padding, padding, width - padding, total_height - padding], radius=28, fill=(15, 23, 42, 235), outline=(251, 191, 36, 240), width=3)

        # Rozet (Üst Ortalanmış veya Sol)
        badge_box = [padding + 20, padding + 20, padding + 20 + 210, padding + 58]
        draw.rounded_rectangle(badge_box, radius=12, fill=(6, 78, 59, 255), outline=(52, 211, 153, 220), width=1)
        draw.text((badge_box[0] + 16, badge_box[1] + 6), badge_text, fill=(251, 191, 36, 255), font=badge_f)

        # Başlık
        draw.text((padding + 20, padding + 75), title, fill=(248, 250, 252, 255), font=title_f)

        # Ayırıcı İnce Çizgi
        draw.line([(padding + 20, padding + 115), (width - padding - 20, padding + 115)], fill=(56, 189, 248, 150), width=2)

        # Dikey Blokları Çiz
        cur_y = padding + 130
        for label, wrapped_val_lines in processed_rows:
            row_h = 32 + (len(wrapped_val_lines) * 28) + 10
            row_box = [padding + 16, cur_y, width - padding - 16, cur_y + row_h]
            draw.rounded_rectangle(row_box, radius=14, fill=(30, 41, 59, 245), outline=(56, 189, 248, 200), width=1)

            # Label
            draw.text((row_box[0] + 16, cur_y + 10), label, fill=(251, 191, 36, 255), font=label_f)

            # Value satırları
            v_y = cur_y + 40
            for line in wrapped_val_lines:
                draw.text((row_box[0] + 16, v_y), line, fill=(241, 245, 249, 255), font=val_f)
                v_y += 28

            cur_y += row_h + 16

        # Not
        if note:
            for line in wrapped_note:
                draw.text((padding + 24, cur_y + 4), line, fill=(203, 213, 225, 255), font=note_f)
                cur_y += 26

        return card
