import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import numpy as np
import os
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Space Rover Dashboard",
    page_icon="🛸",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    h1 {
        color: #1f77b4;
        padding-bottom: 10px;
        border-bottom: 3px solid #1f77b4;
    }
    .dataframe {
        font-size: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ==================== Data Loading Functions ====================

@st.cache_data(ttl=2)  # Cache for 2 seconds for near real-time updates
def load_json_data(filepath='rover_data_log.json'):
    """Load data from JSON log file"""
    try:
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        with open(filepath, 'r') as f:
            data = [json.loads(line) for line in f if line.strip()]
        
        if not data:
            return pd.DataFrame()
        
        # Flatten nested dictionaries
        flattened_data = []
        for entry in data:
            flat_entry = {
                'timestamp': entry.get('timestamp'),
                'x': entry.get('position', {}).get('x', 0),
                'y': entry.get('position', {}).get('y', 0),
                'heading': entry.get('position', {}).get('heading', 0),
                'temperature': entry.get('temperature'),
                'humidity': entry.get('humidity'),
                'soil_ph': entry.get('soil_ph'),
                'soil_voltage': entry.get('soil_voltage'),
                'action': entry.get('action', 'unknown'),
                'obstacles_front': entry.get('obstacles', {}).get('front', False),
                'obstacles_back': entry.get('obstacles', {}).get('back', False),
                'obstacles_left': entry.get('obstacles', {}).get('left', False),
                'obstacles_right': entry.get('obstacles', {}).get('right', False),
            }
            flattened_data.append(flat_entry)
        
        df = pd.DataFrame(flattened_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=2)
def load_csv_data(filepath='rover_data.csv'):
    """Load data from CSV file"""
    try:
        if not os.path.exists(filepath):
            return pd.DataFrame()
        
        df = pd.read_csv(filepath)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return pd.DataFrame()

def get_latest_data(df):
    """Get the most recent data point"""
    if df.empty:
        return None
    return df.iloc[-1]

# ==================== Visualization Functions ====================

def create_path_map(df):
    """Create 2D map of rover path"""
    if df.empty or 'x' not in df.columns:
        return None
    
    fig = go.Figure()
    
    # Path line
    fig.add_trace(go.Scatter(
        x=df['x'],
        y=df['y'],
        mode='lines+markers',
        name='Path',
        line=dict(color='blue', width=2),
        marker=dict(size=6, color='lightblue'),
        hovertemplate='<b>Position</b><br>X: %{x:.2f}m<br>Y: %{y:.2f}m<extra></extra>'
    ))
    
    # Starting point
    fig.add_trace(go.Scatter(
        x=[df['x'].iloc[0]],
        y=[df['y'].iloc[0]],
        mode='markers',
        name='Start',
        marker=dict(size=15, color='green', symbol='star'),
        hovertemplate='<b>Start Point</b><extra></extra>'
    ))
    
    # Current position
    fig.add_trace(go.Scatter(
        x=[df['x'].iloc[-1]],
        y=[df['y'].iloc[-1]],
        mode='markers',
        name='Current',
        marker=dict(size=15, color='red', symbol='diamond'),
        hovertemplate='<b>Current Position</b><extra></extra>'
    ))
    
    # Study locations (where action is STUDY_LOCATION)
    if 'action' in df.columns:
        study_points = df[df['action'] == 'STUDY_LOCATION']
        if not study_points.empty:
            fig.add_trace(go.Scatter(
                x=study_points['x'],
                y=study_points['y'],
                mode='markers',
                name='Study Sites',
                marker=dict(size=12, color='orange', symbol='circle-open', line=dict(width=2)),
                hovertemplate='<b>Study Site</b><br>X: %{x:.2f}m<br>Y: %{y:.2f}m<extra></extra>'
            ))
    
    fig.update_layout(
        title='Rover Movement Path',
        xaxis_title='X Position (meters)',
        yaxis_title='Y Position (meters)',
        hovermode='closest',
        showlegend=True,
        height=500,
        plot_bgcolor='rgba(240,240,240,0.5)',
        xaxis=dict(gridcolor='white', zeroline=True, zerolinecolor='black'),
        yaxis=dict(gridcolor='white', zeroline=True, zerolinecolor='black', scaleanchor='x', scaleratio=1)
    )
    
    return fig

def create_environmental_chart(df):
    """Create temperature and humidity time series"""
    if df.empty:
        return None
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Temperature Over Time', 'Humidity Over Time'),
        vertical_spacing=0.15
    )
    
    # Temperature
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['temperature'],
            mode='lines+markers',
            name='Temperature',
            line=dict(color='red', width=2),
            marker=dict(size=4),
            hovertemplate='<b>%{y:.1f}°C</b><br>%{x}<extra></extra>'
        ),
        row=1, col=1
    )
    
    # Humidity
    fig.add_trace(
        go.Scatter(
            x=df['timestamp'],
            y=df['humidity'],
            mode='lines+markers',
            name='Humidity',
            line=dict(color='blue', width=2),
            marker=dict(size=4),
            hovertemplate='<b>%{y:.1f}%</b><br>%{x}<extra></extra>'
        ),
        row=2, col=1
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_yaxes(title_text="Temperature (°C)", row=1, col=1)
    fig.update_yaxes(title_text="Humidity (%)", row=2, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=False,
        hovermode='x unified'
    )
    
    return fig

def create_soil_ph_chart(df):
    """Create soil pH time series"""
    if df.empty or 'soil_ph' not in df.columns:
        return None
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['soil_ph'],
        mode='lines+markers',
        name='Soil pH',
        line=dict(color='green', width=2),
        marker=dict(size=6),
        hovertemplate='<b>pH: %{y:.2f}</b><br>%{x}<extra></extra>'
    ))
    
    # Add pH reference lines
    fig.add_hline(y=7.0, line_dash="dash", line_color="gray", 
                  annotation_text="Neutral (pH 7)", annotation_position="right")
    fig.add_hline(y=6.0, line_dash="dot", line_color="orange", 
                  annotation_text="Slightly Acidic", annotation_position="right")
    fig.add_hline(y=8.0, line_dash="dot", line_color="purple", 
                  annotation_text="Slightly Alkaline", annotation_position="right")
    
    fig.update_layout(
        title='Soil pH Over Time',
        xaxis_title='Time',
        yaxis_title='pH Value',
        height=400,
        hovermode='x unified',
        yaxis=dict(range=[4, 10])
    )
    
    return fig

