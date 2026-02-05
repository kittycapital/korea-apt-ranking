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
    '26110':('부산시','중구'),'26140':('부산시','서구'),'26170':('부산시','동구'),
    '26200':('부산시','영도구'),'26230':('부산시','부산진구'),'26260':('부산시','동래구'),
    '26290':('부산시','남구'),'26320':('부산시','북구'),'26350':('부산시','해운대구'),
    '26380':('부산시','사하구'),'26410':('부산시','금정구'),'26440':('부산시','강서구'),
    '26470':('부산시','연제구'),'26500':('부산시','수영구'),'26530':('부산시','사상구'),
    '26710':('부산시','기장군'),
    '27110':('대구시','중구'),'27140':('대구시','동구'),'27170':('대구시','서구'),
    '27200':('대구시','남구'),'27230':('대구시','북구'),'27260':('대구시','수성구'),
    '27290':('대구시','달서구'),'27710':('대구시','달성군'),'27720':('대구시','군위군'),
    '28110':('인천시','중구'),'28140':('인천시','동구'),'28177':('인천시','미추홀구'),
    '28185':('인천시','연수구'),'28200':('인천시','남동구'),'28237':('인천시','부평구'),
    '28245':('인천시','계양구'),'28260':('인천시','서구'),'28710':('인천시','강화군'),
    '28720':('인천시','옹진군'),
    '29110':('광주시','동구'),'29140':('광주시','서구'),'29155':('광주시','남구'),
    '29170':('광주시','북구'),'29200':('광주시','광산구'),
    '30110':('대전시','동구'),'30140':('대전시','중구'),'30170':('대전시','서구'),
    '30200':('대전시','유성구'),'30230':('대전시','대덕구'),
    '31110':('울산시','중구'),'31140':('울산시','남구'),'31170':('울산시','동구'),
    '31200':('울산시','북구'),'31710':('울산시','울주군'),
    '36110':('세종시','세종시'),
    '41111':('경기도','수원시 장안구'),'41113':('경기도','수원시 권선구'),
    '41115':('경기도','수원시 팔달구'),'41117':('경기도','수원시 영통구'),
    '41131':('경기도','성남시 수정구'),'41133':('경기도','성남시 중원구'),
    '41135':('경기도','성남시 분당구'),'41150':('경기도','의정부시'),
    '41171':('경기도','안양시 만안구'),'41173':('경기도','안양시 동안구'),
    '41190':('경기도','부천시'),'41210':('경기도','광명시'),
    '41220':('경기도','평택시'),'41250':('경기도','동두천시'),
    '41271':('경기도','안산시 상록구'),'41273':('경기도','안산시 단원구'),
    '41281':('경기도','고양시 덕양구'),'41285':('경기도','고양시 일산동구'),
    '41287':('경기도','고양시 일산서구'),'41290':('경기도','과천시'),
    '41310':('경기도','구리시'),'41360':('경기도','남양주시'),
    '41370':('경기도','오산시'),'41390':('경기도','시흥시'),
    '41410':('경기도','군포시'),'41430':('경기도','의왕시'),
    '41450':('경기도','하남시'),'41461':('경기도','용인시 처인구'),
    '41463':('경기도','용인시 기흥구'),'41465':('경기도','용인시 수지구'),
    '41480':('경기도','파주시'),'41500':('경기도','이천시'),
    '41550':('경기도','안성시'),'41570':('경기도','김포시'),
    '41590':('경기도','화성시'),'41610':('경기도','광주시'),
    '41630':('경기도','양주시'),'41650':('경기도','포천시'),
    '41670':('경기도','여주시'),'41800':('경기도','연천군'),
    '41820':('경기도','가평군'),'41830':('경기도','양평군'),
    '51110':('강원도','춘천시'),'51130':('강원도','원주시'),
    '51150':('강원도','강릉시'),'51170':('강원도','동해시'),
    '51190':('강원도','태백시'),'51210':('강원도','속초시'),
    '51230':('강원도','삼척시'),'51710':('강원도','홍천군'),
    '51720':('강원도','횡성군'),'51730':('강원도','영월군'),
    '51740':('강원도','평창군'),'51750':('강원도','정선군'),
    '51760':('강원도','철원군'),'51770':('강원도','화천군'),
    '51780':('강원도','양구군'),'51790':('강원도','인제군'),
    '51800':('강원도','고성군'),'51810':('강원도','양양군'),
    '43111':('충북','청주시 상당구'),'43112':('충북','청주시 서원구'),
    '43113':('충북','청주시 흥덕구'),'43114':('충북','청주시 청원구'),
    '43130':('충북','충주시'),'43150':('충북','제천시'),
    '43720':('충북','보은군'),'43730':('충북','옥천군'),
    '43740':('충북','영동군'),'43745':('충북','증평군'),
    '43750':('충북','진천군'),'43760':('충북','괴산군'),
    '43770':('충북','음성군'),'43800':('충북','단양군'),
    '44131':('충남','천안시 동남구'),'44133':('충남','천안시 서북구'),
    '44150':('충남','공주시'),'44180':('충남','보령시'),
    '44200':('충남','아산시'),'44210':('충남','서산시'),
    '44230':('충남','논산시'),'44250':('충남','계룡시'),
    '44270':('충남','당진시'),'44710':('충남','금산군'),
    '44760':('충남','부여군'),'44770':('충남','서천군'),
    '44790':('충남','청양군'),'44800':('충남','홍성군'),
    '44810':('충남','예산군'),'44825':('충남','태안군'),
    '52111':('전북','전주시 완산구'),'52113':('전북','전주시 덕진구'),
    '52130':('전북','군산시'),'52140':('전북','익산시'),
    '52180':('전북','정읍시'),'52190':('전북','남원시'),
    '52210':('전북','김제시'),'52710':('전북','완주군'),
    '52720':('전북','진안군'),'52730':('전북','무주군'),
    '52740':('전북','장수군'),'52750':('전북','임실군'),
    '52770':('전북','순창군'),'52790':('전북','고창군'),
    '52800':('전북','부안군'),
    '46110':('전남','목포시'),'46130':('전남','여수시'),
    '46150':('전남','순천시'),'46170':('전남','나주시'),
    '46230':('전남','광양시'),'46710':('전남','담양군'),
    '46720':('전남','곡성군'),'46730':('전남','구례군'),
    '46770':('전남','고흥군'),'46780':('전남','보성군'),
    '46790':('전남','화순군'),'46800':('전남','장흥군'),
    '46810':('전남','강진군'),'46820':('전남','해남군'),
    '46830':('전남','영암군'),'46840':('전남','무안군'),
    '46860':('전남','함평군'),'46870':('전남','영광군'),
    '46880':('전남','장성군'),'46890':('전남','완도군'),
    '46900':('전남','진도군'),'46910':('전남','신안군'),
    '47111':('경북','포항시 남구'),'47113':('경북','포항시 북구'),
    '47130':('경북','경주시'),'47150':('경북','김천시'),
    '47170':('경북','안동시'),'47190':('경북','구미시'),
    '47210':('경북','영주시'),'47230':('경북','영천시'),
    '47250':('경북','상주시'),'47280':('경북','문경시'),
    '47290':('경북','경산시'),'47720':('경북','의성군'),
    '47730':('경북','청송군'),'47750':('경북','영양군'),
    '47760':('경북','영덕군'),'47770':('경북','청도군'),
    '47820':('경북','고령군'),'47830':('경북','성주군'),
    '47840':('경북','칠곡군'),'47850':('경북','예천군'),
    '47900':('경북','봉화군'),'47920':('경북','울진군'),
    '47930':('경북','울릉군'),
    '48121':('경남','창원시 의창구'),'48123':('경남','창원시 성산구'),
    '48125':('경남','창원시 마산합포구'),'48127':('경남','창원시 마산회원구'),
    '48129':('경남','창원시 진해구'),'48170':('경남','진주시'),
    '48220':('경남','통영시'),'48240':('경남','사천시'),
    '48250':('경남','김해시'),'48270':('경남','밀양시'),
    '48310':('경남','거제시'),'48330':('경남','양산시'),
    '48720':('경남','의령군'),'48730':('경남','함안군'),
    '48740':('경남','창녕군'),'48820':('경남','고성군'),
    '48840':('경남','남해군'),'48850':('경남','하동군'),
    '48860':('경남','산청군'),'48870':('경남','함양군'),
    '48880':('경남','거창군'),'48890':('경남','합천군'),
    '50110':('제주도','제주시'),'50130':('제주도','서귀포시'),
}

