import dash_bootstrap_components as dbc
from dash import Dash, dcc, html

from components import callbacks, tabs

app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    suppress_callback_exceptions=True,
)
# suppress_callback_exceptions is needed because of the tabs lazy loading, otherwise
# the dash app just stops working before loading, this lets the dash components load
# even if there are errors (because they don't yet exist), at runtime everything is ok

app.layout = dbc.Container(
    [
        dcc.Store(id="params-data-store", storage_type="session"),
        dcc.Store(id="scenario-params-store", storage_type="session"),
        dcc.Store(id="sales-data-store", storage_type="session"),
        dcc.Store(id="budgets-data-store", storage_type="session"),
        dcc.Store(id="cashflow-data-store", storage_type="session"),
        dbc.Tabs(
            id="tabs",
            active_tab="tab-upload",
            children=[
                dbc.Tab(label="Upload & Preview", tab_id="tab-upload"),
                dbc.Tab(label="Budgets", tab_id="tab-budgets"),
                dbc.Tab(label="Financial", tab_id="tab-financial"),
                dbc.Tab(label="Scenario Analysis", tab_id="tab-scenario"),
            ],
        ),
        html.Div(id="tab-content"),
    ],
    fluid=True,
)

if __name__ == "__main__":
    app.run(debug=True)
