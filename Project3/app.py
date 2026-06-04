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

/* Hero */
.hero {
    position: relative;
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 20px;
    padding: 52px 40px 44px;
    text-align: center;
    margin-bottom: 28px;
    overflow: hidden;
    background-color: #0d1520;
    background-image:
        linear-gradient(rgba(0,212,255,0.07) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,0.07) 1px, transparent 1px);
    background-size: 40px 40px;
    box-shadow: 0 0 80px rgba(0,212,255,0.08);
}
.hero::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(ellipse at 50% 0%, rgba(0,212,255,0.12) 0%, transparent 70%);
    pointer-events: none;
}
.hero-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 3.2rem;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: 6px;
    text-shadow:
        0 0 20px rgba(0,212,255,0.9),
        0 0 40px rgba(0,212,255,0.6),
        0 0 80px rgba(0,212,255,0.3);
    margin-bottom: 14px;
}
.hero-sub {
    color: #90e0ef;
    font-size: 1.05rem;
    letter-spacing: 1px;
    opacity: 0.9;
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
    <div class="hero-title">SURVEYPOINT</div>
    <div class="hero-sub">מערכת חכמה לניתוח תיקי חישובים הנדסיים | אוניברסיטת אריאל</div>
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

DATASETS  = get_datasets()
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
    st.markdown("העלי תיק חישובים (TIF/PDF) לחילוץ קואורדינטות אוטומטי.")
    st.markdown("---")

    st.markdown("### 🔑 Gemini API Key")
    gemini_key = st.text_input(
        "הכניסי Gemini API Key:",
        type="password",
        placeholder="AQ. ... או AIzaSy...",
        key="gemini_key",
        help="קבלי Key חינם ב: aistudio.google.com/app/apikey"
    )
    if gemini_key:
        st.success("✅ Key הוכנס — מוכן לחילוץ")

    st.markdown("---")

    st.markdown("### 📂 קובץ תיק חישובים")
    uploaded = st.file_uploader(
        "גרורי קובץ TIF או PDF לכאן",
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

    dfs_all = {}
    if DATASETS:
        cols_m = st.columns(max(len(DATASETS), 1))
        for idx, (fld, path) in enumerate(DATASETS.items()):
            df = load_csv(path)
            dfs_all[fld] = df
            with cols_m[idx]:
                if df is not None:
                    st.metric(f"מערך {fld}", f"{len(df)} נקודות",
                              f"Y: {df['Y'].min():.0f}–{df['Y'].max():.0f}")
    else:
        st.info("לא נמצאו מערכי נתונים בתיקיית DATA")

    if dfs_all:
        col_b, col_m = st.columns(2)
        with col_b:
            st.markdown("### השוואת גדלים")
            bar_data = [{"מערך": f"מערך {k}", "נקודות": len(v)}
                        for k, v in dfs_all.items() if v is not None]
            if bar_data:
                fig_bar = px.bar(pd.DataFrame(bar_data), x="מערך", y="נקודות",
                                 color="מערך", color_discrete_sequence=COLORS)
                fig_bar.update_layout(**PLOT_STYLE, height=300, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True, key=ck())
        with col_m:
            st.markdown("### מפת כל הנקודות")
            fig_all = go.Figure()
            for idx, (fld, df) in enumerate(dfs_all.items()):
                if df is not None:
                    fig_all.add_trace(go.Scatter(
                        x=df["Y"], y=df["X"], mode="markers", name=f"מערך {fld}",
                        marker=dict(size=4, color=COLORS[idx % len(COLORS)]),
                        text=df["שם נקודה"],
                        hovertemplate="<b>%{text}</b><br>Y:%{x:.1f}<br>X:%{y:.1f}<extra></extra>",
                    ))
            fig_all.update_layout(**PLOT_STYLE, height=300,
                xaxis=dict(title="Y", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
                yaxis=dict(title="X", gridcolor="rgba(0,212,255,0.1)", zeroline=False),
            )
            st.plotly_chart(fig_all, use_container_width=True, key=ck())

# ── תחתית ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#1e2d40;font-size:0.85rem;
border-top:1px solid rgba(0,212,255,0.1);padding-top:16px">
    📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
