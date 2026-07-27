import pandas as pd
import numpy as np
import pdfplumber
import re
import csv

print("=== PROCESSOR VERSION: v4-csv-messy-fix ===")


# ── Categorization ───────────────────────────────────────────
_CATEGORY_KEYWORDS = {
    'Food & Dining':  ['zomato','swiggy','food','restaurant','cafe','pizza','burger','kfc','domino'],
    'Shopping':       ['amazon','flipkart','myntra','shop','store','mall','meesho','ajio','shopping'],
    'Utilities & Recharge': ['electricity','gas','water','bill','broadband','dth','recharge','airtel','jio','bsnl','vi'],
    'Transport':      ['ola','uber','rapido','metro','irctc','bus','train','flight','travel','petrol'],
    'Entertainment':  ['netflix','hotstar','spotify','bookmyshow','prime','zee','movie','youtube'],
    'Groceries':      ['bigbasket','blinkit','grocer','supermarket','dmart','zepto','instamart','vegetable'],
    'Healthcare':     ['apollo','pharmacy','hospital','doctor','medical','health','netmeds','1mg'],
    'Education':      ['udemy','coursera','byju','school','college','education','unacademy'],
    'Bank Transfer':  ['transfer','sent','received','self','neft','imps','emi','loan','atm'],
}


def auto_categorize(text):
    text = str(text).lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                return category
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
    if 'transaction id' in cols and 'payment method' in cols and 'description' in cols:
        return 'Google Play'
    if 'transaction' in cols and 'amount' in cols:
        return 'GPay'
    return 'GPay'


# ── PDF extraction ───────────────────────────────────────────

_MONTHS = {m: i + 1 for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
)}

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
    import pdfplumber, pandas as pd, re

    try:
        uploaded_file.seek(0)
    except Exception:
        pass

    raw_rows = []
    with pdfplumber.open(uploaded_file) as pdf:
        header_txt = pdf.pages[0].extract_text() or ""
        m = re.search(r"Statement for\s+\d{1,2}\s\w+'\d{2}\s+-\s+\d{1,2}\s\w+'(\d{2})", header_txt)
        end_year = 2000 + int(m.group(1)) if m else 2025

        for page in pdf.pages:
            words = page.extract_words()
            if not words:
                continue

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

    parsed = []
    for r in raw_rows:
        m = re.match(r'^(\d{1,2})\s([A-Za-z]{3}).*?(\d{1,2}:\d{2}\s?[AP]M)', r['dt'])
        if not m or 'Rs.' not in r['amt']:
            continue
        day, mon, time_ = m.group(1), m.group(2), m.group(3)

        det_text = r['det']
        det_text = re.sub(r'\s*UPI ID:.*?(?=UPI Ref No:|$)', ' ', det_text)
        det_text = re.sub(r'\s*UPI Ref No:.*$', '', det_text)
        det_text = re.sub(r'\bon\b\s*$', '', det_text).strip()
        det_text = re.sub(r'\s+', ' ', det_text)

        # Paytm's "Notes & Tags" column carries two unrelated things: a
        # real category tag ("Tag: food") or a free-text payment note
        # ("Note: 5p9bb", "Note: Upi Transaction"). Only a "Tag:" is a
        # genuine spending category - a "Note:" is arbitrary text (a UPI
        # note/reference code) and must NOT be treated as a category, or
        # transactions end up labelled "Note 5p9bb" etc. Keep tags_text
        # empty for anything that isn't actually a Tag.
        notes_raw = r['notes'].strip()
        tag_match = re.match(r'^Tag:\s*(.*)$', notes_raw, flags=re.IGNORECASE)
        tags_text = tag_match.group(1).strip() if tag_match else ''

        parsed.append({
            'day': day, 'mon': mon, 'time': time_,
            'merchant': det_text or 'Unknown',
            'amount_raw': r['amt'].strip(),
            'tags_raw': tags_text,
            'account': r['acct'].strip(),
        })

    if not parsed:
        raise ValueError("No transactions found in this PDF.")

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


def _load_messy_csv(uploaded_file):
    try:
        uploaded_file.seek(0)
    except Exception:
        pass
    raw = uploaded_file.read()
    if isinstance(raw, bytes):
        raw = raw.decode('utf-8', errors='replace')
    raw_lines = raw.splitlines(keepends=True)

    header_idx = None
    for i, line in enumerate(raw_lines[:15]):
        if not line.strip():
            continue
        parts = next(csv.reader([line]))
        if len(parts) >= 4:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("Could not find a table header in this CSV.")

    header = next(csv.reader([raw_lines[header_idx]]))
    ncols = len(header)

    data_rows = []
    for line in raw_lines[header_idx + 1:]:
        if not line.strip():
            continue
        parts = next(csv.reader([line]))
        if len(parts) != ncols:
            break
        data_rows.append(parts)

    if not data_rows:
        raise ValueError("No transaction rows found in this CSV.")

    return pd.DataFrame(data_rows, columns=header)


def load_file(uploaded_file):
    filename = uploaded_file.name
    fname_lower = filename.lower()

    if fname_lower.endswith('.pdf'):
        df = _load_pdf(uploaded_file)
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
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        try:
            df = pd.read_csv(uploaded_file)
        except Exception:
            df = _load_messy_csv(uploaded_file)
        app_name = detect_app(filename, df)
        return df, app_name


