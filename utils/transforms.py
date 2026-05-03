import base64
import io
import os
import json
import pandas as pd


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


def pretty_labels(labels: list) -> list:
    return [label.replace("_", " ").title() for label in labels]


def to_grid(data_df: pd.DataFrame, cols: list):
    subset = data_df[cols].round(2).reset_index(drop=True)
    rows = subset[cols].to_dict("records")  # type: ignore
    col_defs = [
        {"field": c, "headerName": name}
        for c, name in zip(subset.columns, pretty_labels(list(subset.columns)))
    ]
    return rows, col_defs


# mutates input dictionary in place, based on the path of strings inserted, used in
# unpacking scenario analysis inputs
def set_nested(d: dict, path: str, value) -> None:
    keys = path.split(".")

    for key in keys[:-1]:
        d = d[int(key)] if key.isdigit() else d[key]

    last = keys[-1]
    if last.isdigit():
        d[int(last)] = value
    else:
        d[last] = value
