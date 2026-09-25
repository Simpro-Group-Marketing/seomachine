from __future__ import annotations

import math
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "images" / "blog" / "overtime-tracker"
SOURCE_FEATURE = Path(
    r"C:\Users\patrick.grueschow\.codex\generated_images\01a0cf94-b3ff-7ed1-9c0e-4b0dc371d867\call_bCNYEvvgCL5M4mkWX7Zfnwar.png"
)

JOB_DETAIL_REPORT_URL = (
    "https://www.datocms-assets.com/16247/1753905086-clockshark-job-detail-report-summary.webp"
)

FONT_REGULAR = Path(r"C:\Windows\Fonts\segoeui.ttf")
FONT_BOLD = Path(r"C:\Windows\Fonts\segoeuib.ttf")
FONT_SEMIBOLD = Path(r"C:\Windows\Fonts\seguisb.ttf")

TEAL = "#153243"
BLUE = "#005288"
LIGHT_BLUE = "#E8F4FA"
MID_BLUE = "#2D79A0"
ORANGE = "#F49B2F"
INK = "#153243"
MUTED = "#5B6B74"
BG = "#F6FAFC"
WHITE = "#FFFFFF"
LINE = "#D5E5EC"
GREEN = "#2C9B73"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    preferred = FONT_BOLD if bold else FONT_REGULAR
    if bold and FONT_SEMIBOLD.exists():
        preferred = FONT_SEMIBOLD
    if preferred.exists():
        return ImageFont.truetype(str(preferred), size=size)
    return ImageFont.load_default(size=size)


def gradient(size: tuple[int, int], top: str, bottom: str) -> Image.Image:
    width, height = size
    top_rgb = hex_to_rgb(top)
    bottom_rgb = hex_to_rgb(bottom)
    image = Image.new("RGB", size, top_rgb)
    pixels = image.load()
    for y in range(height):
        ratio = y / max(height - 1, 1)
        color = tuple(
            round(top_rgb[i] * (1 - ratio) + bottom_rgb[i] * ratio) for i in range(3)
        )
        for x in range(width):
            pixels[x, y] = color
    return image


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def cover_crop(image: Image.Image, target: tuple[int, int]) -> Image.Image:
    image = image.convert("RGB")
    target_w, target_h = target
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize(
        (math.ceil(src_w * scale), math.ceil(src_h * scale)),
        Image.Resampling.LANCZOS,
    )
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def contain_fit(image: Image.Image, target: tuple[int, int], background: str = WHITE) -> Image.Image:
    image = image.convert("RGBA")
    target_w, target_h = target
    src_w, src_h = image.size
    scale = min(target_w / src_w, target_h / src_h)
    resized = image.resize(
        (max(1, math.floor(src_w * scale)), max(1, math.floor(src_h * scale))),
        Image.Resampling.LANCZOS,
    )
    canvas = Image.new("RGBA", target, background)
    x = (target_w - resized.width) // 2
    y = (target_h - resized.height) // 2
    canvas.alpha_composite(resized, (x, y))
    return canvas


def rounded_mask(size: tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), radius=radius, fill=255)
    return mask


def paste_rounded(
    canvas: Image.Image,
    image: Image.Image,
    xy: tuple[int, int],
    radius: int,
    shadow: bool = True,
) -> None:
    if shadow:
        shadow_layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        x, y = xy
        shadow_draw.rounded_rectangle(
            (x + 2, y + 8, x + image.width + 2, y + image.height + 8),
            radius=radius,
            fill=(0, 0, 0, 70),
        )
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(14))
        canvas.alpha_composite(shadow_layer)
    mask = rounded_mask(image.size, radius)
    canvas.paste(image.convert("RGBA"), xy, mask)


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    max_width: int,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    line_gap: int = 6,
) -> int:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=text_font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=text_font, fill=fill)
        bbox = draw.textbbox((x, y), line, font=text_font)
        y += bbox[3] - bbox[1] + line_gap
    return y


def draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    text_font: ImageFont.FreeTypeFont,
    fill: str,
) -> None:
    bbox = draw.textbbox((0, 0), text, font=text_font)
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    x = box[0] + ((box[2] - box[0]) - width) / 2
    y = box[1] + ((box[3] - box[1]) - height) / 2 - 1
    draw.text((x, y), text, font=text_font, fill=fill)


def draw_centered_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    max_width: int,
    text_font: ImageFont.FreeTypeFont,
    fill: str,
    line_gap: int = 3,
) -> None:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=text_font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_heights = [
        draw.textbbox((0, 0), line, font=text_font)[3]
        - draw.textbbox((0, 0), line, font=text_font)[1]
        for line in lines
    ]
    total_height = sum(line_heights) + line_gap * max(len(lines) - 1, 0)
    y = box[1] + ((box[3] - box[1]) - total_height) / 2
    for line, line_height in zip(lines, line_heights, strict=True):
        bbox = draw.textbbox((0, 0), line, font=text_font)
        width = bbox[2] - bbox[0]
        x = box[0] + ((box[2] - box[0]) - width) / 2
        draw.text((x, y), line, font=text_font, fill=fill)
        y += line_height + line_gap


