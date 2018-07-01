import tushare as ts
import progressbar as pb


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
def get_data_time_price_item(data, time_price_index, price_type):
    return TimePriceItem(get_data_time(data, time_price_index), get_data_price(data, time_price_index, price_type))


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
        left_money = money - (buy_stock_num * stock_price) - calc_get_buy_stock_cost(stock_code,
                                                                                     buy_stock_num,
                                                                                     stock_price)
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
# 获取、更新以及保存交易数据源类
########################################################################################################################
class GetStockRawData(object):
    def __init__(self, stock_code, start, end):
        self.stock_code = stock_code  # 股票代码
        self.start = start
        self.end = end
        self.data = ts.get_k_data(stock_code, start, end)


########################################################################################################################
# 交易策略基类
########################################################################################################################
class BaseTradeStrategy(object):
    def __init__(self, stock_raw_data_obj, init_money):
        self.stock_code = stock_raw_data_obj.stock_code     # 股票代码
        self.data = stock_raw_data_obj.data                 # 原始数据
        self.init_money = init_money    # 初始资金
        self.money = init_money  # 当前资金，用于计算过程
        self.stock_num = 0
        self.buy_list = []
        self.stock_buy_num = 0
        self.stock_last_buy_time = ''
        self.stock_last_buy_price = 0
        self.sell_list = []
        self.stock_sell_num = 0
        self.stock_last_sell_time = ''
        self.stock_last_sell_price = 0
        self.stock_buy_succ_num = 0
        self.general_asset = 0          # 资产总额, 现金+股票*当日收盘价
        self.succ_ratio = 0             # 买入成功率
        self.gain_ratio = 0             # 资产增值率

    # 买入股票
    def buy_stock(self, intent_stock_buy_time, intent_stock_buy_price):
        # 购买的股票必须是100的整数倍,并且要扣佣金等费用
        afford_stock_num = calc_affordable_buy_stock_num(self.stock_code, self.money, intent_stock_buy_price)
        # 钱至少够买100股的情况下才计算买入，不存在多次连续买入的情况
        if (0 != self.stock_num) or (100 > afford_stock_num):
            return
        self.stock_num += afford_stock_num
        self.money -= afford_stock_num * intent_stock_buy_price
        # 记录成功买入的时间和价格
        self.stock_buy_num += 1
        self.buy_list.append(TimePriceItem(intent_stock_buy_time, intent_stock_buy_price))
        self.stock_last_buy_time = intent_stock_buy_time
        self.stock_last_buy_price = intent_stock_buy_price

    # 卖出股票
    def sell_stock(self, intent_stock_sell_time, intent_stock_sell_price):
        if 0 >= self.stock_num:
            return
        # 假定卖出股票的钱一定比手续费多
        self.money += self.stock_num * intent_stock_sell_price - \
            calc_get_sell_stock_cost(self.stock_code, self.stock_num, intent_stock_sell_price)
        self.stock_num = 0
        # 记录成功卖出的时间和价格
        self.stock_sell_num += 1
        self.sell_list.append(TimePriceItem(intent_stock_sell_time, intent_stock_sell_price))
        self.stock_last_sell_time = intent_stock_sell_time
        self.stock_last_sell_price = intent_stock_sell_price
        # 卖出时计算买入成功率, 卖出金额>买入金额*1.01, 代价按1%来计算
        if self.stock_last_sell_price > self.stock_last_buy_price*1.01:
            self.stock_buy_succ_num += 1

    def print_gain_ratio(self, list_len):
        # 显示最终金额以及买入卖出数据,如果股票没有卖出要采用最后一天的价格来计算
        self.general_asset = self.money + self.stock_num * get_data_price(self.data, list_len - 1, COL_CLOSE)
        # print('money = %.3f, stork_num = %d, general_asset = %.3f' % (self.money, self.stock_num, self.general_asset))
        # print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d' % (self.stock_buy_num,
        #                                                                            self.stock_sell_num,
        #                                                                            self.stock_buy_succ_num))
        # 计算买卖成功率
        self.gain_ratio = (self.general_asset - self.init_money) / self.init_money * 100
        if 0 < self.stock_buy_num:
            self.succ_ratio = self.stock_buy_succ_num / self.stock_buy_num * 100
        else:
            self.succ_ratio = 0
        # print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (self.gain_ratio, self.succ_ratio))


########################################################################################################################
# 基于均线买卖的策略
########################################################################################################################
TRADE_PASS = 0
TRADE_BUY = 1
TRADE_SELL = 2


