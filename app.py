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

st.set_page_config(page_title='UPI Insights', page_icon='◇', layout='wide')

# ── Global CSS ────────────────────────────────────────────────
# Design note: this app reads bank/UPI passbooks, so the visual
# language borrows from a ledger — a quiet ink-navy surface, one
# accent (a muted ledger-green), and monospaced figures for amounts,
# the way a real statement prints them. One accent color, not four
# clashing brand colors; flat surfaces, not stacked gradients.
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
    --bg:        #0e1116;
    --surface:   #161a21;
    --border:    #262b35;
    --text:      #e7e9ee;
    --muted:     #8a8f9c;
    --accent:    #5fa87c;
    --accent-dim: rgba(95,168,124,0.14);
    --danger:    #d9765f;
    --danger-dim: rgba(217,118,95,0.12);
}

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.main { background: var(--bg) !important; }
.block-container { padding: 2.5rem 3rem 3rem !important; max-width: 1200px; }
#MainMenu, footer, header { visibility: hidden; }
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }

/* ── Header ─────────────────────────────────────────────── */
.app-header {
    display: flex; align-items: baseline; justify-content: space-between;
    border-bottom: 1px solid var(--border);
    padding-bottom: 20px; margin-bottom: 28px;
}
.app-header h1 {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.5rem !important; font-weight: 700 !important;
    color: var(--text) !important; margin: 0 !important;
    letter-spacing: -0.01em;
}
.app-header h1 span { color: var(--accent); }
.app-header p {
    color: var(--muted) !important; font-size: 0.85rem !important;
    margin: 0 !important;
}

/* ── Section titles ─────────────────────────────────────── */
.section-title {
    font-family: 'Space Grotesk', sans-serif !important;
    font-size: 1.05rem !important; font-weight: 600 !important;
    color: var(--text) !important; margin: 36px 0 14px 0 !important;
    display: flex; align-items: center; gap: 10px;
}
.section-title .idx {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.7rem;
    color: var(--accent); border: 1px solid var(--border);
    border-radius: 4px; padding: 2px 6px;
}

/* ── Metrics ────────────────────────────────────────────── */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important; padding: 16px 18px !important;
}
[data-testid="stMetricLabel"] {
    color: var(--muted) !important; font-size: 0.72rem !important;
    font-weight: 500 !important; text-transform: uppercase; letter-spacing: 0.06em;
}
[data-testid="stMetricValue"] {
    color: var(--text) !important; font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1.35rem !important; font-weight: 500 !important;
}

/* ── Charts & tables ────────────────────────────────────── */
[data-testid="stPlotlyChart"], .stPyplot {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important; padding: 10px !important;
}
[data-testid="stDataFrame"] { background: var(--surface) !important; border-radius: 10px !important; }

/* ── Sidebar ────────────────────────────────────────────── */
[data-testid="stSidebar"] { background: var(--surface) !important; border-right: 1px solid var(--border) !important; }
[data-testid="stSidebar"] * { color: var(--text) !important; }
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] { background: var(--bg) !important; border-color: var(--border) !important; }

/* ── Buttons ────────────────────────────────────────────── */
.stButton > button {
    background: var(--bg) !important; color: var(--text) !important;
    border: 1px solid var(--border) !important; border-radius: 8px !important;
    font-weight: 500 !important; padding: 9px 18px !important;
    transition: border-color 0.15s !important; width: 100% !important;
}
.stButton > button:hover { border-color: var(--accent) !important; color: var(--accent) !important; }

.stDownloadButton > button {
    background: var(--accent-dim) !important; color: var(--accent) !important;
    border: 1px solid var(--accent) !important; border-radius: 8px !important;
    font-weight: 600 !important; width: auto !important;
}
.stDownloadButton > button:hover { background: var(--accent) !important; color: var(--bg) !important; }

/* ── Uploader / expander / alerts ───────────────────────── */
[data-testid="stFileUploader"] {
    background: var(--surface) !important; border: 1px dashed var(--border) !important;
    border-radius: 10px !important; padding: 14px !important;
}
[data-testid="stExpander"] { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; }
.stAlert { background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 10px !important; color: var(--text) !important; }
hr { border-color: var(--border) !important; margin: 28px 0 !important; }

