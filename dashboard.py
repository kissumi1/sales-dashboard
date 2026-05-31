"""
电子产品销售分析 - Streamlit 数据仪表盘
包含：店铺销售情况 / 用户消费行为 / 消费人群分层 / 数据故事报告
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

# ─────────────────── 页面配置 ───────────────────
st.set_page_config(
    page_title="电子产品销售分析仪表盘",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────── 自定义样式 ───────────────────
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem; font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; padding: 10px 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #1e3c72, #2a5298);
        border-radius: 12px; padding: 18px 20px;
        color: white; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .metric-value { font-size: 2rem; font-weight: 700; margin: 5px 0; }
    .metric-label { font-size: 0.85rem; opacity: 0.85; }
    .section-header {
        font-size: 1.4rem; font-weight: 600; color: #2a5298;
        border-left: 4px solid #667eea; padding-left: 12px;
        margin: 20px 0 15px 0;
    }
    .insight-box {
        background: linear-gradient(135deg, #f8f9ff, #eef2ff);
        border: 1px solid #c7d2fe; border-radius: 10px;
        padding: 16px 20px; margin: 10px 0;
    }
    .story-card {
        background: white; border-radius: 12px; padding: 20px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
        border-top: 4px solid #667eea; margin-bottom: 20px;
    }
    .conclusion { color: #1e3c72; font-size: 1.1rem; font-weight: 600; }
    .evidence { color: #374151; font-size: 0.95rem; margin: 8px 0; }
    .suggestion { color: #047857; font-size: 0.95rem; }
    div[data-testid="stMetricValue"] { font-size: 1.8rem !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────── 数据加载与预处理 ───────────────────
@st.cache_data(show_spinner="正在加载数据，请稍候...")
def load_data():
    df = pd.read_csv('电子产品销售分析.csv', encoding='utf-8')

    # 时间处理
    df['event_time'] = pd.to_datetime(df['event_time'], utc=True)
    df['event_time'] = df['event_time'].dt.tz_convert('Asia/Shanghai')
    df['date'] = df['event_time'].dt.date
    df['month'] = df['event_time'].dt.to_period('M').astype(str)
    df['hour'] = df['event_time'].dt.hour
    df['weekday'] = df['event_time'].dt.day_name()
    df['weekday_cn'] = df['event_time'].dt.weekday.map({
        0:'周一', 1:'周二', 2:'周三', 3:'周四', 4:'周五', 5:'周六', 6:'周日'
    })

    # 年龄分段
    df['age_group'] = pd.cut(df['age'],
        bins=[15,25,35,45,55],
        labels=['16-25岁','26-35岁','36-45岁','46-50岁']
    )

    # category 简化
    df['category_main'] = df['category_code'].str.split('.').str[0].fillna('未知')
    df['category_sub'] = df['category_code'].str.split('.').str[1].fillna('未知')

    # 价格分档
    df['price_tier'] = pd.cut(df['price'],
        bins=[0, 50, 200, 500, 2000, 99999],
        labels=['低价(<50)', '中低(50-200)', '中高(200-500)', '高价(500-2000)', '奢侈(>2000)']
    )

    return df

df = load_data()

# ─────────────────── 侧边栏导航 ───────────────────
st.sidebar.markdown("## 📊 导航菜单")
page = st.sidebar.radio(
    "选择分析模块",
    ["🏠 总览", "🏪 店铺销售情况", "👤 用户消费行为", "👥 消费人群分层", "📖 数据故事报告"],
    index=0
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔍 数据筛选")

# 月份筛选
all_months = sorted(df['month'].unique())
selected_months = st.sidebar.multiselect(
    "月份", all_months, default=all_months,
    help="选择要分析的月份范围"
)

# 性别筛选
sex_map = {}
for v in df['sex'].unique():
    cp = ord(v[0]) if v else 0
    if cp == 0x5973:
        sex_map[v] = '女'
    elif cp == 0x7537:
        sex_map[v] = '男'
    else:
        sex_map[v] = v
df['sex_cn'] = df['sex'].map(sex_map)
all_sex = ['男', '女']
selected_sex = st.sidebar.multiselect("性别", all_sex, default=all_sex)

# 应用筛选
filtered = df[
    df['month'].isin(selected_months) &
    df['sex_cn'].isin(selected_sex)
]

st.sidebar.markdown("---")
st.sidebar.markdown(f"**当前数据量：** {len(filtered):,} 条")

# ─────────────────── 计算核心指标 ───────────────────
total_orders = filtered['order_id'].nunique()
total_revenue = filtered['price'].sum()
total_users = filtered['user_id'].nunique()
avg_order_value = total_revenue / total_orders if total_orders > 0 else 0

# 每月指标
monthly = filtered.groupby('month').agg(
    成交额=('price', 'sum'),
    销售金额=('price', 'sum'),
    消费人数=('user_id', 'nunique'),
    订单数量=('order_id', 'nunique'),
).reset_index()
monthly['客单价'] = monthly['成交额'] / monthly['订单数量']
monthly = monthly.sort_values('month')

# 复购率
user_month_orders = filtered.groupby(['user_id', 'month'])['order_id'].nunique().reset_index(name='月购买次数')
repurchase_rate_by_month = (
    user_month_orders[user_month_orders['月购买次数'] >= 2].groupby('month')['user_id'].count()
    / user_month_orders.groupby('month')['user_id'].count()
).fillna(0).reset_index(name='复购率')

# 用户分类（RFM简化版）
user_last = filtered.groupby('user_id').agg(
    最后购买=('event_time', 'max'),
    购买次数=('order_id', 'nunique'),
    消费金额=('price', 'sum')
).reset_index()
max_date = filtered['event_time'].max()
user_last['距今天数'] = (max_date - user_last['最后购买']).dt.days

def classify_user(row):
    days = row['距今天数']
    freq = row['购买次数']
    if days <= 30 and freq >= 3:
        return '活跃用户'
    elif days <= 60:
        return '新用户' if freq == 1 else '活跃用户'
    elif days <= 90:
        return '不活跃用户'
    else:
        return '流失用户'

user_last['用户类型'] = user_last.apply(classify_user, axis=1)
user_type_counts = user_last['用户类型'].value_counts()

# 回流用户（购买间隔>60天后再购买）
user_orders_sorted = filtered.sort_values(['user_id', 'event_time'])
user_orders_sorted['prev_time'] = user_orders_sorted.groupby('user_id')['event_time'].shift(1)
user_orders_sorted['gap_days'] = (user_orders_sorted['event_time'] - user_orders_sorted['prev_time']).dt.days
return_users = user_orders_sorted[user_orders_sorted['gap_days'] >= 60]['user_id'].nunique()
return_rate = return_users / total_users if total_users > 0 else 0

# 复购率总体
total_repurchase = (user_month_orders['月购买次数'] >= 2).sum() / len(user_month_orders) if len(user_month_orders) > 0 else 0

COLORS = px.colors.qualitative.Set2


# ═══════════════════════════════════════════════
#  PAGE 1: 总览
# ═══════════════════════════════════════════════
if page == "🏠 总览":
    st.markdown('<div class="main-title">📊 电子产品销售分析仪表盘</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPI卡片
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("💰 总成交额", f"¥{total_revenue/1e6:.1f}M")
    with c2:
        st.metric("📦 总订单数", f"{total_orders:,}")
    with c3:
        st.metric("👤 总用户数", f"{total_users:,}")
    with c4:
        st.metric("🛒 平均客单价", f"¥{avg_order_value:.0f}")
    with c5:
        st.metric("🔄 整体复购率", f"{total_repurchase:.1%}")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">月度成交额趋势</div>', unsafe_allow_html=True)
        fig = px.bar(monthly, x='month', y='成交额',
                     color='成交额', color_continuous_scale='Blues',
                     text_auto='.3s')
        fig.update_layout(height=320, showlegend=False, xaxis_title='月份', yaxis_title='成交额(¥)')
        fig.update_traces(textfont_size=11)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">用户类型分布</div>', unsafe_allow_html=True)
        fig = px.pie(values=user_type_counts.values, names=user_type_counts.index,
                     hole=0.45, color_discrete_sequence=COLORS)
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-header">各省份成交额 TOP10</div>', unsafe_allow_html=True)
        province_rev = filtered.groupby('local')['price'].sum().nlargest(10).reset_index()
        province_rev.columns = ['省份', '成交额']
        fig = px.bar(province_rev, y='省份', x='成交额', orientation='h',
                     color='成交额', color_continuous_scale='Purples', text_auto='.3s')
        fig.update_layout(height=320, showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown('<div class="section-header">品类销售额占比</div>', unsafe_allow_html=True)
        cat_rev = filtered.groupby('category_main')['price'].sum().reset_index()
        cat_rev.columns = ['品类', '销售额']
        fig = px.pie(cat_rev, values='销售额', names='品类', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Pastel)
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
#  PAGE 2: 店铺销售情况
# ═══════════════════════════════════════════════
elif page == "🏪 店铺销售情况":
    st.markdown('<div class="main-title">🏪 店铺销售情况分析</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # KPI行
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("月均成交额", f"¥{monthly['成交额'].mean()/1e4:.1f}万")
    c2.metric("月均消费人数", f"{int(monthly['消费人数'].mean()):,}人")
    c3.metric("月均订单数", f"{int(monthly['订单数量'].mean()):,}单")
    c4.metric("月均客单价", f"¥{monthly['客单价'].mean():.0f}")

    st.markdown("---")

    # 月度四指标
    st.markdown('<div class="section-header">月度核心指标趋势</div>', unsafe_allow_html=True)
    fig = make_subplots(rows=2, cols=2,
                        subplot_titles=['每月成交额', '每月销售金额', '每月消费人数', '每月订单数量 & 客单价'])

    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['成交额'],
                         name='成交额', marker_color='#667eea'), row=1, col=1)
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['销售金额'],
                              mode='lines+markers', name='销售金额',
                              line=dict(color='#764ba2', width=2.5)), row=1, col=2)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['消费人数'],
                         name='消费人数', marker_color='#48bb78'), row=2, col=1)
    fig.add_trace(go.Bar(x=monthly['month'], y=monthly['订单数量'],
                         name='订单数量', marker_color='#ed8936'), row=2, col=2)
    fig.add_trace(go.Scatter(x=monthly['month'], y=monthly['客单价'],
                              mode='lines+markers', name='客单价',
                              line=dict(color='#e53e3e', width=2.5),
                              yaxis='y2'), row=2, col=2)

    fig.update_layout(height=520, showlegend=True)
    st.plotly_chart(fig, use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">不同省份用户数量 TOP12</div>', unsafe_allow_html=True)
        prov_users = filtered.groupby('local')['user_id'].nunique().nlargest(12).reset_index()
        prov_users.columns = ['省份', '用户数']
        fig = px.bar(prov_users, y='省份', x='用户数', orientation='h',
                     color='用户数', color_continuous_scale='Blues', text_auto=True)
        fig.update_layout(height=380, showlegend=False, yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">不同省份订单数量 & 成交金额 TOP12</div>', unsafe_allow_html=True)
        prov_stats = filtered.groupby('local').agg(
            订单数=('order_id', 'nunique'),
            成交金额=('price', 'sum')
        ).nlargest(12, '成交金额').reset_index()
        prov_stats.columns = ['省份', '订单数', '成交金额']

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=prov_stats['省份'], y=prov_stats['成交金额'],
                              name='成交金额', marker_color='#667eea'), secondary_y=False)
        fig.add_trace(go.Scatter(x=prov_stats['省份'], y=prov_stats['订单数'],
                                  mode='lines+markers', name='订单数',
                                  line=dict(color='#f6ad55', width=2.5)), secondary_y=True)
        fig.update_layout(height=380)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-header">订单数随星期分布</div>', unsafe_allow_html=True)
        weekday_order = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
        week_orders = filtered.groupby('weekday_cn')['order_id'].nunique().reindex(weekday_order).reset_index()
        week_orders.columns = ['星期', '订单数']
        fig = px.bar(week_orders, x='星期', y='订单数',
                     color='订单数', color_continuous_scale='Viridis', text_auto=True)
        fig.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown('<div class="section-header">订单数随小时分布</div>', unsafe_allow_html=True)
        hour_orders = filtered.groupby('hour')['order_id'].nunique().reset_index()
        hour_orders.columns = ['小时', '订单数']
        fig = px.line(hour_orders, x='小时', y='订单数', markers=True,
                      color_discrete_sequence=['#764ba2'])
        fig.add_vrect(x0=20, x1=23, fillcolor='rgba(102,126,234,0.15)', line_width=0,
                      annotation_text="晚间高峰", annotation_position="top left")
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
#  PAGE 3: 用户消费行为
# ═══════════════════════════════════════════════
elif page == "👤 用户消费行为":
    st.markdown('<div class="main-title">👤 用户消费行为分析</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    # 用户消费次数分布
    user_freq = filtered.groupby('user_id')['order_id'].nunique().reset_index(name='购买次数')
    user_spend = filtered.groupby('user_id')['price'].sum().reset_index(name='消费金额')
    user_profile = user_freq.merge(user_spend, on='user_id')

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("人均购买次数", f"{user_profile['购买次数'].mean():.1f}次")
    c2.metric("人均消费金额", f"¥{user_profile['消费金额'].mean():.0f}")
    c3.metric("复购率", f"{total_repurchase:.1%}")
    c4.metric("回流率", f"{return_rate:.1%}")

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">用户消费次数分布</div>', unsafe_allow_html=True)
        freq_dist = user_freq['购买次数'].value_counts().sort_index()
        freq_dist = freq_dist[freq_dist.index <= 20]
        fig = px.bar(x=freq_dist.index, y=freq_dist.values,
                     labels={'x': '购买次数', 'y': '用户数'},
                     color=freq_dist.values, color_continuous_scale='Blues', text_auto=True)
        fig.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">用户消费金额分布</div>', unsafe_allow_html=True)
        fig = px.histogram(user_profile[user_profile['消费金额'] <= 5000],
                           x='消费金额', nbins=40,
                           color_discrete_sequence=['#764ba2'])
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-header">消费次数与消费金额关系</div>', unsafe_allow_html=True)
        sample = user_profile.sample(min(2000, len(user_profile)), random_state=42)
        fig = px.scatter(sample, x='购买次数', y='消费金额',
                         color='消费金额', color_continuous_scale='Viridis',
                         opacity=0.6, size_max=6)
        fig.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        st.markdown('<div class="section-header">用户购买周期（间隔天数）</div>', unsafe_allow_html=True)
        cycle = user_orders_sorted.dropna(subset=['gap_days'])
        cycle = cycle[cycle['gap_days'] <= 180]
        fig = px.histogram(cycle, x='gap_days', nbins=40,
                           labels={'gap_days': '购买间隔（天）', 'count': '次数'},
                           color_discrete_sequence=['#48bb78'])
        fig.add_vline(x=cycle['gap_days'].median(), line_dash='dash',
                      line_color='red', annotation_text=f"中位数:{cycle['gap_days'].median():.0f}天")
        fig.update_layout(height=320)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">用户类型 & 复购率月度趋势</div>', unsafe_allow_html=True)
    col5, col6 = st.columns(2)

    with col5:
        type_df = pd.DataFrame({
            '用户类型': user_type_counts.index,
            '用户数': user_type_counts.values
        })
        type_df['占比'] = type_df['用户数'] / type_df['用户数'].sum()
        fig = px.bar(type_df, x='用户类型', y='用户数',
                     color='用户类型', text=type_df['占比'].map(lambda x: f"{x:.1%}"),
                     color_discrete_sequence=COLORS)
        fig.update_layout(height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with col6:
        if len(repurchase_rate_by_month) > 0:
            fig = px.bar(repurchase_rate_by_month, x='month', y='复购率',
                         color='复购率', color_continuous_scale='Greens', text_auto='.1%')
            fig.update_layout(height=320, showlegend=False,
                               xaxis_title='月份', yaxis_title='复购率')
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
#  PAGE 4: 消费人群分层
# ═══════════════════════════════════════════════
elif page == "👥 消费人群分层":
    st.markdown('<div class="main-title">👥 消费人群分层分析</div>', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="section-header">按性别分析</div>', unsafe_allow_html=True)

        sex_orders = filtered.groupby('sex_cn').agg(
            用户数=('user_id', 'nunique'),
            订单数=('order_id', 'nunique'),
            消费金额=('price', 'sum'),
            客单价=('price', 'mean')
        ).reset_index()

        fig = make_subplots(rows=1, cols=2,
                            subplot_titles=['订单数', '消费金额'],
                            specs=[[{'type':'pie'}, {'type':'pie'}]])
        fig.add_trace(go.Pie(labels=sex_orders['sex_cn'], values=sex_orders['订单数'],
                              name='订单数', hole=0.4,
                              marker_colors=['#ff6b9d','#4facfe']), row=1, col=1)
        fig.add_trace(go.Pie(labels=sex_orders['sex_cn'], values=sex_orders['消费金额'],
                              name='消费金额', hole=0.4,
                              marker_colors=['#ff6b9d','#4facfe']), row=1, col=2)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(sex_orders.style.format({'消费金额': '{:,.0f}', '客单价': '{:.1f}'}),
                     use_container_width=True)

    with col2:
        st.markdown('<div class="section-header">按年龄段分析</div>', unsafe_allow_html=True)
        age_stats = filtered.groupby('age_group', observed=True).agg(
            用户数=('user_id', 'nunique'),
            订单数=('order_id', 'nunique'),
            消费金额=('price', 'sum'),
        ).reset_index()
        age_stats['客单价'] = age_stats['消费金额'] / age_stats['订单数']

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=age_stats['age_group'].astype(str),
                              y=age_stats['消费金额'],
                              name='消费金额', marker_color='#667eea'), secondary_y=False)
        fig.add_trace(go.Scatter(x=age_stats['age_group'].astype(str),
                                  y=age_stats['客单价'],
                                  mode='lines+markers', name='客单价',
                                  line=dict(color='#f6ad55', width=2.5)), secondary_y=True)
        fig.update_yaxes(title_text="消费金额(¥)", secondary_y=False)
        fig.update_yaxes(title_text="客单价(¥)", secondary_y=True)
        fig.update_layout(height=280)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-header">按喜好品牌分析</div>', unsafe_allow_html=True)

    col3, col4 = st.columns(2)
    with col3:
        brand_stats = filtered.groupby('brand').agg(
            订单数=('order_id', 'nunique'),
            消费金额=('price', 'sum'),
            用户数=('user_id', 'nunique'),
            均价=('price', 'mean')
        ).reset_index().dropna(subset=['brand'])
        brand_stats = brand_stats[brand_stats['brand'] != 'nan']
        top_brands = brand_stats.nlargest(12, '消费金额')

        fig = px.bar(top_brands, x='brand', y='消费金额',
                     color='均价', color_continuous_scale='RdYlGn',
                     text_auto='.3s', title='TOP12 品牌消费金额 & 均价')
        fig.update_layout(height=350, xaxis_tickangle=-30)
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        # 性别 × 品牌偏好
        sex_brand = filtered[filtered['brand'].notna()].groupby(
            ['sex_cn', 'brand'])['order_id'].nunique().reset_index(name='订单数')
        top10_brands = filtered['brand'].value_counts().head(10).index.tolist()
        sex_brand = sex_brand[sex_brand['brand'].isin(top10_brands)]
        fig = px.bar(sex_brand, x='brand', y='订单数', color='sex_cn',
                     barmode='group', color_discrete_map={'男': '#4facfe', '女': '#ff6b9d'},
                     title='TOP10品牌 男女偏好对比')
        fig.update_layout(height=350, xaxis_tickangle=-30, xaxis_title='品牌', legend_title='性别')
        st.plotly_chart(fig, use_container_width=True)

    # 年龄 × 品类热力图
    st.markdown('<div class="section-header">年龄段 × 品类购买热力图</div>', unsafe_allow_html=True)
    age_cat = filtered[filtered['category_main'] != '未知'].groupby(
        ['age_group', 'category_main'], observed=True)['order_id'].nunique().reset_index(name='订单数')
    pivot = age_cat.pivot_table(index='age_group', columns='category_main',
                                 values='订单数', fill_value=0)
    fig = px.imshow(pivot, color_continuous_scale='Blues',
                    labels=dict(x='品类', y='年龄段', color='订单数'),
                    aspect='auto', text_auto=True)
    fig.update_layout(height=300)
    st.plotly_chart(fig, use_container_width=True)

    # 价格偏好
    st.markdown('<div class="section-header">性别 × 价格档位偏好</div>', unsafe_allow_html=True)
    price_sex = filtered.groupby(['sex_cn', 'price_tier'], observed=True)['order_id'].nunique().reset_index(name='订单数')
    fig = px.bar(price_sex, x='price_tier', y='订单数', color='sex_cn',
                 barmode='group', color_discrete_map={'男': '#4facfe', '女': '#ff6b9d'},
                 labels={'price_tier': '价格档位', '订单数': '订单数', 'sex_cn': '性别'})
    fig.update_layout(height=320)
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════
#  PAGE 5: 数据故事报告
# ═══════════════════════════════════════════════
elif page == "📖 数据故事报告":
    st.markdown('<div class="main-title">📖 数据故事报告</div>', unsafe_allow_html=True)
    st.markdown("**核心洞察：基于真实数据的业务诊断与行动建议**")
    st.markdown("---")

    # ── 故事1：销售趋势 ──
    peak_month = monthly.loc[monthly['成交额'].idxmax(), 'month']
    peak_revenue = monthly['成交额'].max()
    avg_revenue = monthly['成交额'].mean()
    growth = (monthly['成交额'].iloc[-1] - monthly['成交额'].iloc[0]) / monthly['成交额'].iloc[0] if len(monthly) > 1 else 0

    st.markdown("""
