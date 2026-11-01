"""Black Friday ALTERNATIVE Meta catalog cards, built on the live v10 card (make_v7.card) without editing any repo file.

How the v10 card stays exactly as today:
  make_v7.card() is re-compiled from its own source with ONE extra line before its final save, which hands the finished
  canvas and its layout (photo box, badge row, instalments pill) to this module. Every product's v10 canvas is checked
  pixel-for-pixel against an unpatched make_v7.card() render of the same item (check 'v10_identical').
  The BF layer is then drawn on a copy of that canvas. Nothing in the photo box moves or shrinks.

Slot rule (v10 elements keep their place, size and count):
  1. Top-left row on the photo = the v10 chips, untouched (feed badges such as ΝΕΟ / Best Seller, warranty on sofas/beds).
  2. "Ετοιμοπαράδοτο" (13 ready-to-deliver products only) = a product fact, so it uses the v10 badge style and joins the
     top row after the existing chips when it fits inside the photo; otherwise it goes to the free bottom-right slot.
  3. The phase chip (P1 / P2 / P3) = the BF message, one per card, always bottom-right of the photo on the
     instalments-pill row (bottom-left stays the Klarna/TBI pill). Sized to fit there on every v10 photo (max 467 px);
     it is never moved over the product. Black + gold on room photos, light gold + black on cut-outs (qc_assets score).
  No band is added to the 1:1 card: the only free space above the photo is the 44 px margin, and any taller band would
  shrink the photo (v10 rule). The 9:16 version carries the BF band above the card instead, in the cream space.

Allowed: BLACK FRIDAY chip, Εγγύηση τιμής έως 10/12 chip, Έως Πέμπτη 10/12 chip, Ετοιμοπαράδοτο chip, BF band (9:16 only).
Never drawn: price, discount, Viber pill, dark card background, dimension lines on the photo, showroom line, tap hints, zoom.

Usage (read-only for Meta, the feed and the repo; writes only under this folder):
  JT_FEED=data/feed.xml python3 bf_cards.py            renders out/, runs QC, writes out/qc.json and boards/
"""
import os, sys, io, json, inspect, textwrap, unicodedata, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, 'generator'))
sys.dont_write_bytecode = True  # leave no __pycache__ in the repo
import make_v7 as m
import qc_assets as qa     # noqa: E402  repo guardrail, reused as is

# ---------- tokens (bf_system.md) ----------
BF_BLACK, BF_BLACK2, BF_GOLD, BF_GOLD_LT, BF_GOLD_DK = '#0E0D0B', '#1C1A16', '#C9A76A', '#E4CF9E', '#A88848'
CREAM, INK = m.CREAM, m.INK
READY = {'92678', '90505', '88650', '86150', '86083', '85678', '83064', '82358', '81392', '81068', '80681', '78509', '62758'}  # pa_label 5651, parent ids
READY_TXT = 'Ετοιμοπαράδοτο'
PHASES = {
    'P1': {'chip': 'guarantee', 'kicker': 'BLACK FRIDAY ΑΠΟ ΤΩΡΑ', 'line': 'Εγγύηση τιμής έως 10/12'},
    'P2': {'chip': 'bf', 'kicker': '', 'line': 'BLACK FRIDAY'},
    'P3': {'chip': 'last', 'kicker': 'ΤΕΛΕΥΤΑΙΕΣ ΜΕΡΕΣ BLACK FRIDAY', 'line': 'Έως Πέμπτη 10/12'},
}
# Test products: FAMILY hero, Chara table (ready), top sofa / dining / bed / Cosmostrom mattress / lamp by 28-day catalog
# impressions (meta-cards/scorecard/data/2026-10-22/products.csv; mattress: highest Cosmostrom mattress, 318 impressions).
PRODUCTS = [('92679', 'FAMILY hero (parent 92678)'), ('80681', 'Chara table, ready'), ('9288', 'top sofa Paros'),
            ('91348', 'top dining Olympus'), ('45367', 'top bed Elsa'), ('88408', 'Cosmostrom mattress Hypnotic'),
            ('89094', 'top lamp 031')]
# The live feed still carries the old title "Flexy" for FAMILY (site and Store API: "Γωνιακός Καναπές Family 270x200x90").
# Mock only: the card shows the site name. A live card needs the feed title fixed first (supp_build matches on title).
NAME_FIX = {'92679': 'Γωνιακός Καναπές Family'}
FORBIDDEN = ['€', '%', 'Viber', 'Δείτε το από κοντά', 'πατήστε', 'Παράταση', 'τελευταία μέρα', chr(0x2014)]

