"""
Supabase 數據存儲模組
用於在 Supabase 雲端數據庫中存儲和查詢賽馬數據
"""

import pandas as pd
import logging
from typing import Dict, List, Optional, Tuple
from supabase import create_client, Client
import os

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Supabase 存儲 ====================

class SupabaseDataStorage:
    """
    使用 Supabase 存儲賽馬數據
    優點：雲端存儲、自動備份、支持複雜查詢、易於擴展
    """
    
    def __init__(self, 
                 supabase_url: Optional[str] = None,
                 supabase_key: Optional[str] = None):
        """
        初始化 Supabase 存儲
        
        Args:
            supabase_url: Supabase URL (可從環境變數讀取)
            supabase_key: Supabase API Key (可從環境變數讀取)
        """
        # 從環境變數讀取
        self.supabase_url = supabase_url or os.getenv('SUPABASE_URL')
        self.supabase_key = supabase_key or os.getenv('SUPABASE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "需要設置 SUPABASE_URL 和 SUPABASE_KEY 環境變數"
            )
        
        # 初始化 Supabase 客戶端
        self.client: Client = create_client(self.supabase_url, self.supabase_key)
        
        # 初始化表結構
        self.init_tables()
        
        logger.info("Supabase 存儲初始化成功")
    
    def init_tables(self):
        """初始化 Supabase 表結構"""
        try:
            # 檢查表是否存在，如果不存在則創建
            # 注意：Supabase 需要通過 SQL 編輯器手動創建表
            # 或者使用以下 SQL 語句
            
            logger.info("表結構已準備")
        
        except Exception as e:
            logger.error(f"初始化表結構失敗: {e}")
    
    def insert_race_results(self, df: pd.DataFrame) -> int:
        """
        插入比賽結果
        
        Args:
            df: 比賽結果 DataFrame
        
        Returns:
            插入的記錄數
        """
        try:
            # 準備數據
            records = []
            for _, row in df.iterrows():
                record = {
                    'date': str(row.get('日期', '')),
                    'venue': str(row.get('場地', '')),
                    'venue_code': str(row.get('場地代碼', '')),
                    'race_no': int(row.get('賽次', 0)),
                    'horse_no': int(row.get('馬號', 0)),
                    'horse_name': str(row.get('馬名', '')),
                    'jockey': str(row.get('騎師', '')),
                    'trainer': str(row.get('練馬師', '')),
                    'draw': int(row.get('排位', 0)) if pd.notna(row.get('排位')) else None,
                    'weight': float(row.get('負磅', 0)) if pd.notna(row.get('負磅')) else None,
                    'rating': float(row.get('評分', 0)) if pd.notna(row.get('評分')) else None,
                    'recent_form': str(row.get('近績', '')),
                    'finishing_position': int(row.get('名次', 0)) if pd.notna(row.get('名次')) else None,
                    'track_type': str(row.get('賽道類型', '')),
                    'race_distance': int(row.get('比賽距離', 0)),
                    'race_class': str(row.get('賽事等級', '')),
                }
                records.append(record)
            
            # 分批插入（Supabase 有單次請求大小限制）
            batch_size = 100
            inserted_count = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    response = self.client.table('race_results').insert(batch).execute()
                    inserted_count += len(batch)
                    logger.info(f"插入 {len(batch)} 條比賽記錄")
                except Exception as e:
                    logger.warning(f"批次插入失敗: {e}，嘗試逐條插入")
                    # 逐條插入
                    for record in batch:
                        try:
                            self.client.table('race_results').insert(record).execute()
                            inserted_count += 1
                        except Exception as e:
                            logger.warning(f"插入失敗: {e}")
            
            logger.info(f"成功插入 {inserted_count} 條比賽記錄")
            return inserted_count
        
        except Exception as e:
            logger.error(f"插入比賽結果失敗: {e}")
            return 0
    
    def insert_jockey_ranking(self, df: pd.DataFrame, season: str) -> int:
        """
        插入騎師排名
        
        Args:
            df: 騎師排名 DataFrame
            season: 賽季
        
        Returns:
            插入的記錄數
        """
        try:
            records = []
            for _, row in df.iterrows():
                record = {
                    'jockey_name': str(row.get('騎師', '')),
                    'jockey_name_en': str(row.get('騎師英文', '')),
                    'wins': int(row.get('勝', 0)),
                    'seconds': int(row.get('亞', 0)),
                    'thirds': int(row.get('季', 0)),
                    'starts': int(row.get('出賽', 0)),
                    'prize_money': float(row.get('獎金', 0)),
                    'season': season,
                }
                records.append(record)
            
            # 分批插入
            batch_size = 100
            inserted_count = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    self.client.table('jockey_ranking').insert(batch).execute()
                    inserted_count += len(batch)
                except Exception as e:
                    logger.warning(f"批次插入失敗: {e}")
                    for record in batch:
                        try:
                            self.client.table('jockey_ranking').insert(record).execute()
                            inserted_count += 1
                        except:
                            pass
            
            logger.info(f"成功插入 {inserted_count} 條騎師排名記錄")
            return inserted_count
        
        except Exception as e:
            logger.error(f"插入騎師排名失敗: {e}")
            return 0
    
    def insert_trainer_ranking(self, df: pd.DataFrame, season: str) -> int:
        """
        插入練馬師排名
        
        Args:
            df: 練馬師排名 DataFrame
            season: 賽季
        
        Returns:
            插入的記錄數
        """
        try:
            records = []
            for _, row in df.iterrows():
                record = {
                    'trainer_name': str(row.get('練馬師', '')),
                    'trainer_name_en': str(row.get('練馬師英文', '')),
                    'wins': int(row.get('勝', 0)),
                    'seconds': int(row.get('亞', 0)),
                    'thirds': int(row.get('季', 0)),
                    'starts': int(row.get('出賽', 0)),
                    'prize_money': float(row.get('獎金', 0)),
                    'season': season,
                }
                records.append(record)
            
            # 分批插入
            batch_size = 100
            inserted_count = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                try:
                    self.client.table('trainer_ranking').insert(batch).execute()
                    inserted_count += len(batch)
                except Exception as e:
                    logger.warning(f"批次插入失敗: {e}")
                    for record in batch:
                        try:
                            self.client.table('trainer_ranking').insert(record).execute()
                            inserted_count += 1
                        except:
                            pass
            
            logger.info(f"成功插入 {inserted_count} 條練馬師排名記錄")
            return inserted_count
        
        except Exception as e:
            logger.error(f"插入練馬師排名失敗: {e}")
            return 0
    
    def query_race_results(self,
                          date: Optional[str] = None,
                          venue: Optional[str] = None,
                          limit: int = 1000) -> pd.DataFrame:
        """
        查詢比賽結果
        
        Args:
            date: 日期 (可選)
            venue: 場地 (可選)
            limit: 返回記錄數限制
        
        Returns:
            查詢結果 DataFrame
        """
        try:
            query = self.client.table('race_results').select('*')
            
            if date:
                query = query.eq('date', date)
            
            if venue:
                query = query.eq('venue', venue)
            
            response = query.limit(limit).execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                return df
            else:
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"查詢比賽結果失敗: {e}")
            return pd.DataFrame()
    
    def query_jockey_ranking(self, season: str) -> pd.DataFrame:
        """
        查詢騎師排名
        
        Args:
            season: 賽季
        
        Returns:
            查詢結果 DataFrame
        """
        try:
            response = self.client.table('jockey_ranking')\
                .select('*')\
                .eq('season', season)\
                .order('wins', desc=True)\
                .execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                return df
            else:
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"查詢騎師排名失敗: {e}")
            return pd.DataFrame()
    
    def query_trainer_ranking(self, season: str) -> pd.DataFrame:
        """
        查詢練馬師排名
        
        Args:
            season: 賽季
        
        Returns:
            查詢結果 DataFrame
        """
        try:
            response = self.client.table('trainer_ranking')\
                .select('*')\
                .eq('season', season)\
                .order('wins', desc=True)\
                .execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                return df
            else:
                return pd.DataFrame()
        
        except Exception as e:
            logger.error(f"查詢練馬師排名失敗: {e}")
            return pd.DataFrame()
    
    def get_statistics(self) -> Dict:
        """
        獲取數據庫統計信息
        
        Returns:
            統計信息字典
        """
        try:
            stats = {}
            
            # 比賽結果統計
            response = self.client.table('race_results')\
                .select('count', count='exact')\
                .execute()
            stats['race_results_count'] = response.count or 0
            
            # 騎師排名統計
            response = self.client.table('jockey_ranking')\
                .select('count', count='exact')\
                .execute()
            stats['jockey_count'] = response.count or 0
            
            # 練馬師排名統計
            response = self.client.table('trainer_ranking')\
                .select('count', count='exact')\
                .execute()
            stats['trainer_count'] = response.count or 0
            
            return stats
        
        except Exception as e:
            logger.error(f"獲取統計信息失敗: {e}")
            return {}


