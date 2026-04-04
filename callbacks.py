import base64
import io
import os
import json
import numpy as np
import pandas as pd
import plotly.express as px
from dash import Input, Output, State, callback
from dash.exceptions import PreventUpdate


def deconstruct_df(df: pd.DataFrame) -> dict:
    deconstructed_df = {
        "columns": list(df.columns),
        "records": df.to_dict(orient="records"),
    }

    return deconstructed_df


def reconstruct_df(payload: dict) -> pd.DataFrame:
    records = payload["records"]
    columns = payload.get("columns")
    df = pd.DataFrame.from_records(records)

    if columns is not None:
        df = df.loc[:, columns]

    return df


def product_json_normalize(params: dict) -> pd.DataFrame:
    products = params["products"]

    rows = []

    for code, product in products.items():
        rows.append(
            {
                "product_code": code,
                "name": product["name"],
                "selling_price": product["selling_price"],
                "inventory_ratio": product["inventory_ratio"],
                "labour_hourly_cost": product["direct_labor"]["cost_per_hour"],
                "minutes_per_unit": product["direct_labor"]["minutes_per_unit"],
                "material_cost_per_kg": product["raw_materials"]["cost_per_kg"],
                "kg_per_unit": product["raw_materials"]["kg_per_unit"],
                "labour_hours_per_unit": product["lp_coefficients"][
                    "labor_hours_per_unit"
                ],
                "material_units_per_unit": product["lp_coefficients"][
                    "material_units_per_unit"
                ],
                "profit_margin_per_unit": product["lp_coefficients"][
                    "profit_margin_per_unit"
                ],
            }
        )

    return pd.DataFrame(rows)


def parse_contents(contents, filename):
    _, content_string = contents.split(",")
    _, ext = os.path.splitext(filename.lower())

    decoded_contents = base64.b64decode(content_string)

    data = None
    detected_type = None
    ok = False
    err = None

    try:
        if ext == ".csv":
            data = pd.read_csv(io.StringIO(decoded_contents.decode("utf-8")))
            detected_type = "table"
        elif ext in {".xls", ".xlsx"}:
            data = pd.read_excel(io.BytesIO(decoded_contents))
            detected_type = "table"
        elif ext == ".json":
            data = json.loads(decoded_contents.decode("utf-8"))
            detected_type = "json"

        ok = True
        err = None

    except Exception as e:
        ok = False
        data = None
        detected_type = None
        err = str(e)

    data_out = {
        "ok": ok,
        "data": data,
        "detected_type": detected_type,
        "err": err,
        "filename": filename,
    }

    return data_out


# Store Uploaded sales data
@callback(
    Output("sales-data-store", "data"),
    Input("sales-data-upload", "contents"),
    State("sales-data-upload", "filename"),
)
def store_sales_data(contents, filename):
    if contents is None or filename is None:
        raise PreventUpdate

    data = parse_contents(contents, filename)

    if data["ok"] is False:
        raise PreventUpdate

    data["data"] = deconstruct_df(data["data"])

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

    data = parse_contents(contents, filename)

    return data


# Update sales data graph
@callback(
    Output("sales-data-graph", "figure"),
    Input("sales-data-store", "data"),
)
def plot_sales_data(data):
    if data is None or not data["ok"]:
        raise PreventUpdate

    df = reconstruct_df(data["data"])

    if data["filename"] is not None:
        title = data["filename"]
    else:
        title = "Uploaded Sales Data"

    fig = px.line(df, x="month", y="sales_units", color="product", title=title)

    return fig


@callback(
    Output("product-data-table", "rowData"),
    Output("product-data-table", "columnDefs"),
    Input("params-data-store", "data"),
)
def construct_product_table(data):
    if not data:
        return [], []

    df = product_json_normalize(data["data"])
    records = df.to_dict("records")
    cols = [{"field": c} for c in df.columns]

    return records, cols
