#!/usr/bin/env python3
"""매일 실행: icnkr 앱 招聘 목록에서 '어제' 공고만 수집 -> data.json 병합 -> index.html 재생성 -> git push."""
import json,subprocess,time,re,sys,os,datetime
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import build
os.chdir(os.path.dirname(os.path.abspath(__file__)))
CUA='/Users/xujun/.local/bin/cua-driver'
BID='com.icnkr.xinhua'; S='icnkr-'+str(int(time.time()))
DRY='--dry' in sys.argv
def sh(*a,**k): return subprocess.run(a,capture_output=True,text=True,**k)
def call(t,a,sess=True):
    a=dict(a)
    if sess: a['session']=S
    return sh(CUA,'call',t,json.dumps(a)).stdout
def jcall(t,a):
    o=call(t,a)
    try: return json.loads(o)
    except Exception: return {}
def ensure_daemon():
    if 'is running' in sh(CUA,'status').stdout: return
    subprocess.Popen([CUA,'serve'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True); time.sleep(4)
_d=json.load(open('data.json'))
if max(datetime.date.fromisoformat(r['date']) for r in _d)>=datetime.date.today():
    print('up to date'); sys.exit()
ensure_daemon()
call('start_session',{})
sh('pkill','-f','Wrapper/icnkr.app/icnkr'); time.sleep(2)
pid=jcall('launch_app',{'bundle_id':BID}).get('pid'); 
if not pid: sys.exit('launch failed')
win=None
for _ in range(20):
    time.sleep(2)
    for w in jcall('list_windows',{}).get('windows',[]):
        if w['pid']==pid and w.get('title'): win=w['window_id']
    if win: break
if not win: sys.exit('no window')
def state():
    return jcall('get_window_state',{'pid':pid,'window_id':win,'include_screenshot':False})
def txt(e): return e.get('label') or e.get('value') or ''
def click_idx(idx,s=None):
    s=s or state(); t=[e['element_token'] for e in s.get('elements',[]) if e['element_index']==idx]
    if t: call('click',{'pid':pid,'window_id':win,'element_token':t[0]})
def goto_tab():
    for _ in range(10):
        s=state(); r=[e['element_index'] for e in s.get('elements',[]) if e['role']=='AXRadioButton' and e.get('label')=='招聘']
        if r: click_idx(r[0],s); time.sleep(4); 
        s=state()
        if listitems(s): return
        time.sleep(3)
def listitems(s):
    r=[];meta=None
    for e in s.get('elements',[]):
        if e['role'].startswith('AXMenu'): continue
        l=txt(e)
        if e['role']=='AXStaticText' and '阅读' in l: meta=l
        elif e['role']=='AXGenericElement' and meta: r.append((meta,l,e['element_token'])); meta=None
    return r
def is_detail(s): return any(e['role']=='AXHeading' for e in s.get('elements',[]))
today=datetime.date.today(); yday=today-datetime.timedelta(days=1)
data=json.load(open('data.json')); known={(r['a'],r['t']) for r in data}
last=max(datetime.date.fromisoformat(r['date']) for r in data)
start=last  # 마지막 수집일부터 다시 훑어 누락분 보충(중복은 known으로 제외)
def to_date(dt):
    if dt.startswith('昨天'): return yday
    if re.search(r'分钟前|小时前|刚刚',dt): return today
    m=re.match(r'(\d\d)-(\d\d)',dt)
    if m:
        d=datetime.date(today.year,int(m.group(1)),int(m.group(2)))
        return d if d<=today else d.replace(year=today.year-1)
    return today
def day_of(dt):
    d=to_date(dt)
    if d>=today: return 'T'
    return 'Y' if d>=start else 'O'
new=[];done=set();older=0
goto_tab()
for it in range(300):
    s=state()
    if not s.get('elements'): time.sleep(3); goto_tab(); continue
    if is_detail(s): click_idx(1,s); time.sleep(2); continue
    items=listitems(s)
    if not items: goto_tab(); continue
    todo=[]
    for meta,title,tok in items:
        a,vw,dt=meta.split('\u3000'); k=(a,title.replace('\ufffc','').strip())
        d=day_of(dt)
        if d=='O': older+=1
        if d=='Y' and k not in done and k not in known: todo.append((meta,title,tok,k,a,vw,dt))
    if todo:
        meta,title,tok,k,a,vw,dt=todo[0]; done.add(k)
        call('click',{'pid':pid,'window_id':win,'element_token':tok}); time.sleep(3)
        d=state()
        if not is_detail(d): time.sleep(3); d=state()
        f={};body=[]
        if is_detail(d):
            rows=[(e['role'],txt(e)) for e in d['elements'] if not e['role'].startswith('AXMenu')]
            f,body=build.parse(rows); body=[b for b in body if b not in (a,dt)]
            click_idx(1,d); time.sleep(2)
        pd=to_date(dt); new.append(dict(dt=pd.strftime('%m-%d'),date=pd.isoformat(),a=a,v=vw.replace('阅读',''),t=k[1],f=f,b=body))
        print('+',k[1][:30],flush=True); continue
    if older>=3: break  # 보충 범위보다 오래된 공고에 도달
    toks=[e['element_token'] for e in s['elements'] if e['role']=='AXGenericElement']
    if toks: call('scroll',{'pid':pid,'window_id':win,'element_token':toks[0],'direction':'down','by':'page','amount':3}); time.sleep(1.2)
call('end_session',{})
sh('pkill','-f','Wrapper/icnkr.app/icnkr')
print('collected',len(new))
if DRY: sys.exit()
if new:
    data+=new; json.dump(data,open('data.json','w'),ensure_ascii=False,indent=0)
open('index.html','w').write(build.render(data))
sh('git','add','data.json','index.html')
if sh('git','diff','--cached','--quiet').returncode:
    sh('git','commit','-qm',f'Update {today.isoformat()}: +{len(new)}')
    print(sh('git','push','-q').stderr)
