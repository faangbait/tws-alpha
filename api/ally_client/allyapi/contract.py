from allyapi.object_implem import Object
from api.models import Position

class Contract(Object):
    def __init__(self) -> None:
        self.symbol: str = ""
        self.secType: str = "STK"
        self.currency: str = "USD"
        self.exchange: str = ""
        self.primaryExchange: str = "NYSE"
        self.position: Position = Position()


class ContractDescription(Object):
    def __init__(self):
        self.contract = Contract()
        self.derivativeSecTypes = None


