from api.db import twsDatabase
from api.models import Position
from api.wrappers import twsClient, twsWrapper
from etl.load_seekingalpha import capture_keyboard_paste
from sqlalchemy.orm import Session

import logging

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

    def print_menu(self):
        print("A\tSelect Account")
        print("C\tClear Watchlist")
        print("L\tLoad New Watchlist (SA)")
        print("R\tRefresh All")
        print("Z\tRebalance Export")
        print("X\tExit")

    def show_menu(self):
        print("\n--------------------------------------------------------------------------------")
        self.print_menu()
        selection = input("selection: ")
        match selection.upper():
            case "A":
                self.select_account()
            case "C":
                self.clear_watchlist()
            case "R":
                self.refresh_all()
            case "L":
                new_positions = capture_keyboard_paste()
                for pos in new_positions:
                    self.add_position(pos)
            case "Z":
                self.rebalance_all()
            case "X":
                self.stop()
                self.done=True

        print("--------------------------------------------------------------------------------\n")
        logger.debug("Resuming flow...")

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
