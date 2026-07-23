"""
상담원 만족도(agent_satisfaction) vs 재문의율(is_recontact=Y 비율) 산점도 (plotly.express)

data/data_consultations.csv를 직접 읽어 상담원(agent_id)별 재문의율을 재계산한다.
agent_satisfaction은 BigQuery project1_day1.agents 테이블에만 존재하고 로컬 CSV가 없어,
아래 AGENT_SATISFACTION에 상담원 20명 값을 그대로 옮겨왔다(원본: BigQuery 직접 조회).
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
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "06_plotly_직원만족도재문의율상관관계.png")

# source: BigQuery project-6342726b-6c19-4847-844.project1_day1.agents (로컬 CSV 없음)
AGENT_SATISFACTION = {
    "AG01": 7, "AG02": 6, "AG03": 4, "AG04": 6, "AG05": 7,
    "AG06": 5, "AG07": 3, "AG08": 8, "AG09": 2, "AG10": 6,
    "AG11": 9, "AG12": 8, "AG13": 6, "AG14": 4, "AG15": 7,
    "AG16": 2, "AG17": 6, "AG18": 7, "AG19": 3, "AG20": 2,
}

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0a1930"
GRID_COLOR = "#24345c"
AXIS_LINE_COLOR = "#3b4f7c"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7d3ea"
MARKER_COLOR = "#f5a623"
TREND_COLOR = "#7ea6e0"


def load_scatter_data():
    consultations = pd.read_csv(CONSULTATIONS_PATH, encoding="utf-8-sig")

    recontact_rate = (
        consultations.assign(is_recontact_flag=consultations["is_recontact"].str.strip().str.upper() == "Y")
        .groupby("agent_id")["is_recontact_flag"]
        .mean()
        .rename("재문의율")
        .reset_index()
    )
    recontact_rate["재문의율"] = recontact_rate["재문의율"] * 100
    recontact_rate["agent_satisfaction"] = recontact_rate["agent_id"].map(AGENT_SATISFACTION)

    return recontact_rate.dropna(subset=["agent_satisfaction"])


def main():
    df = load_scatter_data()

    r = df["agent_satisfaction"].corr(df["재문의율"])

    fig = px.scatter(
        df,
        x="agent_satisfaction",
        y="재문의율",
        custom_data=["agent_id", "agent_satisfaction", "재문의율"],
        title="상담원 만족도 vs 재문의율 (n=20)",
        labels={"agent_satisfaction": "agent_satisfaction (상담원 만족도)", "재문의율": "재문의율 (%)"},
    )

    fig.update_traces(
        marker=dict(size=14, color=MARKER_COLOR, opacity=0.9, line=dict(width=1, color=BG_NAVY)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "agent_satisfaction: %{customdata[1]}<br>"
            "재문의율: %{customdata[2]:.1f}%"
            "<extra></extra>"
        ),
    )

    slope, intercept = np.polyfit(df["agent_satisfaction"], df["재문의율"], 1)
    trend_x = np.array([1, 10])
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
            range=[1, 10],
        ),
        yaxis=dict(
            title=dict(font=dict(color=TEXT_SECONDARY, size=14)),
            tickfont=dict(color=TEXT_SECONDARY, size=12),
            gridcolor=GRID_COLOR,
            linecolor=AXIS_LINE_COLOR,
            zerolinecolor=AXIS_LINE_COLOR,
            ticksuffix="%",
        ),
        hoverlabel=dict(bgcolor="#132242", font=dict(color=TEXT_PRIMARY, size=13)),
        margin=dict(t=90, b=220, l=80, r=40),
    )

    insight_text = (
        f"※ 상관계수 r = {r:.3f} — 만족도가 낮을수록 재문의율이 높은 방향(약한 음의 상관)은 확인되지만,<br>"
        "|r|<0.3으로 관계가 약하고 표본이 상담원 20명뿐입니다. 같은 만족도 점수에서도 재문의율 편차가 커서<br>"
        "만족도 하나만으로 재문의율을 설명하기는 어렵습니다."
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
