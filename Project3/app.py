import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import io
import os
import glob
from sklearn.ensemble import IsolationForest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

st.set_page_config(
    page_title="SurveyPoint",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── עיצוב ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&family=Orbitron:wght@700;900&display=swap');

* { font-family: 'Heebo', sans-serif !important; direction: rtl; }
.stApp { background: #0A0E1A; }

/* ══ HERO — Engineering Scanner ══ */
@keyframes scan-beam {
    0%   { top: 0%; opacity: 0; }
    5%   { opacity: 1; }
    95%  { opacity: 1; }
    100% { top: 100%; opacity: 0; }
}
@keyframes pulse-ring {
    0%   { transform: scale(0.85); opacity: 0.9; }
    50%  { transform: scale(1.05); opacity: 0.5; }
    100% { transform: scale(0.85); opacity: 0.9; }
}
@keyframes pulse-ring2 {
    0%   { transform: scale(1); opacity: 0.6; }
    50%  { transform: scale(1.2); opacity: 0.2; }
    100% { transform: scale(1); opacity: 0.6; }
}
@keyframes coord-blink {
    0%,88%,100% { opacity: 1; }
    92%          { opacity: 0.15; }
}
@keyframes status-pulse {
    0%,100% { opacity: 1; }
    50%     { opacity: 0.4; }
}
.hero {
    position: relative;
    border: 1px solid rgba(0,212,255,0.3);
    border-radius: 16px;
    padding: 56px 40px 48px;
    text-align: center;
    margin-bottom: 28px;
    overflow: hidden;
    background-color: #070d18;
    background-image:
        linear-gradient(rgba(0,212,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.035) 1px, transparent 1px),
        linear-gradient(rgba(0,212,255,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.07) 1px, transparent 1px);
    background-size: 20px 20px, 20px 20px, 100px 100px, 100px 100px;
    box-shadow: 0 0 100px rgba(0,212,255,0.07), inset 0 0 60px rgba(0,0,0,0.4);
}
/* Scanning beam */
.hero-scan {
    position: absolute;
    left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent 0%, rgba(0,212,255,0.1) 20%,
                rgba(0,212,255,0.7) 50%, rgba(0,212,255,0.1) 80%, transparent 100%);
    animation: scan-beam 4s ease-in-out infinite;
    pointer-events: none;
}
/* CAD corner markers */
.hero-corner {
    position: absolute;
    width: 22px; height: 22px;
    border-color: rgba(0,212,255,0.55);
    border-style: solid;
}
.hc-tl { top:12px; left:12px;  border-width: 2px 0 0 2px; }
.hc-tr { top:12px; right:12px; border-width: 2px 2px 0 0; }
.hc-bl { bottom:12px; left:12px;  border-width: 0 0 2px 2px; }
.hc-br { bottom:12px; right:12px; border-width: 0 2px 2px 0; }
/* Crosshair target */
.hero-target {
    position: absolute;
    left: 6%;
    top: 50%;
    transform: translateY(-50%);
    width: 90px; height: 90px;
    display: flex; align-items: center; justify-content: center;
}
.ht-ring1 {
    position: absolute;
    width: 90px; height: 90px;
    border-radius: 50%;
    border: 1.5px solid rgba(0,212,255,0.5);
    animation: pulse-ring 2.5s ease-in-out infinite;
}
.ht-ring2 {
    position: absolute;
    width: 58px; height: 58px;
    border-radius: 50%;
    border: 1px solid rgba(0,212,255,0.35);
    animation: pulse-ring2 2.5s ease-in-out infinite 0.4s;
}
.ht-cross-h {
    position: absolute;
    width: 90px; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(0,212,255,0.5), transparent);
}
.ht-cross-v {
    position: absolute;
    height: 90px; width: 1px;
    background: linear-gradient(180deg, transparent, rgba(0,212,255,0.5), transparent);
}
.ht-dot {
    position: absolute;
    width: 5px; height: 5px;
    border-radius: 50%;
    background: #00D4FF;
    box-shadow: 0 0 8px #00D4FF;
}
/* Coordinate readout */
.hero-coords {
    position: absolute;
    right: 18px; bottom: 14px;
    font-family: 'Courier New', monospace;
    font-size: 0.72rem;
    color: rgba(0,212,255,0.6);
    text-align: right;
    line-height: 1.6;
    animation: coord-blink 5s infinite;
    letter-spacing: 0.5px;
}
/* Status bar */
.hero-status {
    position: absolute;
    left: 18px; bottom: 14px;
    display: flex; gap: 16px;
    font-size: 0.65rem;
    letter-spacing: 1.5px;
    font-family: 'Orbitron', sans-serif;
    color: rgba(0,212,255,0.45);
}
.hs-dot {
    color: #00ff88;
    animation: status-pulse 2s infinite;
    margin-left: 4px;
}
.hero-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 3.4rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 8px;
    text-shadow:
        0 0 15px rgba(0,212,255,1),
        0 0 35px rgba(0,212,255,0.7),
        0 0 70px rgba(0,212,255,0.35),
        0 0 120px rgba(0,212,255,0.15);
    margin-bottom: 14px;
    position: relative;
}
.hero-sub {
    color: rgba(144,224,239,0.85);
    font-size: 1rem;
    letter-spacing: 0.5px;
    position: relative;
}

