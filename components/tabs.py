import dash_bootstrap_components as dbc
import dash_ag_grid as dag
from dash import dcc, html


def build_scenario_layout(params: dict) -> list:

    static_tab: list = [html.H5("Overhead Parameters", style={"textAlign": "center"})]

    for key, value in params["overhead"].items():
        if key != "total":
            static_tab.append(
                dbc.Row(
                    [
                        dbc.Col(dbc.Label(key.replace("_", " ").title()), md=4),
                        dbc.Col(
                            dbc.Input(
                                type="number",
                                value=value,
                                min=0,
                                id={
                                    "type": "scenario-input",
                                    "param": f"overhead{key}",
                                },
                            ),
                            md=8,
                        ),
                    ]
                )
            )

    static_tab.extend(
        [
            html.Hr(),
            dbc.Row(
                [
                    dbc.Col(dbc.Label("Materials Inventory Ratio"), md=4),
                    dbc.Col(
                        dbc.Input(
                            type="number",
                            value=params["raw_materials_inventory"][
                                "ending_inventory_rate"
                            ],
                            min=0,
                            max=1,
                            id={
                                "type": "scenario-input",
                                "param": "raw_materials_inventory.ending_inventory_rate",
                            },
                        ),
                        md=8,
                    ),
                ]
            ),
        ]
    )

    tabs = [static_tab]

    return tabs


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
    dbc.Col(
        dcc.RadioItems(
            id="cashflow-view-mode",
            options=[
                {"label": "Monthly", "value": "monthly"},
                {"label": "Quarterly", "value": "quarterly"},
            ],
            value="monthly",
            inline=True,
        ),
        className="d-flex justify-content-center align-items-center",
    ),
    dbc.Accordion(
        [
            dbc.AccordionItem(
                title="Cash Collection",
                children=[
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
                    html.Hr(),
                    html.H3(
                        "Cash collection vs Revenue Chart",
                        style={"textAlign": "center"},
                    ),
                    html.Hr(),
                    dcc.Dropdown(
                        id="cashvrevenue-product-dropdown",
                        options=[],
                        value=None,
                    ),
                    html.Hr(),
                    dcc.Graph("cash-revenue-line-chart"),
                ],
            ),
            dbc.AccordionItem(
                title="Cash Payments",
                children=[
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
                    html.Hr(),
                    html.H3(
                        "Variable costs payments composition",
                        style={"textAlign": "center"},
                    ),
                    html.Hr(),
                    dcc.Dropdown(
                        id="varpayments-product-dropdown",
                        options=[],
                        value=None,
                    ),
                    html.Hr(),
                    dcc.Graph(id="variable-costs-area-chart"),
                ],
            ),
            dbc.AccordionItem(
                title="Net Cash Flow",
                children=[
                    dag.AgGrid(
                        id="net-cashflow-table",
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
                    html.H3("Net Cashflow Dynamic", style={"textAlign": "center"}),
                    dcc.Dropdown(
                        id="zerobar-waterfall-product-dropdown",
                        options=[],
                        value=None,
                    ),
                    html.Hr(),
                    dcc.Graph(id="zerobar-waterfall-cashflow-chart"),
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
                    ),
                    html.Hr(),
                    html.H3(
                        "Contribution Margin and contribution margin on revenue",
                        style={"textAlign": "center"},
                    ),
                    dcc.Dropdown(
                        id="contrib-margin-product-dropdown",
                        options=[],
                        value=None,
                    ),
                    html.Hr(),
                    dcc.Graph(id="contribution-margin-subplot"),
                    html.Hr(),
                    html.H3(
                        "Contribution Margin Composition", style={"textAlign": "center"}
                    ),
                    dcc.Graph(id="contribution-margin-waterfall"),
                ],
            ),
        ]
    ),
]

scenario_layout = [
    html.H1("Scenario Analysis", style={"textAlign": "center"}),
    html.H4(
        "Create your Scenario, then hit 'Compute'. Hit 'Reset' to reset to upload parameters",
        style={"textAlign": "center"},
    ),
    html.Hr(),
    dbc.Row(
        [
            dbc.Col(
                [
                    dcc.Button(
                        "Compute Scenario",
                        id="compute-scenario",
                        n_clicks=0,
                        className="w-100",
                    )
                ],
                md=6,
            ),
            dbc.Col(
                [
                    dcc.Button(
                        "Reset values", id="reset-values", n_clicks=0, className="w-100"
                    )
                ],
                md=6,
            ),
        ]
    ),
    html.Hr(),
    html.Div(id="scenario-input"),
]
