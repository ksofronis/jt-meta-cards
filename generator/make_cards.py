"""Build square Meta catalog cards: name band / original photo (uncropped) / info band.
Usage: python3 make_cards.py feed.xml id1 id2 ...  (no ids = all items)"""
import os, sys, re, io, json, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont, ImageChops
NS = {'g': 'http://base.google.com/ns/1.0'}
S, BAND = 1080, 170
PHONE = '210 247 6585'
_ic = Image.open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'icon-phone-hi.png'))
ICON = _ic.resize((round(_ic.width * 44 / _ic.height), 44), Image.LANCZOS)  # newsletter tabler phone icon

def phone_line(d, cy):
    f = ImageFont.truetype(FB, 42)
    wt = d.textlength(PHONE, font=f); wi = ICON.width
    x = (S - wi - 14 - wt) / 2
    d._image.paste(ICON, (int(x), int(cy - ICON.height / 2)), ICON)
    d.text((x + wi + 14, cy), PHONE, font=f, fill=(34, 34, 34), anchor='lm')
FB = '/System/Library/Fonts/Supplemental/Arial Bold.ttf'
F = '/System/Library/Fonts/Supplemental/Arial.ttf'
DIM = re.compile(r'\d{2,3}(?:[,.]\d)?(?:\s*[xχΧ×]\s*\d{2,3}(?:[,.]\d)?)+')  # 2 or more numbers, e.g. 300x360x170x100
import os; OUT = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'cards')

def split_name(title):
    dims = DIM.findall(title)
    name = DIM.sub('', title)
    name = re.sub(r'(?:[\s,]+|\s[x×])+$', '', re.sub(r'\s{2,}', ' ', name)).strip(' ,-')  # never eat a final letter (Triplex, Lux)
    line = ', '.join(re.sub(r'\s*[xχΧ×]\s*', '×', d) for d in dims)
    return name, (line + ' εκ.') if line else ''

BADGES = [  # (regex on title+description+product_type, badge); first match wins, only claims stated in the feed
    (r'μετατρέπεται σε κρεβάτι|γίνεται κρεβάτι|γωνία\s*[-–]\s*κρεβάτι|καναπέδες κρεβάτια', 'Γίνεται κρεβάτι'),
    (r'με αποθηκευτικό χώρο|ντουλάπια αποθηκευτικού χώρου|πλούσιους αποθηκευτικούς χώρους', 'Με αποθηκευτικό χώρο'),
    (r'^[^|]*τραπέζι[^|]*\|.*(ανοιγόμεν|επεκτειν|επιπλέον χώρο όποτε)', 'Ανοιγόμενο'),
    (r'αλλαγής των (?:εργοστασιακών )?διαστάσ|υφάσματος και διαστάσεων|στις διαστάσεις που επιθυμείτε', 'Στα μέτρα σας'),
    (r'αδιάβροχ.{0,25}(?:ύφασμ|υφάσμ)', 'Αδιάβροχο ύφασμα'),
    (r'ελληνικής κατασκευής', 'Ελληνική κατασκευή'),
    (r'(?:από|σε συνδυασμό με) (?:φυσικό )?ξύλο δρυς|ξύλο δρυς σε συνδυασμό|κατασκευ\w* από (?:φυσικό )?ξύλο δρυς', 'Ξύλο δρυς'),
    (r'best sellers', 'Best Seller'),
    # mattresses (category Στρώματα = last | field): most specific feature first
    (r'(?=.*\|[^|]*στρώματα[^|]*$).*(?:pocket spring|ανεξάρτητ\w* ελατήρ)', 'Pocket ελατήρια'),
    (r'(?=.*\|[^|]*στρώματα[^|]*$).*(?:memory foam|memory gel|αφρ\w* μνήμης)', 'Memory foam'),
    (r'(?=.*\|[^|]*στρώματα[^|]*$).*(?:διπλής όψης|δύο όψεων)', 'Διπλής όψης'),
    (r'(?=.*\|[^|]*στρώματα[^|]*$).*ανατομικ', 'Ανατομικό'),
    (r'φωτισμ\w* led|\bled\b', 'Με φωτισμό LED'),
]
SOFA_LINE = 'Επιλέξτε ύφασμα & διαστάσεις'
def is_sofa(ptype): return 'Καναπέδες' in ptype
def badge_for(text, sofa=False):
    t = ' '.join(text.lower().split())  # one line, single spaces; sofas already carry the customization line, so skip the duplicate badge
    return next((b for rx, b in BADGES if re.search(rx, t) and not (sofa and b == 'Στα μέτρα σας')), '')