# 根据买卖交易均线趋势判断该买还是卖，短期均线操作优先级高
def ma_trade_judge(buy_ma_len, sell_ma_len, buy_ma_first_price, buy_ma_next_price, sell_ma_first_price,
                   sell_ma_next_price):
    # 买优先级高
    if buy_ma_len < sell_ma_len:
        # 短期均线向上买
        if buy_ma_first_price < buy_ma_next_price:
            return TRADE_BUY
        else:
            # 短期均线向下且长期均线向下卖
            if sell_ma_first_price > sell_ma_next_price:
                return TRADE_SELL
            else:
                # 短期均线向下而长期均线向上，不做操作
                return TRADE_PASS
    # 卖优先级高
    if buy_ma_len > sell_ma_len:
        # 短期均线向下卖
        if sell_ma_first_price > sell_ma_next_price:
            return TRADE_SELL
        else:
            # 短期均线向上且长期均线向上买
            if buy_ma_first_price < buy_ma_next_price:
                return TRADE_BUY
            else:
                # 短期均线向上且长期均线向下，不做操作
                return TRADE_PASS
    # 买卖优先级一样
    if buy_ma_len == sell_ma_len:
        if buy_ma_first_price < buy_ma_next_price:
            return TRADE_BUY
        elif buy_ma_first_price > buy_ma_next_price:
            return TRADE_SELL
        else:  # buy_ma_first_price == buy_ma_next_price:
            return TRADE_PASS


class MATradeStrategy(BaseTradeStrategy):
    def __init__(self, stock_raw_data_obj, init_money, buy_ma_len=5, sell_ma_len=5):
        BaseTradeStrategy.__init__(self, stock_raw_data_obj, init_money)
        self.buy_ma_len = buy_ma_len    # 买入时均线长度
        self.sell_ma_len = sell_ma_len  # 卖出时均线长度
        self.buy_ma_list = []           # 买入时均线价格列表, 用于计算和绘图
        self.sell_ma_list = []          # 卖出时均线价格列表, 用于计算和绘图
        # 获取买入卖出MA价格列表
        if 0 < self.buy_ma_len:
            self.get_ma_list(self.buy_ma_list, self.buy_ma_len)
        if 0 < self.sell_ma_len:
            self.get_ma_list(self.sell_ma_list, self.sell_ma_len)

    # 计算某个价格对应的ma价格
    def calc_ma_price(self, price_index, ma_len):
        if (ma_len > 0) and ((price_index + 1 - ma_len) >= 0):
            # 利用开盘价计算均线，0列是时间，1列是开盘价，2是收盘价
            ma_sum = 0.000
            for j in range(ma_len):
                ma_sum += float(get_data_price(self.data, price_index - j, COL_CLOSE))
            # 均线值
            ma_price = ma_sum / ma_len
        else:
            ma_price = 0.000
        return ma_price

    # 获取MA价格列表
    def get_ma_list(self, ma_list, ma_len):
        # 生成均线列表
        for i in range(len(self.data)):
            ma_price = self.calc_ma_price(i, ma_len)
            # 加入均线列表中
            ma_list.append(TimePriceItem(get_data_time(self.data, i), ma_price))

    def display_ma_list(self):
        for i in range(len(self.buy_ma_list)):
            print('buy_ma_list')
            print('date = %s, ma_price = %.3f' % (self.buy_ma_list[i].time, self.buy_ma_list[i].price))
        for i in range(len(self.sell_ma_list)):
            print('sell_ma_list')
            print('date = %s, ma_price = %.3f' % (self.sell_ma_list[i].time, self.sell_ma_list[i].price))

    def run_trade_strategy(self):
        # buy_ma_list和sell_ma_list时一样的长度
        buy_ma_list_len = len(self.buy_ma_list)
        sell_ma_list_len = len(self.sell_ma_list)
        if (0 >= self.money) or (0 >= buy_ma_list_len) or (0 >= sell_ma_list_len) \
                or (buy_ma_list_len != sell_ma_list_len):
            print('MATradeStrategy.run_trade_strategy error ma list len %d or init money %0.3f'
                  % (buy_ma_list_len, self.money))
            return

        # 按MA均线判断收益率
        for i in range(buy_ma_list_len):
            j = i + 1
            if j < buy_ma_list_len:
                if (0 >= self.buy_ma_list[i].price) or (0 >= self.buy_ma_list[j].price):
                    continue
                # 判断是买还是卖
                ma_trade = ma_trade_judge(self.buy_ma_len, self.sell_ma_len, self.buy_ma_list[i].price,
                                          self.buy_ma_list[j].price, self.sell_ma_list[i].price,
                                          self.sell_ma_list[j].price)
                if TRADE_BUY == ma_trade:
                    # 买入股票
                    self.buy_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                elif TRADE_SELL == ma_trade:
                    # 卖出股票
                    self.sell_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                else:
                    # 不交易 TRASE_PASS == ma_trade
                    pass

        # print(' ', end='\n')
        # print('MATradeStrategy: buy_ma_len = %d, sell_ma_len = %d' % (self.buy_ma_len, self.sell_ma_len))
        self.print_gain_ratio(buy_ma_list_len)


