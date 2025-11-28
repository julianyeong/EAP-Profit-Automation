import os
import sys
import argparse
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import pandas as pd 

# 로깅 설정 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add modules directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'modules'))

# [수정된 임포트]: data_processor에서 create_detailed_sheet를 제거
from modules.web_setup import setup_driver, login_groupware
from modules.data_crawler import get_last_12_months, parse_date_range, crawl_all_data, navigate_to_handover_document_list 
from modules.data_processor import export_to_excel, process_monthly_summary, create_profit_analysis

def main():
    """Main execution function"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='영업 부서 매출/매입 현황 자동화 시스템')
    
    parser.add_argument('--url', help='그룹웨어 URL', default=os.getenv('GROUPWARE_URL'))
    parser.add_argument('--id', help='로그인 ID', default=os.getenv('GROUPWARE_ID')) 
    parser.add_argument('--pw', help='로그인 비밀번호', default=os.getenv('GROUPWARE_PW')) 
    
    parser.add_argument('--mode', choices=['auto', 'manual'], default='auto', 
                        help='날짜 범위 모드: auto(최근 12개월) 또는 manual(수동 입력)')
    parser.add_argument('--start-date', help='시작 날짜 (YYYY-MM-DD, manual 모드에서 사용)')
    parser.add_argument('--end-date', help='종료 날짜 (YYYY-MM-DD, manual 모드에서 사용)')
    
    parser.add_argument('--headless', action='store_true', default=True, help='브라우저 창을 숨김 (Headless 모드 실행)')
    parser.add_argument('--no-headless', action='store_true', help='브라우저 창을 표시 (디버깅용)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not all([args.url, args.id, args.pw]):
        print("❌ 오류: 그룹웨어 URL, ID, 비밀번호가 필요합니다.")
        print("환경변수(.env 파일) 또는 명령행 인수로 제공하세요.")
        return 1
    
    # Determine date range
    if args.mode == 'auto':
        start_date, end_date = get_last_12_months()
        logger.info(f"📅 지정된 기간간 데이터 추출")
    else:
        if not args.start_date or not args.end_date:
            logger.error("❌ 오류: manual 모드에서는 --start-date와 --end-date가 필요합니다.")
            return 1
        try:
            start_date, end_date = parse_date_range(args.start_date, args.end_date)
            logger.info(f"📅 수동 모드: 지정된 기간 데이터 추출")
        except ValueError as e:
            logger.error(f"❌ 날짜 형식 오류: {e}")
            return 1
    
    driver = None
    try:
        logger.info("🚀 시스템 초기화 및 크롤링 시작...")
        
        # Setup WebDriver (디버깅 시 --no-headless 옵션 사용)
        headless_mode = args.headless and not args.no_headless
        driver = setup_driver(headless=headless_mode)
        
        # Login to groupware
        if not login_groupware(driver, args.url, args.id, args.pw):
            logger.error("❌ 로그인 실패")
            return 1
        logger.info("✅ 로그인 성공")
        
        # [로그인 확인을 위한 대기]
        time.sleep(2) 
        
        # 메뉴 이동
        logger.info("▶️ 품의서 목록 페이지로 이동 중...")
        if not navigate_to_handover_document_list(driver):
            logger.error("❌ 인수인계문서 목록 페이지 이동 실패. 작업을 중단합니다.")
            return 1
        logger.info("✅ 인수인계문서 목록 페이지로 이동 성공.")
        
        # 데이터 크롤링 및 표준화된 DataFrame 반환
        logger.info("📊 전체 데이터 크롤링 및 표준화 시작...")
        df = crawl_all_data(driver, start_date, end_date) 
        
        if df.empty:
            logger.warning("⚠️ 추출된 데이터가 없거나 날짜 표준화에 실패하여 빈 DataFrame이 반환되었습니다.")
            return 0
            
        logger.info(f"✅ 총 {len(df)}건의 표준화된 데이터 추출 완료")
        
        # --- 📈 데이터 분석 및 Excel 보고서 생성 ---
        logger.info("📈 데이터 분석 및 Excel 보고서 생성 중...")
        
        # 1. 월별 요약 데이터 생성 (분석의 기본)
        monthly_df = process_monthly_summary(df)
        
        # 2. 손익 분석 데이터 생성
        analysis_df = create_profit_analysis(monthly_df)
        
        # 3. Excel 보고서 생성 (df를 상세 내역으로 전달하여 매출/매입 시트 분리)
        filename = export_to_excel(
            detailed_df=df, # 전체 상세 데이터 (data_processor에서 분리 처리)
            monthly_df=monthly_df, 
            analysis_df=analysis_df
        ) 
        
        logger.info(f"🎉 작업 완료! 보고서가 저장되었습니다: {filename}")
        return 0
            
    except Exception as e:
        logger.error(f"❌ 치명적인 오류 발생: {e}", exc_info=True)
        return 1
            
    finally:
        if driver:
            logger.info("🔚 WebDriver 종료 중...")
            driver.quit()

if __name__ == "__main__":
    exit(main())