def draw_arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    fill: str,
    width: int = 4,
) -> None:
    draw.line((start, end), fill=fill, width=width)
    angle = math.atan2(end[1] - start[1], end[0] - start[0])
    size = width * 3
    p1 = (
        end[0] - size * math.cos(angle - math.pi / 6),
        end[1] - size * math.sin(angle - math.pi / 6),
    )
    p2 = (
        end[0] - size * math.cos(angle + math.pi / 6),
        end[1] - size * math.sin(angle + math.pi / 6),
    )
    draw.polygon((end, p1, p2), fill=fill)


def save_webp(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(path, "WEBP", quality=86, method=6)


def create_feature() -> Path:
    source = Image.open(SOURCE_FEATURE).convert("RGB")
    canvas = gradient((1040, 520), TEAL, BLUE).convert("RGBA")
    framed = cover_crop(source, (964, 450))
    paste_rounded(canvas, framed, (38, 35), 25, shadow=True)
    path = OUT_DIR / "overtime-tracker-field-crews-feature.webp"
    save_webp(canvas, path)
    return path


def icon_clock(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    draw.ellipse(
        (cx - 20 * scale, cy - 20 * scale, cx + 20 * scale, cy + 20 * scale),
        outline=color,
        width=4 * scale,
    )
    draw.line((cx, cy, cx, cy - 13 * scale), fill=color, width=4 * scale)
    draw.line((cx, cy, cx + 12 * scale, cy + 7 * scale), fill=color, width=4 * scale)


def icon_rules(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    draw.rounded_rectangle(
        (cx - 18 * scale, cy - 23 * scale, cx + 18 * scale, cy + 23 * scale),
        radius=5 * scale,
        outline=color,
        width=4 * scale,
    )
    for i in range(3):
        y = cy - 12 * scale + i * 12 * scale
        draw.line((cx - 9 * scale, y, cx + 11 * scale, y), fill=color, width=3 * scale)


def icon_alert(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    points = [
        (cx, cy - 24 * scale),
        (cx - 25 * scale, cy + 20 * scale),
        (cx + 25 * scale, cy + 20 * scale),
    ]
    draw.line(points + [points[0]], fill=color, width=4 * scale, joint="curve")
    draw.line((cx, cy - 8 * scale, cx, cy + 6 * scale), fill=color, width=4 * scale)
    draw.ellipse(
        (cx - 2 * scale, cy + 12 * scale, cx + 2 * scale, cy + 16 * scale),
        fill=color,
    )


def icon_approve(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    draw.rounded_rectangle(
        (cx - 22 * scale, cy - 20 * scale, cx + 22 * scale, cy + 20 * scale),
        radius=7 * scale,
        outline=color,
        width=4 * scale,
    )
    draw.line(
        (
            cx - 11 * scale,
            cy + scale,
            cx - 2 * scale,
            cy + 10 * scale,
            cx + 15 * scale,
            cy - 11 * scale,
        ),
        fill=GREEN,
        width=5 * scale,
    )


def icon_jobs(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    draw.rectangle(
        (cx - 24 * scale, cy - 8 * scale, cx + 24 * scale, cy + 20 * scale),
        outline=color,
        width=4 * scale,
    )
    draw.rectangle(
        (cx - 11 * scale, cy - 22 * scale, cx + 11 * scale, cy - 8 * scale),
        outline=color,
        width=4 * scale,
    )
    draw.line((cx - 6 * scale, cy - 8 * scale, cx - 6 * scale, cy + 20 * scale), fill=color, width=3 * scale)
    draw.line((cx + 6 * scale, cy - 8 * scale, cx + 6 * scale, cy + 20 * scale), fill=color, width=3 * scale)


def icon_export(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: str, scale: int = 1) -> None:
    draw.rounded_rectangle(
        (cx - 22 * scale, cy - 19 * scale, cx + 22 * scale, cy + 21 * scale),
        radius=6 * scale,
        outline=color,
        width=4 * scale,
    )
    draw.line((cx - 5 * scale, cy - 7 * scale, cx + 10 * scale, cy + 8 * scale), fill=color, width=4 * scale)
    draw.line((cx + 10 * scale, cy + 8 * scale, cx - 5 * scale, cy + 23 * scale), fill=color, width=4 * scale)
    draw.line((cx - 15 * scale, cy + 8 * scale, cx + 10 * scale, cy + 8 * scale), fill=color, width=4 * scale)


def create_workflow_diagram() -> Path:
    output_size = (1200, 675)
    render_scale = 3
    image = Image.new("RGBA", (output_size[0] * render_scale, output_size[1] * render_scale), BG)
    draw = ImageDraw.Draw(image)
    title_font = font(40 * render_scale, bold=True)
    label_font = font(23 * render_scale, bold=True)
    body_font = font(17 * render_scale)
    small_font = font(18 * render_scale, bold=True)

    def xy(x: int, y: int) -> tuple[int, int]:
        return x * render_scale, y * render_scale

    def box(bounds: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
        return tuple(value * render_scale for value in bounds)

    def distance(value: int) -> int:
        return value * render_scale

    draw.text(xy(58, 48), "Overtime tracking software workflow", font=title_font, fill=INK)
    draw.text(
        xy(60, 105),
        "From field clock-in to payroll export",
        font=font(24 * render_scale),
        fill=MUTED,
    )

    steps = [
        ("1", "Capture hours", "Employee, job, and time"),
        ("2", "Apply rules", "Daily or weekly thresholds"),
        ("3", "Flag overtime", "Exceptions before payroll"),
        ("4", "Review and approve", "Supervisor checks the record"),
        ("5", "Connect to jobs", "Labor by job and task"),
        ("6", "Export payroll", "Approved hours ready"),
    ]
    icon_funcs = [icon_clock, icon_rules, icon_alert, icon_approve, icon_jobs, icon_export]
    cards = [
        (70, 178, 374, 338),
        (448, 178, 752, 338),
        (826, 178, 1130, 338),
        (826, 388, 1130, 548),
        (448, 388, 752, 548),
        (70, 388, 374, 548),
    ]
    arrow_color = "#88AFC0"

    connectors = [
        ((390, 258), (432, 258)),
        ((768, 258), (810, 258)),
        ((978, 354), (978, 372)),
        ((810, 468), (768, 468)),
        ((432, 468), (390, 468)),
    ]
    for start, end in connectors:
        draw_arrow(draw, xy(*start), xy(*end), arrow_color, width=distance(4))

    for idx, (num, label, sub) in enumerate(steps):
        card = box(cards[idx])
        card_color = ORANGE if idx == 2 else MID_BLUE
        shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow)
        shadow_draw.rounded_rectangle(
            (card[0] + distance(4), card[1] + distance(8), card[2] + distance(4), card[3] + distance(8)),
            radius=distance(20),
            fill=(0, 0, 0, 28),
        )
        shadow = shadow.filter(ImageFilter.GaussianBlur(distance(10)))
        image.alpha_composite(shadow)
        draw.rounded_rectangle(card, radius=distance(20), fill=WHITE, outline=LINE, width=distance(2))
        draw.rounded_rectangle(
            (card[0], card[1], card[0] + distance(7), card[3]),
            radius=distance(20),
            fill=card_color,
        )
        draw.rectangle((card[0] + distance(4), card[1], card[0] + distance(12), card[3]), fill=card_color)

        badge = (card[0] + distance(30), card[1] + distance(24), card[0] + distance(74), card[1] + distance(68))
        draw.ellipse(badge, fill=card_color)
        draw_centered_text(draw, num, badge, small_font, WHITE)
        icon_funcs[idx](draw, card[2] - distance(58), card[1] + distance(48), card_color, scale=render_scale)
        draw_wrapped_text(
            draw,
            label,
            (card[0] + distance(30), card[1] + distance(86)),
            distance(248),
            label_font,
            INK,
            line_gap=distance(4),
        )
        draw_wrapped_text(
            draw,
            sub,
            (card[0] + distance(30), card[1] + distance(120)),
            distance(248),
            body_font,
            MUTED,
            line_gap=distance(4),
        )

    band = box((65, 585, 1135, 638))
    draw.rounded_rectangle(band, radius=distance(18), fill="#EAF5F8", outline="#CDE3EA", width=distance(2))
    draw.text(xy(92, 601), "Control point:", font=font(20 * render_scale, bold=True), fill=INK)
    draw.text(
        xy(228, 601),
        "Each step gives the next owner a specific record to check before payroll.",
        font=font(20 * render_scale),
        fill=INK,
    )

    path = OUT_DIR / "overtime-tracking-software-clock-in-to-payroll.webp"
    image = image.resize(output_size, Image.Resampling.LANCZOS)
    save_webp(image, path)
    return path


def download_image(url: str) -> Image.Image:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; seomachine-image-prep/1.0)",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return Image.open(BytesIO(response.read())).convert("RGBA")


def create_report_visual() -> Path:
    source = download_image(JOB_DETAIL_REPORT_URL)
    target = (1200, 675)
    scale = min((target[0] - 60) / source.width, (target[1] - 36) / source.height)
    resized = source.resize(
        (round(source.width * scale), round(source.height * scale)),
        Image.Resampling.LANCZOS,
    )
    image = Image.new("RGBA", target, "#F6F8F9")
    image.alpha_composite(
        resized,
        ((target[0] - resized.width) // 2, (target[1] - resized.height) // 2),
    )

    path = OUT_DIR / "employee-overtime-tracking-by-job.webp"
    save_webp(image, path)
    return path


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    outputs = [create_feature(), create_workflow_diagram(), create_report_visual()]
    for output in outputs:
        with Image.open(output) as check:
            print(f"{output} | {check.size[0]}x{check.size[1]} | {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
