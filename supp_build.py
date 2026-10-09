"""Build feed/supplementary.csv (id,image_link) for Meta.
Includes the first N ids of the rollout order (supp_count.txt) whose manifest photo+title still match the live feed.
Products whose photo or title changed are left out, so Meta keeps their original image."""
import csv, json, re, urllib.request
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
raw = urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read().decode()
cur = {}
for b in re.findall(r'<item>.*?</item>', raw, re.S):
    g = lambda t: (re.search(rf'<g:{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:{t}>', b, re.S) or [None, ''])[1].strip()
    cur[g('id')] = (g('image_link'), g('title'))
man = json.load(open('manifest_items.json'))
order = [l.strip() for l in open('supp_order.txt') if l.strip()]
n = int(open('supp_count.txt').read().strip())
rows = [(i, f'https://ksofronis.github.io/jt-meta-cards/item/{i}.jpg') for i in order[:n]
        if i in man and i in cur and cur[i] == (man[i]['image'], man[i]['title'])]
with open('feed/supplementary.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['id', 'image_link']); w.writerows(rows)
print('supplementary rows', len(rows), 'of first', n)
