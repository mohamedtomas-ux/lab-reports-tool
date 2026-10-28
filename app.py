import fitz
import streamlit as st
import streamlit.components.v1 as components
from io import BytesIO
import zipfile
import os
import base64
from datetime import datetime

# إعدادات التطبيق
OLD_HEADER_HEIGHT = 100
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130
TEMPLATE_FILE = "template.pdf"
LOGO_FILE = "logo.png"

# CSS للتصميم المدمج (Compact)
st.markdown("""
<style>
    /* إخفاء الشريط الجانبي */
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    
    /* الخلفية بيضاء */
    .stApp { background: #ffffff; }
    
    /* تقليل المسافات العامة في Streamlit */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 1000px !important;
    }
    
    /* اللوجو - حجم صغير جداً */
    .logo-wrapper {
        margin-top: 10px !important;
        margin-bottom: 5px !important;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    
    .logo-wrapper img {
        max-height: 70px !important; /* تصغير اللوجو */
        width: auto;
    }
    
    /* العنوان - حجم مضغوط */
    .main-title {
        text-align: center;
        padding: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 10px !important;
    }
    
    .main-title h1 {
        margin: 0 0 2px 0 !important;
        font-size: 1.4em !important; /* تصغير العنوان */
        font-weight: bold;
        color: #000000;
    }
    
    .main-title p {
        margin: 0 !important;
        font-size: 0.8em !important;
        color: #555555;
    }
    
    /* بوكس رفع الملفات - مضغوط */
    .upload-box {
        background: #f8f9fa;
        padding: 10px 15px !important;
        border-radius: 8px;
        border: 2px dashed #8B1A1A;
        margin: 5px auto 10px auto !important;
        max-width: 600px;
        text-align: right;
        direction: rtl;
    }
    
    .upload-box h2 {
        color: #000000;
        margin: 0 0 2px 0 !important;
        font-size: 1.1em !important;
        font-weight: bold;
    }
    
    .small-hint {
        color: #666;
        font-size: 0.75em !important;
        margin: 0 !important;
    }
    
    /* زر المعالجة - صغير ومدمج */
    .stButton > button {
        background: #8B1A1A !important;
        color: white !important;
        border: none !important;
        padding: 8px 30px !important;
        border-radius: 6px !important;
        font-weight: bold !important;
        font-size: 1em !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 5px rgba(139, 26, 26, 0.3) !important;
    }
    
    .stButton > button:hover {
        background: #A52A2A !important;
        transform: translateY(-1px) !important;
    }
    
    /* إخفاء footer */
    footer { visibility: hidden; }
    
    /* uploader */
    .stFileUploader {
        background: transparent !important;
        border: none !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* تقليل حجم الإحصائيات */
    .stat-card {
        padding: 8px !important;
        border-radius: 8px;
    }
    
    .stat-card h2 { 
        margin: 0; 
        font-size: 1.5em !important; 
    }
    
    .stat-card p { 
        margin: 2px 0 0 0 !important; 
        font-size: 0.8em !important; 
    }
    
    /* تقليل المسافات بين الأعمدة */
    .stColumn {
        padding: 0 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# دوال المعاينة والمعالجة
def preview_pdf(pdf_bytes, height=400):
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="{height}px" type="application/pdf" style="border: none; border-radius: 8px;"></iframe>'
    components.html(pdf_display, height=height + 20, scrolling=True)

def detect_and_remove_qr_code(page):
    try:
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            img_rects = page.get_image_rects(xref)
            for rect in img_rects:
                if rect.y0 > page.rect.height * 0.75:
                    width = rect.width
                    height = rect.height
                    if 0.7 < width/height < 1.3 and width < 120 and height < 120:
                        margin = 10
                        qr_rect = fitz.Rect(
                            max(0, rect.x0 - margin),
                            max(0, rect.y0 - margin),
                            min(page.rect.width, rect.x1 + margin),
                            min(page.rect.height, rect.y1 + margin)
                        )
                        page.add_redact_annot(qr_rect, fill=(1, 1, 1))
        page.apply_redactions()
    except Exception as e:
        print(f"خطأ في اكتشاف QR Code: {e}")

def process_pdf(input_pdf_bytes, template_path):
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    template_doc = fitz.open(template_path)
    template_page = template_doc[0]
    template_rect = template_page.rect
    template_width = template_rect.width
    template_height = template_rect.height
    
    for page in doc:
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        header_rect = fitz.Rect(0, 0, page_width, OLD_HEADER_HEIGHT)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        detect_and_remove_qr_code(page)
        
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
    
    output_bytes = BytesIO()
    doc.save(output_bytes, deflate=True, garbage=4)
    output_bytes.seek(0)
    
    doc.close()
    template_doc.close()
    
    return output_bytes.getvalue()

# الواجهة الرئيسية
def main():
    st.set_page_config(
        page_title="برنامج الفحص الشامل",
        page_icon="🏥",
        layout="centered",  # تغيير إلى centered لتقليل العرض الزائد
        initial_sidebar_state="collapsed"
    )
    
    logo_exists = os.path.exists(LOGO_FILE)
    template_exists = os.path.exists(TEMPLATE_FILE)
    
    if not template_exists:
        st.error("❌ ملف الهيدر الثابت غير موجود!")
        return
    
    # 1. اللوجو (حجم صغير)
    if logo_exists:
        col1, col2, col3 = st.columns([1, 4, 1])
        with col2:
            st.image(LOGO_FILE, use_container_width=True)
    else:
        st.warning("⚠️ اللوجو غير متوفر")
    
    # 2. العنوان (مضغوط)
    st.markdown("""
    <div class="main-title">
        <h1>برنامج الفحص الشامل - طباعة النتائج المعملية</h1>
        <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. بوكس رفع الملفات (مضغوط)
    st.markdown("""
    <div style="text-align: center;">
        <div class="upload-box">
            <h2> رفع ملفات النتائج</h2>
            <p class="small-hint">يمكن اختيار أكثر من ملف</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col_up1, col_up2, col_up3 = st.columns([1, 4, 1])
    with col_up2:
        uploaded_files = st.file_uploader(
            "",
            type="pdf",
            accept_multiple_files=True,
            label_visibility="collapsed"
        )
    
    # 4. إحصائيات الملفات المرفوعة (صغيرة)
    if uploaded_files:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center;">
                <h2>{len(uploaded_files)}</h2>
                <p>ملفات</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
            st.markdown(f"""
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; text-align: center;">
                <h2>{total_size:.2f}</h2>
                <p>ميغابايت</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div class="stat-card" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); color: white; text-align: center;">
                <h2>✓</h2>
                <p>جاهز</p>
            </div>
            """, unsafe_allow_html=True)
    
    # 5. زر المعالجة (صغير وفي المنتصف)
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        start_button = st.button("بدء المعالجة", use_container_width=True)
    
    if start_button:
        if not uploaded_files:
            st.error("❌ يرجى رفع ملفات النتائج أولاً")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        processed_files = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"⚙️ جاري معالجة: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            input_bytes = uploaded_file.read()
            try:
                output_bytes = process_pdf(input_bytes, TEMPLATE_FILE)
                processed_files.append({
                    'name': uploaded_file.name,
                    'data': output_bytes,
                    'size': len(output_bytes) / 1024
                })
            except Exception as e:
                st.error(f"❌ خطأ في معالجة {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.empty()
        progress_bar.empty()
        
        st.success(f"✅ اكتملت المعالجة بنجاح! ({len(processed_files)} ملف)")
        
        # المعاينة والتحميل
        if len(processed_files) > 0:
            st.markdown("---")
            st.subheader("️ معاينة وتحميل")
            
            if len(processed_files) == 1:
                st.download_button(
                    label=f"📥 تحميل {processed_files[0]['name']}",
                    data=processed_files[0]['data'],
                    file_name=processed_files[0]['name'],
                    mime="application/pdf",
                    use_container_width=True
                )
                # معاينة الملف الوحيد
                preview_pdf(processed_files[0]['data'], height=400)
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_info in processed_files:
                        zip_file.writestr(file_info['name'], file_info['data'])
                zip_buffer.seek(0)
                
                st.download_button(
                    label=f" تحميل جميع الملفات ({len(processed_files)} ملف) كـ ZIP",
                    data=zip_buffer.getvalue(),
                    file_name=f"processed_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                # معاينة أول ملف فقط لتوفير المساحة
                st.markdown(f"**معاينة أول ملف:** {processed_files[0]['name']}")
                preview_pdf(processed_files[0]['data'], height=400)

if __name__ == "__main__":
    main()
