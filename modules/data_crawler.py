"""
데이터 크롤링 모듈
Amaranth 그룹웨어에서 종결된 매출/매입 품의서 데이터를 추출합니다.
"""

from tarfile import data_filter
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
    
    Args:
        driver: Selenium WebDriver 인스턴스
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)
        doc_keyword (str): 문서 제목에 포함될 키워드 ('매출품의' 또는 '매입품의')
        
    Returns:
        List[Dict[str, Any]]: 추출된 문서 링크 리스트 (문서제목, 링크, 날짜 포함)
    """
    documents = []
    
    try:
        logger.info(f"📄 '{doc_keyword}' 키워드 문서 목록 추출 중...")
        
        # 1. HTML 소스 가져오기 및 BeautifulSoup 파싱
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # [핵심 수정 1: UL 컨테이너 탐색으로 대체] 
        document_list_container = soup.select_one('ul.tableBody') 
        
        if not document_list_container:
            logger.warning("⚠️ 품의서 목록 컨테이너 (ul.tableBody)를 찾을 수 없습니다")
            return documents

        # 2. LI 행들 추출 및 cells 로직 제거
        rows = document_list_container.find_all('li', recursive=False)  
        logger.info(f"📊 총 {len(rows)}개의 행을 찾았습니다.")

        for idx, row in enumerate(rows, 1):
            try:
                # 1. 문서 제목 추출 (titDiv .title span)
                title_element = row.select_one('.titDiv .title span')
                if not title_element:
                    # 제목 텍스트를 가진 span이 없을 경우, title 클래스 자체의 텍스트를 시도 (안정성 보강)
                    title_element = row.select_one('.titDiv .title')
                    if not title_element: continue
                title = title_element.get_text(strip=True)
                
                # 2. 문서번호/링크 추출 (infoDiv 내부, 두 번째 infoLink 텍스트 사용)
                info_links_container = row.select_one('.infoDiv .h-box')
                if not info_links_container: continue

                info_links = info_links_container.find_all('div', class_=lambda x: x and 'txt' in x and 'infoLink' in x)
                if len(info_links) < 2: continue # 품의 종류와 문서번호 2개가 있어야 함

                link_text_element = info_links[1] # 두 번째 infoLink (문서번호 텍스트)
                link_href = link_text_element.get_text(strip=True) #부서 및 문서번호호
                
                # 3. 기안일 추출 (dateText 클래스)
                date_text_element = row.select_one('.dateText')
                date_text = date_text_element.get_text(strip=True) if date_text_element else ""
                
                # 4. 상태 확인 (종결/완료된 문서만)
                status_element = row.select_one('.process .ellipsis2')
                status = status_element.get_text(strip=True) if status_element else ""
                
                if '종결' not in status and '완료' not in status: continue
                
                # 5. 날짜 파싱 및 필터링 (기존 로직 유지)
                doc_date = parse_date_from_text(date_text)
                if not is_date_in_range(doc_date, start_date, end_date): continue
                print(doc_date)
                
                # 6. 키워드 필터링 및 데이터 구조화 (금액 로직은 완전히 제거됨)
                if doc_keyword not in title: continue
                
                doc_type = '매출품의' if '매출품의' in title else '매입품의'
                
                print(doc_date)
                print(title)
                print(link_href)
                print(doc_type)
                
                document_data = {
                    '기안일': doc_date.strftime('%Y-%m-%d'),
                    '매출품의|매입품의': doc_type,
                    '문서제목': title,
                    '사업본부-문서번호': link_href,
                    '종결|완료' : status
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

def extract_detail_amount(driver) -> Dict[str, Any]:
    """
    팝업 상세 페이지에서 재무 정보를 추출합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        
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
        logger.info("🔍 상세 정보 추출 중...")
        
        # 페이지 소스 가져오기
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # 전체 텍스트에서 레이블 기반으로 값 추출
        full_text = soup.get_text()
        
        # 거래처명 추출
        account_patterns = [
            r'거래처명[:\s]*([^\n]+)',
            r'거래처[:\s]*([^\n]+)',
            r'거래처명[:\s]*([가-힣a-zA-Z0-9\s]+)'
        ]
        
        for pattern in account_patterns:
            match = re.search(pattern, full_text)
            if match:
                detail_data['거래처명'] = match.group(1).strip()
                break
        
        # 공급가액 추출
        supply_patterns = [
            r'공급가액[:\s]*([\d,]+)',
            r'공급가[:\s]*([\d,]+)',
            r'공급가액[:\s]*([0-9,]+)'
        ]
        
        for pattern in supply_patterns:
            match = re.search(pattern, full_text)
            if match:
                try:
                    detail_data['공급가액'] = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # 부가세 추출
        vat_patterns = [
            r'부가세[:\s]*([\d,]+)',
            r'VAT[:\s]*([\d,]+)',
            r'부가세[:\s]*([0-9,]+)'
        ]
        
        for pattern in vat_patterns:
            match = re.search(pattern, full_text)
            if match:
                try:
                    detail_data['부가세'] = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # 합계금액 추출
        total_patterns = [
            r'합계금액[:\s]*([\d,]+)',
            r'합계[:\s]*([\d,]+)',
            r'총액[:\s]*([\d,]+)',
            r'합계금액[:\s]*([0-9,]+)'
        ]
        
        for pattern in total_patterns:
            match = re.search(pattern, full_text)
            if match:
                try:
                    detail_data['합계금액'] = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        logger.info(f"✅ 상세 정보 추출 완료: {detail_data}")
        
    except Exception as e:
        logger.error(f"❌ 상세 정보 추출 중 오류: {e}")
    
    return detail_data

