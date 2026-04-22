"""
香港賽馬會 (HKJC) 數據爬蟲系統
用於從官方網站採集歷史比賽數據、騎師排名、練馬師排名等信息
"""

import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import logging
import json
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, parse_qs, urlparse
import re

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== 常數定義 ====================

# HKJC 官方網址
HKJC_BASE_URL = "https://bet.hkjc.com"
HKJC_RACING_URL = "https://racing.hkjc.com"
HKJC_INFO_URL = "https://info.cld.hkjc.com"

# 場地代碼
VENUES = {
    'ST': '沙田',
    'HV': '跑馬地',
}

# 賽道類型
TRACK_TYPES = {
    'T': '草地',
    'D': '泥地',
}

# ==================== 第一部分：GraphQL API 爬蟲 ====================

class HKJCGraphQLScraper:
    """
    使用 GraphQL API 獲取 HKJC 數據
    這是最穩定和高效的方法
    """
    
    def __init__(self):
        """初始化 GraphQL 爬蟲"""
        self.base_url = "https://info.cld.hkjc.com/graphql/base/"
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://bet.hkjc.com/',
            'Origin': 'https://bet.hkjc.com',
        }
        self.session = requests.Session()
    
    def _fetch_graphql(self, operation_name: str, query: str, variables: Dict) -> Optional[Dict]:
        """
        執行 GraphQL 查詢
        
        Args:
            operation_name: 操作名稱
            query: GraphQL 查詢字符串
            variables: 查詢變數
        
        Returns:
            API 響應數據
        """
        payload = {
            "operationName": operation_name,
            "variables": variables,
            "query": query
        }
        
        try:
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"GraphQL 請求失敗: {response.status_code}")
                return None
        
        except Exception as e:
            logger.error(f"GraphQL 請求異常: {e}")
            return None
    
    def fetch_race_results(self, date: str, venue: str) -> Optional[pd.DataFrame]:
        """
        獲取指定日期和場地的比賽結果
        
        Args:
            date: 日期 (格式: YYYY-MM-DD)
            venue: 場地 (ST 或 HV)
        
        Returns:
            比賽結果 DataFrame
        """
        query = """
        query racing($date: String, $venueCode: String) {
          raceMeetings(date: $date, venueCode: $venueCode) {
            races {
              raceNumber
              raceName
              raceStatus
              postTime
              trackCondition
              trackType
              raceDistance
              raceClass
              starters {
                no
                horse {
                  name_ch
                  name_en
                }
                jockey {
                  name_ch
                  name_en
                }
                trainer {
                  name_ch
                  name_en
                }
                weight
                draw
                rating
                last6run
                finishing {
                  position
                  dividends {
                    oddsType
                    dividend
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "date": date,
            "venueCode": venue
        }
        
        try:
            data = self._fetch_graphql("racing", query, variables)
            
            if not data or 'data' not in data:
                return None
            
            race_meetings = data['data'].get('raceMeetings', [])
            
            results = []
            for meeting in race_meetings:
                races = meeting.get('races', [])
                
                for race in races:
                    race_no = race.get('raceNumber')
                    starters = race.get('starters', [])
                    
                    for starter in starters:
                        finishing = starter.get('finishing', {})
                        
                        result = {
                            '日期': date,
                            '場地': VENUES.get(venue, venue),
                            '場地代碼': venue,
                            '賽次': race_no,
                            '馬號': starter.get('no'),
                            '馬名': starter.get('horse', {}).get('name_ch', ''),
                            '騎師': starter.get('jockey', {}).get('name_ch', ''),
                            '練馬師': starter.get('trainer', {}).get('name_ch', ''),
                            '排位': starter.get('draw'),
                            '負磅': starter.get('weight'),
                            '評分': starter.get('rating'),
                            '近績': starter.get('last6run', ''),
                            '名次': finishing.get('position'),
                            '賽道類型': TRACK_TYPES.get(race.get('trackType'), ''),
                            '比賽距離': race.get('raceDistance'),
                            '賽事等級': race.get('raceClass', ''),
                        }
                        
                        results.append(result)
            
            if results:
                return pd.DataFrame(results)
            else:
                return None
        
        except Exception as e:
            logger.error(f"獲取比賽結果失敗: {e}")
            return None
    
    def fetch_jockey_ranking(self, season: str = "25/26") -> Optional[pd.DataFrame]:
        """
        獲取騎師排名
        
        Args:
            season: 賽季 (格式: YY/YY)
        
        Returns:
            騎師排名 DataFrame
        """
        query = """
        query rw_GetJockeyRanking($season: String) {
          jockeyStat(season: $season) {
            code
            name_ch
            name_en
            status
            id
            isCurSsn
            season
            ssnStat {
              numFirst
              numSecond
              numThird
              numFourth
              numFifth
              numStarts
              stakeWon
              trk
              ven
            }
            dhStat {
              numFirst
              numSecond
              numThird
              numFourth
              numFifth
              numStarts
              stakeWon
              trk
              ven
            }
          }
        }
        """
        
        variables = {"season": season}
        
        try:
            data = self._fetch_graphql("rw_GetJockeyRanking", query, variables)
            
            if not data or 'data' not in data:
                return None
            
            jockey_stats = data['data'].get('jockeyStat', [])
            
            results = []
            for jockey in jockey_stats:
                ssn_stat = jockey.get('ssnStat', {})
                
                result = {
                    '騎師': jockey.get('name_ch', ''),
                    '騎師英文': jockey.get('name_en', ''),
                    '勝': ssn_stat.get('numFirst', 0),
                    '亞': ssn_stat.get('numSecond', 0),
                    '季': ssn_stat.get('numThird', 0),
                    '出賽': ssn_stat.get('numStarts', 0),
                    '獎金': ssn_stat.get('stakeWon', 0),
                    '賽季': season,
                }
                
                results.append(result)
            
            if results:
                return pd.DataFrame(results)
            else:
                return None
        
        except Exception as e:
            logger.error(f"獲取騎師排名失敗: {e}")
            return None
    
    def fetch_trainer_ranking(self, season: str = "25/26") -> Optional[pd.DataFrame]:
        """
        獲取練馬師排名
        
        Args:
            season: 賽季 (格式: YY/YY)
        
        Returns:
            練馬師排名 DataFrame
        """
        query = """
        query rw_GetTrainerRanking($season: String) {
          trainerStat(season: $season) {
            code
            name_ch
            name_en
            status
            id
            isCurSsn
            season
            ssnStat {
              numFirst
              numSecond
              numThird
              numFourth
              numFifth
              numStarts
              stakeWon
              trk
              ven
            }
            dhStat {
              numFirst
              numSecond
              numThird
              numFourth
              numFifth
              numStarts
              stakeWon
              trk
              ven
            }
          }
        }
        """
        
        variables = {"season": season}
        
        try:
            data = self._fetch_graphql("rw_GetTrainerRanking", query, variables)
            
            if not data or 'data' not in data:
                return None
            
            trainer_stats = data['data'].get('trainerStat', [])
            
            results = []
            for trainer in trainer_stats:
                ssn_stat = trainer.get('ssnStat', {})
                
                result = {
                    '練馬師': trainer.get('name_ch', ''),
                    '練馬師英文': trainer.get('name_en', ''),
                    '勝': ssn_stat.get('numFirst', 0),
                    '亞': ssn_stat.get('numSecond', 0),
                    '季': ssn_stat.get('numThird', 0),
                    '出賽': ssn_stat.get('numStarts', 0),
                    '獎金': ssn_stat.get('stakeWon', 0),
                    '賽季': season,
                }
                
                results.append(result)
            
            if results:
                return pd.DataFrame(results)
            else:
                return None
        
        except Exception as e:
            logger.error(f"獲取練馬師排名失敗: {e}")
            return None


# ==================== 第二部分：HTML 爬蟲 (備用方案) ====================

class HKJCHTMLScraper:
    """
    使用 HTML 爬蟲獲取 HKJC 數據
    作為 GraphQL 爬蟲的備用方案
    """
    
    def __init__(self):
        """初始化 HTML 爬蟲"""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        self.session = requests.Session()
    
    def fetch_race_calendar(self, year: int, month: int) -> Optional[List[Tuple[str, str]]]:
        """
        獲取指定月份的比賽日期
        
        Args:
            year: 年份
            month: 月份
        
        Returns:
            [(日期, 場地), ...] 的列表
        """
        try:
            # 構建日曆 URL
            url = f"{HKJC_RACING_URL}/zh-hk/racing/calendar?year={year}&month={month}"
            
            response = self.session.get(url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析日期和場地
            race_dates = []
            
            # 查找所有比賽日期的鏈接
            date_links = soup.find_all('a', class_='race-date-link')
            
            for link in date_links:
                date_str = link.get('data-date', '')
                venue = link.get('data-venue', '')
                
                if date_str and venue:
                    race_dates.append((date_str, venue))
            
            return race_dates if race_dates else None
        
        except Exception as e:
            logger.error(f"獲取比賽日期失敗: {e}")
            return None


# ==================== 第三部分：數據採集管理器 ====================

class HKJCDataCollector:
    """
    HKJC 數據採集管理器
    協調各個爬蟲組件進行數據採集
    """
    
    def __init__(self):
        """初始化數據採集器"""
        self.graphql_scraper = HKJCGraphQLScraper()
        self.html_scraper = HKJCHTMLScraper()
        self.collected_data = {}
    
    def collect_historical_data(self, 
                               start_date: str,
                               end_date: str,
                               venues: List[str] = ['ST', 'HV']) -> Dict[str, pd.DataFrame]:
        """
        採集指定日期範圍內的歷史數據
        
        Args:
            start_date: 開始日期 (YYYY-MM-DD)
            end_date: 結束日期 (YYYY-MM-DD)
            venues: 場地列表 (ST, HV)
        
        Returns:
            包含採集數據的字典
        """
        logger.info(f"開始採集 {start_date} 到 {end_date} 的歷史數據")
        
        all_results = []
        
        # 生成日期列表
        current_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
        
        while current_date <= end_datetime:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # 對每個場地採集數據
            for venue in venues:
                logger.info(f"採集 {date_str} {VENUES.get(venue, venue)} 的數據")
                
                result_df = self.graphql_scraper.fetch_race_results(date_str, venue)
                
                if result_df is not None:
                    all_results.append(result_df)
                    logger.info(f"成功採集 {len(result_df)} 條記錄")
                else:
                    logger.warning(f"未能採集 {date_str} {venue} 的數據")
                
                # 避免請求過於頻繁
                time.sleep(1)
            
            current_date += timedelta(days=1)
        
        if all_results:
            combined_df = pd.concat(all_results, ignore_index=True)
            self.collected_data['race_results'] = combined_df
            logger.info(f"共採集 {len(combined_df)} 條比賽記錄")
            return {'race_results': combined_df}
        else:
            logger.warning("未採集到任何數據")
            return {}
    
    def collect_jockey_rankings(self, season: str = "25/26") -> Optional[pd.DataFrame]:
        """
        採集騎師排名
        
        Args:
            season: 賽季
        
        Returns:
            騎師排名 DataFrame
        """
        logger.info(f"採集 {season} 賽季的騎師排名")
        
        jockey_df = self.graphql_scraper.fetch_jockey_ranking(season)
        
        if jockey_df is not None:
            self.collected_data['jockey_ranking'] = jockey_df
            logger.info(f"成功採集 {len(jockey_df)} 位騎師的排名")
            return jockey_df
        else:
            logger.warning("未能採集騎師排名")
            return None
    
    def collect_trainer_rankings(self, season: str = "25/26") -> Optional[pd.DataFrame]:
        """
        採集練馬師排名
        
        Args:
            season: 賽季
        
        Returns:
            練馬師排名 DataFrame
        """
        logger.info(f"採集 {season} 賽季的練馬師排名")
        
        trainer_df = self.graphql_scraper.fetch_trainer_ranking(season)
        
        if trainer_df is not None:
            self.collected_data['trainer_ranking'] = trainer_df
            logger.info(f"成功採集 {len(trainer_df)} 位練馬師的排名")
            return trainer_df
        else:
            logger.warning("未能採集練馬師排名")
            return None
    
    def collect_all_data(self, 
                        start_date: str,
                        end_date: str,
                        season: str = "25/26") -> Dict[str, pd.DataFrame]:
        """
        採集所有類型的數據
        
        Args:
            start_date: 開始日期
            end_date: 結束日期
            season: 賽季
        
        Returns:
            包含所有採集數據的字典
        """
        logger.info("開始採集所有數據")
        
        # 採集比賽結果
        self.collect_historical_data(start_date, end_date)
        
        # 採集騎師排名
        self.collect_jockey_rankings(season)
        
        # 採集練馬師排名
        self.collect_trainer_rankings(season)
        
        logger.info("數據採集完成")
        
        return self.collected_data


# ==================== 使用範例 ====================

def example_usage():
    """使用範例"""
    
    print("=== HKJC 數據爬蟲系統示例 ===\n")
    
    # 初始化數據採集器
    collector = HKJCDataCollector()
    
    # 採集最近 7 天的數據
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    
    print(f"採集 {start_date} 到 {end_date} 的數據\n")
    
    # 採集所有數據
    data = collector.collect_all_data(start_date, end_date)
    
    # 顯示採集結果
    for data_type, df in data.items():
        print(f"\n{data_type}:")
        print(f"  記錄數: {len(df)}")
        print(f"  列數: {len(df.columns)}")
        if len(df) > 0:
            print(f"  樣本:\n{df.head()}")


if __name__ == "__main__":
    example_usage()
