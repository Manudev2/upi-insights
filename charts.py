import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib as mpl

# Dark theme colors
COLORS = ['#4285F4','#34A853','#FBBC05','#EA4335',
          '#8AB4F8','#81C995','#FDD663','#F28B82',
          '#a8d5a2','#c084fc']

DARK_BG   = '#0a1628'
DARK_CARD = '#0d1f3c'
GRID_CLR  = 'rgba(66,133,244,0.08)'
TEXT_CLR  = '#7b8fc0'

LAYOUT = dict(
    paper_bgcolor=DARK_CARD,
    plot_bgcolor=DARK_BG,
    font=dict(family='DM Sans', color=TEXT_CLR, size=12),
    title_font=dict(family='Syne', color='#e8eaf6', size=15),
    xaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR, tickfont=dict(color=TEXT_CLR)),
    yaxis=dict(gridcolor=GRID_CLR, linecolor=GRID_CLR, tickfont=dict(color=TEXT_CLR)),
    margin=dict(l=16, r=16, t=48, b=16),
    legend=dict(bgcolor='rgba(0,0,0,0)', font=dict(color=TEXT_CLR)),
)

def _apply(fig):
    fig.update_layout(**LAYOUT)
    return fig

def plot_heatmap(pivot_df):
    mpl.rcParams.update({
        'figure.facecolor': DARK_CARD,
        'axes.facecolor':   DARK_BG,
        'text.color':       TEXT_CLR,
        'axes.labelcolor':  TEXT_CLR,
        'xtick.color':      TEXT_CLR,
        'ytick.color':      TEXT_CLR,
    })
    fig, ax = plt.subplots(figsize=(16, 4))
    fig.patch.set_facecolor(DARK_CARD)
    ax.set_facecolor(DARK_BG)
    sns.heatmap(pivot_df, cmap='Blues', linewidths=0.3,
                ax=ax, cbar_kws={'label':'Amount (₹)'})
    ax.set_title('Peak Hour & Day — Spending Heatmap',
                 fontsize=13, color='#e8eaf6', pad=12)
    ax.set_xlabel('Hour of Day (0–23)', color=TEXT_CLR)
    ax.set_ylabel('', color=TEXT_CLR)
    plt.tight_layout()
    return fig

def plot_daily_trend(df):
    fig = px.line(df, x='date', y='amount',
                  title='Daily Spending Trend',
                  labels={'amount':'Amount (₹)','date':'Date'})
    fig.update_traces(line_color='#4285F4', line_width=2.5,
                      fill='tozeroy',
                      fillcolor='rgba(66,133,244,0.08)')
    return _apply(fig)

def plot_monthly_trend(df):
    fig = px.bar(df, x='month', y='amount',
                 title='Monthly Spending',
                 labels={'amount':'Amount (₹)','month':'Month'},
                 text_auto='.2s')
    fig.update_traces(marker_color='#4285F4',
                      marker_line_color='rgba(66,133,244,0.3)',
                      marker_line_width=1)
    return _apply(fig)

def plot_category_bar(df):
    fig = px.bar(df, x='category', y='total_amount',
                 color='category', color_discrete_sequence=COLORS,
                 title='Spend by Category',
                 labels={'total_amount':'Amount (₹)','category':'Category'},
                 text_auto='.2s')
    fig.update_layout(showlegend=False, xaxis_tickangle=-30)
    return _apply(fig)

def plot_category_pie(df):
    fig = px.pie(df, names='category', values='total_amount',
                 title='Category Distribution',
                 color_discrete_sequence=COLORS,
                 hole=0.4)
    fig.update_traces(textfont_color='#e8eaf6')
    return _apply(fig)

def plot_merchant_bar(df):
    fig = px.bar(df.sort_values('total_amount'),
                 x='total_amount', y='merchant', orientation='h',
                 color='total_amount', color_continuous_scale='Blues',
                 title='Top 10 Merchants by Spend',
                 labels={'total_amount':'Amount (₹)','merchant':''},
                 text_auto='.2s')
    fig.update_layout(coloraxis_showscale=False)
    return _apply(fig)

def plot_status_pie(df):
    fig = px.pie(df, names='status', values='count',
                 title='Transaction Status',
                 color_discrete_sequence=['#34A853','#EA4335','#FBBC05'],
                 hole=0.45)
    fig.update_traces(textfont_color='#e8eaf6')
    return _apply(fig)

def plot_anomaly_scatter(df):
    d = df.copy()
    d['label'] = d['is_anomaly'].map({True:'🚨 Anomaly', False:'Normal'})
    fig = px.scatter(d, x='date', y='amount', color='label',
                     color_discrete_map={'🚨 Anomaly':'#EA4335','Normal':'#4285F4'},
                     title='Anomaly Detection',
                     labels={'amount':'Amount (₹)'},
                     opacity=0.7)
    return _apply(fig)

def plot_weekday_bar(df):
    order = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
    data = df.groupby('day_of_week')['amount'].sum().reindex(order).reset_index()
    fig = px.bar(data, x='day_of_week', y='amount',
                 title='Spending by Day of Week',
                 labels={'amount':'Amount (₹)','day_of_week':''},
                 color='amount', color_continuous_scale='Blues')
    fig.update_layout(coloraxis_showscale=False)
    return _apply(fig)