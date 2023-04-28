from decimal import Decimal
import re
from typing import Dict, Literal
from allyapi.object_implem import Object
from allyapi.common import UNSET_DECIMAL, UNSET_DOUBLE
from allyapi.contract import Contract

ORDER_TYPE_MAP = {
    "MKT": 1,
    "LMT": 2,
    "STP": 3,
    "STP LMT": 4
}

TIF_MAP = {
    "DAY": 0,
    "GTC": 1,
    "MOC": 7
}

ACTION_MAP = {
    "BUY": 1,
    "SELL": 2,
    "SHORT": 5,
    "COVER": 1
}

SEC_TYPE_MAP = {
    "CALL": "OC",
    "PUT": "OP",
    "STK": "CS"
}

class Order(Object):
    def __init__(self, contract: Contract) -> None:
        self.account: str = ""
        self.contract = contract
        
        self.action: Literal["BUY","SELL","SHORT","COVER"] = "BUY"
        self.totalQuantity = UNSET_DECIMAL
        self.orderType: Literal["MKT","LMT","STP","STP LMT"] = "LMT"
        self.lmtPrice = UNSET_DOUBLE
        self.stopPrice = UNSET_DOUBLE
        self.tif: Literal["DAY","GTC","MOC"] = "DAY"

        self.transmit: bool = False
        self.orig_id: str = ""

        if self.tif == "MOC" and self.contract.secType != "STK":
            raise Exception("Market on Close valid only for Stock contracts")

    @property
    def render_instrument(self) -> str:
        cfi = SEC_TYPE_MAP.get(self.contract.secType)
        if cfi == "CS":
            inst = f"""<Instrmt SecTyp="CS" Sym="{self.contract.symbol}"/>"""
        else:
            inst = f"""<Instrmt SecTyp="OPT" CFI="{cfi}" Sym="{self.contract.symbol}"/>"""
        return inst
    
    @property
    def render_order(self) -> str:
        match (self.orderType):
            case "MKT":
                order = f"""
    <Order TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Side="{ACTION_MAP.get(self.action)}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </Order>
"""
            case "LMT":
                order = f"""
    <Order TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Px="{self.lmtPrice:.2f}" Side="{ACTION_MAP.get(self.action)}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </Order>
"""
            case "STP":
                order = f"""
    <Order TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" StopPx="{self.stopPrice:.2f}" Side="{ACTION_MAP.get(self.action)}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </Order>
"""
            case "STP LMT":
                order = f"""
    <Order TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Px="{self.lmtPrice:.2f}" StopPx="{self.stopPrice:.2f}" Side="{ACTION_MAP.get(self.action)}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </Order>
"""
            case _:
                raise NotImplemented("Order type not implemented")
        return order

    @property
    def render(self) -> str:
        if self.contract.secType != "STK":
            raise NotImplemented("Option trades not implemented")
        
        trade = f"""<FIXML xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2">{self.render_order}</FIXML>"""

        return trade

    def parse(self, msg):
        match = re.search(r'Sym="(\w{1,})"', msg)
        if match:
            self.contract.symbol = match.groups()[0]

        fields = [
            ("orig_id", r'OrdID="([A-Z]{3}-\d+)\"'),
            ("account", r'Acct="([A-Z0-9]{8}).?"'),
            ("totalQuantity", r'\bQty="([0-9\.]{1,})"'),
            ("lmtPrice", r'Px="([0-9\.]{1,})"'),
        ]

        for attr, pattern in fields:
            match = re.search(pattern, msg)
            if match:
                setattr(self, attr, match.groups()[0])
        
        fields = [
            ("orderType",ORDER_TYPE_MAP,r'\bTyp="(\d)"'),
            ("tif",TIF_MAP,r'TmInForce="(\d)"'),
            ("action",ACTION_MAP,r'Side="(\d)"'),
            ("sec_type",SEC_TYPE_MAP,r'SecTyp="(\w{2,})"'),
        ]

        for attr, map, pattern in fields:
            match = re.search(pattern, msg)
            if match:
                for k,v in map.items():
                    if str(v) == match.groups()[0]:
                        setattr(self, attr, k)

    @property
    def render_cancel(self):
        match (self.orderType):
            case "MKT":
                ordcxl = f"""
    <OrdCxlReq TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Side="{ACTION_MAP.get(self.action)}" OrigID="{self.orig_id}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </OrdCxlReq>"""
            case "LMT":
                ordcxl = f"""
    <OrdCxlReq TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Px="{self.lmtPrice}" Side="{ACTION_MAP.get(self.action)}" OrigID="{self.orig_id}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </OrdCxlReq>"""
            case "STP":
                ordcxl = f"""
    <OrdCxlReq TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" StopPx="{self.stopPrice}" Side="{ACTION_MAP.get(self.action)}" OrigID="{self.orig_id}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </OrdCxlReq>"""
            case "STP LMT":
                ordcxl = f"""
    <OrdCxlReq TmInForce="{TIF_MAP.get(self.tif)}" Typ="{ORDER_TYPE_MAP.get(self.orderType)}" Px="{self.lmtPrice}" StopPx="{self.stopPrice:.2f}" Side="{ACTION_MAP.get(self.action)}" OrigID="{self.orig_id}" Acct="{self.account}">
        {self.render_instrument}
        <OrdQty Qty="{self.totalQuantity}"/>
    </OrdCxlReq>"""
            case _:
                raise NotImplemented("Order type not implemented")

        fixml = f"""<FIXML xmlns="http://www.fixprotocol.org/FIXML-5-0-SP2">{ordcxl}</FIXML>"""

        print(fixml)
        return fixml

    def __str__(self):
        return self.__repr__()
    
    def __repr__(self):
        return f"""Order(Account={self.account}, Symbol={self.contract.symbol}, Action={self.action}, Qty={self.totalQuantity}, Type={self.orderType}, Px={self.lmtPrice}, TIF={self.tif}, OrigId={self.orig_id})"""
