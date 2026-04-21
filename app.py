import streamlit as st
import pandas as pd
from datetime import datetime
import io

# ================= AYARLAR =================
# Sayfa tasarımını minimal ve geniş yapmak için:
st.set_page_config(page_title="Pazaryeri Fiyat Raporu", page_icon="📊", layout="wide")

# Buraya kendi Google Sheets ID'ni yapıştır
SHEET_ID = "https://docs.google.com/spreadsheets/d/1So1V2L7NLT-xow8VEwGeogR2Ot7lDhhJUpG_cNSLTC0/edit?usp=sharing" 
SHEET_NAME = "Guncel"
# ===========================================

# Veriyi Google Sheets'ten çeken fonksiyon
@st.cache_data(ttl=300) # Veriyi 5 dakikada bir yeniler (Sunucuyu yormaz)
def load_data():
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"
    try:
        df = pd.read_csv(url)
        return df
    except Exception as e:
        return None

# Excel indirme butonunu hazırlayan fonksiyon
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Fiyatlar')
    return output.getvalue()

# ================= ARAYÜZ (UI) =================
st.title("📊 Aksiyon ve Pazaryeri Fiyat Raporu")
st.markdown("Bu ekranda, güncel pazaryeri fiyatlarını minimal bir tasarımla inceleyebilir ve filtreleyebilirsiniz.")

df = load_data()

if df is not None:
    # Google Sheets'te "Son Güncelleme" bilgisini yazdığımız hücreyi (N1) bulup arayüze ekleyelim
    # (Eğer tablonda N sütunu yoksa veya farklıysa burayı silebilirsin)
    son_guncelleme = "Bilinmiyor"
    if "Son Güncelleme" in df.columns: # Eğer başlık olarak aldıysa
        st.caption(f"🔄 **{df.columns[-1]}**") 
    
    st.divider() # Şık bir ayraç çizgisi

    # 1. Filtreleme Alanı (Arama)
    search_query = st.text_input("🔍 Ürün Barkodu veya Kodu ile Arama Yapın:")
    
    if search_query:
        # Arama kutusuna bir şey yazılırsa, df'i o kelimeye göre filtrele
        mask = df.apply(lambda row: row.astype(str).str.contains(search_query, case=False, na=False).any(), axis=1)
        df_filtered = df[mask]
    else:
        df_filtered = df
        
    # 2. Veri Tablosunu Gösterme
    # Streamlit'in kendi süper hızlı dataframe özelliği:
    st.dataframe(df_filtered, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 3. Dinamik Tarihli Excel İndirme Butonu
    now_str = datetime.now().strftime("%d.%m.%Y_%H-%M")
    excel_data = to_excel(df_filtered)
    
    col1, col2, col3 = st.columns([1,2,1]) # Butonu ortalamak için
    with col2:
        st.download_button(
            label="📥 Güncel Tabloyu Excel Olarak İndir",
            data=excel_data,
            file_name=f"Fiyat_Raporu_{now_str}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
else:
    st.error("⚠️ Veriler Google Sheets'ten çekilemedi. Dosya ID'sini veya paylaşım ayarlarını kontrol edin.")