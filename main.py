# app.py
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_top_companies():
    url = "https://companiesmarketcap.com/"
    res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(res.text, "html.parser")

    rows = soup.select("tbody tr")[:2]
    top_companies = []
    for row in rows:
        name = row.select_one(".company-name").text.strip()
        ticker = row.select_one(".company-code").text.strip().replace("(", "").replace(")", "")
        market_cap = row.select_one(".td-right").text.strip()
        top_companies.append({"name": name, "ticker": ticker, "market_cap_text": market_cap})
  
    return top_companies


st.set_page_config(page_title="Global Market Cap Dashboard", layout="wide")
st.markdown(
    """
    <style>
        /* Streamlit 상단 메뉴, 헤더 숨기기 */
        .css-18e3th9 {padding-top: 0rem;}  /* 페이지 전체 패딩 */
        header {visibility: hidden;}       /* 기본 헤더 숨기기 */
        .block-container {padding-top: 0rem;} /* 컨텐츠 상단 여백 최소화 */
    </style>
    """,
    unsafe_allow_html=True
)
st.subheader("🌍 Global Market Overview Dashboard", divider="rainbow")
# st.divider()

# ----------------------------------------
# 1️⃣ 나스닥 종합 지수
# ----------------------------------------
nasdaq = yf.Ticker("^IXIC")
nasdaq_hist = nasdaq.history(period="6mo")
nasdaq_current = nasdaq_hist["Close"].iloc[-1]
nasdaq_prev = nasdaq_hist["Close"].iloc[-2]
nasdaq_change = (nasdaq_current - nasdaq_prev) / nasdaq_prev * 100

vix = yf.Ticker("^VIX")
vix_hist = vix.history(period="2d")  # 최근 2일 데이터
vix_current = vix_hist["Close"].iloc[-1]
vix_prev = vix_hist["Close"].iloc[-2]
vix_change = (vix_current - vix_prev) / vix_prev * 100

nasdaq = yf.Ticker("^IXIC")
hist = nasdaq.history(period="6mo")  # 1년치 데이터

# 2️⃣ 전일 대비 변화율 계산
hist['pct_change'] = hist['Close'].pct_change() * 100

# 3️⃣ -3% 이하 하락한 날 필터
down_days = hist[hist['pct_change'] <= -3]

col1, col2 = st.columns(2)
with col1.container(border=True):    
    st.subheader("📈 나스닥 종합 지수(^IXIC)")
    subs = st.columns(3)
    subs[0].metric("NASDAQ Composite", f"{nasdaq_current:,.2f}", f"{nasdaq_change:+.2f}%")
    subs[1].metric("VIX Index", f"{vix_current:.2f}", f"{vix_change:+.2f}%")
    if vix_current <= 15:
        subs[2].success("VIX ≤ 15, 매수 적기")
    else:
        subs[2].warning("VIX > 15, 매수 주의")

    if nasdaq_change <= -3:
        st.error(f"📉 NASDAQ Composite 지수 전일 대비 {nasdaq_change:+.2f}% 하락! 자산 매도 요망")
    else:
        
        # 4️⃣ 마지막 발생 날짜
        if not down_days.empty:
            last_down_date = down_days.index[-1].date()
            last_down_pct = down_days['pct_change'].iloc[-1]
            today = datetime.today().date()
            days_since_down = (today - last_down_date).days
            st.info(f"**{last_down_date} ({last_down_pct:.2f}%)로부터 {days_since_down}일 경과**")
        else:
            st.info("최근 1년 동안 -3% 이상 하락한 날 없음")

    st.markdown("#### 📈 6개월 주가 추이 비교")
    fig_nasdaq = px.line(nasdaq_hist, y="Close", title="📊 NASDAQ Composite (6개월)")
    fig_nasdaq.add_scatter(
        x=down_days.index,
        y=down_days['Close'],
        mode='markers',
        marker=dict(color='red', size=10, symbol='x'),
        name='-3% 이상 하락'
    )
    st.plotly_chart(fig_nasdaq, use_container_width=True)

