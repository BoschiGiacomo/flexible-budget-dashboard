import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
    # Initialization for the sales multipliers, to decide if this is correct approach
    # i don't fully like the idea of modifying silently the original upload
    data["data"]["sales_multipliers"] = {code: 1.0 for code in data["data"]["products"]}

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

    sales_rows, sales_cols = transforms.to_grid(
        data_df, ["product", period_col, "sales_units", "revenue"]
    )
    prod_rows, prod_cols = transforms.to_grid(
        data_df,
        [
            "product",
            period_col,
            "sales_units",
            "desired_end_inv",
            "beginning_inv",
            "total_production",
        ],
    )
    mat_rows, mat_cols = transforms.to_grid(
        data_df,
        [
            "product",
            period_col,
            "materials_for_production",
            "ending_material_inventory",
            "materials_needs",
            "beginning_materials_inventory",
            "materials_purchases",
            "expense_for_materials",
        ],
    )
    lab_rows, lab_cols = transforms.to_grid(
        data_df, ["product", period_col, "total_labor_time", "total_direct_labor_cost"]
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
    Output("cashflow-collection-table", "rowData"),
    Output("cashflow-collection-table", "columnDefs"),
    Output("cashflow-payments-table", "rowData"),
    Output("cashflow-payments-table", "columnDefs"),
    Output("net-cashflow-table", "rowData"),
    Output("net-cashflow-table", "columnDefs"),
    Output("contribution-margin-table", "rowData"),
    Output("contribution-margin-table", "columnDefs"),
    Input("cashflow-data-store", "data"),
    Input("budgets-data-store", "data"),
    Input("cashflow-view-mode", "value"),
)
def update_cashflow_tables(cashflow_data, budgets_data, cashflow_view_mode):
    if cashflow_data is None or budgets_data is None:
        raise PreventUpdate

    cashflow_df = transforms.reconstruct_df(cashflow_data)
    budgets_df = transforms.reconstruct_df(budgets_data)

    collect_rows = None
    collect_cols = None
    payment_rows = None
    payment_cols = None
    net_cashflow_rows = None
    net_cashflow_cols = None
    contribution_rows = None
    contribution_cols = None

    match cashflow_view_mode:
        case "quarterly":

            cashflow_df["quarter"] = (
                pd.to_datetime(cashflow_df["month"]).dt.to_period("Q").astype("str")
            )

            cashflow_df = cashflow_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

            budgets_df["quarter"] = (
                pd.to_datetime(budgets_df["month"]).dt.to_period("Q").astype("str")
            )

            budgets_df = budgets_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

            collect_rows, collect_cols = transforms.to_grid(
                cashflow_df, ["product", "quarter", "revenue", "total_cash_collected"]
            )

            payment_rows, payment_cols = transforms.to_grid(
                cashflow_df,
                [
                    "product",
                    "quarter",
                    "total_materials_payments",
                    "total_labor_payments",
                    "total_var_cost_payments",
                ],
            )

            net_cashflow_rows, net_cashflow_cols = transforms.to_grid(
                cashflow_df,
                [
                    "product",
                    "quarter",
                    "total_cash_collected",
                    "total_var_cost_payments",
                    "overhead_payment",
                    "net_cash_flow",
                ],
            )

            contribution_rows, contribution_cols = transforms.to_grid(
                budgets_df,
                [
                    "product",
                    "quarter",
                    "revenue",
                    "expense_for_materials",
                    "total_direct_labor_cost",
                    "contribution_margin",
                ],
            )

        case "monthly":

            collect_rows, collect_cols = transforms.to_grid(
                cashflow_df,
                [
                    "product",
                    "month",
                    "revenue",
                    "collected_same_month",
                    "collected_lag1",
                    "collected_lag2",
                    "total_cash_collected",
                ],
            )

            payment_rows, payment_cols = transforms.to_grid(
                cashflow_df,
                [
                    "product",
                    "month",
                    "materials_paid_lag0",
                    "materials_paid_lag1",
                    "materials_paid_lag2",
                    "total_materials_payments",
                    "labor_paid_lag0",
                    "labor_paid_lag1",
                    "labor_paid_lag2",
                    "total_labor_payments",
                    "total_var_cost_payments",
                ],
            )

            net_cashflow_rows, net_cashflow_cols = transforms.to_grid(
                cashflow_df,
                [
                    "product",
                    "month",
                    "total_cash_collected",
                    "total_var_cost_payments",
                    "overhead_payment",
                    "net_cash_flow",
                ],
            )

            contribution_rows, contribution_cols = transforms.to_grid(
                budgets_df,
                [
                    "product",
                    "month",
                    "revenue",
                    "expense_for_materials",
                    "total_direct_labor_cost",
                    "contribution_margin",
                ],
            )

    if any(
        v is None
        for v in [
            collect_rows,
            collect_cols,
            payment_rows,
            payment_cols,
            net_cashflow_rows,
            net_cashflow_cols,
            contribution_rows,
            contribution_cols,
        ]
    ):
        raise PreventUpdate

    return (
        collect_rows,
        collect_cols,
        payment_rows,
        payment_cols,
        net_cashflow_rows,
        net_cashflow_cols,
        contribution_rows,
        contribution_cols,
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
def populate_budgets_product_dropdown(budgets_df, params):
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
    Output("cashvrevenue-product-dropdown", "options"),
    Output("cashvrevenue-product-dropdown", "value"),
    Output("zerobar-waterfall-product-dropdown", "options"),
    Output("zerobar-waterfall-product-dropdown", "value"),
    Output("varpayments-product-dropdown", "options"),
    Output("varpayments-product-dropdown", "value"),
    Output("contrib-margin-product-dropdown", "options"),
    Output("contrib-margin-product-dropdown", "value"),
    Input("cashflow-data-store", "data"),
    State("params-data-store", "data"),
)
def populate_cashflow_product_dropdown(cashflow_df, params):
    if cashflow_df is None or params is None:
        raise PreventUpdate

    cashflow_df = transforms.reconstruct_df(cashflow_df)
    products = sorted(cashflow_df["product"].unique())
    options = [
        {"label": params["data"]["products"][code]["name"], "value": code}
        for code in products
    ]

    options_with_all = options + [{"label": "All Products", "value": "all"}]

    return (
        options_with_all,
        "all",
        options_with_all,
        "all",
        options_with_all,
        "all",
        options_with_all,
        "all",
    )


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


