import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate

from utils import transforms, budgets


# Store Uploaded sales data
@callback(
    Output("sales-data-store", "data"),
    Input("sales-data-upload", "contents"),
    State("sales-data-upload", "filename"),
)
def store_sales_data(contents, filename):
    if contents is None or filename is None:
        raise PreventUpdate

    data = transforms.parse_contents(contents, filename)

    if data["ok"] is False:
        raise PreventUpdate

    data["data"] = transforms.deconstruct_df(data["data"])

    return data


# Store uploaded parameters data
@callback(
    Output("params-data-store", "data"),
    Input("params-data-upload", "contents"),
    State("params-data-upload", "filename"),
)
def store_params_data(contents, filename):
    if contents is None or filename is None:
        raise PreventUpdate

    data = transforms.parse_contents(contents, filename)

    return data


# Update sales data graph
@callback(
    Output("sales-data-graph", "figure"),
    Input("sales-data-store", "data"),
)
def plot_sales_data(data):
    if data is None or not data["ok"]:
        raise PreventUpdate

    df = transforms.reconstruct_df(data["data"])

    if data["filename"] is not None:
        title = data["filename"]
    else:
        title = "Uploaded Sales Data"

    fig = px.line(df, x="month", y="sales_units", color="product", title=title)

    return fig


# Update json parameters table visualization
@callback(
    Output("product-data-table", "rowData"),
    Output("product-data-table", "columnDefs"),
    Input("params-data-store", "data"),
)
def build_product_table(data):
    if not data:
        return [], []

    df = transforms.product_json_normalize(data["data"])
    records = df.to_dict("records")
    cols = [{"field": c} for c in df.columns]

    return records, cols


# update pareto plot with overhead from parameters
@callback(
    Output("params-overhead-pareto", "figure"),
    Input("params-data-store", "data"),
)
def build_overhead_pareto(data):
    if data is None or not data["ok"]:
        raise PreventUpdate

    overhead = (
        pd.Series(data["data"]["overhead"]).drop("total").sort_values(ascending=False)
    )
    total = overhead.sum()
    cum_amount = overhead.cumsum()
    cum_pct = cum_amount / total

    fig = px.bar(
        x=overhead.index,
        y=overhead.values,
        title="Overhead Expense Participation",
        labels={"x": "Category", "y": "Amount"},
    )

    fig.update_layout(
        yaxis=dict(title="Amount", range=[0, total], showline=True),
        yaxis2=dict(
            title="Cumulative %",
            overlaying="y",
            side="right",
            tickvals=[0, 0.25 * total, 0.5 * total, 0.75 * total, total],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            range=[0, total],
            showline=False,
            showgrid=False,
            zeroline=False,
        ),
    )

    fig.add_scatter(
        x=overhead.index,
        y=cum_amount,
        mode="lines+markers",
        name="Cumulative %",
        yaxis="y2",
        customdata=cum_pct,
        hovertemplate=(
            "<b>%{x}</b><br>" "Cumulative %: %{customdata:.1%}" "<extra></extra>"
        ),
    )

    return fig


# store budget and cashflow calculations
@callback(
    Output("budgets-data-store", "data"),
    Output("cashflow-data-store", "data"),
    Input("sales-data-store", "modified_timestamp"),
    Input("params-data-store", "modified_timestamp"),
    State("sales-data-store", "data"),
    State("params-data-store", "data"),
)
def store_budget_data(sales_ts, params_ts, sales_data, params_data):
    if sales_data is None or params_data is None:
        raise PreventUpdate

    budget_df, cashflow_df = budgets.compute_budgets(sales_data, params_data)

    return (
        transforms.deconstruct_df(budget_df),
        transforms.deconstruct_df(cashflow_df),
    )
