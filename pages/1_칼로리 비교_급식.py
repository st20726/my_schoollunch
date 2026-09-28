```python
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
    page_title="우리 학교와 다른 학교와의 칼로리 비교",
    page_icon="🍚",
    layout="wide"
)

st.title("우리 학교와 다른 학교와의 칼로리 비교")
st.write("송탄고등학교와 평택지역 학교의 같은 날 중식 칼로리를 비교해 보세요.")


# --------------------------------------------------
# NEIS API
# --------------------------------------------------

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# 경기도교육청
OFFICE_CODE = "J10"

# 송탄고등학교
SONGTAN_HIGH_CODE = "7530480"


# --------------------------------------------------
# 평택지역 비교 학교
# --------------------------------------------------
# 학교 이름과 NEIS 학교 코드를 고정해 둔다.
# 필요하면 이 목록에 학교를 추가할 수 있다.
#
# 모든 학교는 경기도교육청(J10) 소속으로 설정한다.
# --------------------------------------------------

COMPARISON_SCHOOLS = {
    "송탄고등학교": {
        "office_code": "J10",
        "school_code": "7530480"
    },

    # 비교 학교
    # 아래 학교들은 학교 코드가 바뀌지 않는 한 그대로 사용할 수 있다.
    "평택고등학교": {
        "office_code": "J10",
        "school_code": "7530540"
    },

    "한광고등학교": {
        "office_code": "J10",
        "school_code": "7530539"
    },

    "신한고등학교": {
        "office_code": "J10",
        "school_code": "7530538"
    }
}


# --------------------------------------------------
# 한국 시간
# --------------------------------------------------

KST = ZoneInfo("Asia/Seoul")
today_kst = datetime.now(KST).date()


# --------------------------------------------------
# 급식 API 결과의 RESULT 코드 확인
# --------------------------------------------------

def get_result_code(data):
    try:
        if "mealServiceDietInfo" not in data:
            return None

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
# 급식 조회
# --------------------------------------------------

@st.cache_data(ttl=3600)
def get_meal(office_code, school_code, date_string):
    """
    선택한 학교의 선택 날짜 중식만 조회한다.
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

    # 급식 데이터가 없는 경우
    result_code = get_result_code(data)

    if result_code == "INFO-200":
        return None, "empty"

    try:
        rows = data["mealServiceDietInfo"][1]["row"]
    except (KeyError, IndexError, TypeError):
        return None, "empty"

    if not rows:
        return None, "empty"

    # 선택 날짜와 일치하는 급식 찾기
    for row in rows:
        if row.get("MLSV_YMD") == date_string:
            return row, "success"

    return None, "empty"


# --------------------------------------------------
# 메뉴 HTML 정리
# --------------------------------------------------

def format_menu(menu):
    """
    NEIS의 <br/>로 구분된 메뉴를 줄바꿈해서 표시한다.
    알레르기 번호는 원래 데이터 그대로 유지한다.
    """

    if not menu:
        return "등록된 메뉴가 없습니다."

    menu = html.escape(menu)

    menu = re.sub(
        r"&lt;br\s*/?&gt;",
        "<br>",
        menu,
        flags=re.IGNORECASE
    )

    return menu


# --------------------------------------------------
# 칼로리 숫자 추출
# --------------------------------------------------

def extract_calories(cal_info):
    """
    CAL_INFO에서 숫자를 찾아 비교용 숫자로 반환한다.

    예:
    '780.45 Kcal' -> 780.45
    """

    if not cal_info:
        return None

    match = re.search(r"[\d.]+", str(cal_info))

    if match:
        try:
            return float(match.group())
        except ValueError:
            return None

    return None


# --------------------------------------------------
# 날짜 선택
# --------------------------------------------------

st.subheader("📅 날짜 선택")

selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=today_kst,
    max_value=today_kst,
    format="YYYY-MM-DD"
)

date_string = selected_date.strftime("%Y%m%d")

st.caption(
    f"선택한 날짜: {selected_date.strftime('%Y년 %m월 %d일')}"
)


# --------------------------------------------------
# 모든 학교의 급식 조회
# --------------------------------------------------

meal_results = {}

for school_name, school_info in COMPARISON_SCHOOLS.items():

    meal, status = get_meal(
        school_info["office_code"],
        school_info["school_code"],
        date_string
    )

    meal_results[school_name] = {
        "meal": meal,
        "status": status
    }


# --------------------------------------------------
# 송탄고등학교 급식 카드
# --------------------------------------------------

st.divider()

st.subheader("🍚 송탄고등학교 중식")

songtan_result = meal_results["송탄고등학교"]

if songtan_result["status"] == "empty":

    st.info("급식이 없는 날입니다")

elif songtan_result["status"] == "network":

    st.error("급식 정보를 불러오지 못했습니다.")

elif songtan_result["status"] == "json":

    st.error("급식 정보의 응답을 읽지 못했습니다.")

elif songtan_result["status"] == "success":

    meal = songtan_result["meal"]

    menu = meal.get("DDISH_NM", "")
    calories = meal.get("CAL_INFO", "")
    origin = meal.get("ORPLC_INFO", "")

    # 송탄고 카드
    st.markdown(
        f"""
        <div style="
            border: 1px solid #d9d9d9;
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 20px;
            background-color: #fafafa;
        ">

            <h2 style="margin-top: 0;">
                🏫 송탄고등학교
            </h2>

            <h4>
                🍚 중식
            </h4>

            <div style="
                font-size: 17px;
                line-height: 1.9;
                margin-bottom: 18px;
            ">
                {format_menu(menu)}
            </div>

            <hr>

            <p style="font-size: 18px;">
                🔥 <b>칼로리</b> : {html.escape(str(calories))}
            </p>

            <p style="font-size: 14px; color: #666;">
                원산지 : {html.escape(str(origin)) if origin else "정보 없음"}
            </p>

        </div>
        """,
        unsafe_allow_html=True
    )


# --------------------------------------------------
# 학교별 칼로리 비교
# --------------------------------------------------

st.divider()

st.subheader("📊 평택지역 학교와 칼로리 비교")

comparison_data = []

for school_name, result in meal_results.items():

    meal = result["meal"]

    if result["status"] == "success" and meal:

        calories_text = meal.get("CAL_INFO", "")
        calories_number = extract_calories(calories_text)

        comparison_data.append({
            "학교": school_name,
            "칼로리": calories_number,
            "칼로리_표시": calories_text
        })


# --------------------------------------------------
# 비교 가능한 학교가 없는 경우
# --------------------------------------------------

if not comparison_data:

    st.info("이 날짜에는 비교할 수 있는 학교의 급식이 없습니다.")

else:

    # 칼로리 숫자가 없는 학교 제거
    comparison_data = [
        item
        for item in comparison_data
        if item["칼로리"] is not None
    ]

    if comparison_data:

        # 가장 높은 칼로리부터 정렬
        comparison_data = sorted(
            comparison_data,
            key=lambda x: x["칼로리"],
            reverse=True
        )

        # 막대그래프
        chart_data = {
            item["학교"]: item["칼로리"]
            for item in comparison_data
        }

        st.bar_chart(chart_data)

        st.caption(
            "※ 그래프의 칼로리는 NEIS에 등록된 해당 날짜의 중식 칼로리입니다."
        )

        # 학교별 카드
        columns = st.columns(len(comparison_data))

        for column, item in zip(columns, comparison_data):

            with column:

                st.markdown(
                    f"""
                    <div style="
                        border: 1px solid #dddddd;
                        border-radius: 12px;
                        padding: 18px;
                        text-align: center;
                        min-height: 150px;
                    ">

                        <div style="
                            font-size: 17px;
                            font-weight: bold;
                            margin-bottom: 15px;
                        ">
                            {html.escape(item["학교"])}
                        </div>

                        <div style="
                            font-size: 28px;
                            font-weight: bold;
                        ">
                            {item["칼로리"]:,.1f}
                        </div>

                        <div style="
                            font-size: 14px;
                            color: #666;
                            margin-top: 5px;
                        ">
                            kcal
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )

    else:

        st.info(
            "이 날짜에는 칼로리 정보가 등록된 학교가 없습니다."
        )


# --------------------------------------------------
# 급식이 없는 비교 학교 안내
# --------------------------------------------------

no_meal_schools = []

for school_name, result in meal_results.items():

    if result["status"] == "empty":
        no_meal_schools.append(school_name)

if no_meal_schools:

    st.markdown("")

    st.info(
        "급식이 없는 학교: "
        + ", ".join(no_meal_schools)
    )


# --------------------------------------------------
# 안내
# --------------------------------------------------

st.divider()

st.caption(
    "급식 정보 출처: 나이스 교육정보 개방 포털"
)
```
