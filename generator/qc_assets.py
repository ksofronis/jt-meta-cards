"""Guardrail for every extra that reaches Meta (owner report 21/10: swatch-only colour cards and videos whose first frame
was an empty card ran as product images). supp_build only publishes an asset whose manifest 'qc' flag is True.
- image cards: the product photo must be in the recorded box (low-res correlation with the source photo)
- videos: same photo check on frame 0, and frame 0 must already carry the full info block (frame 0 = Meta's thumbnail)."""
import subprocess
import numpy as np
from PIL import Image

PHOTO_MIN, INFO_MAX = 0.55, 6.0

def _g(im, box=None, n=32):
    im = im.convert('L')
    if box: im = im.crop(box)
    a = np.asarray(im.resize((n, n), Image.BILINEAR), dtype=float); return a - a.mean()

def _corr(a, b):
    d = np.sqrt((a * a).sum() * (b * b).sum()); return float((a * b).sum() / d) if d else 0.0

def _frame(path, t, W, H):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(t), '-i', path, '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    return Image.frombytes('RGB', (W, H), raw[:W * H * 3])

def photo_score(asset, src, box):
    bw, bh = box[2] - box[0], box[3] - box[1]; r = min(bw / src.width, bh / src.height)
    s = Image.new('RGB', (bw, bh), 'white'); t = src.convert('RGB').resize((max(1, round(src.width * r)), max(1, round(src.height * r))))
    s.paste(t, ((bw - t.width) // 2, (bh - t.height) // 2)); return _corr(_g(asset, box), _g(s))

def check_image(path, src, box):
    return photo_score(Image.open(path), src, box) >= PHOTO_MIN

def check_video(path, src, boxes, W, H):
    f0, f1 = _frame(path, 0, W, H), _frame(path, 1.9, W, H)
    info = float(np.abs(np.asarray(f0.crop(boxes['info']), dtype=float) - np.asarray(f1.crop(boxes['info']), dtype=float)).mean())
    return photo_score(f0, src, boxes['photo']) >= PHOTO_MIN and info <= INFO_MAX

def check_all(x, spec, files):
    """files: {'c2':..., 'c3':..., 'story':..., 'feed':...} just rendered by make_v9x (x). Returns {kind: bool}."""
    src, _ = x.photo(spec); out = {}
    for k, f in files.items():
        b = x.BOXES.get(f)
        try:
            out[k] = bool(b) and (check_video(f, src, b, 1080, 1920 if k == 'story' else 1080) if f.endswith('.mp4') else check_image(f, src, b['photo']))
        except Exception:
            out[k] = False
    return out
