import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ================= AYARLAR =================
st.set_page_config(page_title="Fiyat Analiz Paneli", page_icon="📈", layout="wide")

# Google Sheets ID'niz (Kendi ID'nizi buraya yapıştırın)
SHEET_ID = "1a2b3c4d5e6f7g8h9i0j_ABCDEFG" 
SHEET_NAME = "Guncel"

# Veriyi çeken fonksiyon
@st.cache_data(ttl=60) 
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        # Sütun isimlerindeki boşlukları temizleyelim
        df.columns = [c.strip() for c in df.columns]
        return df
    except:
        return None

# ================= RENKLENDİRME MANTIĞI (STYLING) =================
def highlight_min_prices(row):
    """
    Her satırdaki fiyat sütunlarını karşılaştırır ve en ucuz olanı yeşil yapar.
    """
    # Karşılaştırılacak fiyat sütunları
    price_cols = ["Aksiyon", "Braun Shop", "Media Markt", "Teknosa", "Vatan", "Trendyol", "Hepsiburada", "Amazon"]
    
    # Sadece tabloda var olan sütunları seçelim
    valid_cols = [c for c in price_cols if c in row.index]
    
    # Değerleri sayıya çevirelim (Hata almamak için)
    numeric_values = pd.to_numeric(row[valid_cols], errors='coerce')
    min_val = numeric_values.min()
    
    styles = ['' for _ in row.index]
    for col in valid_cols:
        col_idx = row.index.get_loc(col)
        val = pd.to_numeric(row[col], errors='coerce')
        if pd.notnull(val) and val == min_val and min_val > 0:
            styles[col_idx] = 'background-color: #d4edda; color: #155724; font-weight: bold' # Soft Yeşil
    return styles

# ================= ARAYÜZ =================
st.title("📈 Stratejik Fiyat Takip Paneli")

df = load_data()

if df is not None:
    # Arama motoru
    search = st.text_input("🔍 Ürün Ara (Barkod, İsim vb.):")
    if search:
        df = df[df.apply(lambda r: r.astype(str).str.contains(search, case=False).any(), axis=1)]

    # Renklendirmeyi uygula
    styled_df = df.style.apply(highlight_min_prices, axis=1)

    # Link ve Sütun Yapılandırması
    # Not: CSV ile linkler doğrudan gelmediği için, eğer link sütunların varsa
    # onları LinkColumn olarak tanımlayabiliriz. 
    # Eğer linkler hücrenin içindeyse, Excel formatında çekmemiz gerekir.
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Aksiyon": st.column_config.NumberColumn(format="%.2f TL"),
            "Braun Shop": st.column_config.NumberColumn(format="%.2f TL"),
            "Trendyol": st.column_config.NumberColumn(format="%.2f TL"),
            "Hepsiburada": st.column_config.NumberColumn(format="%.2f TL"),
            "Amazon": st.column_config.NumberColumn(format="%.2f TL"),
            # Eğer ürün linklerini içeren bir sütun eklemek istersen:
            # "Ürün Linki": st.column_config.LinkColumn("Git"),
        }
    )

    st.divider()
    
    # Excel Export
    now = datetime.now().strftime("%d-%m-%Y_%H-%M")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    
    st.download_button(
        label="📥 Verileri Excel Olarak İndir",
        data=output.getvalue(),
        file_name=f"Fiyat_Analizi_{now}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    st.warning("Veri yüklenemedi. Lütfen Google Sheets ID ve Paylaşım ayarlarını kontrol edin.")
