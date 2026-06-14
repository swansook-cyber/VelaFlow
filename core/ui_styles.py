from __future__ import annotations

import streamlit as st


def get_global_css() -> str:
    return """
<style>
:root {
  --vf-bg: #f7f8fb;
  --vf-panel: #ffffff;
  --vf-panel-soft: #fbfcfe;
  --vf-text: #151a2d;
  --vf-muted: #5b6478;
  --vf-border: #d9deea;
  --vf-border-strong: #c7cedd;
  --vf-primary: #2f5be7;
  --vf-primary-dark: #2448bd;
  --vf-danger: #c62828;
  --vf-shadow: 0 8px 22px rgba(20, 29, 53, 0.07);
  --vf-monitor-text: #f8fafc;
  --vf-monitor-muted: #aeb8ca;
}

html, body, [class*="css"] {
  font-family: Inter, "Segoe UI", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

.stApp {
  background: var(--vf-bg);
  color: var(--vf-text);
}

.block-container {
  padding-top: 1.7rem;
  padding-bottom: 2.4rem;
  max-width: 1420px;
}

h1 {
  font-size: 2.15rem !important;
  font-weight: 760 !important;
  letter-spacing: 0 !important;
  color: var(--vf-text) !important;
  margin-bottom: 0.2rem !important;
}

h2, h3 {
  font-weight: 700 !important;
  letter-spacing: 0 !important;
  color: var(--vf-text) !important;
}

h3 {
  font-size: 1.38rem !important;
  margin-top: 0.7rem !important;
  margin-bottom: 0.18rem !important;
}

p, li, label, div[data-testid="stMarkdownContainer"] {
  font-size: 0.96rem;
  line-height: 1.52;
}

small, [data-testid="stCaptionContainer"], .stCaption {
  color: var(--vf-muted) !important;
  font-size: 0.84rem !important;
}

section[data-testid="stSidebar"] {
  background: #eef2f8;
  border-right: 1px solid var(--vf-border-strong);
}

section[data-testid="stSidebar"] > div {
  padding-top: 1.1rem;
}

section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label {
  color: #172036 !important;
  font-weight: 700 !important;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
  color: #303a50;
}

[data-testid="stExpander"] {
  border: 1px solid var(--vf-border-strong) !important;
  border-radius: 8px !important;
  background: rgba(255,255,255,0.68) !important;
  box-shadow: 0 2px 8px rgba(20, 29, 53, 0.035);
  margin-bottom: 0.55rem;
}

[data-testid="stExpander"] summary {
  font-weight: 700 !important;
  color: var(--vf-text) !important;
}

div[data-testid="stMetric"] {
  background: var(--vf-panel);
  border: 1px solid var(--vf-border);
  border-radius: 8px;
  padding: 0.82rem 0.92rem;
  box-shadow: var(--vf-shadow);
  min-height: 88px;
}

div[data-testid="stMetric"] label {
  color: var(--vf-muted) !important;
  font-weight: 700 !important;
}

div[data-testid="stMetricValue"] {
  color: var(--vf-text) !important;
  font-weight: 760 !important;
}

div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--vf-border) !important;
  border-radius: 8px !important;
  background: var(--vf-panel) !important;
  box-shadow: 0 5px 15px rgba(20, 29, 53, 0.055);
}

.stButton > button,
.stDownloadButton > button {
  min-height: 2.45rem;
  border-radius: 7px !important;
  font-weight: 700 !important;
  border: 1px solid var(--vf-border-strong) !important;
  transition: border-color .12s ease, box-shadow .12s ease, transform .12s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: var(--vf-primary) !important;
  box-shadow: 0 3px 12px rgba(47, 91, 231, 0.12);
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
  background: var(--vf-primary) !important;
  border-color: var(--vf-primary-dark) !important;
  color: #ffffff !important;
}

button[kind="secondary"] {
  background: #ffffff !important;
  color: var(--vf-text) !important;
}

[data-testid="stDataFrame"],
[data-testid="stTable"] {
  border: 1px solid var(--vf-border) !important;
  border-radius: 8px !important;
  overflow: hidden;
  background: var(--vf-panel);
}

[data-testid="stDataFrame"] * {
  font-size: 0.91rem;
}

div[data-testid="stTabs"] button {
  font-weight: 700 !important;
}

div[data-baseweb="select"] > div,
input,
textarea {
  border-color: var(--vf-border-strong) !important;
  border-radius: 7px !important;
}

textarea {
  line-height: 1.5 !important;
}

.stProgress > div > div > div {
  background-color: var(--vf-primary) !important;
}

hr {
  margin: 1.05rem 0 !important;
  border-color: var(--vf-border) !important;
}

code {
  border-radius: 7px !important;
  border: 1px solid var(--vf-border) !important;
}

.vf-monitor-hero {
  border: 1px solid rgba(125, 211, 252, 0.26);
  border-radius: 12px;
  padding: 1.05rem 1.15rem;
  background:
    radial-gradient(circle at top right, rgba(125, 211, 252, 0.18), transparent 34%),
    linear-gradient(135deg, #111827 0%, #182033 58%, #101624 100%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.22);
  color: var(--vf-monitor-text);
  margin-bottom: 0.85rem;
}

.vf-monitor-hero h2,
.vf-monitor-hero h3,
.vf-monitor-hero p {
  color: var(--vf-monitor-text) !important;
  margin: 0;
}

.vf-monitor-hero p {
  color: var(--vf-monitor-muted) !important;
  margin-top: 0.35rem;
}

.vf-monitor-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.22rem 0.58rem;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  color: var(--vf-monitor-text);
  font-size: 0.78rem;
  font-weight: 700;
  margin: 0 0.28rem 0.48rem 0;
}

.vf-monitor-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0.65rem;
  margin: 0.45rem 0 1rem 0;
}

.vf-monitor-card {
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  box-shadow: var(--vf-shadow);
  padding: 0.82rem 0.9rem;
  min-height: 118px;
}

.vf-monitor-card strong {
  display: block;
  color: var(--vf-text);
  font-size: 0.98rem;
  margin-bottom: 0.2rem;
}

.vf-monitor-card span {
  display: block;
  color: var(--vf-muted);
  font-size: 0.84rem;
  line-height: 1.34;
}

.vf-section-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem;
  margin: 1.05rem 0 0.45rem 0;
}

.vf-section-title h3 {
  margin: 0 !important;
}

.vf-section-title span {
  color: var(--vf-muted);
  font-size: 0.82rem;
  font-weight: 700;
}

.vf-output-card {
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  background: var(--vf-panel);
  padding: 0.74rem 0.82rem;
  box-shadow: 0 5px 15px rgba(20, 29, 53, 0.055);
  margin-bottom: 0.5rem;
}

.vf-output-card h4 {
  margin: 0 0 0.28rem 0;
  font-size: 0.98rem;
  color: var(--vf-text);
}

.vf-output-card p {
  margin: 0;
  color: var(--vf-muted);
  font-size: 0.84rem;
}

.vf-step-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.55rem;
  margin: 0.55rem 0 0.85rem 0;
}

.vf-step {
  border: 1px solid var(--vf-border);
  border-radius: 10px;
  padding: 0.6rem 0.7rem;
  background: #ffffff;
  color: var(--vf-muted);
  font-weight: 700;
}

.vf-step-active {
  border-color: rgba(47, 91, 231, 0.46);
  background: #eef4ff;
  color: var(--vf-primary-dark);
}

@media (max-width: 768px) {
  .block-container {
    padding-top: max(2.5rem, calc(env(safe-area-inset-top) + 1.5rem)) !important;
    padding-left: 0.9rem;
    padding-right: 0.9rem;
    padding-bottom: 1.55rem;
  }

  h1,
  .main-title,
  .velaflow-header {
    font-size: 1.58rem !important;
    line-height: 1.15 !important;
    margin-top: 0.75rem !important;
    margin-bottom: 0.08rem !important;
  }

  h2 {
    font-size: 1.28rem !important;
    line-height: 1.24 !important;
  }

  h3 {
    font-size: 1.08rem !important;
    line-height: 1.25 !important;
    margin-top: 0.35rem !important;
    margin-bottom: 0.08rem !important;
  }

  p, li, label, div[data-testid="stMarkdownContainer"] {
    font-size: 0.92rem;
    line-height: 1.42;
  }

  [data-testid="stCaptionContainer"], .stCaption {
    font-size: 0.78rem !important;
    line-height: 1.32 !important;
  }

  div[data-testid="stVerticalBlock"] {
    gap: 0.42rem !important;
  }

  [data-testid="column"] {
    width: 100% !important;
    min-width: 100% !important;
    flex: 1 1 100% !important;
  }

  div[data-testid="stMetric"] {
    min-height: 68px;
    padding: 0.62rem 0.72rem;
  }

  div[data-testid="stMetricValue"] {
    font-size: 1.02rem !important;
  }

  [data-testid="stExpander"] {
    margin-bottom: 0.38rem;
  }

  [data-testid="stExpander"] summary {
    padding-top: 0.62rem !important;
    padding-bottom: 0.62rem !important;
  }

  .stButton > button,
  .stDownloadButton > button {
    min-height: 2.72rem;
    width: 100%;
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
  }

  textarea {
    min-height: 104px !important;
  }

  .stAlert {
    padding: 0.62rem 0.72rem !important;
  }

  section[data-testid="stSidebar"] > div {
    padding-top: 0.65rem;
  }

  section[data-testid="stSidebar"] [data-testid="stRadio"] label,
  section[data-testid="stSidebar"] [data-baseweb="select"] {
    font-size: 0.92rem !important;
  }

  hr {
    margin: 0.72rem 0 !important;
  }

  .vf-monitor-hero {
    padding: 0.86rem 0.9rem;
    border-radius: 10px;
  }

  .vf-monitor-grid,
  .vf-step-row {
    grid-template-columns: 1fr;
    gap: 0.45rem;
  }

  .vf-monitor-card {
    min-height: auto;
    padding: 0.7rem 0.78rem;
  }

  .vf-section-title {
    display: block;
    margin-top: 0.8rem;
  }
}
</style>
"""


def apply_global_styles() -> None:
    st.markdown(get_global_css(), unsafe_allow_html=True)
