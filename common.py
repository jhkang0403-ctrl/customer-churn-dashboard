"""여러 페이지에서 공유하는 경로, 색상, 렌더링 헬퍼, BigQuery 연결 유틸리티."""

import os

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORT_PATH = os.path.join(BASE_DIR, "report", "고객서비스_만족도개선_리포트.md")

REFERENCE_DATE = pd.Timestamp("2024-12-31")

COLOR_NEUTRAL = "#898781"
COLOR_CRITICAL = "#d03b3b"
COLOR_BAR = "#2a78d6"
COLOR_LINE = "#eb6834"
COLOR_POSITIVE = "#2a9d57"

CHART_LAYOUT = dict(
    font=dict(size=13),
    margin=dict(t=40, b=40, l=10, r=10),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

PLOTLY_CONFIG = {"displayModeBar": False}

BQ_PROJECT_ID = "project-6342726b-6c19-4847-844"
BQ_DATASET = "project1_day1"
TEAM_OPTIONS = ["전체", "1팀", "2팀", "3팀"]

FORCE_SNAPSHOT = os.environ.get("FORCE_SNAPSHOT", "").strip().lower() in ("1", "true", "yes")


def render_hero(title: str, subtitle: str) -> None:
    """페이지 상단 제목+부제 배너. 페이지마다 동일한 형태로 재사용한다."""
    st.title(title)
    st.caption(subtitle)


def render_stat_tile(label: str, value: str, delta: str | None = None, caption: str | None = None) -> None:
    """KPI 카드 하나. st.columns와 함께 여러 개를 나란히 배치해 쓴다."""
    st.metric(label, value, delta, border=True)
    if caption:
        st.caption(caption)


@st.cache_resource
def get_bigquery_client() -> bigquery.Client | None:
    """실패(None 포함)도 st.cache_resource에 캐시된다 — 인증정보가 없는 배포 환경(예: 서비스
    계정 미설정 Streamlit Cloud)에서 매 rerun마다 느린 ADC/메타데이터서버 타임아웃을
    반복하지 않기 위함. 호출부는 반환값이 None이면 즉시 실패로 처리해야 한다."""
    try:
        if "gcp_service_account" in st.secrets:
            credentials = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"]
            )
            return bigquery.Client(project=BQ_PROJECT_ID, credentials=credentials)
    except Exception:
        # st.secrets 파일 자체가 없는 로컬 환경 등 — 기존처럼 ADC로 폴백
        pass
    try:
        return bigquery.Client(project=BQ_PROJECT_ID)
    except Exception:
        return None


def team_job_config(team: str) -> bigquery.QueryJobConfig | None:
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


def load_bigquery_marketing_spend() -> pd.DataFrame:
    """marketing_spend 테이블을 조회만 한다 (SELECT 전용 — INSERT/UPDATE/DELETE 없음)."""
    client = get_bigquery_client()
    if client is None:
        raise RuntimeError("BigQuery client unavailable")
    query = f"""
        SELECT month, channel, spend, impressions, clicks, signups
        FROM `{BQ_PROJECT_ID}.{BQ_DATASET}.marketing_spend`
        ORDER BY month, channel
    """
    return client.query(query).to_dataframe()


def load_marketing_spend_snapshot() -> pd.DataFrame:
    """배포 환경에는 BigQuery 인증 정보가 없으므로, scripts/export_marketing_snapshot.py로
    미리 내려받아 둔 스냅샷 CSV를 대신 읽는다."""
    return pd.read_csv(os.path.join(DATA_DIR, "marketing_spend_snapshot.csv"), encoding="utf-8-sig")


def load_marketing_spend_with_fallback() -> tuple[pd.DataFrame, str]:
    """FORCE_SNAPSHOT이 켜져 있으면 무조건 스냅샷을, 아니면 load_with_fallback과 같은 방식으로
    BigQuery 라이브 조회를 먼저 시도하고 인증 정보가 없거나 실패하면 스냅샷으로 대체한다.
    반환값은 (데이터프레임, source) 튜플이며 source는 "live" 또는 "snapshot"이다."""
    if FORCE_SNAPSHOT:
        return load_marketing_spend_snapshot(), "snapshot"
    return load_with_fallback(load_bigquery_marketing_spend, load_marketing_spend_snapshot)


@st.cache_data
def load_marketing_campaigns() -> pd.DataFrame:
    return pd.read_csv(os.path.join(DATA_DIR, "marketing_campaigns.csv"), encoding="utf-8-sig")


def verify_overlap(
    spend_df: pd.DataFrame, campaigns_df: pd.DataFrame, months: list[str] = ["2024-05", "2024-06"]
) -> pd.DataFrame:
    """campaigns_df(캠페인 단위)를 채널×월로 집계해 spend_df(월×채널 집계본)와 대조한다.

    채널명의 공백 표기 차이(예: "오프라인매장" vs "오프라인 매장")는 비교 전에 제거해서
    같은 채널로 통일한 뒤 비교한다.
    """
    campaigns = campaigns_df[campaigns_df["월"].isin(months)].copy()
    campaigns["채널_통일"] = campaigns["채널"].str.replace(" ", "", regex=False)
    campaign_agg = (
        campaigns.groupby(["월", "채널_통일"])
        .agg(캠페인_실집행=("실집행", "sum"), 캠페인_유입건수=("유입건수", "sum"))
        .reset_index()
        .rename(columns={"채널_통일": "채널"})
    )

    spend = spend_df[spend_df["month"].isin(months)].copy()
    spend["채널_통일"] = spend["channel"].str.replace(" ", "", regex=False)
    spend_agg = (
        spend.groupby(["month", "채널_통일"])
        .agg(spend_실집행=("spend", "sum"), spend_유입건수=("signups", "sum"))
        .reset_index()
        .rename(columns={"month": "월", "채널_통일": "채널"})
    )

    result = pd.merge(campaign_agg, spend_agg, on=["월", "채널"], how="outer")
    result["실집행_일치"] = result["캠페인_실집행"] == result["spend_실집행"]
    result["유입건수_일치"] = result["캠페인_유입건수"] == result["spend_유입건수"]
    return result.sort_values(["월", "채널"]).reset_index(drop=True)