def _parse_signed_amount(val):
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


def _clean_gpay(df):
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
        # tags_raw is empty for rows that had a "Note:" (or nothing) in
        # the PDF's Notes & Tags column, since _load_pdf only keeps real
        # "Tag:" values. For those rows, categorize from the merchant
        # text instead of falling back to a blank/garbage tag.
        df['category'] = df.apply(
            lambda r: _clean_paytm_tag(r['tags_raw'])
            if str(r['tags_raw']).strip() not in ('', 'nan')
            else auto_categorize(r['merchant']),
            axis=1
        )
    else:
        df['category'] = df['merchant'].apply(auto_categorize)

    return df


def _clean_phonepe(df):
    df = df.copy()
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
        elif cl in ['transaction','transaction details','details','remarks','remark']:
            rename_map[c] = 'merchant'
        elif cl in ['type', 'transaction type']:
            rename_map[c] = 'txn_type_raw'
    df = df.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]

    if 'amount_raw' not in df.columns:
        raise ValueError(f"Amount column not found. Columns are: {list(df.columns)}")
    if 'date_raw' not in df.columns:
        raise ValueError(f"Date column not found. Columns are: {list(df.columns)}")
    if 'merchant' not in df.columns:
        df['merchant'] = 'Unknown'

    df['date_raw'] = df['date_raw'].astype(str).str.strip()
    if 'time_raw' in df.columns:
        df['time_raw'] = df['time_raw'].astype(str).str.strip()

    df['amount'] = df['amount_raw'].apply(_parse_signed_amount).abs()

    date_parsed = pd.to_datetime(df['date_raw'], format='%Y-%m-%d', errors='coerce')
    if date_parsed.isna().mean() > 0.5:
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

    if 'txn_type_raw' in df.columns:
        df['txn_direction'] = df['txn_type_raw'].astype(str).apply(
            lambda x: 'Credit' if 'credit' in x.lower() else 'Debit'
        )
    else:
        df['txn_direction'] = 'Debit'

    df['category'] = df['merchant'].apply(auto_categorize)
    return df


def _clean_google_play(df):
    df = df.copy()
    rename_map = {}
    for c in df.columns:
        cl = str(c).strip().lower()
        if cl == 'time':
            rename_map[c] = 'date_raw'
        elif cl == 'description':
            rename_map[c] = 'merchant'
        elif cl == 'amount':
            rename_map[c] = 'amount_raw'
        elif cl == 'status':
            rename_map[c] = 'status_raw'
        elif cl == 'product':
            rename_map[c] = 'product'
    df = df.rename(columns=rename_map)

    df['date'] = pd.to_datetime(df['date_raw'], errors='coerce')

    df['amount_signed'] = df['amount_raw'].apply(_parse_signed_amount)
    df['amount'] = df['amount_signed'].abs()

    df['txn_direction'] = 'Debit'

    if 'status_raw' in df.columns:
        def norm_status(s):
            s = str(s).strip().lower()
            if s in ('complete', 'completed', 'success'):
                return 'Success'
            if s in ('cancelled', 'canceled', 'failed', 'declined'):
                return 'Failed'
            return str(s).title()
        df['status'] = df['status_raw'].apply(norm_status)
    else:
        df['status'] = 'Success'

    desc_source = df['merchant'] if 'merchant' in df.columns else df.get('product', 'Unknown')
    df['category'] = desc_source.apply(auto_categorize)
    if 'merchant' not in df.columns:
        df['merchant'] = df.get('product', 'Unknown')

    return df


def _clean_pdf_generic(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]

    date_col = None
    for c in df.columns:
        if 'date' in c:
            date_col = c
            break
    if date_col is None:
        date_col = df.columns[0]

    amount_col = None
    for c in df.columns:
        if 'amount' in c or 'amt' in c or 'debit' in c or 'credit' in c:
            amount_col = c
            break
    if amount_col is None:
        amount_col = df.columns[-1]

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


def clean_data(df, app_name):
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)

    print("APP:", app_name)
    print("COLUMNS:", df.columns.tolist())

    if app_name == 'PDF':
        df = _clean_pdf_generic(df)
    elif app_name == 'Paytm':
        df = _clean_paytm(df)
    elif app_name == 'PhonePe':
        df = _clean_phonepe(df)
    elif app_name == 'Google Play':
        df = _clean_google_play(df)
    else:
        df = _clean_gpay(df)

    df = df.loc[:, ~df.columns.duplicated()]
    df = df.reset_index(drop=True)

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
        df['transaction_id'] = [f"TXN{str(i).zfill(6)}" for i in range(len(df))]

    if len(df) > 0:
        Q1 = df['amount'].quantile(0.25)
        Q3 = df['amount'].quantile(0.75)
        IQR = Q3 - Q1
        df['is_anomaly'] = df['amount'] > (Q3 + 3 * IQR)
    else:
        df['is_anomaly'] = False

    keep_cols = ['transaction_id','date','hour','day_of_week','month','month_num',
                 'amount','merchant','category','status','is_anomaly']

    if 'txn_direction' in df.columns:
        keep_cols.append('txn_direction')

    keep_cols = [c for c in keep_cols if c in df.columns]

    return df[keep_cols].reset_index(drop=True)


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