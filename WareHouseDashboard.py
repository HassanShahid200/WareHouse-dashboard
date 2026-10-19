import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Set up the webpage layout
st.set_page_config(page_title="Warehouse Analytics", page_icon="📦", layout="wide")

st.title("📦 Warehouse Real-Time Dashboard")
st.markdown("---")

uploaded_file = st.file_uploader("Upload 'WareHouse Real time data.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 1. READ DATA
        df_dispatch = pd.read_excel(uploaded_file, sheet_name='Dispatch')
        df_received = pd.read_excel(uploaded_file, sheet_name='Recieved')
        df_helper = pd.read_excel(uploaded_file, sheet_name='Helper Table')
        
        # 2. DATE FORMATTING & EXTRACTION (For Year/Month Slicers)
        df_dispatch['Date'] = pd.to_datetime(df_dispatch['Dispatch Date'])
        df_received['Date'] = pd.to_datetime(df_received['Posting Date'])
        
        df_dispatch['Year'] = df_dispatch['Date'].dt.year.astype(str)
        df_dispatch['Month'] = df_dispatch['Date'].dt.strftime('%b') # Jan, Feb, etc.
        df_received['Year'] = df_received['Date'].dt.year.astype(str)
        df_received['Month'] = df_received['Date'].dt.strftime('%b')

        # 3. BRIDGE TABLES (Replicating the Star Schema Model)
        df_dispatch = pd.merge(df_dispatch, df_helper[['Customer Code', 'Customer Name']], left_on='CardCode', right_on='Customer Code', how='left')
        df_dispatch['Customer Name'] = df_dispatch['Customer Name'].fillna(df_dispatch['CardName']) # Fallback if missing
        
        df_received = pd.merge(df_received, df_helper[['Customer Name', 'Group']], left_on='Vendor Name', right_on='Customer Name', how='left')
        df_received['Customer Name'] = df_received['Vendor Name']

        # 4. DAX LOGIC TRANSLATION (Row Context / SUMX)
        # Delivered Layer Pad Logic
        def get_lp_divisor(cat):
            if cat == "17 Layers": return 543
            elif cat == "18 Layers": return 544.5
            elif cat == "20 Layers": return 547.61
            return 1
            
        # Delivered Pallets Logic
        def get_pallet_divisor(cat):
            if cat == "17 Layers": return 9775
            elif cat == "18 Layers": return 10350
            elif cat == "20 Layers": return 11500
            return 1

        df_dispatch['Delivered Layer Pad'] = df_dispatch['Net Dispatch Qty'] / df_dispatch['Catgeory'].apply(get_lp_divisor)
        df_dispatch['Delivered Pallets'] = df_dispatch['Net Dispatch Qty'] / df_dispatch['Catgeory'].apply(get_pallet_divisor)
        df_dispatch['Delivered Top Frame'] = df_dispatch['Delivered Pallets']

        # 5. SIDEBAR SLICERS
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=100)
        st.sidebar.header("⚙️ Filter Panel")
        
        # Get unique values for slicers
        all_years = sorted(list(set(df_dispatch['Year'].dropna()) | set(df_received['Year'].dropna())))
        all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        available_months = [m for m in all_months if m in set(df_dispatch['Month'].dropna()) | set(df_received['Month'].dropna())]
        all_groups = sorted(list(set(df_dispatch['Group'].dropna()) | set(df_received['Group'].dropna())))
        all_customers = sorted(list(set(df_dispatch['Customer Name'].dropna()) | set(df_received['Customer Name'].dropna())))

        # Render Slicers
        selected_years = st.sidebar.multiselect("📅 Select Year", all_years, default=all_years)
        selected_months = st.sidebar.multiselect("📆 Select Month", available_months, default=available_months)
        selected_groups = st.sidebar.multiselect("🏢 Select Group", all_groups, default=all_groups)
        selected_customers = st.sidebar.multiselect("👤 Select Customer", all_customers, default=all_customers)

        # 6. APPLY SLICER FILTERS
        mask_disp = (df_dispatch['Year'].isin(selected_years)) & (df_dispatch['Month'].isin(selected_months)) & (df_dispatch['Group'].isin(selected_groups)) & (df_dispatch['Customer Name'].isin(selected_customers))
        filtered_dispatch = df_dispatch[mask_disp]

        mask_rec = (df_received['Year'].isin(selected_years)) & (df_received['Month'].isin(selected_months)) & (df_received['Group'].isin(selected_groups)) & (df_received['Customer Name'].isin(selected_customers))
        filtered_received = df_received[mask_rec]

        # 7. DAX AGGREGATIONS (Filter Context / CALCULATE)
        # Exclude Mehran Bottlers from Layer Pads calculation
        del_lp_total = filtered_dispatch[filtered_dispatch['Group'] != "Mehran Bottlers (Pvt) Ltd."]['Delivered Layer Pad'].sum()
        del_pallet_total = filtered_dispatch['Delivered Pallets'].sum()
        del_tf_total = filtered_dispatch['Delivered Top Frame'].sum()

        rec_lp_total = filtered_received[filtered_received['Categ'] == "Layer Pads"]['Net Quantity'].sum()
        rec_pallet_total = filtered_received[filtered_received['Categ'] == "Pallets"]['Net Quantity'].sum()
        rec_tf_total = filtered_received[filtered_received['Categ'] == "Top Frame"]['Net Quantity'].sum()

        # 8. DASHBOARD KPI CARDS
        st.subheader("📊 Material Tracking Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Layer Pads (Delivered vs Received)", f"{del_lp_total:,.0f}", f"{rec_lp_total - del_lp_total:,.0f} Net diff", delta_color="off")
        with col2:
            st.metric("Pallets (Delivered vs Received)", f"{del_pallet_total:,.0f}", f"{rec_pallet_total - del_pallet_total:,.0f} Net diff", delta_color="off")
        with col3:
            st.metric("Top Frames (Delivered vs Received)", f"{del_tf_total:,.0f}", f"{rec_tf_total - del_tf_total:,.0f} Net diff", delta_color="off")

        st.markdown("---")

        # 9. VISUALIZATIONS
        st.subheader("📈 Delivery & Recovery Trends")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Group Level Delivery Summary
            grp_summary = filtered_dispatch.groupby('Group')[['Delivered Layer Pad', 'Delivered Pallets']].sum().reset_index()
            fig1 = px.bar(grp_summary, x='Group', y=['Delivered Layer Pad', 'Delivered Pallets'], 
                          title="Deliveries by Group", barmode='group')
            st.plotly_chart(fig1, use_container_width=True)
            
        with chart_col2:
            # Group Level Received Summary
            rec_summary = filtered_received.groupby('Group')[['Net Quantity']].sum().reset_index()
            fig2 = px.bar(rec_summary, x='Group', y='Net Quantity', 
                          title="Total Received Materials by Group", color_discrete_sequence=['#2ecc71'])
            st.plotly_chart(fig2, use_container_width=True)

    except Exception as e:
        st.error(f"Error processing data: {e}")
else:
    st.info("👆 Please upload the Excel file to generate the dashboard.")
