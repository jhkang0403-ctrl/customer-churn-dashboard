"""
번아웃(초과근무시간) vs 상담원별 CSAT 평균 산점도 (plotly.express, trendline="ols")

BigQuery project1_day1의 agents·consultations·satisfaction 테이블을 직접 조인해
상담원(agent_id)별 CSAT 평균을 재계산한다.
"""
import os

import pandas as pd
import plotly.express as px
from google.cloud import bigquery

PROJECT_ID = "project-6342726b-6c19-4847-844"
DATASET = "project1_day1"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "08-1_plotly_번아웃CSAT산점도.png")

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0f1e3d"
GRID_COLOR = "#24345c"
AXIS_LINE_COLOR = "#3b4f7c"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7cfe3"
MARKER_COLOR = "#3987e5"
TREND_COLOR = "#d95926"


def load_agent_csat() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            a.agent_id,
            a.overtime_hours_avg,
            AVG(s.csat) AS csat_avg
        FROM `{PROJECT_ID}.{DATASET}.agents` a
        JOIN `{PROJECT_ID}.{DATASET}.consultations` c ON c.agent_id = a.agent_id
        JOIN `{PROJECT_ID}.{DATASET}.satisfaction` s ON s.consult_id = c.consult_id
        GROUP BY a.agent_id, a.overtime_hours_avg
    """
    return client.query(query).to_dataframe()


def main():
    df = load_agent_csat()

    r = df["overtime_hours_avg"].corr(df["csat_avg"])

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="csat_avg",
        trendline="ols",
        trendline_color_override=TREND_COLOR,
        custom_data=["agent_id", "overtime_hours_avg", "csat_avg"],
        title=f"번아웃(초과근무시간) vs 상담원별 CSAT 평균 (n={len(df)})",
        labels={"overtime_hours_avg": "overtime_hours_avg (월 평균 초과근무시간)", "csat_avg": "CSAT 평균"},
    )

    fig.update_traces(
        selector=dict(mode="markers"),
        marker=dict(size=14, color=MARKER_COLOR, opacity=0.9, line=dict(width=1, color=BG_NAVY)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "초과근무: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.3f}"
            "<extra></extra>"
        ),
    )
    fig.update_traces(selector=dict(mode="lines"), line=dict(width=2, dash="dash"))

    fig.update_layout(
        paper_bgcolor=BG_NAVY,
        plot_bgcolor=BG_NAVY,
        font=dict(color=TEXT_SECONDARY, size=13),
        title=dict(font=dict(color=TEXT_PRIMARY, size=20)),
        width=1100,
        height=750,
        xaxis=dict(
            title=dict(font=dict(color=TEXT_SECONDARY, size=14)),
            tickfont=dict(color=TEXT_SECONDARY, size=12),
            gridcolor=GRID_COLOR,
            linecolor=AXIS_LINE_COLOR,
            zerolinecolor=AXIS_LINE_COLOR,
        ),
        yaxis=dict(
            title=dict(font=dict(color=TEXT_SECONDARY, size=14)),
            tickfont=dict(color=TEXT_SECONDARY, size=12),
            gridcolor=GRID_COLOR,
            linecolor=AXIS_LINE_COLOR,
            zerolinecolor=AXIS_LINE_COLOR,
        ),
        hoverlabel=dict(bgcolor="#050c1f", font=dict(color=TEXT_PRIMARY, size=13)),
        margin=dict(t=90, b=60, l=80, r=40),
    )

    fig.add_annotation(
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        xanchor="right",
        yanchor="bottom",
        text=f"r = {r:.2f}",
        showarrow=False,
        font=dict(size=16, color=TEXT_PRIMARY),
        bgcolor="rgba(255,255,255,0.08)",
        bordercolor=AXIS_LINE_COLOR,
        borderwidth=1,
        borderpad=6,
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.write_image(OUTPUT_PATH, scale=2)

    fig.show()


if __name__ == "__main__":
    main()
