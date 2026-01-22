import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Ridho Store Admin", page_icon="🚀", layout="wide")

# --- FUNGSI BERSIH-BERSIH DUIT ---
def clean_currency(value):
    try:
        if isinstance(value, str):
            return int(value.replace('Rp', '').replace('.', '').replace(',', '').strip())
        return int(value)
    except:
        return 0

# --- KONEKSI KE GOOGLE SHEETS (VERSI ONLINE + FIX ERROR) ---
def get_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # Ambil secrets dari Streamlit Cloud
    # Kita ubah jadi dictionary biasa dulu biar bisa diedit
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    # 🔥 JURUS PERBAIKAN KUNCI (FIX INCORRECT PADDING) 🔥
    # Ini mengubah tulisan "\n" menjadi karakter Enter yang asli
    creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ID Sheet Kamu
    spreadsheet_id = "14zCestGTLmzP7KGymjyVtmsYxjPgZ44G6syQTVO0PHQ"
    sheet = client.open_by_key(spreadsheet_id).sheet1 
    data = sheet.get_all_records()
    return sheet, data

# --- HEADER ---
st.title("🚀 Ridho Store Command Center")

try:
    sheet, data = get_sheet_data()
    df = pd.DataFrame(data)

    # 🔥 JURUS ANTI SPASI HANTU 🔥
    # Kode ini membuang spasi di depan/belakang nama kolom otomatis
    df.columns = df.columns.str.strip()

    # --- DEBUGGER (PENTING BUAT CEK NAMA KOLOM) ---
    # Kalau masih error, lihat bagian kuning di layar aplikasi
    with st.expander("🔍 KLIK DISINI UNTUK CEK NAMA KOLOM ASLI"):
        st.write("Python membaca kolom kamu sebagai berikut:")
        st.write(df.columns.tolist())
        st.info("Pastikan nama di bawah (Mapping) sama persis dengan list di atas.")

    # --- MAPPING KOLOM ---
    # Sesuaikan teks di kanan dengan yang muncul di Debugger
    col_layanan = 'Pilih Layanan'
    col_target  = 'Target / Link'
    col_jumlah  = 'Jumlah Order'
    col_total   = 'Total Transfer'
    col_status  = 'Status'
    col_modal   = 'Modal'
    col_profit  = 'Profit'

    # Cek apakah kolom WAJIB ada
    wajib_ada = [col_total, col_status]
    missing = [c for c in wajib_ada if c not in df.columns]
    
    if missing:
        st.error(f"❌ KOLOM HILANG: {missing}")
        st.warning("Cek nama kolom di Google Sheet, mungkin ada typo atau beda huruf besar/kecil.")
        st.stop() # Berhenti dulu biar gak crash

    # --- LOGIC APLIKASI ---
    # 1. Bersihkan Angka
    df['clean_total'] = df[col_total].apply(clean_currency)
    
    # 2. Siapkan Kolom Modal & Profit (Kalau belum ada di sheet)
    if col_modal not in df.columns: df[col_modal] = 0
    if col_profit not in df.columns: df[col_profit] = 0
    df[col_modal] = pd.to_numeric(df[col_modal], errors='coerce').fillna(0)
    df[col_profit] = pd.to_numeric(df[col_profit], errors='coerce').fillna(0)

    # 3. Metrics
    total_omzet = df['clean_total'].sum()
    total_profit = df[col_profit].sum()
    pending_df = df[(df[col_status].str.upper() == 'PENDING') | (df[col_status] == '')]

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
            with st.expander(f"🛒 {row[col_layanan]} | {row.get('Timestamp', '-')}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**Target:** `{row[col_target]}`")
                    st.write(f"**Jumlah:** {row[col_jumlah]}")
                    st.write(f"**Transfer:** Rp {clean_currency(row[col_total]):,}")
                    st.caption(f"Metode: {row.get('Metode Pembayaran', '-')}")
                with c2:
                    modal = st.number_input("Modal (Rp)", min_value=0, step=100, key=f"m_{index}")
                    cuan = clean_currency(row[col_total]) - modal
                    if modal > 0:
                        st.write(f"Cuan: **Rp {cuan:,}**")
                    
                    if st.button("✅ SUKSES", key=f"b_{index}"):
                        with st.spinner('Updating...'):
                            try:
                                # Cari lokasi kolom
                                headers = [h.strip() for h in sheet.row_values(1)]
                                r = index + 2
                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                st.success("Done!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Gagal Update: {ex}")

except Exception as e:
    st.error("TERJADI ERROR:")
    st.code(e)
