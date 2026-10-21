"""Classify every site gallery photo in the JT feed: product photo (keep) vs swatch/sample chart, drawing, diagram (drop).
Owner rule 21/10: only images that show the product reach Meta. Fail-closed: unclear = drop.
Writes <repo>/site_photos_qc.json {url: {"p": product probability, "ok": bool}}; supp_build and make_v9x read it.
Run: python3 generator/site_photo_qc.py .   (hourly workflow; local: meta-cards/.venv-clip/bin/python). Loads the model only when new photos exist."""
import io, json, os, sys, hashlib, urllib.request, xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else '.'); CACHE = os.environ.get('SITE_PHOTO_CACHE', os.path.join(REPO, '..', '..', 'site_photo_cache')); os.makedirs(CACHE, exist_ok=True)
OUT = os.path.join(REPO, 'site_photos_qc.json'); KEEP = 0.85
NS = {'g': 'http://base.google.com/ns/1.0'}
PRODUCT = ['a photo of a sofa', 'a photo of a corner sofa in a living room', 'a photo of an armchair', 'a photo of a bed in a bedroom',
           'a photo of a mattress', 'a photo of a chair', 'a photo of a dining table with chairs', 'a photo of a coffee table',
           'a photo of a wardrobe', 'a photo of a nightstand', 'a photo of a console table', 'a photo of a tv unit',
           'a photo of furniture in a room', 'a photo of a stool', 'a photo of a desk', 'a photo of a mirror', 'a photo of a lamp', 'a photo of a wall clock']
OTHER = ['fabric swatches', 'a color palette chart', 'a chart of wood samples', 'a grid of color samples', 'fabric samples hanging in a row',
         'a fabric sample book', 'a texture of fabric', 'a wood texture', 'a technical drawing with dimensions', 'a diagram of mattress layers',
         'a cross section of a mattress', 'a sheet of text', 'a logo', 'a color chart with labels', 'a leather texture', 'a marble texture',
         'a close-up of fabric', 'a close-up of a mattress surface', 'a close-up of wood grain', 'a close-up of stitching', 'a storefront', 'an office interior', 'a stone texture', 'wallpaper pattern']

def urls():
    its = ET.parse(os.path.join(REPO, 'feed/facebook.xml')).getroot().findall('./channel/item')
    return sorted({e.text.strip() for it in its for e in it.findall('g:additional_image_link', namespaces=NS) if e.text and e.text.strip()})

def thumb(u):
    p = os.path.join(CACHE, hashlib.sha1(u.encode()).hexdigest()[:16] + '.jpg')
    if not os.path.exists(p):
        try:
            im = Image.open(io.BytesIO(urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read())).convert('RGB')
            im.thumbnail((384, 384)); im.save(p, quality=90)
        except Exception: return u, None
    return u, p

if __name__ == '__main__':
    old = json.load(open(OUT)) if os.path.exists(OUT) else {}
    todo = [u for u in urls() if u not in old]
    print('site photos new', len(todo))
    if '--count' in sys.argv: sys.exit(0 if todo else 3)  # workflow: 0 = new photos, install the model
    if not todo: sys.exit()
    import torch, open_clip
    with ThreadPoolExecutor(16) as ex: paths = dict(ex.map(thumb, todo))
    dev = 'mps' if torch.backends.mps.is_available() else 'cpu'
    model, _, pre = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k', device=dev); model.eval()
    tok = open_clip.get_tokenizer('ViT-B-32')
    with torch.no_grad():
        tf = model.encode_text(tok(PRODUCT + OTHER).to(dev)); tf /= tf.norm(dim=-1, keepdim=True)
        items = [(u, p) for u, p in paths.items() if p]
        for k in range(0, len(items), 64):
            b = items[k:k + 64]; x = torch.stack([pre(Image.open(p)) for _, p in b]).to(dev)
            f = model.encode_image(x); f /= f.norm(dim=-1, keepdim=True)
            pr = (100 * f @ tf.T).softmax(dim=-1)[:, :len(PRODUCT)].sum(dim=-1).tolist()
            for (u, _), s in zip(b, pr): old[u] = {'p': round(s, 3), 'ok': s >= KEEP}
    for u, p in paths.items():
        if not p: old[u] = {'p': None, 'ok': False}  # unreadable = drop
    json.dump(old, open(OUT, 'w'), indent=0, sort_keys=True)
    ok = sum(v['ok'] for v in old.values()); print('photos', len(old), 'keep', ok, 'drop', len(old) - ok)
