"""
Monte Carlo Portfolio Simulator — Flask Backend
"""
import io
import os
import base64

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick

from flask import Flask, render_template, request, jsonify, send_file

app = Flask(__name__)

# ── Simulation core ────────────────────────────────────────────────────────────
def monte_carlo_portfolio_yearly(
    initial_investment, allocations, avg_returns, volatilities,
    years=10, annual_expenses=102000, inflation_rate=0.025,
    income_streams=None, liquid_assets=250000,
    num_simulations=10000, seed=42
):
    np.random.seed(seed)
    if income_streams is None:
        income_streams = []

    asset_classes    = list(allocations.keys())
    proportions      = np.array([allocations[ac] for ac in asset_classes])
    avg_returns_arr  = np.array([avg_returns[ac]  for ac in asset_classes])
    vol_arr          = np.array([volatilities[ac] for ac in asset_classes])

    liquid_asset_years = (liquid_assets / annual_expenses
                          if annual_expenses > 0 else 0)
    initial_amounts    = initial_investment * proportions
    portfolio_values   = np.zeros((num_simulations, years + 1))

    for sim in range(num_simulations):
        portfolio        = initial_amounts.copy()
        liquid_remaining = liquid_assets
        liq_yrs          = liquid_asset_years
        portfolio_values[sim, 0] = portfolio.sum() + liquid_remaining

        for year in range(1, years + 1):
            returns   = np.random.normal(avg_returns_arr, vol_arr)
            portfolio = portfolio * (1 + returns)

            exp_year = annual_expenses * ((1 + inflation_rate) ** (year - 1))
            income   = 0.0
            for s in income_streams:
                if year - 1 >= s["start_year"]:
                    end_ok = s["end_year"] is None or year - 1 <= s["end_year"]
                    if end_ok:
                        if s["inflation_adjusted"]:
                            yrs_since = year - 1 - s["start_year"]
                            income += s["amount"] * ((1 + inflation_rate) ** yrs_since)
                        else:
                            income += s["amount"]

            shortfall = max(exp_year - income, 0)

            if year - 1 < liq_yrs and liquid_remaining > 0:
                liquid_remaining -= shortfall
                if liquid_remaining < 0:
                    liquid_remaining = 0
                    liq_yrs = year - 1
            else:
                total_p = portfolio.sum()
                if total_p <= 0:
                    portfolio[:] = 0
                    portfolio_values[sim, year:] = 0
                    break
                portfolio -= shortfall * (portfolio / total_p)
                portfolio  = np.maximum(portfolio, 0)

            total_p = portfolio.sum()
            portfolio = (total_p * proportions) if total_p > 0 else portfolio * 0
            portfolio_values[sim, year] = portfolio.sum() + liquid_remaining

    df = pd.DataFrame(portfolio_values, columns=list(range(years + 1)))
    summary = pd.DataFrame({
        "Mean":            df.mean(),
        "Median":          df.median(),
        "5th Percentile":  df.quantile(0.05),
        "95th Percentile": df.quantile(0.95),
    })
    return df, summary


# ── Chart helper ───────────────────────────────────────────────────────────────
def build_chart_png(summary):
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#14141f")

    idx = summary.index
    ax.fill_between(idx,
                    summary["5th Percentile"]  / 1e6,
                    summary["95th Percentile"] / 1e6,
                    color="#7c6af7", alpha=0.18, label="5th–95th Band")
    ax.plot(idx, summary["95th Percentile"] / 1e6, color="#56cfad", lw=1.5, ls="--", label="95th Pct")
    ax.plot(idx, summary["Mean"]            / 1e6, color="#f0c060", lw=2.2, label="Mean")
    ax.plot(idx, summary["Median"]          / 1e6, color="#7c6af7", lw=2.2, label="Median")
    ax.plot(idx, summary["5th Percentile"]  / 1e6, color="#e06c75", lw=1.5, ls="--", label="5th Pct")

    ax.set_title("Portfolio Value Over Time", color="#e0e0f0", fontsize=13, pad=14)
    ax.set_xlabel("Year",                    color="#9090b0", fontsize=11)
    ax.set_ylabel("Value (Millions $)",      color="#9090b0", fontsize=11)
    ax.tick_params(colors="#9090b0")
    ax.yaxis.set_major_formatter(mtick.FuncFormatter(lambda v, _: f"${v:.1f}M"))
    for spine in ax.spines.values():
        spine.set_edgecolor("#2a2a3e")
    ax.grid(True, color="#2a2a3e", linewidth=0.8)
    leg = ax.legend(facecolor="#2a2a3e", edgecolor="#2a2a3e",
                    labelcolor="#e0e0f0", fontsize=10)
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