########################################################################################################################
# 基于均线买卖的策略， 根据10、20、30上行还是下行动态调整买入和卖出的MA价格，
# 如果L天线上行，动态计算M买入均线和N卖出均线，其中
# 如果L天线下行，
########################################################################################################################
class PhaseMaLenItem(object):
    def __init__(self, phase_start_index, phase_end_index, phase_buy_ma_len, phase_sell_ma_len):
        self.phase_start_index = phase_start_index
        self.phase_end_index = phase_end_index
        self.phase_buy_ma_len = phase_buy_ma_len
        self.phase_sell_ma_len = phase_sell_ma_len


MA_DIR_INIT = 0
MA_DIR_UP = 1
MA_DIR_DOWN = 2


class SmartMATradeStrategy(MATradeStrategy):
    def __init__(self, stock_raw_data_obj, init_money, max_long_ma_len):
        MATradeStrategy.__init__(self, stock_raw_data_obj, init_money, 0, 0)
        self.long_ma_list = []                      # 长期比较均线列表
        self.max_long_ma_len = max_long_ma_len      # 长期比较均线
        self.phase_index_ma_len_list = []           # 阶段和ma长度记录列表

    # 计算历史到当前阶段总收益
    def get_phase_general_asset(self, phase_start_index, phase_end_index, phase_buy_ma_len, phase_sell_ma_len):
        self.buy_ma_list = []
        self.sell_ma_list = []
        self.get_ma_list(self.buy_ma_list, phase_buy_ma_len)
        self.get_ma_list(self.sell_ma_list, phase_sell_ma_len)
        for i in range(phase_start_index, phase_end_index):
            j = i + 1
            if j <= phase_end_index:
                if (0 >= self.buy_ma_list[i].price) or (0 >= self.buy_ma_list[j].price):
                    continue
                # 判断是买还是卖
                ma_trade = ma_trade_judge(phase_buy_ma_len, phase_sell_ma_len, self.buy_ma_list[i].price,
                                          self.buy_ma_list[j].price, self.sell_ma_list[i].price,
                                          self.sell_ma_list[j].price)
                if TRADE_BUY == ma_trade:
                    # 买入股票
                    self.buy_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                elif TRADE_SELL == ma_trade:
                    # 卖出股票
                    self.sell_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                else:
                    # 不交易 TRADE_PASS == ma_trade
                    pass
        # 计算阶段收益
        return self.money + self.stock_num*get_data_price(self.data, phase_end_index, COL_CLOSE)

    # 获取阶段最大的总收益
    def get_max_phase_general_asset(self, phase_start_index, phase_end_index, long_ma_len, ma_dir):
        max_phase_general_asset = 0
        max_phase_money = 0
        max_phase_stock_num = 0
        max_phase_stock_buy_num = 0
        max_phase_buy_list = []
        max_phase_stock_last_buy_time = 0
        max_phase_stock_last_buy_price = 0
        max_phase_stock_sell_num = 0
        max_phase_sell_list = []
        max_phase_stock_last_sell_time = 0
        max_phase_stock_last_sell_price = 0
        max_phase_stock_buy_succ_num = 0
        best_phase_buy_ma_len = 0
        best_phase_sell_ma_len = 0

        print(' ', end='\n')
        print('phase_start_index = %d,phase_end_index = %d,long_ma_len = %d, ma_dir = %d'
              % (phase_start_index, phase_end_index, long_ma_len, ma_dir))

        # 假设长期均线L向上，买入均线M小于卖出均线N, 且L > N > M（快买慢卖）, 根据这个假设便利计算最高收益率对应的各均线值
        if MA_DIR_UP == ma_dir:
            # 遍历买入卖出均线组合
            for phase_sell_ma_len in range(2, long_ma_len):
                for phase_buy_ma_len in range(2, phase_sell_ma_len):
                    # 保存操作前的初始金额和股票数以便回退操作
                    phase_money = self.money
                    phase_stock_num = self.stock_num
                    phase_stock_buy_num = self.stock_buy_num
                    phase_buy_list = self.buy_list.copy()
                    phase_stock_last_buy_time = self.stock_last_buy_time
                    phase_stock_last_buy_price = self.stock_last_buy_price
                    phase_stock_sell_num = self.stock_sell_num
                    phase_sell_list = self.sell_list.copy()
                    phase_stock_last_sell_time = self.stock_last_sell_time
                    phase_stock_last_sell_price = self.stock_last_sell_price
                    phase_stock_buy_succ_num = self.stock_buy_succ_num
                    # 获取阶段收益
                    phase_general_asset = self.get_phase_general_asset(phase_start_index, phase_end_index,
                                                                       phase_buy_ma_len, phase_sell_ma_len)
                    # 记录最大总收益
                    if max_phase_general_asset < phase_general_asset:
                        max_phase_general_asset = phase_general_asset
                        # 记录money, stock_num以及阶段ma长度
                        max_phase_money = self.money
                        max_phase_stock_num = self.stock_num
                        max_phase_stock_buy_num = self.stock_buy_num
                        max_phase_buy_list = self.buy_list.copy()
                        max_phase_stock_last_buy_time = self.stock_last_buy_time
                        max_phase_stock_last_buy_price = self.stock_last_buy_price
                        max_phase_stock_sell_num = self.stock_sell_num
                        max_phase_sell_list = self.sell_list.copy()
                        max_phase_stock_last_sell_time = self.stock_last_sell_time
                        max_phase_stock_last_sell_price = self.stock_last_sell_price
                        max_phase_stock_buy_succ_num = self.stock_buy_succ_num
                        best_phase_buy_ma_len = phase_buy_ma_len
                        best_phase_sell_ma_len = phase_sell_ma_len

                    # 回退到初始状态
                    self.money = phase_money
                    self.stock_num = phase_stock_num
                    self.stock_buy_num = phase_stock_buy_num
                    self.buy_list = phase_buy_list.copy()
                    self.stock_last_buy_time = phase_stock_last_buy_time
                    self.stock_last_buy_price = phase_stock_last_buy_price
                    self.stock_sell_num = phase_stock_sell_num
                    self.sell_list = phase_sell_list.copy()
                    self.stock_last_sell_time = phase_stock_last_sell_time
                    self.stock_last_sell_price = phase_stock_last_sell_price
                    self.stock_buy_succ_num = phase_stock_buy_succ_num

        # 假设长期均线L向下，买入均线M大于卖出均线N（慢买快卖）, 且L > M > N, 根据这个假设便利计算最高收益率对应的各均线值
        else:  # MA_DIR_DOWN == ma_dir:
            # 遍历买入卖出均线组合
            for phase_buy_ma_len in range(2, long_ma_len):
                for phase_sell_ma_len in range(2, phase_buy_ma_len):
                    # 保存操作前的初始金额和股票数以便回退操作
                    phase_money = self.money
                    phase_stock_num = self.stock_num
                    phase_stock_buy_num = self.stock_buy_num
                    phase_buy_list = self.buy_list.copy()
                    phase_stock_last_buy_time = self.stock_last_buy_time
                    phase_stock_last_buy_price = self.stock_last_buy_price
                    phase_stock_sell_num = self.stock_sell_num
                    phase_sell_list = self.sell_list.copy()
                    phase_stock_last_sell_time = self.stock_last_sell_time
                    phase_stock_last_sell_price = self.stock_last_sell_price
                    phase_stock_buy_succ_num = self.stock_buy_succ_num
                    # 获取阶段收益
                    phase_general_asset = self.get_phase_general_asset(phase_start_index, phase_end_index,
                                                                       phase_buy_ma_len, phase_sell_ma_len)
                    # 记录最大总收益
                    if max_phase_general_asset < phase_general_asset:
                        max_phase_general_asset = phase_general_asset
                        # 记录money, stock_num以及阶段ma长度
                        max_phase_money = self.money
                        max_phase_stock_num = self.stock_num
                        max_phase_stock_buy_num = self.stock_buy_num
                        max_phase_buy_list = self.buy_list.copy()
                        max_phase_stock_last_buy_time = self.stock_last_buy_time
                        max_phase_stock_last_buy_price = self.stock_last_buy_price
                        max_phase_stock_sell_num = self.stock_sell_num
                        max_phase_sell_list = self.sell_list.copy()
                        max_phase_stock_last_sell_time = self.stock_last_sell_time
                        max_phase_stock_last_sell_price = self.stock_last_sell_price
                        max_phase_stock_buy_succ_num = self.stock_buy_succ_num
                        best_phase_buy_ma_len = phase_buy_ma_len
                        best_phase_sell_ma_len = phase_sell_ma_len

                    # 回退到初始状态
                    self.money = phase_money
                    self.stock_num = phase_stock_num
                    self.stock_buy_num = phase_stock_buy_num
                    self.buy_list = phase_buy_list.copy()
                    self.stock_last_buy_time = phase_stock_last_buy_time
                    self.stock_last_buy_price = phase_stock_last_buy_price
                    self.stock_sell_num = phase_stock_sell_num
                    self.sell_list = phase_sell_list.copy()
                    self.stock_last_sell_time = phase_stock_last_sell_time
                    self.stock_last_sell_price = phase_stock_last_sell_price
                    self.stock_buy_succ_num = phase_stock_buy_succ_num

        # 遍历完毕后保存最高总收益状态
        self.money = max_phase_money
        self.stock_num = max_phase_stock_num
        self.stock_buy_num = max_phase_stock_buy_num
        self.buy_list = max_phase_buy_list.copy()
        self.stock_last_buy_time = max_phase_stock_last_buy_time
        self.stock_last_buy_price = max_phase_stock_last_buy_price
        self.stock_sell_num = max_phase_stock_sell_num
        self.sell_list = max_phase_sell_list.copy()
        self.stock_last_sell_time = max_phase_stock_last_sell_time
        self.stock_last_sell_price = max_phase_stock_last_sell_price
        self.stock_buy_succ_num = max_phase_stock_buy_succ_num
        self.phase_index_ma_len_list.append(PhaseMaLenItem(phase_start_index, phase_end_index,
                                                           best_phase_buy_ma_len, best_phase_sell_ma_len))

    def run_trade_strategy(self):
        if 0 >= self.money:
            print('error init money %0.3f' % self.money)
            return

        # 按MA均线判断收益率, 从10天均线开始计算
        for long_ma_len in range(10, self.max_long_ma_len+1):
            self.long_ma_list = []
            self.get_ma_list(self.long_ma_list, long_ma_len)
            ma_dir = MA_DIR_INIT  # 0 初始化 1 代表上升  2代表下降
            phase_start_index = 0
            # 计算转折点阶段总收益
            long_ma_list_len = len(self.long_ma_list)
            for i in range(long_ma_list_len):
                j = i + 1
                if j < long_ma_list_len:
                    if MA_DIR_INIT == ma_dir:
                        if self.long_ma_list[i].price == self.long_ma_list[j].price:
                            continue
                        elif self.long_ma_list[i].price < self.long_ma_list[j].price:
                            ma_dir = MA_DIR_UP
                        else:
                            ma_dir = MA_DIR_DOWN
                    # 上升转下降 或者 下降转上升 情况下要计算阶段总收益
                    if ((self.long_ma_list[i].price > self.long_ma_list[j].price) and (MA_DIR_UP == ma_dir)) \
                            or ((self.long_ma_list[i].price < self.long_ma_list[j].price) and (MA_DIR_DOWN == ma_dir)):
                        # 计算上一段的总收益
                        self.get_max_phase_general_asset(phase_start_index, j, long_ma_len, ma_dir)
                        phase_start_index = j
                        # 更改方向
                        if MA_DIR_UP == ma_dir:
                            ma_dir = MA_DIR_DOWN
                        else:
                            ma_dir = MA_DIR_UP
                    else:   # 非转折不计算
                        continue
            # 计算最后一段
            if phase_start_index < (long_ma_list_len - 1):
                self.get_max_phase_general_asset(phase_start_index, long_ma_list_len - 1, long_ma_len, ma_dir)

        print(' ', end='\n')
        for i in range(len(self.phase_index_ma_len_list)):
            print('phase_start_index = %d,phase_end_index = %d,best_phase_buy_ma_len = %d,best_phase_sell_ma_len = %d'
                  % (self.phase_index_ma_len_list[i].phase_start_index,
                     self.phase_index_ma_len_list[i].phase_end_index,
                     self.phase_index_ma_len_list[i].phase_buy_ma_len,
                     self.phase_index_ma_len_list[i].phase_sell_ma_len))
            print(' ', end='\n')
            print('Best SmartMATradeStrategy for stock_code = %s:' % self.stock_code)
            print('money = %.3f, stork_num = %d, general_asset = %.3f'
                  % (self.money, self.stock_num, self.general_asset))
            print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d'
                  % (self.stock_buy_num, self.stock_sell_num, self.stock_buy_succ_num))
            print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (self.gain_ratio, self.succ_ratio))


