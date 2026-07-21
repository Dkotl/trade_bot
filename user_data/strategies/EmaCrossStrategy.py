from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas_ta as ta


class EmaCrossStrategy(IStrategy):
    leverage = 5.0
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'

    # Защитный стоп-лосс (2%)
    stoploss = -0.012

    # Тейк-профит отключаем (ставим огромным), так как цену будет вести Трейлинг-стоп
    minimal_roi = {"0": 10.0}

    # --- НАСТРОЙКА УМНОГО ТРЕЙЛИНГ-СТОПА ---
    trailing_stop = True
    # Начинаем активировать трейлинг, как только сделка выходит в +0.8% прибыли
    trailing_stop_positive = 0.025
    # Стоп-лосс будет следовать за пиком цены на расстоянии 1.2% от нее
    trailing_stop_positive_offset = 0.035
    # Трейлинг включится ТОЛЬКО тогда, когда цена достигнет offset (+1.2%)
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['ema_fast'] = ta.ema(dataframe['close'], length=9)
        dataframe['ema_slow'] = ta.ema(dataframe['close'], length=21)
        dataframe['ema_trend'] = ta.ema(dataframe['close'], length=200)
        dataframe['adx'] = ta.adx(
            dataframe['high'], dataframe['low'], dataframe['close'])['ADX_14']
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Подняли фильтр силы тренда до 25
        strong_trend = dataframe['adx'] > 25

        # LONG
        dataframe.loc[
            (dataframe['ema_fast'] > dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) <= dataframe['ema_slow'].shift(1)) &
            (dataframe['close'] > dataframe['ema_trend']) &
            strong_trend,
            'enter_long'
        ] = 1

        # SHORT
        dataframe.loc[
            (dataframe['ema_fast'] < dataframe['ema_slow']) &
            (dataframe['ema_fast'].shift(1) >= dataframe['ema_slow'].shift(1)) &
            (dataframe['close'] < dataframe['ema_trend']) &
            strong_trend,
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # МЫ БОЛЬШЕ НЕ ВЫХОДИМ ПО СИГНАЛАМ ЕМА. Выход только по стопу или трейлингу!
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
