"""
데이터 처리 및 Excel 내보내기 모듈
크롤링된 매출/매입 데이터를 분석하고 Excel 보고서를 생성합니다.
"""

import os
from datetime import datetime
from typing import Tuple
import pandas as pd
import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.utils import get_column_letter
import logging

logger = logging.getLogger(__name__)

def process_monthly_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    월별 매출/매입 요약 데이터를 생성합니다. (개선된 Pandas 로직 적용)
    """
    try:
        logger.info("📊 월별 요약 데이터 생성 중...")
        
        if df.empty:
            return pd.DataFrame(columns=['년월', '매출액', '매입액', '손익'])
        
        df_copy = df.copy()
        df_copy['년월'] = df_copy['날짜'].dt.to_period('M').astype(str) # string으로 변환
        
        # 1. 월별, 구분별 공급가액 합계 계산
        summary_df = df_copy.groupby(['년월', '구분'])['공급가액'].sum().unstack(fill_value=0)
        
        # 2. 컬럼명 표준화 및 손익 계산
        if '매출' in summary_df.columns:
            summary_df = summary_df.rename(columns={'매출': '매출액'})
        else:
            summary_df['매출액'] = 0
            
        if '매입' in summary_df.columns:
            summary_df = summary_df.rename(columns={'매입': '매입액'})
        else:
            summary_df['매입액'] = 0
            
        summary_df['손익'] = summary_df['매출액'] - summary_df['매입액']
        
        # 인덱스(년월)를 컬럼으로 변환 및 정렬
        monthly_df = summary_df.reset_index().sort_values('년월')
        monthly_df = monthly_df[['년월', '매출액', '매입액', '손익']]
        
        logger.info(f"✅ 월별 요약 데이터 생성 완료: {len(monthly_df)}개월")
        return monthly_df
        
    except Exception as e:
        logger.error(f"❌ 월별 요약 데이터 생성 실패: {e}")
        return pd.DataFrame(columns=['년월', '매출액', '매입액', '손익'])

def create_detailed_sheet(df: pd.DataFrame) -> pd.DataFrame:
    """
    상세 내역 시트용 데이터를 생성합니다.
    (요청된 모든 상세 정보를 포함하도록 컬럼 순서 지정)
    """
    try:
        logger.info("📋 상세 내역 데이터 생성 중...")
        
        if df.empty:
            # 필수 컬럼 외에 요청된 모든 컬럼을 포함
            required_cols = ['기안일', '문서제목', '문서번호', '링크', '구분', '거래처명', '공급가액', '부가세', '합계금액']
            return pd.DataFrame(columns=required_cols)
        
        detailed_df = df.copy()
        
        # '날짜' 컬럼이 '기안일'로 통합되었으므로, '날짜'를 기준으로 년월/년도/월을 생성
        # NOTE: data_crawler.py에서 '기안일'이 '날짜'로 변경되었으므로, df['날짜']를 사용합니다.
        
        # 금액 컬럼이 정수형이 아닐 경우 강제로 변환 (Excel 포맷팅을 위해)
        for col in ['공급가액', '부가세', '합계금액']:
             if col in detailed_df.columns:
                 # 오류가 있는 셀은 NaN으로 처리 후 0으로 채움
                 detailed_df[col] = pd.to_numeric(detailed_df[col], errors='coerce').fillna(0).astype(int)

        # 요청된 최종 컬럼 순서 지정
        column_order = [
            '날짜', '문서제목', '문서번호', '링크', '구분',
            '거래처명', '공급가액', '부가세', '합계금액'
        ]
        
        # DataFrame에 존재하는 컬럼만 포함
        final_columns = [col for col in column_order if col in detailed_df.columns]
        
        # 날짜 순으로 정렬
        detailed_df = detailed_df.sort_values('날짜')
        detailed_df = detailed_df[final_columns]
        
        # 헤더명을 요청된 이름으로 다시 변경 (예: '날짜' -> '기안일')
        detailed_df = detailed_df.rename(columns={'날짜': '기안일'})
        
        logger.info(f"✅ 상세 내역 데이터 생성 완료: {len(detailed_df)}건")
        return detailed_df
        
    except Exception as e:
        logger.error(f"❌ 상세 내역 데이터 생성 실패: {e}")
        required_cols = ['기안일', '문서제목', '문서번호', '링크', '구분', '거래처명', '공급가액', '부가세', '합계금액']
        return pd.DataFrame(columns=required_cols)

def create_profit_analysis(monthly_df: pd.DataFrame) -> pd.DataFrame:
    """
    손익 분석 데이터를 생성합니다.
    
    Args:
        monthly_df (pd.DataFrame): 월별 요약 데이터
        
    Returns:
        pd.DataFrame: 손익 분석 데이터
    """
    try:
        logger.info("📈 손익 분석 데이터 생성 중...")
        
        if monthly_df.empty:
            return pd.DataFrame(columns=['년월', '매출액', '매입액', '손익', '누적손익', '수익률'])
        
        analysis_df = monthly_df.copy()
        
        # 누적 손익 계산
        analysis_df['누적손익'] = analysis_df['손익'].cumsum()
        
        # 수익률 계산 (매출액 대비 손익 비율)
        analysis_df['수익률'] = np.where(
            analysis_df['매출액'] > 0,
            (analysis_df['손익'] / analysis_df['매출액'] * 100).round(2),
            0
        )
        
        # 전월 대비 증감률 계산
        analysis_df['매출증감률'] = analysis_df['매출액'].pct_change() * 100
        analysis_df['손익증감률'] = analysis_df['손익'].pct_change() * 100
        
        # 첫 번째 행의 증감률은 0으로 설정
        analysis_df['매출증감률'] = analysis_df['매출증감률'].fillna(0)
        analysis_df['손익증감률'] = analysis_df['손익증감률'].fillna(0)
        
        # 컬럼 순서 조정
        column_order = ['년월', '매출액', '매입액', '손익', '누적손익', '수익률', '매출증감률', '손익증감률']
        analysis_df = analysis_df[column_order]
        
        logger.info(f"✅ 손익 분석 데이터 생성 완료: {len(analysis_df)}개월")
        return analysis_df
        
    except Exception as e:
        logger.error(f"❌ 손익 분석 데이터 생성 실패: {e}")
        return pd.DataFrame(columns=['년월', '매출액', '매입액', '손익', '누적손익', '수익률'])

def export_to_excel(detailed_df: pd.DataFrame, monthly_df: pd.DataFrame, analysis_df: pd.DataFrame, filename: str = None) -> str:
    """
    데이터를 Excel 파일로 내보냅니다.
    
    Args:
        detailed_df (pd.DataFrame): 상세 내역 데이터
        monthly_df (pd.DataFrame): 월별 요약 데이터
        analysis_df (pd.DataFrame): 손익 분석 데이터
        filename (str, optional): 파일명 (없으면 자동 생성)
        
    Returns:
        str: 저장된 파일 경로
    """
    try:
        logger.info("📊 Excel 보고서 생성 중...")
        
        # output 디렉토리 확인 및 생성
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"📁 {output_dir} 디렉토리 생성")
        
        # 파일명 생성
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"매출매입현황_{timestamp}.xlsx"
        
        filepath = os.path.join(output_dir, filename)
        
        # Excel 워크북 생성
        wb = Workbook()
        
        # 기본 시트 제거
        wb.remove(wb.active)
        
        # 스타일 정의
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        header_alignment = Alignment(horizontal="center", vertical="center")
        
        number_format = "#,##0"
        currency_format = "#,##0"
        
        # 1. 상세내역 시트
        if not detailed_df.empty:
            ws_detailed = wb.create_sheet("상세내역")
            add_dataframe_to_sheet(ws_detailed, detailed_df, "상세 거래 내역")
            format_worksheet(ws_detailed, detailed_df, header_font, header_fill, header_alignment, number_format)
        
        # 2. 월별요약 시트
        if not monthly_df.empty:
            ws_monthly = wb.create_sheet("월별요약")
            add_dataframe_to_sheet(ws_monthly, monthly_df, "월별 매출/매입 현황")
            format_worksheet(ws_monthly, monthly_df, header_font, header_fill, header_alignment, number_format)

        # 3. 손익분석 시트
        if not analysis_df.empty:
            ws_analysis = wb.create_sheet("손익분석")
            add_dataframe_to_sheet(ws_analysis, analysis_df, "손익 분석")
            format_worksheet(ws_analysis, analysis_df, header_font, header_fill, header_alignment, number_format)
        
        # 파일 저장
        wb.save(filepath)
        
        logger.info(f"✅ Excel 보고서 생성 완료: {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"❌ Excel 보고서 생성 실패: {e}")
        raise

def add_dataframe_to_sheet(worksheet, df: pd.DataFrame, title: str):
    """
    워크시트에 DataFrame 데이터를 추가합니다.
    
    Args:
        worksheet: openpyxl 워크시트 객체
        df (pd.DataFrame): 추가할 데이터
        title (str): 시트 제목
    """
    # 제목 추가
    worksheet['A1'] = title
    worksheet['A1'].font = Font(size=14, bold=True)
    
    # 데이터 추가 (3행부터 시작)
    for r in dataframe_to_rows(df, index=False, header=True):
        worksheet.append(r)

def format_worksheet(worksheet, df: pd.DataFrame, header_font, header_fill, header_alignment, number_format):
    """
    워크시트를 포맷팅합니다.
    
    Args:
        worksheet: openpyxl 워크시트 객체
        df (pd.DataFrame): 데이터
        header_font: 헤더 폰트
        header_fill: 헤더 배경색
        header_alignment: 헤더 정렬
        number_format: 숫자 형식
    """
    # 헤더 스타일 적용 (4행, 데이터가 있는 경우)
    if len(df) > 0:
        for col in range(1, len(df.columns) + 1):
            cell = worksheet.cell(row=4, column=col)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment
        
        # 숫자 컬럼 포맷팅
        for col_idx, col_name in enumerate(df.columns, 1):
            if '액' in col_name or '가격' in col_name or '금액' in col_name:
                for row in range(5, len(df) + 5):
                    cell = worksheet.cell(row=row, column=col_idx)
                    cell.number_format = number_format
        
        # 컬럼 너비 자동 조정
        for column in worksheet.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

def create_summary_report(detailed_df: pd.DataFrame) -> dict:
    """
    요약 통계를 생성합니다.
    
    Args:
        detailed_df (pd.DataFrame): 상세 데이터
        
    Returns:
        dict: 요약 통계
    """
    try:
        if detailed_df.empty:
            return {
                '총_거래건수': 0,
                '총_매출액': 0,
                '총_매입액': 0,
                '총_손익': 0,
                '평균_월매출': 0,
                '평균_월매입': 0
            }
        
        # 기본 통계
        total_sales = detailed_df[detailed_df['구분'] == '매출']['공급가액'].sum()
        total_purchases = detailed_df[detailed_df['구분'] == '매입']['공급가액'].sum()
        total_profit = total_sales - total_purchases
        total_transactions = len(detailed_df)
        
        # 월별 평균 계산
        monthly_sales = detailed_df[detailed_df['구분'] == '매출'].groupby('년월')['공급가액'].sum()
        monthly_purchases = detailed_df[detailed_df['구분'] == '매입'].groupby('년월')['공급가액'].sum()
        
        avg_monthly_sales = monthly_sales.mean() if not monthly_sales.empty else 0
        avg_monthly_purchases = monthly_purchases.mean() if not monthly_purchases.empty else 0
        
        return {
            '총_거래건수': total_transactions,
            '총_매출액': total_sales,
            '총_매입액': total_purchases,
            '총_손익': total_profit,
            '평균_월매출': avg_monthly_sales,
            '평균_월매입': avg_monthly_purchases
        }
        
    except Exception as e:
        logger.error(f"❌ 요약 통계 생성 실패: {e}")
        return {}

