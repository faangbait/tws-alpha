import time
from typing import List
from api.models import Position

def letter_to_value(letter):
    if letter == "A+":
        return 1
    if letter == "A":
        return .8
    if letter == "A-":
        return .6
    if letter == "B+":
        return .4
    if letter == "B":
        return .2
    if letter == "B-":
        return .1
    if letter == "C+":
        return 0
    if letter == "C":
        return -.1
    if letter == "C-":
        return -.2
    if letter == "D+":
        return -.4
    if letter == "D":
        return -.6
    if letter == "D-":
        return -.8
    if letter == "F":
        return -1
    if letter == "-":
        return 0
    
    try:
        val = float(letter)
    except:
        val = 0

    return val

def capture_keyboard_paste():
    new_positions: List[Position] = []
    screener = False

    while True:
        try:
            obj = Position()
            obj.currency = "USD"
            obj.updated_at = int(time.time())

            col1 = input("Rank/Symbol:\t")

            if col1.isdigit():
                screener = True
                obj.symbol = input("Symbol:\t")
            else:
                screener = False
                obj.symbol = col1
            
            company = input("Company:\t")
            obj.quant_rating = letter_to_value(input("Quant: ")[-4:])
            obj.author_rating = letter_to_value(input("Author: ")[-4:])
            obj.analyst_rating = letter_to_value(input("Analyst: ")[-4:])
            
            cap = input("Market Cap: ")
            div = input("Div: ")
            
            obj.valuation = letter_to_value(input("Valuation: "))
            obj.growth = letter_to_value(input("Growth: "))
            obj.profitability = letter_to_value(input("Profitability: "))
            obj.momentum = letter_to_value(input("Momentum: "))
            obj.epsrevision = letter_to_value(input("EPS Revisions: "))

            new_positions.append(obj)

        except KeyboardInterrupt:
            return new_positions
