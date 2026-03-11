import streamlit as st
from agents import function_tool, AgentHooks, Agent, Tool, RunContextWrapper
from models import UserAccountContext
import random
from datetime import datetime


# =============================================================================
# MENU AGENT TOOLS
# =============================================================================

MENU_DATA = [
    {"name": "김치찌개", "ingredients": ["김치", "돼지고기", "두부", "대파", "고춧가루"], "price": 9000, "calories": 380, "category": "찌개"},
    {"name": "된장찌개", "ingredients": ["된장", "두부", "감자", "호박", "대파", "고추"], "price": 8500, "calories": 320, "category": "찌개"},
    {"name": "불고기", "ingredients": ["소고기", "양파", "당근", "배", "간장", "참기름"], "price": 15000, "calories": 450, "category": "고기"},
    {"name": "갈비찜", "ingredients": ["소갈비", "무", "당근", "밤", "대추", "간장"], "price": 28000, "calories": 620, "category": "고기"},
    {"name": "삼겹살", "ingredients": ["돼지고기", "마늘", "상추", "쌈장"], "price": 16000, "calories": 550, "category": "고기"},
    {"name": "비빔밥", "ingredients": ["밥", "시금치", "당근", "콩나물", "고추장", "계란"], "price": 10000, "calories": 480, "category": "밥"},
    {"name": "해물파전", "ingredients": ["밀가루", "오징어", "새우", "대파", "계란"], "price": 14000, "calories": 390, "category": "전"},
    {"name": "잡채", "ingredients": ["당면", "시금치", "당근", "버섯", "소고기", "간장"], "price": 12000, "calories": 350, "category": "반찬"},
    {"name": "냉면", "ingredients": ["메밀면", "육수", "소고기", "무", "계란", "겨자"], "price": 11000, "calories": 430, "category": "면"},
    {"name": "떡볶이", "ingredients": ["떡", "어묵", "고추장", "대파", "삶은계란"], "price": 7000, "calories": 410, "category": "분식"},
    {"name": "순두부찌개", "ingredients": ["순두부", "해물", "계란", "대파", "고춧가루"], "price": 9500, "calories": 290, "category": "찌개"},
    {"name": "제육볶음", "ingredients": ["돼지고기", "고추장", "양파", "대파", "고추"], "price": 11000, "calories": 480, "category": "고기"},
]


@function_tool
def get_full_menu(context: UserAccountContext) -> str:
    """
    Retrieve the full restaurant menu with dish names, ingredients, prices, and calories.
    Use this tool when the customer asks to see the menu or wants to know what's available.
    """
    lines = ["📋 전체 메뉴판\n"]
    current_category = ""
    for item in MENU_DATA:
        if item["category"] != current_category:
            current_category = item["category"]
            lines.append(f"\n【{current_category}】")
        ingredients_str = ", ".join(item["ingredients"])
        lines.append(
            f"• {item['name']}  |  ₩{item['price']:,}  |  {item['calories']}kcal\n"
            f"  재료: {ingredients_str}"
        )
    return "\n".join(lines)


@function_tool
def search_menu_by_ingredient(context: UserAccountContext, ingredient: str) -> str:
    """
    Search menu items that contain or do NOT contain a specific ingredient.
    Useful for allergy checks or ingredient preference filtering.

    Args:
        ingredient: The ingredient to search for (e.g. "돼지고기", "계란", "밀가루")
    """
    contains = []
    safe = []
    for item in MENU_DATA:
        if ingredient in item["ingredients"]:
            contains.append(item["name"])
        else:
            safe.append(item["name"])

    return f"""
🔍 '{ingredient}' 검색 결과

⚠️ '{ingredient}' 포함 메뉴: {', '.join(contains) if contains else '없음'}
✅ '{ingredient}' 미포함 메뉴: {', '.join(safe) if safe else '없음'}
    """.strip()


