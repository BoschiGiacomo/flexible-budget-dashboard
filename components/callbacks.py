import pandas as pd
from pandas.core.arrays import period
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate

from components import tabs
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
    Input("sales-data-store", "modified_timestamp"),
    State("sales-data-store", "data"),
)
def plot_sales_data(timestamp, data):
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
    Input("params-data-store", "modified_timestamp"),
    State("params-data-store", "data"),
)
def build_product_table(timestamp, data):
    if not data:
        return [], []

    df = transforms.product_json_normalize(data["data"])
    records = df.to_dict("records")
    cols = [
        {"field": c, "headerName": name}
        for c, name in zip(df.columns, transforms.pretty_labels(list(df.columns)))
    ]

    return records, cols


# update pareto plot with overhead from parameters
@callback(
    Output("params-overhead-pareto", "figure"),
    Input("params-data-store", "modified_timestamp"),
    State("params-data-store", "data"),
)
def build_overhead_pareto(timestamp, data):
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


# Retrieve budgets from data sotre and update all the bugets
@callback(
    Output("sales-budget-table", "rowData"),
    Output("sales-budget-table", "columnDefs"),
    Output("production-budget-table", "rowData"),
    Output("production-budget-table", "columnDefs"),
    Output("materials-budget-table", "rowData"),
    Output("materials-budget-table", "columnDefs"),
    Output("labor-budget-table", "rowData"),
    Output("labor-budget-table", "columnDefs"),
    Input("budgets-data-store", "data"),
    Input("budgets-view-mode", "value"),
)
def update_budget_tables(data, view_mode):
    if data is None:
        raise PreventUpdate

    data_df = transforms.reconstruct_df(data)

    period_col = "month"

    match view_mode:
        case "quarterly":

            period_col = "quarter"

            data_df["quarter"] = (
                pd.to_datetime(data_df["month"]).dt.to_period("Q").astype(str)
            )

            inv_agg = (
                data_df.groupby(["product", "quarter"])
                .agg(
                    beginning_inv=("beginning_inv", "first"),
                    desired_end_inv=("desired_end_inv", "last"),
                )
                .reset_index()
            )

            mat_inv_agg = (
                data_df.groupby(["product", "quarter"])
                .agg(
                    beginning_materials_inventory=(
                        "beginning_materials_inventory",
                        "first",
                    ),
                    ending_material_inventory=("ending_material_inventory", "last"),
                )
                .reset_index()
            )

            data_df = data_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

            data_df["beginning_inv"] = inv_agg["beginning_inv"].values
            data_df["desired_end_inv"] = inv_agg["desired_end_inv"].values

            data_df["beginning_materials_inventory"] = mat_inv_agg[
                "beginning_materials_inventory"
            ].values
            data_df["ending_material_inventory"] = mat_inv_agg[
                "ending_material_inventory"
            ].values

        case "monthly":
            pass

    # little helper function to reduce boilerplate, decide if upgrade to global scope
    # returns the format expected by AgGrid
    def to_grid(cols):
        subset = data_df[cols].round(2).reset_index(drop=True)
        rows = subset[cols].to_dict("records")  # type: ignore
        col_defs = [
            {"field": c, "headerName": name}
            for c, name in zip(
                subset.columns, transforms.pretty_labels(list(subset.columns))
            )
        ]
        return rows, col_defs

    sales_rows, sales_cols = to_grid(["product", period_col, "sales_units", "revenue"])
    prod_rows, prod_cols = to_grid(
        [
            "product",
            period_col,
            "sales_units",
            "desired_end_inv",
            "beginning_inv",
            "total_production",
        ]
    )
    mat_rows, mat_cols = to_grid(
        [
            "product",
            period_col,
            "materials_for_production",
            "ending_material_inventory",
            "materials_needs",
            "beginning_materials_inventory",
            "materials_purchases",
            "expense_for_materials",
        ]
    )
    lab_rows, lab_cols = to_grid(
        ["product", period_col, "total_labor_time", "total_direct_labor_cost"]
    )

    return (
        sales_rows,
        sales_cols,
        prod_rows,
        prod_cols,
        mat_rows,
        mat_cols,
        lab_rows,
        lab_cols,
    )


@callback(
    Output("sales-stacked-bar-graph", "figure"),
    Input("budgets-data-store", "data"),
)
def build_sales_summary(budgets_df):
    if budgets_df is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)
    fig = px.bar(
        budgets_df,
        x="month",
        y="revenue",
        color="product",
        custom_data=["sales_units"],
        barmode="stack",
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Product: %{fullData.name}<br>"
            "Revenue: €%{y:,.2f}<br>"
            "Units: %{customdata[0]:,}<br>"
            "<extra></extra>"
        )
    )
    return fig


@callback(
    Output("inventory-movement-graph", "figure"),
    Input("budgets-data-store", "data"),
)
def build_inventory_movement(budgets_df):
    if budgets_df is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)

    inv_df = budgets_df[["product", "month", "beginning_inv", "desired_end_inv"]].copy()
    inv_df["month"] = pd.to_datetime(inv_df["month"])
    inv_df = inv_df.sort_values("month")  # type: ignore

    melted = inv_df.melt(
        id_vars=["product", "month"],
        value_vars=["beginning_inv", "desired_end_inv"],
        var_name="type",
        value_name="units",
    )

    fig = px.line(
        melted,
        x="month",
        y="units",
        color="product",
        line_dash="type",
    )

    return fig


