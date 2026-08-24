from __future__ import annotations

import streamlit as st


def get_global_css() -> str:
    return """
<style>
:root {
  --vf-bg: #f5f7fc;
  --vf-panel: #ffffff;
  --vf-panel-soft: #f9faff;
  --vf-text: #111936;
  --vf-muted: #69728a;
  --vf-label: #303951;
  --vf-border: #e2e6f0;
  --vf-border-strong: #d2d8e6;
  --vf-primary: #4257e8;
  --vf-primary-dark: #3044c9;
  --vf-primary-soft: #edf1ff;
  --vf-danger: #c62828;
  --vf-shadow: 0 7px 22px rgba(29, 39, 78, 0.07);
  --vf-shadow-soft: 0 3px 12px rgba(29, 39, 78, 0.055);
  --vf-radius-card: 16px;
  --vf-radius-control: 12px;
  --vf-radius-button: 13px;
  --vf-monitor-text: #111936;
  --vf-monitor-muted: #69728a;
}

html, body, [class*="css"] {
  font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}

html, body, .stApp {
  overflow-x: hidden;
}

.stApp {
  background: var(--vf-bg);
  color: var(--vf-text);
}

div[data-testid="stElementContainer"]:has(> iframe[data-testid="stIFrame"][height="0"]),
div[data-testid="stElementContainer"].st-key-velaflow_local_api_read {
  display: none !important;
}

.block-container {
  padding-top: 1.35rem;
  padding-bottom: 2.5rem;
  max-width: 1180px;
}

h1, h2, h3, h4 {
  color: var(--vf-text) !important;
  letter-spacing: 0 !important;
}

h1 {
  font-size: 2rem !important;
  font-weight: 780 !important;
  line-height: 1.15 !important;
  margin-bottom: 0.2rem !important;
}

h2, h3 {
  font-weight: 730 !important;
}

h3 {
  font-size: 1.28rem !important;
  margin-top: 0.55rem !important;
  margin-bottom: 0.2rem !important;
}

p, li, label, div[data-testid="stMarkdownContainer"] {
  font-size: 0.95rem;
  line-height: 1.5;
}

small, [data-testid="stCaptionContainer"], .stCaption {
  color: var(--vf-muted) !important;
  font-size: 0.83rem !important;
}

/* Product and workspace headers */
.vf-home-header {
  position: relative;
  padding: 0.25rem 0 0.9rem;
}

.vf-home-header h1 {
  margin: 0 !important;
  font-size: clamp(1.85rem, 5vw, 2.35rem) !important;
}

.vf-home-header p {
  margin: 0.22rem 0 0;
  color: var(--vf-muted);
  font-size: 0.92rem;
}

.vf-home-header::after {
  content: "";
  position: absolute;
  right: 0.2rem;
  bottom: 0.55rem;
  width: 118px;
  height: 35px;
  opacity: 0.18;
  background: repeating-linear-gradient(90deg, transparent 0 7px, var(--vf-primary) 7px 9px);
  clip-path: polygon(0 70%, 8% 45%, 16% 75%, 24% 22%, 32% 58%, 40% 8%, 48% 64%, 56% 30%, 64% 78%, 72% 17%, 80% 55%, 88% 35%, 96% 72%, 100% 70%, 100% 100%, 0 100%);
  pointer-events: none;
}

.vf-page-header {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  max-width: 920px;
  margin: 0 0 1.05rem;
}

.vf-page-icon, .vf-tool-icon, .vf-welcome-icon, .vf-sidebar-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  color: #ffffff;
  background: var(--vf-primary);
  box-shadow: 0 7px 16px rgba(66, 87, 232, 0.2);
}

.vf-page-icon {
  width: 52px;
  height: 52px;
  border-radius: 15px;
  font-size: 1.4rem;
}

.vf-page-header h1 {
  margin: 0 !important;
  font-size: 1.72rem !important;
}

.vf-page-header p {
  margin: 0.18rem 0 0;
  color: var(--vf-muted);
  font-size: 0.88rem;
  line-height: 1.4;
}

.vf-accent-blue { background: #4d82dc; }
.vf-accent-green { background: #39b96c; }
.vf-accent-orange { background: #f0a12f; }
.vf-accent-pink { background: #e74a91; }
.vf-accent-purple { background: #7654df; }
.vf-accent-gray { background: #7b8498; }

/* Home */
.vf-welcome-card {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  border: 1px solid #d9dffd;
  border-radius: var(--vf-radius-card);
  background: #f8f9ff;
  padding: 1rem;
  box-shadow: var(--vf-shadow-soft);
  margin-bottom: 1.25rem;
}

.vf-welcome-icon {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  font-size: 1.35rem;
}

.vf-welcome-card strong, .vf-tool-copy strong {
  display: block;
  color: var(--vf-text);
  font-size: 0.96rem;
}

.vf-welcome-card p, .vf-tool-copy p {
  margin: 0.16rem 0 0;
  color: var(--vf-muted);
  font-size: 0.82rem;
  line-height: 1.38;
}

.vf-home-section {
  margin: 0.2rem 0 0.7rem;
}

.vf-home-section h2 {
  margin: 0 !important;
  font-size: 1.14rem !important;
}

.vf-home-section p {
  margin: 0.16rem 0 0;
  color: var(--vf-muted);
  font-size: 0.82rem;
}

.st-key-vf_home_tools [data-testid="stHorizontalBlock"] {
  align-items: stretch;
  gap: 0.75rem;
}

div[data-testid="stVerticalBlockBorderWrapper"].st-key-vf_home_tools {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.st-key-vf_home_tools [data-testid="stColumn"] > [data-testid="stVerticalBlockBorderWrapper"] {
  border: 0 !important;
  background: transparent !important;
  box-shadow: none !important;
}

.st-key-vf_home_tools [data-testid="stColumn"] > div,
.st-key-vf_home_settings > div {
  height: 100%;
}

.st-key-vf_home_tools div[data-testid="stVerticalBlockBorderWrapper"],
.st-key-vf_home_settings div[data-testid="stVerticalBlockBorderWrapper"] {
  min-height: 158px;
  padding: 0.85rem !important;
}

.vf-tool-head {
  display: flex;
  align-items: flex-start;
  gap: 0.72rem;
  min-height: 76px;
}

.vf-tool-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  font-size: 1.05rem;
}

.st-key-vf_home_tools .stButton > button,
.st-key-vf_home_settings .stButton > button {
  min-height: 2.6rem;
  margin-top: 0.35rem;
  justify-content: space-between;
}

/* Sidebar drawer */
section[data-testid="stSidebar"] {
  background: #ffffff;
  border-right: 1px solid var(--vf-border);
}

section[data-testid="stSidebar"] > div {
  padding-top: 1rem;
}

.vf-sidebar-brand {
  display: flex;
  align-items: center;
  gap: 0.72rem;
  margin: 0.12rem 0 1.2rem;
}

.vf-sidebar-mark {
  width: 42px;
  height: 42px;
  border-radius: 13px;
  font-size: 1.2rem;
}

.vf-sidebar-brand .vf-sidebar-mark {
  display: inline-flex;
  color: #ffffff;
  font-size: 1.02rem;
  font-weight: 760;
}

.vf-sidebar-brand strong {
  display: block;
  color: var(--vf-text);
  font-size: 1.15rem;
}

.vf-sidebar-brand span {
  display: block;
  color: var(--vf-muted);
  font-size: 0.77rem;
  margin-top: 0.05rem;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] > label {
  color: #8992a9 !important;
  font-size: 0.72rem !important;
  font-weight: 750 !important;
  text-transform: uppercase;
  letter-spacing: 0.04em !important;
  margin-bottom: 0.42rem;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] {
  gap: 0.42rem;
  align-items: stretch;
  width: 100%;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label {
  width: 100%;
  min-height: 3.1rem;
  padding: 0.68rem 0.72rem;
  border: 1px solid var(--vf-border);
  border-radius: 12px;
  background: #ffffff;
  color: var(--vf-text) !important;
  font-weight: 650 !important;
  box-shadow: 0 2px 8px rgba(29, 39, 78, 0.035);
  transition: background .12s ease, border-color .12s ease, color .12s ease;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:hover {
  border-color: #bfc8ec;
  background: var(--vf-panel-soft);
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label:has(input:checked) {
  border-color: #d7defc;
  background: var(--vf-primary-soft);
  color: var(--vf-primary-dark) !important;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] > label > div:first-child {
  display: none;
}

section[data-testid="stSidebar"] [data-testid="stRadio"] div[role="radiogroup"] p {
  font-size: 0.9rem;
  margin: 0;
  width: 100%;
}

.vf-sidebar-project-label {
  margin: 1.2rem 0 0.42rem;
  color: #8992a9;
  font-size: 0.7rem;
  font-weight: 750;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.vf-sidebar-project {
  border: 1px solid var(--vf-border);
  border-radius: 12px;
  padding: 0.72rem 0.78rem;
  background: var(--vf-panel-soft);
  color: var(--vf-label);
  font-size: 0.84rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Controls and content surfaces */
[data-testid="stExpander"] {
  border: 1px solid var(--vf-border) !important;
  border-radius: var(--vf-radius-control) !important;
  background: var(--vf-panel) !important;
  box-shadow: var(--vf-shadow-soft);
  margin-bottom: 0.62rem;
  overflow: hidden;
}

[data-testid="stExpander"] summary {
  font-weight: 680 !important;
  color: var(--vf-text) !important;
}

div[data-testid="stMetric"] {
  background: var(--vf-panel);
  border: 1px solid var(--vf-border);
  border-radius: var(--vf-radius-control);
  padding: 0.82rem 0.92rem;
  box-shadow: var(--vf-shadow-soft);
  min-height: 88px;
}

div[data-testid="stMetric"] label {
  color: var(--vf-muted) !important;
  font-weight: 650 !important;
}

div[data-testid="stMetricValue"] {
  color: var(--vf-text) !important;
  font-weight: 760 !important;
}

div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: var(--vf-border) !important;
  border-radius: var(--vf-radius-card) !important;
  background: var(--vf-panel) !important;
  box-shadow: var(--vf-shadow);
}

.st-key-vf_song_form {
  max-width: 820px;
}

.st-key-vf_song_form div[data-testid="stVerticalBlockBorderWrapper"] {
  padding: 1rem !important;
}

.vf-form-kicker {
  color: var(--vf-muted);
  font-size: 0.79rem;
  margin-bottom: 0.15rem;
}

div[data-testid="stWidgetLabel"] label,
div[data-testid="stWidgetLabel"] p {
  color: var(--vf-label) !important;
  font-weight: 650 !important;
}

div[data-baseweb="select"] > div,
input,
textarea {
  border-color: var(--vf-border-strong) !important;
  border-radius: var(--vf-radius-control) !important;
  background: #ffffff !important;
}

input:focus, textarea:focus,
div[data-baseweb="select"]:focus-within > div {
  border-color: var(--vf-primary) !important;
  box-shadow: 0 0 0 2px rgba(66, 87, 232, 0.11) !important;
}

textarea {
  line-height: 1.5 !important;
}

.stButton > button,
.stDownloadButton > button {
  min-height: 2.75rem;
  border-radius: var(--vf-radius-button) !important;
  font-weight: 690 !important;
  border: 1px solid var(--vf-border-strong) !important;
  transition: border-color .12s ease, box-shadow .12s ease, transform .12s ease;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: var(--vf-primary) !important;
  box-shadow: 0 4px 14px rgba(66, 87, 232, 0.14);
  transform: translateY(-1px);
}

.stButton > button:focus-visible,
.stDownloadButton > button:focus-visible {
  outline: 3px solid rgba(66, 87, 232, 0.25) !important;
  outline-offset: 2px;
}

.stButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {
  background: var(--vf-primary) !important;
  border-color: var(--vf-primary) !important;
  color: #ffffff !important;
  box-shadow: 0 7px 17px rgba(66, 87, 232, 0.2);
}

button[kind="secondary"] {
  background: #ffffff !important;
  color: var(--vf-text) !important;
}

.st-key-simple_generate_lyrics button,
.st-key-generate_mastered_wav button {
  min-height: 3.25rem !important;
  font-size: 0.98rem !important;
}

[data-testid="stDataFrame"], [data-testid="stTable"] {
  border: 1px solid var(--vf-border) !important;
  border-radius: var(--vf-radius-control) !important;
  overflow: hidden;
  background: var(--vf-panel);
}

[data-testid="stDataFrame"] * { font-size: 0.91rem; }
div[data-testid="stTabs"] button { font-weight: 680 !important; }
.stProgress > div > div > div { background-color: var(--vf-primary) !important; }
hr { margin: 1.05rem 0 !important; border-color: var(--vf-border) !important; }
code { border-radius: 8px !important; border: 1px solid var(--vf-border) !important; }

/* Existing creator surfaces inherit the premium light system. */
.vf-monitor-hero {
  border: 1px solid #d9dffd;
  border-radius: var(--vf-radius-card);
  padding: 1rem 1.1rem;
  background: #f8f9ff;
  box-shadow: var(--vf-shadow-soft);
  color: var(--vf-text);
  margin-bottom: 0.85rem;
}

.vf-monitor-hero h2, .vf-monitor-hero h3, .vf-monitor-hero p { color: var(--vf-text) !important; margin: 0; }
.vf-monitor-hero p { color: var(--vf-muted) !important; margin-top: 0.35rem; }
.vf-monitor-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.22rem 0.58rem;
  border: 1px solid #d7defc;
  border-radius: 999px;
  background: var(--vf-primary-soft);
  color: var(--vf-primary-dark);
  font-size: 0.76rem;
  font-weight: 680;
  margin: 0 0.28rem 0.48rem 0;
}

.vf-monitor-grid { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0.65rem; margin: 0.45rem 0 1rem; }
.vf-monitor-card, .vf-output-card {
  border: 1px solid var(--vf-border);
  border-radius: var(--vf-radius-control);
  background: var(--vf-panel);
  box-shadow: var(--vf-shadow-soft);
}
.vf-monitor-card { padding: 0.82rem 0.9rem; min-height: 118px; }
.vf-monitor-card strong { display:block; color:var(--vf-text); font-size:.98rem; margin-bottom:.2rem; }
.vf-monitor-card span { display:block; color:var(--vf-muted); font-size:.84rem; line-height:1.34; }
.vf-section-title { display:flex; align-items:center; justify-content:space-between; gap:.65rem; margin:1.05rem 0 .45rem; }
.vf-section-title h3 { margin:0 !important; }
.vf-section-title span { color:var(--vf-muted); font-size:.82rem; font-weight:680; }
.vf-output-card { padding:.74rem .82rem; margin-bottom:.5rem; }
.vf-output-card h4 { margin:0 0 .28rem; font-size:.98rem; color:var(--vf-text); }
.vf-output-card p { margin:0; color:var(--vf-muted); font-size:.84rem; }
.vf-step-row { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:.55rem; margin:.55rem 0 .85rem; }
.vf-step { border:1px solid var(--vf-border); border-radius:var(--vf-radius-control); padding:.6rem .7rem; background:#fff; color:var(--vf-muted); font-weight:680; }
.vf-step-active { border-color:#d7defc; background:var(--vf-primary-soft); color:var(--vf-primary-dark); }

@media (max-width: 768px) {
  .block-container {
    padding-top: max(4.5rem, calc(env(safe-area-inset-top) + 3.75rem)) !important;
    padding-left: 0.9rem;
    padding-right: 0.9rem;
    padding-bottom: 1.4rem;
  }

  .vf-home-header { padding-top: 0; padding-bottom: 0.75rem; }
  .vf-home-header::after { width: 92px; opacity: 0.13; }
  .vf-page-header { gap: 0.72rem; margin-bottom: 0.8rem; }
  .vf-page-icon { width: 46px; height: 46px; border-radius: 13px; font-size: 1.2rem; }
  .vf-page-header h1 { font-size: 1.48rem !important; line-height: 1.15 !important; }
  .vf-page-header p { font-size: 0.78rem; line-height: 1.32; }

  h1, .main-title, .velaflow-header { font-size: 1.58rem !important; line-height: 1.15 !important; margin-top: 0.15rem !important; margin-bottom: 0.08rem !important; }
  h2 { font-size: 1.24rem !important; line-height: 1.24 !important; margin-top: 0.4rem !important; margin-bottom: 0.12rem !important; }
  h3 { font-size: 1.06rem !important; line-height: 1.25 !important; margin-top: 0.35rem !important; }
  p, li, label, div[data-testid="stMarkdownContainer"] { font-size: 0.91rem; line-height: 1.42; }
  [data-testid="stCaptionContainer"], .stCaption { font-size: 0.78rem !important; line-height: 1.32 !important; }
  div[data-testid="stVerticalBlock"] { gap: 0.3rem !important; }
  div[data-testid="stWidgetLabel"] { margin-bottom: 0.08rem !important; }
  [data-testid="stColumn"] { width: 100% !important; min-width: 100% !important; flex: 1 1 100% !important; }

  .stApp .st-key-vf_home_tools [data-testid="stHorizontalBlock"] { width: 100% !important; max-width: 100% !important; flex-wrap: nowrap !important; gap: 0.58rem !important; }
  .stApp .st-key-vf_home_tools div[data-testid="stColumn"] { width: calc(50% - 0.29rem) !important; min-width: 0 !important; max-width: calc(50% - 0.29rem) !important; flex: 0 1 calc(50% - 0.29rem) !important; }
  .st-key-vf_home_tools [data-testid="stColumn"] [data-testid="stVerticalBlock"],
  .st-key-vf_home_tools [data-testid="stColumn"] [data-testid="stElementContainer"],
  .st-key-vf_home_tools [data-testid="stColumn"] [data-testid="stMarkdown"],
  .st-key-vf_home_tools [data-testid="stColumn"] [data-testid="stButton"] {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 0 !important;
  }
  .st-key-vf_home_tools div[data-testid="stVerticalBlockBorderWrapper"] { min-height: 168px; padding: 0.72rem !important; }
  .vf-tool-head { display: block; min-height: 112px; }
  .vf-tool-icon { width: 38px; height: 38px; margin-bottom: 0.55rem; }
  .vf-tool-copy strong { font-size: 0.86rem; }
  .vf-tool-copy p { font-size: 0.73rem; line-height: 1.3; }
  .vf-welcome-card { padding: 0.82rem; margin-bottom: 1rem; }
  .vf-welcome-card p { font-size: 0.76rem; }

  div[data-testid="stMetric"] { min-height: 68px; padding: 0.62rem 0.72rem; }
  div[data-testid="stMetricValue"] { font-size: 1.02rem !important; }
  [data-testid="stExpander"] { margin-bottom: 0.38rem; }
  [data-testid="stExpander"] summary { min-height: 2.75rem; padding-top: 0.52rem !important; padding-bottom: 0.52rem !important; }
  .stButton > button, .stDownloadButton > button { min-height: 2.75rem; padding-left: 0.8rem !important; padding-right: 0.8rem !important; }
  textarea { min-height: 92px !important; }
  div[data-testid="stRadio"] label, div[data-testid="stCheckbox"] label, div[data-testid="stToggle"] label { min-height: 2.75rem; display:flex; align-items:center; }
  .stAlert { padding: 0.62rem 0.72rem !important; }
  section[data-testid="stSidebar"] > div { padding-top: 0.65rem; }
  section[data-testid="stSidebar"] { width: min(88vw, 350px) !important; }
  section[data-testid="stSidebar"] [data-testid="stRadio"] label, section[data-testid="stSidebar"] [data-baseweb="select"] { font-size: 0.92rem !important; }
  hr { margin: 0.72rem 0 !important; }
  .vf-monitor-hero { padding: 0.86rem 0.9rem; border-radius: 14px; }
  .vf-monitor-grid, .vf-step-row { grid-template-columns: 1fr; gap: 0.45rem; }
  .vf-monitor-card { min-height: auto; padding: 0.7rem 0.78rem; }
  .vf-section-title { display:block; margin-top:.8rem; }
  .st-key-vf_song_form div[data-testid="stVerticalBlockBorderWrapper"] { padding: 0.82rem !important; }
}

@media (max-width: 360px) {
  .st-key-vf_home_tools [data-testid="stHorizontalBlock"] { flex-wrap: wrap !important; }
  .st-key-vf_home_tools [data-testid="stColumn"] { width: 100% !important; flex-basis: 100% !important; }
  .vf-tool-head { display:flex; min-height:74px; }
}

@media (min-width: 1200px) {
  .vf-home-shell { max-width: 980px; }
  .st-key-vf_song_form { max-width: 840px; }
}
</style>
"""


def apply_global_styles() -> None:
    st.markdown(get_global_css(), unsafe_allow_html=True)
