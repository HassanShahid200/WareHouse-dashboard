import streamlit as st
import pandas as pd

# Set up the webpage
st.set_page_config(page_title="Warehouse Dashboard", layout="wide")
st.title("Warehouse Real-Time Dashboard")

# Create a file uploader for the client
uploaded_file = st.file_uploader("Upload 'WareHouse Real time data.xlsx'", type=["xlsx"])

if uploaded_file is not None:
    try:
        # 1. Read the sheets
        df_dispatch = pd.read_excel(uploaded_file, sheet_name='Dispatch')
        df_received = pd.read_excel(uploaded_file, sheet_name='Recieved')
        df_helper = pd.read_excel(uploaded_file, sheet_name='Helper Table')
        
        # 2. Bridge the tables using the Helper Table
        df_dispatch = pd.merge(
            df_dispatch, 
            df_helper[['Customer Code', 'Group']], 
            left_on='CardCode', 
            right_on='Customer Code', 
            how='left'
        )
        
        df_received = pd.merge(
            df_received, 
            df_helper[['Customer Name', 'Group']], 
            left_on='Vendor Name', 
            right_on='Customer Name', 
            how='left'
        )
        
        # 3. Create the Slicer in the Sidebar
        st.sidebar.header("Filters")
        all_groups = df_helper['Group'].dropna().unique()
        selected_groups = st.sidebar.multiselect(
            "Select Group (Slicer):", 
            options=all_groups,
            default=all_groups
        )
        
        # 4. Filter the data based on the Slicer
        filtered_dispatch = df_dispatch[df_dispatch['Group'].isin(selected_groups)]
        filtered_received = df_received[df_received['Group'].isin(selected_groups)]
        
        # 5. Summarize and Display Data
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Dispatch Summary")
            dispatch_summary = filtered_dispatch.groupby('Group')['Net Dispatch Qty'].sum().reset_index()
            st.dataframe(dispatch_summary, hide_index=True)
            
        with col2:
            st.subheader("Received Summary")
            received_summary = filtered_received.groupby('Group')['Net Quantity'].sum().reset_index()
            st.dataframe(received_summary, hide_index=True)

    except Exception as e:
        st.error(f"Error reading the file: {e}. Please ensure the sheet names and columns match exactly.")
else:
    st.info("Waiting for file upload...")