# ---------- the v10 card, re-compiled with a hook before its save ----------
_src = textwrap.dedent(inspect.getsource(m.card))
_SAVE = "    os.makedirs(os.path.dirname(out), exist_ok=True); c.save(out, quality=90, optimize=True)"
assert _src.count(_SAVE) == 1, 'make_v7.card changed: review the hook point before rendering'
_src = _src.replace(_SAVE, "    _BF_HOOK(c, locals())\n" + _SAVE)
_ns = dict(m.__dict__)
_LAST = {}
def _hook(c, L):
    _LAST.clear(); _LAST['c'] = c.copy()
    _LAST['L'] = {k: L[k] for k in ('px', 'py', 'tw', 'th', 'cut', 'fin', 'mg', 'bx', 'bsh', 'it') if k in L}
_ns['_BF_HOOK'] = _hook
exec(compile(_src, m.__file__, 'exec'), _ns)
card_hooked = _ns['card']

# ---------- drawing helpers ----------
def spaced_len(d, text, font, track):
    return sum(d.textlength(ch, font=font) for ch in text) + track * (len(text) - 1)

def spaced(d, x, cy, text, font, fill, track):
    for ch in text:
        d.text((x, cy), ch, font=font, fill=fill, anchor='lm'); x += d.textlength(ch, font=font) + track

