"""
초과근무시간(overtime_hours_avg) vs 상담원별 CSAT 평균 산점도 (plotly.express)

data/data_consultations.csv와 data/data_satisfaction.csv를 consult_id로 조인해
상담원(agent_id)별 CSAT 평균을 재계산한다.
overtime_hours_avg는 BigQuery project1_day1.agents 테이블에만 존재하고 로컬 CSV가 없어,
아래 AGENT_OVERTIME_HOURS에 상담원 20명 값을 그대로 옮겨왔다(원본: BigQuery 직접 조회).
"""
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
CONSULTATIONS_PATH = os.path.join(DATA_DIR, "data_consultations.csv")
SATISFACTION_PATH = os.path.join(DATA_DIR, "data_satisfaction.csv")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "06_plotly_번아웃(초과근무)와CSAT영향.png")

# source: BigQuery project-6342726b-6c19-4847-844.project1_day1.agents (로컬 CSV 없음)
AGENT_OVERTIME_HOURS = {
    "AG01": 9, "AG02": 12, "AG03": 18, "AG04": 10, "AG05": 8,
    "AG06": 15, "AG07": 20, "AG08": 7, "AG09": 22, "AG10": 11,
    "AG11": 4, "AG12": 6, "AG13": 9, "AG14": 16, "AG15": 10,
    "AG16": 26, "AG17": 9, "AG18": 8, "AG19": 19, "AG20": 28,
}

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0f1e3d"
GRID_COLOR = "#24345c"
AXIS_LINE_COLOR = "#3b4f7c"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7cfe3"
MARKER_COLOR = "#3987e5"
TREND_COLOR = "#d95926"


def load_scatter_data():
    consultations = pd.read_csv(CONSULTATIONS_PATH, encoding="utf-8-sig")
    satisfaction = pd.read_csv(SATISFACTION_PATH, encoding="utf-8-sig")

    merged = consultations.merge(satisfaction[["consult_id", "csat"]], on="consult_id", how="inner")

    agent_csat = (
        merged.groupby("agent_id")["csat"]
        .mean()
        .rename("csat_avg")
        .reset_index()
    )
    agent_csat["overtime_hours_avg"] = agent_csat["agent_id"].map(AGENT_OVERTIME_HOURS)

    return agent_csat.dropna(subset=["overtime_hours_avg"])


def main():
    df = load_scatter_data()

    r = df["overtime_hours_avg"].corr(df["csat_avg"])

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="csat_avg",
        custom_data=["agent_id", "overtime_hours_avg", "csat_avg"],
        title="초과근무시간 vs 상담원별 CSAT 평균 (n=20)",
        labels={"overtime_hours_avg": "overtime_hours_avg (월 평균 초과근무시간)", "csat_avg": "CSAT 평균"},
    )

    fig.update_traces(
        marker=dict(size=14, color=MARKER_COLOR, opacity=0.9, line=dict(width=2, color=BG_NAVY)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "초과근무: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.3f}"
            "<extra></extra>"
        ),
    )

    slope, intercept = np.polyfit(df["overtime_hours_avg"], df["csat_avg"], 1)
    trend_x = np.array([0, 30])
    trend_y = slope * trend_x + intercept
    fig.add_trace(
        go.Scatter(
            x=trend_x,
            y=trend_y,
            mode="lines",
            line=dict(color=TREND_COLOR, width=2, dash="dash"),
            hoverinfo="skip",
            showlegend=False,
        )
    )

    fig.update_layout(
        paper_bgcolor=BG_NAVY,
        plot_bgcolor=BG_NAVY,
        font=dict(color=TEXT_SECONDARY, size=13),
        title=dict(font=dict(color=TEXT_PRIMARY, size=20)),
        width=1100,
        height=820,
        xaxis=dict(
            title=dict(font=dict(color=TEXT_SECONDARY, size=14)),
            tickfont=dict(color=TEXT_SECONDARY, size=12),
            gridcolor=GRID_COLOR,
            linecolor=AXIS_LINE_COLOR,
            zerolinecolor=AXIS_LINE_COLOR,
            range=[0, 30],
        ),
        yaxis=dict(
            title=dict(font=dict(color=TEXT_SECONDARY, size=14)),
            tickfont=dict(color=TEXT_SECONDARY, size=12),
            gridcolor=GRID_COLOR,
            linecolor=AXIS_LINE_COLOR,
            zerolinecolor=AXIS_LINE_COLOR,
            range=[2.8, 3.7],
        ),
        hoverlabel=dict(bgcolor="#050c1f", font=dict(color=TEXT_PRIMARY, size=13)),
        margin=dict(t=90, b=220, l=80, r=40),
    )

    insight_text = (
        f"※ 상관계수 r = {r:.3f} — 0에 매우 가까워 초과근무시간과 CSAT 평균 사이에 뚜렷한 선형관계가 없습니다.<br>"
        "초과근무가 가장 많은 AG20(28시간)·AG16(26시간)의 CSAT도 각각 3.27, 3.54로 평균 이상·이하가 혼재합니다.<br>"
        "표본이 상담원 20명뿐이라 다른 변수(근속연수, QA 점수 등)와의 다변량 분석을 함께 보는 것을 권장합니다."
    )
    fig.add_annotation(
        x=0,
        y=-0.30,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        text=insight_text,
        showarrow=False,
        align="left",
        font=dict(size=13, color=TEXT_SECONDARY),
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.write_image(OUTPUT_PATH, scale=2)

    fig.show()


if __name__ == "__main__":
    main()
