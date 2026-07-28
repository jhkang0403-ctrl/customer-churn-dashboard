import os
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
from plotly.subplots import make_subplots

st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_PATH = os.path.join(BASE_DIR, "report", "고객서비스_만족도개선_리포트.md")

REFERENCE_DATE = pd.Timestamp("2024-12-31")

COLOR_NEUTRAL = "#898781"
COLOR_HIGHLIGHT = "#d03b3b"
COLOR_BAR = "#2a78d6"
COLOR_LINE = "#eb6834"
COLOR_POSITIVE = "#2a9d57"

BQ_PROJECT_ID = "project-6342726b-6c19-4847-844"
BQ_DATASET = "project1_day1"
TEAM_OPTIONS = ["전체", "1팀", "2팀", "3팀"]


# ---------------------------------------------------------------------------
# BigQuery 연결 (상담원 섹션 전용 — customers/voc 등 기존 6개 차트는 CSV 그대로 사용)
# ---------------------------------------------------------------------------
@st.cache_resource
def get_bigquery_client() -> bigquery.Client:
    try:
        if "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(project=BQ_PROJECT_ID, credentials=credentials)
    except Exception:
        # st.secrets 파일 자체가 없는 로컬 환경 등 — 기존처럼 ADC로 폴백
        pass
    return bigquery.Client(project=BQ_PROJECT_ID)


def _team_job_config(team: str) -> bigquery.QueryJobConfig | None:
    if team == "전체":
        return None
    return bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("team", "STRING", team)])


def load_with_fallback(live_fn, snapshot_fn, *args, **kwargs):
    """live_fn을 먼저 시도하고, 인증/네트워크 등 어떤 이유로든 실패하면 snapshot_fn으로 대체한다.
    반환값은 (결과, source) 튜플이며 source는 "live" 또는 "snapshot"이다."""
    try:
        return live_fn(*args, **kwargs), "live"
    except Exception:
        return snapshot_fn(*args, **kwargs), "snapshot"


# ---------------------------------------------------------------------------
# 데이터 로딩 (원본 CSV를 직접 읽는다)
# ---------------------------------------------------------------------------
@st.cache_data
def load_customers() -> pd.DataFrame:
    df = pd.read_csv(os.path.join(DATA_DIR, "data_customers.csv"), encoding="utf-8-sig")
    df["is_churned"] = df["churn_yn"].str.strip().str.upper() == "Y"
    df["join_date"] = pd.to_datetime(df["join_date"])
    return df


@st.cache_data
def load_voc() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "data_voc.csv"), encoding="utf-8-sig")


@st.cache_data
def load_consultations() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "data_consultations.csv"), encoding="utf-8-sig")


@st.cache_data
def load_satisfaction() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "data_satisfaction.csv"), encoding="utf-8-sig")


@st.cache_data
def load_usage_history() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "data_usage_history.csv"), encoding="utf-8-sig")


@st.cache_data
def load_report_markdown() -> str:
    with open(REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4 :].lstrip("\n")
    return content


