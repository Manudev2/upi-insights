import streamlit as st
import pandas as pd
from processor import (
    load_file, clean_data, get_kpis,
    get_heatmap_data, get_category_data, get_merchant_data,
    get_monthly_trend, get_daily_trend, get_status_data, get_anomalies
)
from charts import (
    plot_heatmap, plot_daily_trend, plot_monthly_trend,
    plot_category_bar, plot_category_pie, plot_merchant_bar,
    plot_status_pie, plot_anomaly_scatter, plot_weekday_bar
)

st.set_page_config(page_title='UPI Insights', page_icon='◈', layout='wide')

# ── Global CSS ────────────────────────────────────────────────
# Design note: this app reads bank/UPI passbooks, so the visual
# language borrows from a ledger — a deep ink-navy surface, figures
# set in monospace the way a statement prints them, and a two-tone
# accent system (green for money in, coral for money out) that does
# real work: it lets you read a debit vs. credit at a glance before
# you've read a single number. One signature moment (the hero mark
# and glow) carries the boldness; everything else stays disciplined.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --bg:          #0b0e13;
    --surface:     #151922;
    --surface-hi:  #1b202b;
    --border:      #262b36;
    --border-hi:   #34404f;
    --text:        #edeff3;
    --muted:       #868da0;
    --in:          #5fc990;
    --in-dim:      rgba(95,201,144,0.13);
    --out:         #e08a6f;
    --out-dim:     rgba(224,138,111,0.13);
    --accent:      #5fc990;
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.main { background: var(--bg) !important; }
.block-container { padding: 2rem 3rem 3rem !important; max-width: 1240px; }
#MainMenu, footer, header { visibility: hidden; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation-duration: 0.001ms !important; transition-duration: 0.001ms !important; } }

/* ── Hero ───────────────────────────────────────────────── */
.hero {
    position: relative; overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 44px 44px 32px;
    margin-bottom: 32px;
    background: radial-gradient(120% 140% at 12% 0%, rgba(95,201,144,0.10), transparent 55%),
                linear-gradient(155deg, #12151d 0%, #0d1016 100%);
}
.hero::after {
    content: ''; position: absolute; top: -120px; right: -120px;
    width: 320px; height: 320px; border-radius: 50%;
    background: radial-gradient(circle, rgba(95,201,144,0.16) 0%, transparent 70%);
    pointer-events: none;
}
.hero-top { display: flex; align-items: center; gap: 14px; margin-bottom: 18px; }
.hero-mark {
    width: 42px; height: 42px; border-radius: 12px;
    border: 1px solid var(--border-hi);
    background: linear-gradient(155deg, var(--surface-hi), var(--surface));
    display: flex; align-items: center; justify-content: center;
    font-family: 'Space Grotesk', sans-serif; font-size: 1.25rem; color: var(--in);
    box-shadow: 0 0 0 4px rgba(95,201,144,0.06);
    animation: pulse-glow 3.5s ease-in-out infinite;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 0 4px rgba(95,201,144,0.06); }
    50%      { box-shadow: 0 0 0 8px rgba(95,201,144,0.12); }
}
.hero-kicker { font-family: 'IBM Plex Mono', monospace; font-size: 0.72rem; color: var(--muted); letter-spacing: 0.08em; text-transform: uppercase; }
.hero h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 2.6rem !important; font-weight: 700 !important;
    margin: 0 0 8px 0 !important; letter-spacing: -0.02em; line-height: 1.05 !important;
    color: var(--text) !important;
}
.hero h1 span {
    background: linear-gradient(90deg, var(--in), #7fd9c4);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;
}
.hero p.sub { color: var(--muted) !important; font-size: 1rem !important; margin: 0 0 22px 0 !important; max-width: 520px; }
.chip-row { display: flex; gap: 10px; flex-wrap: wrap; }
.chip {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; color: var(--text);
    border: 1px solid var(--border-hi); background: rgba(255,255,255,0.02);
    border-radius: 20px; padding: 6px 14px 6px 12px;
    display: flex; align-items: center; gap: 7px;
}
.chip .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--in); }

