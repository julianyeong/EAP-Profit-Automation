"""
데이터 크롤링 모듈
Amaranth 그룹웨어에서 종결된 매출/매입 품의서 데이터를 추출합니다.
"""

import time
import re
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any
import pandas as pd
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def navigate_to_handover_document_list(driver):
    """
    1. '전자결재' 메뉴 클릭
    2. '인수인계문서' 서브 메뉴 클릭을 통해 최종 목적지로 이동합니다.
    """
    
    # 1. '전자결재' 메뉴 클릭 (페이지 이동)
    logger.info("1단계: 🔍 '전자결재' 메뉴 클릭 시도 중...")
    try:
        # 가장 안정적인 텍스트 기반 XPath 사용
        XPATH_ELECTRONIC_APPROVAL = "//span[text()='전자결재']"
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_ELECTRONIC_APPROVAL))
        ).click()
        
        logger.info("✅ '전자결재' 메뉴 클릭 성공. 페이지 로딩 대기 중...")
        
    except TimeoutException:
        logger.error("❌ 1단계: '전자결재' 메뉴를 찾거나 클릭할 수 없습니다. (Timeout)")
        return False
    except Exception as e:
        logger.error(f"❌ 1단계: 예상치 못한 오류 발생: {e}")
        return False
    
    # --- 페이지 이동 후 로딩 대기 및 2단계 클릭 시작 ---

    # 2. '인수인계문서' 서브 메뉴 클릭
    logger.info("2단계: 🔍 '인수인계문서' 서브 메뉴 클릭 시도 중...")
    try:
        # 1. 페이지 로딩 대기: 새로운 페이지에서 고유한 요소(ul class="dep1" 등)가 나타날 때까지 기다립니다.
        # (2단계 요소의 부모 요소인 ul.dep1이 나타날 때까지 기다리는 것이 일반적입니다.)
        XPATH_APPROVAL_CONTENT_AREA = "//ul[@class='dep1']"
        WebDriverWait(driver, 15).until(
             EC.presence_of_element_located((By.XPATH, XPATH_APPROVAL_CONTENT_AREA))
        )
        logger.info("✅ 전자결재 페이지 내부 요소 로딩 완료 확인.")
        
        # 2. 서브 메뉴 클릭: ID 기반 XPath 사용 (가장 안정적)
        ID_HANDOVER_DOCUMENT = "UBA5020_UBA"
        
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, ID_HANDOVER_DOCUMENT)) # By.ID 사용
        ).click()
        
        logger.info("✅ '인수인계문서' 서브 메뉴 클릭 성공.")
        
        # 최종 목록이 로드되는 것을 확인하는 추가 대기 로직이 필요할 수 있습니다.
        # 예: WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "document_list_table")))
        
        return True
    
    except TimeoutException:
        logger.error("❌ 2단계: '인수인계문서' 서브 메뉴를 찾거나 클릭할 수 없습니다. (Timeout)")
        return False
    except Exception as e:
        logger.error(f"❌ 2단계: 예상치 못한 오류 발생: {e}")
        return False