########################################################################################################################
# 计算最佳均线交易
########################################################################################################################
# 验证在不同均线趋势变化时买入卖出算法的正确性以及盈利值, 按1W RMB，按收盘价买入卖出，计算最优ma len
def calc_best_ma_trade_strategy(stock_code, start, end, max_buy_ma_len, max_sell_ma_len, init_money):
    # 初始化进度条
    total = max_buy_ma_len * max_sell_ma_len
    progress = 0
    widgets = ['Progress: ', pb.Percentage(), ' ', pb.Bar('#'), ' ', pb.Timer(), ' ', pb.ETA(), ' ']
    pbar = pb.ProgressBar(widgets=widgets, maxval=total).start()
    # 初始化股票数据
    stock_raw_data_obj = GetStockRawData(stock_code, start, end)

    max_general_asset = 0
    max_stock_code = 0
    max_money = 0
    max_stock_num = 0
    max_stock_buy_num = 0
    max_stock_sell_num = 0
    max_stock_buy_succ_num = 0
    max_gain_ratio = 0
    max_succ_ratio = 0
    best_buy_ma_len = 0
    best_sell_ma_len = 0

    # 画图列表
    # price_list = []
    buy_list = []
    sell_list = []

    '''
    for i in range(1, max_buy_ma_len):
        for j in range(1, max_sell_ma_len):
            trade_strategy_obj = MATradeStrategy(stock_raw_data_obj, init_money, i, j)
            trade_strategy_obj.run_trade_strategy()
            if max_general_asset < trade_strategy_obj.general_asset:
                max_stock_code = trade_strategy_obj.stock_code
                max_money = trade_strategy_obj.money
                max_stock_num = trade_strategy_obj.stock_num
                max_stock_buy_num = trade_strategy_obj.stock_buy_num
                max_stock_sell_num = trade_strategy_obj.stock_sell_num
                max_stock_buy_succ_num = trade_strategy_obj.stock_buy_succ_num
                max_general_asset = trade_strategy_obj.general_asset
                max_gain_ratio = trade_strategy_obj.gain_ratio
                max_succ_ratio = trade_strategy_obj.succ_ratio
                # price_list = trade_strategy_obj.price_list
                buy_list = trade_strategy_obj.buy_list
                sell_list = trade_strategy_obj.sell_list
                best_buy_ma_len = trade_strategy_obj.buy_ma_len
                best_sell_ma_len = trade_strategy_obj.sell_ma_len
            # 更新进度
            progress += 1
            pbar.update(progress)
            # 删除对象释放内存
            del trade_strategy_obj
    '''

    # 计算smart ma
    trade_strategy_obj = SmartMATradeStrategy(stock_raw_data_obj, init_money, max_buy_ma_len)
    trade_strategy_obj.run_trade_strategy()
    if max_general_asset < trade_strategy_obj.general_asset:
        max_stock_code = trade_strategy_obj.stock_code
        max_money = trade_strategy_obj.money
        max_stock_num = trade_strategy_obj.stock_num
        max_stock_buy_num = trade_strategy_obj.stock_buy_num
        max_stock_sell_num = trade_strategy_obj.stock_sell_num
        max_stock_buy_succ_num = trade_strategy_obj.stock_buy_succ_num
        max_general_asset = trade_strategy_obj.general_asset
        max_gain_ratio = trade_strategy_obj.gain_ratio
        max_succ_ratio = trade_strategy_obj.succ_ratio
        # price_list = trade_strategy_obj.price_list
        buy_list = trade_strategy_obj.buy_list
        sell_list = trade_strategy_obj.sell_list
    # 更新进度
    progress += 1
    pbar.update(progress)
    # 删除对象释放内存
    del trade_strategy_obj

    del pbar

    print(' ', end='\n')
    print('Best MATradeStrategy for stock_code = %s:' % max_stock_code)
    print('money = %.3f, stork_num = %d, general_asset = %.3f' % (max_money, max_stock_num, max_general_asset))
    print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d' % (max_stock_buy_num,
                                                                                max_stock_sell_num,
                                                                                max_stock_buy_succ_num))
    print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (max_gain_ratio, max_succ_ratio))
    print('best_buy_ma_len = %d, best_sell_ma_len = %d, start = %s, end = %s' % (best_buy_ma_len, best_sell_ma_len,
                                                                                 start,
                                                                                 end))

    print('deal list:')
    buy_list_len = len(buy_list)
    sell_list_len = len(sell_list)
    for i in range(buy_list_len):
        # print('BUY : date = %s, price = %.03f' % (buy_list[i].time, buy_list[i].price))
        if i < sell_list_len:
            # print('SELL: date = %s, price = %.03f' % (sell_list[i].time, sell_list[i].price))
            pass


