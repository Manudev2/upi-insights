import streamlit as st
import pandas as pd
from processor import (
    clean_data, detect_app, get_kpis,
    get_heatmap_data, get_category_data, get_merchant_data,
    get_monthly_trend, get_daily_trend, get_status_data, get_anomalies
)
from charts import (
    plot_heatmap, plot_daily_trend, plot_monthly_trend,
    plot_category_bar, plot_category_pie, plot_merchant_bar,
    plot_status_pie, plot_anomaly_scatter, plot_weekday_bar
)

st.set_page_config(
    page_title='UPI Insights Pro', page_icon='💳', layout='wide'
)

# ── Global CSS ────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #050d1f !important;
    color: #e8eaf6 !important;
}

.main { background: #050d1f !important; }
.block-container { padding: 2rem 2.5rem !important; }

/* ── Hide Streamlit chrome ── */
#MainMenu, footer, header { visibility: hidden; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a1628; }
::-webkit-scrollbar-thumb { background: #2a3f6f; border-radius: 3px; }

/* ── Hero Header ── */
.hero {
    background: linear-gradient(135deg, #0a1628 0%, #0d2144 50%, #0a1628 100%);
    border: 1px solid rgba(66,133,244,0.2);
    border-radius: 24px;
    padding: 48px 40px;
    margin-bottom: 32px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -60px; right: -60px;
    width: 280px; height: 280px;
    background: radial-gradient(circle, rgba(66,133,244,0.15) 0%, transparent 70%);
    border-radius: 50%;
}
.hero::after {
    content: '';
    position: absolute;
    bottom: -40px; left: 20%;
    width: 200px; height: 200px;
    background: radial-gradient(circle, rgba(52,168,83,0.1) 0%, transparent 70%);
    border-radius: 50%;
}
.hero h1 {
    font-family: 'Syne', sans-serif !important;
    font-size: 3rem !important;
    font-weight: 800 !important;
    background: linear-gradient(90deg, #4285F4, #34A853, #FBBC05);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin: 0 0 8px 0 !important;
    line-height: 1.1 !important;
}
.hero p {
    color: #7b8fc0 !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
    font-weight: 300;
}

/* ── App Cards ── */
.app-card {
    border-radius: 20px;
    padding: 24px 20px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: pointer;
    border: 1px solid rgba(255,255,255,0.06);
    position: relative;
    overflow: hidden;
}
.app-card:hover { transform: translateY(-4px); }
.app-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    border-radius: 20px 20px 0 0;
}
.app-card-gpay { background: linear-gradient(145deg, #0d1f3c, #112a50); }
.app-card-gpay::before { background: linear-gradient(90deg, #4285F4, #34A853); }
.app-card-phonepe { background: linear-gradient(145deg, #160a2e, #1e0d3d); }
.app-card-phonepe::before { background: linear-gradient(90deg, #5f259f, #a855f7); }
.app-card-paytm { background: linear-gradient(145deg, #001a3d, #002966); }
.app-card-paytm::before { background: linear-gradient(90deg, #002970, #0066cc); }
.app-card h3 {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.3rem !important;
    font-weight: 700 !important;
    margin: 8px 0 4px 0 !important;
}
.app-card p {
    font-size: 0.78rem !important;
    color: #7b8fc0 !important;
    margin: 0 !important;
}
.app-icon { font-size: 2.4rem; margin-bottom: 4px; display: block; }

/* ── Upload Box ── */
.upload-section {
    background: linear-gradient(145deg, #0a1628, #0f1e38);
    border: 2px dashed rgba(66,133,244,0.3);
    border-radius: 20px;
    padding: 32px;
    text-align: center;
    transition: border-color 0.2s;
}
.upload-section:hover { border-color: rgba(66,133,244,0.6); }

/* ── Section Title ── */
.section-title {
    font-family: 'Syne', sans-serif !important;
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: #e8eaf6 !important;
    margin: 32px 0 16px 0 !important;
    display: flex;
    align-items: center;
    gap: 8px;
}
.section-title::after {
    content: '';
    flex: 1;
    height: 1px;
    background: linear-gradient(90deg, rgba(66,133,244,0.3), transparent);
    margin-left: 12px;
}

/* ── KPI Cards ── */
[data-testid="metric-container"] {
    background: linear-gradient(145deg, #0d1f3c, #0f2347) !important;
    border: 1px solid rgba(66,133,244,0.2) !important;
    border-radius: 16px !important;
    padding: 20px !important;
    position: relative;
    overflow: hidden;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, #4285F4, #34A853);
}
[data-testid="stMetricLabel"] {
    color: #7b8fc0 !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #e8eaf6 !important;
    font-family: 'Syne', sans-serif !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* ── Chart containers ── */
[data-testid="stPlotlyChart"], .stPyplot {
    background: linear-gradient(145deg, #0a1628, #0d1f3c) !important;
    border: 1px solid rgba(66,133,244,0.12) !important;
    border-radius: 18px !important;
    padding: 12px !important;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #080f1e 0%, #0a1628 100%) !important;
    border-right: 1px solid rgba(66,133,244,0.1) !important;
}
[data-testid="stSidebar"] * { color: #c5cee8 !important; }
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="select"] {
    background: #0d1f3c !important;
    border-color: rgba(66,133,244,0.3) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, #1a3a6e, #1e4480) !important;
    color: #8ab4f8 !important;
    border: 1px solid rgba(66,133,244,0.3) !important;
    border-radius: 12px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 10px 20px !important;
    transition: all 0.2s !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #1e4480, #2456a0) !important;
    border-color: rgba(66,133,244,0.6) !important;
    color: #fff !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(66,133,244,0.2) !important;
}

/* ── File uploader ── */
[data-testid="stFileUploader"] {
    background: #0a1628 !important;
    border: 1px solid rgba(66,133,244,0.2) !important;
    border-radius: 14px !important;
    padding: 12px !important;
}

/* ── Divider ── */
hr {
    border-color: rgba(66,133,244,0.15) !important;
    margin: 24px 0 !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #0a1628 !important;
    border: 1px solid rgba(66,133,244,0.15) !important;
    border-radius: 14px !important;
}

/* ── Dataframe ── */
[data-testid="stDataFrame"] {
    background: #0a1628 !important;
    border-radius: 14px !important;
}

/* ── Download button ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #1a5c32, #1e6e3c) !important;
    color: #81c995 !important;
    border: 1px solid rgba(52,168,83,0.3) !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    width: auto !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #1e6e3c, #24874a) !important;
    box-shadow: 0 8px 24px rgba(52,168,83,0.2) !important;
}

/* ── Info box ── */
.stAlert {
    background: linear-gradient(145deg, #0d1f3c, #112a50) !important;
    border: 1px solid rgba(66,133,244,0.2) !important;
    border-radius: 14px !important;
    color: #8ab4f8 !important;
}

/* ── Success box ── */
[data-baseweb="notification"] {
    background: linear-gradient(145deg, #0d2e1a, #102e1f) !important;
    border-color: rgba(52,168,83,0.3) !important;
    border-radius: 14px !important;
}

/* ── Multiselect tags ── */
[data-baseweb="tag"] {
    background: rgba(66,133,244,0.2) !important;
    border-color: rgba(66,133,244,0.4) !important;
    color: #8ab4f8 !important;
}

/* ── Badge row ── */
.badge-row { display:flex; gap:10px; flex-wrap:wrap; margin:16px 0; }
.badge {
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}
.badge-gpay    { background: rgba(66,133,244,0.15); color: #8ab4f8; border:1px solid rgba(66,133,244,0.3); }
.badge-phonepe { background: rgba(95,37,159,0.15);  color: #c084fc; border:1px solid rgba(95,37,159,0.3); }
.badge-paytm   { background: rgba(0,41,112,0.3);    color: #60a5fa; border:1px solid rgba(0,102,204,0.3); }

/* ── Footer ── */
.footer {
    text-align: center;
    padding: 24px;
    color: #3a4d70 !important;
    font-size: 13px;
    border-top: 1px solid rgba(66,133,244,0.08);
    margin-top: 40px;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>💳 UPI Insights Pro</h1>
    <p>Upload your GPay · PhonePe · Paytm data and unlock deep spending intelligence</p>
    <div class="badge-row" style="margin-top:20px;">
        <span class="badge badge-gpay">🟦 Google Pay</span>
        <span class="badge badge-phonepe">🟣 PhonePe</span>
        <span class="badge badge-paytm">🔵 Paytm</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── App Cards ─────────────────────────────────────────────────
st.markdown('<div class="section-title">📱 Supported Apps</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div class="app-card app-card-gpay">
        <span class="app-icon">🟦</span>
        <h3 style="color:#8ab4f8;">Google Pay</h3>
        <p>Export from GPay or your bank's UPI statement</p>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div class="app-card app-card-phonepe">
        <span class="app-icon">🟣</span>
        <h3 style="color:#c084fc;">PhonePe</h3>
        <p>Profile → Transaction History → Email Statement</p>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div class="app-card app-card-paytm">
        <span class="app-icon">🔵</span>
        <h3 style="color:#60a5fa;">Paytm</h3>
        <p>Passbook → Download Statement as CSV</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)

# ── Upload + Info ─────────────────────────────────────────────
st.markdown('<div class="section-title">📤 Upload Your Data</div>', unsafe_allow_html=True)
u1, u2 = st.columns([3, 2])
with u1:
    uploaded_file = st.file_uploader(
        'Drop your CSV file here',
        type=['csv'],
        help='Supports GPay, PhonePe and Paytm CSV exports'
    )
with u2:
    st.info("""
    **How to get your CSV:**
    - **GPay** → Bank statement (filter UPI)
    - **PhonePe** → History → Request Statement
    - **Paytm** → Passbook → Download CSV
    """)

# ── Sample Buttons ────────────────────────────────────────────
st.markdown('<div class="section-title">🧪 Try Sample Data</div>', unsafe_allow_html=True)
b1, b2, b3 = st.columns(3)
load_gpay    = b1.button('🟦 Load GPay Sample')
load_phonepe = b2.button('🟣 Load PhonePe Sample')
load_paytm   = b3.button('🔵 Load Paytm Sample')

# ── Sample Generator ──────────────────────────────────────────
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
            'transaction_id': f'{app[:2].upper()}{str(i).zfill(6)}',
            'date': dt.strftime('%Y-%m-%d'),
            'time': dt.strftime('%H:%M:%S'),
            'amount': amt,
            'merchant': mer,
            'category': cat,
            'status': sts,
            'upi_id': f'user{random.randint(1000,9999)}@{app.lower()}',
        })
    return pd.DataFrame(rows)

# ── Load Data ─────────────────────────────────────────────────
df = None; app_name = None

if load_gpay:
    df = make_sample('GPay'); app_name = 'GPay'
    st.success('✅ Sample GPay data loaded — 2,000 transactions!')
elif load_phonepe:
    df = make_sample('PhonePe'); app_name = 'PhonePe'
    st.success('✅ Sample PhonePe data loaded — 2,000 transactions!')
elif load_paytm:
    df = make_sample('Paytm'); app_name = 'Paytm'
    st.success('✅ Sample Paytm data loaded — 2,000 transactions!')
elif uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        app_name = detect_app(df)
        st.success(f'✅ Detected **{app_name}** | {len(df):,} transactions loaded!')
    except Exception as e:
        st.error(f'❌ Error: {e}')

# ── Dashboard ─────────────────────────────────────────────────
if df is not None:
    df = clean_data(df, app_name)

    # Sidebar
    st.sidebar.markdown(f"""
    <div style='text-align:center; padding:16px 0 8px 0;'>
        <div style='font-family:Syne,sans-serif; font-size:1.3rem; font-weight:800;
                    background:linear-gradient(90deg,#4285F4,#34A853);
                    -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>
            UPI Insights Pro
        </div>
        <div style='font-size:11px; color:#4a5e80; margin-top:2px;'>
            📱 {app_name}
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.sidebar.markdown('---')
    st.sidebar.markdown('### 🔍 Filters')

    categories = st.sidebar.multiselect(
        'Category', options=sorted(df['category'].unique()),
        default=list(df['category'].unique())
    )
    status_list = st.sidebar.multiselect(
        'Status', options=df['status'].unique(),
        default=list(df['status'].unique())
    )
    date_range = st.sidebar.date_input(
        'Date Range',
        value=[df['date'].min().date(), df['date'].max().date()]
    )
    st.sidebar.markdown('---')
    st.sidebar.markdown(f"""
    <div style='background:rgba(66,133,244,0.08); border:1px solid rgba(66,133,244,0.2);
                border-radius:12px; padding:12px; text-align:center;'>
        <div style='font-size:1.4rem; font-weight:700; color:#8ab4f8;'>{len(df):,}</div>
        <div style='font-size:11px; color:#4a5e80;'>Total Records</div>
    </div>
    """, unsafe_allow_html=True)

    # Apply filters
    fdf = df.copy()
    if categories:
        fdf = fdf[fdf['category'].isin(categories)]
    if status_list:
        fdf = fdf[fdf['status'].isin(status_list)]
    if len(date_range) == 2:
        fdf = fdf[
            (fdf['date'] >= pd.to_datetime(date_range[0])) &
            (fdf['date'] <= pd.to_datetime(date_range[1]))
        ]

    # KPIs
    st.markdown('<div class="section-title">📊 Your Spending Summary</div>', unsafe_allow_html=True)
    kpis = get_kpis(fdf)
    k1,k2,k3,k4,k5,k6 = st.columns(6)
    k1.metric('💳 Transactions',  f"{kpis['total_transactions']:,}")
    k2.metric('💰 Total Spend',   f"₹{kpis['total_spend']:,.0f}")
    k3.metric('📉 Avg per Txn',   f"₹{kpis['avg_transaction']:,.0f}")
    k4.metric('🔝 Highest',       f"₹{kpis['max_transaction']:,.0f}")
    k5.metric('✅ Success Rate',  f"{kpis['success_rate']}%")
    k6.metric('🚨 Anomalies',     f"{kpis['anomaly_count']}")

    st.markdown('<hr>', unsafe_allow_html=True)

    # Row 1
    st.markdown('<div class="section-title">📈 Spending Over Time</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([2,1])
    with c1:
        st.plotly_chart(plot_daily_trend(get_daily_trend(fdf)), use_container_width=True)
    with c2:
        st.plotly_chart(plot_status_pie(get_status_data(fdf)), use_container_width=True)

    # Heatmap
    st.markdown('<div class="section-title">⏰ Peak Spending Hours</div>', unsafe_allow_html=True)
    st.pyplot(plot_heatmap(get_heatmap_data(fdf)))

    st.markdown('<hr>', unsafe_allow_html=True)

    # Row 2
    st.markdown('<div class="section-title">📂 Where Your Money Goes</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3:
        st.plotly_chart(plot_category_pie(get_category_data(fdf)), use_container_width=True)
    with c4:
        st.plotly_chart(plot_weekday_bar(fdf), use_container_width=True)

    c5, c6 = st.columns(2)
    with c5:
        st.plotly_chart(plot_category_bar(get_category_data(fdf)), use_container_width=True)
    with c6:
        st.plotly_chart(plot_merchant_bar(get_merchant_data(fdf)), use_container_width=True)

    # Monthly
    st.markdown('<div class="section-title">📅 Monthly Breakdown</div>', unsafe_allow_html=True)
    st.plotly_chart(plot_monthly_trend(get_monthly_trend(fdf)), use_container_width=True)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Anomaly
    st.markdown('<div class="section-title">🚨 Suspicious Transactions</div>', unsafe_allow_html=True)
    a1, a2 = st.columns(2)
    with a1:
        st.plotly_chart(plot_anomaly_scatter(fdf), use_container_width=True)
    with a2:
        anomalies = get_anomalies(fdf)
        st.markdown(f"""
        <div style='background:rgba(234,67,53,0.08); border:1px solid rgba(234,67,53,0.2);
                    border-radius:14px; padding:14px 18px; margin-bottom:12px;'>
            <span style='color:#f28b82; font-weight:600; font-size:1rem;'>
                🚨 {len(anomalies)} suspicious transactions flagged
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.dataframe(anomalies, use_container_width=True, height=280)

    st.markdown('<hr>', unsafe_allow_html=True)

    # Raw data
    with st.expander('📋 View All Transactions'):
        st.dataframe(fdf, use_container_width=True, height=300)

    st.download_button(
        '📥 Download Filtered CSV',
        data=fdf.to_csv(index=False),
        file_name=f'{app_name}_transactions.csv',
        mime='text/csv'
    )

else:
    # Landing state
    st.markdown('<hr>', unsafe_allow_html=True)
    st.markdown("""
    <div style='text-align:center; padding:60px 20px;'>
        <div style='font-size:4rem; margin-bottom:16px;'>📤</div>
        <div style='font-family:Syne,sans-serif; font-size:1.8rem; font-weight:700;
                    color:#e8eaf6; margin-bottom:8px;'>
            Upload your CSV to get started
        </div>
        <div style='color:#4a5e80; font-size:1rem; max-width:500px; margin:0 auto 32px;'>
            Or click one of the sample data buttons above to explore the dashboard instantly
        </div>
    </div>
    """, unsafe_allow_html=True)

    f1,f2,f3,f4 = st.columns(4)
    features = [
        ('📊','KPI Summary','Spend, avg, success rate'),
        ('⏰','Peak Hours','Heatmap of when you spend'),
        ('📂','Categories','Where your money goes'),
        ('🚨','Anomalies','Detect suspicious txns'),
    ]
    for col, (icon, title, desc) in zip([f1,f2,f3,f4], features):
        col.markdown(f"""
        <div style='background:linear-gradient(145deg,#0a1628,#0d1f3c);
                    border:1px solid rgba(66,133,244,0.15);
                    border-radius:16px; padding:24px; text-align:center;'>
            <div style='font-size:2rem; margin-bottom:8px;'>{icon}</div>
            <div style='font-family:Syne,sans-serif; font-weight:700;
                        color:#8ab4f8; margin-bottom:4px;'>{title}</div>
            <div style='font-size:12px; color:#4a5e80;'>{desc}</div>
        </div>
        """, unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────
st.markdown("""
<div class="footer">
    Built with ❤️ using Streamlit & Python &nbsp;·&nbsp; UPI Insights Pro
</div>
""", unsafe_allow_html=True)