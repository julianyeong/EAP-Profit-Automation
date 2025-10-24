#!/usr/bin/env python3
"""
영업 부서 매출/매입 현황 자동화 시스템
Amaranth 그룹웨어에서 종결된 매출/매입 품의서 데이터를 추출하여 월별 손익 분석을 수행합니다.
"""

import os
import sys
import argparse
import time # [추가] 로그인 테스트를 위한 time 임포트
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging # [추가] 로깅 기능 사용을 위한 임포트

# 로깅 설정 (main.py에서도 로깅이 잘 보이도록 설정)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

from modules.web_setup import setup_driver, login_groupware
from modules.data_crawler import navigate_to_handover_document_list, run_full_crawling, get_last_12_months, parse_date_range
from modules.data_processor import export_to_excel, process_monthly_summary, create_detailed_sheet, create_profit_analysis

def main():
    """Main execution function"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='영업 부서 매출/매입 현황 자동화 시스템')
    
    # 환경 변수 이름을 .env 파일에 맞게 수정
    parser.add_argument('--url', help='그룹웨어 URL', default=os.getenv('GROUPWARE_URL'))
    parser.add_argument('--id', help='로그인 ID', default=os.getenv('GROUPWARE_ID'))  
    parser.add_argument('--pw', help='로그인 비밀번호', default=os.getenv('GROUPWARE_PW')) 
    
    parser.add_argument('--mode', choices=['auto', 'manual'], default='auto', 
                        help='날짜 범위 모드: auto(최근 12개월) 또는 manual(수동 입력)')
    parser.add_argument('--start-date', help='시작 날짜 (YYYY-MM-DD, manual 모드에서 사용)')
    parser.add_argument('--end-date', help='종료 날짜 (YYYY-MM-DD, manual 모드에서 사용)')
    
    # 로그인 테스트를 위해 headless 모드를 끌 수 있는 인수를 추가합니다.
    parser.add_argument('--headless', action='store_true', default=True, help='브라우저 창을 숨김 (Headless 모드 실행)')
    parser.add_argument('--no-headless', action='store_true', help='브라우저 창을 표시 (디버깅용)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not all([args.url, args.id, args.pw]):
        print("❌ 오류: 그룹웨어 URL, ID, 비밀번호가 필요합니다.")
        print("환경변수(.env 파일) 또는 명령행 인수로 제공하세요.")
        return 1
    
    # Determine date range (로그인 테스트 시 이 부분은 실행되지만 데이터 추출은 건너뜁니다.)
    if args.mode == 'auto':
        start_date, end_date = get_last_12_months()
        logger.info(f"📅 자동 모드: 최근 12개월 데이터 추출 ({start_date} ~ {end_date})")
    else:
        if not args.start_date or not args.end_date:
            logger.error("❌ 오류: manual 모드에서는 --start-date와 --end-date가 필요합니다.")
            return 1
        try:
            start_date, end_date = parse_date_range(args.start_date, args.end_date)
            logger.info(f"📅 수동 모드: 지정된 기간 데이터 추출 ({start_date} ~ {end_date})")
        except ValueError as e:
            logger.error(f"❌ 날짜 형식 오류: {e}")
            return 1
    
    driver = None
    try:
        logger.info("🚀 시스템 초기화 중...")
        
        # Setup WebDriver (디버깅 시 --no-headless 옵션 사용)
        logger.info("🔧 WebDriver 설정 중...")
        headless_mode = args.headless and not args.no_headless
        driver = setup_driver(headless=headless_mode)
        
        # Login to groupware
        logger.info("🔐 그룹웨어 로그인 중...")
        if not login_groupware(driver, args.url, args.id, args.pw):
            logger.error("❌ 로그인 실패")
            return 1
        logger.info("✅ 로그인 성공")
        
        # [로그인 테스트를 위해 여기서 잠시 대기합니다.]
        logger.info("🌟 로그인 확인을 위해 5초간 대기합니다.")
        time.sleep(5) 
        
        #메뉴 이동
        logger.info("▶️ 품의서 목록 페이지로 이동 중...")
        if not navigate_to_handover_document_list(driver):
            logger.error("❌ 인수인계문서 목록 페이지 이동 실패. 작업을 중단합니다.")
            return 1 # 이동 실패 시 프로그램 종료
        logger.info("✅ 인수인계문서 목록 페이지로 이동 성공.")
        
        # 데이터 크롤링 실행
        logger.info("📊 데이터 크롤링 시작...")
        all_data = run_full_crawling(driver, start_date, end_date)
        
        if not all_data:
            logger.warning("⚠️ 추출된 데이터가 없습니다.")
            return 0
        
        logger.info(f"✅ 총 {len(all_data)}건의 데이터 추출 완료")
        
        # # DataFrame 생성 및 Excel 보고서 생성
        # logger.info("📈 데이터 분석 및 Excel 보고서 생성 중...")
        
        # # JSON 데이터를 DataFrame으로 변환
        # import pandas as pd
        # df = pd.DataFrame(all_data)
        
        # # 데이터 처리
        # monthly_df = process_monthly_summary(df)
        # detailed_df = create_detailed_sheet(df)
        # analysis_df = create_profit_analysis(monthly_df)
        
        # # Excel 보고서 생성
        # filename = export_to_excel(detailed_df, monthly_df, analysis_df)
        
        # logger.info(f"🎉 작업 완료! 보고서가 저장되었습니다: {filename}")
        # return 0
        
    except Exception as e:
        logger.error(f"❌ 오류 발생: {e}", exc_info=True)
        return 1
        
    finally:
        if driver:
            logger.info("🔚 WebDriver 종료 중...")
            driver.quit()

if __name__ == "__main__":
    exit(main())