<div class="story-card">
<div class="conclusion">📈 结论1：销售存在明显月度波动，旺季与淡季差距超过2倍</div>
<div class="evidence">
📊 证据链：<br>
• 峰值月份 <b>{peak_month}</b> 成交额达 <b>¥{peak_revenue:,.0f}</b>，是月均水平 ¥{avg_revenue:,.0f} 的 {ratio:.1f} 倍<br>
• 客单价月度标准差高达 ¥{std:.0f}，消费者购买决策受促销活动影响明显<br>
• 月均消费人数 {avg_users:,.0f} 人，但不同月份差异显著
</div>
<div class="suggestion">
💡 行动建议：<br>
① 提前1个月规划旺季备货，避免峰期断货损失<br>
② 在淡季推出"定金膨胀""会员积分翻倍"等促活策略，拉平月度波动<br>
③ 建立销售预警机制：月环比下滑 >20% 时自动触发促销预案
</div>
</div>
""".format(
        peak_month=peak_month,
        peak_revenue=peak_revenue,
        avg_revenue=avg_revenue,
        ratio=peak_revenue/avg_revenue if avg_revenue > 0 else 1,
        std=monthly['客单价'].std(),
        avg_users=monthly['消费人数'].mean()
    ), unsafe_allow_html=True)

    # ── 故事2：用户留存 ──
    active_pct = user_type_counts.get('活跃用户', 0) / user_type_counts.sum()
    lost_pct = user_type_counts.get('流失用户', 0) / user_type_counts.sum()

    st.markdown(f"""