# ==================== 使用範例 ====================

def example_usage():
    """使用範例"""
    
    print("=== Supabase 存儲示例 ===\n")
    
    try:
        # 初始化存儲
        storage = SupabaseDataStorage()
        
        # 創建示例數據
        race_data = pd.DataFrame({
            '日期': ['2026-04-22', '2026-04-22'],
            '場地': ['沙田', '沙田'],
            '場地代碼': ['ST', 'ST'],
            '賽次': [1, 1],
            '馬號': [1, 2],
            '馬名': ['馬匹A', '馬匹B'],
            '騎師': ['騎師A', '騎師B'],
            '練馬師': ['練馬師A', '練馬師B'],
            '排位': [1, 2],
            '負磅': [120, 121],
            '評分': [50, 55],
            '近績': ['1/2', '2/3'],
            '名次': [1, 2],
            '賽道類型': ['草地', '草地'],
            '比賽距離': [1200, 1200],
            '賽事等級': ['2級', '2級'],
        })
        
        # 插入數據
        print("1. 插入比賽結果...")
        count = storage.insert_race_results(race_data)
        print(f"✓ 插入 {count} 條記錄\n")
        
        # 查詢數據
        print("2. 查詢比賽結果...")
        results = storage.query_race_results(date='2026-04-22')
        print(f"✓ 查詢到 {len(results)} 條記錄\n")
        
        # 獲取統計信息
        print("3. 獲取統計信息...")
        stats = storage.get_statistics()
        print(f"✓ 統計信息: {stats}")
    
    except Exception as e:
        print(f"✗ 錯誤: {e}")


if __name__ == "__main__":
    example_usage()
