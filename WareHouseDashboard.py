import streamlit as st
import pandas as pd
import plotly.express as px

# Set up the webpage for an Executive Dashboard feel
st.set_page_config(page_title="Warehouse Analytics", page_icon="📦", layout="wide")

st.title("📦 Executive Warehouse Real-Time Dashboard")
st.markdown("---")

uploaded_file = st.file_uploader("Upload 'WareHouse Real time data.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 1. READ DATA
        df_dispatch = pd.read_excel(uploaded_file, sheet_name='Dispatch')
        df_received = pd.read_excel(uploaded_file, sheet_name='Recieved')
        df_helper = pd.read_excel(uploaded_file, sheet_name='Helper Table')
        
        # 2. DATE FORMATTING
        df_dispatch['Date'] = pd.to_datetime(df_dispatch['Dispatch Date'])
        df_received['Date'] = pd.to_datetime(df_received['Posting Date'])
        df_dispatch['Year'] = df_dispatch['Date'].dt.year.astype(str)
        df_dispatch['Month'] = df_dispatch['Date'].dt.strftime('%b') 
        df_received['Year'] = df_received['Date'].dt.year.astype(str)
        df_received['Month'] = df_received['Date'].dt.strftime('%b')

        # 3. BRIDGE TABLES
        df_dispatch = pd.merge(df_dispatch, df_helper[['Customer Code', 'Customer Name']], left_on='CardCode', right_on='Customer Code', how='left')
        df_dispatch['Customer Name'] = df_dispatch['Customer Name'].fillna(df_dispatch['CardName']) 
        
        df_received = pd.merge(df_received, df_helper[['Customer Name', 'Group']], left_on='Vendor Name', right_on='Customer Name', how='left')
        df_received['Customer Name'] = df_received['Vendor Name']

        # 4. DAX LOGIC TRANSLATION
        def get_lp_divisor(cat):
            cat = str(cat).strip()
            if cat == "17 Layers": return 543
            elif cat == "18 Layers": return 544.5
            elif cat == "20 Layers": return 547.61
            return 1
            
        def get_pallet_divisor(cat):
            cat = str(cat).strip()
            if cat == "17 Layers": return 9775
            elif cat == "18 Layers": return 10350
            elif cat == "20 Layers": return 11500
            return 1

        df_dispatch['Delivered Layer Pad'] = df_dispatch['Net Dispatch Qty'] / df_dispatch['Catgeory'].apply(get_lp_divisor)
        df_dispatch['Delivered Pallets'] = df_dispatch['Net Dispatch Qty'] / df_dispatch['Catgeory'].apply(get_pallet_divisor)
        df_dispatch['Delivered Top Frame'] = df_dispatch['Delivered Pallets']

        # 5. POWER BI STYLE SLICERS
        st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2830/2830305.png", width=100)
        st.sidebar.header("⚙️ Filter Panel")
        st.sidebar.caption("💡 Leave a filter empty to select ALL")
        
        all_years = sorted(list(set(df_dispatch['Year'].dropna()) | set(df_received['Year'].dropna())))
        all_months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        avail_months = [m for m in all_months if m in set(df_dispatch['Month'].dropna()) | set(df_received['Month'].dropna())]
        all_groups = sorted(list(set(df_dispatch['Group'].dropna()) | set(df_received['Group'].dropna())))
        all_customers = sorted(list(set(df_dispatch['Customer Name'].dropna()) | set(df_received['Customer Name'].dropna())))

        selected_years = st.sidebar.multiselect("📅 Select Year", all_years, default=all_years)
        selected_months = st.sidebar.multiselect("📆 Select Month", avail_months, default=avail_months)
        selected_groups = st.sidebar.multiselect("🏢 Select Group", all_groups, default=all_groups)
        selected_customers = st.sidebar.multiselect("👤 Select Customer", all_customers, default=all_customers)

        # FIX: Power BI fallback logic! If empty, use ALL.
        use_years = selected_years if selected_years else all_years
        use_months = selected_months if selected_months else avail_months
        use_groups = selected_groups if selected_groups else all_groups
        use_customers = selected_customers if selected_customers else all_customers

        # 6. APPLY FILTERS
        mask_disp = (df_dispatch['Year'].isin(use_years)) & (df_dispatch['Month'].isin(use_months)) & (df_dispatch['Group'].isin(use_groups)) & (df_dispatch['Customer Name'].isin(use_customers))
        filtered_dispatch = df_dispatch[mask_disp]

        mask_rec = (df_received['Year'].isin(use_years)) & (df_received['Month'].isin(use_months)) & (df_received['Group'].isin(use_groups)) & (df_received['Customer Name'].isin(use_customers))
        filtered_received = df_received[mask_rec]

        # 7. DAX AGGREGATIONS
        del_lp_total = filtered_dispatch[filtered_dispatch['Group'] != "Mehran Bottlers (Pvt) Ltd."]['Delivered Layer Pad'].sum()
        del_pallet_total = filtered_dispatch['Delivered Pallets'].sum()
        del_tf_total = filtered_dispatch['Delivered Top Frame'].sum()

        rec_lp_total = filtered_received[filtered_received['Categ'].str.strip() == "Layer Pads"]['Net Quantity'].sum()
        rec_pallet_total = filtered_received[filtered_received['Categ'].str.strip() == "Pallets"]['Net Quantity'].sum()
        rec_tf_total = filtered_received[filtered_received['Categ'].str.strip() == "Top Frame"]['Net Quantity'].sum()

        # 8. TOP KPI CARDS
        st.subheader("📊 Material Tracking Summary")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Layer Pads (Delivered vs Received)", f"{del_lp_total:,.0f}", f"{rec_lp_total - del_lp_total:,.0f} Net diff")
        with col2:
            st.metric("Pallets (Delivered vs Received)", f"{del_pallet_total:,.0f}", f"{rec_pallet_total - del_pallet_total:,.0f} Net diff")
        with col3:
            st.metric("Top Frames (Delivered vs Received)", f"{del_tf_total:,.0f}", f"{rec_tf_total - del_tf_total:,.0f} Net diff")

        st.markdown("---")

        # 9. SEPARATE TABS FOR "WOW" FACTOR
        tab1, tab2 = st.tabs(["📤 Delivered Tracking (by Customer)", "📥 Received Tracking (by Customer)"])

        with tab1:
            st.subheader("Deliveries Breakdown")
            if not filtered_dispatch.empty:
                del_cust = filtered_dispatch.groupby('Customer Name')[['Delivered Layer Pad', 'Delivered Pallets', 'Delivered Top Frame']].sum().reset_index()
                
                # Plotly Bar Chart
                fig_del = px.bar(del_cust, x='Customer Name', y=['Delivered Layer Pad', 'Delivered Pallets', 'Delivered Top Frame'], 
                                 barmode='group', title="Deliveries by Vendor/Customer")
                st.plotly_chart(fig_del, use_container_width=True)
                
                # Interactive Table
                st.dataframe(del_cust.style.format("{:,.1f}", subset=['Delivered Layer Pad', 'Delivered Pallets', 'Delivered Top Frame']), use_container_width=True)
            else:
                st.warning("No Delivery Data for the selected filters.")

        with tab2:
            st.subheader("Receiving Breakdown")
            if not filtered_received.empty:
                rec_cust = filtered_received.pivot_table(index='Customer Name', columns='Categ', values='Net Quantity', aggfunc='sum', fill_value=0).reset_index()
                
                # Ensure columns exist safely
                for col in ['Layer Pads', 'Pallets', 'Top Frame']:
                    if col not in rec_cust.columns:
                        rec_cust[col] = 0
                        
                # Plotly Bar Chart
                fig_rec = px.bar(rec_cust, x='Customer Name', y=['Layer Pads', 'Pallets', 'Top Frame'], 
                                 barmode='group', title="Received Materials by Vendor/Customer",
                                 color_discrete_sequence=['#2ecc71', '#27ae60', '#1abc9c'])
                st.plotly_chart(fig_rec, use_container_width=True)
                
                # Interactive Table
                st.dataframe(rec_cust.style.format("{:,.1f}", subset=['Layer Pads', 'Pallets', 'Top Frame']), use_container_width=True)
            else:
                st.warning("No Received Data for the selected filters.")

    except Exception as e:
        st.error(f"Error processing data: {e}")
else:
    st.info("👆 Please upload the Excel file to generate the dashboard.")
