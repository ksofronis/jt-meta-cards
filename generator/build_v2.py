"""Rebuild only the cards whose text changes between make_cards_v1.py and make_cards.py.
Writes <repo>/v2/<id>.jpg and <repo>/v2_ids.txt. Photo source = manifest (original image_link)."""
import sys, os, json, collections, xml.etree.ElementTree as ET
REPO = sys.argv[1]; DRY = '--dry' in sys.argv
def load(fn):
    ns = {}; sys.argv[0] = os.path.abspath(fn); exec(open(fn).read().split('items = []')[0], ns); return ns
old, new = load('make_cards_v1.py'), load('make_cards.py')
NS = new['NS']; man = json.load(open(f'{REPO}/manifest_items.json'))
live = set(l.split(',')[0] for l in open(f'{REPO}/feed/supplementary.csv').read().split()[1:])
def spec(m, g):
    name, dims = m['split_name'](g('g:title')); pt = g('g:product_type'); txt = ' | '.join(g(k) for k in ('g:title', 'g:description', 'g:product_type'))
    if 'is_sofa' in m:
        return {'name': name, 'line': m['info_line'](dims, pt), 'badge': m['badge_for'](txt, m['is_sofa'](pt)), 'sofa': m['is_sofa'](pt)}
    return {'name': name, 'line': m['info_line'](dims, pt), 'badge': m['badge_for'](txt), 'sofa': False}
todo, why = [], collections.Counter(); badges = collections.Counter()
for it in ET.parse(f'{REPO}/feed/facebook.xml').getroot().findall('./channel/item'):
    g = lambda k: it.findtext(k, namespaces=NS) or ''
    i = g('g:id')
    if i not in live or i not in man: continue
    a, b = spec(old, g), spec(new, g); badges[b['badge'] or '(none)'] += 1
    if a != b:
        for k in a:
            if a[k] != b[k]: why[k] += 1
        todo.append(dict(b, id=i, image=man[i]['image']))
print('changed cards', len(todo), dict(why)); print('badges after', dict(badges.most_common()))
if DRY: sys.exit()
os.makedirs(f'{REPO}/v2', exist_ok=True); new['OUT'] = f'{REPO}/v2'; fail = []
for k, it in enumerate(todo):
    try: new['card'](it)
    except Exception as e: fail.append((it['id'], str(e)[:80]))
    if k % 100 == 0: print(k, flush=True)
open(f'{REPO}/v2_ids.txt', 'w').write('\n'.join(t['id'] for t in todo if t['id'] not in dict(fail)) + '\n')
print('built', len(todo) - len(fail), 'failed', fail)
