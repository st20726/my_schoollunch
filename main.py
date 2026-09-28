import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import re

# --------------------------------------------------
# 기본 설정
# --------------------------------------------------

st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍚",
    layout="wide"
)

st.title("학교 급식 찾아보기")
st.write("학교 이름을 검색하고, 원하는 날짜의 중식 메뉴를 확인해 보세요.")


# --------------------------------------------------
# 나이스 API 주소
# --------------------------------------------------

SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"
MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# --------------------------------------------------
# API 결과에서 RESULT 코드 확인
# --------------------------------------------------

def get_result_code(data):
    """
    NEIS 응답에서 RESULT의 CODE를 찾아 반환한다.
    """
    try:
        if "schoolInfo" in data:
            blocks = data["schoolInfo"]

            for block in blocks:
                if "head" in block:
                    for item in block["head"]:
                        if "RESULT" in item:
                            return item["RESULT"].get("CODE")

        if "mealServiceDietInfo" in data:
            blocks = data["mealServiceDietInfo"]

            for block in blocks:
                if "head" in block:
                    for item in block["head"]:
                        if "RESULT" in item:
                            return item["RESULT"].get("CODE")

    except Exception:
        pass

    return None


# --------------------------------------------------
# 학교 이름 보정
# --------------------------------------------------

def expand_school_name(name):
    """
    검색 결과가 없을 때 줄임말을 정식 명칭으로 바꾼다.

    예:
    수도여고 -> 수도여자고등학교
    수도고 -> 수도고등학교
    """

    name = name.strip()

    # '여고'를 '여자고등학교'로 변경
    if name.endswith("여고"):
        return name[:-2] + "여자고등학교"

    # '고'를 '고등학교'로 변경
    if name.endswith("고"):
        return name[:-1] + "고등학교"

    return None


# --------------------------------------------------
# 학교 검색 API
# --------------------------------------------------

@st.cache_data(ttl=3600)
def search_schools(school_name):
    """
    학교 이름의 일부를 이용해 학교를 검색한다.
    """

    params = {
        "Type": "json",
        "SCHUL_NM": school_name
    }

    try:
        response = requests.get(
            SCHOOL_API_URL,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return None, "network"
    except ValueError:
        return None, "json"

    result_code = get_result_code(data)

    if result_code == "INFO-200":
        return [], "empty"

    try:
        rows = data["schoolInfo"][1]["row"]
    except (KeyError, IndexError, TypeError):
        return [], "empty"

    schools = []

    for row in rows:
        schools.append({
            "name": row.get("SCHUL_NM", ""),
            "office_code": row.get("ATPT_OFCDC_SC_CODE", ""),
            "school_code": row.get("SD_SCHUL_CODE", ""),
            "region": row.get("LCTN_SC_NM", "")
        })

    return schools, "success"


# --------------------------------------------------
# 급식 조회 API
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_meal(office_code, school_code, date_string):
    """
    선택한 학교의 특정 날짜 중식을 조회한다.
    """

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_string,
        "MLSV_TO_YMD": date_string,
        "pSize": "1000",
        "pIndex": "1"
    }

    try:
        response = requests.get(
            MEAL_API_URL,
            params=params,
            timeout=10
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException:
        return None, "network"
    except ValueError:
        return None, "json"

    result_code = get_result_code(data)

    if result_code == "INFO-200":
        return None, "empty"

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError, TypeError):
        return None, "empty"

    if not rows:
        return None, "empty"

    # 혹시 여러 날짜가 반환되더라도 선택한 날짜만 찾는다.
    for row in rows:
        if row.get("MLSV_YMD") == date_string:
            return row, "success"

    return None, "empty"


# --------------------------------------------------
# 메뉴 표시용 함수
# --------------------------------------------------

def clean_menu(menu):
    """
    NEIS의 <br/>로 구분된 메뉴를 화면에 보기 좋게 표시한다.
    메뉴 뒤의 알레르기 번호는 그대로 유지한다.
    """

    if not menu:
        return ""

    # HTML escape를 먼저 적용해서 안전하게 표시
    menu = html.escape(menu)

    # <br>, <br/>, <br /> 등을 줄바꿈으로 변경
    menu = re.sub(
        r"&lt;br\s*/?&gt;",
        "<br>",
        menu,
        flags=re.IGNORECASE
    )

    return menu


# --------------------------------------------------
# 한국 시간
# --------------------------------------------------

KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# --------------------------------------------------
# 학교 검색 화면
# --------------------------------------------------

