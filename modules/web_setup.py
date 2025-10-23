"""
WebDriver 설정 및 그룹웨어 로그인 모듈
Chrome WebDriver를 headless 모드로 설정하고 Amaranth 그룹웨어에 자동 로그인합니다.
"""
# [추가] ----------------------------------------------------
from selenium.webdriver.common.keys import Keys
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_driver(headless=True):
    """
    Chrome WebDriver를 설정하고 반환합니다.
    
    Args:
        headless (bool): headless 모드 사용 여부 (기본값: True)
    
    Returns:
        webdriver.Chrome: 설정된 Chrome WebDriver 인스턴스
    """
    try:
        # Chrome 옵션 설정
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')  # headless 모드
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
        # WebDriverManager를 사용하여 ChromeDriver 자동 설치
        service = Service(ChromeDriverManager().install())
        
        # WebDriver 생성
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        # 자동화 감지 방지
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        logger.info("✅ Chrome WebDriver 설정 완료")
        return driver
        
    except Exception as e:
        logger.error(f"❌ WebDriver 설정 실패: {e}")
        raise

    """
    Amaranth 그룹웨어에 로그인합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        url (str): 그룹웨어 URL
        user_id (str): 로그인 ID
        password (str): 로그인 비밀번호
        
    Returns:
        bool: 로그인 성공 여부
    """
    try:
        logger.info(f"🌐 그룹웨어 접속 중: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(3)
        
        # 로그인 필드 찾기 및 입력
        logger.info("🔑 로그인 정보 입력 중...")
        
        # ID 필드 찾기 및 입력
        try:
            #1단계 : 아이디 입력 및 다음 버튼 클릭
            #ID 필드 찾기 및 입력력
            id_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "reqLoginId"))
            )
            id_field.clear()
            id_field.send_keys(user_id)
            
            #다음 버튼 클릭릭
            next_button = driver.find_element(By.XPATH, "//button[.//span[text()='다음']]")
            next_button.click()
            logger.info("✅ '다음' 버튼 클릭 완료")
            logger.info("✅ ID 입력 완료")
        except TimeoutException:
            logger.error("❌ ID 필드를 찾을 수 없습니다 (login_id)")
            return False
        
        # 비밀번호 필드 찾기 및 입력
        try:
            pw_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "reqLoginPw"))
            )
            pw_field.clear()
            pw_field.send_keys(password)
            logger.info("✅ 비밀번호 입력 완료")
        except NoSuchElementException:
            logger.error("❌ 비밀번호 필드를 찾을 수 없습니다 (login_pw)")
            return False
        
        # 로그인 버튼 클릭
        try:
            # CSS Selector로 로그인 버튼 찾기
            login_button = driver.find_element(By.CSS_SELECTOR, "//button[.//span[text()='로그인']]")
            login_button.click()
            logger.info("✅ 로그인 버튼 클릭 완료")
        except NoSuchElementException:
            # 클래스 이름이 변경된 경우 XPath로 '로그인' 텍스트를 포함하는 버튼 찾기
            try:
                login_button = driver.find_element(By.XPATH, "//button[contains(text(), '로그인')]")
                login_button.click()
                logger.info("✅ 로그인 버튼 클릭 완료 (XPath 대체)")
            except NoSuchElementException:
                logger.warning("⚠️ 로그인 버튼을 찾을 수 없습니다. Enter 키로 로그인 시도")
                pw_field.send_keys("\n")
        except Exception as e:
            logger.warning(f"⚠️ 로그인 버튼 클릭 실패, Enter 키로 시도: {e}")
            pw_field.send_keys("\n")
        
        # 로그인 성공 확인 (다중 검증 방식)
        try:
            logger.info("🔍 로그인 성공 확인 중...")
            
            # 1단계: 로그인 폼이 사라졌는지 확인 (가장 확실한 방법)
            try:
                WebDriverWait(driver, 10).until_not(
                    EC.presence_of_element_located((By.ID, "reqLoginId"))
                )
                logger.info("✅ 로그인 폼이 사라짐 확인")
            except TimeoutException:
                logger.warning("⚠️ 로그인 폼이 여전히 존재합니다")
            
            # 2단계: 페이지 로딩 완료 대기
            wait_for_page_load(driver, 10)
            
            # 3단계: 로그인 후 나타나는 요소들 확인 (여러 선택자 시도)
            success_indicators = [
                "//input[@placeholder='통합 검색']",  # 통합 검색 필드
                "//div[contains(@class, 'dashboard')]",  # 대시보드
                "//nav[contains(@class, 'menu')]",  # 메뉴 네비게이션
                "//div[contains(@class, 'main-content')]",  # 메인 콘텐츠
                "//header[contains(@class, 'header')]"  # 헤더
            ]
            
            login_success = False
            for indicator in success_indicators:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.XPATH, indicator))
                    )
                    logger.info(f"✅ 로그인 성공 지표 발견: {indicator}")
                    login_success = True
                    break
                except TimeoutException:
                    continue
            
            # 4단계: URL 변경 확인 (SPA가 아닌 경우)
            if not login_success:
                try:
                    WebDriverWait(driver, 5).until(
                        lambda driver: driver.current_url != url and 
                        "login" not in driver.current_url.lower()
                    )
                    logger.info("✅ URL 변경으로 로그인 성공 확인")
                    login_success = True
                except TimeoutException:
                    pass
            
            if login_success:
                logger.info("✅ 로그인 성공")
                return True
            else:
                logger.error("❌ 로그인 실패: 성공 지표를 찾을 수 없습니다")
                return False
            
        except Exception as e:
            logger.error(f"❌ 로그인 확인 중 오류: {e}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 로그인 중 오류 발생: {e}")
        return False
