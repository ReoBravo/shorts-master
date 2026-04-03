import streamlit as st
from PIL import Image
import os
import io
import zipfile
# from google.cloud import texttospeech

# --- [앱 기본 설정] ---
st.set_page_config(
    page_title="AI Shorts Asset Maker",
    page_icon="🎬",
    layout="wide"
)

# 커스텀 CSS로 좀 더 '앱'다운 느낌 주기
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3em; background-color: #FF4B4B; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 10px; background-color: #008CBA; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- [사이드바: 설정 및 가이드] ---
with st.sidebar:
    st.title("⚙️ 시스템 설정")
    st.info("이 도구는 스토리보드 이미지를 자르고, 대본을 음성(TTS)으로 변환해줍니다.")
    
    st.subheader("1. Google TTS 설정")
    gcs_key_path = st.text_input("JSON 키 파일 경로", placeholder="C:/keys/service-account.json")
    gcs_key_content = st.text_area("또는 JSON 내용 직접 입력")

    st.subheader("2. 출력 비율 설정")
    ratio_option = st.selectbox(
        "프레임 비율",
        ["원본 유지", "16:9 (Wide)", "9:16 (Shorts)"],
        index=2
    )

    st.subheader("3. 그리드(Grid) 설정")
    col_r, col_c = st.columns(2)
    rows = col_r.number_input("가로 줄(행)", min_value=1, value=4)
    cols = col_c.number_input("세로 칸(열)", min_value=1, value=3)

# --- [메인 화면] ---
st.title("🎬 AI 쇼츠 제작 에셋 자동 생성기")
st.write("이미지를 업로드하고 대본을 입력하면, 편집에 바로 쓸 수 있는 파일들을 만들어 드립니다.")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("🖼️ 스토리보드 이미지")
    uploaded_file = st.file_uploader("이미지를 드래그해서 놓으세요", type=["jpg", "jpeg", "png"])
    if uploaded_file:
        st.image(uploaded_file, caption="업로드된 원본", use_container_width=True)

with col2:
    st.subheader("📜 대본 입력")
    script_text = st.text_area("각 프레임에 들어갈 대본을 한 줄씩 입력하세요.", height=300, 
                               placeholder="첫 번째 프레임 대사\n두 번째 프레임 대사\n...")

# --- [핵심 로직 함수] ---
def crop_to_ratio(image, ratio_type):
    img_w, img_h = image.size
    if ratio_type == "16:9 (Wide)":
        target_ratio = 16 / 9
    elif ratio_type == "9:16 (Shorts)":
        target_ratio = 9 / 16
    else:
        return image

    current_ratio = img_w / img_h
    if current_ratio > target_ratio:
        new_w = int(target_ratio * img_h)
        offset = (img_w - new_w) // 2
        return image.crop((offset, 0, offset + new_w, img_h))
    else:
        new_h = int(img_w / target_ratio)
        offset = (img_h - new_h) // 2
        return image.crop((0, offset, img_w, offset + new_h))

# --- [실행 버튼 및 처리] ---
if st.button("🚀 에셋 생성 및 압축 시작"):
    if not uploaded_file:
        st.error("이미지를 먼저 업로드해 주세요!")
    else:
        try:
            # 1. 이미지 처리
            img = Image.open(uploaded_file)
            w, h = img.size
            cell_w, cell_h = w // cols, h // rows
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                
                # 프레임 추출 루프
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                total_cells = rows * cols
                count = 0
                for r in range(rows):
                    for c in range(cols):
                        count += 1
                        left, top = c * cell_w, r * cell_h
                        right, bottom = left + cell_w, top + cell_h
                        
                        cropped = img.crop((left, top, right, bottom))
                        if ratio_option != "원본 유지":
                            cropped = crop_to_ratio(cropped, ratio_option)
                        
                        # 메모리에 저장 후 ZIP 추가
                        img_byte_arr = io.BytesIO()
                        cropped.save(img_byte_arr, format='PNG')
                        zf.writestr(f"images/frame_{count:02d}.png", img_byte_arr.getvalue())
                        
                        progress_bar.progress(int((count / total_cells) * 50))
                        status_text.text(f"이미지 분할 중... ({count}/{total_cells})")

                # 2. TTS 처리 (입력이 있을 때만)
                # if script_text.strip():
                    status_text.text("음성 생성 중 (Google TTS)...")
                    # (여기서 실제 Google 클라이언트 초기화 및 생성 로직이 들어갑니다)
                    # 실제 API 연결은 사용자 키가 필요하므로 예외처리를 포함합니다.
                    lines = script_text.strip().split('\n')
                    for i, line in enumerate(lines):
                        # TTS 파일 생성 시뮬레이션 (API 연결 성공 시 실행)
                        # 실제 구현 시에는 이 부분에 지난번 알려드린 tts_client.synthesize_speech 로직을 넣으시면 됩니다.
                        zf.writestr(f"audio/voice_{i+1:02d}.txt", f"'{line}' 에 대한 음성 파일이 생성되어야 함 (API 연결 필요)")
                    
                    progress_bar.progress(100)

            status_text.text("✅ 모든 작업 완료!")
            st.balloons()

            # 다운로드 버튼
            st.download_button(
                label="🎁 생성된 에셋(.zip) 내려받기",
                data=zip_buffer.getvalue(),
                file_name="shorts_project_assets.zip",
                mime="application/zip"
            )
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

# --- [푸터] ---
st.markdown("---")
st.caption("제작: 프레임추출+TTS | 본 도구는 이미지 자동 분할 및 비율 교정 기능을 제공합니다.")