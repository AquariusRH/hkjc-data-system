"""
完整的數據採集和管理流程
包括採集、驗證、存儲、預處理等步驟
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, Optional, List
import json

# 導入自定義模組
from hkjc_data_scraper import HKJCDataCollector
from data_storage_manager import DataStorageManager

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 第一部分：數據驗證 ====================

class DataValidator:
    """
    數據驗證和質量檢查
    """
    
    @staticmethod
    def validate_race_results(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        驗證比賽結果數據
        
        Args:
            df: 比賽結果 DataFrame
        
        Returns:
            (是否有效, 錯誤信息列表)
        """
        errors = []
        
        # 檢查必要列
        required_cols = ['日期', '場地', '賽次', '馬號', '名次']
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"缺少必要列: {col}")
        
        if errors:
            return False, errors
        
        # 檢查數據類型
        try:
            pd.to_datetime(df['日期'])
        except:
            errors.append("日期格式不正確")
        
        # 檢查馬號範圍
        invalid_horse_nos = df[(df['馬號'] < 1) | (df['馬號'] > 14)]['馬號'].unique()
        if len(invalid_horse_nos) > 0:
            errors.append(f"馬號超出範圍: {invalid_horse_nos}")
        
        # 檢查名次範圍
        invalid_positions = df[(df['名次'] < 1) | (df['名次'] > 14)]['名次'].unique()
        if len(invalid_positions) > 0:
            errors.append(f"名次超出範圍: {invalid_positions}")
        
        # 檢查缺失值
        missing_cols = df.columns[df.isnull().any()].tolist()
        if missing_cols:
            logger.warning(f"存在缺失值的列: {missing_cols}")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_jockey_ranking(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        驗證騎師排名數據
        
        Args:
            df: 騎師排名 DataFrame
        
        Returns:
            (是否有效, 錯誤信息列表)
        """
        errors = []
        
        # 檢查必要列
        required_cols = ['騎師', '勝', '出賽']
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"缺少必要列: {col}")
        
        if errors:
            return False, errors
        
        # 檢查勝數不超過出賽數
        invalid_rows = df[df['勝'] > df['出賽']]
        if len(invalid_rows) > 0:
            errors.append(f"勝數超過出賽數: {len(invalid_rows)} 行")
        
        return len(errors) == 0, errors
    
    @staticmethod
    def validate_trainer_ranking(df: pd.DataFrame) -> Tuple[bool, List[str]]:
        """
        驗證練馬師排名數據
        
        Args:
            df: 練馬師排名 DataFrame
        
        Returns:
            (是否有效, 錯誤信息列表)
        """
        errors = []
        
        # 檢查必要列
        required_cols = ['練馬師', '勝', '出賽']
        for col in required_cols:
            if col not in df.columns:
                errors.append(f"缺少必要列: {col}")
        
        if errors:
            return False, errors
        
        # 檢查勝數不超過出賽數
        invalid_rows = df[df['勝'] > df['出賽']]
        if len(invalid_rows) > 0:
            errors.append(f"勝數超過出賽數: {len(invalid_rows)} 行")
        
        return len(errors) == 0, errors


# ==================== 第二部分：數據預處理 ====================

class DataPreprocessor:
    """
    數據預處理和轉換
    """
    
    @staticmethod
    def clean_race_results(df: pd.DataFrame) -> pd.DataFrame:
        """
        清理比賽結果數據
        
        Args:
            df: 原始比賽結果 DataFrame
        
        Returns:
            清理後的 DataFrame
        """
        df_clean = df.copy()
        
        # 轉換日期格式
        df_clean['日期'] = pd.to_datetime(df_clean['日期'])
        
        # 轉換數值列
        numeric_cols = ['馬號', '排位', '負磅', '評分', '名次', '比賽距離']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # 填充缺失值
        df_clean['評分'] = df_clean['評分'].fillna(0)
        df_clean['排位'] = df_clean['排位'].fillna(0)
        
        # 移除完全重複的行
        df_clean = df_clean.drop_duplicates()
        
        # 按日期和賽次排序
        df_clean = df_clean.sort_values(['日期', '賽次'])
        
        logger.info(f"清理後的數據: {len(df_clean)} 條記錄")
        
        return df_clean
    
    @staticmethod
    def clean_jockey_ranking(df: pd.DataFrame) -> pd.DataFrame:
        """
        清理騎師排名數據
        
        Args:
            df: 原始騎師排名 DataFrame
        
        Returns:
            清理後的 DataFrame
        """
        df_clean = df.copy()
        
        # 轉換數值列
        numeric_cols = ['勝', '亞', '季', '出賽', '獎金']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
        # 移除重複的騎師
        df_clean = df_clean.drop_duplicates(subset=['騎師'])
        
        # 按勝數排序
        df_clean = df_clean.sort_values('勝', ascending=False)
        
        logger.info(f"清理後的騎師排名: {len(df_clean)} 位騎師")
        
        return df_clean
    
    @staticmethod
    def clean_trainer_ranking(df: pd.DataFrame) -> pd.DataFrame:
        """
        清理練馬師排名數據
        
        Args:
            df: 原始練馬師排名 DataFrame
        
        Returns:
            清理後的 DataFrame
        """
        df_clean = df.copy()
        
        # 轉換數值列
        numeric_cols = ['勝', '亞', '季', '出賽', '獎金']
        for col in numeric_cols:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce').fillna(0)
        
        # 移除重複的練馬師
        df_clean = df_clean.drop_duplicates(subset=['練馬師'])
        
        # 按勝數排序
        df_clean = df_clean.sort_values('勝', ascending=False)
        
        logger.info(f"清理後的練馬師排名: {len(df_clean)} 位練馬師")
        
        return df_clean


# ==================== 第三部分：數據管道 ====================

class DataPipeline:
    """
    完整的數據採集和管理管道
    """
    
    def __init__(self, 
                 storage_type: str = "sqlite",
                 db_path: str = "hkjc_data.db"):
        """
        初始化數據管道
        
        Args:
            storage_type: 存儲類型
            db_path: 數據庫路徑
        """
        self.collector = HKJCDataCollector()
        self.storage = DataStorageManager(storage_type, db_path)
        self.validator = DataValidator()
        self.preprocessor = DataPreprocessor()
    
    def run_full_pipeline(self,
                         start_date: str,
                         end_date: str,
                         season: str = "25/26") -> Dict[str, bool]:
        """
        運行完整的數據採集和管理流程
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            season: 賽季
        
        Returns:
            包含各步驟執行結果的字典
        """
        results = {
            'collection': False,
            'validation': False,
            'preprocessing': False,
            'storage': False,
        }
        
        logger.info("=" * 50)
        logger.info("開始運行數據管道")
        logger.info("=" * 50)
        
        # 步驟 1: 採集數據
        logger.info("\n步驟 1: 採集數據")
        logger.info("-" * 50)
        
        try:
            data = self.collector.collect_all_data(start_date, end_date, season)
            
            if data:
                results['collection'] = True
                logger.info("✓ 數據採集成功")
            else:
                logger.error("✗ 未採集到數據")
                return results
        
        except Exception as e:
            logger.error(f"✗ 數據採集失敗: {e}")
            return results
        
        # 步驟 2: 驗證數據
        logger.info("\n步驟 2: 驗證數據")
        logger.info("-" * 50)
        
        try:
            all_valid = True
            
            if 'race_results' in data:
                is_valid, errors = self.validator.validate_race_results(data['race_results'])
                if is_valid:
                    logger.info("✓ 比賽結果數據驗證通過")
                else:
                    logger.error(f"✗ 比賽結果數據驗證失敗: {errors}")
                    all_valid = False
            
            if 'jockey_ranking' in data:
                is_valid, errors = self.validator.validate_jockey_ranking(data['jockey_ranking'])
                if is_valid:
                    logger.info("✓ 騎師排名數據驗證通過")
                else:
                    logger.error(f"✗ 騎師排名數據驗證失敗: {errors}")
                    all_valid = False
            
            if 'trainer_ranking' in data:
                is_valid, errors = self.validator.validate_trainer_ranking(data['trainer_ranking'])
                if is_valid:
                    logger.info("✓ 練馬師排名數據驗證通過")
                else:
                    logger.error(f"✗ 練馬師排名數據驗證失敗: {errors}")
                    all_valid = False
            
            results['validation'] = all_valid
        
        except Exception as e:
            logger.error(f"✗ 數據驗證失敗: {e}")
            return results
        
        # 步驟 3: 預處理數據
        logger.info("\n步驟 3: 預處理數據")
        logger.info("-" * 50)
        
        try:
            if 'race_results' in data:
                data['race_results'] = self.preprocessor.clean_race_results(data['race_results'])
            
            if 'jockey_ranking' in data:
                data['jockey_ranking'] = self.preprocessor.clean_jockey_ranking(data['jockey_ranking'])
            
            if 'trainer_ranking' in data:
                data['trainer_ranking'] = self.preprocessor.clean_trainer_ranking(data['trainer_ranking'])
            
            logger.info("✓ 數據預處理完成")
            results['preprocessing'] = True
        
        except Exception as e:
            logger.error(f"✗ 數據預處理失敗: {e}")
            return results
        
        # 步驟 4: 存儲數據
        logger.info("\n步驟 4: 存儲數據")
        logger.info("-" * 50)
        
        try:
            self.storage.save_all_data(data, season)
            logger.info("✓ 數據存儲成功")
            results['storage'] = True
        
        except Exception as e:
            logger.error(f"✗ 數據存儲失敗: {e}")
            return results
        
        # 完成
        logger.info("\n" + "=" * 50)
        logger.info("數據管道運行完成")
        logger.info("=" * 50)
        
        return results
    
    def get_summary(self) -> Dict:
        """
        獲取數據摘要
        
        Returns:
            數據摘要字典
        """
        return self.storage.get_statistics()


# ==================== 使用範例 ====================

def example_usage():
    """使用範例"""
    
    print("=== 完整數據管道示例 ===\n")
    
    # 初始化管道
    pipeline = DataPipeline(storage_type="sqlite", db_path="hkjc_data.db")
    
    # 運行管道
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"採集日期: {start_date} 到 {end_date}\n")
    
    results = pipeline.run_full_pipeline(start_date, end_date)
    
    # 顯示結果
    print("\n管道執行結果:")
    for step, success in results.items():
        status = "✓" if success else "✗"
        print(f"  {status} {step}: {'成功' if success else '失敗'}")
    
    # 獲取摘要
    print("\n數據摘要:")
    summary = pipeline.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    example_usage()
