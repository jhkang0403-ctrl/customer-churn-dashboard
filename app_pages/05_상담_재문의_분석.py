import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import common as c

SMALL_SAMPLE_THRESHOLD = 20
WORST_CHANNEL = "이메일"
WORST_CATEGORY = "기타"


@st.cache_data
def load_consultations() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(c.DATA_DIR, "data_consultations.csv"), encoding="utf-8-sig")
    df["is_recontact_flag"] = df["is_recontact"].astype(str).str.strip().str.upper() == "Y"
    return df


def channel_rate(df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby("channel").agg(n=("consult_id", "size"), recontact_n=("is_recontact_flag", "sum")).reset_index()
    summary["재문의율"] = summary["recontact_n"] / summary["n"] * 100
    return summary.sort_values("재문의율", ascending=False).reset_index(drop=True)


def category_rate(df: pd.DataFrame) -> pd.DataFrame:
    summary = df.groupby("category").agg(n=("consult_id", "size"), recontact_n=("is_recontact_flag", "sum")).reset_index()
    summary["재문의율"] = summary["recontact_n"] / summary["n"] * 100
    return summary.sort_values("재문의율", ascending=False).reset_index(drop=True)


def channel_category_matrix(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cross = (
        df.groupby(["channel", "category"])
        .agg(n=("consult_id", "size"), recontact_n=("is_recontact_flag", "sum"))
        .reset_index()
    )
    cross["재문의율"] = cross["recontact_n"] / cross["n"] * 100
    rate_matrix = cross.pivot(index="channel", columns="category", values="재문의율")
    n_matrix = cross.pivot(index="channel", columns="category", values="n")
    return rate_matrix, n_matrix


def build_bar(summary: pd.DataFrame, x_col: str, highlight: str) -> go.Figure:
    colors = [c.COLOR_CRITICAL if v == highlight else c.COLOR_NEUTRAL for v in summary[x_col]]
    fig = go.Figure(
        go.Bar(
            x=summary[x_col],
            y=summary["재문의율"],
            marker_color=colors,
            text=summary["재문의율"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            customdata=summary[["n", "recontact_n"]].values,
            hovertemplate="<b>%{x}</b><br>재문의율: %{y:.1f}%<br>표본수: %{customdata[0]}건<extra></extra>",
        )
    )
    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(showlegend=False, yaxis_title="재문의율 (%)", yaxis_ticksuffix="%")
    return fig


def build_heatmap(rate_matrix: pd.DataFrame, n_matrix: pd.DataFrame) -> go.Figure:
    text = rate_matrix.copy().astype(object)
    for ch in rate_matrix.index:
        for cat in rate_matrix.columns:
            rate = rate_matrix.loc[ch, cat]
            n = n_matrix.loc[ch, cat]
            mark = "*" if n < SMALL_SAMPLE_THRESHOLD else ""
            text.loc[ch, cat] = f"{rate:.1f}%{mark}<br>(n={n})"

    fig = go.Figure(
        go.Heatmap(
            z=rate_matrix.values,
            x=rate_matrix.columns,
            y=rate_matrix.index,
            colorscale=[[0, c.COLOR_NEUTRAL], [1, c.COLOR_CRITICAL]],
            text=text.values,
            texttemplate="%{text}",
            hovertemplate="채널 %{y} × 문의유형 %{x}<br>재문의율 %{z:.1f}%<extra></extra>",
            colorbar=dict(title="재문의율(%)", ticksuffix="%"),
        )
    )
    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(xaxis_title="문의유형", yaxis_title="채널")
    return fig


c.render_hero("상담 재문의 분석", "채널별·문의유형별 재문의율 — 어떤 조합이 특히 재문의가 잦은가")

df = load_consultations()

overall_n = len(df)
overall_rate = df["is_recontact_flag"].mean() * 100

ch_summary = channel_rate(df)
cat_summary = category_rate(df)
best_ch = ch_summary.iloc[-1]
worst_ch = ch_summary.iloc[0]

col1, col2, col3 = st.columns(3)
with col1:
    c.render_stat_tile("전체 재문의율", f"{overall_rate:.1f}%", caption=f"표본 {overall_n:,}건 (2024-01~2025-02)")
with col2:
    c.render_stat_tile(
        "채널 최대 격차",
        f"{worst_ch['channel']} {worst_ch['재문의율']:.1f}%",
        caption=f"최저 {best_ch['channel']} {best_ch['재문의율']:.1f}% 대비",
    )
with col3:
    c.render_stat_tile("문의유형 편차", f"{cat_summary['재문의율'].max() - cat_summary['재문의율'].min():.1f}%p", caption="채널 편차보다 훨씬 작음")

st.divider()

col_ch, col_cat = st.columns(2)
with col_ch:
    st.subheader("채널별 재문의율")
    st.plotly_chart(build_bar(ch_summary, "channel", WORST_CHANNEL), width="stretch", config=c.PLOTLY_CONFIG)
with col_cat:
    st.subheader("문의유형별 재문의율")
    st.plotly_chart(build_bar(cat_summary, "category", WORST_CATEGORY), width="stretch", config=c.PLOTLY_CONFIG)

st.subheader("채널 × 문의유형 조합별 재문의율")
rate_matrix, n_matrix = channel_category_matrix(df)
st.plotly_chart(build_heatmap(rate_matrix, n_matrix), width="stretch", config=c.PLOTLY_CONFIG)
st.caption(f"* 표시된 조합은 표본이 {SMALL_SAMPLE_THRESHOLD}건 미만이라 참고용으로만 볼 것 (앱×기타, 앱×명의변경, 이메일×명의변경)")
