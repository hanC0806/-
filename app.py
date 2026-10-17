import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="서울 기후 분석 대시보드",
    page_icon="🌦️",
    layout="wide",
)

st.title("🌦️ 서울 기후 분석 대시보드")
st.write("서울의 장기 기온 데이터를 여러 관점에서 탐색합니다.")

NUMERIC_COLS = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
REQUIRED_COLS = ["날짜", "지점", *NUMERIC_COLS]


@st.cache_data
def load_data(file):
    """CSV를 읽고 날짜/기온을 정리한 뒤 필수 값의 결측 행을 제거합니다."""
    if file is None:
        df = pd.read_csv("seoul_temperature.csv", encoding="utf-8-sig")
    else:
        df = pd.read_csv(file, encoding="utf-8-sig")

    df.columns = df.columns.astype(str).str.strip()
    missing = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing:
        raise ValueError(
            "CSV에 필요한 컬럼이 없습니다: " + ", ".join(missing)
        )

    # 날짜 문자열 앞의 탭 문자 및 앞뒤 공백 제거
    df["날짜"] = df["날짜"].astype("string").str.strip()
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")

    # 기온 컬럼을 숫자로 변환할 수 없는 값은 결측치 처리
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    rows_before = len(df)
    df = df.dropna(subset=["날짜", *NUMERIC_COLS]).copy()
    dropped_rows = rows_before - len(df)

    df["연도"] = df["날짜"].dt.year
    df["월"] = df["날짜"].dt.month
    df["월 이름"] = df["월"].astype(str).str.zfill(2) + "월"
    df["일교차(℃)"] = df["최고기온(℃)"] - df["최저기온(℃)"]
    df["계절"] = df["월"].map({
        3: "봄", 4: "봄", 5: "봄",
        6: "여름", 7: "여름", 8: "여름",
        9: "가을", 10: "가을", 11: "가을",
        12: "겨울", 1: "겨울", 2: "겨울",
    })
    # 계절 순서를 그래프에 일관되게 표시
    df["계절"] = pd.Categorical(
        df["계절"], categories=["봄", "여름", "가을", "겨울"], ordered=True
    )
    return df.sort_values("날짜"), dropped_rows


with st.sidebar:
    st.header("분석 설정")
    uploaded_file = st.file_uploader(
        "서울 기온 CSV 업로드",
        type=["csv"],
        help="업로드하지 않으면 같은 폴더의 seoul_temperature.csv를 읽습니다.",
    )

try:
    df, dropped_rows = load_data(uploaded_file)
except FileNotFoundError:
    st.error(
        "`seoul_temperature.csv` 파일을 찾을 수 없습니다. "
        "CSV를 앱 파일과 같은 폴더에 두거나 사이드바에서 업로드하세요."
    )
    st.stop()
except Exception as exc:
    st.error(f"데이터를 불러오는 중 문제가 발생했습니다: {exc}")
    st.stop()

if df.empty:
    st.error("날짜와 기온 값이 모두 유효한 데이터가 없습니다.")
    st.stop()

min_year = int(df["연도"].min())
max_year = int(df["연도"].max())

with st.sidebar:
    chart_type = st.radio(
        "분석 항목 선택",
        ["추세선 분석", "월별 히트맵", "계절 분석", "기록 조회", "일교차 분석"],
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
    f"유효 데이터 {len(filtered):,}건 · 결측/날짜 오류로 제외한 행 {dropped_rows:,}건"
)

# 상단 요약 지표
c1, c2, c3, c4 = st.columns(4)
c1.metric("평균기온 평균", f"{filtered['평균기온(℃)'].mean():.1f} °C")
c2.metric("기간 최고기온", f"{filtered['최고기온(℃)'].max():.1f} °C")
c3.metric("기간 최저기온", f"{filtered['최저기온(℃)'].min():.1f} °C")
c4.metric("평균 일교차", f"{filtered['일교차(℃)'].mean():.1f} °C")

