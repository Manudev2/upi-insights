import pandas as pd
import numpy as np

def detect_app(df):
    cols = [c.lower().strip() for c in df.columns]
    if any('wallet' in c for c in cols):
        return 'Paytm'
    elif any('receiver' in c for c in cols):
        return 'GPay'
    elif any('upi_id' in c for c in cols):
        return 'PhonePe'
    return 'GPay'

def clean_data(df, app_name):
    df = df.copy()
    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    # ── Rename columns based on app ──────────────────────────
    if app_name == 'Paytm':
        rename_map = {
            'txn_date': 'date', 'txn_amount': 'amount',
            'comment': 'merchant', 'txn_details': 'merchant',
            'debit/credit': 'type', 'status': 'status',
        }
    elif app_name == 'PhonePe':
        rename_map = {
            'transaction_date': 'date', 'amount_(inr)': 'amount',
            'remarks': 'merchant', 'transaction_id': 'transaction_id',
            'status': 'status',
        }
    else:  # GPay / generic
        rename_map = {
            'transaction_date': 'date', 'txn_date': 'date',
            'paid_amount': 'amount', 'debit': 'amount',
        }
    df.rename(columns=rename_map, inplace=True)

    # ── Parse date ───────────────────────────────────────────
    if 'date' in df.columns:
        for fmt in ['%Y-%m-%d','%d-%m-%Y','%d/%m/%Y','%m/%d/%Y',
                    '%d %b %Y','%b %d, %Y','%Y/%m/%d']:
            try:
                df['date'] = pd.to_datetime(df['date'], format=fmt)
                break
            except:
                continue
        if df['date'].dtype == object:
            df['date'] = pd.to_datetime(df['date'], infer_datetime_format=True, errors='coerce')

    # ── Parse amount ─────────────────────────────────────────
    if 'amount' in df.columns:
        df['amount'] = (
            df['amount'].astype(str)
            .str.replace('[₹,, ,+]', '', regex=True)
            .str.replace('INR', '', regex=False)
            .str.replace('Dr','', regex=False)
            .str.replace('Cr','', regex=False)
            .str.strip()
        )
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df = df.dropna(subset=['amount'])
        df = df[df['amount'] > 0]

    # ── Add missing columns ──────────────────────────────────
    if 'status' not in df.columns:
        df['status'] = 'Success'
    else:
        df['status'] = df['status'].fillna('Success')

    if 'category' not in df.columns:
        df['category'] = df.get('merchant', pd.Series(['Uncategorized'] * len(df)))
        df['category'] = df['category'].apply(auto_categorize)

    if 'merchant' not in df.columns:
        df['merchant'] = 'Unknown'

    if 'transaction_id' not in df.columns:
        df['transaction_id'] = [f'TXN{str(i).zfill(6)}' for i in range(len(df))]

    # ── Time features ────────────────────────────────────────
    df['date']        = pd.to_datetime(df['date'])
    df['hour']        = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.strftime('%A')
    df['month']       = df['date'].dt.strftime('%B')
    df['month_num']   = df['date'].dt.month

    # ── Anomaly detection (IQR) ──────────────────────────────
    Q1  = df['amount'].quantile(0.25)
    Q3  = df['amount'].quantile(0.75)
    IQR = Q3 - Q1
    df['is_anomaly'] = df['amount'] > (Q3 + 3 * IQR)

    return df

def auto_categorize(merchant):
    merchant = str(merchant).lower()
    if any(k in merchant for k in ['zomato','swiggy','food','restaurant','cafe','pizza','burger','kfc','domino']):
        return 'Food & Dining'
    elif any(k in merchant for k in ['amazon','flipkart','myntra','shop','store','mall','meesho','ajio']):
        return 'Shopping'
    elif any(k in merchant for k in ['electricity','gas','water','bill','broadband','dth','recharge','airtel','jio','bsnl','vi']):
        return 'Utilities & Recharge'
    elif any(k in merchant for k in ['ola','uber','rapido','metro','irctc','bus','train','flight','travel']):
        return 'Transport'
    elif any(k in merchant for k in ['netflix','hotstar','spotify','bookmyshow','prime','zee','movie']):
        return 'Entertainment'
    elif any(k in merchant for k in ['bigbasket','blinkit','grocer','supermarket','dmart','zepto','instamart']):
        return 'Groceries'
    elif any(k in merchant for k in ['apollo','pharmacy','hospital','doctor','medical','health','netmeds','1mg']):
        return 'Healthcare'
    elif any(k in merchant for k in ['udemy','coursera','byju','school','college','education','unacademy']):
        return 'Education'
    elif any(k in merchant for k in ['transfer','sent','received','upi','neft','imps','emi','loan']):
        return 'Bank Transfer'
    return 'Others'

def get_kpis(df):
    success_df = df[df['status'].str.lower().str.contains('success', na=False)]
    return {
        'total_transactions': len(df),
        'total_spend':        round(success_df['amount'].sum(), 2),
        'avg_transaction':    round(df['amount'].mean(), 2),
        'max_transaction':    round(df['amount'].max(), 2),
        'anomaly_count':      int(df['is_anomaly'].sum()),
        'success_rate':       round(df['status'].str.lower().str.contains('success', na=False).mean() * 100, 1),
        'failed_count':       int(df['status'].str.lower().str.contains('fail', na=False).sum()),
    }

def get_heatmap_data(df):
    order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    df = df.copy()
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=order, ordered=True)
    return (
        df.groupby(['day_of_week','hour'])['amount']
        .sum().reset_index()
        .pivot(index='day_of_week', columns='hour', values='amount')
        .fillna(0)
    )

def get_category_data(df):
    return (
        df.groupby('category')
        .agg(total_amount=('amount','sum'), count=('amount','count'))
        .reset_index().sort_values('total_amount', ascending=False)
    )

def get_merchant_data(df, top_n=10):
    return (
        df.groupby('merchant')
        .agg(total_amount=('amount','sum'), count=('amount','count'))
        .reset_index().sort_values('total_amount', ascending=False)
        .head(top_n)
    )

def get_monthly_trend(df):
    return (
        df.groupby(['month_num','month'])['amount']
        .sum().reset_index().sort_values('month_num')
    )

def get_daily_trend(df):
    return df.groupby('date')['amount'].sum().reset_index()

def get_status_data(df):
    return df['status'].value_counts().reset_index()

def get_anomalies(df):
    cols = ['transaction_id','date','merchant','category','amount','status']
    cols = [c for c in cols if c in df.columns]
    return df[df['is_anomaly']][cols].sort_values('amount', ascending=False)