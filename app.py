import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from scipy import stats

st.set_page_config(page_title="스마트 제조 SPC & 공정능력분석 시스템", layout="wide")

st.title("🏭 스마트 제조 SPC & 공정능력분석 대시보드")
st.markdown("강데이터 변경에 따라 실시간으로 통계적 공정관리(SPC) 및 공정능력분석(Cpk)을 수행하는 웹앱입니다.")

# ==========================================
# 1. 사이드바: 데이터 업로드 및 파라미터 설정
# ==========================================
st.sidebar.header("📁 데이터 및 조건 설정")
uploaded_file = st.sidebar.file_uploader("CSV 또는 Excel 파일을 업로드하세요.", type=["csv", "xlsx"])

# 테스트용 샘플 데이터 생성 (파일이 없을 때 보여줄 기본 데이터)
if uploaded_file is None:
    st.sidebar.info("💡 샘플 데이터로 구동 중입니다. 본인의 파일을 업로드해 보세요.")
    # 샘플: Lot당 5개씩 20개의 Lot 데이터 생성 (평균 20, 표준편차 0.5)
    np.random.seed(42)
    lots = np.repeat(np.arange(1, 21), 5)
    weights = np.random.normal(loc=20.0, scale=0.5, size=100)
    # 일부러 이상치 1개 주입
    weights[42] = 22.2
    df = pd.DataFrame({"Lot": lots, "Weight": weights})
else:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

# 데이터 컬럼 선택
all_columns = df.columns.tolist()
val_col = st.sidebar.selectbox("공정 특성치(측정값) 컬럼 선택", all_columns, index=1 if len(all_columns)>1 else 0)
group_col = st.sidebar.selectbox("부분군(Lot/Group) ID 컬럼 선택", all_columns, index=0)

# 규격치 설정
data_mean = float(df[val_col].mean())
data_std = float(df[val_col].std())

st.sidebar.markdown("---")
st.sidebar.subheader("📐 공정 규격(Specification) 설정")
lsl = st.sidebar.number_input("하한규격 (LSL)", value=round(data_mean - 3*data_std, 2))
usl = st.sidebar.number_input("상한규격 (USL)", value=round(data_mean + 3*data_std, 2))
target = st.sidebar.number_input("목표값 (Target)", value=round(data_mean, 2))

# 데이터 프리뷰
with st.expander("📊 업로드된 데이터 확인 (Preview)", expanded=False):
    st.dataframe(df.head(10), use_container_width=True)
    st.write(f"전체 데이터 개수: {len(df)}개")

# ==========================================
# 2. 통계 데이터 전처리 (Lot별 평균 및 범위 계산)
# ==========================================
# Lot별 평균(X-bar) 및 범위(R) 계산
group_stats = df.groupby(group_col)[val_col].agg(['mean', lambda x: x.max() - x.min(), 'std', 'count']).reset_index()
group_stats.columns = [group_col, 'X_bar', 'R', 'S', 'n']

# 통계적 관리도 상수표 (부분군 크기 n에 따른 계수, 일반적으로 n=5 기준 관리도 적용 시)
# 강의록 기준 d2, A2 등의 상수를 사용하거나 전체 데이터 기준 표준편차(3시그마)를 사용할 수 있습니다.
# 여기서는 데이터의 전체 거동을 직관적으로 보기 위해 3시그마 기반 관리선(임시) 또는 표준 관리도 방식을 적용합니다.
overall_mean = group_stats['X_bar'].mean()
r_bar = group_stats['R'].mean()

# n=5 일 때의 일반적 계수 (강의록 사정에 맞춰 조정 가능)
# 여기서는 개별 부분군의 크기가 일정하다고 가정하고 단순 전체 데이터 표준편차 기반 3시그마 관리한계를 시각화에 적용
x_ucl = overall_mean + 3 * (data_std / np.sqrt(5))
x_lcl = overall_mean - 3 * (data_std / np.sqrt(5))

r_ucl = r_bar * 2.114 # n=5 기준 D4=2.114
r_lcl = r_bar * 0     # n=5 기준 D3=0

# ==========================================
# 3. 메인 대시보드 탭 구성
# ==========================================
tab1, tab2 = st.tabs(["📈 통계적 공정관리 (SPC)", "📊 공정능력분석 (Process Capability)"])

