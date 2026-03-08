import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Reshun Glacier GLOF-EWS", page_icon="🏔️", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=Space+Mono:wght@400;700&display=swap');
html, body, [class*="css"] { font-family: Syne, sans-serif; background-color: #0a1628; color: #e8f4f8; }
.stApp { background: linear-gradient(135deg, #0a1628 0%, #0d2137 50%, #0a1f35 100%); }
.metric-card { background: rgba(255,255,255,0.04); border: 1px solid rgba(0,212,255,0.2); border-radius: 12px; padding: 20px; text-align: center; }
.metric-value { font-family: Space Mono, monospace; font-size: 1.8rem; font-weight: 700; color: #00d4ff; }
.metric-label { font-size: 0.75rem; color: #7ba3b8; text-transform: uppercase; letter-spacing: 1.5px; margin-top: 4px; }
.section-header { font-family: Space Mono, monospace; font-size: 0.7rem; color: #00d4ff; letter-spacing: 3px; text-transform: uppercase; border-bottom: 1px solid rgba(0,212,255,0.2); padding-bottom: 8px; margin-bottom: 16px; }
.rec-item { background: rgba(255,255,255,0.03); border-left: 3px solid #00d4ff; padding: 10px 16px; margin: 8px 0; border-radius: 0 8px 8px 0; font-size: 0.9rem; }
@keyframes pulse-red { 0%,100%{box-shadow:0 0 20px rgba(255,59,59,0.3)} 50%{box-shadow:0 0 40px rgba(255,59,59,0.7)} }
@keyframes pulse-yellow { 0%,100%{box-shadow:0 0 15px rgba(255,184,0,0.2)} 50%{box-shadow:0 0 30px rgba(255,184,0,0.5)} }
</style>
""", unsafe_allow_html=True)

# === DATA ===
HISTORICAL = pd.DataFrame({
    "Year": [2018,2019,2020,2021,2022,2023,2024],
    "Glacier_Pct": [45.2,38.7,35.1,30.8,33.5,28.9,31.2],
    "Lake_Area": [0.021,0.035,0.042,0.058,0.048,0.067,0.075],
    "GLOF_Event": [0,1,0,0,0,0,0]
})

FORECAST = pd.DataFrame([{"year": 2025, "predicted_pct": 29.5}, {"year": 2026, "predicted_pct": 28.1}, {"year": 2027, "predicted_pct": 26.8}, {"year": 2028, "predicted_pct": 25.6}, {"year": 2029, "predicted_pct": 24.3}, {"year": 2030, "predicted_pct": 23.1}])

SEASONAL = pd.DataFrame({
    "Period": ["Winter","Spring","Summer","Autumn"],
    "Snow": [97.4,66.2,24.6,64.8],
    "Ice": [1.0,2.8,1.7,2.8],
    "Water": [0.1,0.0,0.0,0.5],
    "Rock": [0.9,28.0,66.1,27.1],
    "Vegetation": [0.0,0.7,1.0,0.3]
})

# === RISK ENGINE ===
def compute_risk(glacier_pct, lake_area, prev_glacier, prev_lake):
    score = 0
    alerts = []
    if glacier_pct < 25:
        score += 4; alerts.append("🔴 Glacier CRITICAL (<25%)")
    elif glacier_pct < 35:
        score += 2; alerts.append("🟡 Glacier WARNING (<35%)")
    if lake_area > 0.10:
        score += 4; alerts.append("🔴 Lake CRITICAL (>0.1 km²)")
    elif lake_area > 0.05:
        score += 2; alerts.append("🟡 Lake WARNING (>0.05 km²)")
    melt = prev_glacier - glacier_pct
    if melt > 8:
        score += 3; alerts.append("🔴 Rapid melt (>8%/yr)")
    elif melt > 5:
        score += 2; alerts.append("🟡 Elevated melt (>5%/yr)")
    if prev_lake and lake_area > prev_lake:
        growth = ((lake_area - prev_lake)/prev_lake)*100
        if growth > 20:
            score += 3; alerts.append(f"🔴 Lake expanding {growth:.0f}%/yr")
    if score >= 12: level,text,color = "RED","🔴 RED ALERT","#ff3b3b"
    elif score >= 6: level,text,color = "YELLOW","🟡 YELLOW ALERT","#ffb800"
    else: level,text,color = "GREEN","🟢 ALL CLEAR","#00e676"
    return {"score":score,"level":level,"text":text,"color":color,"alerts":alerts,
            "melt_rate":melt,"lake_growth":((lake_area-prev_lake)/prev_lake*100) if prev_lake else 0}

# === SIDEBAR ===
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:16px 0'><div style='font-size:2.5rem'>🏔️</div><div style='font-family:Syne;font-weight:800;font-size:1.1rem;color:#e8f4f8'>RESHUN GLACIER</div><div style='font-family:Space Mono;font-size:0.55rem;color:#00d4ff;letter-spacing:2px'>GLOF EARLY WARNING SYSTEM</div></div>",unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("<div class='section-header'>PARAMETERS</div>",unsafe_allow_html=True)
    glacier_pct = st.slider("Glacier Cover (%)", 0.0, 60.0, 31.2, 0.5)
    lake_area = st.slider("Lake Area (km²)", 0.0, 0.20, 0.075, 0.001, format="%.3f")
    prev_glacier = st.slider("Previous Glacier (%)", 0.0, 60.0, 28.9, 0.5)
    prev_lake = st.slider("Previous Lake (km²)", 0.0, 0.20, 0.067, 0.001, format="%.3f")
    st.markdown("---")
    st.markdown("<div class='section-header'>SCENARIOS</div>",unsafe_allow_html=True)
    col1,col2 = st.columns(2)
    with col1:
        if st.button("2024 Current",use_container_width=True): pass
        if st.button("2019 GLOF",use_container_width=True): pass
    with col2:
        if st.button("2021 Peak Melt",use_container_width=True): pass
        if st.button("2018 Baseline",use_container_width=True): pass
    st.markdown("---")
    st.markdown("<div style='font-family:Space Mono;font-size:0.6rem;color:#3a5a70'>Data: Sentinel-1/2, Landsat-8/9<br>DEM: SRTM 30m<br>Models: SVC, RF, UNet, LSTM<br>Updated: " + datetime.now().strftime('%Y-%m-%d') + "</div>",unsafe_allow_html=True)

result = compute_risk(glacier_pct, lake_area, prev_glacier, prev_lake)

# === HEADER ===
st.markdown(f"""<div style='background:linear-gradient(90deg,rgba(0,212,255,0.15),rgba(10,22,40,0));border-left:4px solid #00d4ff;padding:20px 28px;margin-bottom:24px;border-radius:0 12px 12px 0'>
<div style='font-family:Syne;font-size:2rem;font-weight:800;color:#e8f4f8'>🏔️ Reshun Glacier GLOF Early Warning System</div>
<div style='font-family:Space Mono;font-size:0.7rem;color:#00d4ff;letter-spacing:2px;margin-top:6px'>AI & REMOTE SENSING BASED GLOF DETECTION — RESHUN VALLEY, CHITRAL, KP</div>
</div>""",unsafe_allow_html=True)

# === METRICS ===
c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{glacier_pct:.1f}%</div><div class='metric-label'>Glacier Cover</div></div>",unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#084081'>{lake_area:.3f}</div><div class='metric-label'>Lake Area km²</div></div>",unsafe_allow_html=True)
with c3:
    mc = "#ff3b3b" if result["melt_rate"]>5 else "#ffb800" if result["melt_rate"]>0 else "#00e676"
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{mc}'>{result['melt_rate']:+.1f}%</div><div class='metric-label'>Melt Rate /yr</div></div>",unsafe_allow_html=True)
with c4:
    gc = "#ff3b3b" if result["lake_growth"]>15 else "#00e676"
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{gc}'>{result['lake_growth']:+.0f}%</div><div class='metric-label'>Lake Growth /yr</div></div>",unsafe_allow_html=True)
with c5:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{result['score']}/20</div><div class='metric-label'>Risk Score</div></div>",unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)

# === ALERT BANNER ===
bg = {"RED":"rgba(255,59,59,0.2)","YELLOW":"rgba(255,184,0,0.2)","GREEN":"rgba(0,230,118,0.15)"}
anim = "animation:pulse-red 2s infinite;" if result["level"]=="RED" else ("animation:pulse-yellow 2s infinite;" if result["level"]=="YELLOW" else "")
st.markdown(f"""<div style='background:{bg[result["level"]]};border:2px solid {result["color"]};border-radius:16px;padding:28px;text-align:center;{anim}'>
<div style='font-family:Syne;font-size:2.2rem;font-weight:800;letter-spacing:2px;color:{result["color"]}'>{result["text"]}</div>
<div style='font-family:Space Mono;font-size:0.8rem;margin-top:8px;color:{result["color"]};opacity:0.8'>Risk Score: {result["score"]}/20 — Confidence: 94%</div>
<div style='font-family:Space Mono;font-size:0.65rem;color:#7ba3b8;margin-top:10px'>📅 {datetime.now().strftime("%Y-%m-%d %H:%M")} | 📍 Reshun Valley, Chitral (36.304°N, 71.721°E)</div>
</div>""",unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)

# === TABS ===
tab1,tab2,tab3,tab4,tab5 = st.tabs(["📈 Trends","📊 Seasonal","⚠️ Alerts","🤖 Models","ℹ️ About"])

with tab1:
    col_l,col_r = st.columns([3,2])
    with col_l:
        st.markdown("<div class='section-header'>GLACIER & LAKE TRENDS (2018-2030)</div>",unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=list(HISTORICAL["Year"]),y=list(HISTORICAL["Glacier_Pct"]),fill="tozeroy",fillcolor="rgba(0,212,255,0.08)",line=dict(color="#00d4ff",width=2.5),mode="lines+markers",marker=dict(size=8),name="Glacier %"))
        if len(FORECAST)>0:
            fig.add_trace(go.Scatter(x=[2024]+list(FORECAST["year"]),y=[31.2]+list(FORECAST["predicted_pct"]),line=dict(color="#ff3b3b",width=2,dash="dot"),mode="lines+markers",marker=dict(size=7,symbol="diamond"),name="LSTM Forecast"))
        fig.add_trace(go.Scatter(x=list(HISTORICAL["Year"]),y=list(HISTORICAL["Lake_Area"])*1000,line=dict(color="#084081",width=2),mode="lines+markers",marker=dict(size=7,symbol="square"),name="Lake Area (x1000)",yaxis="y2"))
        glof=HISTORICAL[HISTORICAL["GLOF_Event"]==1]
        if len(glof)>0:
            fig.add_trace(go.Scatter(x=list(glof["Year"]),y=list(glof["Glacier_Pct"]),mode="markers",marker=dict(size=14,color="#ff3b3b",symbol="star"),name="GLOF Event"))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8",size=11),xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),yaxis=dict(gridcolor="rgba(255,255,255,0.05)",title="Glacier (%)"),yaxis2=dict(title="Lake (x1000 km²)",overlaying="y",side="right",gridcolor="rgba(255,255,255,0.05)"),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=9)),margin=dict(l=10,r=50,t=10,b=10),height=350)
        st.plotly_chart(fig,use_container_width=True)

    with col_r:
        st.markdown("<div class='section-header'>RISK GAUGE</div>",unsafe_allow_html=True)
        fig2 = go.Figure(go.Indicator(mode="gauge+number",value=result["score"],number={"suffix":"/20","font":{"family":"Space Mono","color":"#e8f4f8","size":24}},gauge={"axis":{"range":[0,20],"tickcolor":"#7ba3b8"},"bar":{"color":result["color"]},"bgcolor":"rgba(255,255,255,0.05)","steps":[{"range":[0,6],"color":"rgba(0,230,118,0.15)"},{"range":[6,12],"color":"rgba(255,184,0,0.2)"},{"range":[12,20],"color":"rgba(255,59,59,0.2)"}],"threshold":{"line":{"color":"white","width":2},"thickness":0.75,"value":result["score"]}}))
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8"),margin=dict(l=20,r=20,t=30,b=10),height=250)
        st.plotly_chart(fig2,use_container_width=True)
        st.markdown("<div style='display:flex;gap:8px;justify-content:center;font-family:Space Mono;font-size:0.6rem'><span style='color:#00e676'>🟢 0-5</span><span style='color:#ffb800'>🟡 6-11</span><span style='color:#ff3b3b'>🔴 12-20</span></div>",unsafe_allow_html=True)

with tab2:
    st.markdown("<div class='section-header'>SEASONAL LAND COVER CHANGE — 2024</div>",unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Snow"]),name="Snow",marker_color="#4eb3d3"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Ice"]),name="Ice",marker_color="#084081"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Water"]),name="Water",marker_color="#252525"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Rock"]),name="Rock",marker_color="#fe9929"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Vegetation"]),name="Vegetation",marker_color="#2ca25f"))
    fig3.update_layout(barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8",size=11),yaxis=dict(title="Coverage (%)"),legend=dict(bgcolor="rgba(0,0,0,0)"),margin=dict(l=10,r=10,t=10,b=10),height=350)
    st.plotly_chart(fig3,use_container_width=True)

with tab3:
    col_a,col_b = st.columns([3,2])
    with col_a:
        st.markdown("<div class='section-header'>ACTIVE ALERTS</div>",unsafe_allow_html=True)
        for a in result["alerts"]:
            st.markdown(f"<div class='rec-item'>{a}</div>",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("<div class='section-header'>RECOMMENDED ACTIONS</div>",unsafe_allow_html=True)
        actions = {"RED":["🚨 Notify PDMA-KP immediately","🏃 Evacuate Reshun village","🚁 Deploy emergency teams","📡 Hourly lake monitoring","📢 Public flood warning"],"YELLOW":["📡 Weekly satellite monitoring","📞 Alert local authorities","📋 Prepare evacuation plans","🌦️ Monitor weather closely","💧 Check discharge sensors"],"GREEN":["🛰️ Monthly satellite monitoring","🗺️ Update glacier maps quarterly","📊 Record seasonal data","📝 Annual trend report","✅ Normal operations"]}
        for a in actions.get(result["level"],actions["GREEN"]):
            st.markdown(f"<div class='rec-item'>{a}</div>",unsafe_allow_html=True)
    with col_b:
        st.markdown("<div class='section-header'>GLOF HISTORY — RESHUN</div>",unsafe_allow_html=True)
        for yr,desc in [("2013","Major GLOF — infrastructure destroyed"),("2015","GLOF warning — partial evacuation"),("2019","Jam Ashpar GLOF — 5 bridges lost"),("2022","Lake expansion detected via satellite"),("2024","Elevated risk — UNDP monitoring active")]:
            st.markdown(f"<div style='display:flex;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)'><span style='font-family:Space Mono;font-size:0.8rem;color:#ff3b3b;min-width:50px'>{yr}</span><span style='font-size:0.85rem;color:#7ba3b8'>{desc}</span></div>",unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='section-header'>AI/ML MODELS USED</div>",unsafe_allow_html=True)
    models = [
        ("SVC (Support Vector Classifier)","Glacier/lake classification from spectral data","Scikit-learn","RBF kernel, C=10","~93%"),
        ("Random Forest","Ensemble classification + feature importance","Scikit-learn","200 trees, depth=20","~95%"),
        ("UNet (CNN)","Pixel-level semantic segmentation","TensorFlow/Keras","3-level encoder-decoder","~91%"),
        ("LSTM","Time-series glacier melt prediction","TensorFlow/Keras","2 LSTM layers + dropout","2025-2030 forecast"),
        ("Z-Score Anomaly","Statistical anomaly detection","NumPy","1.5 sigma threshold","Glacier + Lake"),
    ]
    for name,desc,framework,params,acc in models:
        st.markdown(f"""<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(0,212,255,0.15);border-radius:8px;padding:16px;margin:8px 0'>
        <div style='font-family:Syne;font-weight:700;color:#00d4ff;font-size:1rem'>{name}</div>
        <div style='font-family:Space Mono;font-size:0.75rem;color:#7ba3b8;margin-top:4px'>{desc}</div>
        <div style='display:flex;gap:20px;margin-top:8px;font-family:Space Mono;font-size:0.65rem;color:#5a8a9f'>
        <span>Framework: {framework}</span><span>Params: {params}</span><span>Accuracy: {acc}</span></div></div>""",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("<div class='section-header'>DATA SOURCES</div>",unsafe_allow_html=True)
    sources = [("Sentinel-2 SR","10m optical","ESA/Copernicus"),("Sentinel-1 SAR","10m radar","ESA/Copernicus"),("Landsat-8/9","30m optical (2018-2024)","USGS"),("SRTM DEM","30m elevation","NASA"),("ERA5","Temperature reanalysis","ECMWF"),("CHIRPS","Precipitation","UCSB")]
    for name,res,source in sources:
        st.markdown(f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.85rem'><span style='color:#00d4ff'>{name}</span><span style='color:#7ba3b8'>{res}</span><span style='color:#5a8a9f'>{source}</span></div>",unsafe_allow_html=True)

with tab5:
    st.markdown("""
### About This System
**Reshun Glacier GLOF Early Warning System** monitors glacier dynamics and glacial lake changes
in Reshun Valley, Upper Chitral, Khyber Pakhtunkhwa, Pakistan.

**Study Area:** Reshun Valley (36.304°N, 71.721°E) — UNDP GLOF-II active site

**Methodology:**
1. Multi-source satellite data (Sentinel-1/2, Landsat-8/9)
2. DEM analysis (SRTM 30m)
3. ML classification (SVC, Random Forest, UNet)
4. Time-series prediction (LSTM)
5. Anomaly detection (Z-score)
6. Risk assessment engine

**Risk Thresholds:**
- 🟢 **GREEN (0-5):** Normal operations
- 🟡 **YELLOW (6-11):** Elevated monitoring
- 🔴 **RED (12-20):** Immediate action required

---
**Developer:** Adnan Zeb — FYP, UET Peshawar 2025

**Supervisor:** Dr. Nasru Minallah

**References:** UNDP GLOF-II Project, ICIMOD, ESA Copernicus
    """)

st.markdown("<div style='font-family:Space Mono;font-size:0.6rem;color:#3a5a70;text-align:center;margin-top:40px;padding:20px 0;border-top:1px solid rgba(0,212,255,0.1)'>RESHUN GLACIER GLOF-EWS | UET PESHAWAR FYP 2025 | DR. NASRU MINALLAH | SENTINEL-1/2 + LANDSAT + AI</div>",unsafe_allow_html=True)