@function_tool
def get_menu_detail(context: UserAccountContext, dish_name: str) -> str:
    """
    Get detailed information about a specific dish including ingredients, price, and calories.

    Args:
        dish_name: Name of the dish to look up (e.g. "김치찌개", "불고기")
    """
    for item in MENU_DATA:
        if item["name"] == dish_name:
            ingredients_str = ", ".join(item["ingredients"])
            return f"""
🍽️ {item['name']} 상세 정보

📂 카테고리: {item['category']}
💰 가격: ₩{item['price']:,}
🔥 칼로리: {item['calories']}kcal
🥘 재료: {ingredients_str}
            """.strip()

    available = ", ".join(item["name"] for item in MENU_DATA)
    return f"❌ '{dish_name}' 메뉴를 찾을 수 없습니다.\n📋 현재 메뉴: {available}"


# =============================================================================
# ORDER AGENT TOOLS
# =============================================================================

ORDER_QUEUE = [
    {"order_id": "ORD-001", "table": 3, "items": ["김치찌개 x1", "불고기 x1", "비빔밥 x2"], "status": "조리중", "wait_minutes": 15},
    {"order_id": "ORD-002", "table": 7, "items": ["삼겹살 x2", "된장찌개 x1"], "status": "조리중", "wait_minutes": 20},
    {"order_id": "ORD-003", "table": 1, "items": ["해물파전 x1", "냉면 x2"], "status": "대기중", "wait_minutes": 30},
    {"order_id": "ORD-004", "table": 5, "items": ["갈비찜 x1", "잡채 x1", "떡볶이 x1"], "status": "대기중", "wait_minutes": 35},
    {"order_id": "ORD-005", "table": 10, "items": ["순두부찌개 x2", "제육볶음 x1"], "status": "서빙완료", "wait_minutes": 0},
]

ORDER_POLICIES = {
    "취소": "주문 후 5분 이내에만 취소 가능합니다. 조리가 시작된 주문은 취소할 수 없습니다.",
    "변경": "조리 시작 전에만 메뉴 변경이 가능합니다. '대기중' 상태의 주문만 변경할 수 있습니다.",
    "알레르기": "모든 메뉴의 알레르기 정보는 메뉴판에 표시되어 있습니다. 알레르기가 있으신 경우 주문 시 반드시 말씀해 주세요. 특정 재료를 빼고 조리하는 것이 가능합니다.",
    "결제": "현금, 신용카드, 카카오페이, 네이버페이를 지원합니다. 테이블별 개별 결제(더치페이)도 가능합니다.",
    "포장": "모든 메뉴 포장 가능합니다. 포장 시 10% 할인이 적용됩니다. 포장 용기는 친환경 소재를 사용합니다.",
    "대기시간": "평균 조리 시간은 15~25분입니다. 피크 시간(12:00-13:00, 18:00-19:30)에는 최대 40분까지 소요될 수 있습니다.",
    "반찬": "기본 반찬은 무제한 리필 가능합니다. 리필을 원하시면 직원에게 말씀해 주세요.",
}


@function_tool
def get_order_queue_status(context: UserAccountContext) -> str:
    """
    Check the current order queue status including all pending, cooking, and completed orders.
    Use this tool when the customer asks about wait times or how busy the kitchen is.
    """
    cooking = [o for o in ORDER_QUEUE if o["status"] == "조리중"]
    waiting = [o for o in ORDER_QUEUE if o["status"] == "대기중"]
    completed = [o for o in ORDER_QUEUE if o["status"] == "서빙완료"]

    lines = [
        "📊 현재 주문 대기열 현황\n",
        f"🔥 조리중: {len(cooking)}건  |  ⏳ 대기중: {len(waiting)}건  |  ✅ 서빙완료: {len(completed)}건\n",
    ]

    for order in ORDER_QUEUE:
        status_icon = {"조리중": "🔥", "대기중": "⏳", "서빙완료": "✅"}[order["status"]]
        items_str = ", ".join(order["items"])
        wait_str = f"약 {order['wait_minutes']}분" if order["wait_minutes"] > 0 else "완료"
        lines.append(
            f"{status_icon} {order['order_id']} (테이블 {order['table']})\n"
            f"   메뉴: {items_str}\n"
            f"   예상 대기: {wait_str}"
        )

    avg_wait = sum(o["wait_minutes"] for o in ORDER_QUEUE if o["status"] != "서빙완료") / max(len(cooking) + len(waiting), 1)
    lines.append(f"\n📈 현재 평균 대기 시간: 약 {int(avg_wait)}분")

    return "\n".join(lines)


