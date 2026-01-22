import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import requests # Wajib ada di requirements.txt

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Ridho Store Admin", page_icon="🚀", layout="wide")

# --- 2. LOGIN SYSTEM ---
try:
    password_rahasia = st.secrets["auth"]["password"]
except KeyError:
    st.error("⚠️ Password belum disetting di Secrets.")
    st.stop()

with st.sidebar:
    st.title("🔐 Login Admin")
    input_pass = st.text_input("Masukkan Password", type="password")
    
if input_pass != password_rahasia:
    st.warning("⛔ Masukkan password untuk akses Dashboard.")
    st.stop()

# ==========================================
# 🔥 MAPPING LAYANAN MEDANPEDIA (EDIT DISINI) 🔥
# ==========================================
# Format: "Nama Di Google Form" : ID_ANGKA_MEDANPEDIA
# Cek ID di menu 'Daftar Layanan' MedanPedia

MAPPING_LAYANAN = {
    # GANTI ANGKA INI DENGAN ID ASLI DARI MEDANPEDIA
    "Followers Instagram Murah": 2541,  
    "Likes Instagram Fast": 1120,
    "TikTok Followers": 3310,
    "Subscriber Youtube": 550,
}

# --- 3. FUNGSI TEMBAK API MEDANPEDIA ---
def tembak_medanpedia(service_id, target_link, jumlah):
    try:
        # Ambil credentials dari Secrets
        url = st.secrets["medanpedia"]["url"]
        api_id = st.secrets["medanpedia"]["api_id"]
        api_key = st.secrets["medanpedia"]["api_key"]
        
        # Format Data Sesuai Dokumentasi MedanPedia
        payload = {
            'api_id': api_id,
            'api_key': api_key,
            'service': service_id,
            'target': target_link,
            'quantity': jumlah
        }
        
        # Kirim Request (POST)
        response = requests.post(url, data=payload)
        hasil = response.json() 
        
        # MedanPedia biasanya return: {'status': True, 'data': {'id': '12345'}}
        return hasil
        
    except Exception as e:
        return {"status": False, "data": str(e)}

# --- 4. FUNGSI PENDUKUNG (Google Sheet & Currency) ---
def clean_currency(value):
    try:
        if isinstance(value, str):
            return int(value.replace('Rp', '').replace('.', '').replace(',', '').strip())
        return int(value)
    except:
        return 0

def get_sheet_data():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    if "private_key" in creds_dict:
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    spreadsheet_id = "14zCestGTLmzP7KGymjyVtmsYxjPgZ44G6syQTVO0PHQ"
    sheet = client.open_by_key(spreadsheet_id).sheet1 
    data = sheet.get_all_records()
    return sheet, data

# --- 5. DASHBOARD UTAMA ---
st.title("🚀 Ridho Store Auto-Pilot")

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
    col_waktu   = 'Timestamp'

    if col_status not in df.columns:
        st.error(f"Kolom '{col_status}' tidak ditemukan!")
        st.stop()

    df['clean_total'] = df[col_total].apply(clean_currency)
    for col in [col_modal, col_profit]:
        if col not in df.columns: df[col] = 0
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Metrics
    total_omzet = df['clean_total'].sum()
    total_profit = df[col_profit].sum()
    pending_df = df[(df[col_status].str.strip().str.upper() == 'PENDING') | (df[col_status].isna()) | (df[col_status] == '')]

    c1, c2, c3 = st.columns(3)
    c1.metric("💰 Omzet", f"Rp {total_omzet:,.0f}")
    c2.metric("💸 Profit", f"Rp {total_profit:,.0f}")
    c3.metric("🔥 Pending", f"{len(pending_df)}", delta_color="inverse")

    st.markdown("---")
    
    # --- 6. ORDER LIST ---
    st.subheader("📋 Daftar Order Pending")

    if pending_df.empty:
        st.success("Aman! Tidak ada orderan pending.")
    else:
        for index, row in pending_df.iterrows():
            with st.expander(f"🛒 {row.get(col_layanan, '-')}"):
                c1, c2 = st.columns(2)
                
                nama_layanan_user = row.get(col_layanan, '')
                target = row.get(col_target, '-')
                jumlah = row.get(col_jumlah, 0)
                
                # Cek ID MedanPedia
                id_pusat = MAPPING_LAYANAN.get(nama_layanan_user)

                with c1:
                    st.write(f"**Target:** `{target}`")
                    st.write(f"**Jumlah:** {jumlah}")
                    
                    if id_pusat:
                        st.success(f"✅ Auto-Connect MedanPedia (ID: {id_pusat})")
                    else:
                        st.warning("⚠️ ID tidak ditemukan di Mapping (Mode Manual)")
                    
                    # Info WA
                    raw_wa = str(row.get(col_wa, '')).strip()
                    clean_wa = raw_wa.replace('-', '').replace(' ', '').replace('+', '').replace('.0', '')
                    if clean_wa.startswith('0'): clean_wa = '62' + clean_wa[1:]
                    elif clean_wa.startswith('8'): clean_wa = '62' + clean_wa
                    
                    if len(clean_wa) > 8:
                         msg = f"Halo kak! Orderan *{nama_layanan_user}* sudah diproses. Thanks! 🙏"
                         st.link_button("💬 Chat WA", f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}")

                with c2:
                    st.write("### Eksekusi")
                    modal = st.number_input("Modal (Rp)", 0, step=100, key=f"m_{index}")
                    
                    # TOMBOL AUTO ORDER
                    tombol_label = "🚀 ORDER KE PUSAT & UPDATE" if id_pusat else "✅ UPDATE MANUAL SAJA"
                    
                    if st.button(tombol_label, key=f"btn_{index}"):
                        if modal == 0:
                            st.warning("Isi modal dulu bos!")
                        else:
                            with st.spinner('Menghubungi MedanPedia...'):
                                order_sukses = False
                                pesan_error = ""

                                # 1. TEMBAK API (Jika ID Ada)
                                if id_pusat:
                                    hasil = tembak_medanpedia(id_pusat, target, jumlah)
                                    
                                    # Cek status respon dari MedanPedia (True/False)
                                    if hasil.get('status') == True:
                                        order_id_pusat = hasil['data'].get('id', 'Unknown')
                                        st.toast(f"✅ Sukses Order! Order ID Pusat: {order_id_pusat}")
                                        order_sukses = True
                                    else:
                                        pesan_error = hasil.get('data', 'Unknown Error')
                                        st.error(f"❌ Gagal Order ke Pusat: {pesan_error}")
                                else:
                                    # Jika tidak ada ID, langsung sukseskan manual
                                    order_sukses = True
                                    st.toast("Update Manual Berhasil")

                                # 2. UPDATE SHEET (Hanya jika order sukses/manual)
                                if order_sukses:
                                    try:
                                        headers = [h.strip() for h in sheet.row_values(1)]
                                        r = index + 2
                                        cuan = clean_currency(row.get(col_total, '0')) - modal
                                        
                                        sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                        sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                        sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                        
                                        st.success("Data Tersimpan!")
                                        st.rerun()
                                    except Exception as ex:
                                        st.error(f"Gagal Update Sheet: {ex}")

except Exception as e:
    st.error("TERJADI ERROR:")
    st.write(e)
