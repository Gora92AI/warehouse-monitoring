"""
S&L Cold Storage - AI Avocado Ripening System
Version: 3.4 - Fast & Clean Edition

Changes:
- NO auto-refresh blocking
- Silent background data fetch (no loading indicators)
- Single room with 2 sensors display
- Persistent batch storage
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta, timezone
import json

# ============================================================================
# PAGE CONFIG - MUST BE FIRST
# ============================================================================
st.set_page_config(
    page_title="S&L Cold Storage - AI Ripening",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS STYLING
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* Hide Streamlit branding */
    #MainMenu, footer, header, [data-testid="stToolbar"], .stDeployButton {
        display: none !important;
    }
    
    /* Force sidebar always visible */
    [data-testid="collapsedControl"] { display: none !important; }
    section[data-testid="stSidebar"] { 
        width: 300px !important; 
        min-width: 300px !important; 
    }
    
    .stApp {
        background: linear-gradient(145deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
        font-family: 'Outfit', sans-serif;
    }
    
    /* Metric Cards */
    div[data-testid="metric-container"] {
        background: linear-gradient(135deg, #1a2332 0%, #0d1117 100%);
        border: 1px solid #238636;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 8px 32px rgba(35, 134, 54, 0.15);
    }
    
    div[data-testid="metric-container"] label {
        color: #8b949e !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 500 !important;
    }
    
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
    }
    
    h1, h2, h3 { color: #58a6ff !important; font-family: 'Outfit', sans-serif !important; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab"] {
        background: #21262d;
        color: #8b949e;
        border-radius: 8px 8px 0 0;
        border: 1px solid #30363d;
        padding: 10px 20px;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: #ffffff;
    }
    
    /* Alert boxes */
    .alert-critical {
        background: linear-gradient(135deg, #da3633 0%, #b62324 100%);
        border: 1px solid #f85149;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
        font-weight: 500;
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #9e6a03 0%, #845306 100%);
        border: 1px solid #d29922;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
    }
    
    .alert-success {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        border: 1px solid #3fb950;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
    }
    
    /* AI Panel */
    .ai-panel {
        background: linear-gradient(145deg, #1a2332 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
    }
    
    .ai-recommendation {
        background: #21262d;
        border-left: 4px solid #3fb950;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        color: #c9d1d9;
    }
    
    .ai-recommendation-urgent {
        background: #21262d;
        border-left: 4px solid #f85149;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        color: #c9d1d9;
    }
    
    /* Batch card */
    .batch-card {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        color: #ffffff;
    }
    
    /* Sensor card */
    .sensor-card {
        background: #21262d;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px;
        margin: 8px 0;
    }
    
    .sensor-online { color: #3fb950; }
    .sensor-offline { color: #f85149; }
    
    /* Progress stages */
    .stage-green { background: #238636; color: white; padding: 8px 16px; border-radius: 20px; }
    .stage-breaking { background: #9e6a03; color: white; padding: 8px 16px; border-radius: 20px; }
    .stage-ripe { background: #f0883e; color: white; padding: 8px 16px; border-radius: 20px; }
    .stage-ready { background: #da3633; color: white; padding: 8px 16px; border-radius: 20px; }
    
    /* Quick ref */
    .quick-ref-box {
        background: #21262d;
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# CONSTANTS
# ============================================================================
AVOCADO_PARAMS = {
    'temperature': {'optimal_min': 60, 'optimal_max': 68, 'critical_high': 86, 'critical_low': 40},
    'humidity': {'optimal_min': 90, 'optimal_max': 95, 'warning_low': 85, 'critical_low': 80},
    'ethylene': {'optimal_min': 10, 'optimal_max': 100, 'warning_low': 5, 'critical_high': 150},
    'ripening_time': {
        'early_season': {'ethylene_hours': 48, 'total_days': 6},
        'mid_season': {'ethylene_hours': 36, 'total_days': 5},
        'late_season': {'ethylene_hours': 24, 'total_days': 4},
    }
}

# ============================================================================
# BATCH MANAGER - PERSISTENT STORAGE
# ============================================================================
class BatchManager:
    def __init__(self):
        self.table_client = None
        try:
            from azure.data.tables import TableServiceClient
            conn = st.secrets['azure']['storage_connection_string']
            service = TableServiceClient.from_connection_string(conn)
            try:
                service.create_table("batches")
            except:
                pass
            self.table_client = service.get_table_client("batches")
        except:
            pass
    
    def get_active_batch(self):
        if not self.table_client:
            return None
        try:
            entity = self.table_client.get_entity("batch", "active")
            if entity.get('is_active'):
                return {
                    'name': entity.get('name', 'Unnamed'),
                    'season': entity.get('season', 'mid_season'),
                    'start_time': datetime.fromisoformat(entity['start_time']),
                    'is_active': True
                }
        except:
            pass
        return None
    
    def start_batch(self, name, season):
        if not self.table_client:
            return False
        try:
            start = datetime.now(timezone.utc)
            self.table_client.upsert_entity({
                'PartitionKey': 'batch',
                'RowKey': 'active',
                'name': name or f"Batch-{start.strftime('%m%d-%H%M')}",
                'season': season,
                'start_time': start.isoformat(),
                'is_active': True
            })
            return True
        except:
            return False
    
    def end_batch(self):
        if not self.table_client:
            return False
        try:
            entity = self.table_client.get_entity("batch", "active")
            entity['is_active'] = False
            entity['end_time'] = datetime.now(timezone.utc).isoformat()
            self.table_client.upsert_entity(entity)
            return True
        except:
            return False

# ============================================================================
# DATA FUNCTIONS - SILENT BACKGROUND FETCH
# ============================================================================
def c_to_f(c):
    return (c * 9/5) + 32 if c is not None else None

@st.cache_data(ttl=20, show_spinner=False)  # Cache 20s, NO spinner
def fetch_sensor_data():
    """Silently fetch data from Azure - no loading indicators"""
    try:
        from azure.data.tables import TableServiceClient
        conn = st.secrets['azure']['storage_connection_string']
        table = st.secrets['azure']['table_name']
        
        service = TableServiceClient.from_connection_string(conn)
        client = service.get_table_client(table)
        
        cutoff = datetime.now(timezone.utc) - timedelta(hours=4)
        data = []
        
        for entity in client.list_entities():
            try:
                ts = entity.get('timestamp') or entity.get('Timestamp')
                if ts:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    if ts.tzinfo is None:
                        ts = ts.replace(tzinfo=timezone.utc)
                    if ts >= cutoff:
                        data.append({
                            'station': entity.get('station', entity.get('PartitionKey', 'unknown')),
                            'timestamp': ts,
                            'temperature': float(entity['temperature']) if entity.get('temperature') else None,
                            'humidity': float(entity['humidity']) if entity.get('humidity') else None,
                            'ethylene': float(entity['ethylene']) if entity.get('ethylene') else None
                        })
            except:
                continue
        
        return data, True
    except:
        return [], False

def get_demo_data():
    """Demo data for testing"""
    import random
    data = []
    now = datetime.now(timezone.utc)
    for i in range(100):
        ts = now - timedelta(minutes=i*2)
        data.append({
            'station': 'sensor1',
            'timestamp': ts,
            'temperature': 18.5 + random.uniform(-0.5, 0.5),
            'humidity': 92 + random.uniform(-2, 2),
            'ethylene': 45 + random.uniform(-10, 15)
        })
        data.append({
            'station': 'sensor2',
            'timestamp': ts,
            'temperature': 18.2 + random.uniform(-0.5, 0.5),
            'humidity': 91.5 + random.uniform(-2, 2),
            'ethylene': 48 + random.uniform(-8, 12)
        })
    return data

def get_latest(data):
    """Get latest reading from each sensor"""
    if not data:
        return None, None
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    s1 = df[df['station'].str.contains('1', na=False)].sort_values('timestamp')
    s2 = df[df['station'].str.contains('2', na=False)].sort_values('timestamp')
    
    return (s1.iloc[-1].to_dict() if len(s1) else None,
            s2.iloc[-1].to_dict() if len(s2) else None)

# ============================================================================
# AI ENGINE
# ============================================================================
class AIEngine:
    def __init__(self):
        self.p = AVOCADO_PARAMS
    
    def analyze(self, temp_f, humidity, ethylene, batch_start=None, season='mid_season'):
        alerts = []
        recs = []
        status = 'optimal'
        
        # Temperature
        if temp_f:
            if temp_f >= self.p['temperature']['critical_high']:
                status = 'critical'
                alerts.append({'type': 'critical', 'msg': f'🚨 CRITICAL: {temp_f:.1f}°F - Risk of flesh darkening!'})
                recs.append({'msg': '🌡️ IMMEDIATELY lower temperature below 68°F', 'urgent': True})
            elif temp_f > self.p['temperature']['optimal_max']:
                status = 'warning' if status != 'critical' else status
                alerts.append({'type': 'warning', 'msg': f'⚠️ Temperature {temp_f:.1f}°F above optimal (60-68°F)'})
                recs.append({'msg': f'🌡️ Reduce temperature by {temp_f - 68:.1f}°F', 'urgent': True})
            elif temp_f < self.p['temperature']['critical_low']:
                status = 'critical'
                alerts.append({'type': 'critical', 'msg': f'🚨 CRITICAL: {temp_f:.1f}°F - Chilling injury risk!'})
                recs.append({'msg': '🌡️ IMMEDIATELY raise temperature above 40°F', 'urgent': True})
            elif temp_f < self.p['temperature']['optimal_min']:
                status = 'warning' if status != 'critical' else status
                alerts.append({'type': 'warning', 'msg': f'⚠️ Temperature {temp_f:.1f}°F below optimal (60-68°F)'})
                recs.append({'msg': f'🌡️ Increase temperature by {60 - temp_f:.1f}°F', 'urgent': False})
        
        # Humidity
        if humidity:
            if humidity < self.p['humidity']['critical_low']:
                status = 'critical'
                alerts.append({'type': 'critical', 'msg': f'🚨 CRITICAL: Humidity {humidity:.1f}% - Quality loss!'})
                recs.append({'msg': '💧 IMMEDIATELY increase humidification', 'urgent': True})
            elif humidity < self.p['humidity']['warning_low']:
                status = 'warning' if status != 'critical' else status
                alerts.append({'type': 'warning', 'msg': f'⚠️ Humidity {humidity:.1f}% below optimal (90-95%)'})
                recs.append({'msg': f'💧 Increase humidity by {90 - humidity:.1f}%', 'urgent': True})
        
        # Ethylene
        if ethylene:
            if ethylene > self.p['ethylene']['critical_high']:
                status = 'warning' if status != 'critical' else status
                alerts.append({'type': 'warning', 'msg': f'⚠️ Ethylene {ethylene:.1f} ppm very high'})
                recs.append({'msg': '🌬️ Ventilate room to reduce ethylene', 'urgent': True})
            elif ethylene < self.p['ethylene']['warning_low']:
                alerts.append({'type': 'warning', 'msg': f'⚠️ Ethylene {ethylene:.1f} ppm very low'})
                recs.append({'msg': '🍌 Consider adding ethylene source', 'urgent': False})
        
        # Progress
        progress = 0
        stage = 'Green'
        remaining = None
        
        if batch_start:
            elapsed_h = (datetime.now(timezone.utc) - batch_start).total_seconds() / 3600
            total_h = self.p['ripening_time'][season]['total_days'] * 24
            progress = min(100, (elapsed_h / total_h) * 100)
            remaining = max(0, total_h - elapsed_h)
            
            if progress < 20: stage = 'Green'
            elif progress < 50: stage = 'Breaking'
            elif progress < 80: stage = 'Ripe'
            else: stage = 'Ready-to-Eat'
            
            # Ventilation reminder
            if elapsed_h % 12 >= 11.5:
                recs.append({'msg': '🌬️ Ventilation due - open doors for 20 min', 'urgent': False})
        
        if status == 'optimal' and not alerts:
            recs.insert(0, {'msg': '✅ All conditions optimal for ripening', 'urgent': False})
        
        return {
            'status': status,
            'alerts': alerts,
            'recs': recs,
            'stage': stage,
            'progress': progress,
            'remaining': remaining
        }

# ============================================================================
# UI COMPONENTS
# ============================================================================
def render_header():
    st.markdown("""
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <h1 style='font-size: 2.5rem; margin-bottom: 5px; 
            background: linear-gradient(90deg, #3fb950, #58a6ff); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            🥑 S&L Cold Storage
        </h1>
        <p style='color: #8b949e; font-size: 1.1rem;'>AI-Powered Avocado Ripening System</p>
    </div>
    """, unsafe_allow_html=True)

def create_gauge(value, title, min_v, max_v, opt_min, opt_max, unit):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value or 0,
        title={'text': title, 'font': {'color': '#c9d1d9', 'size': 14}},
        number={'suffix': unit, 'font': {'color': '#fff', 'size': 22}},
        gauge={
            'axis': {'range': [min_v, max_v], 'tickcolor': '#8b949e'},
            'bar': {'color': '#3fb950'},
            'bgcolor': '#21262d',
            'steps': [
                {'range': [min_v, opt_min], 'color': '#9e6a03'},
                {'range': [opt_min, opt_max], 'color': '#238636'},
                {'range': [opt_max, max_v], 'color': '#9e6a03'}
            ]
        }
    ))
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=180,
        margin=dict(l=20, r=20, t=40, b=10)
    )
    return fig

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    render_header()
    
    # Init
    batch_mgr = BatchManager()
    has_azure = False
    try:
        has_azure = bool(st.secrets.get('azure', {}).get('storage_connection_string'))
    except:
        pass
    
    active_batch = batch_mgr.get_active_batch() if has_azure else None
    
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        demo_mode = st.checkbox("Demo Mode", value=not has_azure)
        
        st.markdown("---")
        st.markdown("### 🥑 Batch Management")
        
        batch_name = st.text_input("Batch Name", placeholder="e.g., Batch-001")
        season = st.selectbox("Season", ['early_season', 'mid_season', 'late_season'],
                             format_func=lambda x: x.replace('_', ' ').title(), index=1)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶️ Start", use_container_width=True):
                if batch_mgr.start_batch(batch_name, season):
                    st.success("Started!")
                    st.rerun()
        with c2:
            if st.button("⏹️ End", use_container_width=True):
                if batch_mgr.end_batch():
                    st.info("Ended")
                    st.rerun()
        
        if active_batch:
            elapsed = (datetime.now(timezone.utc) - active_batch['start_time']).total_seconds() / 3600
            st.markdown(f"""
            <div class="batch-card">
                <div style="font-weight: 600;">📦 Active Batch</div>
                <div>Name: <b>{active_batch['name']}</b></div>
                <div>Season: <b>{active_batch['season'].replace('_', ' ').title()}</b></div>
                <div>Elapsed: <b>{int(elapsed)}h {int((elapsed % 1) * 60)}m</b></div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.markdown("<p style='color:#8b949e; font-size:0.8rem; text-align:center;'>S&L Cold Storage v3.4</p>", 
                   unsafe_allow_html=True)
    
    # === GET DATA (SILENT) ===
    if demo_mode:
        data = get_demo_data()
    else:
        data, _ = fetch_sensor_data()
    
    sensor1, sensor2 = get_latest(data)
    
    # Average readings for AI
    temps, hums, eths = [], [], []
    for s in [sensor1, sensor2]:
        if s:
            if s.get('temperature'): temps.append(c_to_f(s['temperature']))
            if s.get('humidity'): hums.append(s['humidity'])
            if s.get('ethylene'): eths.append(s['ethylene'])
    
    avg_temp = sum(temps)/len(temps) if temps else None
    avg_hum = sum(hums)/len(hums) if hums else None
    avg_eth = sum(eths)/len(eths) if eths else None
    
    # AI Analysis
    ai = AIEngine()
    analysis = ai.analyze(avg_temp, avg_hum, avg_eth,
                         active_batch['start_time'] if active_batch else None,
                         active_batch['season'] if active_batch else 'mid_season')
    
    # === TABS ===
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 AI Dashboard", "📊 Sensors", "📈 Trends", "📋 Reports"])
    
    # === TAB 1: AI DASHBOARD ===
    with tab1:
        # AI Panel
        status_colors = {'optimal': '#3fb950', 'warning': '#d29922', 'critical': '#f85149'}
        st.markdown(f"""
        <div class="ai-panel">
            <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 16px;">
                <span style="font-size: 1.5rem;">🤖</span>
                <span style="font-size: 1.3rem; font-weight: 600; color: {status_colors[analysis['status']]};">
                    AI Ripening Advisor
                </span>
            </div>
        """, unsafe_allow_html=True)
        
        for alert in analysis['alerts']:
            cls = 'alert-critical' if alert['type'] == 'critical' else 'alert-warning'
            st.markdown(f'<div class="{cls}">{alert["msg"]}</div>', unsafe_allow_html=True)
        
        if analysis['recs']:
            st.markdown("<h4 style='color: #8b949e;'>Recommendations:</h4>", unsafe_allow_html=True)
            for rec in analysis['recs']:
                cls = 'ai-recommendation-urgent' if rec['urgent'] else 'ai-recommendation'
                st.markdown(f'<div class="{cls}">{rec["msg"]}</div>', unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Progress (if batch active)
        if active_batch:
            st.markdown(f"""
            <div class="ai-panel">
                <h3 style="color: #58a6ff;">🥑 Ripening Progress</h3>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns(3)
            with c1:
                stage_cls = {'Green': 'stage-green', 'Breaking': 'stage-breaking', 
                            'Ripe': 'stage-ripe', 'Ready-to-Eat': 'stage-ready'}
                st.markdown(f"""
                <div style="text-align: center;">
                    <p style="color: #8b949e;">Stage</p>
                    <span class="{stage_cls.get(analysis['stage'], 'stage-green')}">{analysis['stage']}</span>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="text-align: center;">
                    <p style="color: #8b949e;">Progress</p>
                    <p style="font-size: 2rem; color: #3fb950; margin: 0;">{analysis['progress']:.0f}%</p>
                </div>
                """, unsafe_allow_html=True)
            with c3:
                if analysis['remaining']:
                    d, h = int(analysis['remaining'] // 24), int(analysis['remaining'] % 24)
                    t = f"{d}d {h}h" if d else f"{h}h"
                else:
                    t = "N/A"
                st.markdown(f"""
                <div style="text-align: center;">
                    <p style="color: #8b949e;">Est. Remaining</p>
                    <p style="font-size: 2rem; color: #58a6ff; margin: 0;">{t}</p>
                </div>
                """, unsafe_allow_html=True)
            
            st.progress(analysis['progress'] / 100)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.info("💡 Start a batch to track ripening progress")
        
        # Gauges
        st.markdown("### 📊 Room Conditions")
        g1, g2, g3 = st.columns(3)
        with g1:
            st.plotly_chart(create_gauge(avg_temp, "Temperature", 30, 100, 60, 68, "°F"), use_container_width=True)
        with g2:
            st.plotly_chart(create_gauge(avg_hum, "Humidity", 50, 100, 90, 95, "%"), use_container_width=True)
        with g3:
            st.plotly_chart(create_gauge(avg_eth, "Ethylene", 0, 150, 10, 100, "ppm"), use_container_width=True)
    
    # === TAB 2: SENSORS (Single Room, 2 Sensors) ===
    with tab2:
        st.markdown("### 🏭 Ripening Room - Sensor Readings")
        st.markdown("*Two sensors monitoring the same room for accuracy*")
        
        st.markdown("---")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 📡 Sensor 1")
            if sensor1:
                temp_f = c_to_f(sensor1.get('temperature'))
                st.metric("Temperature", f"{temp_f:.1f}°F" if temp_f else "N/A")
                st.metric("Humidity", f"{sensor1.get('humidity', 0):.1f}%" if sensor1.get('humidity') else "N/A")
                st.metric("Ethylene", f"{sensor1.get('ethylene', 0):.1f} ppm" if sensor1.get('ethylene') else "N/A")
                st.markdown("<span class='sensor-online'>🟢 Online</span>", unsafe_allow_html=True)
            else:
                st.warning("No data")
        
        with c2:
            st.markdown("#### 📡 Sensor 2")
            if sensor2:
                temp_f = c_to_f(sensor2.get('temperature'))
                st.metric("Temperature", f"{temp_f:.1f}°F" if temp_f else "N/A")
                st.metric("Humidity", f"{sensor2.get('humidity', 0):.1f}%" if sensor2.get('humidity') else "N/A")
                st.metric("Ethylene", f"{sensor2.get('ethylene', 0):.1f} ppm" if sensor2.get('ethylene') else "N/A")
                st.markdown("<span class='sensor-online'>🟢 Online</span>", unsafe_allow_html=True)
            else:
                st.warning("No data")
        
        st.markdown("---")
        
        # Show average
        st.markdown("#### 📊 Room Average")
        a1, a2, a3 = st.columns(3)
        with a1:
            st.metric("Avg Temperature", f"{avg_temp:.1f}°F" if avg_temp else "N/A")
        with a2:
            st.metric("Avg Humidity", f"{avg_hum:.1f}%" if avg_hum else "N/A")
        with a3:
            st.metric("Avg Ethylene", f"{avg_eth:.1f} ppm" if avg_eth else "N/A")
    
    # === TAB 3: TRENDS ===
    with tab3:
        st.markdown("### 📈 Sensor Trends")
        
        metric = st.selectbox("Select Metric", ['temperature', 'humidity', 'ethylene'],
                             format_func=str.title)
        
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            
            fig = go.Figure()
            for station in df['station'].unique():
                sd = df[df['station'] == station].sort_values('timestamp')
                y = sd[metric]
                if metric == 'temperature':
                    y = y.apply(c_to_f)
                
                name = "Sensor 1" if '1' in station else "Sensor 2"
                color = '#3fb950' if '1' in station else '#58a6ff'
                
                fig.add_trace(go.Scatter(x=sd['timestamp'], y=y, mode='lines', 
                                        name=name, line=dict(color=color, width=2)))
            
            # Optimal range
            ranges = {'temperature': (60, 68), 'humidity': (90, 95), 'ethylene': (10, 100)}
            if metric in ranges:
                fig.add_hrect(y0=ranges[metric][0], y1=ranges[metric][1],
                             fillcolor="rgba(35,134,54,0.2)", line_width=0)
            
            units = {'temperature': '°F', 'humidity': '%', 'ethylene': 'ppm'}
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(gridcolor='#21262d'),
                yaxis=dict(title=f"{metric.title()} ({units[metric]})", gridcolor='#21262d'),
                legend=dict(orientation="h", y=1.1),
                height=400,
                margin=dict(l=60, r=20, t=40, b=40)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for trends")
    
    # === TAB 4: REPORTS ===
    with tab4:
        st.markdown("### 📋 Reports & Reference")
        
        if active_batch:
            elapsed = (datetime.now(timezone.utc) - active_batch['start_time']).total_seconds() / 3600
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Batch Name", active_batch['name'])
            with c2:
                st.metric("Time Elapsed", f"{int(elapsed)}h {int((elapsed % 1) * 60)}m")
            with c3:
                st.metric("Current Stage", analysis['stage'])
            
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                st.download_button("📥 Download Data (CSV)", csv, 
                                  f"batch_{active_batch['name']}.csv", "text/csv")
        else:
            st.info("💡 Start a batch to generate reports")
        
        st.markdown("---")
        st.markdown("### 🥑 Quick Reference")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""
            **Optimal Conditions:**
            - 🌡️ Temperature: 60-68°F
            - 💧 Humidity: 90-95%
            - 🌿 Ethylene: 10-100 ppm
            - 💨 Ventilate every 12h for 20 min
            """)
        with c2:
            st.markdown("""
            **Ripening Timeline:**
            - 🌱 Early Season: 5-6 days
            - 🌿 Mid Season: 4-5 days
            - 🍃 Late Season: 3-4 days
            """)
        
        st.markdown("""
        **⚠️ Critical Thresholds:**
        - Temperature >86°F = Flesh darkening risk
        - Temperature <40°F = Chilling injury
        - Humidity <80% = Quality loss
        """)


if __name__ == "__main__":
    main()
