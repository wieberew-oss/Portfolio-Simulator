"""
Monte Carlo Portfolio Simulator — Streamlit App
"""

import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick


# ─────────────────────────────────────────────────────────────────────────────
# Page configuration
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Monte Carlo Portfolio Simulator",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ─────────────────────────────────────────────────────────────────────────────
# Custom styling
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }

        .hero {
            padding: 1.5rem 0 1.25rem 0;
        }

        .hero h1 {
            font-size: 2.6rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
            letter-spacing: -0.03em;
        }

        .hero p {
            font-size: 1.05rem;
            opacity: 0.70;
            margin-top: 0;
        }

        .section-title {
            font-size: 1.35rem;
            font-weight: 650;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
        }

        .metric-card {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 12px;
            padding: 1.15rem 1.25rem;
            min-height: 120px;
            background: rgba(128, 128, 128, 0.045);
        }

        .metric-label {
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            opacity: 0.65;
            margin-bottom: 0.35rem;
        }

        .metric-value {
            font-size: 1.85rem;
            font-weight: 700;
            letter-spacing: -0.02em;
        }

        .metric-description {
            font-size: 0.78rem;
            opacity: 0.55;
            margin-top: 0.25rem;
        }

        .info-box {
            border-left: 3px solid #7c6af7;
            padding: 0.75rem 1rem;
            margin: 1rem 0;
            background: rgba(124, 106, 247, 0.07);
            border-radius: 0 8px 8px 0;
        }

        .disclaimer {
            font-size: 0.75rem;
            opacity: 0.55;
            border-top: 1px solid rgba(128, 128, 128, 0.18);
            padding-top: 1rem;
            margin-top: 3rem;
        }

        div[data-testid="stMetric"] {
            border: 1px solid rgba(128, 128, 128, 0.22);
            border-radius: 12px;
            padding: 1rem;
        }

        div[data-testid="stSidebar"] {
            border-right: 1px solid rgba(128, 128, 128, 0.15);
        }

        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Simulation engine
