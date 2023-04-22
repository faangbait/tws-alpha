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

def capture_keyboard_paste(screener=True):
    new_positions: List[Position] = []

    while True:
        try:
            obj = Position()
            if screener:
                rank = input("Rank:\t")
            
            obj.symbol = input("Symbol:\t")
            obj.currency = "USD"
            
            if screener:
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

            obj.updated_at = int(time.time())
            new_positions.append(obj)
        except KeyboardInterrupt:
            return new_positions
