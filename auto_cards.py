"""Hourly: make cards for products that have none yet (new) or whose photo/title changed on the website.
Same renderer and rules as the bulk build (generator/make_cards.py). Output: auto/<id>-<hash>.jpg + auto_manifest.json.
A new file name per change makes Meta download the new card. supp_build.py uses these when they match the live feed.
Usage: python3 auto_cards.py            (normal run, max MAX per run)
       python3 auto_cards.py --preview ID ID ...   (render given ids to preview/, no manifest change)"""
import sys, os, json, hashlib, re, urllib.request, xml.etree.ElementTree as ET
MAX = 60
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
GEN = os.path.abspath('generator/make_cards.py')
ns = {}; argv = sys.argv; sys.argv = [GEN]; exec(open(GEN).read().split('items = []')[0], ns); sys.argv = argv
NS = ns['NS']
root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read())
def spec(it):
    g = lambda k: (it.findtext(k, namespaces=NS) or '').strip()
    pt = g('g:product_type'); sofa = ns['is_sofa'](pt); name, dims = ns['split_name'](g('g:title'))
    return {'id': g('g:id'), 'image': g('g:image_link'), 'title': g('g:title'), 'name': name, 'line': ns['info_line'](dims, pt), 'sofa': sofa,
            'badges': ns['badges_for'](' | '.join(g(k) for k in ('g:title', 'g:description', 'g:product_type')), sofa)}
items = [spec(it) for it in root.findall('./channel/item')]
items = [i for i in items if i['id'] and i['image']]
if '--preview' in sys.argv:
    want = set(sys.argv[sys.argv.index('--preview') + 1:]); os.makedirs('preview', exist_ok=True); ns['OUT'] = os.path.abspath('preview')
    for it in items:
        if it['id'] in want: ns['card'](it); print('preview', it['id'], it['name'], it['badges'])
    sys.exit()
man = json.load(open('manifest_items.json'))
auto = json.load(open('auto_manifest.json')) if os.path.exists('auto_manifest.json') else {}
def done(it):
    m = man.get(it['id']); a = auto.get(it['id'])
    return (m and (m['image'], m['title']) == (it['image'], it['title'])) or (a and (a['image'], a['title']) == (it['image'], it['title']))
todo = [it for it in items if not done(it)]
print('products needing a card', len(todo), '| this run', min(len(todo), MAX))
os.makedirs('auto', exist_ok=True); ns['OUT'] = os.path.abspath('auto'); made = 0
for it in todo[:MAX]:
    h = hashlib.sha1((it['image'] + '|' + it['title']).encode()).hexdigest()[:8]
    it2 = dict(it, id=f"{it['id']}-{h}")
    try:
        ns['card'](it2)
    except Exception as e:
        print('failed', it['id'], str(e)[:100]); continue
    old = auto.get(it['id'], {}).get('path')
    if old and os.path.exists(old): os.remove(old)
    auto[it['id']] = {'image': it['image'], 'title': it['title'], 'path': f"auto/{it2['id']}.jpg"}; made += 1
json.dump(auto, open('auto_manifest.json', 'w'), ensure_ascii=False, indent=0)
print('cards made', made)
