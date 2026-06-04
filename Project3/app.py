import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import joblib
import io
import os
import glob

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

st.set_page_config(
    page_title="SurveyPoint — מערכת חכמה למדידה",
    page_icon="📐",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── עיצוב ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&family=Orbitron:wght@700&display=swap');

* { font-family: 'Heebo', sans-serif !important; direction: rtl; }
.stApp { background: #050c1a; }

/* Hero */
.hero {
    background: linear-gradient(135deg, #0a1628 0%, #0d2040 50%, #0a1628 100%);
    border: 1px solid rgba(0,180,216,0.3);
    border-radius: 20px;
    padding: 40px;
    text-align: center;
    margin-bottom: 28px;
    box-shadow: 0 0 60px rgba(0,180,216,0.15);
}
.hero-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #00b4d8, #90e0ef, #ffd700);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
}
.hero-sub { color: #90e0ef; font-size: 1.1rem; letter-spacing: 1px; }

/* כרטיסי שלבים */
.step-card {
    background: linear-gradient(135deg, #0d1b2a, #162032);
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 16px;
    transition: border-color 0.3s;
}
.step-card:hover { border-color: rgba(0,180,216,0.6); }
.step-num {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 2rem;
    color: #ffd700;
    font-weight: 700;
}
.step-title { color: #00b4d8; font-size: 1.3rem; font-weight: 700; }
.step-desc { color: #90e0ef; font-size: 0.95rem; margin-top: 6px; }

/* Metrics */
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1b2a, #162032) !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
    border-radius: 14px !important;
    padding: 16px !important;
}
[data-testid="stMetricValue"] { color: #ffd700 !important; font-size: 2rem !important; font-weight: 700 !important; }
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
    padding: 8px 16px;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,180,216,0.2) !important;
    color: #00b4d8 !important;
}

/* כפתורים */
.stButton > button {
    background: linear-gradient(135deg, #00b4d8, #0077b6) !important;
    color: white !important;
    font-weight: 700 !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 10px 24px !important;
    font-size: 1rem !important;
    transition: all 0.3s !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #0077b6, #00b4d8) !important;
    box-shadow: 0 4px 20px rgba(0,180,216,0.4) !important;
}
.stDownloadButton button {
    background: linear-gradient(135deg, #ffd700, #ffa500) !important;
    color: #0a1628 !important;
    font-weight: 900 !important;
    border: none !important;
    border-radius: 10px !important;
    width: 100% !important;
}

/* קו הפרדה */
hr { border-color: rgba(0,180,216,0.2) !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(13,27,42,0.6) !important;
    border: 2px dashed rgba(0,180,216,0.4) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}

/* Text input */
.stTextInput input {
    background: rgba(13,27,42,0.8) !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
    border-radius: 8px !important;
    color: white !important;
}

/* Selectbox */
.stSelectbox > div > div {
    background: rgba(13,27,42,0.8) !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
}

/* Section title */
.stMarkdown h3 { color: #00b4d8 !important; }
</style>
""", unsafe_allow_html=True)

# ── כותרת ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div style="font-size:3rem; margin-bottom:12px">📐</div>
    <div class="hero-title">SURVEYPOINT</div>
    <div class="hero-sub">מערכת חכמה לניתוח תיקי חישובים הנדסיים | אוניברסיטת אריאל</div>
    <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; margin-top:16px">
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8;font-size:0.9rem">📄 חילוץ מ-TIF עם Gemini AI</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8;font-size:0.9rem">🤖 זיהוי חריגים — Isolation Forest</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8;font-size:0.9rem">📊 ניתוח EDA</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8;font-size:0.9rem">📁 ייצוא CSV / Excel</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── פונקציות ──────────────────────────────────────────────────────────────────

@st.cache_resource
def load_models():
    path = os.path.join(BASE_DIR, "Model", "model.pkl")
    return joblib.load(path) if os.path.exists(path) else None

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

DATASETS = get_datasets()
models   = load_models()
COLORS   = ["#00b4d8", "#ffd700", "#00ff88", "#ff6b6b"]

PLOT_STYLE = dict(
    plot_bgcolor="rgba(5,12,26,0.95)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#90e0ef", size=13),
    legend=dict(bgcolor="rgba(13,27,42,0.9)", bordercolor="#00b4d8", borderwidth=1),
    margin=dict(l=50, r=20, t=30, b=50),
)

_ck = [0]
def ck():
    _ck[0] += 1
    return f"k{_ck[0]}"

def anomaly_results(df_res):
    n_total = len(df_res)
    n_ok  = (df_res["pred"] == 1).sum()
    n_bad = (df_res["pred"] == -1).sum()
    pct   = round(n_ok / n_total * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📍 סה״כ נקודות",  n_total)
    c2.metric("✅ תקינות",        n_ok)
    c3.metric("⚠️ חשודות",        n_bad)
    c4.metric("🎯 אחוז תקינות",  f"{pct}%")

    df_ok  = df_res[df_res["pred"] == 1]
    df_bad = df_res[df_res["pred"] == -1]
    fig = go.Figure()
    if len(df_ok):
        fig.add_trace(go.Scatter(
            x=df_ok["Y"], y=df_ok["X"], mode="markers", name="✅ תקין",
            marker=dict(size=8, color="#00ff88", symbol="circle"),
            text=df_ok["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y:%{x:.3f}<br>X:%{y:.3f}<extra></extra>",
        ))
    if len(df_bad):
        fig.add_trace(go.Scatter(
            x=df_bad["Y"], y=df_bad["X"], mode="markers", name="⚠️ חשוד",
            marker=dict(size=12, color="#ff4444", symbol="x", line=dict(width=2)),
            text=df_bad["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y:%{x:.3f}<br>X:%{y:.3f}<extra></extra>",
        ))
    fig.update_layout(**PLOT_STYLE, height=460,
        xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
        yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, key=ck())

    if n_bad > 0:
        st.markdown("### ⚠️ נקודות חשודות")
        st.dataframe(df_bad[["שם נקודה","Y","X"]].reset_index(drop=True),
                     use_container_width=True)

    out = io.BytesIO()
    df_res.drop(columns=["pred"]).to_excel(out, index=False)
    st.download_button("⬇️ הורד Excel — תוצאות ניתוח", data=out.getvalue(),
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
    st.markdown("העלי תיק חישובים (TIF/PDF) — Gemini AI יחלץ את כל הקואורדינטות אוטומטית.")
    st.markdown("---")

    # Gemini Key
    st.markdown("### 🤖 Gemini AI Key")
    gemini_key = st.text_input(
        "הכניסי Gemini API Key:",
        type="password",
        placeholder="AQ. ... או AIzaSy...",
        key="gemini_key",
        help="קבלי Key חינם ב: aistudio.google.com/app/apikey"
    )
    if gemini_key:
        st.success("✅ Key הוכנס — Gemini מוכן לחילוץ")

    st.markdown("---")

    # העלאת קובץ
    st.markdown("### 📂 קובץ תיק חישובים")
    col_f, col_c = st.columns([3, 2])
    with col_f:
        uploaded = st.file_uploader(
            "גרורי קובץ TIF או PDF",
            type=["tif","TIF","tiff","TIFF","pdf","PDF"],
            key="ocr_upload",
        )
    with col_c:
        ref_csv = st.file_uploader(
            "CSV ייחוס לשיפור דיוק (אופציונלי)",
            type=["csv","CSV"],
            key="ref_csv",
            help="אם תעלי את קובץ הקואורדינטות המקורי — שמות שגויים יתוקנו אוטומטית לפי Spatial Matching (סף 2מ׳)"
        )

    if uploaded:
        file_bytes = uploaded.read()
        fname = uploaded.name.lower()

        total_pages = 1
        if not fname.endswith(".pdf"):
            try:
                from PIL import Image as _PIL
                _img = _PIL.open(io.BytesIO(file_bytes))
                total_pages = getattr(_img, 'n_frames', 1)
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

            def cb(done, total):
                prog.progress(int(done / total * 100))
                stat.text(f"מעבד עמוד {done} מתוך {total}...")

            ref_df = load_csv(ref_csv.getvalue(), is_bytes=True) if ref_csv else None

            with st.spinner("מריץ חילוץ..."):
                try:
                    if fname.endswith(".pdf"):
                        df_ocr = extract_from_pdf(file_bytes)
                    elif gemini_key:
                        df_ocr = extract_with_gemini(file_bytes, api_key=gemini_key, progress_cb=cb)
                        if ref_df is not None and len(df_ocr) > 0:
                            from extractor import spatial_match_to_reference
                            df_ocr = spatial_match_to_reference(df_ocr, ref_df, threshold=2.0)
                    else:
                        df_ocr = extract_from_tif(file_bytes, progress_cb=cb, reference_df=ref_df)
                    prog.progress(100)
                    stat.empty()
                except Exception as e:
                    st.error(f"שגיאה: {e}")
                    df_ocr = pd.DataFrame(columns=["שם נקודה","Y","X"])

            core_cols = ["שם נקודה","Y","X"]
            ocr_core = df_ocr[core_cols] if all(c in df_ocr.columns for c in core_cols) else df_ocr
            st.session_state["ocr_df"] = ocr_core if len(ocr_core) > 0 else None

            if len(df_ocr) == 0:
                st.warning("לא נמצאו קואורדינטות.")
            else:
                st.success(f"✅ חולצו **{len(df_ocr)} נקודות**!")

                if ref_df is not None:
                    st.info("🔗 Spatial Matching הופעל — שמות תוקנו לפי מרחק מרחבי (סף: 2מ׳)")

                col_t, col_p = st.columns([1, 2])
                with col_t:
                    st.dataframe(ocr_core, use_container_width=True, height=360,
                        column_config={
                            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                        })
                with col_p:
                    fig_o = px.scatter(ocr_core, x="Y", y="X", hover_name="שם נקודה",
                                       color_discrete_sequence=["#00b4d8"])
                    fig_o.update_traces(marker=dict(size=7))
                    fig_o.update_layout(**PLOT_STYLE, height=360,
                        xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
                        yaxis=dict(title="X", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
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

                if models and len(ocr_core) >= 5:
                    st.markdown("---")
                    st.markdown("### 🤖 זיהוי חריגים על הנתונים שחולצו")
                    mk = st.selectbox("מודל:", [f"מערך {k}" for k in models.keys()], key="ocr_model")
                    df_r = ocr_core.copy()
                    df_r["pred"] = models[mk.split()[-1]].predict(df_r[["Y","X"]])
                    df_r["סטטוס"] = df_r["pred"].map({1:"✅ תקין", -1:"⚠️ חשוד"})
                    anomaly_results(df_r)

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 2 — זיהוי חריגים
# ══════════════════════════════════════════════════════════════════════════════
with tab_detect:
    st.markdown("## 🤖 זיהוי נקודות חשודות")
    st.markdown("טעיני קובץ קואורדינטות — המערכת תזהה אוטומטית נקודות שיוצאות מהכלל.")
    st.markdown("---")

    if models is None:
        st.error("❌ מודל לא נמצא — הריצי את trainmodel.py")
        st.stop()

    has_ocr = "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None
    source_opts = ["מערך נתונים קיים", "העלאת קובץ CSV"]
    if has_ocr:
        source_opts.insert(0, "נתונים שחולצו מ-TIF ✅")

    col_s, col_m = st.columns(2)
    with col_s:
        if has_ocr:
            st.success(f"✅ {len(st.session_state['ocr_df'])} נקודות מחולצות מוכנות לניתוח")
        source = st.radio("מקור נתונים:", source_opts, horizontal=False, key="det_src")
    with col_m:
        mk = st.selectbox("מודל Isolation Forest:", [f"מערך {k}" for k in models.keys()], key="det_model")
        fk = mk.split()[-1]

    df_input = None
    if source == "נתונים שחולצו מ-TIF ✅":
        df_input = st.session_state["ocr_df"]
    elif source == "מערך נתונים קיים":
        if DATASETS:
            sel = st.selectbox("בחרי מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="det_sel")
            df_input = load_csv(DATASETS[sel.split()[-1]])
    else:
        up = st.file_uploader("העלי קובץ CSV (שם נקודה, Y, X):", type=["csv","CSV"], key="det_csv")
        if up:
            df_input = load_csv(up.read(), is_bytes=True)

    if df_input is not None and len(df_input) > 0:
        st.markdown("---")
        st.success(f"✅ נטענו **{len(df_input)}** נקודות")
        df_r = df_input.copy()
        df_r["pred"] = models[fk].predict(df_r[["Y","X"]])
        df_r["סטטוס"] = df_r["pred"].map({1:"✅ תקין", -1:"⚠️ חשוד"})
        anomaly_results(df_r)

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 3 — EDA
# ══════════════════════════════════════════════════════════════════════════════
with tab_eda:
    st.markdown("## 📊 ניתוח נתונים — EDA")
    st.markdown("---")

    if not DATASETS:
        st.warning("לא נמצאו קבצי נתונים")
        st.stop()

    sel_e = st.selectbox("בחרי מערך לניתוח:", [f"מערך {k}" for k in DATASETS.keys()], key="eda")
    df_e  = load_csv(DATASETS[sel_e.split()[-1]])

    if df_e is None:
        st.error("שגיאה בטעינה")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("מספר נקודות",  len(df_e))
    c2.metric("טווח Y",       f"{df_e['Y'].max()-df_e['Y'].min():.1f}")
    c3.metric("טווח X",       f"{df_e['X'].max()-df_e['X'].min():.1f}")
    c4.metric("ערכים חסרים",  int(df_e.isnull().sum().sum()))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### פיזור נקודות")
        fig_sc = px.scatter(df_e, x="Y", y="X", hover_name="שם נקודה",
                            color_discrete_sequence=["#00b4d8"])
        fig_sc.update_traces(marker=dict(size=6))
        fig_sc.update_layout(**PLOT_STYLE, height=360,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
            yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
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
        st.dataframe(df_e[["Y","X"]].describe().round(3), use_container_width=True, height=290)

    st.markdown("### 10 נקודות ראשונות")
    st.dataframe(df_e.head(10).reset_index(drop=True), use_container_width=True, hide_index=True)
    csv_out = df_e.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ הורד CSV", data=csv_out,
                       file_name=f"dataset_{sel_e.split()[-1]}.csv",
                       mime="text/csv", key=ck())

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 4 — ראשי
# ══════════════════════════════════════════════════════════════════════════════
with tab_home:
    st.markdown("## 🏠 סקירת מערכי הנתונים")
    st.markdown("---")

    dfs_all = {}
    cols = st.columns(max(len(DATASETS),1))
    for idx, (fld, path) in enumerate(DATASETS.items()):
        df = load_csv(path)
        dfs_all[fld] = df
        with cols[idx]:
            if df is not None:
                st.metric(f"מערך {fld}", f"{len(df)} נקודות",
                          f"Y:{df['Y'].min():.0f}–{df['Y'].max():.0f}")

    if dfs_all:
        col_b, col_m = st.columns(2)
        with col_b:
            st.markdown("### השוואת גדלים")
            bar_data = [{"מערך": f"מערך {k}", "נקודות": len(v)}
                        for k,v in dfs_all.items() if v is not None]
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
                        marker=dict(size=4, color=COLORS[idx]),
                        text=df["שם נקודה"],
                        hovertemplate="<b>%{text}</b><br>Y:%{x:.1f}<br>X:%{y:.1f}<extra></extra>",
                    ))
            fig_all.update_layout(**PLOT_STYLE, height=300,
                xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
                yaxis=dict(title="X", gridcolor="rgba(0,180,216,0.12)", zeroline=False),
            )
            st.plotly_chart(fig_all, use_container_width=True, key=ck())

# ── תחתית ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#2a3a4a;font-size:0.85rem;
border-top:1px solid rgba(0,180,216,0.15);padding-top:16px">
    📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
