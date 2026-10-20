"""Hourly: review sheet of new and changed product cards, so a person can check them at a glance.
Compares v7_manifest.json with review/state.json (card paths already seen). New paths are added to review/log.json
(newest first, last 200 kept). Writes:
  review/latest.jpg   contact sheet of the 40 most recent new/changed cards (open on a phone or laptop)
  review/index.html   same cards with name, id, time, extras links, flags; counts for the last 24 h and 7 days
Flags are hints for the reviewer, not errors: very small file, no colour/size row expected, no extras yet."""
import os, re, json, html, datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
os.makedirs('review', exist_ok=True)
now = datetime.datetime.now(ZoneInfo('Europe/Athens'))
man = json.load(open('v7_manifest.json'))
x = json.load(open('v9x_manifest.json')) if os.path.exists('v9x_manifest.json') else {}
state = json.load(open('review/state.json')) if os.path.exists('review/state.json') else None
log = json.load(open('review/log.json')) if os.path.exists('review/log.json') else []
seen = set(state) if state is not None else {e['path'] for e in man.values()}  # first run: no backlog
new = [(i, e) for i, e in man.items() if e['path'] not in seen and os.path.exists(e['path'])]
for i, e in new:
    flags = []
    if os.path.getsize(e['path']) < 40_000: flags.append('very small file')
    if re.match(r'^[\dA-Z]{1,6}[-\d]*\s', e['title']): flags.append('code in name')
    log.insert(0, {'id': i, 'title': e['title'], 'path': e['path'], 'at': now.isoformat(timespec='minutes'), 'flags': flags})
log = log[:200]
json.dump(sorted({e['path'] for e in man.values()}), open('review/state.json', 'w'))
json.dump(log, open('review/log.json', 'w'), ensure_ascii=False, indent=0)

recent = [r for r in log if os.path.exists(r['path'])][:40]
F = lambda s: ImageFont.truetype(os.path.join('generator', 'v7', 'fonts', 'Inter-600.ttf'), s)
T, C = 300, 5
rows = max(1, -(-len(recent) // C))
sh = Image.new('RGB', (C * (T + 16) + 16, 90 + rows * (T + 52)), '#eef0f3'); d = ImageDraw.Draw(sh)
d.text((16, 22), f"New / changed cards · updated {now:%d/%m %H:%M} Athens · {len(recent)} shown", font=F(26), fill='#15181d')
if not recent: d.text((16, 60), 'No new or changed cards yet.', font=F(20), fill='#555c66')
for k, r in enumerate(recent):
    px, py = 16 + (k % C) * (T + 16), 70 + (k // C) * (T + 52)
    sh.paste(Image.open(r['path']).convert('RGB').resize((T, T), Image.LANCZOS), (px, py))
    d.text((px, py + T + 6), f"{r['id']} · {r['at'][5:16].replace('T', ' ')}", font=F(15), fill='#555c66')
    if r['flags']: d.text((px, py + T + 26), ', '.join(r['flags']), font=F(15), fill='#b4232c')
sh.save('review/latest.jpg', quality=82)

since = lambda h: sum(1 for r in log if datetime.datetime.fromisoformat(r['at']) > now - datetime.timedelta(hours=h))
R2 = open('r2_public.txt').read().strip().rstrip('/') + '/' if os.path.exists('r2_public.txt') else 'https://ksofronis.github.io/jt-meta-cards/'
def extras(i):
    f = x.get(i, {}).get('files', {}); base = R2 if x.get(i, {}).get('r2') else 'https://ksofronis.github.io/jt-meta-cards/'
    return ' '.join(f'<a href="{base}{v}">{k}</a>' for k, v in f.items()) or '<span class="flag">no extras yet</span>'
cards = '\n'.join(f'<figure><img loading="lazy" src="../{html.escape(r["path"])}" alt=""><figcaption><b>{html.escape(r["title"])}</b>'
                  f'<span>{r["id"]} · {r["at"][:16].replace("T", " ")} </span><span>{extras(r["id"])}</span>'
                  + ''.join(f'<span class="flag">{html.escape(f)}</span>' for f in r['flags']) + '</figcaption></figure>' for r in log[:80])
open('review/index.html', 'w').write(f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Card review</title><style>body{{font:15px/1.4 system-ui,sans-serif;margin:0;padding:16px;background:#eef0f3;color:#15181d}}
h1{{font-size:20px;margin:0 0 4px}}p{{margin:0 0 16px;color:#555c66}}main{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}
figure{{margin:0;background:#fff;border-radius:8px;overflow:hidden}}img{{width:100%;display:block}}figcaption{{padding:8px 10px;display:grid;gap:3px;font-size:13px}}
figcaption span{{color:#555c66}}.flag{{color:#b4232c!important}}a{{color:#1f5eff}}</style>
<h1>New and changed product cards</h1><p>Updated {now:%d/%m/%Y %H:%M} Athens · last 24 h: {since(24)} · last 7 days: {since(168)} · newest first</p>
<main>{cards or "<p>No new or changed cards yet.</p>"}</main>''')
print('review: new', len(new), '| log', len(log), '| 24h', since(24), '| 7d', since(168))
