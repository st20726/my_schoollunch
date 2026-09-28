
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
# 송탄고등학교
# ============================================================

SONGTAN_NAME = "송탄고등학교"

SONGTAN_OFFICE_CODE = "J10"

SONGTAN_SCHOOL_CODE = "7530480"


# ============================================================
# 평택시 고등학교 고정 목록
# ============================================================

PYEONGTAEK_HIGH_SCHOOLS = [
    "경기물류고등학교",
    "동일공업고등학교",
    "라온고등학교",
    "비전고등학교",
    "송탄고등학교",
    "신한고등학교",
    "안중고등학교",
    "용죽고등학교",
    "은혜고등학교",
    "이충고등학교",
    "진위고등학교",
    "청담고등학교",
    "청북고등학교",
    "태광고등학교",
    "평택고등학교",
    "평택마이스터고등학교",
    "평택여자고등학교",
    "한국관광고등학교",
    "한광고등학교",
    "한광여자고등학교",
    "현화고등학교",
    "효명고등학교"
]


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
    "송탄고등학교와 평택지역 고등학교의 같은 날 중식 칼로리를 비교합니다."
)


# ============================================================
# 학교기본정보 API
# 고정된 학교 이름으로 학교 코드 찾기
# ============================================================

@st.cache_data(ttl=86400)
def find_school(school_name):

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

        return None

    except ValueError:

        return None


    try:

        rows = data["schoolInfo"][1]["row"]

    except (
        KeyError,
        IndexError,
        TypeError
    ):

        return None


    # 이름이 정확히 같은 학교를 먼저 찾기
    for row in rows:

        if row.get("SCHUL_NM") == school_name:

            return {
                "name": row.get(
                    "SCHUL_NM",
                    school_name
                ),
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
            }


    return None


# ============================================================
# 급식 API
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
    # 날짜에 해당하는 급식 찾기
    # --------------------------------------------------------

    for row in rows:

        if row.get("MLSV_YMD") == date_string:

            return row, "success"


    return None, "empty"


# ============================================================
# 메뉴 정리
# ============================================================

def split_menu(menu):

    if not menu:

        return []


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
# 칼로리 숫자 추출
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
# 비교 학교 선택
# ============================================================

st.subheader("1. 비교할 학교")

comparison_options = [
    school
    for school in PYEONGTAEK_HIGH_SCHOOLS
    if school != SONGTAN_NAME
]


selected_school_name = st.selectbox(
    "비교할 평택지역 고등학교를 선택하세요.",
    comparison_options,
    index=(
        comparison_options.index("평택고등학교")
        if "평택고등학교" in comparison_options
        else 0
    )
)


# ============================================================
# 선택한 학교의 정보 가져오기
# ============================================================

comparison_school = find_school(
    selected_school_name
)


if comparison_school is None:

    st.error(
        "선택한 학교의 정보를 불러오지 못했습니다."
    )

    st.stop()


# ============================================================
# 날짜 선택
# ============================================================

st.divider()

st.subheader("2. 급식 날짜")

selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=today,
    max_value=today,
    format="YYYY-MM-DD"
)


date_string = selected_date.strftime(
    "%Y%m%d"
)


st.caption(
    selected_date.strftime(
        "%Y년 %m월 %d일"
    )
    + " 중식"
)


# ============================================================
# 급식 조회
# ============================================================

songtan_meal, songtan_status = get_meal(
    SONGTAN_OFFICE_CODE,
    SONGTAN_SCHOOL_CODE,
    date_string
)


other_meal, other_status = get_meal(
    comparison_school["office_code"],
    comparison_school["school_code"],
    date_string
)


# ============================================================
# 두 학교 모두 급식 없음
# ============================================================

if (
    songtan_status == "empty"
    and other_status == "empty"
):

    st.divider()

    st.info("급식이 없는 날입니다.")

    st.stop()


# ============================================================
# 오류 처리
# ============================================================

if songtan_status == "network":

    st.error(
        "송탄고등학교 급식 정보를 불러오지 못했습니다."
    )

    st.stop()