@function_tool
def get_order_policy(context: UserAccountContext, policy_topic: str) -> str:
    """
    Look up restaurant order policies such as cancellation, modification, payment, packaging, and allergy policies.

    Args:
        policy_topic: The policy topic to look up (취소, 변경, 알레르기, 결제, 포장, 대기시간, 반찬)
    """
    policy = ORDER_POLICIES.get(policy_topic)
    if policy:
        return f"📜 [{policy_topic}] 정책 안내\n\n{policy}"

    available_topics = ", ".join(ORDER_POLICIES.keys())
    return f"❌ '{policy_topic}' 정책을 찾을 수 없습니다.\n📋 조회 가능한 정책: {available_topics}"


# =============================================================================
# RESERVATION AGENT TOOLS
# =============================================================================

TABLES = [
    {"table_id": 1, "seats": 2, "status": "사용중", "reserved_by": "김민수", "time": "18:00-19:30"},
    {"table_id": 2, "seats": 2, "status": "예약됨", "reserved_by": "이서연", "time": "19:00-20:30"},
    {"table_id": 3, "seats": 4, "status": "사용중", "reserved_by": "박지훈", "time": "18:30-20:00"},
    {"table_id": 4, "seats": 4, "status": "빈자리", "reserved_by": None, "time": None},
    {"table_id": 5, "seats": 4, "status": "사용중", "reserved_by": "최유진", "time": "17:30-19:00"},
    {"table_id": 6, "seats": 6, "status": "빈자리", "reserved_by": None, "time": None},
    {"table_id": 7, "seats": 6, "status": "사용중", "reserved_by": "정도현", "time": "18:00-19:30"},
    {"table_id": 8, "seats": 8, "status": "예약됨", "reserved_by": "한소희", "time": "20:00-21:30"},
    {"table_id": 9, "seats": 8, "status": "빈자리", "reserved_by": None, "time": None},
    {"table_id": 10, "seats": 10, "status": "사용중", "reserved_by": "강현우", "time": "18:00-20:00"},
]


@function_tool
def get_table_status(context: UserAccountContext) -> str:
    """
    Check the current status of all tables in the restaurant including which are occupied, reserved, or available.
    Use this tool when the customer asks about table availability or current restaurant capacity.
    """
    in_use = [t for t in TABLES if t["status"] == "사용중"]
    reserved = [t for t in TABLES if t["status"] == "예약됨"]
    available = [t for t in TABLES if t["status"] == "빈자리"]

    lines = [
        "🪑 현재 테이블 현황\n",
        f"총 {len(TABLES)}테이블  |  🔴 사용중: {len(in_use)}  |  🟡 예약됨: {len(reserved)}  |  🟢 빈자리: {len(available)}\n",
    ]

    for table in TABLES:
        icon = {"사용중": "🔴", "예약됨": "🟡", "빈자리": "🟢"}[table["status"]]
        info = f"{icon} 테이블 {table['table_id']} ({table['seats']}인석) - {table['status']}"
        if table["reserved_by"]:
            info += f"  |  {table['reserved_by']}님  |  {table['time']}"
        lines.append(info)

    total_seats = sum(t["seats"] for t in available)
    lines.append(f"\n📈 현재 예약 가능: {len(available)}테이블 (총 {total_seats}석)")

    return "\n".join(lines)