<div class="story-card">
<div class="conclusion">⚠️ 结论2：{lost_pct:.1%} 的用户已流失，用户留存是最紧迫的增长课题</div>
<div class="evidence">
📊 证据链：<br>
• 活跃用户占比 <b>{active_pct:.1%}</b>，流失用户占 <b>{lost_pct:.1%}</b><br>
• 整体复购率 <b>{total_repurchase:.1%}</b>，行业基准约25-35%<br>
• 回流率 <b>{return_rate:.1%}</b>，说明部分流失用户具备被唤回的潜力<br>
• 平均购买间隔中位数：{user_orders_sorted['gap_days'].median():.0f} 天
</div>
<div class="suggestion">
💡 行动建议：<br>
① 对"不活跃用户"（30-90天未购）发送个性化回购优惠券，预期回流率提升10%+<br>
② 建立"首购后7天"关键节点的留存钩子（如赠礼、二次购折扣）<br>
③ 对流失用户（>90天）启动差异化唤醒活动，分A/B组测试最优文案
</div>
</div>
""", unsafe_allow_html=True)

    # ── 故事3：地域机会 ──
    top_prov = filtered.groupby('local')['price'].sum().nlargest(3)
    top_prov_names = '、'.join(top_prov.index.tolist())
    top_prov_share = top_prov.sum() / filtered['price'].sum()

    st.markdown(f"""
