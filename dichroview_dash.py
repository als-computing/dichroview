#!/usr/bin/env python

"""dichroview_dash.py

    Plot live data from databroker
"""

import os
# from time import sleep
from datetime import datetime, date, time #, timedelta
# from dateutil import relativedelta as rel_date
import pytz

import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from dash_extensions import WebSocket
import plotly.express as px
import flask

import pandas as pd
import json


tz_id = 'America/Los_Angeles'
timezone = pytz.timezone(tz_id)


def create_dash_app(requests_pathname_prefix: str = None) -> dash.Dash:
    """
    TBD
    """
    server = flask.Flask(__name__)
    server.secret_key = os.environ.get('secret_key', 'secret')

    app = dash.Dash(__name__, server=server, requests_pathname_prefix=requests_pathname_prefix)

    app.layout = html.Div([
        html.H1('Live Plotting'),
        html.H3('<Project Name>', id="project"),
        html.Div([
            html.H4('<Scan #>', id="scan_id"),
            html.H4('<Scan ID>', id="scan_uid"),
            html.H4('<Timestamp>', id="timestamp"),
        ], className="scan_title"),
        html.Div([
            html.H4('<Purpose>', id="purpose"),
            html.H4('<Scan Type>', id="scan_type"),
        ], className="scan_subtitle"),
        dcc.Graph(id='graph'),
        WebSocket(id="new-run", url="ws://127.0.0.1:8003/new-run"),
        WebSocket(id="add-data", url="ws://127.0.0.1:8003/add-data"),
        ], className="container")

    @app.callback(
        Output("graph", "figure"), 
        Output("project", "children"), 
        Output("scan_id", "children"), 
        Output("scan_uid", "children"), 
        Output("timestamp", "children"), 
        Output("purpose", "children"), 
        Output("scan_type", "children"), 
        [Input("new-run", "message")], 
        [Input("add-data", "message")], 
        [State("graph", "figure")],
        )
    def build_graph(msg_new_run, msg_add_data, figure):
        ctx = dash.callback_context
        # print(ctx.__dict__)
        # if msg_new_run:
        #     print(f"{msg_new_run.keys()=}")
        #     print(f"{json.loads(msg_new_run['data']).keys()=}")
        # else:
        #     print(f"{msg_new_run=}")
        # if msg_add_data:
        #     print(f"{msg_add_data.keys()=}")
        #     print(f"{json.loads(msg_add_data['data']).keys()=}")
        # else:
        #     print(f"{msg_add_data=}")
        # ctx_msg = json.dumps({
        #         'states': ctx.states,
        #         'triggered': ctx.triggered,
        #         'inputs': ctx.inputs
        #     }, indent=2)
        # print(ctx_msg)
        # raise PreventUpdate 
        if not ctx.triggered:
            raise PreventUpdate
        
        project = dash.no_update
        scan_id = dash.no_update
        scan_uid = dash.no_update
        timestamp = dash.no_update
        purpose = dash.no_update
        scan_type = dash.no_update

        msg_id = ctx.triggered[0]['prop_id'].split('.')[0]
        print(f"Trigger: {msg_id}")
        if msg_id == "new-run":
            msg = json.loads(msg_new_run['data'])
            # print(msg)
            # raise PreventUpdate
            msg = msg["start"]
            fig = new_graph(msg, figure)
            project = msg["project"]
            scan_id = msg["scan_id"]
            scan_uid = msg["uid"]
            dtime = datetime.fromtimestamp(msg["time"], tz=timezone)
            timestamp = dtime.strftime("(%a) %b %d, %Y @ %H:%M:%S.%f [%z]")
            purpose = msg["purpose"]
            scan_type = f'[{msg["scan_type"]}]'
        elif msg_id == "add-data":
            msg = json.loads(msg_add_data['data'])
            # print(msg)
            # raise PreventUpdate
            msg = msg["event"]
            fig = update_graph(msg, figure)
            dtime = datetime.fromtimestamp(msg["time"], tz=timezone)
            timestamp = dtime.strftime("(%a) %b %d, %Y @ %H:%M:%S.%f [%z]")
        
        return fig, project, scan_id, scan_uid, timestamp, purpose, scan_type

    # @app.callback(Output("graph", "figure"), [Input("new-run", "message")], [State("graph", "figure")])
    def new_graph(msg, figure):
        hints = msg["hints"]
        x_label = hints["dimensions"][0][0][0]
        y_label = hints["fields"][0]

        df = pd.DataFrame({x_label: [], y_label: []})
        # print(f"{df=}")

        fig = px.scatter(df, x=x_label, y=y_label,)
        norm_signals = msg.get("normalization_signals", None)
        if norm_signals:
            fig['layout']['yaxis']['title']['text'] += f"/{norm_signals[0]}"
        print(fig)
        # fig = px.scatter(df, x="gdp per capita", y="life expectancy",
        #          size="population", color="continent", hover_name="country",
        #          log_x=True, size_max=60)
        return fig

    # @app.callback(Output("graph", "figure"), [Input("add-data", "message")], [State("graph", "figure")])
    def update_graph(msg, figure):
        # print(figure['data'])
        if figure['data']:
            x, y = figure['data'][0]['x'], figure['data'][0]['y']
        else:
            x, y = [], []
        x_label = figure['layout']['xaxis']['title']['text']
        y_label = figure['layout']['yaxis']['title']['text']
        y_labels = y_label.rsplit('/', 1)
        if len(y_labels) > 1:
            y_label = y_labels[0]
            y0_label = y_labels[-1]
        else:
            y0_label = None
        # print(f"{y0_label=}")
        # return go.Figure(data=go.Scatter(x=x + [len(x)], y=y + [float(msg['data'])]))
        new_x, new_y = msg["data"][x_label], msg["data"][y_label]
        if y0_label:
            new_y0 = msg["data"][y0_label]
            new_y /= new_y0
            y_label = f"{y_label}/{y0_label}"
        x.append(new_x)
        y.append(new_y)
        df = pd.DataFrame({x_label: x, y_label: y})

        fig = px.scatter(df, x=x_label, y=y_label,)
        return fig

    return app
