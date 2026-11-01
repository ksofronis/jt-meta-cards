"""Black Friday 2026 catalog cards for the separate BF catalog (live catalog and its v10 cards are never touched).
render SHARD NSHARDS: renders P1/P2/P3 in 1:1 and 9:16 for products missing a current asset, uploads to R2, writes bf26/m/<shard>.json.
feed: merges the shard manifests, writes bf26/feed.xml on R2: live feed with image_link = BF card of today's phase (Athens date), 9:16 as additional image.
Only assets passing qc_assets reach the feed; a product without one stays out. From 11/12 both modes do nothing."""
import sys, os, re, io, json, html, hashlib, datetime, tempfile, urllib.request, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.abspath('generator'))
os.environ.setdefault('JT_FEED', '/dev/null')
import bf_cards as b, make_v7 as m, qc_assets as qa
SRC = 'https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml'
ATHENS = datetime.timezone(datetime.timedelta(hours=2))
PUBLIC = open('r2_public.txt').read().strip().rstrip('/') + '/'
def phase(d=None):
    d = d or datetime.datetime.now(ATHENS).date(); Y = 2026
    if d >= datetime.date(Y, 12, 11): return None
    return 'P1' if d < datetime.date(Y, 11, 23) else 'P2' if d < datetime.date(Y, 12, 1) else 'P3'
def fetch(): return urllib.request.urlopen(urllib.request.Request(SRC, headers={'User-Agent': 'Mozilla/5.0'}), timeout=120).read()
def s3():
    import boto3
    return boto3.client('s3', endpoint_url=os.environ['R2_ENDPOINT'], aws_access_key_id=os.environ['R2_ACCESS_KEY_ID'], aws_secret_access_key=os.environ['R2_SECRET_ACCESS_KEY'], region_name='auto')
def get_json(key):
    try: return json.load(urllib.request.urlopen(urllib.request.Request(PUBLIC + key + f'?t={datetime.datetime.now().timestamp()}', headers={'User-Agent': 'Mozilla/5.0'}), timeout=60))
    except Exception: return {}
def render_one(it, g, outdir):
    """{phase: {sq, vt, qc}} for one item; local jpg paths under outdir."""
    spec = b.item_spec(it, g); iid = spec.get('id') or g(it, 'id')
    ready = iid in b.READY or g(it, 'item_group_id') in b.READY
    tmp = os.path.join(outdir, f'{iid}_base.png'); b.card_hooked(spec, tmp); base, L = b._LAST['c'], b._LAST['L']
    src = b.src_photo(spec); box = (L['px'], L['py'], L['px'] + L['tw'], L['py'] + L['th']); res = {}
    for ph in b.PHASES:
        sq, _, _ = b.bf_layer(base, L, ph, ready)
        c, _, _ = b.bf_layer(base, L, ph, ready, with_phase_chip=False); st, _ = b.story(c, ph)
        f1, f2 = os.path.join(outdir, f'{iid}_{ph}_1x1.jpg'), os.path.join(outdir, f'{iid}_{ph}_9x16.jpg')
        sq.convert('RGB').save(f1, quality=90, optimize=True); st.convert('RGB').save(f2, quality=90, optimize=True)
        sbox = (box[0], box[1] + b.CARD_Y, box[2], box[3] + b.CARD_Y)
        res[ph] = {'sq': f1, 'vt': f2, 'qc': bool(qa.check_image(f1, src, box)) and bool(qa.check_image(f2, src, sbox))}
    os.remove(tmp); return res