def get_last_12_months():
    """
    최근 12개월의 시작일과 종료일을 반환합니다.
    
    Returns:
        Tuple[str, str]: (시작일, 종료일) YYYY-MM-DD 형식
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)  # 약 12개월 전
    
    return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")

def parse_date_range(start_date_str: str, end_date_str: str) -> Tuple[str, str]:
    """
    사용자 입력 날짜를 파싱하고 유효성을 검증합니다.
    
    Args:
        start_date_str (str): 시작 날짜 (YYYY-MM-DD)
        end_date_str (str): 종료 날짜 (YYYY-MM-DD)
        
    Returns:
        Tuple[str, str]: (시작일, 종료일) YYYY-MM-DD 형식
        
    Raises:
        ValueError: 날짜 형식이 잘못된 경우
    """
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if start_date > end_date:
            raise ValueError("시작 날짜가 종료 날짜보다 늦습니다")
        
        if end_date > datetime.now():
            raise ValueError("종료 날짜가 현재 날짜보다 늦습니다")
            
        return start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d")
        
    except ValueError as e:
        if "time data" in str(e):
            raise ValueError("날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식을 사용하세요")
        raise

def extract_completed_documents(driver, start_date: str, end_date: str, doc_keyword: str) -> List[Dict[str, Any]]:
    """
    종결된 품의서에서 특정 키워드가 포함된 문서들을 추출합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)
        doc_keyword (str): 문서 제목에 포함될 키워드 ('매출' 또는 '매입')
        
    Returns:
        List[Dict[str, Any]]: 추출된 문서 데이터 리스트
    """
    documents = []
    
    try:
        logger.info(f"📄 '{doc_keyword}' 키워드 문서 추출 중...")
        
        # 페이지 소스 가져오기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 품의서 목록 테이블 또는 리스트 찾기
        # 실제 그룹웨어 구조에 맞게 수정 필요
        table_selectors = [
            "table.tbl-list",
            "table.approval-list", 
            ".document-list table",
            ".list-table",
            "table"
        ]
        
        table = None
        for selector in table_selectors:
            table = soup.select_one(selector)
            if table:
                break
        
        if not table:
            logger.warning("⚠️ 품의서 목록 테이블을 찾을 수 없습니다")
            return documents
        
        # 테이블 행들 추출
        rows = table.find_all('tr')[1:]  # 헤더 제외
        
        for row in rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 4:  # 최소 필요한 컬럼 수
                    continue
                
                # 각 셀에서 데이터 추출 (실제 그룹웨어 구조에 맞게 수정)
                document_data = {}
                
                # 문서 제목 추출
                title_cell = cells[1] if len(cells) > 1 else cells[0]
                title_link = title_cell.find('a')
                title = title_link.get_text(strip=True) if title_link else title_cell.get_text(strip=True)
                
                # 키워드 필터링
                if doc_keyword not in title:
                    continue
                
                # 상태 확인 (종결된 문서만)
                status_cell = cells[2] if len(cells) > 2 else cells[1]
                status = status_cell.get_text(strip=True)
                if '종결' not in status and '완료' not in status:
                    continue
                
                # 날짜 추출
                date_cell = cells[3] if len(cells) > 3 else cells[2]
                date_text = date_cell.get_text(strip=True)
                
                # 날짜 파싱 및 필터링
                try:
                    doc_date = parse_date_from_text(date_text)
                    if not is_date_in_range(doc_date, start_date, end_date):
                        continue
                except:
                    continue
                
                # 공급가액 추출 (금액이 포함된 셀 찾기)
                amount = 0
                for cell in cells:
                    cell_text = cell.get_text(strip=True)
                    amount_match = re.search(r'[\d,]+', cell_text.replace(',', ''))
                    if amount_match:
                        try:
                            amount = int(amount_match.group().replace(',', ''))
                            break
                        except ValueError:
                            continue
                
                if amount == 0:
                    continue
                
                # 문서 타입 결정
                doc_type = '매출' if '매출' in title else '매입'
                
                document_data = {
                    '날짜': doc_date.strftime('%Y-%m-%d'),
                    '문서제목': title,
                    '구분': doc_type,
                    '공급가액': amount
                }
                
                documents.append(document_data)
                logger.debug(f"✅ 문서 추출: {title} - {amount:,}원")
                
            except Exception as e:
                logger.warning(f"⚠️ 행 처리 중 오류: {e}")
                continue
        
        logger.info(f"✅ '{doc_keyword}' 키워드 문서 {len(documents)}건 추출 완료")
        
    except Exception as e:
        logger.error(f"❌ 문서 추출 중 오류: {e}")
    
    return documents

def parse_date_from_text(date_text: str) -> datetime:
    """
    텍스트에서 날짜를 파싱합니다.
    
    Args:
        date_text (str): 날짜가 포함된 텍스트
        
    Returns:
        datetime: 파싱된 날짜
    """
    # 다양한 날짜 형식 지원
    date_patterns = [
        r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})',  # YYYY-MM-DD, YYYY.MM.DD
        r'(\d{4})/(\d{1,2})/(\d{1,2})',        # YYYY/MM/DD
        r'(\d{1,2})[.-](\d{1,2})[.-](\d{4})',  # MM-DD-YYYY, MM.DD.YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, date_text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    if len(groups[0]) == 4:  # YYYY-MM-DD 형식
                        year, month, day = groups
                    else:  # MM-DD-YYYY 형식
                        month, day, year = groups
                    
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
    
    # 기본값으로 현재 날짜 반환
    return datetime.now()

def is_date_in_range(date: datetime, start_date: str, end_date: str) -> bool:
    """
    날짜가 지정된 범위 내에 있는지 확인합니다.
    
    Args:
        date (datetime): 확인할 날짜
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)
        
    Returns:
        bool: 범위 내 여부
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
        end = datetime.strptime(end_date, "%Y-%m-%d")
        return start <= date <= end
    except ValueError:
        return False

def crawl_all_data(driver, start_date: str, end_date: str) -> pd.DataFrame:
    """
    모든 매출/매입 데이터를 크롤링하여 DataFrame으로 반환합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)
        
    Returns:
        pd.DataFrame: 추출된 데이터 (컬럼: ['날짜', '문서제목', '구분', '공급가액'])
    """
    try:
        logger.info("🚀 전체 데이터 크롤링 시작")
        
        # 품의서 목록 페이지로 이동
        if not navigate_to_approval_list(driver):
            logger.error("❌ 품의서 목록 페이지 이동 실패")
            return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])
        
        all_documents = []
        
        # 매출 문서 추출
        logger.info("💰 매출 문서 추출 중...")
        sales_docs = extract_completed_documents(driver, start_date, end_date, '매출')
        all_documents.extend(sales_docs)
        
        # 매입 문서 추출
        logger.info("💸 매입 문서 추출 중...")
        purchase_docs = extract_completed_documents(driver, start_date, end_date, '매입')
        all_documents.extend(purchase_docs)
        
        # DataFrame 생성
        if all_documents:
            df = pd.DataFrame(all_documents)
            df['날짜'] = pd.to_datetime(df['날짜'])
            df = df.sort_values('날짜')
            logger.info(f"✅ 총 {len(df)}건의 데이터 크롤링 완료")
        else:
            df = pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])
            logger.warning("⚠️ 추출된 데이터가 없습니다")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ 데이터 크롤링 중 오류: {e}")
        return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])

