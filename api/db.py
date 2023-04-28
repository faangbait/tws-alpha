
import csv
from decimal import Decimal
import time
from typing import List
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
import logging
from allyapi.order import Order
from api.conf import Config
from api.recommendations import sell_above_analyst_target, sell_bad_quants
from api.wrappers import twsClient, twsWrapper
from allyapi.contract import Contract, ContractDescription
from allyapi.common import ListOfContractDescription, TagValueList, TickAttrib, TickType, TickerId
from api.models import Base, Account, Position
from etl.yahoo_finance import get_analyst_target_mean
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
                logger.info(f"Getting data for {obj.symbol}")
                contract=Contract()
                contract.symbol = obj.symbol
                contract.position = obj
                contract.primaryExchange = obj.primary_exchange
                contract.secType = obj.sec_type
                self.reqMktData(self.nextOrderId(), contract, "", False, False, [])
                obj.analyst_target = get_analyst_target_mean(obj.symbol)
                session.add(obj)
            session.commit()

    def clear_watchlist(self):
        with Session(self.engine) as session:
            session.query(Position).where(Position.account_id == None).delete()
            session.commit()

    def rebalance_all(self):
        with Session(self.engine) as session:
            objs = session.query(Position).filter(Position._position > 0).union(session.query(Position).filter(Position._target_liquidity > 0))
            with open (Config.BASE_PATH / "exports" / "rebalance.csv", "w") as csvfile:
                csvwriter = csv.writer(csvfile)
                for obj in objs:
                    csvwriter.writerow([
                        "DES",
                        obj.symbol,
                        obj.sec_type,
                        # f"{'SMART' or obj.exchange}/{obj.primary_exchange}",
                        f"{'SMART/ARCAEDGE' if obj.primary_exchange in ['PINK'] else 'SMART/AMEX'}",
                        '', '', '', '', '',
                        obj.target_liquidity * 100
                        ])
                    logger.info(f"DES,{obj.symbol},{obj.sec_type},SMART/AMEX,,,,,,{obj.target_liquidity * 100}")
            logger.info(f"Rebalance exported...{objs.count()} positions changed")

    def generate_sell_recs(self):
        sells: List[Order] = []

        with Session(self.engine) as session:
            objs = session.query(Position).where(Position._position > 0).all()
            for obj in sell_bad_quants(objs):
                contract = Contract()
                contract.symbol = obj.symbol
                contract.secType = obj.sec_type
                contract.position = obj
                
                order = Order(contract)
                order.account = obj.account_id
                order.action = "SELL"
                order.totalQuantity = obj._position
                order.orderType = "LMT"
                order.lmtPrice = obj.last_trade
                order.tif = "GTC"
                order.transmit = True
                sells.append(order)

            for obj in sell_above_analyst_target(objs):
                contract = Contract()
                contract.symbol = obj.symbol
                contract.secType = obj.sec_type
                contract.position = obj

                order = Order(contract)
                order.account = obj.account_id
                order.action = "SELL"
                order.totalQuantity = obj._position
                order.orderType = "LMT"
                order.lmtPrice = obj.analyst_target
                order.tif = "GTC"
                order.transmit = True
                sells.append(order)
        return sells
    
    def generate_buy_recs(self):
        buys: List[Order] = []
        
        with Session(self.engine) as session:
            objs = session.query(Position).all()
        
        return buys
    
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
        with Session(self.engine) as session:
            pos = session.get(Position, symbol)
            if not pos:
                pos = Position(symbol=symbol, currency="USD")
            self.add_position(pos)

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

    def managedAccounts(self, accountsList: str):
        with Session(self.engine) as session:
            for id in accountsList.split(','):
                if session.get(Account, id) is None:
                    logger.info(f"Discovered account {id}, adding to database")
                    session.add(Account(id=id))
            session.commit()
        super().managedAccounts(accountsList)

    def updatePortfolio(self, contract: Contract, position: Decimal, marketPrice: float, marketValue: float, averageCost: float, unrealizedPNL: float, realizedPNL: float, accountName: str):
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)

            if not obj:
                self.add_symbol(contract.symbol)
            
            obj = session.get(Position, contract.symbol)
            if not obj:
                raise Exception(f"Couldn't create position {obj}")

            obj.account_id = accountName
            obj.position = position
            obj.last_trade = marketPrice
            obj.updated_at = int(time.time())
            
            logger.debug(f"Updated Position: {obj}")
            session.add(obj)            
            session.commit()

        super().updatePortfolio(contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName)

    def position(self, account: str, contract: Contract, position: Decimal, avgCost: float):
        """ Database update for position"""
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)

            if not obj:
                self.add_symbol(contract.symbol)
            
            obj = session.get(Position, contract.symbol)
            if not obj:
                raise Exception(f"Couldn't create position {obj}")
                
            obj.account_id = account
            obj.position = position
            obj.updated_at = int(time.time())
            
            logger.debug(f"Updated Position: {obj}")
            session.add(obj)            
            session.commit()
        super().position(account, contract, position, avgCost)

    def symbolSamples(self, reqId: int, contractDescriptions: ListOfContractDescription):
        contractDescription: ContractDescription
        with Session(self.engine) as session:

            for contractDescription in contractDescriptions:
                contract = contractDescription.contract
                if contract.primaryExchange not in ["NYSE", "NASDAQ", "ARCA", "PINK", "AMEX"]:
                    continue
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

    def reqMktData(self, reqId: TickerId, contract: Contract, genericTickList: str, snapshot: bool, regulatorySnapshot: bool, mktDataOptions: TagValueList):
        with Session(self.engine) as session:
            obj = session.get(Position, contract.symbol)
            if obj:
                obj.req_id = reqId
                logger.debug(f"Requesting Market Data Stream for {obj.symbol} ReqId {reqId}")
                session.add(obj)
                session.commit()
                super().reqMktData(reqId, contract, genericTickList, snapshot, regulatorySnapshot, mktDataOptions)

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

