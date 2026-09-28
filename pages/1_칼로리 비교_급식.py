```python
import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ==========================================
# 페이지 설정
# ==========================================

st.set_page_config(
    page_title="우리 학교와 다른 학교와의 칼로리 비교",
    page_icon="🍚",
    layout="wide"
)


# ==========================================
# 제목
# ==========================================

st.title("우리 학교와 다른 학교와의 칼로리 비교")

st.write(
    "송탄고등학교와 평택지역 학교의 같은 날 중식 칼로리를 비교해 보세요."
)


# ==========================================
# NEIS 급식 API
# ==========================================

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

OFFICE_CODE = "J10"


# ==========================================
# 평택지역 비교 학교
# ==========================================

SCHOOLS = {
    "송탄고등학교": "7530480",
    "평택고등학교": "7530132",
    "신한고등학교": "7530179",
    "한광고등학교": "7530215",
    "평택여자고등학교": "7530578",
    "이충고등학교": "7530891",
    "태광고등학교": "7530600",
    "진위고등학교": "7530595",
    "안중고등학교": "7530594",
    "현화고등학교": "7530819",
    "효명고등학교": "7530601",
    "한국관광고등학교": "7530488"
}


# ==========================================
# 한국 시간 기준 오늘
# ==========================================

KST = ZoneInfo("Asia/Seoul")
today = datetime.now(KST).date()


# ==========================================
# 급식 API 조회 함수
# ==========================================

@st.cache_data(ttl=3600)
def get_meal(school_code, date_string):

    params = {
        "Type": "json",
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
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


    # ======================================
    # 급식 데이터 확인
    # ======================================

    try:
        result = data["mealServiceDietInfo"][0]["head"]

        for item in result:

            if "RESULT" in item:

                code = item["RESULT"].get("CODE")

                if code == "INFO-200":
                    return None, "empty"

    except (KeyError, IndexError, TypeError):
        pass


    # ======================================
    # 급식 row 가져오기
    # ======================================

    try:
        rows = data["mealServiceDietInfo"][1]["row"]

    except (KeyError, IndexError, TypeError):
        return None, "empty"


    if not rows:
        return None, "empty"


    # ======================================
    # 선택한 날짜의 중식 찾기
    # ======================================

    for row in rows:

        if row.get("MLSV_YMD") == date_string:

            return row, "success"


    return None, "empty"


# ==========================================
# 메뉴 정리
# ==========================================

def split_menu(menu):

    if not menu:
        return []

    menu = str(menu)

    # NEIS의 <br/>를 줄바꿈으로 변경
    menu = re.sub(
        r"<br\s*/?>",
        "\n",
        menu,
        flags=re.IGNORECASE
    )

    items = []

    for item in menu.split("\n"):

        item = item.strip()

        if item:
            items.append(item)

    return items


# ==========================================
# 칼로리 숫자 추출
# ==========================================

def get_calorie(calorie_text):

    if not calorie_text:
        return None

    match = re.search(
        r"[0-9]+(?:\.[0-9]+)?",
        str(calorie_text)
    )

    if match:

        try:
            return float(match.group())

        except ValueError:
            return None

    return None


# ==========================================
# 날짜 선택
# ==========================================

st.subheader("📅 날짜 선택")

selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=today,
    max_value=today,
    format="YYYY-MM-DD"
)

date_string = selected_date.strftime("%Y%m%d")

st.caption(
    "선택한 날짜: "
    + selected_date.strftime("%Y년 %m월 %d일")
)


# ==========================================
# 송탄고등학교 급식
# ==========================================

st.divider()

st.subheader("🍚 송탄고등학교 중식")

songtan_meal, songtan_status = get_meal(
    SCHOOLS["송탄고등학교"],
    date_string
)


if songtan_status == "empty":

    st.info("급식이 없는 날입니다.")


elif songtan_status == "network":

    st.error(
        "급식 정보를 불러오지 못했습니다. "
        "잠시 후 다시 시도해 주세요."
    )


elif songtan_status ==_
```
