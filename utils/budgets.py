import pandas as pd
from utils import transforms


def compute_sales_budget(data_df, prices_df) -> pd.DataFrame:
    sales_df = data_df.merge(prices_df, on="product", how="left")
    sales_df["revenue"] = sales_df["sales_units"] * sales_df["selling_price"]

    return sales_df


def compute_production_budget(budget_df, inv_df, handle_missing=False) -> pd.DataFrame:
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
            production_df["sales_units"] * production_df["inventory_ratio"]
        )

        production_df["total_production"] = (
            production_df["sales_units"]
            + production_df["desired_end_inv"]
            - production_df["beginning_inv"]
        )

        # else: handle_missing=True is a planned extension. Not yet implemented

    return production_df


def compute_materials_budget(
    production_df, raw_mat_df, handle_missing=False
) -> pd.DataFrame:
    materials_df = production_df.merge(raw_mat_df, on="product", how="left")

    materials_df["materials_for_production"] = (
        materials_df["total_production"] * materials_df["material_kg_per_unit"]
    )

    if not handle_missing:
        materials_df["ending_material_inventory"] = (
            materials_df.groupby("product")["materials_for_production"].shift(-1)
            * materials_df["raw_mat_inv_rate"]
        )

    # else: handle_missing=True is yet to be implemented like in the above case

    materials_df["beginning_materials_inventory"] = (
        materials_df["materials_for_production"] * materials_df["raw_mat_inv_rate"]
    )

    materials_df["materials_needs"] = (
        materials_df["materials_for_production"]
        + materials_df["ending_material_inventory"]
    )

    materials_df["materials_purchases"] = (
        materials_df["materials_needs"] - materials_df["beginning_materials_inventory"]
    )

    materials_df["expense_for_materials"] = (
        materials_df["materials_purchases"] * materials_df["material_cost_per_kg"]
    )

    return materials_df


def compute_labor_budget(production_df, direct_labor_df) -> pd.DataFrame:
    labor_df = production_df.merge(direct_labor_df, on="product", how="left")

    labor_df["total_labor_time"] = (
        labor_df["total_production"] * labor_df["hours_per_unit"]
    )

    labor_df["total_direct_labor_cost"] = (
        labor_df["total_labor_time"] * labor_df["labor_cost_hour"]
    )

    return labor_df


def compute_cashflow(sales_df, cash_collection_df) -> pd.DataFrame:
    cashflow_df = sales_df.merge(cash_collection_df, on="product", how="left")

    cashflow_df["collected_same_month"] = (
        cashflow_df["revenue"] * cashflow_df["collection_rate_0"]
    )

    cashflow_df["collected_lag1"] = (
        cashflow_df.groupby("product")["revenue"].shift(1)
        * cashflow_df["collection_rate_1"]
    )

    cashflow_df["collected_lag2"] = (
        cashflow_df.groupby("product")["revenue"].shift(2)
        * cashflow_df["collection_rate_2"]
    )

    cashflow_df["total_cash_collected"] = (
        cashflow_df["collected_same_month"]
        + cashflow_df["collected_lag1"]
        + cashflow_df["collected_lag2"]
    )

    return cashflow_df


def compute_overhead():
    # STILL TODO
    return


def compute_budgets(sales_payload, params_payload, handle_missing=False):
    data_df = transforms.reconstruct_df(sales_payload["data"])

    params = params_payload["data"]

    price_df = pd.DataFrame(
        [
            {"product": code, "selling_price": product["selling_price"]}
            for code, product in params["products"].items()
        ]
    )

    sales_df = compute_sales_budget(data_df, price_df)

    inv_df = pd.DataFrame(
        [
            {"product": code, "inventory_ratio": product["inventory_ratio"]}
            for code, product in params["products"].items()
        ]
    )

    production_df = compute_production_budget(sales_df, inv_df, handle_missing)

    raw_mat_inv = params["raw_materials_inventory"]["ending_inventory_rate"]

    raw_mat_df = pd.DataFrame(
        [
            {
                "product": code,
                "material_cost_per_kg": product["raw_materials"]["cost_per_kg"],
                "material_kg_per_unit": product["raw_materials"]["kg_per_unit"],
            }
            for code, product in params["products"].items()
        ]
    )
    raw_mat_df["raw_mat_inv_rate"] = raw_mat_inv

    materials_df = compute_materials_budget(production_df, raw_mat_df, handle_missing)

    # For the future might be worth implementing a minutes/hours flag in case
    # a user wants to input values as hours and not minutes

    direct_labor_df = pd.DataFrame(
        [
            {
                "product": code,
                "hours_per_unit": product["direct_labor"]["minutes_per_unit"] / 60,
                "labor_cost_hour": product["direct_labor"]["cost_per_hour"],
            }
            for code, product in params["products"].items()
        ]
    )

    labor_df = compute_labor_budget(materials_df, direct_labor_df)

    cash_collection_df = pd.DataFrame(
        [
            {
                "product": code,
                "collection_rate_0": rates[0],
                "collection_rate_1": rates[1],
                "collection_rate_2": rates[2],
            }
            for code, rates in params["cash_collection_policies"].items()
        ]
    )

    cashflow_df = compute_cashflow(sales_df, cash_collection_df)

    costs_df = pd.DataFrame(
        labor_df.groupby("month")[["expense_for_materials", "total_direct_labor_cost"]]
        .sum()
        .reset_index()  # type: ignore
    )

    payment_policies = params["cash_payment_policies"]

    return labor_df, cashflow_df
