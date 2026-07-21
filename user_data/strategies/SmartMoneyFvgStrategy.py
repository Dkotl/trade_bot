from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np


class SmartMoneyFvgStrategy(IStrategy):
    leverage = 5.0
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'

    # Короткий стоп-лосс (базовый 1.2%, но custom_info перепишет его точнее)
    stoploss = -0.012
    # Целимся в соотношение 1:3.5 (забираем хорошую прибыль)
    minimal_roi = {"0": 0.042}

    # Включаем встроенный трейлинг, чтобы защищать прибыль, если цена не дошла до тейка
    trailing_stop = True
    trailing_stop_positive = 0.015
    trailing_stop_positive_offset = 0.022
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Расчет FVG (Дисбаланса) по 3-м свечам
        # Сдвигаем значения High и Low на 1 и 2 свечи назад
        dataframe['prev_high'] = dataframe['high'].shift(2)
        dataframe['next_low'] = dataframe['low']

        dataframe['prev_low'] = dataframe['low'].shift(2)
        dataframe['next_high'] = dataframe['high']

        # Расчет уровня Фибоначчи 0.618 для тела сигнальной свечи (индекс .shift(1))
        # Фиба строится от High до Low сигнальной свечи
        dataframe['fibo_618_long'] = dataframe['high'].shift(
            1) - (dataframe['high'].shift(1) - dataframe['low'].shift(1)) * 0.618
        dataframe['fibo_618_short'] = dataframe['low'].shift(
            1) + (dataframe['high'].shift(1) - dataframe['low'].shift(1)) * 0.618

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Условие Бычьего FVG: High первой свечи ниже Low третьей свечи
        # Дополнительно проверяем, что сигнальная свечь была крупной (тело > 0.3%)
        body_size = abs(dataframe['close'].shift(
            1) - dataframe['open'].shift(1)) / dataframe['open'].shift(1)

        fvg_long_condition = (
            dataframe['next_low'] > dataframe['prev_high']) & (body_size > 0.003)
        fvg_short_condition = (
            dataframe['next_high'] < dataframe['prev_low']) & (body_size > 0.003)

        # LONG: Цена вернулась (скорректировалась) к уровню 0.618 бычьего имбаланса
        dataframe.loc[
            fvg_long_condition &
            (dataframe['low'] <= dataframe['fibo_618_long']) &
            (dataframe['close'] > dataframe['fibo_618_long']),
            'enter_long'
        ] = 1

        # SHORT: Цена скорректировалась вверх к уровню 0.618 медвежьего имбаланса
        dataframe.loc[
            fvg_short_condition &
            (dataframe['high'] >= dataframe['fibo_618_short']) &
            (dataframe['close'] < dataframe['fibo_618_short']),
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe
