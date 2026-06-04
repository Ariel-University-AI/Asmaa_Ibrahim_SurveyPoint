import streamlit as st
import streamlit.components.v1 as components
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

# ── רקע אנימטיבי ──────────────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    function init() {
        try {
            var doc = window.parent.document;
            var existing = doc.getElementById('sp-bg-canvas');
            if (existing) return;

            var canvas = doc.createElement('canvas');
            canvas.id = 'sp-bg-canvas';
            canvas.style.cssText = [
                'position:fixed','top:0','left:0',
                'width:100%','height:100%',
                'z-index:0','pointer-events:none',
                'opacity:0.85'
            ].join(';');
            doc.body.insertBefore(canvas, doc.body.firstChild);

            function resize() {
                canvas.width  = window.parent.innerWidth;
                canvas.height = window.parent.innerHeight;
            }
            resize();
            window.parent.addEventListener('resize', resize);

            var ctx = canvas.getContext('2d');
            var pts = [];
            for (var i = 0; i < 80; i++) {
                var gold = Math.random() > 0.72;
                pts.push({
                    x: Math.random() * canvas.width,
                    y: Math.random() * canvas.height,
                    vx: (Math.random() - 0.5) * 0.25,
                    vy: (Math.random() - 0.5) * 0.25,
                    r:  Math.random() * 2 + 0.4,
                    a:  Math.random(),
                    da: (Math.random() * 0.008 + 0.002) * (Math.random() > 0.5 ? 1 : -1),
                    c:  gold ? '#FFD700' : '#00D4FF'
                });
            }

            function draw() {
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                /* fine grid */
                ctx.strokeStyle = 'rgba(0,212,255,0.03)';
                ctx.lineWidth = 1;
                for (var x = 0; x < canvas.width; x += 60) {
                    ctx.beginPath(); ctx.moveTo(x,0); ctx.lineTo(x,canvas.height); ctx.stroke();
                }
                for (var y = 0; y < canvas.height; y += 60) {
                    ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(canvas.width,y); ctx.stroke();
                }

                /* nebula corners */
                var g1 = ctx.createRadialGradient(0, 0, 0, 0, 0, 400);
                g1.addColorStop(0, 'rgba(123,47,190,0.07)');
                g1.addColorStop(1, 'transparent');
                ctx.fillStyle = g1; ctx.fillRect(0, 0, 400, 400);

                var g2 = ctx.createRadialGradient(canvas.width, canvas.height, 0,
                         canvas.width, canvas.height, 450);
                g2.addColorStop(0, 'rgba(0,212,255,0.06)');
                g2.addColorStop(1, 'transparent');
                ctx.fillStyle = g2;
                ctx.fillRect(canvas.width - 450, canvas.height - 450, 450, 450);

                var g3 = ctx.createRadialGradient(canvas.width, 0, 0, canvas.width, 0, 300);
                g3.addColorStop(0, 'rgba(13,31,60,0.12)');
                g3.addColorStop(1, 'transparent');
                ctx.fillStyle = g3; ctx.fillRect(canvas.width - 300, 0, 300, 300);

                /* animated points */
                pts.forEach(function(p) {
                    p.x += p.vx; p.y += p.vy;
                    p.a += p.da;
                    if (p.a >= 1) { p.a = 1; p.da = -Math.abs(p.da); }
                    if (p.a <= 0) { p.a = 0; p.da =  Math.abs(p.da); }
                    if (p.x < 0) p.x = canvas.width;
                    if (p.x > canvas.width) p.x = 0;
                    if (p.y < 0) p.y = canvas.height;
                    if (p.y > canvas.height) p.y = 0;

                    ctx.save();
                    ctx.globalAlpha = p.a * 0.9;
                    ctx.shadowBlur  = 10;
                    ctx.shadowColor = p.c;
                    ctx.fillStyle   = p.c;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                });

                requestAnimationFrame(draw);
            }
            draw();
        } catch(e) {}
    }
    setTimeout(init, 300);
    setTimeout(init, 1500);
})();
</script>
""", height=0)

# ── עיצוב ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Heebo:wght@300;400;600;700;900&family=Orbitron:wght@400;700;900&display=swap');

* { font-family: 'Heebo', sans-serif !important; direction: rtl; }
.stApp {
    background: radial-gradient(ellipse at 20% 50%, #0d1f3c 0%, #050c1a 50%, #0a0518 100%) !important;
    background-attachment: fixed !important;
}
/* Hide components iframe */
iframe[title="streamlit_components"] { display: none !important; }


/* ══════════════════════════════════════════════════
   ANIMATIONS
══════════════════════════════════════════════════ */
@keyframes scan-beam {
    0%   { top:-2px; opacity:0; }  4%   { opacity:1; }
    96%  { opacity:1; }             100% { top:100%; opacity:0; }
}
@keyframes radar-sweep {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
}
@keyframes glow-point {
    0%,100% { opacity:0.15; transform:scale(0.6); }
    50%     { opacity:1;    transform:scale(1.3); box-shadow:0 0 12px #00D4FF, 0 0 24px #00D4FF; }
}
@keyframes pulse-ring  { 0%,100%{transform:scale(0.88);opacity:.9} 50%{transform:scale(1.06);opacity:.4} }
@keyframes pulse-ring2 { 0%,100%{transform:scale(1);opacity:.6}   50%{transform:scale(1.22);opacity:.15} }
@keyframes corner-anim { 0%,100%{border-color:rgba(0,212,255,.55)} 50%{border-color:rgba(255,215,0,.8)} }
@keyframes coord-blink { 0%,85%,100%{opacity:1} 90%{opacity:.1} }
@keyframes status-pulse{ 0%,100%{opacity:1} 50%{opacity:.35} }
@keyframes title-glow  {
    0%,100%{ text-shadow: 0 0 15px #00D4FF, 0 0 40px #00D4FF, 0 0 80px rgba(0,212,255,.3),
                          0 0 15px #FFD700, 0 0 30px rgba(255,215,0,.2); }
    50%    { text-shadow: 0 0 25px #00D4FF, 0 0 60px #00D4FF, 0 0 120px rgba(0,212,255,.5),
                          0 0 25px #FFD700, 0 0 50px rgba(255,215,0,.4); }
}
@keyframes scan-doc    { 0%{top:0;opacity:0} 5%{opacity:.8} 95%{opacity:.8} 100%{top:100%;opacity:0} }
@keyframes blink-cursor{ 0%,100%{opacity:1} 50%{opacity:0} }
@keyframes btn-pulse   {
    0%,100%{ box-shadow: 0 4px 15px rgba(123,47,190,0.4); }
    50%    { box-shadow: 0 4px 30px rgba(123,47,190,0.8), 0 0 0 6px rgba(123,47,190,0.1); }
}
@keyframes metric-in   { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:none} }
@keyframes tab-line    { from{width:0;left:50%} to{width:100%;left:0} }

/* ══ HERO ══════════════════════════════════════════ */
.hero {
    position: relative;
    border: 1px solid rgba(0,212,255,0.25);
    border-radius: 16px;
    padding: 60px 40px 52px;
    text-align: center;
    margin-bottom: 28px;
    overflow: hidden;
    background: #060c16;
    background-image:
        linear-gradient(rgba(0,212,255,.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,.03) 1px, transparent 1px),
        linear-gradient(rgba(0,212,255,.06) 1px, transparent 1px),
        linear-gradient(90deg, rgba(0,212,255,.06) 1px, transparent 1px);
    background-size: 20px 20px, 20px 20px, 100px 100px, 100px 100px;
    box-shadow: 0 0 120px rgba(0,212,255,.06), 0 0 60px rgba(123,47,190,.04);
}
/* Scanning beam */
.hero-scan {
    position:absolute; left:0; right:0; height:2px;
    background: linear-gradient(90deg,transparent,rgba(0,212,255,.08) 20%,rgba(0,212,255,.75) 50%,rgba(0,212,255,.08) 80%,transparent);
    animation: scan-beam 4s ease-in-out infinite;
}
/* Radar circle */
.hero-radar {
    position:absolute; left:5%; top:50%; transform:translateY(-50%);
    width:100px; height:100px;
}
.hr-circle {
    position:absolute; inset:0;
    border-radius:50%;
    border: 1px solid rgba(0,212,255,0.18);
}
.hr-inner { inset:20px; border: 1px solid rgba(0,212,255,0.12); }
.hr-sweep {
    position:absolute; inset:0;
    border-radius:50%;
    background: conic-gradient(from 0deg, transparent 70%, rgba(0,212,255,0.4) 100%);
    animation: radar-sweep 4s linear infinite;
}
.hr-center {
    position:absolute; top:50%; left:50%;
    transform:translate(-50%,-50%);
    width:6px; height:6px; border-radius:50%;
    background:#00D4FF;
    box-shadow: 0 0 10px #00D4FF;
}
.hr-h {
    position:absolute; top:50%; left:0; right:0; height:1px;
    transform:translateY(-50%);
    background: linear-gradient(90deg,transparent,rgba(0,212,255,.4),transparent);
}
.hr-v {
    position:absolute; left:50%; top:0; bottom:0; width:1px;
    transform:translateX(-50%);
    background: linear-gradient(180deg,transparent,rgba(0,212,255,.4),transparent);
}
/* Survey points scattered */
.hero-point {
    position:absolute; width:5px; height:5px;
    border-radius:50%; background:#00D4FF;
    box-shadow: 0 0 6px #00D4FF;
}
.hp1{top:20%;left:18%;animation:glow-point 2.1s infinite 0s;}
.hp2{top:65%;left:25%;animation:glow-point 2.1s infinite .4s;}
.hp3{top:35%;left:80%;animation:glow-point 2.1s infinite .8s;}
.hp4{top:75%;left:72%;animation:glow-point 2.1s infinite 1.2s;}
.hp5{top:15%;left:60%;animation:glow-point 2.1s infinite 1.6s;}
.hp6{top:80%;left:45%;animation:glow-point 2.1s infinite 2.0s;background:#FFD700;box-shadow:0 0 6px #FFD700;}
/* CAD corners */
.hero-corner { position:absolute; width:20px; height:20px; border-style:solid; animation:corner-anim 3s ease-in-out infinite; }
.hc-tl{top:10px;left:10px; border-width:2px 0 0 2px;}
.hc-tr{top:10px;right:10px; border-width:2px 2px 0 0;}
.hc-bl{bottom:10px;left:10px; border-width:0 0 2px 2px;}
.hc-br{bottom:10px;right:10px; border-width:0 2px 2px 0;}
/* Coords & status */
.hero-coords {
    position:absolute; right:16px; bottom:12px;
    font-family:'Courier New',monospace; font-size:.7rem;
    color:rgba(0,212,255,.55); text-align:right; line-height:1.7;
    animation: coord-blink 5s infinite;
}
.hero-status {
    position:absolute; left:16px; bottom:12px;
    display:flex; gap:14px;
    font-family:'Orbitron',sans-serif; font-size:.6rem;
    letter-spacing:1.5px; color:rgba(0,212,255,.4);
}
.hs-dot{ color:#00ff88; animation:status-pulse 2s infinite; }
/* Title */
.hero-title {
    font-family:'Orbitron',sans-serif !important;
    font-size:3.6rem; font-weight:900;
    color:#fff; letter-spacing:8px;
    animation: title-glow 3s ease-in-out infinite;
    margin-bottom:12px; position:relative;
}
.hero-sub { color:rgba(144,224,239,.8); font-size:1rem; letter-spacing:.5px; position:relative; }

/* ══ GLASSMORPHISM CARDS ══ */
div[data-testid="metric-container"] {
    background: rgba(255,255,255,0.03) !important;
    backdrop-filter: blur(20px) !important;
    -webkit-backdrop-filter: blur(20px) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 14px !important;
    padding: 18px !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.06) !important;
    transition: border-color .3s, box-shadow .3s !important;
    animation: metric-in .6s ease-out both;
}
div[data-testid="metric-container"]:hover {
    border-color: rgba(0,212,255,0.5) !important;
    box-shadow: 0 0 30px rgba(0,212,255,0.18) !important;
    transform: scale(1.02) !important;
}
[data-testid="stMetricValue"] {
    background: linear-gradient(90deg,#00D4FF,#FFD700) !important;
    -webkit-background-clip: text !important;
    -webkit-text-fill-color: transparent !important;
    font-size:2.1rem !important; font-weight:800 !important;
}
[data-testid="stMetricLabel"] { color:#90e0ef !important; font-size:.9rem !important; }
[data-testid="stMetricDelta"]  { color:#00ff88 !important; }

/* ══ TABS ══ */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(13,21,32,0.9);
    backdrop-filter: blur(10px);
    border-radius: 12px; padding:4px; gap:4px;
    border: 1px solid rgba(0,212,255,0.1);
}
.stTabs [data-baseweb="tab"] {
    color:#6b8fa8 !important; font-weight:600; font-size:.95rem;
    border-radius:8px; padding:8px 18px;
    transition: color .2s, background .2s;
    position: relative;
}
.stTabs [aria-selected="true"] {
    background: rgba(0,212,255,0.12) !important;
    color:#00D4FF !important;
    box-shadow: 0 2px 0 0 #00D4FF !important;
}

/* ══ BUTTONS ══ */
.stButton > button {
    background: linear-gradient(135deg,#00D4FF 0%,#7B2FBE 100%) !important;
    color:#fff !important; font-weight:700 !important;
    border:none !important; border-radius:10px !important;
    padding:10px 28px !important; font-size:1rem !important;
    transition: all .3s !important;
    animation: btn-pulse 2.5s ease-in-out infinite;
}
.stButton > button:hover {
    transform: translateY(-2px) scale(1.03) !important;
    box-shadow: 0 8px 30px rgba(123,47,190,0.6) !important;
}
.stDownloadButton button {
    background: linear-gradient(135deg,#00ff88,#00b4d8) !important;
    color:#0A0E1A !important; font-weight:900 !important;
    border:none !important; border-radius:10px !important; width:100% !important;
    animation: none !important;
}
.stDownloadButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 6px 20px rgba(0,255,136,0.4) !important;
}

/* ══ UPLOAD TERMINAL ══ */
@keyframes blink-cursor { 0%,100%{opacity:1} 50%{opacity:0} }
.scan-terminal {
    background: rgba(255,255,255,0.02);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(0,212,255,0.2);
    border-radius: 14px; padding:28px 32px 20px;
    margin-bottom:16px; position:relative; overflow:hidden;
    transition: border-color .3s;
}
.scan-terminal:hover { border-color: rgba(0,212,255,0.5); }
.scan-terminal::before {
    content:''; position:absolute; left:0; right:0; height:1.5px;
    background: linear-gradient(90deg,transparent,rgba(0,212,255,.6),transparent);
    animation: scan-doc 3.5s ease-in-out infinite;
}
.st-corner{position:absolute;width:14px;height:14px;border-color:rgba(0,212,255,.6);border-style:solid;}
.st-tl{top:8px;left:8px; border-width:2px 0 0 2px;}
.st-tr{top:8px;right:8px; border-width:2px 2px 0 0;}
.st-bl{bottom:8px;left:8px; border-width:0 0 2px 2px;}
.st-br{bottom:8px;right:8px; border-width:0 2px 2px 0;}
.st-header{display:flex;align-items:center;gap:16px;margin-bottom:6px;}
.st-icon{font-size:2.2rem;filter:drop-shadow(0 0 8px rgba(0,212,255,.6));}
.st-label{font-family:'Orbitron',sans-serif;font-size:.68rem;letter-spacing:3px;color:rgba(0,212,255,.5);}
.st-title{font-family:'Orbitron',sans-serif;font-size:1.1rem;font-weight:700;color:#fff;letter-spacing:2px;}
.st-formats{font-size:.75rem;color:rgba(0,212,255,.4);letter-spacing:2px;margin-top:2px;}
.st-cursor{animation:blink-cursor 1s infinite;}

hr { border-color: rgba(0,212,255,0.1) !important; }

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.02) !important;
    backdrop-filter: blur(10px) !important;
    border: 1px dashed rgba(0,212,255,0.3) !important;
    border-radius: 12px !important; padding: 16px !important;
}
[data-testid="stFileUploader"] label,
[data-testid="stFileUploaderDropzone"] > div > p,
[data-testid="stFileUploaderDropzone"] small { color:#fff !important; }
[data-testid="stFileUploaderDropzone"] button {
    position:relative !important; min-width:120px !important; direction:ltr !important;
}
[data-testid="stFileUploaderDropzone"] button * { visibility:hidden !important; }
[data-testid="stFileUploaderDropzone"] button::after {
    content:"Browse files"; visibility:visible !important;
    position:absolute !important; inset:0 !important;
    display:flex !important; align-items:center !important; justify-content:center !important;
    font-size:14px !important; font-family:'Heebo',sans-serif !important;
    direction:ltr !important; white-space:nowrap !important;
}
/* Inputs */
.stTextInput input {
    background:rgba(13,27,42,.8) !important;
    border:1px solid rgba(0,212,255,.25) !important;
    border-radius:8px !important; color:#fff !important;
    transition: border-color .2s !important;
}
.stTextInput input:focus { border-color:rgba(0,212,255,.6) !important; }
.stSelectbox>div>div {
    background:rgba(13,27,42,.8) !important;
    border:1px solid rgba(0,212,255,.25) !important;
}
.stMarkdown h3 { color:#00D4FF !important; }
.stMarkdown h2 {
    background: linear-gradient(90deg,#00D4FF,#7B2FBE);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    font-weight:800 !important;
}
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
    <div class="hero-point hp1"></div>
    <div class="hero-point hp2"></div>
    <div class="hero-point hp3"></div>
    <div class="hero-point hp4"></div>
    <div class="hero-point hp5"></div>
    <div class="hero-point hp6"></div>
    <div class="hero-radar">
        <div class="hr-circle"></div>
        <div class="hr-circle hr-inner"></div>
        <div class="hr-sweep"></div>
        <div class="hr-h"></div>
        <div class="hr-v"></div>
        <div class="hr-center"></div>
    </div>
    <div class="hero-title">SURVEYPOINT</div>
    <div class="hero-sub">מערכת חכמה לניתוח תיקי חישובים הנדסיים | אוניברסיטת אריאל</div>
    <div class="hero-coords">Y: 151,650.99<br>X: 243,464.96<br>&Delta;: &plusmn;0.003m</div>
    <div class="hero-status">
        <span><span class="hs-dot">&#9679;</span> ACTIVE</span>
        <span>GEMINI AI</span><span>ITM GRID</span>
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

    st.markdown("""
