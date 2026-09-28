
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
# ===========================================

