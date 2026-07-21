from freqtrade.strategy import IStrategy
from pandas import DataFrame
import numpy as np


class FiboImbalanceStrategy(IStrategy):
    # Панель управления ордерами и плечом
    leverage = 5.0
    order_types = {
        'entry': 'limit',
        'exit': 'limit',
        'emergency_exit': 'market',
        'force_entry': 'market',
        'force_exit': 'market',
        'stoploss': 'market',
        'stoploss_on_exchange': False,
        'leverage': 'limit'
    }

    # Базовые параметры
    timeframe = '4h'
    stoploss = -0.01  # Базовый стоп-лосс -1% от входа (рискуем 1)

    # Тейк-профит 1:15 (забираем 15% движения при риске в 1%)
    minimal_roi = {"0": 0.15}

    # Включаем кастомный трейлинг для реализации шагов перемещения стопа
    use_custom_stoploss = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # 1. Расчет абсолютного размера тела 4-часовой свечи (в процентах от открытия)
        dataframe['candle_body_pct'] = (
            abs(dataframe['close'] - dataframe['open']) / dataframe['open'])

        # 2. Определение направления импульса (зеленая свеча — лонг)
        dataframe['is_bullish'] = dataframe['close'] > dataframe['open']

        # 3. Расчет целевого уровня Фибоначчи 0.618 для каждой свечи
        # Фиба строится по всей свече: от High до Low
        dataframe['fibo_618'] = dataframe['high'] - \
            (dataframe['high'] - dataframe['low']) * 0.618

        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Инициализируем обе фьючерсные колонки
        dataframe['enter_long'] = 0
        dataframe['enter_short'] = 0

        # Логика сохранения сигнала на 5 свечей вперед
        for i in range(len(dataframe)):
            if dataframe.loc[i, 'candle_body_pct'] >= 0.05 and dataframe.loc[i, 'is_bullish']:
                target_fibo = dataframe.loc[i, 'fibo_618']

                for j in range(1, 6):
                    if i + j < len(dataframe):
                        if dataframe.loc[i + j, 'low'] <= target_fibo <= dataframe.loc[i + j, 'high']:
                            dataframe.loc[i + j, 'enter_long'] = 1
                            break
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        # Инициализируем фьючерсные колонки выхода
        dataframe['exit_long'] = 0
        dataframe['exit_short'] = 0
        return dataframe

    def custom_stoploss(self, pair: str, trade, current_time, current_rate: float,
                        current_profit: float, after_fill: bool, **kwargs) -> float:
        """
        Логика ступенчатого перевода стоп-лосса из видео:
        - Риск -1%
        - При достижении +6% прибыли -> Стоп переносится в безубыток +1%
        - При достижении +9% прибыли -> Стоп подтягивается на +3%
        - При достижении +12% прибыли -> Стоп подтягивается на +7%
        """
        # Переводим текущую прибыль в чистые проценты движения
        profit_pct = current_profit * 100

        if profit_pct >= 12.0:
            # Стоп на +7% прибыли (расстояние от текущей цены до +7% профита)
            return (7.0 - profit_pct) / 100
        elif profit_pct >= 9.0:
            # Стоп на +3% прибыли
            return (3.0 - profit_pct) / 100
        elif profit_pct >= 6.0:
            # Стоп на +1% прибыли (безубыток +1)
            return (1.0 - profit_pct) / 100

        # Если условия для трейлинга не выполнены, остается базовый стоп-лосс -1%
        return -0.01