<div class="scan-terminal">
    <div class="st-corner st-tl"></div><div class="st-corner st-tr"></div>
    <div class="st-corner st-bl"></div><div class="st-corner st-br"></div>
    <div class="st-header">
        <div class="st-icon">📐</div>
        <div>
            <div class="st-label">DOCUMENT INGESTION TERMINAL</div>
            <div class="st-title">SCAN CALCULATION FILE<span class="st-cursor">_</span></div>
            <div class="st-formats">TIF &nbsp;•&nbsp; TIFF &nbsp;•&nbsp; PDF &nbsp;|&nbsp; MAX 200MB</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "גרירת קובץ TIF/PDF לכאן",
        type=["tif", "TIF", "tiff", "TIFF", "pdf", "PDF"],
        key="ocr_upload",
        label_visibility="collapsed",
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
    st.markdown("---")

    has_ocr = "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None

    if has_ocr:
        df_input = st.session_state["ocr_df"]
        st.success(f"✅ {len(df_input)} נקודות מחולצות")
        contamination = st.slider("רגישות לחריגים", 0.01, 0.20, 0.05, 0.01,
                                  help="0.05 = 5% מהנקודות יסומנו כחשודות", key="det_cont")
        df_r = run_anomaly(df_input, contamination=contamination)
        show_anomaly_chart(df_r)
    else:
        st.info("💡 חלץ קובץ TIF בלשונית 'חילוץ' — התוצאות יוצגו כאן אוטומטית.")

