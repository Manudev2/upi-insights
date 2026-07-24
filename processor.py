import pandas as pd
import numpy as np
import pdfplumber
import re


# ── Categorization ───────────────────────────────────────────
def auto_categorize(text):
    text = str(text).lower()
    if any(k in text for k in ['zomato','swiggy','food','restaurant','cafe','pizza','burger','kfc','domino']):
        return 'Food & Dining'
    elif any(k in text for k in ['amazon','flipkart','myntra','shop','store','mall','meesho','ajio','shopping']):
        return 'Shopping'
    elif any(k in text for k in ['electricity','gas','water','bill','broadband','dth','recharge','airtel','jio','bsnl','vi']):
        return 'Utilities & Recharge'
    elif any(k in text for k in ['ola','uber','rapido','metro','irctc','bus','train','flight','travel','petrol']):
        return 'Transport'
    elif any(k in text for k in ['netflix','hotstar','spotify','bookmyshow','prime','zee','movie']):
        return 'Entertainment'
    elif any(k in text for k in ['bigbasket','blinkit','grocer','supermarket','dmart','zepto','instamart','vegetable']):
        return 'Groceries'
    elif any(k in text for k in ['apollo','pharmacy','hospital','doctor','medical','health','netmeds','1mg']):
        return 'Healthcare'
    elif any(k in text for k in ['udemy','coursera','byju','school','college','education','unacademy']):
        return 'Education'
    elif any(k in text for k in ['transfer','sent','received','self','neft','imps','emi','loan','atm']):
        return 'Bank Transfer'
    return 'Others'


# ── App detection ─────────────────────────────────────────────
def detect_app(filename, df_or_sheets):
    fname = filename.lower()
    if 'paytm' in fname:
        return 'Paytm'
    if 'phonepe' in fname:
        return 'PhonePe'
    if 'gpay' in fname or 'google' in fname:
        return 'GPay'

    if isinstance(df_or_sheets, dict):
        cols = []
        for sheet_df in df_or_sheets.values():
            cols += [c.lower() for c in sheet_df.columns]
    else:
        cols = [str(c).lower() for c in df_or_sheets.columns]

    if 'tags' in cols or 'upi ref no.' in cols:
        return 'Paytm'
    if 'transaction' in cols and 'amount' in cols:
        return 'GPay'
    return 'GPay'


# ── PDF extraction ───────────────────────────────────────────

_MONTHS = {m: i + 1 for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
)}

# Column boundaries (x0 coordinates) for the Paytm passbook card layout.
# Each transaction "row" in the PDF is actually a block of several text
# lines laid out in 5 side-by-side columns (Date&Time, Transaction
# Details, Notes&Tags, Your Account, Amount). pdfplumber's plain
# extract_text() merges words that share a similar vertical position
# onto the same line REGARDLESS of which column they belong to, which
# scrambles date/merchant/amount together. We instead pull word-level
# bounding boxes and bucket each word into its column by x0, then
# reconstruct each column's text independently.
_COL_BOUNDS = [
    ('dt', 85),
    ('det', 285),
    ('notes', 390),
    ('acct', 490),
    ('amt', float('inf')),
]


def _bucket_column(x0):
    for name, upper in _COL_BOUNDS:
        if x0 < upper:
            return name
    return 'amt'


