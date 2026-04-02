#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
import traceback

# ================= 1. 页面基本设置 =================
st.set_page_config(page_title="南海农商银行-风险观测看板", layout="wide")

# ================= 2. 智能读取与自动单位换算 =================
@st.cache_data
def load_and_clean_data():
    file_path = "/Users/bow/Downloads/Python学习/南海农商银行-风险观测看板.xlsx"
    
    try:
        df_macro = pd.read_excel(file_path, sheet_name="Macro_Trends")
        df_roll = pd.read_excel(file_path, sheet_name="Roll_Rates")
        
        df_macro.rename(columns={
            df_macro.columns[0]: '月份',
            df_macro.columns[1]: '资产余额_原',
            df_macro.columns[2]: '新增余额_原',
            df_macro.columns[3]: '累计不良率_原'
        }, inplace=True)
        
        df_roll.rename(columns={
            df_roll.columns[0]: '月份',
            df_roll.columns[1]: '产品类别',
            df_roll.columns[2]: '结转阶段',
            df_roll.columns[3]: '期初结转比_原'
        }, inplace=True)

        def clean_number(x):
            if isinstance(x, str):
                nums = re.findall(r'[\d.]+', x)
                if nums:
                    val = float(nums[0])
                    if '%' in x:
                        val = val / 100
                    return val
                return 0.0
            return float(x)

        # 清洗基础数据
        df_macro['资产余额'] = df_macro['资产余额_原'].apply(clean_number)
        df_macro['新增余额'] = df_macro['新增余额_原'].apply(clean_number)
        df_macro['累计不良率'] = df_macro['累计不良率_原'].apply(clean_number)

        # 【重点：智能自动单位换算】
        # 如果资产余额大于 100,000，说明 Excel 里存的是原生“元”，我们自动除以 1 亿转化成“亿元”
        if df_macro['资产余额'].max() > 100000:
            df_macro['资产余额'] = df_macro['资产余额'] / 100000000
            
        if df_macro['新增余额'].max() > 100000:
            df_macro['新增余额'] = df_macro['新增余额'] / 100000000

        # 过滤并清洗 M0-M1
        df_m0m1 = df_roll[df_roll['结转阶段'] == 'M0-M1'].copy()
        df_m0m1['月份'] = pd.to_datetime(df_m0m1['月份']).dt.strftime('%Y-%m')
        df_m0m1['M0_M1结转率'] = df_m0m1['期初结转比_原'].apply(clean_number)

        # 拼接数据
        df_macro['月份'] = pd.to_datetime(df_macro['月份']).dt.strftime('%Y-%m')
        df_final = pd.merge(df_macro, df_m0m1[['月份', 'M0_M1结转率']], on='月份', how='left')
        
        return df_final
    except Exception as e:
        st.error(f"读取或清洗数据时出错啦：{e}")
        st.code(traceback.format_exc()) 
        return None

df = load_and_clean_data()

# ================= 3. 开始渲染看板 =================
if df is not None and not df.empty:
    
    current_data = df.iloc[-1]
    prev_data = df.iloc[-2] if len(df) > 1 else current_data
    latest_month = current_data['月份']
    
    st.title("🏦 风险关键指标观测看板")
    
    st.markdown(f"""
    **📝 本月风控摘要 ({latest_month})：**
    * **大盘稳健**：整体资产余额稳步增长至 **{current_data['资产余额']:.2f} 亿**。
    * **风险提示**：累计不良率目前为 **{current_data['累计不良率']*100:.2f}%**。**M0-M1早期指标目前为 {current_data['M0_M1结转率']*100:.2f}%**，请结合业务实际情况关注早期逾期抬头风险。
    """)
    st.divider()
    
    col1, col2, col3, col4 = st.columns(4)
    
    diff_asset = current_data['资产余额'] - prev_data['资产余额']
    col1.metric("当前资产余额 (亿)", f"{current_data['资产余额']:.2f}", f"{diff_asset:+.2f} 环比", delta_color="normal")
    
    diff_npl = (current_data['累计不良率'] - prev_data['累计不良率']) * 100
    col2.metric("当前累计不良率", f"{current_data['累计不良率']*100:.2f}%", f"{diff_npl:+.2f}% 环比", delta_color="inverse")
    
    diff_loan = current_data['新增余额'] - prev_data['新增余额']
    col3.metric("当月新增放款-大额分期 (亿)", f"{current_data['新增余额']:.2f}", f"{diff_loan:+.2f} 环比", delta_color="normal")
    
    diff_m0m1 = (current_data['M0_M1结转率'] - prev_data['M0_M1结转率']) * 100
    col4.metric("当月大额分期 M0-M1", f"{current_data['M0_M1结转率']*100:.2f}%", f"{diff_m0m1:+.2f}% 环比", delta_color="inverse")
    
    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("整体资产余额与累计不良率趋势")
        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
        
        fig1.add_trace(
            go.Bar(x=df['月份'], y=df['资产余额'], name="资产余额(亿)", marker_color='#2c5282', opacity=0.8),
            secondary_y=False,
        )
        fig1.add_trace(
            go.Scatter(x=df['月份'], y=df['累计不良率'], name="累计不良率", mode='lines+markers',
                       line=dict(color='#e53e3e', width=3), marker=dict(size=8)),
            secondary_y=True,
        )
        
        fig1.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=0, r=0, t=30, b=0),
            hovermode="x unified"
        )
        # 这里把 Y 轴的 2.5B 改成清晰的 25亿
        fig1.update_yaxes(title_text="资产余额 (亿)", ticksuffix="亿", showgrid=True, gridwidth=1, gridcolor='LightGray', secondary_y=False)
        fig1.update_yaxes(title_text="不良率", tickformat=".2%", showgrid=False, secondary_y=True)
        st.plotly_chart(fig1, use_container_width=True)

    with col_right:
        st.subheader("早期风险预警：M0-M1 金额结转比趋势")
        fig2 = go.Figure()
        
        m0m1_plot_values = (df['M0_M1结转率'] * 100).tolist()
        
        fig2.add_trace(go.Scatter(x=df['月份'], y=m0m1_plot_values, name="大额分期 M0-M1", mode='lines+markers+text',
                                  line=dict(color='#dd6b20', width=3),
                                  text=[f"{val:.2f}%" if i in[0, len(m0m1_plot_values)-1] else "" for i, val in enumerate(m0m1_plot_values)], 
                                  textposition="top center"))
        
        fig2.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="警戒线 (2.0%)")

        fig2.update_layout(
            plot_bgcolor='white', paper_bgcolor='white',
            yaxis=dict(title="结转比 (%)", showgrid=True, gridwidth=1, gridcolor='LightGray', ticksuffix="%"),
            hovermode="x unified"
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.write("---")
    with st.expander("🔍 点击查看底层清洗后的合并数据 (用于核对)"):
        st.dataframe(df.style.format({
            "资产余额": "{:.2f}亿",
            "累计不良率": "{:.4%}",
            "新增余额": "{:.2f}亿",
            "M0_M1结转率": "{:.2%}"
        }), use_container_width=True)

