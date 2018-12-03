import sys
import traceback
import ccxt
import time
from datetime import datetime, timedelta, timezone
import re
from tenacity import RetryError

from conf import Configuration

class SignalsTA:

    def __init__(self, exchange):
        self.ex = exchange
        self.exchange = getattr(ccxt, exchange)({
                    "enableRateLimit": True
                })
        config = Configuration()
        self.indicator_conf = config.indicators
        self.informant_conf = config.informants
        self.crossover_conf = config.crossovers
        # TODO: analyzer
        self.strategy_analyzer = StrategyAnalyzer()
    
    # analisis handler 
    def _test_strategies(self, market):
        new_result = dict()
        new_result[self.ex] = dict()
        new_result[self.ex][market]['indicators'] = self._get_indicator_results(market)
        # new_result[exchange][market]['informants'] = self._get_informant_results(exchange, market)
        # new_result[exchange][market]['crossovers'] = self._get_crossover_results(new_result[exchange][market])
        return new_result

    # analisis de indicadores
    def _get_indicator_results(self, market):
        # TODO: analyzer
        indicator_dispatcher = self.strategy_analyzer.indicator_dispatcher()
        results = { indicator: list() for indicator in self.indicator_conf.keys() }
        historical_data_cache = dict()

        # loop para cada indicador
        for indicator in self.indicator_conf:
            if indicator not in indicator_dispatcher:
                print("no se encuentra indicador")
                continue

            # loop para la config de cada indicador
            for indicator_conf in self.indicator_conf[indicator]:
                if indicator_conf['enabled']:
                    candle_period = indicator_conf['candle_period']
                else:
                    print(" %s is disabled. skipping", indicator)
                    continue

                if candle_period not in historical_data_cache:
                    historical_data_cache[candle_period] = self._get_historical_data(market, candle_period)

                if historical_data_cache[candle_period]:
                    analysis_args = {
                        'historical_data': historical_data_cache[candle_period],
                        'signal': indicator_conf['signal'],
                        'hot_thresh': indicator_conf['hot'],
                        'cold_thresh': indicator_conf['cold']
                    }

                    if 'period_count' in indicator_conf:
                        analysis_args['period_count'] = indicator_conf['period_count']

                    results[indicator].append({
                        'result': self._get_analysis_result(
                            indicator_dispatcher,
                            indicator,
                            analysis_args,
                            market
                        ),
                        'config': indicator_conf
                    })
        return results
    
    # obtiene los resultados del analisis
    def _get_analysis_result(self, dispatcher, indicator, dispatcher_args, market):
        try:
            results = dispatcher[indicator](**dispatcher_args)
        except TypeError:
            print(f'Invalid type encountered while processing pair {market} for indicator {indicator}, skipping')
            print(traceback.format_exc())
            results = str()
        return results

    # obtiene el historico de un market
    def _get_historical_data(self, market, candle_period):
        historical_data = list()
        try:
            historical_data = self.get_historical_data(market, self.ex, candle_period)
        
        except RetryError:
            print(f'Too many retries fetching information for pair {market}, skipping')

        except ccxt.ExchangeError:
            print(f'Exchange supplied bad data for pair {market}, skipping')

        except ValueError as e:
            print(e)
            print(f'Invalid data encountered while processing pair {market}, skipping')
            print(traceback.format_exc())

        except AttributeError:
            print(f'Something went wrong fetching data for {market}, skipping')
            print(traceback.format_exc())
        return historical_data


    def get_historical_data(self, market, time_unit, start_date=None, max_periods=100):
        try:
            if time_unit not in self.exchange.timeframes:
                raise ValueError(f"{self.ex} does not support {time_unit} timeframe for OHLCV data. Possible values are: {list(self.exchange.timeframes)}")
                
        except AttributeError:
            print(f'{self.ex} does not support timeframe queries! We are unable to fetch data!')
            raise AttributeError(sys.exc_info())

        if not start_date:
            timeframe_regex = re.compile('([0-9]+)([a-zA-Z])')
            timeframe_matches = timeframe_regex.match(time_unit)
            time_quantity = timeframe_matches.group(1)
            time_period = timeframe_matches.group(2)

            timedelta_values = {
                'm': 'minutes',
                'h': 'hours',
                'd': 'days',
                'w': 'weeks',
                'M': 'months',
                'y': 'years'
            }

            timedelta_args = { timedelta_values[time_period]: int(time_quantity) }

            start_date_delta = timedelta(**timedelta_args)

            max_days_date = datetime.now() - (max_periods * start_date_delta)
            start_date = int(max_days_date.replace(tzinfo=timezone.utc).timestamp() * 1000)

        historical_data = self.exchange.fetch_ohlcv(market, timeframe=time_unit, since=start_date)

        if not historical_data:
            raise ValueError('No historical data provided returned by exchange.')
        # Sort by timestamp in ascending order
        historical_data.sort(key=lambda d: d[0])
        time.sleep(self.exchange.rateLimit / 1000)
        return historical_data


    # TODO:
    def _get_informant_results(self, market):
        return
    
    # TODO:
    def _get_crossover_results(self, new_result):
        return