"""
S&L Cold Storage - Warehouse Monitoring Dashboard
Real-time ethylene, temperature, and humidity monitoring for fruit storage facilities

Connects to Azure IoT Hub via Event Hub-compatible endpoint
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from collections import deque
import json
import time
import threading

# Page configuration - MUST BE FIRST
st.set_page_config(
    page_title="S&L Cold Storage Monitor",
    page_icon="❄️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for professional styling
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
    
    div[data-testid="metric-container"] label {
        color: #a0a0a0 !important;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-size: 2rem !important;
    }
    
    h1, h2, h3 {
        color: #00b4d8 !important;
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0d2137 0%, #0a1628 100%);
        border-right: 1px solid #00b4d8;
    }
    
    .alert-box {
        background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
        font-weight: bold;
    }
    
    .warning-box {
        background: linear-gradient(135deg, #ffaa00 0%, #cc8800 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
        font-weight: bold;
    }
    
    .normal-box {
        background: linear-gradient(135deg, #00cc66 0%, #009944 100%);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        color: white;
        font-weight: bold;
    }
    
    .footer {
        text-align: center;
        color: #666;
        padding: 20px;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'sensor_data' not in st.session_state:
    st.session_state.sensor_data = deque(maxlen=2000)
    st.session_state.last_update = None
    st.session_state.connection_status = "Initializing..."
    st.session_state.messages_received = 0
    st.session_state.azure_consumer = None
    st.session_state.receiving_thread = None

# Thresholds
ETHYLENE_THRESHOLDS = {'optimal_min': 0.1, 'optimal_max': 1.0, 'warning': 5.0, 'critical': 10.0}
TEMP_THRESHOLDS = {'min': 25, 'max': 45, 'optimal_min': 30, 'optimal_max': 40}


def get_ethylene_status(ppm):
    if ppm is None:
        return "Unknown", "gray"
    if ppm < ETHYLENE_THRESHOLDS['optimal_min']:
        return "Low", "#00b4d8"
    elif ppm <= ETHYLENE_THRESHOLDS['optimal_max']:
        return "Optimal", "#00ff88"
    elif ppm <= ETHYLENE_THRESHOLDS['warning']:
        return "Elevated", "#ffaa00"
    elif ppm <= ETHYLENE_THRESHOLDS['critical']:
        return "Warning", "#ff6600"
    else:
        return "Critical", "#ff0000"


def get_temp_status(temp_f):
    if temp_f is None:
        return "Unknown", "gray"
    if temp_f < TEMP_THRESHOLDS['min']:
        return "Too Cold", "#00b4d8"
    elif temp_f > TEMP_THRESHOLDS['max']:
        return "Too Warm", "#ff4444"
    elif TEMP_THRESHOLDS['optimal_min'] <= temp_f <= TEMP_THRESHOLDS['optimal_max']:
        return "Optimal", "#00ff88"
    else:
        return "Acceptable", "#ffaa00"


def celsius_to_fahrenheit(celsius):
    if celsius is None:
        return None
    return (celsius * 9/5) + 32


def create_gauge_chart(value, title, min_val, max_val, thresholds, unit=""):
    if value is None:
        value = 0
    
    if len(thresholds) >= 3:
        if value < thresholds[0]:
            color = "#00b4d8"
        elif value < thresholds[1]:
            color = "#00ff88"
        elif value < thresholds[2]:
            color = "#ffaa00"
        else:
            color = "#ff4444"
    else:
        color = "#00ff88"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
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
                {'range': [min_val, thresholds[0] if len(thresholds) > 0 else max_val * 0.33], 'color': 'rgba(0, 180, 216, 0.3)'},
                {'range': [thresholds[0] if len(thresholds) > 0 else max_val * 0.33, thresholds[1] if len(thresholds) > 1 else max_val * 0.66], 'color': 'rgba(0, 255, 136, 0.3)'},
                {'range': [thresholds[1] if len(thresholds) > 1 else max_val * 0.66, thresholds[2] if len(thresholds) > 2 else max_val], 'color': 'rgba(255, 170, 0, 0.3)'},
            ],
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#ffffff'},
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_multi_station_chart(df, y_column, title, y_label):
    import plotly.express as px
    fig = px.line(
        df, 
        x='timestamp', 
        y=y_column,
        color='device_id',
        title=title,
        color_discrete_map={
            'station1': '#00b4d8',
            'station2': '#00ff88',
            'Station1': '#00b4d8',
            'Station2': '#00ff88'
        }
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,22,40,0.8)',
        font={'color': '#ffffff'},
        xaxis={'gridcolor': '#1e3a5f', 'title': 'Time'},
        yaxis={'gridcolor': '#1e3a5f', 'title': y_label},
        height=350,
        margin=dict(l=50, r=20, t=50, b=50),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig


def create_time_series_chart(df, y_column, title, color, y_label):
    import plotly.express as px
    fig = px.line(df, x='timestamp', y=y_column, title=title, color_discrete_sequence=[color])
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,22,40,0.8)',
        font={'color': '#ffffff'},
        xaxis={'gridcolor': '#1e3a5f', 'title': 'Time'},
        yaxis={'gridcolor': '#1e3a5f', 'title': y_label},
        height=300,
        margin=dict(l=50, r=20, t=50, b=50),
        showlegend=False
    )
    
    return fig


def generate_demo_data():
    """Generate demo data for testing"""
    import random
    current_time = datetime.now()
    
    data = []
    data.append({
        'timestamp': current_time,
        'device_id': 'station1',
        'temperature_c': 2.5 + random.uniform(-0.5, 0.5),
        'humidity': 46 + random.uniform(-2, 2),
        'ethylene_ppm': 0.5 + random.uniform(-0.2, 0.3)
    })
    data.append({
        'timestamp': current_time,
        'device_id': 'station2',
        'temperature_c': None,
        'humidity': None,
        'ethylene_ppm': 0.3 + random.uniform(-0.1, 0.2)
    })
    
    return data


def load_historical_demo_data():
    """Load historical demo data for charts"""
    import random
    
    data = []
    current_time = datetime.now()
    
    for i in range(240, 0, -1):
        timestamp = current_time - timedelta(seconds=i * 30)
        
        data.append({
            'timestamp': timestamp,
            'device_id': 'station1',
            'temperature_c': 2.5 + random.uniform(-1, 1),
            'humidity': 46 + random.uniform(-3, 3),
            'ethylene_ppm': 0.5 + random.uniform(-0.2, 0.5)
        })
        
        data.append({
            'timestamp': timestamp,
            'device_id': 'station2',
            'temperature_c': None,
            'humidity': None,
            'ethylene_ppm': 0.3 + random.uniform(-0.15, 0.4)
        })
    
    return pd.DataFrame(data)


def start_azure_consumer(connection_string, consumer_group):
    """Start Azure Event Hub consumer in background thread"""
    try:
        from azure.eventhub import EventHubConsumerClient
        
        def on_event(partition_context, event):
            try:
                body = event.body_as_str()
                data = json.loads(body)
                
                # Get device ID
                device_id = None
                if event.system_properties:
                    device_id = event.system_properties.get(b'iothub-connection-device-id')
                    if device_id:
                        device_id = device_id.decode('utf-8') if isinstance(device_id, bytes) else str(device_id)
                
                if not device_id:
                    device_id = data.get('deviceId', data.get('device_id', 'unknown'))
                
                # Parse sensor data
                reading = {
                    'timestamp': datetime.now(),
                    'device_id': device_id,
                    'temperature_c': data.get('temperature_c') or data.get('temperature'),
                    'humidity': data.get('humidity'),
                    'ethylene_ppm': data.get('ethylene_ppm') or data.get('ethylene')
                }
                
                # Apply decimal correction for ZE03 sensor if needed
                if reading['ethylene_ppm'] and reading['ethylene_ppm'] > 100:
                    reading['ethylene_ppm'] = reading['ethylene_ppm'] / 10.0
                
                st.session_state.sensor_data.append(reading)
                st.session_state.messages_received += 1
                st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                partition_context.update_checkpoint(event)
                
            except Exception as e:
                print(f"Error processing event: {e}")
        
        def on_error(partition_context, error):
            print(f"Error: {error}")
        
        client = EventHubConsumerClient.from_connection_string(
            conn_str=connection_string,
            consumer_group=consumer_group
        )
        
        st.session_state.azure_consumer = client
        st.session_state.connection_status = "Connected to Azure"
        
        # Start receiving
        client.receive(
            on_event=on_event,
            on_error=on_error,
            starting_position="-1"  # Start from latest
        )
        
    except ImportError:
        st.session_state.connection_status = "Azure SDK not installed"
    except Exception as e:
        st.session_state.connection_status = f"Connection error: {str(e)[:50]}"


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

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    
    # Check for secrets
    has_azure_secrets = False
    try:
        if 'azure' in st.secrets and 'eventhub_connection_string' in st.secrets['azure']:
            has_azure_secrets = True
    except:
        pass
    
    # Connection mode
    if has_azure_secrets:
        demo_mode = st.checkbox("Demo Mode", value=False, help="Use simulated data instead of real Azure data")
    else:
        demo_mode = st.checkbox("Demo Mode", value=True, help="Azure secrets not configured - using demo data")
        if not demo_mode:
            st.warning("⚠️ Azure secrets not configured. Please add secrets in Streamlit Cloud settings.")
            demo_mode = True
    
    st.markdown("---")
    
    st.markdown("### 🔄 Refresh Settings")
    auto_refresh = st.checkbox("Auto Refresh", value=True)
    refresh_interval = st.slider("Refresh Interval (seconds)", 5, 60, 10)
    
    st.markdown("---")
    
    st.markdown("### 🎯 Alert Thresholds")
    with st.expander("Ethylene (ppm)"):
        eth_warning = st.number_input("Warning Level", value=5.0, step=0.5)
        eth_critical = st.number_input("Critical Level", value=10.0, step=0.5)
    
    with st.expander("Temperature (°F)"):
        temp_min = st.number_input("Minimum", value=25.0, step=1.0)
        temp_max = st.number_input("Maximum", value=45.0, step=1.0)
    
    st.markdown("---")
    
    st.markdown("### 📊 System Info")
    mode_text = "Demo Mode" if demo_mode else "Live Azure Data"
    st.markdown(f"""
    - **Mode:** {mode_text}
    - **Messages:** {st.session_state.messages_received}
    - **Last Update:** {st.session_state.last_update or 'N/A'}
    - **Buffer:** {len(st.session_state.sensor_data)} readings
    """)

# Data handling
if demo_mode:
    # Demo mode - generate fake data
    new_data = generate_demo_data()
    for reading in new_data:
        st.session_state.sensor_data.append(reading)
    
    st.session_state.last_update = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.messages_received += len(new_data)
    st.session_state.connection_status = "Demo Mode"
    
    df = load_historical_demo_data()

else:
    # Real Azure connection
    if st.session_state.azure_consumer is None and has_azure_secrets:
        try:
            connection_string = st.secrets['azure']['eventhub_connection_string']
            consumer_group = st.secrets['azure'].get('consumer_group', 'webappvisualization')
            
            # Start consumer in background thread
            if st.session_state.receiving_thread is None or not st.session_state.receiving_thread.is_alive():
                st.session_state.connection_status = "Connecting to Azure..."
                thread = threading.Thread(
                    target=start_azure_consumer,
                    args=(connection_string, consumer_group),
                    daemon=True
                )
                thread.start()
                st.session_state.receiving_thread = thread
                
        except Exception as e:
            st.session_state.connection_status = f"Error: {str(e)[:50]}"
    
    # Convert session data to DataFrame
    if st.session_state.sensor_data:
        df = pd.DataFrame(list(st.session_state.sensor_data))
    else:
        df = pd.DataFrame()

# Get latest readings
latest_station1 = None
latest_station2 = None

for reading in reversed(list(st.session_state.sensor_data)):
    device = reading.get('device_id', '').lower()
    if 'station1' in device or device == 'station1':
        if latest_station1 is None:
            latest_station1 = reading
    elif 'station2' in device or device == 'station2':
        if latest_station2 is None:
            latest_station2 = reading
    if latest_station1 and latest_station2:
        break

# Status bar
status_color = "🟢" if demo_mode or "Connected" in st.session_state.connection_status else "🟡"
if "error" in st.session_state.connection_status.lower():
    status_color = "🔴"

st.markdown(f"""
<div style='background: rgba(30, 58, 95, 0.5); border-radius: 5px; padding: 10px; margin-bottom: 20px; text-align: center; border: 1px solid #1e3a5f;'>
    {status_color} Status: <strong>{st.session_state.connection_status}</strong> | 
    📡 Messages: <strong>{st.session_state.messages_received}</strong> | 
    🕐 Last Update: <strong>{st.session_state.last_update or 'Waiting...'}</strong>