def close_popup(driver):
    """
    팝업을 닫습니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        
    Returns:
        bool: 팝업 닫기 성공 여부
    """
    try:
        logger.info("🚪 팝업 닫기 시도 중...")
        
        # 다양한 닫기 버튼 선택자
        close_selectors = [
            "//button[contains(text(), '닫기')]",
            "//button[contains(text(), 'X')]",
            "//span[contains(text(), '닫기')]",
            "//span[contains(text(), 'X')]",
            "//button[@class='close']",
            "//button[@class='btn-close']",
            "//*[@id='closeBtn']",
            "//*[@id='btnClose']"
        ]
        
        for selector in close_selectors:
            try:
                close_button = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((By.XPATH, selector))
                )
                close_button.click()
                logger.info(f"✅ 팝업 닫기 성공: {selector}")
                time.sleep(1)
                return True
            except TimeoutException:
                continue
        
        # 닫기 버튼을 찾지 못한 경우 ESC 키 시도
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        logger.info("✅ ESC 키로 팝업 닫기 시도")
        time.sleep(1)
        return True
        
    except Exception as e:
        logger.warning(f"⚠️ 팝업 닫기 실패: {e}")
        return False

def run_full_crawling(driver, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    전체 크롤링 파이프라인을 실행합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        start_date (str): 시작 날짜 (YYYY-MM-DD)
        end_date (str): 종료 날짜 (YYYY-MM-DD)
        
    Returns:
        List[Dict[str, Any]]: 추출된 전체 데이터 리스트
    """
    all_data = []
    
    try:
        logger.info("🚀 전체 크롤링 시작")
        
        # '매출품의'와 '매입품의' 키워드로 목록 추출
        keywords = ['매출품의', '매입품의']
        
        for keyword in keywords:
            logger.info(f"📋 '{keyword}' 목록 추출 중...")
            
            # 목록 페이지에서 문서 링크 추출
            document_list = extract_document_list(driver, start_date, end_date, keyword)
            
            if not document_list:
                logger.warning(f"⚠️ '{keyword}' 문서가 없습니다")
                continue
            
            logger.info(f"✅ '{keyword}' 문서 {len(document_list)}건 발견")
            
            # 각 문서 링크를 순회하며 상세 정보 추출
            for idx, doc in enumerate(document_list, 1):
                try:
                    logger.info(f"📄 [{idx}/{len(document_list)}] {doc['문서제목']} 처리 중...")
                    
                    # a. 문서 링크 클릭하여 팝업 띄우기
                    try:
                        # 링크가 상대 경로인 경우 절대 경로로 변환
                        link = doc['링크']
                        if link.startswith('/'):
                            link = driver.current_url.rsplit('/', 1)[0] + link
                        elif not link.startswith('http'):
                            link = driver.current_url.rsplit('/', 1)[0] + '/' + link
                        
                        driver.get(link)
                        time.sleep(2)  # 팝업 로딩 대기
                        
                    except Exception as e:
                        logger.error(f"❌ 팝업 열기 실패: {e}")
                        continue
                    
                    # b. 팝업 내부 정보 추출
                    detail_info = extract_detail_amount(driver)
                    
                    # 문서 정보와 상세 정보 통합
                    combined_data = {
                        **doc,
                        **detail_info
                    }
                    
                    all_data.append(combined_data)
                    logger.info(f"✅ [{idx}/{len(document_list)}] 추출 완료")
                    
                    # c. 팝업 닫기
                    close_popup(driver)
                    
                    # 목록 페이지로 돌아가기
                    driver.back()
                    time.sleep(1)
                    
                except Exception as e:
                    logger.error(f"❌ 문서 처리 중 오류: {e}")
                    continue
        
        # 최종 데이터를 JSON 파일로 저장
        import json
        import os
        
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, "temp_raw_data.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 전체 크롤링 완료: {len(all_data)}건의 데이터를 {output_file}에 저장")
        
        return all_data
        
    except Exception as e:
        logger.error(f"❌ 전체 크롤링 중 오류: {e}")
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
        pd.DataFrame: 추출된 데이터 (컬럼: ['날짜', '문서제목', '구분', '공급가액'])
    """
    try:
        logger.info("🚀 전체 데이터 크롤링 시작")
        
        # 품의서 목록 페이지로 이동 (이미 navigate_to_handover_document_list로 이동했으므로 스킵)
        # if not navigate_to_handover_document_list(driver):
        #     logger.error("❌ 품의서 목록 페이지 이동 실패")
        #     return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])
        
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