########################################################################################################################
# MACD交易公共函数
########################################################################################################################
# 计算当前EMA
def calc_cur_ema(ema_len, last_ema, cur_close_price):
    return last_ema + ((cur_close_price - last_ema) * 2 / (ema_len + 1))


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
########################################################################################################################
# MACD标准算法交易策略，按金叉死叉买入卖出
# 1.DIFF向上突破DEA，买入信号。
# 2.DIFF向下跌破DEA，卖出信号。
# 3.DEA线与K线发生背离，行情反转信号。
########################################################################################################################
class MACDStandardTradeStrategy(BaseTradeStrategy):
    def __init__(self, stock_raw_data_obj, init_money):
        BaseTradeStrategy.__init__(self, stock_raw_data_obj, init_money)
        self.ema12_list = []
        self.ema26_list = []
        self.diff_list = []
        self.dea_list = []
        self.bar_list = []

        self.calc_ema12_list()
        self.calc_ema26_list()
        self.calc_diff_list()
        self.calc_dea_list()
        self.calc_bar_list()

    # 计算EMA12列表
    def calc_ema12_list(self):
        self.ema12_list.clear()
        data_len = len(self.data)
        if 0 >= data_len:
            return
        # 按前一日收盘价计算, 要改
        self.ema12_list.append(TimePriceItem(get_data_time(self.data, 0), get_data_price(self.data, 0, COL_CLOSE)))
        for i in range(1, data_len):
            last_ema12 = self.ema12_list[i-1].price
            cur_ema12 = calc_cur_ema(12, last_ema12, get_data_price(self.data, i, COL_CLOSE))
            self.ema12_list.append(TimePriceItem(get_data_time(self.data, i), cur_ema12))

    def calc_ema26_list(self):
        self.ema26_list.clear()
        data_len = len(self.data)
        if 0 >= data_len:
            return
        # 按前一日收盘价计算, 要改
        self.ema26_list.append(TimePriceItem(get_data_time(self.data, 0), get_data_price(self.data, 0, COL_CLOSE)))
        for i in range(1, data_len):
            last_ema26 = self.ema26_list[i-1].price
            cur_ema26 = calc_cur_ema(26, last_ema26, get_data_price(self.data, i, COL_CLOSE))
            self.ema26_list.append(TimePriceItem(get_data_time(self.data, i), cur_ema26))

    def calc_diff_list(self):
        list_len = len(self.ema12_list)
        for i in range(list_len):
            self.diff_list.append(TimePriceItem(self.ema12_list[i].time,
                                                self.ema12_list[i].price - self.ema26_list[i].price))

    def calc_dea_list(self):
        list_len = len(self.diff_list)
        if 0 >= list_len:
            return
        self.dea_list.append(TimePriceItem(self.diff_list[0].time, 0.000))
        for i in range(1, list_len):
            last_dea = self.dea_list[i-1].price
            cur_dea = last_dea*8/10 + self.diff_list[i].price*2/10
            self.dea_list.append(TimePriceItem(self.diff_list[i].time, cur_dea))

    def calc_bar_list(self):
        list_len = len(self.diff_list)
        for i in range(list_len):
            self.bar_list.append(TimePriceItem(self.diff_list[i].time,
                                               2*(self.diff_list[i].price - self.dea_list[i].price)))

    def print_macd(self):
        for i in range(len(self.ema12_list)):
            print("%s %0.3f %0.3f %0.3f %0.3f %0.3f" % (self.ema12_list[i].time, self.ema12_list[i].price,
                                                        self.ema26_list[i].price, self.diff_list[i].price,
                                                        self.dea_list[i].price, self.bar_list[i].price))

    def run_trade_strategy(self):
        # diff_list和sell_ma_list时一样的长度
        diff_list_len = len(self.diff_list)
        dea_list_len = len(self.dea_list)
        if (0 >= self.money) or (0 >= diff_list_len) or (0 >= dea_list_len) or (diff_list_len != dea_list_len):
            print('MACDStandardTradeStrategy.run_trade_strategy error ma list len %d or init money %0.3f'
                  % (diff_list_len, self.money))
            return

        # 按MA均线判断收益率
        for i in range(diff_list_len):
            j = i + 1
            if j < diff_list_len:
                # 趋势向上买入股票, DIFF向上穿过DEA
                if (self.diff_list[i].price < self.diff_list[j].price) \
                        and (self.diff_list[j].price > self.dea_list[j].price):
                    # 买入股票
                    self.buy_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                # 趋势向下卖出股票, DIFF向下穿过DEA
                if (self.diff_list[i].price > self.diff_list[j].price) \
                        and (self.diff_list[j].price < self.dea_list[j].price):
                    # 卖出股票
                    self.sell_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))

        # print(' ', end='\n')
        # print('MACDStandardTradeStrategy: ')
        self.print_gain_ratio(diff_list_len)