</div>
""", unsafe_allow_html=True)

# Station Overview
st.markdown("## 📍 Station Overview")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏭 Station 1")
    st.markdown("<small>Temperature + Humidity + Ethylene</small>", unsafe_allow_html=True)
    
    if latest_station1:
        temp_c = latest_station1.get('temperature_c')
        temp_f = celsius_to_fahrenheit(temp_c) if temp_c else None
        humidity = latest_station1.get('humidity')
        ethylene = latest_station1.get('ethylene_ppm')
        
        m1, m2, m3 = st.columns(3)
        
        with m1:
            temp_status, temp_color = get_temp_status(temp_f)
            st.metric("🌡️ Temperature", f"{temp_f:.1f}°F" if temp_f else "N/A", f"{temp_c:.1f}°C" if temp_c else None)
            st.markdown(f"<small style='color:{temp_color}'>{temp_status}</small>", unsafe_allow_html=True)
        
        with m2:
            st.metric("💧 Humidity", f"{humidity:.1f}%" if humidity else "N/A")
        
        with m3:
            eth_status, eth_color = get_ethylene_status(ethylene)
            st.metric("🍃 Ethylene", f"{ethylene:.2f} ppm" if ethylene else "N/A")
            st.markdown(f"<small style='color:{eth_color}'>{eth_status}</small>", unsafe_allow_html=True)
    else:
        st.info("Waiting for data from Station 1...")

with col2:
    st.markdown("### 🏭 Station 2")
    st.markdown("<small>Ethylene Only</small>", unsafe_allow_html=True)
    
    if latest_station2:
        ethylene = latest_station2.get('ethylene_ppm')
        
        m1, m2, m3 = st.columns(3)
        
        with m1:
            st.metric("🌡️ Temperature", "N/A")
            st.markdown("<small style='color:gray'>Not equipped</small>", unsafe_allow_html=True)
        
        with m2:
            st.metric("💧 Humidity", "N/A")
            st.markdown("<small style='color:gray'>Not equipped</small>", unsafe_allow_html=True)
        
        with m3:
            eth_status, eth_color = get_ethylene_status(ethylene)
            st.metric("🍃 Ethylene", f"{ethylene:.2f} ppm" if ethylene else "N/A")
            st.markdown(f"<small style='color:{eth_color}'>{eth_status}</small>", unsafe_allow_html=True)
    else:
        st.info("Waiting for data from Station 2...")

st.markdown("---")

# Gauge charts
st.markdown("## 📊 Real-Time Gauges")

g1, g2, g3, g4 = st.columns(4)

with g1:
    temp_f = celsius_to_fahrenheit(latest_station1.get('temperature_c')) if latest_station1 else 0
    fig = create_gauge_chart(temp_f, "Temperature (S1)", 0, 80, [25, 40, 50], "°F")
    st.plotly_chart(fig, use_container_width=True)

with g2:
    humidity = latest_station1.get('humidity') if latest_station1 else 0
    fig = create_gauge_chart(humidity, "Humidity (S1)", 0, 100, [30, 60, 80], "%")
    st.plotly_chart(fig, use_container_width=True)

with g3:
    ethylene = latest_station1.get('ethylene_ppm') if latest_station1 else 0
    fig = create_gauge_chart(ethylene, "Ethylene (S1)", 0, 15, [1, 5, 10], " ppm")
    st.plotly_chart(fig, use_container_width=True)

with g4:
    ethylene = latest_station2.get('ethylene_ppm') if latest_station2 else 0
    fig = create_gauge_chart(ethylene, "Ethylene (S2)", 0, 15, [1, 5, 10], " ppm")
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Historical charts
st.markdown("## 📈 Historical Trends")

if not df.empty:
    time_range = st.selectbox("Time Range", ["Last 30 minutes", "Last 1 hour", "Last 2 hours", "All data"], index=2)
    
    now = datetime.now()
    if time_range == "Last 30 minutes":
        df_filtered = df[df['timestamp'] > now - timedelta(minutes=30)]
    elif time_range == "Last 1 hour":
        df_filtered = df[df['timestamp'] > now - timedelta(hours=1)]
    elif time_range == "Last 2 hours":
        df_filtered = df[df['timestamp'] > now - timedelta(hours=2)]
    else:
        df_filtered = df
    
    # Ethylene chart
    st.markdown("### 🍃 Ethylene Levels Comparison")
    eth_df = df_filtered[df_filtered['ethylene_ppm'].notna()]
    if not eth_df.empty:
        fig = create_multi_station_chart(eth_df, 'ethylene_ppm', 'Ethylene by Station', 'Ethylene (ppm)')
        fig.add_hline(y=5.0, line_dash="dash", line_color="#ffaa00", annotation_text="Warning")
        fig.add_hline(y=10.0, line_dash="dash", line_color="#ff4444", annotation_text="Critical")
        st.plotly_chart(fig, use_container_width=True)
    
    # Temperature and Humidity
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🌡️ Temperature (Station 1)")
        df_s1 = df_filtered[df_filtered['device_id'].str.lower().str.contains('station1', na=False)]
        if not df_s1.empty and df_s1['temperature_c'].notna().any():
            df_s1 = df_s1.copy()
            df_s1['temperature_f'] = df_s1['temperature_c'].apply(celsius_to_fahrenheit)
            fig = create_time_series_chart(df_s1, 'temperature_f', 'Temperature', '#00b4d8', 'Temperature (°F)')
            fig.add_hline(y=25, line_dash="dash", line_color="#00b4d8")
            fig.add_hline(y=45, line_dash="dash", line_color="#ff4444")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No temperature data")
    
    with col2:
        st.markdown("### 💧 Humidity (Station 1)")
        if not df_s1.empty and df_s1['humidity'].notna().any():
            fig = create_time_series_chart(df_s1, 'humidity', 'Humidity', '#90e0ef', 'Humidity (%)')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No humidity data")
else:
    st.info("📊 Waiting for data...")

st.markdown("---")

# Alerts
st.markdown("## 🚨 Active Alerts")

alerts = []

if latest_station1:
    temp_f = celsius_to_fahrenheit(latest_station1.get('temperature_c'))
    if temp_f and (temp_f < 25 or temp_f > 45):
        alerts.append(("critical", f"Station 1 Temperature: {temp_f:.1f}°F out of range!"))
    
    eth = latest_station1.get('ethylene_ppm')
    if eth and eth > 10:
        alerts.append(("critical", f"Station 1 Ethylene: {eth:.2f} ppm CRITICAL!"))
    elif eth and eth > 5:
        alerts.append(("warning", f"Station 1 Ethylene: {eth:.2f} ppm elevated"))

if latest_station2:
    eth = latest_station2.get('ethylene_ppm')
    if eth and eth > 10:
        alerts.append(("critical", f"Station 2 Ethylene: {eth:.2f} ppm CRITICAL!"))
    elif eth and eth > 5:
        alerts.append(("warning", f"Station 2 Ethylene: {eth:.2f} ppm elevated"))

if alerts:
    for alert_type, message in alerts:
        if alert_type == "critical":
            st.markdown(f'<div class="alert-box">🚨 CRITICAL: {message}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="warning-box">⚠️ WARNING: {message}</div>', unsafe_allow_html=True)
else:
    st.markdown('<div class="normal-box">✅ All systems operating normally</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div class="footer">
    <p><strong>S&L Cold Storage</strong> - Warehouse Monitoring System v1.0</p>
    <p>Powered by Azure IoT Hub | Built with Streamlit</p>
</div>
""", unsafe_allow_html=True)

# Auto-refresh
if auto_refresh:
    time.sleep(refresh_interval)
    st.rerun()
