from decimal import Decimal
import unittest
from allyapi.client import AllyAPI, EClient
from allyapi.order import Order
from allyapi.contract import Contract
from allyapi.wrapper import EWrapper
from api.secret import OAUTH_CREDENTIALS


class TestAllyClient(unittest.TestCase):
    def setUp(self):
        self.client = AllyAPI(OAUTH_CREDENTIALS)
        self.ewrapper = EWrapper()
        self.eclient = EClient(self.ewrapper)
        self.eclient.account = "3LB85910"
        self.eclient.connect("","","")

    def tearDown(self):
        self.client.session.close()
        self.eclient.disconnect()

    def test_utility(self):
        r = self.client.utility.version
        assert r is not None
        assert r.response.error == "Success"
        assert r.response.version == 1.0
        del r

        r = self.client.utility.status
        assert r is not None
        assert r.response.error == "Success"
        assert r.response.time is not None
        del r

    def test_member(self):
        r = self.client.member.profile
        assert r is not None
        assert r.response.error == "Success"
        assert r.response.userdata.disabled == False
        del r

    def test_market(self):
        r = self.client.market.clock
        assert r is not None
        assert r.response.error == "Success"
        assert r.response.status.current in ["open", "close"]
        del r
        
        r = self.client.market.quotes("aapl")
        assert r is not None
        assert r.response.error == "Success"
        assert r.response.quotes.quote.ask > 0
        del r

        r = self.client.market.quotes(["aapl", "meta"])
        assert r is not None
        assert r.response.error == "Success"
        assert float(r.response.quotes.quote[0].get("ask")) > 0
        del r

    def test_global_cancel(self):
        self.eclient.reqGlobalCancel()

    def test_run(self):
        self.eclient.run()
        assert self.eclient.account is not None
        

    def test_trade(self):
        id = "3LB85910"
        contract = Contract()
        contract.currency = "USD"
        contract.symbol = "AAPL"
        contract.secType = "STK"

        limit_order = Order(contract)
        limit_order.account = "3LB85910"
        limit_order.action = "BUY"
        limit_order.lmtPrice = .01
        limit_order.orderType = "LMT"
        limit_order.tif = "GTC"
        limit_order.totalQuantity = Decimal(1)

        contract.symbol = "AAPL"
        market_order = Order(contract)
        market_order.account = "3LB85910"
        market_order.orderType = "MKT"
        market_order.action = "BUY"
        market_order.totalQuantity = Decimal(1)
        
        r = self.client.trade.get_orders(id)
        assert r is not None
        assert r.response.error == "Success"
        assert isinstance(r.response.orderstatus.order, list)
        del r

        r = self.client.trade.post_preview(id, limit_order)
        assert r is not None
        assert r.response.error.startswith("Your account does not have sufficient funds for this transaction") or r.response.error == "Success"
        del r

        r = self.client.trade.post_preview(id, market_order)
        assert r is not None
        assert r.response.error.startswith("Your account does not have sufficient funds for this transaction") or r.response.error == "Success"
        del r