/* ── Format hint line ───────────────────────────────────── */
.format-hint {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.78rem;
    color: var(--muted); display: flex; gap: 20px; flex-wrap: wrap;
    padding: 10px 0 0 0;
}
.format-hint b { color: var(--text); font-weight: 500; }

/* ── Empty state ────────────────────────────────────────── */
.empty-state {
    text-align: center; padding: 64px 20px; color: var(--muted);
    border: 1px dashed var(--border); border-radius: 12px; margin-top: 12px;
}
.empty-state .mark {
    font-family: 'Space Grotesk', sans-serif; font-size: 2rem; color: var(--accent);
    margin-bottom: 10px;
}
.empty-state h3 {
    font-family: 'Space Grotesk', sans-serif !important; color: var(--text) !important;
    font-size: 1.2rem !important; font-weight: 600 !important; margin-bottom: 6px !important;
}
.feature-row { display: flex; gap: 14px; justify-content: center; margin-top: 28px; flex-wrap: wrap; }
.feature-chip {
    font-family: 'IBM Plex Mono', monospace; font-size: 0.75rem; color: var(--muted);
    border: 1px solid var(--border); border-radius: 20px; padding: 6px 14px;
}

.footer { text-align: center; padding: 20px; color: var(--muted) !important; font-size: 0.78rem; border-top: 1px solid var(--border); margin-top: 44px; }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div>
        <h1>UPI <span>Insights</span></h1>
        <p>Upload a statement, see where the money goes.</p>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Upload ────────────────────────────────────────────────────
u1, u2 = st.columns([3, 2])
with u1:
    uploaded_file = st.file_uploader(
        'Drop your CSV, Excel, or PDF statement',
        type=['csv', 'xlsx', 'xls', 'pdf'],
        label_visibility='visible'
    )
with u2:
    st.markdown("""
    <div class="format-hint">
        <span><b>GPay</b> — .csv</span>
        <span><b>PhonePe</b> — .csv / .xlsx</span>
        <span><b>Paytm</b> — .xlsx / .pdf</span>
        <span><b>Any bank</b> — .pdf</span>
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
    <div style='border:1px solid #262b35; border-radius:8px; padding:10px; text-align:center;'>
        <div style='font-family:"IBM Plex Mono",monospace; font-size:1.2rem; font-weight:600; color:#5fa87c;'>{len(df):,}</div>
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
        if 'txn_direction' in fdf.columns:
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            k1.metric('Transactions', f"{kpis['total_transactions']:,}")
            k2.metric('Spent',        f"₹{kpis['total_spend']:,.0f}")
            k3.metric('Received',     f"₹{kpis['total_received']:,.0f}")
            k4.metric('Highest',      f"₹{kpis['max_transaction']:,.0f}")
            k5.metric('Success rate', f"{kpis['success_rate']}%")
            k6.metric('Anomalies',    f"{kpis['anomaly_count']}")
        else:
            k1,k2,k3,k4,k5,k6 = st.columns(6)
            k1.metric('Transactions', f"{kpis['total_transactions']:,}")
            k2.metric('Spend',        f"₹{kpis['total_spend']:,.0f}")
            k3.metric('Avg / txn',    f"₹{kpis['avg_transaction']:,.0f}")
            k4.metric('Highest',      f"₹{kpis['max_transaction']:,.0f}")
            k5.metric('Success rate', f"{kpis['success_rate']}%")
            k6.metric('Anomalies',    f"{kpis['anomaly_count']}")

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
            <div style='border:1px solid #262b35; background:rgba(217,118,95,0.08); border-radius:8px; padding:12px 16px; margin-bottom:10px;'>
                <span style='color:#d9765f; font-weight:600;'>{len(anomalies)} flagged</span>
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
        <div class="mark">◇</div>
        <h3>Upload a statement to get started</h3>
        <div>Or try a sample above to explore the dashboard instantly.</div>
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