/* Metrics */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1b2a, #162032) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    border-radius: 14px !important;
    padding: 16px !important;
}
[data-testid="stMetricValue"] { color: #00D4FF !important; font-size: 2rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #90e0ef !important; }
[data-testid="stMetricDelta"] { color: #00ff88 !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(13,27,42,0.8);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: #90e0ef !important;
    font-weight: 600;
    font-size: 1rem;
    border-radius: 8px;
    padding: 8px 18px;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,212,255,0.15) !important;
    color: #00D4FF !important;
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #00D4FF, #0077b6) !important;
    color: #0A0E1A !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 28px !important;
    font-size: 1rem !important;
    transition: all 0.3s !important;
}
.stButton > button:hover {
    box-shadow: 0 4px 24px rgba(0,212,255,0.5) !important;
    transform: translateY(-1px);
}
.stDownloadButton button {
    background: linear-gradient(135deg, #00ff88, #00b4d8) !important;
    color: #0A0E1A !important;
    font-weight: 900 !important;
    border: none !important;
    border-radius: 10px !important;
    width: 100% !important;
}

hr { border-color: rgba(0,212,255,0.15) !important; }

[data-testid="stFileUploader"] {
    background: rgba(13,27,42,0.6) !important;
    border: 2px dashed rgba(0,212,255,0.35) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploader"] p,
[data-testid="stFileUploader"] span,
[data-testid="stFileUploaderDropzone"] > div > p,
[data-testid="stFileUploaderDropzone"] small {
    color: #ffffff !important;
}
/* Fix Uploadpload — hide all button children, show clean ::after */
[data-testid="stFileUploaderDropzone"] button {
    position: relative !important;
    min-width: 120px !important;
    direction: ltr !important;
}
[data-testid="stFileUploaderDropzone"] button * {
    visibility: hidden !important;
}
[data-testid="stFileUploaderDropzone"] button::after {
    content: "Browse files";
    visibility: visible !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 14px !important;
    font-family: 'Heebo', sans-serif !important;
    direction: ltr !important;
    white-space: nowrap !important;
}
.stTextInput input {
    background: rgba(13,27,42,0.8) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
    border-radius: 8px !important;
    color: white !important;
}
.stSelectbox > div > div {
    background: rgba(13,27,42,0.8) !important;
    border: 1px solid rgba(0,212,255,0.3) !important;
}
.stMarkdown h3 { color: #00D4FF !important; }
</style>
""", unsafe_allow_html=True)

# ── Hero ───────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-scan"></div>
    <div class="hero-corner hc-tl"></div>
    <div class="hero-corner hc-tr"></div>
    <div class="hero-corner hc-bl"></div>
    <div class="hero-corner hc-br"></div>
    <div class="hero-target">
        <div class="ht-ring1"></div>
        <div class="ht-ring2"></div>
        <div class="ht-cross-h"></div>
        <div class="ht-cross-v"></div>
        <div class="ht-dot"></div>
    </div>
    <div class="hero-title">SURVEYPOINT</div>
    <div class="hero-sub">מערכת חכמה לניתוח תיקי חישובים הנדסיים | אוניברסיטת אריאל</div>
    <div class="hero-coords">
        Y: 151,650.99<br>
        X: 243,464.96<br>
        &Delta;: &plusmn;0.003m
    </div>
    <div class="hero-status">
        <span><span class="hs-dot">&#9679;</span> ACTIVE</span>
        <span>GEMINI AI</span>
        <span>ITM GRID</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── פונקציות ──────────────────────────────────────────────────────────────────

def load_csv(src, is_bytes=False):
    for enc in ["utf-8-sig", "cp1255", "utf-8", "latin-1"]:
        try:
            raw = io.BytesIO(src) if is_bytes else src
            df = pd.read_csv(raw, encoding=enc)
            df = df.iloc[:, :3].copy()
            df.columns = ["שם נקודה", "Y", "X"]
            df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
            df["X"] = pd.to_numeric(df["X"], errors="coerce")
            df = df.dropna(subset=["Y", "X"])
            if len(df) > 0:
                return df
        except Exception:
            continue
    return None

def get_datasets():
    result = {}
    for i in ["1", "2", "3", "4"]:
        folder = os.path.join(ROOT_DIR, "DATA", i)
        for ext in [".CSV", ".csv"]:
            p = os.path.join(folder, f"coordinates_{i}{ext}")
            if os.path.exists(p):
                result[i] = p
                break
        if i not in result:
            files = glob.glob(os.path.join(folder, "*.csv")) + glob.glob(os.path.join(folder, "*.CSV"))
            if files:
                result[i] = files[0]
    return result

def run_anomaly(df, contamination=0.05):
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    coords = df[["Y", "X"]].copy()
    df = df.copy()
    df["pred"] = model.fit_predict(coords)
    df["סטטוס"] = df["pred"].map({1: "✅ תקין", -1: "⚠️ חשוד"})
    return df

def load_api_key():
    key_file = os.path.join(ROOT_DIR, "key.txt")
    if os.path.exists(key_file):
        with open(key_file, encoding="utf-8") as f:
            k = f.read().strip()
        if k:
            return k
    return None

DATASETS  = get_datasets()
AUTO_KEY  = load_api_key()
COLORS    = ["#00D4FF", "#ffd700", "#00ff88", "#ff6b6b"]
PLOT_STYLE = dict(
    plot_bgcolor="rgba(10,14,26,0.95)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#90e0ef", size=13),
    legend=dict(bgcolor="rgba(13,27,42,0.9)", bordercolor="#00D4FF", borderwidth=1),
    margin=dict(l=50, r=20, t=30, b=50),
)

_ck = [0]
def ck():
    _ck[0] += 1
    return f"k{_ck[0]}"

def show_anomaly_chart(df_res):
    n_total = len(df_res)
    n_ok    = (df_res["pred"] == 1).sum()
    n_bad   = (df_res["pred"] == -1).sum()
    pct     = round(n_ok / n_total * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📍 סה״כ נקודות", n_total)
    c2.metric("✅ תקינות",       n_ok)
    c3.metric("⚠️ חשודות",       n_bad)
    c4.metric("🎯 אחוז תקינות", f"{pct}%")

    df_ok  = df_res[df_res["pred"] == 1]
    df_bad = df_res[df_res["pred"] == -1]
    fig = go.Figure()
    if len(df_ok):
        fig.add_trace(go.Scatter(
            x=df_ok["Y"], y=df_ok["X"], mode="markers", name="✅ תקין",
            marker=dict(size=7, color="#00ff88", symbol="circle",
                        line=dict(color="#00cc66", width=1)),
            text=df_ok["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y:%{x:.3f}<br>X:%{y:.3f}<extra></extra>",
        ))
    if len(df_bad):
        fig.add_trace(go.Scatter(
            x=df_bad["Y"], y=df_bad["X"], mode="markers", name="⚠️ חשוד",
            marker=dict(size=13, color="#ff3333", symbol="x",
                        line=dict(color="#ff0000", width=2.5)),
            text=df_bad["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y:%{x:.3f}<br>X:%{y:.3f}<extra></extra>",
        ))
    fig.update_layout(**PLOT_STYLE, height=460,
        xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
        yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, key=ck())

    if n_bad > 0:
        st.markdown("### ⚠️ נקודות חשודות")
        df_bad_show = df_bad[["שם נקודה", "Y", "X"]].reset_index(drop=True)
        st.dataframe(df_bad_show, use_container_width=True,
                     column_config={
                         "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                         "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                     })
        csv_bad = df_bad_show.to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ הורד נקודות חשודות — CSV", data=csv_bad,
                           file_name="suspicious_points.csv",
                           mime="text/csv", key=ck())

    out = io.BytesIO()
    df_res.drop(columns=["pred"]).to_excel(out, index=False)
    st.download_button("⬇️ הורד Excel — תוצאות מלאות", data=out.getvalue(),
                       file_name="SurveyPoint_analysis.xlsx",
                       mime="application/vnd.ms-excel", key=ck())

# ── לשוניות ───────────────────────────────────────────────────────────────────
tab_ocr, tab_detect, tab_eda, tab_home = st.tabs([
    "📄  חילוץ מ-TIF/PDF",
    "🤖  זיהוי חריגים",
    "📊  ניתוח נתונים",
    "🏠  סקירה כללית",
])

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 1 — חילוץ
# ══════════════════════════════════════════════════════════════════════════════
with tab_ocr:
    st.markdown("## 📄 חילוץ קואורדינטות מתיק חישובים")
    st.markdown("העלאת תיק חישובים (TIF/PDF) לחילוץ קואורדינטות אוטומטי.")
    st.markdown("---")

    if AUTO_KEY:
        gemini_key = AUTO_KEY
        st.success("✅ Gemini API Key נטען אוטומטית")
    else:
        with st.expander("🔑 Gemini API Key", expanded=True):
            gemini_key = st.text_input(
                "הכניסי Gemini API Key:",
                type="password",
                placeholder="AQ. ... או AIzaSy...",
                key="gemini_key",
                help="או צרי קובץ key.txt בתיקיית הפרויקט"
            )
            if not gemini_key:
                st.caption("💡 ניתן גם ליצור קובץ key.txt עם ה-Key בתיקיית הפרויקט")

    st.markdown("---")

    st.markdown("### 📂 קובץ תיק חישובים")
    uploaded = st.file_uploader(
        "גרירת קובץ TIF/PDF לכאן",
        type=["tif", "TIF", "tiff", "TIFF", "pdf", "PDF"],
        key="ocr_upload",
    )

    if uploaded:
        file_bytes = uploaded.read()
        fname = uploaded.name.lower()

        total_pages = 1
        if not fname.endswith(".pdf"):
            try:
                from PIL import Image as _PIL
                _img = _PIL.open(io.BytesIO(file_bytes))
                total_pages = getattr(_img, "n_frames", 1)
            except Exception:
                pass

        st.info(f"📂 **{uploaded.name}** | {len(file_bytes)//1024} KB"
                + (f" | **{total_pages} עמודים**" if total_pages > 1 else ""))

        if st.button("🚀 התחל חילוץ קואורדינטות", type="primary", key="ocr_btn"):
            try:
                from extractor import extract_from_tif, extract_from_pdf, extract_with_gemini
            except ImportError as e:
                st.error(f"שגיאת טעינה: {e}")
                st.stop()

            prog = st.progress(0)
            stat = st.empty()
            t_start = __import__("time").time()

            def cb(done, total):
                prog.progress(int(done / total * 100))
                stat.text(f"מעבד עמוד {done} מתוך {total}...")

            with st.spinner("מחלץ קואורדינטות..."):
                try:
                    if fname.endswith(".pdf"):
                        df_ocr = extract_from_pdf(file_bytes)
                    elif gemini_key:
                        df_ocr = extract_with_gemini(file_bytes, api_key=gemini_key, progress_cb=cb)
                    else:
                        df_ocr = extract_from_tif(file_bytes, progress_cb=cb)
                    prog.progress(100)
                    stat.empty()
                except Exception as e:
                    st.error(f"שגיאה בחילוץ — נסי שוב או בדקי את ה-Key: {e}")
                    df_ocr = pd.DataFrame(columns=["שם נקודה", "Y", "X"])

            elapsed = __import__("time").time() - t_start

            core_cols = ["שם נקודה", "Y", "X"]
            ocr_core = df_ocr[core_cols] if all(c in df_ocr.columns for c in core_cols) else df_ocr
            st.session_state["ocr_df"] = ocr_core if len(ocr_core) > 0 else None

            if len(df_ocr) == 0:
                st.warning("לא נמצאו קואורדינטות בקובץ זה.")
            else:
                st.success(f"✅ חולצו **{len(df_ocr)} נקודות** | ⏱ {elapsed:.0f} שניות")

                # טבלה + מפה
                col_t, col_p = st.columns([1, 2])
                with col_t:
                    st.dataframe(ocr_core, use_container_width=True, height=360,
                        column_config={
                            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                        })
                with col_p:
                    fig_o = px.scatter(ocr_core, x="Y", y="X", hover_name="שם נקודה",
                                       color_discrete_sequence=["#00D4FF"])
                    fig_o.update_traces(marker=dict(size=7))
                    fig_o.update_layout(**PLOT_STYLE, height=360,
                        xaxis=dict(title="Y", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
                        yaxis=dict(title="X", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
                    )
                    st.plotly_chart(fig_o, use_container_width=True, key=ck())

                col_c, col_e = st.columns(2)
                with col_c:
                    csv_out = ocr_core.to_csv(index=False).encode("utf-8-sig")
                    st.download_button("⬇️ הורד CSV", data=csv_out,
                                       file_name="coordinates_extracted.csv",
                                       mime="text/csv", key=ck())
                with col_e:
                    xls = io.BytesIO()
                    ocr_core.to_excel(xls, index=False)
                    st.download_button("⬇️ הורד Excel", data=xls.getvalue(),
                                       file_name="coordinates_extracted.xlsx",
                                       mime="application/vnd.ms-excel", key=ck())

                # ── EDA אוטומטי אחרי חילוץ ──────────────────────────────────
                if len(ocr_core) >= 5:
                    st.markdown("---")
                    st.markdown("## 📊 ניתוח אוטומטי")

                    df_analyzed = run_anomaly(ocr_core)

                    # טבלה עם סטטוס
                    st.markdown("### טבלת קואורדינטות עם סטטוס")
                    st.dataframe(
                        df_analyzed[["שם נקודה", "Y", "X", "סטטוס"]],
                        use_container_width=True,
                        column_config={
                            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                            "סטטוס": st.column_config.TextColumn("סטטוס"),
                        }
                    )

                    st.markdown("### מפת זיהוי חריגים")
                    show_anomaly_chart(df_analyzed)

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 2 — זיהוי חריגים
# ══════════════════════════════════════════════════════════════════════════════
with tab_detect:
    st.markdown("## 🤖 זיהוי חריגים")
    st.markdown("טעיני קובץ קואורדינטות — המערכת תזהה נקודות חשודות אוטומטית.")
    st.markdown("---")

    has_ocr = "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None
    source_opts = ["העלאת קובץ CSV", "מערך נתונים קיים"]
    if has_ocr:
        source_opts.insert(0, "נתונים שחולצו מ-TIF ✅")

    col_s, col_cont = st.columns([2, 1])
    with col_s:
        if has_ocr:
            st.success(f"✅ {len(st.session_state['ocr_df'])} נקודות מחולצות מוכנות")
        source = st.radio("מקור נתונים:", source_opts, horizontal=False, key="det_src")
    with col_cont:
        contamination = st.slider("רגישות לחריגים", 0.01, 0.20, 0.05, 0.01,
                                  help="0.05 = 5% מהנקודות יסומנו כחשודות")

    df_input = None
    if source == "נתונים שחולצו מ-TIF ✅":
        df_input = st.session_state["ocr_df"]
    elif source == "מערך נתונים קיים":
        if DATASETS:
            sel = st.selectbox("בחרי מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="det_sel")
            df_input = load_csv(DATASETS[sel.split()[-1]])
        else:
            st.warning("לא נמצאו מערכי נתונים")
    else:
        up = st.file_uploader("העלי קובץ CSV (שם נקודה, Y, X):",
                              type=["csv", "CSV"], key="det_csv")
        if up:
            df_input = load_csv(up.read(), is_bytes=True)
            if df_input is None:
                st.error("לא ניתן לקרוא את הקובץ — בדקי שהפורמט תקין")

    if df_input is not None and len(df_input) >= 5:
        st.markdown("---")
        st.success(f"✅ נטענו **{len(df_input)}** נקודות")
        df_r = run_anomaly(df_input, contamination=contamination)
        show_anomaly_chart(df_r)
    elif df_input is not None:
        st.warning("נדרשות לפחות 5 נקודות לניתוח חריגים")

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 3 — EDA
# ══════════════════════════════════════════════════════════════════════════════
with tab_eda:
    st.markdown("## 📊 ניתוח נתונים")
    st.markdown("---")

    eda_source = "מערך קיים"
    if "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None:
        eda_src_opt = st.radio("מקור:", ["נתונים שחולצו ✅", "מערך נתונים קיים"],
                               horizontal=True, key="eda_src")
        if eda_src_opt == "נתונים שחולצו ✅":
            df_e = st.session_state["ocr_df"]
        else:
            df_e = None
            eda_source = "מערך קיים"
    else:
        df_e = None

    if df_e is None:
        if not DATASETS:
            st.warning("לא נמצאו קבצי נתונים")
            st.stop()
        sel_e = st.selectbox("בחרי מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="eda_sel")
        df_e  = load_csv(DATASETS[sel_e.split()[-1]])
        if df_e is None:
            st.error("שגיאה בטעינת הנתונים")
            st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("מספר נקודות", len(df_e))
    c2.metric("טווח Y", f"{df_e['Y'].max()-df_e['Y'].min():.1f}")
    c3.metric("טווח X", f"{df_e['X'].max()-df_e['X'].min():.1f}")
    c4.metric("ערכים חסרים", int(df_e.isnull().sum().sum()))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### פיזור נקודות")
        fig_sc = px.scatter(df_e, x="Y", y="X", hover_name="שם נקודה",
                            color_discrete_sequence=["#00D4FF"])
        fig_sc.update_traces(marker=dict(size=6))
        fig_sc.update_layout(**PLOT_STYLE, height=360,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
            yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
        )
        st.plotly_chart(fig_sc, use_container_width=True, key=ck())

    with col2:
        st.markdown("### התפלגות Y")
        fig_hy = px.histogram(df_e, x="Y", nbins=25, color_discrete_sequence=["#ffd700"])
        fig_hy.update_layout(**PLOT_STYLE, height=360)
        st.plotly_chart(fig_hy, use_container_width=True, key=ck())

    col3, col4 = st.columns(2)
    with col3:
        st.markdown("### התפלגות X")
        fig_hx = px.histogram(df_e, x="X", nbins=25, color_discrete_sequence=["#00ff88"])
        fig_hx.update_layout(**PLOT_STYLE, height=300)
        st.plotly_chart(fig_hx, use_container_width=True, key=ck())
    with col4:
        st.markdown("### סטטיסטיקה תיאורית")
        st.dataframe(df_e[["Y", "X"]].describe().round(3), use_container_width=True, height=290)

    st.markdown("### כל הנקודות")
    st.dataframe(df_e.reset_index(drop=True), use_container_width=True, hide_index=True,
                 column_config={
                     "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                     "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                 })
    csv_out = df_e.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ הורד CSV", data=csv_out,
                       file_name="data_eda.csv", mime="text/csv", key=ck())

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 4 — סקירה כללית
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.markdown("## 🏠 סקירה כללית")
    st.markdown("---")

    # ── פרטי תיק חישובים ──────────────────────────────────────────────────────
    st.markdown("### 📋 פרטי תיק חישובים")
    c1, c2, c3, c4 = st.columns(4)
    with c1: tik_num = st.text_input("מספר תיק חישובי", key="tik_num", placeholder="למשל: 2024-15")
    with c2: gush    = st.text_input("גוש",              key="gush",    placeholder="למשל: 6719")
    with c3: helka   = st.text_input("חלקה",             key="helka",   placeholder="למשל: 42")
    with c4: year    = st.text_input("שנת התיק",         key="year",    placeholder="למשל: 1982")

    if any([tik_num, gush, helka, year]):
        st.markdown("---")
        m1, m2, m3, m4 = st.columns(4)
        if tik_num: m1.metric("📁 מספר תיק", tik_num)
        if gush:    m2.metric("🗺️ גוש",        gush)
        if helka:   m3.metric("📌 חלקה",       helka)
        if year:    m4.metric("📅 שנת התיק",   year)

    st.markdown("---")

    # ── טבלאות קואורדינטות ────────────────────────────────────────────────────
    has_data = "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None
    if has_data:
        df_src = st.session_state["ocr_df"]
        df_analyzed = run_anomaly(df_src)
        df_ok  = df_analyzed[df_analyzed["pred"] ==  1][["שם נקודה","Y","X"]].reset_index(drop=True)
        df_bad = df_analyzed[df_analyzed["pred"] == -1][["שם נקודה","Y","X"]].reset_index(drop=True)

        col_cfg = {
            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
        }

        col_ok, col_bad = st.columns(2)
        with col_ok:
            st.markdown(f"### ✅ נקודות תקינות — {len(df_ok)}")
            st.dataframe(df_ok, use_container_width=True, height=400,
                         column_config=col_cfg, hide_index=True)
            csv_ok = df_ok.to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ הורד תקינות CSV", data=csv_ok,
                               file_name="valid_points.csv", mime="text/csv", key=ck())

        with col_bad:
            st.markdown(f"### ⚠️ נקודות חשודות — {len(df_bad)}")
            if len(df_bad) > 0:
                st.dataframe(df_bad, use_container_width=True, height=400,
                             column_config=col_cfg, hide_index=True)
                csv_bad = df_bad.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ הורד חשודות CSV", data=csv_bad,
                                   file_name="suspicious_points.csv",
                                   mime="text/csv", key=ck())
            else:
                st.success("לא נמצאו נקודות חשודות!")
    else:
        st.info("💡 חלץ קובץ TIF בלשונית 'חילוץ' כדי לראות את הנקודות כאן.")

# ── תחתית ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#1e2d40;font-size:0.85rem;
border-top:1px solid rgba(0,212,255,0.1);padding-top:16px">
    📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
