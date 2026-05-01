import pulp


def extract_constraints(params: dict) -> tuple:
    products = {
        code: product["lp_coefficients"] for code, product in params["products"].items()
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

    # TODO: add support for min units produced into the solver, and add the number
    # of minimum units in the params.json under the products[product]["lp_coefficients"]

    prob.solve(pulp.PULP_CBC_CMD(msg=0))  # type: ignore

    return {
        "status": pulp.LpStatus[prob.status],
        "quantities": {code: pulp.value(lp_vars[code]) for code in products},
        "objective": pulp.value(prob.objective),
        "shadow_prices": {
            name: prob.constraints[name].pi
            for name in ["labor", "materials", "warehouse"]
        },
    }