def _load_pdf(uploaded_file):
    """Parser for Paytm Passbook PDF (card/column layout, not a real table)."""
    import pdfplumber, pandas as pd, re

    # Defensive: Streamlit's UploadedFile (and any file-like object) keeps
    # a read cursor. If something upstream (a preview, a hash, another
    # loader) already read from this object, the cursor sits at EOF and
    # pdfplumber will see an empty/corrupt stream -> silently 0 pages of
    # words -> "No transactions found" even though the code is correct.
    # Rewind defensively before opening.
    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    raw_rows = []
    with pdfplumber.open(uploaded_file) as pdf:
        # Determine the statement's ending year from the cover page, e.g.
        # "Statement for 24 JUL'25 - 23 JUL'26" -> end_year = 2026
        header_txt = pdf.pages[0].extract_text() or ""
        m = re.search(r"Statement for\s+\d{1,2}\s\w+'\d{2}\s+-\s+\d{1,2}\s\w+'(\d{2})", header_txt)
        end_year = 2000 + int(m.group(1)) if m else 2025

        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue

            # A new transaction block starts wherever a bare day-number
            # (e.g. "21") appears in the leftmost (date) column.
            anchors = sorted(set(
                w['top'] for w in words if w['x0'] < 85 and re.match(r'^\d{1,2}$', w['text'])
            ))
            for idx, atop in enumerate(anchors):
                bottom = anchors[idx + 1] if idx + 1 < len(anchors) else float('inf')
                block_words = [w for w in words if atop - 1 <= w['top'] < bottom - 1]

                cols = {'dt': [], 'det': [], 'notes': [], 'acct': [], 'amt': []}
                for w in block_words:
                    cols[_bucket_column(w['x0'])].append(w)

                def join_col(ws):
                    ws = sorted(ws, key=lambda w: (round(w['top']), w['x0']))
                    return ' '.join(w['text'] for w in ws)

                raw_rows.append({k: join_col(v) for k, v in cols.items()})

    # Keep only blocks that actually look like a transaction row: date
    # column must read "DD Mon ... HH:MM AM/PM" and amount column must
    # contain "Rs." (this filters out header/footer/summary blocks).
    parsed = []
    for r in raw_rows:
        m = re.match(r'^(\d{1,2})\s([A-Za-z]{3}).*?(\d{1,2}:\d{2}\s?[AP]M)', r['dt'])
        if not m or 'Rs.' not in r['amt']:
            continue
        day, mon, time_ = m.group(1), m.group(2), m.group(3)

        # Merchant/description text lives in the "det" column, but also
        # contains "UPI ID: ..." / "UPI Ref No: ..." / trailing "on"
        # lines mixed in - strip those out.
        det_text = r['det']
        det_text = re.sub(r'\s*UPI ID:.*?(?=UPI Ref No:|$)', ' ', det_text)
        det_text = re.sub(r'\s*UPI Ref No:.*$', '', det_text)
        det_text = re.sub(r'\bon\b\s*$', '', det_text).strip()
        det_text = re.sub(r'\s+', ' ', det_text)

        tags_text = re.sub(r'^Tag:\s*', '', r['notes']).strip()

        parsed.append({
            'day': day, 'mon': mon, 'time': time_,
            'merchant': det_text or 'Unknown',
            'amount_raw': r['amt'].strip(),
            'tags_raw': tags_text,
            'account': r['acct'].strip(),
        })

    if not parsed:
        raise ValueError("No transactions found in this PDF.")

    # Assign calendar years. Rows come in reverse-chronological order
    # (newest first). Statement covers two calendar years, so whenever
    # the month number goes UP compared to the previous row (e.g. Jan
    # -> Dec), that means we've stepped back into the prior year.
    year = end_year
    prev_month = None
    rows = []
    for p in parsed:
        mnum = _MONTHS.get(p['mon'][:3].title())
        if prev_month is not None and mnum is not None and mnum > prev_month:
            year -= 1
        prev_month = mnum if mnum is not None else prev_month

        rows.append({
            'date_raw': f"{p['day']} {p['mon']} {year}",
            'time_raw': p['time'],
            'merchant': p['merchant'],
            'amount_raw': p['amount_raw'],
            'tags_raw': p['tags_raw'],
            'account': p['account'],
        })

    return pd.DataFrame(rows)

# ── File loading ─────────────────────────────────────────────
def load_file(uploaded_file):
    """
    Load CSV (GPay) / XLSX (Paytm/PhonePe) / PDF (any) and return (raw_df, app_name)
    """
    filename = uploaded_file.name
    fname_lower = filename.lower()

    if fname_lower.endswith('.pdf'):
        df = _load_pdf(uploaded_file)
        # _load_pdf already emits Paytm-style columns (date_raw, time_raw,
        # merchant, amount_raw, tags_raw), so route it through the Paytm
        # cleaner rather than the generic PDF-table cleaner.
        app_name = "Paytm"
        return df, app_name

    elif fname_lower.endswith(('.xlsx', '.xls')):
        xl = pd.ExcelFile(uploaded_file)
        sheets = {s: pd.read_excel(xl, sheet_name=s) for s in xl.sheet_names}
        app_name = detect_app(filename, sheets)

        target_sheet = None
        for s in sheets:
            if 'passbook' in s.lower() or 'history' in s.lower() or 'transaction' in s.lower():
                target_sheet = s
                break
        if target_sheet is None:
            target_sheet = max(sheets, key=lambda s: len(sheets[s]))

        df = sheets[target_sheet]
        return df, app_name

    else:
        df = pd.read_csv(uploaded_file)
        app_name = detect_app(filename, df)
        return df, app_name


