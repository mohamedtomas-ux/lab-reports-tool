import fitz
import streamlit as st
from io import BytesIO
import zipfile
import os

# إعدادات
OLD_HEADER_HEIGHT = 100
NEW_HEADER_HEIGHT = 100
NEW_FOOTER_HEIGHT = 130

# اسم ملف الهيدر الثابت (لازم يكون موجود في نفس المجلد)
TEMPLATE_FILE = "template.pdf"

def detect_and_remove_qr_code(page):
    """اكتشاف وإزالة QR Code فقط"""
    try:
        image_list = page.get_images(full=True)
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            img_rects = page.get_image_rects(xref)
            
            for rect in img_rects:
                # لو الصورة في الجزء السفلي من الصفحة
                if rect.y0 > page.rect.height * 0.75:
                    width = rect.width
                    height = rect.height
                    
                    # لو الصورة مربعة تقريباً وصغيرة (QR Code)
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
    """معالجة ملف PDF"""
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
        
        # 1. مسح الهيدر القديم
        header_rect = fitz.Rect(0, 0, page_width, OLD_HEADER_HEIGHT)
        page.add_redact_annot(header_rect, fill=(1, 1, 1))
        page.apply_redactions()
        
        # 2. اكتشاف وإزالة QR Code فقط
        detect_and_remove_qr_code(page)
        
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
    
    # التحقق من وجود ملف الهيدر الثابت
    if not os.path.exists(TEMPLATE_FILE):
        st.error(f"❌ ملف الهيدر الثابت غير موجود: {TEMPLATE_FILE}")
        st.info("يرجى رفع ملف `template.pdf` إلى GitHub Repository")
        return
    
    st.success("✅ ملف الهيدر الثابت جاهز للاستخدام")
    st.markdown("---")
    
    # رفع ملفات النتائج فقط
    st.subheader("📁 رفع ملفات النتائج")
    uploaded_files = st.file_uploader(
        "اختر ملفات PDF للنتائج المعملية",
        type="pdf",
        accept_multiple_files=True,
        help="يمكنك رفع عدد غير محدود من الملفات"
    )
    
    st.markdown("---")
    
    if st.button("🚀 بدء المعالجة", type="primary", use_container_width=True):
        if not uploaded_files:
            st.error("❌ يرجى رفع ملفات النتائج أولاً")
            return
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        processed_files = []
        
        for i, uploaded_file in enumerate(uploaded_files):
            status_text.text(f"جاري معالجة: {uploaded_file.name} ({i+1}/{len(uploaded_files)})")
            
            input_bytes = uploaded_file.read()
            
            try:
                output_bytes = process_pdf(input_bytes, TEMPLATE_FILE)
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
