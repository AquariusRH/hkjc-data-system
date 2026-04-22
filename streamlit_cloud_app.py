"""
Streamlit Cloud 數據採集和管理應用程式
用於在 Streamlit Cloud 上部署和管理賽馬數據
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Optional

# 導入自定義模組
from data_pipeline_cloud import CloudDataPipeline
from supabase_storage import SupabaseDataStorage

# ==================== 頁面配置 ====================

st.set_page_config(
    page_title="賽馬數據採集系統",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 日誌配置 ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Session State 初始化 ====================

@st.cache_resource
def init_pipeline():
    """初始化數據管道（緩存）"""
    try:
        return CloudDataPipeline()
    except Exception as e:
        st.error(f"❌ 初始化失敗: {e}")
        return None

# ==================== 標題和介紹 ====================

st.title("🏇 賽馬數據採集和管理系統")
st.markdown("""
### 系統功能
- ✅ **自動採集**: 從香港賽馬會官方網站自動採集數據
- ✅ **雲端存儲**: 使用 Supabase 進行雲端存儲
- ✅ **數據驗證**: 自動驗證數據質量和完整性
- ✅ **數據預處理**: 自動清理和轉換數據
- ✅ **實時查詢**: 實時查詢已存儲的數據
- ✅ **統計分析**: 查看數據統計信息
""")

# ==================== 側邊欄 ====================

st.sidebar.header("⚙️ 系統設置")

# 初始化管道
pipeline = init_pipeline()

if pipeline is None:
    st.error("❌ 無法連接到 Supabase。請檢查環境變數設置。")
    st.stop()

# ==================== 主要內容區域 ====================

# 創建標籤頁
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 數據採集",
    "🔍 數據查詢",
    "📈 統計信息",
    "📚 幫助文檔"
])

# ==================== 標籤 1: 數據採集 ====================

with tab1:
    st.header("📊 數據採集")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("採集設置")
        
        # 日期選擇
        end_date = st.date_input(
            "結束日期",
            value=datetime.now().date(),
            key="end_date"
        )
        
        start_date = st.date_input(
            "開始日期",
            value=(datetime.now() - timedelta(days=7)).date(),
            key="start_date"
        )
        
        # 賽季選擇
        season = st.text_input(
            "賽季 (格式: YY/YY)",
            value="25/26",
            key="season"
        )
        
        # 採集按鈕
        if st.button("🚀 開始採集", key="collect_button"):
            if start_date > end_date:
                st.error("❌ 開始日期不能晚於結束日期")
            else:
                st.info("⏳ 正在採集數據，請稍候...")
                
                # 轉換日期格式
                start_date_str = start_date.strftime('%Y-%m-%d')
                end_date_str = end_date.strftime('%Y-%m-%d')
                
                # 運行管道
                with st.spinner("採集中..."):
                    results = pipeline.run_full_pipeline(
                        start_date_str,
                        end_date_str,
                        season
                    )
                
                # 顯示結果
                st.subheader("採集結果")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    if results['collection']:
                        st.success("✓ 採集")
                    else:
                        st.error("✗ 採集")
                
                with col2:
                    if results['validation']:
                        st.success("✓ 驗證")
                    else:
                        st.error("✗ 驗證")
                
                with col3:
                    if results['preprocessing']:
                        st.success("✓ 預處理")
                    else:
                        st.error("✗ 預處理")
                
                with col4:
                    if results['storage']:
                        st.success("✓ 存儲")
                    else:
                        st.error("✗ 存儲")
                
                # 顯示摘要
                if all(results.values()):
                    st.success("✅ 數據採集成功！")
                    
                    summary = pipeline.get_summary()
                    st.subheader("數據摘要")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(
                            "比賽記錄",
                            f"{summary.get('race_results_count', 0):,}"
                        )
                    
                    with col2:
                        st.metric(
                            "騎師數量",
                            f"{summary.get('jockey_count', 0):,}"
                        )
                    
                    with col3:
                        st.metric(
                            "練馬師數量",
                            f"{summary.get('trainer_count', 0):,}"
                        )
                else:
                    st.error("❌ 數據採集過程中出現錯誤")
    
    with col2:
        st.subheader("採集說明")
        st.write("""
        **採集流程：**
        1. 從 HKJC 官方網站採集數據
        2. 驗證數據質量和完整性
        3. 清理和轉換數據格式
        4. 上傳到 Supabase 雲端數據庫
        
        **採集內容：**
        - 比賽結果（馬號、騎師、練馬師等）
        - 騎師排名（勝、亞、季、出賽、獎金）
        - 練馬師排名（勝、亞、季、出賽、獎金）
        
        **採集時間：**
        - 首次採集可能需要 5-10 分鐘
        - 後續採集時間取決於數據量
        
        **建議：**
        - 首次採集建議從較小的日期範圍開始
        - 定期採集以保持數據最新
        """)

# ==================== 標籤 2: 數據查詢 ====================

with tab2:
    st.header("🔍 數據查詢")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("查詢比賽結果")
        
        # 查詢條件
        query_date = st.date_input(
            "查詢日期 (可選)",
            value=None,
            key="query_date"
        )
        
        query_venue = st.selectbox(
            "場地 (可選)",
            ["全部", "沙田", "跑馬地"],
            key="query_venue"
        )
        
        query_limit = st.slider(
            "返回記錄數",
            min_value=10,
            max_value=1000,
            value=100,
            step=10,
            key="query_limit"
        )
        
        # 查詢按鈕
        if st.button("🔍 查詢", key="query_button"):
            with st.spinner("查詢中..."):
                # 準備查詢條件
                date_str = query_date.strftime('%Y-%m-%d') if query_date else None
                venue_str = query_venue if query_venue != "全部" else None
                
                # 執行查詢
                results = pipeline.query_race_results(
                    date=date_str,
                    venue=venue_str,
                    limit=query_limit
                )
                
                if len(results) > 0:
                    st.success(f"✓ 查詢到 {len(results)} 條記錄")
                    st.dataframe(results, use_container_width=True)
                    
                    # 下載按鈕
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"race_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("ℹ️ 未查詢到匹配的記錄")
    
    with col2:
        st.subheader("查詢騎師排名")
        
        # 賽季選擇
        ranking_season = st.text_input(
            "賽季 (格式: YY/YY)",
            value="25/26",
            key="ranking_season"
        )
        
        # 查詢按鈕
        if st.button("🔍 查詢騎師排名", key="jockey_query_button"):
            with st.spinner("查詢中..."):
                results = pipeline.query_jockey_ranking(ranking_season)
                
                if len(results) > 0:
                    st.success(f"✓ 查詢到 {len(results)} 位騎師")
                    st.dataframe(results, use_container_width=True)
                    
                    # 下載按鈕
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"jockey_ranking_{ranking_season}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("ℹ️ 未查詢到匹配的記錄")
        
        st.divider()
        
        st.subheader("查詢練馬師排名")
        
        # 查詢按鈕
        if st.button("🔍 查詢練馬師排名", key="trainer_query_button"):
            with st.spinner("查詢中..."):
                results = pipeline.query_trainer_ranking(ranking_season)
                
                if len(results) > 0:
                    st.success(f"✓ 查詢到 {len(results)} 位練馬師")
                    st.dataframe(results, use_container_width=True)
                    
                    # 下載按鈕
                    csv = results.to_csv(index=False)
                    st.download_button(
                        label="📥 下載 CSV",
                        data=csv,
                        file_name=f"trainer_ranking_{ranking_season}.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("ℹ️ 未查詢到匹配的記錄")

# ==================== 標籤 3: 統計信息 ====================

with tab3:
    st.header("📈 統計信息")
    
    # 獲取統計信息
    with st.spinner("加載統計信息..."):
        summary = pipeline.get_summary()
    
    # 顯示統計信息
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "比賽記錄總數",
            f"{summary.get('race_results_count', 0):,}",
            delta="條"
        )
    
    with col2:
        st.metric(
            "騎師總數",
            f"{summary.get('jockey_count', 0):,}",
            delta="位"
        )
    
    with col3:
        st.metric(
            "練馬師總數",
            f"{summary.get('trainer_count', 0):,}",
            delta="位"
        )
    
    # 數據統計表
    st.subheader("詳細統計")
    
    stats_df = pd.DataFrame({
        '統計項目': ['比賽記錄', '騎師', '練馬師'],
        '數量': [
            summary.get('race_results_count', 0),
            summary.get('jockey_count', 0),
            summary.get('trainer_count', 0)
        ]
    })
    
    st.dataframe(stats_df, use_container_width=True)

# ==================== 標籤 4: 幫助文檔 ====================

with tab4:
    st.header("📚 幫助文檔")
    
    st.subheader("快速開始")
    st.write("""
    1. **設置環境變數**
       - 在 Streamlit Cloud 的 Secrets 中設置 SUPABASE_URL 和 SUPABASE_KEY
    
    2. **採集數據**
       - 在"數據採集"標籤頁選擇日期範圍並點擊"開始採集"
    
    3. **查詢數據**
       - 在"數據查詢"標籤頁查詢已存儲的數據
    
    4. **查看統計**
       - 在"統計信息"標籤頁查看數據統計
    """)
    
    st.subheader("常見問題")
    
    with st.expander("Q: 採集需要多長時間？"):
        st.write("""
        採集時間取決於日期範圍和網絡速度：
        - 1 天的數據：1-2 分鐘
        - 1 週的數據：5-10 分鐘
        - 1 個月的數據：15-30 分鐘
        - 1 年的數據：1-2 小時
        """)
    
    with st.expander("Q: 數據存儲在哪裡？"):
        st.write("""
        數據存儲在 Supabase 雲端數據庫中：
        - 自動備份
        - 可以從任何地方訪問
        - 支持複雜查詢
        - 免費額度充足
        """)
    
    with st.expander("Q: 如何更新數據？"):
        st.write("""
        您可以定期運行採集任務來更新數據：
        - 手動採集：在"數據採集"標籤頁手動運行
        - 自動採集：使用 GitHub Actions 定期運行
        """)
    
    with st.expander("Q: 如何導出數據？"):
        st.write("""
        在"數據查詢"標籤頁查詢數據後，可以點擊"下載 CSV"按鈕導出數據。
        """)
    
    st.subheader("系統要求")
    st.write("""
    - Python 3.8+
    - Streamlit
    - Supabase 帳戶
    - GitHub 帳戶（用於部署）
    """)

# ==================== 頁腳 ====================

st.markdown("---")
st.markdown("""
<div style="text-align: center; color: gray; font-size: 12px;">
    賽馬數據採集系統 v1.0 | 
    最後更新: 2026-04-22 | 
    © 2026 All Rights Reserved
</div>
""", unsafe_allow_html=True)
