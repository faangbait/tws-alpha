from decimal import Decimal
from typing import Set
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import time

from ibapi.contract import Contract


class Base(DeclarativeBase):
    pass

class Account(Base):
    __tablename__ = "account"

    id: Mapped[str] = mapped_column(primary_key=True)
    positions: Mapped[Set["Position"]] = relationship(back_populates="account")
    _cash_balance: Mapped[Decimal] = mapped_column(nullable=True, default=None)
    created_at: Mapped[int] = mapped_column(default=int(time.time()))
    updated_at: Mapped[int] = mapped_column(default=int(time.time()))

    @property
    def cash_balance(self):
        return self._cash_balance.quantize(Decimal('1.00'))
    
    @cash_balance.setter
    def cash_balance(self, val):
        self._cash_balance = Decimal(val)

    def __repr__(self) -> str:
        return f"Account(id={self.id!r})"

class Position(Base):
    __tablename__ = "position"

    symbol: Mapped[str] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(ForeignKey("account.id"), nullable=True)
    account: Mapped["Account"] = relationship(back_populates="positions")
    sec_type: Mapped[str] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(nullable=True)
    exchange: Mapped[str] = mapped_column(nullable=True)
    primary_exchange: Mapped[str] = mapped_column(nullable=True)
    _position: Mapped[Decimal] = mapped_column(default=0)
    last_trade: Mapped[float] = mapped_column(nullable=True, default=None)
    quant_rating: Mapped[float] = mapped_column(default=0)
    author_rating: Mapped[float] = mapped_column(default=0)
    analyst_rating: Mapped[float] = mapped_column(default=0)
    valuation: Mapped[float] = mapped_column(default=0)
    growth: Mapped[float] = mapped_column(default=0)
    profitability: Mapped[float] = mapped_column(default=0)
    momentum: Mapped[float] = mapped_column(default=0)
    epsrevision: Mapped[float] = mapped_column(default=0)
    analyst_target: Mapped[float] = mapped_column(default=0)
    _target_liquidity: Mapped[Decimal] = mapped_column(default=Decimal('0.00000'))
    req_id: Mapped[int|None] = mapped_column(nullable=True, default=None)
    created_at: Mapped[int] = mapped_column(default=int(time.time()))
    updated_at: Mapped[int] = mapped_column(default=int(time.time()))

    @property
    def liquidity(self) -> Decimal:
        if self.account and self.position > 0 and self.last_trade:
            return ((self._position * Decimal(self.last_trade)) / self.account.cash_balance).quantize(Decimal('1.00000'))
        else:
            return Decimal('0.00000')

    @property
    def position(self):
        return self._position.quantize(Decimal('1.00'))

    @position.setter
    def position(self, val):
        self._position = val

    @property
    def target_liquidity(self):
        return self._target_liquidity.quantize(Decimal('1.00000'))

    @target_liquidity.setter
    def target_liquidity(self, val):
        self._target_liquidity = val

    @property
    def contract(self):
        contract = Contract()
        contract.symbol = self.symbol
        contract.currency = self.currency
        contract.secType = self.sec_type
        if self.exchange:
            contract.exchange = self.exchange
        else:
            contract.exchange = "SMART"
        contract.primaryExchange = self.primary_exchange
        return contract

    def __repr__(self) -> str:
        if self.position > 0:
            return f"OWNED -> {self.symbol!r} ({self.primary_exchange!r}) LAST({self.last_trade!r}) QUANT({self.quant_rating!r}) LIQ({self.liquidity!r})"
        else:
            return f"WATCH -> {self.symbol!r} ({self.primary_exchange!r}) LAST({self.last_trade!r}) QUANT({self.quant_rating!r})"
