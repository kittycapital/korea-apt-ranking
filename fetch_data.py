"""
전국 아파트 평당가 TOP 20 데이터 수집 및 HTML 생성
- 데이터 출처: 국토교통부 아파트 매매 실거래가 API
- 기간: 최근 6개월
- 필터: 전용면적 59㎡ 이상
- 중복처리: 단지별 최고가만
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from collections import defaultdict
import os
import time

# ========== 설정 ==========
API_KEY = os.environ.get('MOLIT_API_KEY', 'YOUR_API_KEY_HERE')
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'YOUR_GOOGLE_MAPS_API_KEY_HERE')
BASE_URL = "http://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev"

# 전국 시/도 및 시/군/구 코드
# 법정동코드 앞 5자리 (시군구 코드)
REGIONS = {
    # 서울특별시
    '11110': ('서울시', '종로구'), '11140': ('서울시', '중구'), '11170': ('서울시', '용산구'),
    '11200': ('서울시', '성동구'), '11215': ('서울시', '광진구'), '11230': ('서울시', '동대문구'),
    '11260': ('서울시', '중랑구'), '11290': ('서울시', '성북구'), '11305': ('서울시', '강북구'),
    '11320': ('서울시', '도봉구'), '11350': ('서울시', '노원구'), '11380': ('서울시', '은평구'),
    '11410': ('서울시', '서대문구'), '11440': ('서울시', '마포구'), '11470': ('서울시', '양천구'),
    '11500': ('서울시', '강서구'), '11530': ('서울시', '구로구'), '11545': ('서울시', '금천구'),
    '11560': ('서울시', '영등포구'), '11590': ('서울시', '동작구'), '11620': ('서울시', '관악구'),
    '11650': ('서울시', '서초구'), '11680': ('서울시', '강남구'), '11710': ('서울시', '송파구'),
    '11740': ('서울시', '강동구'),
    
    # 부산광역시
    '26110': ('부산시', '중구'), '26140': ('부산시', '서구'), '26170': ('부산시', '동구'),
    '26200': ('부산시', '영도구'), '26230': ('부산시', '부산진구'), '26260': ('부산시', '동래구'),
    '26290': ('부산시', '남구'), '26320': ('부산시', '북구'), '26350': ('부산시', '해운대구'),
    '26380': ('부산시', '사하구'), '26410': ('부산시', '금정구'), '26440': ('부산시', '강서구'),
    '26470': ('부산시', '연제구'), '26500': ('부산시', '수영구'), '26530': ('부산시', '사상구'),
    '26710': ('부산시', '기장군'),
    
    # 대구광역시
    '27110': ('대구시', '중구'), '27140': ('대구시', '동구'), '27170': ('대구시', '서구'),
    '27200': ('대구시', '남구'), '27230': ('대구시', '북구'), '27260': ('대구시', '수성구'),
    '27290': ('대구시', '달서구'), '27710': ('대구시', '달성군'), '27720': ('대구시', '군위군'),
    
    # 인천광역시
    '28110': ('인천시', '중구'), '28140': ('인천시', '동구'), '28177': ('인천시', '미추홀구'),
    '28185': ('인천시', '연수구'), '28200': ('인천시', '남동구'), '28237': ('인천시', '부평구'),
    '28245': ('인천시', '계양구'), '28260': ('인천시', '서구'), '28710': ('인천시', '강화군'),
    '28720': ('인천시', '옹진군'),
    
    # 광주광역시
    '29110': ('광주시', '동구'), '29140': ('광주시', '서구'), '29155': ('광주시', '남구'),
    '29170': ('광주시', '북구'), '29200': ('광주시', '광산구'),
    
    # 대전광역시
    '30110': ('대전시', '동구'), '30140': ('대전시', '중구'), '30170': ('대전시', '서구'),
    '30200': ('대전시', '유성구'), '30230': ('대전시', '대덕구'),
    
    # 울산광역시
    '31110': ('울산시', '중구'), '31140': ('울산시', '남구'), '31170': ('울산시', '동구'),
    '31200': ('울산시', '북구'), '31710': ('울산시', '울주군'),
    
    # 세종특별자치시
    '36110': ('세종시', '세종시'),
    
    # 경기도
    '41111': ('경기도', '수원시 장안구'), '41113': ('경기도', '수원시 권선구'),
    '41115': ('경기도', '수원시 팔달구'), '41117': ('경기도', '수원시 영통구'),
    '41131': ('경기도', '성남시 수정구'), '41133': ('경기도', '성남시 중원구'),
    '41135': ('경기도', '성남시 분당구'), '41150': ('경기도', '의정부시'),
    '41171': ('경기도', '안양시 만안구'), '41173': ('경기도', '안양시 동안구'),
    '41190': ('경기도', '부천시'), '41210': ('경기도', '광명시'),
    '41220': ('경기도', '평택시'), '41250': ('경기도', '동두천시'),
    '41271': ('경기도', '안산시 상록구'), '41273': ('경기도', '안산시 단원구'),
    '41281': ('경기도', '고양시 덕양구'), '41285': ('경기도', '고양시 일산동구'),
    '41287': ('경기도', '고양시 일산서구'), '41290': ('경기도', '과천시'),
    '41310': ('경기도', '구리시'), '41360': ('경기도', '남양주시'),
    '41370': ('경기도', '오산시'), '41390': ('경기도', '시흥시'),
    '41410': ('경기도', '군포시'), '41430': ('경기도', '의왕시'),
    '41450': ('경기도', '하남시'), '41461': ('경기도', '용인시 처인구'),
    '41463': ('경기도', '용인시 기흥구'), '41465': ('경기도', '용인시 수지구'),
    '41480': ('경기도', '파주시'), '41500': ('경기도', '이천시'),
    '41550': ('경기도', '안성시'), '41570': ('경기도', '김포시'),
    '41590': ('경기도', '화성시'), '41610': ('경기도', '광주시'),
    '41630': ('경기도', '양주시'), '41650': ('경기도', '포천시'),
    '41670': ('경기도', '여주시'), '41800': ('경기도', '연천군'),
    '41820': ('경기도', '가평군'), '41830': ('경기도', '양평군'),
    
    # 강원특별자치도
    '51110': ('강원도', '춘천시'), '51130': ('강원도', '원주시'),
    '51150': ('강원도', '강릉시'), '51170': ('강원도', '동해시'),
    '51190': ('강원도', '태백시'), '51210': ('강원도', '속초시'),
    '51230': ('강원도', '삼척시'), '51710': ('강원도', '홍천군'),
    '51720': ('강원도', '횡성군'), '51730': ('강원도', '영월군'),
    '51740': ('강원도', '평창군'), '51750': ('강원도', '정선군'),
    '51760': ('강원도', '철원군'), '51770': ('강원도', '화천군'),
    '51780': ('강원도', '양구군'), '51790': ('강원도', '인제군'),
    '51800': ('강원도', '고성군'), '51810': ('강원도', '양양군'),
    
    # 충청북도
    '43111': ('충북', '청주시 상당구'), '43112': ('충북', '청주시 서원구'),
    '43113': ('충북', '청주시 흥덕구'), '43114': ('충북', '청주시 청원구'),
    '43130': ('충북', '충주시'), '43150': ('충북', '제천시'),
    '43720': ('충북', '보은군'), '43730': ('충북', '옥천군'),
    '43740': ('충북', '영동군'), '43745': ('충북', '증평군'),
    '43750': ('충북', '진천군'), '43760': ('충북', '괴산군'),
    '43770': ('충북', '음성군'), '43800': ('충북', '단양군'),
    
    # 충청남도
    '44131': ('충남', '천안시 동남구'), '44133': ('충남', '천안시 서북구'),
    '44150': ('충남', '공주시'), '44180': ('충남', '보령시'),
    '44200': ('충남', '아산시'), '44210': ('충남', '서산시'),
    '44230': ('충남', '논산시'), '44250': ('충남', '계룡시'),
    '44270': ('충남', '당진시'), '44710': ('충남', '금산군'),
    '44760': ('충남', '부여군'), '44770': ('충남', '서천군'),
    '44790': ('충남', '청양군'), '44800': ('충남', '홍성군'),
    '44810': ('충남', '예산군'), '44825': ('충남', '태안군'),
    
    # 전북특별자치도
    '52111': ('전북', '전주시 완산구'), '52113': ('전북', '전주시 덕진구'),
    '52130': ('전북', '군산시'), '52140': ('전북', '익산시'),
    '52180': ('전북', '정읍시'), '52190': ('전북', '남원시'),
    '52210': ('전북', '김제시'), '52710': ('전북', '완주군'),
    '52720': ('전북', '진안군'), '52730': ('전북', '무주군'),
    '52740': ('전북', '장수군'), '52750': ('전북', '임실군'),
    '52770': ('전북', '순창군'), '52790': ('전북', '고창군'),
    '52800': ('전북', '부안군'),
    
    # 전라남도
    '46110': ('전남', '목포시'), '46130': ('전남', '여수시'),
    '46150': ('전남', '순천시'), '46170': ('전남', '나주시'),
    '46230': ('전남', '광양시'), '46710': ('전남', '담양군'),
    '46720': ('전남', '곡성군'), '46730': ('전남', '구례군'),
    '46770': ('전남', '고흥군'), '46780': ('전남', '보성군'),
    '46790': ('전남', '화순군'), '46800': ('전남', '장흥군'),
    '46810': ('전남', '강진군'), '46820': ('전남', '해남군'),
    '46830': ('전남', '영암군'), '46840': ('전남', '무안군'),
    '46860': ('전남', '함평군'), '46870': ('전남', '영광군'),
    '46880': ('전남', '장성군'), '46890': ('전남', '완도군'),
    '46900': ('전남', '진도군'), '46910': ('전남', '신안군'),
    
    # 경상북도
    '47111': ('경북', '포항시 남구'), '47113': ('경북', '포항시 북구'),
    '47130': ('경북', '경주시'), '47150': ('경북', '김천시'),
    '47170': ('경북', '안동시'), '47190': ('경북', '구미시'),
    '47210': ('경북', '영주시'), '47230': ('경북', '영천시'),
    '47250': ('경북', '상주시'), '47280': ('경북', '문경시'),
    '47290': ('경북', '경산시'), '47720': ('경북', '의성군'),
    '47730': ('경북', '청송군'), '47750': ('경북', '영양군'),
    '47760': ('경북', '영덕군'), '47770': ('경북', '청도군'),
    '47820': ('경북', '고령군'), '47830': ('경북', '성주군'),
    '47840': ('경북', '칠곡군'), '47850': ('경북', '예천군'),
    '47900': ('경북', '봉화군'), '47920': ('경북', '울진군'),
    '47930': ('경북', '울릉군'),
    
    # 경상남도
    '48121': ('경남', '창원시 의창구'), '48123': ('경남', '창원시 성산구'),
    '48125': ('경남', '창원시 마산합포구'), '48127': ('경남', '창원시 마산회원구'),
    '48129': ('경남', '창원시 진해구'), '48170': ('경남', '진주시'),
    '48220': ('경남', '통영시'), '48240': ('경남', '사천시'),
    '48250': ('경남', '김해시'), '48270': ('경남', '밀양시'),
    '48310': ('경남', '거제시'), '48330': ('경남', '양산시'),
    '48720': ('경남', '의령군'), '48730': ('경남', '함안군'),
    '48740': ('경남', '창녕군'), '48820': ('경남', '고성군'),
    '48840': ('경남', '남해군'), '48850': ('경남', '하동군'),
    '48860': ('경남', '산청군'), '48870': ('경남', '함양군'),
    '48880': ('경남', '거창군'), '48890': ('경남', '합천군'),
    
    # 제주특별자치도
    '50110': ('제주도', '제주시'), '50130': ('제주도', '서귀포시'),
}

MIN_AREA = 59  # 최소 전용면적 (㎡)


def get_recent_months(n=6):
    """최근 n개월의 YYYYMM 리스트 반환"""
    months = []
    today = datetime.today()
    for i in range(n):
        date = today - timedelta(days=30 * i)
        months.append(date.strftime('%Y%m'))
    return list(set(months))


def fetch_apartment_data(region_code, deal_ym):
    """특정 지역/월의 아파트 거래 데이터 조회"""
    params = {
        'serviceKey': API_KEY,
        'LAWD_CD': region_code,
        'DEAL_YMD': deal_ym,
        'pageNo': '1',
        'numOfRows': '1000'
    }
    
    try:
        response = requests.get(BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        return parse_xml_response(response.text, region_code)
    except Exception as e:
        print(f"Error fetching {region_code} {deal_ym}: {e}")
        return []


def parse_xml_response(xml_text, region_code):
    """XML 응답 파싱"""
    items = []
    try:
        root = ET.fromstring(xml_text)
        for item in root.findall('.//item'):
            apt_name = get_text(item, 'aptNm', '')
            area = float(get_text(item, 'excluUseAr', '0'))
            price_str = get_text(item, 'dealAmount', '0').replace(',', '').strip()
            
            if area < MIN_AREA:
                continue
            
            try:
                price = int(price_str)
            except ValueError:
                continue
            
            price_per_pyeong = (price / area) * 3.3 if area > 0 else 0
            
            sido, sigungu = REGIONS.get(region_code, ('', ''))
            
            items.append({
                'apt_name': apt_name,
                'sido': sido,
                'sigungu': sigungu,
                'dong': get_text(item, 'umdNm', ''),
                'area_m2': area,
                'area_pyeong': round(area / 3.3, 1),
                'price': price,
                'price_per_pyeong': round(price_per_pyeong),
                'deal_year': get_text(item, 'dealYear', ''),
                'deal_month': get_text(item, 'dealMonth', ''),
                'deal_day': get_text(item, 'dealDay', ''),
                'floor': get_text(item, 'floor', ''),
                'build_year': get_text(item, 'buildYear', '')
            })
    except ET.ParseError as e:
        print(f"XML Parse Error: {e}")
    
    return items


def get_text(element, tag, default=''):
    """XML 요소에서 텍스트 추출"""
    child = element.find(tag)
    return child.text.strip() if child is not None and child.text else default


def format_price_billion(price_manwon):
    """만원 단위를 억 단위로 변환"""
    billion = price_manwon / 10000
    if billion >= 1:
        if billion == int(billion):
            return f"{int(billion)}억"
        else:
            return f"{billion:.1f}억"
    else:
        return f"{price_manwon:,}만"


def format_price_per_pyeong(price):
    """평당가 포맷"""
    billion = price // 10000
    remainder = price % 10000
    if billion > 0:
        return f"{billion}억 {remainder:,}만"
    else:
        return f"{price:,}만"


def get_top_20_by_complex(all_data):
    """단지별 최고가만 추출 후 TOP 20 반환"""
    complex_best = defaultdict(lambda: None)
    
    for item in all_data:
        key = (item['apt_name'], item['sido'], item['sigungu'])
        if complex_best[key] is None or item['price_per_pyeong'] > complex_best[key]['price_per_pyeong']:
            complex_best[key] = item
    
    sorted_list = sorted(complex_best.values(), key=lambda x: x['price_per_pyeong'], reverse=True)
    
    return sorted_list[:20]


def generate_html(top_20, google_maps_api_key):
    """HTML 파일 생성"""
    update_time = datetime.now().strftime('%Y.%m.%d %H:%M')
    
    rows_html = ""
    for i, item in enumerate(top_20, 1):
        deal_date = f"{item['deal_year']}.{item['deal_month'].zfill(2)}.{item['deal_day'].zfill(2)}"
        location = f"{item['sido']} {item['sigungu']}"
        map_query = f"{item['apt_name']}+{item['sido']}+{item['sigungu']}+{item['dong']}"
        
        rows_html += f"""
        <tr class="main-row" onclick="toggleDetail({i})">
            <td>{i}</td>
            <td class="apt-name">{item['apt_name']} <span class="arrow" id="arrow-{i}">▼</span></td>
            <td>{location}</td>
            <td class="price">{format_price_per_pyeong(item['price_per_pyeong'])}</td>
        </tr>
        <tr class="detail-row" id="detail-{i}">
            <td colspan="4">
                <div class="detail-content">
                    <div class="detail-info">
                        <table class="detail-table">
                            <tr><th>동</th><td>{item['dong']}</td></tr>
                            <tr><th>전용면적</th><td>{item['area_m2']}㎡ ({item['area_pyeong']}평)</td></tr>
                            <tr><th>거래금액</th><td>{format_price_billion(item['price'])}</td></tr>
                            <tr><th>거래일</th><td>{deal_date}</td></tr>
                            <tr><th>층</th><td>{item['floor']}층</td></tr>
                            <tr><th>건축년도</th><td>{item['build_year']}년</td></tr>
                        </table>
                    </div>
                    <div class="detail-map">
                        <iframe
                            width="300"
                            height="200"
                            style="border:0; border-radius: 8px;"
                            loading="lazy"
                            allowfullscreen
                            referrerpolicy="no-referrer-when-downgrade"
                            src="https://www.google.com/maps/embed/v1/place?key={google_maps_api_key}&q={map_query}&zoom=15">
                        </iframe>
                    </div>
                </div>
            </td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>전국 아파트 평당가 TOP 20</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Noto Sans KR', sans-serif;
            background-color: #000000;
            color: #ffffff;
            min-height: 100vh;
            padding: 40px 20px;
        }}
        
        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}
        
        h1 {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 8px;
            letter-spacing: -0.5px;
        }}
        
        .subtitle {{
            color: #888888;
            font-size: 0.9rem;
            margin-bottom: 30px;
        }}
        
        table.main-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        
        table.main-table thead th {{
            text-align: left;
            padding: 16px 12px;
            border-bottom: 2px solid #333333;
            font-weight: 500;
            color: #aaaaaa;
            font-size: 0.85rem;
        }}
        
        table.main-table thead th:last-child {{
            text-align: right;
        }}
        
        .main-row {{
            cursor: pointer;
            transition: background-color 0.2s ease;
        }}
        
        .main-row:hover {{
            background-color: #1a1a1a;
        }}
        
        .main-row td {{
            padding: 18px 12px;
            border-bottom: 1px solid #222222;
            font-size: 1rem;
        }}
        
        .main-row td:first-child {{
            font-weight: 700;
            color: #666666;
            width: 50px;
        }}
        
        .apt-name {{
            font-weight: 500;
        }}
        
        .arrow {{
            color: #555555;
            font-size: 0.75rem;
            margin-left: 8px;
            transition: transform 0.2s ease;
            display: inline-block;
        }}
        
        .arrow.open {{
            transform: rotate(180deg);
        }}
        
        .price {{
            text-align: right;
            font-weight: 700;
            color: #00d4aa;
            font-variant-numeric: tabular-nums;
        }}
        
        .detail-row {{
            display: none;
        }}
        
        .detail-row.show {{
            display: table-row;
        }}
        
        .detail-row td {{
            padding: 0;
            background-color: #0d0d0d;
            border-bottom: 1px solid #222222;
        }}
        
        .detail-content {{
            padding: 20px 12px 20px 50px;
            display: flex;
            gap: 30px;
            align-items: flex-start;
        }}
        
        .detail-info {{
            flex: 1;
        }}
        
        .detail-map {{
            flex-shrink: 0;
        }}
        
        .detail-table {{
            width: 100%;
            max-width: 350px;
        }}
        
        .detail-table tr {{
            border: none;
        }}
        
        .detail-table th {{
            text-align: left;
            padding: 8px 20px 8px 0;
            color: #666666;
            font-weight: 400;
            font-size: 0.9rem;
            width: 100px;
        }}
        
        .detail-table td {{
            padding: 8px 0;
            font-size: 0.95rem;
            color: #cccccc;
        }}
        
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #222222;
            color: #555555;
            font-size: 0.8rem;
            text-align: center;
        }}
        
        @media (max-width: 768px) {{
            body {{
                padding: 20px 15px;
            }}
            
            h1 {{
                font-size: 1.5rem;
            }}
            
            table.main-table thead th,
            .main-row td {{
                padding: 12px 8px;
                font-size: 0.9rem;
            }}
            
            .detail-content {{
                flex-direction: column;
                padding: 15px 8px 15px 30px;
                gap: 20px;
            }}
            
            .detail-map iframe {{
                width: 100%;
                max-width: 300px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>전국 아파트 평당가 TOP 20 <span style="font-weight: 400; font-size: 1rem; color: #888;">(전용면적 기준)</span></h1>
        <p class="subtitle">최근 6개월 실거래 기준 · 단지별 최고가</p>
        
        <table class="main-table">
            <thead>
                <tr>
                    <th>순위</th>
                    <th>단지명</th>
                    <th>지역</th>
                    <th style="text-align: right;">평당가</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        
        <div class="footer">
            마지막 업데이트: {update_time} · 데이터 출처: 국토교통부 실거래가 공개시스템
        </div>
    </div>
    
    <script>
        function toggleDetail(id) {{
            const detailRow = document.getElementById('detail-' + id);
            const arrow = document.getElementById('arrow-' + id);
            
            detailRow.classList.toggle('show');
            arrow.classList.toggle('open');
        }}
    </script>
</body>
</html>"""
    
    return html


def main():
    print("전국 아파트 평당가 TOP 20 데이터 수집 시작...")
    
    all_data = []
    months = get_recent_months(6)
    total_regions = len(REGIONS)
    
    print(f"수집 기간: {months}")
    print(f"전체 지역 수: {total_regions}")
    
    for idx, (region_code, (sido, sigungu)) in enumerate(REGIONS.items(), 1):
        for month in months:
            print(f"  [{idx}/{total_regions}] {sido} {sigungu} {month} 조회 중...")
            data = fetch_apartment_data(region_code, month)
            all_data.extend(data)
        
        # API 호출 제한 방지를 위한 딜레이
        if idx % 10 == 0:
            time.sleep(1)
    
    print(f"\n총 {len(all_data)}건 수집 완료")
    
    top_20 = get_top_20_by_complex(all_data)
    
    print("\n=== TOP 20 ===")
    for i, item in enumerate(top_20, 1):
        print(f"{i}. {item['apt_name']} ({item['sido']} {item['sigungu']}) - {format_price_per_pyeong(item['price_per_pyeong'])}")
    
    html = generate_html(top_20, GOOGLE_MAPS_API_KEY)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("\n✅ index.html 생성 완료!")


if __name__ == '__main__':
    main()