# cash vs revenue line chart in financial tab
@callback(
    Output("cash-revenue-line-chart", "figure"),
    Input("cashflow-data-store", "data"),
    Input("cashflow-view-mode", "value"),
    Input("cashvrevenue-product-dropdown", "value"),
)
def build_cash_revenue_chart(cashflow_data, view_mode, products):
    if cashflow_data is None:
        raise PreventUpdate

    cashflow_df = transforms.reconstruct_df(cashflow_data)

    # TODO: decide if drop nans before computation, and add range slider

    time_period = "month"

    match view_mode:
        case "quarterly":
            time_period = "quarter"

            cashflow_df["quarter"] = (
                pd.to_datetime(cashflow_df["month"]).dt.to_period("Q").astype("str")
            )

            cashflow_df = cashflow_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

        case "monthly":
            pass

    fig = None

    match products:
        case "all":
            agg_df = cashflow_df.groupby(time_period).sum(numeric_only=True).reset_index()  # type: ignore

            fig = px.line(agg_df, x=time_period, y=["revenue", "total_cash_collected"])

        case _:
            fig = px.line(
                cashflow_df[cashflow_df["product"] == products],
                x=time_period,
                y=["revenue", "total_cash_collected"],
            )

    return fig


# graph in the cash payments accordion, area chart of material payments + labor payments =  total variable payments
@callback(
    Output("variable-costs-area-chart", "figure"),
    Input("cashflow-data-store", "data"),
    Input("cashflow-view-mode", "value"),
    Input("varpayments-product-dropdown", "value"),
)
def build_payments_area_chart(cashflow_data, view_mode, product):
    if cashflow_data is None:
        raise PreventUpdate

    cashflow_df = transforms.reconstruct_df(cashflow_data)

    cashflow_df = cashflow_df.dropna(
        subset=["total_materials_payments", "total_labor_payments"]
    )

    time_period = "month"

    match view_mode:
        case "quarterly":
            time_period = "quarter"

            cashflow_df["quarter"] = (
                pd.to_datetime(cashflow_df["month"]).dt.to_period("Q").astype("str")
            )

            cashflow_df = cashflow_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

        case "monthly":
            pass

    match product:
        case "all":
            plot_df = cashflow_df.groupby(time_period).sum(numeric_only=True).reset_index()  # type: ignore
        case _:
            plot_df = cashflow_df[cashflow_df["product"] == product].sort_values(time_period).reset_index(drop=True)  # type: ignore

    fig = px.area(
        plot_df,
        x=time_period,
        y=["total_materials_payments", "total_labor_payments"],
    )

    return fig