# ─────────────────────────────────────────────────────────────────────────────

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

    proportions = np.array(
        [allocations[ac] for ac in asset_classes]
    )

    avg_returns_arr = np.array(
        [avg_returns[ac] for ac in asset_classes]
    )

    vol_arr = np.array(
        [volatilities[ac] for ac in asset_classes]
    )

    liquid_asset_years = (
        liquid_assets / annual_expenses
        if annual_expenses > 0
        else 0
    )

    initial_amounts = initial_investment * proportions

    portfolio_values = np.zeros(
        (num_simulations, years + 1)
    )

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
                                * (
                                    (1 + inflation_rate)
                                    ** years_since
                                )
                            )

                        else:
                            income += income_stream["amount"]

            shortfall = max(exp_year - income, 0)

            if (
                year - 1 < liq_yrs
                and liquid_remaining > 0
            ):

                liquid_remaining -= shortfall

                if liquid_remaining < 0:
                    liquid_remaining = 0
                    liq_yrs = year - 1

            else:

                total_p = portfolio.sum()

                if total_p <= 0:

                    portfolio[:] = 0
                    portfolio_values[
                        sim, year:
                    ] = 0

                    break

                portfolio -= (
                    shortfall
                    * (portfolio / total_p)
                )

                portfolio = np.maximum(
                    portfolio,
                    0
                )

            total_p = portfolio.sum()

            if total_p > 0:
                portfolio = total_p * proportions
            else:
                portfolio = portfolio * 0

            portfolio_values[sim, year] = (
                portfolio.sum()
                + liquid_remaining
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


# ─────────────────────────────────────────────────────────────────────────────
# Charts
# ─────────────────────────────────────────────────────────────────────────────

def build_chart(summary):

    fig, ax = plt.subplots(figsize=(12, 5.5))

    idx = summary.index

    ax.fill_between(
        idx,
        summary["5th Percentile"] / 1e6,
        summary["95th Percentile"] / 1e6,
        alpha=0.16,
        label="5th–95th Percentile",
    )

    ax.plot(
        idx,
        summary["95th Percentile"] / 1e6,
        linestyle="--",
        linewidth=1.3,
        label="95th Percentile",
    )

    ax.plot(
        idx,
        summary["Mean"] / 1e6,
        linewidth=2.4,
        label="Mean",
    )

    ax.plot(
        idx,
        summary["Median"] / 1e6,
        linewidth=2.4,
        label="Median",
    )

    ax.plot(
        idx,
        summary["5th Percentile"] / 1e6,
        linestyle="--",
        linewidth=1.3,
        label="5th Percentile",
    )

    ax.set_title(
        "Projected Portfolio Value",
        fontsize=15,
        fontweight="bold",
        pad=15,
    )

    ax.set_xlabel("Year")
    ax.set_ylabel("Portfolio Value")

    ax.yaxis.set_major_formatter(
        mtick.FuncFormatter(
            lambda value, _: f"${value:.1f}M"
        )
    )

    ax.grid(
        True,
        alpha=0.18,
        linewidth=0.8
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.legend(
        frameon=False,
        ncol=4,
        loc="upper left",
    )

    fig.tight_layout()

    return fig


def build_allocation_chart(allocations):

    fig, ax = plt.subplots(figsize=(5, 4))

    labels = list(allocations.keys())
    values = list(allocations.values())

    ax.pie(
        values,
        labels=labels,
        autopct="%1.0f%%",
        startangle=90,
        wedgeprops={"width": 0.42},
    )

    ax.set_title(
        "Portfolio Allocation",
        fontsize=13,
        fontweight="bold",
    )

    fig.tight_layout()

    return fig


# ─────────────────────────────────────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="hero">
        <h1>Monte Carlo Portfolio Simulator</h1>
        <p>
            Explore thousands of possible financial futures
            based on your portfolio, spending, income, and
            investment assumptions.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:

    st.header("Simulation")

    years = st.number_input(
        "Simulation Years",
        min_value=1,
        max_value=100,
        value=30,
        step=1,
        help="How many years into the future to simulate.",
    )

    num_simulations = st.number_input(
        "Number of Simulations",
        min_value=100,
        max_value=100000,
        value=10000,
        step=1000,
        help="More simulations produce a smoother estimate but take longer.",
    )

    seed = st.number_input(
        "Random Seed",
        min_value=0,
        value=42,
        step=1,
        help="Using the same seed makes results reproducible.",
    )

    st.divider()

    st.header("Financial Assumptions")

    liquid_assets = st.number_input(
        "Liquid Assets",
        min_value=0.0,
        value=250000.0,
        step=10000.0,
        format="%.0f",
        help="Cash or other assets used to cover expenses before portfolio withdrawals.",
    )

    annual_expenses = st.number_input(
        "Annual Expenses",
        min_value=0.0,
        value=102000.0,
        step=5000.0,
        format="%.0f",
    )

    inflation_percent = st.number_input(
        "Inflation Rate",
        min_value=0.0,
        max_value=20.0,
        value=2.5,
        step=0.1,
        format="%.1f",
    )

    st.divider()

    st.caption(
        "Monte Carlo simulations are estimates, not predictions. "
        "Results depend heavily on the assumptions entered."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-title">Portfolio</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="info-box">
        Enter the current dollar amount, expected annual return,
        and volatility for each asset class. The simulator
        automatically converts dollar amounts into target
        allocation percentages.
    </div>
    """,
    unsafe_allow_html=True,
)

asset_count = st.number_input(
    "Number of Asset Classes",
    min_value=1,
    max_value=10,
    value=3,
    step=1,
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

    with st.container(border=True):

        cols = st.columns(
            [2.4, 2, 1.6, 1.6]
        )

        with cols[0]:
            name = st.text_input(
                "Asset Class",
                value=defaults["name"],
                key=f"asset_name_{i}",
            )

        with cols[1]:
            amount = st.number_input(
                "Current Value ($)",
                min_value=0.0,
                value=defaults["amount"],
                step=10000.0,
                format="%.0f",
                key=f"asset_amount_{i}",
            )

        with cols[2]:
            avg_return = st.number_input(
                "Return (%)",
                min_value=-100.0,
                max_value=100.0,
                value=defaults["return"],
                step=0.5,
                format="%.1f",
                key=f"asset_return_{i}",
            )

        with cols[3]:
            volatility = st.number_input(
                "Volatility (%)",
                min_value=0.0,
                max_value=100.0,
                value=defaults["volatility"],
                step=0.5,
                format="%.1f",
                key=f"asset_volatility_{i}",
            )

    assets.append({
        "name": name.strip(),
        "amount": amount,
        "avg_return": avg_return,
        "volatility": volatility,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Income
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    '<div class="section-title">Income Streams</div>',
    unsafe_allow_html=True,
)

st.caption(
    "Optional income such as Social Security, pensions, rental income, "
    "or other recurring cash flow."
)

income_count = st.number_input(
    "Number of Income Streams",
    min_value=0,
    max_value=10,
    value=0,
    step=1,
)

income_streams = []

for i in range(int(income_count)):

    with st.container(border=True):

        cols = st.columns(
            [2, 1.8, 1.3, 1.3, 1.7]
        )

        with cols[0]:
            name = st.text_input(
                "Income Source",
                value=f"Income {i + 1}",
                key=f"income_name_{i}",
            )

        with cols[1]:
            amount = st.number_input(
                "Annual Amount ($)",
                min_value=0.0,
                value=30000.0,
                step=1000.0,
                format="%.0f",
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
                value=int(years),
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
            None
            if end_year >= years
            else int(end_year)
        ),
        "inflation_adjusted": inflation_adjusted,
    })


# ─────────────────────────────────────────────────────────────────────────────
# Simulation button
# ─────────────────────────────────────────────────────────────────────────────

st.divider()

run_simulation = st.button(
    "▶  Run Monte Carlo Simulation",
    type="primary",
    use_container_width=True,
)


# ─────────────────────────────────────────────────────────────────────────────
# Run simulation
# ─────────────────────────────────────────────────────────────────────────────

if run_simulation:

    valid_assets = [
        asset
        for asset in assets
        if asset["name"]
    ]

    if not valid_assets:

        st.error(
            "Please enter at least one asset class."
        )

    else:

        raw_amounts = {}
        avg_returns = {}
        volatilities = {}

        duplicate_names = []

        for asset in valid_assets:

            if asset["name"] in raw_amounts:
                duplicate_names.append(
                    asset["name"]
                )

            raw_amounts[
                asset["name"]
            ] = asset["amount"]

            avg_returns[
                asset["name"]
            ] = asset["avg_return"] / 100

            volatilities[
                asset["name"]
            ] = asset["volatility"] / 100

        if duplicate_names:

            st.error(
                "Each asset class must have a unique name."
            )

            st.stop()

        total_investment = sum(
            raw_amounts.values()
        )

        if total_investment <= 0:

            st.error(
                "Total portfolio value must be greater than zero."
            )

        else:

            allocations = {
                name: amount / total_investment
                for name, amount
                in raw_amounts.items()
            }

            with st.spinner(
                f"Running {int(num_simulations):,} simulations..."
            ):

                df, summary = (
                    monte_carlo_portfolio_yearly(
                        initial_investment=total_investment,
                        allocations=allocations,
                        avg_returns=avg_returns,
                        volatilities=volatilities,
                        years=int(years),
                        annual_expenses=annual_expenses,
                        inflation_rate=(
                            inflation_percent / 100
                        ),
                        income_streams=income_streams,
                        liquid_assets=liquid_assets,
                        num_simulations=int(
                            num_simulations
                        ),
                        seed=int(seed),
                    )
                )

            # ─────────────────────────────────────────────────────────────────
            # Results
            # ─────────────────────────────────────────────────────────────────

            st.markdown(
                '<div class="section-title">Simulation Results</div>',
                unsafe_allow_html=True,
            )

            final_median = summary[
                "Median"
            ].iloc[-1]

            final_mean = summary[
                "Mean"
            ].iloc[-1]

            final_5th = summary[
                "5th Percentile"
            ].iloc[-1]

            final_95th = summary[
                "95th Percentile"
            ].iloc[-1]

            survival = (
                (df.iloc[:, -1] > 0).mean()
                * 100
            )

            # Result cards
            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            Final Median
                        </div>
                        <div class="metric-value">
                            ${final_median:,.0f}
                        </div>
                        <div class="metric-description">
                            Middle simulation outcome
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c2:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            Final Mean
                        </div>
                        <div class="metric-value">
                            ${final_mean:,.0f}
                        </div>
                        <div class="metric-description">
                            Average simulation outcome
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c3:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            5th Percentile
                        </div>
                        <div class="metric-value">
                            ${final_5th:,.0f}
                        </div>
                        <div class="metric-description">
                            Lower-end outcome
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with c4:
                st.markdown(
                    f"""
                    <div class="metric-card">
                        <div class="metric-label">
                            Survival Probability
                        </div>
                        <div class="metric-value">
                            {survival:.1f}%
                        </div>
                        <div class="metric-description">
                            Simulations ending above $0
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.write("")

            # ─────────────────────────────────────────────────────────────────
            # Chart + allocation
            # ─────────────────────────────────────────────────────────────────

            chart_col, allocation_col = st.columns(
                [2.5, 1]
            )

            with chart_col:

                st.subheader(
                    "Projected Portfolio Value"
                )

                fig = build_chart(summary)

                st.pyplot(
                    fig,
                    use_container_width=True,
                )

                plt.close(fig)

            with allocation_col:

                st.subheader(
                    "Starting Allocation"
                )

                allocation_fig = (
                    build_allocation_chart(
                        allocations
                    )
                )

                st.pyplot(
                    allocation_fig,
                    use_container_width=True,
                )

                plt.close(allocation_fig)

                allocation_table = pd.DataFrame({
                    "Asset": list(
                        allocations.keys()
                    ),
                    "Allocation": [
                        f"{value * 100:.1f}%"
                        for value in allocations.values()
                    ],
                })

                st.dataframe(
                    allocation_table,
                    hide_index=True,
                    use_container_width=True,
                )

            # ─────────────────────────────────────────────────────────────────
            # Summary table
            # ─────────────────────────────────────────────────────────────────

            st.subheader(
                "Year-by-Year Summary"
            )

            display_summary = summary.copy()

            display_summary.index.name = "Year"

            st.dataframe(
                display_summary.style.format(
                    "${:,.0f}"
                ),
                use_container_width=True,
            )

            # ─────────────────────────────────────────────────────────────────
            # Download
            # ─────────────────────────────────────────────────────────────────

            csv_data = (
                summary
                .rename_axis("Year")
                .to_csv()
                .encode("utf-8")
            )

            st.download_button(
                "Download Results as CSV",
                data=csv_data,
                file_name=(
                    "monte_carlo_summary.csv"
                ),
                mime="text/csv",
            )


# ─────────────────────────────────────────────────────────────────────────────
# Footer
# ─────────────────────────────────────────────────────────────────────────────

st.markdown(
    """
    <div class="disclaimer">
        <strong>Disclaimer:</strong>
        This application is intended for educational and exploratory
        purposes only. Monte Carlo simulations are mathematical models,
        not predictions of actual investment performance. Results depend
        heavily on the assumptions supplied, including expected returns,
        volatility, inflation, expenses, and income. This tool is not
        financial, investment, tax, or retirement-planning advice.
    </div>
    """,
    unsafe_allow_html=True,
)

