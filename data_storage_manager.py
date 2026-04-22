"""
賽馬數據存儲和管理系統
支持 SQLite、CSV 和內存存儲
"""

import pandas as pd
import sqlite3
import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 第一部分：SQLite 存儲 ====================

class SQLiteDataStorage:
    """
    使用 SQLite 存儲賽馬數據
    優點：持久化存儲、支持複雜查詢、文件體積小
    """
    
    def __init__(self, db_path: str = "hkjc_data.db"):
        """
        初始化 SQLite 存儲
        
        Args:
            db_path: 數據庫文件路徑
        """
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """初始化數據庫表結構"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            # 比賽結果表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS race_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    venue TEXT NOT NULL,
                    venue_code TEXT NOT NULL,
                    race_no INTEGER NOT NULL,
                    horse_no INTEGER NOT NULL,
                    horse_name TEXT,
                    jockey TEXT,
                    trainer TEXT,
                    draw INTEGER,
                    weight REAL,
                    rating REAL,
                    recent_form TEXT,
                    finishing_position INTEGER,
                    track_type TEXT,
                    race_distance INTEGER,
                    race_class TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(date, venue_code, race_no, horse_no)
                )
            """)
            
            # 騎師排名表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS jockey_ranking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    jockey_name TEXT NOT NULL,
                    jockey_name_en TEXT,
                    wins INTEGER,
                    seconds INTEGER,
                    thirds INTEGER,
                    starts INTEGER,
                    prize_money REAL,
                    season TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(jockey_name, season)
                )
            """)
            
            # 練馬師排名表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trainer_ranking (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trainer_name TEXT NOT NULL,
                    trainer_name_en TEXT,
                    wins INTEGER,
                    seconds INTEGER,
                    thirds INTEGER,
                    starts INTEGER,
                    prize_money REAL,
                    season TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trainer_name, season)
                )
            """)
            
            # 數據更新日誌表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS data_update_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_type TEXT NOT NULL,
                    start_date TEXT,
                    end_date TEXT,
                    records_count INTEGER,
                    status TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            self.conn.commit()
            logger.info(f"數據庫初始化成功: {self.db_path}")
        
        except Exception as e:
            logger.error(f"數據庫初始化失敗: {e}")
    
    def insert_race_results(self, df: pd.DataFrame) -> int:
        """
        插入比賽結果
        
        Args:
            df: 比賽結果 DataFrame
        
        Returns:
            插入的記錄數
        """
        try:
            # 重命名列以匹配數據庫字段
            df_copy = df.copy()
            df_copy.columns = df_copy.columns.str.lower()
            
            # 映射列名
            column_mapping = {
                '日期': 'date',
                '場地': 'venue',
                '場地代碼': 'venue_code',
                '賽次': 'race_no',
                '馬號': 'horse_no',
                '馬名': 'horse_name',
                '騎師': 'jockey',
                '練馬師': 'trainer',
                '排位': 'draw',
                '負磅': 'weight',
                '評分': 'rating',
                '近績': 'recent_form',
                '名次': 'finishing_position',
                '賽道類型': 'track_type',
                '比賽距離': 'race_distance',
                '賽事等級': 'race_class',
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in df.columns:
                    df_copy[new_col] = df[old_col]
            
            # 只保留需要的列
            required_cols = list(column_mapping.values())
            df_copy = df_copy[[col for col in required_cols if col in df_copy.columns]]
            
            # 插入數據
            df_copy.to_sql('race_results', self.conn, if_exists='append', index=False)
            self.conn.commit()
            
            logger.info(f"成功插入 {len(df)} 條比賽記錄")
            return len(df)
        
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
            df_copy = df.copy()
            
            # 添加賽季列
            df_copy['season'] = season
            
            # 重命名列
            df_copy = df_copy.rename(columns={
                '騎師': 'jockey_name',
                '騎師英文': 'jockey_name_en',
                '勝': 'wins',
                '亞': 'seconds',
                '季': 'thirds',
                '出賽': 'starts',
                '獎金': 'prize_money',
            })
            
            # 只保留需要的列
            required_cols = ['jockey_name', 'jockey_name_en', 'wins', 'seconds', 
                           'thirds', 'starts', 'prize_money', 'season']
            df_copy = df_copy[[col for col in required_cols if col in df_copy.columns]]
            
            # 插入數據
            df_copy.to_sql('jockey_ranking', self.conn, if_exists='append', index=False)
            self.conn.commit()
            
            logger.info(f"成功插入 {len(df)} 條騎師排名記錄")
            return len(df)
        
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
            df_copy = df.copy()
            
            # 添加賽季列
            df_copy['season'] = season
            
            # 重命名列
            df_copy = df_copy.rename(columns={
                '練馬師': 'trainer_name',
                '練馬師英文': 'trainer_name_en',
                '勝': 'wins',
                '亞': 'seconds',
                '季': 'thirds',
                '出賽': 'starts',
                '獎金': 'prize_money',
            })
            
            # 只保留需要的列
            required_cols = ['trainer_name', 'trainer_name_en', 'wins', 'seconds',
                           'thirds', 'starts', 'prize_money', 'season']
            df_copy = df_copy[[col for col in required_cols if col in df_copy.columns]]
            
            # 插入數據
            df_copy.to_sql('trainer_ranking', self.conn, if_exists='append', index=False)
            self.conn.commit()
            
            logger.info(f"成功插入 {len(df)} 條練馬師排名記錄")
            return len(df)
        
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
            query = "SELECT * FROM race_results WHERE 1=1"
            params = []
            
            if date:
                query += " AND date = ?"
                params.append(date)
            
            if venue:
                query += " AND venue = ?"
                params.append(venue)
            
            query += f" LIMIT {limit}"
            
            df = pd.read_sql_query(query, self.conn, params=params)
            return df
        
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
            query = "SELECT * FROM jockey_ranking WHERE season = ? ORDER BY wins DESC"
            df = pd.read_sql_query(query, self.conn, params=[season])
            return df
        
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
            query = "SELECT * FROM trainer_ranking WHERE season = ? ORDER BY wins DESC"
            df = pd.read_sql_query(query, self.conn, params=[season])
            return df
        
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
            cursor = self.conn.cursor()
            
            stats = {}
            
            # 比賽結果統計
            cursor.execute("SELECT COUNT(*) FROM race_results")
            stats['race_results_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(DISTINCT date) FROM race_results")
            stats['unique_dates'] = cursor.fetchone()[0]
            
            # 騎師排名統計
            cursor.execute("SELECT COUNT(*) FROM jockey_ranking")
            stats['jockey_count'] = cursor.fetchone()[0]
            
            # 練馬師排名統計
            cursor.execute("SELECT COUNT(*) FROM trainer_ranking")
            stats['trainer_count'] = cursor.fetchone()[0]
            
            return stats
        
        except Exception as e:
            logger.error(f"獲取統計信息失敗: {e}")
            return {}
    
    def close(self):
        """關閉數據庫連接"""
        if self.conn:
            self.conn.close()
            logger.info("數據庫連接已關閉")


# ==================== 第二部分：CSV 存儲 ====================

class CSVDataStorage:
    """
    使用 CSV 文件存儲賽馬數據
    優點：易於分享、易於備份、易於查看
    """
    
    def __init__(self, directory: str = "hkjc_data"):
        """
        初始化 CSV 存儲
        
        Args:
            directory: 數據目錄
        """
        self.directory = directory
        
        # 創建目錄
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"創建數據目錄: {directory}")
    
    def save_race_results(self, df: pd.DataFrame, filename: str = "race_results.csv"):
        """
        保存比賽結果到 CSV
        
        Args:
            df: 比賽結果 DataFrame
            filename: 文件名
        """
        try:
            filepath = os.path.join(self.directory, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"成功保存比賽結果: {filepath}")
        
        except Exception as e:
            logger.error(f"保存比賽結果失敗: {e}")
    
    def save_jockey_ranking(self, df: pd.DataFrame, season: str):
        """
        保存騎師排名到 CSV
        
        Args:
            df: 騎師排名 DataFrame
            season: 賽季
        """
        try:
            filename = f"jockey_ranking_{season}.csv"
            filepath = os.path.join(self.directory, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"成功保存騎師排名: {filepath}")
        
        except Exception as e:
            logger.error(f"保存騎師排名失敗: {e}")
    
    def save_trainer_ranking(self, df: pd.DataFrame, season: str):
        """
        保存練馬師排名到 CSV
        
        Args:
            df: 練馬師排名 DataFrame
            season: 賽季
        """
        try:
            filename = f"trainer_ranking_{season}.csv"
            filepath = os.path.join(self.directory, filename)
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"成功保存練馬師排名: {filepath}")
        
        except Exception as e:
            logger.error(f"保存練馬師排名失敗: {e}")
    
    def load_race_results(self, filename: str = "race_results.csv") -> pd.DataFrame:
        """
        從 CSV 加載比賽結果
        
        Args:
            filename: 文件名
        
        Returns:
            比賽結果 DataFrame
        """
        try:
            filepath = os.path.join(self.directory, filename)
            df = pd.read_csv(filepath, encoding='utf-8-sig')
            logger.info(f"成功加載比賽結果: {filepath}")
            return df
        
        except Exception as e:
            logger.error(f"加載比賽結果失敗: {e}")
            return pd.DataFrame()


