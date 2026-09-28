```python
import streamlit as st
import requests
import re
import html
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

st.title("우리 학교와 다른 학교와의 칼로리 비교")
st.write("송탄고등학교와 평택지역 고등학교의 중식 칼로리를 비교해 봅니다.")


# ==================================================
# NEIS API
# ==================================================

MEAL_API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# 경기도교육청
OFFICE_CODE = "J10"


# ==================================================
# 평택지역 고등학교
#
# 학교 코드:
# 송탄고등학교      7530480
# 평택고등학교      7530132
# 신한고등학교      7530179
# 한광고등학교      7530215
# 평택여자고등학교 7530578
# 이충고등학교      7530891
# 태광고등학교      7530600
# 진위고등학교      7530595
# 안중고등학교      7530594
# 현화고등학교      7530819
# 효명고등학교      7530601
# 한국관광고등학교 7530488
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
TODAY = datetime.now(KST).date()


# ==================================================
# 급식 API에서 RESULT 코드 확인
# ==================================================

def get_result_code(data):

    try:
        blocks = data.get("mealServiceDietInfo", [])

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

        # 하루만 조회하므로 충분한 크기
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

    # ----------------------------------------------
    # 급식 데이터 없음
    # ----------------------------------------------

    result_code = get_result_code(data)

    if result_code == "INFO-200":
        return None, "empty"

    # ----------------------------------------------
    # row 가져오기
    # ----------------------------------------------

    try:

        rows = data["mealServiceDietInfo"][1]["row"]

    except (KeyError, IndexError, TypeError):

        return None, "empty"

    if not rows:
        return None, "empty"

    # ----------------------------------------------
    # 선택한 날짜의 중식 찾기
    # ----------------------------------------------

    for row in rows:

        if (
            row.get("MLSV_YMD") == date_string
            and row.get("MMEAL_SC_CODE") == "2"
        ):

            return row, "success"

    return None, "empty"


# ==================================================
# 칼로리 숫자만 추출
# ==================================================

def get_calorie_number(cal_info):

    if not cal_info:
        return None

    # 예: "812.4 Kcal"
    match = re.search(
        r"([0-9]+(?:\.[0-9]+)?)",
        str(cal_info)
    )

    if match:

        try:
            return float(match.group(1))

        except ValueError:
            return None

    return None


# ==================================================
# 메뉴 표시
# ==================================================

def make_menu_html(menu):

    if not menu:
        return "등록된 메뉴가 없습니다."

    # HTML 특수문자 처리
    safe_menu = html.escape(str(menu))

    # NEIS의 <br/>를 줄바꿈으로 변경
    safe_menu = re.sub(
        r"&lt;br\s*/?&gt;",
        "<br>",
        safe_menu,
        flags=re.IGNORECASE
    )

    return safe_menu


# ==================================================
# 날짜 선택
# ==================================================

st.subheader("📅 날짜 선택")

selected_date = st.date_input(
    "비교할 날짜를 선택하세요.",
    value=TODAY,
    max_value=TODAY,
    format="YYYY-MM-DD"
)

date_string = selected_date.strftime("%Y%m%d")

st.caption(
    f"선택한 날짜: {selected_date.strftime('%Y년 %m월 %d일')}"
)


# ==================================================
# 송탄고등학교 급식
# ==================================================

st.divider()

st.subheader("🍚 송탄고등학교")

songtan_meal, songtan_status = get_meal(
    SCHOOLS["송탄고등학교"],
    date_string
)


# ==================================================
# 송탄고 급식이 없는 경우
# ==================================================

if songtan_status == "empty":

    st.info("급식이 없는 날입니다")


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
# 송탄고 급식 카드
# ==================================================

elif songtan_status == "success":

    menu = songtan_meal.get("DDISH_NM", "")
    calorie = songtan_meal.get("CAL_INFO", "")
    origin = songtan_meal.get("ORPLC_INFO", "")

    st.markdown(
        f"""
        <div style="
            border: 1px solid #dddddd;
            border-radius: 16px;
            padding: 25px;
            margin-top: 10px;
            margin-bottom: 20px;
            background-color: #ffffff;
        ">

            <h2 style="margin-top: 0;">
                🏫 송탄고등학교
            </h2>

            <p style="
                color: #666666;
                margin-bottom: 20px;
            ">
                {selected_date.strftime('%Y년 %m월 %d일')} 중식
            </p>

            <h3>🍚 메뉴</h3>

            <div style="
                font-size: 18px;
                line-height: 2;
                padding: 15px;
                background-color: #f7f7f7;
                border-radius: 10px;
            ">
                {make_menu_html(menu)}
            </div>

            <br>

            <h3>🔥 칼로리</h3>

            <div style="
                font-size: 28px;
                font-weight: bold;
            ">
                {html.escape(str(calorie))}
            </div>

            <br>

            <details>
                <summary>원산지 보기</summary>

                <div style="
                    margin-top: 10px;
                    line-height: 1.8;
                    color: #555555;
                ">
                    {make_menu_html(origin)}
                </div>

            </details>

        </div>
        """,
        unsafe_allow_html=True
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

    # ----------------------------------------------
    # 급식이 없는 학교
    # ----------------------------------------------

    if status == "empty":

        no_meal_schools.append(school_name)

        continue

    # ----------------------------------------------
    # 정상적인 급식
    # ----------------------------------------------

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
                "칼로리표시": calorie_text
            })


# ==================================================
# 비교 결과가 없는 경우
# ==================================================

if not comparison:

    st.info("이 날짜에는 비교할 수 있는 급식 정보가 없습니다.")


else:

    # ==================================================
    # 칼로리 순으로 정렬
    # ==================================================

    comparison.sort(
        key=lambda x: x["칼로리"],
        reverse=True
    )


    # ==================================================
    # 막대그래프
    # ==================================================

    chart_data = {
        item["학교"]: item["칼로리"]
        for item in comparison
    }

    st.bar_chart(chart_data)


    # ==================================================
    # 학교별 칼로리 카드
    # ==================================================

    st.subheader("학교별 칼로리")

    # 한 줄에 최대 3개
    for start in range(
        0,
        len(comparison),
        3
    ):

        row = comparison[
            start:start + 3
        ]

        columns = st.columns(
            len(row)
        )

        for column, item in zip(
            columns,
            row
        ):

            with column:

                is_songtan = (
                    item["학교"] == "송탄고등학교"
                )

                border = (
                    "#4CAF50"
                    if is_songtan
                    else "#dddddd"
                )

                background = (
                    "#f0fff0"
                    if is_songtan
                    else "#ffffff"
                )

                st.markdown(
                    f"""
                    <div style="
                        border: 2px solid {border};
                        border-radius: 14px;
                        padding: 20px;
                        margin-bottom: 15px;
                        background-color: {background};
                        text-align: center;
                    ">

                        <div style="
                            font-size: 18px;
                            font-weight: bold;
                            margin-bottom: 15px;
                        ">
                            {html.escape(item["학교"])}
                        </div>

                        <div style="
                            font-size: 30px;
                            font-weight: bold;
                        ">
                            {item["칼로리"]:,.1f}
                        </div>

                        <div style="
                            color: #777777;
                            margin-top: 5px;
                        ">
                            kcal
                        </div>

                    </div>
                    """,
                    unsafe_allow_html=True
                )


# ==================================================
# 급식이 없는 학교 안내
# ==================================================

if no_meal_schools:

    st.divider()

    st.caption(
        "이 날짜에 급식이 없는 학교: "
        + ", ".join(no_meal_schools)
    )


# ==================================================
# 안내
# ==================================================

st.divider()

st.caption(
    "급식 정보 출처: 나이스 교육정보 개방 포털"
)
```
