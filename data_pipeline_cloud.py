"""
雲端數據管道
支持 Supabase 存儲的完整數據採集和管理流程
"""

import pandas as pd
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from hkjc_data_scraper import HKJCDataCollector
from supabase_storage import SupabaseDataStorage
from data_pipeline import DataValidator, DataPreprocessor

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 雲端數據管道 ====================

class CloudDataPipeline:
    """
    雲端數據管道
    使用 Supabase 作為後端存儲
    """
    
    def __init__(self):
        """初始化雲端數據管道"""
        try:
            self.collector = HKJCDataCollector()
            self.storage = SupabaseDataStorage()
            self.validator = DataValidator()
            self.preprocessor = DataPreprocessor()
            logger.info("雲端數據管道初始化成功")
        except Exception as e:
            logger.error(f"初始化失敗: {e}")
            raise
    
    def run_full_pipeline(self,
                         start_date: str,
                         end_date: str,
                         season: str = "25/26") -> Dict[str, bool]:
        """
        運行完整的雲端數據採集和管理流程
        
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
        logger.info("開始運行雲端數據管道")
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
        
        # 步驟 4: 上傳到 Supabase
        logger.info("\n步驟 4: 上傳到 Supabase")
        logger.info("-" * 50)
        
        try:
            if 'race_results' in data:
                self.storage.insert_race_results(data['race_results'])
            
            if 'jockey_ranking' in data:
                self.storage.insert_jockey_ranking(data['jockey_ranking'], season)
            
            if 'trainer_ranking' in data:
                self.storage.insert_trainer_ranking(data['trainer_ranking'], season)
            
            logger.info("✓ 數據上傳成功")
            results['storage'] = True
        
        except Exception as e:
            logger.error(f"✗ 數據上傳失敗: {e}")
            return results
        
        # 完成
        logger.info("\n" + "=" * 50)
        logger.info("雲端數據管道運行完成")
        logger.info("=" * 50)
        
        return results
    
    def get_summary(self) -> Dict:
        """
        獲取數據摘要
        
        Returns:
            數據摘要字典
        """
        return self.storage.get_statistics()
    
    def query_race_results(self,
                          date: Optional[str] = None,
                          venue: Optional[str] = None,
                          limit: int = 1000) -> pd.DataFrame:
        """
        查詢比賽結果
        
        Args:
            date: 日期
            venue: 場地
            limit: 返回記錄數限制
        
        Returns:
            查詢結果 DataFrame
        """
        return self.storage.query_race_results(date, venue, limit)
    
    def query_jockey_ranking(self, season: str) -> pd.DataFrame:
        """
        查詢騎師排名
        
        Args:
            season: 賽季
        
        Returns:
            查詢結果 DataFrame
        """
        return self.storage.query_jockey_ranking(season)
    
    def query_trainer_ranking(self, season: str) -> pd.DataFrame:
        """
        查詢練馬師排名
        
        Args:
            season: 賽季
        
        Returns:
            查詢結果 DataFrame
        """
        return self.storage.query_trainer_ranking(season)


# ==================== 使用範例 ====================

def example_usage():
    """使用範例"""
    
    print("=== 雲端數據管道示例 ===\n")
    
    try:
        # 初始化管道
        pipeline = CloudDataPipeline()
        
        # 採集最近 7 天的數據
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        
        print(f"採集日期: {start_date} 到 {end_date}\n")
        
        # 運行管道
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
        
        # 查詢數據
        print("\n查詢示例:")
        results = pipeline.query_race_results(limit=10)
        print(f"最近比賽: {len(results)} 條記錄")
        if len(results) > 0:
            print(results.head())
    
    except Exception as e:
        print(f"✗ 錯誤: {e}")


if __name__ == "__main__":
    example_usage()
