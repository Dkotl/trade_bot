import pandas_ta as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy
# Импортируем типы параметров для Hyperopt
from freqtrade.strategy import IntParameter, DecimalParameter


class EmaCrossStrategy(IStrategy):
    leverage = 5.0
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'
    minimal_roi = {"0": 10.0}

    # --- ПАРАМЕТРЫ ДЛЯ ОПТИМИЗАЦИИ (HYPEROPT) ---
    
    # 1. Стоп-лосс (оптимизация от -5% до -0.5%)
    stoploss = DecimalParameter(-0.05, -0.005, default=-0.012, decimals=3, space='sell', load=True)

    # 2. Настройки умного трейлинг-стопа
    trailing_stop = True
    trailing_only_offset_is_reached = True
    
    # Расстояние, на котором стоп следует за ценой (от 0.5% до 4.0%)
    trailing_stop_positive = DecimalParameter(0.005, 0.04, default=0.025, decimals=3, space='sell', load=True)
    # Триггер включения трейлинга (от 0.8% до 5.0%)
    trailing_stop_positive_offset = DecimalParameter(0.008, 0.05, default=0.035, decimals=3, space='sell', load=True)

    # 3. Настройки индикаторов (Периоды EMA и ADX)
    ema_fast_len = IntParameter(5, 15, default=9, space='buy', load=True)
    ema_slow_len = IntParameter(16, 40, default=21, space='buy', load=True)
    ema_trend_len = IntParameter(100, 300, default=200, space='buy', load=True)
    
    adx_len = IntParameter(10, 25, default=14, space='buy', load=True)
    adx_min = IntParameter(15, 40, default=25, space='buy', load=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Считаем индикаторы для максимально возможных диапазонов, чтобы не ломать Hyperopt
        # Вычисляем сетку EMA от минимального до максимального значения
        for length in range(self.ema_fast_len.low, self.ema_fast_len.high + 1):
            dataframe[f'ema_fast_{length}'] = ta.ema(dataframe['close'], length=length)
            
        for length in range(self.ema_slow_len.low, self.ema_slow_len.high + 1):
            dataframe[f'ema_slow_{length}'] = ta.ema(dataframe['close'], length=length)
            
        for length in range(self.ema_trend_len.low, self.ema_trend_len.high + 1, 10): # Шаг 10 для экономии памяти
            dataframe[f'ema_trend_{length}'] = ta.ema(dataframe['close'], length=length)

        for length in range(self.adx_len.low, self.adx_len.high + 1):
            dataframe[f'adx_{length}'] = ta.adx(
                dataframe['high'], dataframe['low'], dataframe['close'], length=length
            )[f'ADX_{length}']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Динамически получаем имена колонок на основе текущих параметров шага оптимизации
        ema_fast_col = f'ema_fast_{self.ema_fast_len.value}'
        ema_slow_col = f'ema_slow_{self.ema_slow_len.value}'
        ema_trend_col = f'ema_trend_{self.ema_trend_len.value}'
        adx_col = f'adx_{self.adx_len.value}'

        # Фильтр силы тренда
        strong_trend = dataframe[adx_col] > self.adx_min.value

        # LONG
        dataframe.loc[
            (dataframe[ema_fast_col] > dataframe[ema_slow_col]) &
            (dataframe[ema_fast_col].shift(1) <= dataframe[ema_slow_col].shift(1)) &
            (dataframe['close'] > dataframe[ema_trend_col]) &
            strong_trend,
            'enter_long'
        ] = 1

        # SHORT
        dataframe.loc[
            (dataframe[ema_fast_col] < dataframe[ema_slow_col]) &
            (dataframe[ema_fast_col].shift(1) >= dataframe[ema_slow_col].shift(1)) &
            (dataframe['close'] < dataframe[ema_trend_col]) &
            strong_trend,
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
