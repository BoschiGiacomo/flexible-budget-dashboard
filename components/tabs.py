import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from dash import dcc, html

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

upload_layout = [
    html.H1("Data Upload", style={"textAlign": "center"}),
    html.H2("Upload sales data and parameters here", style={"textAlign": "center"}),
    html.Hr(),
    dbc.Row(
        [
            dbc.Col(
                [
                    dcc.Upload(
                        id="sales-data-upload",
                        children=html.Div([html.A("Upload"), " or Drop Sales Data"]),
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
                columnSize="responsiveSizeToFit",
                style={"height": "300px", "width": "100%"},
            ),
        ],
    ),
    dbc.Row(
        [dcc.Graph(id="params-overhead-pareto")],
    ),
]

budgets_layout = [
    html.H1("Budgets view", style={"textAlign": "center"}),
    html.Hr(),
    dbc.Col(
        dcc.RadioItems(
            id="budgets-view-mode",
            options=[
                {"label": "Monthly", "value": "monthly"},
                {"label": "Quarterly", "value": "quarterly"},
            ],
            value="monthly",
            inline=True,
        ),
        className="d-flex justify-content-center align-items-center",
    ),
    html.Hr(),
    dbc.Accordion(
        [
            dbc.AccordionItem(
                title="Sales Budget",
                children=[
                    dag.AgGrid(
                        id="sales-budget-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                    html.H3("Sales Summary", style={"textAlign": "center"}),
                    dcc.Graph(id="sales-stacked-bar-graph"),
                ],
            ),
            dbc.AccordionItem(
                title="Production Budget",
                children=[
                    dag.AgGrid(
                        id="production-budget-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                    html.H3("Inventory Movements", style={"textAlign": "center"}),
                    dcc.Graph(id="inventory-movement-graph"),
                    html.Hr(),
                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="waterfall-quarter-dropdown",
                                        options=[],
                                        value=None,
                                        multi=True,
                                    ),
                                ],
                                md=5,
                            ),
                            dbc.Col(
                                [
                                    dcc.Dropdown(
                                        id="waterfall-product-dropdown",
                                        options=[],
                                        value=None,
                                    ),
                                ],
                                md=5,
                            ),
                            dbc.Col(
                                [
                                    dcc.RadioItems(
                                        id="waterfall-mode",
                                        options=[
                                            {"label": "Build-up", "value": "buildup"},
                                            {"label": "Delta", "value": "delta"},
                                        ],
                                        value="buildup",
                                        inline=True,
                                    ),
                                ],
                                md=2,
                            ),
                        ]
                    ),
                    html.Hr(),
                    dcc.Graph(id="inventory-waterfall-chart"),
                ],
            ),
            dbc.AccordionItem(
                title="Materials Budget",
                children=[
                    dag.AgGrid(
                        id="materials-budget-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                    html.Hr(),
                    html.H3("Materials Overview", style={"textAlign": "center"}),
                    dcc.Graph(id="materials-expenses-stacked"),
                ],
            ),
            dbc.AccordionItem(
                title="Labor Budget",
                children=[
                    dag.AgGrid(
                        id="labor-budget-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                    html.Hr(),
                    html.H3("Labor Overview", style={"textAlign": "center"}),
                    dcc.Graph(id="labor-expenses-stacked"),
                ],
            ),
        ]
    ),
]

financial_layout = [
    html.H1("Financial Overview & Summary", style={"textAlign": "center"}),
    html.Hr(),
    dbc.Accordion(
        [
            dbc.AccordionItem(
                title="Cash Collection",
                children=[
                    dbc.Col(
                        dcc.RadioItems(
                            id="cashflow-collection-view-mode",
                            options=[
                                {"label": "Monthly", "value": "monthly"},
                                {"label": "Quarterly", "value": "quarterly"},
                            ],
                            value="monthly",
                            inline=True,
                        ),
                        className="d-flex justify-content-center align-items-center",
                    ),
                    dag.AgGrid(
                        id="cashflow-collection-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                ],
            ),
            dbc.AccordionItem(
                title="Cash Payments",
                children=[
                    dbc.Col(
                        dcc.RadioItems(
                            id="cashflow-payment-view-mode",
                            options=[
                                {"label": "Monthly", "value": "monthly"},
                                {"label": "Quarterly", "value": "quarterly"},
                            ],
                            value="monthly",
                            inline=True,
                        ),
                        className="d-flex justify-content-center align-items-center",
                    ),
                    dag.AgGrid(
                        id="cashflow-payments-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    ),
                ],
            ),
            dbc.AccordionItem(
                title="Overhead",
                children=[
                    dag.AgGrid(
                        id="overhead-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    )
                ],
            ),
            dbc.AccordionItem(
                title="Contribution Margin",
                children=[
                    dag.AgGrid(
                        id="contribution-margin-table",
                        rowData=[],
                        columnDefs=[],
                        defaultColDef={
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                        },
                        columnSize="responsiveSizeToFit",
                        style={"height": "300px", "width": "100%"},
                    )
                ],
            ),
        ]
    ),
]
