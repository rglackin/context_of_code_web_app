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
import re

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
        # Get unique stock symbols by extracting them from metric names
        stock_metrics = db.session.query(DeviceMetricType.name)\
            .filter(DeviceMetricType.name.like('Stock Price (%)'))\
            .distinct()\
            .all()

        # Extract stock symbols from metric names
        stock_options = []
        for row in stock_metrics:
            name = row[0]  # Extract string from SQLAlchemy Row
            symbol_match = re.search(r'Stock Price \((.*?)\)', name)
            if symbol_match:
                symbol = symbol_match.group(1)
                stock_options.append({'label': symbol, 'value': symbol})
        default_stock = stock_options[0]['value'] if stock_options else None

        return html.Div([
            html.H1("Stock Metrics", className="dashboard-title"),
            dcc.Interval(id='stock-interval-component', interval=60*1000, n_intervals=0),
            html.Div([
                html.Div([
                    dcc.Graph(id='stock-price-graph')
                ], className="card"),
                html.Div([
                    dcc.Graph(id='btc-usd-graph')
                ], className="card"),
                html.Div([
                    dcc.Dropdown(
                        id='stock-dropdown',
                        options=stock_options,  # Use the processed list of options
                        value=default_stock,
                        placeholder="Select a Stock Symbol",
                        clearable=False
                    ),
                    dcc.Graph(id='stock-price-line-chart')
                ], className="card")
            ], className="card-container"),
            html.Button("Refresh Data", id="stock-refresh-button", className="nav-button"),
            html.H3("Add Stock Symbols", className="card-title"),
                    dcc.Input(
                        id='stock-symbols-input',
                        type='text',
                        placeholder='Enter comma-separated stock symbols (e.g., AAPL,MSFT,GOOG)',
                        style={'width': '100%', 'marginBottom': '10px'}
                    ),
                    html.Button('Add Symbols', id='add-symbols-button', className="nav-button"),
                    html.Div(id='symbols-status-message')
        ])
    
    def base_metric_query(fetch_aggregator=False):
        columns = [Snapshot.client_timestamp_epoch, Metric.value]
        if fetch_aggregator:
            columns.append(Aggregator.name)
        return db.session.query(*columns).join(Metric).join(DeviceMetricType).join(Device)

    def add_aggregator_join(query):
        return query.join(Aggregator)

    def add_metric_filter(query, metric_name):
        return query.filter(DeviceMetricType.name == metric_name)

    def add_aggregator_filter(query, aggregator_id):
        return query.filter(Device.aggregator_id == aggregator_id)

    def order_by_timestamp(query):
        return query.order_by(desc(Snapshot.client_timestamp_epoch))

    def add_limit(query, limit):
        return query.limit(limit)

    def fetch_metric_data(metric_name, aggregator_id=None, limit=None):
        try:
            query = base_metric_query()
            query = add_metric_filter(query, metric_name)
            if aggregator_id:
                query = add_aggregator_filter(query, aggregator_id)
            query = order_by_timestamp(query)
            if limit:
                query = add_limit(query, limit)
            return query.all()
        except Exception as e:
            logger.error(f"Error fetching {metric_name} data: {str(e)}")
            return []

    def fetch_metric_data_by_aggregator(metric_name):
        try:
            query = base_metric_query(fetch_aggregator=True)
            query = add_aggregator_join(query)
            query = add_metric_filter(query, metric_name)
            query = order_by_timestamp(query)
            return query.all()
        except Exception as e:
            logger.error(f"Error fetching {metric_name} data: {str(e)}")
            return []

    def create_time_series_figure(df, metric_name, yaxis_title):
        figure = px.line(df, x='timestamp', y='value', title=f'{metric_name} Over Time')
        figure.update_layout(
            xaxis_title='Time',
            yaxis_title=yaxis_title,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            )
        )
        return figure

    def create_time_series_graph(metric_name):
        figure = go.Figure()
        metric_data = fetch_metric_data_by_aggregator(metric_name)
        if metric_data:
            logger.info(f"Data found for {metric_name}: {metric_data}")
            df = pd.DataFrame(metric_data, columns=['timestamp', 'value', 'aggregator'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            for aggregator in df['aggregator'].unique():
                agg_df = df[df['aggregator'] == aggregator]
                figure.add_trace(go.Scatter(
                    x=agg_df['timestamp'],
                    y=agg_df['value'],
                    mode='lines',
                    name=aggregator
                ))
            figure.update_layout(
                title=f'{metric_name} Over Time',
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
                normalized_df['normalized_value'] = 0.0  # Initialize with default values
                stocks = normalized_df['Stock'].unique()
                
                for stock in stocks:
                    stock_data = normalized_df[normalized_df['Stock'] == stock]
                    if not stock_data.empty:
                        # Get the first value for this stock
                        first_value = stock_data['value'].iloc[0]
                        if (first_value != 0):  # Avoid division by zero
                            # Calculate percentage change from first value
                            normalized_df.loc[normalized_df['Stock'] == stock, 'normalized_value'] = \
                                ((normalized_df.loc[normalized_df['Stock'] == stock, 'value'] - first_value) / first_value) * 100
                
                # Remove any rows with NaN values
                normalized_df = normalized_df.dropna(subset=['normalized_value'])
                
                # Make sure we still have data to plot
                if not normalized_df.empty:
                    # Create the figure using go.Figure and go.Scatter for more control
                    figure = go.Figure()
                    
                    for stock in stocks:
                        stock_data = normalized_df[normalized_df['Stock'] == stock]
                        if not stock_data.empty:
                            figure.add_trace(go.Scatter(
                                x=stock_data['timestamp'],
                                y=stock_data['normalized_value'],
                                mode='lines',
                                name=stock
                            ))
                    
                    figure.update_layout(
                        title='Stock Price Performance (% Change from Initial Price)',
                        xaxis_title='Time',
                        yaxis_title='Percentage Change (%)',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="center",
                            x=0.5,
                            itemsizing='constant',
                            itemwidth=40,
                        ),
                        margin=dict(t=100),
                        title_x=0.5,
                        title_y=0.95
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
                else:
                    logger.warning("No valid data after normalization for stocks")
                    
            else:
                logger.warning("No stock data found")
                    
        except Exception as e:
            logger.error(f"Error updating stock graph: {str(e)}")
            # Log the full traceback for debugging
            import traceback
            logger.error(traceback.format_exc())
    
        return figure
    
    def create_btc_usd_time_series_graph():
        figure = go.Figure()

        try:
            metric_name = "BTC-USD"
            logger.info(f"Fetching {metric_name} data")
            metric_data = fetch_metric_data(metric_name)
            logger.info(f"{metric_name} data fetched")
            logger.debug(f"Number of {metric_name} records found: {len(metric_data)}")
            
            if metric_data:
                df = pd.DataFrame(metric_data, columns=['timestamp', 'value'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
                figure = create_time_series_figure(df, metric_name, 'Bitcoin value (USD)')
        except Exception as e:
            logger.error(f"Error updating {metric_name} graph: {str(e)}")

        return figure
    
    def create_gauge(metric_name, aggregator_id):
        gauge = go.Figure()
        if not aggregator_id:
            logger.error("Aggregator ID not provided for %s gauge", metric_name)
            return gauge

        metric_data = fetch_metric_data(metric_name, aggregator_id, limit=1)
        if metric_data:
            timestamp, value = metric_data[0]
            readable_time = datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=value,
                title={'text': f"{metric_name}", 'font': {'size': 24}},
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
            gauge.add_annotation(
                text=f"Last updated: {readable_time}",
                x=0.5,
                y=-0.25,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=14)
            )
            gauge.update_layout(
                height=250,
                margin=dict(l=20, r=20, t=60, b=60)
            )
        return gauge

    def create_stock_line_chart(symbol):
        figure = go.Figure()
        metric_name = f"Stock Price ({symbol})"
        metric_data = fetch_metric_data(metric_name)
        if metric_data:
            df = pd.DataFrame(metric_data, columns=['timestamp', 'value'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
            figure = create_time_series_figure(df, metric_name, 'Stock Price (USD)')
            if not df.empty:
                current_price = df['value'].iloc[0]
                figure.add_annotation(
                    text=f"${current_price:.2f}",
                    x=df['timestamp'].iloc[0],
                    y=current_price,
                    xref="x",
                    yref="y",
                    showarrow=True,
                    arrowhead=2,
                    ax=0,
                    ay=-40,
                    font=dict(size=14, color="red"),
                    bgcolor="white"
                )
        return figure

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
        Output('btc-usd-graph', 'figure'),
        [Input('stock-refresh-button', 'n_clicks')]
    )
    def update_btc_usd_graph(n_clicks):
        return create_btc_usd_time_series_graph()
    
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
    
    @dash_app.callback(
        Output('stock-price-line-chart', 'figure'),
        [Input('stock-refresh-button', 'n_clicks'),
         Input('stock-dropdown', 'value')]
    )
    def update_stock_line_chart(n_clicks, symbol):
        if not symbol:
            return go.Figure()
        return create_stock_line_chart(symbol)

    # Callback to update graphs when interval triggers
    @dash_app.callback(
        [Output('cpu-percent-graph', 'figure', allow_duplicate=True),
         Output('ram-usage-graph', 'figure', allow_duplicate=True),
         Output('cpu-usage-gauge', 'figure', allow_duplicate=True),
         Output('ram-usage-gauge', 'figure', allow_duplicate=True)],
        [Input('interval-component', 'n_intervals')],
        [dash.State('aggregator-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_winos_graphs_interval(n_intervals, aggregator_id):
        logger.info(f"Interval refresh triggered for WinOS metrics")
        cpu_figure = create_time_series_graph('CPU Percent')
        ram_figure = create_time_series_graph('RAM Usage')
        cpu_gauge = create_gauge('CPU Percent', aggregator_id)
        ram_gauge = create_gauge('RAM Usage', aggregator_id)
        return cpu_figure, ram_figure, cpu_gauge, ram_gauge

    @dash_app.callback(
        [Output('stock-price-graph', 'figure', allow_duplicate=True),
         Output('btc-usd-graph', 'figure', allow_duplicate=True),
         Output('stock-price-line-chart', 'figure', allow_duplicate=True)],
        [Input('stock-interval-component', 'n_intervals')],
        [dash.State('stock-dropdown', 'value')],
        prevent_initial_call=True
    )
    def update_stock_graphs_interval(n_intervals, symbol):
        logger.info(f"Interval refresh triggered for stock metrics")
        stock_figure = create_all_stocks_time_series_graph()
        btc_figure = create_btc_usd_time_series_graph()
        stock_line_chart = create_stock_line_chart(symbol) if symbol else go.Figure()
        return stock_figure, btc_figure, stock_line_chart

    # This callback will change the stock symbols returned by the /stock-symbols route
    @dash_app.callback(
    Output('symbols-status-message', 'children'),
    [Input('add-symbols-button', 'n_clicks')],
    [dash.State('stock-symbols-input', 'value')]
    )
    def update_stock_symbols(n_clicks, symbols_input):
        if not n_clicks:
            return ""

        if not symbols_input:
            return html.Div("Please enter at least one stock symbol", style={'color': 'red'})

        try:
            logger.info("Stock symbols input received")
            # Parse the input into a list of symbols
            symbols = [symbol.strip() for symbol in symbols_input.split(',')]
            if not symbols:
                return html.Div("Please enter valid stock symbols", style={'color': 'red'})

            # Import directly from routes and call the functions
            from routes import add_stock_symbols_internal

            # Call the function directly instead of using HTTP
            result = add_stock_symbols_internal({'symbols': symbols})

            if isinstance(result, tuple):
                json_response, status_code = result
            else:
                json_response = result
                status_code = 200

            logger.debug(f"Response: {json_response}, Status: {status_code}")

            if status_code == 200:
                # Get valid and invalid symbols from the response
                valid_symbols = json_response.get('symbols', [])
                invalid_symbols = json_response.get('invalid_symbols', [])

                # Create a success message
                valid_msg = f"Successfully added {len(valid_symbols)} stock symbol(s): {', '.join(valid_symbols)}"

                # If there were invalid symbols, add a warning message
                if invalid_symbols:
                    invalid_msg = f"Invalid symbols that were ignored: {', '.join(invalid_symbols)}"
                    return html.Div([
                        html.Div(valid_msg, style={'color': 'green'}),
                        html.Div(invalid_msg, style={'color': 'orange', 'marginTop': '10px'})
                    ])
                else:
                    return html.Div(valid_msg, style={'color': 'green'})
            else:
                error_msg = json_response.get('error', 'Unknown error occurred')
                return html.Div(f"Error adding symbols: {error_msg}", style={'color': 'red'})
        except Exception as e:
            logger.error(f"Error updating stock symbols: {str(e)}")
            return html.Div(f"An error occurred: {str(e)}", style={'color': 'red'})
    return dash_app