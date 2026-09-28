
import streamlit as st
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
import html
import re


# --------------------------------------------------
# 페이지 설정
# --------------------------------------------------

st.set_page_config(
    page_title="학교 급식 찾아보기",
    page_icon="🍚",
    layout="wide"
)


# --------------------------------------------------
# 제목
# --------------------------------------------------

st.title("학교 급식 찾아보기")

st.write(
    "학교 이름을 검색하고, 원하는 날짜의 중식 메뉴를 확인해 보세요."
)


# --------------------------------------------------
# 칼로리 비교 페이지 이동 버튼
# --------------------------------------------------

st.page_link(
    "pages/1_칼로리 비교_급식.py",
    label="🍚 우리 학교와 다른 학교와의 칼로리 비교",
    icon="🍚"
)


# --------------------------------------------------
# NEIS API
# --------------------------------------------------

SCHOOL_API_URL = "https://open.neis.go.kr/hub/schoolInfo"

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"


# --------------------------------------------------
# 한국 시간
# --------------------------------------------------

KST = ZoneInfo("Asia/Seoul")

today_kst = datetime.now(KST).date()


# --------------------------------------------------
# RESULT 코드 확인
# --------------------------------------------------

def get_result_code(data):

    try:

        if "schoolInfo" in data:

            for block in data["schoolInfo"]:

                if "head" in block:

                    for item in block["head"]:

                        if "RESULT" in item:
                            return item["RESULT"].get("CODE")


        if "mealServiceDietInfo" in data:

            for block in data["mealServiceDietInfo"]:

                if "head" in block:

                    for item in block["head"]:

                        if "RESULT" in item:
                            return item["RESULT"].get("CODE")

    except Exception:
        pass

    return None


# --------------------------------------------------
# 줄임말 변환
# --------------------------------------------------

def expand_school_name(name):

    name = name.strip()

    # 수도여고 → 수도여자고등학교
    if name.endswith("여고"):
        return name[:-2] + "여자고등학교"

    # 수도고 → 수도고등학교
    if name.endswith("고"):
        return name[:-1] + "고등학교"

    return None


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

@st.cache_data(ttl=3600)
def search_schools(school_name):

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
            "office_code": row.get(
                "ATPT_OFCDC_SC_CODE",
                ""
            ),
            "school_code": row.get(
                "SD_SCHUL_CODE",
                ""
            ),
            "region": row.get(
                "LCTN_SC_NM",
                ""
            )
        })


    return schools, "success"


# --------------------------------------------------
# 급식 조회
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_meal(
    office_code,
    school_code,
    date_string
):

    params = {

        "Type": "json",

        "ATPT_OFCDC_SC_CODE":
            office_code,

        "SD_SCHUL_CODE":
            school_code,

        "MMEAL_SC_CODE":
            "2",

        "MLSV_FROM_YMD":
            date_string,

        "MLSV_TO_YMD":
            date_string,

        "pSize":
            "1000",

        "pIndex":
            "1"
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

        rows = data[
            "mealServiceDietInfo"
        ][1]["row"]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        return None, "empty"


    if not rows:
        return None, "empty"


    for row in rows:

        if row.get("MLSV_YMD") == date_string:

            return row, "success"


    return None, "empty"


# --------------------------------------------------
# 메뉴 표시
# --------------------------------------------------

def clean_menu(menu):

    if not menu:
        return ""

    menu = html.escape(str(menu))

    menu = re.sub(
        r"&lt;br\s*/?&gt;",
        "<br>",
        menu,
        flags=re.IGNORECASE
    )

    return menu


# --------------------------------------------------
# 학교 검색
# --------------------------------------------------

st.subheader("1. 학교 찾기")


school_input = st.text_input(
    "학교 이름을 입력하세요",
    placeholder="예: 수도여고, 서울고, 수도여자고등학교"
)


if school_input.strip():

    search_name = school_input.strip()

    schools, status = search_schools(
        search_name
    )


    # ----------------------------------------------
    # 줄임말 검색
    # ----------------------------------------------

    if not schools:

        expanded_name = expand_school_name(
            search_name
        )

        if (
            expanded_name
            and expanded_name != search_name
        ):

            schools, status = search_schools(
                expanded_name
            )

            if schools:

                st.info(
                    f"'{search_name}'로 찾을 수 없어 "
                    f"'{expanded_name}'로 다시 검색했습니다."
                )


    # ----------------------------------------------
    # 오류
    # ----------------------------------------------

    if status == "network":

        st.error(
            "학교 정보를 불러오지 못했습니다."
        )

        schools = []


    elif status == "json":

        st.error(
            "학교 정보 API의 응답을 읽지 못했습니다."
        )

        schools = []


    # ----------------------------------------------
    # 학교 없음
    # ----------------------------------------------

    elif not schools:

        st.info(
            "학교를 찾지 못했습니다. "
            "학교 이름을 다시 확인해 주세요."
        )


    # ----------------------------------------------
    # 학교 선택
    # ----------------------------------------------

    if schools:

        st.success(
            f"학교 {len(schools)}곳을 찾았습니다."
        )


        school_options = []

        for school in schools:

            school_options.append(
                f"{school['name']} "
                f"({school['region']})"
            )


        selected_index = st.selectbox(
            "학교를 선택하세요",
            range(len(schools)),
            format_func=lambda i:
                school_options[i]
        )


        selected_school = schools[
            selected_index
        ]


        st.session_state[
            "selected_school"
        ] = selected_school


# --------------------------------------------------
# 급식 날짜
# --------------------------------------------------

if "selected_school" in st.session_state:

    selected_school = st.session_state[
        "selected_school"
    ]


    st.divider()

    st.subheader("2. 급식 날짜 선택")


    st.write(
        f"선택한 학교: "
        f"**{selected_school['name']}** "
        f"({selected_school['region']})"
    )


    selected_date = st.date_input(
        "날짜를 선택하세요",
        value=today_kst,
        max_value=today_kst,
        format="YYYY-MM-DD"
    )


    date_string = selected_date.strftime(
        "%Y%m%d"
    )


    st.divider()

    st.subheader("3. 중식")


    meal, meal_status = get_meal(

        selected_school[
            "office_code"
        ],

        selected_school[
            "school_code"
        ],

        date_string
    )


    # ----------------------------------------------
    # 급식 없음
    # ----------------------------------------------

    if meal_status == "empty":

        st.info(
            "급식이 없는 날입니다."
        )


    # ----------------------------------------------
    # API 오류
    # ----------------------------------------------

    elif meal_status == "network":

        st.error(
            "급식 정보를 불러오지 못했습니다. "
            "잠시 후 다시 시도해 주세요."
        )


    elif meal_status == "json":

        st.error(
            "급식 정보 API의 응답을 읽지 못했습니다."
        )


    # ----------------------------------------------
    # 급식 표시
    # ----------------------------------------------

    elif meal_status == "success":

        menu = meal.get(
            "DDISH_NM",
            ""
        )

        calories = meal.get(
            "CAL_INFO",
            ""
        )


        st.markdown(
            f"### 🍚 "
            f"{selected_date.strftime('%Y년 %m월 %d일')} "
            f"중식"
        )


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


        st.markdown("")


        if calories:

            st.metric(
                "총 칼로리",
                calories
            )

        else:

            st.info(
                "칼로리 정보가 등록되어 있지 않습니다."
            )

else:

    st.info(
        "먼저 학교 이름을 입력해 주세요."
    )

