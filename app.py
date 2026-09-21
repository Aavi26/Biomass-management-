import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Page Configuration (Mobile Responsive)
st.set_page_config(page_title="Biomass ERP", page_icon="🏭", layout="wide")

# Database Initialization
conn = sqlite3.connect("pellet_plant.db", check_same_thread=False)
c = conn.cursor()

# Tables Creation
c.execute('''CREATE TABLE IF NOT EXISTS raw_material_inward (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, gate_pass_no TEXT, supplier TEXT, truck_no TEXT,
                gross_wt REAL, tare_wt REAL, net_wt REAL, rate_per_ton REAL,
                moisture REAL, ash REAL, foreign_matter TEXT, qc_status TEXT,
                deduction REAL, total_payable REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS production_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, shift TEXT, start_time TEXT, stop_time TEXT,
                run_hours REAL, stop_reason TEXT, input_tons REAL,
                output_tons REAL, screening_loss REAL, moisture_loss REAL,
                yield_efficiency REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS outward_sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, invoice_no TEXT, buyer TEXT, truck_no TEXT,
                tare_wt REAL, gross_wt REAL, net_wt REAL, rate_per_ton REAL,
                tax_type TEXT, taxable_amt REAL, gst_amt REAL, total_invoice REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS attendance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, shift TEXT, operator_present TEXT, loader_present TEXT,
                labour_present TEXT, contract_workers INTEGER, contract_wage REAL,
                daily_contract_payout REAL)''')

c.execute('''CREATE TABLE IF NOT EXISTS plant_expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, category TEXT, amount REAL, payment_mode TEXT,
                vendor TEXT, remarks TEXT)''')
conn.commit()

# Sidebar Navigation (Mobile Friendly Drawer)
st.sidebar.title("🏭 Pellet Plant ERP")
role = st.sidebar.radio("Navigation Menu", [
    "Clerk: Inward & QC (Rice Husk)",
    "Manager: Machine Production",
    "Clerk: Outward Dispatch & Billing",
    "Manager: Shift Attendance",
    "Clerk: Daily Expenses",
    "Admin: Live Reports & Analytics"
])

