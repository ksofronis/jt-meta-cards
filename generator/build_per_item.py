"""One card per feed item (id.jpg) + manifest {id: {image, title}} used by the feed job to decide swaps."""
import sys, os, json, xml.etree.ElementTree as ET
sys.argv = [os.path.abspath('make_cards.py')]
exec(open('make_cards.py').read().split('items = []')[0])
OUT = os.path.abspath('cards_item'); os.makedirs(OUT, exist_ok=True)
man, failed = {}, []
for it in ET.parse(os.environ['FEED']).getroot().findall('./channel/item'):
    t = lambda k: it.findtext(k, namespaces=NS) or ''
    iid, img, title = t('g:id'), t('g:image_link'), t('g:title')
    if not img: continue
    name, dims = split_name(title)
    item = {'id': iid, 'image': img, 'name': name, 'line': info_line(dims, t('g:product_type')),
            'badge': badge_for(' | '.join(t(k) for k in ('g:title', 'g:description', 'g:product_type')))}
    try:
        if not os.path.exists(f'{OUT}/{iid}.jpg'): card(item)
        man[iid] = {'image': img, 'title': title}
    except Exception as e:
        failed.append((iid, str(e)))
json.dump(man, open('manifest_items.json', 'w'), ensure_ascii=False, indent=0)
print('cards', len(man), 'failed', len(failed), failed[:5])
