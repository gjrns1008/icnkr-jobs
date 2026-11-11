# -*- coding: utf-8 -*-
"""奋斗在韩国(icnkr) 招工信息 게시판(fid=137, sortid=148)을 앱 공개 API로 수집한다.
 - 로그인·기기 불필요 (GitHub Actions 에서 실행 가능)
 - data.json 에 누적 병합 -> index.html 재생성
사용: python collect.py [--dry] [--days N]
기존 앱 화면 자동화 방식(cua-driver, macOS 전용)을 대체한다."""
import json, re, sys, os, time, html, datetime, argparse
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
sys.path.insert(0, HERE)
import build

B = 'https://app.icnkr.com'
H = {'User-Agent': 'okhttp/4.9.3', 'Accept': 'application/json'}
FID, SORTID = 1618, '393'
KST = datetime.timezone(datetime.timedelta(hours=9))
MAX_PAGES = 60

ap = argparse.ArgumentParser()
ap.add_argument('--dry', action='store_true')
ap.add_argument('--days', type=int, default=3, help='마지막 수집일로부터 되짚어 볼 최소 일수(누락 보충)')
args = ap.parse_args()


def get(path, **params):
    err = None
    for i in range(4):
        try:
            r = requests.get(B + path, headers=H, params=params, timeout=40)
            if r.status_code == 200: return r
            err = r.status_code
        except Exception as e:
            err = e
        time.sleep(2 * (i + 1))
    raise RuntimeError(f'요청 실패 {path} {params} {err}')


def kst(ts): return datetime.datetime.fromtimestamp(int(ts), KST)


def balanced(s, start):
    d = 0; ins = False; esc = False
    for k in range(start, len(s)):
        c = s[k]
        if ins:
            if esc: esc = False
            elif c == chr(92): esc = True
            elif c == '"': ins = False
        else:
            if c == '"': ins = True
            elif c == '{': d += 1
            elif c == '}':
                d -= 1
                if d == 0: return s[start:k + 1]


def detail(tid):
    """상세 페이지에서 (조건표 dict, 본문 줄 리스트) 반환."""
    h = get('/mag/circle/v1/forum/threadViewPage', tid=tid, circle_id=0, mag_hide_progress=1).text
    f = {}
    for k, v in re.findall(r'<td width="30%">(.*?)</td>\s*<td\s*>(.*?)</td>', h, re.S):
        k = html.unescape(re.sub(r'<[^>]+>', '', k)).strip(); v = html.unescape(re.sub(r'<[^>]+>', '', v)).replace('\xa0', ' ').strip()
        if k in ('有效期至', '所在地区', '雇佣形式', '薪资待遇', '韩语水平', '招工类型', '行业分类', '工作内容') and v:
            f[k] = v
    body = []
    i = h.find('"content":"')
    if i < 0: return f, body
    st = h.rfind('{', 0, h.rfind('"tid"', 0, i) + 1)
    blob = balanced(h, st)
    try:
        row = json.loads(blob)
    except Exception:
        return f, body
    c = row.get('content') or ''
    c = c.split('<link rel="stylesheet"')[0]                 # 광고·경고 블록 이전까지가 본문
    c = re.sub(r'<br\s*/?>', '\n', c, flags=re.I)
    c = re.sub(r'</(p|div|li|tr)>', '\n', c, flags=re.I)
    c = html.unescape(re.sub(r'<[^>]+>', '', c)).replace('\xa0', ' ')
    for ln in c.split('\n'):
        ln = ln.strip()
        if ln and not ln.startswith('-- 提高警惕'): body.append(ln)
    return f, body


data = json.load(open('data.json', encoding='utf8'))
for r in data:
    r.setdefault('date', '2026-' + r['dt'])
norm = lambda s: re.sub(r'[^\u4e00-\u9fffA-Za-z0-9가-힣]', '', s or '')
known_tid = {r['tid'] for r in data if r.get('tid')}
known_key = {(r['a'], norm(r['t'])) for r in data}
last = max(datetime.date.fromisoformat(r['date']) for r in data)
cutoff = datetime.datetime.combine(last - datetime.timedelta(days=args.days), datetime.time(0, 0), KST)
print('last collected', last, '| scan back to', cutoff.date())

# ---- 목록(작성 최신순) ----
cands = {}
for pg in range(1, MAX_PAGES + 1):
    j = get('/mag/circle/v2/forum/forumViewV2', fid=FID, p=pg, order='dateline').json()
    items = [x for x in j.get('list', []) if 'tid' in x and str(x.get('sortid')) == SORTID]
    if not items: break
    for x in items: cands[x['tid']] = x
    if min(kst(x['create_time']) for x in items) < cutoff: break
print('listed', len(cands), 'pages', pg)
if len(cands) < 20:
    sys.exit(f'목록 {len(cands)}건: 이상 응답으로 보고 중단합니다')

from concurrent.futures import ThreadPoolExecutor
todo = []
for tid, x in sorted(cands.items(), key=lambda kv: -int(kv[1]['create_time'])):
    ct = kst(x['create_time'])
    if ct < cutoff: continue
    title = re.sub(r'\s+', ' ', x.get('subject') or x.get('title') or '').strip()
    if tid in known_tid or (x['user_name'], norm(title)) in known_key: continue
    todo.append((tid, x, ct, title))

def work(t):
    tid, x, ct, title = t
    try:
        f, body = detail(tid)
    except Exception as e:
        print('detail fail', tid, e); f, body = {}, []
    click = str(x.get('click', '')).replace('阅读', '').strip()
    return dict(tid=tid, dt=ct.strftime('%m-%d'), date=ct.date().isoformat(), a=x['user_name'], v=click, t=title, f=f, b=body)

with ThreadPoolExecutor(max_workers=8) as ex:
    new = list(ex.map(work, todo))
print('new', len(new))
for n in new[:8]: print('  +', n['date'], n['a'], n['t'][:36], '|', len(n['b']), 'lines', n['f'].get('所在地区'))

if args.dry: sys.exit()
if new:
    data += new
    data.sort(key=lambda r: r['date'])
    json.dump(data, open('data.json', 'w', encoding='utf8'), ensure_ascii=False, indent=0)
open('index.html', 'w', encoding='utf8').write(build.render(data))
print('wrote index.html', len(data), 'rows')
