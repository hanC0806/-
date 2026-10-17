import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="서울 기후 분석 대시보드",
    page_icon="🌦️",
    layout="wide",
)

st.title("🌦️ 서울 기후 분석 대시보드")
st.write("서울의 장기 기온 데이터를 여러 관점에서 탐색합니다.")

NUMERIC_COLS = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
REQUIRED_COLS = ["날짜", "지점", *NUMERIC_COLS]
DATA_PATH = Path(__file__).parent / "seoul_temperature.csv"


@st.cache_data
def load_data(file):
    if file is None:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    else:
        df = pd.read_csv(file, encoding="utf-8-sig")

    df.columns = df.columns.astype(str).str.strip()

    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(
            "CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing)
        )

    df["날짜"] = pd.to_datetime(
        df["날짜"].astype("string").str.strip(),
        errors="coerce",
    )

    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    rows_before = len(df)
    df = df.dropna(subset=["날짜", *NUMERIC_COLS]).copy()
    dropped_rows = rows_before - len(df)

    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month

    # 일교차 컬럼 생성
    df["일교차(℃)"] = df["최고기온(℃)"] - df["최저기온(℃)"]

    df["계절"] = df["월"].map({
        12: "겨울",
        1: "겨울",
        2: "겨울",
        3: "봄",
        4: "봄",
        5: "봄",
        6: "여름",
        7: "여름",
        8: "여름",
        9: "가을",
        10: "가을",
        11: "가을",
    })

    df["계절"] = pd.Categorical(
        df["계절"],
        categories=["봄", "여름", "가을", "겨울"],
        ordered=True,
    )

    return df.sort_values("날짜"), dropped_rows


with st.sidebar:
    st.header("분석 설정")

    uploaded_file = st.file_uploader(
        "서울 기온 CSV 업로드",
        type=["csv"],
        help="CSV를 업로드하지 않으면 앱과 같은 폴더의 seoul_temperature.csv를 사용합니다.",
    )

try:
    df, dropped_rows = load_data(uploaded_file)

except FileNotFoundError:
    st.error(
        "`seoul_temperature.csv` 파일을 찾을 수 없습니다. "
        "CSV 파일을 app.py와 같은 폴더에 추가하거나 "
        "사이드바에서 직접 업로드하세요."
    )
    st.stop()

except Exception as exc:
    st.error(f"데이터를 불러오는 중 문제가 발생했습니다: {exc}")
    st.stop()

if df.empty:
    st.error("유효한 날짜와 기온 데이터가 없습니다.")
    st.stop()


min_year = int(df["연도"].min())
max_year = int(df["연도"].max())

with st.sidebar:
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

    if min_year == max_year:
        year_range = (min_year, max_year)
        st.info(f"데이터 연도: {min_year}년")
    else:
        year_range = st.slider(
            "연도 범위",
            min_value=min_year,
            max_value=max_year,
            value=(min_year, max_year),
            step=1,
        )


filtered = df[
    df["연도"].between(year_range[0], year_range[1])
].copy()

if filtered.empty:
    st.warning("선택한 연도 범위에 데이터가 없습니다.")
    st.stop()


st.caption(
    f"분석 기간: {year_range[0]}–{year_range[1]}년 · "
    f"유효 데이터 {len(filtered):,}건 · "
    f"결측/날짜 오류로 제외한 행 {dropped_rows:,}건"
)


# 상단 요약 지표
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


