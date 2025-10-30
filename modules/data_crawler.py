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
from selenium.webdriver import ActionChains
import logging

logger = logging.getLogger(__name__)

def _clean_amount(text: str) -> int:
    """
    금액 문자열을 정수로 변환합니다.
    (쉼표 제거 및 숫자만 추출)
    """
    if not text:
        return 0
    
    # 숫자(0-9)와 쉼표(,)를 제외한 모든 문자를 제거하고 쉼표를 제거
    cleaned = re.sub(r'[^\d,]', '', text).replace(',', '')
    
    try:
        return int(cleaned)
    except ValueError:
        # 변환 실패 시 0 반환 (데이터 오류 방지)
        return 0

def _clean_text(text: str) -> str:
    """ 텍스트에서 공백, 줄바꿈, 특수 공백을 제거하고 모두 소문자로 변환합니다. """
    if not text:
        return ""
    # 모든 종류의 공백 문자(줄바꿈, 탭, 일반 공백, nbsp 등) 제거
    cleaned = re.sub(r'\s+', '', text.strip()).lower()
    return cleaned

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

    logger.info("2단계: 🔍 '인수인계' 메뉴 확장 및 '인수인계문서' 클릭 시도 중...")
    try:
        # 1. 페이지 로딩 대기: 새로운 페이지에서 고유한 요소가 나타날 때까지 기다립니다.
        XPATH_APPROVAL_CONTENT_AREA = "//div[@id='sideLnb']"
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, XPATH_APPROVAL_CONTENT_AREA))
        )
        logger.info("✅ 전자결재 페이지 내부 요소 로딩 완료 확인.")
        
        # 추가 안정화 시간
        time.sleep(2)
        
        # 2. '인수인계' 상위 메뉴 찾기 및 클릭 (하위 메뉴 펼치기)
        XPATH_HANDOVER_PARENT_MENU = "//span[text()='인수인계']"
        
        logger.info("🔍 '인수인계' 상위 메뉴 탐색 중...")
        handover_parent = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, XPATH_HANDOVER_PARENT_MENU))
        )
        logger.info("✅ '인수인계' 상위 메뉴 요소 발견")
        
        # 요소가 보이도록 스크롤
        logger.info("📜 요소가 보이도록 스크롤 중...")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", handover_parent)
        time.sleep(1)
        
        # 클릭 가능할 때까지 대기
        logger.info("⏳ 요소가 클릭 가능할 때까지 대기 중...")
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_HANDOVER_PARENT_MENU))
        )
        
        # 클릭 시도 (여러 방법)
        click_success = False
        
        # 방법 1: 일반 클릭
        try:
            logger.info("🖱️ 방법 1: 일반 클릭 시도...")
            handover_parent.click()
            logger.info("✅ '인수인계' 상위 메뉴 클릭 성공 (일반 클릭)")
            click_success = True
        except Exception as e:
            logger.warning(f"⚠️ 일반 클릭 실패: {e}")
        
        # 방법 2: JavaScript 클릭
        if not click_success:
            try:
                logger.info("🖱️ 방법 2: JavaScript 클릭 시도...")
                driver.execute_script("arguments[0].click();", handover_parent)
                logger.info("✅ '인수인계' 상위 메뉴 클릭 성공 (JavaScript 클릭)")
                click_success = True
            except Exception as e:
                logger.warning(f"⚠️ JavaScript 클릭 실패: {e}")
        
        if not click_success:
            logger.error("❌ 모든 클릭 방법 실패")
            return False
        
        # 하위 메뉴가 펼쳐질 때까지 대기
        logger.info("⏳ 하위 메뉴 펼쳐짐 대기 중...")
        time.sleep(2)
        
        # 3. '인수인계문서' 서브 메뉴 클릭
        XPATH_HANDOVER_DOCUMENT = "//span[text()='인수인계문서']"
        
        logger.info("🔍 '인수인계문서' 서브 메뉴 탐색 중...")
        handover_doc = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_HANDOVER_DOCUMENT))
        )
        logger.info("✅ '인수인계문서' 서브 메뉴 요소 발견")
        
        # 요소가 보이도록 스크롤
        logger.info("📜 요소가 보이도록 스크롤 중...")
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", handover_doc)
        time.sleep(1)
        
        # 클릭 시도 (여러 방법)
        click_success = False
        
        # 방법 1: 일반 클릭
        try:
            logger.info("🖱️ 방법 1: 일반 클릭 시도...")
            handover_doc.click()
            logger.info("✅ '인수인계문서' 서브 메뉴 클릭 성공 (일반 클릭)")
            click_success = True
        except Exception as e:
            logger.warning(f"⚠️ 일반 클릭 실패: {e}")
        
        # 방법 2: JavaScript 클릭
        if not click_success:
            try:
                logger.info("🖱️ 방법 2: JavaScript 클릭 시도...")
                driver.execute_script("arguments[0].click();", handover_doc)
                logger.info("✅ '인수인계문서' 서브 메뉴 클릭 성공 (JavaScript 클릭)")
                click_success = True
            except Exception as e:
                logger.warning(f"⚠️ JavaScript 클릭 실패: {e}")
        
        if not click_success:
            logger.error("❌ 모든 클릭 방법 실패")
            return False
        
        # 최종 페이지 로딩 대기
        logger.info("⏳ 인수인계문서 목록 페이지 로딩 대기 중...")
        time.sleep(3)
        
        logger.info("✅✅✅ '인수인계문서' 목록 페이지 이동 완료 ✅✅✅")
        return True
    
    except TimeoutException as te:
        logger.error(f"❌ 2단계: 타임아웃 오류 - {te}")
        # 디버깅을 위한 스크린샷 저장
        try:
            driver.save_screenshot("debug_timeout_error.png")
            logger.info("💾 디버깅용 스크린샷 저장: debug_timeout_error.png")
        except:
            pass
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

