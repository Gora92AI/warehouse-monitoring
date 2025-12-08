"""
S&L Cold Storage - AI Avocado Ripening System
Intelligent monitoring and recommendations for optimal fruit ripening

Version: 3.3 - Persistent Batch Storage Edition
FIXED: Batch data now persists in Azure Table Storage (survives page refresh)
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
# CUSTOM CSS - Clean UI with Hidden Streamlit Elements
# ============================================================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
    
    /* ===== HIDE STREAMLIT BRANDING & CONTROLS ===== */
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    
    /* Hide GitHub icon, fork button, and viewer badge */
    .css-1jc7ptx, .e1ewe7hr3, .viewerBadge_container__1QSob,
    .styles_viewerBadge__1yB5_, .viewerBadge_link__1S137,
    .viewerBadge_text__1JaDK, [data-testid="stToolbar"],
    .stDeployButton, [data-testid="stDecoration"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Hide top-right buttons */
    .stApp > header {
        display: none !important;
    }
    
    /* Remove top padding since header is hidden */
    .stApp > .main {
        padding-top: 0 !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
    }
    
    /* ===== MAIN APP STYLING ===== */
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
    
    /* Headings */
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
    }
    
    h1 { font-size: 2.5rem !important; }
    h2 { font-size: 1.8rem !important; }
    h3 { font-size: 1.4rem !important; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #161b22 0%, #0d1117 100%);
        border-right: 1px solid #30363d;
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: #c9d1d9;
    }
    
    /* Tabs */
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
    
    /* Alert Boxes */
    .alert-critical {
        background: linear-gradient(135deg, #da3633 0%, #b62324 100%);
        border: 1px solid #f85149;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
        font-weight: 500;
        box-shadow: 0 4px 20px rgba(248, 81, 73, 0.3);
    }
    
    .alert-warning {
        background: linear-gradient(135deg, #9e6a03 0%, #845306 100%);
        border: 1px solid #d29922;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
        font-weight: 500;
        box-shadow: 0 4px 20px rgba(210, 153, 34, 0.3);
    }
    
    .alert-success {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        border: 1px solid #3fb950;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 12px;
        color: #ffffff;
        font-weight: 500;
        box-shadow: 0 4px 20px rgba(63, 185, 80, 0.3);
    }
    
    /* AI Panel */
    .ai-panel {
        background: linear-gradient(145deg, #1a2332 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
    }
    
    .ai-panel-header {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-bottom: 16px;
    }
    
    .ai-panel-title {
        font-size: 1.4rem;
        font-weight: 600;
        font-family: 'Outfit', sans-serif;
    }
    
    .ai-recommendation {
        background: #21262d;
        border-left: 4px solid #3fb950;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        color: #c9d1d9;
    }
    
    .ai-recommendation-action {
        background: #21262d;
        border-left: 4px solid #f85149;
        padding: 12px 16px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
        color: #c9d1d9;
    }
    
    /* Ripening Progress */
    .ripening-progress-container {
        background: linear-gradient(145deg, #1a2332 0%, #161b22 100%);
        border: 1px solid #30363d;
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 24px;
    }
    
    .ripening-stage {
        display: inline-block;
        padding: 8px 20px;
        border-radius: 20px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
        font-size: 1.1rem;
    }
    
    .stage-green {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        color: #ffffff;
    }
    
    .stage-breaking {
        background: linear-gradient(135deg, #9e6a03 0%, #845306 100%);
        color: #ffffff;
    }
    
    .stage-ripe {
        background: linear-gradient(135deg, #f0883e 0%, #db6d28 100%);
        color: #ffffff;
    }
    
    .stage-ready {
        background: linear-gradient(135deg, #da3633 0%, #b62324 100%);
        color: #ffffff;
    }
    
    /* Checklist */
    .checklist-item {
        background: #21262d;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        display: flex;
        align-items: center;
        gap: 12px;
        color: #c9d1d9;
    }
    
    .checklist-check {
        color: #3fb950;
        font-size: 1.2rem;
    }
    
    .checklist-pending {
        color: #8b949e;
        font-size: 1.2rem;
    }
    
    /* Batch Card */
    .batch-card {
        background: linear-gradient(135deg, #238636 0%, #196c2e 100%);
        border-radius: 12px;
        padding: 16px;
        margin: 12px 0;
        color: #ffffff;
    }
    
    .batch-header {
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    
    .batch-detail {
        font-size: 0.9rem;
        margin: 4px 0;
        color: rgba(255, 255, 255, 0.9);
    }
    
    .batch-value {
        font-family: 'JetBrains Mono', monospace;
        font-weight: 500;
    }
    
    /* Data Table */
    .dataframe {
        font-family: 'JetBrains Mono', monospace !important;
        font-size: 0.9rem !important;
    }
    
    /* Quick Reference */
    .quick-ref-box {
        background: #21262d;
        border-radius: 12px;
        padding: 20px;
        margin: 12px 0;
    }
    
    .quick-ref-title {
        color: #58a6ff;
        font-weight: 600;
        margin-bottom: 12px;
        font-size: 1.1rem;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #238636, #3fb950);
    }
    
    /* Persistence indicator */
    .persistence-badge {
        background: #238636;
        color: white;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 500;
        display: inline-flex;
        align-items: center;
        gap: 6px;
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
# PERSISTENT BATCH STORAGE - STORES IN AZURE TABLE
# ============================================================================
class BatchManager:
    """
    Manages batch persistence in Azure Table Storage.
    Batches survive page refreshes, server restarts, and work across multiple users.
    """
    
    BATCH_TABLE_NAME = "batches"
    ACTIVE_BATCH_ROW_KEY = "active"
    
    def __init__(self):
        self.table_client = None
        self._init_table_client()
    
    def _init_table_client(self):
        """Initialize Azure Table client"""
        try:
            from azure.data.tables import TableServiceClient
            connection_string = st.secrets['azure']['storage_connection_string']
            table_service = TableServiceClient.from_connection_string(connection_string)
            
            # Create batches table if it doesn't exist
            try:
                table_service.create_table(self.BATCH_TABLE_NAME)
            except Exception:
                pass  # Table already exists
            
            self.table_client = table_service.get_table_client(self.BATCH_TABLE_NAME)
        except Exception as e:
            self.table_client = None
    
    def get_active_batch(self):
        """
        Retrieve the currently active batch from Azure Table Storage.
        Returns None if no active batch exists.
        """
        if not self.table_client:
            return None
        
        try:
            entity = self.table_client.get_entity(
                partition_key="batch",
                row_key=self.ACTIVE_BATCH_ROW_KEY
            )
            
            # Check if batch is still active
            if entity.get('is_active', False):
                return {
                    'name': entity.get('name', 'Unnamed'),
                    'season': entity.get('season', 'mid_season'),
                    'start_time': datetime.fromisoformat(entity['start_time']),
                    'is_active': True
                }
            return None
            
        except Exception:
            return None
    
    def start_batch(self, name, season):
        """
        Start a new batch and persist it to Azure Table Storage.
        """
        if not self.table_client:
            return False
        
        try:
            start_time = datetime.now(timezone.utc)
            entity = {
                'PartitionKey': 'batch',
                'RowKey': self.ACTIVE_BATCH_ROW_KEY,
                'name': name or f"Batch-{start_time.strftime('%Y%m%d-%H%M')}",
                'season': season,
                'start_time': start_time.isoformat(),
                'is_active': True
            }
            
            # Upsert (update or insert) the batch
            self.table_client.upsert_entity(entity)
            return True
            
        except Exception as e:
            st.error(f"Failed to start batch: {e}")
            return False
    
    def end_batch(self):
        """
        End the currently active batch.
        """
        if not self.table_client:
            return False
        
        try:
            entity = self.table_client.get_entity(
                partition_key="batch",
                row_key=self.ACTIVE_BATCH_ROW_KEY
            )
            
            # Mark as inactive and record end time
            entity['is_active'] = False
            entity['end_time'] = datetime.now(timezone.utc).isoformat()
            
            self.table_client.upsert_entity(entity)
            return True
            
        except Exception:
            return False
    
    def get_batch_history(self, limit=10):
        """
        Get historical batches (for reports).
        """
        # This would query a separate history table
        # For now, return empty list
        return []


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
                'message': f'🌡️ Reduce temperature by {(temp_f - p["optimal_max"]):.1f}°F for optimal ripening',
                'priority': 'high'
            })
        elif temp_f < p['critical_low']:
            status = 'critical'
            alerts.append({
                'type': 'critical',
                'message': f'🚨 CRITICAL: Temperature {temp_f:.1f}°F below {p["critical_low"]}°F - Chilling injury risk!'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌡️ IMMEDIATELY raise temperature above {p["critical_low"]}°F',
                'priority': 'critical'
            })
        elif temp_f < p['optimal_min']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Temperature {temp_f:.1f}°F is below optimal range ({p["optimal_min"]}-{p["optimal_max"]}°F)'
            })
            recommendations.append({
                'type': 'action',
                'message': f'🌡️ Increase temperature by {(p["optimal_min"] - temp_f):.1f}°F for faster ripening',
                'priority': 'medium'
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
                'message': f'🚨 CRITICAL: Humidity {humidity:.1f}% below {p["critical_low"]}% - Quality loss occurring!'
            })
            recommendations.append({
                'type': 'action',
                'message': '💧 IMMEDIATELY increase humidification - risk of weight loss and quality degradation',
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
                'message': f'💧 Increase humidity by {(p["optimal_min"] - humidity):.1f}% to prevent moisture loss',
                'priority': 'high'
            })
        elif humidity > p['optimal_max']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Humidity {humidity:.1f}% is above optimal - condensation risk'
            })
            recommendations.append({
                'type': 'action',
                'message': '💧 Reduce humidity slightly to prevent condensation and mold risk',
                'priority': 'medium'
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
                'message': f'⚠️ Ethylene {ethylene_ppm:.1f} ppm is very high - may cause over-ripening'
            })
            recommendations.append({
                'type': 'action',
                'message': '🌬️ Ventilate room to reduce ethylene concentration',
                'priority': 'high'
            })
        elif ethylene_ppm < p['warning_low']:
            status = 'warning'
            alerts.append({
                'type': 'warning',
                'message': f'⚠️ Ethylene {ethylene_ppm:.1f} ppm is very low - slow ripening expected'
            })
            recommendations.append({
                'type': 'action',
                'message': '🍌 Consider adding ethylene generator or ripe fruit to increase levels',
                'priority': 'medium'
            })
        elif ethylene_ppm < p['optimal_min']:
            recommendations.append({
                'type': 'info',
                'message': f'🌿 Ethylene {ethylene_ppm:.1f} ppm is acceptable but below optimal ({p["optimal_min"]}-{p["optimal_max"]} ppm)',
                'priority': 'low'
            })
        
        return status, alerts, recommendations
    
    def _check_ventilation_schedule(self, batch_start_time):
        if not batch_start_time:
            return None
        
        hours_elapsed = (datetime.now(timezone.utc) - batch_start_time).total_seconds() / 3600
        vent_interval = self.params['ventilation']['interval_hours']
        vent_duration = self.params['ventilation']['duration_minutes']
        
        hours_since_last_vent = hours_elapsed % vent_interval
        
        if hours_since_last_vent >= (vent_interval - 0.5):
            return {
                'type': 'action',
                'message': f'🌬️ Ventilation due soon - open doors for {vent_duration} minutes to prevent CO₂ buildup',
                'priority': 'medium'
            }
        elif hours_since_last_vent < 0.5:
            return {
                'type': 'info',
                'message': f'✅ Ventilation recently completed - next due in ~{vent_interval:.0f} hours',
                'priority': 'low'
            }
        
        return None


# ============================================================================
# AZURE DATA FUNCTIONS
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
        table_name = st.secrets['azure']['table_name']
        
        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client(table_name)
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=4)
        
        all_entities = []
        for entity in table_client.list_entities():
            try:
                timestamp = entity.get('timestamp') or entity.get('Timestamp')
                if timestamp:
                    if isinstance(timestamp, str):
                        timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    if timestamp.tzinfo is None:
                        timestamp = timestamp.replace(tzinfo=timezone.utc)
                    
                    if timestamp >= cutoff_time:
                        temperature = entity.get('temperature')
                        humidity = entity.get('humidity')
                        ethylene = entity.get('ethylene')
                        station = entity.get('station', entity.get('PartitionKey', 'unknown'))
                        
                        if temperature is not None:
                            temperature = float(temperature)
                        if humidity is not None:
                            humidity = float(humidity)
                        if ethylene is not None:
                            ethylene = float(ethylene)
                        
                        all_entities.append({
                            'station': station,
                            'timestamp': timestamp,
                            'temperature': temperature,
                            'humidity': humidity,
                            'ethylene': ethylene
                        })
            except Exception:
                continue
        
        status = "Connected to Azure"
        return all_entities, status, len(all_entities)
        
    except KeyError:
        return [], "Azure not configured", 0
    except Exception as e:
        return [], f"Error: {str(e)[:30]}", 0


def generate_demo_data():
    """Generate realistic demo data - BOTH stations have full sensors"""
    import random
    data = []
    current_time = datetime.now(timezone.utc)
    
    for i in range(480, 0, -1):
        timestamp = current_time - timedelta(seconds=i * 30)
        
        # Station 1 - Full sensors (Ripening Room A)
        data.append({
            'station': 'station1',
            'timestamp': timestamp,
            'temperature': 18.5 + random.uniform(-0.5, 0.5),
            'humidity': 92.0 + random.uniform(-2, 2),
            'ethylene': 45.0 + random.uniform(-10, 15)
        })
        
        # Station 2 - Full sensors (Ripening Room B)
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
    <div style='text-align: center; padding: 10px 0 20px 0;'>
        <h1 style='font-size: 2.8rem; margin-bottom: 5px; 
            background: linear-gradient(90deg, #3fb950, #58a6ff, #3fb950); 
            -webkit-background-clip: text; -webkit-text-fill-color: transparent;
            font-family: "Outfit", sans-serif; font-weight: 700;'>
            🥑 S&L Cold Storage
        </h1>
        <p style='color: #8b949e; font-size: 1.2rem; margin-top: 0; font-family: "Outfit", sans-serif;'>
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
            time_str = f"{days}d {hours}h" if days > 0 else f"{hours}h"
        else:
            time_str = "N/A"
        
        st.markdown(f"""
        <div style="text-align: center;">
            <p style="color: #8b949e; margin-bottom: 8px;">Est. Remaining</p>
            <p style="font-family: 'JetBrains Mono', monospace; font-size: 2rem; color: #58a6ff; margin: 0;">
                {time_str}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.progress(progress / 100)
    st.markdown("</div>", unsafe_allow_html=True)