# populate the first subplot of the net cashflow area. bar chart with zero line and waterfall for per product net cashflow composition
@callback(
    Output("zerobar-waterfall-cashflow-chart", "figure"),
    Input("cashflow-data-store", "data"),
    Input("cashflow-view-mode", "value"),
    Input("zerobar-waterfall-product-dropdown", "value"),
)
def build_net_cashflow_charts(cashflow_data, view_mode, product):
    if cashflow_data is None:
        raise PreventUpdate

    cashflow_df = transforms.reconstruct_df(cashflow_data)

    cashflow_df = cashflow_df.dropna(
        subset=["total_cash_collected", "total_var_cost_payments", "net_cash_flow"]
    )

    time_period = "month"

    match view_mode:
        case "quarterly":
            time_period = "quarter"

            cashflow_df["quarter"] = (
                pd.to_datetime(cashflow_df["month"]).dt.to_period("Q").astype("str")
            )

            cashflow_df = cashflow_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

        case "monthly":
            pass

    match product:
        case "all":
            agg_df = cashflow_df.groupby(time_period).sum(numeric_only=True).reset_index()  # type: ignore

            x_outer, x_inner, measures, values = [], [], [], []

            for _, row in agg_df.iterrows():
                period = row[time_period]
                x_outer += [period, period, period, period]
                x_inner += ["+", "-Var", "-OH", "="]
                measures += ["absolute", "relative", "relative", "absolute"]
                values += [
                    row["total_cash_collected"],
                    -row["total_var_cost_payments"],
                    -row["overhead_payment"],
                    row["net_cash_flow"],
                ]

            bar_trace = go.Bar(
                x=agg_df[time_period],
                y=agg_df["net_cash_flow"],
                marker_color=[
                    "green" if v >= 0 else "red" for v in agg_df["net_cash_flow"]
                ],
            )

        case _:
            subset = cashflow_df[cashflow_df["product"] == product]

            subset = subset.sort_values(time_period).reset_index(drop=True)  # type: ignore

            x_outer, x_inner, measures, values = [], [], [], []

            for _, row in subset.iterrows():
                period = row[time_period]
                x_outer += [period, period, period, period]
                x_inner += ["+", "-Var", "-OH", "="]
                measures += ["absolute", "relative", "relative", "absolute"]
                values += [
                    row["total_cash_collected"],
                    -row["total_var_cost_payments"],
                    -row["overhead_payment"],
                    row["net_cash_flow"],
                ]

            bar_trace = go.Bar(
                x=subset[time_period],
                y=subset["net_cash_flow"],
                marker_color=[
                    "green" if v >= 0 else "red" for v in subset["net_cash_flow"]
                ],
            )

    # TODO: find a way to colour differently the cash collected and net cashflow columns
    # TODO if time remains, refactor waterfall with flat x axis (no inner/outer axis) so that
    # the shared axis works and a navigation map can be added to the plot cleanly
    waterfall_trace = go.Waterfall(
        x=[x_outer, x_inner],
        measure=measures,
        y=values,
        connector={"line": {"color": "black", "width": 1}},
    )

    fig = make_subplots(
        rows=1,
        cols=2,
        shared_xaxes=True,
        subplot_titles=("Net Cashflow Buildup", "Net Cashflow Bar"),
    )

    fig.add_trace(waterfall_trace, row=1, col=1)
    fig.add_trace(bar_trace, row=1, col=2)
    fig.add_shape(
        type="line",
        x0=0,
        x1=1,
        xref="x2 domain",
        y0=0,
        y1=0,
        yref="y2",
        line={"color": "black", "width": 1},
    )

    return fig