def create_obstacle_heatmap(df):
    """Create heatmap showing obstacle detection frequency"""
    if df.empty:
        return None
    
    obstacle_cols = ['obstacles_front', 'obstacles_back', 'obstacles_left', 'obstacles_right']
    
    if not all(col in df.columns for col in obstacle_cols):
        return None
    
    obstacle_counts = df[obstacle_cols].sum()
    obstacle_counts.index = ['Front', 'Back', 'Left', 'Right']
    
    fig = go.Figure(data=[
        go.Bar(
            x=obstacle_counts.index,
            y=obstacle_counts.values,
            marker_color=['red', 'orange', 'yellow', 'blue'],
            text=obstacle_counts.values,
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Detections: %{y}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='Obstacle Detection Count by Direction',
        xaxis_title='Direction',
        yaxis_title='Number of Detections',
        height=350
    )
    
    return fig

def create_action_distribution(df):
    """Create pie chart of rover actions"""
    if df.empty or 'action' not in df.columns:
        return None
    
    action_counts = df['action'].value_counts()
    
    fig = go.Figure(data=[go.Pie(
        labels=action_counts.index,
        values=action_counts.values,
        hole=0.3,
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title='Rover Action Distribution',
        height=350
    )
    
    return fig

def create_3d_path(df):
    """Create 3D visualization with position and pH"""
    if df.empty or 'soil_ph' not in df.columns:
        return None
    
    fig = go.Figure(data=[go.Scatter3d(
        x=df['x'],
        y=df['y'],
        z=df['soil_ph'],
        mode='markers+lines',
        marker=dict(
            size=6,
            color=df['soil_ph'],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="pH"),
            cmin=df['soil_ph'].min(),
            cmax=df['soil_ph'].max()
        ),
        line=dict(color='gray', width=2),
        hovertemplate='<b>Position</b><br>X: %{x:.2f}m<br>Y: %{y:.2f}m<br>pH: %{z:.2f}<extra></extra>'
    )])
    
    fig.update_layout(
        title='3D Path with Soil pH',
        scene=dict(
            xaxis_title='X Position (m)',
            yaxis_title='Y Position (m)',
            zaxis_title='Soil pH',
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.2))
        ),
        height=600
    )
    
    return fig

# ==================== Main Dashboard ====================

def main():
    # Title
    st.title("🛸 Space Rover Data Dashboard")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Dashboard Controls")
        
        # Data source selection
        data_source = st.radio(
            "Data Source:",
            options=["JSON Log", "CSV Export"],
            index=0
        )
        
        # File upload option
        st.subheader("📁 Upload Data File")
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['json', 'csv'],
            help="Upload rover data log file"
        )
        
        # Auto-refresh toggle
        auto_refresh = st.checkbox("Auto-refresh (2s)", value=True)
        
        if auto_refresh:
            st.info("Dashboard updates every 2 seconds")
        
        # Manual refresh button
        if st.button("🔄 Refresh Now"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        
        # Data info
        st.subheader("📊 Data Statistics")
    
    # Load data
    if uploaded_file:
        if uploaded_file.name.endswith('.json'):
            # Save uploaded file temporarily
            with open('temp_data.json', 'wb') as f:
                f.write(uploaded_file.getvalue())
            df = load_json_data('temp_data.json')
        else:
            df = pd.read_csv(uploaded_file)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
    else:
        if data_source == "JSON Log":
            df = load_json_data('rover_data_log.json')
        else:
            df = load_csv_data('rover_data.csv')
    
    # Check if data is available
    if df.empty:
        st.warning("⚠️ No data available. Make sure the rover is running and generating data.")
        st.info("Expected file: `rover_data_log.json` or `rover_data.csv` in the same directory")
        st.stop()
    
    # Sidebar statistics
    with st.sidebar:
        st.metric("Total Data Points", len(df))
        st.metric("Duration", f"{(df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 60:.1f} min")
        if 'x' in df.columns and 'y' in df.columns:
            total_distance = np.sqrt(df['x'].diff()**2 + df['y'].diff()**2).sum()
            st.metric("Distance Traveled", f"{total_distance:.2f} m")
    
    # Get latest data
    latest = get_latest_data(df)
    
    # Current Status Section
    st.header("📍 Current Status")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "🌡️ Temperature",
            f"{latest['temperature']:.1f}°C" if latest['temperature'] is not None else "N/A"
        )
    
    with col2:
        st.metric(
            "💧 Humidity",
            f"{latest['humidity']:.1f}%" if latest['humidity'] is not None else "N/A"
        )
    
    with col3:
        st.metric(
            "🌱 Soil pH",
            f"{latest['soil_ph']:.2f}" if latest['soil_ph'] is not None else "N/A"
        )
    
    with col4:
        if 'x' in latest and 'y' in latest:
            st.metric(
                "📍 Position",
                f"({latest['x']:.2f}, {latest['y']:.2f})"
            )
        else:
            st.metric("📍 Position", "N/A")
    
    with col5:
        if 'heading' in latest:
            st.metric("🧭 Heading", f"{latest['heading']:.0f}°")
        else:
            st.metric("🧭 Heading", "N/A")
    
    # Last action
    st.info(f"🚀 **Last Action:** {latest['action'].upper().replace('_', ' ')}")
    
    # Obstacle status
    st.subheader("🚧 Obstacle Detection Status")
    obs_col1, obs_col2, obs_col3, obs_col4 = st.columns(4)
    
    with obs_col1:
        status = "🔴 BLOCKED" if latest.get('obstacles_front', False) else "🟢 CLEAR"
        st.markdown(f"**Front:** {status}")
    
    with obs_col2:
        status = "🔴 BLOCKED" if latest.get('obstacles_back', False) else "🟢 CLEAR"
        st.markdown(f"**Back:** {status}")
    
    with obs_col3:
        status = "🔴 BLOCKED" if latest.get('obstacles_left', False) else "🟢 CLEAR"
        st.markdown(f"**Left:** {status}")
    
    with obs_col4:
        status = "🔴 BLOCKED" if latest.get('obstacles_right', False) else "🟢 CLEAR"
        st.markdown(f"**Right:** {status}")
    
    st.markdown("---")
    
    # Visualization Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗺️ Path Map",
        "🌡️ Environment",
        "🌱 Soil Analysis",
        "📊 Statistics",
        "📋 Raw Data"
    ])
    
    with tab1:
        st.subheader("Rover Movement Path")
        path_map = create_path_map(df)
        if path_map:
            st.plotly_chart(path_map, use_container_width=True)
        
        # 3D visualization
        if 'soil_ph' in df.columns:
            st.subheader("3D Path Visualization (with pH)")
            path_3d = create_3d_path(df)
            if path_3d:
                st.plotly_chart(path_3d, use_container_width=True)
    
    with tab2:
        st.subheader("Environmental Conditions")
        env_chart = create_environmental_chart(df)
        if env_chart:
            st.plotly_chart(env_chart, use_container_width=True)
        
        # Statistics
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Temperature Statistics:**")
            st.write(df['temperature'].describe())
        with col2:
            st.markdown("**Humidity Statistics:**")
            st.write(df['humidity'].describe())
    
    with tab3:
        st.subheader("Soil pH Analysis")
        ph_chart = create_soil_ph_chart(df)
        if ph_chart:
            st.plotly_chart(ph_chart, use_container_width=True)
        
        # pH Statistics
        if 'soil_ph' in df.columns:
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average pH", f"{df['soil_ph'].mean():.2f}")
            with col2:
                st.metric("Min pH", f"{df['soil_ph'].min():.2f}")
            with col3:
                st.metric("Max pH", f"{df['soil_ph'].max():.2f}")
            
            # pH classification
            avg_ph = df['soil_ph'].mean()
            if avg_ph < 6.5:
                st.warning("⚠️ Soil is **acidic** (pH < 6.5)")
            elif avg_ph > 7.5:
                st.info("ℹ️ Soil is **alkaline** (pH > 7.5)")
            else:
                st.success("✅ Soil is **neutral** (pH 6.5-7.5)")
    
    with tab4:
        st.subheader("Rover Performance Statistics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Obstacle detection
            obstacle_chart = create_obstacle_heatmap(df)
            if obstacle_chart:
                st.plotly_chart(obstacle_chart, use_container_width=True)
        
        with col2:
            # Action distribution
            action_chart = create_action_distribution(df)
            if action_chart:
                st.plotly_chart(action_chart, use_container_width=True)
    
    with tab5:
        st.subheader("Raw Data Table")
        
        # Time range filter
        col1, col2 = st.columns(2)
        with col1:
            show_last_n = st.selectbox(
                "Show last N records:",
                options=[10, 25, 50, 100, 'All'],
                index=1
            )
        
        # Display data
        if show_last_n == 'All':
            st.dataframe(df, use_container_width=True)
        else:
            st.dataframe(df.tail(show_last_n), use_container_width=True)
        
        # Download button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Download Data as CSV",
            data=csv,
            file_name=f"rover_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Footer
    st.markdown("---")
    st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Auto-refresh
    if auto_refresh:
        import time
        time.sleep(2)
        st.rerun()

if __name__ == "__main__":
    main()