/* ── Section titles ─────────────────────────────────────── */
.section-title {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.15rem !important; font-weight: 600 !important;
    color: var(--text) !important; margin: 40px 0 16px 0 !important;
    display: flex; align-items: center; gap: 12px;
}
.section-title .idx {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.68rem;
    color: var(--in); border: 1px solid var(--border-hi);
    background: var(--in-dim);
    border-radius: 6px; padding: 3px 7px;
}
.section-title::after { content:''; flex:1; height:1px; background: linear-gradient(90deg, var(--border), transparent); }

/* ── Custom metric cards (replaces st.metric for color coding) ── */
.metric-card {
    background: linear-gradient(160deg, var(--surface-hi), var(--surface));
    border: 1px solid var(--border);
    border-left: 3px solid var(--m-accent, var(--border-hi));
    border-radius: 12px; padding: 16px 18px;
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
    height: 100%;
}
.metric-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(0,0,0,0.35); border-color: var(--m-accent, var(--border-hi)); }
.metric-label { color: var(--muted); font-size: 0.7rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 8px; }
.metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.4rem; font-weight: 600; color: var(--text); }
.metric-sub { font-size: 0.7rem; color: var(--muted); margin-top: 4px; }

/* ── Charts & tables ────────────────────────────────────── */
[data-testid="stPlotlyChart"], .stPyplot {
    background: linear-gradient(160deg, var(--surface-hi), var(--surface)) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important; padding: 14px !important;
}
[data-testid="stDataFrame"] { background: var(--surface) !important; border-radius: 12px !important; border: 1px solid var(--border) !important; }

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] { background: var(--bg) !important; border-color: var(--border) !important; }

