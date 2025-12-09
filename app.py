"""
S&L Cold Storage - AI Avocado Ripening System v3.0
===================================================
Built on stable monitoring foundation with added ripening intelligence.

DESIGN PRINCIPLES:
- O(n) time complexity for all operations
- Minimal memory footprint
- No blocking operations
- Graceful degradation
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import time
from zoneinfo import ZoneInfo

# Timezone configuration
NY_TZ = ZoneInfo("America/New_York")

# ============================================================================
# CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="S&L Cold Storage - AI Ripening",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Compact CSS - optimized for performance, supports light/dark mode
st.markdown("""
<style>
    /* Force dark theme background for consistent branding */
    .stApp { 
        background: linear-gradient(135deg, #0a1628 0%, #1a2d4a 100%) !important; 
    }
    
    /* Metric containers */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%) !important;
        border: 1px solid #00b4d8; border-radius: 10px; padding: 15px;
    }
    div[data-testid="metric-container"] label { color: #a0a0a0 !important; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: #fff !important; }
    
    /* Headers */
    h1, h2, h3 { color: #00b4d8 !important; }
    
    /* Force white text for status bar */
    .status-bar { 
        background: rgba(30,58,95,0.8) !important; 
        border-radius: 10px; padding: 12px; margin-bottom: 20px; 
        text-align: center; border: 1px solid #00b4d8;
        color: #ffffff !important;
    }
    .status-bar strong { color: #ffffff !important; }
    
    .status-card { 
        background: rgba(30,58,95,0.7) !important; 
        border-radius: 12px; padding: 20px; 
        margin: 10px 0; border-left: 4px solid #00b4d8;
        color: #ffffff !important;
    }
    
    /* Alert styles */
    .alert-critical { 
        background: linear-gradient(135deg, #ff4444, #cc0000) !important; 
        border-radius: 10px; padding: 15px; color: #ffffff !important; margin: 5px 0; 
    }
    .alert-warning { 
        background: linear-gradient(135deg, #ffaa00, #cc8800) !important; 
        border-radius: 10px; padding: 15px; color: #ffffff !important; margin: 5px 0; 
    }
    .alert-success { 
        background: linear-gradient(135deg, #00cc66, #009944) !important; 
        border-radius: 10px; padding: 15px; color: #ffffff !important; margin: 5px 0; 
    }
    
    /* Ripening stages */
    .ripening-stage { 
        font-size: 1.5rem; font-weight: bold; text-align: center; 
        padding: 15px; border-radius: 10px; margin: 10px 0; 
    }
    .stage-1 { background: linear-gradient(135deg, #2d5016, #1a3009) !important; color: #90EE90 !important; }
    .stage-2 { background: linear-gradient(135deg, #4a7c23, #2d5016) !important; color: #ADFF2F !important; }
    .stage-3 { background: linear-gradient(135deg, #7cb342, #558b2f) !important; color: #FFFF00 !important; }
    .stage-4 { background: linear-gradient(135deg, #c0a000, #8b7500) !important; color: #FFD700 !important; }
    .stage-5 { background: linear-gradient(135deg, #1b5e20, #0d3010) !important; color: #00ff00 !important; }
    
    /* Recommendations */
    .recommendation { 
        background: rgba(0,180,216,0.2) !important; 
        border-left: 4px solid #00b4d8;
        padding: 15px; margin: 10px 0; border-radius: 0 10px 10px 0;
        color: #ffffff !important;
    }
    
    /* Hide default status widget */
    div[data-testid="stStatusWidget"] { display: none; }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# DATA CLASSES - Efficient Memory Layout
# ============================================================================

@dataclass(frozen=True, slots=True)
class RipeningThresholds:
    """Immutable thresholds - allocated once, reused everywhere"""
    # Temperature (°F) - Avocado specific
    temp_min: float = 58.0
    temp_optimal_low: float = 64.0
    temp_optimal_high: float = 68.0
    temp_max: float = 72.0
    temp_danger_high: float = 86.0  # Flesh darkening risk
    temp_danger_low: float = 40.0   # Chilling injury risk
    
    # Humidity (%)
    humidity_min: float = 85.0
    humidity_optimal: float = 90.0
    humidity_max: float = 95.0
    
    # Ethylene (ppm) - Ripening stages
    eth_stage1: float = 0.1    # Hard/Green
    eth_stage2: float = 1.0    # Conditioning
    eth_stage3: float = 10.0   # Breaking
    eth_stage4: float = 50.0   # Ripe
    eth_stage5: float = 100.0  # Ready to eat


@dataclass(slots=True)
class SensorReading:
    """Memory-efficient sensor reading"""
    station: str
    timestamp: datetime
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None
    ethylene: Optional[float] = None
    
    @property
    def temp_f(self) -> Optional[float]:
        """Convert to Fahrenheit - computed on demand"""
        return (self.temperature * 9/5 + 32) if self.temperature else None


@dataclass(slots=True)
class RipeningAnalysis:
    """Analysis result for a batch"""
    stage: int  # 1-5
    stage_name: str
    progress_percent: float
    estimated_hours: Optional[float]
    recommendations: List[str]
    alerts: List[Tuple[str, str]]  # (level, message)


# Singleton thresholds instance
THRESHOLDS = RipeningThresholds()

# Stage definitions - O(1) lookup
STAGE_NAMES = {
    1: "Hard/Green",
    2: "Conditioning",
    3: "Breaking", 
    4: "Ripe",
    5: "Ready to Eat"
}

STAGE_COLORS = {
    1: "#2d5016",
    2: "#4a7c23",
    3: "#7cb342",
    4: "#c0a000",
    5: "#1b5e20"
}


# ============================================================================
# CORE ALGORITHMS - O(n) Time Complexity
# ============================================================================

def analyze_ripening_stage(ethylene: float) -> Tuple[int, str, float]:
    """
    Determine ripening stage from ethylene level.
    Time: O(1), Space: O(1)
    """
    if ethylene is None or pd.isna(ethylene):
        return 1, STAGE_NAMES[1], 0.0
    
    # Binary search could be used but with 5 stages, linear is fine
    if ethylene < THRESHOLDS.eth_stage1:
        return 1, STAGE_NAMES[1], min(ethylene / THRESHOLDS.eth_stage1 * 20, 20)
    elif ethylene < THRESHOLDS.eth_stage2:
        progress = 20 + (ethylene - THRESHOLDS.eth_stage1) / (THRESHOLDS.eth_stage2 - THRESHOLDS.eth_stage1) * 20
        return 2, STAGE_NAMES[2], progress
    elif ethylene < THRESHOLDS.eth_stage3:
        progress = 40 + (ethylene - THRESHOLDS.eth_stage2) / (THRESHOLDS.eth_stage3 - THRESHOLDS.eth_stage2) * 20
        return 3, STAGE_NAMES[3], progress
    elif ethylene < THRESHOLDS.eth_stage4:
        progress = 60 + (ethylene - THRESHOLDS.eth_stage3) / (THRESHOLDS.eth_stage4 - THRESHOLDS.eth_stage3) * 20
        return 4, STAGE_NAMES[4], progress
    else:
        progress = min(80 + (ethylene - THRESHOLDS.eth_stage4) / (THRESHOLDS.eth_stage5 - THRESHOLDS.eth_stage4) * 20, 100)
        return 5, STAGE_NAMES[5], progress


def estimate_ripening_time(current_stage: int, ethylene: float, temperature_f: float) -> Optional[float]:
    """
    Estimate hours to fully ripe based on current conditions.
    Time: O(1), Space: O(1)
    
    Based on research: Optimal ripening at 64-68°F takes 4-6 days.
    Every 10°F above optimal reduces time by ~50%.
    """
    if current_stage >= 5:
        return 0.0
    
    # Base hours to ripe from each stage (at optimal conditions)
    base_hours = {1: 120, 2: 96, 3: 72, 4: 36, 5: 0}
    
    hours = base_hours.get(current_stage, 96)
    
    # Temperature adjustment
    if temperature_f:
        if THRESHOLDS.temp_optimal_low <= temperature_f <= THRESHOLDS.temp_optimal_high:
            # Optimal - no adjustment
            pass
        elif temperature_f > THRESHOLDS.temp_optimal_high:
            # Warmer = faster ripening
            excess = temperature_f - THRESHOLDS.temp_optimal_high
            hours *= max(0.5, 1 - (excess / 20))
        else:
            # Cooler = slower ripening  
            deficit = THRESHOLDS.temp_optimal_low - temperature_f
            hours *= min(2.0, 1 + (deficit / 15))
    
    return round(hours, 1)


def generate_recommendations(reading: SensorReading, stage: int) -> List[str]:
    """
    Generate actionable recommendations based on current conditions.
    Time: O(1), Space: O(k) where k = number of recommendations (bounded)
    """
    recommendations = []
    temp_f = reading.temp_f
    
    if temp_f is None:
        recommendations.append("⚠️ Temperature sensor offline - check connection")
        return recommendations
    
    # Temperature recommendations
    if temp_f > THRESHOLDS.temp_danger_high:
        recommendations.append(f"🚨 URGENT: Temperature {temp_f:.1f}°F risks flesh darkening! Cool immediately!")
    elif temp_f > THRESHOLDS.temp_max:
        recommendations.append(f"⬇️ Lower temperature to 64-68°F range (currently {temp_f:.1f}°F)")
    elif temp_f < THRESHOLDS.temp_danger_low:
        recommendations.append(f"🚨 URGENT: Temperature {temp_f:.1f}°F risks chilling injury! Warm immediately!")
    elif temp_f < THRESHOLDS.temp_min:
        recommendations.append(f"⬆️ Raise temperature to 64-68°F range (currently {temp_f:.1f}°F)")
    elif THRESHOLDS.temp_optimal_low <= temp_f <= THRESHOLDS.temp_optimal_high:
        recommendations.append(f"✅ Temperature optimal at {temp_f:.1f}°F")
    
    # Humidity recommendations
    if reading.humidity is not None:
        if reading.humidity < THRESHOLDS.humidity_min:
            recommendations.append(f"💧 Increase humidity to 90-95% (currently {reading.humidity:.0f}%)")
        elif reading.humidity > THRESHOLDS.humidity_max:
            recommendations.append(f"💨 Reduce humidity below 95% to prevent mold (currently {reading.humidity:.0f}%)")
        elif reading.humidity >= THRESHOLDS.humidity_optimal:
            recommendations.append(f"✅ Humidity optimal at {reading.humidity:.0f}%")
    
    # Stage-specific recommendations
    if stage == 1:
        recommendations.append("🌡️ Consider applying ethylene gas to initiate ripening")
    elif stage == 2:
        recommendations.append("⏳ Conditioning phase - maintain stable conditions")
    elif stage == 3:
        recommendations.append("🔄 Breaking stage - monitor closely for color changes")
    elif stage == 4:
        recommendations.append("📦 Ripe soon - prepare for distribution within 24-48 hours")
    elif stage == 5:
        recommendations.append("🚚 Ready for distribution - ship within 24 hours for best quality")
    
    # Ventilation reminder based on time
    hour = datetime.now().hour
    if hour in [6, 14, 22]:  # 6 AM, 2 PM, 10 PM
        recommendations.append("🌬️ Scheduled ventilation check - ensure 15-20 minutes fresh air exchange")
    
    return recommendations


def generate_alerts(reading: SensorReading) -> List[Tuple[str, str]]:
    """
    Generate alerts based on sensor readings.
    Time: O(1), Space: O(k) where k = number of alerts (bounded)
    Returns: List of (level, message) tuples where level is 'critical', 'warning', or 'info'
    """
    alerts = []
    temp_f = reading.temp_f
    
    if temp_f:
        if temp_f > THRESHOLDS.temp_danger_high:
            alerts.append(("critical", f"🔥 {reading.station}: Temperature {temp_f:.1f}°F - FLESH DARKENING RISK"))
        elif temp_f < THRESHOLDS.temp_danger_low:
            alerts.append(("critical", f"❄️ {reading.station}: Temperature {temp_f:.1f}°F - CHILLING INJURY RISK"))
        elif temp_f > THRESHOLDS.temp_max:
            alerts.append(("warning", f"⬆️ {reading.station}: Temperature {temp_f:.1f}°F above optimal"))
        elif temp_f < THRESHOLDS.temp_min:
            alerts.append(("warning", f"⬇️ {reading.station}: Temperature {temp_f:.1f}°F below optimal"))
    
    if reading.humidity is not None:
        if reading.humidity < 80:
            alerts.append(("warning", f"💧 {reading.station}: Low humidity {reading.humidity:.0f}% - quality risk"))
        elif reading.humidity > 98:
            alerts.append(("warning", f"💦 {reading.station}: High humidity {reading.humidity:.0f}% - mold risk"))
    
    if reading.ethylene is not None:
        if reading.ethylene > THRESHOLDS.eth_stage5:
            alerts.append(("warning", f"🍃 {reading.station}: High ethylene {reading.ethylene:.1f}ppm - over-ripening risk"))
    
    return alerts


# ============================================================================
# DATA FETCHING - Cached & Efficient
# ============================================================================

@st.cache_data(ttl=15)
def fetch_sensor_data(connection_string: str, table_name: str, hours_back: int = 2) -> Tuple[List[Dict], str, int]:
    """
    Fetch sensor data from Azure Table Storage.
    Uses server-side filtering for efficiency.
    Time: O(n) where n = number of records returned
    """
    try:
        from azure.data.tables import TableClient
        
        table_client = TableClient.from_connection_string(connection_string, table_name)
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        time_filter = time_threshold.strftime('%Y-%m-%dT%H:%M:%S')
        
        # Server-side filter - only fetch what we need
        entities = table_client.query_entities(
            query_filter=f"timestamp ge '{time_filter}'",
            select=['PartitionKey', 'timestamp', 'temperature', 'humidity', 'ethylene']
        )
        
        data = []
        for entity in entities:
            try:
                ts = entity.get('timestamp', '')
                timestamp = datetime.fromisoformat(ts.replace('Z', '+00:00')) if isinstance(ts, str) else ts
                
                # Clean ethylene value
                eth_raw = entity.get('ethylene')
                ethylene = float(eth_raw) if eth_raw is not None and not pd.isna(eth_raw) else 0.0
                
                data.append({
                    'station': entity.get('PartitionKey', 'unknown'),
                    'timestamp': timestamp,
                    'temperature': float(entity['temperature']) if entity.get('temperature') else None,
                    'humidity': float(entity['humidity']) if entity.get('humidity') else None,
                    'ethylene': ethylene
                })
            except (ValueError, TypeError, KeyError):
                continue
        
        return data, "Connected", len(data)
        
    except ImportError:
        return [], "Azure SDK not installed", 0
    except Exception as e:
        return [], f"Error: {str(e)[:40]}", 0


def get_latest_readings(data: List[Dict]) -> Dict[str, SensorReading]:
    """
    Get latest reading per station.
    Time: O(n) single pass, Space: O(s) where s = number of stations
    """
    latest = {}
    
    for record in data:
        station = record['station']
        if station not in latest or record['timestamp'] > latest[station].timestamp:
            latest[station] = SensorReading(
                station=station,
                timestamp=record['timestamp'],
                temperature=record.get('temperature'),
                humidity=record.get('humidity'),
                ethylene=record.get('ethylene', 0.0)
            )
    
    return latest


# ============================================================================
# VISUALIZATION COMPONENTS
# ============================================================================

def hex_to_rgba(hex_color: str, alpha: float = 0.2) -> str:
    """Convert hex color to rgba format for Plotly"""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def create_gauge(value: float, title: str, min_val: float, max_val: float, 
                 ranges: List[Tuple[float, float, str]], unit: str = "") -> go.Figure:
    """
    Create an efficient gauge chart with static centered number.
    """
    if value is None:
        value = 0
    
    # Round value to 1 decimal place
    value = round(value, 1)
    
    # Determine color based on ranges
    color = "#00ff88"
    for low, high, c in ranges:
        if low <= value < high:
            color = c
            break
    
    # Build steps with proper rgba colors
    steps = []
    for r in ranges:
        steps.append({
            'range': [r[0], r[1]], 
            'color': hex_to_rgba(r[2], 0.2)
        })
    
    # Create gauge WITHOUT number (we'll add it as annotation)
    fig = go.Figure(go.Indicator(
        mode="gauge",  # No number here
        value=value,
        title={'text': title, 'font': {'size': 13, 'color': '#90e0ef'}},
        gauge={
            'axis': {
                'range': [min_val, max_val], 
                'tickcolor': '#fff',
                'tickfont': {'size': 9},
                'tickwidth': 1
            },
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': '#0a1628',
            'borderwidth': 1,
            'bordercolor': '#1e3a5f',
            'steps': steps
        }
    ))
    
    # Add number as static centered annotation
    fig.add_annotation(
        text=f"<b>{value:.1f}</b> {unit}",
        x=0.5,
        y=0.25,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=20, color="#ffffff"),
        xanchor="center",
        yanchor="middle"
    )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=200,
        margin=dict(l=15, r=15, t=30, b=10)
    )
    
    return fig


def create_trend_chart(df: pd.DataFrame, y_col: str, title: str, 
                       y_label: str, optimal_range: Tuple[float, float] = None) -> go.Figure:
    """
    Create a multi-station trend chart with optional optimal range.
    """
    fig = go.Figure()
    
    if df.empty:
        fig.add_annotation(text="No data", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)
    else:
        colors = {'station1-raspberry-pi': '#00b4d8', 'station2': '#00ff88', 'station1': '#00b4d8'}
        
        for station in df['station'].unique():
            station_df = df[df['station'] == station]
            color = colors.get(station, '#ffffff')
            display_name = "Station 1" if "station1" in station.lower() or "raspberry" in station.lower() else "Station 2"
            
            fig.add_trace(go.Scatter(
                x=station_df['timestamp'],
                y=station_df[y_col],
                mode='lines',
                name=display_name,
                line=dict(color=color, width=2)
            ))
        
        # Add optimal range
        if optimal_range:
            fig.add_hrect(
                y0=optimal_range[0], y1=optimal_range[1],
                fillcolor="rgba(0, 255, 136, 0.1)",
                line_width=0,
                annotation_text="Optimal",
                annotation_position="top right"
            )
    
    fig.update_layout(
        title=title,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(10,22,40,0.8)',
        font={'color': '#fff'},
        xaxis={'gridcolor': '#1e3a5f', 'title': 'Time'},
        yaxis={'gridcolor': '#1e3a5f', 'title': y_label},
        height=300,
        margin=dict(l=50, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


def create_progress_bar(progress: float, stage: int) -> str:
    """Generate HTML progress bar for ripening stage"""
    color = STAGE_COLORS.get(stage, "#00b4d8")
    return f"""
    <div style='background: #1e3a5f; border-radius: 10px; height: 30px; overflow: hidden; margin: 10px 0;'>
        <div style='background: linear-gradient(90deg, {color}, {color}88); height: 100%; width: {progress}%;
                    display: flex; align-items: center; justify-content: center; color: white; font-weight: bold;
                    transition: width 0.5s ease;'>
            {progress:.0f}%
        </div>
    </div>
    """


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    # Header
    st.markdown("""
    <div style='text-align: center; padding: 15px 0;'>
        <h1 style='font-size: 2.5rem; margin: 0;'>🥑 S&L Cold Storage</h1>
        <p style='color: #90e0ef; font-size: 1.1rem; margin: 5px 0;'>AI Ripening System v3.0</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Configuration
    connection_string = None
    table_name = "sensordata"
    
    try:
        if 'azure' in st.secrets:
            connection_string = st.secrets['azure'].get('storage_connection_string')
            table_name = st.secrets['azure'].get('table_name', 'sensordata')
    except Exception:
        pass
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        if not connection_string:
            st.warning("Azure not configured - Demo mode")
            demo_mode = True
        else:
            demo_mode = st.checkbox("Demo Mode", value=False)
        
        hours_back = st.slider("History (hours)", 1, 24, 4)
        auto_refresh = st.checkbox("Auto Refresh", value=True)
        refresh_rate = st.slider("Refresh (sec)", 10, 60, 20)
        
        st.markdown("---")
        st.markdown("### 🥑 Ripening Targets")
        target_stage = st.selectbox("Target Stage", [3, 4, 5], format_func=lambda x: STAGE_NAMES[x])
    
    # Fetch data
    if demo_mode:
        # Generate demo data
        data = []
        now = datetime.now(timezone.utc)
        for i in range(240):
            ts = now - timedelta(minutes=i)
            data.append({
                'station': 'station1-raspberry-pi',
                'timestamp': ts,
                'temperature': 20.0 + (i % 20) * 0.1,
                'humidity': 88.0 + (i % 10) * 0.5,
                'ethylene': 5.0 + (i % 30) * 0.2
            })
            data.append({
                'station': 'station2',
                'timestamp': ts,
                'temperature': 21.0 + (i % 15) * 0.1,
                'humidity': 85.0 + (i % 12) * 0.5,
                'ethylene': 8.0 + (i % 25) * 0.3
            })
        status = "Demo Mode"
        count = len(data)
    else:
        data, status, count = fetch_sensor_data(connection_string, table_name, hours_back)
    
    # Get latest readings
    latest = get_latest_readings(data)
    
    # Status bar
    status_color = "🟢" if status == "Connected" else "🟡" if "Demo" in status else "🔴"
    update_time = datetime.now(NY_TZ).strftime("%H:%M:%S")
    
    st.markdown(f"""
    <div style='background: rgba(30,58,95,0.6); border-radius: 10px; padding: 12px; margin-bottom: 20px; 
                text-align: center; border: 1px solid #00b4d8;'>
        {status_color} <strong>{status}</strong> | 📊 {count} readings | 🕐 {update_time}
    </div>
    """, unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🎯 Dashboard", "📊 Sensors", "📈 Trends"])
    
    # ========== TAB 1: DASHBOARD ==========
    with tab1:
        # Collect all alerts
        all_alerts = []
        
        # Station cards
        col1, col2 = st.columns(2)
        
        for idx, (col, station_key) in enumerate([(col1, 'station1'), (col2, 'station2')]):
            with col:
                # Find the reading for this station
                reading = None
                for key, val in latest.items():
                    if station_key in key.lower() or ('raspberry' in key.lower() and station_key == 'station1'):
                        reading = val
                        break
                
                station_name = "Station 1" if station_key == 'station1' else "Station 2"
                st.markdown(f"### 🏭 {station_name}")
                
                if reading:
                    # Analyze ripening
                    stage, stage_name, progress = analyze_ripening_stage(reading.ethylene)
                    est_hours = estimate_ripening_time(stage, reading.ethylene, reading.temp_f)
                    recommendations = generate_recommendations(reading, stage)
                    alerts = generate_alerts(reading)
                    all_alerts.extend(alerts)
                    
                    # Stage display
                    st.markdown(f"""
                    <div class='ripening-stage stage-{stage}'>
                        Stage {stage}: {stage_name}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # Progress bar
                    st.markdown(create_progress_bar(progress, stage), unsafe_allow_html=True)
                    
                    # Metrics
                    m1, m2, m3 = st.columns(3)
                    with m1:
                        st.metric("🌡️ Temp", f"{reading.temp_f:.1f}°F" if reading.temp_f else "N/A",
                                 f"{reading.temperature:.1f}°C" if reading.temperature else None)
                    with m2:
                        st.metric("💧 Humidity", f"{reading.humidity:.0f}%" if reading.humidity else "N/A")
                    with m3:
                        st.metric("🍃 Ethylene", f"{reading.ethylene:.1f} ppm" if reading.ethylene else "0 ppm")
                    
                    # Estimated time
                    if est_hours is not None:
                        if est_hours == 0:
                            st.success("✅ Ready for distribution!")
                        elif est_hours < 24:
                            st.info(f"⏱️ Est. ready in **{est_hours:.0f} hours**")
                        else:
                            days = est_hours / 24
                            st.info(f"⏱️ Est. ready in **{days:.1f} days**")
                    
                    # Top recommendation
                    if recommendations:
                        st.markdown(f"""
                        <div class='recommendation'>
                            <strong>💡 Recommendation:</strong><br>{recommendations[0]}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info(f"Waiting for {station_name} data...")
        
        # Alerts section
        st.markdown("---")
        st.markdown("### 🚨 Alerts")
        
        if all_alerts:
            for level, message in all_alerts:
                css_class = f"alert-{level}"
                st.markdown(f'<div class="{css_class}">{message}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="alert-success">✅ All systems operating within normal parameters</div>', 
                       unsafe_allow_html=True)
        
        # All recommendations
        st.markdown("---")
        st.markdown("### 💡 All Recommendations")
        
        for key, reading in latest.items():
            if reading:
                stage, _, _ = analyze_ripening_stage(reading.ethylene)
                recs = generate_recommendations(reading, stage)
                station_name = "Station 1" if "station1" in key.lower() or "raspberry" in key.lower() else "Station 2"
                
                with st.expander(f"🏭 {station_name}", expanded=False):
                    for rec in recs:
                        st.markdown(f"• {rec}")
    
    # ========== TAB 2: SENSORS ==========
    with tab2:
        st.markdown("### 📊 Real-Time Gauges")
        
        for key, reading in latest.items():
            station_name = "Station 1" if "station1" in key.lower() or "raspberry" in key.lower() else "Station 2"
            st.markdown(f"#### 🏭 {station_name}")
            
            if reading:
                g1, g2, g3 = st.columns(3)
                
                with g1:
                    temp_ranges = [
                        (0, THRESHOLDS.temp_min, "#00b4d8"),
                        (THRESHOLDS.temp_min, THRESHOLDS.temp_optimal_low, "#ffaa00"),
                        (THRESHOLDS.temp_optimal_low, THRESHOLDS.temp_optimal_high, "#00ff88"),
                        (THRESHOLDS.temp_optimal_high, THRESHOLDS.temp_max, "#ffaa00"),
                        (THRESHOLDS.temp_max, 100, "#ff4444")
                    ]
                    fig = create_gauge(reading.temp_f or 0, "Temperature", 30, 100, temp_ranges, "°F")
                    st.plotly_chart(fig, use_container_width=True, key=f"gauge_temp_{key}")
                
                with g2:
                    hum_ranges = [
                        (0, 80, "#ffaa00"),
                        (80, THRESHOLDS.humidity_min, "#00b4d8"),
                        (THRESHOLDS.humidity_min, THRESHOLDS.humidity_max, "#00ff88"),
                        (THRESHOLDS.humidity_max, 100, "#ffaa00")
                    ]
                    fig = create_gauge(reading.humidity or 0, "Humidity", 0, 100, hum_ranges, "%")
                    st.plotly_chart(fig, use_container_width=True, key=f"gauge_hum_{key}")
                
                with g3:
                    eth_ranges = [
                        (0, THRESHOLDS.eth_stage2, "#00b4d8"),
                        (THRESHOLDS.eth_stage2, THRESHOLDS.eth_stage3, "#00ff88"),
                        (THRESHOLDS.eth_stage3, THRESHOLDS.eth_stage4, "#ffaa00"),
                        (THRESHOLDS.eth_stage4, 150, "#ff4444")
                    ]
                    fig = create_gauge(reading.ethylene or 0, "Ethylene", 0, 100, eth_ranges, " ppm")
                    st.plotly_chart(fig, use_container_width=True, key=f"gauge_eth_{key}")
            else:
                st.info("Waiting for data...")
            
            st.markdown("---")
    
    # ========== TAB 3: TRENDS ==========
    with tab3:
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            
            # Temperature chart
            if 'temperature' in df.columns:
                temp_df = df[df['temperature'].notna()].copy()
                temp_df['temp_f'] = temp_df['temperature'].apply(lambda x: x * 9/5 + 32 if x else None)
                fig = create_trend_chart(temp_df, 'temp_f', '🌡️ Temperature History', '°F',
                                        (THRESHOLDS.temp_optimal_low, THRESHOLDS.temp_optimal_high))
                st.plotly_chart(fig, use_container_width=True, key="trend_temp")
            
            # Humidity chart
            if 'humidity' in df.columns:
                hum_df = df[df['humidity'].notna()]
                fig = create_trend_chart(hum_df, 'humidity', '💧 Humidity History', '%',
                                        (THRESHOLDS.humidity_min, THRESHOLDS.humidity_max))
                st.plotly_chart(fig, use_container_width=True, key="trend_hum")
            
            # Ethylene chart
            if 'ethylene' in df.columns:
                eth_df = df[df['ethylene'].notna()]
                fig = create_trend_chart(eth_df, 'ethylene', '🍃 Ethylene History', 'ppm')
                
                # Add stage lines
                fig.add_hline(y=THRESHOLDS.eth_stage2, line_dash="dot", line_color="#00b4d8",
                             annotation_text="Conditioning")
                fig.add_hline(y=THRESHOLDS.eth_stage3, line_dash="dot", line_color="#00ff88",
                             annotation_text="Breaking")
                fig.add_hline(y=THRESHOLDS.eth_stage4, line_dash="dot", line_color="#ffaa00",
                             annotation_text="Ripe")
                
                st.plotly_chart(fig, use_container_width=True, key="trend_eth")
        else:
            st.warning("No data available for the selected time range")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 20px; font-size: 0.8rem;'>
        <strong>S&L Cold Storage</strong> - AI Ripening System v3.0<br>
        Optimized for Performance | O(n) Algorithms | Azure Table Storage
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


if __name__ == "__main__":
    main()
