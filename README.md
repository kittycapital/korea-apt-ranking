# 전국 아파트 평당가 TOP 20

최근 6개월간 전국 아파트 실거래 데이터 기반 평당가 랭킹 대시보드

## 미리보기

- 검정 배경 + 흰색 텍스트
- 단지명 클릭 시 상세 정보 + Google Maps 표시
- 전용면적 기준 평당가 산정

## 설정 방법

### 1. 국토교통부 API 키 발급

1. [data.go.kr](https://www.data.go.kr) 회원가입
2. "아파트 매매 실거래" 검색
3. **국토교통부_아파트 매매 실거래가 자료** 활용신청
4. 마이페이지 → 인증키 복사

### 2. Google Maps API 키 발급

1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. 새 프로젝트 생성
3. APIs & Services → Library → "Maps Embed API" 활성화
4. APIs & Services → Credentials → Create API Key
5. (권장) API 키 제한: HTTP referrers → `https://[username].github.io/*`

### 3. GitHub 설정

1. 이 저장소를 Fork 또는 새로 생성
2. Settings → Secrets and variables → Actions
3. 두 개의 Secret 추가:
   - `MOLIT_API_KEY`: 국토교통부 API 키
   - `GOOGLE_MAPS_API_KEY`: Google Maps API 키

### 4. GitHub Pages 활성화

1. Settings → Pages
2. Source: Deploy from a branch
3. Branch: `main` / `root`
4. Save

### 5. 자동 업데이트

- 매일 오전 7시 (KST) 자동 실행
- Actions 탭에서 수동 실행도 가능

## 파일 구조

```
├── fetch_data.py          # 데이터 수집 및 HTML 생성
├── index.html             # 결과 HTML (GitHub Pages용)
├── .github/
│   └── workflows/
│       └── update.yml     # GitHub Actions 워크플로우
└── README.md
```

## 데이터 사양

| 항목 | 값 |
|------|-----|
| 기간 | 최근 6개월 |
| 지역 | 전국 (17개 시도) |
| 면적필터 | 전용 59㎡ 이상 |
| 중복처리 | 단지별 최고가만 |
| 가격기준 | 전용면적 기준 평당가 |

## 포함 지역

- 서울특별시 (25개 구)
- 부산광역시 (16개 구/군)
- 대구광역시 (9개 구/군)
- 인천광역시 (10개 구/군)
- 광주광역시 (5개 구)
- 대전광역시 (5개 구)
- 울산광역시 (5개 구/군)
- 세종특별자치시
- 경기도 (31개 시/군)
- 강원특별자치도 (18개 시/군)
- 충청북도 (14개 시/군)
- 충청남도 (16개 시/군)
- 전북특별자치도 (15개 시/군)
- 전라남도 (22개 시/군)
- 경상북도 (23개 시/군)
- 경상남도 (22개 시/군)
- 제주특별자치도 (2개 시)

## 데이터 출처

국토교통부 실거래가 공개시스템 (rt.molit.go.kr)
