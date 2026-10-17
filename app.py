import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# 페이지 설정
st.set_page_config(
    page_title="서울 기후 분석 대시보드",
    page_icon="🌦️",
    layout="wide",


# 제목
st.title("🌦️ 서울 기후 분석 대시보드")
st.write("서울의 장기 기온 데이터를 여러 관점에서 탐색합니다.")

# 데이터 설정
NUMERIC_COLS = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
REQUIRED_COLS = ["날짜", *NUMERIC_COLS]
DATA_PATH = Path(__file__).parent / "seoul_temperature.csv"


# 데이터 불러오기 및 전처리
@st.cache_data
def load_data(file):
    if file is not None:
        df = pd.read_csv(file, encoding="utf-8-sig")
    else:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    # 컬럼명과 날짜 앞뒤 공백 제거
    df.columns = df.columns.astype(str).str.strip()
    df["날짜"] = df["날짜"].astype("string").str.strip()

    # 필요한 컬럼 확인
    missing = [col for col in REQUIRED_COLS if col not in df.columns]

    if missing:
        raise ValueError(
            f"CSV에 필요한 컬럼이 없습니다: {', '.join(missing)}"
        )

    # 날짜 변환
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    # 기온 숫자 변환
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # 결측치 제거
    rows_before = len(df)
    df = df.dropna(subset=["날짜"] + NUMERIC_COLS).copy()
    dropped_rows = rows_before - len(df)

    if df.empty:
        raise ValueError(
            "유효한 날짜 및 기온 데이터가 없습니다. CSV 내용을 확인해 주세요."
        )

    # 날짜 관련 컬럼 생성
    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month

    # 일교차 컬럼 생성
    df["일교차(℃)"] = (
        df["최고기온(℃)"] - df["최저기온(℃)"]
    )

    # 계절 컬럼 생성
    season_map = {
        3: "봄", 4: "봄", 5: "봄",
        6: "여름", 7: "여름", 8: "여름",
        9: "가을", 10: "가을", 11: "가을",
        12: "겨울", 1: "겨울", 2: "겨울",
    }

    df["계절"] = df["월"].map(season_map)

    df = df.sort_values("날짜").reset_index(drop=True)

    return df, dropped_rows


# 사이드바
with st.sidebar:
    st.header("분석 설정")

    uploaded_file = st.file_uploader(
        "서울 기온 CSV 업로드",
        type=["csv"],
        help="CSV 파일을 업로드하세요.",
    )

    chart_type = st.radio(
        "분석 항목 선택",
        [
            "추세선 분석",
            "월별 히트맵",
            "기온 기록 TOP 10",
            "계절 분석",
            "일교차 분석",
        ],
    )


# 데이터 불러오기
try:
    if uploaded_file is not None:
        df, dropped_rows = load_data(uploaded_file)
    elif DATA_PATH.exists():
        df, dropped_rows = load_data(None)
    else:
        st.info(
            "왼쪽 사이드바에서 서울 기온 CSV 파일을 업로드해 주세요."
        )
        st.stop()

except Exception as e:
    st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
    st.stop()


# 연도 선택
min_year = int(df["연도"].min())
max_year = int(df["연도"].max())

with st.sidebar:
    if min_year < max_year:
        year_range = st.slider(
            "분석 연도 범위",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            step=1,
        )
    else:
        year_range = (min_year, max_year)
        st.info(f"데이터 연도: {min_year}년")


# 선택한 연도 필터링
filtered = df[
    df["연도"].between(year_range[0], year_range[1])
].copy()

if filtered.empty:
    st.warning("선택한 연도 범위에 데이터가 없습니다.")
    st.stop()


st.caption(
    f"분석 기간: {year_range[0]}~{year_range[1]}년 | "
    f"데이터 {len(filtered):,}건 | "
    f"결측치 등으로 제외한 행 {dropped_rows:,}건"
)


# 요약 지표
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "평균기온 평균",
    f"{filtered['평균기온(℃)'].mean():.1f} °C",
)

c2.metric(
    "기간 최고기온",
    f"{filtered['최고기온(℃)'].max():.1f} °C",
)

c3.metric(
    "기간 최저기온",
    f"{filtered['최저기온(℃)'].min():.1f} °C",
)

c4.metric(
    "평균 일교차",
    f"{filtered['일교차(℃)'].mean():.1f} °C",
)

st.divider()


