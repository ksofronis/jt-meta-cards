"""Hourly: v7 cards for products in the groups enabled in v7_groups.txt (rollout: sofas, tables, bedrooms, rest).
Renders new products and products whose photo/title changed since their v7 card. Output: v7/<id>-<hash>.jpg + v7_manifest.json.
supp_build.py prefers a v7 card while it matches the live feed and its group is enabled.
Usage: python3 v7_cards.py                      (normal run, max MAX per run)
       python3 v7_cards.py --preview ID ID ...  (render to preview/, no manifest change)"""
import sys, os, re, json, hashlib, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('generator'))
import make_v7 as m, v7_groups
MAX = 60
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
SAFE_ID = re.compile(r'[A-Za-z0-9_-]{1,64}')  # id becomes a file name
root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read())
g = lambda it, k: (it.findtext(f'g:{k}', namespaces=m.NS) or '').strip()
on = v7_groups.enabled()
items = [it for it in root.findall('./channel/item') if SAFE_ID.fullmatch(g(it, 'id')) and v7_groups.group_of(g(it, 'product_type')) in on]
if '--preview' in sys.argv:
    want = set(sys.argv[sys.argv.index('--preview') + 1:]); os.makedirs('preview', exist_ok=True)
    for it in root.findall('./channel/item'):
        if g(it, 'id') in want: m.card(m.build(it), f"preview/v7_{g(it, 'id')}.jpg"); print('preview', g(it, 'id'))
    sys.exit()
man = json.load(open('v7_manifest.json')) if os.path.exists('v7_manifest.json') else {}
todo = [it for it in items if (man.get(g(it, 'id'), {}).get('image'), man.get(g(it, 'id'), {}).get('title')) != (g(it, 'image_link'), g(it, 'title'))]
print('groups', sorted(on), '| products', len(items), '| needing a v7 card', len(todo), '| this run', min(len(todo), MAX))
os.makedirs('v7', exist_ok=True); made = 0
for it in todo[:MAX]:
    iid, img, title = g(it, 'id'), g(it, 'image_link'), g(it, 'title')
    path = f"v7/{iid}-{hashlib.sha1((img + '|' + title).encode()).hexdigest()[:8]}.jpg"  # new name per change -> Meta re-downloads
    try: m.card(m.build(it), path)
    except Exception as e: print('failed', iid, str(e)[:100]); continue
    old = man.get(iid, {}).get('path')
    if old and old != path and os.path.exists(old): os.remove(old)
    man[iid] = {'image': img, 'title': title, 'path': path}; made += 1
json.dump(man, open('v7_manifest.json', 'w'), ensure_ascii=False, indent=0)
print('v7 cards made', made)
