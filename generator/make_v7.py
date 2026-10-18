"""v7 card renderer (live for the product groups listed in v7_groups.txt; driven by v7_cards.py): mobile-first Meta catalog card in the website card language.
Photo (uncropped, rounded) with up to 2 badges; name; dimensions as text; options as the site shows them
(real fabric/wood swatches: photo colour first, then a calm light-to-dark spread with at most 1 strong colour, "+N" circle when more exist; size chips for mattresses); phone always.
Every text is >= 34px on the 1080 canvas, so it stays readable at ~360px (Stories grid tile, phone feed).
Library only: v7_cards.py builds items from the live feed and calls card(item, out_path)."""
import ast, io, os, re, sys, json, math, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))  # generator/
ASSETS = os.path.join(HERE, 'v7')  # Inter fonts, the site's swatch sprites and library (snapshot of jtpk.js, 2026-10-19)
LIB = json.load(open(os.path.join(ASSETS, 'swatch_lib.json'), encoding='utf-8'))  # the site's swatch library (jtpk.js)
FONT = lambda w, s: ImageFont.truetype(os.path.join(ASSETS, 'fonts', f'Inter-{w}.ttf'), s)
S, M, X = 1080, 44, 4
INK, INK2, MUT, LINE, CREAM = '#352600', '#5c4a2a', '#8f8064', '#e4dacb', '#F7F3EC'  # site tokens
PHONE = '210 247 6585'
NS = {'g': 'http://base.google.com/ns/1.0'}

# badge rules: the live renderer's list, unchanged (only claims stated in the product's own text)
_src = open(os.path.join(HERE, 'make_cards.py'), encoding='utf-8').read()
BADGES = ast.literal_eval(re.search(r'BADGES = (\[.*?\n\])', _src, re.S).group(1))
DIM = re.compile(r'\d{2,3}(?:[,.]\d)?(?:\s*[xχΧ×*]\s*\d{2,3}(?:[,.]\d)?)+')
PLAIN = [(r'^μεταλλικό γκρι ανθρακί$', '#3d3f42'), (r'^γκρι σκούρο$', '#4a4a4a'), (r'^γκρι$', '#8c8c8a'), (r'^μπεζ$', '#d9c8aa'),
         (r'^κεραμικό λευκό$', '#efece6'), (r'^λευκό$', '#f5f3ef'), (r'^εκρού$', '#ece4d2'), (r'^καφέ σκούρο$', '#4a3424'),
         (r'^καφέ$', '#6b4a2f'), (r'^μόκα$', '#7b5a45'), (r'^μαύρο$', '#1d1d1d'), (r'^ανθρακί$', '#3b3b3b')]
SIZE_PREF = ['90x200', '140x200', '160x200', '150x200', '170x200', '180x200', '100x200', '120x200']

# ---------- data ----------
def norm(s):  # same key normalisation as the site (jtpk.js norm)
    s = s.strip().lower()
    if not s.startswith('rustic/'): s = s.split('/')[0]
    s = re.sub(r'[^a-z0-9α-ωάέήίόύώ]', '', s.replace('bata', 'beta').replace('d.k', 'dk'))
    return re.sub(r'\d+', lambda m: str(int(m.group())), s)

def swatch(term):
    it = LIB['items'].get(norm(term))
    if it: c = LIB['colls'][it['coll']]; return {'hex': it['hex'], 'sprite': c['sp'], 'n': c['n'], 'i': it['i']}
    t = term.split('/')[0].strip().lower()
    for rx, h in PLAIN:
        if re.match(rx, t): return {'hex': h}
    return None

_store = {}
def store(gid):  # WooCommerce Store API (public): variation attributes; cached per run
    if gid not in _store:
        u = f'https://jthomedesign.gr/wp-json/wc/store/v1/products/{int(gid)}'
        _store[gid] = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30))
    return _store[gid]

