import pandas_ta as ta
from pandas import DataFrame
from freqtrade.strategy import IStrategy, IntParameter, DecimalParameter

class EmaCrossStrategy(IStrategy):
    # УДАЛЕНО leverage = 5.0 во избежание сбоев вызова 'float' object is not callable
    
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'
    minimal_roi = {"0": 10.0}
    
    # Жесткая заглушка стоп-лосса, обязательная для инициализации ядра бота
    stoploss = -0.10  
    use_custom_stoploss = True

    # --- ПАРАМЕТРЫ ДЛЯ ОПТИМИЗАЦИИ (HYPEROPT) ---
    
    # Оптимизация стоп-лосса (от -5% до -0.5%) под уникальным именем
    hp_stoploss = DecimalParameter(-0.05, -0.005, default=-0.012, decimals=3, space='sell', load=True)

    # Настройки встроенного трейлинг-стопа
    trailing_stop = True
    trailing_only_offset_is_reached = True
    
    # Расстояние удержания трейлинга (от 0.5% до 4.0%)
    trailing_stop_positive = DecimalParameter(0.005, 0.04, default=0.025, decimals=3, space='sell', load=True)
    # Триггер активации трейлинга (от 0.8% до 5.0%)
    trailing_stop_positive_offset = DecimalParameter(0.008, 0.05, default=0.035, decimals=3, space='sell', load=True)

    # Настройки периодов индикаторов (пространство 'buy')
    ema_fast_len = IntParameter(5, 15, default=9, space='buy', load=True)
    ema_slow_len = IntParameter(16, 40, default=21, space='buy', load=True)
    ema_trend_len = IntParameter(100, 300, default=200, space='buy', load=True)
    
    adx_len = IntParameter(10, 25, default=14, space='buy', load=True)
    adx_min = IntParameter(15, 40, default=25, space='buy', load=True)

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Предварительный расчет сетки Быстрых EMA
        for length in range(self.ema_fast_len.low, self.ema_fast_len.high + 1):
            dataframe[f'ema_fast_{length}'] = ta.ema(dataframe['close'], length=length)
            
        # Предварительный расчет сетки Медленных EMA    
        for length in range(self.ema_slow_len.low, self.ema_slow_len.high + 1):
            dataframe[f'ema_slow_{length}'] = ta.ema(dataframe['close'], length=length)
            
        # Предварительный расчет Тренда с шагом 10 для колоссальной экономии ОЗУ
        for length in range(self.ema_trend_len.low, self.ema_trend_len.high + 1):
            if length % 10 == 0 or length == self.ema_trend_len.low or length == self.ema_trend_len.high:
                dataframe[f'ema_trend_{length}'] = ta.ema(dataframe['close'], length=length)

        # Предварительный расчет сетки ADX
        for length in range(self.adx_len.low, self.adx_len.high + 1):
            dataframe[f'adx_{length}'] = ta.adx(
                dataframe['high'], dataframe['low'], dataframe['close'], length=length
            )[f'ADX_{length}']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Получаем текущие тестируемые значения параметров на данной эпохе
        fast_len = self.ema_fast_len.value
        slow_len = self.ema_slow_len.value
        adx_len_val = self.adx_len.value
        
        # Защита от отсутствия точного шага деления на 10 для ema_trend
        trend_len = self.ema_trend_len.value
        if f'ema_trend_{trend_len}' not in dataframe.columns:
            # Округляем до ближайшего существующего шага кратного 10
            trend_len = int(round(trend_len / 10.0) * 10)

        ema_fast_col = f'ema_fast_{fast_len}'
        ema_slow_col = f'ema_slow_{slow_len}'
        ema_trend_col = f'ema_trend_{trend_len}'
        adx_col = f'adx_{adx_len_val}'

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

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, **kwargs) -> float:
        # Динамически передаем подобранный стоп-лосс из параметров Hyperopt
        return self.hp_stoploss.value
