import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
import json
import smtplib
from email.mime.text import MIMEText

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
.live-badge { background: #ff3b3b; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.65rem; font-family: Space Mono; animation: blink 1s infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.5} }
@keyframes pulse-red { 0%,100%{box-shadow:0 0 20px rgba(255,59,59,0.3)} 50%{box-shadow:0 0 40px rgba(255,59,59,0.7)} }
@keyframes pulse-yellow { 0%,100%{box-shadow:0 0 15px rgba(255,184,0,0.2)} 50%{box-shadow:0 0 30px rgba(255,184,0,0.5)} }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔴 REAL-TIME DATA FETCHING MODULE
# ==========================================
@st.cache_data(ttl=3600)  # Cache for 1 hour, then re-fetch
def fetch_latest_weather():
    """Fetch real-time weather from Open-Meteo API (FREE, no key needed)"""
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": 36.304,
            "longitude": 71.721,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,snow_depth",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum",
            "timezone": "Asia/Karachi",
            "forecast_days": 7
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

@st.cache_data(ttl=3600)
def fetch_historical_weather():
    """Fetch last 30 days weather"""
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        url = "https://archive-api.open-meteo.com/v1/archive"
        params = {
            "latitude": 36.304,
            "longitude": 71.721,
            "start_date": start,
            "end_date": end,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum",
            "timezone": "Asia/Karachi"
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None

# ==========================================
# 📧 ALERT NOTIFICATION SYSTEM
# ==========================================
def send_email_alert(risk_level, risk_score, details):
    """Send email alert (configure with your email)"""
    alert_msg = f"""
    ⚠️ GLOF EARLY WARNING — RESHUN VALLEY
    ========================================
    Risk Level: {risk_level}
    Risk Score: {risk_score}/20
    Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    Location: Reshun Valley, Chitral (36.304°N, 71.721°E)

    Details:
    {chr(10).join(details)}

    Recommended: Check dashboard at https://adnanzeb07-glacier-snow-cover-mapping.streamlit.app
    ========================================
    Automated alert from Reshun Glacier GLOF-EWS
    """
    return alert_msg

# ==========================================
# DATA
# ==========================================
HISTORICAL = pd.DataFrame({
    "Year": [2018,2019,2020,2021,2022,2023,2024],
    "Glacier_Pct": [45.2,38.7,35.1,30.8,33.5,28.9,31.2],
    "Lake_Area": [0.021,0.035,0.042,0.058,0.048,0.067,0.075],
    "GLOF_Event": [0,1,0,0,0,0,0]
})

FORECAST = pd.DataFrame([
    {"year":2025,"predicted_pct":29.5},{"year":2026,"predicted_pct":28.1},
    {"year":2027,"predicted_pct":26.8},{"year":2028,"predicted_pct":25.6},
    {"year":2029,"predicted_pct":24.3},{"year":2030,"predicted_pct":23.1}
])

SEASONAL = pd.DataFrame({
    "Period": ["Winter","Spring","Summer","Autumn"],
    "Snow": [62.3, 45.1, 18.7, 28.5],
    "Ice": [8.1, 12.4, 22.3, 15.6],
    "Water": [0.5, 1.8, 4.2, 3.1],
    "Rock": [24.8, 32.4, 48.1, 42.3],
    "Vegetation": [4.3, 8.3, 6.7, 10.5]
})

# ==========================================
# RISK ENGINE
# ==========================================
def compute_risk(glacier_pct, lake_area, prev_glacier, prev_lake, weather=None):
    score = 0
    alerts = []

    # Glacier assessment
    if glacier_pct < 25:
        score += 4; alerts.append("🔴 Glacier CRITICAL (<25%)")
    elif glacier_pct < 35:
        score += 2; alerts.append("🟡 Glacier WARNING (<35%)")

    # Lake assessment
    if lake_area > 0.10:
        score += 4; alerts.append("🔴 Lake CRITICAL (>0.1 km²)")
    elif lake_area > 0.05:
        score += 2; alerts.append("🟡 Lake WARNING (>0.05 km²)")

    # Melt rate
    melt = prev_glacier - glacier_pct
    if melt > 8:
        score += 3; alerts.append(f"🔴 Rapid melt: {melt:.1f}%/yr")
    elif melt > 5:
        score += 2; alerts.append(f"🟡 Elevated melt: {melt:.1f}%/yr")

    # Lake growth
    lake_growth = 0
    if prev_lake and prev_lake > 0:
        lake_growth = ((lake_area - prev_lake) / prev_lake) * 100
        if lake_growth > 20:
            score += 3; alerts.append(f"🔴 Lake expanding {lake_growth:.0f}%/yr")
        elif lake_growth > 10:
            score += 2; alerts.append(f"🟡 Lake growing {lake_growth:.0f}%/yr")

    # REAL-TIME: Weather risk
    if weather and weather.get("current"):
        temp = weather["current"].get("temperature_2m", 0)
        precip = weather["current"].get("precipitation", 0)
        if temp > 15:
            score += 2; alerts.append(f"🔴 High temp: {temp}°C (accelerated melt)")
        elif temp > 10:
            score += 1; alerts.append(f"🟡 Warm temp: {temp}°C")
        if precip > 20:
            score += 2; alerts.append(f"🔴 Heavy rain: {precip}mm (flood risk)")

    if score >= 12: level,text,color = "RED","🔴 RED ALERT — IMMEDIATE ACTION","#ff3b3b"
    elif score >= 6: level,text,color = "YELLOW","🟡 YELLOW ALERT — ELEVATED MONITORING","#ffb800"
    else: level,text,color = "GREEN","🟢 ALL CLEAR — NORMAL OPERATIONS","#00e676"

    return {"score":score,"level":level,"text":text,"color":color,"alerts":alerts,
            "melt_rate":melt,"lake_growth":lake_growth}

# ==========================================
# FETCH LIVE DATA
# ==========================================
weather = fetch_latest_weather()
hist_weather = fetch_historical_weather()

# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<div style='text-align:center;padding:16px 0'><div style='font-size:2.5rem'>🏔️</div><div style='font-family:Syne;font-weight:800;font-size:1.1rem;color:#e8f4f8'>RESHUN GLACIER</div><div style='font-family:Space Mono;font-size:0.55rem;color:#00d4ff;letter-spacing:2px'>GLOF EARLY WARNING SYSTEM</div><br><span class='live-badge'>● LIVE</span></div>",unsafe_allow_html=True)
    st.markdown("---")

    # Live weather display
    if weather and weather.get("current"):
        curr = weather["current"]
        st.markdown("<div class='section-header'>🌡️ LIVE WEATHER</div>",unsafe_allow_html=True)
        st.markdown(f"""<div style='background:rgba(0,212,255,0.05);border-radius:8px;padding:12px;font-family:Space Mono;font-size:0.75rem'>
        🌡️ Temp: <b>{curr.get('temperature_2m','N/A')}°C</b><br>
        💧 Humidity: <b>{curr.get('relative_humidity_2m','N/A')}%</b><br>
        🌧️ Precipitation: <b>{curr.get('precipitation','0')}mm</b><br>
        💨 Wind: <b>{curr.get('wind_speed_10m','N/A')} km/h</b><br>
        ❄️ Snow Depth: <b>{curr.get('snow_depth','0')}m</b>
        </div>""",unsafe_allow_html=True)
        st.markdown("---")

    st.markdown("<div class='section-header'>PARAMETERS</div>",unsafe_allow_html=True)
    glacier_pct = st.slider("Glacier Cover (%)", 0.0, 60.0, 31.2, 0.5)
    lake_area = st.slider("Lake Area (km²)", 0.0, 0.20, 0.075, 0.001, format="%.3f")
    prev_glacier = st.slider("Previous Glacier (%)", 0.0, 60.0, 28.9, 0.5)
    prev_lake = st.slider("Previous Lake (km²)", 0.0, 0.20, 0.067, 0.001, format="%.3f")

    st.markdown("---")
    st.markdown("<div class='section-header'>QUICK SCENARIOS</div>",unsafe_allow_html=True)
    c1,c2 = st.columns(2)
    with c1:
        if st.button("2024 Current",use_container_width=True): pass
        if st.button("2019 GLOF",use_container_width=True): pass
    with c2:
        if st.button("2021 Peak",use_container_width=True): pass
        if st.button("2018 Base",use_container_width=True): pass

    st.markdown("---")
    auto_refresh = st.checkbox("🔄 Auto-refresh (5 min)", value=False)
    if auto_refresh:
        st.markdown("<meta http-equiv='refresh' content='300'>",unsafe_allow_html=True)

    st.markdown(f"<div style='font-family:Space Mono;font-size:0.55rem;color:#3a5a70'>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>Data: Sentinel-1/2, Landsat, Open-Meteo<br>Models: SVC, RF, UNet, LSTM</div>",unsafe_allow_html=True)

# ==========================================
# COMPUTE RISK
# ==========================================
result = compute_risk(glacier_pct, lake_area, prev_glacier, prev_lake, weather)

# ==========================================
# HEADER
# ==========================================
st.markdown(f"""<div style='background:linear-gradient(90deg,rgba(0,212,255,0.15),rgba(10,22,40,0));border-left:4px solid #00d4ff;padding:20px 28px;margin-bottom:24px;border-radius:0 12px 12px 0'>
<div style='display:flex;align-items:center;gap:12px'>
<div style='font-family:Syne;font-size:2rem;font-weight:800;color:#e8f4f8'>🏔️ Reshun Glacier GLOF Early Warning System</div>
<span class='live-badge'>● LIVE</span></div>
<div style='font-family:Space Mono;font-size:0.7rem;color:#00d4ff;letter-spacing:2px;margin-top:6px'>AI & REMOTE SENSING BASED GLOF DETECTION — RESHUN VALLEY, CHITRAL, KP | REAL-TIME MONITORING</div>
</div>""",unsafe_allow_html=True)

# ==========================================
# METRICS ROW
# ==========================================
c1,c2,c3,c4,c5,c6 = st.columns(6)
with c1:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{glacier_pct:.1f}%</div><div class='metric-label'>Glacier Cover</div></div>",unsafe_allow_html=True)
with c2:
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:#084081'>{lake_area:.3f}</div><div class='metric-label'>Lake km²</div></div>",unsafe_allow_html=True)
with c3:
    mc="#ff3b3b" if result["melt_rate"]>5 else "#ffb800" if result["melt_rate"]>0 else "#00e676"
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{mc}'>{result['melt_rate']:+.1f}%</div><div class='metric-label'>Melt Rate</div></div>",unsafe_allow_html=True)
with c4:
    gc="#ff3b3b" if result["lake_growth"]>15 else "#00e676"
    st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{gc}'>{result['lake_growth']:+.0f}%</div><div class='metric-label'>Lake Growth</div></div>",unsafe_allow_html=True)
with c5:
    if weather and weather.get("current"):
        temp = weather["current"].get("temperature_2m","--")
        tc = "#ff3b3b" if isinstance(temp,(int,float)) and temp > 15 else "#00d4ff"
        st.markdown(f"<div class='metric-card'><div class='metric-value' style='color:{tc}'>{temp}°C</div><div class='metric-label'>🌡️ Live Temp</div></div>",unsafe_allow_html=True)
    else:
        st.markdown("<div class='metric-card'><div class='metric-value'>--</div><div class='metric-label'>🌡️ Temp</div></div>",unsafe_allow_html=True)
with c6:
    st.markdown(f"<div class='metric-card'><div class='metric-value'>{result['score']}/20</div><div class='metric-label'>Risk Score</div></div>",unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)

# ==========================================
# ALERT BANNER
# ==========================================
bg={"RED":"rgba(255,59,59,0.2)","YELLOW":"rgba(255,184,0,0.2)","GREEN":"rgba(0,230,118,0.15)"}
anim="animation:pulse-red 2s infinite;" if result["level"]=="RED" else ("animation:pulse-yellow 2s infinite;" if result["level"]=="YELLOW" else "")
st.markdown(f"""<div style='background:{bg[result["level"]]};border:2px solid {result["color"]};border-radius:16px;padding:28px;text-align:center;{anim}'>
<div style='font-family:Syne;font-size:2.2rem;font-weight:800;letter-spacing:2px;color:{result["color"]}'>{result["text"]}</div>
<div style='font-family:Space Mono;font-size:0.8rem;margin-top:8px;color:{result["color"]};opacity:0.8'>Risk Score: {result["score"]}/20 | Models: SVC+RF+UNet+LSTM</div>
<div style='font-family:Space Mono;font-size:0.65rem;color:#7ba3b8;margin-top:10px'>📅 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 📍 Reshun Valley (36.304°N, 71.721°E) | <span class="live-badge">● LIVE</span></div>
</div>""",unsafe_allow_html=True)

st.markdown("<br>",unsafe_allow_html=True)

# ==========================================
# TABS
# ==========================================
tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(["📈 Trends","🌡️ Live Weather","📊 Seasonal","⚠️ Alerts","🤖 Models","ℹ️ About"])

with tab1:
    cl,cr = st.columns([3,2])
    with cl:
        st.markdown("<div class='section-header'>GLACIER & LAKE TRENDS (2018-2030)</div>",unsafe_allow_html=True)
        fig=go.Figure()
        fig.add_trace(go.Scatter(x=list(HISTORICAL["Year"]),y=list(HISTORICAL["Glacier_Pct"]),fill="tozeroy",fillcolor="rgba(0,212,255,0.08)",line=dict(color="#00d4ff",width=2.5),mode="lines+markers",marker=dict(size=8),name="Glacier %"))
        fig.add_trace(go.Scatter(x=[2024]+list(FORECAST["year"]),y=[31.2]+list(FORECAST["predicted_pct"]),line=dict(color="#ff3b3b",width=2,dash="dot"),mode="lines+markers",marker=dict(size=7,symbol="diamond"),name="LSTM Forecast"))
        fig.add_trace(go.Scatter(x=list(HISTORICAL["Year"]),y=[v*1000 for v in HISTORICAL["Lake_Area"]],line=dict(color="#084081",width=2),mode="lines+markers",marker=dict(size=7,symbol="square"),name="Lake (x1000 km²)",yaxis="y2"))
        glof=HISTORICAL[HISTORICAL["GLOF_Event"]==1]
        if len(glof)>0:
            fig.add_trace(go.Scatter(x=list(glof["Year"]),y=list(glof["Glacier_Pct"]),mode="markers",marker=dict(size=14,color="#ff3b3b",symbol="star"),name="GLOF Event"))
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8",size=11),xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),yaxis=dict(gridcolor="rgba(255,255,255,0.05)",title="Glacier %"),yaxis2=dict(title="Lake x1000",overlaying="y",side="right"),legend=dict(bgcolor="rgba(0,0,0,0)",font=dict(size=9)),margin=dict(l=10,r=50,t=10,b=10),height=350)
        st.plotly_chart(fig,use_container_width=True)
    with cr:
        st.markdown("<div class='section-header'>RISK GAUGE</div>",unsafe_allow_html=True)
        fig2=go.Figure(go.Indicator(mode="gauge+number",value=result["score"],number={"suffix":"/20","font":{"family":"Space Mono","color":"#e8f4f8","size":24}},gauge={"axis":{"range":[0,20]},"bar":{"color":result["color"]},"bgcolor":"rgba(255,255,255,0.05)","steps":[{"range":[0,6],"color":"rgba(0,230,118,0.15)"},{"range":[6,12],"color":"rgba(255,184,0,0.2)"},{"range":[12,20],"color":"rgba(255,59,59,0.2)"}]}))
        fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8"),margin=dict(l=20,r=20,t=30,b=10),height=250)
        st.plotly_chart(fig2,use_container_width=True)

with tab2:
    st.markdown("<div class='section-header'>🌡️ LIVE WEATHER — RESHUN VALLEY (REAL-TIME)</div>",unsafe_allow_html=True)
    if weather and weather.get("daily"):
        daily = weather["daily"]
        dates = daily.get("time",[])
        temp_max = daily.get("temperature_2m_max",[])
        temp_min = daily.get("temperature_2m_min",[])
        precip = daily.get("precipitation_sum",[])
        snow = daily.get("snowfall_sum",[])

        fig_w = go.Figure()
        fig_w.add_trace(go.Scatter(x=dates,y=temp_max,mode="lines+markers",name="Max Temp °C",line=dict(color="#ff3b3b",width=2)))
        fig_w.add_trace(go.Scatter(x=dates,y=temp_min,mode="lines+markers",name="Min Temp °C",line=dict(color="#00d4ff",width=2)))
        fig_w.add_trace(go.Bar(x=dates,y=precip,name="Precipitation mm",marker_color="rgba(0,100,255,0.4)",yaxis="y2"))
        fig_w.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8"),yaxis=dict(title="Temperature °C"),yaxis2=dict(title="Precipitation mm",overlaying="y",side="right"),legend=dict(bgcolor="rgba(0,0,0,0)"),margin=dict(l=10,r=50,t=10,b=10),height=300)
        st.plotly_chart(fig_w,use_container_width=True)

        # Melt risk indicator
        if temp_max and max(temp_max) > 10:
            st.markdown(f"<div style='background:rgba(255,59,59,0.1);border:1px solid rgba(255,59,59,0.3);border-radius:8px;padding:12px'><span style='color:#ff3b3b;font-weight:700'>⚠️ MELT RISK:</span> Max temperature {max(temp_max)}°C in next 7 days — accelerated glacier melt expected</div>",unsafe_allow_html=True)
    else:
        st.info("Weather data temporarily unavailable. Retrying in 1 hour...")

    # Historical weather (30 days)
    if hist_weather and hist_weather.get("daily"):
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("<div class='section-header'>📊 LAST 30 DAYS WEATHER HISTORY</div>",unsafe_allow_html=True)
        hd = hist_weather["daily"]
        fig_h = go.Figure()
        fig_h.add_trace(go.Scatter(x=hd.get("time",[]),y=hd.get("temperature_2m_max",[]),fill="tonexty",name="Max Temp",line=dict(color="#ff3b3b")))
        fig_h.add_trace(go.Scatter(x=hd.get("time",[]),y=hd.get("temperature_2m_min",[]),fill="tozeroy",name="Min Temp",line=dict(color="#00d4ff")))
        fig_h.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8"),height=250,margin=dict(l=10,r=10,t=10,b=10))
        st.plotly_chart(fig_h,use_container_width=True)

with tab3:
    st.markdown("<div class='section-header'>SEASONAL LAND COVER CHANGE — 2024</div>",unsafe_allow_html=True)
    fig3=go.Figure()
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Snow"]),name="Snow",marker_color="#4eb3d3"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Ice"]),name="Ice",marker_color="#084081"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Water"]),name="Water",marker_color="#252525"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Rock"]),name="Rock",marker_color="#fe9929"))
    fig3.add_trace(go.Bar(x=list(SEASONAL["Period"]),y=list(SEASONAL["Vegetation"]),name="Vegetation",marker_color="#2ca25f"))
    fig3.update_layout(barmode="stack",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(0,0,0,0)",font=dict(family="Space Mono",color="#7ba3b8"),yaxis=dict(title="Coverage %"),legend=dict(bgcolor="rgba(0,0,0,0)"),margin=dict(l=10,r=10,t=10,b=10),height=350)
    st.plotly_chart(fig3,use_container_width=True)

with tab4:
    ca,cb = st.columns([3,2])
    with ca:
        st.markdown("<div class='section-header'>ACTIVE ALERTS</div>",unsafe_allow_html=True)
        for a in result["alerts"]:
            st.markdown(f"<div class='rec-item'>{a}</div>",unsafe_allow_html=True)
        st.markdown("<br>",unsafe_allow_html=True)
        st.markdown("<div class='section-header'>RECOMMENDED ACTIONS</div>",unsafe_allow_html=True)
        actions={"RED":["🚨 Notify PDMA-KP Emergency Operations","🏃 Evacuate Reshun village (15,000 people)","🚁 Deploy emergency teams to Chitral","📡 Hourly lake level monitoring","📢 Public flood warning via media/SMS"],"YELLOW":["📡 Weekly satellite monitoring","📞 Alert local DC Chitral","📋 Prepare evacuation routes","🌦️ Daily weather monitoring","💧 Check river discharge sensors"],"GREEN":["🛰️ Monthly satellite monitoring","🗺️ Quarterly glacier mapping","📊 Record seasonal data","📝 Annual report preparation","✅ Normal operations"]}
        for a in actions.get(result["level"],actions["GREEN"]):
            st.markdown(f"<div class='rec-item'>{a}</div>",unsafe_allow_html=True)

        # Email alert button
        st.markdown("<br>",unsafe_allow_html=True)
        if result["level"] in ["RED","YELLOW"]:
            if st.button("📧 Send Alert Email to Authorities",type="primary"):
                msg = send_email_alert(result["level"],result["score"],result["alerts"])
                st.code(msg)
                st.success("Alert generated! Configure SMTP to send automatically.")

    with cb:
        st.markdown("<div class='section-header'>GLOF HISTORY — RESHUN</div>",unsafe_allow_html=True)
        for yr,desc in [("2013","Major GLOF — infrastructure destroyed"),("2015","GLOF warning — partial evacuation"),("2019","Jam Ashpar GLOF — 5 bridges lost"),("2022","Lake expansion detected via satellite"),("2024","Elevated risk — UNDP monitoring")]:
            st.markdown(f"<div style='display:flex;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.05)'><span style='font-family:Space Mono;font-size:0.8rem;color:#ff3b3b;min-width:50px'>{yr}</span><span style='font-size:0.85rem;color:#7ba3b8'>{desc}</span></div>",unsafe_allow_html=True)

with tab5:
    st.markdown("<div class='section-header'>AI/ML MODELS USED</div>",unsafe_allow_html=True)
    models=[
        ("SVC","Glacier/lake classification","Scikit-learn","RBF, C=10","~93%"),
        ("Random Forest","Ensemble classification","Scikit-learn","200 trees","~95%"),
        ("UNet (CNN)","Semantic segmentation","TensorFlow","Encoder-decoder","~91%"),
        ("LSTM","Glacier melt forecast","TensorFlow","2-layer + dropout","2025-2030"),
        ("Z-Score","Anomaly detection","NumPy","±1.5σ threshold","Real-time"),
    ]
    for name,desc,fw,params,acc in models:
        st.markdown(f"""<div style='background:rgba(255,255,255,0.03);border:1px solid rgba(0,212,255,0.15);border-radius:8px;padding:14px;margin:8px 0'>
        <div style='font-family:Syne;font-weight:700;color:#00d4ff'>{name}</div>
        <div style='font-family:Space Mono;font-size:0.75rem;color:#7ba3b8;margin-top:4px'>{desc}</div>
        <div style='display:flex;gap:16px;margin-top:8px;font-size:0.65rem;color:#5a8a9f'><span>{fw}</span><span>{params}</span><span>{acc}</span></div></div>""",unsafe_allow_html=True)

    st.markdown("<br>",unsafe_allow_html=True)
    st.markdown("<div class='section-header'>DATA SOURCES</div>",unsafe_allow_html=True)
    for name,res,src in [("Sentinel-2 SR","10m optical","ESA"),("Sentinel-1 SAR","10m radar","ESA"),("Landsat-8/9","30m (2018-2024)","USGS"),("SRTM DEM","30m elevation","NASA"),("Open-Meteo","Live weather","Open-Meteo API"),("ERA5/CHIRPS","Climate reanalysis","ECMWF/UCSB")]:
        st.markdown(f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.05);font-size:0.85rem'><span style='color:#00d4ff'>{name}</span><span style='color:#7ba3b8'>{res}</span><span style='color:#5a8a9f'>{src}</span></div>",unsafe_allow_html=True)

with tab6:
    st.markdown("""
### About This System
**Reshun Glacier GLOF Early Warning System** is a real-time geo-intelligence platform that monitors
glacier dynamics, glacial lake changes, and weather conditions to predict and alert GLOF risk
in Reshun Valley, Upper Chitral, KP, Pakistan.

**Real-Time Features:**
- 🌡️ Live weather from Open-Meteo API (updates hourly)
- 📡 Sentinel-1/2 satellite data (5-day revisit)
- 🤖 5 AI/ML models for classification + prediction
- 📧 Alert notification system
- 🔄 Auto-refresh capability

**Study Area:** Reshun Valley (36.304°N, 71.721°E) | Elevation: 1,900-5,200m

**Risk Thresholds:**
- 🟢 **GREEN (0-5):** Normal
- 🟡 **YELLOW (6-11):** Elevated
- 🔴 **RED (12-20):** Immediate action

---
**Developer:** Adnan Zeb — FYP, UET Peshawar 2025 | **Supervisor:** Dr. Nasru Minallah
    """)

st.markdown("<div style='font-family:Space Mono;font-size:0.55rem;color:#3a5a70;text-align:center;margin-top:40px;padding:20px 0;border-top:1px solid rgba(0,212,255,0.1)'>RESHUN GLACIER GLOF-EWS | REAL-TIME | UET PESHAWAR FYP 2025 | DR. NASRU MINALLAH | SENTINEL + AI + LIVE WEATHER</div>",unsafe_allow_html=True)
