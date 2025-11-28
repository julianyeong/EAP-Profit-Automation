# 영업 부서 매출/매입 현황 자동화 시스템

Amaranth 그룹웨어에서 종결된 매출 및 매입 품의서 데이터를 자동 추출하여 월별 손익 분석을 수행하는 시스템입니다.

## 🎯 주요 기능

- **자동 데이터 추출**: 그룹웨어에서 종결된 매출/매입 품의서 자동 수집
- **월별 손익 분석**: 매출액, 매입액, 손익을 지정 기간 별 집계 및 분석
- **유연한 날짜 범위**: 사용자 지정 기간

## 📋 시스템 요구사항

- Python 3.8 이상
- Chrome 브라우저
- Amaranth 그룹웨어 접근 권한

## 🚀 설치 및 설정

### 1. 프로젝트 클론 및 의존성 설치

```bash
# 프로젝트 디렉토리로 이동
cd inno_profit

# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 그룹웨어 정보를 입력하세요:

```bash
# .env 파일 생성
cp .env.example .env
```

`.env` 파일 내용:
```env
GROUPWARE_URL=https://your-groupware-url.com
GROUPWARE_ID=your_username
GROUPWARE_PW=your_password
```

## 📖 사용법

### 기본 사용법 (최근 12개월 데이터)

```bash
python main.py
```

### 전체 옵션

```bash
python main.py --help
```

## 📊 출력 파일

`output/` 디렉토리에 다음 형식으로 Excel 파일이 생성됩니다:

- **파일명**: `매출매입현황_YYYYMMDD_HHMMSS.xlsx`
- **시트 구성**:
  1. **월별요약**: 월별 매출액, 매입액, 손익 요약
  2. **상세내역**: 개별 거래 내역 상세 정보
  3. **손익분석**: 누적 손익, 수익률, 증감률 분석

## 🔧 설정 및 커스터마이징

### 그룹웨어 구조에 맞는 수정

실제 그룹웨어의 HTML 구조에 따라 다음 파일들을 수정해야 할 수 있습니다:

1. **`modules/web_setup.py`**: 로그인 필드 ID 및 버튼 선택자
2. **`modules/data_crawler.py`**: 품의서 목록 테이블 선택자 및 데이터 추출 로직

### 주요 설정 포인트

```python
# web_setup.py - 로그인 필드 ID
id_field = driver.find_element(By.ID, "login_id")  # 실제 ID로 변경
pw_field = driver.find_element(By.ID, "login_pw")  # 실제 ID로 변경

# data_crawler.py - 품의서 목록 테이블 선택자
table_selectors = [
    "table.tbl-list",           # 실제 클래스명으로 변경
    "table.approval-list",      # 실제 클래스명으로 변경
    # ... 기타 선택자들
]
```

## 🛡️ 보안 고려사항

- **인증 정보 보호**: `.env` 파일을 `.gitignore`에 추가하여 버전 관리에서 제외
- **로그 보안**: 로그에 민감한 정보가 포함되지 않도록 주의
- **네트워크 보안**: VPN 또는 안전한 네트워크에서 실행 권장

## 🐛 문제 해결

### 일반적인 문제들

1. **WebDriver 오류**
   ```
   해결방법: Chrome 브라우저가 최신 버전인지 확인
   ```

2. **로그인 실패**
   ```
   해결방법: 그룹웨어 URL, ID, PW 확인 및 로그인 필드 ID 수정
   ```

3. **데이터 추출 실패**
   ```
   해결방법: 품의서 목록 페이지 구조 확인 및 선택자 수정
   ```

### 디버깅 모드

headless 모드를 비활성화하여 브라우저 동작을 확인할 수 있습니다:

```python
# modules/web_setup.py
chrome_options.add_argument('--headless')  # 이 줄을 주석 처리
```

## 📝 로그 확인

시스템 실행 중 상세한 로그를 확인하려면:

```bash
python main.py 2>&1 | tee execution.log
```

## 🤝 기여하기

1. 이슈 리포트: 버그나 개선사항을 이슈로 등록
2. 풀 리퀘스트: 코드 개선사항 제출
3. 문서화: 사용법이나 설정 가이드 개선

## 📄 라이선스

이 프로젝트는 내부 사용을 위한 것입니다.

## 📞 지원

기술적 문제나 문의사항이 있으시면 개발팀에 연락하세요.

---

**주의**: 이 시스템은 Amaranth 그룹웨어의 특정 구조에 맞춰 개발되었습니다. 다른 그룹웨어 사용 시 HTML 선택자 및 로그인 로직을 수정해야 할 수 있습니다.


