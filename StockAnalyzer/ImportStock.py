

########################################################################################################################
# 公共函数 定义 和 类
########################################################################################################################
# 时间价格数据对
class TimePriceItem(object):
    def __init__(self, time, price):
        self.time = time
        self.price = price


# 按给定时长计算的均线对象(日线）
# ma_time = 0表示不指定具体时间的均线，将获取所有的均线；如果不等于零仅获取对应时间的均线
COL_DATE = 0    # 时间列号
COL_OPEN = 1    # 开盘价列号
COL_CLOSE = 2   # 收盘价列号

# 印花税率 0.1%, 仅卖出时收
TAX_RATE = (0.1/100)
# 券商佣金双向万6，不足5元的按5元收取
BROKER_COMMISSION_RATE = (6/10000)
# 沪市过付费, 双向成交金额0.02/1000, 不足1元的按1元收取
SH_TRANSFER_RATE = (0.02/1000)


# 根据时间索引从dataframe中获取时间
def get_data_time(data, time_index):
    return data.iat[time_index, COL_DATE]


# 根据价格索引从dataframe中获取价格
def get_data_price(data, price_index, price_type):
    return data.iat[price_index, price_type]


# 时间价格对
def get_data_time_price_item(data, timeprice_index, price_type):
    return TimePriceItem(get_data_time(data, timeprice_index), get_data_price(data, timeprice_index, price_type))

########################################################################################################################
# 获取、更新以及保存交易数据源类
########################################################################################################################


