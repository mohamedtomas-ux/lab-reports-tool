import fitz
import streamlit as st
from io import BytesIO
import zipfile
import numpy as np
from PIL import Image

# إعدادات
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130
SIGNATURE_HEIGHT = 80

def detect_qr_code_simple(page):
    """اكتشاف QR Code باستخدام PyMuPDF فقط - بدون OpenCV"""
    try:
        qr_rects = []
        
        # البحث عن الصور في الصفحة
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            
            # الحصول على موقع الصورة في الصفحة
            img_rects = page.get_image_rects(xref)
            
            for rect in img_rects:
                # لو الصورة في الجزء السفلي من الصفحة (أكثر من 70% من ارتفاع الصفحة)
                if rect.y0 > page.rect.height * 0.7:
                    width = rect.width
                    height = rect.height
                    
                    # لو الصورة مربعة تقريباً (QR Code عادة مربع) وصغيرة
                    if 0.7 < width/height < 1.3 and width < 150 and height < 150:
                        # إضافة هامش حول الـ QR Code
                        margin = 15
                        qr_rect = fitz.Rect(
                            max(0, rect.x0 - margin),
                            max(0, rect.y0 - margin),
                            min(page.rect.width, rect.x1 + margin),
                            min(page.rect.height, rect.y1 + margin)
                        )
                        qr_rects.append(qr_rect)
        
        return qr_rects
    except Exception as e:
        print(f"خطأ في اكتشاف QR Code: {e}")
        return []

def extract_signature_region(page):
    """استخراج منطقة التوقيع من نهاية الصفحة"""
    try:
        page_height = page.rect.height
        
        # منطقة التوقيع (فوق الفوتر القديم)
        sig_rect = fitz.Rect(
            0,
            page_height - 200,  # من 200 نقطة من الأسفل
            page.rect.width,
            page_height - 130   # إلى 130 نقطة من الأسفل
        )
        
        # استخراج المنطقة كصورة
        pix = page.get_pixmap(clip=sig_rect, dpi=150)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        
        # تحويل لـ PNG bytes
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        
        return buffer.getvalue()
    except Exception as e:
        print(f"خطأ في استخراج التوقيع: {e}")
        return None

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
        
        # 1. استخراج التوقيع من الصفحة الأصلية (قبل المسح)
        signature_bytes = extract_signature_region(page)
        
        # 2. مسح الهيدر القديم
        header_rect = fitz.Rect(0, 0, page_width, old_header_height)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 3. اكتشاف وإزالة QR Code تلقائياً
        qr_rects = detect_qr_code_simple(page)
        for qr_rect in qr_rects:
            page.add_redact_annot(qr_rect, fill=(1, 1, 1))
        if qr_rects:
            page.apply_redactions()
        
        # 4. مسح منطقة التوقيع الأصلية
        sig_rect = fitz.Rect(
            0,
            page_height - 200,
            page_width,
            page_height - 130
        )
        page.add_redact_annot(sig_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 5. إضافة الهيدر الجديد
        new_header_rect = fitz.Rect(0, 0, page_width, NEW_HEADER_HEIGHT)
        header_clip = fitz.Rect(0, 0, template_width, NEW_HEADER_HEIGHT)
        page.show_pdf_page(new_header_rect, template_doc, 0, clip=header_clip)
        
        # 6. إضافة الفوتر الجديد
        new_footer_rect = fitz.Rect(0, page_height - NEW_FOOTER_HEIGHT, page_width, page_height)
        footer_clip = fitz.Rect(0, template_height - NEW_FOOTER_HEIGHT, template_width, template_height)
        page.show_pdf_page(new_footer_rect, template_doc, 0, clip=footer_clip)
        
        # 7. إضافة التوقيع المستخرج فوق الفوتر الجديد
        if signature_bytes:
            sig_insert_rect = fitz.Rect(
                0,
                page_height - NEW_FOOTER_HEIGHT - SIGNATURE_HEIGHT,
                page_width,
                page_height - NEW_FOOTER_HEIGHT
            )
            page.insert_image(sig_insert_rect, stream=signature_bytes)
    
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
        
        global NEW_HEADER_HEIGHT, NEW_FOOTER_HEIGHT
        NEW_HEADER_HEIGHT = new_header
        NEW_FOOTER_HEIGHT = new_footer
    
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
