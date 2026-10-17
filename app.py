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
