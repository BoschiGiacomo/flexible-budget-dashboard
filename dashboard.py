import numpy as np
import pandas as pd
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from dash import Dash, dcc, html, Input, Output, callback

import callbacks

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

upload_style = {
    "width": "100%",
    "height": "60px",
    "lineHeight": "60px",
    "borderWidth": "1px",
    "borderStyle": "solid",
    "borderRadius": "5px",
    "textAlign": "center",
    "margin": "10px 0",
}

app.layout = dbc.Container(
    [
        dcc.Store(id="params-data-store"),
        dcc.Store(id="sales-data-store"),
        html.H1("Data Upload", style={"textAlign": "center"}),
        html.H2("Upload sales data and parameters here", style={"textAlign": "center"}),
        html.Hr(),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Upload(
                            id="sales-data-upload",
                            children=html.Div(
                                [html.A("Upload"), " or Drop Sales Data"]
                            ),
                            style=upload_style,
                            multiple=False,
                        ),
                        html.Div(id="sales-upload-output"),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        dcc.Upload(
                            id="params-data-upload",
                            children=html.Div(
                                [html.A("Upload"), " or Drop Parameters.json file"]
                            ),
                            style=upload_style,
                            multiple=False,
                        ),
                        html.Div(id="parameters-upload-output"),
                    ],
                    md=6,
                ),
            ]
        ),
        html.Hr(),
        html.H3("Sales Data", style={"textAlign": "center"}),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dcc.Graph(id="sales-data-graph"),
                    ],
                    md=12,
                ),
            ],
        ),
        html.Hr(),
        html.H3("Parameters Data", style={"textAlign": "center"}),
        dbc.Row(
            [
                dag.AgGrid(
                    id="product-data-table",
                    columnDefs=[
                        {"field": "product_code"},
                    ],
                    rowData=[],
                    defaultColDef={
                        "sortable": True,
                        "filter": True,
                        "resizable": True,
                    },
                    columnSize="autoSize",
                ),
            ],
        ),
        dbc.Row(
            [dcc.Graph(id="params-overhead-pareto")],
        ),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