########################################################################################################################
# 交易计算主程序类
########################################################################################################################
class CalcStockGain(object):
    def __init__(self, data, stock_code='', buy_ma_len=5, sell_ma_len=5):
        self.stock_code = stock_code    # 股票代码
        self.buy_ma_len = buy_ma_len    # 买入时均线长度
        self.sell_ma_len = sell_ma_len  # 卖出时均线长度
        self.buy_ma_list = []           # 买入时均线价格列表, 用于计算和绘图
        self.sell_ma_list = []          # 卖出时均线价格列表, 用于计算和绘图
        self.money = 0                  # 现金
        self.stock_num = 0              # 股票数量
        self.stock_buy_price = 0        # 股票买入价
        self.stock_buy_num = 0          # 买入次数
        self.stock_sell_num = 0         # 卖出次数
        self.stock_buy_succ_num = 0     # 买入成功次数, 卖出价大于买入价
        self.general_asset = 0          # 资产总额, 现金+股票*当日收盘价
        self.succ_ratio = 0             # 买入成功率
        self.gain_ratio = 0             # 资产增值率
        self.price_list = []            # 价格列表, 仅用于绘图
        self.buy_list = []              # 买入价格列表, 仅用于绘图
        self.sell_list = []             # 卖出价格列表, 仅用于绘图

        self.get_price_list(data, COL_CLOSE)
        self.get_ma_list(data, self.buy_ma_list, self.buy_ma_len)
        self.get_ma_list(data, self.sell_ma_list, self.sell_ma_len)
        self.calc_succ_ratio_and_gain(data)

    # 获取时间价格列表
    def get_price_list(self, data, price_type=COL_CLOSE):
        for i in range(len(data)):
            self.price_list.append(get_data_time_price_item(data, i, price_type))

    # 计算某个价格对应的ma价格
    def calc_ma_price(self, data, price_index, price_type=COL_CLOSE, ma_len=5):
        if (ma_len > 0) and ((price_index + 1 - ma_len) >= 0):
            # 利用开盘价计算均线，0列是时间，1列是开盘价，2是收盘价
            ma_sum = 0.000
            for j in range(ma_len):
                ma_sum += float(get_data_price(data, price_index - j, price_type))
            # 均线值
            ma_price = ma_sum / ma_len
        else:
            ma_price = 0.000
        return ma_price

    def get_ma_list(self, data, ma_list, ma_len):
        # 生成均线列表
        for i in range(len(data)):
            ma_price = self.calc_ma_price(data, i, price_type=COL_CLOSE, ma_len=ma_len)
            # 加入均线列表中
            ma_list.append(TimePriceItem(get_data_time(data, i), ma_price))

    def get_buy_ma_list(self, data):
        get_ma_list(data, self.buy_ma_list, self.buy_ma_len)

    def get_sell_ma_list(self,data):
        get_ma_list(data,self.sell_ma_list, self.sell_ma_len)

    def display_ma_list(self):
        for i in range(len(self.buy_ma_list)):
            print('buy_ma_list')
            print('date = %s, ma_price = %.3f' % (self.buy_ma_list[i].time, self.buy_ma_list[i].price))
        for i in range(len(self.sell_ma_list)):
            print('sell_ma_list')
            print('date = %s, ma_price = %.3f' % (self.sell_ma_list[i].time, self.sell_ma_list[i].price))

    # 验证在不同均线趋势变化时买入卖出算法的正确性以及盈利值, 按1W RMB，按收盘价买入卖出
    def calc_succ_ratio_and_gain(self, data, init_money=10000, price_type = COL_CLOSE):
        self.money = init_money
        self.stock_num = 0
        self.stock_buy_price = 0
        self.stock_buy_num = 0
        self.stock_sell_num = 0
        self.stock_buy_succ_num = 0
        self.general_asset = 0
        self.gain_ratio = 0
        self.succ_ratio = 0
        self.buy_list = []
        self.sell_list = []

        # 默认buy_ma_list和sell_ma_list时一样的长度
        ma_list_len = len(self.buy_ma_list)
        if (0 >= ma_list_len) or (0 >= init_money):
            print('error ma list len %d or init money %0.3f' % (ma_list_len, init_money))
            return

        stock_buy_price = 0

        for i in range(ma_list_len):
            j = i-1
            if (j >= 0) and (0 < self.buy_ma_list[i].price) and (0 < self.buy_ma_list[j].price):
                # 趋势向上买入股票
                if self.buy_ma_list[i].price > self.buy_ma_list[j].price:
                    temp_stock_price = get_data_price(data, i, price_type)
                    # 只有没有股票并且钱至少够买100股的情况下才计算买入，不存在多次连续买入的情况
                    if (0 == self.stock_num) and ((self.money // temp_stock_price) >= 100):
                        stock_buy_price = temp_stock_price  # 成功买入时才会记录stock_buy_price
                        # 购买的股票必须是100的整数倍,并且要扣佣金等费用
                        afford_stock_num = calc_affordable_buy_stock_num(self.stock_code, self.money, stock_buy_price)
                        self.stock_num += afford_stock_num
                        self.money -= afford_stock_num * stock_buy_price
                        # 记录买入
                        self.stock_buy_num += 1
                        self.buy_list.append(TimePriceItem(get_data_time(data, i), stock_buy_price))

            if (j >= 0) and (0 < self.sell_ma_list[i].price) and (0 < self.sell_ma_list[j].price):
                # 趋势向下卖出股票
                if self.sell_ma_list[i].price < self.sell_ma_list[j].price:
                    if 0 < self.stock_num:
                        stock_sell_price = get_data_price(data, i, price_type)
                        self.money += self.stock_num * stock_sell_price - calc_get_sell_stock_cost(self.stock_code, self.stock_num, stock_sell_price)
                        self.stock_num = 0
                        self.stock_sell_num += 1
                        self.sell_list.append(TimePriceItem(get_data_time(data, i), stock_sell_price))
                        # 计算买入成功率
                        if stock_sell_price > stock_buy_price:
                            self.stock_buy_succ_num += 1

        # 显示最终金额以及买入卖出数据,如果股票没有卖出要采用最后一天的价格来计算
        self.general_asset = self.money + self.stock_num * data.iat[ma_list_len-1, price_type]
        print('money = %.3f, stork_num = %d, general_asset = %.3f' % (self.money, self.stock_num, self.general_asset))
        print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d' % (self.stock_buy_num, self.stock_sell_num, self.stock_buy_succ_num))

        self.gain_ratio = (self.general_asset - init_money)/init_money*100
        if 0 < self.stock_buy_num:
            self.succ_ratio = self.stock_buy_succ_num/self.stock_buy_num*100
        else:
            self.succ_ratio = 0
        print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (self.gain_ratio, self.succ_ratio))
        print('buy_ma_len = %d, sell_ma_len = %d' % (self.buy_ma_len, self.sell_ma_len))


########################################################################################################################
# 买卖费率计算
########################################################################################################################
# 获取印花税费用，买入不收
def get_tax_fare(trade_stock_num, stock_price):
    return trade_stock_num * stock_price * TAX_RATE


# 获取券商佣金
# 2.证管费：约为成交金额的0.002%收取
# 3.证券交易经手费：A股，按成交金额的0.00696%收取；B股，按成交额双边收取0.0001%；基金，按成交额双边收取0.00975%；权证，按成交额双边收取0.0045%。
# A股2、3项收费合计称为交易规费，合计收取成交金额的0.00896%，包含在券商交易佣金中。
def get_broker_commission(trade_stock_num, stock_price):
    broker_commission = trade_stock_num * stock_price * BROKER_COMMISSION_RATE
    if 5 > broker_commission:
        broker_commission = 5
    return broker_commission


# 计算沪市过户费，600，601，603开头，仅沪市交易收
def get_sh_transfer_fare(stock_code, trade_stock_num, stock_price):
    stock_code_head = int(stock_code) // 1000
    if (600 <= stock_code_head) and (699 >= stock_code_head):
        sh_transfer_fare = trade_stock_num * stock_price * SH_TRANSFER_RATE
        if 1 > sh_transfer_fare:  # 不足1元按1元收取
            sh_transfer_fare = 1
        return sh_transfer_fare
    else:  # 非沪市不收过户费
        return 0


# 获取买入股票的所有涉及费用（包括券商佣金以及沪市过户费）
def calc_get_buy_stock_cost(stock_code, buy_stock_num, stock_price):
    broker_commission = get_broker_commission(buy_stock_num, stock_price)
    sh_transfer_fare = get_sh_transfer_fare(stock_code, buy_stock_num, stock_price)
    return broker_commission + sh_transfer_fare


# 计算可买的股票数量
def calc_affordable_buy_stock_num(stock_code, money, stock_price):
    buy_stock_num = money // stock_price // 100 * 100
    while True:
        if 0 >= buy_stock_num:
            return 0
        left_money = money - (buy_stock_num * stock_price) - calc_get_buy_stock_cost(stock_code, buy_stock_num, stock_price)
        if 0 > left_money:  # 回退100股继续计算
            buy_stock_num -= 100
        else:
            return buy_stock_num


# 获取卖出股票的所有涉及费用（包括券商佣金，印花税以及沪市过户费）
def calc_get_sell_stock_cost(stock_code, sell_stock_num, stock_price):
    tax_fare = get_tax_fare(sell_stock_num, stock_price)
    broker_commission = get_broker_commission(sell_stock_num, stock_price)
    sh_transfer_fare = get_sh_transfer_fare(stock_code, sell_stock_num, stock_price)
    return tax_fare + broker_commission + sh_transfer_fare

########################################################################################################################
# 买卖策略
########################################################################################################################
# 均线交易


# MACD交易
# 具体计算公式及例子如下：
# EMA（12）= 前一日EMA（12）×11/13＋今日收盘价×2/13 = 前一日EMA（12）+ （今日收盘价 - 前一日EMA（12））* 2 / 13
# EMA（26）= 前一日EMA（26）×25/27＋今日收盘价×2/27 = 前一日EMA（26）+ （今日收盘价 - 前一日EMA（26））* 2 / 27
# 关键的一点是：新股上市首日，其DIFF,DEA以及MACD都为0，因为当日不存在前一日，无法做迭代。而计算新股上市第二日的EMA时，
# 前一日的EMA需要用收盘价（而非0）来计算。另外，需要注意，计算过程小数点后四舍五入保留4位小数，最后显示的时候四舍五入保
# 留3位小数。
# DIFF = 今日EMA（12）- 今日EMA（26）
# DEA（MACD）= 前一日DEA×8/10＋今日DIFF×2/10
# BAR = 2×(DIFF－DEA)
class CalcMACD(object):
    def __init__(self, data):
        self.EMA12_list = []
        self.EMA26_list = []
        self.DIFF_list = []
        self.DEA_list = []
        self.BAR_list = []
        self.calc_EMA12_list(data)
        self.calc_EMA26_list(data)
        self.calc_DIFF_list()
        self.calc_DEA_list()
        self.calc_BAR_list()

    # 计算当前EMA值
    def calc_cur_EMA(self, data, EMA_len, last_EMA, cur_close_price):
        return last_EMA + ((cur_close_price - last_EMA) * 2 / (EMA_len + 1))

    # 计算EMA12列表
    def calc_EMA12_list(self, data):
        self.EMA12_list.clear()
        data_len = len(data)
        if 0 >= data_len:
            return
        self.EMA12_list.append(TimePriceItem(get_data_time(data, 0), get_data_price(data, 0, COL_CLOSE)))    # 按前一日收盘价计算, 要改
        for i in range(1, data_len):
            last_EMA12 = self.EMA12_list[i-1].price
            cur_EMA12 = self.calc_cur_EMA(data, 12, last_EMA12, get_data_price(data, i, COL_CLOSE))
            self.EMA12_list.append(TimePriceItem(get_data_time(data, i), cur_EMA12))

    def calc_EMA26_list(self, data):
        self.EMA26_list.clear()
        data_len = len(data)
        if 0 >= data_len:
            return
        self.EMA26_list.append(TimePriceItem(get_data_time(data, 0), get_data_price(data, 0, COL_CLOSE)))   # 按前一日收盘价计算, 要改
        for i in range(1, data_len):
            last_EMA26 = self.EMA26_list[i-1].price
            cur_EMA26 = self.calc_cur_EMA(data, 26, last_EMA26, get_data_price(data, i, COL_CLOSE))
            self.EMA26_list.append(TimePriceItem(get_data_time(data, i), cur_EMA26))

    def calc_DIFF_list(self):
        list_len = len(self.EMA12_list)
        for i in range(list_len):
            self.DIFF_list.append(TimePriceItem(self.EMA12_list[i].time, self.EMA12_list[i].price - self.EMA26_list[i].price))

    def calc_DEA_list(self):
        list_len = len(self.DIFF_list)
        if 0 >= list_len:
            return
        self.DEA_list.append(TimePriceItem(self.DIFF_list[0].time, 0.000))
        for i in range(1, list_len):
            last_DEA = self.DEA_list[i-1].price
            cur_DEA = last_DEA*8/10 + self.DIFF_list[i].price*2/10
            self.DEA_list.append(TimePriceItem(self.DIFF_list[i].time, cur_DEA))

    def calc_BAR_list(self):
        list_len = len(self.DIFF_list)
        for i in range(list_len):
            self.BAR_list.append(TimePriceItem(self.DIFF_list[i].time, 2*(self.DIFF_list[i].price - self.DEA_list[i].price)))

    def print_MACD(self):
        for i in range(len(self.EMA12_list)):
            print("%s %0.3f %0.3f %0.3f %0.3f %0.3f" % (self.EMA12_list[i].time, self.EMA12_list[i].price,
                                                        self.EMA26_list[i].price, self.DIFF_list[i].price,
                                                        self.DEA_list[i].price, self.BAR_list[i].price))