# ==================== 第三部分：數據管理器 ====================

class DataStorageManager:
    """
    統一的數據存儲管理器
    支持多種存儲方式
    """
    
    def __init__(self, 
                 storage_type: str = "sqlite",
                 db_path: str = "hkjc_data.db",
                 csv_dir: str = "hkjc_data"):
        """
        初始化數據存儲管理器
        
        Args:
            storage_type: 存儲類型 ('sqlite' 或 'csv')
            db_path: SQLite 數據庫路徑
            csv_dir: CSV 文件目錄
        """
        self.storage_type = storage_type
        
        if storage_type == "sqlite":
            self.storage = SQLiteDataStorage(db_path)
        elif storage_type == "csv":
            self.storage = CSVDataStorage(csv_dir)
        else:
            raise ValueError(f"不支持的存儲類型: {storage_type}")
    
    def save_all_data(self, data: Dict[str, pd.DataFrame], season: str = "25/26"):
        """
        保存所有數據
        
        Args:
            data: 包含各類型數據的字典
            season: 賽季
        """
        if 'race_results' in data:
            self.storage.save_race_results(data['race_results'])
        
        if 'jockey_ranking' in data:
            self.storage.save_jockey_ranking(data['jockey_ranking'], season)
        
        if 'trainer_ranking' in data:
            self.storage.save_trainer_ranking(data['trainer_ranking'], season)
    
    def get_statistics(self) -> Dict:
        """
        獲取存儲統計信息
        
        Returns:
            統計信息字典
        """
        if self.storage_type == "sqlite":
            return self.storage.get_statistics()
        else:
            return {}


# ==================== 使用範例 ====================

def example_usage():
    """使用範例"""
    
    print("=== 數據存儲管理系統示例 ===\n")
    
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
    
    # 使用 SQLite 存儲
    print("1. SQLite 存儲示例:")
    sqlite_storage = SQLiteDataStorage("test_hkjc.db")
    sqlite_storage.insert_race_results(race_data)
    
    # 查詢數據
    results = sqlite_storage.query_race_results()
    print(f"查詢結果: {len(results)} 條記錄")
    
    # 獲取統計信息
    stats = sqlite_storage.get_statistics()
    print(f"統計信息: {stats}")
    
    sqlite_storage.close()
    
    # 使用 CSV 存儲
    print("\n2. CSV 存儲示例:")
    csv_storage = CSVDataStorage("test_hkjc_data")
    csv_storage.save_race_results(race_data)
    
    # 加載數據
    loaded_data = csv_storage.load_race_results()
    print(f"加載結果: {len(loaded_data)} 條記錄")


if __name__ == "__main__":
    example_usage()
