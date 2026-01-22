import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse 

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

# --- KONEKSI KE GOOGLE SHEETS ---
def get_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
    except KeyError:
        st.error("Error: Secrets belum disetting.")
        st.stop()
    
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    
    # ID Sheet
    spreadsheet_id = "14zCestGTLmzP7KGymjyVtmsYxjPgZ44G6syQTVO0PHQ"
    sheet = client.open_by_key(spreadsheet_id).sheet1 
    data = sheet.get_all_records()
    return sheet, data

# --- BAGIAN UTAMA APLIKASI ---
st.title("🚀 Ridho Store Command Center")

try:
    sheet, data = get_sheet_data()
    df = pd.DataFrame(data)

    df.columns = df.columns.str.strip()

    # Mapping Kolom
    col_layanan = 'Pilih Layanan'
    col_target  = 'Target / Link'
    col_jumlah  = 'Jumlah Order'
    col_total   = 'Total Transfer'
    col_status  = 'Status'
    col_modal   = 'Modal'
    col_profit  = 'Profit'
    col_wa      = 'Nomor WhatsApp Anda' 

    if col_status not in df.columns:
        st.error(f"Kolom '{col_status}' tidak ditemukan!")
        st.stop()

    df['clean_total'] = df[col_total].apply(clean_currency)
    
    for col in [col_modal, col_profit]:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    total_omzet = df['clean_total'].sum()
    total_profit = df[col_profit].sum()
    
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
                    
                    # 🔥 FIX LOGIKA WA DISINI 🔥
                    raw_wa = str(row.get(col_wa, '')).strip()
                    # Bersihkan spasi, strip, dan .0 (efek angka excel)
                    clean_wa = raw_wa.replace('-', '').replace(' ', '').replace('+', '').replace('.0', '')
                    
                    # Logika deteksi 08 atau 8
                    if clean_wa.startswith('0'):
                        clean_wa = '62' + clean_wa[1:]
                    elif clean_wa.startswith('8'):
                        clean_wa = '62' + clean_wa
                    
                    st.caption(f"📱 WA: +{clean_wa}")

                with c2:
                    st.write("### Aksi")
                    
                    if clean_wa and len(clean_wa) > 8:
                        nama_layanan = row.get(col_layanan, 'Layanan')
                        target_akun = row.get(col_target, '-')
                        
                        pesan = f"Halo kak! Orderan *{nama_layanan}* untuk target *{target_akun}* sudah *SUCCESS* diproses ya. Terima kasih telah order di Ridho Store! 🙏"
                        pesan_encoded = urllib.parse.quote(pesan)
                        link_wa = f"https://wa.me/{clean_wa}?text={pesan_encoded}"
                        
                        st.link_button("💬 Chat WA", link_wa)
                    else:
                        st.warning("No WA Tidak Valid")

                    st.write("---")
                    
                    modal = st.number_input("Modal (Rp)", min_value=0, step=100, key=f"m_{index}")
                    
                    if st.button("✅ SUKSESKAN", key=f"b_{index}"):
                        with st.spinner('Updating...'):
                            try:
                                headers = [h.strip() for h in sheet.row_values(1)]
                                r = index + 2
                                cuan = clean_currency(row.get(col_total, '0')) - modal
                                
                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                
                                st.success("Berhasil!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Gagal Update: {ex}")

except Exception as e:
    st.error("TERJADI ERROR FATAL:")
    st.code(e)
