import re
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st


st.set_page_config(
    page_title="우리 학교와 다른 학교와의 칼로리 비교",
    page_icon="🍚",
    layout="wide",
)


st.title("우리 학교와 다른 학교와의 칼로리 비교")

st.write(
    "송탄고등학교와 평택지역 학교의 같은 날 중식 칼로리를 비교해 보세요."
)


MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

OFFICE_CODE = "J10"


SCHOOLS = {
    "송탄고등학교": "7530480",
    "평택고등학교": "7530132",
    "신한고등학교": "7530179",
    "한광고등학교": "7530215",
    "평택여자고등학교": "7530578",
}


KST = ZoneInfo("Asia/Seoul")
today = datetime.now(KST).date()


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


    try:

        head = data[
            "mealServiceDietInfo"
        ][0]["head"]

        for item in head:

            if "RESULT" in item:

                code = item["RESULT"].get("CODE")

                if code == "INFO-200":
                    return None, "empty"

    except (
        KeyError,
        IndexError,
        TypeError
    ):
        pass


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


    for row in rows:

        if row.get("MLSV_YMD") == date_string:

            return row, "success"


    return None, "empty"


def split_menu(text):

    if not text:
        return []

    text = re.sub(
        r"<br\s*/?>",
        "\n",
        str(text),
        flags=re.IGNORECASE
    )

    return [
        item.strip()
        for item in text.splitlines()
        if item.strip()
    ]


def get_calorie(text):

    if not text:
        return None

    match = re.search(
        r"[0-9]+(?:\.[0-9]+)?",
        str(text)
    )

    if not match:
        return None

    return float(match.group())


st.subheader("📅 날짜 선택")


selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=today,
    max_value=today,
    format="YYYY-MM-DD"
)


date_string = selected_date.strftime("%Y%m%d")


st.caption(
    f"선택한 날짜: "
    f"{selected_date.strftime('%Y년 %m월 %d일')}"
)


st.divider()

st.subheader("🍚 송탄고등학교 중식")


songtan_meal, songtan_status = get_meal(
    SCHOOLS["송탄고등학교"],
    date_string
)


if songtan_status == "empty":

    st.info("급식이 없는 날입니다")


elif songtan_status == "network":

    st.error(
        "급식 정보를 불러오지 못했습니다. "
        "잠시 후 다시 시도해 주세요."
    )


elif songtan_status == "json":

    st.error(
        "급식 정보 API의 응답을 읽지 못했습니다."
    )


elif songtan_status == "success":

    menu_items = split_menu(
        songtan_meal.get(
            "DDISH_NM",
            ""
        )
    )

    calorie = songtan_meal.get(
        "CAL_INFO",
        "정보 없음"
    )

    origin_items = split_menu(
        songtan_meal.get(
            "ORPLC_INFO",
            ""
        )
    )


    st.markdown(
        f"### 🏫 송탄고등학교 — "
        f"{selected_date.strftime('%Y년 %m월 %d일')} 중식"
    )


    with st.container(border=True):

        st.markdown("#### 🍚 메뉴")


        if menu_items:

            for item in menu_items:

                st.write(
                    f"• {item}"
                )

        else:

            st.write(
                "등록된 메뉴가 없습니다."
            )


        st.divider()


        col1, col2 = st.columns(2)


        with col1:

            st.metric(
                "🔥 총 칼로리",
                str(calorie)
            )


        with col2:

            st.markdown("**🌾 원산지**")


            if origin_items:

                for item in origin_items:

                    st.write(
                        f"• {item}"
                    )

            else:

                st.write(
                    "등록된 정보가 없습니다."
                )


st.divider()

st.subheader("📊 평택지역 학교 칼로리 비교")


comparison = []

no_meal = []


for school_name, school_code in SCHOOLS.items():

    meal, status = get_meal(
        school_code,
        date_string
    )


    if status == "empty":

        no_meal.append(
            school_name
        )

        continue


    if status != "success":

        continue


    calorie = get_calorie(
        meal.get(
            "CAL_INFO",
            ""
        )
    )


    if calorie is not None:

        comparison.append(
            {
                "학교": school_name,
                "칼로리": calorie
            }
        )


if not comparison:

    st.info(
        "이 날짜에는 비교할 수 있는 "
        "급식 정보가 없습니다."
    )


else:

    comparison.sort(
        key=lambda item: item["칼로리"],
        reverse=True
    )


    chart_data = {
        item["학교"]: item["칼로리"]
        for item in comparison
    }


    st.bar_chart(chart_data)


    st.markdown(
        "### 🏫 학교별 칼로리"
    )


    for item in comparison:

        col1, col2 = st.columns(
            [2, 1]
        )


        with col1:

            st.write(
                item["학교"]
            )


        with col2:

            st.write(
                f"**{item['칼로리']:,.1f} kcal**"
            )


if no_meal:

    st.caption(
        "이 날짜에 급식이 없는 학교: "
        + ", ".join(no_meal)
    )


st.divider()


st.caption(
    "급식 정보 출처: 나이스 교육정보 개방 포털"
)