def items_of(raw):
    root = ET.fromstring(raw); g = lambda it, k: (it.findtext(f'g:{k}', namespaces=m.NS) or '').strip()
    return [it for it in root.findall('./channel/item') if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', g(it, 'id'))], g
def key_of(it, g): return hashlib.sha1('|'.join((g(it, 'image_link'), g(it, 'title'), g(it, 'sale_price') or g(it, 'price'))).encode()).hexdigest()[:8]
def render(shard, n):
    items, g = items_of(fetch()); cl = s3(); bucket = os.environ['R2_BUCKET']
    mkey = f'bf26/m/{shard}.json'; man = get_json(mkey); made = fail = 0
    mine = [it for it in items if int(hashlib.sha1(g(it, 'id').encode()).hexdigest(), 16) % n == shard]
    for it in mine:
        iid, k = g(it, 'id'), key_of(it, g)
        if man.get(iid, {}).get('key') == k: continue
        with tempfile.TemporaryDirectory() as d:
            try: res = render_one(it, g, d)
            except Exception as e: print('failed', iid, str(e)[:120]); man[iid] = {'key': k, 'error': str(e)[:120]}; fail += 1; continue
            rec = {'key': k, 'ph': {}}
            for ph, r in res.items():
                urls = {}
                for fmt in ('sq', 'vt'):
                    key = f'bf26/{iid}-{k}-{ph.lower()}-{fmt}.jpg'
                    cl.upload_file(r[fmt], bucket, key, ExtraArgs={'ContentType': 'image/jpeg', 'CacheControl': 'public, max-age=31536000, immutable'}); urls[fmt] = key
                rec['ph'][ph] = {**urls, 'qc': r['qc']}
        man[iid] = rec; made += 1
        if made % 25 == 0: cl.put_object(Bucket=bucket, Key=mkey, Body=json.dumps(man).encode(), ContentType='application/json', CacheControl='no-store')
    cl.put_object(Bucket=bucket, Key=mkey, Body=json.dumps(man).encode(), ContentType='application/json', CacheControl='no-store')
    print('shard', shard, 'products', len(mine), 'made', made, 'failed', fail)
def feed(n):
    ph = phase()
    if not ph: print('after 10/12: nothing'); return
    man = {}
    for s in range(n): man.update(get_json(f'bf26/m/{s}.json'))
    raw = fetch().decode(); kept = dropped = 0
    def sub(mo):
        nonlocal kept, dropped
        x = mo.group(0); iid = (re.search(r'<g:id>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</g:id>', x, re.S) or [None, ''])[1].strip()
        a = man.get(iid, {}).get('ph', {}).get(ph)
        if not a or not a['qc']: dropped += 1; return ''
        x = re.sub(r'\s*<g:additional_image_link>.*?</g:additional_image_link>', '', x, flags=re.S)
        x = re.sub(r'<g:image_link>.*?</g:image_link>', f"<g:image_link><![CDATA[{PUBLIC + a['sq']}]]></g:image_link>\n<g:additional_image_link><![CDATA[{PUBLIC + a['vt']}]]></g:additional_image_link>", x, count=1, flags=re.S)
        kept += 1; return x
    out = re.sub(r'<item>.*?</item>', sub, raw, flags=re.S)
    ET.fromstring(out.encode())
    if kept < 500: raise SystemExit(f'only {kept} products with a passing BF card: feed not published')
    s3().put_object(Bucket=os.environ['R2_BUCKET'], Key='bf26/feed.xml', Body=out.encode(), ContentType='application/xml', CacheControl='no-store')
    print('phase', ph, 'kept', kept, 'dropped', dropped)
if __name__ == '__main__':
    if not phase(): print('BF over'); sys.exit()
    if sys.argv[1] == 'render': render(int(sys.argv[2]), int(sys.argv[3]))
    elif sys.argv[1] == 'feed': feed(int(sys.argv[2]))
    elif sys.argv[1] == 'test':
        items, g = items_of(fetch()); want = set(sys.argv[3:]); os.makedirs(sys.argv[2], exist_ok=True)
        for it in items:
            if g(it, 'id') in want:
                r = render_one(it, g, sys.argv[2]); print(g(it, 'id'), {p: v['qc'] for p, v in r.items()})
