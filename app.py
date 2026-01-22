import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import urllib.parse
import requests 
import html
import math 

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

# =================================================================
# 🔥 MAPPING LAYANAN & HARGA MODAL (LOGIKA BARU) 🔥
# =================================================================
MAPPING_LAYANAN = {
    # --- INSTAGRAM ---
    "IG Followers Mix (Less Drop)": { "id": 6081, "harga": 20000 },
    "IG Followers Indo (Real)":     { "id": 5758, "harga": 40091 },
    "IG Likes (Non-Drop)":          { "id": 6121, "harga": 1999 },
    "IG Views (Reels)":             { "id": 5747, "harga": 182 },

    # --- TIKTOK ---
    "TikTok Likes":       { "id": 5877, "harga": 237 },   
    "TikTok Views (FYP)": { "id": 6132, "harga": 20 },   
    "TikTok Shares":      { "id": 5365, "harga": 1552 },
    "TikTok Favorit":     { "id": 6053, "harga": 182 }, 
    "TikTok Followers":   { "id": 5592, "harga": 14468 }, 
}

# --- 3. FUNGSI KHUSUS MEDANPEDIA ---
def cek_saldo_medanpedia():
    """Mengecek sisa saldo di akun MedanPedia"""
    try:
        # Endpoint khusus profile/saldo
        url_profile = "https://api.medanpedia.co.id/profile"
        api_id = st.secrets["medanpedia"]["api_id"]
        api_key = st.secrets["medanpedia"]["api_key"]
        
        payload = {'api_id': api_id, 'api_key': api_key}
        
        response = requests.post(url_profile, data=payload)
        hasil = response.json()
        
        if hasil.get('status') == True:
            # Ambil data balance
            return int(float(hasil['data']['balance']))
        else:
            return 0
    except:
        return 0

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

# 🔥 FITUR BARU: TAMPILKAN SALDO DI SIDEBAR 🔥
with st.sidebar:
    st.markdown("---")
    st.caption("🏦 Info Pusat")
    saldo_pusat = cek_saldo_medanpedia()
    
    if saldo_pusat < 10000:
        st.error(f"Sisa Saldo: Rp {saldo_pusat:,}")
        st.warning("⚠️ Saldo Menipis! Segera Deposit.")
    else:
        st.success(f"Sisa Saldo: Rp {saldo_pusat:,}")
    st.markdown("---")

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
    
    # --- 6. MANAJEMEN ORDER ---
    st.subheader("📋 Manajemen Order")
    
    tab_auto, tab_manual = st.tabs(["🤖 Mode Auto-Pilot", "✍️ Mode Manual"])

    # ========================================================
    # TAB 1: KHUSUS AUTO ORDER
    # ========================================================
    with tab_auto:
        st.info("Tab ini KHUSUS untuk menembak order ke MedanPedia secara otomatis.")
        
        if pending_df.empty:
            st.success("Tidak ada orderan pending.")
        else:
            count_auto = 0
            for index, row in pending_df.iterrows():
                nama_layanan = row.get(col_layanan, '')
                data_layanan = MAPPING_LAYANAN.get(nama_layanan) 
                
                raw_target = str(row.get(col_target, '-'))
                clean_target = html.unescape(raw_target)

                if data_layanan:
                    count_auto += 1
                    id_pusat = data_layanan['id']
                    harga_pusat = data_layanan['harga']
                    
                    # Hitung Modal Otomatis
                    qty = int(row.get(col_jumlah, 0))
                    estimasi_modal = math.ceil((qty / 1000) * harga_pusat) 
                    
                    with st.expander(f"🤖 AUTO: {nama_layanan} | {clean_target}"):
                        c1, c2 = st.columns([1, 1])
                        
                        with c1:
                            st.write(f"**Target:** `{clean_target}`")
                            st.write(f"**Jumlah:** {qty}")
                            st.caption(f"🆔 ID Pusat: {id_pusat} | 🏷️ Modal/1k: Rp {harga_pusat:,}")
                            
                        with c2:
                            modal = st.number_input("Modal Otomatis (Rp)", value=estimasi_modal, step=100, key=f"auto_m_{index}")
                            
                            if st.button("🚀 TEMBAK KE PUSAT", key=f"auto_btn_{index}"):
                                # Cek Saldo Dulu biar aman
                                if saldo_pusat < modal:
                                    st.error("❌ SALDO MEDANPEDIA TIDAK CUKUP! Silakan deposit dulu.")
                                elif modal == 0 and harga_pusat > 0:
                                    st.warning("⚠️ Cek modal lagi!")
                                else:
                                    with st.spinner('Menghubungi MedanPedia...'):
                                        hasil = tembak_medanpedia(id_pusat, clean_target, qty)
                                        
                                        if hasil.get('status') == True:
                                            order_id_pusat = hasil['data'].get('id', 'Unknown')
                                            st.toast(f"✅ Sukses! Order ID: {order_id_pusat}")
                                            
                                            try:
                                                headers = [h.strip() for h in sheet.row_values(1)]
                                                r = index + 2
                                                cuan = clean_currency(row.get(col_total, '0')) - modal
                                                
                                                sheet.update_cell(r, headers.index(col_status)+1, "SUCCESS")
                                                sheet.update_cell(r, headers.index(col_modal)+1, modal)
                                                sheet.update_cell(r, headers.index(col_profit)+1, cuan)
                                                st.success(f"Order {order_id_pusat} Berhasil!")
                                                st.rerun()
                                            except Exception as ex:
                                                st.error(f"Error Update Sheet: {ex}")
                                        else:
                                            pesan_error = hasil.get('data', 'Unknown Error')
                                            st.error(f"❌ Gagal Order: {pesan_error}")
            
            if count_auto == 0:
                st.warning("Tidak ada orderan yang cocok dengan Mapping ID.")

    # ========================================================
    # TAB 2: KHUSUS MANUAL
    # ========================================================
    with tab_manual:
        st.warning("Update status ke 'SUCCESS' TANPA order ke MedanPedia.")
        
        if pending_df.empty:
            st.success("Aman! Tidak ada orderan pending.")
        else:
            for index, row in pending_df.iterrows():
                
                raw_target = str(row.get(col_target, '-'))
                clean_target = html.unescape(raw_target)
                qty = int(row.get(col_jumlah, 0))
                
                nama_layanan = row.get(col_layanan, '')
                data_layanan = MAPPING_LAYANAN.get(nama_layanan)
                modal_default = 0
                if data_layanan:
                    modal_default = math.ceil((qty / 1000) * data_layanan['harga'])

                with st.expander(f"📝 MANUAL: {nama_layanan}"):
                    c1, c2 = st.columns([1, 1])
                    
                    with c1:
                        st.write(f"**Target:** `{clean_target}`")
                        st.write(f"**Jumlah:** {qty}")
                        
                        raw_wa = str(row.get(col_wa, '')).strip()
                        clean_wa = raw_wa.replace('-', '').replace(' ', '').replace('+', '').replace('.0', '')
                        if clean_wa.startswith('0'): clean_wa = '62' + clean_wa[1:]
                        elif clean_wa.startswith('8'): clean_wa = '62' + clean_wa
                        
                        if len(clean_wa) > 8:
                             msg = f"Halo kak! Orderan *{nama_layanan}* sudah SUCCESS. Makasih! 🙏"
                             st.link_button("💬 Chat WA", f"https://wa.me/{clean_wa}?text={urllib.parse.quote(msg)}")

                    with c2:
                        modal = st.number_input("Modal (Rp)", value=modal_default, step=100, key=f"man_m_{index}")
                        
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
