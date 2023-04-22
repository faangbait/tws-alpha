
import csv
from decimal import Decimal
import time
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import logging
from api.conf import Config
from api.wrappers import twsClient, twsWrapper
from ibapi.common import ListOfContractDescription, TagValueList, TickAttrib, TickerId
from ibapi.contract import Contract, ContractDescription
from ibapi.ticktype import TickType
from api.models import Base, Account, Position

from ibapi.utils import iswrapper

logger = logging.getLogger('tws-alpha')

class twsDatabase(twsWrapper, twsClient):
    def __init__(self, fresh=False, **kwargs) -> None:
        self.engine = create_engine("sqlite:///stocks.sqlite3")

        if fresh:
            Base.metadata.drop_all(self.engine)
            Base.metadata.create_all(self.engine)

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        super().error(reqId, errorCode, errorString, advancedOrderRejectJson)
        self.stop_request(reqId)
    
    def refresh_all(self):
        with Session(self.engine) as session:
            for obj in session.query(Position).filter(Position.req_id == None):
                self.reqMktData(self.nextOrderId(), obj.contract, "", False, False, [])

    def rebalance_all(self):
        with Session(self.engine) as session:
            objs = session.query(Position).filter(Position._position > 0).all()
            objs.extend(session.query(Position).filter(Position._target_liquidity > 0).all())
            
            with open (Config.BASE_PATH / "exports" / "rebalance.csv", "w") as csvfile:
                csvwriter = csv.writer(csvfile)
                for obj in objs:
                    csvwriter.writerow([
                        "DES",
                        obj.symbol,
                        obj.sec_type,
                        f"{'SMART' or obj.exchange}/{obj.primary_exchange}",
                        '', '', '', '', '',
                        obj.target_liquidity
                        ])
            logger.info(f"Rebalance exported...{len(objs)} positions changed")

    def stop_request(self, reqId: TickerId):
        with Session(self.engine) as session:
            for obj in session.scalars(select(Position).where(Position.req_id == reqId)):
                self.cancelMktData(reqId)
                obj.req_id = None
                session.add(obj)
            session.commit()

    def cancel_all(self):
        with Session(self.engine) as session:
            for obj in session.scalars(select(Position)):
                obj.req_id = None
                session.add(obj)
            session.commit()

    def add_symbol(self, symbol: str):
        self.reqMatchingSymbols(self.nextOrderId(), symbol)
        
        with Session(self.engine) as session:
            pos = session.get(Position, symbol)
            if pos:
                return pos
            else:
                return Position(symbol=symbol, currency="USD")

    def add_position(self, position: Position):
        symbol = position.symbol
        with Session(self.engine) as session:
            session.add(session.merge(position))
            session.commit()
        
        self.reqMatchingSymbols(self.nextOrderId(), symbol)

    @property
    def accounts(self):
        with Session(self.engine) as session:
            return session.query(Account).all()

    @iswrapper
    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        """Database update for account value"""
        with Session(self.engine) as session:
            match key:
                case "CashBalance":
                    obj = session.get(Account, accountName)
                    if not obj:
                        obj = Account(id=accountName)
                    obj.cash_balance = Decimal(val)
                    obj.updated_at = int(time.time())
                    logger.debug(f"Updated Cash Balance: {obj.id}, {obj.cash_balance}")
                    session.add(obj)
            session.commit()
        super().updateAccountValue(key, val, currency, accountName)

    @iswrapper
    def managedAccounts(self, accountsList: str):
        with Session(self.engine) as session:
            for id in accountsList.split(','):
                if session.get(Account, id) is None:
                    logger.info(f"Discovered account {id}, adding to database")
                    session.add(Account(id=id))
            session.commit()
        super().managedAccounts(accountsList)

    @iswrapper
    def updatePortfolio(self, contract: Contract, position: Decimal, marketPrice: float, marketValue: float, averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)

            if not obj:
                obj = self.add_symbol(contract.symbol)
            
            obj.account_id = accountName
            obj.position = position
            obj.last_trade = marketPrice
            obj.updated_at = int(time.time())
            
            logger.debug(f"Updated Position: {obj}")
            session.add(obj)            
            session.commit()

        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)

    @iswrapper
    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        """ Database update for position"""
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)

            if not obj:
                obj = self.add_symbol(contract.symbol)
            
            obj.account_id = account
            obj.position = position
            obj.updated_at = int(time.time())
            
            logger.debug(f"Updated Position: {obj}")
            session.add(obj)            
            session.commit()
        super().position(account, contract, position, avgCost)

    @iswrapper
    def symbolSamples(self, reqId: int, contractDescriptions: ListOfContractDescription):
        contractDescription: ContractDescription
        with Session(self.engine) as session:

            for contractDescription in contractDescriptions:
                contract = contractDescription.contract
                obj = session.query(Position).filter(Position.symbol == contract.symbol, Position.currency == contract.currency).first()
                if obj:
                    obj.sec_type = contract.secType
                    obj.exchange = contract.exchange
                    obj.primary_exchange = contract.primaryExchange
                    obj.updated_at = int(time.time())
                    logger.info(f"Updated Symbol: {obj}")
                    session.add(obj)
            session.commit()
        super().symbolSamples(reqId, contractDescriptions)

    @iswrapper
    def reqMktData(self, reqId: TickerId, contract: Contract, genericTickList: str, snapshot: bool, regulatorySnapshot: bool, mktDataOptions: TagValueList):
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)
            if obj:
                obj.req_id = reqId
                logger.debug(f"Requesting Market Data Stream for {obj.symbol} ReqId {reqId}")
                session.add(obj)
                session.commit()
                super().reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)

    @iswrapper
    def tickPrice(self, reqId: TickerId, tickType: TickType, price: float, attrib: TickAttrib):
        with Session(self.engine) as session:
            for obj in session.scalars(select(Position).where(Position.req_id == reqId)):
                if price and price != -1 :
                    obj.last_trade = price
                    obj.updated_at = int(time.time())
                obj.req_id = None
                session.add(obj)
            session.commit()
        super().tickPrice(reqId, tickType, price, attrib)

