import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Ridho Store Admin", page_icon="🚀", layout="wide")

# --- FUNGSI BERSIH DUIT ---
def clean_currency(value):
    try:
        if isinstance(value, str):
            return int(value.replace('Rp', '').replace('.', '').replace(',', '').strip())
        return int(value)
    except:
        return 0

# --- KONEKSI KE GOOGLE SHEETS (VERSI RESET & STABIL) ---
def get_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 1. Ambil Secrets dengan cara standar Streamlit
    # Ini akan membaca bagian [gcp_service_account] di Secrets
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except KeyError:
        st.error("Error: Secrets belum disetting dengan benar. Cek nama [gcp_service_account].")
        st.stop()
    
    # 2. 🔥 PERBAIKAN FORMAT KUNCI (WAJIB ADA) 🔥
    # Mengubah "\\n" menjadi Enter yang asli agar tidak Error Padding
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ID Sheet Kamu
    spreadsheet_id = "14zCestGTLmzP7KGymjyVtmsYxjPgZ44G6syQTVO0PHQ"
    sheet = client.open_by_key(spreadsheet_id).sheet1 
    data = sheet.get_all_records()
    return sheet, data

# --- BAGIAN UTAMA APLIKASI ---
st.title("🚀 Ridho Store Command Center")

try:
    sheet, data = get_sheet_data()
    df = pd.DataFrame(data)

    # Bersihkan Spasi Nama Kolom
    df.columns = df.columns.str.strip()

    # Mapping Kolom (Sesuaikan jika ada perubahan)
    col_layanan = 'Pilih Layanan'
    col_target  = 'Target / Link'
    col_jumlah  = 'Jumlah Order'
    col_total   = 'Total Transfer'
    col_status  = 'Status'
    col_modal   = 'Modal'
    col_profit  = 'Profit'

    # Cek Kolom
    if col_status not in df.columns:
        st.error(f"Kolom '{col_status}' tidak ditemukan di Google Sheet!")
        st.write("Kolom yang terbaca:", df.columns.tolist())
        st.stop()

    # Pemrosesan Data
    df['clean_total'] = df[col_total].apply(clean_currency)
    
    # Pastikan kolom Modal/Profit ada
    for col in [col_modal, col_profit]:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Tampilan Metrics
    total_omzet = df['clean_total'].sum()
    total_profit = df[col_profit].sum()
    
    # Filter Pending (Case insensitive & handle kosong)
    pending_df = df[
        (df[col_status].str.strip().str.upper() == 'PENDING') | 
        (df[col_status].isna()) | 
        (df[col_status] == '')
    ]

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Omzet", f"Rp {total_omzet:,.0f}")
    c2.metric("💸 Profit", f"Rp {total_profit:,.0f}")
    c3.metric("🔥 Pending", f"{len(pending_df)}", delta_color="inverse")

    st.markdown("---")
    st.subheader("📋 Orderan Masuk")

    if pending_df.empty:
        st.success("Aman! Tidak ada orderan pending.")
    else:
        for index, row in pending_df.iterrows():
            with st.expander(f"🛒 {row.get(col_layanan, 'Layanan')} | {row.get('Timestamp', '-')}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Target:** `{row.get(col_target, '-')}`")
                    st.write(f"**Jumlah:** {row.get(col_jumlah, '-')}")
                    st.write(f"**Transfer:** Rp {clean_currency(row.get(col_total, '0')):,}")
                    st.caption(f"Metode: {row.get('Metode Pembayaran', '-')}")
                with c2:
                    modal = st.number_input("Modal (Rp)", min_value=0, step=100, key=f"m_{index}")
                    
                    if st.button("✅ SUKSES", key=f"b_{index}"):
                        with st.spinner('Updating...'):
                            try:
                                headers = [h.strip() for h in sheet.row_values(1)]
                                r = index + 2
                                
                                # Update data
                                cuan = clean_currency(row.get(col_total, '0')) - modal
                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                
                                st.success("Done!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Gagal: {ex}")

except Exception as e:
    st.error("TERJADI ERROR:")
    st.code(e)