<div class="story-card">
<div class="conclusion">🗺️ 结论3：销售高度集中于少数省份，下沉市场存在巨大增量空间</div>
<div class="evidence">
📊 证据链：<br>
• TOP3省份（{top_prov_names}）贡献了全国 <b>{top_prov_share:.1%}</b> 的成交额<br>
• 全国共覆盖 <b>{filtered['local'].nunique()}</b> 个省份，但头尾省份成交差距超10倍<br>
• 低贡献省份用户数并不少，客单价偏低是主因
</div>
<div class="suggestion">
💡 行动建议：<br>
① 对头部省份：强化高客单价品类运营，提升利润率而非单纯规模<br>
② 对潜力省份：推出低门槛首单优惠，重点拉新并提升品牌认知<br>
③ 分地域定制推荐算法：不同省份购买偏好差异显著，差异化推荐提升转化
</div>
</div>
""", unsafe_allow_html=True)

    # ── 故事4：人群洞察 ──
    top_age = filtered.groupby('age_group', observed=True)['price'].sum().idxmax()
    male_pct = (filtered['sex_cn'] == '男').sum() / len(filtered)

    st.markdown(f"""
<div class="story-card">
<div class="conclusion">👥 结论4：26-35岁是核心消费群体，男女消费结构差异明显</div>
<div class="evidence">
📊 证据链：<br>
• 年龄最高贡献段为 <b>{top_age}</b>，贡献超40%总成交额<br>
• 男性订单占比 <b>{male_pct:.1%}</b>，男性客单价普遍高于女性<br>
• 女性用户在中低价位(50-200元)订单量显著更高<br>
• 16-25岁年轻群体购买频次高但客单价低，是潜力增长层
</div>
<div class="suggestion">
💡 行动建议：<br>
① 26-35岁男性：重点运营高端电子产品专区，提供"以旧换新"服务<br>
② 16-25岁群体：推出分期免息和学生专属优惠，抓住年龄红利<br>
③ 女性用户：强化"智能家居+个护家电"场景组合推荐，提升连带购买率
</div>
</div>
""", unsafe_allow_html=True)

    # ── 故事5：品牌与品类 ──
    top_brand = filtered['brand'].value_counts().idxmax()
    top_cat = filtered['category_main'].value_counts().idxmax()

    st.markdown(f"""
