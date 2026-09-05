"""
Monte Carlo Portfolio Simulator — Streamlit App
"""

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


# ── Simulation core ──────────────────────────────────────────────────────────

def monte_carlo_portfolio_yearly(
    initial_investment,
    allocations,
    avg_returns,
    volatilities,
    years=10,
    annual_expenses=102000,
    inflation_rate=0.025,
    income_streams=None,
    liquid_assets=250000,
    num_simulations=10000,
    seed=42,
):
    np.random.seed(seed)

    if income_streams is None:
        income_streams = []

    asset_classes = list(allocations.keys())
    proportions = np.array([allocations[ac] for ac in asset_classes])
    avg_returns_arr = np.array([avg_returns[ac] for ac in asset_classes])
    vol_arr = np.array([volatilities[ac] for ac in asset_classes])

    liquid_asset_years = (
        liquid_assets / annual_expenses
        if annual_expenses > 0
        else 0
    )

    initial_amounts = initial_investment * proportions

    portfolio_values = np.zeros((num_simulations, years + 1))

    for sim in range(num_simulations):
        portfolio = initial_amounts.copy()
        liquid_remaining = liquid_assets
        liq_yrs = liquid_asset_years

        portfolio_values[sim, 0] = (
            portfolio.sum() + liquid_remaining
        )

        for year in range(1, years + 1):

            returns = np.random.normal(
                avg_returns_arr,
                vol_arr
            )

            portfolio = portfolio * (1 + returns)

            exp_year = annual_expenses * (
                (1 + inflation_rate) ** (year - 1)
            )

            income = 0.0

            for income_stream in income_streams:

                if year - 1 >= income_stream["start_year"]:

                    end_ok = (
                        income_stream["end_year"] is None
                        or year - 1 <= income_stream["end_year"]
                    )

                    if end_ok:

                        if income_stream["inflation_adjusted"]:
                            years_since = (
                                year
                                - 1
                                - income_stream["start_year"]
                            )

                            income += (
                                income_stream["amount"]
                                * ((1 + inflation_rate) ** years_since)
                            )
                        else:
                            income += income_stream["amount"]

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
                portfolio = np.maximum(portfolio, 0)

            total_p = portfolio.sum()

            if total_p > 0:
                portfolio = total_p * proportions
            else:
                portfolio = portfolio * 0

            portfolio_values[sim, year] = (
                portfolio.sum() + liquid_remaining
            )

    df = pd.DataFrame(
        portfolio_values,
        columns=list(range(years + 1))
    )

    summary = pd.DataFrame({
        "Mean": df.mean(),
        "Median": df.median(),
        "5th Percentile": df.quantile(0.05),
        "95th Percentile": df.quantile(0.95),
    })

    return df, summary


# ── Chart ─────────────────────────────────────────────────────────────────────

def build_chart(summary):

    fig, ax = plt.subplots(figsize=(11, 5))

    idx = summary.index

    ax.fill_between(
        idx,
        summary["5th Percentile"] / 1e6,
        summary["95th Percentile"] / 1e6,
        alpha=0.18,
        label="5th–95th Band",
    )

    ax.plot(
        idx,
        summary["95th Percentile"] / 1e6,
        lw=1.5,
        ls="--",
        label="95th Pct",
    )

    ax.plot(
        idx,
        summary["Mean"] / 1e6,
        lw=2.2,
        label="Mean",
    )

    ax.plot(
        idx,
        summary["Median"] / 1e6,
        lw=2.2,
        label="Median",
    )

    ax.plot(
        idx,
        summary["5th Percentile"] / 1e6,
        lw=1.5,
        ls="--",
        label="5th Pct",
    )

    ax.set_title(
        "Portfolio Value Over Time",
        fontsize=14,
        pad=14,
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Value (Millions $)")

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(lambda value, _: f"${value:.1f}M")
    )

    ax.grid(True, alpha=0.25)

    ax.legend()

    fig.tight_layout()

    return fig


