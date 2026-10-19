"""v9 extras for the top products (v9_top.txt): carousel card 2 (colour range), card 3 (dimensions + showroom/delivery),
and a 6 s motion card in 9:16 (Stories/Reels) and 1:1 (Feed), 60 fps. Built on the live v7/v8/v9 renderer (make_v7).
Library only: v9_extras.py calls photo(), colours(), details(), video()."""
import os, io, math, subprocess, urllib.request, urllib.parse
from PIL import Image, ImageDraw
import make_v7 as m
from make_v7 import FONT, S, M, INK, INK2, MUT, LINE, CREAM, PHONE
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = '.'
SHOWROOM = 'Έκθεση 2 ορόφων · Αχαρνές'  # legacy text, replaced by loc_line()
# showroom + nationwide delivery, both stated on jthomedesign.gr (home page, 2026-10-19: "Αποστολές σε όλη την Ελλάδα")
LOC = (('store', 'Αχαρνές'), ('truck', 'Πανελλαδικά'))

def line_icon(kind, size, color):
    """Thin-line icons in the site's ink, 4x supersampled: shop front (showroom) and delivery truck."""
    b = size * 4; im = Image.new('RGBA', (b, b), (0, 0, 0, 0)); d = ImageDraw.Draw(im); w = max(4, int(b * 0.085))
    if kind == 'store':
        d.line((b*.12, b*.18, b*.88, b*.18), fill=color, width=w)                       # roof line
        for i in range(4):                                                           # scalloped awning
            x0 = b*.08 + i*b*.21; d.arc((x0, b*.18, x0 + b*.21, b*.44), 0, 180, fill=color, width=w)
        d.line((b*.08, b*.18, b*.08, b*.31), fill=color, width=w); d.line((b*.92, b*.18, b*.92, b*.31), fill=color, width=w)
        d.rectangle((b*.16, b*.40, b*.84, b*.88), outline=color, width=w)               # body
        d.rectangle((b*.42, b*.58, b*.62, b*.88), outline=color, width=w)               # door
    else:
        d.rounded_rectangle((b*.04, b*.26, b*.60, b*.70), radius=b*.04, outline=color, width=w)   # box
        d.line((b*.60, b*.38, b*.78, b*.38), fill=color, width=w); d.line((b*.78, b*.38, b*.94, b*.54), fill=color, width=w)
        d.line((b*.94, b*.54, b*.94, b*.70), fill=color, width=w); d.line((b*.60, b*.70, b*.94, b*.70), fill=color, width=w)
        for cx in (b*.24, b*.76): d.ellipse((cx - b*.10, b*.66, cx + b*.10, b*.86), fill=(255, 255, 255, 255), outline=color, width=w)
    return im.resize((size, size), Image.LANCZOS)

def loc_line(c, x, y, h, size=36, color=INK2, measure=False):
    """Icon + 'Αχαρνές'  ·  icon + 'Πανελλαδικά', vertically centred on y + h/2. Returns width (narrower than the old showroom text)."""
    d = ImageDraw.Draw(c); f = FONT(600, size); ic = round(size * 1.0); cx = x
    for k, (kind, txt) in enumerate(LOC):
        if k: cx += round(size * 0.5)
        if not measure: i = line_icon(kind, ic, color); c.paste(i, (int(cx), int(y + (h - ic) / 2)), i)
        cx += ic + round(size * 0.22)
        if not measure: d.text((cx, y + h / 2), txt, font=f, fill=color, anchor='lm')
        cx += d.textlength(txt, font=f)
    return int(cx - x)

