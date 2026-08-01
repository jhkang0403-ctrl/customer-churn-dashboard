import streamlit as st

st.set_page_config(page_title="고객은 왜 이탈하는가", layout="wide")

pg = st.navigation(
    [
        st.Page("app_pages/01_dashboard.py", title="대시보드", icon=":material/dashboard:"),
        st.Page("app_pages/02_report.py", title="개선 제안 리포트", icon=":material/description:"),
        st.Page("app_pages/03_channel_efficiency.py", title="채널 효율", icon=":material/payments:"),
    ],
    position="top",
)
pg.run()