########################################################################################################################
# MACD Diff算法交易策略，DIFF向上就买入, DIFF向下就卖出
########################################################################################################################
class MACDDiffTradeStrategy(MACDStandardTradeStrategy):
    def __init__(self, stock_raw_data_obj, init_money):
        MACDStandardTradeStrategy.__init__(self, stock_raw_data_obj, init_money)

    def run_trade_strategy(self):
        # diff_list和sell_ma_list时一样的长度
        diff_list_len = len(self.diff_list)
        if (0 >= self.money) or (0 >= diff_list_len):
            print('MACDDiffTradeStrategy.run_trade_strategy error ma list len %d or init money %0.3f'
                  % (diff_list_len, self.money))
            return

        # 按DIFF均线判断收益率
        for i in range(diff_list_len):
            j = i + 1
            if j < diff_list_len:
                # 趋势向上买入股票, DIFF向上穿过DEA
                if self.diff_list[i].price < self.diff_list[j].price:
                    # 买入股票
                    self.buy_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))
                # 趋势向下卖出股票, DIFF向下穿过DEA
                if self.diff_list[i].price > self.diff_list[j].price:
                    # 卖出股票
                    self.sell_stock(get_data_time(self.data, j), get_data_price(self.data, j, COL_CLOSE))

        # print(' ', end='\n\n')
        # print('MACDDiffTradeStrategy: ')
        self.print_gain_ratio(diff_list_len)


