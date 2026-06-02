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

st.set_page_config(page_title="SurveyPoint", page_icon="📐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700;900&family=Rajdhani:wght@400;600;700&display=swap');
* { font-family: 'Rajdhani', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 100%); }
.hero-title {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 3rem !important; font-weight: 900 !important;
    background: linear-gradient(90deg, #00b4d8, #90e0ef, #FFD700);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.section-title { color: #00b4d8; font-size: 1.6rem; font-weight: 700; border-bottom: 2px solid #00b4d8; padding-bottom: 8px; margin: 18px 0 12px 0; }
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1b2a, #162032) !important;
    border: 1px solid #00b4d8 !important; border-radius: 14px !important; padding: 16px !important;
}
[data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 2.2rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #90e0ef !important; }
.stTabs [data-baseweb="tab-list"] { background: rgba(13,27,42,0.8); border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #90e0ef !important; font-weight: 600; font-size: 1rem; }
.stTabs [aria-selected="true"] { background: rgba(0,180,216,0.2) !important; color: #00b4d8 !important; border-radius: 8px; }
.stDownloadButton button {
    background: linear-gradient(135deg, #FFD700, #FFA500) !important;
    color: #0a0e1a !important; font-weight: 900 !important;
    border-radius: 10px !important; border: none !important; width: 100% !important;
}
.step-box {
    background: linear-gradient(135deg, #0d1b2a, #1a2a3a);
    border: 1px solid #00b4d8; border-radius: 12px;
    padding: 14px 18px; margin: 6px 0; color: #90e0ef;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="background:linear-gradient(135deg,#0d1b2a,#1a2a3a);border:1px solid #00b4d8;border-radius:20px;padding:36px;text-align:center;margin-bottom:24px;box-shadow:0 0 40px rgba(0,180,216,0.3)">
    <div style="font-size:3.2rem;margin-bottom:8px">📐 🔭 🗺️</div>
    <div class="hero-title">SURVEYPOINT</div>
    <div style="color:#90e0ef;font-size:1.2rem;margin-top:8px;letter-spacing:2px">מערכת חכמה לניתוח תיקי חישובים הנדסיים</div>
    <div style="margin-top:16px;display:flex;justify-content:center;gap:16px;flex-wrap:wrap">
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">📄 TIF / PDF</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">🔍 EasyOCR</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">🤖 Isolation Forest</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">📁 ייצוא CSV / Excel</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ── טעינת מודלים ────────────────────────────────────────────────────────────

@st.cache_resource
def load_models():
    path = os.path.join(BASE_DIR, "Model", "model.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_csv_file(path_or_bytes, is_bytes=False):
    for enc in ["utf-8-sig", "cp1255", "utf-8", "latin-1"]:
        try:
            src = io.BytesIO(path_or_bytes) if is_bytes else path_or_bytes
            df = pd.read_csv(src, encoding=enc)
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
        folder_path = os.path.join(ROOT_DIR, "DATA", i)
        for ext in [".CSV", ".csv"]:
            p = os.path.join(folder_path, f"coordinates_{i}{ext}")
            if os.path.exists(p):
                result[i] = p
                break
        if i not in result:
            files = glob.glob(os.path.join(folder_path, "*.csv")) + \
                    glob.glob(os.path.join(folder_path, "*.CSV"))
            if files:
                result[i] = files[0]
    return result


DATASETS = get_datasets()
models = load_models()

PLOT_STYLE = dict(
    plot_bgcolor="rgba(10,20,35,0.95)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#90e0ef", size=13),
    legend=dict(bgcolor="rgba(13,27,42,0.9)", bordercolor="#00b4d8", borderwidth=1),
    margin=dict(l=60, r=20, t=30, b=60),
)

COLORS = ["#00b4d8", "#FFD700", "#00ff88", "#ff6b6b"]


def run_anomaly(df, model):
    """מריץ זיהוי חריגים ומחזיר DataFrame עם עמודת סטטוס"""
    df = df.copy()
    df["pred"] = model.predict(df[["Y", "X"]])
    df["סטטוס"] = df["pred"].map({1: "✅ תקין", -1: "⚠️ חשוד"})
    return df


def show_results(df_res):
    """מציג מטריקות, גרף וטבלה לאחר זיהוי חריגים"""
    n_total = len(df_res)
    n_ok    = (df_res["pred"] == 1).sum()
    n_bad   = (df_res["pred"] == -1).sum()
    pct     = round(n_ok / n_total * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📍 סה״כ נקודות",  n_total)
    c2.metric("✅ נקודות תקינות", n_ok)
    c3.metric("⚠️ נקודות חשודות", n_bad)
    c4.metric("🎯 אחוז תקינות",  f"{pct}%")

    df_ok  = df_res[df_res["pred"] == 1]
    df_bad = df_res[df_res["pred"] == -1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_ok["Y"], y=df_ok["X"], mode="markers", name="✅ תקין",
        marker=dict(size=9, color="#00ff88", symbol="circle", line=dict(width=1, color="white")),
        text=df_ok["שם נקודה"],
        hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<extra></extra>",
    ))
    if len(df_bad) > 0:
        fig.add_trace(go.Scatter(
            x=df_bad["Y"], y=df_bad["X"], mode="markers", name="⚠️ חשוד",
            marker=dict(size=13, color="#ff4444", symbol="x", line=dict(width=2, color="white")),
            text=df_bad["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<br>⚠️ חשוד!<extra></extra>",
        ))
    fig.update_layout(**PLOT_STYLE, height=460,
        xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
        yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 טבלה מלאה", expanded=False):
        st.dataframe(df_res.drop(columns=["pred"]), use_container_width=True, height=300,
            column_config={
                "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
            })

    if n_bad > 0:
        st.markdown('<div class="section-title">⚠️ נקודות חשודות</div>', unsafe_allow_html=True)
        st.dataframe(df_bad[["שם נקודה","Y","X","סטטוס"]].reset_index(drop=True),
                     use_container_width=True)

    out = io.BytesIO()
    df_res.drop(columns=["pred"]).to_excel(out, index=False)
    st.download_button("⬇️ הורד Excel", data=out.getvalue(),
                       file_name="SurveyPoint_analysis.xlsx",
                       mime="application/vnd.ms-excel")


# ── לשוניות ────────────────────────────────────────────────────────────────

tab_extract, tab_detect, tab_eda, tab_home = st.tabs([
    "📄 חילוץ מ-TIF/PDF",
    "🤖 זיהוי חריגים",
    "📊 EDA",
    "🏠 ראשי",
])


# ══════════════════════════════════════════════════════════════════════════════
# לשונית 1 — חילוץ קואורדינטות מ-TIF/PDF
# ══════════════════════════════════════════════════════════════════════════════

with tab_extract:
    st.markdown('<div class="section-title">📄 חילוץ קואורדינטות מתיק חישובים</div>',
                unsafe_allow_html=True)

    col_inst, col_up = st.columns([2, 3])

    with col_inst:
        st.markdown("""
        <div class="step-box">🔹 <b>שלב 1:</b> העלה קובץ TIF או PDF</div>
        <div class="step-box">🔹 <b>שלב 2:</b> המערכת מריצה OCR על כל העמודים</div>
        <div class="step-box">🔹 <b>שלב 3:</b> קואורדינטות מחולצות אוטומטית</div>
        <div class="step-box">🔹 <b>שלב 4:</b> מזהה חריגים במידת הצורך</div>
        <div class="step-box">🔹 <b>שלב 5:</b> הורד CSV / Excel מסודר</div>
        <br>
        <div style="color:#FFD700; font-size:0.9rem; padding: 8px;">
        ⚠️ OCR מתאים לתיקי חישובים מודפסים/סרוקים.<br>
        כתב יד עשוי לדרוש בדיקה ידנית.
        </div>
        """, unsafe_allow_html=True)

    with col_up:
        uploaded = st.file_uploader(
            "גרור קובץ TIF או PDF של תיק חישובים",
            type=["tif", "TIF", "tiff", "TIFF", "pdf", "PDF"],
            key="tif_upload"
        )

    if uploaded is not None:
        file_bytes = uploaded.read()
        fname = uploaded.name.lower()

        st.info(f"📂 קובץ: **{uploaded.name}** | גודל: {len(file_bytes)//1024} KB")

        if st.button("🚀 התחל חילוץ קואורדינטות", type="primary"):
            from extractor import extract_from_tif, extract_from_pdf

            progress_bar = st.progress(0)
            status_text  = st.empty()

            def update_progress(done, total):
                pct = int(done / total * 100)
                progress_bar.progress(pct)
                status_text.text(f"מעבד עמוד {done} מתוך {total}...")

            with st.spinner("מריץ OCR — עשוי לקחת כמה דקות..."):
                try:
                    if fname.endswith(".pdf"):
                        df_extracted = extract_from_pdf(file_bytes)
                    else:
                        df_extracted = extract_from_tif(file_bytes, progress_cb=update_progress)

                    progress_bar.progress(100)
                    status_text.empty()
                except Exception as e:
                    st.error(f"שגיאה בחילוץ: {e}")
                    df_extracted = pd.DataFrame(columns=["שם נקודה","Y","X"])

            if len(df_extracted) == 0:
                st.warning("לא נמצאו קואורדינטות. ייתכן שהתמונה אינה ברת-OCR.")
            else:
                st.success(f"✅ חולצו **{len(df_extracted)}** נקודות!")
                st.session_state["extracted_df"] = df_extracted

                # תצוגה ראשונית
                col_t, col_p = st.columns([1, 2])
                with col_t:
                    st.dataframe(df_extracted, use_container_width=True, height=300,
                        column_config={
                            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                        })
                with col_p:
                    fig = px.scatter(df_extracted, x="Y", y="X",
                                     hover_name="שם נקודה",
                                     color_discrete_sequence=["#00b4d8"])
                    fig.update_traces(marker=dict(size=8))
                    fig.update_layout(**PLOT_STYLE, height=300,
                        xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                        yaxis=dict(title="X", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                    )
                    st.plotly_chart(fig, use_container_width=True)

                # ייצוא CSV
                csv_out = df_extracted.to_csv(index=False).encode("utf-8-sig")
                st.download_button("⬇️ הורד CSV", data=csv_out,
                                   file_name="coordinates_extracted.csv",
                                   mime="text/csv")

                # זיהוי חריגים על הנתונים שחולצו
                if models and len(df_extracted) >= 5:
                    st.markdown('<div class="section-title">🤖 זיהוי חריגים על הנתונים שחולצו</div>',
                                unsafe_allow_html=True)
                    model_key = st.selectbox(
                        "בחר מודל:",
                        [f"מערך {k}" for k in models.keys()],
                        key="ext_model"
                    )
                    fk = model_key.split()[-1]
                    df_res = run_anomaly(df_extracted, models[fk])
                    show_results(df_res)

    elif "extracted_df" in st.session_state:
        st.info("נתונים קיימים מחילוץ קודם זמינים בלשוניית זיהוי חריגים.")


# ══════════════════════════════════════════════════════════════════════════════
# לשונית 2 — זיהוי חריגים
# ══════════════════════════════════════════════════════════════════════════════

with tab_detect:
    st.markdown('<div class="section-title">🔍 ניתוח וזיהוי חריגים</div>', unsafe_allow_html=True)

    if models is None:
        st.error("❌ מודל לא נמצא — יש להריץ את trainmodel.py תחילה")
        st.stop()

    source_options = ["מערך נתונים קיים", "העלאת קובץ CSV"]
    if "extracted_df" in st.session_state:
        source_options.insert(0, "נתונים מחולצים (TIF/PDF)")

    col_src, col_model = st.columns(2)
    with col_src:
        source = st.radio("מקור נתונים:", source_options, horizontal=True)
    with col_model:
        model_key = st.selectbox("מודל:", [f"מערך {k}" for k in models.keys()])
        folder_key = model_key.split()[-1]

    df_input = None

    if source == "נתונים מחולצים (TIF/PDF)":
        df_input = st.session_state["extracted_df"]
        st.info(f"נטענו {len(df_input)} נקודות שחולצו מהתיק")

    elif source == "מערך נתונים קיים":
        if DATASETS:
            sel = st.selectbox("בחר מערך:", [f"מערך {k}" for k in DATASETS.keys()])
            df_input = load_csv_file(DATASETS[sel.split()[-1]])
        else:
            st.warning("לא נמצאו קבצי CSV")

    else:
        up_csv = st.file_uploader("העלה קובץ CSV", type=["csv","CSV"], key="det_csv")
        if up_csv:
            df_input = load_csv_file(up_csv.read(), is_bytes=True)

    if df_input is not None and len(df_input) > 0:
        st.success(f"✅ נטענו {len(df_input)} נקודות")
        df_res = run_anomaly(df_input, models[folder_key])
        show_results(df_res)


# ══════════════════════════════════════════════════════════════════════════════
# לשונית 3 — EDA
# ══════════════════════════════════════════════════════════════════════════════

with tab_eda:
    st.markdown('<div class="section-title">📊 ניתוח נתונים מקיף (EDA)</div>', unsafe_allow_html=True)

    eda_sources = list(DATASETS.keys())
    if not eda_sources:
        st.warning("לא נמצאו קבצי נתונים")
        st.stop()

    sel_eda = st.selectbox("בחר מערך נתונים:", [f"מערך {k}" for k in eda_sources], key="eda")
    folder_eda = sel_eda.split()[-1]
    df_eda = load_csv_file(DATASETS[folder_eda])

    if df_eda is None:
        st.error("שגיאה בטעינת הנתונים")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("מספר נקודות", len(df_eda))
    c2.metric("טווח Y", f"{df_eda['Y'].max()-df_eda['Y'].min():.1f} מ׳")
    c3.metric("טווח X", f"{df_eda['X'].max()-df_eda['X'].min():.1f} מ׳")
    c4.metric("ערכים חסרים", int(df_eda.isnull().sum().sum()))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">פיזור נקודות</div>', unsafe_allow_html=True)
        fig_sc = px.scatter(df_eda, x="Y", y="X", hover_name="שם נקודה",
                            color_discrete_sequence=["#00b4d8"])
        fig_sc.update_traces(marker=dict(size=6 if len(df_eda) > 80 else 9))
        fig_sc.update_layout(**PLOT_STYLE, height=360,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
            yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
        )
        st.plotly_chart(fig_sc, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">התפלגות Y</div>', unsafe_allow_html=True)
        fig_hy = px.histogram(df_eda, x="Y", nbins=30, color_discrete_sequence=["#FFD700"])
        fig_hy.update_layout(**PLOT_STYLE, height=360,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)"),
            yaxis=dict(title="תדירות",   gridcolor="rgba(0,180,216,0.15)"),
        )
        st.plotly_chart(fig_hy, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">התפלגות X</div>', unsafe_allow_html=True)
        fig_hx = px.histogram(df_eda, x="X", nbins=30, color_discrete_sequence=["#00ff88"])
        fig_hx.update_layout(**PLOT_STYLE, height=300,
            xaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)"),
            yaxis=dict(title="תדירות",   gridcolor="rgba(0,180,216,0.15)"),
        )
        st.plotly_chart(fig_hx, use_container_width=True)
    with col4:
        st.markdown('<div class="section-title">סטטיסטיקה תיאורית</div>', unsafe_allow_html=True)
        st.dataframe(df_eda[["Y","X"]].describe().round(2), use_container_width=True, height=290)

    st.markdown('<div class="section-title">10 נקודות ראשונות</div>', unsafe_allow_html=True)
    st.dataframe(df_eda.head(10).reset_index(drop=True), use_container_width=True, hide_index=True,
        column_config={
            "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
            "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
        })

    csv_out = df_eda.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ הורד CSV", data=csv_out,
                       file_name=f"coordinates_{folder_eda}_clean.csv", mime="text/csv")


# ══════════════════════════════════════════════════════════════════════════════
# לשונית 4 — ראשי (סקירה כללית)
# ══════════════════════════════════════════════════════════════════════════════

with tab_home:
    st.markdown('<div class="section-title">📋 סקירת מערכי הנתונים</div>', unsafe_allow_html=True)

    dfs_all = {}
    cols = st.columns(len(DATASETS)) if DATASETS else []
    for idx, (folder, path) in enumerate(DATASETS.items()):
        df = load_csv_file(path)
        dfs_all[folder] = df
        with cols[idx]:
            if df is not None:
                st.metric(f"מערך {folder}", f"{len(df)} נקודות")
            else:
                st.metric(f"מערך {folder}", "—")

    if dfs_all:
        bar_data = [{"מערך": f"מערך {k}", "נקודות": len(v)}
                    for k, v in dfs_all.items() if v is not None]
        if bar_data:
            fig_bar = px.bar(pd.DataFrame(bar_data), x="מערך", y="נקודות",
                             color="מערך", color_discrete_sequence=COLORS)
            fig_bar.update_layout(**PLOT_STYLE, height=300, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        fig_all = go.Figure()
        for idx, (folder, df) in enumerate(dfs_all.items()):
            if df is not None:
                fig_all.add_trace(go.Scatter(
                    x=df["Y"], y=df["X"], mode="markers", name=f"מערך {folder}",
                    marker=dict(size=5, color=COLORS[idx]),
                    text=df["שם נקודה"],
                    hovertemplate="<b>%{text}</b><br>Y: %{x:.2f}<br>X: %{y:.2f}<extra></extra>",
                ))
        fig_all.update_layout(**PLOT_STYLE, height=460,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
            yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
        )
        st.plotly_chart(fig_all, use_container_width=True)


st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#444;font-size:0.85rem;border-top:1px solid #1a2a3a;padding-top:16px">
    📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