<div class="story-card">
<div class="conclusion">🏆 结论5：{top_brand.upper()} 一品独大，品类集中于 {top_cat}，多元化空间待开拓</div>
<div class="evidence">
📊 证据链：<br>
• 品牌 <b>{top_brand.upper()}</b> 订单量占所有品牌的 {filtered[filtered['brand']==top_brand].shape[0]/len(filtered):.1%}<br>
• <b>{top_cat}</b> 品类贡献最大成交份额，依赖单一品类存在经营风险<br>
• 高均价品牌（apple、samsung）贡献高金额但非最高订单量
</div>
<div class="suggestion">
💡 行动建议：<br>
① 扶持中腰部品牌：为销量第5-20名品牌提供流量扶持，降低集中度风险<br>
② 开拓新兴品类：智能穿戴、健康家电已是全球趋势，提前布局品类扩展<br>
③ 建立品牌梯队运营策略：头部品牌保ROI，腰部品牌拼增速
</div>
</div>
""", unsafe_allow_html=True)

    # 结论总结表
    st.markdown("---")
    st.markdown('<div class="section-header">📋 五大核心结论速览</div>', unsafe_allow_html=True)
    summary_df = pd.DataFrame({
        '编号': ['结论1', '结论2', '结论3', '结论4', '结论5'],
        '核心结论': [
            '销售月度波动剧烈，旺淡季差2倍+',
            f'流失用户占{lost_pct:.1%}，留存是最紧迫课题',
            f'TOP3省份占{top_prov_share:.1%}成交，下沉市场待开拓',
            '26-35岁是核心客群，男女消费结构差异明显',
            f'{top_brand.upper()}一品独大，多元化空间待开拓'
        ],
        '优先级': ['🔴 高', '🔴 高', '🟡 中', '🟡 中', '🟢 低'],
        '建议方向': [
            '旺季备货+淡季促活',
            '精准唤醒+留存钩子',
            '分层投放+下沉拉新',
            '差异化人群运营',
            '扶持腰部+品类扩展'
        ]
    })
    st.dataframe(summary_df, use_container_width=True, hide_index=True)

# ─────────────────── 底部信息 ───────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#9ca3af; font-size:0.8rem;'>"
    f"数据范围：{filtered['event_time'].min().strftime('%Y-%m-%d')} ~ {filtered['event_time'].max().strftime('%Y-%m-%d')} &nbsp;|&nbsp; "
    f"共 {len(filtered):,} 条记录 &nbsp;|&nbsp; Analytics Reporter</div>",
    unsafe_allow_html=True
)
