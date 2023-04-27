from decimal import Decimal
from allyapi.common import ListOfContractDescription, TickAttrib, TickType, TickerId
import logging

from allyapi.contract import Contract

logger = logging.getLogger(__name__)

class EWrapper:
    def __init__(self) -> None:
        logger.info("Initializing wrapper...")

    def nextValidId(self, orderId: int):
        pass

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        if advancedOrderRejectJson:
            logger.error("ERROR %s %s %s %s", reqId, errorCode, errorString, advancedOrderRejectJson)
        else: 
            logger.error("ERROR %s %s %s", reqId, errorCode, errorString)

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        pass

    def managedAccounts(self, accountsList: str):
        pass

    def updatePortfolio(self, contract: Contract, position: Decimal, marketPrice: float, marketValue: float, averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        pass

    def symbolSamples(self, reqId: int, contractDescriptions: ListOfContractDescription):
        pass

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        pass

    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        pass

    def stop(self):
        pass
