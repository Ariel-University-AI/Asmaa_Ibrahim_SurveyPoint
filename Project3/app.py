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
.section-title {
    color: #00b4d8; font-size: 1.5rem; font-weight: 700;
    border-bottom: 2px solid #00b4d8; padding-bottom: 8px; margin: 16px 0 12px 0;
}
.card {
    background: linear-gradient(135deg, #0d1b2a, #1a2a3a);
    border: 1px solid #00b4d8; border-radius: 14px; padding: 16px; margin: 6px 0;
}
div[data-testid="metric-container"] {
    background: linear-gradient(135deg, #0d1b2a, #162032) !important;
    border: 1px solid #00b4d8 !important; border-radius: 14px !important; padding: 16px !important;
}
[data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 2rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #90e0ef !important; }
.stTabs [data-baseweb="tab-list"] { background: rgba(13,27,42,0.8); border-radius: 10px; padding: 4px; }
.stTabs [data-baseweb="tab"] { color: #90e0ef !important; font-weight: 600; font-size: 1rem; }
.stTabs [aria-selected="true"] { background: rgba(0,180,216,0.2) !important; color: #00b4d8 !important; border-radius: 8px; }
.stDownloadButton button {
    background: linear-gradient(135deg, #FFD700, #FFA500) !important;
    color: #0a0e1a !important; font-weight: 900 !important;
    border-radius: 10px !important; border: none !important; width: 100% !important;
}
</style>
""", unsafe_allow_html=True)

# ── כותרת ─────────────────────────────────────────────────────────────────────
st.markdown("""
<div style="background:linear-gradient(135deg,#0d1b2a,#1a2a3a);border:1px solid #00b4d8;
border-radius:20px;padding:32px;text-align:center;margin-bottom:20px;
box-shadow:0 0 40px rgba(0,180,216,0.25)">
    <div style="font-size:3rem;margin-bottom:8px">📐 🔭 🗺️</div>
    <div class="hero-title">SURVEYPOINT</div>
    <div style="color:#90e0ef;font-size:1.1rem;margin-top:8px;letter-spacing:2px">
        מערכת חכמה לניתוח תיקי חישובים הנדסיים | אוניברסיטת אריאל
    </div>
    <div style="margin-top:14px;display:flex;justify-content:center;gap:14px;flex-wrap:wrap">
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">📍 קואורדינטות ITM</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">🤖 Isolation Forest</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">📊 EDA Dashboard</span>
        <span style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;border-radius:20px;padding:4px 14px;color:#00b4d8">📄 OCR מ-TIF/PDF</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── פונקציות עזר ─────────────────────────────────────────────────────────────

@st.cache_resource
def load_models():
    path = os.path.join(BASE_DIR, "Model", "model.pkl")
    if os.path.exists(path):
        return joblib.load(path)
    return None


def load_csv_file(src, is_bytes=False):
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
COLORS   = ["#00b4d8", "#FFD700", "#00ff88", "#ff6b6b"]

PLOT_STYLE = dict(
    plot_bgcolor="rgba(10,20,35,0.95)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#90e0ef", size=13),
    legend=dict(bgcolor="rgba(13,27,42,0.9)", bordercolor="#00b4d8", borderwidth=1),
    margin=dict(l=60, r=20, t=30, b=60),
)

_chart_counter = [0]

def _chart_key():
    _chart_counter[0] += 1
    return f"chart_{_chart_counter[0]}"


def run_anomaly(df, model):
    df = df.copy()
    df["pred"] = model.predict(df[["Y", "X"]])
    df["סטטוס"] = df["pred"].map({1: "✅ תקין", -1: "⚠️ חשוד"})
    return df


def show_anomaly_results(df_res):
    n_total = len(df_res)
    n_ok  = (df_res["pred"] == 1).sum()
    n_bad = (df_res["pred"] == -1).sum()
    pct   = round(n_ok / n_total * 100, 1)

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
        marker=dict(size=8, color="#00ff88", symbol="circle",
                    line=dict(width=1, color="white")),
        text=df_ok["שם נקודה"],
        hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<extra></extra>",
    ))
    if len(df_bad) > 0:
        fig.add_trace(go.Scatter(
            x=df_bad["Y"], y=df_bad["X"], mode="markers", name="⚠️ חשוד",
            marker=dict(size=12, color="#ff4444", symbol="x",
                        line=dict(width=2, color="white")),
            text=df_bad["שם נקודה"],
            hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<br>⚠️ חשוד!<extra></extra>",
        ))
    fig.update_layout(**PLOT_STYLE, height=460,
        xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
        yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
    )
    st.plotly_chart(fig, use_container_width=True, key=_chart_key())

    with st.expander("📋 טבלה מלאה", expanded=False):
        st.dataframe(df_res.drop(columns=["pred"]), use_container_width=True, height=300,
            column_config={
                "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
            })

    if n_bad > 0:
        st.markdown('<div class="section-title">⚠️ נקודות חשודות לבדיקה</div>',
                    unsafe_allow_html=True)
        st.dataframe(
            df_bad[["שם נקודה", "Y", "X", "סטטוס"]].reset_index(drop=True),
            use_container_width=True,
            column_config={
                "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
            }
        )

    out = io.BytesIO()
    df_res.drop(columns=["pred"]).to_excel(out, index=False)
    st.download_button(
        "⬇️ הורד Excel — קואורדינטות + ניתוח חריגים",
        data=out.getvalue(), file_name="SurveyPoint_analysis.xlsx",
        mime="application/vnd.ms-excel", key=_chart_key(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# לשוניות
# ══════════════════════════════════════════════════════════════════════════════

tab_ocr, tab_detect, tab_eda, tab_home = st.tabs([
    "📄 שלב 1 — חילוץ מ-TIF/PDF",
    "🤖 שלב 2 — זיהוי חריגים",
    "📊 שלב 3 — EDA",
    "🏠 ראשי",
])

# ──────────────────────────────────────────────────────────────────────────────
# לשונית 1 — ראשי
# ──────────────────────────────────────────────────────────────────────────────
with tab_home:
    st.markdown('<div class="section-title">📋 סקירת מערכי הנתונים</div>',
                unsafe_allow_html=True)

    dfs_all = {}
    cols = st.columns(max(len(DATASETS), 1))
    for idx, (fld, path) in enumerate(DATASETS.items()):
        df = load_csv_file(path)
        dfs_all[fld] = df
        with cols[idx]:
            if df is not None:
                st.metric(f"מערך {fld}", f"{len(df)} נקודות",
                          f"Y: {df['Y'].min():.0f}–{df['Y'].max():.0f}")
            else:
                st.metric(f"מערך {fld}", "—")

    if dfs_all:
        bar_data = [{"מערך": f"מערך {k}", "נקודות": len(v)}
                    for k, v in dfs_all.items() if v is not None]
        if bar_data:
            col_b, col_m = st.columns(2)
            with col_b:
                st.markdown('<div class="section-title">📊 השוואת גדלים</div>',
                            unsafe_allow_html=True)
                fig_bar = px.bar(pd.DataFrame(bar_data), x="מערך", y="נקודות",
                                 color="מערך", color_discrete_sequence=COLORS)
                fig_bar.update_layout(**PLOT_STYLE, height=300, showlegend=False)
                st.plotly_chart(fig_bar, use_container_width=True, key=_chart_key())

            with col_m:
                st.markdown('<div class="section-title">🗺️ כל הנקודות</div>',
                            unsafe_allow_html=True)
                fig_all = go.Figure()
                for idx, (fld, df) in enumerate(dfs_all.items()):
                    if df is not None:
                        fig_all.add_trace(go.Scatter(
                            x=df["Y"], y=df["X"], mode="markers",
                            name=f"מערך {fld}",
                            marker=dict(size=4, color=COLORS[idx]),
                            text=df["שם נקודה"],
                            hovertemplate="<b>%{text}</b><br>Y:%{x:.1f}<br>X:%{y:.1f}<extra></extra>",
                        ))
                fig_all.update_layout(**PLOT_STYLE, height=300,
                    xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                    yaxis=dict(title="X", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                )
                st.plotly_chart(fig_all, use_container_width=True, key=_chart_key())

    # סיכום
    st.markdown('<div class="section-title">ℹ️ אודות SurveyPoint</div>',
                unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
    <b style="color:#FFD700">SurveyPoint</b> <span style="color:#90e0ef">היא מערכת לניתוח תיקי חישובים הנדסיים.</span><br><br>
    <b style="color:#00b4d8">🔹 לשונית זיהוי חריגים</b> <span style="color:#90e0ef">— טעינת קובץ קואורדינטות, זיהוי נקודות חשודות ע״י Isolation Forest, ייצוא Excel</span><br>
    <b style="color:#00b4d8">🔹 לשונית EDA</b> <span style="color:#90e0ef">— ניתוח סטטיסטי, היסטוגרמות, סטטיסטיקה תיאורית</span><br>
    <b style="color:#00b4d8">🔹 לשונית חילוץ OCR</b> <span style="color:#90e0ef">— העלאת TIF/PDF וחילוץ קואורדינטות אוטומטי</span>
    </div>
    """, unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────────────────────
# לשונית 2 — זיהוי חריגים
# ──────────────────────────────────────────────────────────────────────────────
with tab_detect:
    st.markdown('<div class="section-title">🔍 ניתוח וזיהוי נקודות חשודות</div>',
                unsafe_allow_html=True)

    if models is None:
        st.error("❌ מודל לא נמצא — הריצי את trainmodel.py")
        st.stop()

    # הודעה אם יש נתונים מחולצים
    has_ocr = "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None
    if has_ocr:
        n_ocr = len(st.session_state["ocr_df"])
        st.success(f"✅ נמצאו נתונים מחולצים מ-TIF — **{n_ocr} נקודות** מוכנות לניתוח!")
    else:
        st.info("💡 חלצי קואורדינטות מ-TIF בשלב 1 — הן יופיעו כאן אוטומטית")

    # מקור נתונים
    source_opts = ["מערך נתונים קיים", "העלאת קובץ CSV"]
    if has_ocr:
        source_opts.insert(0, "נתונים שחולצו מ-TIF ✅")

    col_src, col_mod = st.columns(2)
    with col_src:
        source = st.radio("מקור נתונים:", source_opts, horizontal=True, key="det_src")
    with col_mod:
        mk = st.selectbox("מודל לשימוש:", [f"מערך {k}" for k in models.keys()], key="det_model")
        fk = mk.split()[-1]

    df_input = None

    if source == "נתונים שחולצו מ-TIF ✅":
        df_input = st.session_state["ocr_df"]
        st.info(f"נטענו {len(df_input)} נקודות מחילוץ OCR")

    elif source == "מערך נתונים קיים":
        if DATASETS:
            sel = st.selectbox("בחר מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="det_sel")
            df_input = load_csv_file(DATASETS[sel.split()[-1]])
        else:
            st.warning("לא נמצאו קבצי נתונים")

    else:
        up = st.file_uploader("העלה קובץ CSV (שם נקודה, Y, X):",
                               type=["csv", "CSV"], key="det_csv")
        if up:
            df_input = load_csv_file(up.read(), is_bytes=True)

    if df_input is not None and len(df_input) > 0:
        st.success(f"✅ נטענו **{len(df_input)}** נקודות")
        df_res = run_anomaly(df_input, models[fk])
        show_anomaly_results(df_res)
    elif df_input is not None:
        st.warning("הקובץ ריק או לא בפורמט הנכון")

# ──────────────────────────────────────────────────────────────────────────────
# לשונית 3 — EDA
# ──────────────────────────────────────────────────────────────────────────────
with tab_eda:
    st.markdown('<div class="section-title">📊 ניתוח נתונים מקיף</div>',
                unsafe_allow_html=True)

    if not DATASETS:
        st.warning("לא נמצאו קבצי נתונים")
        st.stop()

    sel_e = st.selectbox("בחר מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="eda_sel")
    fe    = sel_e.split()[-1]
    df_e  = load_csv_file(DATASETS[fe])

    if df_e is None:
        st.error("שגיאה בטעינה")
        st.stop()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("נקודות",     len(df_e))
    c2.metric("טווח Y",     f"{df_e['Y'].max()-df_e['Y'].min():.1f} מ׳")
    c3.metric("טווח X",     f"{df_e['X'].max()-df_e['X'].min():.1f} מ׳")
    c4.metric("ערכים חסרים", int(df_e.isnull().sum().sum()))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-title">פיזור נקודות</div>', unsafe_allow_html=True)
        fig_sc = px.scatter(df_e, x="Y", y="X", hover_name="שם נקודה",
                            color_discrete_sequence=["#00b4d8"])
        fig_sc.update_traces(marker=dict(size=6 if len(df_e) > 80 else 9))
        fig_sc.update_layout(**PLOT_STYLE, height=350,
            xaxis=dict(title="Y (צפון)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
            yaxis=dict(title="X (מזרח)", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
        )
        st.plotly_chart(fig_sc, use_container_width=True, key=_chart_key())

    with col2:
        st.markdown('<div class="section-title">התפלגות Y</div>', unsafe_allow_html=True)
        fig_hy = px.histogram(df_e, x="Y", nbins=25, color_discrete_sequence=["#FFD700"])
        fig_hy.update_layout(**PLOT_STYLE, height=350,
            xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.15)"),
            yaxis=dict(title="תדירות", gridcolor="rgba(0,180,216,0.15)"),
        )
        st.plotly_chart(fig_hy, use_container_width=True, key=_chart_key())

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">התפלגות X</div>', unsafe_allow_html=True)
        fig_hx = px.histogram(df_e, x="X", nbins=25, color_discrete_sequence=["#00ff88"])
        fig_hx.update_layout(**PLOT_STYLE, height=300,
            xaxis=dict(title="X", gridcolor="rgba(0,180,216,0.15)"),
            yaxis=dict(title="תדירות", gridcolor="rgba(0,180,216,0.15)"),
        )
        st.plotly_chart(fig_hx, use_container_width=True, key=_chart_key())
    with col4:
        st.markdown('<div class="section-title">סטטיסטיקה תיאורית</div>', unsafe_allow_html=True)
        st.dataframe(df_e[["Y", "X"]].describe().round(3),
                     use_container_width=True, height=280)

    st.markdown('<div class="section-title">10 נקודות ראשונות</div>', unsafe_allow_html=True)
    st.dataframe(df_e.head(10).reset_index(drop=True), use_container_width=True,
                 hide_index=True,
                 column_config={
                     "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                     "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                 })

    csv_out = df_e.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ הורד CSV", data=csv_out,
                       file_name=f"coordinates_{fe}.csv", mime="text/csv",
                       key=_chart_key())

# ──────────────────────────────────────────────────────────────────────────────
# לשונית 4 — חילוץ OCR מ-TIF/PDF
# ──────────────────────────────────────────────────────────────────────────────
with tab_ocr:
    st.markdown('<div class="section-title">📄 חילוץ קואורדינטות מתיק חישובים</div>',
                unsafe_allow_html=True)

    # ── Gemini API Key ──────────────────────────────────────────────────────
    st.markdown('<div class="section-title">🤖 מפתח Gemini AI (לחילוץ מלא)</div>',
                unsafe_allow_html=True)

    col_key, col_info = st.columns([3, 2])
    with col_key:
        gemini_key = st.text_input(
            "הכניסי את ה-Gemini API Key שלך:",
            type="password",
            placeholder="AIzaSy...",
            key="gemini_key",
        )
    with col_info:
        if gemini_key:
            # בדיקת חיבור
            if st.button("🔗 בדוק חיבור", key="test_gemini"):
                try:
                    from google import genai as _genai
                    import requests as _req
                    _url = (f"https://generativelanguage.googleapis.com"
                            f"/v1beta/models/gemini-1.5-flash:generateContent"
                            f"?key={gemini_key}")
                    _res = _req.post(_url, json={"contents": [{"parts":
                           [{"text": "Say OK"}]}]}, timeout=15)
                    _res.raise_for_status()
                    _r = type('R', (), {'text': _res.json()
                           ['candidates'][0]['content']['parts'][0]['text']})()
                    st.success(f"✅ Gemini מחובר! תשובה: {_r.text.strip()[:20]}")
                except Exception as _e:
                    st.error(f"❌ שגיאה: {_e}")
            else:
                st.success("✅ Gemini מוכן — יחלץ **את כל הנקודות**!")
        else:
            st.markdown("""
            <div class="card" style="font-size:0.9rem">
            <b style="color:#FFD700">ללא Key:</b> <span style="color:#90e0ef">Tesseract (~15% נקודות)</span><br>
            <b style="color:#00ff88">עם Key:</b> <span style="color:#90e0ef">Gemini (~99% נקודות) ✨</span>
            </div>
            """, unsafe_allow_html=True)

    st.divider()

    # ── קבצים ──────────────────────────────────────────────────────────────
    # העלאת TIF — תמיד. CSV — רק בלי Gemini
    if gemini_key:
        uploaded = st.file_uploader(
            "📄 קובץ TIF או PDF (תיק חישובים)",
            type=["tif", "TIF", "tiff", "TIFF", "pdf", "PDF"],
            key="ocr_upload",
        )
        ref_csv = None
    else:
        col_tif, col_csv = st.columns(2)
        with col_tif:
            uploaded = st.file_uploader(
                "📄 קובץ TIF או PDF (תיק חישובים)",
                type=["tif", "TIF", "tiff", "TIFF", "pdf", "PDF"],
                key="ocr_upload",
            )
        with col_csv:
            ref_csv = st.file_uploader(
                "📊 קובץ CSV לאימות (אופציונלי)",
                type=["csv", "CSV"],
                key="ref_csv",
            )

    if uploaded is not None:
        file_bytes = uploaded.read()
        fname = uploaded.name.lower()

        # ספור עמודים
        total_pages = 1
        if not fname.endswith(".pdf"):
            try:
                from PIL import Image as _PIL
                _img = _PIL.open(io.BytesIO(file_bytes))
                total_pages = getattr(_img, 'n_frames', 1)
            except Exception:
                total_pages = 1

        st.info(f"📂 **{uploaded.name}** | {len(file_bytes)//1024} KB"
                + (f" | **{total_pages} עמודים**" if total_pages > 1 else ""))

        # בוחר עמודים — רק בלי Gemini
        max_pages = total_pages
        if total_pages > 1 and not gemini_key:
            col_sl, col_est = st.columns([3, 2])
            with col_sl:
                max_pages = st.slider("כמה עמודים לעבד?",
                                      min_value=1, max_value=total_pages,
                                      value=total_pages, key="ocr_pages")
            with col_est:
                est = round(max_pages * 2.5 / 60, 1)
                st.markdown(f"""
                <div style="background:rgba(0,180,216,0.1);border:1px solid #00b4d8;
                border-radius:10px;padding:12px;text-align:center;margin-top:8px">
                <div style="color:#FFD700;font-size:1.5rem;font-weight:700">{max_pages} עמודים</div>
                <div style="color:#90e0ef">~{est} דקות</div>
                </div>""", unsafe_allow_html=True)

        # טען CSV לימוד אם הועלה
        ref_df = None
        if ref_csv is not None:
            ref_df = load_csv_file(ref_csv.read(), is_bytes=True)
            if ref_df is not None:
                st.success(f"📊 CSV לימוד נטען: **{len(ref_df)} נקודות** — מצב דיוק גבוה מופעל!")
            else:
                st.warning("לא ניתן לקרוא את קובץ ה-CSV")

        if st.button("🚀 התחל חילוץ קואורדינטות", type="primary", key="ocr_btn"):
            try:
                from extractor import extract_from_tif, extract_from_pdf
            except ImportError as e:
                st.error(f"שגיאת טעינה: {e}")
                st.stop()

            prog = st.progress(0)
            stat = st.empty()

            def cb(done, total):
                prog.progress(int(done / total * 100))
                stat.text(f"מעבד עמוד {done} מתוך {total}...")

            # בחירת מנוע
            if gemini_key:
                est_min = round(total_pages * 4 / 60, 1)
                st.success(f"✨ Gemini Vision — ~{est_min} דקות לכל {total_pages} עמודים")
                mode = "✨ Gemini Vision AI"
            else:
                use_combined = st.checkbox(
                    "🔀 מצב משולב — Tesseract + EasyOCR",
                    value=False, key="combined_mode"
                )
                mode = "🔀 Tesseract + EasyOCR" if use_combined else "🔍 Tesseract בלבד"
                est_min = round(max_pages * (62 if use_combined else 2.5) / 60, 1)
                st.info(f"⏱️ ~{est_min} דקות")

            with st.spinner(f"מריץ חילוץ — {mode}..."):
                try:
                    if fname.endswith(".pdf"):
                        df_ocr = extract_from_pdf(file_bytes)
                    elif gemini_key:
                        from extractor import extract_with_gemini
                        df_ocr = extract_with_gemini(
                            file_bytes,
                            api_key=gemini_key,
                            progress_cb=cb,
                        )
                    else:
                        df_ocr = extract_from_tif(
                            file_bytes,
                            progress_cb=cb,
                            max_pages=max_pages,
                            reference_df=ref_df,
                            use_combined=use_combined,
                        )
                    prog.progress(100)
                    stat.empty()
                except Exception as e:
                    st.error(f"שגיאה בחילוץ: {e}")
                    df_ocr = pd.DataFrame(columns=["שם נקודה", "Y", "X"])

            # שמור רק עמודות ליבה לזיהוי חריגים
            core_cols = ["שם נקודה", "Y", "X"]
            ocr_core = df_ocr[core_cols] if all(c in df_ocr.columns for c in core_cols) else df_ocr
            st.session_state["ocr_df"] = ocr_core if len(ocr_core) > 0 else None

            if len(df_ocr) == 0:
                st.warning("לא נמצאו קואורדינטות.")
            else:
                # הצג מדדים
                n_total = len(df_ocr)
                has_src = "מקור" in df_ocr.columns
                n_ocr = (df_ocr["מקור"] == "OCR ✓").sum() if has_src else n_total
                n_csv = (df_ocr["מקור"] != "OCR ✓").sum() if has_src else 0

                if has_src:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("📍 סה״כ נקודות", n_total)
                    c2.metric("✅ נמצאו ב-OCR", n_ocr)
                    c3.metric("📋 הושלמו מ-CSV", n_csv)
                else:
                    st.success(f"✅ חולצו **{n_total}** נקודות!")

                # גרף וטבלה
                col_t, col_p = st.columns([1, 2])
                with col_t:
                    display_cols = {
                        "Y": st.column_config.NumberColumn("Y (צפון)", format="%.3f"),
                        "X": st.column_config.NumberColumn("X (מזרח)", format="%.3f"),
                    }
                    if has_src:
                        display_cols["מקור"] = st.column_config.TextColumn("מקור")
                    st.dataframe(df_ocr, use_container_width=True, height=340,
                                 column_config=display_cols)
                with col_p:
                    color_col = "מקור" if has_src else None
                    fig_o = px.scatter(
                        df_ocr, x="Y", y="X", hover_name="שם נקודה",
                        color=color_col,
                        color_discrete_map={"OCR ✓": "#00ff88",
                                            "CSV (לא נמצא ב-OCR)": "#FFD700"},
                        color_discrete_sequence=["#00b4d8"],
                    )
                    fig_o.update_traces(marker=dict(size=7))
                    fig_o.update_layout(**PLOT_STYLE, height=340,
                        xaxis=dict(title="Y", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                        yaxis=dict(title="X", gridcolor="rgba(0,180,216,0.15)", zeroline=False),
                    )
                    st.plotly_chart(fig_o, use_container_width=True, key=_chart_key())

                # הורדות
                csv_ocr = df_ocr.to_csv(index=False).encode("utf-8-sig")
                col_c, col_e = st.columns(2)
                with col_c:
                    st.download_button("⬇️ הורד CSV", data=csv_ocr,
                                       file_name="coordinates_extracted.csv",
                                       mime="text/csv", key=_chart_key())
                with col_e:
                    xls = io.BytesIO()
                    df_ocr.to_excel(xls, index=False)
                    st.download_button("⬇️ הורד Excel", data=xls.getvalue(),
                                       file_name="coordinates_extracted.xlsx",
                                       mime="application/vnd.ms-excel", key=_chart_key())

                # זיהוי חריגים על הנתונים שחולצו
                if models and len(df_ocr) >= 5:
                    st.markdown('<div class="section-title">🤖 זיהוי חריגים על הנתונים שחולצו</div>',
                                unsafe_allow_html=True)
                    mk2 = st.selectbox("מודל:", [f"מערך {k}" for k in models.keys()],
                                       key="ocr_model")
                    df_ocr_res = run_anomaly(df_ocr, models[mk2.split()[-1]])
                    show_anomaly_results(df_ocr_res)

    elif "ocr_df" in st.session_state and st.session_state.get("ocr_df") is not None:
        st.info(f"נתונים קיימים: {len(st.session_state['ocr_df'])} נקודות — עברי ללשונית זיהוי חריגים")


# ── תחתית ────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center;color:#444;font-size:0.85rem;
border-top:1px solid #1a2a3a;padding-top:14px">
📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