if other_status == "network":

    st.error(
        f"{selected_school_name} 급식 정보를 불러오지 못했습니다."
    )

    st.stop()


# ============================================================
# 칼로리 계산
# ============================================================

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


# ============================================================
# 비교 제목
# ============================================================

st.divider()

st.subheader(
    f"3. 급식 칼로리 비교 "
    f"({selected_date.strftime('%Y년 %m월 %d일')})"
)


# ============================================================
# 막대그래프
# ============================================================

chart_data = {}


if songtan_calorie is not None:

    chart_data[
        SONGTAN_NAME
    ] = songtan_calorie


if other_calorie is not None:

    chart_data[
        selected_school_name
    ] = other_calorie


if chart_data:

    st.markdown(
        f"**{SONGTAN_NAME} vs {selected_school_name}**"
    )

    st.bar_chart(
        chart_data
    )

else:

    st.info(
        "이 날짜에는 비교할 수 있는 칼로리 정보가 없습니다."
    )


# ============================================================
# 메뉴 카드
# ============================================================

st.divider()

st.subheader("4. 두 학교의 중식 메뉴")


left, right = st.columns(2)


# ============================================================
# 송탄고 카드
# ============================================================

with left:

    st.markdown(
        f"### 🏫 {SONGTAN_NAME}"
    )


    if songtan_status == "empty":

        st.info(
            "급식이 없는 날입니다."
        )

    elif songtan_status == "success":

        if songtan_calorie is not None:

            st.metric(
                "중식 칼로리",
                f"{songtan_calorie:,.1f} Kcal"
            )

        else:

            st.metric(
                "중식 칼로리",
                "정보 없음"
            )


        st.markdown(
            "#### 🍚 식단 메뉴"
        )


        menu_items = split_menu(
            songtan_meal.get(
                "DDISH_NM",
                ""
            )
        )


        if menu_items:

            for item in menu_items:

                st.write(
                    "• " + item
                )

        else:

            st.write(
                "등록된 메뉴가 없습니다."
            )


        with st.expander(
            "알레르기·원산지 정보 보기"
        ):

            st.write(
                "메뉴에 표시된 괄호 안 숫자는 "
                "알레르기 유발 식재료 번호입니다."
            )


            origin = songtan_meal.get(
                "ORPLC_INFO",
                ""
            )


            if origin:

                st.markdown(
                    "**원산지**"
                )

                origin_items = split_menu(
                    origin
                )

                for item in origin_items:

                    st.write(
                        "• " + item
                    )

            else:

                st.write(
                    "등록된 원산지 정보가 없습니다."
                )


# ============================================================
# 비교 학교 카드
# ============================================================

with right:

    st.markdown(
        f"### 🏫 {selected_school_name}"
    )


    if other_status == "empty":

        st.info(
            "급식이 없는 날입니다."
        )

    elif other_status == "success":

        if other_calorie is not None:

            st.metric(
                "중식 칼로리",
                f"{other_calorie:,.1f} Kcal"
            )

        else:

            st.metric(
                "중식 칼로리",
                "정보 없음"
            )


        st.markdown(
            "#### 🍚 식단 메뉴"
        )


        menu_items = split_menu(
            other_meal.get(
                "DDISH_NM",
                ""
            )
        )


        if menu_items:

            for item in menu_items:

                st.write(
                    "• " + item
                )

        else:

            st.write(
                "등록된 메뉴가 없습니다."
            )


        with st.expander(
            "알레르기·원산지 정보 보기"
        ):

            st.write(
                "메뉴에 표시된 괄호 안 숫자는 "
                "알레르기 유발 식재료 번호입니다."
            )


            origin = other_meal.get(
                "ORPLC_INFO",
                ""
            )


            if origin:

                st.markdown(
                    "**원산지**"
                )

                origin_items = split_menu(
                    origin
                )

                for item in origin_items:

                    st.write(
                        "• " + item
                    )

            else:

                st.write(
                    "등록된 원산지 정보가 없습니다."
                )


# ============================================================
# 출처
# ============================================================

st.divider()

st.caption(
    "급식 정보 출처: 나이스 교육정보 개방 포털"
)