# ── Helpers ────────────────────────────────────────────────────
def _parse_signed_amount(val):
    """Parse '+20,000.00' or '-100.00' or 'Dr 100.00' into signed float."""
    s = str(val).strip()
    if s == '' or s.lower() == 'nan' or s == '-':
        return np.nan

    sign = 1
    s_lower = s.lower()
    if 'dr' in s_lower:
        sign = -1
    elif 'cr' in s_lower:
        sign = 1
    elif s.startswith('+'):
        sign = 1
    elif s.startswith('-'):
        sign = -1

    # Extract just the numeric portion (e.g. "Rs.2,500" -> "2,500",
    # not ".2500"). Stripping characters blindly left a stray decimal
    # point from "Rs." attached to the number, silently corrupting
    # every amount by ~100x (e.g. Rs.2,500 became 0.25).
    m = re.search(r'\d[\d,]*\.?\d*', s)
    if not m:
        return np.nan
    num_str = m.group(0).replace(',', '')
    try:
        return sign * float(num_str)
    except (ValueError, TypeError):
        return np.nan


def _clean_paytm_tag(tag):
    if tag is None or str(tag) == 'nan':
        return 'Others'
    cleaned = ''.join(ch for ch in str(tag) if ch.isalnum() or ch.isspace())
    cleaned = cleaned.replace('#', '').strip()
    return cleaned if cleaned else 'Others'


# ── App-specific cleaners ──────────────────────────────────────
def _clean_gpay(df):
    """GPay CSV: Date, Time, Transaction, Amount"""
    rename_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl == 'date':
            rename_map[c] = 'date_raw'
        elif cl == 'time':
            rename_map[c] = 'time_raw'
        elif cl == 'transaction':
            rename_map[c] = 'merchant'
        elif cl == 'amount':
            rename_map[c] = 'amount'
    df = df.rename(columns=rename_map)

    df['date'] = pd.to_datetime(
        df['date_raw'].astype(str) + ' ' + df.get('time_raw', '').astype(str),
        errors='coerce', format='mixed'
    )
    mask = df['date'].isna()
    if mask.any():
        df.loc[mask, 'date'] = pd.to_datetime(df.loc[mask, 'date_raw'], errors='coerce')

    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')

    df['txn_direction'] = df['merchant'].astype(str).apply(
        lambda x: 'Credit' if x.lower().startswith('received') else 'Debit'
    )
    df['category'] = df['merchant'].apply(auto_categorize)
    return df


def _clean_paytm(df):
    """Paytm XLSX 'Passbook Payment History' sheet"""
    rename_map = {}
    for c in df.columns:
        cl = c.strip().lower()
        if cl == 'date':
            rename_map[c] = 'date_raw'
        elif cl == 'time':
            rename_map[c] = 'time_raw'
        elif cl == 'transaction details':
            rename_map[c] = 'merchant'
        elif cl == 'amount':
            rename_map[c] = 'amount_raw'
        elif cl == 'tags':
            rename_map[c] = 'tags_raw'
    df = df.rename(columns=rename_map)

    df['amount_signed'] = df['amount_raw'].apply(_parse_signed_amount)
    df['txn_direction'] = df['amount_signed'].apply(
        lambda x: 'Credit' if x > 0 else ('Debit' if x < 0 else 'Unknown')
    )

    # Self-transfer rows (money moved between the user's own accounts)
    # have no +/- sign in the PDF and the statement explicitly excludes
    # them from total money paid/received. Tag them separately so
    # get_kpis()'s Debit/Credit sums don't double-count them.
    if 'tags_raw' in df.columns:
        is_self = df['tags_raw'].astype(str).str.contains('Self Transfer', case=False, na=False)
        df.loc[is_self, 'txn_direction'] = 'Self Transfer'

    df['amount'] = df['amount_signed'].abs()

    date_parsed = pd.to_datetime(df['date_raw'], format='%d/%m/%Y', errors='coerce')
    if date_parsed.isna().all():
        date_parsed = pd.to_datetime(df['date_raw'], errors='coerce', dayfirst=True)

    if 'time_raw' in df.columns:
        df['date'] = pd.to_datetime(
            date_parsed.dt.strftime('%Y-%m-%d') + ' ' + df['time_raw'].astype(str),
            errors='coerce'
        )
        mask = df['date'].isna()
        df.loc[mask, 'date'] = date_parsed[mask]
    else:
        df['date'] = date_parsed

    if 'tags_raw' in df.columns:
        df['category'] = df['tags_raw'].apply(_clean_paytm_tag)
    else:
        df['category'] = df['merchant'].apply(auto_categorize)

    return df


