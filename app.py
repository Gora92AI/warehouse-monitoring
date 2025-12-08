"""
S&L Cold Storage - AI Avocado Ripening System
Intelligent monitoring and recommendations for optimal fruit ripening

Version: 3.1 - AI Ripening Edition (Fixed)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta, timezone
import time
import json

# ============================================================================
# PAGE CONFIGURATION - MUST BE FIRST
# ============================================================================
st.set_page_config(
    page_title="S&L Cold Storage - AI Ripening",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS - Professional Dark Theme with Avocado Green Accents
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    .stApp {
        background: linear-gradient(145deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        font-family: 'Outfit', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
        border: 1px solid #238636;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(35, 134, 54, 0.15);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    
    div[data-testid="metric-container"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 40px rgba(35, 134, 54, 0.25);
    }
    
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2.2rem !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricDelta"] {
        font-family: 'JetBrains Mono', monospace !important;
    }
    
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }
    
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #c9d1d9;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: #21262d;
        color: #8b949e;
        border-radius: 8px 8px 0 0;
        border: 1px solid #30363d;
        border-bottom: none;
        padding: 10px 20px;
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: #ffffff;
        border-color: #238636;
    }
    
    .alert-critical {
        background: linear-gradient(135deg, #da3633 0%, #b62324 100%);
        border: 1px solid #f85149;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        color: #ffffff;
        font-weight: 500;
        font-family: 'Outfit', sans-serif;
        box-shadow: 0 4px 20px rgba(248, 81, 73, 0.3);
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #9e6a03 0%, #845306 100%);
        border: 1px solid #d29922;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        color: #ffffff;
        font-weight: 500;
        font-family: 'Outfit', sans-serif;
        box-shadow: 0 4px 20px rgba(210, 153, 34, 0.3);
    }
    
    .alert-success {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        border: 1px solid #3fb950;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        color: #ffffff;
        font-weight: 500;
        font-family: 'Outfit', sans-serif;
        box-shadow: 0 4px 20px rgba(63, 185, 80, 0.3);
    }
    
    .alert-info {
        background: linear-gradient(135deg, #1f6feb 0%, #1158c7 100%);
        border: 1px solid #58a6ff;
        border-radius: 12px;
        padding: 16px 20px;
        margin: 12px 0;
        color: #ffffff;
        font-weight: 500;
        font-family: 'Outfit', sans-serif;
        box-shadow: 0 4px 20px rgba(88, 166, 255, 0.3);
    }
    
    .ai-panel {
        background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
        border: 2px solid #238636;
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        box-shadow: 0 8px 32px rgba(35, 134, 54, 0.2);
    }
    
    .ai-panel-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #30363d;
    }
    
    .ai-panel-title {
        color: #3fb950;
        font-size: 1.3rem;
        font-weight: 600;
        font-family: 'Outfit', sans-serif;
        margin: 0;
    }
    
    .ai-recommendation {
        background: #21262d;
        border-left: 4px solid #238636;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        color: #c9d1d9;
        font-family: 'Outfit', sans-serif;
    }
    
    .ai-recommendation-action {
        background: #21262d;
        border-left: 4px solid #f0883e;
        border-radius: 0 8px 8px 0;
        padding: 12px 16px;
        margin: 8px 0;
        color: #c9d1d9;
        font-family: 'Outfit', sans-serif;
    }
    
    .ripening-progress-container {
        background: #21262d;
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
        border: 1px solid #30363d;
    }
    
    .ripening-stage {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
        font-family: 'Outfit', sans-serif;
    }
    
    .stage-green { background: #238636; color: white; }
    .stage-breaking { background: #9e6a03; color: white; }
    .stage-ripe { background: #f0883e; color: white; }
    .stage-ready { background: #da3633; color: white; }
    
    .checklist-item {
        background: #21262d;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 12px;
        border: 1px solid #30363d;
        transition: all 0.3s ease;
    }
    
    .checklist-item:hover {
        border-color: #238636;
        background: #1a2332;
    }
    
    .footer {
        text-align: center;
        padding: 24px;
        color: #8b949e;
        font-family: 'Outfit', sans-serif;
        border-top: 1px solid #30363d;
        margin-top: 40px;
    }
    
    .batch-card {
        background: linear-gradient(135deg, #1a2332 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
    }
    
    .batch-header {
        color: #58a6ff;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 12px;
        font-family: 'Outfit', sans-serif;
    }
    
    .batch-detail {
        color: #8b949e;
        font-size: 0.9rem;
        margin: 4px 0;
        font-family: 'Outfit', sans-serif;
    }
    
    .batch-value {
        color: #c9d1d9;
        font-weight: 500;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-family: 'Outfit', sans-serif;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 4px 20px rgba(46, 160, 67, 0.4);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# AVOCADO RIPENING CONSTANTS
# ============================================================================
AVOCADO_PARAMS = {
    'ethylene': {
        'optimal_min': 10,
        'optimal_max': 100,
        'warning_low': 5,
        'critical_high': 150,
    },
    'temperature': {
        'optimal_min': 60,
        'optimal_max': 68,
        'storage_min': 40,
        'storage_max': 45,
        'critical_high': 86,
        'critical_low': 40,
    },
    'humidity': {
        'optimal_min': 90,
        'optimal_max': 95,
        'warning_low': 85,
        'critical_low': 80,
    },
    'ripening_time': {
        'early_season': {'ethylene_hours': 48, 'total_days': 6},
        'mid_season': {'ethylene_hours': 36, 'total_days': 5},
        'late_season': {'ethylene_hours': 24, 'total_days': 4},
    },
    'ventilation': {
        'interval_hours': 12,
        'duration_minutes': 20,
    }
}


# ============================================================================
# AI ENGINE
# ============================================================================
class AIRipeningEngine:
    def __init__(self, params=AVOCADO_PARAMS):
        self.params = params
    
    def analyze_conditions(self, temperature_f, humidity, ethylene_ppm, 
                          batch_start_time=None, season='mid_season'):
        alerts = []
        recommendations = []
        status = 'optimal'
        
        # Temperature Analysis
        temp_status, temp_alerts, temp_recs = self._analyze_temperature(temperature_f)
        alerts.extend(temp_alerts)
        recommendations.extend(temp_recs)
        if temp_status == 'critical':
            status = 'critical'
        elif temp_status == 'warning' and status != 'critical':
            status = 'warning'
        
        # Humidity Analysis
        hum_status, hum_alerts, hum_recs = self._analyze_humidity(humidity)
        alerts.extend(hum_alerts)
        recommendations.extend(hum_recs)
        if hum_status == 'critical':
            status = 'critical'
        elif hum_status == 'warning' and status != 'critical':
            status = 'warning'
        
        # Ethylene Analysis
        eth_status, eth_alerts, eth_recs = self._analyze_ethylene(ethylene_ppm)
        alerts.extend(eth_alerts)
        recommendations.extend(eth_recs)
        if eth_status == 'critical':
            status = 'critical'
        elif eth_status == 'warning' and status != 'critical':
            status = 'warning'
        
        # Calculate ripening progress
        progress_percent = 0
        ripening_stage = 'Green'
        time_remaining = None
        
        if batch_start_time:
            hours_elapsed = (datetime.now(timezone.utc) - batch_start_time).total_seconds() / 3600
            season_params = self.params['ripening_time'].get(season, self.params['ripening_time']['mid_season'])
            total_hours = season_params['total_days'] * 24
            
            progress_percent = min(100, (hours_elapsed / total_hours) * 100)
            time_remaining = max(0, total_hours - hours_elapsed)
            
            if progress_percent < 20:
                ripening_stage = 'Green'
            elif progress_percent < 50:
                ripening_stage = 'Breaking'
            elif progress_percent < 80:
                ripening_stage = 'Ripe'
            else:
                ripening_stage = 'Ready-to-Eat'
        
        # Ventilation reminder
        vent_rec = self._check_ventilation_schedule(batch_start_time)
        if vent_rec:
            recommendations.append(vent_rec)
        
        if status == 'optimal' and not alerts:
            recommendations.insert(0, {
                'type': 'success',
                'message': '✅ All conditions are optimal for avocado ripening',
                'priority': 'info'
            })
        
        return {
            'status': status,
            'alerts': alerts,
            'recommendations': recommendations,
            'ripening_stage': ripening_stage,
            'progress_percent': progress_percent,
            'time_remaining': time_remaining
        }
    
    def _analyze_temperature(self, temp_f):
        alerts = []
        recommendations = []
        status = 'optimal'
        p = self.params['temperature']
        
        if temp_f is None:
            return 'unknown', [], []
        
        if temp_f >= p['critical_high']:
            status = 'critical'
            alerts.append({
                'type': 'critical',
                'message': f'🚨 CRITICAL: Temperature {temp_f:.1f}°F exceeds {p["critical_high"]}°F - Risk of flesh darkening!'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌡️ IMMEDIATELY lower temperature to {p["optimal_max"]}°F or below',
                'priority': 'critical'
            })
        elif temp_f > p['optimal_max']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Temperature {temp_f:.1f}°F is above optimal range ({p["optimal_min"]}-{p["optimal_max"]}°F)'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌡️ Lower temperature to {p["optimal_max"]}°F for optimal ripening',
                'priority': 'high'
            })
        elif temp_f < p['optimal_min']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Temperature {temp_f:.1f}°F is below optimal range ({p["optimal_min"]}-{p["optimal_max"]}°F)'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌡️ Increase temperature to {p["optimal_min"]}°F for faster ripening',
                'priority': 'medium'
            })
        else:
            recommendations.append({
                'type': 'status',
                'message': f'🌡️ Temperature {temp_f:.1f}°F is in optimal range ✓',
                'priority': 'info'
            })
        
        return status, alerts, recommendations
    
    def _analyze_humidity(self, humidity):
        alerts = []
        recommendations = []
        status = 'optimal'
        p = self.params['humidity']
        
        if humidity is None:
            return 'unknown', [], []
        
        if humidity < p['critical_low']:
            status = 'critical'
            alerts.append({
                'type': 'critical',
                'message': f'🚨 CRITICAL: Humidity {humidity:.1f}% is dangerously low!'
            })
            recommendations.append({
                'type': 'action',
                'message': f'💧 IMMEDIATELY activate humidifier - Target {p["optimal_min"]}-{p["optimal_max"]}%',
                'priority': 'critical'
            })
        elif humidity < p['warning_low']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Humidity {humidity:.1f}% is below optimal ({p["optimal_min"]}-{p["optimal_max"]}%)'
            })
            recommendations.append({
                'type': 'action',
                'message': f'💧 Increase humidity to {p["optimal_min"]}% to prevent quality loss',
                'priority': 'high'
            })
        elif humidity > p['optimal_max']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Humidity {humidity:.1f}% is above optimal - Risk of mold'
            })
            recommendations.append({
                'type': 'action',
                'message': f'💨 Reduce humidity to {p["optimal_max"]}% or below',
                'priority': 'medium'
            })
        else:
            recommendations.append({
                'type': 'status',
                'message': f'💧 Humidity {humidity:.1f}% is in optimal range ✓',
                'priority': 'info'
            })
        
        return status, alerts, recommendations
    
    def _analyze_ethylene(self, ethylene_ppm):
        alerts = []
        recommendations = []
        status = 'optimal'
        p = self.params['ethylene']
        
        if ethylene_ppm is None:
            return 'unknown', [], []
        
        if ethylene_ppm > p['critical_high']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Ethylene {ethylene_ppm:.1f} ppm is very high'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌿 Consider reducing ethylene generation or ventilating',
                'priority': 'medium'
            })
        elif ethylene_ppm < p['warning_low']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Ethylene {ethylene_ppm:.1f} ppm is too low for effective ripening'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌿 Increase ethylene to {p["optimal_min"]}-{p["optimal_max"]} ppm',
                'priority': 'high'
            })
        elif ethylene_ppm < p['optimal_min']:
            recommendations.append({
                'type': 'action',
                'message': f'🌿 Ethylene {ethylene_ppm:.1f} ppm - Consider increasing to {p["optimal_min"]}+ ppm',
                'priority': 'low'
            })
        else:
            recommendations.append({
                'type': 'status',
                'message': f'🌿 Ethylene {ethylene_ppm:.1f} ppm is in optimal range ✓',
                'priority': 'info'
            })
        
        return status, alerts, recommendations
    
    def _check_ventilation_schedule(self, batch_start_time):
        if not batch_start_time:
            return None
        
        hours_elapsed = (datetime.now(timezone.utc) - batch_start_time).total_seconds() / 3600
        interval = self.params['ventilation']['interval_hours']
        duration = self.params['ventilation']['duration_minutes']
        
        hours_since_last_vent = hours_elapsed % interval
        
        if hours_since_last_vent < 0.5:
            return {
                'type': 'action',
                'message': f'💨 VENTILATION TIME: Open vents for {duration} minutes to clear CO₂',
                'priority': 'high'
            }
        elif hours_since_last_vent > interval - 1:
            next_vent = interval - hours_since_last_vent
            return {
                'type': 'status',
                'message': f'💨 Next ventilation in {next_vent*60:.0f} minutes',
                'priority': 'info'
            }
        
        return None


# ============================================================================
# DATA FUNCTIONS
# ============================================================================
def celsius_to_fahrenheit(celsius):
    if celsius is None:
        return None
    return (celsius * 9/5) + 32


def get_azure_data():
    """Fetch data from Azure Table Storage"""
    try:
        from azure.data.tables import TableServiceClient
        
        connection_string = st.secrets['azure']['storage_connection_string']
        table_name = st.secrets['azure'].get('table_name', 'sensordata')
        
        service = TableServiceClient.from_connection_string(connection_string)
        table_client = service.get_table_client(table_name)
        
        # Query last 4 hours of data
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=4)
        cutoff_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        query_filter = f"Timestamp ge datetime'{cutoff_str}'"
        
        entities = table_client.query_entities(query_filter=query_filter)
        
        data = []
        for entity in entities:
            try:
                # Parse timestamp properly
                ts = entity.get('Timestamp') or entity.get('timestamp')
                if ts and not isinstance(ts, datetime):
                    ts = pd.to_datetime(ts)
                
                data.append({
                    'station': entity.get('PartitionKey', 'unknown'),
                    'timestamp': ts,
                    'temperature': float(entity['temperature']) if entity.get('temperature') else None,
                    'humidity': float(entity['humidity']) if entity.get('humidity') else None,
                    'ethylene': float(entity['ethylene']) if entity.get('ethylene') else None,
                })
            except Exception:
                continue
        
        return data, "Connected to Azure", len(data)
        
    except ImportError:
        return [], "Azure SDK not installed", 0
    except KeyError:
        return [], "Azure secrets not configured", 0
    except Exception as e:
        return [], f"Error: {str(e)[:50]}", 0


def generate_demo_data():
    """Generate realistic demo data - BOTH stations have full sensors"""
    import random
    data = []
    current_time = datetime.now(timezone.utc)
    
    for i in range(480, 0, -1):
        timestamp = current_time - timedelta(seconds=i * 30)
        
        # Station 1 - Full sensors
        data.append({
            'station': 'station1-raspberry-pi',
            'timestamp': timestamp,
            'temperature': 18.5 + random.uniform(-0.5, 0.5),
            'humidity': 92.0 + random.uniform(-2, 2),
            'ethylene': 45.0 + random.uniform(-10, 15)
        })
        
        # Station 2 - Also full sensors now!
        data.append({
            'station': 'station2',
            'timestamp': timestamp,
            'temperature': 18.2 + random.uniform(-0.5, 0.5),
            'humidity': 91.5 + random.uniform(-2, 2),
            'ethylene': 48.0 + random.uniform(-8, 12)
        })
    
    return data


def get_latest_readings(data):
    """Get the most recent readings for each station"""
    if not data:
        return None, None
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    station1_data = df[df['station'].str.contains('station1', case=False, na=False)]
    station2_data = df[df['station'].str.contains('station2', case=False, na=False)]
    
    latest_station1 = None
    latest_station2 = None
    
    if not station1_data.empty:
        latest_station1 = station1_data.sort_values('timestamp').iloc[-1].to_dict()
    
    if not station2_data.empty:
        latest_station2 = station2_data.sort_values('timestamp').iloc[-1].to_dict()
    
    return latest_station1, latest_station2


# ============================================================================
# UI COMPONENTS
# ============================================================================
def render_header():
    st.markdown("""
    <div style='text-align: center; padding: 20px 0 30px 0;'>
        <h1 style='font-size: 3rem; margin-bottom: 5px; 
            background: linear-gradient(90deg, #3fb950, #58a6ff, #3fb950); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-family: "Outfit", sans-serif; font-weight: 700;'>
            🥑 S&L Cold Storage
        </h1>
        <p style='color: #8b949e; font-size: 1.3rem; margin-top: 0; font-family: "Outfit", sans-serif;'>
            AI-Powered Avocado Ripening System
        </p>
    </div>
    """, unsafe_allow_html=True)


def render_ai_panel(analysis_result):
    status = analysis_result['status']
    alerts = analysis_result['alerts']
    recommendations = analysis_result['recommendations']
    
    header_colors = {
        'optimal': '#3fb950',
        'warning': '#d29922',
        'critical': '#f85149'
    }
    header_color = header_colors.get(status, '#3fb950')
    
    st.markdown(f"""
    <div class="ai-panel">
        <div class="ai-panel-header">
            <span style="font-size: 1.5rem;">🤖</span>
            <span class="ai-panel-title" style="color: {header_color};">AI Ripening Advisor</span>
        </div>
    """, unsafe_allow_html=True)
    
    for alert in alerts:
        alert_class = 'alert-critical' if alert['type'] == 'critical' else 'alert-warning'
        st.markdown(f'<div class="{alert_class}">{alert["message"]}</div>', unsafe_allow_html=True)
    
    st.markdown("<h4 style='color: #8b949e; margin-top: 16px;'>Recommendations:</h4>", unsafe_allow_html=True)
    
    for rec in recommendations:
        rec_class = 'ai-recommendation-action' if rec.get('priority') in ['critical', 'high'] else 'ai-recommendation'
        st.markdown(f'<div class="{rec_class}">{rec["message"]}</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def render_ripening_progress(analysis_result):
    progress = analysis_result['progress_percent']
    stage = analysis_result['ripening_stage']
    time_remaining = analysis_result['time_remaining']
    
    stage_colors = {
        'Green': 'stage-green',
        'Breaking': 'stage-breaking',
        'Ripe': 'stage-ripe',
        'Ready-to-Eat': 'stage-ready'
    }
    
    stage_class = stage_colors.get(stage, 'stage-green')
    
    st.markdown("""
    <div class="ripening-progress-container">
        <h3 style="color: #58a6ff; margin-bottom: 16px;">🥑 Ripening Progress</h3>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="color: #8b949e; margin-bottom: 8px;">Current Stage</p>
            <span class="ripening-stage {stage_class}">{stage}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="color: #8b949e; margin-bottom: 8px;">Progress</p>
            <p style="font-family: 'JetBrains Mono', monospace; font-size: 2rem; color: #3fb950; margin: 0;">
                {progress:.0f}%
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        if time_remaining is not None:
            days = int(time_remaining // 24)
            hours = int(time_remaining % 24)
            st.markdown(f"""
            <div style="text-align: center;">
                <p style="color: #8b949e; margin-bottom: 8px;">Est. Time Remaining</p>
                <p style="font-family: 'JetBrains Mono', monospace; font-size: 1.5rem; color: #58a6ff; margin: 0;">
                    {days}d {hours}h
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    st.progress(progress / 100)
    
    st.markdown("""
    <div style="display: flex; justify-content: space-between; margin-top: 16px; padding: 0 10px;">
        <span style="color: #238636;">🟢 Green</span>
        <span style="color: #9e6a03;">🟡 Breaking</span>
        <span style="color: #f0883e;">🟠 Ripe</span>
        <span style="color: #da3633;">🔴 Ready</span>
    </div>
    </div>
    """, unsafe_allow_html=True)


def render_action_checklist():
    st.markdown("""
    <div style="background: #161b22; border-radius: 12px; padding: 20px; border: 1px solid #30363d;">
        <h3 style="color: #58a6ff; margin-bottom: 16px;">📋 Operator Checklist</h3>
    """, unsafe_allow_html=True)
    
    checklist = [
        ("🌡️", "Check temp is 60-68°F"),
        ("💧", "Verify humidity 90-95%"),
        ("🌿", "Confirm ethylene 10-100 ppm"),
        ("💨", "Vent room every 12 hours"),
        ("👁️", "Inspect fruit color"),
        ("📝", "Log any issues"),
    ]
    
    for icon, text in checklist:
        st.markdown(f"""
        <div class="checklist-item">
            <span style="font-size: 1.2rem;">{icon}</span>
            <span style="color: #c9d1d9;">{text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def create_gauge_chart(value, title, min_val, max_val, optimal_min, optimal_max, unit):
    if value is None:
        color = "#8b949e"
        value = 0
    elif optimal_min <= value <= optimal_max:
        color = "#3fb950"
    else:
        color = "#f85149"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': title, 'font': {'size': 16, 'color': '#c9d1d9', 'family': 'Outfit'}},
        number={'suffix': f" {unit}", 'font': {'size': 28, 'color': '#ffffff', 'family': 'JetBrains Mono'}},
        gauge={
            'axis': {'range': [min_val, max_val], 'tickcolor': '#8b949e'},
            'bar': {'color': color, 'thickness': 0.75},
            'bgcolor': '#21262d',
            'borderwidth': 2,
            'bordercolor': '#30363d',
            'steps': [
                {'range': [min_val, optimal_min], 'color': '#1a2332'},
                {'range': [optimal_min, optimal_max], 'color': '#0d2818'},
                {'range': [optimal_max, max_val], 'color': '#2d1810'},
            ],
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#c9d1d9'},
        height=220,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_trend_chart(df, column, title, color, optimal_min=None, optimal_max=None):
    fig = go.Figure()
    
    if optimal_min is not None and optimal_max is not None:
        fig.add_hrect(
            y0=optimal_min, y1=optimal_max,
            fillcolor="rgba(63, 185, 80, 0.1)",
            line_width=0,
        )
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df[column],
        mode='lines',
        name=title,
        line=dict(color=color, width=2),
        fill='tozeroy',
        fillcolor=f'rgba({int(color[1:3], 16)}, {int(color[3:5], 16)}, {int(color[5:7], 16)}, 0.1)'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#c9d1d9')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(13, 17, 23, 0.8)',
        font=dict(color='#8b949e'),
        height=300,
        margin=dict(l=40, r=20, t=50, b=40),
        xaxis=dict(gridcolor='#21262d', showgrid=True),
        yaxis=dict(gridcolor='#21262d', showgrid=True),
        showlegend=False
    )
    
    return fig


# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    # Initialize session state
    if 'batch_start_time' not in st.session_state:
        st.session_state.batch_start_time = None
    if 'batch_season' not in st.session_state:
        st.session_state.batch_season = 'mid_season'
    if 'batch_name' not in st.session_state:
        st.session_state.batch_name = None
    
    render_header()
    
    # Check for Azure secrets
    has_azure_secrets = False
    try:
        if 'azure' in st.secrets and st.secrets['azure'].get('storage_connection_string'):
            has_azure_secrets = True
    except Exception:
        pass
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        if has_azure_secrets:
            demo_mode = st.checkbox("Demo Mode", value=False)
        else:
            st.warning("⚠️ Azure not configured")
            demo_mode = True
        
        st.markdown("---")
        st.markdown("### 🥑 Batch Management")
        
        batch_name = st.text_input("Batch Name", value=st.session_state.batch_name or "", placeholder="e.g., Batch-001")
        
        season = st.selectbox(
            "Avocado Season",
            options=['early_season', 'mid_season', 'late_season'],
            format_func=lambda x: x.replace('_', ' ').title(),
            index=1
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                st.session_state.batch_start_time = datetime.now(timezone.utc)
                st.session_state.batch_season = season
                st.session_state.batch_name = batch_name
                st.success("Started!")
        
        with col2:
            if st.button("⏹️ End", use_container_width=True):
                st.session_state.batch_start_time = None
                st.session_state.batch_name = None
                st.info("Ended")
        
        if st.session_state.batch_start_time:
            elapsed = datetime.now(timezone.utc) - st.session_state.batch_start_time
            hours_elapsed = elapsed.total_seconds() / 3600
            st.markdown(f"""
            <div class="batch-card">
                <div class="batch-header">📦 Active Batch</div>
                <div class="batch-detail">Name: <span class="batch-value">{st.session_state.batch_name or 'Unnamed'}</span></div>
                <div class="batch-detail">Season: <span class="batch-value">{st.session_state.batch_season.replace('_', ' ').title()}</span></div>
                <div class="batch-detail">Elapsed: <span class="batch-value">{int(hours_elapsed)}h {int((hours_elapsed % 1) * 60)}m</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🔄 Refresh")
        auto_refresh = st.checkbox("Auto-refresh", value=True)
        refresh_interval = st.slider("Interval (sec)", 10, 60, 30)
    
    # Get data
    if demo_mode:
        data = generate_demo_data()
        connection_status = "Demo Mode"
        record_count = len(data)
    else:
        data, connection_status, record_count = get_azure_data()
    
    latest_station1, latest_station2 = get_latest_readings(data)
    
    # Get readings for AI analysis (average of both stations)
    temp_f = None
    humidity = None
    ethylene = None
    
    temps = []
    hums = []
    eths = []
    
    if latest_station1:
        if latest_station1.get('temperature') is not None:
            temps.append(celsius_to_fahrenheit(latest_station1['temperature']))
        if latest_station1.get('humidity') is not None:
            hums.append(latest_station1['humidity'])
        if latest_station1.get('ethylene') is not None:
            eths.append(latest_station1['ethylene'])
    
    if latest_station2:
        if latest_station2.get('temperature') is not None:
            temps.append(celsius_to_fahrenheit(latest_station2['temperature']))
        if latest_station2.get('humidity') is not None:
            hums.append(latest_station2['humidity'])
        if latest_station2.get('ethylene') is not None:
            eths.append(latest_station2['ethylene'])
    
    if temps:
        temp_f = sum(temps) / len(temps)
    if hums:
        humidity = sum(hums) / len(hums)
    if eths:
        ethylene = sum(eths) / len(eths)
    
    # AI Analysis
    ai_engine = AIRipeningEngine()
    analysis = ai_engine.analyze_conditions(
        temperature_f=temp_f,
        humidity=humidity,
        ethylene_ppm=ethylene,
        batch_start_time=st.session_state.batch_start_time,
        season=st.session_state.batch_season
    )
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 AI Dashboard", "📊 Live Sensors", "📈 Trends", "📋 Reports"])
    
    # TAB 1: AI DASHBOARD
    with tab1:
        render_ai_panel(analysis)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.session_state.batch_start_time:
            render_ripening_progress(analysis)
        else:
            st.info("💡 Start a batch in the sidebar to track ripening progress")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### 📊 Current Conditions (Average)")
            
            gauge_cols = st.columns(3)
            
            with gauge_cols[0]:
                fig = create_gauge_chart(temp_f or 0, "Temperature", 30, 100, 60, 68, "°F")
                st.plotly_chart(fig, use_container_width=True)
            
            with gauge_cols[1]:
                fig = create_gauge_chart(humidity or 0, "Humidity", 50, 100, 90, 95, "%")
                st.plotly_chart(fig, use_container_width=True)
            
            with gauge_cols[2]:
                fig = create_gauge_chart(ethylene or 0, "Ethylene", 0, 150, 10, 100, "ppm")
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            render_action_checklist()
    
    # TAB 2: LIVE SENSORS
    with tab2:
        st.markdown("### 📡 Live Sensor Readings")
        
        status_cols = st.columns(4)
        with status_cols[0]:
            st.markdown(f"**Status:** {connection_status}")
        with status_cols[1]:
            st.markdown(f"**Records:** {record_count}")
        with status_cols[2]:
            if latest_station1:
                ts = latest_station1.get('timestamp')
                if ts:
                    st.markdown(f"**Last Update:** {pd.to_datetime(ts).strftime('%H:%M:%S')}")
        with status_cols[3]:
            if st.button("🔄 Refresh"):
                st.rerun()
        
        st.markdown("---")
        
        # Station 1
        st.markdown("#### 🏭 Station 1 - Ripening Room A")
        if latest_station1:
            cols = st.columns(4)
            with cols[0]:
                temp_c = latest_station1.get('temperature')
                temp_f_val = celsius_to_fahrenheit(temp_c) if temp_c else None
                st.metric("Temperature", f"{temp_f_val:.1f}°F" if temp_f_val else "N/A", 
                         delta=f"{temp_c:.1f}°C" if temp_c else None)
            with cols[1]:
                hum = latest_station1.get('humidity')
                st.metric("Humidity", f"{hum:.1f}%" if hum else "N/A")
            with cols[2]:
                eth = latest_station1.get('ethylene')
                st.metric("Ethylene", f"{eth:.1f} ppm" if eth else "N/A")
            with cols[3]:
                st.metric("Status", "🟢 Online")
        else:
            st.warning("No data from Station 1")
        
        st.markdown("---")
        
        # Station 2
        st.markdown("#### 🏭 Station 2 - Ripening Room B")
        if latest_station2:
            cols = st.columns(4)
            with cols[0]:
                temp_c = latest_station2.get('temperature')
                temp_f_val = celsius_to_fahrenheit(temp_c) if temp_c else None
                st.metric("Temperature", f"{temp_f_val:.1f}°F" if temp_f_val else "N/A",
                         delta=f"{temp_c:.1f}°C" if temp_c else None)
            with cols[1]:
                hum = latest_station2.get('humidity')
                st.metric("Humidity", f"{hum:.1f}%" if hum else "N/A")
            with cols[2]:
                eth = latest_station2.get('ethylene')
                st.metric("Ethylene", f"{eth:.1f} ppm" if eth else "N/A")
            with cols[3]:
                st.metric("Status", "🟢 Online")
        else:
            st.warning("No data from Station 2")
    
    # TAB 3: TRENDS
    with tab3:
        st.markdown("### 📈 Historical Trends")
        
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            station_filter = st.selectbox(
                "Select Station",
                options=['All', 'Station 1', 'Station 2']
            )
            
            if station_filter == 'Station 1':
                df = df[df['station'].str.contains('station1', case=False, na=False)]
            elif station_filter == 'Station 2':
                df = df[df['station'].str.contains('station2', case=False, na=False)]
            
            time_range = st.selectbox(
                "Time Range",
                options=['Last 1 Hour', 'Last 2 Hours', 'Last 4 Hours', 'All Data']
            )
            
            if time_range != 'All Data':
                hours = int(time_range.split()[1])
                cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
                # Convert cutoff to pandas timestamp for comparison
                cutoff = pd.Timestamp(cutoff)
                df = df[df['timestamp'] > cutoff]
            
            df = df.sort_values('timestamp')
            
            if not df.empty:
                # Temperature
                if df['temperature'].notna().any():
                    df_temp = df.copy()
                    df_temp['temperature_f'] = df_temp['temperature'].apply(
                        lambda x: celsius_to_fahrenheit(x) if pd.notna(x) else None
                    )
                    fig = create_trend_chart(df_temp, 'temperature_f', 'Temperature (°F)', '#f0883e', 60, 68)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Humidity
                if df['humidity'].notna().any():
                    fig = create_trend_chart(df, 'humidity', 'Humidity (%)', '#58a6ff', 90, 95)
                    st.plotly_chart(fig, use_container_width=True)
                
                # Ethylene
                if df['ethylene'].notna().any():
                    fig = create_trend_chart(df, 'ethylene', 'Ethylene (ppm)', '#3fb950', 10, 100)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No data for selected filters")
        else:
            st.warning("No data available")
    
    # TAB 4: REPORTS
    with tab4:
        st.markdown("### 📋 Reports & Reference")
        
        if st.session_state.batch_start_time:
            st.markdown("#### Current Batch Summary")
            
            elapsed = datetime.now(timezone.utc) - st.session_state.batch_start_time
            hours_elapsed = elapsed.total_seconds() / 3600
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Batch Name", st.session_state.batch_name or "Unnamed")
                st.metric("Season", st.session_state.batch_season.replace('_', ' ').title())
            
            with col2:
                st.metric("Time Elapsed", f"{int(hours_elapsed)}h {int((hours_elapsed % 1) * 60)}m")
                st.metric("Progress", f"{analysis['progress_percent']:.0f}%")
            
            with col3:
                st.metric("Current Stage", analysis['ripening_stage'])
                if analysis['time_remaining']:
                    days = int(analysis['time_remaining'] // 24)
                    hours = int(analysis['time_remaining'] % 24)
                    st.metric("Est. Remaining", f"{days}d {hours}h")
            
            st.markdown("---")
            
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Data (CSV)",
                    data=csv,
                    file_name=f"ripening_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        else:
            st.info("💡 Start a batch to generate reports")
        
        st.markdown("---")
        st.markdown("#### 🥑 Avocado Ripening Reference")
        
        ref_col1, ref_col2 = st.columns(2)
        
        with ref_col1:
            st.markdown("""
            **Optimal Conditions:**
            - Temperature: 60-68°F (15-20°C)
            - Humidity: 90-95% RH
            - Ethylene: 10-100 ppm
            - Ventilate: Every 12 hours for 20 min
            """)
        
        with ref_col2:
            st.markdown("""
            **Ripening Timeline:**
            - Early Season: 48h ethylene, 5-6 days
            - Mid Season: 36h ethylene, 4-5 days
            - Late Season: 24h ethylene, 3-4 days
            """)
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p><strong>S&L Cold Storage</strong> - AI Ripening System v3.1</p>
        <p style="font-size: 0.85rem;">Powered by Azure IoT | Built with Streamlit</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()
