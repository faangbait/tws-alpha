from yahooquery import Ticker
from allyapi.utils import AttrDict

def get_info(symbol: str) -> AttrDict:
    symbol = symbol.lower()
    ret = Ticker(symbol)
    return AttrDict.from_nested_dicts(ret.all_modules.get(symbol))

def get_analyst_target_mean(symbol: str) -> float:
    symbol = symbol.lower()
    ret = Ticker(symbol)
    fin_data = ret.financial_data
    data = fin_data.get(symbol)

    if type(data) == type({}):
        return data.get('targetMeanPrice', 0.0)

    return 0.00

