from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas_ta as ta


class BollingerRsiScalper(IStrategy):
    leverage = 5.0
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'

    # Очень короткий защитный стоп-лосс (1.0%), так как мы ловим именно разворот точки
    stoploss = -0.01

    # Фиксированный тейк-профит на уровне 2% (быстро забрали прибыль во флете и вышли)
    minimal_roi = {
        "0": 0.02
    }

    # Отключаем трейлинг, так как в контр-тренде нужно забирать фиксированный математический отскок
    trailing_stop = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Расчет стандартных Полос Боллинджера (период 20, отклонение 2)
        bbands = ta.bbands(dataframe['close'], length=20, std=2.0)
        dataframe['bb_lower'] = bbands['BBL_20_2.0']
        dataframe['bb_middle'] = bbands['BBM_20_2.0']
        dataframe['bb_upper'] = bbands['BBU_20_2.0']

        # 2. Индикатор RSI для определения зон перекупленности/перепроданности
        dataframe['rsi'] = ta.rsi(dataframe['close'], length=14)

        # 3. Индикатор ADX для фильтрации сильных трендов (защита от пампов/дампов)
        dataframe['adx'] = ta.adx(
            dataframe['high'], dataframe['low'], dataframe['close'])['ADX_14']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Фильтр: заходим только если на рынке НЕТ сильного направленного тренда
        flat_market = dataframe['adx'] < 25

        # LONG: Цена пробила нижнюю ленту И RSI в зоне перепроданности (< 25)
        dataframe.loc[
            (dataframe['close'] < dataframe['bb_lower']) &
            (dataframe['rsi'] < 25) &
            flat_market,
            'enter_long'
        ] = 1

        # SHORT: Цена пробила верхнюю ленту И RSI в зоне перекупленности (> 75)
        dataframe.loc[
            (dataframe['close'] > dataframe['bb_upper']) &
            (dataframe['rsi'] > 75) &
            flat_market,
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        # Выход по сигналам не нужен — закрываем позиции строго по фиксированным целям minimal_roi и стоп-лоссу
        return dataframe
