import sys
sys.path.append(r'./StockAnalyzer')
import ImportStock as Sa


# Test code here
def main():

    '''
    # 600000
    # 早期长期下跌趋势
    calc_best_ma_len(data, stock_code='600000', start='1990-01-01', end='2005-05-31')
    del data

    # 2008年前单上行趋势
    data = ts.get_k_data('600000', start='2005-06-01', end='2008-01-15')
    calc_best_ma_len(data, stock_code='600000', start='2005-06-01', end='2008-01-15')
    del data

    # 2008年单下行趋势
    data = ts.get_k_data('600000', start='2008-01-16', end='2008-10-31')
    calc_best_ma_len(data, stock_code='600000', start='2008-01-16', end='2008-10-31')
    del data

    # 2007 2008 急速上升下降趋势
    data = ts.get_k_data('600000', start='2005-06-01', end='2008-10-31')
    calc_best_ma_len(data, stock_code='600000', start='2005-06-01', end='2008-10-31')
    del data

    # 2008年10月31日到最近震荡趋势
    data = ts.get_k_data('600000', start='2008-11-1', end='2018-6-14')
    calc_best_ma_len(data, stock_code='600000', start='2008-11-1', end='2018-6-14')
    del data

    ####################################################################################
    # 600021
    # 早期长期下跌趋势
    data = ts.get_k_data('600021', start='1990-01-01', end='2014-09-30')
    calc_best_ma_len(data, stock_code='600021', start='1990-01-01', end='2014-09-30')
    del data

    # 2015年前单上行趋势
    data = ts.get_k_data('600021', start='2014-10-01', end='2015-05-30')
    calc_best_ma_len(data, stock_code='600021', start='2014-10-01', end='2015-05-30')
    del data

    # 2015年单下行趋势
    data = ts.get_k_data('600021', start='2015-05-30', end='2016-01-30')
    calc_best_ma_len(data, stock_code='600021', start='2015-05-30', end='2016-01-30')
    del data

    # 2015急速上升下行趋势
    data = ts.get_k_data('600021', start='2014-10-01', end='2016-01-30')
    calc_best_ma_len(data, stock_code='600021', start='2014-10-01', end='2016-01-30')
    del data

    # 2015到最近震荡趋势
    data = ts.get_k_data('600021', start='2016-02-01', end='2018-6-14')
    calc_best_ma_len(data, stock_code='600021', start='2016-02-01', end='2018-6-14')
    del data

    ######################################################################################
    # 000783
    # 早期长期下跌趋势
    data = ts.get_k_data('000783', start='1990-01-01', end='2006-06-30')
    calc_best_ma_len(data, stock_code='000783', start='1990-01-01', end='2006-06-30')
    del data

    # 2008前单上行趋势
    data = ts.get_k_data('000783', start='2006-07-01', end='2007-12-30')
    calc_best_ma_len(data, stock_code='000783', start='2006-07-01', end='2007-12-30')
    del data

    # 2008单下行趋势
    data = ts.get_k_data('000783', start='2008-01-01', end='2008-12-31')
    calc_best_ma_len(data, stock_code='000783', start='2008-01-01', end='2008-12-31')
    del data

    # 2006 2008急速上升下降趋势
    data = ts.get_k_data('000783', start='2006-07-01', end='2008-12-31')
    calc_best_ma_len(data, stock_code='000783', start='2006-07-01', end='2008-12-31')
    del data

    # 2009 最近震荡趋势
    data = ts.get_k_data('000783', start='2009-01-01', end='2018-6-14')
    calc_best_ma_len(data, stock_code='000783', start='2009-01-01', end='2018-6-14')
    del data
    '''

    # 2015到最近震荡趋势
    # data = ts.get_k_data('002322', autype=None, start='2009-12-18', end='2009-12-21')
    # a1 = Sa.CalcMACD(data)
    # a1.print_MACD()
    # calc_best_ma_len(data, stock_code='600021', start='2017-01-01', end='2018-06-15')
    # del data

    # stock_list = ['600000', '601666', '600111', '000783', '002594', '300024', '600000', '600021', '300258']
    stock_list = ['600000']

    stock_list_len = len(stock_list)
    for i in range(stock_list_len):
        Sa.calc_best_ma_trade_strategy(stock_list[i], '2005-01-01', '2008-10-30', 15, 15, 10000)
        # Sa.calc_best_macd_trade_strategy(stock_list[i], '2005-06-01', '2008-10-30', 10000)


main()





