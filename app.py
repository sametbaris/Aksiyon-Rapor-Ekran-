import streamlit as st
import pandas as pd
from datetime import datetime
import io
import re

# ================= AYARLAR =================
# Sayfayı geniş yapıyoruz ki tablo rahat nefes alsın
st.set_page_config(page_title="Fiyat Karşılaştırma Paneli", page_icon="⚖️", layout="wide")

SHEET_ID = "1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0" # Kendi ID'ni yapıştırmayı unutma!
SHEET_NAME = "Guncel"

# ================= MODERN CSS (YUVARLAK HATLAR VE GÖLGELER) =================
st.markdown("""
<style>
    /* Arka planı çok hafif gri yaparak beyaz tablonun öne çıkmasını sağlama */
    .stApp {
        background-color: #fcfcfc;
    }
    
    /* Veri Tablosunun dış çerçevesini yuvarlatma ve hafif gölge ekleme */
    [data-testid="stDataFrame"] {
        border-radius: 16px !important;
        overflow: hidden !important;
        box-shadow: 0px 8px 24px rgba(0, 0, 0, 0.06) !important;
        border: 1px solid #f0f0f0 !important;
    }
    
    /* Arama kutusunu modern, yuvarlak hap şeklinde yapma */
    .stTextInput input {
        border-radius: 25px !important;
        border: 1px solid #e0e0e0 !important;
        padding: 12px 20px !important;
        box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.03) !important;
    }
    .stTextInput input:focus {
        border-color: #4CAF50 !important;
        box-shadow: 0px 4px 12px rgba(76, 175, 80, 0.15) !important;
    }

    /* İndirme butonunu modernleştirme */
    .stDownloadButton button {
        border-radius: 25px !important;
        background-color: #1E1E1E !important; /* Asil Koyu Gri/Siyah */
        color: white !important;
        border: none !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0px 6px 16px rgba(0, 0, 0, 0.1) !important;
    }
    .stDownloadButton button:hover {
        background-color: #4CAF50 !important; /* Üzerine gelince Yeşil */
        transform: translateY(-2px) !important;
        color: white !important;
        box-shadow: 0px 8px 20px rgba(76, 175, 80, 0.2) !important;
    }
</style>
""", unsafe_allow_html=True)

# ================= VERİ ÇEKME VE TEMİZLEME =================
@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        df.columns = [c.strip() for c in df.columns]
        
        # SİHİRLİ DOKUNUŞ: Bütün "None" ve "NaN" ları tamamen siliyoruz (Boş bırakıyoruz)
        df = df.fillna("")
        
        return df
    except:
        return None

# ================= METNİ SAYIYA ÇEVİRME FİLTRESİ =================
def parse_price(val):
    if not val: return None
    val_str = str(val).lower().replace("tl", "").replace("₺", "").strip()
    
    clean = re.sub(r"[^\d.,]", "", val_str)
    if not clean: return None
    
    if "." in clean and "," in clean:
        clean = clean.replace(".", "").replace(",", ".")
    elif "," in clean:
        clean = clean.replace(",", ".")
        
    try:
        return float(clean)
    except:
        return None

# ================= BRAUN SHOP BAZLI RENKLENDİRME =================
def apply_comparative_style(row):
    target_cols = ["Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    ref_col = "Braun Shop"
    
    styles = ['' for _ in row.index]
    
    ref_val = parse_price(row[ref_col]) if ref_col in row.index else None
    
    if ref_val is not None and ref_val > 0:
        for col in target_cols:
            if col in row.index:
                col_idx = row.index.get_loc(col)
                current_val = parse_price(row[col])
                
                # Eğer hücre boşsa ("") işlem yapma, rengi beyaz kalsın
                if current_val is not None:
                    if current_val == ref_val:
                        # Eşitse soft yuvarlak hatlı Yeşil
                        styles[col_idx] = 'background-color: #e8f5e9; color: #2e7d32; font-weight: bold;'
                    else:
                        # Sapma varsa soft yuvarlak hatlı Kırmızı
                        styles[col_idx] = 'background-color: #ffebee; color: #c62828;'
    
    return styles

# ================= ARAYÜZ (UI) =================
st.title("⚖️ Braun Shop Bazlı Fiyat Analizi")
st.info("💡 Braun Shop fiyatına eşit olanlar **Yeşil**, düşük veya yüksek olanlar **Kırmızı** görünür. Boş hücreler veri olmadığını gösterir.")

df = load_data()

if df is not None:
    search = st.text_input("🔍 Listede Ara (Ürün Adı, Barkod...):")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    styled_df = df.style.apply(apply_comparative_style, axis=1)

    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.write("<br>", unsafe_allow_html=True) # Araya şık bir boşluk
    
    now = datetime.now().strftime("%d.%m.%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.download_button(
            label=f"📥 Verileri Excel Olarak İndir ({now})",
            data=output.getvalue(),
            file_name=f"Fiyat_Analiz_Raporu_{now}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    st.error("Google Sheets bağlantısı kurulamadı!")
