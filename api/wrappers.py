import json

from ratelimit import sleep_and_retry, limits
from allyapi.client import EClient
from allyapi.common import TagValueList, TickerId
from allyapi.contract import Contract
from allyapi.wrapper import EWrapper
import logging

logger = logging.getLogger('tws-alpha')

class twsClient(EClient):
    def __init__(self, wrapper):
        self.connected = False
        super().__init__(wrapper=self)

    def connectAck(self):
        if self.asynchronous:
            self.startApi()

    def keyboardInterrupt(self):
        super().keyboardInterrupt()
        self.stop()
        self.done = True

    def stop(self):
        self.disconnect()
        logger.warn("Disconnecting...")


    @sleep_and_retry
    @limits(calls=1, period=1)
    def reqMatchingSymbols(self, reqId: int, pattern: str):
        return super().reqMatchingSymbols(reqId, pattern)

    @sleep_and_retry
    @limits(calls=4, period=1)
    def reqMktData(self, reqId: TickerId, contract: Contract, genericTickList: str, snapshot: bool, regulatorySnapshot: bool, mktDataOptions: TagValueList):
        return super().reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)

class twsWrapper(EWrapper):
    def __init__(self):
        super().__init__()

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson = ""):
        match errorCode:
            case 10089:
                logger.error(f"Not enough market data for reqId {reqId}.")
            case 504:
                logger.error(f"Lost connection.")
            case 2104:
                pass
            case 2158:
                pass
            case 2106:
                pass
            case 2107:
                pass
            case 2108:
                pass
            case _:
                super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
                if advancedOrderRejectJson:
                    logger.warn(f"Error. { json.loads(advancedOrderRejectJson) }")
                else:
                    logger.warn(f"Error. { dict(id=reqId, code=errorCode, msg=errorString) }")
    
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        logger.debug(f"setting nextValidOrderId: %d", orderId)
        self.nextValidOrderId = orderId

    def nextOrderId(self):
        if self.nextValidOrderId:
            oid = self.nextValidOrderId
            self.nextValidOrderId += 1
            return oid
        else:
            raise Exception("Invalid Order ID")

    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        super().updateAccountValue(key, val, currency, accountName)
        logger.debug(f"{key}: {val}")
