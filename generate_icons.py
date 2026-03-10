"""
generate_icons.py
Run: py generate_icons.py
Requires: pip install pillow

Outputs:
  server_icon.png  — central node connected to 4 smaller nodes
  client_icon.png  — device sending arrow to server
  server_icon.ico  — multi-size ICO for PyInstaller
  client_icon.ico  — multi-size ICO for PyInstaller
"""

from PIL import Image, ImageDraw
import math

# ── Colour palette ─────────────────────────────
BG          = (0, 0, 0, 0)           # transparent
DARK        = (30,  36,  48, 255)    # dark grey node fill
DARK_STROKE = (50,  60,  78, 255)    # slightly lighter border
BLUE        = (59, 130, 246, 255)    # soft blue  #3b82f6
BLUE_LIGHT  = (96, 165, 250, 255)    # lighter blue #60a5fa
WHITE       = (241, 245, 249, 255)   # near-white for highlights
LINE        = (59, 130, 246, 180)    # semi-transparent blue line


def aa_circle(draw, cx, cy, r, fill, outline=None, width=2):
    """Draw a filled circle with optional outline."""
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=fill)
    if outline:
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=outline, width=width)


def aa_rect(draw, x0, y0, x1, y1, r, fill, outline=None, width=2):
    """Draw a rounded rectangle."""
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill)
    if outline:
        draw.rounded_rectangle([x0, y0, x1, y1], radius=r, outline=outline, width=width)


def draw_server_icon(size=256):
    """
    Central large rounded-square node connected by lines
    to 4 smaller circular nodes at top, right, bottom, left.
    """
    img  = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    pad    = size * 0.08

    # ── Centre node (rounded square)
    cn  = int(size * 0.22)   # half-size of centre node
    cr  = int(size * 0.06)   # corner radius
    aa_rect(draw,
            cx-cn, cy-cn, cx+cn, cy+cn,
            cr, fill=BLUE, outline=BLUE_LIGHT, width=max(1, size//64))

    # ── Small node radius and orbit radius
    sn   = int(size * 0.085)   # small node radius
    orb  = int(size * 0.34)    # distance from centre to small node centre

    positions = [
        (cx,       cy - orb),   # top
        (cx + orb, cy),          # right
        (cx,       cy + orb),   # bottom
        (cx - orb, cy),          # left
    ]

    # Draw connection lines first (so nodes sit on top)
    line_w = max(2, size // 80)
    for nx, ny in positions:
        # shorten line so it doesn't overlap node circles
        dx, dy  = nx - cx, ny - cy
        dist    = math.hypot(dx, dy)
        ux, uy  = dx / dist, dy / dist
        gap_c   = cn + size * 0.03    # gap at centre node edge
        gap_n   = sn + size * 0.02    # gap at satellite node edge
        x0 = int(cx + ux * gap_c)
        y0 = int(cy + uy * gap_c)
        x1 = int(nx - ux * gap_n)
        y1 = int(ny - uy * gap_n)
        draw.line([x0, y0, x1, y1], fill=LINE, width=line_w)

    # Draw satellite nodes
    for nx, ny in positions:
        aa_circle(draw, nx, ny, sn, fill=DARK, outline=BLUE_LIGHT,
                  width=max(1, size//80))
        # inner dot
        dot = max(2, sn // 3)
        aa_circle(draw, nx, ny, dot, fill=BLUE_LIGHT)

    # White dot in centre node
    wdot = max(3, cn // 3)
    aa_circle(draw, cx, cy, wdot, fill=WHITE)

    return img


def draw_client_icon(size=256):
    """
    Left: a thin laptop/device rectangle.
    Right: a small server rectangle.
    Centre: a rightward arrow between them.
    """
    img  = Image.new("RGBA", (size, size), BG)
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    h_mid  = cy   # vertical centre

    # ── Shared vertical centre for both devices
    dev_h  = int(size * 0.28)   # device height
    dev_w  = int(size * 0.18)   # device width
    r      = int(size * 0.045)  # corner radius

    # Client device (left)  — slightly wider, laptop feel
    cl_cx  = int(size * 0.18)
    cl_w   = int(size * 0.20)
    cl_h   = int(size * 0.26)
    aa_rect(draw,
            cl_cx - cl_w//2, h_mid - cl_h//2,
            cl_cx + cl_w//2, h_mid + cl_h//2,
            r, fill=DARK, outline=BLUE_LIGHT, width=max(1, size//80))
    # screen area inside client
    sc_pad = max(3, size // 40)
    aa_rect(draw,
            cl_cx - cl_w//2 + sc_pad, h_mid - cl_h//2 + sc_pad,
            cl_cx + cl_w//2 - sc_pad, h_mid + cl_h//4,
            max(1, r//2), fill=(45, 55, 72, 255))
    # status dot on client
    aa_circle(draw, cl_cx, h_mid + cl_h//4 + sc_pad*2,
              max(2, size//40), fill=BLUE)

    # Server device (right) — taller, rack-unit feel
    sv_cx  = int(size * 0.82)
    sv_w   = int(size * 0.16)
    sv_h   = int(size * 0.32)
    aa_rect(draw,
            sv_cx - sv_w//2, h_mid - sv_h//2,
            sv_cx + sv_w//2, h_mid + sv_h//2,
            r, fill=DARK, outline=BLUE, width=max(2, size//64))
    # Three horizontal lines on server (rack slots)
    slot_gap = sv_h // 5
    for k in range(1, 4):
        sy = h_mid - sv_h//2 + slot_gap * k
        draw.line(
            [sv_cx - sv_w//2 + sc_pad, sy,
             sv_cx + sv_w//2 - sc_pad, sy],
            fill=BLUE_LIGHT, width=max(1, size//128)
        )
    # blinking LED dot on server
    aa_circle(draw, sv_cx - sv_w//2 + sc_pad*2,
              h_mid - sv_h//2 + sc_pad*2,
              max(2, size//48), fill=BLUE)

    # ── Arrow from client to server
    gap     = int(size * 0.04)
    ax0     = cl_cx + cl_w//2 + gap
    ax1     = sv_cx - sv_w//2 - gap
    ay      = h_mid
    line_w  = max(2, size // 60)
    arrow_w = max(6, size // 24)   # arrowhead width (half)
    arrow_l = max(8, size // 20)   # arrowhead length

    # shaft
    draw.line([ax0, ay, ax1 - arrow_l, ay], fill=BLUE, width=line_w)

    # arrowhead triangle
    tip = [(ax1, ay),
           (ax1 - arrow_l, ay - arrow_w),
           (ax1 - arrow_l, ay + arrow_w)]
    draw.polygon(tip, fill=BLUE)

    return img


def save_ico(img_256, filename):
    sizes = [256, 128, 64, 48, 32, 16]
    frames = [img_256.resize((s, s), Image.LANCZOS) for s in sizes]
    frames[0].save(
        filename,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=frames[1:],
    )
    print(f"  Saved {filename}")


if __name__ == "__main__":
    print("Generating icons...")

    srv = draw_server_icon(256)
    cli = draw_client_icon(256)

    srv.save("server_icon.png")
    cli.save("client_icon.png")
    print("  Saved server_icon.png")
    print("  Saved client_icon.png")

    save_ico(srv, "server_icon.ico")
    save_ico(cli, "client_icon.ico")

    print("\nDone!  Four files created:")
    print("  server_icon.png  server_icon.ico")
    print("  client_icon.png  client_icon.ico")