st.divider()

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
        window=5, min_periods=1
    ).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=yearly["연도"], y=yearly["평균기온"],
        mode="lines", name="연도별 평균기온",
        hovertemplate="%{x}년<br>평균기온 %{y:.2f} °C<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=yearly["연도"], y=yearly["5년 이동평균"],
        mode="lines", name="5년 이동평균",
        line=dict(dash="dash", width=3),
        hovertemplate="%{x}년<br>5년 이동평균 %{y:.2f} °C<extra></extra>",
    ))
    fig.update_layout(
        xaxis_title="연도", yaxis_title="기온 (°C)",
        hovermode="x unified", legend_title="범례",
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("**연도별 요약 통계**")
    st.dataframe(yearly.round(2), use_container_width=True, hide_index=True)

elif chart_type == "월별 히트맵":
    st.subheader("연도별 · 월별 평균기온 히트맵")
    monthly = (
        filtered.groupby(["연도", "월"], as_index=False, observed=True)
        ["평균기온(℃)"].mean()
    )
    heatmap_data = monthly.pivot(
        index="연도", columns="월", values="평균기온(℃)"
    ).reindex(columns=range(1, 13))
    heatmap_data.columns = [f"{month}월" for month in heatmap_data.columns]

    fig = px.imshow(
        heatmap_data,
        aspect="auto",
        color_continuous_scale="RdYlBu_r",
        labels=dict(x="월", y="연도", color="평균기온 (°C)"),
    )
    fig.update_layout(coloraxis_colorbar_title="°C")
    st.plotly_chart(fig, use_container_width=True)
    st.caption("각 칸은 해당 연도·월의 일별 평균기온 평균입니다. 관측값이 없는 달은 비어 있습니다.")

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
        labels={"계절": "계절", "기온(℃)": "기온 (°C)"},
        title="계절별 평균·최고·최저 기온",
    )
    st.plotly_chart(fig, use_container_width=True)

    box = px.box(
        filtered,
        x="계절",
        y="평균기온(℃)",
        category_orders={"계절": season_order},
        points=False,
        labels={"계절": "계절", "평균기온(℃)": "일별 평균기온 (°C)"},
        title="계절별 일별 평균기온 분포",
    )
    st.plotly_chart(box, use_container_width=True)
    st.dataframe(seasonal.round(2), use_container_width=True, hide_index=True)

elif chart_type == "기록 조회":
    st.subheader("기간 내 기온 기록")
    record_type = st.selectbox(
        "조회할 기록",
        ["가장 더운 날(최고기온)", "가장 추운 날(최저기온)", "평균기온이 가장 높은 날", "평균기온이 가장 낮은 날"],
    )
    record_count = st.slider("표시할 기록 수", min_value=1, max_value=50, value=10)

    if record_type == "가장 더운 날(최고기온)":
        sort_col, ascending = "최고기온(℃)", False
    elif record_type == "가장 추운 날(최저기온)":
        sort_col, ascending = "최저기온(℃)", True
    elif record_type == "평균기온이 가장 높은 날":
        sort_col, ascending = "평균기온(℃)", False
    else:
        sort_col, ascending = "평균기온(℃)", True

    records = filtered.sort_values(sort_col, ascending=ascending).head(record_count)
    show_cols = ["날짜", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)", "일교차(℃)"]
    st.dataframe(
        records[show_cols].assign(날짜=records["날짜"].dt.strftime("%Y-%m-%d")).round(2),
        use_container_width=True,
        hide_index=True,
    )
    st.download_button(
        "조회 결과 CSV 다운로드",
        data=records[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name="seoul_temperature_records.csv",
        mime="text/csv",
    )

elif chart_type == "일교차 분석":
    st.subheader("일교차 분석")
    daily_range = filtered.sort_values("날짜").copy()
    fig = px.line(
        daily_range,
        x="날짜",
        y="일교차(℃)",
        labels={"날짜": "날짜", "일교차(℃)": "일교차 (°C)"},
        title="일별 최고·최저기온 차이",
    )
    st.plotly_chart(fig, use_container_width=True)

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

    yearly_range = (
        filtered.groupby("연도", as_index=False)
        .agg(평균일교차=("일교차(℃)", "mean"))
        .sort_values("연도")
    )
    fig2 = px.line(
        yearly_range,
        x="연도",
        y="평균일교차",
        markers=True,
        labels={"연도": "연도", "평균일교차": "평균 일교차 (°C)"},
        title="연도별 평균 일교차",
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()
with st.expander("데이터 미리보기"):
    st.dataframe(
        filtered[["날짜", "연도", "평균기온(℃)", "최저기온(℃)", "최고기온(℃)", "일교차(℃)"]]
        .assign(날짜=lambda x: x["날짜"].dt.strftime("%Y-%m-%d"))
        .tail(100),
        use_container_width=True,
        hide_index=True,
    )

st.caption("기온 단위는 °C입니다. 이동평균은 연도별 평균기온을 기준으로 계산하며, 결측치/날짜 변환 오류가 있는 행은 제외합니다.")
