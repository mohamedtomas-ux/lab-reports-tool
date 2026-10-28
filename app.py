import fitz
import streamlit as st
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

# دالة لقراءة اللوجو وتحويله إلى Base64
def get_logo_base64():
    try:
        with open(LOGO_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except:
        return None

logo_b64 = get_logo_base64()

# CSS للتصميم
st.markdown("""
<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarNav"] { display: none; }
    .stApp { background: #ffffff; }
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        max-width: 900px !important;
    }
    .main-title {
        text-align: center;
        padding: 0 !important;
        margin-top: 5px !important;
        margin-bottom: 15px !important;
    }
    .main-title h1 {
        margin: 5px 0 2px 0 !important;
        font-size: 1.6em !important;
        font-weight: bold;
        color: #000000;
    }
    .main-title p {
        margin: 0 !important;
        font-size: 0.85em !important;
        color: #555555;
    }
    .stats-bar {
        display: flex;
        justify-content: center;
        gap: 15px;
        margin: 10px 0 15px 0;
        flex-wrap: wrap;
    }
    .stat-badge {
        background: #f8f9fa;
        border: 1px solid #e0e0e0;
        border-radius: 20px;
        padding: 6px 18px;
        font-size: 0.9em;
        color: #333;
        display: flex;
        align-items: center;
        gap: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stat-badge .number {
        font-weight: bold;
        color: #8B1A1A;
        font-size: 1.1em;
    }
    .stat-badge.success {
        background: #e8f5e9;
        border-color: #c8e6c9;
    }
    .stat-badge.success .number {
        color: #2e7d32;
    }
    .stButton > button {
        background: #8B1A1A !important;
        color: white !important;
        border: none !important;
        padding: 12px 40px !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        font-size: 1.1em !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 3px 8px rgba(139, 26, 26, 0.3) !important;
    }
    .stButton > button:hover {
        background: #A52A2A !important;
        transform: translateY(-2px) !important;
    }
    footer { visibility: hidden; }
    .stFileUploader {
        background: #fafafa;
        border: 2px dashed #8B1A1A;
        border-radius: 10px;
        padding: 15px !important;
        margin: 10px 0 !important;
    }
</style>
""", unsafe_allow_html=True)

# دوال المعالجة
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
        page_icon="",
        layout="centered",
        initial_sidebar_state="collapsed"
    )
    
    template_exists = os.path.exists(TEMPLATE_FILE)
    
    if not template_exists:
        st.error("❌ ملف الهيدر الثابت غير موجود!")
        return
    
    # 1. اللوجو باستخدام Base64 (مضمون 100%)
    if logo_b64:
        st.markdown(f"""
        <div style="text-align: center; margin: 10px 0 15px 0;">
            <img src="data:image/png;base64,{logo_b64}" style="max-width: 100%; height: auto; display: inline-block;" />
        </div>
        """, unsafe_allow_html=True)
    
    # 2. العنوان
    st.markdown("""
    <div class="main-title">
        <h1>برنامج الفحص الشامل - طباعة النتائج المعملية</h1>
        <p>أداة احترافية وسريعة لتعديل هيدر وفوتر ملفات نتائج التحاليل المعملية</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 3. زر الرفع
    st.markdown('<div style="text-align: center; margin-bottom: 5px;"><strong style="color: #333; font-size: 1.1em;">📁 رفع ملفات النتائج</strong><br><small style="color: #666;">يمكن اختيار أكثر من ملف</small></div>', unsafe_allow_html=True)
    
    uploaded_files = st.file_uploader(
        "",
        type="pdf",
        accept_multiple_files=True,
        label_visibility="collapsed",
        key="main_uploader"
    )
    
    # 4. شريط الإحصائيات
    if uploaded_files:
        total_size = sum(f.size for f in uploaded_files) / (1024 * 1024)
        st.markdown(f"""
        <div class="stats-bar">
            <div class="stat-badge">
                <span>📄 الملفات:</span>
                <span class="number">{len(uploaded_files)}</span>
            </div>
            <div class="stat-badge">
                <span>💾 الحجم:</span>
                <span class="number">{total_size:.2f} MB</span>
            </div>
            <div class="stat-badge success">
                <span>✅ الحالة:</span>
                <span class="number">جاهز</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # 5. زر المعالجة
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
            status_text.text(f"⚙️ معالجة: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            input_bytes = uploaded_file.read()
            try:
                output_bytes = process_pdf(input_bytes, TEMPLATE_FILE)
                processed_files.append({
                    'name': uploaded_file.name,
                    'data': output_bytes,
                    'size': len(output_bytes) / 1024
                })
            except Exception as e:
                st.error(f"❌ خطأ في {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.empty()
        progress_bar.empty()
        
        # 6. زر التحميل الأخضر
        if len(processed_files) > 0:
            if len(processed_files) == 1:
                download_data = processed_files[0]['data']
                download_filename = processed_files[0]['name']
                download_mime = "application/pdf"
            else:
                zip_buffer = BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for file_info in processed_files:
                        zip_file.writestr(file_info['name'], file_info['data'])
                zip_buffer.seek(0)
                download_data = zip_buffer.getvalue()
                download_filename = f"reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
                download_mime = "application/zip"
            
            col_d1, col_d2, col_d3 = st.columns([1, 2, 1])
            with col_d2:
                st.download_button(
                    label="التحميل",
                    data=download_data,
                    file_name=download_filename,
                    mime=download_mime,
                    use_container_width=True,
                    key="download_btn"
                )
            
            # CSS لجعل زر التحميل أخضر
            st.markdown("""
            <style>
                a[data-testid="stDownloadButton-download_btn"] button {
                    background: #2e7d32 !important;
                    color: white !important;
                    border: none !important;
                    padding: 12px 40px !important;
                    border-radius: 8px !important;
                    font-weight: bold !important;
                    font-size: 1.1em !important;
                    box-shadow: 0 3px 8px rgba(46, 125, 50, 0.3) !important;
                }
                a[data-testid="stDownloadButton-download_btn"] button:hover {
                    background: #388e3c !important;
                    transform: translateY(-2px) !important;
                }
            </style>
            """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