# ── Streamlit page ───────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Monte Carlo Portfolio Simulator",
    page_icon="📈",
    layout="wide",
)

st.title("Monte Carlo Portfolio Simulator")

st.write(
    "Explore potential long-term portfolio outcomes using "
    "Monte Carlo simulation."
)


# ── Sidebar inputs ───────────────────────────────────────────────────────────

st.sidebar.header("Simulation Settings")

years = st.sidebar.number_input(
    "Simulation Years",
    min_value=1,
    max_value=100,
    value=30,
)

num_simulations = st.sidebar.number_input(
    "Number of Simulations",
    min_value=100,
    max_value=100000,
    value=10000,
    step=1000,
)

seed = st.sidebar.number_input(
    "Random Seed",
    min_value=0,
    value=42,
)

st.sidebar.header("Financial Assumptions")

liquid_assets = st.sidebar.number_input(
    "Liquid Assets ($)",
    min_value=0.0,
    value=250000.0,
    step=10000.0,
)

annual_expenses = st.sidebar.number_input(
    "Annual Expenses ($)",
    min_value=0.0,
    value=102000.0,
    step=5000.0,
)

inflation_percent = st.sidebar.number_input(
    "Inflation Rate (%)",
    min_value=0.0,
    max_value=20.0,
    value=2.5,
    step=0.1,
)


# ── Asset classes ────────────────────────────────────────────────────────────

st.header("Portfolio")

st.write(
    "Enter the dollar amount allocated to each asset class. "
    "Allocations will automatically be converted to percentages."
)

default_assets = [
    {
        "name": "US Stocks",
        "amount": 500000.0,
        "return": 8.0,
        "volatility": 18.0,
    },
    {
        "name": "International Stocks",
        "amount": 200000.0,
        "return": 7.0,
        "volatility": 20.0,
    },
    {
        "name": "Bonds",
        "amount": 300000.0,
        "return": 4.0,
        "volatility": 7.0,
    },
]

asset_count = st.number_input(
    "Number of Asset Classes",
    min_value=1,
    max_value=10,
    value=3,
)

assets = []

for i in range(int(asset_count)):

    defaults = (
        default_assets[i]
        if i < len(default_assets)
        else {
            "name": f"Asset Class {i + 1}",
            "amount": 0.0,
            "return": 6.0,
            "volatility": 15.0,
        }
    )

    cols = st.columns([2, 2, 2, 2])

    with cols[0]:
        name = st.text_input(
            f"Asset Class {i + 1}",
            value=defaults["name"],
            key=f"asset_name_{i}",
        )

    with cols[1]:
        amount = st.number_input(
            "Amount ($)",
            min_value=0.0,
            value=defaults["amount"],
            step=10000.0,
            key=f"asset_amount_{i}",
        )

    with cols[2]:
        avg_return = st.number_input(
            "Avg Return (%)",
            min_value=-100.0,
            max_value=100.0,
            value=defaults["return"],
            step=0.5,
            key=f"asset_return_{i}",
        )

    with cols[3]:
        volatility = st.number_input(
            "Volatility (%)",
            min_value=0.0,
            max_value=100.0,
            value=defaults["volatility"],
            step=0.5,
            key=f"asset_volatility_{i}",
        )

    assets.append({
        "name": name.strip(),
        "amount": amount,
        "avg_return": avg_return,
        "volatility": volatility,
    })


# ── Income streams ───────────────────────────────────────────────────────────

st.header("Income Streams")

income_count = st.number_input(
    "Number of Income Streams",
    min_value=0,
    max_value=10,
    value=0,
)

income_streams = []