def _clean_phonepe(df):
    """PhonePe XLSX/CSV handler"""

    df = df.copy()

    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    rename_map = {}

    for c in df.columns:

        cl = str(c).strip().lower()

        if cl == 'date':
            rename_map[c] = 'date_raw'

        elif cl == 'time':
            rename_map[c] = 'time_raw'

        elif cl == 'amount':
            rename_map[c] = 'amount_raw'

        elif cl in [
            'transaction',
            'transaction details',
            'details',
            'remarks',
            'remark'
        ]:
            rename_map[c] = 'merchant'

        elif cl == 'type':
            rename_map[c] = 'txn_type_raw'

    df = df.rename(columns=rename_map)

    # Remove duplicates again after rename
    df = df.loc[:, ~df.columns.duplicated()]

    if 'amount_raw' not in df.columns:
        raise ValueError(
            f"Amount column not found. Columns are: {list(df.columns)}"
        )

    if 'date_raw' not in df.columns:
        raise ValueError(
            f"Date column not found. Columns are: {list(df.columns)}"
        )

    if 'merchant' not in df.columns:
        df['merchant'] = 'Unknown'

    df['amount'] = (
        df['amount_raw']
        .apply(_parse_signed_amount)
        .abs()
    )

    date_parsed = pd.to_datetime(
        df['date_raw'],
        errors='coerce',
        dayfirst=True
    )

    if 'time_raw' in df.columns:

        df['date'] = pd.to_datetime(
            date_parsed.dt.strftime('%Y-%m-%d')
            + ' '
            + df['time_raw'].astype(str),
            errors='coerce'
        )

        mask = df['date'].isna()
        df.loc[mask, 'date'] = date_parsed[mask]

    else:
        df['date'] = date_parsed

    if 'txn_type_raw' in df.columns:

        df['txn_direction'] = (
            df['txn_type_raw']
            .astype(str)
            .apply(
                lambda x:
                'Credit'
                if 'credit' in x.lower()
                else 'Debit'
            )
        )

    else:
        df['txn_direction'] = 'Debit'

    df['category'] = df['merchant'].apply(auto_categorize)

    return df


def _clean_pdf_generic(df):
    """
    Generic cleaner for PDF-extracted tables.
    Tries to find date, amount, and description columns by name/content.
    """
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Find date column
    date_col = None
    for c in df.columns:
        if 'date' in c:
            date_col = c
            break
    if date_col is None:
        date_col = df.columns[0]

    # Find amount column
    amount_col = None
    for c in df.columns:
        if 'amount' in c or 'amt' in c or 'debit' in c or 'credit' in c:
            amount_col = c
            break
    if amount_col is None:
        amount_col = df.columns[-1]

    # Find description column
    desc_col = None
    for c in df.columns:
        if any(k in c for k in ['transaction', 'description', 'particular', 'detail', 'remark', 'narration']):
            desc_col = c
            break
    if desc_col is None:
        candidates = [c for c in df.columns if c not in (date_col, amount_col)]
        if candidates:
            desc_col = max(candidates, key=lambda c: df[c].astype(str).str.len().mean())
        else:
            desc_col = date_col

    out = pd.DataFrame()
    out['date_raw']   = df[date_col]
    out['merchant']   = df[desc_col].astype(str)
    out['amount_raw'] = df[amount_col]

    out['amount_signed'] = out['amount_raw'].apply(_parse_signed_amount)
    out['amount'] = out['amount_signed'].abs()

    def guess_direction(row):
        text = str(row['merchant']).lower()
        if row['amount_signed'] < 0 or 'paid' in text or 'debit' in text or 'sent' in text:
            return 'Debit'
        if row['amount_signed'] > 0 or 'received' in text or 'credit' in text:
            return 'Credit'
        return 'Debit'

    out['txn_direction'] = out.apply(guess_direction, axis=1)

    out['date'] = pd.to_datetime(out['date_raw'], errors='coerce', dayfirst=True)
    if out['date'].isna().mean() > 0.5:
        out['date'] = pd.to_datetime(out['date_raw'], errors='coerce', format='mixed', dayfirst=True)

    out['category'] = out['merchant'].apply(auto_categorize)

    return out


