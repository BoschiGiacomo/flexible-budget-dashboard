import base64
import io
import os
import json
import numpy as np
import pandas as pd
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
