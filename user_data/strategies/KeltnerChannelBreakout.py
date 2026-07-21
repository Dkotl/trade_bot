from freqtrade.strategy import IStrategy
from pandas import DataFrame
import pandas_ta as ta


class KeltnerChannelBreakout(IStrategy):
    startup_candle_count = 30
    leverage = 5.0
    order_types = {
        'entry': 'limit', 'exit': 'limit', 'emergency_exit': 'market',
        'force_entry': 'market', 'force_exit': 'market', 'stoploss': 'market',
        'stoploss_on_exchange': False, 'leverage': 'limit'
    }

    timeframe = '5m'

    # Первоначальный защитный стоп-лосс (1.5%)
    stoploss = -0.015

    # Тейк-профит ставим большим, так как позицию будет сопровождать трейлинг
    minimal_roi = {"0": 10.0}

    # --- НАСТРОЙКА СКОЛЬЗЯЩЕГО ТРЕЙЛИНГ-СТОПА ---
    trailing_stop = True
    # Активируем трейлинг, как только цена дает +1.5% чистой прибыли
    trailing_stop_positive = 0.015
    # Стоп-лосс идет за ценой на расстоянии 1.2% от пика
    trailing_stop_positive_offset = 0.025
    trailing_only_offset_is_reached = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Считаем среднюю линию как EMA 20
        dataframe['kc_middle'] = ta.ema(dataframe['close'], length=20)

        # 2. Считаем индикатор ATR за 20 свечей для определения волатильности
        dataframe['atr'] = ta.atr(
            dataframe['high'], dataframe['low'], dataframe['close'], length=20)

        # 3. Строим границы канала (Множитель = 2.0)
        dataframe['kc_upper'] = dataframe['kc_middle'] + \
            (dataframe['atr'] * 2.0)
        dataframe['kc_lower'] = dataframe['kc_middle'] - \
            (dataframe['atr'] * 2.0)

        # 4. Фильтр объема (скользящая средняя за 20 свечей)
        dataframe['volume_mean'] = dataframe['volume'].rolling(
            window=20).mean()

        # 5. Индикатор ADX для подтверждения силы тренда
        dataframe['adx'] = ta.adx(
            dataframe['high'], dataframe['low'], dataframe['close'])['ADX_14']

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Общие условия: в рынок зашли объемы (на 30% выше среднего) + тренд оживает (ADX > 20)
        volume_filter = dataframe['volume'] > (dataframe['volume_mean'] * 1.3)
        trend_filter = dataframe['adx'] > 20

        # LONG: Свеча закрылась ВЫШЕ верхней границы канала Кельтнера + фильтры
        dataframe.loc[
            (dataframe['close'] > dataframe['kc_upper']) &
            (dataframe['close'].shift(1) <= dataframe['kc_upper'].shift(1)) &
            volume_filter &
            trend_filter,
            'enter_long'
        ] = 1

        # SHORT: Свеча закрылась НИЖЕ нижней границы канала Кельтнера + фильтры
        dataframe.loc[
            (dataframe['close'] < dataframe['kc_lower']) &
            (dataframe['close'].shift(1) >= dataframe['kc_lower'].shift(1)) &
            volume_filter &
            trend_filter,
            'enter_short'
        ] = 1

        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0

        # Досрочный выход по сигналам отключен, полностью доверяем трейлинг-стопу
        return dataframe
