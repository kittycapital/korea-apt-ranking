"""
전국 아파트 평당가 TOP 20 대시보드
- 데이터: 국토교통부 아파트 매매 실거래가 API
- TOP 20 산정: 최근 6개월 / 추이 차트: 최근 3년
- 필터: 전용면적 59㎡ 이상, 단지별 최고가
- 기능: 추이 차트(1/2/3년), 지역 분포 도넛, 순위 변동, 인사이트 카드
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict
import os, json, time

API_KEY = os.environ.get('MOLIT_API_KEY', 'YOUR_API_KEY_HERE')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'YOUR_GOOGLE_MAPS_API_KEY_HERE')
BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"
DATA_DIR = 'data'
MIN_AREA = 59

REGIONS = {
    '11110':('서울시','종로구'),'11140':('서울시','중구'),'11170':('서울시','용산구'),
    '11200':('서울시','성동구'),'11215':('서울시','광진구'),'11230':('서울시','동대문구'),
    '11260':('서울시','중랑구'),'11290':('서울시','성북구'),'11305':('서울시','강북구'),
    '11320':('서울시','도봉구'),'11350':('서울시','노원구'),'11380':('서울시','은평구'),
    '11410':('서울시','서대문구'),'11440':('서울시','마포구'),'11470':('서울시','양천구'),
    '11500':('서울시','강서구'),'11530':('서울시','구로구'),'11545':('서울시','금천구'),
    '11560':('서울시','영등포구'),'11590':('서울시','동작구'),'11620':('서울시','관악구'),
    '11650':('서울시','서초구'),'11680':('서울시','강남구'),'11710':('서울시','송파구'),
    '11740':('서울시','강동구'),
}

def get_months(n):
    months = set()
    today = datetime.today()
    for i in range(n):
        d = today.replace(day=1) - timedelta(days=30*i)
        months.add(d.strftime('%Y%m'))
    return sorted(months)

def fetch(code, ym):
    url = f"{BASE_URL}?serviceKey={API_KEY}&LAWD_CD={code}&DEAL_YMD={ym}&pageNo=1&numOfRows=1000"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        if '<resultCode>' in r.text:
            import re
            rc = re.search(r'<resultCode>(\d+)</resultCode>', r.text)
            rm = re.search(r'<resultMsg>([^<]+)</resultMsg>', r.text)
            if rc and rc.group(1) != '00':
                print(f"  ⚠️ API Error [{code}/{ym}]: {rc.group(1)} - {rm.group(1) if rm else 'unknown'}")
                return []
        return parse(r.text, code)
    except Exception as e:
        print(f"  ❌ Request failed [{code}/{ym}]: {e}")
        return []

def parse(xml, code):
    items = []
    try:
        root = ET.fromstring(xml)
        for it in root.findall('.//item'):
            area = float(gt(it,'excluUseAr','0'))
            if area < MIN_AREA: continue
            ps = gt(it,'dealAmount','0').replace(',','').strip()
            try: price = int(ps)
            except: continue
            sido,sigungu = REGIONS.get(code,('',''))
            items.append({
                'apt_name':gt(it,'aptNm',''),'sido':sido,'sigungu':sigungu,
                'dong':gt(it,'umdNm',''),'area_m2':area,'area_pyeong':round(area/3.3,1),
                'price':price,'price_per_pyeong':round((price/area)*3.3),
                'deal_year':gt(it,'dealYear',''),'deal_month':gt(it,'dealMonth',''),
                'deal_day':gt(it,'dealDay',''),'floor':gt(it,'floor',''),
                'build_year':gt(it,'buildYear',''),'region_code':code
            })
    except: pass
    return items

def gt(el,tag,d=''):
    c=el.find(tag)
    return c.text.strip() if c is not None and c.text else d

def fb(p):
    b=p/10000
    if b>=1: return f"{int(b)}억" if b==int(b) else f"{b:.1f}억"
    return f"{p:,}만"

def fp(p):
    b=p//10000;r=p%10000
    return f"{b}억 {r:,}만" if b>0 else f"{p:,}만"

def top20(data):
    best=defaultdict(lambda:None)
    for it in data:
        k=(it['apt_name'],it['sido'],it['sigungu'])
        if best[k] is None or it['price_per_pyeong']>best[k]['price_per_pyeong']:
            best[k]=it
    return sorted(best.values(),key=lambda x:x['price_per_pyeong'],reverse=True)[:20]

def monthly_avg(data, keys):
    m=defaultdict(list)
    for it in data:
        k=(it['apt_name'],it['sido'],it['sigungu'])
        if k in keys:
            ym=f"{it['deal_year']}.{it['deal_month'].zfill(2)}"
            m[ym].append(it['price_per_pyeong'])
    return {ym:round(sum(v)/len(v)) for ym,v in sorted(m.items())}

def per_apt_monthly(data, t20):
    """각 아파트별 월별 평당가 계산"""
    all_months = set()
    apt_data = defaultdict(lambda: defaultdict(list))
    keys = set((it['apt_name'],it['sido'],it['sigungu']) for it in t20)
    for it in data:
        k = (it['apt_name'],it['sido'],it['sigungu'])
        if k in keys:
            ym = f"{it['deal_year']}.{it['deal_month'].zfill(2)}"
            all_months.add(ym)
            apt_data[k][ym].append(it['price_per_pyeong'])
    months = sorted(all_months)
    result = []
    for it in t20:
        k = (it['apt_name'],it['sido'],it['sigungu'])
        vals = []
        for m in months:
            if m in apt_data[k]:
                vals.append(round(sum(apt_data[k][m])/len(apt_data[k][m])))
            else:
                vals.append(None)
        result.append({'name': it['apt_name'], 'values': vals})
    return months, result

def region_dist(t20):
    d=defaultdict(int)
    for it in t20: d[it['sigungu']]+=1
    return dict(sorted(d.items(),key=lambda x:x[1],reverse=True))

def rank_changes(t20, f):
    prev={}
    if os.path.exists(f):
        with open(f,'r',encoding='utf-8') as fp_: prev=json.load(fp_)
    ch=[]
    for i,it in enumerate(t20):
        k=f"{it['apt_name']}|{it['sido']}|{it['sigungu']}"
        p=prev.get(k)
        ch.append('new' if p is None else p-(i+1))
    cur={f"{it['apt_name']}|{it['sido']}|{it['sigungu']}":i+1 for i,it in enumerate(t20)}
    os.makedirs(DATA_DIR,exist_ok=True)
    with open(f,'w',encoding='utf-8') as fp_: json.dump(cur,fp_,ensure_ascii=False)
    return ch

def insights(t20, mavg):
    ms=sorted(mavg.keys())
    avg=round(sum(it['price_per_pyeong'] for it in t20)/len(t20))
    mom=0
    if len(ms)>=2:
        c,p=mavg[ms[-1]],mavg[ms[-2]]
        mom=round((c-p)/p*100,1) if p>0 else 0
    rd=region_dist(t20)
    streak=0;direction='flat'
    if len(ms)>=2:
        for i in range(len(ms)-1,0,-1):
            diff=mavg[ms[i]]-mavg[ms[i-1]]
            if streak==0:
                direction='up' if diff>0 else 'down'
                streak=1
            elif (direction=='up' and diff>0) or (direction=='down' and diff<0):
                streak+=1
            else: break
    return {'avg':avg,'mom':mom,'top_apt':t20[0]['apt_name'],'top_apt_price':t20[0]['price_per_pyeong'],
            'top_region':list(rd.keys())[0],'top_region_count':list(rd.values())[0],
            'streak':streak,'direction':direction}

def gen_html(t20, rch, mavg, rdist, ins, gkey, apt_months, apt_series):
    ut=datetime.now().strftime('%Y.%m.%d %H:%M')
    cl=json.dumps(list(mavg.keys()));cv=json.dumps(list(mavg.values()))
    dl=json.dumps(list(rdist.keys()));dv=json.dumps(list(rdist.values()))
    colors=['#00d4aa','#4ecdc4','#ff6b6b','#45b7d1','#96ceb4','#ffeaa7','#dfe6e9','#a29bfe','#fd79a8','#e17055','#00b894','#6c5ce7','#fdcb6e','#e84393','#636e72','#fab1a0','#74b9ff','#55efc4','#b2bec3','#ff7675']
    dc=json.dumps(colors[:len(rdist)])
    af=fp(ins['avg']);mom=ins['mom']
    ms='▲' if mom>0 else ('▼' if mom<0 else '─')
    mc='#00d4aa' if mom>0 else ('#ff4757' if mom<0 else '#888')
    
    tp=[]
    if ins['streak']>1:
        e='📈' if ins['direction']=='up' else '📉'
        tp.append(f"{e} {ins['streak']}개월 연속 {'상승' if ins['direction']=='up' else '하락'} 중")
    for i,rc in enumerate(rch):
        if rc=='new': tp.append(f"🆕 신규 진입: {t20[i]['apt_name']}")
    mvrs=[(i,rc) for i,rc in enumerate(rch) if isinstance(rc,int) and rc!=0]
    if mvrs:
        bu=max(mvrs,key=lambda x:x[1])
        bd=min(mvrs,key=lambda x:x[1])
        if bu[1]>0: tp.append(f"🔥 최대 상승: {t20[bu[0]]['apt_name']} (+{bu[1]}위)")
        if bd[1]<0: tp.append(f"❄️ 최대 하락: {t20[bd[0]]['apt_name']} ({bd[1]}위)")
    th=' · '.join(tp) if tp else '📊 순위 변동 데이터 수집 중...'
    
    # Per-apartment chart data
    apt_labels = json.dumps(apt_months)
    apt_datasets_js = "["
    for i, s in enumerate(apt_series):
        c = colors[i % len(colors)]
        vals = json.dumps(s['values'])
        apt_datasets_js += f"""{{
            label:'{s['name']}',data:{vals},borderColor:'{c}',
            backgroundColor:'transparent',tension:0.3,
            pointRadius:0,pointHoverRadius:4,borderWidth:1.5,
            spanGaps:true
        }},"""
    apt_datasets_js += "]"
    
    rows=""
    for i,it in enumerate(t20):
        rc=rch[i]
        if rc=='new': ch='<span style="color:#ffeaa7;font-size:0.8rem;">NEW</span>'
        elif rc>0: ch=f'<span style="color:#00d4aa;">▲{{rc}}</span>'
        elif rc<0: ch=f'<span style="color:#ff4757;">▼{{abs(rc)}}</span>'
        else: ch='<span style="color:#888;">─</span>'
        dd=f"{{it['deal_year']}}.{{it['deal_month'].zfill(2)}}.{{it['deal_day'].zfill(2)}}"
        loc=f"{{it['sido']}} {{it['sigungu']}}"
        mq=f"{{it['apt_name']}}+{{it['sido']}}+{{it['sigungu']}}+{{it['dong']}}"
        c = colors[i % len(colors)]
        rows+=f'''
        <tr class="main-row" data-idx="{{i}}" onclick="handleRowClick({{i}})">
            <td class="rank-cell">{{i+1}}</td><td class="change-cell">{{ch}}</td>
            <td class="apt-name"><span class="color-dot" style="background:{{c}};"></span>{{it['apt_name']}} <span class="arrow" id="arrow-{{i+1}}">▼</span></td>
            <td class="loc-cell">{{loc}}</td><td class="price">{{fp(it['price_per_pyeong'])}}</td>
        </tr>
        <tr class="detail-row" id="detail-{{i+1}}"><td colspan="5"><div class="detail-content">
            <div class="detail-info"><table class="detail-table">
                <tr><th>동</th><td>{{it['dong']}}</td></tr>
                <tr><th>전용면적</th><td>{{it['area_m2']}}㎡ ({{it['area_pyeong']}}평)</td></tr>
                <tr><th>거래금액</th><td>{{fb(it['price'])}}</td></tr>
                <tr><th>거래일</th><td>{{dd}}</td></tr>
                <tr><th>층</th><td>{{it['floor']}}층</td></tr>
                <tr><th>건축년도</th><td>{{it['build_year']}}년</td></tr>
            </table></div>
            <div class="detail-map"><iframe width="300" height="200" style="border:0;border-radius:8px;" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed/v1/place?key={{gkey}}&q={{mq}}&zoom=15"></iframe></div>
        </div></td></tr>'''

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>서울 아파트 평당가 TOP 20</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Noto Sans KR',sans-serif;background:#000;color:#fff;min-height:100vh;padding:40px 20px}}
.container{{max-width:1200px;margin:0 auto}}
h1{{font-size:2rem;font-weight:700;margin-bottom:8px;letter-spacing:-0.5px}}
.subtitle{{color:#888;font-size:0.9rem;margin-bottom:24px}}
.insight-cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}}
.insight-card{{background:#1a1a1a;border-radius:12px;padding:20px}}
.insight-card .label{{color:#888;font-size:0.8rem;margin-bottom:8px}}
.insight-card .value{{font-size:1.3rem;font-weight:700}}
.insight-card .sub{{font-size:0.85rem;margin-top:4px;color:#888}}
.chart-section{{background:#1a1a1a;border-radius:12px;padding:24px;margin-bottom:20px}}
.chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;flex-wrap:wrap;gap:10px}}
.chart-title{{font-size:1rem;font-weight:700}}
.chart-hint{{font-size:0.8rem;color:#555;margin-top:8px;text-align:center}}
.toggle-btns{{display:flex;gap:4px}}
.toggle-btn{{background:#333;border:none;color:#aaa;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:0.8rem;font-family:inherit;transition:all 0.2s}}
.toggle-btn.active{{background:#00d4aa;color:#000}}
.chart-canvas-wrap{{width:100%;height:200px;position:relative}}
.chart-canvas-wrap canvas{{width:100%!important;height:100%!important}}
.selected-label{{position:absolute;top:8px;left:12px;font-size:0.9rem;font-weight:700;color:#00d4aa;opacity:0;transition:opacity 0.3s;pointer-events:none}}
.selected-label.show{{opacity:1}}
.trend-bar{{background:#1a1a1a;border-radius:12px;padding:16px 20px;margin-bottom:20px;font-size:0.9rem;color:#aaa}}
table.main-table{{width:100%;border-collapse:collapse}}
table.main-table thead th{{text-align:left;padding:14px 10px;border-bottom:2px solid #333;font-weight:500;color:#aaa;font-size:0.82rem}}
table.main-table thead th:last-child{{text-align:right}}
.main-row{{cursor:pointer;transition:background 0.25s,opacity 0.25s}}
.main-row:hover{{background:#1a1a1a}}
.main-row td{{padding:16px 10px;border-bottom:1px solid #222;font-size:0.95rem}}
.main-row.active-row{{background:rgba(0,212,170,0.08)}}
.main-row.dimmed{{opacity:0.35}}
.color-dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:8px;vertical-align:middle}}
.rank-cell{{font-weight:700;color:#666;width:40px}}
.change-cell{{width:50px;font-size:0.85rem}}
.apt-name{{font-weight:500}}
.loc-cell{{color:#aaa}}
.arrow{{color:#555;font-size:0.7rem;margin-left:6px;transition:transform 0.2s;display:inline-block}}
.arrow.open{{transform:rotate(180deg)}}
.price{{text-align:right;font-weight:700;color:#00d4aa;font-variant-numeric:tabular-nums}}
.detail-row{{display:none}}
.detail-row.show{{display:table-row}}
.detail-row td{{padding:0;background:#0d0d0d;border-bottom:1px solid #222}}
.detail-content{{padding:20px 10px 20px 50px;display:flex;gap:30px;align-items:flex-start}}
.detail-info{{flex:1}}
.detail-map{{flex-shrink:0}}
.detail-table{{width:100%;max-width:350px}}
.detail-table th{{text-align:left;padding:7px 16px 7px 0;color:#666;font-weight:400;font-size:0.88rem;width:90px}}
.detail-table td{{padding:7px 0;font-size:0.93rem;color:#ccc}}
.footer{{margin-top:40px;padding-top:20px;border-top:1px solid #222;color:#555;font-size:0.8rem;text-align:center}}
@media(max-width:1024px){{.insight-cards{{grid-template-columns:repeat(2,1fr)}}}}
@media(max-width:600px){{body{{padding:20px 12px}}h1{{font-size:1.4rem}}.insight-cards{{grid-template-columns:1fr 1fr}}.chart-canvas-wrap{{height:180px}}.detail-content{{flex-direction:column;padding:15px 8px 15px 20px;gap:16px}}.detail-map iframe{{width:100%;max-width:300px}}.main-row td{{padding:12px 6px;font-size:0.88rem}}}}
</style>
</head>
<body>
<div class="container">
<h1>서울 아파트 평당가 TOP 20 <span style="font-weight:400;font-size:1rem;color:#888;">(전용면적 기준)</span></h1>
<p class="subtitle">최근 6개월 실거래 기준 · 단지별 최고가</p>

<div class="insight-cards">
<div class="insight-card"><div class="label">TOP 20 평균 평당가</div><div class="value">{af}</div></div>
<div class="insight-card"><div class="label">전월 대비</div><div class="value" style="color:{mc};">{ms} {abs(mom)}%</div></div>
<div class="insight-card"><div class="label">최고가 단지</div><div class="value" style="font-size:1.1rem;">{ins['top_apt']}</div><div class="sub">{fp(ins['top_apt_price'])}</div></div>
<div class="insight-card"><div class="label">최다 지역</div><div class="value" style="font-size:1.1rem;">{ins['top_region']}</div><div class="sub">TOP 20 중 {ins['top_region_count']}개</div></div>
</div>

<div class="chart-section" id="chartSection">
<div class="chart-header">
<span class="chart-title">📈 아파트별 평당가 추이</span>
<div class="toggle-btns">
<button class="toggle-btn" onclick="setRange(12)" id="btn-1y">1년</button>
<button class="toggle-btn" onclick="setRange(24)" id="btn-2y">2년</button>
<button class="toggle-btn active" onclick="setRange(36)" id="btn-3y">3년</button>
</div>
</div>
<div class="chart-canvas-wrap">
<div class="selected-label" id="selectedLabel"></div>
<canvas id="trendChart"></canvas>
</div>
<div class="chart-hint">👆 아래 리스트에서 아파트를 클릭하면 해당 추이가 강조됩니다</div>
</div>

<div class="trend-bar">{th}</div>

<table class="main-table">
<thead><tr><th>순위</th><th></th><th>단지명</th><th>지역</th><th style="text-align:right;">평당가</th></tr></thead>
<tbody>{rows}</tbody>
</table>

<div class="footer">마지막 업데이트: {ut} · 데이터 출처: 국토교통부 실거래가 공개시스템</div>
</div>

<script>
const aptLabels = {apt_labels};
const aptDatasets = {apt_datasets_js};
const avgLabels = {cl};
const avgValues = {cv};

const COLORS = {json.dumps(colors[:20])};

/* ── Chart.js: 아파트별 추이 ── */
const ctx = document.getElementById('trendChart').getContext('2d');
const datasets = aptDatasets.map((d, i) => ({{
    ...d,
    borderColor: COLORS[i],
    borderWidth: 1.5,
    pointRadius: 0,
    pointHoverRadius: 4,
    backgroundColor: 'transparent',
    tension: 0.3,
    spanGaps: true,
    _origColor: COLORS[i]
}}));

const tc = new Chart(ctx, {{
    type: 'line',
    data: {{ labels: aptLabels, datasets: datasets }},
    options: {{
        responsive: true, maintainAspectRatio: false,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
            legend: {{ display: false }},
            tooltip: {{
                backgroundColor: '#1a1a1a', titleColor: '#fff',
                bodyColor: '#ccc', borderColor: '#333', borderWidth: 1,
                filter: function(item) {{ return item.raw !== null; }},
                callbacks: {{
                    label: function(c) {{
                        if (c.raw === null) return null;
                        const v = c.raw;
                        const b = Math.floor(v / 10000);
                        const r = v % 10000;
                        const p = b > 0 ? b + '억 ' + r.toLocaleString() + '만' : v.toLocaleString() + '만';
                        return c.dataset.label + ': ' + p;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{ ticks: {{ color: '#666', maxRotation: 45, maxTicksLimit: 12 }}, grid: {{ color: '#222' }} }},
            y: {{
                ticks: {{
                    color: '#666',
                    callback: function(v) {{
                        const b = Math.floor(v / 10000);
                        return b > 0 ? b + '억' : v.toLocaleString() + '만';
                    }}
                }},
                grid: {{ color: '#222' }}
            }}
        }}
    }}
}});

/* ── 기간 토글 ── */
function setRange(m) {{
    document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(m === 12 ? 'btn-1y' : m === 24 ? 'btn-2y' : 'btn-3y').classList.add('active');
    tc.data.labels = aptLabels.slice(-m);
    tc.data.datasets.forEach((ds, i) => {{
        ds.data = aptDatasets[i].data.slice(-m);
    }});
    tc.update();
}}

/* ── 클릭 인터랙션: 리스트 → 차트 하이라이트 ── */
let activeIdx = -1;

function highlightChart(idx) {{
    const label = document.getElementById('selectedLabel');
    tc.data.datasets.forEach((ds, i) => {{
        if (i === idx) {{
            ds.borderWidth = 3.5;
            ds.borderColor = ds._origColor;
            ds.pointRadius = 3;
            ds.pointBackgroundColor = ds._origColor;
        }} else {{
            ds.borderWidth = 1;
            ds.borderColor = ds._origColor + '1A';
            ds.pointRadius = 0;
        }}
    }});
    label.textContent = aptDatasets[idx].label;
    label.style.color = COLORS[idx];
    label.classList.add('show');
    tc.update();
}}

function resetChart() {{
    const label = document.getElementById('selectedLabel');
    tc.data.datasets.forEach((ds) => {{
        ds.borderWidth = 1.5;
        ds.borderColor = ds._origColor;
        ds.pointRadius = 0;
    }});
    label.classList.remove('show');
    tc.update();
}}

function highlightRows(idx) {{
    document.querySelectorAll('.main-row').forEach((row, i) => {{
        if (i === idx) {{
            row.classList.add('active-row');
            row.classList.remove('dimmed');
        }} else {{
            row.classList.remove('active-row');
            row.classList.add('dimmed');
        }}
    }});
}}

function resetRows() {{
    document.querySelectorAll('.main-row').forEach(row => {{
        row.classList.remove('active-row', 'dimmed');
    }});
}}

function handleRowClick(idx) {{
    if (activeIdx === idx) {{
        activeIdx = -1;
        resetChart();
        resetRows();
    }} else {{
        activeIdx = idx;
        highlightChart(idx);
        highlightRows(idx);
        document.getElementById('chartSection').scrollIntoView({{ behavior: 'smooth', block: 'nearest' }});
    }}
    toggleDetail(idx + 1);
}}

function toggleDetail(id) {{
    document.getElementById('detail-' + id).classList.toggle('show');
    document.getElementById('arrow-' + id).classList.toggle('open');
}}
</script>
</body>
</html>'''

def main():
    print("=== 서울 아파트 평당가 TOP 20 ===\n")
    
    if API_KEY in ('YOUR_API_KEY_HERE', ''):
        print("❌ MOLIT_API_KEY가 설정되지 않았습니다!")
        exit(1)
    print(f"✅ API Key: {API_KEY[:8]}...{API_KEY[-4:]}")
    
    test_ym = get_months(1)[0]
    test_url = f"{BASE_URL}?serviceKey={API_KEY}&LAWD_CD=11680&DEAL_YMD={test_ym}&pageNo=1&numOfRows=1"
    try:
        tr = requests.get(test_url, timeout=15)
        if '<resultCode>00</resultCode>' in tr.text:
            print(f"✅ API 테스트 성공 (강남구 {test_ym})")
        else:
            import re
            rc = re.search(r'<resultCode>(\d+)</resultCode>', tr.text)
            rm = re.search(r'<resultMsg>([^<]+)</resultMsg>', tr.text)
            code = rc.group(1) if rc else 'unknown'
            msg = rm.group(1) if rm else tr.text[:200]
            print(f"❌ API 테스트 실패: {code} - {msg}")
            exit(1)
    except Exception as e:
        print(f"❌ API 연결 실패: {e}")
        exit(1)
    print(f"📊 조회 지역: 서울시 {len(REGIONS)}개 구 (예상 API 호출: ~{len(REGIONS)*6+len(REGIONS)*30}건)\n")
    
    months_6=get_months(6)
    print(f"Step 1: 전 지역 최근 6개월 ({months_6[0]}~{months_6[-1]})")
    recent=[]
    total=len(REGIONS)
    for i,(code,(s,g)) in enumerate(REGIONS.items(),1):
        for m in months_6: recent.extend(fetch(code,m))
        if i%20==0: print(f"  [{i}/{total}]..."); time.sleep(1)
    print(f"  → {len(recent)}건")
    if len(recent) == 0:
        print("\n❌ 에러: 데이터를 가져오지 못했습니다!")
        print("  → API 키를 확인하세요 (GitHub Secrets: MOLIT_API_KEY)")
        exit(1)
    t20=top20(recent)
    keys=set((it['apt_name'],it['sido'],it['sigungu']) for it in t20)
    regs=set(it['region_code'] for it in t20)
    print(f"  → TOP 20 확정 ({len(regs)}개 지역)\n")
    
    months_36=get_months(36)
    extra=[m for m in months_36 if m not in months_6]
    print(f"Step 2: TOP 20 지역 히스토리 ({len(extra)}개월 × {len(regs)}개 지역)")
    alldata=list(recent)
    for code in regs:
        for m in extra: alldata.extend(fetch(code,m))
        time.sleep(0.5)
    print(f"  → 총 {len(alldata)}건\n")
    
    print("Step 3: 분석...")
    mavg=monthly_avg(alldata,keys)
    apt_months, apt_series = per_apt_monthly(alldata, t20)
    rd=region_dist(t20)
    os.makedirs(DATA_DIR,exist_ok=True)
    rch=rank_changes(t20,os.path.join(DATA_DIR,'previous_rank.json'))
    ins=insights(t20,mavg)
    
    with open(os.path.join(DATA_DIR,'top20.json'),'w',encoding='utf-8') as f: json.dump([it for it in t20],f,ensure_ascii=False,indent=2)
    with open(os.path.join(DATA_DIR,'history.json'),'w',encoding='utf-8') as f: json.dump(mavg,f,ensure_ascii=False,indent=2)
    
    print("Step 4: HTML 생성...")
    html=gen_html(t20,rch,mavg,rd,ins,GOOGLE_MAPS_API_KEY,apt_months,apt_series)
    with open('index.html','w',encoding='utf-8') as f: f.write(html)
    
    print("\n✅ 완료!")
    for i,it in enumerate(t20,1): print(f"  {i}. {it['apt_name']} ({it['sido']} {it['sigungu']}) - {fp(it['price_per_pyeong'])}")

if __name__=='__main__': main()
