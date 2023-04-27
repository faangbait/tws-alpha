from decimal import Decimal
import unittest
from allyapi.contract import Contract
from allyapi.order import Order

class TestAllyOrder(unittest.TestCase):
    def test_render_fixml(self):
        contract = Contract()
        contract.currency = "USD"
        contract.symbol = "AAPL"
        contract.secType = "STK"

        limit_order = Order(contract)
        limit_order.account = "3LB85910"
        limit_order.action = "BUY"
        limit_order.lmtPrice = 100
        limit_order.orderType = "LMT"
        limit_order.tif = "GTC"
        limit_order.totalQuantity = Decimal(1)

        assert limit_order.render == """<FIXML xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2">
    <Order TmInForce="1" Typ="2" Px="100.00" Side="1" Acct="3LB85910">
        <Instrmt SecTyp="CS" Sym="AAPL"/>
        <OrdQty Qty="1"/>
    </Order>
</FIXML>"""

        contract.symbol="GM"

        market_order = Order(contract)
        market_order.account = "3LB85910"
        market_order.action = "BUY"
        market_order.orderType = "MKT"
        market_order.tif = "DAY"
        market_order.totalQuantity = Decimal(1)

        assert market_order.render == """<FIXML xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2">
    <Order TmInForce="0" Typ="1" Side="1" Acct="3LB85910">
        <Instrmt SecTyp="CS" Sym="GM"/>
        <OrdQty Qty="1"/>
    </Order>
</FIXML>"""
