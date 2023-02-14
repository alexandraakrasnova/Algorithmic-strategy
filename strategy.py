import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from pprint import pprint

# weights for calculating delta price, the total should be 1
WEIGHT1 = 0.8
WEIGHT2 = 0.15
WEIGHT3 = 0.05

def direction(one_tick_data):
    direction = []
    PVO_hist, delta_price = one_tick_data['PVO_histogram'], one_tick_data['delta_price']
    for i in range(len(PVO_hist)):
        if (PVO_hist.iloc[i] * delta_price.iloc[i] >= 0):
            direction.append('BUY')
        else:
            direction.append('SELL')
    index = one_tick_data.shape[1]
    one_tick_data.insert(index, 'direction', np.array(direction))


def EMA(days_in_period, stock_param_str):
    k = 2 / (days_in_period + 1)
    EMA_list = []
    param = one_tick_data[f'{stock_param_str}']
    for i in range(len(one_tick_data)):
        if i == 0:
            EMA_list.append(param.iloc[i])
        else:
            EMA_list.append(param.iloc[i] * k + EMA_list[i-1] * (1 - k))
    
    index = one_tick_data.shape[1]
    one_tick_data.insert(index, f'EMA_{stock_param_str}_{days_in_period}', np.array(EMA_list))


def trading(one_tick_data):
    cash_list, stock_list, total_list = [], [], []
    cash = 10000  # example with $10'000
    stock = 0
    #total = 10000
    direction = one_tick_data['direction']
    open = one_tick_data['open']
    for i in range(len(direction)):
        if direction.iloc[i] == 'BUY' and cash != 0:
            stock = (cash / open.iloc[i]) * (1 - broker_comission)
            cash = 0
        elif direction.iloc[i] == 'SELL' and stock != 0:
            cash = (stock * open.iloc[i]) * (1 - broker_comission)
            stock = 0
        cash_list.append(cash)
        stock_list.append(stock)
        total_list.append(cash_list[i] + stock_list[i] * open.iloc[i])
    
    index = one_tick_data.shape[1]
    one_tick_data.insert(index, 'return', np.array(total_list) / 100 - 100)    # %



broker_comission = 0.00025  # example from TinkoffInvestment
start_date = '2020-01-01'  # first year or two are preparatory
end_date = '2022-05-11'
tickers = pd.read_csv('ticker_info.csv')
tickers_list = (tickers['ticker']).head(10).tolist()
stock_data = pd.read_csv('stock_data.csv')
stock_data = pd.DataFrame(stock_data)[['date','ticker','open','high','low','close','volume']]

final_results = dict()
for ticker in tickers_list:

    df = stock_data.loc[stock_data['ticker'] == ticker]
    mask = (df['date'] >= start_date) & (df['date'] <= end_date)
    one_tick_data = df.loc[mask]

    if (one_tick_data.shape[0] < 365):  # does not have a proper amout of data 
        continue

    EMA(9, 'volume')    # 9-period ema represent a week-and-a-half’s worth of data
    EMA(12, 'volume')   # 12-period ema - two weeks
    EMA(26, 'volume')   # 26-period ema - one month
    
    EMA(9, 'open')
    EMA(12, 'open')
    EMA(26, 'open')

    cur_index = one_tick_data.shape[1]
    one_tick_data.insert(cur_index, 'PVO', (one_tick_data['EMA_volume_12'] - one_tick_data['EMA_volume_26']) / one_tick_data['EMA_volume_26'])
    one_tick_data.shift(periods=1, fill_value=0)
    EMA(9, 'PVO')  # Signal line (or trigger line) is used to generate buy and sell signals or suggest a change in a trend

    cur_index = one_tick_data.shape[1]
    one_tick_data.insert(cur_index, 'PVO_histogram', one_tick_data['PVO'] - one_tick_data['EMA_PVO_9'])  
    # histogram is a visual representation of the distance between these two lines

    cur_index = one_tick_data.shape[1]
    delta_price = one_tick_data['open'] - (WEIGHT1 * one_tick_data['EMA_open_9'] + WEIGHT2 * one_tick_data['EMA_open_12'] + WEIGHT3 * one_tick_data['EMA_open_26'])
    one_tick_data.insert(cur_index,'delta_price', delta_price)
    direction(one_tick_data)
    trading(one_tick_data)
    results = dict()

    # Sharp ratio
    years = int(end_date[:4]) - int(start_date[:4]) + (int(end_date[5:7]) - int(start_date[5:7])) / 12 + (
            int(end_date[8:]) - int(start_date[8:])) / 365
    total = (one_tick_data['return'] + 100) * 100

    try:
        stock_return = (math.log(total.iloc[-1] / total.iloc[0]) / math.log(years)) * 100 - 100  # %
    except IndexError:
        continue
    RFR = 5  # % - Risk Free Rate

    average_return = (one_tick_data['close'][365:] / one_tick_data['close'].shift(365)[365:]).mean() * 100 - 100
    StdDev = (np.square(((one_tick_data['close'][365:] / one_tick_data['close'].shift(365)[365:])
                        * 100 - 100 - average_return)).to_numpy()).mean() ** (0.5)  # Standard Deviation
    results['Sharp ratio'] = (stock_return - RFR) / StdDev

    # Calmar ratio
    calmar_numerator = (one_tick_data['close'][365:] - one_tick_data['close'].shift(365)[365:]) / one_tick_data['close'].shift(365)[365:]
    calmar_denominator = (one_tick_data['close'].rolling(365).min()[365:] - one_tick_data['close'].shift(365)[365:]).abs() / \
                         one_tick_data['close'].shift(365)[365:]
    results['Calmar ratio'] = (calmar_numerator / calmar_denominator).median()

    final_results[ticker] = results

print(final_results)