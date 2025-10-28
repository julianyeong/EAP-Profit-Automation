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
    """
    documents = []
    
    try:
        logger.info(f"📄 '{doc_keyword}' 키워드 문서 목록 추출 중...")
        
        # 1. HTML 소스 가져오기 및 BeautifulSoup 파싱
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

def extract_detail_amount(driver, document_type: str) -> Dict[str, Any]:
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
    
    # try:
    #     logger.info("🔍 상세 정보 추출 중...")
        
        # 페이지 소스 가져오기
    page_source = driver.page_source
    soup = BeautifulSoup(page_source, 'html.parser')
        
    # 전체 텍스트에서 레이블 기반으로 값 추출
    full_text = soup.get_text()
        
    #     # 거래처명 추출
    #     account_patterns = [
    #         r'거래처명[:\s]*([^\n]+)',
    #         r'거래처[:\s]*([^\n]+)',
    #         r'거래처명[:\s]*([가-힣a-zA-Z0-9\s]+)'
    #     ]
        
    #     for pattern in account_patterns:
    #         match = re.search(pattern, full_text)
    #         if match:
    #             detail_data['거래처명'] = match.group(1).strip()
    #             break
        
    #     # 공급가액 추출
    #     supply_patterns = [
    #         r'공급가액[:\s]*([\d,]+)',
    #         r'공급가[:\s]*([\d,]+)',
    #         r'공급가액[:\s]*([0-9,]+)'
    #     ]
        
    #     for pattern in supply_patterns:
    #         match = re.search(pattern, full_text)
    #         if match:
    #             try:
    #                 detail_data['공급가액'] = int(match.group(1).replace(',', ''))
    #                 break
    #             except ValueError:
    #                 continue
        
    #     # 부가세 추출
    #     vat_patterns = [
    #         r'부가세[:\s]*([\d,]+)',
    #         r'VAT[:\s]*([\d,]+)',
    #         r'부가세[:\s]*([0-9,]+)'
    #     ]
        
    #     for pattern in vat_patterns:
    #         match = re.search(pattern, full_text)
    #         if match:
    #             try:
    #                 detail_data['부가세'] = int(match.group(1).replace(',', ''))
    #                 break
    #             except ValueError:
    #                 continue
        
    #     # 합계금액 추출
    #     total_patterns = [
    #         r'합계금액[:\s]*([\d,]+)',
    #         r'합계[:\s]*([\d,]+)',
    #         r'총액[:\s]*([\d,]+)',
    #         r'합계금액[:\s]*([0-9,]+)'
    #     ]
        
    #     for pattern in total_patterns:
    #         match = re.search(pattern, full_text)
    #         if match:
    #             try:
    #                 detail_data['합계금액'] = int(match.group(1).replace(',', ''))
    #                 break
    #             except ValueError:
    #                 continue
        
    #     logger.info(f"✅ 상세 정보 추출 완료: {detail_data}")
        
    # except Exception as e:
    #     logger.error(f"❌ 상세 정보 추출 중 오류: {e}")
    
    # return detail_data
    detail_data = {'공급가액': 0, '부가세': 0, '합계금액': 0, '회사 이름': 'N/A'}
    
    # 1. 합계 정보가 포함된 테이블 탐색 (고정된 스타일 속성 사용)
    total_sum_table = soup.find('table', 
        style=lambda s: s and 'border-top:2px solid rgb(102, 102, 102)' in s)
        
    if not total_sum_table:
        logger.warning("⚠️ 합계 테이블을 찾을 수 없습니다. 정규 표현식으로 fallback.")
        # 테이블을 못 찾으면 기존의 정규 표현식 로직으로 대체됩니다. (이후 코드에서 처리)
        return detail_data 

    # 2. '합계' 텍스트가 Bold 처리된 최종 합계 행(Row) 탐색
    final_sum_row = total_sum_table.find('tr', string=lambda t: t and '합계' in t)
        
    if not final_sum_row:
         logger.warning("⚠️ 합계 금액이 담긴 행(Row)을 찾을 수 없습니다.")
         return detail_data 
         
    # 3. 해당 행의 모든 셀(<td> 또는 <th>) 추출
    # NOTE: 합계 행은 마지막 <tr>의 모든 셀을 사용합니다.
    sum_cells = final_sum_row.find_all(['td', 'th'])

    # 4. 금액 추출 (뒤에서 3개 셀)
    # [합계금액, 부가세, 공급가액]이 뒤에서 -1, -2, -3 인덱스로 있다고 가정합니다.
    if len(sum_cells) >= 3:
        try:
            # 💡 추출 목표: 공급가액, 부가세, 합계
            detail_data['합계금액'] = _clean_amount(sum_cells[-1].get_text(strip=True))
            detail_data['부가세'] = _clean_amount(sum_cells[-2].get_text(strip=True))
            detail_data['공급가액'] = _clean_amount(sum_cells[-3].get_text(strip=True))
        except Exception:
            logger.warning("⚠️ 합계 행에서 금액을 추출할 수 없습니다. 셀 인덱스/값 확인 필요.")
            
    # 5. 거래처명 추출 (가장 상단의 레이블 테이블에서 추출)
    account_label = soup.find('th', string=lambda t: t and '거래처명' in t)
    if account_label:
        account_value_cell = account_label.find_next_sibling('td')
        if account_value_cell:
             # 거래처명은 상위의 다른 테이블에 있으므로, 추출된 텍스트만 저장합니다.
             detail_data['회사 이름'] = account_value_cell.get_text(strip=True).split('외')[0].strip()

    return detail_data

def close_popup(driver):
    """팝업을 닫습니다. (ESC 키 사용으로 최적화)"""
    try:
        logger.info("🚪 팝업 닫기 시도 중...")
        from selenium.webdriver.common.keys import Keys
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
        logger.info("✅ ESC 키로 팝업 닫기 성공")
        time.sleep(1) 
        return True
    except Exception as e:
        logger.warning(f"⚠️ 팝업 닫기 실패: {e}")
        return False

def run_full_crawling(driver, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    전체 크롤링 파이프라인을 실행합니다.
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
                list_page_url = driver.current_url # 현재 목록 페이지 URL 저장 (오류 복구용)
                
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
                    time.sleep(2) # 팝업 로딩 대기

                    # --- b. 팝업 내부 정보 추출 (문서 종류 전달) ---
                    doc_type = doc.get('구분', '')
                    detail_info = extract_detail_amount(driver, doc_type) 
                    
                    # --- c. 팝업 닫기 및 통합 ---
                    close_popup(driver)
                    logger.info("✅ 팝업 닫기 완료.")
                        
                    # 목록 페이지로 복귀 (팝업이 레이어 모달이므로 driver.back() 불필요)
                    if driver.current_url != list_page_url:
                        driver.get(list_page_url) 
                    time.sleep(1)
                        
                    # 문서 정보와 상세 정보 통합
                    combined_data = {
                        **doc,
                        **detail_info
                    }
                    all_data.append(combined_data)
                    logger.info(f"✅ [{idx}/{len(document_list)}] 데이터 통합 완료")
                        
                except Exception as e:
                    logger.error(f"❌ 문서 처리 중 오류: {e}")
                    # 오류 발생 시 목록 페이지로 강제 복귀
                    try: driver.get(list_page_url) 
                    except: pass
                    continue
        
        # 4. 최종 데이터를 JSON 파일로 저장
        import json
        import os
        
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        output_file = os.path.join(output_dir, "temp_raw_data.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 전체 크롤링 완료: {len(all_data)}건의 데이터를 {output_file}에 저장")
        
        return pd.DataFrame(all_data)
        
    except Exception as e:
        logger.error(f"❌ 전체 크롤링 중 오류: {e}")
        return pd.DataFrame(columns=['날짜', '문서제목', '구분', '공급가액'])

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