# ══════════════════════════════════════════════════════════════════════════════
# לשונית 3 — EDA
# ══════════════════════════════════════════════════════════════════════════════
with tab_eda:
    st.markdown("## 📊 ניתוח נתונים")
    st.markdown("---")

    if "ocr_df" in st.session_state and st.session_state["ocr_df"] is not None:
        df_e = st.session_state["ocr_df"]
        st.success(f"✅ מציג נתונים מחולצים — {len(df_e)} נקודות")
    elif DATASETS:
        sel_e = st.selectbox("בחר מערך:", [f"מערך {k}" for k in DATASETS.keys()], key="eda_sel")
        df_e  = load_csv(DATASETS[sel_e.split()[-1]])
        if df_e is None:
            st.error("שגיאה בטעינה")
            st.stop()
    else:
        st.info("💡 חלץ קובץ TIF בלשונית 'חילוץ' — התוצאות יוצגו כאן אוטומטית.")
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
    r1c1, r1c2, r1c3 = st.columns(3)
    with r1c1: tik_num  = st.text_input("מספר תיק",          key="tik_num",  placeholder="9546")
    with r1c2: tlr_num  = st.text_input('מספר תל"ר',         key="tlr_num",  placeholder="989-986")
    with r1c3: tlr_year = st.text_input('שנת תל"ר',          key="tlr_year", placeholder="2006")

    r2c1, r2c2, r2c3 = st.columns(3)
    with r2c1: gush      = st.text_input("גוש",               key="gush",     placeholder="3893")
    with r2c2: helka     = st.text_input("חלקה",              key="helka",    placeholder="")
    with r2c3: tik_chish = st.text_input("מספר תיק חישובי",   key="tik_chish",placeholder="525")

    fields = {"📁 מספר תיק": tik_num, '📋 מספר תל"ר': tlr_num,
              '📅 שנת תל"ר': tlr_year, "🗺️ גוש": gush,
              "📌 חלקה": helka, "🔢 מספר תיק חישובי": tik_chish}
    filled = {k: v for k, v in fields.items() if v}
    if filled:
        st.markdown("---")
        mcols = st.columns(len(filled))
        for i, (label, val) in enumerate(filled.items()):
            mcols[i].metric(label, val)

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
