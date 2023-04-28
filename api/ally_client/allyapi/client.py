from decimal import Decimal
from enum import Enum
import time
from typing import List, Literal, Set
from urllib.parse import urljoin

import requests
from ratelimit import limits, sleep_and_retry
from requests_oauthlib import OAuth1Session
from allyapi.common import TagValueList, TickAttrib
from allyapi.contract import Contract, ContractDescription

from allyapi.utils import AttrDict

from allyapi.order import Order
from allyapi import get_version_string
from allyapi.wrapper import EWrapper
from api.secret import OAUTH_CREDENTIALS

import logging

logger = logging.getLogger(__name__)

def validate_response(func):
    def is_valid_response(r: requests.Response) -> bool:
        return r.status_code == 200
   
    def to_attr(*args, **kwargs):
        r: requests.Response = func(*args, **kwargs)

        if is_valid_response(r):
            return AttrDict.from_nested_dicts(r.json())
        
        return AttrDict.from_nested_dicts({
            "response": {
                "error": r.text
            }
        })
    return to_attr


class RESTMethod(Enum):
    get = 1
    post = 2
    delete = 3

class AllyAPI:
    endpoint = "https://devapi.invest.ally.com/v1/"
    fmt = ".json"

    def __init__(self, credentials: dict):
        self.session = OAuth1Session(**credentials)

        self.account = self._AccountCalls(self.session)
        self.trade = self._TradeCalls(self.session)
        self.market = self._MarketCalls(self.session)
        self.member = self._MemberCalls(self.session)
        self.utility = self._UtilityCalls(self.session)
        self.watchlist = self._WatchlistCalls(self.session)

    class _AccountCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session
        
        @sleep_and_retry
        @limits(calls=180, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ):
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        def get_accounts(self):
            uri = f"accounts"
            method = RESTMethod.get
            return self.__request(method, uri)
        
        def get_account_balances(self):
            uri = f"accounts/balances"
            method = RESTMethod.get
            return self.__request(method, uri)
        
        def get_account_by_id(self, id: str):
            uri = f"accounts/{id}"
            method = RESTMethod.get
            return self.__request(method, uri)
        
        def get_account_balances_by_id(self, id: str):
            uri = f"accounts/{id}/balances"
            method = RESTMethod.get
            return self.__request(method, uri)
        
        def get_account_history(
            self, 
            id: str, 
            range: Literal["all", "today", "current_week", "current_month", "last_month"] = "all",
            transactions: Literal["all", "bookkeeping", "trade"] = "all"
        ):
            uri = f"accounts/{id}/history"
            method = RESTMethod.get
            params = {
                "range": range,
                "transactions": transactions
            }
            return self.__request(method, uri, params=params)
        
        def get_account_holdings(self, id: str):
            uri = f"accounts/{id}/holdings"
            method = RESTMethod.get
            return self.__request(method, uri)
    
    class _TradeCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session

        @sleep_and_retry
        @limits(calls=40, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ) -> requests.Response:
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        def get_orders(self, id: str):
            uri = f"accounts/{id}/orders"
            method = RESTMethod.get
            return self.__request(method, uri)

        def post_orders(self, id: str, order: Order, warn_on_orders=True):
            uri = f"accounts/{id}/orders"
            method = RESTMethod.post
            headers = {
                "TKI_OVERRIDE": (not warn_on_orders).__repr__().lower()
            }
            return self.__request(method, uri, data=order.render, headers=headers)

        def cancel_orders(self, id: str, order: Order, warn_on_orders=True):
            uri = f"accounts/{id}/orders"
            method = RESTMethod.post
            headers = {
                "TKI_OVERRIDE": (not warn_on_orders).__repr__().lower()
            }
            return self.__request(method, uri, data=order.render_cancel, headers=headers)

        def post_preview(self, id: str, order: Order, warn_on_orders=True):
            uri = f"accounts/{id}/orders/preview"
            method = RESTMethod.post
            return self.__request(method, uri, data=order.render)

    class _MarketCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session
        
        @sleep_and_retry
        @limits(calls=60, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ):
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        @property
        def clock(self):
            uri = f"market/clock"
            method = RESTMethod.get
            return self.__request(method, uri)

        def quotes(self, symbols: List[str] | str, fids: Set[str] = set()):
            """
            Note: You can technically use a list of symbols, but the return has to be manually handled.
            """
            uri = f"market/ext/quotes"
            method = RESTMethod.get

            params = {
                "fids": ",".join(set(fids))
            }

            if isinstance(symbols, str):
                params['symbols'] = symbols
            else:
                params['symbols'] = ",".join(symbols)
                
            return self.__request(method, uri, params=params)

        # def news_search(self):
        #     uri = f"market/news/search"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def news_by_id(self, id: str):
        #     uri = f"market/news/{id}"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def options_search(self):
        #     uri = f"market/options/search"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def options_strike(self):
        #     uri = f"market/options/strike"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def options_expir(self):
        #     uri = f"market/options/expirations"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def timesales(self):
        #     uri = f"market/timesales"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def toplists(self):
        #     uri = f"market/toplists"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

    class _MemberCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session

        @sleep_and_retry
        @limits(calls=180, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ):
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        @property
        def profile(self):
            uri = f"member/profile"
            method = RESTMethod.get
            return self.__request(method, uri)


    class _UtilityCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session

        @sleep_and_retry
        @limits(calls=300, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ):
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        @property
        def status(self):
            uri = f"utility/status"
            method = RESTMethod.get
            return self.__request(method, uri)

        @property
        def version(self):
            uri = f"utility/version"
            method = RESTMethod.get
            return self.__request(method, uri)


    class _WatchlistCalls:
        def __init__(self, session: OAuth1Session):
            self.session = session

        @sleep_and_retry
        @limits(calls=180, period=60)
        @validate_response
        def __request(
            self,
            method: RESTMethod,
            uri: str,
            **kwargs
        ):
            uri = urljoin(AllyAPI.endpoint, uri)
            uri += AllyAPI.fmt
            
            r: requests.Response

            if method == RESTMethod.post:
                r = self.session.post(uri, **kwargs)
            elif method == RESTMethod.delete:
                r = self.session.delete(uri, **kwargs)
            else:
                r = self.session.get(uri, **kwargs)

            return r

        # def get_watchlists(self):
        #     uri = f"watchlists"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def post_watchlist(self):
        #     uri = f"watchlists"
        #     method = RESTMethod.post
        #     return self.__request(method, uri)

        # def get_watchlist_by_id(self, id: str):
        #     uri = f"watchlists/{id}"
        #     method = RESTMethod.get
        #     return self.__request(method, uri)

        # def delete_watchlist(self, id: str):
        #     uri = f"watchlists/{id}"
        #     method = RESTMethod.delete
        #     return self.__request(method, uri)

        # def post_symbol_to_watchlist(self, id: str):
        #     uri = f"watchlists/{id}/symbols"
        #     method = RESTMethod.post
        #     return self.__request(method, uri)

        # def delete_symbol_from_watchlist(self, id: str):
        #     uri = f"watchlists/{id}/symbols"
        #     method = RESTMethod.post
        #     return self.__request(method, uri)


    account: _AccountCalls
    trade: _TradeCalls
    market: _MarketCalls
    member: _MemberCalls
    utility: _UtilityCalls
    watchlist: _WatchlistCalls

