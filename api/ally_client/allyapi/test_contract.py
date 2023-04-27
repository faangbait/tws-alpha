import unittest
from allyapi.contract import Contract

class TestAllyContract(unittest.TestCase):
    def test_contract(self):
        contract = Contract()
        contract.symbol = "AAPL"
        
        assert contract.symbol == "AAPL"
        assert contract.currency == "USD"
        assert contract.secType == "STK"