# ---------------------------------------------------------------------------
# ① VOC로 본 이탈
# ---------------------------------------------------------------------------
def build_voc_chart(customers: pd.DataFrame) -> go.Figure:
    voc = load_voc()

    target_ids = set(
        voc.loc[(voc["category"] == "해지관련") & (voc["sentiment"] == "부정"), "customer_id"]
    )
    target = customers[customers["customer_id"].isin(target_ids)]

    def summarize(df: pd.DataFrame):
        total = len(df)
        churned = int(df["is_churned"].sum())
        rate = (churned / total * 100) if total else 0
        return total, churned, rate

    all_total, all_churned, all_rate = summarize(customers)
    t_total, t_churned, t_rate = summarize(target)

    summary = pd.DataFrame(
        {
            "구분": ["전체 고객", "해지관련 부정 VOC 이력 있음"],
            "고객수": [all_total, t_total],
            "이탈고객수": [all_churned, t_churned],
            "이탈율": [all_rate, t_rate],
        }
    )

    fig = px.bar(
        summary,
        x="구분",
        y="이탈율",
        color="구분",
        color_discrete_map={"전체 고객": COLOR_NEUTRAL, "해지관련 부정 VOC 이력 있음": COLOR_HIGHLIGHT},
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        labels={"이탈율": "이탈율 (%)"},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{customdata[2]:.1f}%<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# ② 채널·만족도로 본 이탈
# ---------------------------------------------------------------------------
def build_channel_csat_chart() -> go.Figure:
    satisfaction = load_satisfaction()
    consultations = load_consultations()

    merged = satisfaction.merge(
        consultations[["consult_id", "channel", "is_recontact"]], on="consult_id", how="inner"
    )
    merged["is_recontact_flag"] = merged["is_recontact"].str.strip().str.upper() == "Y"

    summary = (
        merged.groupby("channel")
        .agg(상담건수=("consult_id", "size"), CSAT평균=("csat", "mean"), 재문의율=("is_recontact_flag", "mean"))
        .reset_index()
    )
    summary["재문의율"] = summary["재문의율"] * 100
    summary = summary.sort_values("CSAT평균", ascending=True).reset_index(drop=True)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(
            x=summary["channel"],
            y=summary["CSAT평균"],
            name="CSAT 평균",
            marker_color=COLOR_BAR,
            customdata=summary[["channel", "CSAT평균", "재문의율"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>CSAT 평균: %{customdata[1]:.2f}점<br>"
                "재문의율: %{customdata[2]:.1f}%<extra></extra>"
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
            line=dict(color=COLOR_LINE, width=2),
            marker=dict(size=9),
            customdata=summary[["channel", "CSAT평균", "재문의율"]].values,
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>CSAT 평균: %{customdata[1]:.2f}점<br>"
                "재문의율: %{customdata[2]:.1f}%<extra></extra>"
            ),
        ),
        secondary_y=True,
    )
    fig.update_layout(xaxis_title="채널", legend_title_text="")
    fig.update_yaxes(title_text="CSAT 평균 (점)", secondary_y=False)
    fig.update_yaxes(title_text="재문의율 (%)", secondary_y=True, ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# ③ 재문의 반복으로 본 이탈
# ---------------------------------------------------------------------------
def bucketize(count: int) -> str:
    if count == 0:
        return "0회"
    if count == 1:
        return "1회"
    return "2회 이상"


def build_recontact_bucket_chart(customers: pd.DataFrame) -> go.Figure:
    consultations = load_consultations()

    recontact_counts = (
        consultations[consultations["is_recontact"].str.strip().str.upper() == "Y"]
        .groupby("customer_id")
        .size()
    )

    df = customers.copy()
    df["recontact_count"] = df["customer_id"].map(recontact_counts).fillna(0).astype(int)
    df["recontact_bucket"] = df["recontact_count"].apply(bucketize)

    bucket_order = ["0회", "1회", "2회 이상"]
    summary = (
        df.groupby("recontact_bucket")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reindex(bucket_order)
        .fillna(0)
        .astype({"고객수": int, "이탈고객수": int})
        .reset_index()
        .rename(columns={"recontact_bucket": "재문의구간"})
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100
    overall_rate = df["is_churned"].mean() * 100

    fig = px.bar(
        summary,
        x="재문의구간",
        y="이탈율",
        color="재문의구간",
        color_discrete_map={"0회": COLOR_NEUTRAL, "1회": COLOR_NEUTRAL, "2회 이상": COLOR_HIGHLIGHT},
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        labels={"이탈율": "이탈율 (%)", "재문의구간": "재문의 횟수"},
        category_orders={"재문의구간": bucket_order},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{customdata[2]:.1f}%<extra></extra>"
        ),
    )
    fig.add_hline(y=overall_rate, line_dash="dash", line_color="#0b0b0b")
    fig.add_annotation(
        x=0.5,
        y=overall_rate,
        xref="x",
        yref="y",
        xanchor="left",
        yanchor="bottom",
        text=f"전체 평균 이탈율 {overall_rate:.1f}%",
        showarrow=False,
        bgcolor="rgba(252,252,251,0.85)",
        font=dict(color="#0b0b0b"),
    )
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# ④ 요금제로 본 이탈
# ---------------------------------------------------------------------------
def build_plan_chart(customers: pd.DataFrame) -> go.Figure:
    highlight_plan = "베이직"

    summary = (
        customers.groupby("plan")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100
    summary = summary.sort_values("이탈율", ascending=False).reset_index(drop=True)

    fig = px.bar(
        summary,
        x="plan",
        y="이탈율",
        color="plan",
        color_discrete_map={
            plan: (COLOR_HIGHLIGHT if plan == highlight_plan else COLOR_NEUTRAL) for plan in summary["plan"]
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        labels={"이탈율": "이탈율 (%)", "plan": "요금제"},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{customdata[2]:.1f}%<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# ⑤ 지역으로 본 이탈
# ---------------------------------------------------------------------------
def build_region_chart(customers: pd.DataFrame) -> go.Figure:
    highlight_regions = {"부산", "대구"}
    caption_region = "인천"

    summary = (
        customers.groupby("region")
        .agg(고객수=("customer_id", "size"), 이탈고객수=("is_churned", "sum"))
        .reset_index()
    )
    summary["이탈율"] = summary["이탈고객수"] / summary["고객수"] * 100
    summary = summary.sort_values("이탈율", ascending=False).reset_index(drop=True)

    caption_row = summary[summary["region"] == caption_region].iloc[0]
    caption_text = (
        f"※ {caption_region}은 표본이 {int(caption_row['고객수'])}건이지만 "
        f"이탈 {int(caption_row['이탈고객수'])}건뿐입니다."
    )

    fig = px.bar(
        summary,
        x="region",
        y="이탈율",
        color="region",
        color_discrete_map={
            region: (COLOR_HIGHLIGHT if region in highlight_regions else COLOR_NEUTRAL)
            for region in summary["region"]
        },
        text=summary["이탈율"].map(lambda v: f"{v:.1f}%"),
        custom_data=["고객수", "이탈고객수", "이탈율"],
        labels={"이탈율": "이탈율 (%)", "region": "지역"},
    )
    fig.update_traces(
        textposition="outside",
        hovertemplate=(
            "<b>%{x}</b><br>고객 수: %{customdata[0]}명<br>"
            "이탈 고객 수: %{customdata[1]}명<br>이탈율: %{customdata[2]:.1f}%<extra></extra>"
        ),
    )
    fig.update_layout(showlegend=False, yaxis_ticksuffix="%", margin=dict(b=140))
    fig.add_annotation(
        x=0,
        y=-0.3,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
        text=caption_text,
        showarrow=False,
        font=dict(size=12, color="#52514e"),
    )
    return fig


# ---------------------------------------------------------------------------
# ⑥ 가입기간·이용량으로 본 이탈
# ---------------------------------------------------------------------------
def build_tenure_usage_scatter(customers: pd.DataFrame) -> go.Figure:
    usage = load_usage_history()

    df = customers.copy()
    df["tenure_months"] = (REFERENCE_DATE.year - df["join_date"].dt.year) * 12 + (
        REFERENCE_DATE.month - df["join_date"].dt.month
    )

    avg_usage = usage.groupby("customer_id")["data_gb"].mean().rename("avg_data_gb")
    df = df.merge(avg_usage, on="customer_id", how="left")
    df["이탈여부"] = df["churn_yn"].str.strip().str.upper().map({"Y": "이탈", "N": "유지"})

    fig = px.scatter(
        df,
        x="tenure_months",
        y="avg_data_gb",
        color="이탈여부",
        color_discrete_map={"유지": COLOR_NEUTRAL, "이탈": COLOR_HIGHLIGHT},
        custom_data=["customer_id", "tenure_months", "avg_data_gb", "이탈여부"],
        labels={"tenure_months": "가입기간 (개월)", "avg_data_gb": "평균 데이터 사용량 (GB)"},
    )
    fig.update_traces(
        marker=dict(size=9, opacity=0.75, line=dict(width=0.5, color="white")),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>가입기간: %{customdata[1]}개월<br>"
            "평균 데이터 사용량: %{customdata[2]:.1f}GB<br>이탈 여부: %{customdata[3]}<extra></extra>"
        ),
    )
    fig.update_layout(legend_title_text="이탈 여부")
    return fig


# ---------------------------------------------------------------------------
# ⑦ 상담원 데이터로 본 조직 건강도 (BigQuery agents/consultations/satisfaction 직접 조회)
# 팀 selectbox가 바뀔 때마다 리런되며 BigQuery를 다시 조회한다 (쿼리 결과는 캐싱하지 않음).
# ---------------------------------------------------------------------------
def load_enps(team: str) -> tuple[float, int]:
    client = get_bigquery_client()
    where_clause = "WHERE team = @team" if team != "전체" else ""
    query = f"""
        SELECT agent_satisfaction
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.agents`
        {where_clause}
    """
    df = client.query(query, job_config=_team_job_config(team)).to_dataframe()

    def categorize(score):
        if score >= 9:
            return "promoter"
        if score >= 7:
            return "passive"
        return "detractor"

    category = df["agent_satisfaction"].apply(categorize)
    enps = (category == "promoter").mean() * 100 - (category == "detractor").mean() * 100
    return enps, len(df)


def build_enps_gauge_chart(team: str, enps: float, n: int) -> go.Figure:
    bar_color = COLOR_HIGHLIGHT if enps < 0 else COLOR_POSITIVE
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=enps,
            number={"valueformat": ".0f"},
            title={"text": f"{team} eNPS (n={n})"},
            gauge={
                "axis": {"range": [-100, 100]},
                "bar": {"color": bar_color, "thickness": 0.3},
                "steps": [
                    {"range": [-100, 0], "color": "#f7dcdc"},
                    {"range": [0, 100], "color": "#dcefdf"},
                ],
                "threshold": {"line": {"color": "#333333", "width": 2}, "thickness": 0.9, "value": 0},
            },
        )
    )
    fig.update_layout(height=320, margin=dict(t=70, b=20, l=40, r=40))
    return fig


def load_burnout_csat(team: str) -> pd.DataFrame:
    client = get_bigquery_client()
    where_clause = "WHERE a.team = @team" if team != "전체" else ""
    query = f"""
        SELECT
            a.agent_id,
            a.overtime_hours_avg,
            AVG(s.csat) AS csat_avg
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.agents` a
        JOIN `{BQ_PROJECT_ID}.{BQ_DATASET}.consultations` c ON c.agent_id = a.agent_id
        JOIN `{BQ_PROJECT_ID}.{BQ_DATASET}.satisfaction` s ON s.consult_id = c.consult_id
        {where_clause}
        GROUP BY a.agent_id, a.overtime_hours_avg
    """
    return client.query(query, job_config=_team_job_config(team)).to_dataframe()


def build_burnout_csat_chart(df: pd.DataFrame) -> go.Figure:
    r = df["overtime_hours_avg"].corr(df["csat_avg"]) if len(df) >= 2 else float("nan")

    fig = px.scatter(
        df,
        x="overtime_hours_avg",
        y="csat_avg",
        trendline="ols" if len(df) >= 3 else None,
        trendline_color_override=COLOR_LINE,
        custom_data=["agent_id", "overtime_hours_avg", "csat_avg"],
        labels={"overtime_hours_avg": "월 평균 초과근무시간", "csat_avg": "CSAT 평균"},
    )
    fig.update_traces(
        selector=dict(mode="markers"),
        marker=dict(size=12, color=COLOR_BAR, opacity=0.85, line=dict(width=1, color="white")),
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>초과근무: %{customdata[1]}시간<br>"
            "CSAT 평균: %{customdata[2]:.3f}<extra></extra>"
        ),
    )
    fig.add_annotation(
        x=1,
        y=1,
        xref="paper",
        yref="paper",
        xanchor="right",
        yanchor="bottom",
        text=f"r = {r:.2f}" if pd.notna(r) else "r = N/A (표본 부족)",
        showarrow=False,
        font=dict(size=14),
        bgcolor="rgba(255,255,255,0.7)",
    )
    fig.update_layout(height=420, margin=dict(t=50, b=40, l=60, r=20))
    return fig


def load_training_comparison(team: str) -> pd.DataFrame:
    client = get_bigquery_client()
    where_clause = "WHERE a.team = @team" if team != "전체" else ""
    query = f"""
        WITH base AS (
            SELECT
                a.agent_id,
                a.training_completed_yn,
                c.consult_id,
                c.is_recontact
            FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.agents` a
            JOIN `{BQ_PROJECT_ID}.{BQ_DATASET}.consultations` c ON c.agent_id = a.agent_id
            {where_clause}
        ),
        with_csat AS (
            SELECT b.*, s.csat
            FROM base b
            JOIN `{BQ_PROJECT_ID}.{BQ_DATASET}.satisfaction` s ON s.consult_id = b.consult_id
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
    df = client.query(query, job_config=_team_job_config(team)).to_dataframe()
    df["교육이수"] = df["training_completed_yn"].map({True: "Y", False: "N"})
    return df.set_index("교육이수").reindex(["N", "Y"])


# ---------------------------------------------------------------------------
# 스냅샷 CSV 폴백 (BigQuery 라이브 조회 실패 시 대체 — data/*_snapshot.csv, load_with_fallback과 함께 사용)
# ---------------------------------------------------------------------------
def _agent_snapshot_date_label() -> str:
    mtime = datetime.fromtimestamp(os.path.getmtime(os.path.join(DATA_DIR, "agents_snapshot.csv")))
    return f"{mtime.month}월 {mtime.day}일"


def _load_agents_snapshot() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "agents_snapshot.csv"), encoding="utf-8-sig")


def _load_agent_consultations_snapshot() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "agent_consultations_snapshot.csv"), encoding="utf-8-sig")


def load_enps_snapshot(team: str) -> tuple[float, int]:
    agents = _load_agents_snapshot()
    if team != "전체":
        agents = agents[agents["team"] == team]

    def categorize(score):
        if score >= 9:
            return "promoter"
        if score >= 7:
            return "passive"
        return "detractor"

    category = agents["agent_satisfaction"].apply(categorize)
    enps = (category == "promoter").mean() * 100 - (category == "detractor").mean() * 100
    return enps, len(agents)


def load_burnout_csat_snapshot(team: str) -> pd.DataFrame:
    agents = _load_agents_snapshot()
    if team != "전체":
        agents = agents[agents["team"] == team]
    consultations = _load_agent_consultations_snapshot()
    merged = consultations.merge(agents[["agent_id", "overtime_hours_avg"]], on="agent_id", how="inner")
    return (
        merged.groupby(["agent_id", "overtime_hours_avg"], as_index=False)["csat"]
        .mean()
        .rename(columns={"csat": "csat_avg"})
    )


def load_training_comparison_snapshot(team: str) -> pd.DataFrame:
    agents = _load_agents_snapshot()
    if team != "전체":
        agents = agents[agents["team"] == team]
    consultations = _load_agent_consultations_snapshot()
    merged = consultations.merge(agents[["agent_id", "training_completed_yn"]], on="agent_id", how="inner")
    df = (
        merged.groupby("training_completed_yn")
        .agg(
            n_consults=("consult_id", "count"),
            n_agents=("agent_id", "nunique"),
            csat_avg=("csat", "mean"),
            recontact_rate_pct=("is_recontact", lambda s: 100.0 * s.sum() / len(s)),
        )
        .reset_index()
    )
    df["교육이수"] = df["training_completed_yn"].map({True: "Y", False: "N"})
    return df.set_index("교육이수").reindex(["N", "Y"])


def build_training_comparison_chart(df: pd.DataFrame) -> go.Figure:
    group_order = ["N", "Y"]
    colors = [COLOR_NEUTRAL, COLOR_BAR]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("CSAT 평균", "재문의율 평균"))

    fig.add_trace(
        go.Bar(
            x=group_order,
            y=df["csat_avg"],
            marker_color=colors,
            text=df["csat_avg"].map(lambda v: f"{v:.2f}"),
            textposition="outside",
            showlegend=False,
        ),
        row=1,
        col=1,
    )
    fig.add_trace(
        go.Bar(
            x=group_order,
            y=df["recontact_rate_pct"],
            marker_color=colors,
            text=df["recontact_rate_pct"].map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            showlegend=False,
        ),
        row=1,
        col=2,
    )

    fig.update_yaxes(title_text="CSAT 평균", range=[0, 5], row=1, col=1)
    fig.update_yaxes(title_text="재문의율 (%)", range=[0, 50], ticksuffix="%", row=1, col=2)
    fig.update_xaxes(title_text="교육 이수 여부")
    fig.update_layout(height=380, margin=dict(t=60, b=40, l=60, r=20), showlegend=False)
    return fig


# ---------------------------------------------------------------------------
# 페이지 구성
# ---------------------------------------------------------------------------
st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")
st.caption("EDATA 7기 · 강나형")

tab_dashboard, tab_report = st.tabs(["대시보드", "개선 제안 리포트"])

with tab_dashboard:
    customers_df = load_customers()
    total_customers = len(customers_df)
    churned_customers = int(customers_df["is_churned"].sum())
    churn_rate = churned_customers / total_customers * 100

    with st.container(horizontal=True):
        st.metric("전체 고객 수", f"{total_customers:,}명", border=True)
        st.metric("이탈 고객 수", f"{churned_customers:,}명", border=True)
        st.metric("전체 이탈율", f"{churn_rate:.1f}%", border=True)

    st.divider()

    st.subheader("① VOC로 본 이탈")
    st.plotly_chart(build_voc_chart(customers_df), use_container_width=True)

    st.subheader("② 채널·만족도로 본 이탈")
    st.plotly_chart(build_channel_csat_chart(), use_container_width=True)

    st.subheader("③ 재문의 반복으로 본 이탈")
    st.plotly_chart(build_recontact_bucket_chart(customers_df), use_container_width=True)

    st.subheader("④ 요금제로 본 이탈")
    st.plotly_chart(build_plan_chart(customers_df), use_container_width=True)

    st.subheader("⑤ 지역으로 본 이탈")
    st.plotly_chart(build_region_chart(customers_df), use_container_width=True)

    st.subheader("⑥ 가입기간·이용량으로 본 이탈")
    st.plotly_chart(build_tenure_usage_scatter(customers_df), use_container_width=True)

    st.divider()

    st.subheader("상담원 관점: 직원만족도와 고객 경험")
    st.caption("BigQuery agents·consultations·satisfaction 테이블을 직접 조회 (팀 선택 시마다 재조회, 캐시 없음)")

    selected_team = st.selectbox("팀 선택", TEAM_OPTIONS)

    (enps_value, enps_n), enps_source = load_with_fallback(load_enps, load_enps_snapshot, selected_team)
    burnout_df, burnout_source = load_with_fallback(load_burnout_csat, load_burnout_csat_snapshot, selected_team)
    training_df, training_source = load_with_fallback(
        load_training_comparison, load_training_comparison_snapshot, selected_team
    )

    if "snapshot" in (enps_source, burnout_source, training_source):
        st.caption(
            f"🟡 로컬 스냅샷 데이터 ({_agent_snapshot_date_label()} 기준) — "
            "배포 환경에 BigQuery 인증 정보가 없어 그 시점 데이터로 대체 표시 중입니다"
        )
    else:
        st.caption("🟢 BigQuery 라이브 데이터")

    score_left, score_center, score_right = st.columns([1, 2, 1])
    with score_center:
        st.plotly_chart(build_enps_gauge_chart(selected_team, enps_value, enps_n), width="stretch")

    scatter_col, training_col = st.columns(2)
    with scatter_col:
        st.plotly_chart(build_burnout_csat_chart(burnout_df), width="stretch")
    with training_col:
        st.plotly_chart(build_training_comparison_chart(training_df), width="stretch")

with tab_report:
    st.markdown(load_report_markdown())