for i in range(int(income_count)):

    cols = st.columns([2, 2, 1.5, 1.5, 2])

    with cols[0]:
        name = st.text_input(
            f"Income {i + 1} Name",
            value=f"Income {i + 1}",
            key=f"income_name_{i}",
        )

    with cols[1]:
        amount = st.number_input(
            "Annual Amount ($)",
            min_value=0.0,
            value=30000.0,
            step=1000.0,
            key=f"income_amount_{i}",
        )

    with cols[2]:
        start_year = st.number_input(
            "Start Year",
            min_value=0,
            max_value=100,
            value=0,
            key=f"income_start_{i}",
        )

    with cols[3]:
        end_year = st.number_input(
            "End Year",
            min_value=0,
            max_value=100,
            value=100,
            key=f"income_end_{i}",
        )

    with cols[4]:
        inflation_adjusted = st.checkbox(
            "Inflation Adjusted",
            value=True,
            key=f"income_inflation_{i}",
        )

    income_streams.append({
        "name": name,
        "amount": amount,
        "start_year": int(start_year),
        "end_year": (
            None if end_year >= years else int(end_year)
        ),
        "inflation_adjusted": inflation_adjusted,
    })


# ── Run simulation ───────────────────────────────────────────────────────────

st.divider()

run_simulation = st.button(
    "Run Monte Carlo Simulation",
    type="primary",
    use_container_width=True,
)


if run_simulation:

    # Validate asset classes
    valid_assets = [
        asset for asset in assets
        if asset["name"]
    ]

    if not valid_assets:
        st.error("Please enter at least one asset class.")

    else:

        raw_amounts = {}
        avg_returns = {}
        volatilities = {}

        for asset in valid_assets:

            raw_amounts[asset["name"]] = asset["amount"]

            avg_returns[asset["name"]] = (
                asset["avg_return"] / 100
            )

            volatilities[asset["name"]] = (
                asset["volatility"] / 100
            )

        total_investment = sum(raw_amounts.values())

        if total_investment <= 0:

            st.error(
                "Total portfolio allocation must be greater than zero."
            )

        else:

            allocations = {
                name: amount / total_investment
                for name, amount in raw_amounts.items()
            }

            with st.spinner(
                f"Running {num_simulations:,} simulations..."
            ):

                df, summary = monte_carlo_portfolio_yearly(
                    initial_investment=total_investment,
                    allocations=allocations,
                    avg_returns=avg_returns,
                    volatilities=volatilities,
                    years=int(years),
                    annual_expenses=annual_expenses,
                    inflation_rate=inflation_percent / 100,
                    income_streams=income_streams,
                    liquid_assets=liquid_assets,
                    num_simulations=int(num_simulations),
                    seed=int(seed),
                )

            # ── Results ───────────────────────────────────────────────────────

            st.header("Results")

            final_median = summary["Median"].iloc[-1]
            final_mean = summary["Mean"].iloc[-1]

            survival = (
                (df.iloc[:, -1] > 0).mean() * 100
            )

            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric(
                    "Final Median",
                    f"${final_median:,.0f}",
                )

            with col2:
                st.metric(
                    "Final Mean",
                    f"${final_mean:,.0f}",
                )

            with col3:
                st.metric(
                    "Portfolio Survival",
                    f"{survival:.1f}%",
                )

            # ── Chart ────────────────────────────────────────────────────────

            fig = build_chart(summary)

            st.pyplot(
                fig,
                use_container_width=True,
            )

            # ── Summary table ────────────────────────────────────────────────

            st.subheader("Simulation Summary")

            display_summary = summary.copy()

            display_summary.index.name = "Year"

            st.dataframe(
                display_summary.style.format(
                    "${:,.0f}"
                ),
                use_container_width=True,
            )

            # ── CSV download ─────────────────────────────────────────────────

            csv = summary.copy()

            csv.index.name = "Year"

            csv_data = csv.to_csv().encode("utf-8")

            st.download_button(
                "Download Results as CSV",
                data=csv_data,
                file_name="monte_carlo_summary.csv",
                mime="text/csv",
            )