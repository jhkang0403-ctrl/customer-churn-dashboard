"""
상담 채널별 CSAT 평균(막대, 왼쪽 축)과 재문의율(꺾은선, 오른쪽 축) 결합차트 (plotly)

data/data_satisfaction.csv, data/data_consultations.csv를 consult_id로 연결해 재계산한다.
"""
import os

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

SATISFACTION_PATH = os.path.join(DATA_DIR, "data_satisfaction.csv")
CONSULTATIONS_PATH = os.path.join(DATA_DIR, "data_consultations.csv")


def load_channel_summary():
    satisfaction = pd.read_csv(SATISFACTION_PATH, encoding="utf-8-sig")
    consultations = pd.read_csv(CONSULTATIONS_PATH, encoding="utf-8-sig")

    merged = satisfaction.merge(
        consultations[["consult_id", "channel", "is_recontact"]],
        on="consult_id",
        how="inner",
    )
    merged["is_recontact_flag"] = merged["is_recontact"].str.strip().str.upper() == "Y"

    summary = (
        merged.groupby("channel")
        .agg(
            상담건수=("consult_id", "size"),
            CSAT평균=("csat", "mean"),
            재문의율=("is_recontact_flag", "mean"),
        )
        .reset_index()
    )
    summary["재문의율"] = summary["재문의율"] * 100
    summary = summary.sort_values("CSAT평균", ascending=True).reset_index(drop=True)
    return summary


def main():
    summary = load_channel_summary()

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(
            x=summary["channel"],
            y=summary["CSAT평균"],
            name="CSAT 평균",
            marker_color="#2a78d6",
            customdata=summary[["channel", "CSAT평균", "재문의율"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "CSAT 평균: %{customdata[1]:.2f}점<br>"
                "재문의율: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
        ),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=summary["channel"],
            y=summary["재문의율"],
            name="재문의율",
            mode="lines+markers",
            line=dict(color="#eb6834", width=2),
            marker=dict(size=9),
            customdata=summary[["channel", "CSAT평균", "재문의율"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "CSAT 평균: %{customdata[1]:.2f}점<br>"
                "재문의율: %{customdata[2]:.1f}%"
                "<extra></extra>"
            ),
        ),
        secondary_y=True,
    )

    fig.update_layout(
        title="채널별 CSAT 평균 vs 재문의율 (CSAT 낮은 순)",
        xaxis_title="채널",
        legend_title_text="",
    )
    fig.update_yaxes(title_text="CSAT 평균 (점)", secondary_y=False)
    fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True, ticksuffix="%")

    fig.show()


if __name__ == "__main__":
    main()