@callback(
    Output("waterfall-quarter-dropdown", "options"),
    Output("waterfall-quarter-dropdown", "value"),
    Input("budgets-data-store", "data"),
)
def populate_quarter_dropdown(budgets_df):
    if budgets_df is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)

    budgets_df["quarter"] = (
        pd.to_datetime(budgets_df["month"]).dt.to_period("Q").astype(str)
    )
    quarters = sorted(budgets_df["quarter"].unique())
    options = [{"label": q, "value": q} for q in quarters]

    return options, [quarters[0]]


@callback(
    Output("waterfall-product-dropdown", "options"),
    Output("waterfall-product-dropdown", "value"),
    Input("budgets-data-store", "data"),
    State("params-data-store", "data"),
)
def populate_product_dropdown(budgets_df, params):
    if budgets_df is None or params is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)
    products = sorted(budgets_df["product"].unique())
    options = [
        {"label": params["data"]["products"][code]["name"], "value": code}
        for code in products
    ]

    return options, products[0]


@callback(
    Output("inventory-waterfall-chart", "figure"),
    Input("waterfall-quarter-dropdown", "value"),
    Input("waterfall-product-dropdown", "value"),
    Input("waterfall-mode", "value"),
    Input("budgets-data-store", "data"),
)
def build_inventory_waterfall(quarters, product, mode, budgets_df):
    if quarters is None or product is None or budgets_df is None:
        raise PreventUpdate

    if isinstance(quarters, str):
        quarters = [quarters]

    budgets_df = transforms.reconstruct_df(budgets_df)
    budgets_df["quarter"] = (
        pd.to_datetime(budgets_df["month"]).dt.to_period("Q").astype("str")
    )

    # month_dt is a dummy column to allow sorting by datetime to fix misaligned sorting bug
    filtered = (
        budgets_df[
            (budgets_df["quarter"].isin(quarters)) & (budgets_df["product"] == product)
        ]
        .assign(month_dt=lambda df: pd.to_datetime(df["month"]))
        .sort_values("month_dt")
        .reset_index(drop=True)
    )

    if filtered.empty:
        raise PreventUpdate

    x_outer, x_inner, measures, values = [], [], [], []

    match mode:
        case "buildup":
            x_outer.append(filtered["month"].iloc[0])
            x_inner.append("Start Inv")
            measures.append("absolute")
            values.append(filtered["beginning_inv"].iloc[0])

            for _, row in filtered.iterrows():
                month = row["month"]
                x_outer += [month, month, month]
                x_inner += ["Prod", "Sales", "End Inv"]
                measures += ["relative", "relative", "total"]
                values += [row["total_production"], -row["sales_units"], 0]

        case "delta":
            x_outer.append(filtered["quarter"].iloc[0])
            x_inner.append("Start Inv")
            measures.append("absolute")
            values.append(filtered["beginning_inv"].iloc[0])

            for _, row in filtered.iterrows():
                x_outer.append(row["quarter"])
                x_inner.append(row["month"])
                measures.append("relative")
                values.append(row["total_production"] - row["sales_units"])

            x_outer.append(filtered["quarter"].iloc[-1])
            x_inner.append("End Inv")
            measures.append("total")
            values.append(0)

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=[x_outer, x_inner],
            y=values,
        )
    )

    return fig


@callback(
    Output("materials-expenses-stacked", "figure"),
    Input("budgets-data-store", "data"),
)
def build_materials_expense_bar(budgets_df):
    if budgets_df is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)
    budgets_df.dropna(subset=["expense_for_materials"], inplace=True)
    # Nans are dropped ATM, which means the last 2 months gets always dropped
    # this might change if a NaN handling policy is introduced in the budgets calculation

    fig = px.bar(
        budgets_df,
        x="month",
        y="expense_for_materials",
        custom_data=["materials_purchases"],
        color="product",
        barmode="stack",
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Product: %{fullData.name}<br>"
            "Expenses: €%{y:,.2f}<br>"
            "Purchases: %{customdata[0]:,}<br>"
            "<extra></extra>"
        )
    )

    return fig


@callback(
    Output("labor-expenses-stacked", "figure"),
    Input("budgets-data-store", "data"),
)
def build_labor_expense_bar(budgets_df):
    if budgets_df is None:
        raise PreventUpdate

    budgets_df = transforms.reconstruct_df(budgets_df)
    budgets_df.dropna(subset=["total_direct_labor_cost"], inplace=True)

    fig = px.bar(
        budgets_df,
        x="month",
        y="total_direct_labor_cost",
        color="product",
        custom_data=["total_labor_time"],
        barmode="stack",
    )
    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Product: %{fullData.name}<br>"
            "Costs: €%{y:,.2f}<br>"
            "Time: %{customdata[0]:,}<br>"
            "<extra></extra>"
        )
    )

    return fig


# lazy tab loader for performacne
@callback(
    Output("tab-content", "children"),
    Input("tabs", "active_tab"),
)
def render_tab(active_tab):
    match active_tab:
        case "tab-upload":
            return tabs.upload_layout
        case "tab-budgets":
            return tabs.budgets_layout
        case "tab-financial":
            return tabs.financial_layout
        case _:
            return html.Div("404")