def get_months(n):
    months = set()
    today = datetime.today()
    for i in range(n):
        d = today.replace(day=1) - timedelta(days=30*i)
        months.add(d.strftime('%Y%m'))
    return sorted(months)

def fetch(code, ym):
    params = {'serviceKey':API_KEY,'LAWD_CD':code,'DEAL_YMD':ym,'pageNo':'1','numOfRows':'1000'}
    try:
        r = requests.get(BASE_URL, params=params, timeout=30)
        r.raise_for_status()
        return parse(r.text, code)
    except Exception as e:
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

def gen_html(t20, rch, mavg, rdist, ins, gkey):
    ut=datetime.now().strftime('%Y.%m.%d %H:%M')
    cl=json.dumps(list(mavg.keys()));cv=json.dumps(list(mavg.values()))
    dl=json.dumps(list(rdist.keys()));dv=json.dumps(list(rdist.values()))
    colors=['#00d4aa','#4ecdc4','#ff6b6b','#45b7d1','#96ceb4','#ffeaa7','#dfe6e9','#a29bfe','#fd79a8','#e17055','#00b894','#6c5ce7','#fdcb6e','#e84393','#636e72']
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
    
    rows=""
    for i,it in enumerate(t20):
        rc=rch[i]
        if rc=='new': ch='<span style="color:#ffeaa7;font-size:0.8rem;">NEW</span>'
        elif rc>0: ch=f'<span style="color:#00d4aa;">▲{rc}</span>'
        elif rc<0: ch=f'<span style="color:#ff4757;">▼{abs(rc)}</span>'
        else: ch='<span style="color:#888;">─</span>'
        dd=f"{it['deal_year']}.{it['deal_month'].zfill(2)}.{it['deal_day'].zfill(2)}"
        loc=f"{it['sido']} {it['sigungu']}"
        mq=f"{it['apt_name']}+{it['sido']}+{it['sigungu']}+{it['dong']}"
        rows+=f'''
        <tr class="main-row" onclick="toggleDetail({i+1})">
            <td class="rank-cell">{i+1}</td><td class="change-cell">{ch}</td>
            <td class="apt-name">{it['apt_name']} <span class="arrow" id="arrow-{i+1}">▼</span></td>
            <td class="loc-cell">{loc}</td><td class="price">{fp(it['price_per_pyeong'])}</td>
        </tr>
        <tr class="detail-row" id="detail-{i+1}"><td colspan="5"><div class="detail-content">
            <div class="detail-info"><table class="detail-table">
                <tr><th>동</th><td>{it['dong']}</td></tr>
                <tr><th>전용면적</th><td>{it['area_m2']}㎡ ({it['area_pyeong']}평)</td></tr>
                <tr><th>거래금액</th><td>{fb(it['price'])}</td></tr>
                <tr><th>거래일</th><td>{dd}</td></tr>
                <tr><th>층</th><td>{it['floor']}층</td></tr>
                <tr><th>건축년도</th><td>{it['build_year']}년</td></tr>
            </table></div>
            <div class="detail-map"><iframe width="300" height="200" style="border:0;border-radius:8px;" loading="lazy" allowfullscreen referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps/embed/v1/place?key={gkey}&q={mq}&zoom=15"></iframe></div>
        </div></td></tr>'''

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>전국 아파트 평당가 TOP 20</title>
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
.trend-bar{{background:#1a1a1a;border-radius:12px;padding:16px 20px;margin-bottom:24px;font-size:0.9rem;color:#aaa}}
.content-grid{{display:grid;grid-template-columns:380px 1fr;gap:24px}}
.left-panel{{display:flex;flex-direction:column;gap:20px}}
.chart-box,.donut-box{{background:#1a1a1a;border-radius:12px;padding:20px}}
.chart-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}}
.chart-title{{font-size:0.95rem;font-weight:500}}
.toggle-btns{{display:flex;gap:4px}}
.toggle-btn{{background:#333;border:none;color:#aaa;padding:6px 14px;border-radius:8px;cursor:pointer;font-size:0.8rem;font-family:inherit;transition:all 0.2s}}
.toggle-btn.active{{background:#00d4aa;color:#000}}
.chart-canvas{{width:100%;height:200px}}
.donut-canvas{{width:100%;height:200px}}
table.main-table{{width:100%;border-collapse:collapse}}
table.main-table thead th{{text-align:left;padding:14px 10px;border-bottom:2px solid #333;font-weight:500;color:#aaa;font-size:0.82rem}}
table.main-table thead th:last-child{{text-align:right}}
.main-row{{cursor:pointer;transition:background 0.2s}}
.main-row:hover{{background:#1a1a1a}}
.main-row td{{padding:16px 10px;border-bottom:1px solid #222;font-size:0.95rem}}
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
@media(max-width:1024px){{.insight-cards{{grid-template-columns:repeat(2,1fr)}}.content-grid{{grid-template-columns:1fr}}.left-panel{{flex-direction:row}}.chart-box,.donut-box{{flex:1}}}}
@media(max-width:600px){{body{{padding:20px 12px}}h1{{font-size:1.4rem}}.insight-cards{{grid-template-columns:1fr 1fr}}.left-panel{{flex-direction:column}}.detail-content{{flex-direction:column;padding:15px 8px 15px 20px;gap:16px}}.detail-map iframe{{width:100%;max-width:300px}}.main-row td{{padding:12px 6px;font-size:0.88rem}}}}
</style>
</head>
<body>
<div class="container">
<h1>전국 아파트 평당가 TOP 20 <span style="font-weight:400;font-size:1rem;color:#888;">(전용면적 기준)</span></h1>
<p class="subtitle">최근 6개월 실거래 기준 · 단지별 최고가</p>
<div class="insight-cards">
<div class="insight-card"><div class="label">TOP 20 평균 평당가</div><div class="value">{af}</div></div>
<div class="insight-card"><div class="label">전월 대비</div><div class="value" style="color:{mc};">{ms} {abs(mom)}%</div></div>
<div class="insight-card"><div class="label">최고가 단지</div><div class="value" style="font-size:1.1rem;">{ins['top_apt']}</div><div class="sub">{fp(ins['top_apt_price'])}</div></div>
<div class="insight-card"><div class="label">최다 지역</div><div class="value" style="font-size:1.1rem;">{ins['top_region']}</div><div class="sub">TOP 20 중 {ins['top_region_count']}개</div></div>
</div>
<div class="trend-bar">{th}</div>
<div class="content-grid">
<div class="left-panel">
<div class="chart-box">
<div class="chart-header"><span class="chart-title">평균 평당가 추이</span>
<div class="toggle-btns">
<button class="toggle-btn" onclick="setRange(12)" id="btn-1y">1년</button>
<button class="toggle-btn" onclick="setRange(24)" id="btn-2y">2년</button>
<button class="toggle-btn active" onclick="setRange(36)" id="btn-3y">3년</button>
</div></div>
<canvas id="trendChart" class="chart-canvas"></canvas>
</div>
<div class="donut-box">
<div class="chart-header"><span class="chart-title">지역 분포</span></div>
<canvas id="donutChart" class="donut-canvas"></canvas>
</div>
</div>
<div class="right-panel">
<table class="main-table"><thead><tr>
<th>순위</th><th></th><th>단지명</th><th>지역</th><th style="text-align:right;">평당가</th>
</tr></thead><tbody>{rows}</tbody></table>
</div>
</div>
<div class="footer">마지막 업데이트: {ut} · 데이터 출처: 국토교통부 실거래가 공개시스템</div>
</div>
<script>
const aL={cl};const aV={cv};const dL={dl};const dV={dv};const dC={dc};
const ctx=document.getElementById('trendChart').getContext('2d');
const tc=new Chart(ctx,{{type:'line',data:{{labels:aL,datasets:[{{data:aV,borderColor:'#00d4aa',backgroundColor:'rgba(0,212,170,0.1)',fill:true,tension:0.3,pointRadius:2,pointHoverRadius:5,borderWidth:2}}]}},options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}},tooltip:{{backgroundColor:'#1a1a1a',titleColor:'#fff',bodyColor:'#00d4aa',borderColor:'#333',borderWidth:1,callbacks:{{label:function(c){{const v=c.parsed.y;const b=Math.floor(v/10000);const r=v%10000;return b>0?b+'억 '+r.toLocaleString()+'만':v.toLocaleString()+'만'}}}}}}}},scales:{{x:{{ticks:{{color:'#666',maxRotation:45}},grid:{{color:'#222'}}}},y:{{ticks:{{color:'#666',callback:function(v){{const b=Math.floor(v/10000);return b>0?b+'억':v.toLocaleString()+'만'}}}},grid:{{color:'#222'}}}}}}}}}});
function setRange(m){{document.querySelectorAll('.toggle-btn').forEach(b=>b.classList.remove('active'));document.getElementById(m===12?'btn-1y':m===24?'btn-2y':'btn-3y').classList.add('active');tc.data.labels=aL.slice(-m);tc.data.datasets[0].data=aV.slice(-m);tc.update()}}
new Chart(document.getElementById('donutChart').getContext('2d'),{{type:'doughnut',data:{{labels:dL,datasets:[{{data:dV,backgroundColor:dC,borderWidth:0}}]}},options:{{responsive:true,maintainAspectRatio:false,cutout:'60%',plugins:{{legend:{{position:'right',labels:{{color:'#aaa',font:{{size:12}},padding:12}}}}}}}}}});
function toggleDetail(id){{document.getElementById('detail-'+id).classList.toggle('show');document.getElementById('arrow-'+id).classList.toggle('open')}}
</script>
</body>
</html>'''

def main():
    print("=== 전국 아파트 평당가 TOP 20 ===\n")
    months_6=get_months(6)
    print(f"Step 1: 전 지역 최근 6개월 ({months_6[0]}~{months_6[-1]})")
    recent=[]
    total=len(REGIONS)
    for i,(code,(s,g)) in enumerate(REGIONS.items(),1):
        for m in months_6: recent.extend(fetch(code,m))
        if i%20==0: print(f"  [{i}/{total}]..."); time.sleep(1)
    print(f"  → {len(recent)}건")
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
    rd=region_dist(t20)
    os.makedirs(DATA_DIR,exist_ok=True)
    rch=rank_changes(t20,os.path.join(DATA_DIR,'previous_rank.json'))
    ins=insights(t20,mavg)
    
    with open(os.path.join(DATA_DIR,'top20.json'),'w',encoding='utf-8') as f: json.dump([it for it in t20],f,ensure_ascii=False,indent=2)
    with open(os.path.join(DATA_DIR,'history.json'),'w',encoding='utf-8') as f: json.dump(mavg,f,ensure_ascii=False,indent=2)
    
    print("Step 4: HTML 생성...")
    html=gen_html(t20,rch,mavg,rd,ins,GOOGLE_MAPS_API_KEY)
    with open('index.html','w',encoding='utf-8') as f: f.write(html)
    
    print("\n✅ 완료!")
    for i,it in enumerate(t20,1): print(f"  {i}. {it['apt_name']} ({it['sido']} {it['sigungu']}) - {fp(it['price_per_pyeong'])}")

if __name__=='__main__': main()