def extract_document_list(driver, start_date: str, end_date: str, doc_keyword: str) -> List[Dict[str, Any]]:
    """
    목록 페이지에서 특정 키워드가 포함된 문서들의 링크를 추출합니다.
    (특정 목록 컨테이너 내부 스크롤 로직 적용)
    """
    documents = []
    
    try:
        logger.info(f"📄 '{doc_keyword}' 키워드 문서 목록 추출 중...")
        
        # 1. 스크롤 대상 요소 찾기 (인라인 스타일 속성을 이용한 정확한 탐색)
        # CSS Selector: style 속성에 'overflow: scroll'을 포함하는 모든 DIV
        SCROLL_CONTAINER_CSS = "div[style*='overflow: scroll']"
        
        try:
            # 10초 대기하여 스크롤 가능한 요소 확보
            scrollable_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, SCROLL_CONTAINER_CSS))
            )
            logger.info("✅ 스크롤 대상 요소 (style*='overflow: scroll') 찾기 성공")
        except TimeoutException:
            logger.error("❌ 스크롤 대상 컨테이너를 찾지 못했습니다. 목록 영역이 로드되지 않았을 수 있습니다.")
            return documents
        
        # 2. 반복 스크롤 로직 실행 (전체 목록 로드를 보장)
        last_height = 0 
        max_attempts = 15 # 충분한 시도 횟수

        for i in range(max_attempts):
            logger.info(f"📜 [{i+1}차 스크롤] 목록 최하단으로 스크롤 중...")
            
            # 스크롤 명령 실행 (요소 내부 스크롤을 최하단으로)
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_element)
            time.sleep(3) # 데이터 로딩 및 안정화 대기
            
            # 새 높이 가져오기
            new_height = driver.execute_script("return arguments[0].scrollHeight", scrollable_element)
            
            # 스크롤 높이가 변하지 않으면 종료
            if new_height == last_height:
                logger.info("✅ 더 이상 새로운 행이 로드되지 않아 스크롤 종료.")
                break 
                
            last_height = new_height
            
        logger.info(f"✅ 반복 스크롤 완료.")
        
        # 2. HTML 소스 가져오기 및 BeautifulSoup 파싱
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # [UL 컨테이너 탐색]
        document_list_container = soup.select_one('ul.tableBody') 
        
        if not document_list_container:
            logger.warning("⚠️ 품의서 목록 컨테이너 (ul.tableBody)를 찾을 수 없습니다")
            return documents

        # 2. LI 행들 추출
        rows = document_list_container.find_all('li', recursive=False) 
        logger.info(f"📊 총 {len(rows)}개의 행을 찾았습니다.")

        for idx, row in enumerate(rows, 1):
            try:
                # 1. 문서 제목 추출
                title_element = row.select_one('.titDiv .title span')
                if not title_element:
                    title_element = row.select_one('.titDiv .title')
                    if not title_element: continue
                title = title_element.get_text(strip=True)
                
                # 2. 문서번호/링크 추출
                info_links_container = row.select_one('.infoDiv .h-box')
                if not info_links_container: continue

                info_links = info_links_container.find_all('div', class_=lambda x: x and 'txt' in x and 'infoLink' in x)
                if len(info_links) < 2: continue

                link_text_element = info_links[1] 
                link_href = link_text_element.get_text(strip=True) # 품의번호 텍스트

                # 3. 기안일, 상태 확인 및 필터링 (생략된 로직)
                date_text = row.select_one('.dateText').get_text(strip=True)
                status = row.select_one('.process .ellipsis2').get_text(strip=True)
                
                if '종결' not in status and '완료' not in status: continue
                
                # NOTE: parse_date_from_text, is_date_in_range 함수는 외부에서 정의되었다고 가정
                doc_date = parse_date_from_text(date_text)
                if not is_date_in_range(doc_date, start_date, end_date): continue
                
                # 4. 키워드 필터링 및 데이터 구조화
                if doc_keyword not in title: continue
                doc_type = '매출품의' if '매출품의' in title else '매입품의'

                document_data = {
                    '기안일': doc_date.strftime('%Y-%m-%d'),
                    '문서제목': title,
                    '링크': link_href, 
                    '구분': doc_type
                }
                
                documents.append(document_data)
                logger.debug(f"✅ 문서 링크 추출: {title} - {doc_date.strftime('%Y-%m-%d')}")
                
            except Exception as e:
                logger.warning(f"⚠️ [{idx}/{len(rows)}] 행 처리 중 오류: {e}")
                continue
        
        logger.info(f"✅ '{doc_keyword}' 키워드 문서 {len(documents)}건 추출 완료")
        
    except Exception as e:
        logger.error(f"❌ 문서 목록 추출 중 오류: {e}", exc_info=True)
    
    return documents

