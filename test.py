import tushare as ts
import datetime
import numpy as np
import sys
sys.path.append(r'./StockAnalyzer')
import ImportStock as Sa
import BaiduIndexCrawler as BIC


# Test code here
def main():
    # stock_list = ['600000', '601666', '600111', '000783', '002594', '300024', '600000', '600021', '300258']
    # stock_list = ['002594']

    # stock_list_len = len(stock_list)
    #for i in range(stock_list_len):
    #    Sa.calc_best_ma_trade_strategy(stock_list[i], '20170615', '20170730', 30, 30, 10000)
    # Sa.calc_best_macd_trade_strategy(stock_list[i], '2018-06-30', '2019-07-05', 10000)

    # BIC.GetBaiduIndex()
    ts_pro = ts.pro_api('45dba9f72d4488e265fc980ea7b70f4416b529589d46afa55540894a')
    stock_list = ts_pro.query('stock_basic', exchange='', list_status='L',
                              fields='ts_code,symbol,name,area,industry,list_date')
    for i in range(len(stock_list)):
        stock_code = str(stock_list.iloc[i, 1])
        stock_file = 'D:' + '\\stock_data\\' + stock_code + ".csv"
        network_data = ts.get_k_data(stock_code, '1994-01-01')
        # network_data数据转换
        for j in range(len(network_data)):
            network_data.iloc[j, 0] = int(
                datetime.datetime.strptime(network_data.iloc[j, 0], '%Y-%m-%d').strftime('%Y%m%d'))
        network_data[['date', 'volume', 'code']] = network_data[['date', 'volume', 'code']].astype(int)
        network_data[['open', 'close', 'high', 'low']] = network_data[['open', 'close', 'high', 'low']].astype(
            np.float32)
        network_data.to_csv(stock_file, index=False)


main()