def login_groupware(driver, url, user_id, password):
    # HTML 선택자 정의 (유지보수 용이)
    ID_FIELD_ID = "reqLoginId"
    PW_FIELD_ID = "reqLoginPw" # 최종 확정 값
    NEXT_BTN_XPATH = "//button[.//span[text()='다음']]"
    LOGIN_BTN_XPATH = "//button[.//span[text()='로그인']]"
    MAIN_SEARCH_XPATH = "//input[@placeholder='통합 검색']"
    WAIT_TIME = 10
    
    try:
        logger.info(f"🌐 그룹웨어 접속 중: {url}")
        driver.get(url)
        time.sleep(3) 

        # --- [1단계: ID 입력 및 다음 버튼 클릭] ---
        logger.info("🔑 1단계: ID 입력 및 다음 버튼 탐색 중...")
        
        # ID 필드 찾기 및 입력 (클릭 가능할 때까지 대기)
        id_field = WebDriverWait(driver, WAIT_TIME).until(
            # [수정] EC.presence_of_element_located -> EC.element_to_be_clickable로 변경 (Interactable 보장)
            EC.element_to_be_clickable((By.ID, ID_FIELD_ID))
        )
        id_field.clear()
        id_field.send_keys(user_id)
        
        # '다음' 버튼 클릭 (클릭 가능할 때까지 대기)
        next_button = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, NEXT_BTN_XPATH))
        )
        next_button.click()
        logger.info("✅ '다음' 버튼 클릭 완료")
        logger.info("✅ ID 입력 완료")
        
        # --- [2단계: PW 입력 및 최종 로그인] ---
        logger.info("🔑 2단계: PW 필드 대기 및 정보 입력 중...")
        
        # [핵심 수정] PW 필드가 나타나고 조작 가능할 때까지 대기 (Interactable 해결)
        pw_field = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.ID, PW_FIELD_ID))
        )
        pw_field.clear()
        pw_field.send_keys(password)
        logger.info("✅ 비밀번호 입력 완료")
        
        # '로그인' 버튼 클릭
        login_button = WebDriverWait(driver, WAIT_TIME).until(
            EC.element_to_be_clickable((By.XPATH, LOGIN_BTN_XPATH))
        )
        login_button.click()
        logger.info("✅ '로그인' 버튼 클릭 완료")
        
        # # --- [3단계: 로그인 성공 최종 확인] ---
        # logger.info("🔍 최종 성공 확인 중: 메인 페이지 요소 대기...")

        # # 1. 로그인 폼(ID 필드)이 사라지기를 기다립니다.
        # WebDriverWait(driver, 15).until_not(
        #     EC.presence_of_element_located((By.ID, ID_FIELD_ID))
        # )
        
        # # 2. 메인 페이지의 고유 요소('통합 검색' 입력 필드)가 나타나기를 기다립니다.
        # WebDriverWait(driver, WAIT_TIME).until(
        #     EC.presence_of_element_located((By.XPATH, MAIN_SEARCH_XPATH))
        # )
        
        logger.info("🌟🌟🌟 로그인 성공 및 메인 페이지 진입 확인 완료 🌟🌟🌟")
        return True
            
    # [에러 처리 수정] NoSuchElementException은 더 이상 발생하지 않도록 코드를 개선했으므로, 
    # TimeoutException과 일반 Exception만 포괄적으로 처리합니다.
    except TimeoutException as te:
        logger.error(f"❌ 로그인 타임아웃 오류: 특정 요소를 10초 내에 찾을 수 없습니다. (오류: {te})", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"❌ 로그인 중 치명적인 오류 발생: {e}", exc_info=True)
        return False
