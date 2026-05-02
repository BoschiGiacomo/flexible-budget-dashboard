import pulp


def extract_constraints(params: dict) -> tuple:
    products = {}
    for code, product in params["products"].items():
        lp = product["lp_coefficients"]
        labor_cost = (product["direct_labor"]["minutes_per_unit"] / 60) * product["direct_labor"]["cost_per_hour"]
        material_cost = product["raw_materials"]["kg_per_unit"] * product["raw_materials"]["cost_per_kg"]
        products[code] = {
            "labor_hours_per_unit": lp["labor_hours_per_unit"],
            "material_units_per_unit": lp["material_units_per_unit"],
            "min_units": lp.get("min_units", 0),
            "profit_margin_per_unit": product["selling_price"] - labor_cost - material_cost,
        }

    constraints = params["lp_constraints"]

    return products, constraints


def solve(products: dict, constraints: dict) -> dict:
    prob = pulp.LpProblem("product_mix", pulp.LpMaximize)

    # decision variables
    lp_vars = {code: pulp.LpVariable(code, lowBound=0) for code in products}

    # obj function
    prob += pulp.lpSum(
        products[code]["profit_margin_per_unit"] * lp_vars[code] for code in products
    )

    # constraints
    prob += (
        pulp.lpSum(
            products[code]["labor_hours_per_unit"] * lp_vars[code] for code in products
        )
        <= constraints["labor_hours_available"],
        "labor",
    )
    prob += (
        pulp.lpSum(
            products[code]["material_units_per_unit"] * lp_vars[code]
            for code in products
        )
        <= constraints["material_units_available"],
        "materials",
    )
    prob += (
        pulp.lpSum(lp_vars[code] for code in products)
        <= constraints["warehouse_capacity_units"],
        "warehouse",
    )

    for code in products:
        min_units = products[code].get("min_units", 0)
        if min_units > 0:
            prob += (lp_vars[code] >= min_units, f"min_{code}")

    prob.solve(pulp.PULP_CBC_CMD(msg=0))  # type: ignore

    shadow_prices = {
        name: prob.constraints[name].pi
        for name in ["labor", "materials", "warehouse"]
    }
    shadow_prices.update({
        f"min_{code}": prob.constraints[f"min_{code}"].pi
        for code in products
        if f"min_{code}" in prob.constraints
    })

    return {
        "status": pulp.LpStatus[prob.status],
        "quantities": {code: pulp.value(lp_vars[code]) for code in products},
        "objective": pulp.value(prob.objective),
        "shadow_prices": shadow_prices,
    }
