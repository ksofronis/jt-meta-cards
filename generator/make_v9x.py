"""v9/v10 extras for the products (v9_top.txt): carousel card 2 (colour range), card 3 (dimensions + showroom/delivery),
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

BOXES = {}  # out path -> where the product photo / info block sit; read by qc_assets.py (guardrail, 21/10)

def colours(it, out):
    """Carousel card 2: the full colour range, big real swatches (what the customer actually chooses from)."""
    c = Image.new('RGB', (S, S), CREAM); d = ImageDraw.Draw(c)
    n = len(it['swatches']); show = it['swatches'][:15] if n > 16 else it['swatches']
    cols = 4 if len(show) <= 16 else 5; rows = math.ceil(len(show) / cols)
    d.text((M + 4, M + 10), it['name'].replace('"', ''), font=m.fit(d, it['name'], 600, 52, S - 2 * M, floor=40)[1], fill=INK, anchor='lt')
    d.text((M + 4, M + 80), f"{n} χρώματα · δείτε τα από κοντά στην έκθεση", font=FONT(500, 36), fill=INK2, anchor='lt')
    # product photo first: grid and collection formats can show this card alone, so it must show the product (owner report 21/10)
    im, cut = photo(it); pt, pb = M + 150, M + 150 + 470; aw, ah = S - 2 * M, pb - pt
    m.shadow(c, (M, pt, M + aw, pb), 28, m.PHOTO_SH); c.paste(Image.new('RGB', (aw, ah), 'white'), (M, pt), m.mask((aw, ah), 28))
    r = min((aw - 24) / im.width, (ah - 24) / im.height); t = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    px, py = M + (aw - t.width) // 2, pt + (ah - t.height) // 2
    if cut: c.paste(t, (px, py), m.bg_alpha(t))
    else: c.paste(t, (px, py), m.mask(t.size, 22))
    BOXES[out] = {'photo': (px, py, px + t.width, py + t.height)}
    show = it['swatches'][:11] if n > 12 else it['swatches'][:12]; cols = 6; rows = math.ceil(len(show) / cols) if n <= 12 else 2
    top, bot = pb + 24, S - M - 76 - 24
    rad = int(min((S - 2 * M) / cols, (bot - top) / max(rows, 1)) * 0.36)
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
    BOXES[out] = {'photo': (px, py, px + t.width, py + t.height)}
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

GOLD = '#c9a76a'

def _fetch(u):
    """Gallery photo from the client's own site only (same host rule as the main photo)."""
    pu = urllib.parse.urlparse(u)
    if pu.scheme != 'https' or pu.hostname not in m.ALLOWED_HOSTS: raise ValueError('host')
    raw = urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(u, safe=':/%?=&'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
    im = Image.open(io.BytesIO(raw))
    if im.mode in ('RGBA', 'LA', 'P'): im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
    return m.trim_white(im.convert('RGB'))

def _contain(im, fw, fh):
    """Gallery shot into the fixed frame without cropping: a blurred, softened copy of itself fills the gaps."""
    from PIL import ImageFilter
    r = min(fw / im.width, fh / im.height); t = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    rb = max(fw / im.width, fh / im.height); bg = im.resize((round(im.width * rb) + 2, round(im.height * rb) + 2), Image.LANCZOS)
    bg = bg.crop(((bg.width - fw) // 2, (bg.height - fh) // 2, (bg.width - fw) // 2 + fw, (bg.height - fh) // 2 + fh)).filter(ImageFilter.GaussianBlur(28))
    bg = Image.blend(bg, Image.new('RGB', bg.size, CREAM), 0.35); bg.paste(t, ((fw - t.width) // 2, (fh - t.height) // 2)); return bg

def video(it, out, W, H, secs=6.0, fps=30):
    """v10 motion card (owner-approved 2026-10-21: proposals 6 + 8 + swatch-row cycle).
    0-2 s: hook. Name and instalments on screen from frame 1, the main photo settles from 107% to 100% in 0.7 s,
    colours from 0.25 s, size 0.9 s, phone 1.3 s. 2-6 s: up to 2 distinct site gallery photos (2 s each, 0.35 s crossfade;
    under 700 px, cutouts and near-copies skipped; 1 extra photo = 2 shots of 3 s; none = the main photo throughout).
    From 2 s the swatches light up one by one (gold ring) and the fabric's name replaces 'N χρώματα'.
    Photos are never cropped. 9:16: white card inside Meta's Stories/Reels safe zone (top 14%, bottom 20% free)."""
    from PIL import ImageFilter
    im, cut = photo(it); vertical = H > W
    pick = m.calm_pick(it['swatches'], 5 if len(it['swatches']) > 6 else 6, m.photo_match(im, it['swatches'])) if it['swatches'] else []
    more = len(it['swatches']) - len(pick)
    ph = phone_icon(); pf = FONT(700, 44 if vertical else 40); phh = 84 if vertical else 76
    nm = it['name'].replace('"', '').replace('  ', ' ')
    # gallery shots first: the frame shape depends on whether there are any
    srcs, gal = [im], []
    th = lambda z: list(z.convert('L').resize((24, 24)).getdata())
    for u in (it.get('gallery') or [])[:8]:
        if len(gal) == 2: break
        try:
            g = _fetch(u)
            if g.width < 700 or m.is_cutout(g): continue
            if any(sum(abs(a - b) for a, b in zip(th(g), th(s0))) / 576 < 22 for s0 in srcs): continue
            srcs.append(g); gal.append(g)
        except Exception: pass
    MULTI = bool(gal)
    if vertical:
        sz_top, sz_bot = int(H * 0.14), int(H * 0.80); pad = 40
        cx0, cx1 = M, W - M; iw = cx1 - cx0 - 2 * pad
        info_h = 66 + 36 + (84 + 36 if pick else 0) + (50 + 40 if it['dims'] else 0) + phh + 28 + 40
        ph_max = sz_bot - sz_top - 2 * pad - 44 - info_h
        if cut or MULTI: fw, fh = iw, min(ph_max, int(iw * (0.8 if cut else 0.75)))
        else: r = min(iw / im.width, ph_max / im.height); fw, fh = round(im.width * r), round(im.height * r)
        card_h = 2 * pad + fh + 44 + info_h; cy0 = sz_top + (sz_bot - sz_top - card_h) // 2
        fx, fy = cx0 + pad + (iw - fw) // 2, cy0 + pad; info_x, info_y = cx0 + pad + 4, fy + fh + 44; right = cx1 - pad
    else:
        info_h = 62 + 36 + (76 + 36 if pick else 0) + 76
        aw, ah = W - 2 * M, H - 2 * M - info_h - 44
        if cut or MULTI: fw, fh = aw, ah
        else: r = min(aw / im.width, ah / im.height); fw, fh = round(im.width * r), round(im.height * r)
        fx, fy = (W - fw) // 2, M + (ah - fh) // 2; info_x, info_y = M + 4, M + ah + 44; right = W - M
    def framed(src, is_cut):
        if is_cut:
            free = 24 + 72 + 12 if it['finance'] else 0
            pr = min(fw * 0.94 / src.width, (fh - free) * 0.94 / src.height); t = src.resize((round(src.width * pr), round(src.height * pr)), Image.LANCZOS)
            fr = Image.new('RGB', (fw, fh), CREAM); fr.paste(t, ((fw - t.width) // 2, (fh - free - t.height) // 2 + 8), m.bg_alpha(t)); return fr
        return _contain(src, fw, fh) if MULTI else src.resize((fw, fh), Image.LANCZOS)
    frames = [framed(im, cut)] + [framed(g, False) for g in gal]
    fmask = m.mask((fw, fh), 28)
    bg = Image.new('RGB', (W, H), CREAM if vertical else 'white')
    if vertical:
        m.shadow(bg, (cx0, cy0, cx1, cy0 + card_h), 40, m.PHOTO_SH)
        cm = m.mask((cx1 - cx0, card_h), 40); bg.paste(Image.new('RGB', cm.size, 'white'), (cx0, cy0), cm)
    PAD = 160; lw, lh = fw + 2 * PAD, fh + 2 * PAD
    bgp = Image.new('RGB', (W + 2 * PAD, H + 2 * PAD), CREAM if vertical else 'white'); bgp.paste(bg, (PAD, PAD))
    lay0 = bgp.crop((fx, fy, fx + lw, fy + lh)); m.shadow(lay0, (PAD, PAD, PAD + fw, PAD + fh), 28, m.PHOTO_SH)
    def layer(fr):
        L = lay0.copy(); L.paste(fr, (PAD, PAD), fmask); bx = PAD + 24
        for b_ in it['badges'][:1 if it.get('warranty') else 2]:  # same chips as the main card (warranty takes the 2nd slot)
            dark = b_ == 'ΝΕΟ'
            bx += m.pill(L, bx, PAD + 24, b_, FONT(700 if dark else 600, 36), CREAM if dark else INK, INK if dark else (255, 255, 255), h=68, pad=28, depth=m.BTN_SH[1:]) + 14
        if it.get('warranty'): m.pill(L, bx, PAD + 24, m.WARRANTY, FONT(600, 36), INK, (255, 255, 255), h=68, pad=26, depth=m.BTN_SH[1:], icon=m.shield(38, INK))
        return L
    lays = [layer(f) for f in frames]
    la = Image.new('L', (lw, lh), 0); ImageDraw.Draw(la).rectangle((PAD // 2, PAD // 2, lw - PAD // 2, lh - PAD // 2), fill=255); la = la.filter(ImageFilter.GaussianBlur(PAD / 6))
    ox, oy = fx - PAD, fy - PAD; ccx, ccy = fx + fw / 2, fy + fh / 2
    HOOK = 2.0; seg = (secs - HOOK) / len(gal) if gal else None
    def shot(t):  # (layer index, time inside that shot, shot length)
        if not gal or t < HOOK: return 0, t, HOOK if gal else secs
        i = min(int((t - HOOK) // seg), len(gal) - 1); return i + 1, t - HOOK - i * seg, seg
    def scale(i, tl, ln):
        if i == 0: return 1.07 - 0.07 * out_cubic(tl / 0.7) + 0.02 * ease((tl - 0.7) / max(0.1, ln - 0.7))
        return 1.02 + 0.03 * ease(tl / ln)
    def warp(L, k):  # bilinear: zoom stays within 1.00 to 1.07, bicubic cost 2x for no visible gain
        inv = 1 / k; tx = ccx - ox - (ccx - ox) * inv; ty = ccy - oy - (ccy - oy) * inv
        return (L.transform(L.size, Image.AFFINE, (inv, 0, tx, 0, inv, ty), resample=Image.BILINEAR),
                la.transform(la.size, Image.AFFINE, (inv, 0, tx, 0, inv, ty), resample=Image.BILINEAR))
    def base(t):
        c = bg.copy(); i, tl, ln = shot(t); sl, sa = warp(lays[i], scale(i, tl, ln)); X0 = 0.35
        if i and tl < X0:  # crossfade from the previous shot (held at its last scale)
            pi, pl_ = i - 1, (HOOK if i == 1 else seg); pl, _ = warp(lays[pi], scale(pi, pl_, pl_)); sl = Image.blend(pl, sl, ease(tl / X0))
        c.paste(sl, (ox, oy), sa); return c
    # everything on screen from frame 0: Meta uses frame 0 as the thumbnail and grid formats show it still (owner report 21/10); motion = photo zoom, gallery, swatch cycle
    T = {'name': 0.0, 'sw': 0.0, 'swd': 0.0, 'dims': 0.0, 'fin': 0.0, 'phone': 0.0, 'loc': 0.0}
    E = []; y = info_y
    def name_(c, dy, y=y):
        d = ImageDraw.Draw(c); n2, f = m.fit(d, nm, 600, 66 if vertical else 62, right - info_x - 4, floor=46); d.text((info_x, y + dy), n2, font=f, fill=INK, anchor='lt')
    E.append((T['name'], name_)); y += (66 if vertical else 62) + 36
    sw_y = y; rad, gap = (40, 20) if vertical else (36, 18); sw_x = []; lbl_x = info_x
    if pick:
        cx = info_x + rad
        for i, s_ in enumerate(pick):
            sw_x.append(cx); E.append((T['sw'] + T['swd'] * i, lambda c, dy, s_=s_, cx=cx, y=y: m.swatch_dot(c, s_, cx, y + rad + 2 + dy, rad))); cx += 2 * rad + gap
        st = T['sw'] + T['swd'] * len(pick)
        if more:
            def plus(c, dy, cx=cx, y=y):
                d = ImageDraw.Draw(c); m.ring(c, cx, y + rad + 2 + dy, rad + 2, color='white', w=5, fill='white'); m.ring(c, cx, y + rad + 2 + dy, rad, color=LINE, w=2, fill=CREAM)
                d.text((cx, y + rad + 2 + dy), f"+{more}", font=FONT(600, 36), fill=INK, anchor='mm')
            E.append((st, plus)); cx += 2 * rad + gap; st += T['swd']
        lbl_x = cx + 6
        E.append((st, lambda c, dy, cx=cx, y=y: ImageDraw.Draw(c).text((cx + 6, y + rad + 2 + dy), f"{len(it['swatches'])} χρώματα", font=FONT(500, 44 if vertical else 42), fill=INK2, anchor='lm')))
        y += (84 if vertical else 76) + 36
    pw = int(ImageDraw.Draw(Image.new('RGB', (1, 1))).textlength(PHONE, font=pf) + 2 * 30 + ph.width + 14)
    if vertical:
        if it['dims']:
            def dims_(c, dy, y=y):
                ic = m.ruler_icon(48, INK2); c.paste(ic, (info_x - 2, y + 1 + dy), ic); ImageDraw.Draw(c).text((info_x + 66, y + 25 + dy), it['dims'], font=FONT(500, 46), fill=INK2, anchor='lm')
            E.append((T['dims'], dims_)); y += 50 + 40
        E.append((T['phone'], lambda c, dy, y=y: m.pill(c, info_x, y + dy, PHONE, pf, CREAM, INK, h=phh, pad=30, depth=m.BTN_SH, icon=ph)))
        E.append((T['loc'], lambda c, dy, y=y: loc_line(c, info_x + 4, y + phh + 20 + dy, 48, size=38, color=INK2)))
    else:
        if it['dims']:
            def dims_(c, dy, y=y):
                d = ImageDraw.Draw(c); ic = m.ruler_icon(46, INK2); c.paste(ic, (info_x - 2, y + 15 + dy), ic)
                dt, df = m.fit(d, it['dims'], 500, 42, right - pw - 24 - (info_x + 62), floor=34); d.text((info_x + 62, y + 38 + dy), dt, font=df, fill=INK2, anchor='lm')
            E.append((T['dims'], dims_))
        E.append((T['phone'], lambda c, dy, y=y: m.pill(c, right - pw, y + dy, PHONE, pf, CREAM, INK, h=phh, pad=30, depth=m.BTN_SH, icon=ph)))
    if it['finance']: E.append((T['fin'], lambda c, dy: m.fin_pill(c, fx + 24 - dy, fy + fh - 24 - 72, it['finance'])))
    terms = it.get('swatch_terms') or []
    nm_of = lambda s_: (terms[it['swatches'].index(s_)].split('/')[0].strip().title() if it['swatches'].index(s_) < len(terms) else '')
    def rowcyc(c, t):  # swatch-row colour cycle from 2 s
        i = int((t - 2.0) / 0.6) % len(pick); a = out_cubic(((t - 2.0) % 0.6) / 0.2); d = ImageDraw.Draw(c)
        cx_, cy_ = sw_x[i], sw_y + rad + 2
        m.ring(c, cx_, cy_, rad + 9, color=GOLD, w=4); m.swatch_dot(c, pick[i], cx_, cy_, int(rad * (1 + 0.1 * a)))
        fz = FONT(600, 44 if vertical else 42); d.rectangle((lbl_x - 4, cy_ - 34, right, cy_ + 34), fill='white')
        n_ = nm_of(pick[i]) or f"{len(it['swatches'])} χρώματα"; n_, fz = m.fit(d, n_, 600, 44 if vertical else 42, right - lbl_x, floor=30)
        d.text((lbl_x, cy_), n_, font=fz, fill=INK, anchor='lm')
    N = int(secs * fps); D = 0.5
    # frames go straight into ffmpeg as raw RGB (no JPEG round trip: sharper, ~2x faster, no temp files)
    enc = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                            '-c:v', 'libx264', '-threads', '2', '-preset', 'slow', '-crf', '26', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
    for fi in range(N):
        t = fi / fps; c = base(t)
        for st, fn in E:
            if t < st: continue
            a = out_cubic((t - st) / D) if st > 0 else 1
            if a >= 1: fn(c, 0); continue
            c2 = c.copy(); fn(c2, round((1 - a) * 24)); c = Image.blend(c, c2, min(1, a * 1.4))
        if pick and t >= 2.0:
            a = out_cubic((t - 2.0) / 0.4); c2 = c.copy(); rowcyc(c2, t); c = Image.blend(c, c2, a) if a < 1 else c2
        enc.stdin.write(c.tobytes())
    enc.stdin.close(); assert enc.wait() == 0
    BOXES[out] = {'photo': (fx, fy, fx + fw, fy + fh), 'info': (0, info_y - 10, W, min(H, info_y + 420))}
