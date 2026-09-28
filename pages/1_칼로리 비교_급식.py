```python
import streamlit as st
import requests
import re
from datetime import datetime
from zoneinfo import ZoneInfo


# ==================================================
# 페이지 설정
# ==================================================

st.set_page_config(
    page_title="우리 학교와 다른 학교와의 칼로리 비교",
    page_icon="🍚",
    layout="wide"
)


# ==================================================
# 제목
# ==================================================

st.title("우리 학교와 다른 학교와의 칼로리 비교")

st.write(
    "송탄고등학교와 평택지역 학교의 같은 날 중식 칼로리를 비교해 보세요."
)


# ==================================================
# NEIS 급식 API
# ==================================================

MEAL_API_URL = (
    "https://open.neis.go.kr/hub/mealServiceDietInfo"
)

OFFICE_CODE = "J10"


# ==================================================
# 평택지역 학교
# ==================================================

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
    "한국관광고등학교": "7530488",
}


# ==================================================
# 한국 시간
# ==================================================

KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# ==================================================
# API 결과 코드 확인
# ==================================================

def get_result_code(data):

    try:
        blocks = data.get(
            "mealServiceDietInfo",
            []
        )

        for block in blocks:

            if "head" not in block:
                continue

            for item in block["head"]:

                if "RESULT" in item:
                    return item["RESULT"].get("CODE")

    except Exception:
        pass

    return None


# ==================================================
# 급식 조회
# ==================================================

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
        "pIndex": "1",
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


# ==================================================
# 메뉴 정리
# ==================================================

def clean_menu(menu):

    if not menu:
        return []

    # <br>, <br/>, <br />를 줄바꿈으로 변경
    menu = re.sub(
        r"<br\s*/?>",
        "\n",
        str(menu),
        flags=re.IGNORECASE
    )

    # 메뉴별로 나누기
    items = [
        item.strip()
        for item in menu.split("\n")
        if item.strip()
    ]

    return items


# ==================================================
# 칼로리 숫자 추출
# ==================================================

def get_calorie_number(calorie_text):

    if not calorie_text:
        return None

    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        str(calorie_text)
    )

    if not match:
        return None

    try:
        return float(match.group(1))

    except ValueError:
        return None


# ==================================================
# 날짜 선택
# ==================================================

st.subheader("📅 날짜 선택")

selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=today_kst,
    max_value=today_kst,
    format="YYYY-MM-DD"
)

date_string = selected_date.strftime("%Y%m%d")

st.caption(
    f"선택한 날짜: "
    f"{selected_date.strftime('%Y년 %m월 %d일')}"
)


# ==================================================
# 송탄고등학교 급식
# ==================================================

st.divider()

st.subheader("🍚 송탄고등학교 중식")

songtan_meal, songtan_status = get_meal(
    SCHOOLS["송탄고등학교"],
    date_string
)


# ==================================================
# 급식이 없는 날
# ==================================================

if songtan_status == "empty":

    st.info("급식이 없는 날입니다.")

# ==================================================
# API 오류
# ==================================================

elif songtan_status == "network":

    st.error(
        "급식 정보를 불러오지 못했습니다. "
        "잠시 후 다시 시도해 주세요."
    )

elif songtan_status == "json":

    st.error(
        "급식 정보의 응답을 읽지 못했습니다."
    )


# ==================================================
# 송탄고 급식 표시
# ==================================================

elif songtan_status == "success":

    menu = songtan_meal.get(
        "DDISH_NM",
        ""
    )

    calorie = songtan_meal.get(
        "CAL_INFO",
        ""
    )

    origin = songtan_meal.get(
        "ORPLC_INFO",
        ""
    )

    menu_items = clean_menu(menu)


    # --------------------------------------------------
    # 메뉴 카드
    # --------------------------------------------------

    with st.container(border=True):

        st.markdown(
            f"### 🏫 송탄고등학교"
        )

        st.caption(
            f"{selected_date.strftime('%Y년 %m월 %d일')} 중식"
        )

        st.markdown("#### 🍚 메뉴")

        if menu_items:

            for item in menu_items:

                st.write(f"• {item}")

        else:

            st.write("등록된 메뉴가 없습니다.")


        st.divider()


        # --------------------------------------------------
        # 칼로리
        # --------------------------------------------------

        calorie_col, origin_col = st.columns(2)

        with calorie_col:

            st.metric(
                "🔥 총 칼로리",
                calorie if calorie else "정보 없음"
            )

        with origin_col:

            with st.expander("원산지 정보 보기"):

                if origin:

                    origin_items = clean_menu(origin)

                    for item in origin_items:
                        st.write(f"• {item}")

                else:

                    st.write(
                        "등록된 원산지 정보가 없습니다."
                    )


# ==================================================
# 평택지역 학교 급식 조회
# ==================================================

st.divider()

st.subheader("📊 평택지역 학교 칼로리 비교")


comparison = []

no_meal_schools = []


for school_name, school_code in SCHOOLS.items():

    meal, status = get_meal(
        school_code,
        date_string
    )

    if status == "empty":

        no_meal_schools.append(
            school_name
        )

        continue

    if status == "success" and meal:

        calorie_text = meal.get(
            "CAL_INFO",
            ""
        )

        calorie_number = get_calorie_number(
            calorie_text
        )

        if calorie_number is not None:

            comparison.append({
                "학교": school_name,
                "칼로리": calorie_number,
                "표시": calorie_text
            })


# ==================================================
# 비교 그래프
# ==================================================

if not comparison:

    st.info(
        "이 날짜에는 비교할 수 있는 "
        "급식 정보가 없습니다."
    )

else:

    # 칼로리 높은 순
    comparison.sort(
        key=lambda x: x["칼로리"],
        reverse=True
    )


    # --------------------------------------------------
    # 그래프
    # --------------------------------------------------

    chart_data = {
        item["학교"]: item["칼로리"]
        for item in comparison
    }

    st.bar_chart(chart_data)


    # --------------------------------------------------
    # 학교별 칼로리
    # --------------------------------------------------

    st.subheader("학교별 칼로리")

    for start in range(
        0,
        len(comparison),
        3
    ):

        current_row = comparison[
            start:start + 3
        ]

        columns = st.columns(
            len(current_row)
        )

        for column, item in zip(
            columns,
            current_row
        ):

            with column:

                if item["학교"] == "송탄고등학교":

                    title = "🏫 송탄고등학교"

                else:

                    title = item["학교"]


                with st.container(
                    border=True
                ):

                    st.markdown(
                        f"### {title}"
                    )

                    st.metric(
                        "총 칼로리",
                        f"{item['칼로리']:,.1f} kcal"
                    )


# ==================================================
# 급식이 없는 학교
# ==================================================

if no_meal_schools:

    st.divider()

    st.caption(
        "이 날짜에 급식이 없는 학교: "
        + ", ".join(no_meal_schools)
    )


# ==================================================
# 출처
# ==================================================

st.divider()

st.caption(
    "급식 정보 출처: 나이스 교육정보 개방 포털"
)
```
