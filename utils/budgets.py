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

    return production_df


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