st.subheader("1. 학교 찾기")

school_input = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고, 서울고, 수도여자고등학교"
)

schools = None
search_message = None
searched_name = None

if school_input.strip():
    searched_name = school_input.strip()

    schools, status = search_schools(searched_name)

    # --------------------------------------------------
    # 원래 검색 결과가 없으면 줄임말을 풀어서 다시 검색
    # --------------------------------------------------

    if status == "empty" or not schools:
        expanded_name = expand_school_name(searched_name)

        if expanded_name and expanded_name != searched_name:
            schools, status = search_schools(expanded_name)

            if schools:
                st.info(
                    f"'{searched_name}'로 찾을 수 없어 "
                    f"'{expanded_name}'로 다시 검색했습니다."
                )

    # --------------------------------------------------
    # 네트워크/API 오류
    # --------------------------------------------------

    if status == "network":
        st.error(
            "학교 정보를 불러오지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )
        schools = []

    elif status == "json":
        st.error(
            "학교 정보 API의 응답을 읽지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )
        schools = []

    # --------------------------------------------------
    # 학교 검색 결과 없음
    # --------------------------------------------------

    elif not schools:
        st.info(
            "학교를 찾지 못했습니다. "
            "학교 이름을 다시 확인해 주세요."
        )

    # --------------------------------------------------
    # 학교 목록 표시
    # --------------------------------------------------

    if schools:
        st.success(f"학교 {len(schools)}곳을 찾았습니다.")

        school_options = []

        for school in schools:
            label = (
                f"{school['name']} "
                f"({school['region']})"
            )
            school_options.append(label)

        selected_index = st.selectbox(
            "학교를 선택하세요",
            range(len(schools)),
            format_func=lambda i: school_options[i]
        )

        selected_school = schools[selected_index]

        st.session_state["selected_school"] = selected_school


# --------------------------------------------------
# 선택한 학교 확인
# --------------------------------------------------

if "selected_school" in st.session_state:

    selected_school = st.session_state["selected_school"]

    st.divider()

    st.subheader("2. 급식 날짜 선택")

    st.write(
        f"선택한 학교: **{selected_school['name']}** "
        f"({selected_school['region']})"
    )

    selected_date = st.date_input(
        "날짜를 선택하세요",
        value=today_kst,
        max_value=today_kst,
        format="YYYY-MM-DD"
    )

    # 날짜를 YYYYMMDD 형식으로 변경
    date_string = selected_date.strftime("%Y%m%d")

    st.divider()

    st.subheader("3. 중식")

    meal, meal_status = get_meal(
        selected_school["office_code"],
        selected_school["school_code"],
        date_string
    )

    # --------------------------------------------------
    # 급식이 없는 경우
    # --------------------------------------------------

    if meal_status == "empty":
        st.info(
            f"{selected_date.strftime('%Y년 %m월 %d일')}에는 "
            "등록된 중식 급식이 없습니다."
        )

    # --------------------------------------------------
    # API 통신 오류
    # --------------------------------------------------

    elif meal_status == "network":
        st.error(
            "급식 정보를 불러오지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )

    elif meal_status == "json":
        st.error(
            "급식 정보 API의 응답을 읽지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )

    # --------------------------------------------------
    # 급식 표시
    # --------------------------------------------------

    elif meal_status == "success":

        meal_date = meal.get("MLSV_YMD", "")
        menu = meal.get("DDISH_NM", "")
        calories = meal.get("CAL_INFO", "")

        try:
            display_date = datetime.strptime(
                meal_date,
                "%Y%m%d"
            ).strftime("%Y년 %m월 %d일")
        except ValueError:
            display_date = selected_date.strftime(
                "%Y년 %m월 %d일"
            )

        st.markdown(
            f"### 🍚 {display_date} 중식"
        )

        # 메뉴
        st.markdown(
            f"""
            <div style="
                border: 1px solid #dddddd;
                border-radius: 10px;
                padding: 20px;
                background-color: #fafafa;
                font-size: 18px;
                line-height: 1.8;
            ">
                {clean_menu(menu)}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 칼로리
        if calories:
            st.markdown("")
            st.metric(
                "총 칼로리",
                calories
            )
        else:
            st.info("칼로리 정보가 등록되어 있지 않습니다.")

else:
    if not school_input.strip():
        st.info(
            "먼저 위에서 학교 이름을 입력하면 "
            "학교를 선택할 수 있습니다."
        )
