from decimal import Decimal
from typing import List, Tuple
from api.db import twsDatabase
from api.models import Position
from api.wrappers import twsClient, twsWrapper
from etl.load_seekingalpha import capture_keyboard_paste
from etl.yahoo_finance import get_info
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.utils import iswrapper
from sqlalchemy.orm import Session
from prettytable.colortable import ColorTable, Themes
import logging

from utils import COLORS

logger = logging.getLogger('tws-alpha')

class twsStrategy(twsDatabase):
    def __init__(self, *args, **kwargs) -> None:
        self.global_cancel = False
        self.started = False
        self.nextValidOrderId = None

        logger.info("Initializing...")
        twsWrapper.__init__(self)
        twsClient.__init__(self, wrapper=self)
        twsDatabase.__init__(self, **kwargs)

    def cancel_all(self):
        logger.warn("Executing Global Cancel")
        self.reqGlobalCancel()
        super().cancel_all()
    
    def start(self):
        self.started = True

        if self.global_cancel:
            self.cancel_all()
            self.stop()
            self.done = True
            return
        
        logger.info("Updates started...")

        self.cancel_all()
        self.reqMarketDataType(4)

        if len(self.accounts) > 1:
            self.reqPositions()

    @iswrapper
    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        if not self.started:
            self.start()
    
    @iswrapper
    def managedAccounts(self, accountsList: str):
        logger.info(f"Account discover started: {accountsList}")
        super().managedAccounts(accountsList)

        for account in accountsList.split(','):
            logger.info(f"Requesting account updates for {account}")
            self.reqAccountUpdates(True, account)
        if self.nextValidOrderId is not None and not self.started:
            self.start()

    @iswrapper
    def updateAccountValue(self, key: str, val: str, currency: str, accountName: str):
        if currency == "USD":
            super().updateAccountValue(key, val, currency, accountName)

    def keyboardInterrupt(self):
        try:
            self.show_menu()
        except KeyboardInterrupt:
            super().keyboardInterrupt()

    def rebalance_all(self):
        with Session(self.engine) as session:
            positions = session.query(Position)
            for position in positions:
                position.target_liquidity = 0
            session.add_all(positions)
            session.commit()

        with Session(self.engine) as session:
            positions = (session.query(Position)
                .filter(Position.quant_rating + Position.analyst_rating + Position.author_rating > 13)
                .filter(Position.primary_exchange != "PINK")
                .order_by(-1 * Position.quant_rating)
                .limit(5)
            )
            for position in positions:
                position.target_liquidity = .2
            session.add_all(positions)
            session.commit()
        super().rebalance_all()

    def print_menu(self):
        print("!\tGlobal Cancel")
        print("A\tSelect Account")
        print("B\tBuy Recommendations")
        print("C\tClear Watchlist")
        print("L\tLoad New Watchlist (SA)")
        print("R\tRefresh All")
        print("S\tSell Recommendations")
        print("Z\tRebalance Export")
        print("X\tExit")


    def show_menu(self):
        print("\n--------------------------------------------------------------------------------")
        self.print_menu()
        selection = input("selection: ")
        match selection.upper():
            case "!":
                self.cancel_all()
            case "A":
                self.select_account()
            case "B":
                buys: List[Tuple[Order, Contract]] = self.generate_buy_recs()
                try:
                    for order, contract in buys:
                        self.show_trade_confirmation(order, contract)
                except KeyboardInterrupt:
                    logger.info("Got interrupt. Resuming.")
            case "C":
                self.clear_watchlist()
            case "R":
                self.refresh_all()
            case "L":
                new_positions = capture_keyboard_paste()
                for pos in new_positions:
                    self.add_position(pos)
            case "S":
                sells: List[Tuple[Order, Contract]] = self.generate_sell_recs()
                for order, contract in sells:
                    self.reqMktData(self.nextOrderId(), contract, "", False, False, [])
                try:
                    for order, contract in sells:
                        self.show_trade_confirmation(order, contract)
                except KeyboardInterrupt:
                    logger.info("Got interrupt. Resuming.")
            case "Z":
                self.rebalance_all()
            case "X":
                self.stop()
                self.done=True

        print("--------------------------------------------------------------------------------\n")
        logger.debug("Resuming flow...")

    def show_trade_confirmation(self, order: Order, contract: Contract):
        with Session(self.engine) as session:
            position = session.get(Position, contract.symbol)

        info = get_info(contract.symbol)
        price = getattr(info, "price")
        profile = getattr(info, "summaryProfile")
        quote_type = getattr(info, "quoteType")

        if not position:
            raise Exception("Couldn't get position for trade confirmation")

        # recent_bid = recent_quote.response.quotes.quote.bid
        # recent_ask = recent_quote.response.quotes.quote.ask
        recent_bid = position.last_trade
        recent_ask = position.last_trade
        pchg = 0
        recent_mid = (recent_bid + recent_ask) / 2
        # pchg = recent_quote.response.quotes.quote.get("pchg","")

        c = ColorTable(
            [
                "Symbol".center(6), 
                "Name".center(34),
                "Bid".center(10), 
                "Ask".center(10), 
                # "Last $".center(10),
                "Target %".center(10),
                "Change %".center(10), 
                "Qty".center(10)
            ], 
            border=True, 
            theme=Themes.OCEAN,
            float_format=".2",
        )

        
        target_price_difference = "N/A"

        if position.analyst_target > 0:
            target_price_difference = ((position.analyst_target - recent_mid) / recent_mid) * 100
        

        c.add_row([
            contract.symbol,
            getattr(price, "shortName", "-"),
            recent_bid,
            recent_ask,
            # getattr(price, "regularMarketPrice", "-"),
            target_price_difference,
            pchg,
            order.totalQuantity.quantize(Decimal("1.00"))
        ])

        print("\n" * 5)
        print(
            COLORS.dim(f"""{getattr(profile, "sector", "").upper()} - {getattr(profile, "industry", "").upper()}"""), 
            COLORS.red(f"""RECOMMEND: {order.action} {order.totalQuantity:.4f} {contract.symbol} @ {order.lmtPrice} {order.tif}""")
        )
        print(c)
        
        ratings = []

        for name, rating in [
            ("QUANT",position.quant_rating),
            ("AUTHOR",position.author_rating),
            ("ANALYSTS",position.analyst_rating),
        ]:
            if rating > 4.5:
                rgb = (0,255,0)
            elif rating > 4:
                rgb = (10,200,10)
            elif rating > 3.5:
                rgb = (20,180,20)
            elif rating > 3:
                rgb = (120, 120, 20)
            elif rating > 2.5:
                rgb = (140, 100, 20)
            elif rating > 2:
                rgb = (160, 90, 10)
            else:
                rgb = (255, 0, 0)
            ratings.append(COLORS.bg_rgb(f" {name} {rating} ", *rgb))
        
        if getattr(quote_type, "quoteType") == "EQUITY":
            for name, rating in [
                ("VALUATION",position.valuation),
                ("GROWTH",position.growth),
                ("PROFITABILITY",position.profitability),
                ("MOMENTUM",position.momentum),
                ("EPSREVISION",position.epsrevision),
            ]:
                if rating > .8:
                    rgb = (0,255,0)
                elif rating > .6:
                    rgb = (10,200,10)
                elif rating > .3:
                    rgb = (20,180,20)
                elif rating > 0:
                    rgb = (120, 120, 20)
                elif rating > -.3:
                    rgb = (140, 100, 20)
                elif rating > -.6:
                    rgb = (160, 90, 10)
                else:
                    rgb = (255, 0, 0)
                ratings.append(COLORS.bg_rgb(f" {name} {rating} ", *rgb))

        print(" ".join(ratings))
        print("\n")
        
        confirm = input(f"Trade at (B)id, (A)sk, (M)idpoint, (T)arget, or (MKT/MOC)? ").lower()
        
        if confirm in ["b"]:
            order.lmtPrice = recent_bid
        elif confirm in ["a"]:
            order.lmtPrice = recent_ask
        elif confirm in ["m"]:
            order.lmtPrice = recent_mid
        elif confirm in ["t"]:
            order.lmtPrice = position.analyst_target
        elif confirm in ["mkt"]:
            order.orderType = "MKT"
            order.tif = "DAY"
        elif confirm in ["moc"]:
            order.orderType = "MKT"
            order.tif = "MOC"
        else:
            logger.warn("Not trading this security.")
            return
        
        self.placeOrder(self.nextOrderId(), contract, order)

