import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import requests 

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
# 🔥 MAPPING LAYANAN MEDANPEDIA (FIX) 🔥
# ==========================================
MAPPING_LAYANAN = {
    # --- INSTAGRAM ---
    "IG Followers Mix (Less Drop)": 6086,
    "IG Followers Indo (Real)": 5758,
    "IG Likes (Non-Drop)": 6121,
    "IG Views (Reels)": 5747,

    # --- TIKTOK ---
    "TikTok Likes": 5877,   
    "TikTok Views (FYP)": 6132,   
    "TikTok Shares": 5365,
    "TikTok Favorit": 6053, 
    "TikTok Followers": 5592, 
}

# --- 3. FUNGSI TEMBAK API MEDANPEDIA ---
def tembak_medanpedia(service_id, target_link, jumlah):
    try:
        url = st.secrets["medanpedia"]["url"]
        api_id = st.secrets["medanpedia"]["api_id"]
        api_key = st.secrets["medanpedia"]["api_key"]
        
        payload = {
            'api_id': api_id,
            'api_key': api_key,
            'service': service_id,
            'target': target_link,
            'quantity': jumlah
        }
        
        response = requests.post(url, data=payload)
        return response.json() 
        
    except Exception as e:
        return {"status": False, "data": str(e)}

# --- 4. FUNGSI PENDUKUNG ---
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
    
    # --- 6. MANAJEMEN ORDER (TAB TERPISAH) ---
    st.subheader("📋 Manajemen Order")
    
    # KITA BUAT 2 TAB DISINI
    tab_auto, tab_manual = st.tabs(["🤖 Mode Auto-Pilot", "✍️ Mode Manual"])

    # ========================================================
    # TAB 1: KHUSUS AUTO ORDER (Hanya yg punya ID Mapping)
    # ========================================================
    with tab_auto:
        st.info("Tab ini KHUSUS untuk menembak order ke MedanPedia secara otomatis.")
        
        if pending_df.empty:
            st.success("Tidak ada orderan pending.")
        else:
            # Hitung ada berapa yg bisa di-auto
            count_auto = 0
            
            for index, row in pending_df.iterrows():
                nama_layanan = row.get(col_layanan, '')
                id_pusat = MAPPING_LAYANAN.get(nama_layanan)
                
                # HANYA TAMPILKAN JIKA PUNYA ID PUSAT
                if id_pusat:
                    count_auto += 1
                    with st.expander(f"🤖 AUTO: {nama_layanan} | {row.get(col_target, '-')}"):
                        c1, c2 = st.columns([1, 1])
                        
                        with c1:
                            st.write(f"**Target:** `{row.get(col_target)}`")
                            st.write(f"**Jumlah:** {row.get(col_jumlah)}")
                            st.success(f"✅ ID Pusat Terdeteksi: **{id_pusat}**")
                            
                        with c2:
                            modal = st.number_input("Modal (Rp)", 0, step=100, key=f"auto_m_{index}")
                            
                            # TOMBOL EKSEKUSI API
                            if st.button("🚀 TEMBAK KE PUSAT", key=f"auto_btn_{index}"):
                                if modal == 0:
                                    st.warning("⚠️ Masukkan modal dulu agar profit terhitung!")
                                else:
                                    with st.spinner('Menghubungi MedanPedia...'):
                                        # 1. TEMBAK API
                                        hasil = tembak_medanpedia(id_pusat, row.get(col_target), row.get(col_jumlah))
                                        
                                        if hasil.get('status') == True:
                                            order_id_pusat = hasil['data'].get('id', 'Unknown')
                                            st.toast(f"✅ Sukses! Order ID: {order_id_pusat}")
                                            
                                            # 2. UPDATE SHEET
                                            try:
                                                headers = [h.strip() for h in sheet.row_values(1)]
                                                r = index + 2
                                                cuan = clean_currency(row.get(col_total, '0')) - modal
                                                
                                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                                st.success(f"Order {order_id_pusat} berhasil dicatat!")
                                                st.rerun()
                                            except Exception as ex:
                                                st.error(f"Error Update Sheet: {ex}")
                                        else:
                                            pesan_error = hasil.get('data', 'Unknown Error')
                                            st.error(f"❌ Gagal Order: {pesan_error}")
            
            if count_auto == 0:
                st.warning("Ada orderan pending, tapi TIDAK ADA yang cocok dengan Mapping ID. Silakan cek Tab Manual.")

    # ========================================================
    # TAB 2: KHUSUS MANUAL (Semua Orderan Muncul)
    # ========================================================
    with tab_manual:
        st.warning("Tab ini hanya untuk update status ke 'SUCCESS' di Google Sheet TANPA order ke MedanPedia.")
        
        if pending_df.empty:
            st.success("Aman! Tidak ada orderan pending.")
        else:
            for index, row in pending_df.iterrows():
                with st.expander(f"📝 MANUAL: {row.get(col_layanan, '-')}"):
                    c1, c2 = st.columns([1, 1])
                    
                    with c1:
                        st.write(f"**Target:** `{row.get(col_target)}`")
                        st.write(f"**Jumlah:** {row.get(col_jumlah)}")
                        
                        # Info WA Customer
                        raw_wa = str(row.get(col_wa, '')).strip()
                        clean_wa = raw_wa.replace('-', '').replace(' ', '').replace('+', '').replace('.0', '')
                        if clean_wa.startswith('0'): clean_wa = '62' + clean_wa[1:]
                        elif clean_wa.startswith('8'): clean_wa = '62' + clean_wa
                        
                        if len(clean_wa) > 8:
                             msg = f"Halo kak! Orderan *{row.get(col_layanan)}* sudah SUCCESS. Makasih! 🙏"
                             st.link_button("💬 Chat WA", f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}")

                    with c2:
                        modal = st.number_input("Modal (Rp)", 0, step=100, key=f"man_m_{index}")
                        
                        # TOMBOL MANUAL
                        if st.button("✅ UPDATE SHEET SAJA", key=f"man_btn_{index}"):
                            try:
                                headers = [h.strip() for h in sheet.row_values(1)]
                                r = index + 2
                                cuan = clean_currency(row.get(col_total, '0')) - modal
                                
                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                
                                st.success("Data berhasil diupdate manual!")
                                st.rerun()
                            except Exception as ex:
                                st.error(f"Gagal Update: {ex}")

except Exception as e:
    st.error("TERJADI ERROR:")
    st.write(e)
