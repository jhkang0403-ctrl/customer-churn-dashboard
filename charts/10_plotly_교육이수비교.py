"""
교육 이수 여부(training_completed_yn: Y/N)에 따른 CSAT 평균 vs 재문의율 평균 비교

BigQuery project1_day1의 agents·consultations·satisfaction 테이블을 직접 조인해
상담 건 단위로 CSAT 평균과 재문의율을 교육 이수 여부별로 재계산한다.
"""
import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.cloud import bigquery

PROJECT_ID = "project-6342726b-6c19-4847-844"
DATASET = "project1_day1"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "10_plotly_교육이수비교.png")

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0f1e3d"
GRID_COLOR = "#24345c"
AXIS_LINE_COLOR = "#3b4f7c"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7cfe3"
COLOR_Y = "#f5a623"  # 교육 이수(Y) 강조색
COLOR_N = "#7d8aa8"  # 교육 미이수(N) 회색 계열

GROUP_ORDER = ["N", "Y"]
GROUP_COLORS = {"N": COLOR_N, "Y": COLOR_Y}


def load_training_comparison() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        WITH base AS (
            SELECT
                a.agent_id,
                a.training_completed_yn,
                c.consult_id,
                c.is_recontact
            FROM `{PROJECT_ID}.{DATASET}.agents` a
            JOIN `{PROJECT_ID}.{DATASET}.consultations` c ON c.agent_id = a.agent_id
        ),
        with_csat AS (
            SELECT b.*, s.csat
            FROM base b
            JOIN `{PROJECT_ID}.{DATASET}.satisfaction` s ON s.consult_id = b.consult_id
        )
        SELECT
            training_completed_yn,
            COUNT(*) AS n_consults,
            COUNT(DISTINCT agent_id) AS n_agents,
            AVG(csat) AS csat_avg,
            100.0 * SUM(IF(is_recontact, 1, 0)) / COUNT(*) AS recontact_rate_pct
        FROM with_csat
        GROUP BY training_completed_yn
    """
    df = client.query(query).to_dataframe()
    df["교육이수"] = df["training_completed_yn"].map({True: "Y", False: "N"})
    return df.set_index("교육이수").reindex(GROUP_ORDER)


def main():
    df = load_training_comparison()

    colors = [GROUP_COLORS[g] for g in GROUP_ORDER]

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=("CSAT 평균", "재문의율 평균"),
    )

    fig.add_trace(
        go.Bar(
            x=GROUP_ORDER,
            y=df["csat_avg"],
            marker_color=colors,
            text=df["csat_avg"].map(lambda v: f"{v:.2f}"),
            textposition="outside",
            customdata=df[["n_consults", "n_agents"]].values,
            hovertemplate=(
                "교육이수: %{x}<br>CSAT 평균: %{y:.3f}<br>"
                "상담건수: %{customdata[0]}건 (상담원 %{customdata[1]}명)<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.add_trace(
        go.Bar(
            x=GROUP_ORDER,
            y=df["recontact_rate_pct"],
            marker_color=colors,
            text=df["recontact_rate_pct"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            customdata=df[["n_consults", "n_agents"]].values,
            hovertemplate=(
                "교육이수: %{x}<br>재문의율: %{y:.1f}%<br>"
                "상담건수: %{customdata[0]}건 (상담원 %{customdata[1]}명)<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    fig.update_xaxes(
        title_text="교육 이수 여부",
        gridcolor=GRID_COLOR,
        linecolor=AXIS_LINE_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=13),
        title_font=dict(color=TEXT_SECONDARY, size=13),
    )
    fig.update_yaxes(
        title_text="CSAT 평균",
        range=[0, 5],
        gridcolor=GRID_COLOR,
        linecolor=AXIS_LINE_COLOR,
        zerolinecolor=AXIS_LINE_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, size=13),
        row=1,
        col=1,
    )
    fig.update_yaxes(
        title_text="재문의율 (%)",
        range=[0, 50],
        ticksuffix="%",
        gridcolor=GRID_COLOR,
        linecolor=AXIS_LINE_COLOR,
        zerolinecolor=AXIS_LINE_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, size=13),
        row=1,
        col=2,
    )

    for annotation in fig.layout.annotations:
        annotation.font = dict(color=TEXT_PRIMARY, size=16)

    fig.update_traces(textfont=dict(color=TEXT_PRIMARY, size=14))

    fig.update_layout(
        paper_bgcolor=BG_NAVY,
        plot_bgcolor=BG_NAVY,
        font=dict(color=TEXT_SECONDARY, size=13),
        title=dict(
            text=f"교육 이수 여부에 따른 CSAT·재문의율 비교 (상담 {int(df['n_consults'].sum())}건)",
            font=dict(color=TEXT_PRIMARY, size=20),
        ),
        width=1100,
        height=650,
        showlegend=False,
        margin=dict(t=100, b=140, l=70, r=40),
    )

    csat_gap = df.loc["Y", "csat_avg"] - df.loc["N", "csat_avg"]
    recontact_gap = df.loc["Y", "recontact_rate_pct"] - df.loc["N", "recontact_rate_pct"]
    insight_text = (
        f"※ 교육 이수(Y) 그룹은 미이수(N) 대비 CSAT 평균이 {csat_gap:+.3f}점, 재문의율이 {recontact_gap:+.1f}%p 차이납니다. "
        f"(N: 상담원 {int(df.loc['N', 'n_agents'])}명·{int(df.loc['N', 'n_consults'])}건, "
        f"Y: 상담원 {int(df.loc['Y', 'n_agents'])}명·{int(df.loc['Y', 'n_consults'])}건)"
    )
    fig.add_annotation(
        x=0,
        y=-0.28,
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
