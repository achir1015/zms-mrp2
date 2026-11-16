"""產生程式圖示：assets/icon.png（1024）、assets/icon.ico、packaging/icon.ico（程式、工作列、桌面捷徑共用）。

設計：深紫到青綠的圓角方塊；上方「資料助秘」字樣；中間白色 BOM 樹（成品 → 三個零件）與齒輪；
右下金色徽章寫「MRP II」。
"""
import math
import os

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S = 1024
FONT = os.path.join(HERE, "assets", "fonts", "NotoSansTC-VF.ttf")


def font(size, weight="Black"):
    f = ImageFont.truetype(FONT, size)
    try:
        f.set_variation_by_name(weight)
    except Exception:
        try:
            f.set_variation_by_axes([900 if weight == "Black" else 700])
        except Exception:
            pass
    return f


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def shadow(img, shape_fn, blur=16, off=(10, 18), alpha=100):
    sh = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    shape_fn(ImageDraw.Draw(sh), off, (0, 0, 0, alpha))
    return Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(blur)))


def gear(d, cx, cy, r, teeth, fill, hole):
    pts = []
    for i in range(teeth * 4):
        a = i * math.pi * 2 / (teeth * 4)
        rr = r if (i % 4) in (0, 1) else r * 0.80
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=fill)
    d.ellipse([cx - r * 0.62, cy - r * 0.62, cx + r * 0.62, cy + r * 0.62], fill=fill)
    d.ellipse([cx - r * 0.28, cy - r * 0.28, cx + r * 0.28, cy + r * 0.28], fill=hole)


def main():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    grad = Image.new("RGBA", (S, S))
    gd = ImageDraw.Draw(grad)
    c1, c2 = (59, 22, 120), (12, 128, 116)
    for y in range(S):
        gd.line([(0, y), (S, y)], fill=lerp(c1, c2, y / S) + (255,))
    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle([40, 40, S - 40, S - 40], radius=220, fill=255)
    img.paste(grad, (0, 0), mask)
    gloss = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    ImageDraw.Draw(gloss).ellipse([-220, -560, S + 220, 400], fill=(255, 255, 255, 30))
    img = Image.alpha_composite(img, Image.composite(gloss, Image.new("RGBA", (S, S)), mask))
    d = ImageDraw.Draw(img)

    # 資料助秘
    d.text((S // 2, 170), "資料助秘", font=font(104), fill=(237, 233, 254, 255), anchor="mm")

    # 背景齒輪（半透明疊上去）
    layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gear(ImageDraw.Draw(layer), 790, 400, 165, 10, (255, 255, 255, 46), (0, 0, 0, 0))
    img = Image.alpha_composite(img, layer)
    d = ImageDraw.Draw(img)

    # BOM 樹：成品 → 三個零件
    line = (226, 232, 240, 255)
    d.line([(512, 380), (512, 455)], fill=line, width=16)
    d.line([(250, 455), (774, 455)], fill=line, width=16)
    for x in (250, 512, 774):
        d.line([(x, 455), (x, 520)], fill=line, width=16)

    def node(x0, y0, w, h, fill, txt=None, tsize=60, tfill=(30, 27, 75, 255)):
        global img
        node.img = shadow(node.img, lambda dd, o, c: dd.rounded_rectangle([x0 + o[0] // 2, y0 + o[1] // 2, x0 + w + o[0] // 2,
                                                                         y0 + h + o[1] // 2], radius=30, fill=c), 14, (12, 16), 90)
        dd = ImageDraw.Draw(node.img)
        dd.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=30, fill=fill)
        if txt:
            dd.text((x0 + w // 2, y0 + h // 2 - 4), txt, font=font(tsize), fill=tfill, anchor="mm")
    node.img = img
    node(362, 250, 300, 135, (255, 255, 255, 255), "成品", 70)
    for x in (250, 512, 774):
        node(x - 105, 515, 210, 120, (196, 181, 253, 255) if x != 512 else (153, 246, 228, 255), "件", 62)
    img = node.img
    d = ImageDraw.Draw(img)

    # 金色 MRP II 徽章
    bx0, by0, bx1, by1 = 200, 700, 824, 900
    img = shadow(img, lambda dd, o, c: dd.rounded_rectangle([bx0 + o[0], by0 + o[1], bx1 + o[0], by1 + o[1]], radius=100,
                                                              fill=c), 18, (8, 18), 110)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=100, fill=(242, 182, 40, 255), outline=(255, 228, 150, 255), width=12)
    d.text(((bx0 + bx1) // 2, (by0 + by1) // 2 - 8), "MRP II", font=font(150), fill=(46, 16, 101, 255), anchor="mm")

    out = os.path.join(HERE, "assets", "icon.png")
    img.save(out)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    for p in (os.path.join(HERE, "packaging", "icon.ico"), os.path.join(HERE, "assets", "icon.ico")):
        img.save(p, sizes=sizes)
    img.resize((256, 256), Image.LANCZOS).save(os.path.join(HERE, "assets", "icon-256.png"))
    print("ok", out)


if __name__ == "__main__":
    main()
