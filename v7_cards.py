"""Hourly: v7 cards for products in the groups enabled in v7_groups.txt (rollout: sofas, tables, bedrooms, rest).
Renders new products and products whose photo/title changed since their v7 card. Output: v7/<id>-<hash>.jpg + v7_manifest.json.
supp_build.py prefers a v7 card while it matches the live feed and its group is enabled.
Usage: python3 v7_cards.py                      (normal run, max MAX per run)
       python3 v7_cards.py --preview ID ID ...  (render to preview/, no manifest change)"""
import sys, os, re, json, hashlib, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('generator'))
import make_v7 as m, v7_groups
MAX = int(os.environ.get('V7_MAX', 60))
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
SAFE_ID = re.compile(r'[A-Za-z0-9_-]{1,64}')  # id becomes a file name
root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read())
g = lambda it, k: (it.findtext(f'g:{k}', namespaces=m.NS) or '').strip()
on = v7_groups.enabled()
items = [it for it in root.findall('./channel/item') if SAFE_ID.fullmatch(g(it, 'id')) and v7_groups.group_of(g(it, 'product_type')) in on]
# v8: per-product crop boxes found offline (meta-cards/v8, product mask + visual QC); used only while the photo is unchanged
crops = json.load(open('v8_crops.json')) if os.path.exists('v8_crops.json') else {}
# v9: instalments pill + cream panel for white-background shots; switch = v9.txt ('on'), rollback = empty file (cards rebuild back to v7/v8)
V9 = os.path.exists('v9.txt') and open('v9.txt').read().strip() == 'on'
# v10 4:5 crop-safe card, per product group listed in v45_groups.txt (rollout: tables first, 2026-10-21)
G45 = v7_groups.enabled('v45_groups.txt')
R45 = lambda it: v7_groups.group_of(g(it, 'product_type')) in G45
v9_of = lambda it: ('v9:' + ('|'.join(m.finance_line(g(it, 'sale_price') or g(it, 'price')) or ('-',))) + m.name_salt(g(it, 'title')) + '|L10' + ('|45' if R45(it) else '') + ('|W' if m.has_warranty(g(it, 'product_type')) else '')) if V9 else None  # |L10: legible layout (2026-10-21), part of the card hash
crop_of = lambda it: crops[g(it, 'id')]['crop'] if g(it, 'id') in crops and crops[g(it, 'id')]['image'] == g(it, 'image_link') else None
if '--preview' in sys.argv:
    want = set(sys.argv[sys.argv.index('--preview') + 1:]); os.makedirs('preview', exist_ok=True)
    for it in root.findall('./channel/item'):
        if g(it, 'id') in want: m.card(dict(m.build(it), crop=crop_of(it), v9=V9, r45=R45(it)), f"preview/v7_{g(it, 'id')}.jpg"); print('preview', g(it, 'id'))
    sys.exit()
man = json.load(open('v7_manifest.json')) if os.path.exists('v7_manifest.json') else {}
key_of = lambda e: (e.get('image'), e.get('title'), e.get('crop'), e.get('v9'))
todo = [it for it in items if key_of(man.get(g(it, 'id'), {})) != (g(it, 'image_link'), g(it, 'title'), crop_of(it), v9_of(it))]
print('groups', sorted(on), '| products', len(items), '| needing a v7 card', len(todo), '| this run', min(len(todo), MAX))
os.makedirs('v7', exist_ok=True); made = 0
for it in todo[:MAX]:
    iid, img, title = g(it, 'id'), g(it, 'image_link'), g(it, 'title')
    crop, v9 = crop_of(it), v9_of(it)
    path = f"v7/{iid}-{hashlib.sha1((img + '|' + title + ('|' + str(crop) if crop else '') + ('|' + v9 if v9 else '')).encode()).hexdigest()[:8]}.jpg"  # new name per change -> Meta re-downloads
    try: m.card(dict(m.build(it), crop=crop, v9=bool(v9), r45=R45(it)), path)
    except Exception as e: print('failed', iid, str(e)[:100]); continue
    old = man.get(iid, {}).get('path')
    if old and old != path and os.path.exists(old): os.remove(old)
    man[iid] = {'image': img, 'title': title, 'path': path, **({'crop': crop} if crop else {}), **({'v9': v9} if v9 else {})}; made += 1
json.dump(man, open('v7_manifest.json', 'w'), ensure_ascii=False, indent=0)
print('v7 cards made', made)