_img = {}
def photo(it):
    """The photo exactly as the live card prepares it: trimmed, v8 zoom when approved. Returns (image, is_cutout)."""
    if it['id'] not in _img:
        u = urllib.parse.urlparse(it['image'])
        if u.scheme != 'https' or u.hostname not in m.ALLOWED_HOSTS: raise ValueError(f"refused image host for {it['id']!r}")
        raw = urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(it['image'], safe=':/%?=&'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
        im = Image.open(io.BytesIO(raw))
        if im.mode in ('RGBA', 'LA', 'P'): im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
        im = im.convert('RGB'); cut = m.is_cutout(im); im = m.trim_white(im)
        if it.get('crop') and not cut: im = im.crop(tuple(it['crop']))
        _img[it['id']] = (im, cut)
    return _img[it['id']]



def phone_icon():
    ph = Image.open(os.path.join(REPO, 'generator', 'icon-phone-hi.png')).convert('RGBA'); ph = ph.resize((round(ph.width * 38 / ph.height), 38), Image.LANCZOS)
    return Image.merge('RGBA', (*Image.new('RGB', ph.size, CREAM).split(), ph.split()[3]))

def phone_row(c, d, x, y, dims, right=S - M):
    ph = phone_icon(); pf = FONT(700, 40); pw = int(d.textlength(PHONE, font=pf) + 2 * 30 + ph.width + 14)
    m.pill(c, right - pw, y, PHONE, pf, CREAM, INK, h=76, pad=30, depth=m.BTN_SH, icon=ph)
    if dims:
        ic = m.ruler_icon(46, INK2); c.paste(ic, (x - 2, y + 15), ic)
        dt, df = m.fit(d, dims, 500, 42, right - pw - 24 - (x + 62), floor=34); d.text((x + 62, y + 38), dt, font=df, fill=INK2, anchor='lm')

def colours(it, out):
    """Carousel card 2: the full colour range, big real swatches (what the customer actually chooses from)."""
    c = Image.new('RGB', (S, S), CREAM); d = ImageDraw.Draw(c)
    n = len(it['swatches']); show = it['swatches'][:15] if n > 16 else it['swatches']
    cols = 4 if len(show) <= 16 else 5; rows = math.ceil(len(show) / cols)
    d.text((M + 4, M + 10), it['name'].replace('"', ''), font=m.fit(d, it['name'], 600, 52, S - 2 * M, floor=40)[1], fill=INK, anchor='lt')
    d.text((M + 4, M + 84), f"{n} χρώματα · δείτε τα από κοντά στην έκθεση", font=FONT(500, 36), fill=INK2, anchor='lt')
    top, bot = M + 170, S - M - 76 - 40
    rad = int(min((S - 2 * M) / cols, (bot - top) / rows) * 0.36)
    for k, s_ in enumerate(show):
        cx = M + int((k % cols + 0.5) * (S - 2 * M) / cols); cy = top + int((k // cols + 0.5) * (bot - top) / rows)
        m.swatch_dot(c, s_, cx, cy, rad)
    if n > len(show):
        k = len(show); cx = M + int((k % cols + 0.5) * (S - 2 * M) / cols); cy = top + int((k // cols + 0.5) * (bot - top) / rows)
        m.ring(c, cx, cy, rad + 2, color='white', w=5, fill='white'); m.ring(c, cx, cy, rad, color=LINE, w=2, fill='white')
        d.text((cx, cy), f"+{n - len(show)}", font=FONT(600, 44), fill=INK, anchor='mm')
    phone_row(c, d, M + 4, S - M - 76, '')
    c.save(out, quality=85); return c

def details(it, out):
    """Carousel card 3: size in large type + showroom invitation (local trust) + phone. Photo takes everything else."""
    im, cut = photo(it)
    c = Image.new('RGB', (S, S), 'white'); d = ImageDraw.Draw(c)
    nums = [v.strip() for v in it['dims'].replace(' cm', '').split('×')] if it['dims'] else []
    dims_h = 150 if nums else 0
    aw, ah = S - 2 * M, S - 2 * M - 76 - 44 - dims_h - (40 if nums else 0)
    r = min(aw / im.width, ah / im.height); t = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    px, py = (S - t.width) // 2, M + (ah - t.height) // 2
    if not cut: m.shadow(c, (px, py, px + t.width, py + t.height), 28, m.PHOTO_SH); c.paste(t, (px, py), m.mask(t.size, 28))
    else: c.paste(t, (px, py))
    y = M + ah + 40
    labels = ['ΠΛΑΤΟΣ', 'ΒΑΘΟΣ', 'ΥΨΟΣ'][:len(nums)] if len(nums) != 4 else ['ΠΛΑΤΟΣ', 'ΒΑΘΟΣ', 'ΒΑΘΟΣ', 'ΥΨΟΣ']
    if nums:
        cw = (S - 2 * M) / len(nums)
        for k, (v, l) in enumerate(zip(nums, labels)):
            cx = M + cw * (k + 0.5)
            d.text((cx, y + 44), v, font=FONT(600, 88), fill=INK, anchor='mm'); d.text((cx, y + 116), l + ' · cm', font=FONT(600, 30), fill=MUT, anchor='mm')
            if k: d.line((M + cw * k, y + 10, M + cw * k, y + 134), fill=LINE, width=2)
    yb = S - M - 76
    lw_ = loc_line(c, 0, 0, 76, measure=True)
    m.pill(c, M, yb, ' ', FONT(600, 36), INK, CREAM, h=76, pad=(lw_ + 56) // 2, outline=LINE)
    loc_line(c, M + 28, yb, 76, color=INK)
    phone_row(c, d, M + 4, yb, '')
    c.save(out, quality=85); return c

# ---------- video ----------
ease = lambda t: 0.5 - 0.5 * math.cos(math.pi * max(0, min(1, t)))
out_cubic = lambda t: 1 - (1 - max(0, min(1, t))) ** 3  # fast start, soft landing: entries

def video(it, out, W, H, secs=6.0, fps=60):
    """Mobile-first motion card. Frame 0 already shows the full photo (thumb-stop frame, never a fade from white).
    The photo is never cropped: motion is a slow 96%->100% scale of the whole framed photo.
    9:16: cream page + white card inside Meta's Stories/Reels safe zone (top 14%, bottom 20% kept free).
    Timeline: 0.5s name, 1.0s swatches one by one, 2.6s dimensions, 3.2s instalments, 4.0s phone, 4.4s showroom; hold to 6s."""
    im, cut = photo(it)
    vertical = H > W
    pick = m.calm_pick(it['swatches'], 5 if len(it['swatches']) > 6 else 6, m.photo_match(im, it['swatches'])) if it['swatches'] else []
    more = len(it['swatches']) - len(pick)
    ph = phone_icon(); pf = FONT(700, 44 if vertical else 40); phh = 84 if vertical else 76
    nm = it['name'].replace('"', '').replace('  ', ' ')
    # ---- layout ----
    if vertical:
        sz_top, sz_bot = int(H * 0.14), int(H * 0.80); pad = 40
        cx0, cx1 = M, W - M; iw = cx1 - cx0 - 2 * pad
        info_h = 66 + 36 + (84 + 36 if pick else 0) + (50 + 40 if it['dims'] else 0) + phh + 28 + 40
        ph_max = sz_bot - sz_top - 2 * pad - 44 - info_h
        if cut: fw, fh = iw, min(ph_max, int(iw * 0.8))
        else:
            r = min(iw / im.width, ph_max / im.height); fw, fh = round(im.width * r), round(im.height * r)
        card_h = 2 * pad + fh + 44 + info_h; cy0 = sz_top + (sz_bot - sz_top - card_h) // 2
        fx, fy = cx0 + pad + (iw - fw) // 2, cy0 + pad; info_x, info_y = cx0 + pad + 4, fy + fh + 44; right = cx1 - pad
    else:
        info_h = 62 + 36 + (76 + 36 if pick else 0) + 76
        aw, ah = W - 2 * M, H - 2 * M - info_h - 44
        if cut: fw, fh = aw, ah
        else:
            r = min(aw / im.width, ah / im.height); fw, fh = round(im.width * r), round(im.height * r)
        fx, fy = (W - fw) // 2, M + (ah - fh) // 2; info_x, info_y = M + 4, M + ah + 44; right = W - M
    if cut:  # cream panel, product kept clear of the instalments pill
        free = 24 + 72 + 12 if it['finance'] else 0
        pr = min(fw * 0.94 / im.width, (fh - free) * 0.94 / im.height); t = im.resize((round(im.width * pr), round(im.height * pr)), Image.LANCZOS)
        frame = Image.new('RGB', (fw, fh), CREAM); frame.paste(t, ((fw - t.width) // 2, (fh - free - t.height) // 2 + 8), m.bg_alpha(t))
    else: frame = im.resize((fw, fh), Image.LANCZOS)
    fmask = m.mask(frame.size, 28)
    # ---- static background + elements ----
    # static layers, built once: background (+ white card) and the photo layer (shadow + photo + badges) at 100%
    bg = Image.new('RGB', (W, H), CREAM if vertical else 'white')
    if vertical:
        m.shadow(bg, (cx0, cy0, cx1, cy0 + card_h), 40, m.PHOTO_SH)
        cm = m.mask((cx1 - cx0, card_h), 40); bg.paste(Image.new('RGB', cm.size, 'white'), (cx0, cy0), cm)
    PAD = 160; lw, lh = fw + 2 * PAD, fh + 2 * PAD
    bgp = Image.new('RGB', (W + 2 * PAD, H + 2 * PAD), CREAM if vertical else 'white'); bgp.paste(bg, (PAD, PAD))
    lay = bgp.crop((fx, fy, fx + lw, fy + lh))  # layer background = exactly what sits behind the photo (white card)
    m.shadow(lay, (PAD, PAD, PAD + fw, PAD + fh), 28, m.PHOTO_SH); lay.paste(frame, (PAD, PAD), fmask)
    bx = PAD + 24
    for b_ in it['badges']:
        dark = b_ == 'ΝΕΟ'
        bx += m.pill(lay, bx, PAD + 24, b_, FONT(700 if dark else 600, 36), CREAM if dark else INK, INK if dark else (255, 255, 255), h=68, pad=28, depth=m.BTN_SH[1:]) + 14
    # soft-edged alpha for the layer so its rectangle never shows when scaled down
    la = Image.new('L', (lw, lh), 0); ImageDraw.Draw(la).rectangle((PAD // 2, PAD // 2, lw - PAD // 2, lh - PAD // 2), fill=255)
    la = la.filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(PAD / 6))
    ox, oy = fx - PAD, fy - PAD; ccx, ccy = fx + fw / 2, fy + fh / 2
    def base(t):
        k = 0.96 + 0.04 * ease(t / secs)
        # sub-pixel scale about the photo centre: no whole-pixel size jumps -> no shimmer
        inv = 1 / k; tx = ccx - ox - (ccx - ox) * inv; ty = ccy - oy - (ccy - oy) * inv
        sl = lay.transform(lay.size, Image.AFFINE, (inv, 0, tx, 0, inv, ty), resample=Image.BICUBIC)
        sa = la.transform(la.size, Image.AFFINE, (inv, 0, tx, 0, inv, ty), resample=Image.BICUBIC)
        c = bg.copy(); c.paste(sl, (ox, oy), sa); return c
    E = []  # (start, draw(c, dy))
    y = info_y
    def name_(c, dy, y=y):
        d = ImageDraw.Draw(c); n2, f = m.fit(d, nm, 600, 66 if vertical else 62, right - info_x - 4, floor=46); d.text((info_x, y + dy), n2, font=f, fill=INK, anchor='lt')
    E.append((0.5, name_)); y += (66 if vertical else 62) + 36
    if pick:
        rad, gap = (40, 20) if vertical else (36, 18); cx = info_x + rad
        for i, s_ in enumerate(pick):
            E.append((1.0 + 0.12 * i, lambda c, dy, s_=s_, cx=cx, y=y: m.swatch_dot(c, s_, cx, y + rad + 2 + dy, rad))); cx += 2 * rad + gap
        st = 1.0 + 0.12 * len(pick)
        if more:
            def plus(c, dy, cx=cx, y=y):
                d = ImageDraw.Draw(c); m.ring(c, cx, y + rad + 2 + dy, rad + 2, color='white', w=5, fill='white'); m.ring(c, cx, y + rad + 2 + dy, rad, color=LINE, w=2, fill=CREAM)
                d.text((cx, y + rad + 2 + dy), f"+{more}", font=FONT(600, 36), fill=INK, anchor='mm')
            E.append((st, plus)); cx += 2 * rad + gap; st += 0.12
        E.append((st, lambda c, dy, cx=cx, y=y: ImageDraw.Draw(c).text((cx + 6, y + rad + 2 + dy), f"{len(it['swatches'])} χρώματα", font=FONT(500, 44 if vertical else 42), fill=INK2, anchor='lm')))
        y += (84 if vertical else 76) + 36
    pw = int(ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(PHONE, font=pf) + 2 * 30 + ph.width + 14)
    if vertical:
        if it['dims']:
            def dims_(c, dy, y=y):
                ic = m.ruler_icon(48, INK2); c.paste(ic, (info_x - 2, y + 1 + dy), ic); ImageDraw.Draw(c).text((info_x + 66, y + 25 + dy), it['dims'], font=FONT(500, 46), fill=INK2, anchor='lm')
            E.append((2.6, dims_)); y += 50 + 40
        E.append((4.0, lambda c, dy, y=y: m.pill(c, info_x, y + dy, PHONE, pf, CREAM, INK, h=phh, pad=30, depth=m.BTN_SH, icon=ph)))
        E.append((4.4, lambda c, dy, y=y: loc_line(c, info_x + 4, y + phh + 20 + dy, 48, size=38, color=INK2)))
    else:
        if it['dims']:
            def dims_(c, dy, y=y):
                d = ImageDraw.Draw(c); ic = m.ruler_icon(46, INK2); c.paste(ic, (info_x - 2, y + 15 + dy), ic)
                dt, df = m.fit(d, it['dims'], 500, 42, right - pw - 24 - (info_x + 62), floor=34); d.text((info_x + 62, y + 38 + dy), dt, font=df, fill=INK2, anchor='lm')
            E.append((2.6, dims_))
        E.append((4.0, lambda c, dy, y=y: m.pill(c, right - pw, y + dy, PHONE, pf, CREAM, INK, h=phh, pad=30, depth=m.BTN_SH, icon=ph)))
    if it['finance']:
        E.append((3.2, lambda c, dy: m.fin_pill(c, fx + 24 - dy, fy + fh - 24 - 72, it['finance'])))
    N = int(secs * fps); D = 0.5
    # frames go straight into ffmpeg as raw RGB (no JPEG round trip: sharper, ~2x faster, no temp files)
    enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                            '-c:v', 'libx264', '-preset', 'slow', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for f in range(N):
        t = f / fps; c = base(t)
        for st, fn in E:
            if t < st: continue
            a = out_cubic((t - st) / D)
            if a >= 1: fn(c, 0); continue
            c2 = c.copy(); fn(c2, round((1 - a) * 24)); c = Image.blend(c, c2, min(1, a * 1.4))
        enc.stdin.write(c.tobytes())
    enc.stdin.close(); assert enc.wait() == 0