@function_tool
def get_available_tables(context: UserAccountContext, party_size: int) -> str:
    """
    Find available tables that can accommodate the given party size.

    Args:
        party_size: Number of guests in the party
    """
    suitable = [t for t in TABLES if t["status"] == "빈자리" and t["seats"] >= party_size]

    if not suitable:
        almost = [t for t in TABLES if t["status"] == "예약됨" or t["status"] == "사용중"]
        ending_soon = [t for t in almost if t["time"] and t["status"] == "사용중"]
        if ending_soon:
            soonest = ending_soon[0]
            return (
                f"❌ 현재 {party_size}인 이상 빈 테이블이 없습니다.\n\n"
                f"⏳ 가장 빨리 비는 테이블: 테이블 {soonest['table_id']} ({soonest['seats']}인석)\n"
                f"   예상 종료 시간: {soonest['time'].split('-')[1]}"
            )
        return f"❌ 현재 {party_size}인 이상 예약 가능한 테이블이 없습니다. 잠시 후 다시 확인해 주세요."

    lines = [f"🟢 {party_size}인 이상 예약 가능한 테이블:\n"]
    for t in suitable:
        lines.append(f"• 테이블 {t['table_id']} - {t['seats']}인석")

    lines.append(f"\n총 {len(suitable)}개 테이블 이용 가능합니다.")
    return "\n".join(lines)


# =============================================================================
# COMPLAINT AGENT TOOLS
# =============================================================================

REFUND_POLICY = {
    "음식_품질": {
        "description": "음식 품질 문제 (이물질, 덜 익음, 맛 이상 등)",
        "refund_rate": 100,
        "note": "해당 메뉴 전액 환불 + 재조리 제공",
    },
    "서비스_불만": {
        "description": "서비스 관련 불만 (무례한 응대, 긴 대기, 주문 누락 등)",
        "refund_rate": 0,
        "note": "환불 대신 다음 방문 시 10% 할인 쿠폰 제공",
    },
    "알레르기_사고": {
        "description": "알레르기 정보 미고지 또는 잘못된 재료 사용",
        "refund_rate": 100,
        "note": "전체 주문 전액 환불 + 매니저 직접 사과 + 치료비 지원 협의 가능",
    },
    "주문_오류": {
        "description": "잘못된 메뉴 배달, 수량 오류 등",
        "refund_rate": 100,
        "note": "해당 메뉴 전액 환불 또는 올바른 메뉴로 즉시 재제공",
    },
    "위생_문제": {
        "description": "매장 청결, 식기 위생 문제",
        "refund_rate": 50,
        "note": "전체 주문 50% 환불 + 매니저 사과",
    },
    "대기_시간": {
        "description": "과도한 대기 시간 (40분 초과)",
        "refund_rate": 0,
        "note": "디저트 또는 음료 무료 제공",
    },
}

DISCOUNT_POLICY = {
    "첫_방문_불만": {
        "description": "첫 방문 고객의 불만 경험",
        "discount_rate": 20,
        "validity": "30일",
        "note": "다음 방문 시 20% 할인 쿠폰 발급",
    },
    "재방문_고객_불만": {
        "description": "단골/재방문 고객의 불만 경험",
        "discount_rate": 15,
        "validity": "60일",
        "note": "다음 방문 시 15% 할인 쿠폰 + 사이드 메뉴 1개 무료 쿠폰",
    },
    "경미한_불편": {
        "description": "사소한 불편 사항 (소음, 온도, 자리 배치 등)",
        "discount_rate": 10,
        "validity": "30일",
        "note": "다음 방문 시 10% 할인 쿠폰",
    },
    "심각한_불만": {
        "description": "반복적이거나 심각한 서비스 실패",
        "discount_rate": 30,
        "validity": "90일",
        "note": "다음 방문 시 30% 할인 쿠폰 + 매니저 콜백 예약",
    },
}