# 1. 추세선 분석
if chart_type == "추세선 분석":
    st.subheader("연도별 평균기온 추세")

    yearly = (
        filtered.groupby("연도", as_index=False)
        .agg(
            평균기온=("평균기온(℃)", "mean"),
            최고기온=("최고기온(℃)", "max"),
            최저기온=("최저기온(℃)", "min"),
        )
        .sort_values("연도")
    )

    yearly["5년 이동평균"] = yearly["평균기온"].rolling(
        window=5,
        min_periods=1,
    ).mean()

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["평균기온"],
            mode="lines",
            name="연도별 평균기온",
            hovertemplate="%{x}년<br>평균기온 %{y:.2f} °C<extra></extra>",
        )
    )

    fig.add_trace(
        go.Scatter(
            x=yearly["연도"],
            y=yearly["5년 이동평균"],
            mode="lines",
            name="5년 이동평균",
            line=dict(dash="dash", width=3),
            hovertemplate="%{x}년<br>5년 이동평균 %{y:.2f} °C<extra></extra>",
        )
    )

    fig.update_layout(
        xaxis_title="연도",
        yaxis_title="기온 (°C)",
        hovermode="x unified",
        legend_title="범례",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("### 연도별 요약 통계")
    st.dataframe(
        yearly.round(2),
        use_container_width=True,
        hide_index=True,
    )


# 2. 월별 히트맵
elif chart_type == "월별 히트맵":
    st.subheader("연도별 · 월별 평균기온 히트맵")

    monthly = (
        filtered.groupby(["연도", "월"], as_index=False)
        .agg(평균기온=("평균기온(℃)", "mean"))
    )

    heatmap_data = monthly.pivot(
        index="연도",
        columns="월",
        values="평균기온",
    )

    # 월 1~12를 가로축에 표시
    heatmap_data = heatmap_data.reindex(columns=range(1, 13))
    heatmap_data = heatmap_data.sort_index(ascending=True)

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
        ticktext=[str(month) for month in range(1, 13)],
        title="월",
    )

    fig.update_yaxes(
        title="연도",
        dtick=max(1, len(heatmap_data.index) // 20),
    )

    fig.update_layout(
        coloraxis_colorbar_title="평균기온 (°C)",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "가로축은 1~12월, 세로축은 연도이며 "
        "색상은 해당 연도·월의 평균기온을 나타냅니다. "
        "관측값이 없는 달은 비어 있습니다."
    )


# 3. 최고기온 TOP 10 및 최저기온 TOP 10
elif chart_type == "기온 기록 TOP 10":
    st.subheader("기온 기록 TOP 10")

    show_cols = [
        "날짜",
        "평균기온(℃)",
        "최저기온(℃)",
        "최고기온(℃)",
        "일교차(℃)",
    ]

    hot_days = (
        filtered.sort_values("최고기온(℃)", ascending=False)
        .head(10)[show_cols]
        .copy()
    )

    cold_days = (
        filtered.sort_values("최저기온(℃)", ascending=True)
        .head(10)[show_cols]
        .copy()
    )

    hot_days["날짜"] = hot_days["날짜"].dt.strftime("%Y-%m-%d")
    cold_days["날짜"] = cold_days["날짜"].dt.strftime("%Y-%m-%d")

    left, right = st.columns(2)

    with left:
        st.markdown("### 최고기온 상위 10일")
        st.dataframe(
            hot_days.round(2),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "최고기온 TOP 10 CSV 다운로드",
            data=hot_days.to_csv(
                index=False,
                encoding="utf-8-sig",
            ).encode("utf-8-sig"),
            file_name="seoul_top10_highest_temperature.csv",
            mime="text/csv",
        )

    with right:
        st.markdown("### 최저기온 하위 10일")
        st.dataframe(
            cold_days.round(2),
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "최저기온 TOP 10 CSV 다운로드",
            data=cold_days.to_csv(
                index=False,
                encoding="utf-8-sig",
            ).encode("utf-8-sig"),
            file_name="seoul_top10_lowest_temperature.csv",
            mime="text/csv",
        )


# 4. 계절 분석
elif chart_type == "계절 분석":
    st.subheader("계절별 기온 비교")

    season_order = ["봄", "여름", "가을", "겨울"]

    seasonal = (
        filtered.groupby("계절", observed=False)
        .agg(
            평균기온=("평균기온(℃)", "mean"),
            최고기온=("최고기온(℃)", "max"),
            최저기온=("최저기온(℃)", "min"),
        )
        .reindex(season_order)
        .reset_index()
    )

    season_long = seasonal.melt(
        id_vars="계절",
        value_vars=["평균기온", "최고기온", "최저기온"],
        var_name="기온 항목",
        value_name="기온(℃)",
    )

    fig = px.bar(
        season_long,
        x="계절",
        y="기온(℃)",
        color="기온 항목",
        barmode="group",
        category_orders={"계절": season_order},
        labels={
            "계절": "계절",
            "기온(℃)": "기온 (°C)",
        },
        title="계절별 평균·최고·최저 기온",
    )

    st.plotly_chart(fig, use_container_width=True)

    box = px.box(
        filtered,
        x="계절",
        y="평균기온(℃)",
        category_orders={"계절": season_order},
        points=False,
        labels={
            "계절": "계절",
            "평균기온(℃)": "일별 평균기온 (°C)",
        },
        title="계절별 일별 평균기온 분포",
    )

    st.plotly_chart(box, use_container_width=True)

    st.markdown("### 계절별 요약 통계")
    st.dataframe(
        seasonal.round(2),
        use_container_width=True,
        hide_index=True,
    )


# 5. 일교차 분석
elif chart_type == "일교차 분석":
    st.subheader("일교차 분석")

    # 일별 일교차 그래프
    daily_range = filtered.sort_values("날짜").copy()

    fig = px.line(
        daily_range,
        x="날짜",
        y="일교차(℃)",
        labels={
            "날짜": "날짜",
            "일교차(℃)": "일교차 (°C)",
        },
        title="일별 최고·최저기온 차이",
    )

    st.plotly_chart(fig, use_container_width=True)

    # 최대 및 최소 일교차
    a, b = st.columns(2)

    widest = filtered.loc[filtered["일교차(℃)"].idxmax()]
    narrowest = filtered.loc[filtered["일교차(℃)"].idxmin()]

    a.metric(
        "가장 큰 일교차",
        f"{widest['일교차(℃)']:.1f} °C",
        widest["날짜"].strftime("%Y-%m-%d"),
    )

    b.metric(
        "가장 작은 일교차",
        f"{narrowest['일교차(℃)']:.1f} °C",
        narrowest["날짜"].strftime("%Y-%m-%d"),
    )

    # 연도별 평균 일교차
    yearly_range = (
        filtered.groupby("연도", as_index=False)
        .agg(평균일교차=("일교차(℃)", "mean"))
        .sort_values("연도")
    )

    st.markdown("### 연도별 평균 일교차")

    fig2 = px.line(
        yearly_range,
        x="연도",
        y="평균일교차",
        markers=True,
        labels={
            "연도": "연도",
            "평균일교차": "평균 일교차 (°C)",
        },
        title="연도별 평균 일교차 변화",
    )

    fig2.update_layout(
        xaxis_title="연도",
        yaxis_title="평균 일교차 (°C)",
        hovermode="x unified",
    )

    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(
        yearly_range.round(2),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "연도별 평균 일교차 CSV 다운로드",
        data=yearly_range.to_csv(
            index=False,
            encoding="utf-8-sig",
        ).encode("utf-8-sig"),
        file_name="seoul_yearly_average_temperature_range.csv",
        mime="text/csv",
    )


st.divider()

with st.expander("데이터 미리보기"):
    preview_cols = [
        "날짜",
        "연도",
        "월",
        "평균기온(℃)",
        "최저기온(℃)",
        "최고기온(℃)",
        "일교차(℃)",
    ]

    preview = filtered[preview_cols].tail(100).copy()
    preview["날짜"] = preview["날짜"].dt.strftime("%Y-%m-%d")

    st.dataframe(
        preview,
        use_container_width=True,
        hide_index=True,
    )

st.caption(
    "기온 단위는 °C입니다. "
    "일교차는 최고기온에서 최저기온을 뺀 값이며, "
    "결측치 또는 날짜 변환 오류가 있는 행은 제외합니다."
)
- 5년 이동평균은 연도별 평균기온 시계열의 최근 5개 행을 기준으로 계산합니다. 데이터가 없는 연도가 있다면 관측된 연도 행 기준으로 계산됩니다.
- 계절은 기상학적 월 기준으로 봄(3–5월), 여름(6–8월), 가을(9–11월), 겨울(12–2월)로 구분합니다.
- 기록 조회에서 내려받는 CSV는 선택 기간 및 기록 종류에 따라 필터링된 결과입니다.
