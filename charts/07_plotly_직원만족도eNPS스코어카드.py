"""
직원만족도 eNPS(Employee Net Promoter Score) 스코어카드 (plotly.graph_objects.Indicator)

BigQuery project1_day1.agents 테이블을 직접 조회해 agent_satisfaction(0~10점)을
promoter(9~10) / passive(7~8) / detractor(0~6)로 분류하고,
eNPS = promoter비율(%) - detractor비율(%) 을 전체 및 팀(1팀·2팀·3팀)별로 재계산한다.
"""
import os

import pandas as pd
import plotly.graph_objects as go
from google.cloud import bigquery

PROJECT_ID = "project-6342726b-6c19-4847-844"
DATASET = "project1_day1"
TABLE = "agents"
TEAM_ORDER = ["1팀", "2팀", "3팀"]

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "07_plotly_직원만족도eNPS스코어카드.png")

# 네이비 배경 위에서 가독성이 좋은 색상
BG_NAVY = "#0a1930"
TEXT_PRIMARY = "#ffffff"
TEXT_SECONDARY = "#c7d3ea"
POSITIVE_COLOR = "#3fae6a"
NEGATIVE_COLOR = "#e0454f"
CARD_BORDER = "#3b4f7c"


def load_agents_from_bigquery() -> pd.DataFrame:
    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT agent_id, team, agent_satisfaction
        FROM `{PROJECT_ID}.{DATASET}.{TABLE}`
    """
    return client.query(query).to_dataframe()


def categorize(score: float) -> str:
    if score >= 9:
        return "promoter"
    if score >= 7:
        return "passive"
    return "detractor"


def compute_enps(df: pd.DataFrame) -> float:
    category = df["agent_satisfaction"].apply(categorize)
    promoter_pct = (category == "promoter").mean() * 100
    detractor_pct = (category == "detractor").mean() * 100
    return promoter_pct - detractor_pct


def gauge_color(value: float) -> str:
    return NEGATIVE_COLOR if value < 0 else POSITIVE_COLOR


def main():
    df = load_agents_from_bigquery()

    overall_enps = compute_enps(df)
    team_enps = {team: compute_enps(group) for team, group in df.groupby("team")}
    team_enps = {team: team_enps[team] for team in TEAM_ORDER if team in team_enps}

    fig = go.Figure()

    # 큰 게이지: 전체 eNPS (-100 ~ 100)
    fig.add_trace(
        go.Indicator(
            mode="gauge+number",
            value=overall_enps,
            number={"valueformat": ".0f", "font": {"size": 52, "color": TEXT_PRIMARY}},
            title={
                "text": f"전체 eNPS<br><span style='font-size:0.55em;color:{TEXT_SECONDARY}'>(agents n={len(df)})</span>",
                "font": {"size": 20, "color": TEXT_PRIMARY},
            },
            domain={"x": [0.02, 0.48], "y": [0.05, 0.95]},
            gauge={
                "axis": {
                    "range": [-100, 100],
                    "tickcolor": TEXT_SECONDARY,
                    "tickfont": {"color": TEXT_SECONDARY, "size": 12},
                },
                "bar": {"color": gauge_color(overall_enps), "thickness": 0.28},
                "bgcolor": BG_NAVY,
                "borderwidth": 0,
                "steps": [
                    {"range": [-100, -50], "color": "#5c1a22"},
                    {"range": [-50, 0], "color": "#8f2c37"},
                    {"range": [0, 50], "color": "#1c2b4d"},
                    {"range": [50, 100], "color": "#123a2c"},
                ],
                "threshold": {
                    "line": {"color": TEXT_PRIMARY, "width": 2},
                    "thickness": 0.9,
                    "value": 0,
                },
            },
        )
    )

    # 작은 숫자 카드 3개: 팀별 eNPS
    card_x_ranges = [(0.54, 0.6733), (0.6933, 0.8267), (0.8467, 0.98)]
    for (x0, x1), team in zip(card_x_ranges, TEAM_ORDER):
        value = team_enps.get(team)
        if value is None:
            continue

        fig.add_shape(
            type="rect",
            xref="paper",
            yref="paper",
            x0=x0 - 0.015,
            x1=x1 + 0.015,
            y0=0.22,
            y1=0.78,
            fillcolor=NEGATIVE_COLOR if value < 0 else POSITIVE_COLOR,
            opacity=0.16,
            line={"color": CARD_BORDER, "width": 1},
            layer="below",
        )
        fig.add_trace(
            go.Indicator(
                mode="number",
                value=value,
                number={"valueformat": ".0f", "font": {"size": 34, "color": gauge_color(value)}},
                title={"text": f"{team} eNPS", "font": {"size": 15, "color": TEXT_SECONDARY}},
                domain={"x": [x0, x1], "y": [0.25, 0.75]},
            )
        )

    worst_team = min(team_enps, key=team_enps.get)
    best_team = max(team_enps, key=team_enps.get)
    insight_text = (
        f"※ 전체 eNPS는 {overall_enps:.0f}점으로 세 팀 모두 마이너스 구간입니다. "
        f"{worst_team}({team_enps[worst_team]:.0f})이 가장 낮고 {best_team}({team_enps[best_team]:.0f})가 상대적으로 양호합니다.<br>"
        "detractor(0~6점) 비중이 높은 팀부터 우선적으로 원인 점검(초과근무·QA 점수 등)이 필요합니다."
    )
    fig.add_annotation(
        x=0,
        y=-0.18,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        text=insight_text,
        showarrow=False,
        align="left",
        font={"size": 13, "color": TEXT_SECONDARY},
    )

    fig.update_layout(
        paper_bgcolor=BG_NAVY,
        plot_bgcolor=BG_NAVY,
        font={"color": TEXT_SECONDARY, "size": 13},
        title={
            "text": "직원만족도 eNPS 스코어카드",
            "font": {"color": TEXT_PRIMARY, "size": 22},
            "x": 0.02,
        },
        width=1100,
        height=560,
        margin={"t": 90, "b": 140, "l": 40, "r": 40},
    )

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.write_image(OUTPUT_PATH, scale=2)

    fig.show()


if __name__ == "__main__":
    main()