# -------------------------------------------------------------
# 1. CLERK: INWARD & QC (RICE HUSK)
# -------------------------------------------------------------
if role == "Clerk: Inward & QC (Rice Husk)":
    st.title("🌾 Inward Gate Pass & Quality Control")
    
    with st.form("inward_form"):
        col1, col2 = st.columns(2)
        with col1:
            supplier = st.text_input("Supplier / Rice Mill Name")
            truck_no = st.text_input("Truck Number (e.g. UP-32-AB-1234)").upper()
            gross_wt = st.number_input("Gross Weight (Loaded Truck in Tons)", min_value=0.0, step=0.01)
            tare_wt = st.number_input("Tare Weight (Empty Truck in Tons)", min_value=0.0, step=0.01)
            rate = st.number_input("Purchase Rate per Ton (₹)", min_value=0.0, step=50.0)
        
        with col2:
            moisture = st.number_input("Moisture Level (%)", min_value=0.0, max_value=100.0, value=10.0, step=0.1)
            ash = st.number_input("Ash Content (%)", min_value=0.0, max_value=100.0, value=16.0, step=0.1)
            foreign = st.selectbox("Foreign Matter (Stone/Soil)", ["None", "Minor", "High"])
            
            # QC Auto Recommendation
            rec_status = "Accepted with Deduction" if (moisture > 12.0 or foreign == "High") else "Accepted"
            qc_status = st.selectbox("QC Decision", ["Accepted", "Accepted with Deduction", "Rejected"], index=0 if rec_status == "Accepted" else 1)
            deduction = st.number_input("Deduction / Penalty (₹)", min_value=0.0, step=100.0)

        submitted = st.form_submit_button("💾 Save Inward Gate Pass")
        if submitted:
            if gross_wt > tare_wt and supplier and truck_no:
                net_wt = gross_wt - tare_wt
                total_payable = (net_wt * rate) - deduction
                gp_no = f"GP-IN-{datetime.now().strftime('%d%H%M%S')}"
                today = datetime.now().strftime("%Y-%m-%d")
                
                c.execute('''INSERT INTO raw_material_inward (date, gate_pass_no, supplier, truck_no, gross_wt, tare_wt, net_wt, rate_per_ton, moisture, ash, foreign_matter, qc_status, deduction, total_payable)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (today, gp_no, supplier, truck_no, gross_wt, tare_wt, net_wt, rate, moisture, ash, foreign, qc_status, deduction, total_payable))
                conn.commit()
                st.success(f"Gate Pass Generated! ID: {gp_no} | Net Weight: {net_wt:.2f} Tons | Payable: ₹{total_payable:.2f}")
            else:
                st.error("Weights invalid hain ya supplier/truck details missing hain!")

    st.subheader("Recent Inward Records")
    df_inward = pd.read_sql("SELECT date, gate_pass_no, supplier, truck_no, net_wt, total_payable, qc_status FROM raw_material_inward ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(df_inward, use_container_width=True)

# -------------------------------------------------------------
# 2. MANAGER: MACHINE PRODUCTION & AUTO-RUNTIME
# -------------------------------------------------------------
elif role == "Manager: Machine Production":
    st.title("⚙️ Machine Production & Auto-Runtime")
    st.caption("Machine Capacity: 2.0 TPH | Benchmark Yield: 90%")

    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "is_running" not in st.session_state:
        st.session_state.is_running = False

    shift = st.selectbox("Shift", ["Shift 1 (8 AM - 4 PM)", "Shift 2 (4 PM - 12 AM)"])

    col1, col2 = st.columns(2)
    with col1:
        if st.button("▶ START MACHINE", disabled=st.session_state.is_running, use_container_width=True):
            st.session_state.start_time = datetime.now()
            st.session_state.is_running = True
            st.rerun()

    with col2:
        if st.button("⏹ STOP / SHUTDOWN", disabled=not st.session_state.is_running, use_container_width=True):
            st.session_state.stop_time = datetime.now()
            st.session_state.is_running = False
            st.rerun()

    st.info(f"Machine Status: {'🟢 RUNNING' if st.session_state.is_running else '🔴 STOPPED'} | Start Time: {st.session_state.start_time.strftime('%I:%M:%S %p') if st.session_state.start_time else '--:--'}")

    with st.form("production_entry"):
        st.subheader("Material Processing & Losses (Tons)")
        c1, c2 = st.columns(2)
        with c1:
            input_tons = st.number_input("Raw Husk Fed to Hopper (Tons)", min_value=0.0, step=0.1)
            output_tons = st.number_input("Finished Pellets Shifted (Tons)", min_value=0.0, step=0.1)
        with c2:
            screening_loss = st.number_input("Screening Waste (Stone, Soil, Sand) (Tons)", min_value=0.0, step=0.1)
            moisture_loss = st.number_input("Moisture & Dust Evaporation (Tons)", min_value=0.0, step=0.1)
        
        stop_reason = st.selectbox("Stop / Breakdown Reason", ["Normal Shift Completion", "Mechanical Breakdown (Die/Roller)", "Power Failure", "Husk Shortage", "Routine Maintenance"])

        submit_prod = st.form_submit_button("📤 Submit Shift Production Report")
        if submit_prod:
            if input_tons > 0 and output_tons > 0:
                run_hrs = 8.0 # Default 8 hours ya actual calculated
                if st.session_state.start_time and hasattr(st.session_state, 'stop_time'):
                    diff = (st.session_state.stop_time - st.session_state.start_time).total_seconds() / 3600
                    run_hrs = round(diff, 2) if diff > 0 else 8.0
                
                efficiency = round((output_tons / input_tons) * 100, 2)
                today = datetime.now().strftime("%Y-%m-%d")
                start_str = st.session_state.start_time.strftime("%I:%M %p") if st.session_state.start_time else "Manual"
                stop_str = datetime.now().strftime("%I:%M %p")

                c.execute('''INSERT INTO production_logs (date, shift, start_time, stop_time, run_hours, stop_reason, input_tons, output_tons, screening_loss, moisture_loss, yield_efficiency)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                          (today, shift, start_str, stop_str, run_hrs, stop_reason, input_tons, output_tons, screening_loss, moisture_loss, efficiency))
                conn.commit()
                st.success(f"Report Submitted! Yield Efficiency: {efficiency}% (Target: 90%)")
            else:
                st.error("Input aur Output weight enter karein!")