@function_tool
def lookup_refund_policy(context: UserAccountContext, complaint_type: str) -> str:
    """
    Look up the restaurant's refund policy for a specific type of complaint.
    Use this tool to determine how much refund the customer is entitled to.

    Args:
        complaint_type: Type of complaint (음식_품질, 서비스_불만, 알레르기_사고, 주문_오류, 위생_문제, 대기_시간)
    """
    policy = REFUND_POLICY.get(complaint_type)
    if policy:
        return f"""
💰 [{complaint_type}] 환불 정책

📋 유형: {policy['description']}
💵 환불률: {policy['refund_rate']}%
📝 조치: {policy['note']}
        """.strip()

    available = ", ".join(REFUND_POLICY.keys())
    return f"❌ '{complaint_type}' 유형을 찾을 수 없습니다.\n📋 조회 가능한 유형: {available}"


@function_tool
def lookup_discount_policy(context: UserAccountContext, situation: str) -> str:
    """
    Look up the restaurant's discount/compensation policy for customer complaints.
    Use this tool to determine what discount or coupon can be offered as compensation.

    Args:
        situation: Complaint situation (첫_방문_불만, 재방문_고객_불만, 경미한_불편, 심각한_불만)
    """
    policy = DISCOUNT_POLICY.get(situation)
    if policy:
        return f"""
🎫 [{situation}] 할인/보상 정책

📋 상황: {policy['description']}
💸 할인율: {policy['discount_rate']}%
⏰ 유효기간: {policy['validity']}
📝 조치: {policy['note']}
        """.strip()

    available = ", ".join(DISCOUNT_POLICY.keys())
    return f"❌ '{situation}' 상황을 찾을 수 없습니다.\n📋 조회 가능한 상황: {available}"


@function_tool
def escalate_to_manager(context: UserAccountContext, issue_summary: str, severity: str) -> str:
    """
    Escalate a serious complaint to the restaurant manager for direct handling.
    Use this for severe issues like allergy incidents, repeated complaints, or when the customer demands to speak with a manager.

    Args:
        issue_summary: Brief summary of the complaint
        severity: Severity level (보통, 심각, 긴급)
    """
    ticket_id = f"CMP-{random.randint(10000, 99999)}"
    now = datetime.now()

    callback_map = {"보통": "24시간 이내", "심각": "2시간 이내", "긴급": "30분 이내"}
    callback_time = callback_map.get(severity, "24시간 이내")

    return f"""
🚨 매니저 에스컬레이션 접수

📋 접수 번호: {ticket_id}
📅 접수 시간: {now.strftime('%Y-%m-%d %H:%M')}
⚡ 심각도: {severity}
👤 고객: {context.name}
📝 내용: {issue_summary}
📞 매니저 콜백 예정: {callback_time}
📧 확인 알림: {context.name}님께 전달 예정

⚠️ 매니저가 직접 연락드릴 예정입니다. 불편을 드려 대단히 죄송합니다.
    """.strip()


# https://openai.github.io/openai-agents-python/ref/lifecycle/#agents.lifecycle.AgentHooksBase
class AgentToolUsageLoggingHooks(AgentHooks):

    async def on_tool_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** starting tool: `{tool.name}`")

    async def on_tool_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        tool: Tool,
        result: str,
    ):
        with st.sidebar:
            st.write(f"🔧 **{agent.name}** used tool: `{tool.name}`")
            st.code(result)

    async def on_handoff(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        source: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🔄 Handoff: **{source.name}** → **{agent.name}**")

    async def on_start(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
    ):
        with st.sidebar:
            st.write(f"🚀 **{agent.name}** activated")

    async def on_end(
        self,
        context: RunContextWrapper[UserAccountContext],
        agent: Agent[UserAccountContext],
        output,
    ):
        with st.sidebar:
            st.write(f"🏁 **{agent.name}** completed")