def info_line(dims, ptype):
    return dims

def fit(draw, text, font_path, size, maxw):
    if draw.textlength(text, font=ImageFont.truetype(font_path, 44)) > maxw and ' με ' in text:
        text = text.split(' με ')[0]
    while size > 40:
        f = ImageFont.truetype(font_path, size)
        if draw.textlength(text, font=f) <= maxw: return text, f
        size -= 2
    f = ImageFont.truetype(font_path, size)
    while draw.textlength(text + '…', font=f) > maxw: text = text[:-1]
    return text.rstrip() + '…', f

def trim_white(im):
    bg = Image.new('RGB', im.size, (255, 255, 255))
    box = ImageChops.difference(im, bg).convert('L').point(lambda p: 255 if p > 12 else 0).getbbox()
    return im.crop(box) if box else im

def card(item):
    raw = urllib.request.urlopen(urllib.request.Request(urllib.parse.quote(item['image'], safe=':/%?=&'), headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
    im = Image.open(io.BytesIO(raw))
    if im.mode in ('RGBA', 'LA', 'P'):
        im = im.convert('RGBA'); bg = Image.new('RGBA', im.size, 'white'); bg.alpha_composite(im); im = bg
    im = trim_white(im.convert('RGB'))
    c = Image.new('RGB', (S, S), 'white'); d = ImageDraw.Draw(c)
    sofa = item.get('sofa')
    aw, ah = S - 40, S - 2 * BAND
    r = min(aw / im.width, ah / im.height)
    t = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    c.paste(t, ((S - t.width) // 2, BAND + (ah - t.height) // 2))
    name, f = fit(d, item['name'], FB, 64, S - 80)
    d.text((S // 2, BAND // 2 + 6), name, font=f, fill=(34, 34, 34), anchor='mm')
    if sofa:  # customization strip across the bottom of the photo (brown, 88% opaque, white text)
        sf = ImageFont.truetype(FB, 40); sw = max(t.width, int(d.textlength(SOFA_LINE, font=sf)) + 60)
        x0, y0 = (S - sw) // 2, BAND + (ah - t.height) // 2 + t.height - 70
        ov = Image.new('RGBA', (sw, 70), (110, 100, 88, 225)); c.paste(ov, (x0, y0), ov)
        d.text((S // 2, y0 + 35), SOFA_LINE, font=sf, fill='white', anchor='mm')
    if item['line']:
        line, f2 = fit(d, item['line'], F, 44, S - 80)
        d.text((S // 2, S - BAND + 50), line, font=f2, fill=(110, 100, 88), anchor='mm')
        phone_line(d, S - 52)
    else:
        phone_line(d, S - BAND // 2 - 6)
    if item.get('badge'):
        bf = ImageFont.truetype(FB, 38); w = d.textlength(item['badge'], font=bf)
        x0, y0 = 40, BAND + 18
        d.rounded_rectangle((x0, y0, x0 + w + 48, y0 + 66), radius=33, fill=(110, 100, 88))
        d.text((x0 + 24 + w / 2, y0 + 33), item['badge'], font=bf, fill='white', anchor='mm')
    c.save(f"{OUT}/{item['id']}.jpg", quality=88, optimize=True)

items = []
for it in ET.parse(sys.argv[1]).getroot().findall('./channel/item'):
    name, dims = split_name(it.findtext('g:title', namespaces=NS) or '')
    items.append({'id': it.findtext('g:id', namespaces=NS), 'image': it.findtext('g:image_link', namespaces=NS),
                  'name': name, 'line': info_line(dims, it.findtext('g:product_type', namespaces=NS) or ''),
                  'sofa': is_sofa(it.findtext('g:product_type', namespaces=NS) or ''),
                  'badge': badge_for(' | '.join(it.findtext(k, namespaces=NS) or '' for k in ('g:title', 'g:description', 'g:product_type')), is_sofa(it.findtext('g:product_type', namespaces=NS) or ''))})
want = set(sys.argv[2:])
done, failed = [], []
for it in items:
    if want and it['id'] not in want: continue
    try: card(it); done.append(it)
    except Exception as e: failed.append((it['id'], str(e)))
json.dump({'done': done, 'failed': failed}, open(OUT + '/../manifest.json', 'w'), ensure_ascii=False, indent=1)
print(len(done), 'ok', len(failed), 'failed', failed[:5])
