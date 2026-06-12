import pdfplumber
import re


def _load_pdf(uploaded_file):
    """Extract full text from all pages of a PDF."""
    full_text = []
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ''
            full_text.append(text)
    return '\n'.join(full_text)


def _detect_pdf_type(text):
    if 'paytm' in text.lower() and 'passbook' in text.lower():
        return 'Paytm'
    if 'phonepe' in text.lower() and 'transaction statement' in text.lower():
        return 'PhonePe'
    return 'Generic'


# ── PhonePe PDF parser ──────────────────────────────────────────
def _parse_phonepe_pdf(text):
    """
    Parses PhonePe 'Transaction Statement' PDF text.
    Each entry looks like:
        Dec 06, 2023
        06:52 PM
        Received from Shivam Bharti
        Transaction ID : T2312061852211880610860
        UTR No : 370694786801
        Credited to XX6168
        Credit INR 500.00
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    date_pat = re.compile(r'^[A-Za-z]{3}\s+\d{1,2},\s+\d{4}$')
    time_pat = re.compile(r'^\d{1,2}:\d{2}\s+(AM|PM)$', re.IGNORECASE)
    type_amount_pat = re.compile(
        r'^(Credit|Debit)\s+INR\s*([\d,]+\.\d{2})$', re.IGNORECASE
    )

    rows = []
    i = 0
    n = len(lines)

    while i < n:
        if date_pat.match(lines[i]):
            date_str = lines[i]
            time_str = ''
            j = i + 1
            if j < n and time_pat.match(lines[j]):
                time_str = lines[j]
                j += 1

            # Description = first line after date/time
            desc_lines = []
            txn_type = None
            amount = None

            while j < n and not date_pat.match(lines[j]):
                m = type_amount_pat.match(lines[j])
                if m:
                    txn_type = m.group(1).capitalize()
                    amount = m.group(2)
                    j += 1
                    break
                # Stop collecting description once we hit metadata lines
                if not (lines[j].startswith('Transaction ID') or
                        lines[j].startswith('UTR No') or
                        lines[j].lower().startswith('credited to') or
                        lines[j].lower().startswith('debited from')):
                    desc_lines.append(lines[j])
                j += 1

                # Handle case where amount wrapped onto next line
                if j < n:
                    m2 = type_amount_pat.match(lines[j])
                    if txn_type is None and m2:
                        txn_type = m2.group(1).capitalize()
                        amount = m2.group(2)
                        j += 1
                        break
                    # handle "Credit INR" on one line and amount on next
                    if txn_type is None and re.match(r'^(Credit|Debit)\s+INR$', lines[j], re.IGNORECASE):
                        ctype = lines[j].split()[0].capitalize()
                        if j + 1 < n and re.match(r'^[\d,]+\.\d{2}$', lines[j+1]):
                            txn_type = ctype
                            amount = lines[j+1]
                            j += 2
                            break

            if amount is not None:
                rows.append({
                    'date_raw': f'{date_str} {time_str}',
                    'merchant': ' '.join(desc_lines).strip(),
                    'amount_raw': amount,
                    'txn_direction_raw': txn_type,
                })

            i = j
        else:
            i += 1

    if not rows:
        raise ValueError('No transactions found. Please upload a valid PhonePe statement.')

    return pd.DataFrame(rows)


# ── Paytm PDF parser ─────────────────────────────────────────────
def _parse_paytm_pdf(text):
    """
    Parses Paytm 'Passbook Payments History' PDF text.
    Each entry looks like:
        23 Mar
        5:58 PM
        Paid to Maa Khodal Fashion
        UPI ID: yv7qyhe97sda@idbi
        UPI Ref No: 544825282515
        - Rs.999.06
    """
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    date_pat = re.compile(r'^\d{1,2}\s+[A-Za-z]{3}$')
    time_pat = re.compile(r'^\d{1,2}:\d{2}\s+(AM|PM)$', re.IGNORECASE)
    amount_pat = re.compile(r'^([+-])\s*Rs\.?\s*([\d,]+(?:\.\d{1,2})?)$')

    # Determine statement year range from header e.g. "1 APR'24 - 31 MAR'25"
    year_match = re.search(r"(\d{1,2})\s+([A-Za-z]{3})'(\d{2})\s*-\s*(\d{1,2})\s+([A-Za-z]{3})'(\d{2})", text)
    start_year = end_year = None
    start_month = end_month = None
    if year_match:
        start_month = year_match.group(2)
        start_year = 2000 + int(year_match.group(3))
        end_month = year_match.group(5)
        end_year = 2000 + int(year_match.group(6))

    months_order = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

    def resolve_year(month_str):
        """Resolve the year for a transaction month based on statement range."""
        if start_year is None:
            return datetime_now_year()
        if start_year == end_year:
            return start_year
        # statement spans two years (e.g. Apr'24 - Mar'25)
        try:
            m_idx = months_order.index(month_str)
            start_idx = months_order.index(start_month)
        except ValueError:
            return end_year
        # If month is >= start month index, it's in start_year, else end_year
        if m_idx >= start_idx:
            return start_year
        else:
            return end_year

    def datetime_now_year():
        from datetime import datetime
        return datetime.now().year

    rows = []
    i = 0
    n = len(lines)

    while i < n:
        if date_pat.match(lines[i]) and i + 1 < n and time_pat.match(lines[i+1]):
            day_month = lines[i]
            time_str = lines[i+1]
            j = i + 2

            desc_lines = []
            amount = None
            direction = None

            while j < n:
                if date_pat.match(lines[j]) and j + 1 < n and time_pat.match(lines[j+1]):
                    break
                m = amount_pat.match(lines[j])
                if m:
                    direction = 'Credit' if m.group(1) == '+' else 'Debit'
                    amount = m.group(2)
                    j += 1
                    break
                if not (lines[j].startswith('UPI ID') or
                        lines[j].startswith('UPI Ref') or
                        lines[j].startswith('Note:') or
                        lines[j].lower().startswith('union bank') or
                        lines[j].lower().startswith('of india') or
                        re.match(r'^\(?\d+\s+payments?', lines[j], re.IGNORECASE)):
                    desc_lines.append(lines[j])
                j += 1

            if amount is not None:
                day, mon = day_month.split()
                year = resolve_year(mon)
                rows.append({
                    'date_raw': f'{day} {mon} {year} {time_str}',
                    'merchant': ' '.join(desc_lines).strip(),
                    'amount_raw': amount,
                    'txn_direction_raw': direction,
                })

            i = j
        else:
            i += 1

    if not rows:
        raise ValueError('No transactions found. Please upload a valid Paytm passbook statement.')

    return pd.DataFrame(rows)


def _load_pdf_to_df(uploaded_file):
    """Load PDF, detect type, return (df, pdf_type)."""
    text = _load_pdf(uploaded_file)
    pdf_type = _detect_pdf_type(text)

    if pdf_type == 'Paytm':
        df = _parse_paytm_pdf(text)
    elif pdf_type == 'PhonePe':
        df = _parse_phonepe_pdf(text)
    else:
        raise ValueError(
            'Could not recognize this PDF format. '
            'Currently supported: Paytm Passbook PDF, PhonePe Transaction Statement PDF.'
        )

    return df, pdf_type