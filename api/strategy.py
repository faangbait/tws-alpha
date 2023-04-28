from decimal import Decimal
from pprint import pp
from typing import List
from allyapi.order import Order
from allyapi.utils import COLORS
from api.db import twsDatabase
from api.models import Position
from api.wrappers import twsClient, twsWrapper
from etl.load_seekingalpha import capture_keyboard_paste
from sqlalchemy.orm import Session
from prettytable.colortable import ColorTable, Themes
import logging

from etl.yahoo_finance import get_info

logger = logging.getLogger('tws-alpha')

class twsStrategy(twsDatabase):
    def __init__(self, *args, **kwargs) -> None:
        logger.info("Initializing strategy...")
        self.global_cancel = False
        self.started = False
        self.nextValidOrderId = 0

        twsWrapper.__init__(self)
        twsClient.__init__(self, wrapper=self)

        logger.info("Initializing database...")
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

        if len(self.accounts) > 1:
            self.reqPositions()

    def nextValidId(self, orderId: int):
        super().nextValidId(orderId)
        if not self.started:
            self.start()
    
    def managedAccounts(self, accountsList: str):
        logger.info(f"Account discover started: {accountsList}")
        super().managedAccounts(accountsList)

        for account in accountsList.split(','):
            logger.info(f"Requesting account updates for {account}")
            self.reqAccountUpdates(True, account)
        if not self.started:
            self.start()

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
                buys: List[Order] = self.generate_buy_recs()
                try:
                    for buy in buys:
                        self.show_trade_confirmation(buy)
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
                sells: List[Order] = self.generate_sell_recs()
                try:
                    for sell in sells:
                        self.show_trade_confirmation(sell)
                except KeyboardInterrupt:
                    logger.info("Got interrupt. Resuming.")
            case "Z":
                self.rebalance_all()
            case "X":
                self.stop()
                self.done=True

        print("--------------------------------------------------------------------------------\n")
        logger.debug("Resuming flow...")

    def show_trade_confirmation(self, order: Order):
        if not self.connection:
            return
        
        recent_quote = self.connection.market.quotes(order.contract.symbol)
        assert recent_quote is not None

        recent_bid = recent_quote.response.quotes.quote.bid
        recent_ask = recent_quote.response.quotes.quote.ask
        recent_mid = (recent_bid + recent_ask) / 2
        pchg = recent_quote.response.quotes.quote.get("pchg","")

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

        info = get_info(order.contract.symbol)
        price = getattr(info, "price")
        profile = getattr(info, "summaryProfile")
        quote_type = getattr(info, "quoteType")

        target_price_difference = "N/A"

        if order.contract.position.analyst_target > 0:
            target_price_difference = ((order.contract.position.analyst_target - recent_mid) / recent_mid) * 100
        

        c.add_row([
            order.contract.symbol,
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
            COLORS.red(f"""RECOMMEND: {order.action} {order.totalQuantity:.4f} {order.contract.symbol} @ {order.lmtPrice} {order.tif}""")
        )
        print(c)
        
        ratings = []

        for name, rating in [
            ("QUANT",order.contract.position.quant_rating),
            ("AUTHOR",order.contract.position.author_rating),
            ("ANALYSTS",order.contract.position.analyst_rating),
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
                ("VALUATION",order.contract.position.valuation),
                ("GROWTH",order.contract.position.growth),
                ("PROFITABILITY",order.contract.position.profitability),
                ("MOMENTUM",order.contract.position.momentum),
                ("EPSREVISION",order.contract.position.epsrevision),
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
            order.lmtPrice = order.contract.position.analyst_target
        elif confirm in ["mkt"]:
            order.orderType = "MKT"
            order.tif = "DAY"
        elif confirm in ["moc"]:
            order.orderType = "MKT"
            order.tif = "MOC"
        else:
            logger.warn("Not trading this security.")
            return
        
        print(COLORS.fg_rgb(order.render,180,30,30))

        if order.lmtPrice < recent_bid and order.orderType != "MKT":
            print(COLORS.red(f"PRICE DISPARITY DETECTED, ADJUSTING LIMIT {order.lmtPrice} -> {recent_bid-.01}"))
            order.lmtPrice = recent_bid-.01

        if order.transmit:
            r = self.connection.trade.post_orders(order.account, order, True)
            assert r is not None
            logger.info(r)

        else:
            r = self.connection.trade.post_preview(order.account, order, True)
            assert r is not None
            pp(r)
