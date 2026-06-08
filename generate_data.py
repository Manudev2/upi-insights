import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

np.random.seed(42)
random.seed(42)

NUM_RECORDS = 10000
START_DATE = datetime(2024, 1, 1)
END_DATE = datetime(2024, 12, 31)

CATEGORIES = {
    'Food & Dining':    ['Zomato', 'Swiggy', "McDonald's", 'Dominos', 'Starbucks', 'KFC', 'Burger King'],
    'Shopping':         ['Amazon', 'Flipkart', 'Myntra', 'Meesho', 'Ajio', 'Nykaa'],
    'Utilities':        ['Electricity Board', 'Gas Agency', 'Water Bill', 'DTH Recharge', 'Broadband'],
    'Transport':        ['Ola', 'Uber', 'Rapido', 'Metro Card', 'IRCTC', 'RedBus'],
    'Entertainment':    ['Netflix', 'Hotstar', 'Spotify', 'BookMyShow', 'Zee5', 'Amazon Prime'],
    'Groceries':        ['BigBasket', 'Blinkit', 'JioMart', 'DMart', 'Zepto', 'Swiggy Instamart'],
    'Healthcare':       ['Apollo Pharmacy', 'Netmeds', '1mg', 'Practo', 'PharmEasy'],
    'Education':        ['Udemy', 'Coursera', "BYJU'S", 'Unacademy', 'Vedantu'],
    'Bank Transfer':    ['Personal Transfer', 'Family Transfer', 'Friend Transfer', 'EMI Payment'],
    'Recharge':         ['Airtel', 'Jio', 'Vi', 'BSNL'],
}

AMOUNT_RANGE = {
    'Food & Dining':  (50,   1500),
    'Shopping':       (200,  15000),
    'Utilities':      (100,  5000),
    'Transport':      (20,   800),
    'Entertainment':  (99,   999),
    'Groceries':      (100,  3000),
    'Healthcare':     (50,   2000),
    'Education':      (199,  9999),
    'Bank Transfer':  (500,  50000),
    'Recharge':       (19,   999),
}

records = []
for i in range(NUM_RECORDS):
    category = random.choice(list(CATEGORIES.keys()))
    merchant  = random.choice(CATEGORIES[category])
    min_amt, max_amt = AMOUNT_RANGE[category]
    amount = round(random.uniform(min_amt, max_amt), 2)

    secs = random.randint(0, int((END_DATE - START_DATE).total_seconds()))
    txn_dt = START_DATE + timedelta(seconds=secs)

    status = random.choices(
        ['Success', 'Failed', 'Pending'],
        weights=[87, 9, 4]
    )[0]

    receiver_upi = f"{merchant.lower().replace(' ', '.')}@okaxis"
    sender_upi   = f"user{random.randint(1000, 9999)}@okicici"

    is_anomaly = False
    if random.random() < 0.03:          # 3% anomalies
        amount     = round(amount * random.uniform(5, 20), 2)
        is_anomaly = True

    records.append({
        'transaction_id': f'GP{str(i+1).zfill(7)}',
        'date':           txn_dt.strftime('%Y-%m-%d'),
        'time':           txn_dt.strftime('%H:%M:%S'),
        'hour':           txn_dt.hour,
        'day_of_week':    txn_dt.strftime('%A'),
        'month':          txn_dt.strftime('%B'),
        'month_num':      txn_dt.month,
        'amount':         amount,
        'category':       category,
        'merchant':       merchant,
        'sender_upi':     sender_upi,
        'receiver_upi':   receiver_upi,
        'status':         status,
        'is_anomaly':     is_anomaly,
        'payment_mode':   'GPay UPI',
    })

df = pd.DataFrame(records)
df.to_csv('data/gpay_transactions.csv', index=False)
print(f"✅ {NUM_RECORDS} GPay transactions saved to data/gpay_transactions.csv")