@callback(
    Output("contribution-margin-subplot", "figure"),
    Input("budgets-data-store", "data"),
    Input("cashflow-view-mode", "value"),
    Input("contrib-margin-product-dropdown", "value"),
)
def build_cm_subplot(budget_data, view_mode, product):
    if budget_data is None:
        raise PreventUpdate

    budget_df = transforms.reconstruct_df(budget_data)

    time_period = "month"

    budget_df = budget_df.dropna(subset=["revenue", "contribution_margin"])

    match view_mode:
        case "quarterly":
            time_period = "quarter"

            budget_df["quarter"] = (
                pd.to_datetime(budget_df["month"]).dt.to_period("Q").astype("str")
            )

            budget_df = budget_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore

        case "monthly":
            pass

    budget_df["cm_ratio"] = budget_df["contribution_margin"] / budget_df["revenue"]

    match product:
        case "all":
            products = budget_df["product"].unique()

            bar_traces = [
                go.Bar(
                    name=p,
                    x=budget_df.loc[budget_df["product"] == p, time_period],
                    y=budget_df.loc[budget_df["product"] == p, "contribution_margin"],
                )
                for p in products
            ]

            line_traces = [
                go.Scatter(
                    name=p,
                    x=budget_df.loc[budget_df["product"] == p, time_period],
                    y=budget_df.loc[budget_df["product"] == p, "cm_ratio"],
                    mode="lines+markers",
                )
                for p in products
            ]
        case _:
            bar_traces = [
                go.Bar(
                    x=budget_df.loc[budget_df["product"] == product, time_period],
                    y=budget_df.loc[
                        budget_df["product"] == product, "contribution_margin"
                    ],
                )
            ]

            line_traces = [
                go.Scatter(
                    x=budget_df.loc[budget_df["product"] == product, time_period],
                    y=budget_df.loc[budget_df["product"] == product, "cm_ratio"],
                )
            ]

    fig = make_subplots(
        rows=1, cols=2, shared_xaxes=True
    )  # TODO: sync not working, figure it out later

    for trace in bar_traces:
        fig.add_trace(trace, row=1, col=1)
    for trace in line_traces:
        fig.add_trace(trace, row=1, col=2)

    # The line plot is currently useless in showing efficiency, as scenario analysis
    # currently won't support analysis starting from a period but will change every
    # value for all periods. The graph becomes more useful when efficiency can change
    # in different periods, write in report

    fig.update_layout(barmode="stack")
    fig.update_xaxes(rangeslider_visible=True)

    return fig


@callback(
    Output("contribution-margin-waterfall", "figure"),
    Input("budgets-data-store", "data"),
    Input("cashflow-view-mode", "value"),
    Input("contrib-margin-product-dropdown", "value"),
)
def build_cm_waterfall(budget_data, view_mode, product):
    if budget_data is None:
        raise PreventUpdate

    budget_df = transforms.reconstruct_df(budget_data)

    budget_df = budget_df.dropna(
        subset=[
            "revenue",
            "expense_for_materials",
            "total_direct_labor_cost",
            "contribution_margin",
        ]
    )

    time_period = "month"

    match view_mode:
        case "quarterly":
            time_period = "quarter"
            budget_df["quarter"] = (
                pd.to_datetime(budget_df["month"]).dt.to_period("Q").astype("str")
            )
            budget_df = budget_df.groupby(["product", "quarter"]).sum(numeric_only=True).reset_index()  # type: ignore
        case "monthly":
            pass

    match product:
        case "all":
            plot_df = budget_df.groupby(time_period).sum(numeric_only=True).reset_index()  # type: ignore
        case _:
            plot_df = (
                budget_df[budget_df["product"] == product]
                .sort_values(time_period)  # type: ignore
                .reset_index(drop=True)
            )

    x_outer, x_inner, measures, values = [], [], [], []

    for _, row in plot_df.iterrows():
        period = row[time_period]
        x_outer += [period, period, period, period]
        x_inner += ["Revenue", "- Mat", "- HR", "= CM"]
        measures += ["absolute", "relative", "relative", "total"]
        values += [
            row["revenue"],
            -row["expense_for_materials"],
            -row["total_direct_labor_cost"],
            0,
        ]

    fig = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=measures,
            x=[x_outer, x_inner],
            y=values,
            connector={"line": {"color": "black", "width": 1}},
        )
    )

    return fig


@callback(
    Output("scenario-input", "children"),
    Input("tabs", "active_tab"),
    State("scenario-params-store", "data"),
)
def populate_scenario_tab(active_tab, scenario_params):
    if active_tab != "tab-scenario" or scenario_params is None:
        raise PreventUpdate

    return tabs.build_scenario_layout(scenario_params["data"])


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
        case "tab-scenario":
            return tabs.scenario_layout
        case _:
            return html.Div("404")