def build(it):
    """Card spec from one <item> element of the live feed."""
    g = lambda k: it.findtext(f'g:{k}', namespaces=NS) or ''
    title, ptype = g('title'), g('product_type')
    dims = [re.sub(r'\s*[xχΧ×*]\s*', ' × ', d) for d in DIM.findall(title)]
    name = re.sub(r'(?:[\s,]+|\s[x×])+$', '', re.sub(r'\s{2,}', ' ', DIM.sub('', title))).strip(' ,-/')
    attrs = {a['taxonomy'] or a['name']: [t['name'] for t in a['terms']] for a in store(g('item_group_id') or g('id')).get('attributes', [])}
    mattress = 'Στρώματα' in ptype
    # primary option row: fabric/colour (pa_xroma, pa_chroma) first, then wood colour; sizes for mattresses
    sw, sw_label = [], ''
    for tax, lbl in (('pa_xroma', 'χρώματα υφάσματος'), ('pa_chroma', 'χρώματα'), ('pa_xroma-xilou', 'χρώματα ξύλου')):
        terms = [t for t in attrs.get(tax, []) if not re.match(r'ως\s*φωτογραφ', t, re.I)]
        found = [s for s in map(swatch, terms) if s]
        if len(terms) > 1 and len(found) >= len(terms) / 2:
            sw, sw_label = found, f"{len(terms)} {lbl if any(s.get('sprite') for s in found) else 'χρώματα'}"; break  # plain named colours: no material claim
    sizes = [s.replace('×', 'x') for s in attrs.get('pa_diastasis-stroma', []) + attrs.get('pa_diastasi', []) if re.fullmatch(r'\d{2,3}[x×]\d{3}', s)]
    # secondary line (footer, left)
    sec = ''
    if len(attrs.get('pa_gwnia', [])) == 2: sec = 'Αριστερή ή δεξιά γωνία'
    elif sizes and not mattress and len(sizes) > 1: sec = f'Σε {len(sizes)} διαστάσεις'
    elif len(attrs.get('Μηχανισμός', [])) > 1: sec = f"{len(attrs['Μηχανισμός'])} τύποι μηχανισμού"
    # badges: ΝΕΟ (site category) + feed-text rules + waterproof when every fabric is waterproof
    text = ' '.join(f'{title} | {g("description")} | {ptype}'.lower().split())
    b = [bd for rx, bd in BADGES if re.search(rx, text)]
    fab = attrs.get('pa_xroma', [])
    if fab and all('/αδιάβροχο' in t.lower() for t in fab): b.insert(0, 'Αδιάβροχο ύφασμα')
    if 'Νέα Προϊόντα' in ptype: b.insert(0, 'ΝΕΟ')
    if 'Καναπέδες' in ptype: b = [x for x in b if x != 'Στα μέτρα σας']
    return {'id': g('id'), 'name': name, 'dims': (dims[0] + ' cm') if dims and not mattress else '', 'image': g('image_link'),
            'badges': list(dict.fromkeys(b))[:2], 'swatches': sw, 'swatch_label': sw_label,
            'sizes': sizes if mattress else [], 'secondary': sec}

