# Monte Carlo Portfolio Simulator

A Streamlit-based Monte Carlo simulation tool for exploring long-term portfolio outcomes under different investment allocations, expected returns, volatility, expenses, inflation, liquid assets, and income streams.

The application runs thousands of simulated portfolio paths and summarizes the resulting range of potential portfolio values over time.

## Features

* Monte Carlo portfolio simulation
* Configurable asset classes
* Custom investment allocations
* Expected annual returns and volatility for each asset class
* Adjustable simulation period
* Configurable number of simulations
* Annual living expenses
* Inflation adjustment
* Additional income streams such as pensions or other recurring income
* Inflation-adjusted or fixed income streams
* Separate liquid assets that can fund expenses before portfolio withdrawals
* Portfolio rebalancing to target allocations after each year
* Mean, median, 5th percentile, and 95th percentile projections
* Probability of the portfolio remaining above zero at the end of the simulation
* Portfolio projection chart
* CSV export of simulation results

## How It Works

The simulator begins with the specified portfolio allocation and liquid assets.

For each simulation, annual investment returns are randomly generated using a normal distribution based on the expected return and volatility specified for each asset class.

Annual expenses are increased according to the selected inflation rate. Income streams can offset some or all of those expenses.

When expenses exceed available income, the simulator first draws from liquid assets when available. Once those assets are exhausted, the remaining shortfall is withdrawn proportionally from the investment portfolio.

After each year, the investment portfolio is rebalanced to its original target allocation.

This process is repeated for the requested number of years and across the requested number of simulations.

## Results

The application reports:

* **Mean** — Average simulated portfolio value
* **Median** — Middle simulated outcome
* **5th Percentile** — A lower-end outcome representing the value below which 5% of simulations fall
* **95th Percentile** — An upper-end outcome representing the value below which 95% of simulations fall
* **Portfolio Survival** — Percentage of simulations with a portfolio value greater than zero at the end of the simulation

The chart displays the mean, median, and 5th–95th percentile range over time.

## Technology

* Python
* Streamlit
* NumPy
* Pandas
* Matplotlib

## Running Locally

Create a virtual environment if desired:

```bash
python -m venv .venv
```

On Windows, activate it with:

```bat
.venv\Scripts\activate
```

Install the dependencies:

```bat
pip install -r requirements.txt
```

Start the application:

```bat
streamlit run app.py
```

Streamlit will provide a local URL, typically:

```text
http://localhost:8501
```

## Deployment

The application is designed to be deployed directly from its GitHub repository using Streamlit Community Cloud.

The repository requires:

```text
app.py
requirements.txt
README.md
```

## Disclaimer

This application is intended for educational and exploratory purposes. Monte Carlo simulations are mathematical models and do not predict actual investment performance. Results depend heavily on the assumptions supplied to the model, including expected returns, volatility, inflation, expenses, and income.

This tool is not financial, investment, tax, or retirement-planning advice.
