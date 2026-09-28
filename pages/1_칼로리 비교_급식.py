
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st


# ============================================================
# 페이지 설정
# ============================================================

st.set_page_config(
    page_title="다른 학교와의 칼로리 비교",
    page_icon="🍱",
    layout="wide"
)


# ============================================================
# API 주소
# ============================================================

SCHOOL_API_URL = (
    "https://open.neis.go.kr/hub/schoolInfo"
)

MEAL_API_URL = (
    "https://open.neis.go.kr/hub/mealServiceDietInfo"
)


# ============================================================
# 고정 학교
# 송탄고등학교
# ============================================================

SONGTAN_NAME = "송탄고등학교"
SONGTAN_OFFICE_CODE = "J10"
SONGTAN_SCHOOL_CODE = "7530480"


# ============================================================
# 한국 시간
# ============================================================

KST = ZoneInfo("Asia/Seoul")

today = datetime.now(KST).date()


# ============================================================
# 제목
# ============================================================

st.title("🍱 다른 학교와의 칼로리 비교")

st.caption(
    "송탄고등학교의 중식 칼로리를 기준으로 다른 학교의 급식 칼로리를 비교합니다."
)


# ============================================================
# 학교 검색 함수
# ============================================================

@st.cache_data(ttl=3600)
def search_pyeongtaek_schools(keyword):

    params = {
        "Type": "json",
        "SCHUL_NM": keyword
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

        return [], "network"

    except ValueError:

        return [], "json"


    try:

        rows = data["schoolInfo"][1]["row"]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        return [], "empty"


    schools = []

    for row in rows:

        region = row.get(
            "LCTN_SC_NM",
            ""
        )

        # 평택 지역 학교만 사용
        if "평택" not in region:
            continue

        school = {
            "name": row.get(
                "SCHUL_NM",
                ""
            ),
            "office_code": row.get(
                "ATPT_OFCDC_SC_CODE",
                ""
            ),
            "school_code": row.get(
                "SD_SCHUL_CODE",
                ""
            ),
            "region": region
        }

        schools.append(school)


    return schools, "success"


# ============================================================
# 급식 조회 함수
# ============================================================

@st.cache_data(ttl=3600)
def get_meal(
    office_code,
    school_code,
    date_string
):

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MMEAL_SC_CODE": "2",
        "MLSV_FROM_YMD": date_string,
        "MLSV_TO_YMD": date_string,
        "pSize": "10",
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


    # --------------------------------------------------------
    # INFO-200 확인
    # --------------------------------------------------------

    try:

        head = data[
            "mealServiceDietInfo"
        ][0]["head"]

        for item in head:

            if "RESULT" in item:

                code = item[
                    "RESULT"
                ].get("CODE")

                if code == "INFO-200":

                    return None, "empty"

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        pass


    # --------------------------------------------------------
    # row 가져오기
    # --------------------------------------------------------

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


    # --------------------------------------------------------
    # 해당 날짜 찾기
    # --------------------------------------------------------

    for row in rows:

        if row.get("MLSV_YMD") == date_string:

            return row, "success"


    return None, "empty"


# ============================================================
# 메뉴를 보기 좋게 나누기
# ============================================================

def split_menu(menu):

    if not menu:

        return []


    # <br/>, <br>, <br /> 모두 처리
    menu = re.sub(
        r"<br\s*/?>",
        "\n",
        str(menu),
        flags=re.IGNORECASE
    )


    result = []

    for item in menu.splitlines():

        item = item.strip()

        if item:

            result.append(item)


    return result


# ============================================================
# 칼로리 숫자
# ============================================================

def get_calorie(calorie_text):

    if not calorie_text:

        return None


    match = re.search(
        r"[0-9]+(?:\.[0-9]+)?",
        str(calorie_text)
    )


    if not match:

        return None


    try:

        return float(
            match.group()
        )

    except ValueError:

        return None


# ============================================================
# 1. 비교할 학교 검색
# ============================================================

st.subheader("1. 비교할 학교 검색")

st.caption(
    "평택지역 학교 이름을 입력해서 비교할 학교를 선택하세요."
)


school_keyword = st.text_input(
    "학교 이름",
    placeholder="예: 평택고, 한광고, 신한고",
    key="comparison_school_search"
)


comparison_schools = []


if school_keyword.strip():

    comparison_schools, search_status = (
        search_pyeongtaek_schools(
            school_keyword.strip()
        )
    )


    if search_status == "network":

        st.error(
            "학교 정보를 불러오지 못했습니다."
        )


    elif search_status == "json":

        st.error(
            "학교 정보 API의 응답을 읽지 못했습니다."
        )


    elif not comparison_schools:

        st.info(
            "평택지역에서 해당 학교를 찾지 못했습니다."
        )


    else:

        school_options = []

        for school in comparison_schools:

            school_options.append(
                f"{school['name']} ({school['region']})"
            )


        selected_index = st.selectbox(
            "검색 결과에서 비교할 학교를 선택하세요.",
            range(len(school_options)),
            format_func=lambda i: school_options[i]
        )


        selected_school = comparison_schools[
            selected_index
        ]


        st.session_state[
            "comparison_school"
        ] = selected_school


else:

    st.info(
        "비교할 학교의 이름을 입력해 주세요."
    )


# ============================================================
# 선택된 비교 학교가 있는 경우
# ============================================================

if "comparison_school" in st.session_state:

    comparison_school = st.session_state[
        "comparison_school"
    ]


    # ========================================================
    # 2. 날짜 선택
    # ========================================================

    st.divider()

    st.subheader(
        "2. 급식 칼로리 비교"
    )


    selected_date = st.date_input(
        "날짜를 선택하세요.",
        value=today,
        max_value=today,
        format="YYYY-MM-DD"
    )


    date_string = selected_date.strftime(
        "%Y%m%d"
    )


    st.markdown(
        f"**{selected_date.strftime('%Y년 %m월 %d일')}**"
        f" · {SONGTAN_NAME} vs "
        f"{comparison_school['name']}"
    )


    # ========================================================
    # 송탄고 급식
    # ========================================================

    songtan_meal, songtan_status = get_meal(
        SONGTAN_OFFICE_CODE,
        SONGTAN_SCHOOL_CODE,
        date_string
    )


    # ========================================================
    # 비교 학교 급식
    # ========================================================

    other_meal, other_status = get_meal(
        comparison_school["office_code"],
        comparison_school["school_code"],
        date_string
    )


    # ========================================================
    # 두 학교 모두 급식이 없는 경우
    # ========================================================

    if (
        songtan_status == "empty"
        and other_status == "empty"
    ):

        st.info("급식이 없는 날입니다.")


    else:

        # ====================================================
        # 칼로리 추출
        # ====================================================

        songtan_calorie = None
        other_calorie = None


        if songtan_status == "success":

            songtan_calorie = get_calorie(
                songtan_meal.get(
                    "CAL_INFO",
                    ""
                )
            )


        if other_status == "success":

            other_calorie = get_calorie(
                other_meal.get(
                    "CAL_INFO",
                    ""
                )
            )


        # ====================================================
        # 그래프
        # ====================================================

        chart_data = {}


        if songtan_calorie is not None:

            chart_data[
                SONGTAN_NAME
            ] = songtan_calorie


        if other_calorie is not None:

            chart_data[
                comparison_school["name"]
            ] = other_calorie


        if chart_data:

            st.markdown(
                f"#### {SONGTAN_NAME} vs "
                f"{comparison_school['name']} 칼로리 비교"
            )


            st.bar_chart(
                chart_data,
                horizontal=False
            )


        # ====================================================
        # 두 학교 카드
        # ====================================================

        st.divider()

        left, right = st.columns(2)


        # ====================================================
        # 송탄고 카드
        # ====================================================

        with left:

            st.markdown(
                f"### 🏫 {SONGTAN_NAME}"
            )


            if songtan_status == "empty":

                st.info(
                    "급식이 없는 날입니다."
                )


            elif songtan_status != "success":

                st.error(
                    "급식 정보를 불러오지 못했습니다."
                )


            else:

                st.caption(
                    "중식 칼로리"
                )


                st.metric(
                    "총 칼로리",
                    songtan_meal.get(
                        "CAL_INFO",
                        "정보 없음"
                    )
                )


                with st.expander(
                    "🍚 식단 메뉴 보기",
                    expanded=True
                ):

                    menu_items = split_menu(
                        songtan_meal.get(
                            "DDISH_NM",
                            ""
                        )
                    )


                    if menu_items:

                        for item in menu_items:

                            st.write(
                                f"• {item}"
                            )

                    else:

                        st.write(
                            "등록된 메뉴가 없습니다."
                        )


        # ====================================================
        # 비교 학교 카드
        # ====================================================

        with right:

            st.markdown(
                f"### 🏫 {comparison_school['name']}"
            )


            if other_status == "empty":

                st.info(
                    "급식이 없는 날입니다."
                )


            elif other_status != "success":

                st.error(
                    "급식 정보를 불러오지 못했습니다."
                )


            else:

                st.caption(
                    "중식 칼로리"
                )


                st.metric(
                    "총 칼로리",
                    other_meal.get(
                        "CAL_INFO",
                        "정보 없음"
                    )
                )


                with st.expander(
                    "🍚 식단 메뉴 보기",
                    expanded=True
                ):

                    menu_items = split_menu(
                        other_meal.get(
                            "DDISH_NM",
                            ""
                        )
                    )


                    if menu_items:

                        for item in menu_items:

                            st.write(
                                f"• {item}"
                            )

                    else:

                        st.write(
                            "등록된 메뉴가 없습니다."
                        )


# ============================================================
# 출처
# ============================================================

st.divider()

st.caption(
    "급식 정보: 나이스 교육정보 개방 포털"
)