def render_action_checklist():
    st.markdown("""
    <div class="quick-ref-box">
        <div class="quick-ref-title">✅ Operator Checklist</div>
    """, unsafe_allow_html=True)
    
    checklist_items = [
        ("Check temperature within range", True),
        ("Verify humidity levels", True),
        ("Monitor ethylene concentration", True),
        ("Ventilate every 12 hours", False),
        ("Inspect for quality issues", False),
    ]
    
    for item, checked in checklist_items:
        icon = "✅" if checked else "⬜"
        st.markdown(f'<div class="checklist-item"><span>{icon}</span> {item}</div>', unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)


def create_gauge_chart(value, title, min_val, max_val, optimal_min, optimal_max, unit):
    """Create a gauge chart with optimal range"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title, 'font': {'color': '#c9d1d9', 'size': 16, 'family': 'Outfit'}},
        number={'suffix': unit, 'font': {'color': '#ffffff', 'size': 24, 'family': 'JetBrains Mono'}},
        gauge={
            'axis': {
                'range': [min_val, max_val], 
                'tickcolor': '#8b949e',
                'tickfont': {'color': '#8b949e'}
            },
            'bar': {'color': '#3fb950'},
            'bgcolor': '#21262d',
            'borderwidth': 2,
            'bordercolor': '#30363d',
            'steps': [
                {'range': [min_val, optimal_min], 'color': '#9e6a03'},
                {'range': [optimal_min, optimal_max], 'color': '#238636'},
                {'range': [optimal_max, max_val], 'color': '#9e6a03'}
            ],
            'threshold': {
                'line': {'color': '#f85149', 'width': 4},
                'thickness': 0.75,
                'value': value
            }
        }
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#c9d1d9', 'family': 'Outfit'},
        height=200,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_time_series_chart(data, selected_metric):
    """Create time series chart for selected metric"""
    if not data:
        return None
    
    df = pd.DataFrame(data)
    df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
    
    fig = go.Figure()
    
    colors = {'station1': '#3fb950', 'station2': '#58a6ff'}
    names = {'station1': 'Room A', 'station2': 'Room B'}
    
    for station in df['station'].unique():
        station_data = df[df['station'] == station].sort_values('timestamp')
        
        y_data = station_data[selected_metric]
        if selected_metric == 'temperature':
            y_data = y_data.apply(lambda x: celsius_to_fahrenheit(x) if x is not None else None)
        
        fig.add_trace(go.Scatter(
            x=station_data['timestamp'],
            y=y_data,
            mode='lines',
            name=names.get(station, station),
            line=dict(color=colors.get(station, '#3fb950'), width=2),
            fill='tozeroy',
            fillcolor=f"rgba({int(colors.get(station, '#3fb950')[1:3], 16)}, {int(colors.get(station, '#3fb950')[3:5], 16)}, {int(colors.get(station, '#3fb950')[5:7], 16)}, 0.1)"
        ))
    
    # Add optimal range
    optimal_ranges = {
        'temperature': (60, 68),
        'humidity': (90, 95),
        'ethylene': (10, 100)
    }
    
    if selected_metric in optimal_ranges:
        opt_min, opt_max = optimal_ranges[selected_metric]
        fig.add_hrect(
            y0=opt_min, y1=opt_max,
            fillcolor="rgba(35, 134, 54, 0.2)",
            line_width=0,
            annotation_text="Optimal",
            annotation_position="top right",
            annotation=dict(font_color="#3fb950")
        )
    
    metric_labels = {
        'temperature': 'Temperature (°F)',
        'humidity': 'Humidity (%)',
        'ethylene': 'Ethylene (ppm)'
    }
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font={'color': '#c9d1d9', 'family': 'Outfit'},
        xaxis=dict(
            title='Time',
            gridcolor='#21262d',
            showgrid=True
        ),
        yaxis=dict(
            title=metric_labels.get(selected_metric, selected_metric),
            gridcolor='#21262d',
            showgrid=True
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=60, r=20, t=40, b=60),
        height=400
    )
    
    return fig


# ============================================================================
# MAIN APPLICATION
# ============================================================================
def main():
    render_header()
    
    # Initialize batch manager for persistent storage
    batch_manager = BatchManager()
    
    # Check for Azure secrets
    has_azure_secrets = False
    try:
        if 'azure' in st.secrets and st.secrets['azure'].get('storage_connection_string'):
            has_azure_secrets = True
    except Exception:
        pass
    
    # Load active batch from persistent storage
    active_batch = batch_manager.get_active_batch() if has_azure_secrets else None
    
    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Settings")
        
        if has_azure_secrets:
            demo_mode = st.checkbox("Demo Mode", value=False)
        else:
            st.info("📡 Demo Mode Active")
            demo_mode = True
        
        st.markdown("---")
        st.markdown("### 🥑 Batch Management")
        
        # Show persistence badge if Azure is configured
        if has_azure_secrets:
            st.markdown("""
            <div class="persistence-badge">
                💾 Cloud Synced
            </div>
            """, unsafe_allow_html=True)
        
        batch_name = st.text_input("Batch Name", placeholder="e.g., Batch-001")
        
        season = st.selectbox(
            "Avocado Season",
            options=['early_season', 'mid_season', 'late_season'],
            format_func=lambda x: x.replace('_', ' ').title(),
            index=1
        )
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("▶️ Start", use_container_width=True):
                if has_azure_secrets:
                    if batch_manager.start_batch(batch_name, season):
                        st.success("Started!")
                        st.rerun()  # Refresh to show updated batch
                    else:
                        st.error("Failed to start batch")
                else:
                    st.warning("Enable Azure to persist batches")
        
        with col2:
            if st.button("⏹️ End", use_container_width=True):
                if has_azure_secrets:
                    if batch_manager.end_batch():
                        st.info("Ended")
                        st.rerun()  # Refresh to clear batch display
                    else:
                        st.error("Failed to end batch")
                else:
                    st.warning("Enable Azure to persist batches")
        
        # Show active batch info (from persistent storage)
        if active_batch:
            elapsed = datetime.now(timezone.utc) - active_batch['start_time']
            hours_elapsed = elapsed.total_seconds() / 3600
            st.markdown(f"""
            <div class="batch-card">
                <div class="batch-header">📦 Active Batch</div>
                <div class="batch-detail">Name: <span class="batch-value">{active_batch['name']}</span></div>
                <div class="batch-detail">Season: <span class="batch-value">{active_batch['season'].replace('_', ' ').title()}</span></div>
                <div class="batch-detail">Elapsed: <span class="batch-value">{int(hours_elapsed)}h {int((hours_elapsed % 1) * 60)}m</span></div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        st.markdown("### 🔄 Auto Refresh")
        auto_refresh = st.checkbox("Enable", value=True)
        refresh_interval = st.slider("Interval (sec)", 10, 60, 30)
        
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #8b949e; font-size: 0.8rem;">
            <p>S&L Cold Storage v3.3</p>
            <p>Persistent Batch Storage</p>
        </div>
        """, unsafe_allow_html=True)
    
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
    
    # AI Analysis - use persistent batch info
    ai_engine = AIRipeningEngine()
    analysis = ai_engine.analyze_conditions(
        temperature_f=temp_f,
        humidity=humidity,
        ethylene_ppm=ethylene,
        batch_start_time=active_batch['start_time'] if active_batch else None,
        season=active_batch['season'] if active_batch else 'mid_season'
    )
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🤖 AI Dashboard", "📊 Live Sensors", "📈 Trends", "📋 Reports"])
    
    # ========== TAB 1: AI DASHBOARD ==========
    with tab1:
        render_ai_panel(analysis)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if active_batch:
            render_ripening_progress(analysis)
        else:
            st.info("💡 Start a batch in the sidebar to track ripening progress. Batches persist even after page refresh!")
        
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
    
    # ========== TAB 2: LIVE SENSORS ==========
    with tab2:
        st.markdown("### 📡 Live Sensor Readings")
        
        status_cols = st.columns(3)
        with status_cols[0]:
            st.markdown(f"**Status:** {connection_status}")
        with status_cols[1]:
            st.markdown(f"**Records:** {record_count}")
        with status_cols[2]:
            if st.button("🔄 Refresh Now"):
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
    
    # ========== TAB 3: TRENDS ==========
    with tab3:
        st.markdown("### 📈 Sensor Trends")
        
        metric_options = ['temperature', 'humidity', 'ethylene']
        selected_metric = st.selectbox(
            "Select Metric",
            options=metric_options,
            format_func=lambda x: x.title()
        )
        
        fig = create_time_series_chart(data, selected_metric)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data available for trends")
    
    # ========== TAB 4: REPORTS ==========
    with tab4:
        st.markdown("### 📋 Reports & Reference")
        
        if active_batch:
            st.markdown("#### 📦 Current Batch Summary")
            
            elapsed = datetime.now(timezone.utc) - active_batch['start_time']
            hours_elapsed = elapsed.total_seconds() / 3600
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Batch Name</p>
                    <p style="color: #ffffff; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {active_batch['name']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Time Elapsed</p>
                    <p style="color: #3fb950; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {int(hours_elapsed)}h {int((hours_elapsed % 1) * 60)}m
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Current Stage</p>
                    <p style="color: #58a6ff; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {analysis['ripening_stage']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Season</p>
                    <p style="color: #ffffff; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {active_batch['season'].replace('_', ' ').title()}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Progress</p>
                    <p style="color: #3fb950; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {analysis['progress_percent']:.0f}%
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                if analysis['time_remaining'] is not None:
                    days = int(analysis['time_remaining'] // 24)
                    hours = int(analysis['time_remaining'] % 24)
                    time_str = f"{days}d {hours}h" if days > 0 else f"{hours}h"
                else:
                    time_str = "N/A"
                
                st.markdown(f"""
                <div style="background: #21262d; padding: 20px; border-radius: 12px; text-align: center;">
                    <p style="color: #8b949e; margin-bottom: 8px;">Est. Remaining</p>
                    <p style="color: #58a6ff; font-size: 1.5rem; font-family: 'JetBrains Mono', monospace; margin: 0;">
                        {time_str}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Download data
            if data:
                df = pd.DataFrame(data)
                csv = df.to_csv(index=False)
                st.download_button(
                    "📥 Download Data (CSV)",
                    csv,
                    f"batch_{active_batch['name']}_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
        else:
            st.info("💡 Start a batch to generate reports")
        
        st.markdown("---")
        
        # Quick Reference
        st.markdown("### 🥑 Avocado Ripening Quick Reference")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="quick-ref-box">
                <div class="quick-ref-title">Optimal Conditions:</div>
                <ul style="color: #c9d1d9; margin: 0; padding-left: 20px;">
                    <li>🌡️ Temperature: 60-68°F (15-20°C)</li>
                    <li>💧 Humidity: 90-95% RH</li>
                    <li>🌿 Ethylene: 10-100 ppm</li>
                    <li>💨 Ventilate: Every 12 hours for 20 min</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="quick-ref-box">
                <div class="quick-ref-title">Ripening Timeline:</div>
                <ul style="color: #c9d1d9; margin: 0; padding-left: 20px;">
                    <li>🌱 Early Season: 48h ethylene, 5-6 days total</li>
                    <li>🌿 Mid Season: 36h ethylene, 4-5 days total</li>
                    <li>🍃 Late Season: 24h ethylene, 3-4 days total</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="quick-ref-box">
            <div class="quick-ref-title" style="color: #f85149;">⚠️ Critical Thresholds:</div>
            <ul style="color: #c9d1d9; margin: 0; padding-left: 20px;">
                <li>Temperature >86°F = Risk of flesh darkening</li>
                <li>Temperature <40°F = Chilling injury on unripe fruit</li>
                <li>Humidity <80% = Quality loss</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_interval)
        st.rerun()


if __name__ == "__main__":
    main()


