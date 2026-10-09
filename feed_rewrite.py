"""Copy the JT Home Design Meta feed and point each product's image_link at its card.
Swap only when the card was built from the same photo and title (manifest_items.json); otherwise keep the original.
Refuses to publish when the source looks broken (guards against a REPLACE upload deleting products)."""
import json, os, re, sys, urllib.request, xml.etree.ElementTree as ET
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
BASE = 'https://ksofronis.github.io/jt-meta-cards/item/'
OUT = 'feed/facebook.xml'
raw = urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read().decode('utf-8')
ET.fromstring(raw.encode())  # source must be valid XML
man = json.load(open('manifest_items.json'))
blocks = re.split(r'(<item>.*?</item>)', raw, flags=re.S)
items = swapped = 0
def tag(b, t):
    m = re.search(rf'<g:{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:{t}>', b, re.S); return m.group(1).strip() if m else ''
for i, b in enumerate(blocks):
    if not b.startswith('<item>'): continue
    items += 1
    iid, img, title = tag(b, 'id'), tag(b, 'image_link'), tag(b, 'title')
    m = man.get(iid)
    if m and m['image'] == img and m['title'] == title and os.path.exists(f'item/{iid}.jpg'):
        blocks[i] = re.sub(r'(<g:image_link>)(?:<!\[CDATA\[)?.*?(?:\]\]>)?(</g:image_link>)',
                           lambda x: f'{x.group(1)}<![CDATA[{BASE}{iid}.jpg]]>{x.group(2)}', b, count=1, flags=re.S)
        swapped += 1
out = ''.join(blocks)
ET.fromstring(out.encode())  # output must be valid XML
prev = len(re.findall(r'<item>', open(OUT).read())) if os.path.exists(OUT) else items
if items < 100 or items < 0.9 * prev:
    sys.exit(f'REFUSED: source has {items} items vs {prev} previously published')
if len(re.findall(r'<item>', out)) != items:
    sys.exit('REFUSED: item count changed during rewrite')
open(OUT, 'w').write(out)
print(f'items {items} swapped {swapped} kept_original {items - swapped}')
