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
import datetime, os
# v2 cards (fixed names, sofa line, new badges) switch on at V2_AT so the image change happens at night
V2_AT = datetime.datetime(2026, 10, 10, 20, 55, tzinfo=datetime.timezone.utc)  # 23:55 Athens, Meta reads at 00:06
v2 = set(open('v2_ids.txt').read().split()) if os.path.exists('v2_ids.txt') and datetime.datetime.now(datetime.timezone.utc) >= V2_AT else set()
v2 |= set(open('v2_now.txt').read().split()) if os.path.exists('v2_now.txt') else set()  # name fixes + sofas: switched immediately
v3 = set(open('v3_now.txt').read().split()) if os.path.exists('v3_now.txt') else set()  # sofas, customization strip on the photo
url = lambda i: f'https://ksofronis.github.io/jt-meta-cards/{"v3" if i in v3 else "v2" if i in v2 else "item"}/{i}.jpg'
rows = [(i, url(i)) for i in order[:n]
        if i in man and i in cur and cur[i] == (man[i]['image'], man[i]['title'])]
with open('feed/supplementary.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['id', 'image_link']); w.writerows(rows)
print('supplementary rows', len(rows), 'of first', n, '| v2', sum(1 for r in rows if '/v2/' in r[1]), '| v3', sum(1 for r in rows if '/v3/' in r[1]))
