import sys, io, time, json

import pandas_datareader as pd_dr
import numpy as np
import pandas as pd
import datetime

import backtrader as bt


class MacdRsiStrategy(bt.Strategy):

    params = (
        ('printlog', False),
        ('macd_fast', 8),
        ('macd_slow', 21),
        ('macd_signal', 6),
        ('rsi', 13),
    )

    def log(self, txt, dt=None, doprint=False):
        if self.params.printlog or doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))

    def __init__(self):

        self.dataclose = self.datas[0].close
        self.datahigh = self.datas[0].high
        self.datalow = self.datas[0].low

        self.macd = bt.talib.MACD(self.data, fastperiod=self.params.macd_fast, slowperiod=self.params.macd_slow, signalperiod=self.params.macd_signal)
        self.rsi = bt.talib.RSI(self.data, timeperiod=self.params.rsi)

        self.macdCrossover = bt.ind.CrossOver(self.macd.macd, self.macd.macdsignal, subplot=False)

    def next(self):

        i =  list(range(0, len(self.datas)))
        for (d,j) in zip(self.datas,i):
            if len(d) == (d.buflen()-1):
                self.close()

        if (self.macdCrossover[0] > 0) and (self.macd.macd[0] < 0) and (self.rsi[0] < 50) and (self.getposition().size == 0):
            self.buy()
        elif (self.macdCrossover[0] < 0) and (self.macd.macd[0] > 0) and (self.getposition().size == 1):
            self.sell()

    def stop(self):

        self.endvalue = self.broker.getvalue()
        self.log(f"End Value: {self.endvalue}", doprint=True)


def bt_format_results(testRes, optParaList):

    testResAna = testRes[0].analyzers.getbyname("trades").get_analysis()

    if testResAna.total.total == 0:
        return False

    # For Debug use
    # print(json.dumps(testResAna))
    # print(f"-------------------------")

    optParaVal = []
    for optParaKey in optParaList:
        optParaVal.append(testRes[0].params._get(optParaKey))
    res1 = dict (zip (optParaList, optParaVal))
    
    res2 = {
        'total_trade': testResAna.total.total,
        'pnl_net': testResAna.pnl.net.total,
        'pnl_gross': testResAna.pnl.gross.total,
        'long_total': testResAna.long.total,
        'long_won': testResAna.long.won,
        'long_lost': testResAna.long.lost,
        'long_won_amt': testResAna.long.pnl.won.total,
        'long_lost_amt': testResAna.long.pnl.lost.total,
        'short_total': testResAna.short.total,
        'short_won': testResAna.short.won,
        'short_lost': testResAna.short.lost,
        'short_won_amt': testResAna.short.pnl.won.total,
        'short_lost_amt': testResAna.short.pnl.lost.total,
    }

    resMerged = {**res1, **res2}

    return resMerged


if __name__ == '__main__':

    optimizationMode = False

    cerebro = bt.Cerebro()
    # cerebro = bt.Cerebro(stdstats=False)
    # cerebro.addobserver(bt.observers.Broker)

    # Get data
    hist_data = pd_dr.data.DataReader('AAPL', 'yahoo', '2021-01-01', '2022-04-01')
    hist_data.reset_index(inplace=True)
    hist_data = hist_data[["Date","High","Low","Open","Close","Volume"]]
    hist_data.columns = ["datetime","high","low","open","close","volume"]
    hist_data.set_index('datetime', inplace=True)

    data = bt.feeds.PandasData(
        dataname=hist_data
        # timeframe=bt.TimeFrame.Minutes  # << Use this if your data is in minutes
    )

    # Data Resampling to 5 min
    # cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=5)
    
    cerebro.adddata(data)

    cerebro.broker.setcash(500.0)

    # cerebro.broker.setcommission(commission=0.005)

    if optimizationMode:
        pass
        cerebro.optstrategy(
            MacdRsiStrategy,
            macd_fast=[8,13,21],
            macd_slow=[13,21,34],
            macd_signal=range(6,11,2), 
            rsi=[8,13,21,34],
        )
        
        optParaList = ["macd_fast","macd_slow","macd_signal","rsi"]

    else:
        cerebro.addstrategy(MacdRsiStrategy)


    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name = "trades")

    strategyTest = cerebro.run()

    if optimizationMode:

        finalResList = []

        print(len(strategyTest))

        for testRes in strategyTest:
            resMerged = bt_format_results(testRes, optParaList)
            if resMerged:
                finalResList.append(resMerged)

        finalResDF = pd.DataFrame(finalResList)

        if (len(finalResDF) > 0):
            finalResDF.sort_values(by='pnl_net', ascending=False, inplace=True)
            finalResDF.to_csv(f"./output_csv/macd_rsi_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", index=False)
        else:
            print("no data")
        

    else:
        # cerebro.plot(style='candlestick', barup='#52A49A', bardown='#DD5E56', barupfill=False)
        cerebro.plot()
