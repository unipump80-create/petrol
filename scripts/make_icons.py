"""Генерация иконок PWA: топливная капля на тёмном фоне."""
from pathlib import Path
from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "static" / "icons"
OUT.mkdir(parents=True, exist_ok=True)

BG = (15, 17, 21)        # тёмный фон приложения
ACCENT = (46, 204, 113)  # зелёный «дёшево»
WHITE = (255, 255, 255)


def rounded(size, radius_ratio=0.22):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = int(size * radius_ratio)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=r, fill=BG)
    return img, d


def draw_drop(d, size):
    """Капля топлива: круг + треугольная вершина."""
    cx = size * 0.5
    cy = size * 0.58
    rr = size * 0.20
    # тело капли
    d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=ACCENT)
    # вершина
    tip_y = size * 0.26
    d.polygon([(cx, tip_y), (cx - rr * 0.85, cy), (cx + rr * 0.85, cy)], fill=ACCENT)
    # блик
    hr = rr * 0.30
    d.ellipse([cx - rr * 0.4 - hr, cy - hr, cx - rr * 0.4 + hr, cy + hr], fill=WHITE)


def make(size):
    img, d = rounded(size)
    draw_drop(d, size)
    img.save(OUT / f"icon-{size}.png")
    # maskable: та же картинка с запасом — фон уже на весь квадрат
    return img


for s in (192, 512):
    make(s)
# apple touch icon
make(180).save(OUT / "apple-touch-icon.png") if False else \
    Image.open(OUT / "icon-192.png").resize((180, 180)).save(OUT / "apple-touch-icon.png")

print("icons:", [p.name for p in OUT.iterdir()])
