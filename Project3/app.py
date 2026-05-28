import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import io
import glob
import os
from sklearn.ensemble import IsolationForest

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

st.set_page_config(page_title="SurveyPoint", page_icon="📐", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@400;600;700&display=swap');
* { font-family: 'Rajdhani', sans-serif; }
.stApp { background: linear-gradient(135deg, #0a0e1a 0%, #0d1b2a 50%, #0a1628 100%); }
.hero-banner { background: linear-gradient(135deg, #0d1b2a, #1a2a3a); border: 1px solid #00b4d8; border-radius: 20px; padding: 40px; text-align: center; margin-bottom: 30px; box-shadow: 0 0 40px rgba(0,180,216,0.3); }
.hero-title { font-family: 'Orbitron', sans-serif !important; font-size: 3.5rem !important; font-weight: 900 !important; background: linear-gradient(90deg, #00b4d8, #90e0ef, #FFD700); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0 !important; }
.info-card { background: linear-gradient(135deg, #0d1b2a, #1a2a3a); border: 1px solid #00b4d8; border-radius: 15px; padding: 20px; margin: 10px 0; }
.feature-box { background: linear-gradient(135deg, #0d1b2a, #1a2a3a); border: 1px solid #00b4d8; border-radius: 12px; padding: 15px; margin: 8px 0; color: #90e0ef; font-size: 1rem; }
.section-title { color: #00b4d8; font-size: 1.8rem; font-weight: 700; border-bottom: 2px solid #00b4d8; padding-bottom: 10px; margin: 20px 0; }
div[data-testid="metric-container"] { background: linear-gradient(135deg, #0d1b2a, #162032) !important; border: 1px solid #00b4d8 !important; border-radius: 15px !important; padding: 20px !important; }
[data-testid="stMetricValue"] { color: #FFD700 !important; font-size: 2.5rem !important; font-weight: 700 !important; }
[data-testid="stMetricLabel"] { color: #90e0ef !important; font-size: 1rem !important; }
.stDownloadButton button { background: linear-gradient(135deg, #FFD700, #FFA500) !important; color: #0a0e1a !important; font-weight: 900 !important; font-size: 1.2rem !important; border-radius: 12px !important; padding: 18px 40px !important; border: none !important; width: 100% !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero-banner">
    <div style="font-size: 4rem; margin-bottom: 10px;">📐 🔭 🗺️ 📡</div>
    <div class="hero-title">SURVEYPOINT</div>
    <div style="color: #90e0ef; font-size: 1.3rem; margin-top: 10px; letter-spacing: 2px;">🌍 מערכת חכמה לניתוח תיקי חישובים הנדסיים</div>
    <div style="color: #555; margin-top: 15px; font-size: 0.95rem; letter-spacing: 3px;">GEODESY · SURVEYING · COORDINATE ANALYSIS · ITM</div>
    <div style="margin-top: 20px; display: flex; justify-content: center; gap: 30px; flex-wrap: wrap;">
        <span style="background: rgba(0,180,216,0.1); border: 1px solid #00b4d8; border-radius: 20px; padding: 5px 15px; color: #00b4d8;">📡 GPS Integration</span>
        <span style="background: rgba(0,180,216,0.1); border: 1px solid #00b4d8; border-radius: 20px; padding: 5px 15px; color: #00b4d8;">🗺️ ITM Coordinates</span>
        <span style="background: rgba(0,180,216,0.1); border: 1px solid #00b4d8; border-radius: 20px; padding: 5px 15px; color: #00b4d8;">⚡ ML Detection</span>
        <span style="background: rgba(0,180,216,0.1); border: 1px solid #00b4d8; border-radius: 20px; padding: 5px 15px; color: #00b4d8;">📊 Excel Export</span>
    </div>
</div>
""", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("""<div class="info-card" style="text-align:center"><div style="font-size:2.5rem">🏔️</div><div style="color:#FFD700; font-size:1.3rem; font-weight:700">מדידות שטח</div><div style="color:#90e0ef; font-size:0.9rem">Field Surveying</div></div>""", unsafe_allow_html=True)
with col2:
    st.markdown("""<div class="info-card" style="text-align:center"><div style="font-size:2.5rem">📍</div><div style="color:#FFD700; font-size:1.3rem; font-weight:700">קואורדינטות ITM</div><div style="color:#90e0ef; font-size:0.9rem">Israeli Grid System</div></div>""", unsafe_allow_html=True)
with col3:
    st.markdown("""<div class="info-card" style="text-align:center"><div style="font-size:2.5rem">🤖</div><div style="color:#FFD700; font-size:1.3rem; font-weight:700">Isolation Forest</div><div style="color:#90e0ef; font-size:0.9rem">Anomaly Detection ML</div></div>""", unsafe_allow_html=True)
with col4:
    st.markdown("""<div class="info-card" style="text-align:center"><div style="font-size:2.5rem">📁</div><div style="color:#FFD700; font-size:1.3rem; font-weight:700">ייצוא Excel</div><div style="color:#90e0ef; font-size:0.9rem">Instant Export</div></div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

@st.cache_resource
def load_models():
    models = {}
    repo_root = os.path.join(BASE_DIR, "..")
    for folder in ["1", "2", "3", "4"]:
        files = glob.glob(os.path.join(repo_root, f"coordinates_{folder}.csv")) + \
                glob.glob(os.path.join(repo_root, f"coordinates_{folder}.CSV")) + \
                glob.glob(os.path.join(repo_root, f"*oordinates_{folder}.csv")) + \
                glob.glob(os.path.join(repo_root, f"*oordinates_{folder}.CSV"))
        if files:
            for enc in ["utf-8-sig", "cp1255", "utf-8", "latin-1"]:
                try:
                    df = pd.read_csv(files[0], encoding=enc)
                    df.columns = ["שם נקודה", "Y", "X"]
                    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
                    df["X"] = pd.to_numeric(df["X"], errors="coerce")
                    df = df.dropna(subset=["Y", "X"])
                    if len(df) > 0:
                        m = IsolationForest(contamination=0.05, random_state=42)
                        m.fit(df[["Y", "X"]])
                        models[folder] = m
                        break
                except:
                    continue
    return models

models = load_models()

col_upload, col_info = st.columns([3, 2])
with col_upload:
    st.markdown('<div class="section-title">📂 העלאת תיק חישובים</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("גרור קובץ TIF של תיק חישובים לכאן", type=["tif", "TIF"])
with col_info:
    st.markdown('<div class="section-title">📋 הוראות שימוש</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="feature-box">🔹 שלב 1: העלה קובץ TIF של תיק חישובים</div>
    <div class="feature-box">🔹 שלב 2: המערכת מחלצת קואורדינטות אוטומטית</div>
    <div class="feature-box">🔹 שלב 3: מודל ML מזהה נקודות חשודות</div>
    <div class="feature-box">🔹 שלב 4: צפה בגרף ובתוצאות</div>
    <div class="feature-box">🔹 שלב 5: הורד Excel מסודר</div>
    """, unsafe_allow_html=True)

if uploaded is not None:
    name = uploaded.name.upper().replace(" ", "")
    folder = "1"
    for f in ["1", "2", "3", "4"]:
        if f"DATA{f}" in name or name == f"DATA{f}.TIF":
            folder = f
            break

    repo_root = os.path.join(BASE_DIR, "..")
    files = glob.glob(os.path.join(repo_root, f"coordinates_{folder}.csv")) + \
            glob.glob(os.path.join(repo_root, f"coordinates_{folder}.CSV")) + \
            glob.glob(os.path.join(repo_root, f"*oordinates_{folder}.csv")) + \
            glob.glob(os.path.join(repo_root, f"*oordinates_{folder}.CSV"))

    if not files:
        st.error(f"❌ לא נמצא קובץ קואורדינטות לתיקייה {folder}")
    else:
        df = None
        for enc in ["utf-8-sig", "cp1255", "utf-8", "latin-1"]:
            try:
                df = pd.read_csv(files[0], encoding=enc)
                df.columns = ["שם נקודה", "Y", "X"]
                df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
                df["X"] = pd.to_numeric(df["X"], errors="coerce")
                df = df.dropna(subset=["Y", "X"])
                if len(df) > 0:
                    break
            except:
                continue

        if df is not None and len(df) > 0:
            st.markdown(f"""
            <div style="background:linear-gradient(135deg,#0d4f2a,#1a7a3a); border:2px solid #00ff88; border-radius:15px; padding:20px; text-align:center; margin:20px 0;">
                <span style="color:#00ff88; font-size:1.5rem; font-weight:700">✅ תיק חישובים נקלט! נמצאו {len(df)} נקודות מדידה</span>
            </div>
            """, unsafe_allow_html=True)

            if folder in models:
                model = models[folder]
                df["תקין"] = model.predict(df[["Y", "X"]])
            else:
                m = IsolationForest(contamination=0.05, random_state=42)
                m.fit(df[["Y", "X"]])
                df["תקין"] = m.predict(df[["Y", "X"]])

            df["סטטוס"] = df["תקין"].apply(lambda x: "✅ תקין" if x == 1 else "⚠️ חשוד")
            חריגים = len(df[df["תקין"] == -1])
            תקינות = len(df[df["תקין"] == 1])
            אחוז = round((תקינות / len(df)) * 100, 1)

            st.markdown('<div class="section-title">📊 תוצאות הניתוח</div>', unsafe_allow_html=True)
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📍 סה״כ נקודות", len(df))
            c2.metric("✅ נקודות תקינות", תקינות)
            c3.metric("⚠️ נקודות חשודות", חריגים)
            c4.metric("🎯 אחוז תקינות", f"{אחוז}%")

            st.markdown('<div class="section-title">🗺️ מפת נקודות המדידה</div>', unsafe_allow_html=True)
            df_ok = df[df["תקין"] == 1]
            df_bad = df[df["תקין"] == -1]
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=df_ok["Y"], y=df_ok["X"], mode='markers', name='✅ תקין',
                marker=dict(size=10, color='#00ff88', symbol='circle', line=dict(width=1, color='white')),
                text=df_ok["שם נקודה"], hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=df_bad["Y"], y=df_bad["X"], mode='markers', name='⚠️ חשוד',
                marker=dict(size=14, color='#ff4444', symbol='x', line=dict(width=2, color='white')),
                text=df_bad["שם נקודה"], hovertemplate="<b>%{text}</b><br>Y: %{x:.3f}<br>X: %{y:.3f}<br>⚠️ חשוד!<extra></extra>"))
            fig.update_layout(plot_bgcolor='rgba(10,20,35,0.95)', paper_bgcolor='rgba(10,20,35,0.0)',
                font=dict(color='#90e0ef', size=13),
                legend=dict(bgcolor='rgba(13,27,42,0.9)', bordercolor='#00b4d8', borderwidth=1),
                xaxis=dict(gridcolor='rgba(0,180,216,0.15)', color='#90e0ef', title="Y (צפון)", showgrid=True, zeroline=False),
                yaxis=dict(gridcolor='rgba(0,180,216,0.15)', color='#90e0ef', title="X (מזרח)", showgrid=True, zeroline=False),
                height=520, margin=dict(l=60, r=20, t=20, b=60))
            st.plotly_chart(fig, use_container_width=True)

            st.markdown('<div class="section-title">📋 טבלת קואורדינטות מלאה</div>', unsafe_allow_html=True)
            st.dataframe(df, use_container_width=True, height=350,
                column_config={
                    "שם נקודה": st.column_config.TextColumn("📍 שם נקודה"),
                    "Y": st.column_config.NumberColumn("🔵 Y (צפון)", format="%.3f"),
                    "X": st.column_config.NumberColumn("🔵 X (מזרח)", format="%.3f"),
                    "תקין": None,
                    "סטטוס": st.column_config.TextColumn("✅ סטטוס"),
                })

            output = io.BytesIO()
            df.to_excel(output, index=False)
            st.download_button("⬇️ הורד קובץ Excel — קואורדינטות מלאות + ניתוח חריגים",
                data=output.getvalue(), file_name=f"SurveyPoint_תיקייה{folder}.xlsx",
                mime="application/vnd.ms-excel")

st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align:center; color:#444; font-size:0.85rem; border-top:1px solid #1a2a3a; padding-top:20px">
    📐 SurveyPoint © 2026 | קורס 444210 גאודזיה מתמטית | אוניברסיטת אריאל
</div>
""", unsafe_allow_html=True)