# ── Routes ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/simulate", methods=["POST"])
def simulate():
    data = request.get_json(force=True)

    try:
        # ── Parse asset classes ──────────────────────────────────────────────
        assets = data.get("assets", [])
        if not assets:
            return jsonify(error="No asset classes provided."), 400

        raw_amounts  = {}
        avg_returns  = {}
        volatilities = {}
        for a in assets:
            name = a["name"].strip()
            if not name:
                return jsonify(error="Asset class name cannot be empty."), 400
            raw_amounts[name]  = float(a["amount"])
            avg_returns[name]  = float(a["avg_return"]) / 100
            volatilities[name] = float(a["volatility"]) / 100

        total_inv = sum(raw_amounts.values())
        if total_inv <= 0:
            return jsonify(error="Total asset allocation must be greater than zero."), 400
        allocations = {k: v / total_inv for k, v in raw_amounts.items()}

        # ── Parse settings ───────────────────────────────────────────────────
        liquid    = float(data["liquid_assets"])
        expenses  = float(data["annual_expenses"])
        inflation = float(data["inflation_rate"]) / 100
        years     = int(data["years"])
        num_sims  = int(data["num_simulations"])
        seed      = int(data.get("seed", 42))

        # ── Parse income streams ─────────────────────────────────────────────
        income_streams = []
        for s in data.get("income_streams", []):
            income_streams.append({
                "name":               s["name"],
                "amount":             float(s["amount"]),
                "start_year":         int(s["start_year"]),
                "end_year":           int(s["end_year"]) if s.get("end_year") not in (None, "") else None,
                "inflation_adjusted": bool(s.get("inflation_adjusted", True)),
            })

    except (KeyError, ValueError, TypeError) as e:
        return jsonify(error=f"Invalid input: {e}"), 400

    # ── Run simulation ───────────────────────────────────────────────────────
    df, summary = monte_carlo_portfolio_yearly(
        initial_investment=total_inv,
        allocations=allocations,
        avg_returns=avg_returns,
        volatilities=volatilities,
        years=years,
        annual_expenses=expenses,
        inflation_rate=inflation,
        income_streams=income_streams,
        liquid_assets=liquid,
        num_simulations=num_sims,
        seed=seed,
    )

    # ── Build chart PNG → base64 ─────────────────────────────────────────────
    chart_buf = build_chart_png(summary)
    chart_b64 = base64.b64encode(chart_buf.read()).decode()

    # ── Build summary table rows ─────────────────────────────────────────────
    table_rows = []
    for yr, row in summary.iterrows():
        table_rows.append({
            "year":    yr,
            "mean":    round(row["Mean"]),
            "median":  round(row["Median"]),
            "pct5":    round(row["5th Percentile"]),
            "pct95":   round(row["95th Percentile"]),
        })

    # ── Probability of not running out ───────────────────────────────────────
    survival = float((df.iloc[:, -1] > 0).mean() * 100)

    return jsonify(
        chart_png=chart_b64,
        table=table_rows,
        survival_pct=round(survival, 1),
        final_median=round(summary["Median"].iloc[-1]),
        final_mean=round(summary["Mean"].iloc[-1]),
    )


@app.route("/export_csv", methods=["POST"])
def export_csv():
    data = request.get_json(force=True)
    rows = data.get("table", [])
    df   = pd.DataFrame(rows)
    df.columns = ["Year", "Mean ($)", "Median ($)", "5th Pct ($)", "95th Pct ($)"]
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)
    return send_file(buf, mimetype="text/csv",
                     as_attachment=True,
                     download_name="monte_carlo_summary.csv")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