# --------------------------------------------------
# 1. 추세선 분석
# --------------------------------------------------
if chart_type == "추세선 분석":

    st.subheader("📈 연도별 평균기온 추세")

    yearly = (
        filtered.groupby("연도", as_index=False)
        .agg(
            평균기온=("평균기온(℃)", "mean"),
            최고기온=("최고기온(℃)", "max"),
            최저기온=("최저기온(℃)", "min"),
        )
        .sort_values("연도")
    )

    # 5년 이동평균 계산
    yearly["5년 이동평균"] = (
        yearly["평균기온"]
        .rolling(window=5, min_periods=1)
        .mean()
    )

    fig = go.Figure()

    # 연도별 평균기온
    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["평균기온"],
            mode="lines",
            name="연도별 평균기온",
            line=dict(width=2),
            hovertemplate=(
                "%{x}년<br>"
                "평균기온: %{y:.2f} °C"
                "<extra></extra>"
            ),
        )
    )

    # 5년 이동평균: 빨간색 점선
    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["5년 이동평균"],
            mode="lines",
            name="5년 이동평균",
            line=dict(color="red", dash="dash", width=3),
            hovertemplate=(
                "%{x}년<br>"
                "5년 이동평균: %{y:.2f} °C"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        xaxis_title="연도",
        yaxis_title="기온 (°C)",
        hovermode="x unified",
        legend_title="범례",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("연도별 기온 통계")

    st.dataframe(
        yearly.round(2),
        use_container_width=True,
        hide_index=True,
    )


# --------------------------------------------------
# 2. 월별 히트맵
# --------------------------------------------------
elif chart_type == "월별 히트맵":

    st.subheader("🌡️ 연도별 · 월별 평균기온 히트맵")

    monthly = (
        filtered.groupby(["연도", "월"], as_index=False)
        .agg(평균기온=("평균기온(℃)", "mean"))
    )

    heatmap_data = monthly.pivot(
        index="연도",
        columns="월",
        values="평균기온",
    )

    # 월을 1~12로 고정
    heatmap_data = heatmap_data.reindex(
        columns=range(1, 13)
    )

    heatmap_data = heatmap_data.sort_index()

    fig = px.imshow(
        heatmap_data,
        x=list(range(1, 13)),
        y=heatmap_data.index.tolist(),
        aspect="auto",
        color_continuous_scale="RdYlBu_r",
        labels={
            "x": "월",
            "y": "연도",
            "color": "평균기온 (°C)",
        },
        origin="lower",
    )

    fig.update_xaxes(
        tickmode="array",
        tickvals=list(range(1, 13)),
        ticktext=[str(m) for m in range(1, 13)],
        title="월",
    )

    fig.update_yaxes(title="연도")

    fig.update_layout(
        coloraxis_colorbar_title="평균기온 (°C)",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "가로축은 1~12월, 세로축은 연도이며 "
        "색상은 해당 월의 평균기온을 나타냅니다."
    )


# --------------------------------------------------
# 3. 최고기온 TOP 10 / 최저기온 TOP 10
# --------------------------------------------------
elif chart_type == "기온 기록 TOP 10":

    st.subheader("🏆 기온 기록 TOP 10")

    show_cols = [
        "날짜",
        "평균기온(℃)",
        "최저기온(℃)",
        "최고기온(℃)",
        "일교차(℃)",
    ]

    hot_days = (
        filtered.sort_values(
            "최고기온(℃)",
            ascending=False,
        )
        .head(10)[show_cols]
        .copy()
    )

    cold_days = (
        filtered.sort_values(
            "최저기온(℃)",
            ascending=True,
        )
        .head(10)[show_cols]
        .copy()
    )

    hot_days["날짜"] = hot_days["날짜"].dt.strftime("%Y-%m-%d")
    cold_days["날짜"] = cold_days["날짜"].dt.strftime("%Y-%m-%d")

    left, right = st.columns(2)

    with left:
        st.markdown("### 🔥 최고기온 상위 10일")

        st.dataframe(
            hot_days.round(2),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "최고기온 TOP 10 다운로드",
            data=hot_days.to_csv(
                index=False,
                encoding="utf-8-sig",
            ),
            file_name="top10_highest_temperature.csv",
            mime="text/csv",
        )

    with right:
        st.markdown("### ❄️ 최저기온 하위 10일")

        st.dataframe(
            cold_days.round(2),
            use_container_width=True,
            hide_index=True,
