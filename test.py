import tushare as ts
import sys
sys.path.append(r'./StockAnalyzer')
import ImportStock as Sa
import progressbar as pb
#import matplotlib.colorbar
#import matplotlib.contour as contour
#import matplotlib.font_manager as font_manager
#from matplotlib import afm, cbook, ft2font, rcParams, get_cachedir
import matplotlib.pyplot as plt

total = 20*20
progress = 0
pbar = None
ma_list = []
price_list = []
buy_list = []
sell_list = []

# 计算最优ma len
def calc_best_ma_len(data, stock_code='', start='', end=''):
    max_stock_code = ''
    max_money = 0
    max_stock_num = 0
    max_stock_buy_num = 0
    max_stock_sell_num = 0
    max_stock_buy_succ_num = 0
    max_general_asset = 0
    max_gain_ratio = 0
    max_succ_ratio = 0
    best_buy_ma_len = 0
    best_sell_ma_len = 0

    global progress
    global pbar
    global ma_list
    global price_list
    global buy_list
    global sell_list

    for i in range(1, 20):
        for j in range(1, 20):
            stock_ma = Sa.CalcStockGain(data, stock_code=stock_code, buy_ma_len=i, sell_ma_len=j)
            if max_general_asset < stock_ma.general_asset:
                max_stock_code = stock_ma.stock_code
                max_money = stock_ma.money
                max_stock_num = stock_ma.stock_num
                max_stock_buy_num = stock_ma.stock_buy_num
                max_stock_sell_num = stock_ma.stock_sell_num
                max_stock_buy_succ_num = stock_ma.stock_buy_succ_num
                max_general_asset = stock_ma.general_asset
                max_gain_ratio = stock_ma.gain_ratio
                max_succ_ratio = stock_ma.succ_ratio
                # buy_ma_list = stock_ma.buy_ma_list
                # sell_ma_list = stock_ma.sell_ma_list
                price_list = stock_ma.price_list
                buy_list = stock_ma.buy_list
                sell_list = stock_ma.sell_list
                best_buy_ma_len = stock_ma.buy_ma_len
                best_sell_ma_len = stock_ma.sell_ma_len


            # 更新进度
            progress += 1
            pbar.update(progress)

    print('stock_code = %s' % max_stock_code)
    print('money = %.3f, stork_num = %d, general_asset = %.3f' % (max_money, max_stock_num, max_general_asset))
    print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d' % (max_stock_buy_num, max_stock_sell_num, max_stock_buy_succ_num))
    print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (max_gain_ratio, max_succ_ratio))
    print('best_buy_ma_len = %d, best_sell_ma_len = %d, start = %s, end = %s' % (best_buy_ma_len, best_sell_ma_len, start, end))

    print('deal list:')
    buy_list_len = len(buy_list)
    sell_list_len = len(sell_list)
    for i in range(buy_list_len):
        # print('BUY : date = %s, price = %.03f' % (buy_list[i].time, buy_list[i].price))
        if i < sell_list_len:
            # print('SELL: date = %s, price = %.03f' % (sell_list[i].time, sell_list[i].price))
            pass

# Test code here
def main():
    global total
    global pbar
    widgets = ['Progress: ', pb.Percentage(), ' ', pb.Bar('#'), ' ', pb.Timer(), ' ', pb.ETA(), ' ']
    pbar = pb.ProgressBar(widgets=widgets, maxval=total).start()

    '''
    # 600000
    # 早期长期下跌趋势
    data = ts.get_k_data('600000', start='1990-01-01', end='2005-05-31')
    calc_best_ma_len(data, stock_code='600000', start='1990-01-01', end='2005-05-31')
    del data

    global ma_list
    global price_list
    global buy_list
    global sell_list
    plt.figure(1)
    # plt.plot(ma_list,)
    plt.ylabel('date')
    plt.ylabel('price')

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
    data = ts.get_k_data('002322', autype=None, start='2009-12-18', end='2009-12-21')
    a1 = Sa.CalcMACD(data)
    a1.print_MACD()
    # calc_best_ma_len(data, stock_code='600021', start='2017-01-01', end='2018-06-15')
    del data

main()





