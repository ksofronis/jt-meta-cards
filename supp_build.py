"""Build feed/supplementary.csv (id,image_link) for Meta.
Includes the first N ids of the rollout order (supp_count.txt) whose manifest photo+title still match the live feed.
Products whose photo or title changed are left out, so Meta keeps their original image."""
import csv, json, re, html, urllib.request
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
raw = urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read().decode()
cur, ptype, extra, price = {}, {}, {}, {}
for b in re.findall(r'<item>.*?</item>', raw, re.S):
    g = lambda t: (re.search(rf'<g:{t}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:{t}>', b, re.S) or [None, ''])[1].strip()
    cur[g('id')] = (html.unescape(g('image_link')), html.unescape(g('title')))  # same text as the XML parser (&quot; etc.)
    ptype[g('id')] = html.unescape(g('product_type'))
    extra[g('id')] = [html.unescape(u.strip()) for u in re.findall(r'<g:additional_image_link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:additional_image_link>', b, re.S)]
    price[g('id')] = g('sale_price') or g('price')
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
v6 = set(open('v6_ids.txt').read().split()) if os.path.exists('v6_ids.txt') else set()  # 11/10: clock, latex, velvet, colour choice, storage, Σε N διαστάσεις/χρώματα (live immediately)
url = lambda i: f'https://ksofronis.github.io/jt-meta-cards/{"v6" if i in v6 else "v5" if i in v5 else "v4" if i in v4 else "v3" if i in v3 else "v2" if i in v2 else "item"}/{i}.jpg'
# auto cards (auto_cards.py): new products and products whose photo/title changed; used while they match the live feed
auto = json.load(open('auto_manifest.json')) if os.path.exists('auto_manifest.json') else {}
ok_auto = lambda i: i in auto and i in cur and cur[i] == (auto[i]['image'], auto[i]['title'])
ok_man = lambda i: i in man and i in cur and cur[i] == (man[i]['image'], man[i]['title'])
# v7 cards (v7_cards.py): highest priority, only for groups enabled in v7_groups.txt and while they match the live feed
import sys; sys.path.insert(0, 'generator'); import v7_groups
v7on = v7_groups.enabled()
v7m = json.load(open('v7_manifest.json')) if os.path.exists('v7_manifest.json') else {}
ok_v7 = lambda i: i in v7m and i in cur and cur[i] == (v7m[i]['image'], v7m[i]['title']) and v7_groups.group_of(ptype.get(i, '')) in v7on
ids = order[:n] + [i for i in cur if i not in set(order)]
pick = lambda i: v7m[i]['path'] if ok_v7(i) else auto[i]['path'] if ok_auto(i) and not ok_man(i) else None
rows = [(i, f"https://ksofronis.github.io/jt-meta-cards/{pick(i)}" if pick(i) else url(i)) for i in ids if ok_v7(i) or ok_man(i) or ok_auto(i)]
# v9 extras (v9_extras.py, top products): cards 2/3 lead the gallery, the site's own gallery photos follow (never dropped);
# videos as video[0] (9:16) and video[1] (1:1). Every row repeats its site gallery so the column never blanks a product's photos.
import make_v7
V9 = os.path.exists('v9.txt') and open('v9.txt').read().strip() == 'on'
v9x = json.load(open('v9x_manifest.json')) if V9 and os.path.exists('v9x_manifest.json') else {}
crops = json.load(open('v8_crops.json')) if os.path.exists('v8_crops.json') else {}
def x_ok(i):
    if i not in v9x or i not in cur: return False
    crop = crops[i]['crop'] if i in crops and crops[i]['image'] == cur[i][0] else None
    fin = '|'.join(make_v7.finance_line(price.get(i, '')) or ('-',))
    return v9x[i]['key'] == [cur[i][0], cur[i][1], crop, fin] and all(os.path.exists(f) for f in v9x[i]['files'].values())
PAGES = 'https://ksofronis.github.io/jt-meta-cards/'
def more(i):
    f = v9x[i]['files'] if x_ok(i) else {}
    imgs = [PAGES + f[k] for k in ('c2', 'c3') if k in f] + extra.get(i, [])
    return [','.join(imgs[:20]), PAGES + f['story'] if 'story' in f else '', PAGES + f['feed'] if 'feed' in f else '']
with open('feed/supplementary.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['id', 'image_link', 'additional_image_link', 'video[0].url', 'video[1].url'])
    w.writerows([r[0], r[1], *more(r[0])] for r in rows)
print('supplementary rows', len(rows), 'of first', n, '| auto', sum(1 for r in rows if '/auto/' in r[1]), '| v2', sum(1 for r in rows if '/v2/' in r[1]), '| v3', sum(1 for r in rows if '/v3/' in r[1]), '| v4', sum(1 for r in rows if '/v4/' in r[1]), '| v5', sum(1 for r in rows if '/v5/' in r[1]), '| v6', sum(1 for r in rows if '/v6/' in r[1]), '| v7', sum(1 for r in rows if '/v7/' in r[1]), '| v9 extras', sum(1 for r in rows if x_ok(r[0])))