def _extract_purchase_details(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    매입품의 상세 페이지에서 재무 정보를 추출합니다.
    (배경색 스타일 속성을 가진 <td> 셀을 직접 탐색)
    """
    detail_data = {
        '거래처명': '',
        '공급가액': 0,
        '부가세': 0,
        '합계금액': 0
    }
    
    try:
        target_style = 'background:rgb(255, 241, 214)'
        sum_cells = soup.find_all(['td', 'th'], 
                                  style=lambda s: s and target_style in s)
        
        if len(sum_cells) < 3:
            logger.warning("⚠️ 특정 배경색 스타일을 가진 셀을 충분히 찾을 수 없습니다. (최소 3개 필요)")
            return detail_data

        # 💡 추출 목표: 합계금액, 부가세, 공급가액 (뒤에서 -1, -2, -3 인덱스)
        detail_data['합계금액'] = _clean_amount(sum_cells[-1].get_text(strip=True))
        detail_data['부가세'] = _clean_amount(sum_cells[-2].get_text(strip=True))
        detail_data['공급가액'] = _clean_amount(sum_cells[-3].get_text(strip=True))
        logger.info("✅ 매입품의 스타일 속성 기반 금액 추출 성공")
        
    except Exception as e:
        logger.error(f"❌ 매입품의 상세 정보 추출 중 오류: {e}")
        
    return detail_data

def _extract_sales_details_kakao(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    매출품의 카카오클라우드 상세 페이지에서 재무 정보를 추출합니다.
    ('합 계' 레이블을 찾아 9번째 셀에서 합계금액만 추출)
    """
    detail_data = {
        '거래처명': '',
        '공급가액': 0,
        '부가세': 0,
        '합계금액': 0
    }
    
    try:
        # '합 계' 텍스트를 포함하는 <tr> 찾기 (공백 정리하여 안정적으로 매칭)
        total_rows = soup.find_all('tr')
        total_row = None
        
        for row in total_rows:
            row_text = re.sub(r'\s+', '', row.get_text(strip=True))
            if '합계' in row_text and '합계' in re.sub(r'\s+', '', row.get_text(strip=True)):
                total_row = row
                break
        
        if not total_row:
            logger.warning("⚠️ '합 계' 행을 찾을 수 없습니다")
            return detail_data
        
        # 해당 행의 모든 셀 추출
        cells = total_row.find_all(['td', 'th'])
        
        if len(cells) >= 9:
            # 9번째 셀 (인덱스 8)에서 합계금액 추출
            detail_data['합계금액'] = _clean_amount(cells[8].get_text(strip=True))
            logger.info("✅ 카카오클라우드 합계금액 추출 성공")
        else:
            logger.warning(f"⚠️ 셀이 부족합니다. {len(cells)}개만 발견 (9개 필요)")
        
    except Exception as e:
        logger.error(f"❌ 카카오클라우드 상세 정보 추출 중 오류: {e}")
        
    return detail_data

def _extract_sales_details_general(soup: BeautifulSoup) -> Dict[str, Any]:
    """
    매출품의 일반 구조 상세 페이지에서 재무 정보를 추출합니다.
    (정제된 텍스트 레이블 기반으로 인접한 값 셀을 찾아 추출하는 최적화된 로직)
    """
    detail_data = {
        '거래처명': '',
        '공급가액': 0,
        '부가세': 0,
        '합계금액': 0
    }
    
    try:
        # 1. '발행금액' 텍스트를 포함하는 <tr> 행을 찾습니다. (행을 찾는 최초 필터링)
        # 이 행에는 '발행금액' 레이블이 포함되어 있으므로 이 행을 먼저 필터링합니다.
        target_row = None
        for row in soup.find_all('tr'):
             if '발행금액' in row.get_text():
                 target_row = row
                 break
        
        if not target_row:
            logger.warning("⚠️ '발행금액' 행(레이블)을 찾을 수 없습니다.")
            return detail_data

        logger.info("✅ '발행금액' 행 탐색 성공. 레이블 기반 값 추출 시작.")
        
        # 2. 행 내에서 레이블을 찾고 바로 옆 셀(Next Sibling)에서 값을 추출합니다.
        
        labels_to_find = {
            '공급가액': '공급가액',
            '부가세': '부가세',
            '합계금액': '합계금액'
        }
        
        # 행 내의 모든 셀을 반복하며 레이블을 찾습니다.
        for cell in target_row.find_all(['td', 'th']):
            cell_clean_text = _clean_text(cell.get_text())
            
            # 레이블을 찾았다면, 바로 다음 형제 셀에서 값을 추출합니다.
            if '공급가액' in cell_clean_text and detail_data['공급가액'] == 0:
                value_cell = cell.find_next_sibling(['td', 'th'])
                if value_cell:
                    detail_data['공급가액'] = _clean_amount(value_cell.get_text(strip=True))
                    logger.debug(f"✅ 공급가액 추출 완료: {detail_data['공급가액']}")

            elif '부가세' in cell_clean_text and detail_data['부가세'] == 0:
                value_cell = cell.find_next_sibling(['td', 'th'])
                if value_cell:
                    detail_data['부가세'] = _clean_amount(value_cell.get_text(strip=True))
                    logger.debug(f"✅ 부가세 추출 완료: {detail_data['부가세']}")
            
            elif '합계금액' in cell_clean_text and detail_data['합계금액'] == 0:
                value_cell = cell.find_next_sibling(['td', 'th'])
                if value_cell:
                    detail_data['합계금액'] = _clean_amount(value_cell.get_text(strip=True))
                    logger.debug(f"✅ 합계금액 추출 완료: {detail_data['합계금액']}")
                    
            # 모든 값을 찾았으면 종료 (옵션)
            if detail_data['공급가액'] != 0 and detail_data['부가세'] != 0 and detail_data['합계금액'] != 0:
                break
        
    except Exception as e:
        logger.error(f"❌ 매출품의(일반) 상세 정보 추출 중 오류: {e}")
        
    return detail_data

def extract_detail_amount(driver, document_type: str, document_title: str = '') -> Dict[str, Any]:
    """
    팝업 상세 페이지에서 재무 정보를 추출합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        document_type: 문서 종류 ('매출품의' 또는 '매입품의')
        document_title: 문서 제목 (카카오클라우드 분기를 위해 필요)
        
    Returns:
        Dict[str, Any]: 추출된 재무 정보 (거래처명, 공급가액, 부가세, 합계금액)
    """
    detail_data = {
        '거래처명': '',
        '공급가액': 0,
        '부가세': 0,
        '합계금액': 0
    }
    
    try:
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 분기 1: '매입품의'
        if document_type == '매입품의':
            logger.info("🔍 매입품의 추출 로직 실행")
            detail_data = _extract_purchase_details(soup)
        
        # 분기 2: '매출품의'
        elif document_type == '매출품의':
            logger.info("🔍 매출품의 추출 로직 실행")
            
            # Case 2-1: 카카오클라우드
            if '카카오클라우드' in document_title:
                logger.info("🔍 카카오클라우드 문서 감지")
                detail_data = _extract_sales_details_kakao(soup)
            # Case 2-2: 그 외 (일반 구조)
            else:
                logger.info("🔍 일반 매출품의 문서 감지")
                detail_data = _extract_sales_details_general(soup)
        
        # 분기되지 않은 경우
        else:
            logger.warning(f"⚠️ 알 수 없는 문서 종류: {document_type}")
            
        logger.info(f"✅ 상세 정보 추출 완료: {detail_data}")
        
    except Exception as e:
        logger.error(f"❌ 상세 정보 추출 중 오류: {e}")
        
    return detail_data

def close_popup(driver):
    """
    팝업을 닫습니다.
    (팝업은 driver.close()로 처리되므로 이 함수는 더 이상 사용되지 않습니다)
    """
    logger.info("🚪 팝업 닫기는 윈도우 컨텍스트 전환으로 처리됩니다")
    return True

def run_full_crawling(driver, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    전체 크롤링 파이프라인을 실행합니다.
    (팝업(새 창)이 열리는 환경을 고려하여 윈도우 핸들 전환 로직을 추가했습니다.)
    """
    all_data = []
    
    try:
        logger.info("🚀 전체 크롤링 시작")
        
        keywords = ['매출품의', '매입품의']
        
        for keyword in keywords:
            logger.info(f"📋 '{keyword}' 목록 추출 중...")
            
            # 1. 목록 페이지에서 문서 링크 추출
            document_list = extract_document_list(driver, start_date, end_date, keyword)
            
            if not document_list:
                logger.warning(f"⚠️ '{keyword}' 문서가 없습니다")
                continue
            
            logger.info(f"✅ '{keyword}' 문서 {len(document_list)}건 발견")
            
            # 2. 각 문서 링크를 순회하며 상세 정보 추출 (팝업 제어)
            for idx, doc in enumerate(document_list, 1):
                list_window = driver.current_window_handle # 현재(목록) 창 핸들 저장
                
                try:
                    logger.info(f"📄 [{idx}/{len(document_list)}] {doc['문서제목']} 처리 중...")
                    
                    # --- a. 문서 제목 요소 찾기 및 클릭하여 팝업 띄우기 ---
                    XPATH_DOC_TITLE = f"//span[text()=\"{doc['문서제목']}\"]" 
                    
                    title_span = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, XPATH_DOC_TITLE))
                    )
                    
                    # JavaScript 강제 클릭 (팝업을 띄우는 올바른 동작)
                    driver.execute_script("arguments[0].click();", title_span)
                    logger.info("✅ 문서 제목 클릭 성공. 팝업 로딩 대기 중...")
                    time.sleep(2) # 팝업 창이 완전히 뜨기를 위한 짧은 고정 대기

                    # *** 🌟 팝업(새 창) 컨텍스트 전환 🌟 ***
                    new_window = None
                    all_windows = driver.window_handles
                    
                    # 목록 창을 제외한 새로운 팝업 창 핸들 찾기
                    for window in all_windows:
                        if window != list_window:
                            new_window = window
                            driver.switch_to.window(new_window)
                            logger.info(f"✅ 윈도우 전환 성공: 새 팝업 창으로 이동")
                            break
                    
                    if not new_window:
                        logger.warning("⚠️ 팝업 창이 감지되지 않아 윈도우 전환에 실패했습니다. 목록 페이지 유지.")
                        continue # 다음 문서로 이동 (목록 창으로 계속 진행)
                    # *** 🌟 팝업 컨텍스트 전환 종료 🌟 ***
                    
                    # --- b. 팝업 내부 정보 추출 (driver는 팝업을 보고 있음) ---
                    doc_type = doc.get('구분', '')
                    doc_title = doc.get('문서제목', '')
                    detail_info = extract_detail_amount(driver, doc_type, doc_title) 
                    
                    # --- c. 팝업 닫기 및 통합 ---
                    # 팝업 창 닫기
                    driver.close() 

                    # 메인(목록) 창으로 다시 전환
                    driver.switch_to.window(list_window)
                    logger.info("✅ 팝업 닫기 및 메인 창 복귀 완료.")
                    
                    # 문서 정보와 상세 정보 통합
                    combined_data = {
                        **doc,
                        **detail_info
                    }
                    all_data.append(combined_data)
                    logger.info(f"✅ [{idx}/{len(document_list)}] 데이터 통합 완료")
                        
                except Exception as e:
                    logger.error(f"❌ 문서 처리 중 오류: {e}")
                    
                    # 오류 발생 시 복구 로직: 팝업이 열려있다면 닫고 메인 창으로 복귀
                    try: 
                        # 팝업이 열린 채 에러가 발생했다면 닫고 메인으로 복귀
                        if driver.current_window_handle != list_window:
                            driver.close()
                            driver.switch_to.window(list_window)
                    except: 
                        logger.error("🚨 오류 복구 중 심각한 오류 발생. 드라이버 상태 확인 필요.")
                    
                    continue # 다음 문서로 이동
                    
    except Exception as e:
        logger.error(f"❌ 전체 크롤링 파이프라인 중 예상치 못한 오류 발생: {e}")
        
    return all_data

def parse_date_from_text(date_text: str) -> datetime:
    """
    텍스트에서 날짜를 파싱합니다. (YYYY-MM-DD 또는 MM-DD 형식 지원)
    
    Args:
        date_text (str): 날짜가 포함된 텍스트 ('10-17 (금)', '2025.10.17' 등)
        
    Returns:
        datetime: 파싱된 날짜
        
    Raises:
        ValueError: 파싱에 실패했을 경우
    """
    
    # 불필요한 공백, 괄호, 요일 정보 제거 (예: '10-17 (금)' -> '10-17')
    cleaned_text = re.sub(r'\s*\(.+\)', '', date_text).strip()
    
    # 1. 월-일 형식 파싱 로직 추가 (목록 페이지 형식)
    month_day_pattern = r'(\d{1,2})[.-]\s*(\d{1,2})' 
    match_md = re.search(month_day_pattern, cleaned_text)
    
    if match_md:
        month, day = match_md.groups()
        current_year = datetime.now().year
        try:
            # 연도 정보가 없으므로 현재 연도를 사용합니다.
            return datetime(current_year, int(month), int(day))
        except ValueError:
            pass # 잘못된 월/일이면 다음 패턴 시도 (매우 드뭄)

    
    # 2. 기존 연도 포함 패턴 시도
    date_patterns = [
        r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})', # YYYY-MM-DD, YYYY.MM.DD
        r'(\d{4})/(\d{1,2})/(\d{1,2})',# YYYY/MM/DD
        r'(\d{1,2})[.-](\d{1,2})[.-](\d{4})',# MM-DD-YYYY, MM.DD.YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, cleaned_text)
        if match:
            groups = match.groups()
            if len(groups) == 3:
                try:
                    if len(groups[0]) == 4: # YYYY-MM-DD 형식
                        year, month, day = groups
                    else: # MM-DD-YYYY 형식
                        month, day, year = groups
                    
                    return datetime(int(year), int(month), int(day))
                except ValueError:
                    continue
    
    # 파싱 실패 시, 기본값 반환 대신 오류 발생 (디버깅 지원)
    raise ValueError(f"날짜 텍스트 파싱 실패: 형식 '{date_text}'")

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
        pd.DataFrame: 추출된 데이터
            - 기본 컬럼: ['날짜', '문서제목', '구분', '공급가액']
            - 추가 컬럼: ['거래처명', '부가세', '합계금액', '링크'] (가능 시)
    """
    try:
        logger.info("🚀 전체 데이터 크롤링 시작 (run_full_crawling 사용)")

        # 통합 크롤링 파이프라인 수행 (목록 → 팝업 상세 → 통합)
        all_data = run_full_crawling(driver, start_date, end_date)

        if not all_data:
            logger.warning("⚠️ 추출된 데이터가 없습니다")
            return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])

        # DataFrame 생성 및 표준 컬럼 정리
        df = pd.DataFrame(all_data)

        # 날짜 컬럼 표준화: '기안일' → '날짜'
        if '기안일' in df.columns:
            df['날짜'] = pd.to_datetime(df['기안일'], errors='coerce')
        elif '날짜' in df.columns:
            df['날짜'] = pd.to_datetime(df['날짜'], errors='coerce')
        else:
            # 날짜 정보가 전혀 없는 경우 빈 프레임 반환 (처리 모듈 호환을 위해)
            logger.warning("⚠️ 날짜 컬럼을 찾을 수 없어 빈 데이터프레임을 반환합니다")
            return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])

        # 구분 표준화: '매출품의'/'매입품의' → '매출'/'매입'
        if '구분' in df.columns:
            df['구분'] = df['구분'].replace({'매출품의': '매출', '매입품의': '매입'})

        # 필수 금액 컬럼 보정
        if '공급가액' not in df.columns:
            df['공급가액'] = 0

        # 표시 컬럼 구성 (가능한 경우 추가 컬럼 포함)
        base_columns = ['날짜', '문서제목', '구분', '공급가액']
        extra_columns = [c for c in ['거래처명', '부가세', '합계금액', '링크'] if c in df.columns]
        df = df[base_columns + extra_columns]

        # 정렬 및 완료 로그
        df = df.sort_values('날짜')
        logger.info(f"✅ 총 {len(df)}건의 데이터 크롤링 완료")

        return df
        
    except Exception as e:
        logger.error(f"❌ 데이터 크롤링 중 오류: {e}")
        return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])