########################################################################################################################
# 计算最佳均线交易
########################################################################################################################
# 验证在不同均线趋势变化时买入卖出算法的正确性以及盈利值, 按1W RMB，按收盘价买入卖出，计算最优ma len
def calc_best_macd_trade_strategy(stock_code, start, end, init_money):
    # 初始化进度条
    total = 2
    progress = 0
    widgets = ['Progress: ', pb.Percentage(), ' ', pb.Bar('#'), ' ', pb.Timer(), ' ', pb.ETA(), ' ']
    pbar = pb.ProgressBar(widgets=widgets, maxval=total).start()
    # 初始化股票数据
    stock_raw_data_obj = GetStockRawData(stock_code, start, end)

    # 画图列表
    # price_list = []

    # 计算标准MACD策略收益率
    trade_strategy_obj = MACDStandardTradeStrategy(stock_raw_data_obj, init_money)
    trade_strategy_obj.run_trade_strategy()
    # 记录最大收益率
    max_general_asset = trade_strategy_obj.general_asset
    max_stock_code = trade_strategy_obj.stock_code
    max_money = trade_strategy_obj.money
    max_stock_num = trade_strategy_obj.stock_num
    max_stock_buy_num = trade_strategy_obj.stock_buy_num
    max_stock_sell_num = trade_strategy_obj.stock_sell_num
    max_stock_buy_succ_num = trade_strategy_obj.stock_buy_succ_num
    max_gain_ratio = trade_strategy_obj.gain_ratio
    max_succ_ratio = trade_strategy_obj.succ_ratio
    # price_list = trade_strategy_obj.price_list
    buy_list = trade_strategy_obj.buy_list
    sell_list = trade_strategy_obj.sell_list
    # 删除对象释放内存
    del trade_strategy_obj

    # 更新进度
    progress += 1
    pbar.update(progress)

    # 计算MACD DIFF策略收益率
    trade_strategy_obj = MACDDiffTradeStrategy(stock_raw_data_obj, init_money)
    trade_strategy_obj.run_trade_strategy()
    flag = 0

    # 记录最大收益率
    if max_general_asset < trade_strategy_obj.general_asset:
        flag = 1
        max_general_asset = trade_strategy_obj.general_asset
        max_stock_code = trade_strategy_obj.stock_code
        max_money = trade_strategy_obj.money
        max_stock_num = trade_strategy_obj.stock_num
        max_stock_buy_num = trade_strategy_obj.stock_buy_num
        max_stock_sell_num = trade_strategy_obj.stock_sell_num
        max_stock_buy_succ_num = trade_strategy_obj.stock_buy_succ_num
        max_gain_ratio = trade_strategy_obj.gain_ratio
        max_succ_ratio = trade_strategy_obj.succ_ratio
        # price_list = trade_strategy_obj.price_list
        buy_list = trade_strategy_obj.buy_list
        sell_list = trade_strategy_obj.sell_list
    # 删除对象释放内存
    del trade_strategy_obj

    # 更新进度
    progress += 1
    pbar.update(progress)

    # 删除对象
    del pbar

    print(' ', end='\n\n')
    if 1 == flag:
        print('MACDDiffTradeStrategy is the best, stock_code = %s' % max_stock_code)
    else:
        print('MACDStandardTradeStrategy is the best, stock_code = %s' % max_stock_code)
    print('money = %.3f, stork_num = %d, general_asset = %.3f' % (max_money, max_stock_num, max_general_asset))
    print('stock_buy_num = %d, stock_sell_num = %d, stock_buy_succ_num = %d' % (max_stock_buy_num,
                                                                                max_stock_sell_num,
                                                                                max_stock_buy_succ_num))
    print('gain_ratio = %.2f%%, succ_ratio = %.2f%%' % (max_gain_ratio, max_succ_ratio))

    print('deal list:')
    buy_list_len = len(buy_list)
    sell_list_len = len(sell_list)
    for i in range(buy_list_len):
        # print('BUY : date = %s, price = %.03f' % (buy_list[i].time, buy_list[i].price))
        if i < sell_list_len:
            # print('SELL: date = %s, price = %.03f' % (sell_list[i].time, sell_list[i].price))
            pass





