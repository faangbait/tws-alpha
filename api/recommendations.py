from typing import List
from api.models import Position


def sell_bad_quants(positions: List[Position]):
    sell: List[Position] = []
    for position in positions:
        if position.quant_rating < 4:
            sell.append(position)
    return sell

def sell_above_analyst_target(positions: List[Position]):
    sell: List[Position] = []
    for position in positions:
        if position.last_trade > position.analyst_target * .95 and position.analyst_target > 0:
            sell.append(position)
    return sell

