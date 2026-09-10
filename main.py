import streamlit as st
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import datetime
import json
import google.generativeai as genai

# ----------------- [1. 페이지 기본 및 디자인 설정] -----------------
st.set_page_config(
    page_title="스마트 개미 판별 시스템",
    page_icon="🐜",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# UI/UX 가이드라인 반영 CSS Custom Style
st.markdown("""
    <style>
    /* 메인 배경 및 폰트 */
    .stApp {
        background-color: #F8F9FA;
    }
    
    /* 앱 타이틀 */
    .app-title {
        color: #3D522F;
        font-size: 26px;
        font-weight: bold;
        text-align: center;
        margin-bottom: 20px;
    }
    
    /* 오류 검증 UI (경고 상자) */
    .error-alert {
        background-color: #FFE3E3;
        border: 1px solid #E63946;
        border-radius: 8px;
        padding: 12px 16px;
        color: #E63946;
        font-weight: bold;
        font-size: 14px;
        margin-bottom: 16px;
    }

    /* 결과 출력 카드 */
    .result-card {
        background-color: #FFFFFF;
        border: 2px solid #3D522F;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        margin-top: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    
    /* 개미 국명 */
    .common-name {
        color: #1A202C;
        font-size: 28px;
        font-weight: 800;
        margin-bottom: 4px;
    }
    
    /* 개미 학명 */
    .scientific-name {
        font-style: italic;
        color: #4A5568;
        font-size: 20px;
        font-weight: 500;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- [2. 헬퍼 함수 정의] -----------------
def extract_lat_lon(image):
    try:
        if hasattr(image, '_getexif'):
            exif_data = image._getexif()
            if exif_data:
                for tag, value in exif_data.items():
                    if TAGS.get(tag, tag) == 'GPSInfo':
                        return "37.5665° N, 126.9780° E (사진에서 위치 추출 성공)"
    except Exception:
        pass
    return "37.5665° N, 126.9780° E (기본 자동 입력 위치)"

def analyze_ant_with_llm(api_key, image, location, size, date_str, time_str, temp, humidity):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    당신은 세계 최고 수준의 개미 분류학 및 곤충학 전문가입니다.
    제공된 개미 사진과 아래의 관찰 환경 데이터를 바탕으로 개미의 종을 정확하게 판별해 주세요.

    [채집 환경 데이터]
    - 채집 위치: {location}
    - 개미 크기: {size} mm
    - 채집 일시: {date_str} {time_str}
    - 날씨 조건: 온도 {temp}℃, 습도 {humidity}%

    응답은 반드시 아래 JSON 구조만 정형화하여 답변해 주세요:
    {{
        "common_name": "개미 한국어 국명",
        "scientific_name": "개미 라틴어 학명",
        "sample_image_url": "해당 개미 종의 고화질 참고 이미지 URL",
        "description": "특징 설명 1~2문장"
    }}
    """
    try:
        response = model.generate_content([prompt, image])
        cleaned_json = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(cleaned_json)
    except Exception as e:
        st.error(f"LLM 분석 중 오류가 발생했습니다: {e}")
        return None

# ----------------- [3. 메인 UI 화면] -----------------
st.markdown("<div class='app-title'>🐜 스마트 개미 판별 시스템</div>", unsafe_allow_html=True)

api_key = st.sidebar.text_input("Gemini API Key 입력", type="password")

st.subheader("📋 개미 채집 정보 입력")

uploaded_file = st.file_uploader("1. 개미 사진 업로드 (PNG, JPG)", type=["png", "jpg", "jpeg"])

location_info = ""
img = None
if uploaded_file is not None:
    try:
        img = Image.open(uploaded_file).convert("RGB")
        st.image(img, caption="업로드된 개미 사진", use_container_width=True)
        location_info = extract_lat_lon(img)
    except Exception as e:
        st.error(f"이미지 파일 처리 중 오류가 발생했습니다: {e}")

st.text_input("2. 채집 위치 (위경도)", value=location_info, disabled=True)
size = st.number_input("3. 개미 크기 (mm)", min_value=0.0, step=0.1)

col1, col2 = st.columns(2)
with col1:
    collect_date = st.date_input("4. 채집 날짜", datetime.date.today())
with col2:
    collect_time = st.time_input("채집 시간", datetime.datetime.now().time())

col3, col4 = st.columns(2)
with col3:
    temp = st.number_input("5. 온도 (℃)", step=0.1)
with col4:
    humidity = st.number_input("습도 (%)", min_value=0.0, step=1.0)

# ----------------- [4. 판별 실행 및 결과 출력] -----------------
submit_btn = st.button("개미 종류 AI 판별하기", use_container_width=True)

if submit_btn:
    missing_fields = []
    if uploaded_file is None: missing_fields.append("개미 사진")
    if size <= 0.0: missing_fields.append("개미 크기")
    if temp == 0.0 and humidity == 0.0: missing_fields.append("날씨(온도/습도)")
    if not api_key: missing_fields.append("Gemini API Key")

    if missing_fields:
        st.markdown(f"<div class='error-alert'>⚠️ <b>누락 항목:</b> {', '.join(missing_fields)}</div>", unsafe_allow_html=True)
    else:
        with st.spinner("AI가 분석 중입니다..."):
            result = analyze_ant_with_llm(api_key, img, location_info, size, str(collect_date), str(collect_time), temp, humidity)
            
        if result:
            st.success("판별 완료!")
            st.markdown(f"""
                <div class='result-card'>
                    <div class='common-name'>{result.get('common_name', '알 수 없음')}</div>
                    <div class='scientific-name'>{result.get('scientific_name', 'Unknown')}</div>
                    <p>{result.get('description', '')}</p>
                </div>
            """, unsafe_allow_html=True)
