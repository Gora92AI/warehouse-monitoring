"""
S&L Cold Storage - AI Avocado Ripening System
Version: 3.6 - Fixed Trends & Charts

FIXES:
1. Trend charts now load automatically
2. Better timestamp parsing for Azure data
3. Removed strict time filtering that was blocking data
4. Added debug mode to see raw data
"""

import streamlit as st
from datetime import datetime, timedelta, timezone

# ============================================================================
# PAGE CONFIG
# ============================================================================
st.set_page_config(
    page_title="S&L Cold Storage",
    page_icon="🥑",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CSS
# ============================================================================
st.markdown("""
<style>
    #MainMenu, footer, header {display: none !important;}
    [data-testid="collapsedControl"] {display: none !important;}
    section[data-testid="stSidebar"] {width: 280px !important; min-width: 280px !important;}
    .stApp {background: #0d1117;}
    div[data-testid="metric-container"] {
        background: #161b22; border: 1px solid #238636; border-radius: 8px; padding: 12px;
    }
    h1,h2,h3 {color: #58a6ff !important;}
    .alert-critical {background: #da3633; border-radius: 8px; padding: 12px; margin: 8px 0; color: white;}
    .alert-warning {background: #9e6a03; border-radius: 8px; padding: 12px; margin: 8px 0; color: white;}
    .alert-success {background: #238636; border-radius: 8px; padding: 12px; margin: 8px 0; color: white;}
    .batch-card {background: #238636; border-radius: 8px; padding: 12px; margin: 8px 0; color: white;}
</style>
""", unsafe_allow_html=True)

# ============================================================================
# AZURE CONNECTION - Singleton
# ============================================================================
@st.cache_resource(show_spinner=False)
def get_azure_clients():
    """Create connection once and reuse"""
    try:
        from azure.data.tables import TableServiceClient
        conn = st.secrets['azure']['storage_connection_string']
        table_name = st.secrets['azure']['table_name']
        
        service = TableServiceClient.from_connection_string(conn)
        data_client = service.get_table_client(table_name)
        
        try:
            service.create_table("batches")
        except:
            pass
        batch_client = service.get_table_client("batches")
        
        return data_client, batch_client, True
    except Exception as e:
        return None, None, False

# ============================================================================
# DATA FETCH - Optimized
# ============================================================================
def parse_timestamp(ts):
    """Robust timestamp parsing"""
    if ts is None:
        return None
    
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts
    
    if isinstance(ts, str):
        # Try various formats
        for fmt in [
            '%Y-%m-%dT%H:%M:%S.%f%z',
            '%Y-%m-%dT%H:%M:%S%z', 
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
        ]:
            try:
                dt = datetime.strptime(ts.replace('Z', '+00:00').replace('+00:00', ''), fmt.replace('%z', ''))
                return dt.replace(tzinfo=timezone.utc)
            except:
                continue
        
        # Last resort - isoformat
        try:
            clean = ts.replace('Z', '+00:00')
            if '+' not in clean and '-' not in clean[10:]:
                clean += '+00:00'
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            pass
    
    return None

@st.cache_data(ttl=30, show_spinner=False)
def fetch_all_data(max_records=500):
    """
    Fetch data from Azure - returns raw list for processing.
    No time filtering here - let the caller decide.
    """
    data_client, _, connected = get_azure_clients()
    if not connected or not data_client:
        return [], False
    
    try:
        data = []
        count = 0
        
        for entity in data_client.list_entities():
            try:
                # Get timestamp from various possible fields
                ts = None
                for ts_field in ['timestamp', 'Timestamp', 'time', 'datetime', 'created']:
                    if entity.get(ts_field):
                        ts = parse_timestamp(entity.get(ts_field))
                        if ts:
                            break
                
                if not ts:
                    # Use current time as fallback
                    ts = datetime.now(timezone.utc)
                
                # Get station identifier
                station = str(entity.get('station', entity.get('PartitionKey', entity.get('device_id', 'unknown'))))
                
                data.append({
                    'station': station,
                    'timestamp': ts,
                    'temperature': float(entity['temperature']) if entity.get('temperature') is not None else None,
                    'humidity': float(entity['humidity']) if entity.get('humidity') is not None else None,
                    'ethylene': float(entity['ethylene']) if entity.get('ethylene') is not None else None
                })
                
                count += 1
                if count >= max_records:
                    break
                    
            except Exception as e:
                continue
        
        # Sort by timestamp descending (newest first)
        data.sort(key=lambda x: x['timestamp'], reverse=True)
        return data, True
        
    except Exception as e:
        return [], False

def get_latest_readings(data):
    """Extract latest reading for each sensor from data"""
    if not data:
        return None, None
    
    sensor1 = None
    sensor2 = None
    
    for reading in data:
        station = str(reading['station']).lower()
        
        # Determine which sensor
        is_sensor1 = any(x in station for x in ['1', 'sensor1', 'station1', 'one'])
        is_sensor2 = any(x in station for x in ['2', 'sensor2', 'station2', 'two'])
        
        if is_sensor1 and sensor1 is None:
            sensor1 = reading
        elif is_sensor2 and sensor2 is None:
            sensor2 = reading
        elif sensor1 is None:
            sensor1 = reading
        elif sensor2 is None:
            sensor2 = reading
        
        if sensor1 and sensor2:
            break
    
    return sensor1, sensor2

def filter_by_hours(data, hours):
    """Filter data to last N hours"""
    if not data:
        return []
    
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [d for d in data if d['timestamp'] >= cutoff]

# ============================================================================
# BATCH MANAGER
# ============================================================================
class BatchManager:
    def __init__(self):
        _, self.client, self.connected = get_azure_clients()
    
    def get_active(self):
        if not self.connected:
            return None
        try:
            e = self.client.get_entity("batch", "active")
            if e.get('is_active'):
                start = parse_timestamp(e.get('start_time'))
                return {
                    'name': e.get('name', 'Batch'),
                    'season': e.get('season', 'mid_season'),
                    'start_time': start or datetime.now(timezone.utc),
                    'is_active': True
                }
        except:
            pass
        return None
    
    def start(self, name, season):
        if not self.connected:
            return False
        try:
            now = datetime.now(timezone.utc)
            self.client.upsert_entity({
                'PartitionKey': 'batch', 'RowKey': 'active',
                'name': name or f"Batch-{now.strftime('%m%d-%H%M')}",
                'season': season, 'start_time': now.isoformat(), 'is_active': True
            })
            return True
        except:
            return False
    
    def end(self):
        if not self.connected:
            return False
        try:
            e = self.client.get_entity("batch", "active")
            e['is_active'] = False
            e['end_time'] = datetime.now(timezone.utc).isoformat()
            self.client.upsert_entity(e)
            return True
        except:
            return False

# ============================================================================
# HELPERS
# ============================================================================
def c_to_f(c):
    return (c * 9/5) + 32 if c is not None else None

def get_demo_data():
    """Demo data"""
    import random
    now = datetime.now(timezone.utc)
    data = []
    for i in range(100):
        ts = now - timedelta(minutes=i*3)
        data.append({
            'station': 'sensor1', 'timestamp': ts,
            'temperature': 18.5 + random.uniform(-1, 1),
            'humidity': 92 + random.uniform(-3, 3),
            'ethylene': 45 + random.uniform(-10, 15)
        })
        data.append({
            'station': 'sensor2', 'timestamp': ts,
            'temperature': 18.2 + random.uniform(-1, 1),
            'humidity': 91 + random.uniform(-3, 3),
            'ethylene': 48 + random.uniform(-10, 15)
        })
    return data

# ============================================================================
# AI ENGINE
# ============================================================================
def analyze_conditions(temp_f, humidity, ethylene, batch_start=None, season='mid_season'):
    alerts = []
    recs = []
    status = 'optimal'
    
    if temp_f:
        if temp_f >= 86:
            status = 'critical'
            alerts.append(('critical', f'🚨 CRITICAL: {temp_f:.1f}°F - Flesh darkening risk!'))
            recs.append(('🌡️ IMMEDIATELY lower temperature below 68°F', True))
        elif temp_f > 68:
            status = 'warning'
            alerts.append(('warning', f'⚠️ Temperature {temp_f:.1f}°F above optimal'))
            recs.append((f'🌡️ Reduce temperature by {temp_f - 68:.1f}°F', True))
        elif temp_f < 40:
            status = 'critical'
            alerts.append(('critical', f'🚨 CRITICAL: {temp_f:.1f}°F - Chilling injury!'))
            recs.append(('🌡️ IMMEDIATELY raise temperature', True))
        elif temp_f < 60:
            if status != 'critical': status = 'warning'
            alerts.append(('warning', f'⚠️ Temperature {temp_f:.1f}°F below optimal'))
    
    if humidity:
        if humidity < 80:
            status = 'critical'
            alerts.append(('critical', f'🚨 Humidity {humidity:.1f}% critically low!'))
            recs.append(('💧 IMMEDIATELY increase humidification', True))
        elif humidity < 90:
            if status != 'critical': status = 'warning'
            alerts.append(('warning', f'⚠️ Humidity {humidity:.1f}% below optimal'))
    
    if ethylene and ethylene > 150:
        if status != 'critical': status = 'warning'
        alerts.append(('warning', f'⚠️ Ethylene {ethylene:.1f} ppm very high'))
        recs.append(('🌬️ Ventilate room', True))
    
    progress = 0
    stage = 'Green'
    remaining_h = None
    
    if batch_start:
        elapsed_h = (datetime.now(timezone.utc) - batch_start).total_seconds() / 3600
        total_days = {'early_season': 6, 'mid_season': 5, 'late_season': 4}
        total_h = total_days.get(season, 5) * 24
        progress = min(100, (elapsed_h / total_h) * 100)
        remaining_h = max(0, total_h - elapsed_h)
        
        if progress < 20: stage = 'Green'
        elif progress < 50: stage = 'Breaking'
        elif progress < 80: stage = 'Ripe'
        else: stage = 'Ready'
    
    if status == 'optimal' and not alerts:
        recs.insert(0, ('✅ All conditions optimal', False))
    
    return {
        'status': status, 'alerts': alerts, 'recs': recs,
        'stage': stage, 'progress': progress, 'remaining_h': remaining_h
    }

# ============================================================================
# GAUGE HTML
# ============================================================================
def gauge_html(value, label, unit, min_v, max_v, opt_min, opt_max):
    if value is None:
        return f"<div style='text-align:center;padding:20px;background:#161b22;border-radius:8px;'><span style='color:#8b949e;'>{label}</span><br><span style='font-size:2rem;color:#8b949e;'>N/A</span></div>"
    
    if opt_min <= value <= opt_max:
        color = '#3fb950'
    elif value < min_v * 0.9 or value > max_v * 1.1:
        color = '#da3633'
    else:
        color = '#d29922'
    
    pct = min(100, max(0, (value - min_v) / (max_v - min_v) * 100))
    
    return f"""
    <div style='text-align:center;padding:15px;background:#161b22;border-radius:8px;border:1px solid #30363d;'>
        <div style='color:#8b949e;font-size:0.9rem;margin-bottom:8px;'>{label}</div>
        <div style='font-size:2.2rem;font-weight:600;color:{color};'>{value:.1f}{unit}</div>
        <div style='background:#21262d;height:6px;border-radius:3px;margin-top:10px;'>
            <div style='background:{color};width:{pct}%;height:100%;border-radius:3px;'></div>
        </div>
        <div style='color:#6e7681;font-size:0.75rem;margin-top:4px;'>Optimal: {opt_min}-{opt_max}{unit}</div>
    </div>
    """

# ============================================================================
# MAIN APP
# ============================================================================
def main():
    # Header
    st.markdown("""
    <div style='text-align:center;padding:10px 0 20px 0;'>
        <h1 style='font-size:2rem;margin:0;color:#3fb950;'>🥑 S&L Cold Storage</h1>
        <p style='color:#8b949e;margin:5px 0 0 0;'>AI Ripening System v3.6</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Check connection
    _, _, connected = get_azure_clients()
    batch_mgr = BatchManager()
    
    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        demo_mode = st.checkbox("Demo Mode", value=not connected)
        debug_mode = st.checkbox("Debug Mode", value=False)
        
        st.markdown("---")
        st.markdown("### 🥑 Batch")
        
        batch_name = st.text_input("Name", placeholder="Batch-001")
        season = st.selectbox("Season", ['early_season', 'mid_season', 'late_season'],
                             format_func=lambda x: x.replace('_', ' ').title(), index=1)
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("▶️ Start", use_container_width=True):
                if batch_mgr.start(batch_name, season):
                    st.rerun()
        with c2:
            if st.button("⏹️ End", use_container_width=True):
                if batch_mgr.end():
                    st.rerun()
        
        active_batch = batch_mgr.get_active()
        if active_batch:
            elapsed = (datetime.now(timezone.utc) - active_batch['start_time']).total_seconds() / 3600
            st.markdown(f"""<div class="batch-card">
                <b>📦 {active_batch['name']}</b><br>
                {active_batch['season'].replace('_', ' ').title()}<br>
                ⏱️ {int(elapsed)}h {int((elapsed % 1) * 60)}m
            </div>""", unsafe_allow_html=True)
        
        st.markdown("---")
        if st.button("🔄 Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown(f"<p style='color:#6e7681;font-size:0.7rem;text-align:center;'>{'🟢 Connected' if connected else '🔴 Offline'}</p>", 
                   unsafe_allow_html=True)
    
    # === GET DATA ===
    if demo_mode:
        all_data = get_demo_data()
        data_ok = True
    else:
        all_data, data_ok = fetch_all_data(max_records=500)
    
    # Get latest readings
    sensor1, sensor2 = get_latest_readings(all_data)
    
    # Debug info
    if debug_mode:
        st.markdown("### 🔧 Debug Info")
        st.write(f"Total records fetched: {len(all_data)}")
        if all_data:
            st.write(f"Newest: {all_data[0]['timestamp']}")
            st.write(f"Oldest: {all_data[-1]['timestamp']}")
            st.write("Sample record:", all_data[0] if all_data else "None")
        st.write(f"Sensor 1: {sensor1}")
        st.write(f"Sensor 2: {sensor2}")
        st.markdown("---")
    
    # Calculate averages
    temps, hums, eths = [], [], []
    for s in [sensor1, sensor2]:
        if s:
            if s.get('temperature') is not None: 
                temps.append(c_to_f(s['temperature']))
            if s.get('humidity') is not None: 
                hums.append(s['humidity'])
            if s.get('ethylene') is not None: 
                eths.append(s['ethylene'])
    
    avg_temp = sum(temps)/len(temps) if temps else None
    avg_hum = sum(hums)/len(hums) if hums else None
    avg_eth = sum(eths)/len(eths) if eths else None
    
    # AI Analysis
    active_batch = batch_mgr.get_active()
    analysis = analyze_conditions(
        avg_temp, avg_hum, avg_eth,
        active_batch['start_time'] if active_batch else None,
        active_batch['season'] if active_batch else 'mid_season'
    )
    
    # === TABS ===
    tab1, tab2, tab3 = st.tabs(["🤖 Dashboard", "📊 Sensors", "📈 Trends"])
    
    # === TAB 1: DASHBOARD ===
    with tab1:
        for atype, msg in analysis['alerts']:
            cls = 'alert-critical' if atype == 'critical' else 'alert-warning'
            st.markdown(f'<div class="{cls}">{msg}</div>', unsafe_allow_html=True)
        
        if not analysis['alerts']:
            st.markdown('<div class="alert-success">✅ All conditions optimal</div>', unsafe_allow_html=True)
        
        if analysis['recs']:
            st.markdown("#### 💡 Recommendations")
            for rec, urgent in analysis['recs']:
                st.markdown(f"{'🔴' if urgent else '🟢'} {rec}")
        
        st.markdown("---")
        st.markdown("#### 📊 Room Conditions")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(gauge_html(avg_temp, "Temperature", "°F", 30, 100, 60, 68), unsafe_allow_html=True)
        with c2:
            st.markdown(gauge_html(avg_hum, "Humidity", "%", 50, 100, 90, 95), unsafe_allow_html=True)
        with c3:
            st.markdown(gauge_html(avg_eth, "Ethylene", " ppm", 0, 150, 10, 100), unsafe_allow_html=True)
        
        if active_batch:
            st.markdown("---")
            st.markdown("#### 🥑 Ripening Progress")
            c1, c2, c3 = st.columns(3)
            with c1:
                colors = {'Green': '#238636', 'Breaking': '#9e6a03', 'Ripe': '#f0883e', 'Ready': '#da3633'}
                st.markdown(f"<div style='text-align:center;'><span style='background:{colors.get(analysis['stage'], '#238636')};padding:8px 16px;border-radius:20px;color:white;'>{analysis['stage']}</span></div>", unsafe_allow_html=True)
            with c2:
                st.metric("Progress", f"{analysis['progress']:.0f}%")
            with c3:
                if analysis['remaining_h']:
                    d, h = int(analysis['remaining_h'] // 24), int(analysis['remaining_h'] % 24)
                    st.metric("Remaining", f"{d}d {h}h" if d else f"{h}h")
            st.progress(analysis['progress'] / 100)
    
    # === TAB 2: SENSORS ===
    with tab2:
        st.markdown("### 🏭 Ripening Room")
        
        c1, c2 = st.columns(2)
        
        with c1:
            st.markdown("#### 📡 Sensor 1")
            if sensor1:
                t = c_to_f(sensor1.get('temperature'))
                st.metric("Temperature", f"{t:.1f}°F" if t else "N/A")
                st.metric("Humidity", f"{sensor1['humidity']:.1f}%" if sensor1.get('humidity') else "N/A")
                st.metric("Ethylene", f"{sensor1['ethylene']:.1f} ppm" if sensor1.get('ethylene') else "N/A")
                age = (datetime.now(timezone.utc) - sensor1['timestamp']).total_seconds()
                st.caption(f"{'🟢' if age < 120 else '🟡'} {int(age)}s ago")
            else:
                st.warning("No data")
        
        with c2:
            st.markdown("#### 📡 Sensor 2")
            if sensor2:
                t = c_to_f(sensor2.get('temperature'))
                st.metric("Temperature", f"{t:.1f}°F" if t else "N/A")
                st.metric("Humidity", f"{sensor2['humidity']:.1f}%" if sensor2.get('humidity') else "N/A")
                st.metric("Ethylene", f"{sensor2['ethylene']:.1f} ppm" if sensor2.get('ethylene') else "N/A")
                age = (datetime.now(timezone.utc) - sensor2['timestamp']).total_seconds()
                st.caption(f"{'🟢' if age < 120 else '🟡'} {int(age)}s ago")
            else:
                st.warning("No data")
        
        st.markdown("---")
        st.markdown("#### 📊 Room Average")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Avg Temp", f"{avg_temp:.1f}°F" if avg_temp else "N/A")
        with c2:
            st.metric("Avg Humidity", f"{avg_hum:.1f}%" if avg_hum else "N/A")
        with c3:
            st.metric("Avg Ethylene", f"{avg_eth:.1f} ppm" if avg_eth else "N/A")
    
    # === TAB 3: TRENDS (Auto-load) ===
    with tab3:
        st.markdown("### 📈 Sensor Trends")
        
        metric = st.selectbox("Select Metric", ['temperature', 'humidity', 'ethylene'], format_func=str.title)
        hours = st.slider("Time Range (hours)", 1, 24, 4)
        
        # Filter data for trends
        trend_data = filter_by_hours(all_data, hours)
        
        if trend_data:
            import plotly.graph_objects as go
            import pandas as pd
            
            df = pd.DataFrame(trend_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df = df.sort_values('timestamp')
            
            fig = go.Figure()
            
            # Get unique stations
            stations = df['station'].unique()
            colors = ['#3fb950', '#58a6ff', '#f0883e', '#da3633']
            
            for idx, station in enumerate(stations):
                sd = df[df['station'] == station]
                y = sd[metric].copy()
                
                if metric == 'temperature':
                    y = y.apply(c_to_f)
                
                # Clean name
                name = f"Sensor {idx+1}" if len(stations) <= 2 else str(station)
                
                fig.add_trace(go.Scatter(
                    x=sd['timestamp'], 
                    y=y, 
                    mode='lines+markers',
                    name=name,
                    line=dict(color=colors[idx % len(colors)], width=2),
                    marker=dict(size=4)
                ))
            
            # Add optimal range shading
            ranges = {'temperature': (60, 68), 'humidity': (90, 95), 'ethylene': (10, 100)}
            if metric in ranges:
                fig.add_hrect(
                    y0=ranges[metric][0], y1=ranges[metric][1],
                    fillcolor="rgba(35,134,54,0.15)", 
                    line_width=0,
                    annotation_text="Optimal", 
                    annotation_position="top left"
                )
            
            units = {'temperature': '°F', 'humidity': '%', 'ethylene': 'ppm'}
            
            fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(
                    gridcolor='#21262d',
                    title="Time"
                ),
                yaxis=dict(
                    title=f"{metric.title()} ({units[metric]})",
                    gridcolor='#21262d'
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ),
                height=400,
                margin=dict(l=60, r=20, t=40, b=60),
                font=dict(color='#c9d1d9')
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Stats
            st.markdown("#### 📊 Statistics")
            c1, c2, c3, c4 = st.columns(4)
            
            vals = df[metric].dropna()
            if metric == 'temperature':
                vals = vals.apply(c_to_f)
            
            with c1:
                st.metric("Min", f"{vals.min():.1f}{units[metric]}" if len(vals) else "N/A")
            with c2:
                st.metric("Max", f"{vals.max():.1f}{units[metric]}" if len(vals) else "N/A")
            with c3:
                st.metric("Average", f"{vals.mean():.1f}{units[metric]}" if len(vals) else "N/A")
            with c4:
                st.metric("Data Points", f"{len(vals)}")
        
        else:
            st.warning(f"No data available for the last {hours} hours")
            st.info("💡 Make sure your sensors are sending data to Azure Table Storage")
            
            if debug_mode:
                st.write(f"Total records in cache: {len(all_data)}")
                if all_data:
                    st.write(f"Data time range: {all_data[-1]['timestamp']} to {all_data[0]['timestamp']}")


if __name__ == "__main__":
    main()
