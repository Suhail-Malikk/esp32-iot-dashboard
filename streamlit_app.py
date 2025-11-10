



import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from supabase import create_client
from datetime import datetime, timedelta
import numpy as np
from sklearn.linear_model import LinearRegression
import time

# ============================================
# PAGE CONFIGURATION
# ============================================

st.set_page_config(
    page_title="MT project",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================
# SUPABASE CONNECTION
# ============================================

@st.cache_resource
def init_supabase():
    """Initialize Supabase client"""
    try:
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
        return create_client(supabase_url, supabase_key)
    except Exception as e:
        st.error(f"Failed to connect to Supabase: {e}")
        st.info("Please configure Supabase credentials in .streamlit/secrets.toml")
        return None

supabase = init_supabase()

# ============================================
# DATA FETCHING FUNCTIONS
# ============================================

# NO CACHING for real-time data - FIXED
def fetch_latest_data(limit=25):
    """Fetch latest sensor data from Supabase - NO CACHING for real-time updates"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        response = supabase.table("sensor_data")\
            .select("*")\
            .order("created_at", desc=True)\
            .limit(limit)\
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            return df.sort_values('created_at')
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=5)  # Cache for 5 seconds for time-based queries
def fetch_data_by_timerange(hours=1):
    """Fetch data for specific time range"""
    if supabase is None:
        return pd.DataFrame()
    
    try:
        time_ago = (datetime.now() - timedelta(hours=hours)).isoformat()
        response = supabase.table("sensor_data")\
            .select("*")\
            .gte("created_at", time_ago)\
            .order("created_at", desc=False)\
            .execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            df['created_at'] = pd.to_datetime(df['created_at'])
            return df
        else:
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=30)
def get_total_records():
    """Get total number of records"""
    if supabase is None:
        return 0
    
    try:
        response = supabase.table("sensor_data")\
            .select("id", count="exact")\
            .execute()
        return response.count if hasattr(response, 'count') else 0
    except:
        return 0

# ============================================
# HELPER FUNCTIONS
# ============================================

def normalize_angle(angle):
    """Convert angle from 0-360 to -180 to 180"""
    if angle > 180:
        return angle - 360
    return angle

def check_tilt_warning(roll, pitch):
    """Check if roll or pitch exceeds safe limits"""
    roll_warning = abs(roll) > 45
    pitch_warning = abs(pitch) > 45
    return roll_warning, pitch_warning

# ============================================
# HEADER
# ============================================

st.title("🌐 ESP32 + BNO055 IoT Dashboard")
st.markdown("### Real-time Sensor Monitoring & Analytics")

# ============================================
# SIDEBAR
# ============================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    # Time range selector - FIXED
    time_range = st.selectbox(
        "Time Range",
        ["Last 25 readings", "Last 1 hour", "Last 6 hours", "Last 24 hours"],
        index=0
    )
    
    # Auto-refresh toggle
    auto_refresh = st.checkbox("Auto-refresh (0.5s)", value=True)
    
    # Refresh button
    if st.button("🔄 Refresh Now"):
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # Statistics
    st.subheader("📊 Statistics")
    total_records = get_total_records()
    st.metric("Total Records", total_records)
    
    st.markdown("---")
    
    # Warning thresholds
    st.subheader("⚠️ Warning Settings")
    st.info("**Tilt Warning Threshold**\n\nRoll: ±45°\nPitch: ±45°")
    
    st.markdown("---")
    
    # Device info
    st.subheader("📡 Device Info")
    st.info("**Device ID:** ESP32_001\n**Sensor:** BNO055\n**Status:** Active\n**Update Rate:** 0.5s")

# ============================================
# FETCH DATA BASED ON SELECTION
# ============================================

if time_range == "Last 25 readings":  # FIXED
    df = fetch_latest_data(25)
elif time_range == "Last 1 hour":
    df = fetch_data_by_timerange(1)
elif time_range == "Last 6 hours":
    df = fetch_data_by_timerange(6)
else:  # Last 24 hours
    df = fetch_data_by_timerange(24)

# ============================================
# MAIN CONTENT
# ============================================

if df.empty:
    st.warning("⚠️ No data available. Make sure your ESP32 is sending data to Supabase.")
    st.info("💡 **Troubleshooting:**\n- Check ESP32 is powered on\n- Verify WiFi connection\n- Check Serial Monitor for errors\n- Verify Supabase credentials")
    st.stop()

# Apply angle normalization to gyroscope data
df['gyro_x_normalized'] = df['gyro_x'].apply(normalize_angle)
df['gyro_y_normalized'] = df['gyro_y'].apply(normalize_angle)
df['gyro_z_normalized'] = df['gyro_z'].apply(normalize_angle)

# Display last update time
st.caption(f"Last updated: {df['created_at'].max().strftime('%Y-%m-%d %H:%M:%S')}")

# ============================================
# TILT WARNING BANNER
# ============================================

latest = df.iloc[-1]

# CORRECTED: Roll is orient_z, Pitch is orient_y
current_roll = latest['orient_z']    # FIXED: Roll = Z-axis
current_pitch = latest['orient_y']   # FIXED: Pitch = Y-axis

roll_warning, pitch_warning = check_tilt_warning(current_roll, current_pitch)

# Display warning banner if either threshold is exceeded
if roll_warning or pitch_warning:
    warning_messages = []
    if roll_warning:
        warning_messages.append(f"🚨 **ROLL WARNING:** {current_roll:.1f}° (Safe range: -45° to +45°)")
    if pitch_warning:
        warning_messages.append(f"🚨 **PITCH WARNING:** {current_pitch:.1f}° (Safe range: -45° to +45°)")
    
    st.error("⚠️ **TILT WARNING DETECTED!**")
    for msg in warning_messages:
        st.markdown(msg)
    st.markdown("---")

# ============================================
# KEY METRICS (TOP ROW)
# ============================================

st.subheader("📈 Current Readings")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric(
        "Temperature",
        f"{latest['temperature']:.1f}°C",
        delta=f"{latest['temperature'] - df.iloc[-2]['temperature']:.1f}°C" if len(df) > 1 else None
    )

with col2:
    # Heading (X-axis)
    st.metric(
        "Heading (X)",
        f"{latest['orient_x']:.1f}°"
    )

with col3:
    # Roll (Z-axis) with warning indicator - CORRECTED
    roll_status = "⚠️ " if roll_warning else ""
    st.metric(
        f"{roll_status}Roll (Z)",
        f"{current_roll:.1f}°"
    )

with col4:
    # Pitch (Y-axis) with warning indicator - CORRECTED
    pitch_status = "⚠️ " if pitch_warning else ""
    st.metric(
        f"{pitch_status}Pitch (Y)",
        f"{current_pitch:.1f}°"
    )

with col5:
    # Calculate total acceleration magnitude
    accel_mag = np.sqrt(latest['accel_x']**2 + latest['accel_y']**2 + latest['accel_z']**2)
    st.metric(
        "Accel Magnitude",
        f"{accel_mag:.2f} m/s²"
    )

st.markdown("---")

# ============================================
# CALIBRATION STATUS
# ============================================

st.subheader("🎯 Calibration Status")

cal_col1, cal_col2, cal_col3, cal_col4 = st.columns(4)

def get_calibration_color(value):
    if value == 3:
        return "🟢"
    elif value == 2:
        return "🟡"
    elif value == 1:
        return "🟠"
    else:
        return "🔴"

with cal_col1:
    st.metric("System", f"{get_calibration_color(latest['cal_system'])} {latest['cal_system']}/3")

with cal_col2:
    st.metric("Gyroscope", f"{get_calibration_color(latest['cal_gyro'])} {latest['cal_gyro']}/3")

with cal_col3:
    st.metric("Accelerometer", f"{get_calibration_color(latest['cal_accel'])} {latest['cal_accel']}/3")

with cal_col4:
    st.metric("Magnetometer", f"{get_calibration_color(latest['cal_mag'])} {latest['cal_mag']}/3")

st.markdown("---")

# ============================================
# VISUALIZATIONS
# ============================================

# Create tabs for different visualizations
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📐 Orientation", 
    "🚀 Acceleration", 
    "🌀 Gyroscope", 
    "🧲 Magnetometer", 
    "📊 Raw Data"
])

# TAB 1: ORIENTATION
with tab1:
    st.subheader("Orientation (Euler Angles)")
    
    # Add warning zones to orientation chart
    fig_orient = go.Figure()
    
    # Add warning zones (±45°)
    fig_orient.add_hrect(y0=45, y1=180, fillcolor="red", opacity=0.1, line_width=0, 
                        annotation_text="Danger Zone", annotation_position="top left")
    fig_orient.add_hrect(y0=-180, y1=-45, fillcolor="red", opacity=0.1, line_width=0, 
                        annotation_text="Danger Zone", annotation_position="bottom left")
    
    # CORRECTED: Y = Pitch, Z = Roll
    fig_orient.add_trace(go.Scatter(
        x=df['created_at'], y=df['orient_x'],
        name='X (Heading)', mode='lines', line=dict(color='red', width=2)
    ))
    fig_orient.add_trace(go.Scatter(
        x=df['created_at'], y=df['orient_y'],
        name='Y (Pitch)', mode='lines', line=dict(color='green', width=2)  # FIXED: Pitch
    ))
    fig_orient.add_trace(go.Scatter(
        x=df['created_at'], y=df['orient_z'],
        name='Z (Roll)', mode='lines', line=dict(color='blue', width=2)    # FIXED: Roll
    ))
    
    fig_orient.update_layout(
        xaxis_title="Time",
        yaxis_title="Degrees (°)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_orient, use_container_width=True)
    
    # Warning indicator
    st.markdown("**⚠️ Warning Zones:** Red shaded areas indicate tilt beyond safe limits (±45°)")

# TAB 2: ACCELERATION
with tab2:
    st.subheader("Acceleration (m/s²)")
    
    fig_accel = go.Figure()
    fig_accel.add_trace(go.Scatter(
        x=df['created_at'], y=df['accel_x'],
        name='X-axis', mode='lines', line=dict(color='red', width=2)
    ))
    fig_accel.add_trace(go.Scatter(
        x=df['created_at'], y=df['accel_y'],
        name='Y-axis', mode='lines', line=dict(color='green', width=2)
    ))
    fig_accel.add_trace(go.Scatter(
        x=df['created_at'], y=df['accel_z'],
        name='Z-axis', mode='lines', line=dict(color='blue', width=2)
    ))
    
    fig_accel.update_layout(
        xaxis_title="Time",
        yaxis_title="Acceleration (m/s²)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_accel, use_container_width=True)
    
    # Acceleration magnitude
    df['accel_magnitude'] = np.sqrt(df['accel_x']**2 + df['accel_y']**2 + df['accel_z']**2)
    
    fig_accel_mag = px.line(
        df, x='created_at', y='accel_magnitude',
        title='Acceleration Magnitude',
        labels={'created_at': 'Time', 'accel_magnitude': 'Magnitude (m/s²)'}
    )
    st.plotly_chart(fig_accel_mag, use_container_width=True)

# TAB 3: GYROSCOPE
with tab3:
    st.subheader("Gyroscope (rad/s) - Normalized Range: -180° to 180°")
    
    fig_gyro = go.Figure()
    fig_gyro.add_trace(go.Scatter(
        x=df['created_at'], y=df['gyro_x_normalized'],
        name='X-axis', mode='lines', line=dict(color='red', width=2)
    ))
    fig_gyro.add_trace(go.Scatter(
        x=df['created_at'], y=df['gyro_y_normalized'],
        name='Y-axis', mode='lines', line=dict(color='green', width=2)
    ))
    fig_gyro.add_trace(go.Scatter(
        x=df['created_at'], y=df['gyro_z_normalized'],
        name='Z-axis', mode='lines', line=dict(color='blue', width=2)
    ))
    
    fig_gyro.update_layout(
        xaxis_title="Time",
        yaxis_title="Angular Velocity (normalized °)",
        hovermode='x unified',
        height=400,
        yaxis=dict(range=[-180, 180])
    )
    st.plotly_chart(fig_gyro, use_container_width=True)
    
    st.info("📊 **Note:** Gyroscope readings are normalized from 0-360° to -180° to 180° range for better visualization.")

# TAB 4: MAGNETOMETER
with tab4:
    st.subheader("Magnetometer (µT)")
    
    fig_mag = go.Figure()
    fig_mag.add_trace(go.Scatter(
        x=df['created_at'], y=df['mag_x'],
        name='X-axis', mode='lines', line=dict(color='red', width=2)
    ))
    fig_mag.add_trace(go.Scatter(
        x=df['created_at'], y=df['mag_y'],
        name='Y-axis', mode='lines', line=dict(color='green', width=2)
    ))
    fig_mag.add_trace(go.Scatter(
        x=df['created_at'], y=df['mag_z'],
        name='Z-axis', mode='lines', line=dict(color='blue', width=2)
    ))
    
    fig_mag.update_layout(
        xaxis_title="Time",
        yaxis_title="Magnetic Field (µT)",
        hovermode='x unified',
        height=400
    )
    st.plotly_chart(fig_mag, use_container_width=True)

# TAB 5: RAW DATA
with tab5:
    st.subheader("Raw Data Table")
    
    # Select columns to display
    display_cols = ['created_at', 'device_id', 'temperature', 
                   'orient_x', 'orient_y', 'orient_z',
                   'accel_x', 'accel_y', 'accel_z',
                   'gyro_x_normalized', 'gyro_y_normalized', 'gyro_z_normalized',
                   'cal_system', 'cal_gyro', 'cal_accel', 'cal_mag']
    
    st.dataframe(
        df[display_cols].sort_values('created_at', ascending=False),
        use_container_width=True,
        height=400
    )
    
    # Download button
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Download Data as CSV",
        data=csv,
        file_name=f"sensor_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ============================================
# STATISTICS & ANALYSIS
# ============================================

st.markdown("---")
st.subheader("📊 Statistical Analysis")

stat_col1, stat_col2, stat_col3 = st.columns(3)

with stat_col1:
    st.markdown("**Temperature Statistics**")
    st.write(f"Mean: {df['temperature'].mean():.2f}°C")
    st.write(f"Min: {df['temperature'].min():.2f}°C")
    st.write(f"Max: {df['temperature'].max():.2f}°C")
    st.write(f"Std Dev: {df['temperature'].std():.2f}°C")

with stat_col2:
    st.markdown("**Acceleration Statistics**")
    st.write(f"Mean Magnitude: {df['accel_magnitude'].mean():.2f} m/s²")
    st.write(f"Min Magnitude: {df['accel_magnitude'].min():.2f} m/s²")
    st.write(f"Max Magnitude: {df['accel_magnitude'].max():.2f} m/s²")

with stat_col3:
    st.markdown("**Data Quality**")
    st.write(f"Total Readings: {len(df)}")
    st.write(f"Time Span: {(df['created_at'].max() - df['created_at'].min()).total_seconds():.0f}s")
    avg_cal = (df['cal_system'].mean() + df['cal_gyro'].mean() + 
               df['cal_accel'].mean() + df['cal_mag'].mean()) / 4
    st.write(f"Avg Calibration: {avg_cal:.1f}/3")
    
    # Tilt warning statistics - CORRECTED
    st.markdown("**Tilt Warnings**")
    roll_violations = len(df[abs(df['orient_z']) > 45])    # FIXED: Roll is Z
    pitch_violations = len(df[abs(df['orient_y']) > 45])   # FIXED: Pitch is Y
    st.write(f"Roll warnings: {roll_violations}")
    st.write(f"Pitch warnings: {pitch_violations}")

# ============================================
# AUTO-REFRESH
# ============================================

if auto_refresh:
    time.sleep(0.5)
    st.rerun()
