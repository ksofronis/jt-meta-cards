# Advance supp_count. While PAUSE exists nothing moves, until RELEASE_AT passes:
# then PAUSE is removed and every product is included in one step.
import datetime, os
RELEASE_AT = datetime.datetime(2026, 10, 9, 21, 0, tzinfo=datetime.timezone.utc)  # 00:00 Athens, Sat 10/10
t = sum(1 for l in open('supp_order.txt') if l.strip())
n = int(open('supp_count.txt').read())
if os.path.exists('PAUSE'):
    if datetime.datetime.now(datetime.timezone.utc) >= RELEASE_AT:
        os.remove('PAUSE')
        n = t
else:
    n = min(t, n + 300)
open('supp_count.txt', 'w').write(str(n))
print('supp_count', n, 'of', t)
