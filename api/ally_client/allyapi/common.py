from decimal import Decimal
import sys

from allyapi.object_implem import Object

UNSET_DECIMAL = Decimal(2 ** 127 - 1)
UNSET_DOUBLE = sys.float_info.max

TickerId = int
ListOfContractDescription = list
TickType = int
TagValueList = list

class TickAttrib(Object):
    def __init__(self):
        self.canAutoExecute = False
        self.pastLimit = False
        self.preOpen = False

    def __str__(self):
        return "CanAutoExecute: %d, PastLimit: %d, PreOpen: %d" % (self.canAutoExecute, self.pastLimit, self.preOpen)
