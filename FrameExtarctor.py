import streamlit as st
from PIL import Image, ImageFilter
import io
import zipfile
import fitz  # PyMuPDF

# Page Configuration
st.set_page_config(page_title="Shorts Frame Master", layout="wide")

st.title("🎬 Automatic Frame Extractor")
st.info("Convert PDF slides, individual images, or grid-style storyboards into Shorts-ready (1080x1920) assets.")

# 1. Sidebar Menu (Global Settings)
with st.sidebar:
    st.header("⚙️ Settings")
    
    st.subheader("1. Quality Control")
    quality_boost = st.checkbox("Enhance Sharpness", value=True, help="Sharpens text and images during resizing to prevent blurring.")
    pdf_dpi = st.slider("PDF Rendering Quality (DPI)", 2, 5, 3, help="Higher values result in clearer text for PDF files.")
    
    st.divider()
    
    st.subheader("2. Grid Splitter (Single Image)")
    use_grid = st.checkbox("Enable Grid Splitting", value=False, help="Check this if you want to split a single storyboard image into multiple frames.")
    grid_input = st.text_input("Grid Config (Cols x Rows)", value="5x4", disabled=not use_grid)

# 2. Main Upload Section (Drag & Drop)
st.subheader("🖼️ Upload Files")
uploaded_files = st.file_uploader(
    "Drag and drop PDF or Image files here", 
    type=["png", "jpg", "jpeg", "pdf"], 
    accept_multiple_files=True
)

# 3. High-Quality Conversion Logic
def process_to_shorts(img, boost=False):
    img = img.convert("RGB")
    cw, ch = img.size
    target_ratio = 9/16
    
    # Aspect Ratio Correction (Black Padding)
    if cw/ch > target_ratio:
        # Landscape -> Vertical padding
        nh = int(cw / target_ratio)
        final = Image.new("RGB", (cw, nh), (0, 0, 0))
        final.paste(img, (0, (nh - ch) // 2))
    else:
        # Portrait -> Horizontal padding
        nw = int(ch * target_ratio)
        final = Image.new("RGB", (nw, ch), (0, 0, 0))
        final.paste(img, ((nw - cw) // 2, 0))
    
    # Resize to 1080x1920 with LANCZOS filter
    final = final.resize((1080, 1920), Image.Resampling.LANCZOS)
    if boost:
        final = final.filter(ImageFilter.SHARPEN)
    return final

# 4. Execution & Zip Generation
if st.button("🚀 Start Batch Conversion", use_container_width=True):
    if not uploaded_files:
        st.error("Please upload files first!")
    else:
        try:
            progress_bar = st.progress(0)
            status_text = st.empty()
            zip_buffer = io.BytesIO()
            
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                frame_count = 1
                total_input = len(uploaded_files)
                
                for idx, file in enumerate(uploaded_files):
                    file_ext = file.name.split('.')[-1].lower()
                    
                    # --- Case 1: PDF Processing ---
                    if file_ext == 'pdf':
                        status_text.text(f"📄 Extracting PDF: {file.name}")
                        doc = fitz.open(stream=file.read(), filetype="pdf")
                        for i in range(len(doc)):
                            page = doc.load_page(i)
                            pix = page.get_pixmap(matrix=fitz.Matrix(pdf_dpi, pdf_dpi))
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            final_img = process_to_shorts(img, boost=quality_boost)
                            
                            img_io = io.BytesIO()
                            final_img.save(img_io, format='PNG', quality=100)
                            zip_file.writestr(f"frames/frame_{frame_count:02d}.png", img_io.getvalue())
                            frame_count += 1
                        doc.close()
                    
                    # --- Case 2: Image Processing (incl. Grid Split) ---
                    else:
                        img = Image.open(file)
                        if use_grid:
                            status_text.text(f"✂️ Splitting Grid: {file.name}")
                            cols, rows = map(int, grid_input.lower().split('x'))
                            tw, th = img.width // cols, img.height // rows
                            for r in range(rows):
                                for c in range(cols):
                                    crop = img.crop((c*tw, r*th, (c+1)*tw, (r+1)*th))
                                    final_img = process_to_shorts(crop, boost=quality_boost)
                                    img_io = io.BytesIO()
                                    final_img.save(img_io, format='PNG', quality=100)
                                    zip_file.writestr(f"frames/frame_{frame_count:02d}.png", img_io.getvalue())
                                    frame_count += 1
                        else:
                            status_text.text(f"🖼️ Processing Image: {file.name}")
                            final_img = process_to_shorts(img, boost=quality_boost)
                            img_io = io.BytesIO()
                            final_img.save(img_io, format='PNG', quality=100)
                            zip_file.writestr(f"frames/frame_{frame_count:02d}.png", img_io.getvalue())
                            frame_count += 1
                    
                    progress_bar.progress((idx + 1) / total_input)
                
                status_text.text(f"✅ Successfully generated {frame_count-1} high-quality frames!")

            st.download_button("🎁 Download All Assets (ZIP)", 
                               data=zip_buffer.getvalue(), 
                               file_name="shorts_assets.zip", 
                               use_container_width=True)
            
        except Exception as e:
            st.error(f"Error occurred: {e}")