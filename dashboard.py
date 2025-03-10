import dash
from dash import dcc, html, Input, Output, callback
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import pandas as pd
from models import db, Device, Aggregator, Snapshot, DeviceMetricType, Metric
from sqlalchemy import desc, func
import logging
import os

logger = logging.getLogger(__name__)

def create_dash_app(flask_app):
    """Create and return a Dash app instance"""
    current_dir = os.getcwd()
    assets_dir = os.path.join(current_dir, 'assets')
    logger.debug(f"Current directory: {current_dir}")
    logger.debug(f"Assets directory: {assets_dir}")
    logger.debug(f"Assets directory exists: {os.path.exists(assets_dir)}")
    if os.path.exists(assets_dir):
        logger.debug(f"Assets directory contents: {os.listdir(assets_dir)}")

    dash_app = dash.Dash(
        __name__,
        server=flask_app,
        url_base_pathname='/',
        assets_folder='assets',
        suppress_callback_exceptions=True  # Add this line to suppress callback exceptions
    )

    # Define the app layout
    dash_app.layout = html.Div([
        html.H1("Metrics Dashboard", className="dashboard-title"),
        html.Div([
            html.Button("Windows OS Metrics", id="win-os-metrics-button", className="nav-button"),
            html.Button("Stock Metrics", id="stock-metrics-button", className="nav-button")
        ], className="nav-buttons-container"),
        dcc.Location(id='url', refresh=False),
        html.Div(id='page-content')
    ], className="dashboard-container")

    @dash_app.callback(
        Output('page-content', 'children'),
        [Input('win-os-metrics-button', 'n_clicks'),
         Input('stock-metrics-button', 'n_clicks')]
    )
    def display_metrics(win_clicks, stock_clicks):
        ctx = dash.callback_context
        if not ctx.triggered:
            return html.Div()
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        if button_id == 'win-os-metrics-button':
            return get_windows_metrics_layout()
        elif button_id == 'stock-metrics-button':
            return get_stock_metrics_layout()
        return html.Div()

    

    def get_windows_metrics_layout():
        aggregators = db.session.query(Aggregator).all()
        default_aggregator = aggregators[0].aggregator_id if aggregators else None
    
        return html.Div([
            html.H1("Windows Metrics", className="dashboard-title"),
            dcc.Interval(id='interval-component', interval=30*1000, n_intervals=0),
            html.Div([
                html.Div([
                    dcc.Graph(id='cpu-percent-graph')
                ], className="card"),
                html.Div([
                    dcc.Graph(id='ram-usage-graph')
                ], className="card"),
                html.Div([
                    dcc.Dropdown(
                        id='aggregator-dropdown',
                        options=[{'label': agg.name, 'value': agg.aggregator_id} for agg in aggregators],
                        value=default_aggregator,
                        placeholder="Select an Aggregator",
                        clearable=False
                    ),
                    html.Div([
                        html.Div([
                            dcc.Graph(id='cpu-usage-gauge', className="gauge")
                        ], className="six columns"),
                        html.Div([
                            dcc.Graph(id='ram-usage-gauge', className="gauge")
                        ], className="six columns")
                    ], className="row")
                ], className="card"),
            ], className="card-container"),
            # Add a trigger button to manually update graphs
            html.Button("Refresh Data", id="refresh-button", className="nav-button")
        ])
    
    def get_stock_metrics_layout():
        return html.Div([
            html.H1("Stock Metrics", className="dashboard-title"),
            dcc.Interval(id='stock-interval-component', interval=30*1000, n_intervals=0),
            html.Div([
                html.Div([
                    dcc.Graph(id='stock-price-graph')
                ], className="card")
            ], className="card-container"),
            html.Button("Refresh Data", id="stock-refresh-button", className="nav-button")
        ])
    
    def create_time_series_graph(metric_name):
        figure = go.Figure()
    
        try:
            logger.info(f"Fetching {metric_name} data")
            metric_data = db.session.query(Snapshot.client_timestamp_epoch, Metric.value, Aggregator.name)\
                .join(Metric)\
                .join(DeviceMetricType)\
                .join(Device)\
                .join(Aggregator)\
                .filter(DeviceMetricType.name == metric_name)\
                .order_by(Snapshot.client_timestamp_epoch)\
                .all()
            logger.info(f"{metric_name} data fetched")
            logger.debug(f"Number of {metric_name} records found: {len(metric_data)}")
            
            if metric_data:
                df = pd.DataFrame(metric_data, columns=['timestamp', 'value', 'Aggregator'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                figure = px.line(df, x='timestamp', y='value', color='Aggregator', title=f'{metric_name} Over Time')
                figure.update_layout(
                    xaxis_title='Time',
                    yaxis_title=metric_name,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    )
                )
        except Exception as e:
            logger.error(f"Error updating {metric_name} graph: {str(e)}")
    
        return figure
    
    def create_all_stocks_time_series_graph():
        figure = go.Figure()
    
        try:
            logger.info("Fetching all stock data")
            metric_data = db.session.query(Snapshot.client_timestamp_epoch, Metric.value, DeviceMetricType.name)\
                .select_from(Snapshot)\
                .join(Metric, Snapshot.snapshot_id == Metric.snapshot_id)\
                .join(DeviceMetricType, Metric.device_metric_type_id == DeviceMetricType.device_metric_type_id)\
                .filter(DeviceMetricType.name.like('Stock Price (%)'))\
                .order_by(Snapshot.client_timestamp_epoch)\
                .all()
            logger.info("All stock data fetched")
            logger.debug(f"Number of stock records found: {len(metric_data)}")
            
            if metric_data:
                df = pd.DataFrame(metric_data, columns=['timestamp', 'value', 'Stock'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                df['Stock'] = df['Stock'].str.extract(r'Stock Price \((.*?)\)')
                
                # Normalize data - calculate percentage change relative to first value for each stock
                normalized_df = df.copy()
                stocks = normalized_df['Stock'].unique()
                
                for stock in stocks:
                    stock_data = normalized_df[normalized_df['Stock'] == stock]
                    if not stock_data.empty:
                        # Get the first value for this stock
                        first_value = stock_data['value'].iloc[0]
                        if first_value != 0:  # Avoid division by zero
                            # Calculate percentage change from first value
                            normalized_df.loc[normalized_df['Stock'] == stock, 'normalized_value'] = \
                                ((normalized_df.loc[normalized_df['Stock'] == stock, 'value'] - first_value) / first_value) * 100
                
                # Create the figure with normalized values
                figure = px.line(
                    normalized_df, 
                    x='timestamp', 
                    y='normalized_value', 
                    color='Stock', 
                    title='Stock Price Performance (% Change from Initial Price)'
                )
                
                figure.update_layout(
                    xaxis_title='Time',
                    yaxis_title='Percentage Change (%)',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="center",
                        x=0.5
                    )
                )
                
                # Add a horizontal line at y=0 for reference
                figure.add_shape(
                    type="line",
                    x0=normalized_df['timestamp'].min(),
                    x1=normalized_df['timestamp'].max(),
                    y0=0,
                    y1=0,
                    line=dict(color="gray", width=1, dash="dash")
                )
                
        except Exception as e:
            logger.error(f"Error updating stock graph: {str(e)}")
            # Log the full traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
    
        return figure
    
    def create_gauge(metric_name, aggregator_id):
        gauge = go.Figure()
    
        if not aggregator_id:
            logger.error("Aggregator ID not provided for %s gauge", metric_name)
            return gauge
    
        try:
            logger.info(f"Fetching {metric_name} data for gauge with aggregator_id: {aggregator_id}")
            metric_data = db.session.query(Snapshot.client_timestamp_epoch, Metric.value)\
                .join(Metric)\
                .join(DeviceMetricType)\
                .join(Device)\
                .filter(DeviceMetricType.name == metric_name, 
                        Device.aggregator_id == aggregator_id)\
                .order_by(Snapshot.client_timestamp_epoch.desc())\
                .first()
            logger.info(f"{metric_name} data for gauge fetched")
    
            if metric_data:
                timestamp, value = metric_data
                # Convert timestamp to readable format
                readable_time = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
    
                # Create gauge with text components
                gauge = go.Figure(go.Indicator(
                    mode="gauge+number",
                    value=value,
                    title={
                        'text': f"{metric_name}",
                        'font': {'size': 24}
                    },
                    gauge={
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "darkblue" if value < 70 else "red"},
                        'steps': [
                            {'range': [0, 50], 'color': 'lightgreen'},
                            {'range': [50, 70], 'color': 'yellow'},
                            {'range': [70, 100], 'color': 'pink'}
                        ],
                        'threshold': {
                            'line': {'color': "red", 'width': 4},
                            'thickness': 0.75,
                            'value': 90
                        }
                    }
                ))
    
                # Add timestamp as an annotation
                gauge.add_annotation(
                    text=f"Last updated: {readable_time}",
                    x=0.5,
                    y=-0.25,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=14)
                )
    
                # Customize layout for better text display
                gauge.update_layout(
                    height=250,
                    margin=dict(l=20, r=20, t=60, b=60)  # Increased bottom margin for annotation
                )
        except Exception as e:
            logger.error(f"Error updating {metric_name} gauge: {str(e)}")
    
        return gauge
    
    @dash_app.callback(
        Output('cpu-percent-graph', 'figure'),
        [Input('refresh-button', 'n_clicks')]
    )
    def update_cpu_graph(n_clicks):
        return create_time_series_graph('CPU Percent')
    
    @dash_app.callback(
        Output('ram-usage-graph', 'figure'),
        [Input('refresh-button', 'n_clicks')]
    )
    def update_ram_graph(n_clicks):
        return create_time_series_graph('RAM Usage')
    
    @dash_app.callback(
        Output('stock-price-graph', 'figure'),
        [Input('stock-refresh-button', 'n_clicks')]
    )
    def update_all_stocks_graph(n_clicks):
        return create_all_stocks_time_series_graph()
    
    @dash_app.callback(
        Output('cpu-usage-gauge', 'figure'),
        [Input('refresh-button', 'n_clicks'),
         Input('aggregator-dropdown', 'value')]
    )
    def update_cpu_gauge(n_clicks, aggregator_id):
        return create_gauge('CPU Percent', aggregator_id)
    
    @dash_app.callback(
        Output('ram-usage-gauge', 'figure'),
        [Input('refresh-button', 'n_clicks'),
         Input('aggregator-dropdown', 'value')]
    )
    def update_ram_gauge(n_clicks, aggregator_id):
        return create_gauge('RAM Usage', aggregator_id)
    
    # Add callback to update graphs when interval triggers
    @dash_app.callback(
        [Output('cpu-percent-graph', 'figure', allow_duplicate=True),
         Output('ram-usage-graph', 'figure', allow_duplicate=True),
         Output('cpu-usage-gauge', 'figure', allow_duplicate=True),
         Output('ram-usage-gauge', 'figure', allow_duplicate=True)],
        [Input('interval-component', 'n_intervals')],
        [dash.State('aggregator-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_graphs_interval(n_intervals, aggregator_id):
        logger.info(f"Interval refresh triggered")
        cpu_figure = create_time_series_graph('CPU Percent')
        ram_figure = create_time_series_graph('RAM Usage')
        cpu_gauge = create_gauge('CPU Percent', aggregator_id)
        ram_gauge = create_gauge('RAM Usage', aggregator_id)
        return cpu_figure, ram_figure, cpu_gauge, ram_gauge
    
    # Add callback to update stock graph when interval triggers
    @dash_app.callback(
        Output('stock-price-graph', 'figure', allow_duplicate=True),
        [Input('stock-interval-component', 'n_intervals')],
        prevent_initial_call=True
    )
    def update_all_stocks_graph_interval(n_intervals):
        return create_all_stocks_time_series_graph()

    return dash_app