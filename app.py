Dashboard both stations · PY
Copy

"""
S&L Cold Storage - Warehouse Monitoring Dashboard
Real-time ethylene, temperature, and humidity monitoring

UPDATED: Both Station 1 and Station 2 with full sensor suites
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
import json
import time

# Page configuration
st.set_page_config(
    page_title="S&L Cold Storage Monitor",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0a1628 0%, #1a2d4a 100%);
    }
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%);
        border: 1px solid #00b4d8;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 15px rgba(0, 180, 216, 0.2);
    }
    div[data-testid="metric-container"] label { color: #a0a0a0 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { 
        color: #ffffff !important; 
        font-size: 2rem !important; 
    }
    h1, h2, h3 { color: #00b4d8 !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #90e0ef;
        border-radius: 4px 4px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e3a5f;
        color: #00b4d8;
    }
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d2137 0%, #0a1628 100%);
        border-right: 1px solid #00b4d8;
    }
    .alert-box {
        background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
        border-radius: 10px; padding: 15px; margin: 10px 0;
        color: white; font-weight: bold;
    }
    .warning-box {
        background: linear-gradient(135deg, #ffaa00 0%, #cc8800 100%);
        border-radius: 10px; padding: 15px; margin: 10px 0;
        color: white; font-weight: bold;
    }
    .normal-box {
        background: linear-gradient(135deg, #00cc66 0%, #009944 100%);
        border-radius: 10px; padding: 15px; margin: 10px 0;
        color: white; font-weight: bold;
    }
    .footer { text-align: center; color: #666; padding: 20px; font-size: 0.8rem; }
    
    /* Hide the running indicator */
    .stStatusWidget { display: none; }
    div[data-testid="stStatusWidget"] { display: none; }
</style>
""", unsafe_allow_html=True)

# Thresholds
ETHYLENE_THRESHOLDS = {'optimal_min': 0.1, 'optimal_max': 1.0, 'warning': 5.0, 'critical': 10.0}
TEMP_THRESHOLDS = {'min': 25, 'max': 45, 'optimal_min': 30, 'optimal_max': 40}


def get_ethylene_status(ppm):
    if ppm is None or pd.isna(ppm): return "Unknown", "gray"
    try:
        ppm = float(ppm)
        if ppm < ETHYLENE_THRESHOLDS['optimal_min']: return "Low", "#00b4d8"
        elif ppm <= ETHYLENE_THRESHOLDS['optimal_max']: return "Optimal", "#00ff88"
        elif ppm <= ETHYLENE_THRESHOLDS['warning']: return "Elevated", "#ffaa00"
        elif ppm <= ETHYLENE_THRESHOLDS['critical']: return "Warning", "#ff6600"
        else: return "Critical", "#ff0000"
    except (ValueError, TypeError):
        return "Unknown", "gray"


def get_temp_status(temp_f):
    if temp_f is None: return "Unknown", "gray"
    if temp_f < TEMP_THRESHOLDS['min']: return "Too Cold", "#00b4d8"
    elif temp_f > TEMP_THRESHOLDS['max']: return "Too Warm", "#ff4444"
    elif TEMP_THRESHOLDS['optimal_min'] <= temp_f <= TEMP_THRESHOLDS['optimal_max']: return "Optimal", "#00ff88"
    else: return "Acceptable", "#ffaa00"


def celsius_to_fahrenheit(celsius):
    if celsius is None: return None
    return (celsius * 9/5) + 32


def create_gauge_chart(value, title, min_val, max_val, thresholds, unit=""):
    if value is None: value = 0
    
    if len(thresholds) >= 3:
        if value < thresholds[0]: color = "#00b4d8"
        elif value < thresholds[1]: color = "#00ff88"
        elif value < thresholds[2]: color = "#ffaa00"
        else: color = "#ff4444"
    else:
        color = "#00ff88"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'color': '#ffffff'}},
        number={'suffix': unit, 'font': {'size': 24, 'color': '#ffffff'}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': '#ffffff', 'tickfont': {'color': '#ffffff'}},
            'bar': {'color': color},
            'bgcolor': '#0a1628',
            'borderwidth': 2,
            'bordercolor': '#1e3a5f',
            'steps': [
                {'range': [min_val, thresholds[0] if thresholds else max_val*0.33], 'color': 'rgba(0, 180, 216, 0.3)'},
                {'range': [thresholds[0] if thresholds else max_val*0.33, thresholds[1] if len(thresholds)>1 else max_val*0.66], 'color': 'rgba(0, 255, 136, 0.3)'},
                {'range': [thresholds[1] if len(thresholds)>1 else max_val*0.66, thresholds[2] if len(thresholds)>2 else max_val], 'color': 'rgba(255, 170, 0, 0.3)'},
            ],
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'}, height=200, margin=dict(l=20, r=20, t=40, b=20)
    )
    return fig


