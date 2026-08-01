import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import common as c

WORST_CHANNEL = "SNS광고"
OVERLAP_MONTHS = ["2024-05", "2024-06"]


def build_month_from_campaigns(campaigns_df: pd.DataFrame, month: str) -> pd.DataFrame:
    """marketing_campaigns.csv의 특정 월을 채널×월로 집계해 spend_df와 같은 스키마로 만든다.

    impressions·clicks는 캠페인 원본에 없는 항목이므로 NaN으로 채운다.
    """
    rows = campaigns_df[campaigns_df["월"] == month].copy()
    rows["channel"] = rows["채널"].str.replace(" ", "", regex=False)
    agg = rows.groupby("channel").agg(spend=("실집행", "sum"), signups=("유입건수", "sum")).reset_index()
    agg.insert(0, "month", month)
    agg["impressions"] = np.nan
    agg["clicks"] = np.nan
    return agg[["month", "channel", "spend", "impressions", "clicks", "signups"]]


def channel_unit_cost(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("channel").agg(spend=("spend", "sum"), signups=("signups", "sum")).reset_index()
    agg["unit_cost"] = agg["spend"] / agg["signups"]
    agg["unit_cost"] = agg["unit_cost"].replace([np.inf, -np.inf], np.nan)
    return agg


def recent_completed_stats(campaigns_df: pd.DataFrame) -> pd.DataFrame:
    """최근 3개월(marketing_campaigns.csv 전체 기간)의 완료 캠페인(is_completed=True)만
    채널별로 집계해 단가를 계산한다.

    강사님 기준 대시보드와 대조해보니 "최근 3개월" 지표는 진행상태 텍스트가 "집행완료"인
    캠페인만 포함해야 값이 일치했다 (누적 지표는 완료 여부와 무관하게 전체 포함이 맞음).
    """
    completed = campaigns_df[campaigns_df["is_completed"] == True].copy()
    completed["channel"] = completed["채널"].str.replace(" ", "", regex=False)
    renamed = completed.rename(columns={"실집행": "spend", "유입건수": "signups"})
    return channel_unit_cost(renamed)


def channel_execution_rate(campaigns_df: pd.DataFrame) -> pd.DataFrame:
    """완료 캠페인(is_completed=True) 기준 채널별 집행률(실집행 ÷ 예산)을 계산한다."""
    completed = campaigns_df[campaigns_df["is_completed"] == True].copy()
    completed["channel"] = completed["채널"].str.replace(" ", "", regex=False)
    agg = completed.groupby("channel").agg(예산=("예산", "sum"), 실집행=("실집행", "sum")).reset_index()
    agg["집행률"] = agg["실집행"] / agg["예산"] * 100
    return agg.sort_values("집행률", ascending=False)


def build_unit_cost_bar(cumulative: pd.DataFrame) -> go.Figure:
    ordered = cumulative.sort_values("unit_cost")
    colors = [c.COLOR_CRITICAL if ch == WORST_CHANNEL else c.COLOR_NEUTRAL for ch in ordered["channel"]]

    fig = go.Figure(
        go.Bar(
            x=ordered["channel"],
            y=ordered["unit_cost"],
            marker_color=colors,
            text=ordered["unit_cost"].map(lambda v: f"{v:,.0f}원" if pd.notna(v) else "N/A"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>유입 1건당 비용: %{y:,.0f}원<extra></extra>",
        )
    )
    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(
        title="채널별 유입 1건당 비용 (누적)",
        yaxis_title="유입 1건당 비용 (원)",
        xaxis_title="채널",
        showlegend=False,
    )
    return fig


def build_recent_vs_cumulative_bar(recent: pd.DataFrame, cumulative: pd.DataFrame) -> go.Figure:
    order = cumulative.sort_values("unit_cost")["channel"]
    recent_indexed = recent.set_index("channel").reindex(order)
    cumulative_indexed = cumulative.set_index("channel").reindex(order)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            name="3개월 단가",
            x=order,
            y=recent_indexed["unit_cost"],
            marker_color=c.COLOR_NEUTRAL,
            text=recent_indexed["unit_cost"].map(lambda v: f"{v:,.0f}원" if pd.notna(v) else "N/A"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>3개월 단가: %{y:,.0f}원<extra></extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            name="누적 단가",
            x=order,
            y=cumulative_indexed["unit_cost"],
            marker_color=c.COLOR_BAR,
            text=cumulative_indexed["unit_cost"].map(lambda v: f"{v:,.0f}원" if pd.notna(v) else "N/A"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>누적 단가: %{y:,.0f}원<extra></extra>",
        )
    )
    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(
        title="채널별 3개월 단가 vs 누적 단가",
        yaxis_title="유입 1건당 비용 (원)",
        xaxis_title="채널",
        barmode="group",
    )
    return fig


def build_execution_rate_bar(rate_df: pd.DataFrame) -> go.Figure:
    fig = go.Figure(
        go.Bar(
            x=rate_df["channel"],
            y=rate_df["집행률"],
            marker_color=c.COLOR_BAR,
            text=rate_df["집행률"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>집행률: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_hline(y=100, line_dash="dash", line_color=c.COLOR_NEUTRAL)
    fig.update_layout(**c.CHART_LAYOUT)
    fig.update_layout(
        title="채널별 집행률 (완료 캠페인 기준)",
        yaxis_title="집행률 (%)",
        xaxis_title="채널",
        showlegend=False,
    )
    return fig


c.render_hero("채널 효율", "채널별 유입 1건당 비용 — 다음 분기 예산 배분의 근거")

spend_df, spend_source = c.load_marketing_spend_with_fallback()
campaigns_df = c.load_marketing_campaigns()

if spend_source == "live":
    st.caption("🟢 BigQuery 라이브 데이터")
else:
    st.caption("🟡 로컬 스냅샷 데이터 — 배포 환경에 BigQuery 인증 정보가 없어 대체 표시 중입니다")

overlap_result = c.verify_overlap(spend_df, campaigns_df, months=OVERLAP_MONTHS)
matched = int((overlap_result["실집행_일치"] & overlap_result["유입건수_일치"]).sum())
total = len(overlap_result)
overlap_icon = "✅" if matched == total else "⚠️"
st.caption(f"{overlap_icon} {matched}/{total} 채널×월 일치 ({OVERLAP_MONTHS[0]}~{OVERLAP_MONTHS[-1]} 엑셀-BigQuery 대조)")

july_df = build_month_from_campaigns(campaigns_df, "2024-07")
combined_df = pd.concat([spend_df[spend_df["month"] < "2024-07"], july_df], ignore_index=True)

cumulative_stats = channel_unit_cost(combined_df)

recent_months = sorted(campaigns_df["월"].unique())
recent_stats = recent_completed_stats(campaigns_df)

total_spend = int(recent_stats["spend"].sum())
total_signups = int(recent_stats["signups"].sum())
avg_unit_cost = total_spend / total_signups

st.caption(f"KPI·최근 3개월 차트 기준: {recent_months[0]}~{recent_months[-1]}, 완료 캠페인(is_completed=True)만 포함")

col1, col2, col3 = st.columns(3)
with col1:
    c.render_stat_tile("총 집행액", f"{total_spend:,}원")
with col2:
    c.render_stat_tile("총 유입", f"{total_signups:,}건")
with col3:
    c.render_stat_tile("평균 유입단가", f"{avg_unit_cost:,.0f}원")

st.divider()

st.subheader("채널별 유입 1건당 비용")
st.plotly_chart(build_unit_cost_bar(cumulative_stats), width="stretch", config=c.PLOTLY_CONFIG)

st.subheader("3개월 단가 vs 누적 단가")
st.caption(f"최근 3개월(완료 캠페인 기준): {recent_months[0]} ~ {recent_months[-1]}")
st.plotly_chart(build_recent_vs_cumulative_bar(recent_stats, cumulative_stats), width="stretch", config=c.PLOTLY_CONFIG)

st.subheader("채널별 집행률")
st.caption("완료 캠페인(is_completed=True) 기준, 점선은 100% 기준선")
st.plotly_chart(build_execution_rate_bar(channel_execution_rate(campaigns_df)), width="stretch", config=c.PLOTLY_CONFIG)