# ----------------------------------------
# 2️⃣ 글로벌 시총 상위 2개 기업 조회 (웹 스크래핑)
# ----------------------------------------
with col2.container(border=True):
    st.subheader("🏆 글로벌 시가총액 TOP 2 자동 조회")
    top_companies = get_top_companies()

    # -----------------------
    # 3️⃣ yfinance에서 시총 계산
    # -----------------------
    data = {}
    for c in top_companies:
        t = yf.Ticker(c["ticker"])
        hist = t.history(period="6mo")
        try:
            shares_outstanding = t.info.get("sharesOutstanding")
        except:
            shares_outstanding = None
        if shares_outstanding:
            hist["MarketCap"] = hist["Close"] * shares_outstanding
        else:
            hist["MarketCap"] = None
        c["market_cap"] = t.info.get("marketCap", None)
        data[c["name"]] = {
            "ticker": c["ticker"],
            "hist": hist,
            "market_cap": c["market_cap"]
        }

    # -----------------------
    # 4️⃣ 시총 및 차이
    # -----------------------
    c1, c2 = top_companies[0], top_companies[1]
    cap1, cap2 = c1["market_cap"], c2["market_cap"]
    diff = cap1 - cap2 if cap1 and cap2 else None
    diff_percent = (diff / cap1 * 100) if diff else None

    col1, col2, col3 = st.columns(3)

    hist1 = data[c1["name"]]["hist"]
    if hist1["MarketCap"].notna().all():
        current1 = hist1["MarketCap"].iloc[-1]
        prev1 = hist1["MarketCap"].iloc[-2]
        change1 = (current1 - prev1) / prev1 * 100
        col1.metric(
            f"🥇 {c1['name']} 시총",
            f"${current1/1e12:.3f} T",
            f"{change1:+.2f}%"
        )
    else:
        col1.metric(f"🥇 **{c1['name']}** 시총", c1["market_cap_text"])

    # 2등 기업
    hist2 = data[c2["name"]]["hist"]
    if hist2["MarketCap"].notna().all():
        current2 = hist2["MarketCap"].iloc[-1]
        prev2 = hist2["MarketCap"].iloc[-2]
        change2 = (current2 - prev2) / prev2 * 100
        col2.metric(
            f"🥈 {c2['name']} 시총",
            f"${current2/1e12:.3f} T",
            f"{change2:+.2f}%"
        )
    else:
        col2.metric(f"🥈 {c2['name']} 시총", c2["market_cap_text"])

    # col1.metric(f"🥇 {c1['name']} 시총", f"${cap1/1e12:.3f} T" if cap1 else c1["market_cap_text"])
    # col2.metric(f"🥈 {c2['name']} 시총", f"${cap2/1e12:.3f} T" if cap2 else c2["market_cap_text"])
    if diff:
        col3.metric("시총 차이", f"${abs(diff)/1e9:.1f} B", f"{abs(diff_percent):.2f}% ↓")

    if cap1 and cap2:
        ratio = cap2 / cap1
        if ratio <= 0.9:  # 1등이 2등보다 10% 이상 큰 경우
            st.success(f"**{c1['name']} 100% 보유 : {c2['name']} 전량 매도 → 100:0**")
        else:  # 10% 미만
            st.info(f"**{c1['name']} 50% 보유 : {c2['name']} 50% 보유 → 50:50**")
    # -----------------------
    # 5️⃣ 시총 6개월 추이 차트
    # -----------------------
    st.markdown("#### 📈 6개월 시총 추이 비교")

    df_compare = pd.DataFrame({
        "Date": data[c1["name"]]["hist"].index,
        c1["name"]: data[c1["name"]]["hist"]["MarketCap"],
        c2["name"]: data[c2["name"]]["hist"]["MarketCap"],
    }).reset_index(drop=True)

    df_melt = df_compare.melt(id_vars=["Date"], var_name="Company", value_name="MarketCap")

    fig_compare = px.line(
        df_melt,
        x="Date",
        y="MarketCap",
        color="Company",
        title=f"{c1['name']} vs {c2['name']} (6개월 시총 추이)",
        labels={"MarketCap":"Market Cap (USD)"}
    )
    st.plotly_chart(fig_compare, use_container_width=True)