# ------------------------------------------
# Tab 1: 통계적 공정관리 (SPC)
# ------------------------------------------
with tab1:
    st.header("통계적 공정 관리 (Xbar - R 관리도)")
    
    col1, col2 = st.columns(2)
    
    # 1) X-bar 관리도
    with col1:
        st.subheader("모니터링: X-bar 관리도")
        fig_x = go.Figure()
        fig_x.add_trace(go.Scatter(x=group_stats[group_col], y=group_stats['X_bar'], mode='lines+markers', name='X-bar', line=dict(color='blue')))
        fig_x.add_hline(y=overall_mean, line_dash="dash", line_color="green", annotation_text=f"CL ({overall_mean:.2f})")
        fig_x.add_hline(y=x_ucl, line_dash="dot", line_color="red", annotation_text=f"UCL ({x_ucl:.2f})")
        fig_x.add_hline(y=x_lcl, line_dash="dot", line_color="red", annotation_text=f"LCL ({x_lcl:.2f})")
        
        # 이상점 표시
        ooc_x = group_stats[(group_stats['X_bar'] > x_ucl) | (group_stats['X_bar'] < x_lcl)]
        fig_x.add_trace(go.Scatter(x=ooc_x[group_col], y=ooc_x['X_bar'], mode='markers', name='이상점(OOC)', marker=dict(color='red', size=10, symbol='x')))
        
        fig_x.update_layout(xaxis_title="부분군 (Lot)", yaxis_title="평균 (X-bar)", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_x, use_container_width=True)

    # 2) R 관리도
    with col2:
        st.subheader("산포 관리: R 관리도")
        fig_r = go.Figure()
        fig_r.add_trace(go.Scatter(x=group_stats[group_col], y=group_stats['R'], mode='lines+markers', name='Range (R)', line=dict(color='orange')))
        fig_r.add_hline(y=r_bar, line_dash="dash", line_color="green", annotation_text=f"CL ({r_bar:.2f})")
        fig_r.add_hline(y=r_ucl, line_dash="dot", line_color="red", annotation_text=f"UCL ({r_ucl:.2f})")
        fig_r.add_hline(y=r_lcl, line_dash="dot", line_color="red", annotation_text=f"LCL ({r_lcl:.2f})")
        
        ooc_r = group_stats[(group_stats['R'] > r_ucl) | (group_stats['R'] < r_lcl)]
        fig_r.add_trace(go.Scatter(x=ooc_r[group_col], y=ooc_r['R'], mode='markers', name='이상점(OOC)', marker=dict(color='red', size=10, symbol='x')))
        
        fig_r.update_layout(xaxis_title="부분군 (Lot)", yaxis_title="범위 (R)", margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_r, use_container_width=True)

    # 이상 부분군 진단 리스트
    all_ooc_lots = set(ooc_x[group_col].tolist() + ooc_r[group_col].tolist())
    if all_ooc_lots:
        st.error(f"🚨 **이상점 탐지 경고**: 관리한계선을 벗어난 이상 부분군(Lot)이 발견되었습니다: **{list(all_ooc_lots)}**")
        st.markdown("- **조치 사항**: 해당 부분군의 원인(작업자 변경, 원자재 이상, 설비 오작동 등)을 파악하고 이상원인을 제거해야 합니다.")
    else:
        st.success("✅ 현재 모든 공정이 관리한계선 내에서 안정적으로 제어되고 있습니다 (정상 상태).")

# ------------------------------------------
# Tab 2: 공정능력분석 (Process Capability)
# ------------------------------------------
with tab2:
    st.header("공정능력분석 (Process Capability Analysis)")
    
    # 지수 계산
    # Cp = (USL - LSL) / (6 * sigma)
    # Cpk = min(USL - mean, mean - LSL) / (3 * sigma)
    cp = (usl - lsl) / (6 * data_std) if data_std > 0 else 0
    cpu = (usl - data_mean) / (3 * data_std) if data_std > 0 else 0
    cpl = (data_mean - lsl) / (3 * data_std) if data_std > 0 else 0
    cpk = min(cpu, cpl)
    
    # KPI 지표 카드 시각화
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric(label="공정 평균 (Mean)", value=f"{data_mean:.4f}")
    kpi2.metric(label="단기 표준편차 (σ)", value=f"{data_std:.4f}")
    kpi3.metric(label="공정능력지수 Cp", value=f"{cp:.3f}")
    kpi4.metric(label="치우침 반영 Cpk", value=f"{cpk:.3f}", delta=f"{cpk - 1.33:.3f} (기준 1.33 대비)")
    
    # 히스토그램 및 정규분포 곡선 그리기
    st.subheader("품질 데이터 분포 및 규격선 비교")
    
    fig_hist = go.Figure()
    # 히스토그램
    fig_hist.add_trace(go.Histogram(x=df[val_col], nbinsx=15, name="실제 데이터 분포", histnorm='probability density', marker_color='lightblue', opacity=0.75))
    
    # 정규분포 곡선 추가
    x_axis = np.linspace(data_mean - 4*data_std, data_mean + 4*data_std, 200)
    y_axis = stats.norm.pdf(x_axis, data_mean, data_std)
    fig_hist.add_trace(go.Scatter(x=x_axis, y=y_axis, mode='lines', name='정규분포 곡선', line=dict(color='darkblue', width=2)))
    
    # 규격선 추가
    fig_hist.add_vline(x=lsl, line_dash="dash", line_color="red", line_width=2, annotation_text=f"LSL ({lsl:.2f})", annotation_position="top left")
    fig_hist.add_vline(x=usl, line_dash="dash", line_color="red", line_width=2, annotation_text=f"USL ({usl:.2f})", annotation_position="top right")
    fig_hist.add_vline(x=target, line_dash="solid", line_color="purple", line_width=1, annotation_text=f"Target ({target:.2f})")
    
    fig_hist.update_layout(xaxis_title="측정값", yaxis_title="밀도 (Density)", margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_hist, use_container_width=True)
    
    # 공정 등급 판정 (강의록 기준 매핑 가능)
    st.subheader("📢 공정능력 평가 결과 보고서")
    if cpk >= 1.67:
        status_text = "이 공정은 **최우수(공정능력 충분)** 상태입니다. 품질 관리가 매우 안정적입니다."
        st.success(status_text)
    elif cpk >= 1.33:
        status_text = "이 공정은 **우수(공정능력 만족)** 상태입니다. 현재 상태를 유지하십시오."
        st.info(status_text)
    elif cpk >= 1.00:
        status_text = "이 공정은 **보통(주의 요망)** 상태입니다. 불량 발생 가능성이 존재하므로 관리가 필요합니다."
        st.warning(status_text)
    else:
        status_text = "이 공정은 **부족(공정능력 불충분)** 상태입니다. 공정 획기적 개선이나 규격 재검토가 시급합니다."
        st.error(status_text)
