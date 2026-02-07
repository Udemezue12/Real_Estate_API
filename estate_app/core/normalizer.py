import re

def normalize_bank_name(name: str) -> str:
   
    if not name:
        return ""
    
    cleaned = name.lower().strip()
    #
    cleaned = re.sub(r'\b(plc|limited|ltd|nigeria|nig|plc|\(nigeria\))\b', '', cleaned, flags=re.IGNORECASE)
    
    cleaned = cleaned.replace("&", "and").replace("/", " ").replace("-", " ")
    
    cleaned = re.sub(r'[^a-z0-9\s]', '', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned



BANK_ALIASES = {
    
    "gtb": "guaranty trust bank",
    "gtbank": "guaranty trust bank",
    "gt": "guaranty trust bank",
    "guaranty trust": "guaranty trust bank",
    "guaranty trust bank": "guaranty trust bank",
    "guaranty": "guaranty trust bank",

   
    "uba": "united bank for africa",
    "united bank for africa": "united bank for africa",
    "uba plc": "united bank for africa",
    "united": "united bank for africa",

    
    "access": "access bank",
    "access bank": "access bank",
    "access bank plc": "access bank",
    "diamond": "access bank",
    "diamond bank": "access bank",

    
    "zenith": "zenith bank",
    "zenith bank": "zenith bank",
    "zenithbank": "zenith bank",
    "zenith plc": "zenith bank",

    
    "first bank": "first bank of nigeria",
    "firstbank": "first bank of nigeria",
    "fbn": "first bank of nigeria",
    "first bank nigeria": "first bank of nigeria",

   
    "fcmb": "first city monument bank",
    "first city monument bank": "first city monument bank",
    "fcmb plc": "first city monument bank",

    
    "fidelity": "fidelity bank",
    "sterling": "sterling bank",
    "stanbic": "stanbic ibtc bank",
    "stanbic ibtc": "stanbic ibtc bank",
    "wema": "wema bank",
    "ecobank": "ecobank",
    "polaris": "polaris bank",
    "kuda": "kuda microfinance bank",
    "opay": "opay digital services limited", 
    "moniepoint": "moniepoint microfinance bank",
}


BANK_ALIASES_REVERSE = {v: k for k, v in BANK_ALIASES.items() if len(k) <= 10}  


def get_canonical_bank_name(user_input: str) -> str:
   
    normalized = normalize_bank_name(user_input)
    
   
    if normalized in BANK_ALIASES:
        return BANK_ALIASES[normalized]
    
   
    return normalized



if __name__ == "__main__":
    test_inputs = [
        "GTBank",
        "guaranty trust",
        "UBA PLC",
        "United Bank For Africa",
        "zenith bank plc",
        "access bank nigeria",
        "diamond bank",
        "fcmb",
        "First city monument",
        "Sterling Bank Limited",
    ]

    for inp in test_inputs:
        canon = get_canonical_bank_name(inp)
        short = BANK_ALIASES_REVERSE.get(canon, canon)
        print(f"Input: {inp:25} → Canonical: {canon:30} (short: {short})")