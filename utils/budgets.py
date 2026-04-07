import pandas as pd
from utils import transforms


def compute_sales_budget(sales_df, prices_df):
    budget_df = sales_df.merge(prices_df, on="product", how="left")
    budget_df["revenue"] = budget_df["sales_units"] * budget_df["selling_price"]

    return budget_df


def compute_production_budget(budget_df, inv_df, handle_missing=False):
    production_df = budget_df.merge(inv_df, on="product", how="left")

    if not handle_missing:
        production_df.sort_values(
            by=["product", "month"], axis=0, ascending=True, inplace=True
        )

        production_df["desired_end_inv"] = (
            production_df.groupby("product")["sales_units"].shift(-1)
            * production_df["inventory_ratio"]
        )

        # for future proofing, it might be necessary to switch from this implementation
        # that we saw in class (current sales * inv ratio = beginning inv) to
        # shifting the column of ending invetory up to the next month in case
        # the rate is allowed to dynamically change in the future
        production_df["beginning_inv"] = (
            production_df.groupby("product")["sales_units"]
            * production_df["inventory_ratio"]
        )

        production_df["total_production"] = (
            production_df["sales_units"]
            + production_df["desired_end_inv"]
            - production_df["beginning_inv"]
        )

        # else: handle_missing=True is a planned extension. Not yet implemented

    return production_df


def compute_materials_budget(production_df, raw_mat_df, handle_missing=False):
    materials_df = production_df.merge(raw_mat_df, on="product", how="left")

    materials_df["materials_for_production"] = (
        materials_df["total_production"] * materials_df["material_kg_per_unit"]
    )

    if not handle_missing:
        materials_df["ending_material_inventory"] = (
            materials_df.groupby("product")["materials_for_production"].shift(-1)
            * materials_df["raw_mat_start_inv"]
        )

    # else: handle_missing=True is yet to be implemented like in the above case

    materials_df["beginning_materials_inventory"] = (
        materials_df.groupby("product")["materials_for_production"]
        * materials_df["raw_mat_start_inv"]
    )

    materials_df["materials_needs"] = (
        materials_df["materials_for_production"]
        + materials_df["ending_material_inventory"]
    )

    materials_df["materials_purchases"] = (
        materials_df["materials_needs"] - materials_df["beginning_materials_inventory"]
    )

    return materials_df

def total_materials()


def compute_budgets(sales_payload, params_payload, handle_missing=False):
    sales_df = transforms.reconstruct_df(sales_payload["data"])

    params = params_payload["data"]

    price_df = pd.DataFrame(
        [
            {"product": code, "selling_price": product["selling_price"]}
            for code, product in params["products"].items()
        ]
    )

    budget_df = compute_sales_budget(sales_df, price_df)

    inv_df = pd.DataFrame(
        [
            {"product": code, "inventory_ratio": product["inventory_ratio"]}
            for code, product in params["products"].items()
        ]
    )

    production_df = compute_production_budget(budget_df, inv_df, handle_missing)

    raw_mat_inv = params["raw_materials_inventory"]["ending_inventory_rate"]

    raw_mat_df = pd.DataFrame(
        [
            {
                "product": code,
                "material_cost_per_kg": product["material_cost_per_kg"],
                "material_kg_per_unit": product["kg_per_unit"],
            }
            for code, product in params["product"].items()
        ]
    )
    raw_mat_df.loc[:]["raw_mat_start_inv"] = raw_mat_inv

    materials_df = compute_materials_budget(
        production_df, raw_mat_df, handle_missing=False
    )

    return