def create_time_series_chart(df, y_column, title, color, y_label):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    else:
        fig = px.line(df, x='timestamp', y=y_column, title=title, color_discrete_sequence=[color])
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10,22,40,0.8)',
        font={'color': '#ffffff'},
        xaxis={'gridcolor': '#1e3a5f', 'title': 'Time'},
        yaxis={'gridcolor': '#1e3a5f', 'title': y_label},
        height=300, margin=dict(l=50, r=20, t=50, b=50), showlegend=False
    )
    return fig


def create_multi_station_chart(df, y_column, title, y_label):
    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    else:
        fig = px.line(df, x='timestamp', y=y_column, color='station', title=title,
            color_discrete_map={'station1-raspberry-pi': '#00b4d8', 'station2': '#00ff88'})
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10,22,40,0.8)',
        font={'color': '#ffffff'},
        xaxis={'gridcolor': '#1e3a5f', 'title': 'Time'},
        yaxis={'gridcolor': '#1e3a5f', 'title': y_label},
        height=350, margin=dict(l=50, r=20, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


@st.cache_data(ttl=10)
def fetch_table_storage_data(connection_string, table_name, hours_back=2):
    """Fetch sensor data from Azure Table Storage"""
    try:
        from azure.data.tables import TableClient
        from datetime import datetime, timedelta, timezone
        
        table_client = TableClient.from_connection_string(connection_string, table_name)
        
        # Calculate time filter
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        time_filter = time_threshold.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Query entities
        entities = table_client.query_entities(
            query_filter=f"timestamp ge '{time_filter}'",
            select=['PartitionKey', 'timestamp', 'temperature', 'humidity', 'ethylene', 'wifi_rssi', 'uptime']
        )
        
        data = []
        for entity in entities:
            try:
                ts = entity.get('timestamp', '')
                if isinstance(ts, str):
                    timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                else:
                    timestamp = ts
                
                # Clean ethylene data - handle NaN/null values
                ethylene_raw = entity.get('ethylene')
                if ethylene_raw is None or pd.isna(ethylene_raw):
                    ethylene_clean = 0.0
                else:
                    try:
                        ethylene_clean = float(ethylene_raw)
                    except (ValueError, TypeError):
                        ethylene_clean = 0.0
                
                data.append({
                    'station': entity.get('PartitionKey', 'unknown'),
                    'timestamp': timestamp,
                    'temperature': float(entity['temperature']) if entity.get('temperature') else None,
                    'humidity': float(entity['humidity']) if entity.get('humidity') else None,
                    'ethylene': ethylene_clean,
                    'wifi_rssi': int(entity['wifi_rssi']) if entity.get('wifi_rssi') else None,
                    'uptime': int(entity['uptime']) if entity.get('uptime') else None
                })
            except Exception as e:
                continue
        
        return data, "Connected to Azure", len(data)
        
    except ImportError:
        return [], "Azure SDK not installed", 0
    except Exception as e:
        return [], f"Error: {str(e)[:50]}", 0


def generate_demo_data():
    """Generate demo data"""
    import random
    data = []
    current_time = datetime.now(timezone.utc)
    
    for i in range(120, 0, -1):
        timestamp = current_time - timedelta(seconds=i * 30)
        data.append({
            'station': 'station1-raspberry-pi',
            'timestamp': timestamp,
            'temperature': 22.0 + random.uniform(-1, 1),
            'humidity': 55.0 + random.uniform(-3, 3),
            'ethylene': 0.3 + random.uniform(-0.1, 0.2)
        })
        data.append({
            'station': 'station2',
            'timestamp': timestamp,
            'temperature': 21.5 + random.uniform(-1, 1),
            'humidity': 52.0 + random.uniform(-3, 3),
            'ethylene': 0.8 + random.uniform(-0.2, 0.3)
        })
    
    return data


# ============================================================================
# MAIN APPLICATION
# ============================================================================

# Header
st.markdown("""
<div style='text-align: center; padding: 20px 0;'>
    <h1 style='font-size: 3rem; margin-bottom: 0; background: linear-gradient(90deg, #00b4d8, #90e0ef); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
        ❄️ S&L Cold Storage
    </h1>
    <p style='color: #90e0ef; font-size: 1.2rem; margin-top: 5px;'>
        Warehouse Monitoring System
    </p>
</div>
""", unsafe_allow_html=True)

# Check for Azure secrets
has_azure_secrets = False
connection_string = None
table_name = "sensordata"

try:
    if 'azure' in st.secrets:
        connection_string = st.secrets['azure'].get('storage_connection_string')
        table_name = st.secrets['azure'].get('table_name', 'sensordata')
        if connection_string:
            has_azure_secrets = True
except Exception:
    pass

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    if has_azure_secrets:
        demo_mode = st.checkbox("Demo Mode", value=False, help="Use simulated data")
    else:
        st.warning("⚠️ Azure secrets not configured. Using demo mode.")
        demo_mode = True
    
    st.markdown("---")
    st.markdown("### 🔄 Refresh")
    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Interval (seconds)", 5, 60, 15)
    
    hours_back = st.slider("History (hours)", 1, 24, 2)
    
    st.markdown("---")
    st.markdown("### 🎯 Thresholds")
    with st.expander("Ethylene (ppm)"):
        eth_warn = st.number_input("Warning", value=5.0, step=0.5, key="eth_warn")
        eth_crit = st.number_input("Critical", value=10.0, step=0.5, key="eth_crit")
    with st.expander("Temperature (°F)"):
        temp_min = st.number_input("Minimum", value=25.0, step=1.0, key="temp_min")
        temp_max = st.number_input("Maximum", value=45.0, step=1.0, key="temp_max")

# Fetch data
if demo_mode:
    sensor_data = generate_demo_data()
    connection_status = "Demo Mode"
    messages_count = len(sensor_data)
else:
    sensor_data, connection_status, messages_count = fetch_table_storage_data(
        connection_string, table_name, hours_back
    )
    if not sensor_data:
        st.warning("No data from Azure. Using demo data...")
        sensor_data = generate_demo_data()
        connection_status = "Demo (No Azure Data)"

# Convert to DataFrame
df = pd.DataFrame(sensor_data)
if not df.empty and 'timestamp' in df.columns:
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')

last_update = datetime.now().strftime("%H:%M:%S")

# Sidebar info
with st.sidebar:
    st.markdown("---")
    st.markdown("### 📊 Status")
    status_icon = "🟢" if "Connected" in connection_status else "🟡" if "Demo" in connection_status else "🔴"
    st.markdown(f"{status_icon} **{connection_status}**")
    st.markdown(f"📊 **{messages_count}** readings")
    st.markdown(f"🕐 **{last_update}**")

# Get latest readings per station
latest_station1 = None
latest_station2 = None

if not df.empty:
    for station in df['station'].unique():
        station_df = df[df['station'] == station].sort_values('timestamp', ascending=False)
        if not station_df.empty:
            latest = station_df.iloc[0].to_dict()
            if 'station1' in station.lower() or 'raspberry' in station.lower():
                latest_station1 = latest
            elif 'station2' in station.lower():
                latest_station2 = latest

# Status bar
st.markdown(f"""
<div style='background: rgba(30, 58, 95, 0.5); border-radius: 10px; padding: 15px; margin-bottom: 20px; text-align: center; border: 1px solid #00b4d8;'>
    <span style='font-size: 1.2rem;'>
        {"🟢" if "Connected" in connection_status else "🟡"} <strong>{connection_status}</strong> | 
        📊 <strong>{messages_count}</strong> readings | 
        🕐 Last update: <strong>{last_update}</strong>
    </span>
</div>
""", unsafe_allow_html=True)

# Station Overview
st.markdown("## 📍 Station Overview")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏭 Station 1")
    st.caption("Full Sensor Suite")
    
    if latest_station1:
        temp_c = latest_station1.get('temperature')
        temp_f = celsius_to_fahrenheit(temp_c) if temp_c else None
        humidity = latest_station1.get('humidity')
        ethylene = latest_station1.get('ethylene')
        
        # Clean ethylene data
        if pd.isna(ethylene) or ethylene is None:
            ethylene = 0.0
        
        m1, m2, m3 = st.columns(3)
        with m1:
            temp_status, temp_color = get_temp_status(temp_f)
            st.metric("🌡️ Room Temp", f"{temp_f:.1f}°F" if temp_f else "N/A", f"{temp_c:.1f}°C" if temp_c else None)
            if temp_f:
                st.markdown(f"<small style='color:{temp_color}'>{temp_status}</small>", unsafe_allow_html=True)
        with m2:
            if humidity is not None:
                st.metric("💧 Humidity", f"{humidity:.1f}%")
            else:
                st.metric("💧 Humidity", "N/A")
        with m3:
            eth_status, eth_color = get_ethylene_status(ethylene)
            if ethylene is not None and not pd.isna(ethylene):
                st.metric("🍃 Ethylene", f"{ethylene:.2f} ppm")
                st.markdown(f"<small style='color:{eth_color}'>{eth_status}</small>", unsafe_allow_html=True)
            else:
                st.metric("🍃 Ethylene", "0.00 ppm")
                st.markdown(f"<small style='color:#00b4d8'>Low</small>", unsafe_allow_html=True)
    else:
        st.info("Waiting for data from Station 1...")

with col2:
    st.markdown("### 🏭 Station 2")
    st.caption("Full Sensor Suite")
    
    if latest_station2:
        temp_c = latest_station2.get('temperature')
        temp_f = celsius_to_fahrenheit(temp_c) if temp_c else None
        humidity = latest_station2.get('humidity')
        ethylene = latest_station2.get('ethylene')
        
        # Clean ethylene data
        if pd.isna(ethylene) or ethylene is None:
            ethylene = 0.0
        
        m1, m2, m3 = st.columns(3)
        with m1:
            temp_status, temp_color = get_temp_status(temp_f)
            st.metric("🌡️ Room Temp", f"{temp_f:.1f}°F" if temp_f else "N/A", f"{temp_c:.1f}°C" if temp_c else None)
            if temp_f:
                st.markdown(f"<small style='color:{temp_color}'>{temp_status}</small>", unsafe_allow_html=True)
        with m2:
            if humidity is not None:
                st.metric("💧 Humidity", f"{humidity:.1f}%")
            else:
                st.metric("💧 Humidity", "N/A")
        with m3:
            eth_status, eth_color = get_ethylene_status(ethylene)
            if ethylene is not None and not pd.isna(ethylene):
                st.metric("🍃 Ethylene", f"{ethylene:.2f} ppm")
                st.markdown(f"<small style='color:{eth_color}'>{eth_status}</small>", unsafe_allow_html=True)
            else:
                st.metric("🍃 Ethylene", "0.00 ppm")
                st.markdown(f"<small style='color:#00b4d8'>Low</small>", unsafe_allow_html=True)
    else:
        st.info("Waiting for data from Station 2...")

st.markdown("---")

# Gauge Charts
st.markdown("## 📊 Real-Time Gauges")

# Station 1 gauges
st.markdown("### 🏭 Station 1")
temp_f_s1 = celsius_to_fahrenheit(latest_station1.get('temperature')) if latest_station1 and latest_station1.get('temperature') else 0
humidity_s1 = latest_station1.get('humidity') if latest_station1 and latest_station1.get('humidity') else 0
eth1_raw = latest_station1.get('ethylene') if latest_station1 else None
eth1 = 0.0 if eth1_raw is None or pd.isna(eth1_raw) else float(eth1_raw)

g1, g2, g3 = st.columns(3)
with g1:
    st.plotly_chart(create_gauge_chart(temp_f_s1, "Temperature", 0, 100, [32, 50, 70], "°F"), use_container_width=True, key="gauge_s1_temp")
with g2:
    st.plotly_chart(create_gauge_chart(humidity_s1, "Humidity", 0, 100, [30, 60, 80], "%"), use_container_width=True, key="gauge_s1_hum")
with g3:
    st.plotly_chart(create_gauge_chart(eth1, "Ethylene", 0, 15, [1, 5, 10], " ppm"), use_container_width=True, key="gauge_s1_eth")

# Station 2 gauges
st.markdown("### 🏭 Station 2")
temp_f_s2 = celsius_to_fahrenheit(latest_station2.get('temperature')) if latest_station2 and latest_station2.get('temperature') else 0
humidity_s2 = latest_station2.get('humidity') if latest_station2 and latest_station2.get('humidity') else 0
eth2_raw = latest_station2.get('ethylene') if latest_station2 else None
eth2 = 0.0 if eth2_raw is None or pd.isna(eth2_raw) else float(eth2_raw)

g4, g5, g6 = st.columns(3)
with g4:
    st.plotly_chart(create_gauge_chart(temp_f_s2, "Temperature", 0, 100, [32, 50, 70], "°F"), use_container_width=True, key="gauge_s2_temp")
with g5:
    st.plotly_chart(create_gauge_chart(humidity_s2, "Humidity", 0, 100, [30, 60, 80], "%"), use_container_width=True, key="gauge_s2_hum")
with g6:
    st.plotly_chart(create_gauge_chart(eth2, "Ethylene", 0, 15, [1, 5, 10], " ppm"), use_container_width=True, key="gauge_s2_eth")

st.markdown("---")

# Historical Charts
st.markdown("## 📈 Historical Trends")

if not df.empty:
    # Ethylene chart (both stations)
    st.markdown("### 🍃 Ethylene Levels - Both Stations")
    eth_df = df[df['ethylene'].notna()].copy()
    if not eth_df.empty:
        fig = create_multi_station_chart(eth_df, 'ethylene', 'Ethylene Comparison', 'ppm')
        fig.add_hline(y=5.0, line_dash="dash", line_color="#ffaa00", annotation_text="Warning")
        fig.add_hline(y=10.0, line_dash="dash", line_color="#ff4444", annotation_text="Critical")
        st.plotly_chart(fig, use_container_width=True, key="chart_ethylene_history")
    
    # Temperature comparison (both stations)
    st.markdown("### 🌡️ Temperature - Both Stations")
    temp_df = df[df['temperature'].notna()].copy()
    if not temp_df.empty:
        temp_df['temp_f'] = temp_df['temperature'].apply(celsius_to_fahrenheit)
        fig = create_multi_station_chart(temp_df, 'temp_f', 'Temperature Comparison', '°F')
        st.plotly_chart(fig, use_container_width=True, key="chart_temp_history")
    
    # Humidity comparison (both stations)
    st.markdown("### 💧 Humidity - Both Stations")
    hum_df = df[df['humidity'].notna()].copy()
    if not hum_df.empty:
        fig = create_multi_station_chart(hum_df, 'humidity', 'Humidity Comparison', '%')
        st.plotly_chart(fig, use_container_width=True, key="chart_humidity_history")

st.markdown("---")

# Alerts
st.markdown("## 🚨 Active Alerts")
alerts = []

if latest_station1:
    temp_f = celsius_to_fahrenheit(latest_station1.get('temperature'))
    if temp_f and (temp_f < 25 or temp_f > 45):
        alerts.append(("critical", f"Station 1 Temperature: {temp_f:.1f}°F out of range!"))
    eth = latest_station1.get('ethylene')
    if eth and eth > 10:
        alerts.append(("critical", f"Station 1 Ethylene: {eth:.2f} ppm CRITICAL!"))
    elif eth and eth > 5:
        alerts.append(("warning", f"Station 1 Ethylene: {eth:.2f} ppm elevated"))

if latest_station2:
    temp_f = celsius_to_fahrenheit(latest_station2.get('temperature'))
    if temp_f and (temp_f < 25 or temp_f > 45):
        alerts.append(("critical", f"Station 2 Temperature: {temp_f:.1f}°F out of range!"))
    eth = latest_station2.get('ethylene')
    if eth and eth > 10:
        alerts.append(("critical", f"Station 2 Ethylene: {eth:.2f} ppm CRITICAL!"))
    elif eth and eth > 5:
        alerts.append(("warning", f"Station 2 Ethylene: {eth:.2f} ppm elevated"))

if alerts:
    for alert_type, message in alerts:
        box_class = "alert-box" if alert_type == "critical" else "warning-box"
        icon = "🚨 CRITICAL:" if alert_type == "critical" else "⚠️ WARNING:"
        st.markdown(f'<div class="{box_class}">{icon} {message}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-box">✅ All systems operating normally</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p><strong>S&L Cold Storage</strong> - Warehouse Monitoring System v2.1</p>
    <p>Powered by Azure Table Storage | Built with Streamlit</p>
    <p>Station 1 & Station 2 - Full Sensor Suites</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh with fragment to reduce "Running..." visibility
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
