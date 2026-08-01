import streamlit as st

import common as c

st.title("고객은 왜 이탈하는가 — 이탈 원인 진단 대시보드")
st.caption("EDATA 7기 · 강나형")


@st.cache_data
def load_report_markdown() -> str:
    with open(c.REPORT_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    if content.startswith("---"):
        end = content.find("\n---", 3)
        if end != -1:
            content = content[end + 4 :].lstrip("\n")
    return content


st.markdown(load_report_markdown())
