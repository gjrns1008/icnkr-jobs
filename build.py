import json,re,html,collections,datetime,sys
e=html.escape
CATS=[('식당·요식',r'火锅|串|麻辣烫|餐|厨|前厅|前台|服务员|包子|烤肉|炒菜|饭店|汤|粉|足道|烤鸭|煎包|早餐'),
('건설·기술',r'技工|工地|电焊|焊|水电|石膏|木工|装修|信号|泥|消防|地铁|工程|油漆|钢|现场|拆|瓷砖|防水|방수|大工|小工|保温|隔断|煤气|门施工|老炮|뿜칠'),
('공장·제조·물류',r'工厂|汽车|零部件|仓|物流|LCD|CNC|cnc|制造|流水线|库|打包|装卸|电子厂|会社|大棚|摘苹果|种洋葱|牛肉厂|海蛎|葡萄'),
('운전·배달',r'司机|外卖|骑手|택시|接送|配送|快递|운전'),
('사무·직장',r'文职|办公|翻译|互译|客服|会计|财务|出纳|销售|运营|主播|助播|经理|助理|秘书|文员|职员|사무|采购|贸易|教师|老师|直播|KOC|SNS|剪辑|求职'),
('기타','.')]
def cat(t):
    for n,p in CATS:
        if re.search(p,t): return n
def parse(rows):
    t=[x for x in rows if not x[0].startswith('AXMenu')]
    i=next(i for i,x in enumerate(t) if x[0]=='AXHeading')
    f={};body=[];j=i+1
    while j<len(t):
        r,s=t[j]
        if s in('有效期至','所在地区','雇佣形式','薪资待遇','韩语水平') and j+1<len(t): f[s]=t[j+1][1]; j+=2; continue
        if s.startswith('-- 提高警惕'): break
        if r in('AXStaticText','AXLink') and s and not s.startswith(('急招-','开启')) and not re.fullmatch(r'[\d.万]+ 阅读|.*分钟前|.*小时前|昨天.*|\d\d-\d\d.*',s) and s not in('联系手机','隐藏内容','版规说明','合规声明','APP私聊','点此私聊','+关注') and not s.startswith(('联系我时请说','本人发布内容不含')):
            body.append(s)
        j+=1
    return f,body
def render(rows):
    rows=sorted(rows,key=lambda r:(r['dt'][:2] in('10','11','12') and (r['dt'][:2]=='12' and 2 or 1) or 3,r['dt']),reverse=True) if False else sorted(rows,key=lambda r:r.get('date',r['dt']),reverse=True)
    for r in rows: r['c']=cat(r['t'])
    cc=collections.Counter(r['c'] for r in rows); dts=sorted({r.get('date',r['dt']) for r in rows}); nd=sum(1 for r in rows if r['b'])
    def row(r):
        meta=''.join(f'<span><b>{e(k)}</b> {e(v)}</span>' for k,v in r['f'].items())
        body='<br>'.join(e(x) for x in r['b']) or '<i>상세 내용을 수집하지 못했습니다(목록 제목만 있음).</i>'
        return f'<tr class="r" data-c="{e(r["c"])}"><td>{e(r["dt"])}</td><td><span class="tag">{e(r["c"])}</span></td><td class="t">{e(r["t"]).replace(chr(10)," ")}</td><td>{e(r["a"])}</td><td class="n">{e(r["v"])}</td></tr><tr class="d" hidden><td colspan="5"><div class="meta">{meta}</div><div class="body">{body}</div></td></tr>'
    trs=''.join(row(r) for r in rows)
    btns=''.join(f'<button data-f="{e(n)}">{e(n)} <b>{k}</b></button>' for n,k in cc.most_common())
    now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%Y-%m-%d %H:%M')+' KST'
    return f'''<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>奋斗在韩国 구인 공고</title><style>
body{{font:14px/1.5 -apple-system,"Apple SD Gothic Neo",sans-serif;margin:24px auto;max-width:1000px;padding:0 16px;color:#222}}
h1{{font-size:20px}} .sum{{color:#666}} button{{margin:2px;padding:4px 10px;border:1px solid #ccc;background:#fff;border-radius:14px;cursor:pointer}}
button.on{{background:#222;color:#fff}} input{{padding:6px 10px;width:240px;margin:8px 0;border:1px solid #ccc;border-radius:6px}}
table{{border-collapse:collapse;width:100%}} td,th{{border-bottom:1px solid #eee;padding:6px 8px;text-align:left;vertical-align:top}}
th{{background:#fafafa;position:sticky;top:0}} .tag{{background:#eef;border-radius:4px;padding:1px 6px;font-size:12px;white-space:nowrap}}
.t{{max-width:460px}} .n{{text-align:right;white-space:nowrap}} tr.r{{cursor:pointer}} tr.r:hover{{background:#f6f8ff}} tr.r.open{{background:#eef2ff}}
tr.d td{{background:#fafbff;padding:12px 16px}} .meta span{{display:inline-block;margin:0 14px 6px 0;color:#345}} .body{{white-space:normal;line-height:1.7}}</style>
<h1>奋斗在韩国(icnkr) 招聘 공고</h1>
<p class="sum">갱신 {now} · {len(rows)}건(상세 {nd}건) · 게시일 {dts[0]} ~ {dts[-1]} · 매일 저녁 8시(KST) 자동 수집 · 행을 클릭하면 공고 내용이 펼쳐집니다 · 중국어 원문, 자동 분류라 오분류 가능</p>
<button class="on" data-f="">전체 <b>{len(rows)}</b></button>{btns}<br><input id="q" placeholder="검색 (예: 司机, 火锅, 400万)">
<table><thead><tr><th>날짜</th><th>분류</th><th>제목</th><th>작성자</th><th>조회</th></tr></thead><tbody>{trs}</tbody></table>
<script>let f='',q='';const rs=[...document.querySelectorAll('tr.r')];
function ap(){{rs.forEach(r=>{{const d=r.nextElementSibling,ok=(!f||r.dataset.c==f)&&(!q||(r.textContent+d.textContent).includes(q));r.hidden=!ok;if(!ok)d.hidden=true}})}}
rs.forEach(r=>r.onclick=()=>{{const d=r.nextElementSibling;d.hidden=!d.hidden;r.classList.toggle('open',!d.hidden)}});
document.querySelectorAll('button').forEach(b=>b.onclick=()=>{{document.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');f=b.dataset.f;ap()}});
document.getElementById('q').oninput=e=>{{q=e.target.value;ap()}}</script></html>'''
if __name__=='__main__':
    rows=json.load(open('data.json'))
    for r in rows:
        if 'date' not in r: r['date']='2026-'+r['dt']
    json.dump(rows,open('data.json','w'),ensure_ascii=False,indent=0)
    open('index.html','w').write(render(rows)); print(len(rows))