def wait_for_page_load(driver, timeout=10):    
    """
    페이지 로딩 완료를 대기합니다.
    
    Args:
        driver: Selenium WebDriver 인스턴스
        timeout (int): 대기 시간 (초)
    """
    try:
        WebDriverWait(driver, timeout).until(
            lambda driver: driver.execute_script("return document.readyState") == "complete"
        )
        time.sleep(2)  # 추가 안정화 시간
    except TimeoutException:
        logger.warning(f"⚠️ 페이지 로딩 타임아웃 ({timeout}초)")
def navigate_to_handover_document_list(driver, timeout=20):
    """
    1. '전자결재' 메뉴 클릭
    2. '인수인계' 상위 메뉴 확장
    3. '인수인계문서' 서브 메뉴 클릭을 통해 최종 목적지로 이동합니다.
    """
    
    # [수정] HTML 선택자 정의 (NameError 방지)
    XPATH_ELECTRONIC_APPROVAL = "//span[text()='전자결재']" 
    XPATH_EAP_SIDE_LOADED = "//span[text()='인수인계']" # 로딩 대기용 텍스트
    ID_TOP_MENU = "UBA_UBA5000"  # '인수인계' 상위 메뉴 ID
    ID_SUB_MENU = "//span[text()='인수인계문서']"  # '인수인계문서' 하위 메뉴 name
    
    # --- 1단계: '전자결재' 메뉴 클릭 (EAP 페이지로 진입) ---
    try:
        logger.info("1단계: 🔍 '전자결재' 메뉴 클릭 시도 중...")
        WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, XPATH_ELECTRONIC_APPROVAL))
        ).click()
        logger.info("✅ '전자결재' 메뉴 클릭 성공. 내부 요소 로딩 대기 중...")
        
        # 전자결재 페이지 내부 요소 (결재수신함) 로딩 대기
        WebDriverWait(driver, timeout).until(
             EC.presence_of_element_located((By.XPATH, XPATH_EAP_SIDE_LOADED))
        )
        logger.info("✅ 전자결재 페이지 내부 요소 로딩 완료 확인.")

    except Exception as e:
        logger.error(f"❌ 1단계: 전자결재 메뉴 이동 실패. 오류: {e}")
        return False
    
    # --- 2단계: '인수인계' 메뉴 확장 및 '인수인계문서' 클릭 ---
    try:
        # --- 2단계: '인수인계문서'로 바로 이동 (이미 펼쳐진 상태 가정) ---
        
        logger.info("2단계: 🔍 '인수인계문서' 서브 메뉴 클릭 시도 중...")
        sub_menu_span_locator = (By.ID, ID_SUB_MENU)
        
        # 하위 메뉴의 <span> 태그가 나타나고 클릭 가능할 때까지 대기
        sub_menu_span = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(sub_menu_span_locator)
        )
        
        # Span의 부모 DIV를 찾아 최종 클릭하여 페이지 이동
        sub_menu_div = sub_menu_span.find_element(By.XPATH, "./..")
        
        # JavaScript 강제 클릭 실행 (가장 확실하게 클릭)
        driver.execute_script("arguments[0].click();", sub_menu_div)
        
        # 최종 페이지 로딩 확인을 위한 잠시 대기
        time.sleep(3) 
        
        logger.info("🎉 '인수인계문서'함으로 최종 이동 성공 (JS 강제 클릭)")
        return True

    except TimeoutException:
        logger.error(f"❌ 2단계: '인수인계' 메뉴 확장/클릭 타임아웃. ID: {ID_TOP_MENU} 또는 {ID_SUB_MENU} 확인 필요.")
        return False
    except NoSuchElementException:
        logger.error(f"❌ 2단계: 메뉴 요소의 HTML 구조가 변경되었습니다. ID/XPath 확인 필요.")
        return False
    except Exception as e:
        logger.error(f"❌ 2단계: 예상치 못한 오류 발생: {e}", exc_info=True)
        return False