# -------------------------------------------------------------
# 3. CLERK: OUTWARD DISPATCH & BILLING
# -------------------------------------------------------------
elif role == "Clerk: Outward Dispatch & Billing":
    st.title("🚚 Finished Goods Dispatch & Sales Bill")
    
    with st.form("dispatch_form"):
        col1, col2 = st.columns(2)
        with col1:
            buyer = st.text_input("Buyer / Power Plant Name")
            truck_no = st.text_input("Dispatch Truck Number").upper()
            tare_wt = st.number_input("Empty Truck Tare Weight (Tons)", min_value=0.0, step=0.01)
            gross_wt = st.number_input("Loaded Gross Weight (Tons)", min_value=0.0, step=0.01)
        with col2:
            rate_per_ton = st.number_input("Selling Rate per Ton (₹)", min_value=0.0, step=100.0, value=6500.0)
            tax_type = st.selectbox("GST Type", ["IntraState (CGST 2.5% + SGST 2.5%)", "InterState (IGST 5%)"])

        dispatch_submit = st.form_submit_button("🧾 Generate Invoice & Gate Pass")
        if dispatch_submit:
            if gross_wt > tare_wt and buyer and truck_no:
                net_wt = gross_wt - tare_wt
                taxable = net_wt * rate_per_ton
                gst = taxable * 0.05
                total = taxable + gst
                inv_no = f"INV-{datetime.now().strftime('%d%H%M%S')}"
                today = datetime.now().strftime("%Y-%m-%d")

                c.execute('''INSERT INTO outward_sales (date, invoice_no, buyer, truck_no, tare_wt, gross_wt, net_wt, rate_per_ton, tax_type, taxable_amt, gst_amt, total_invoice)
                             VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                          (today, inv_no, buyer, truck_no, tare_wt, gross_wt, net_wt, rate_per_ton, tax_type, taxable, gst, total))
                conn.commit()
                st.success(f"Invoice {inv_no} Generated! Net Dispatch: {net_wt:.2f} Tons | Total Invoice: ₹{total:.2f}")
            else:
                st.error("Invalid weights ya customer details missing hain!")

    st.subheader("Recent Sales Invoices")
    df_sales = pd.read_sql("SELECT date, invoice_no, buyer, truck_no, net_wt, total_invoice FROM outward_sales ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(df_sales, use_container_width=True)

# -------------------------------------------------------------
# 4. MANAGER: SHIFT ATTENDANCE
# -------------------------------------------------------------
elif role == "Manager: Shift Attendance":
    st.title("👷 Daily Shift Attendance & Labour Logs")
    shift = st.selectbox("Shift Selection", ["Shift 1", "Shift 2"])
    
    with st.form("att_form"):
        st.subheader("Fixed Monthly Staff")
        col1, col2, col3 = st.columns(3)
        with col1:
            op = st.checkbox("Machine Operator", value=True)
        with col2:
            ld = st.checkbox("Loader Driver", value=True)
        with col3:
            lab = st.checkbox("Plant Regular Labour", value=True)

        st.subheader("On-Demand Contract Labour (Weekly Payout)")
        c1, c2 = st.columns(2)
        with c1:
            contract_count = st.number_input("Contract Labour Headcount", min_value=0, value=0, step=1)
        with c2:
            contract_wage = st.number_input("Shift Rate per Labour (₹)", value=450.0, step=50.0)

        payout = contract_count * contract_wage
        st.caption(f"Calculated Contract Payout: ₹{payout:.2f}")

        submit_att = st.form_submit_button("🔒 Submit Attendance")
        if submit_att:
            today = datetime.now().strftime("%Y-%m-%d")
            c.execute('''INSERT INTO attendance_logs (date, shift, operator_present, loader_present, labour_present, contract_workers, contract_wage, daily_contract_payout)
                         VALUES (?,?,?,?,?,?,?,?)''',
                      (today, shift, "P" if op else "A", "P" if ld else "A", "P" if lab else "A", contract_count, contract_wage, payout))
            conn.commit()
            st.success("Shift Attendance Saved!")

# -------------------------------------------------------------
# 5. CLERK: EXPENSE TRACKER
# -------------------------------------------------------------
elif role == "Clerk: Daily Expenses":
    st.title("💸 Plant Expenses & Wear-and-Tear")
    
    with st.form("expense_form"):
        cat = st.selectbox("Category", [
            "Hospitality (Tea & Snacks)",
            "Wear & Tear (Dies, Rollers & Bearings)",
            "Fuel (Loader/Tractor Diesel)",
            "Electricity & Maintenance",
            "Miscellaneous / Petty Cash"
        ])
        amt = st.number_input("Amount (₹)", min_value=0.0, step=50.0)
        mode = st.selectbox("Payment Mode", ["Cash", "Company UPI", "Bank Transfer"])
        vendor = st.text_input("Shop / Vendor Name")
        remarks = st.text_area("Bill Description / Notes")

        submit_exp = st.form_submit_button("➕ Add Expense")
        if submit_exp:
            if amt > 0:
                today = datetime.now().strftime("%Y-%m-%d")
                c.execute('''INSERT INTO plant_expenses (date, category, amount, payment_mode, vendor, remarks)
                             VALUES (?,?,?,?,?,?)''', (today, cat, amt, mode, vendor, remarks))
                conn.commit()
                st.success(f"Expense of ₹{amt} logged!")
            else:
                st.error("Amount enter karein!")

    st.subheader("Logged Expenses")
    df_exp = pd.read_sql("SELECT date, category, amount, payment_mode, remarks FROM plant_expenses ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(df_exp, use_container_width=True)

# -------------------------------------------------------------
# 6. ADMIN: MASTER DASHBOARD & KPI
# -------------------------------------------------------------
elif role == "Admin: Live Reports & Analytics":
  
    st.title("📊 Plant Director Dashboard & KPI")

    total_inward = pd.read_sql("SELECT SUM(net_wt) as total FROM raw_material_inward", conn)['total'][0] or 0.0
    total_produced = pd.read_sql("SELECT SUM(output_tons) as total FROM production_logs", conn)['total'][0] or 0.0
    total_sold = pd.read_sql("SELECT SUM(net_wt) as total FROM outward_sales", conn)['total'][0] or 0.0
    total_revenue = pd.read_sql("SELECT SUM(total_invoice) as total FROM outward_sales", conn)['total'][0] or 0.0
    total_expenses = pd.read_sql("SELECT SUM(amount) as total FROM plant_expenses", conn)['total'][0] or 0.0
    total_raw_cost = pd.read_sql("SELECT SUM(total_payable) as total FROM raw_material_inward", conn)['total'][0] or 0.0

    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Husk Stock (Approx)", f"{(total_inward - (total_produced / 0.9 if total_produced else 0)):.1f} Tons")
    kpi2.metric("Pellets Produced", f"{total_produced:.1f} Tons")
    kpi3.metric("Pellet Yard Stock", f"{(total_produced - total_sold):.1f} Tons")
    kpi4.metric("Total Sales Revenue", f"₹{total_revenue:,.0f}")

    st.divider()

    st.subheader("Production & Efficiency Analysis")
    df_prod = pd.read_sql("SELECT date, shift, run_hours, input_tons, output_tons, yield_efficiency, stop_reason FROM production_logs ORDER BY id DESC", conn)
    st.dataframe(df_prod, use_container_width=True)

    st.subheader("Financial Overview")
    net_operating_profit = total_revenue - (total_raw_cost + total_expenses)
    st.metric("Net Operational Margin", f"₹{net_operating_profit:,.2f}", delta=f"{'Profitable' if net_operating_profit >= 0 else 'Loss'}")