# ---------- colour: pick the most contrasting swatches (greedy farthest point in Lab) ----------
def lab(h):
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, b = ((c / 12.92) if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b))
    x, y, z = (r * .4124 + g * .3576 + b * .1805) / .95047, r * .2126 + g * .7152 + b * .0722, (r * .0193 + g * .1192 + b * .9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    return 116 * f(y) - 16, 500 * (f(x) - f(y)), 200 * (f(y) - f(z))

_tlab = {}
def slab(s):
    """Lab of what the swatch really shows: mean of its sprite tile centre (hex fallback for plain colours)."""
    if not s.get('sprite'): return lab(s['hex'])
    k = (s['sprite'], s['i'])
    if k not in _tlab:
        sp = Image.open(os.path.join(ASSETS, 'sprites', s['sprite'])).convert('RGB'); tw = sp.width / s['n']
        r, g, b = sp.crop((int(s['i'] * tw + tw * .25), int(sp.height * .25), int(s['i'] * tw + tw * .75), int(sp.height * .75))).resize((1, 1), Image.BOX).getpixel((0, 0))
        _tlab[k] = lab(f'#{r:02x}{g:02x}{b:02x}')
    return _tlab[k]

LOUD = 45  # e.g. pure red: skipped unless nothing calmer is left
STRONG = 20  # Lab chroma above this = a strong colour; at most one per card keeps the row calm
def chroma(l): return math.hypot(l[1], l[2])

def calm_pick(sw, k, first=None):
    """Spread picks over light and dark (lightness weighted 1.6x), at most 1 strong colour; `first` (photo match) leads."""
    if len(sw) <= k: return ([sw[first]] + [s for i, s in enumerate(sw) if i != first]) if first is not None else sw
    L = [slab(s) for s in sw]
    d = lambda a, b: math.sqrt((1.6 * (L[a][0] - L[b][0])) ** 2 + (L[a][1] - L[b][1]) ** 2 + (L[a][2] - L[b][2]) ** 2)
    neutral = sorted(range(len(sw)), key=lambda i: chroma(L[i]))[:max(1, len(sw) // 2)]
    pick = [first if first is not None else min(neutral, key=lambda i: abs(L[i][0] - 50))]
    while len(pick) < k:
        strong_used = sum(chroma(L[i]) > STRONG for i in pick) >= 1
        free = [i for i in range(len(sw)) if i not in pick]
        pool = [i for i in free if chroma(L[i]) <= LOUD and not (strong_used and chroma(L[i]) > STRONG)] or [i for i in free if not (strong_used and chroma(L[i]) > STRONG)] or free
        pick.append(max(pool, key=lambda i: min(d(i, p) for p in pick)))
    head, rest = pick[:1], sorted(pick[1:], key=lambda i: L[i][0])  # photo colour first, then dark to light
    return [sw[i] for i in (head + rest)]

def photo_match(im, sw):
    """Index of the swatch closest to the product's own colour in the photo, or None when nothing covers >= 3% of it."""
    import numpy as np
    sm = im.resize((160, round(160 * im.height / im.width)))
    a = np.asarray(sm, dtype=float)[int(sm.height * .2):int(sm.height * .9), int(sm.width * .12):int(sm.width * .88)] / 255
    a = np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    xyz = a @ np.array([[.4124, .2126, .0193], [.3576, .7152, .1192], [.1805, .0722, .9505]]) / np.array([.95047, 1, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    px = np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1).reshape(-1, 3)
    px = px[px[:, 0] < 88]  # drop white walls and bright floors
    if all(s.get('sprite', '').startswith(('jtpk-bc', 'jtpk-rustic', 'jtpk-fellis')) for s in sw):
        px = px[np.hypot(px[:, 1], px[:, 2]) > 8]  # wood finishes: ignore grey floors/walls, keep the warm wood tones
    if not len(px): return None
    cnt = [int((np.linalg.norm(px - np.array(slab(s)), axis=1) < 10).sum()) for s in sw]
    best = max(range(len(sw)), key=lambda i: cnt[i])
    return best if cnt[best] >= 0.03 * len(px) else None

def is_cutout(im):
    """Product shot on plain white (no room): >= 90% of the outer 2% border is near white."""
    import numpy as np
    a = np.asarray(im.convert('RGB').resize((200, round(200 * im.height / im.width))))
    b = max(2, a.shape[0] // 50)
    edge = np.concatenate([a[:b].reshape(-1, 3), a[-b:].reshape(-1, 3), a[:, :b].reshape(-1, 3), a[:, -b:].reshape(-1, 3)])
    return float((edge.min(1) > 235).mean()) >= 0.9

# ---------- drawing ----------
def mask(size, r=None):
    m = Image.new('L', (size[0] * X, size[1] * X), 0); dr = ImageDraw.Draw(m); box = (0, 0, m.width - 1, m.height - 1)
    dr.ellipse(box, fill=255) if r is None else dr.rounded_rectangle(box, radius=r * X, fill=255)
    return m.resize(size, Image.LANCZOS)

from PIL import ImageFilter
# depth: the website's own shadow recipes (live Texas page, 2026-10-19), warm ink rgba(53,38,0,a), px at 1080 ≈ 2.4x CSS px
PHOTO_SH = [(5, 10, 0, .06), (43, 96, -53, .30)]   # .woocommerce-product-gallery__wrapper: 0 2px 4px .06, 0 18px 40px -22px .3
BTN_SH = [(24, 66, -19, .45), (5, 14, 0, .12)]      # .jth-btn: 0 10px 28px -8px .45, 0 2px 6px .12
DOT_SH = [(3, 12, 0, .14), (10, 22, -8, .22)]       # swatch lift (site swatch: white ring + soft drop)
def shadow(c, box, radius, layers):
    """Paint layered soft shadows under box=(x0,y0,x1,y1); spread<0 shrinks the shape, like CSS."""
    x0, y0, x1, y1 = box; pad = 140
    for dy, blur, spread, a in layers:
        m = Image.new('L', (int(x1 - x0) + 2 * pad, int(y1 - y0) + 2 * pad), 0)
        r = radius if radius is not None else (y1 - y0) / 2
        ImageDraw.Draw(m).rounded_rectangle((pad - spread, pad - spread, pad + x1 - x0 + spread, pad + y1 - y0 + spread), radius=max(0, r + spread), fill=int(255 * a))
        m = m.filter(ImageFilter.GaussianBlur(blur / 2))
        c.paste(Image.new('RGB', m.size, (53, 38, 0)), (int(x0 - pad), int(y0 - pad + dy)), m)

def ring(c, cx, cy, r, color=LINE, w=3, fill=None):
    big = Image.new('RGBA', ((2 * r + 6) * X,) * 2, (0, 0, 0, 0))
    ImageDraw.Draw(big).ellipse((X, X, big.width - X, big.height - X), outline=color, width=w * X, fill=fill)
    big = big.resize((2 * r + 6,) * 2, Image.LANCZOS); c.paste(big, (cx - r - 3, cy - r - 3), big)

def pill(c, x, y, text, font, fg, bg, h=64, pad=26, outline=None, depth=None, icon=None):
    d = ImageDraw.Draw(c); iw = icon.width + 14 if icon else 0; w = int(d.textlength(text, font=font) + 2 * pad + iw)
    if depth: shadow(c, (x, y, x + w, y + h), h / 2, depth)
    big = Image.new('RGBA', (w * X, h * X), (0, 0, 0, 0))
    ImageDraw.Draw(big).rounded_rectangle((0, 0, big.width - 1, big.height - 1), radius=h * X // 2, fill=bg, outline=outline, width=3 * X if outline else 0)
    big = big.resize((w, h), Image.LANCZOS); c.paste(big, (int(x), int(y)), big)
    if icon: c.paste(icon, (int(x + pad), int(y + (h - icon.height) / 2)), icon)
    d.text((x + iw + (w - iw) / 2, y + h / 2), text, font=font, fill=fg, anchor='mm'); return w

_sprites = {}
def swatch_dot(c, s, cx, cy, r):
    if s.get('sprite'):
        sp = _sprites.setdefault(s['sprite'], Image.open(os.path.join(ASSETS, 'sprites', s['sprite'])).convert('RGB'))
        tw = sp.width / s['n']; x0 = s['i'] * tw
        tile = sp.crop((int(x0 + tw * .2), int(sp.height * .2), int(x0 + tw * .8), int(sp.height * .8))).resize((2 * r, 2 * r), Image.LANCZOS)
    else:
        tile = Image.new('RGB', (2 * r, 2 * r), s['hex'])
    shadow(c, (cx - r - 4, cy - r - 4, cx + r + 4, cy + r + 4), None, DOT_SH)
    ring(c, cx, cy, r + 2, color='white', w=5, fill='white')  # site swatch: 2px white ring
    c.paste(tile, (cx - r, cy - r), mask((2 * r, 2 * r))); ring(c, cx, cy, r, color=(53, 38, 0, 30), w=2)

def ruler_icon(size, color):
    b = size * X; im = Image.new('RGBA', (b * 2, b * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w, h, lw = b * 1.5, b * 0.5, int(b * 0.09); x0, y0 = (b * 2 - w) / 2, (b * 2 - h) / 2
    d.rounded_rectangle((x0, y0, x0 + w, y0 + h), radius=b * 0.08, outline=color, width=lw)
    for i in range(1, 6): tx = x0 + w * i / 6; d.line((tx, y0, tx, y0 + h * (0.5 if i % 2 else 0.35)), fill=color, width=lw)
    return im.rotate(45, resample=Image.BICUBIC).crop((b // 2, b // 2, b * 3 // 2, b * 3 // 2)).resize((size, size), Image.LANCZOS)

def fit(d, text, weight, size, maxw, floor=42):
    while size > floor and d.textlength(text, font=FONT(weight, size)) > maxw: size -= 2
    f = FONT(weight, size)
    while d.textlength(text, font=f) > maxw: text = text[:-2] + '…'
    return text, f

def trim_white(im):
    box = ImageChops.difference(im, Image.new('RGB', im.size, 'white')).convert('L').point(lambda p: 255 if p > 12 else 0).getbbox()
    return im.crop(box) if box else im

ALLOWED_HOSTS = ('jthomedesign.gr', 'www.jthomedesign.gr')  # images are only fetched from the client's own site
def card(it, out):
    u = urllib.parse.urlparse(it['image'])
    if u.scheme != 'https' or u.hostname not in ALLOWED_HOSTS: raise ValueError(f"refused image host for {it['id']!r}")
    raw = urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(it['image'], safe=':/%?=&'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
    im = Image.open(io.BytesIO(raw))
    if im.mode in ('RGBA', 'LA', 'P'): im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
    im = im.convert('RGB'); cut = is_cutout(im); im = trim_white(im)
    c = Image.new('RGB', (S, S), 'white'); d = ImageDraw.Draw(c)
    # info block anchored to the bottom; the photo takes the rest at full width (never cropped)
    has_opt = bool(it['swatches'] or it['sizes'])
    info_h = 62 + 36 + (76 + 36 if has_opt else 0) + 76
    area_top, area_bot = M, S - M - info_h - 44
    r = min((S - 2 * M) / im.width, (area_bot - area_top) / im.height); t = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    px, py = (S - t.width) // 2, area_top + (area_bot - area_top - t.height) // 2
    if cut: c.paste(t, (px, py))  # white-background shot: no box, no shadow, the product sits on the card
    else: shadow(c, (px, py, px + t.width, py + t.height), 28, PHOTO_SH); c.paste(t, (px, py), mask(t.size, 28))
    bx = px + 24
    for b in it['badges']:
        dark = b == 'ΝΕΟ'
        bx += pill(c, bx, py + 24, b, FONT(700 if dark else 600, 36), CREAM if dark else INK, INK if dark else (255, 255, 255),
                   h=68, pad=28, depth=BTN_SH[1:]) + 14

    x, y = M + 4, area_bot + 44
    nm = it['name'].replace('"', '').replace('  ', ' ')
    if d.textlength(nm, font=FONT(600, 52)) > S - 2 * M - 8 and ' με ' in nm: nm = nm.split(' με ')[0]  # "… με Σκαμπό/αποθηκευτικό" is detail, not name
    name, f = fit(d, nm, 600, 62, S - 2 * M - 8, floor=46)
    d.text((x, y), name, font=f, fill=INK, anchor='lt'); y += 62 + 36
    if it['swatches']:
        rad, gap, show = 36, 18, 6
        many = len(it['swatches']) > show; pick = calm_pick(it['swatches'], show - 1 if many else show, photo_match(im, it['swatches']))
        cx = x + rad + 4
        for s_ in pick: swatch_dot(c, s_, cx, y + rad + 2, rad); cx += 2 * rad + gap
        if many:  # "+N" overflow cue: same size and lift as a swatch, cream face
            shadow(c, (cx - rad - 4, y - 2, cx + rad + 4, y + 2 * rad + 6), None, DOT_SH)
            ring(c, cx, y + rad + 2, rad + 2, color='white', w=5, fill='white'); ring(c, cx, y + rad + 2, rad, color=LINE, w=2, fill=CREAM)
            d.text((cx, y + rad + 2), f"+{len(it['swatches']) - len(pick)}", font=FONT(600, 34), fill=INK, anchor='mm'); cx += 2 * rad + gap
        d.text((cx + 6, y + rad + 2), f"{len(it['swatches'])} χρώματα", font=FONT(500, 42), fill=INK2, anchor='lm')
        y += 76 + 36
    elif it['sizes']:
        pref = [s_ for s_ in SIZE_PREF if s_ in it['sizes']][:3] or it['sizes'][:3]
        cx = x
        for s_ in pref: cx += pill(c, cx, y, s_.replace('x', '×'), FONT(500, 40), INK, 'white', h=76, pad=26, outline=LINE, depth=DOT_SH) + 14
        if len(it['sizes']) > len(pref): cx += pill(c, cx, y, f"+{len(it['sizes']) - len(pref)}", FONT(600, 40), INK, CREAM, h=76, pad=24, outline=LINE, depth=DOT_SH) + 14
        y += 76 + 36
    # last row: dimensions (icon + text) left, phone as the site's dark pill button right
    ph = Image.open(os.path.join(HERE, 'icon-phone-hi.png')).convert('RGBA'); ph = ph.resize((round(ph.width * 38 / ph.height), 38), Image.LANCZOS)
    ph = Image.merge('RGBA', (*Image.new('RGB', ph.size, CREAM).split(), ph.split()[3]))  # cream icon on the dark button
    pf = FONT(700, 40); pw = int(d.textlength(PHONE, font=pf) + 2 * 30 + ph.width + 14)
    pill(c, S - M - pw, y, PHONE, pf, CREAM, INK, h=76, pad=30, depth=BTN_SH, icon=ph)
    if it['dims']:
        ic = ruler_icon(46, INK2); c.paste(ic, (x - 2, y + 15), ic)
        dt, df = fit(d, it['dims'], 500, 42, S - M - pw - 24 - (x + 62), floor=34)
        d.text((x + 62, y + 38), dt, font=df, fill=INK2, anchor='lm')
    os.makedirs(os.path.dirname(out), exist_ok=True); c.save(out, quality=90, optimize=True)