def chip_spec(kind, d, light=False):
    """Width and painter for one chip. kind: ready | guarantee | bf | last."""
    if kind == 'ready':
        f = m.FONT(600, 36); w = int(d.textlength(READY_TXT, font=f) + 2 * 28)
        def paint(c, x, y, h, sh):
            m.pill(c, x, y, READY_TXT, f, INK, (255, 255, 255), h=h, pad=28, depth=sh)
        return w, paint, [READY_TXT]
    # Phase chips: one per card, sized to fit beside the widest instalments pill (Klarna, 455 px) on the narrowest
    # v10 photo (975 px): max 467 px. Style: black fill + gold on room photos; light-gold fill + black on cut-outs
    # (product on the cream panel), because a black chip on a white product drops the qc_assets photo score below
    # 0.35 (measured 29/10: mattress 88408 black 0.28 / light-gold 0.66).
    fill, fg, ol = (BF_GOLD_LT, BF_BLACK, BF_GOLD_DK) if light else (BF_BLACK, BF_GOLD_LT, BF_GOLD)
    if kind == 'guarantee':  # P1: "Εγγύηση τιμής έως 10/12", outlined chip, calm
        f = m.FONT(600, 34); t = 'Εγγύηση τιμής έως 10/12'; w = int(d.textlength(t, font=f) + 2 * 22)
        def paint(c, x, y, h, sh):
            m.pill(c, x, y, t, f, fg, fill, h=h, pad=22, outline=ol, depth=sh)
        return w, paint, [t]
    if kind == 'bf':  # P2: BLACK FRIDAY, letter-spaced caps, the loudest chip
        f = m.FONT(700, 36); t = 'BLACK FRIDAY'; tr = 4; w = int(spaced_len(d, t, f, tr) + 2 * 30)
        def paint(c, x, y, h, sh):
            m.pill(c, x, y, '', f, fg, fill, h=h, pad=w // 2, outline=ol, depth=sh)
            spaced(ImageDraw.Draw(c), x + 30, y + h / 2, t, f, BF_GOLD if not light else BF_BLACK, tr)
        return w, paint, [t]
    if kind == 'last':  # P3: "Έως Πέμπτη 10/12" (a "BLACK FRIDAY" label inside would need 621 px: does not fit)
        f = m.FONT(600, 36); t = 'Έως Πέμπτη 10/12'; w = int(d.textlength(t, font=f) + 2 * 26)
        def paint(c, x, y, h, sh):
            m.pill(c, x, y, t, f, fg, fill, h=h, pad=26, outline=ol, depth=sh)
        return w, paint, [t]
    raise ValueError(kind)

def fin_width(d, fin):
    f, chip = m.FONT(600, 36), m.FONT(700, 28); label, text = fin
    cw = int(d.textlength(label, font=chip)) + 24; return int(d.textlength(text, font=f)) + cw + 26 + 26

def top_row_right(d, L):
    """Right edge of the v10 top chip row (badges + warranty), recomputed from make_v7's own sizes."""
    it, x = L['it'], L['px'] + 24
    for b in it['badges'][:1 if it.get('warranty') else 2]:
        dark = b == 'ΝΕΟ'; x += int(d.textlength(b, font=m.FONT(700 if dark else 600, 36)) + 2 * 28) + 14
    if it.get('warranty'):
        x += int(d.textlength(m.WARRANTY, font=m.FONT(600, 36)) + 2 * 26 + 38 + 14) + 14
    return x  # next free x (includes the 14 px gap)

def bf_layer(base, L, phase, ready, with_phase_chip=True):
    """Copy of the v10 canvas + BF chips. Returns (image, list of chip rects, texts drawn)."""
    c = base.copy(); d = ImageDraw.Draw(c)
    px, py, tw, th, sh = L['px'], L['py'], L['tw'], L['th'], L['bsh'][1:]
    right, gap = px + tw - 24, 14
    top_x = top_row_right(d, L)
    bot_left = px + 24 + (fin_width(d, L['fin']) + gap if L['fin'] else 0)
    row_y = {'top': py + 24, 'bot': py + th - 24 - 72, 'bot2': py + th - 24 - 72 - 14 - 72}
    used_br = right  # bottom row fills from the right
    rects, texts, place = [], [], []
    if ready:
        w, paint, tx = chip_spec('ready', d)
        if top_x + w <= right: place.append(('top', top_x, w, 68, paint, tx)); top_x += w + gap
        else: place.append(('bot', used_br - w, w, 72, paint, tx)); used_br -= w + gap
    if with_phase_chip:
        w, paint, tx = chip_spec(PHASES[phase]['chip'], d, light=L['cut'])
        # always the bottom-right slot; never moved over the product (a too-narrow photo is reported, not drawn elsewhere)
        if used_br - w < bot_left: raise ValueError(f"phase chip {w}px does not fit beside the instalments pill on {L['it']['id']}")
        place.append(('bot', used_br - w, w, 72, paint, tx))
    for row, x, w, h, paint, tx in place:
        y = row_y[row]; paint(c, x, y, h, sh); rects.append((x, y, x + w, y + h)); texts += tx
    return c, rects, texts

# ---------- 9:16: card on the cream base, BF band above it, Stories safe zones kept clear ----------
SH, TOP_SAFE, BOT_SAFE = 1920, 250, 340      # Meta Stories: top ~14% and bottom ~18% sit under the profile row / CTA
BAND_Y, BAND_H, CARD_Y = TOP_SAFE, 220, TOP_SAFE + 220 + 20   # card 490..1570, bottom zone 1570..1920 stays cream
def story(card_img, phase):
    s = Image.new('RGB', (m.S, SH), CREAM); d = ImageDraw.Draw(s)
    p = PHASES[phase]; texts = []
    m.shadow(s, (0, CARD_Y, m.S, CARD_Y + m.S), 0, [(6, 24, 0, .10)])  # lift the white card off the cream
    s.paste(card_img, (0, CARD_Y))
    d.rectangle((0, BAND_Y, m.S, BAND_Y + BAND_H), fill=BF_BLACK)
    d.rectangle((0, BAND_Y + BAND_H - 4, m.S, BAND_Y + BAND_H), fill=BF_GOLD)
    cx = m.S / 2
    if p['kicker']:
        kf = m.FONT(700, 38); kw = spaced_len(d, p['kicker'], kf, 5)
        spaced(d, cx - kw / 2, BAND_Y + 70, p['kicker'], kf, BF_GOLD, 5); texts.append(p['kicker'])
        lf = m.FONT(600, 62); ic = m.shield(56, BF_GOLD_LT) if phase == 'P1' else None
        lw = d.textlength(p['line'], font=lf) + (ic.width + 18 if ic else 0); x0 = cx - lw / 2
        if ic: s.paste(ic, (int(x0), int(BAND_Y + 146 - ic.height / 2)), ic); x0 += ic.width + 18
        d.text((x0, BAND_Y + 146), p['line'], font=lf, fill=BF_GOLD_LT, anchor='lm'); texts.append(p['line'])
    else:
        lf = m.FONT(700, 104); lw = spaced_len(d, p['line'], lf, 12)
        spaced(d, cx - lw / 2, BAND_Y + BAND_H / 2 - 4, p['line'], lf, BF_GOLD, 12); texts.append(p['line'])
    return s, texts

# ---------- data ----------
def feed_items():
    root = ET.parse(os.environ.get('JT_FEED', os.path.join(HERE, 'data', 'feed.xml'))).getroot()
    g = lambda it, k: (it.findtext(f'g:{k}', namespaces=m.NS) or '').strip()
    return {g(it, 'id'): it for it in root.findall('./channel/item')}, g

def item_spec(it, g):
    """Same item dict as v7_cards.py builds today (v9 on, crop from v8_crops.json, 4:5 off since 21/10)."""
    crops = json.load(open(os.path.join(REPO, 'v8_crops.json')))
    V9 = open(os.path.join(REPO, 'v9.txt')).read().strip() == 'on'
    iid = g(it, 'id'); crop = crops[iid]['crop'] if iid in crops and crops[iid]['image'] == g(it, 'image_link') else None
    spec = dict(m.build(it), crop=crop, v9=V9, r45=False)
    return spec

def src_photo(spec):
    """Source photo prepared the way card() prepares it (for the qc_assets photo check)."""
    import urllib.request, urllib.parse
    raw = urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(spec['image'], safe=':/%?=&'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
    im = Image.open(io.BytesIO(raw))
    if im.mode in ('RGBA', 'LA', 'P'): im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
    im = im.convert('RGB'); cut = m.is_cutout(im); im = m.trim_white(im)
    if spec.get('crop') and not cut and not spec.get('p1'): im = im.crop(tuple(spec['crop']))
    return im

def main():
    out = os.path.join(HERE, 'out'); [os.makedirs(os.path.join(out, k), exist_ok=True) for k in ('v10', '1x1', '9x16')]
    tmp = os.path.join(HERE, 'out', '_tmp'); os.makedirs(tmp, exist_ok=True)
    feed, g = feed_items(); qc = {}
    for iid, why in PRODUCTS:
        it = feed[iid]; spec = item_spec(it, g)
        if iid in NAME_FIX: spec['name'] = NAME_FIX[iid]
        ready = iid in READY or g(it, 'item_group_id') in READY
        # v10 exactly as today: plain make_v7.card vs hooked render must be identical
        m.card(spec, os.path.join(tmp, f'{iid}_plain.png'))
        card_hooked(spec, os.path.join(out, 'v10', f'{iid}_v10.png'))
        base, L = _LAST['c'], _LAST['L']
        same = Image.open(os.path.join(tmp, f'{iid}_plain.png')).convert('RGB').tobytes() == base.tobytes()
        src = src_photo(spec); box = (L['px'], L['py'], L['px'] + L['tw'], L['py'] + L['th'])
        rec = {'why': why, 'name': spec['name'], 'v10_identical': same, 'photo_box': box, 'cut': L['cut'],
               'badges': spec['badges'], 'warranty': spec['warranty'], 'finance': spec['finance'], 'ready': ready,
               'v10_photo_score': round(qa.photo_score(base, src, box), 3), 'assets': {}}
        for ph in PHASES:
            sq, rects, tx = bf_layer(base, L, ph, ready)
            f1 = os.path.join(out, '1x1', f'{iid}_{ph}.png'); sq.save(f1, optimize=True)
            # unchanged outside the chips: every pixel outside the BF chip rects (plus 40 px shadow margin) equals v10
            import numpy as np
            a, b = np.asarray(sq).astype(int), np.asarray(base).astype(int); keep = np.ones(a.shape[:2], bool)
            for x0, y0, x1, y1 in rects: keep[max(0, y0 - 40):y1 + 60, max(0, x0 - 40):x1 + 40] = False
            untouched = bool((a[keep] == b[keep]).all())
            card_for_story, _, tx_s = bf_layer(base, L, ph, ready, with_phase_chip=False)
            st, tx2 = story(card_for_story, ph); f2 = os.path.join(out, '9x16', f'{iid}_{ph}.png'); st.save(f2, optimize=True)
            sbox = (box[0], box[1] + CARD_Y, box[2], box[3] + CARD_Y)
            words = ' '.join(tx + tx2 + [spec['name']])
            for f, bx_, kind in ((f1, box, '1x1'), (f2, sbox, '9x16')):
                im = Image.open(f); score = qa.photo_score(im, src, bx_)
                rec['assets'][f'{ph}_{kind}'] = {
                    'file': os.path.relpath(f, HERE), 'size': im.size, 'photo_score': round(score, 3),
                    'qc_assets_photo': bool(qa.check_image(f, src, bx_)),           # repo guardrail (>= 0.35)
                    'size_ok': im.size == ((1080, 1080) if kind == '1x1' else (1080, 1920)),
                    'photo_box_same_as_v10': True,                                    # base canvas is the v10 canvas
                    'outside_chips_unchanged': untouched if kind == '1x1' else None,
                    'chips_inside_photo': all(box[0] <= r[0] and r[2] <= box[2] and box[1] <= r[1] and r[3] <= box[3] for r in rects),
                    'no_forbidden_words': not any(w in words for w in FORBIDDEN)}
                a_ = rec['assets'][f'{ph}_{kind}']
                a_['pass'] = all(v for k, v in a_.items() if k in ('qc_assets_photo', 'size_ok', 'chips_inside_photo', 'no_forbidden_words')) \
                    and same and a_['outside_chips_unchanged'] is not False
            rec['assets'][f'{ph}_1x1']['chip_rects'] = rects
        qc[iid] = rec; print(iid, spec['name'], 'v10_identical', same, {k: v['pass'] for k, v in rec['assets'].items()})
    json.dump(qc, open(os.path.join(out, 'qc.json'), 'w'), ensure_ascii=False, indent=1)
    for f in os.listdir(tmp): os.remove(os.path.join(tmp, f))
    os.rmdir(tmp)
    boards(qc)

# ---------- boards: v10 beside P1/P2/P3 (rule: new card ideas are shown next to v10) ----------
def boards(qc):
    bd = os.path.join(HERE, 'boards'); os.makedirs(bd, exist_ok=True)
    lab = m.FONT(700, 30); sub = m.FONT(500, 24); T = 540
    tiles = []
    for iid, rec in qc.items():
        W, H = 4 * T + 5 * 24, 70 + T + 60 + 960 + 40
        b = Image.new('RGB', (W, H), '#ECE6DA'); d = ImageDraw.Draw(b)
        d.text((24, 20), f"{rec['name']}  ·  id {iid}  ·  {rec['why']}", font=lab, fill=INK)
        cols = [('v10 (live)', f'out/v10/{iid}_v10.png')] + [(ph, f'out/1x1/{iid}_{ph}.png') for ph in PHASES]
        for k, (t, f) in enumerate(cols):
            x = 24 + k * (T + 24); b.paste(Image.open(os.path.join(HERE, f)).convert('RGB').resize((T, T), Image.LANCZOS), (x, 70))
            ok = '' if k == 0 else ('  QC pass' if rec['assets'][f'{t}_1x1']['pass'] else '  QC FAIL')
            d.text((x, 70 + T + 14), t + ' 1:1' + ok, font=sub, fill=INK)
        d.text((24, 70 + T + 60 + 20), '9:16 versions', font=lab, fill=INK)
        d.text((24, 70 + T + 60 + 64), 'v10 has no 9:16 card;', font=sub, fill=INK)
        d.text((24, 70 + T + 60 + 96), 'Meta letterboxes the 1:1.', font=sub, fill=INK)
        for k, ph in enumerate(PHASES):
            x = 24 + (k + 1) * (T + 24)
            b.paste(Image.open(os.path.join(HERE, f'out/9x16/{iid}_{ph}.png')).convert('RGB').resize((T, 960), Image.LANCZOS), (x, 70 + T + 60))
        b.save(os.path.join(bd, f'{iid}_compare.jpg'), quality=88)
        tiles.append((iid, rec))
    # overview: one row per product, v10 | P1 | P2 | P3 (1:1) | P1 | P2 | P3 (9:16)
    t, ts = 300, (169, 300)
    W = 24 + 4 * (t + 16) + 3 * (ts[0] + 16) + 8; H = 60 + len(tiles) * (t + 40) + 10
    o = Image.new('RGB', (W, H), '#ECE6DA'); d = ImageDraw.Draw(o)
    d.text((24, 16), 'JT Black Friday catalog cards on v10: v10 | P1 | P2 | P3 (1:1) | P1 | P2 | P3 (9:16)', font=sub, fill=INK)
    for r, (iid, rec) in enumerate(tiles):
        y = 60 + r * (t + 40); x = 24
        for f in [f'out/v10/{iid}_v10.png'] + [f'out/1x1/{iid}_{ph}.png' for ph in PHASES]:
            o.paste(Image.open(os.path.join(HERE, f)).convert('RGB').resize((t, t), Image.LANCZOS), (x, y)); x += t + 16
        for ph in PHASES:
            o.paste(Image.open(os.path.join(HERE, f'out/9x16/{iid}_{ph}.png')).convert('RGB').resize(ts, Image.LANCZOS), (x, y)); x += ts[0] + 16
        d.text((24, y + t + 6), f"{iid} {rec['name']}", font=m.FONT(500, 20), fill=INK)
    o.save(os.path.join(bd, 'overview.jpg'), quality=88)

if __name__ == '__main__':
    main()