/* ── Buttons ────────────────────────────────────────────── */
.stButton > button {
    background: var(--surface-hi) !important; color: var(--text) !important;
    border: 1px solid var(--border-hi) !important; border-radius: 9px !important;
    font-weight: 500 !important; padding: 10px 18px !important;
    transition: all 0.15s ease !important; width: 100% !important;
}
.stButton > button:hover {
    border-color: var(--in) !important; color: var(--in) !important;
    box-shadow: 0 6px 18px rgba(95,201,144,0.15) !important; transform: translateY(-1px) !important;
}
.stDownloadButton > button {
    background: var(--in-dim) !important; color: var(--in) !important;
    border: 1px solid var(--in) !important; border-radius: 9px !important;
    font-weight: 600 !important; width: auto !important;
}
.stDownloadButton > button:hover { background: var(--in) !important; color: #08110c !important; }

/* ── Uploader / expander / alerts ───────────────────────── */
[data-testid="stFileUploader"] {
    background: var(--surface) !important; border: 1.5px dashed var(--border-hi) !important;
    border-radius: 14px !important; padding: 18px !important; transition: border-color 0.15s ease !important;
}
[data-testid="stFileUploader"]:hover { border-color: var(--in) !important; }
[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; }
.stAlert { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 12px !important; color: var(--text) !important; }
hr { border-color: var(--border) !important; margin: 28px 0 !important; }

/* ── Empty state ────────────────────────────────────────── */
.empty-state {
    text-align: center; padding: 68px 20px;
    border: 1px dashed var(--border-hi); border-radius: 18px; margin-top: 16px;
    background: radial-gradient(80% 100% at 50% 0%, rgba(95,201,144,0.05), transparent 60%);
}
.empty-state .mark {
    width: 56px; height: 56px; margin: 0 auto 18px;
    border-radius: 16px; display: flex; align-items: center; justify-content: center;
    border: 1px solid var(--border-hi); background: var(--surface-hi);
    font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; color: var(--in);
    animation: pulse-glow 3.5s ease-in-out infinite;
}
.empty-state h3 {
    font-family: 'Space Grotesk', sans-serif !important; color: var(--text) !important;
    font-size: 1.3rem !important; font-weight: 600 !important; margin-bottom: 6px !important;
}
.empty-state .desc { color: var(--muted); font-size: 0.92rem; }
.feature-row { display: flex; gap: 12px; justify-content: center; margin-top: 26px; flex-wrap: wrap; }
.feature-chip {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; color: var(--muted);
    border: 1px solid var(--border-hi); border-radius: 20px; padding: 7px 15px;
    transition: border-color 0.15s ease, color 0.15s ease;
}
.feature-chip:hover { border-color: var(--in); color: var(--in); }

.footer { text-align: center; padding: 22px; color: var(--muted) !important; font-size: 0.78rem; border-top: 1px solid var(--border); margin-top: 46px; }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <div class="hero-top">
        <div class="hero-mark">◈</div>
        <div class="hero-kicker">Passbook · Statement · Ledger reader</div>
    </div>
    <h1>Every transaction,<br><span>read clearly.</span></h1>
    <p class="sub">Drop in a UPI or bank statement — CSV, Excel, or PDF — and see spend, categories, and anomalies in seconds.</p>
    <div class="chip-row">
        <span class="chip"><span class="dot"></span>Multi-format</span>
        <span class="chip"><span class="dot"></span>Auto-categorized</span>
        <span class="chip"><span class="dot"></span>Anomaly detection</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────
st.markdown('<div class="section-title"><span class="idx">◈</span>Upload</div>', unsafe_allow_html=True)
u1, u2 = st.columns([3, 2])
with u1:
    uploaded_file = st.file_uploader(
        'Drop your CSV, Excel, or PDF statement',
        type=['csv', 'xlsx', 'xls', 'pdf'],
        label_visibility='visible'
    )
with u2:
    st.markdown("""
    <div class="chip-row" style="margin-top:8px;">
        <span class="chip"><span class="dot"></span>GPay .csv</span>
        <span class="chip"><span class="dot"></span>PhonePe .csv/.xlsx</span>
        <span class="chip"><span class="dot"></span>Paytm .xlsx/.pdf</span>
        <span class="chip"><span class="dot"></span>Any bank .pdf</span>
    </div>
    """, unsafe_allow_html=True)

b1, b2, b3 = st.columns(3)
load_gpay    = b1.button('Try a GPay sample')
load_phonepe = b2.button('Try a PhonePe sample')
load_paytm   = b3.button('Try a Paytm sample')

def make_sample(app):
    import numpy as np
    from datetime import datetime, timedelta
    import random
    np.random.seed(42); random.seed(42)
    CATEGORIES = {
        'Food & Dining':  ['Zomato','Swiggy',"McDonald's",'Dominos','KFC'],
        'Shopping':       ['Amazon','Flipkart','Myntra','Meesho','Ajio'],
        'Utilities':      ['Electricity Board','Gas Agency','Water Bill','Broadband'],
        'Transport':      ['Ola','Uber','Rapido','Metro Card','IRCTC'],
        'Entertainment':  ['Netflix','Hotstar','Spotify','BookMyShow'],
        'Groceries':      ['BigBasket','Blinkit','JioMart','DMart','Zepto'],
        'Healthcare':     ['Apollo Pharmacy','Netmeds','1mg','Practo'],
        'Education':      ['Udemy','Coursera',"BYJU'S",'Unacademy'],
        'Bank Transfer':  ['Personal Transfer','Family Transfer','EMI Payment','Rent'],
        'Utilities & Recharge': ['Airtel','Jio','Vi','BSNL'],
    }
    AMOUNTS = {
        'Food & Dining':(50,1500),'Shopping':(200,15000),
        'Utilities':(100,5000),'Transport':(20,800),
        'Entertainment':(99,999),'Groceries':(100,3000),
        'Healthcare':(50,2000),'Education':(199,9999),
        'Bank Transfer':(500,50000),'Utilities & Recharge':(19,999),
    }
    START = datetime(2024,1,1); END = datetime(2024,12,31)
    rows = []
    for i in range(2000):
        cat = random.choice(list(CATEGORIES.keys()))
        mer = random.choice(CATEGORIES[cat])
        lo,hi = AMOUNTS[cat]
        amt = round(random.uniform(lo,hi), 2)
        dt  = START + timedelta(seconds=random.randint(0,int((END-START).total_seconds())))
        sts = random.choices(['Success','Failed','Pending'], weights=[87,9,4])[0]
        if random.random() < 0.03:
            amt = round(amt * random.uniform(5,20), 2)
        rows.append({
            'Date': dt.strftime('%d %b, %Y'),
            'Time': dt.strftime('%I:%M %p'),
            'Transaction': mer,
            'Amount': amt,
        })
    return pd.DataFrame(rows)

# ── Load Data ─────────────────────────────────────────────────
df = None; app_name = None; raw_df = None

if load_gpay:
    raw_df = make_sample('GPay'); app_name = 'GPay'
    st.success('Sample GPay data loaded — 2,000 transactions.')
elif load_phonepe:
    raw_df = make_sample('PhonePe'); app_name = 'GPay'
    st.success('Sample PhonePe data loaded — 2,000 transactions.')
elif load_paytm:
    raw_df = make_sample('Paytm'); app_name = 'GPay'
    st.success('Sample Paytm data loaded — 2,000 transactions.')
elif uploaded_file is not None:
    try:
        with st.spinner('Reading file…'):
            raw_df, app_name = load_file(uploaded_file)
        st.success(f'Detected **{app_name}** — {len(raw_df):,} rows loaded.')
    except Exception as e:
        st.error(f'Error reading file: {e}')

# ── Process data ──────────────────────────────────────────────
if raw_df is not None:
    try:
        df = clean_data(raw_df, app_name)
    except Exception as e:
        st.error(f'Error processing data: {e}')
        df = None

# ── Dashboard ─────────────────────────────────────────────────
if df is not None and len(df) > 0:
    st.sidebar.markdown(f"""
    <div style='padding:14px 0 6px 0;'>
        <div style='font-family:"Space Grotesk",sans-serif; font-size:1.1rem; font-weight:700; color:#e7e9ee;'>
            UPI Insights
        </div>
        <div style='font-size:11px; color:#8a8f9c; margin-top:2px;'>Source · {app_name}</div>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown('---')
    st.sidebar.markdown('**Filters**')

    categories = st.sidebar.multiselect(
        'Category', options=sorted(df['category'].unique()),
        default=list(df['category'].unique())
    )
    status_list = st.sidebar.multiselect(
        'Status', options=df['status'].unique(),
        default=list(df['status'].unique())
    )
    if 'txn_direction' in df.columns:
        direction_list = st.sidebar.multiselect(
            'Direction', options=df['txn_direction'].unique(),
            default=list(df['txn_direction'].unique())
        )
    else:
        direction_list = None

    date_range = st.sidebar.date_input(
        'Date range',
        value=[df['date'].min().date(), df['date'].max().date()]
    )
    st.sidebar.markdown('---')
    st.sidebar.markdown(f"""
    <div style='border:1px solid #262b36; border-radius:8px; padding:10px; text-align:center;'>
        <div style='font-family:"IBM Plex Mono",monospace; font-size:1.2rem; font-weight:600; color:#5fc990;'>{len(df):,}</div>
        <div style='font-size:11px; color:#8a8f9c;'>Total records</div>
    </div>
    """, unsafe_allow_html=True)

    fdf = df.copy()
    if categories:
        fdf = fdf[fdf['category'].isin(categories)]
    if status_list:
        fdf = fdf[fdf['status'].isin(status_list)]
    if direction_list:
        fdf = fdf[fdf['txn_direction'].isin(direction_list)]
    if len(date_range) == 2:
        fdf = fdf[
            (fdf['date'] >= pd.to_datetime(date_range[0])) &
            (fdf['date'] <= pd.to_datetime(date_range[1]) + pd.Timedelta(days=1))
        ]

    if len(fdf) == 0:
        st.warning('No transactions match the selected filters.')
    else:
        st.markdown('<div class="section-title"><span class="idx">01</span>Summary</div>', unsafe_allow_html=True)
        kpis = get_kpis(fdf)

        def metric_card(label, value, accent=None, sub=None):
            style = f"--m-accent:{accent};" if accent else ""
            sub_html = f'<div class="metric-sub">{sub}</div>' if sub else ""
            return f"""
            <div class="metric-card" style="{style}">
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
                {sub_html}
            </div>
            """

        if 'txn_direction' in fdf.columns:
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            k1.markdown(metric_card('Transactions', f"{kpis['total_transactions']:,}"), unsafe_allow_html=True)
            k2.markdown(metric_card('Spent',    f"₹{kpis['total_spend']:,.0f}",    accent='var(--out)'), unsafe_allow_html=True)
            k3.markdown(metric_card('Received', f"₹{kpis['total_received']:,.0f}", accent='var(--in)'), unsafe_allow_html=True)
            k4.markdown(metric_card('Highest', f"₹{kpis['max_transaction']:,.0f}"), unsafe_allow_html=True)
            k5.markdown(metric_card('Success rate', f"{kpis['success_rate']}%", accent='var(--in)'), unsafe_allow_html=True)
            k6.markdown(metric_card('Anomalies', f"{kpis['anomaly_count']}", accent='var(--out)' if kpis['anomaly_count'] else None), unsafe_allow_html=True)
        else:
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            k1.markdown(metric_card('Transactions', f"{kpis['total_transactions']:,}"), unsafe_allow_html=True)
            k2.markdown(metric_card('Spend', f"₹{kpis['total_spend']:,.0f}", accent='var(--out)'), unsafe_allow_html=True)
            k3.markdown(metric_card('Avg / txn', f"₹{kpis['avg_transaction']:,.0f}"), unsafe_allow_html=True)
            k4.markdown(metric_card('Highest', f"₹{kpis['max_transaction']:,.0f}"), unsafe_allow_html=True)
            k5.markdown(metric_card('Success rate', f"{kpis['success_rate']}%", accent='var(--in)'), unsafe_allow_html=True)
            k6.markdown(metric_card('Anomalies', f"{kpis['anomaly_count']}", accent='var(--out)' if kpis['anomaly_count'] else None), unsafe_allow_html=True)

        st.markdown('<div class="section-title"><span class="idx">02</span>Over time</div>', unsafe_allow_html=True)
        c1, c2 = st.columns([2,1])
        with c1:
            st.plotly_chart(plot_daily_trend(get_daily_trend(fdf)), width='stretch')
        with c2:
            st.plotly_chart(plot_status_pie(get_status_data(fdf)), width='stretch')

        st.markdown('<div class="section-title"><span class="idx">03</span>Peak hours</div>', unsafe_allow_html=True)
        st.pyplot(plot_heatmap(get_heatmap_data(fdf)))

        st.markdown('<div class="section-title"><span class="idx">04</span>Where it goes</div>', unsafe_allow_html=True)
        c3, c4 = st.columns(2)
        with c3:
            st.plotly_chart(plot_category_pie(get_category_data(fdf)), width='stretch')
        with c4:
            st.plotly_chart(plot_weekday_bar(fdf), width='stretch')

        c5, c6 = st.columns(2)
        with c5:
            st.plotly_chart(plot_category_bar(get_category_data(fdf)), width='stretch')
        with c6:
            st.plotly_chart(plot_merchant_bar(get_merchant_data(fdf)), width='stretch')

        st.markdown('<div class="section-title"><span class="idx">05</span>Monthly breakdown</div>', unsafe_allow_html=True)
        st.plotly_chart(plot_monthly_trend(get_monthly_trend(fdf)), width='stretch')

        st.markdown('<div class="section-title"><span class="idx">06</span>Suspicious transactions</div>', unsafe_allow_html=True)
        a1, a2 = st.columns(2)
        with a1:
            st.plotly_chart(plot_anomaly_scatter(fdf), width='stretch')
        with a2:
            anomalies = get_anomalies(fdf)
            st.markdown(f"""
            <div style='border:1px solid #262b36; background:rgba(224,138,111,0.10); border-radius:8px; padding:12px 16px; margin-bottom:10px;'>
                <span style='color:#e08a6f; font-weight:600;'>{len(anomalies)} flagged</span>
                <span style='color:#8a8f9c; font-size:12px; margin-left:8px;'>transactions well outside the normal range</span>
            </div>
            """, unsafe_allow_html=True)
            st.dataframe(anomalies, width='stretch', height=280)

        with st.expander('View all transactions'):
            st.dataframe(fdf, width='stretch', height=300)

        st.download_button(
            'Download filtered CSV',
            data=fdf.to_csv(index=False),
            file_name=f'{app_name}_transactions.csv',
            mime='text/csv'
        )

elif raw_df is not None and df is not None and len(df) == 0:
    st.warning('The file was read but no valid transactions were found after cleaning. Please check the file format.')

else:
    st.markdown("""
    <div class="empty-state">
        <div class="mark">◈</div>
        <h3>Nothing loaded yet</h3>
        <div class="desc">Upload a statement above, or try a sample to explore the dashboard.</div>
        <div class="feature-row">
            <span class="feature-chip">Summary</span>
            <span class="feature-chip">Peak hours</span>
            <span class="feature-chip">Categories</span>
            <span class="feature-chip">Anomalies</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<div class="footer">UPI Insights · built with Streamlit</div>
""", unsafe_allow_html=True)