class EClient(object):
    def __init__(self, wrapper) -> None:
        logger.info("Initializing client...")
        self.wrapper: EWrapper = wrapper
        self.connection = None
        self.account = ""
        self.reset()

    def reset(self):
        self.asynchronous = False

    def reqGlobalCancel(self):
        if not self.connection:
            return

        if not hasattr(self, "accounts"):
            return

        for account in getattr(self, "accounts", []):
            r = self.connection.trade.get_orders(account.id)
            assert r is not None
            for fixmlorder in r.response.orderstatus.order:
                msg = fixmlorder.get("fixmlmessage")
                order = Order(Contract())
                order.parse(msg)
                self.connection.trade.cancel_orders(order.account, order)
                logger.warn(f"Global Cancel: {order}")

    def reqPositions(self):
        pass

    def reqAccountUpdates(self, subscribe: bool, acctCode: str):
        if not self.connection:
            return
        
        # r = self.connection.account.get_account_balances_by_id(acctCode)
        r = self.connection.account.get_account_by_id(acctCode)
        assert r is not None
        self.wrapper.updateAccountValue("CashBalance", r.response.accountbalance.money.cashavailable, "USD", acctCode)

        if type(r.response.accountholdings.holding) == list:
            positions = r.response.accountholdings.holding
        else:
            positions = [r.response.accountholdings.holding]
            
        for position in positions:
            data = position.get("instrument")
            contract = Contract()
            contract.symbol = data.get("sym")
            contract.currency = "USD"
            contract.secType = "STK" if data.get("sectyp") == "CS" else ""

            self.wrapper.updatePortfolio(
                contract, 
                Decimal(position.get("qty")), 
                float(position.get("price")),
                float(position.get("marketvalue")),
                float(position.get("purchaseprice")),
                float(position.get("gainloss")),
                0,
                acctCode
            )
        

    def reqMatchingSymbols(self, reqId: int, pattern: str):
        cd = ContractDescription()
        cd.contract = Contract()
        cd.contract.currency = "USD"
        cd.contract.primaryExchange = "NYSE"
        cd.contract.secType = "STK"
        cd.contract.symbol = pattern
        self.wrapper.symbolSamples(reqId, [
            cd
        ])
    
    def reqMktData(self, reqId: int, contract: Contract, genericTickList: str, snapshoot: bool, regulatorySnapshot: bool, mktDataOPtions: TagValueList):
        if not self.connection:
            return
        
        r = self.connection.market.quotes(contract.symbol)
        assert r is not None

        bid_price = r.response.quotes.quote.bid
        ask_price = r.response.quotes.quote.ask
        
        c = self.connection.market.clock
        assert c is not None
        
        tick_attrib = TickAttrib()

        tick_attrib.preOpen = c.response.status.current == "pre"
        tick_attrib.canAutoExecute = c.response.status.current == "open"
        self.wrapper.tickPrice(reqId,0,(bid_price + ask_price) / 2,tick_attrib)
    
    def cancelMktData(self, reqId: int):
        pass
    
    def connect(self, host, port, clientId):
        self.connection = AllyAPI(OAUTH_CREDENTIALS)

    def disconnect(self):
        if not self.connection:
            return
        
        self.connection.session.close()
        self.connection = None

    def keyboardInterrupt(self):
        pass

    def serverVersion(self):
        return get_version_string()

    def twsConnectionTime(self):
        return ""

    def run(self):
        if not self.connection:
            return
        
        self.wrapper.nextValidId(29)

        r = self.connection.account.get_accounts()
        assert r is not None
        accountsList = []
        
        for account in r.response.accounts.accountsummary:
            accountsList.append(account.get("account"))
        
        self.wrapper.managedAccounts(",".join(accountsList))

        while True:
            self.show_menu()

            if getattr(self, "done", False):
                break

            time.sleep(1)

    def show_menu(self):
        pass

    def select_account(self):
        if not self.connection:
            return

        if not hasattr(self, "accounts"):
            return

        print("\n\nSelect an account: ")
        
        accountsList = getattr(self, "accounts", [])
        for idx, account in enumerate(accountsList):
            print(f"{idx+1}\t{account}")
        
        try:
            acct_idx = int(input("Account: "))
            self.account = accountsList[acct_idx-1]
        except KeyboardInterrupt:
            self.wrapper.stop()

        except Exception as e:
            print(e)

    def startApi(self):
        pass
