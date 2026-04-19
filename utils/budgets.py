import pandas as pd
from utils import transforms


def compute_sales_budget(data_df, prices_df) -> pd.DataFrame:
    sales_df = data_df.merge(prices_df, on="product", how="left")
    sales_df["revenue"] = (sales_df["sales_units"] * sales_df["selling_price"]).round(2)

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
        ).round(0)

        # for future proofing, it might be necessary to switch from this implementation
        # that we saw in class (current sales * inv ratio = beginning inv) to
        # shifting the column of ending invetory up to the next month in case
        # the rate is allowed to dynamically change in the future
        production_df["beginning_inv"] = (
            production_df["sales_units"] * production_df["inventory_ratio"]
        ).round(0)

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
    ).round(0)

    if not handle_missing:
        materials_df["ending_material_inventory"] = (
            materials_df.groupby("product")["materials_for_production"].shift(-1)
            * materials_df["raw_mat_inv_rate"]
        ).round(0)

    # else: handle_missing=True is yet to be implemented like in the above case

    materials_df["beginning_materials_inventory"] = (
        materials_df["materials_for_production"] * materials_df["raw_mat_inv_rate"]
    ).round(0)

    materials_df["materials_needs"] = (
        materials_df["materials_for_production"]
        + materials_df["ending_material_inventory"]
    )

    materials_df["materials_purchases"] = (
        materials_df["materials_needs"] - materials_df["beginning_materials_inventory"]
    )

    materials_df["expense_for_materials"] = (
        materials_df["materials_purchases"] * materials_df["material_cost_per_kg"]
    ).round(2)

    return materials_df


def compute_labor_budget(production_df, direct_labor_df) -> pd.DataFrame:
    labor_df = production_df.merge(direct_labor_df, on="product", how="left")

    labor_df["total_labor_time"] = (
        labor_df["total_production"] * labor_df["hours_per_unit"]
    ).round(2)

    labor_df["total_direct_labor_cost"] = (
        labor_df["total_labor_time"] * labor_df["labor_cost_hour"]
    ).round(2)

    return labor_df


def compute_cashflow(sales_df, cash_collection_df) -> pd.DataFrame:
    cashflow_df = sales_df.merge(cash_collection_df, on="product", how="left")

    cashflow_df["collected_same_month"] = (
        cashflow_df["revenue"] * cashflow_df["collection_rate_0"]
    ).round(2)

    cashflow_df["collected_lag1"] = (
        cashflow_df.groupby("product")["revenue"].shift(1)
        * cashflow_df["collection_rate_1"]
    ).round(2)

    cashflow_df["collected_lag2"] = (
        cashflow_df.groupby("product")["revenue"].shift(2)
        * cashflow_df["collection_rate_2"]
    ).round(2)

    cashflow_df["total_cash_collected"] = (
        cashflow_df["collected_same_month"]
        + cashflow_df["collected_lag1"]
        + cashflow_df["collected_lag2"]
    )

    return cashflow_df


def compute_payments(budgets_df, payment_policies, overhead_total) -> pd.DataFrame:
    payments_df = budgets_df[
        ["product", "month", "expense_for_materials", "total_direct_labor_cost"]
    ].copy()

    for idx, (mat_policy, labor_policy) in enumerate(payment_policies):

        mat_col_name = f"materials_paid_lag{idx}"
        labor_col_name = f"labor_paid_lag{idx}"

        payments_df[mat_col_name] = (
            payments_df.groupby("product")["expense_for_materials"].shift(idx)
            * mat_policy
        ).round(2)

        payments_df[labor_col_name] = (
            payments_df.groupby("product")["total_direct_labor_cost"].shift(idx)
            * labor_policy
        ).round(2)

    payments_df["total_materials_payments"] = (
        payments_df["materials_paid_lag0"]
        + payments_df["materials_paid_lag1"]
        + payments_df["materials_paid_lag2"]
    )
    payments_df["total_labor_payments"] = (
        payments_df["labor_paid_lag0"]
        + payments_df["labor_paid_lag1"]
        + payments_df["labor_paid_lag2"]
    )
    payments_df["total_var_cost_payments"] = (
        payments_df["total_materials_payments"] + payments_df["total_labor_payments"]
    )

    payments_df["overhead_payment"] = 0.0

    n_products = payments_df["product"].nunique()

    quarter_last_months = payments_df.groupby(
        pd.to_datetime(payments_df["month"]).dt.to_period("Q")
    )["month"].transform("max")

    payments_df.loc[payments_df["month"] == quarter_last_months, "overhead_payment"] = (
        overhead_total / n_products
    )

    return payments_df


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

    budgets_df = compute_labor_budget(materials_df, direct_labor_df)

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

    cash_payment_policies = zip(
        params["cash_payment_policies"]["raw_materials"],
        params["cash_payment_policies"]["labor"],
    )

    overhead_total = params["overhead"]["total"]

    payments_df = compute_payments(budgets_df, cash_payment_policies, overhead_total)

    cashflow_df = cashflow_df.merge(payments_df, on=["product", "month"], how="left")

    cashflow_df["net_cash_flow"] = (
        cashflow_df["total_cash_collected"]
        - cashflow_df["total_var_cost_payments"]
        - cashflow_df["overhead_payment"]
    )

    budgets_df["contribution_margin"] = (
        budgets_df["revenue"]
        - budgets_df["expense_for_materials"]
        - budgets_df["total_direct_labor_cost"]
    )

    return budgets_df, cashflow_df
