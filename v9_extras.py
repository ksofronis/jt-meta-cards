"""Hourly: v9 extras for the top products listed in v9_top.txt (top 200 by catalog-ad impressions, 2026-10-19):
carousel card 2 (colour range, only with swatches), card 3 (dimensions + showroom/delivery), video 9:16 + 1:1.
Output: v9x/<id>-<hash>-{c2,c3}.jpg + -{story,feed}.mp4, manifest v9x_manifest.json.
supp_build.py adds them (additional_image_link, video[0].url, video[1].url) only while the manifest matches the live feed.
Switch: v9.txt ('on'). Rollback: empty v9.txt -> supp_build stops sending extras (files stay until pruned).
Usage: python3 v9_extras.py            (normal run, max V9X_MAX products per run, default 3: videos are slow on CI)"""
import sys, os, re, json, hashlib, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('generator'))
import make_v7 as m, make_v9x as x, qc_assets
MAX = int(os.environ.get('V9X_MAX', 3))
# R2 (Cloudflare object storage): when the 4 secrets are present, files go to the bucket instead of GitHub Pages (no 1 GB cap)
R2 = all(os.environ.get(k) for k in ('R2_ACCESS_KEY_ID', 'R2_SECRET_ACCESS_KEY', 'R2_ENDPOINT', 'R2_BUCKET'))
ALL = os.path.exists('v9_all.txt') and open('v9_all.txt').read().strip() == 'on'  # all products (needs R2) instead of v9_top.txt
s3 = None
if R2:
    import boto3
    s3 = boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'], aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'],
                      aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'], region_name='auto')
def put(f):
    s3.upload_file(f, os.environ['R2_BUCKET'], f, ExtraArgs={'ContentType': 'video/mp4' if f.endswith('.mp4') else 'image/jpeg', 'CacheControl': 'public, max-age=31536000, immutable'})
def drop(f, on_r2):
    if on_r2 and s3: s3.delete_object(Bucket=os.environ['R2_BUCKET'], Key=f)
    elif os.path.exists(f): os.remove(f)
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
SAFE_ID = re.compile(r'[A-Za-z0-9_-]{1,64}')
if not (os.path.exists('v9.txt') and open('v9.txt').read().strip() == 'on'): print('v9 off: no extras'); sys.exit()
top = [l.strip() for l in open('v9_top.txt') if l.strip()] if os.path.exists('v9_top.txt') else []
if ALL and not R2: print('v9_all.txt is on but R2 secrets are missing: keeping the top list only')
root = ET.fromstring(urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read())
g = lambda it, k: (it.findtext(f'g:{k}', namespaces=m.NS) or '').strip()
items = {g(it, 'id'): it for it in root.findall('./channel/item') if SAFE_ID.fullmatch(g(it, 'id'))}
if ALL and R2: top = list(items)
crops = json.load(open('v8_crops.json')) if os.path.exists('v8_crops.json') else {}
crop_of = lambda it: crops[g(it, 'id')]['crop'] if g(it, 'id') in crops and crops[g(it, 'id')]['image'] == g(it, 'image_link') else None
fin_of = lambda it: '|'.join(m.finance_line(g(it, 'sale_price') or g(it, 'price')) or ('-',)) + m.name_salt(g(it, 'title')) + m.X_SALT
key = lambda it: [g(it, 'image_link'), g(it, 'title'), crop_of(it), fin_of(it)]
man = json.load(open('v9x_manifest.json')) if os.path.exists('v9x_manifest.json') else {}
todo = [items[i] for i in top if i in items and man.get(i, {}).get('key') != key(items[i])]
print('top', len(top), '| in feed', sum(i in items for i in top), '| needing extras', len(todo), '| this run', min(len(todo), MAX))
os.makedirs('v9x', exist_ok=True); made = 0
for iid in [i for i in man if i not in set(top)]:  # dropped from the top list: remove its files (keeps the Pages site under 1 GB)
    for f in man[iid].get('files', {}).values(): drop(f, man[iid].get('r2'))
    del man[iid]
for it in todo[:MAX]:
    iid = g(it, 'id'); k = key(it); h = hashlib.sha1(json.dumps(k).encode()).hexdigest()[:8]; base = f'v9x/{iid}-{h}'
    try:
        spec = dict(m.build(it), crop=crop_of(it))
        files = {}
        x.video(spec, f'{base}-story.mp4', 1080, 1920); files['story'] = f'{base}-story.mp4'
        x.video(spec, f'{base}-feed.mp4', 1080, 1080); files['feed'] = f'{base}-feed.mp4'
    except Exception as e: print('failed', iid, str(e)[:120]); continue
    qc = qc_assets.check_all(x, spec, files)  # guardrail: supp_build publishes only assets that pass
    if not all(qc.values()): print('qc failed', iid, qc)
    if R2:
        try:
            for f in files.values(): put(f)
        except Exception as e: print('upload failed', iid, str(e)[:120]); continue
        for f in files.values(): os.remove(f)  # the bucket holds them; nothing large goes into git
    for old in man.get(iid, {}).get('files', {}).values():
        if old not in files.values(): drop(old, man[iid].get('r2'))
    man[iid] = {'key': k, 'files': files, 'qc': qc, **({'r2': True} if R2 else {})}; made += 1
    json.dump(man, open('v9x_manifest.json', 'w'), ensure_ascii=False, indent=0)  # saved per product: a timeout keeps finished work
print('v9 extras made', made)
json.dump(man, open('v9x_manifest.json', 'w'), ensure_ascii=False, indent=0)