# ── Main cleaning entry point ──────────────────────────────────
def clean_data(df, app_name):
    df = df.copy()

    # Clean column names
    df.columns = [str(c).strip() for c in df.columns]

    # Remove duplicate columns
    df = df.loc[:, ~df.columns.duplicated()]

    # Reset index
    df = df.reset_index(drop=True)

    # Debug (remove later)
    print("APP:", app_name)
    print("COLUMNS:", df.columns.tolist())

    if app_name == 'PDF':
        df = _clean_pdf_generic(df)
    elif app_name == 'Paytm':
        df = _clean_paytm(df)
    elif app_name == 'PhonePe':
        df = _clean_phonepe(df)
    else:
        df = _clean_gpay(df)

    # Remove duplicate columns again after renaming
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)

    # Required columns check
    required_cols = ['date', 'amount']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    df = df.dropna(subset=['date', 'amount'])
    df = df[df['amount'] > 0]

    df['hour'] = df['date'].dt.hour
    df['day_of_week'] = df['date'].dt.strftime('%A')
    df['month'] = df['date'].dt.strftime('%B')
    df['month_num'] = df['date'].dt.month

    if 'merchant' not in df.columns:
        df['merchant'] = 'Unknown'

    if 'category' not in df.columns or df['category'].isna().all():
        df['category'] = df['merchant'].apply(auto_categorize)

    if 'status' not in df.columns:
        df['status'] = 'Success'

    df['status'] = df['status'].fillna('Success')

    if 'transaction_id' not in df.columns:
        df['transaction_id'] = [
            f"TXN{str(i).zfill(6)}"
            for i in range(len(df))
        ]

    if len(df) > 0:
        Q1 = df['amount'].quantile(0.25)
        Q3 = df['amount'].quantile(0.75)
        IQR = Q3 - Q1
        df['is_anomaly'] = df['amount'] > (Q3 + 3 * IQR)
    else:
        df['is_anomaly'] = False

    keep_cols = [
        'transaction_id',
        'date',
        'hour',
        'day_of_week',
        'month',
        'month_num',
        'amount',
        'merchant',
        'category',
        'status',
        'is_anomaly'
    ]

    if 'txn_direction' in df.columns:
        keep_cols.append('txn_direction')

    keep_cols = [c for c in keep_cols if c in df.columns]

    return df[keep_cols].reset_index(drop=True)


# ── Aggregation helpers ─────────────────────────────────────────
def get_kpis(df):
    success_df = df[df['status'].astype(str).str.lower().str.contains('success', na=False)]
    has_dir = 'txn_direction' in df.columns
    debit_df = df[df['txn_direction'] == 'Debit'] if has_dir else df

    return {
        'total_transactions': len(df),
        'total_spend':        round(debit_df['amount'].sum(), 2),
        'total_received':     round(df[df['txn_direction'] == 'Credit']['amount'].sum(), 2) if has_dir else 0,
        'avg_transaction':    round(df['amount'].mean(), 2) if len(df) else 0,
        'max_transaction':    round(df['amount'].max(), 2) if len(df) else 0,
        'anomaly_count':      int(df['is_anomaly'].sum()),
        'success_rate':       round(success_df.shape[0] / len(df) * 100, 1) if len(df) else 0,
        'failed_count':       int(df['status'].astype(str).str.lower().str.contains('fail', na=False).sum()),
    }


def get_heatmap_data(df):
    order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    df = df.copy()
    df['day_of_week'] = pd.Categorical(df['day_of_week'], categories=order, ordered=True)
    return (
        df.groupby(['day_of_week','hour'], observed=False)['amount']
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
    out = df.groupby(df['date'].dt.date)['amount'].sum().reset_index()
    out.columns = ['date', 'amount']
    return out


def get_status_data(df):
    return df['status'].value_counts().reset_index()


def get_anomalies(df):
    cols = ['transaction_id','date','merchant','category','amount','status']
    cols = [c for c in cols if c in df.columns]
    return df[df['is_anomaly']][cols].sort_values('amount', ascending=False)