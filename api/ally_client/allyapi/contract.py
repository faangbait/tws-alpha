from typing import Literal
from allyapi.object_implem import Object

class Contract(Object):
    def __init__(self) -> None:
        self.symbol: str = ""
        self.secType: str = "STK"
        self.currency: str = "USD"
        self.exchange: str = "NYSE"
        self.primaryExchange: str = "NYSE"


class ContractDescription(Object):
    def __init__(self):
        self.contract = Contract()
        self.derivativeSecTypes = None


