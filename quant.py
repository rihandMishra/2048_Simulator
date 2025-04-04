import pandas as pd
import numpy as np
import yfinance as yf
import matplotlib.pyplot as plt
from fpdf import FPDF

# Top 50 US large-cap diversified stocks
tickers = [
    'AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'JNJ', 'WMT', 'PG', 'JPM', 'XOM',
    'META', 'NVDA', 'HD', 'DIS', 'BAC', 'PFE', 'V', 'MA', 'KO', 'PEP',
    'MRK', 'CVX', 'UNH', 'ABBV', 'COST', 'MCD', 'NKE', 'CRM', 'ORCL', 'INTC',
    'IBM', 'QCOM', 'AVGO', 'TXN', 'LOW', 'MDT', 'LIN', 'HON', 'GE', 'RTX',
    'CAT', 'DE', 'AMGN', 'COP', 'CMCSA', 'UPS', 'SCHW', 'AXP', 'GS', 'BLK'
]
benchmark_ticker = '^GSPC'

# Download adjusted price data (monthly)
data = yf.download(tickers + [benchmark_ticker], start="2022-01-01", end="2024-12-31", interval='1mo', auto_adjust=False)

prices_monthly = data['Adj Close']


benchmark_prices = prices_monthly[benchmark_ticker]
prices_monthly = prices_monthly.drop(columns=benchmark_ticker)

# Monthly resample
prices = prices_monthly.resample('ME').last()
benchmark_monthly = benchmark_prices.resample('ME').last()
monthly_returns = prices.pct_change()
momentum_raw = (1 + monthly_returns).rolling(4).apply(np.prod, raw=True) - 1
volatility = monthly_returns.rolling(4).std()
benchmark_returns = benchmark_monthly.pct_change()
score_history = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)

# Fetch ROE and earnings growth
def get_fundamentals(tickers):
    roe_dict, growth_dict = {}, {}
    for t in tickers:
        try:
            info = yf.Ticker(t).info
            roe_dict[t] = info.get('returnOnEquity', 0)
            growth_dict[t] = info.get('earningsQuarterlyGrowth', 0)
        except:
            roe_dict[t], growth_dict[t] = 0, 0
    return pd.Series(roe_dict), pd.Series(growth_dict)

roe_series, growth_series = get_fundamentals(tickers)

# Portfolio parameters
initial_capital = 10000
cost_rate = 0.001
portfolio_value = initial_capital
prev_weights = pd.Series(0, index=prices.columns)
portfolio_history = []
daily_values = []

# Rebalance loop
for i in range(4, len(prices.index) - 1):
    date = prices.index[i]
    print(f"🔁 Rebalancing on {date.date()}")

    mom_scores = momentum_raw.loc[date].dropna()
    vol_scores = volatility.loc[date].dropna()
    common = mom_scores.index.intersection(vol_scores.index)

    fundamentals_mask = (roe_series[common] > 0.10) & (growth_series[common] > 0)
    filtered = common[fundamentals_mask]
    if len(filtered) < 10:
        daily_values.append(portfolio_value)
        continue
    #normalising the momentum and volatility
    norm_mom = (mom_scores[filtered] - mom_scores[filtered].mean()) / mom_scores[filtered].std()
    risk_adj = mom_scores[filtered] / vol_scores[filtered]
    norm_risk_adj = (risk_adj - risk_adj.mean()) / risk_adj.std()
    #adding decay factor
    decay_factor = momentum_raw.loc[prices.index[i - 1]][filtered]
    decay_penalty = 1 - decay_factor.rank(pct=True)
    #writing the blended and smoothned scores
    blended_scores = 0.6 * norm_mom + 0.3 * norm_risk_adj + 0.1 * decay_penalty
    blended_scores[mom_scores[filtered] < 0] = 0
    score_history.loc[date, blended_scores.index] = blended_scores
    smoothed_scores = score_history.iloc[i - 2:i + 1].mean().dropna()
    #taking the top 10
    top10 = smoothed_scores.nlargest(15)


    final_top10 = top10.nlargest(10)
    
    # figuring out the weights
    raw_weights = final_top10 / final_top10.sum()
    weights_full = pd.Series(0, index=prices.columns)
    weights_full[raw_weights.index] = raw_weights
    # calculating the return,turnover and other metrics
    next_date = prices.index[i + 1]
    ret_next = monthly_returns.loc[next_date]
    port_ret = (weights_full * ret_next).sum()
    turnover = (weights_full - prev_weights).abs().sum() / 2
    net_ret = port_ret - cost_rate * turnover
    # Constraints
    target_vol = 0.15
    #applying the volatility targeting method
    returns_window = pd.Series(daily_values[-3:] + [portfolio_value * (1 + net_ret)])
    realized_vol = returns_window.pct_change().std() * np.sqrt(12) if len(returns_window) > 2 else np.nan
    if realized_vol and realized_vol > 0:
        scale = min(1.5, target_vol / realized_vol)
        net_ret *= scale

    portfolio_value *= (1 + net_ret)
    portfolio_history.append({
        'Date': next_date,
        'Portfolio Value': portfolio_value,
        'Top 10 Weights': weights_full[final_top10.index]
    })
    prev_weights = weights_full
    daily_values.append(portfolio_value)

# Evaluation
portfolio_df = pd.DataFrame(portfolio_history)
portfolio_series = pd.Series(daily_values, index=prices.index[5:5 + len(daily_values)])
benchmark_series = benchmark_monthly[portfolio_series.index]

total_return = (portfolio_series[-1] / portfolio_series[0]) - 1
benchmark_return = (benchmark_series[-1] / benchmark_series[0]) - 1
returns = portfolio_series.pct_change().dropna()
sharpe_ratio = returns.mean() / returns.std() * np.sqrt(12)
rolling_max = portfolio_series.cummax()
drawdown = (portfolio_series - rolling_max) / rolling_max
drawdown_max = drawdown.min()

# Output
print(f"\n✅ Final Portfolio Value: ${portfolio_series[-1]:.2f}")
print(f"📈 Total Return: {total_return:.2%}")
print(f"⚖️ Sharpe Ratio: {sharpe_ratio:.2f}")
print(f"📉 Max Drawdown: {drawdown_max:.2%}")
print(f"📊 Benchmark Return: {benchmark_return:.2%}")
print("\n📊 Final Top 10 Holdings:")
print(portfolio_df.iloc[-1]['Top 10 Weights'])

# Chart
plt.figure(figsize=(10, 6))
plt.plot(portfolio_series.index, portfolio_series.values, label='Strategy Portfolio')
plt.plot(portfolio_series.index, initial_capital * (benchmark_series / benchmark_series.iloc[0]), label='S&P 500')
plt.title('Portfolio vs Benchmark (Monthly Rebalancing)')
plt.xlabel('Date')
plt.ylabel('Value ($)')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("portfolio_vs_benchmark.png")
plt.show()


