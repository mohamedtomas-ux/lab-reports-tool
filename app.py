import fitz
import streamlit as st
from io import BytesIO
import zipfile
import cv2
import numpy as np

# إعدادات
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130

def detect_qr_code(page):
    """اكتشاف QR Code تلقائياً"""
    try:
        pix = page.get_pixmap(dpi=200)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        detector = cv2.QRCodeDetector()
        retval, decoded_info, points, _ = detector.detectAndDecodeMulti(img)
        
        qr_rects = []
        if retval and points is not None:
            scale_x = page.rect.width / pix.width
            scale_y = page.rect.height / pix.height
            
            for pts in points:
                margin = 15
                x_coords = pts[:, 0]
                y_coords = pts[:, 1]
                
                x0 = max(0, min(x_coords) * scale_x - margin)
                y0 = max(0, min(y_coords) * scale_y - margin)
                x1 = min(page.rect.width, max(x_coords) * scale_x + margin)
                y1 = min(page.rect.height, max(y_coords) * scale_y + margin)
                
                qr_rects.append(fitz.Rect(x0, y0, x1, y1))
        
        return qr_rects
    except Exception as e:
        print(f"خطأ في اكتشاف QR Code: {e}")
        return []

def process_pdf(input_pdf_bytes, template_pdf_bytes, old_header_height=95):
    """معالجة ملف PDF"""
    doc = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    template_doc = fitz.open(stream=template_pdf_bytes, filetype="pdf")
    template_page = template_doc[0]
    template_rect = template_page.rect
    template_width = template_rect.width
    template_height = template_rect.height
    
    for page in doc:
        page_rect = page.rect
        page_width = page_rect.width
        page_height = page_rect.height
        
        # 1. مسح الهيدر القديم
        header_rect = fitz.Rect(0, 0, page_width, old_header_height)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 2. اكتشاف وإزالة QR Code تلقائياً
        qr_rects = detect_qr_code(page)
        for qr_rect in qr_rects:
            page.add_redact_annot(qr_rect, fill=(1, 1, 1))
        if qr_rects:
            page.apply_redactions()
        
        # 3. إضافة الهيدر الجديد
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        # 4. إضافة الفوتر الجديد
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
    
    output_bytes = BytesIO()
    doc.save(output_bytes, deflate=True, garbage=4)
    output_bytes.seek(0)
    
    doc.close()
    template_doc.close()
    
    return output_bytes.getvalue()

def main():
    st.set_page_config(page_title="أداة تعديل هيدر نتائج المعمل", layout="wide")
    
    st.title("🏥 أداة تعديل هيدر نتائج المعمل")
    st.markdown("---")
    
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        old_header = st.number_input("ارتفاع الهيدر القديم", value=95, min_value=50, max_value=200)
        new_header = st.number_input("ارتفاع الهيدر الجديد", value=100, min_value=50, max_value=200)
        new_footer = st.number_input("ارتفاع الفوتر الجديد", value=130, min_value=50, max_value=200)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📁 رفع ملفات النتائج")
        uploaded_files = st.file_uploader(
            "اختر ملفات PDF للنتائج المعملية",
            type="pdf",
            accept_multiple_files=True
        )
    
    with col2:
        st.subheader("📄 رفع ملف الهيدر الجديد")
        template_file = st.file_uploader(
            "اختر ملف PDF للهيدر الجديد",
            type="pdf"
        )
    
    st.markdown("---")
    
    if st.button("🚀 بدء المعالجة", type="primary", use_container_width=True):
        if not uploaded_files:
            st.error("❌ يرجى رفع ملفات النتائج أولاً")
            return
        
        if not template_file:
            st.error("❌ يرجى رفع ملف الهيدر الجديد")
            return
        
        template_bytes = template_file.read()
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"جاري معالجة: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            input_bytes = uploaded_file.read()
            
            try:
                output_bytes = process_pdf(input_bytes, template_bytes, old_header)
                processed_files.append({
                    'name': uploaded_file.name,
                    'data': output_bytes
                })
            except Exception as e:
                st.error(f"خطأ في معالجة {uploaded_file.name}: {str(e)}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        status_text.text("✅ اكتملت المعالجة!")
        
        st.markdown("---")
        st.subheader(f"📦 الملفات المعالجة ({len(processed_files)} ملف)")
        
        if len(processed_files) == 1:
            st.download_button(
                label="📥 تحميل الملف المعدل",
                data=processed_files[0]['data'],
                file_name=processed_files[0]['name'],
                mime="application/pdf",
                use_container_width=True
            )
        else:
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_info in processed_files:
                    zip_file.writestr(file_info['name'], file_info['data'])
            
            zip_buffer.seek(0)
            
            st.download_button(
                label="📥 تحميل جميع الملفات (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="processed_reports.zip",
                mime="application/zip",
                use_container_width=True
            )

if __name__ == "__main__":
    main()