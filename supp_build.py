"""Build feed/supplementary.csv (id,image_link) for Meta.
Includes the first N ids of the rollout order (supp_count.txt) whose manifest photo+title still match the live feed.
Products whose photo or title changed are left out, so Meta keeps their original image."""
import csv, json, re, html, urllib.request
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
raw = urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read().decode()
cur = {}
for b in re.findall(r'<item>.*?</item>', raw, re.S):
    g = lambda t: (re.search(rf'<g:{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:{t}>', b, re.S) or [None, ''])[1].strip()
    cur[g('id')] = (html.unescape(g('image_link')), html.unescape(g('title')))  # same text as the XML parser (&quot; etc.)
man = json.load(open('manifest_items.json'))
order = [l.strip() for l in open('supp_order.txt') if l.strip()]
n = int(open('supp_count.txt').read().strip())
import datetime, os
# v2 cards (fixed names, sofa line, new badges) switch on at V2_AT so the image change happens at night
V2_AT = datetime.datetime(2026, 10, 10, 20, 55, tzinfo=datetime.timezone.utc)  # 23:55 Athens, Meta reads at 00:06
v2 = set(open('v2_ids.txt').read().split()) if os.path.exists('v2_ids.txt') and datetime.datetime.now(datetime.timezone.utc) >= V2_AT else set()
v2 |= set(open('v2_now.txt').read().split()) if os.path.exists('v2_now.txt') else set()  # name fixes + sofas: switched immediately
v3 = set(open('v3_now.txt').read().split()) if os.path.exists('v3_now.txt') else set()  # sofas, customization strip on the photo
# v4: 9 modular sofas with the Πολυμορφικός badge; switch with the rest at V2_AT (no second daytime dropout)
v4 = set(open('v4_ids.txt').read().split()) if os.path.exists('v4_ids.txt') and datetime.datetime.now(datetime.timezone.utc) >= V2_AT else set()
# v5: up to 2 badges side by side (138 cards); also switches at V2_AT, highest priority
v5 = set(open('v5_ids.txt').read().split()) if os.path.exists('v5_ids.txt') and datetime.datetime.now(datetime.timezone.utc) >= V2_AT else set()
url = lambda i: f'https://ksofronis.github.io/jt-meta-cards/{"v5" if i in v5 else "v4" if i in v4 else "v3" if i in v3 else "v2" if i in v2 else "item"}/{i}.jpg'
# auto cards (auto_cards.py): new products and products whose photo/title changed; used while they match the live feed
auto = json.load(open('auto_manifest.json')) if os.path.exists('auto_manifest.json') else {}
ok_auto = lambda i: i in auto and i in cur and cur[i] == (auto[i]['image'], auto[i]['title'])
ok_man = lambda i: i in man and i in cur and cur[i] == (man[i]['image'], man[i]['title'])
ids = order[:n] + [i for i in cur if i not in set(order)]
rows = [(i, f"https://ksofronis.github.io/jt-meta-cards/{auto[i]['path']}" if ok_auto(i) and not ok_man(i) else url(i)) for i in ids if ok_man(i) or ok_auto(i)]
with open('feed/supplementary.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['id', 'image_link']); w.writerows(rows)
print('supplementary rows', len(rows), 'of first', n, '| auto', sum(1 for r in rows if '/auto/' in r[1]), '| v2', sum(1 for r in rows if '/v2/' in r[1]), '| v3', sum(1 for r in rows if '/v3/' in r[1]), '| v4', sum(1 for r in rows if '/v4/' in r[1]), '| v5', sum(1 for r in rows if '/v5/' in r[1]))
