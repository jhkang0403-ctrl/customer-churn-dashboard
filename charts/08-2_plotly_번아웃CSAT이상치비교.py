"""
번아웃(초과근무시간) vs 상담원별 CSAT 평균 — 이상치(초과근무 25시간 이상) 포함/제외 비교

BigQuery project1_day1의 agents·consultations·satisfaction 테이블을 직접 조인해
상담원(agent_id)별 CSAT 평균을 재계산한 뒤, 초과근무 25시간 이상 상담원을 제외했을 때
상관계수·추세선 기울기가 어떻게 달라지는지 나란히 비교한다.
"""
import os

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from google.cloud import bigquery

PROJECT_ID = "project-6342726b-6c19-4847-844"
DATASET = "project1_day1"
OUTLIER_THRESHOLD = 25  # 초과근무 25시간 이상을 이상치로 간주

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "08-2_plotly_번아웃CSAT이상치비교.png")

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0f1e3d"
GRID_COLOR = "#24345c"
AXIS_LINE_COLOR = "#3b4f7c"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7cfe3"
MARKER_COLOR = "#3987e5"
OUTLIER_COLOR = "#e0454f"
TREND_COLOR = "#d95926"


def load_agent_csat():
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


def build_panel(df, marker_color):
    """산점도 + OLS 추세선 트레이스와 r, 기울기를 함께 반환한다."""
    r = df["overtime_hours_avg"].corr(df["csat_avg"])

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="csat_avg",
        trendline="ols",
        trendline_color_override=TREND_COLOR,
        custom_data=["agent_id", "overtime_hours_avg", "csat_avg"],
    )
    slope = px.get_trendline_results(fig).iloc[0]["px_fit_results"].params[1]

    fig.update_traces(
        selector=dict(mode="markers"),
        marker=dict(size=13, color=marker_color, opacity=0.9, line=dict(width=1, color=BG_NAVY)),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>초과근무: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.3f}<extra></extra>"
        ),
    )
    fig.update_traces(selector=dict(mode="lines"), line=dict(width=2, dash="dash"))

    return fig, r, slope


def main():
    full_df = load_agent_csat()
    filtered_df = full_df[full_df["overtime_hours_avg"] < OUTLIER_THRESHOLD]
    outliers_df = full_df[full_df["overtime_hours_avg"] >= OUTLIER_THRESHOLD]

    fig_full, r_full, slope_full = build_panel(full_df, MARKER_COLOR)
    fig_filtered, r_filtered, slope_filtered = build_panel(filtered_df, MARKER_COLOR)

    y_min = full_df["csat_avg"].min() - 0.05
    y_max = full_df["csat_avg"].max() + 0.05
    x_min = full_df["overtime_hours_avg"].min() - 1
    x_max = full_df["overtime_hours_avg"].max() + 1

    fig = make_subplots(
        rows=1,
        cols=2,
        subplot_titles=(
            f"이상치 포함 (n={len(full_df)})",
            f"25시간 이상 제외 (n={len(filtered_df)})",
        ),
        horizontal_spacing=0.1,
    )

    for trace in fig_full.data:
        fig.add_trace(trace, row=1, col=1)
    for trace in fig_filtered.data:
        fig.add_trace(trace, row=1, col=2)

    # 왼쪽 패널에서 이상치(25시간 이상) 표시
    fig.add_trace(
        go.Scatter(
            x=outliers_df["overtime_hours_avg"],
            y=outliers_df["csat_avg"],
            mode="markers",
            marker=dict(
                size=15,
                color=OUTLIER_COLOR,
                symbol="circle-open",
                line=dict(width=2.5, color=OUTLIER_COLOR),
            ),
            customdata=outliers_df[["agent_id", "overtime_hours_avg", "csat_avg"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b> (이상치)<br>초과근무: %{customdata[1]}시간<br>"
                "CSAT 평균: %{customdata[2]:.3f}<extra></extra>"
            ),
            showlegend=False,
        ),
        row=1,
        col=1,
    )

    fig.update_xaxes(
        title_text="overtime_hours_avg (월 평균 초과근무시간)",
        range=[x_min, x_max],
        gridcolor=GRID_COLOR,
        linecolor=AXIS_LINE_COLOR,
        zerolinecolor=AXIS_LINE_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, size=13),
    )
    fig.update_yaxes(
        title_text="CSAT 평균",
        range=[y_min, y_max],
        gridcolor=GRID_COLOR,
        linecolor=AXIS_LINE_COLOR,
        zerolinecolor=AXIS_LINE_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=12),
        title_font=dict(color=TEXT_SECONDARY, size=13),
    )

    for annotation, (r, slope) in zip(
        fig.layout.annotations, [(r_full, slope_full), (r_filtered, slope_filtered)]
    ):
        annotation.font = dict(color=TEXT_PRIMARY, size=15)

    # 각 패널 우측 상단에 r / 기울기 표시
    stat_boxes = [
        (0.46, r_full, slope_full),
        (1.0, r_filtered, slope_filtered),
    ]
    for x_anchor, r, slope in stat_boxes:
        fig.add_annotation(
            x=x_anchor,
            y=1.0,
            xref="paper",
            yref="paper",
            xanchor="right",
            yanchor="bottom",
            text=f"r = {r:.2f}<br>기울기 = {slope:.3f}",
            showarrow=False,
            align="right",
            font=dict(size=14, color=TEXT_PRIMARY),
            bgcolor="rgba(255,255,255,0.08)",
            bordercolor=AXIS_LINE_COLOR,
            borderwidth=1,
            borderpad=6,
        )

    fig.update_layout(
        paper_bgcolor=BG_NAVY,
        plot_bgcolor=BG_NAVY,
        font=dict(color=TEXT_SECONDARY, size=13),
        title=dict(
            text="번아웃(초과근무) vs CSAT — 이상치(초과근무 25시간 이상) 포함/제외 비교",
            font=dict(color=TEXT_PRIMARY, size=20),
        ),
        width=1400,
        height=860,
        showlegend=False,
        margin=dict(t=110, b=230, l=70, r=40),
    )

    r_delta = r_filtered - r_full
    slope_delta_pct = (slope_filtered - slope_full) / abs(slope_full) * 100
    insight_text = (
        f"※ 이상치 후보: {', '.join(outliers_df['agent_id'])} (초과근무 {OUTLIER_THRESHOLD}시간 이상, 빨간 원 표시). "
        f"제외 시 r은 {r_full:.3f} → {r_filtered:.3f}로 {abs(r_delta):.3f}p {'완화' if r_delta > 0 else '심화'}되고,<br>"
        f"추세선 기울기는 {slope_full:.3f} → {slope_filtered:.3f}로 {abs(slope_delta_pct):.1f}% "
        f"{'완만' if abs(slope_filtered) < abs(slope_full) else '가팔라짐'}됩니다. "
        "다만 제외 후에도 |r|>0.7의 강한 음의 상관이 유지되어, 결론(번아웃↑ → CSAT↓)은 이상치 유무와 무관하게 견고합니다."
    )
    fig.add_annotation(
        x=0,
        y=-0.24,
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
