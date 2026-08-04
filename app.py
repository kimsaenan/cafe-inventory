import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from db import init_db, seed_if_empty, get_conn, PART_OWNERS

st.set_page_config(page_title="인마이험블 재고관리", page_icon="☕", layout="wide")

init_db()
seed_if_empty()

st.title("☕ 인마이험블 재고관리 시스템")
st.caption("파트타이머 각자가 담당 재료를 체크하고, 사장님은 발주와 인기 메뉴를 한눈에 확인합니다.")

tab_dash, tab_check, tab_stock, tab_recipe, tab_report = st.tabs(
    ["📊 대시보드", "✅ 재고 체크 입력", "📦 재고 전체보기", "📖 레시피 관리", "🧾 발주 리포트 (사장님용)"]
)

# ---------------------------------------------------------------
# 대시보드
# ---------------------------------------------------------------
with tab_dash:
    with get_conn() as conn:
        ing_df = pd.read_sql_query("SELECT * FROM ingredients ORDER BY part, name", conn)

    ing_df["count"] = (ing_df["quantity"] / ing_df["package_size"]).round(1)
    low_stock = ing_df[ing_df["quantity"] <= ing_df["min_threshold"]]

    col1, col2 = st.columns(2)
    col1.metric("등록된 재료 수", len(ing_df))
    col2.metric("재고 부족 재료", len(low_stock))
    st.caption("담당 파트 · 🟤 공통  🟡 파트1(새난)  🟢 파트2(동락)  🔵 파트3(연지)")

    if len(low_stock) > 0:
        st.warning("⚠️ 재고가 부족한 재료가 있어요!")
        low_stock_display = low_stock.copy()
        low_stock_display["현재 재고"] = low_stock_display["count"].astype(str) + low_stock_display["package_label"]
        st.dataframe(
            low_stock_display[["name", "part", "owner", "현재 재고"]].rename(
                columns={"name": "재료명", "part": "파트", "owner": "담당자"}
            ),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✅ 모든 재료 재고가 충분해요.")

    st.subheader("파트별 재고 현황")
    for part in ["공통", "파트1", "파트2", "파트3"]:
        part_df = ing_df[ing_df["part"] == part]
        if part_df.empty:
            continue
        with st.expander(f"{part} ({PART_OWNERS.get(part, part)}) — 재료 {len(part_df)}개"):
            chart_df = part_df.set_index("name")[["count"]]
            chart_df.columns = ["재고(개수)"]
            st.bar_chart(chart_df)

# ---------------------------------------------------------------
# 재고 체크 입력 (파트타이머용)
# ---------------------------------------------------------------
with tab_check:
    st.subheader("담당 재료 재고 체크")
    st.caption("본인 파트를 선택하면 담당 재료만 보여요. 몇 개(병/봉지/통) 남았는지 세서 입력하면 자동으로 기록돼요.")

    part_choice = st.selectbox(
        "담당 파트 선택",
        ["파트1 (새난)", "파트2 (동락)", "파트3 (연지)", "공통"],
    )
    part_key = part_choice.split(" ")[0]
    checker_name = PART_OWNERS.get(part_key, "공통")

    with get_conn() as conn:
        my_ings = conn.execute(
            "SELECT id, name, unit, quantity, min_threshold, package_size, package_label FROM ingredients WHERE part = ? ORDER BY name",
            (part_key,),
        ).fetchall()

    if not my_ings:
        st.info("해당 파트에 등록된 재료가 없어요.")
    else:
        with st.form("stock_check_form"):
            st.write(f"**{checker_name}님 담당 재료 ({len(my_ings)}개)**")
            inputs = {}
            for row in my_ings:
                current_count = round(row["quantity"] / row["package_size"])
                inputs[row["id"]] = st.number_input(
                    f'{row["name"]} — {int(row["package_size"])}{row["unit"]}/{row["package_label"]}',
                    min_value=0,
                    value=int(current_count),
                    step=1,
                    key=f"check_{row['id']}",
                    help=f'{row["package_label"]} 단위로 몇 개 남았는지 입력',
                )
            submitted = st.form_submit_button("재고 체크 저장", type="primary")

        if submitted:
            with get_conn() as conn:
                for row in my_ings:
                    count = inputs[row["id"]]
                    new_qty = count * row["package_size"]
                    conn.execute(
                        "UPDATE ingredients SET quantity = ? WHERE id = ?", (new_qty, row["id"])
                    )
                    conn.execute(
                        "INSERT INTO stock_checks (ingredient_id, quantity, checked_by) VALUES (?,?,?)",
                        (row["id"], new_qty, checker_name),
                    )
            st.success(f"{checker_name}님의 재고 체크가 저장됐어요. 수고하셨습니다!")
            st.rerun()

    st.divider()
    st.subheader("최근 체크 기록")
    with get_conn() as conn:
        recent = pd.read_sql_query(
            """
            SELECT i.name AS 재료명, s.quantity AS 체크당시수량, s.checked_by AS 체크한사람, s.checked_at AS 체크시각
            FROM stock_checks s JOIN ingredients i ON i.id = s.ingredient_id
            ORDER BY s.checked_at DESC LIMIT 15
            """,
            conn,
        )
    st.dataframe(recent, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------
# 재고 전체보기 + 재료 등록/수정
# ---------------------------------------------------------------
with tab_stock:
    st.subheader("전체 재료 목록")
    with get_conn() as conn:
        ing_df = pd.read_sql_query("SELECT * FROM ingredients ORDER BY part, name", conn)

    part_filter = st.multiselect(
        "파트 필터", ["공통", "파트1", "파트2", "파트3"], default=["공통", "파트1", "파트2", "파트3"]
    )
    filtered = ing_df[ing_df["part"].isin(part_filter)].copy()
    filtered["현재 재고"] = (filtered["quantity"] / filtered["package_size"]).round(1).astype(str) + filtered["package_label"]
    filtered["1개 용량"] = filtered["package_size"].astype(int).astype(str) + filtered["unit"] + "/" + filtered["package_label"]
    st.dataframe(
        filtered.rename(columns={"name": "재료명", "part": "파트", "owner": "담당자"})[
            ["재료명", "파트", "담당자", "현재 재고", "1개 용량"]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("재료 신규 등록")
    with st.form("add_ingredient_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("재료명")
        unit = c2.text_input("단위 (g/ml/개)", value="g")
        part_sel = c3.selectbox("파트", ["공통", "파트1", "파트2", "파트3"])
        c4, c5, c6 = st.columns(3)
        package_size = c4.number_input("1개(병/봉/통)당 용량", min_value=1.0, step=1.0, value=500.0)
        package_label = c5.text_input("포장 단위 이름 (병/봉/통/개)", value="병")
        start_count = c6.number_input("현재 개수", min_value=0, step=1, value=1)
        if st.form_submit_button("등록") and name.strip():
            with get_conn() as conn:
                owner = PART_OWNERS.get(part_sel, "공통")
                conn.execute(
                    """INSERT OR IGNORE INTO ingredients
                    (name, unit, quantity, min_threshold, part, owner, package_size, package_label)
                    VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        name.strip(), unit, start_count * package_size, package_size,
                        part_sel, owner, package_size, package_label,
                    ),
                )
            st.success(f"'{name}' 재료를 등록했어요.")
            st.rerun()

# ---------------------------------------------------------------
# 레시피 관리
# ---------------------------------------------------------------
with tab_recipe:
    st.subheader("메뉴 등록")
    with st.form("add_menu_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        menu_name = c1.text_input("메뉴명")
        price = c2.number_input("가격", min_value=0, step=500)
        part_sel = c3.selectbox("파트", ["공통", "파트1", "파트2", "파트3"], key="menu_part")
        if st.form_submit_button("메뉴 등록") and menu_name.strip():
            with get_conn() as conn:
                try:
                    conn.execute(
                        "INSERT INTO menus (name, price, part) VALUES (?,?,?)",
                        (menu_name.strip(), price, part_sel),
                    )
                    st.success(f"'{menu_name}' 메뉴를 등록했어요.")
                except Exception:
                    st.error("이미 존재하는 메뉴명이에요.")
            st.rerun()

    st.divider()
    st.subheader("레시피 구성")
    with get_conn() as conn:
        menus = conn.execute("SELECT id, name, part FROM menus ORDER BY part, name").fetchall()
        ingredients = conn.execute("SELECT id, name, unit FROM ingredients ORDER BY part, name").fetchall()

    if not menus:
        st.info("먼저 메뉴를 등록해주세요.")
    else:
        menu_options = {f'{row["name"]} ({row["part"]})': row["id"] for row in menus}
        selected_menu_label = st.selectbox("메뉴 선택", menu_options.keys())
        selected_menu_id = menu_options[selected_menu_label]

        with get_conn() as conn:
            current_recipe = pd.read_sql_query(
                """
                SELECT i.name AS 재료명, r.amount_per_serving AS 소모량, i.unit AS 단위
                FROM recipe_items r JOIN ingredients i ON i.id = r.ingredient_id
                WHERE r.menu_id = ?
                """,
                conn,
                params=(selected_menu_id,),
            )
        st.write(f"**'{selected_menu_label}' 레시피 (1잔 기준)**")
        st.dataframe(current_recipe, use_container_width=True, hide_index=True)

        if ingredients:
            ing_options = {f'{row["name"]} ({row["unit"]})': row["id"] for row in ingredients}
            c1, c2, c3 = st.columns([2, 1, 1])
            chosen_ing = c1.selectbox("재료 추가", ing_options.keys())
            amount = c2.number_input("1잔당 소모량", min_value=0.0, step=1.0)
            if c3.button("레시피에 추가"):
                with get_conn() as conn:
                    conn.execute(
                        """
                        INSERT INTO recipe_items (menu_id, ingredient_id, amount_per_serving)
                        VALUES (?,?,?)
                        ON CONFLICT(menu_id, ingredient_id)
                        DO UPDATE SET amount_per_serving = excluded.amount_per_serving
                        """,
                        (selected_menu_id, ing_options[chosen_ing], amount),
                    )
                st.success("레시피를 반영했어요.")
                st.rerun()

# ---------------------------------------------------------------
# 발주 리포트 (사장님용)
# ---------------------------------------------------------------
with tab_report:
    st.subheader("🛒 지금 발주가 필요한 재료")
    with get_conn() as conn:
        ing_df = pd.read_sql_query("SELECT * FROM ingredients ORDER BY part, name", conn)
    low_stock = ing_df[ing_df["quantity"] <= ing_df["min_threshold"]].copy()
    if low_stock.empty:
        st.success("현재 발주가 급한 재료는 없어요.")
    else:
        low_stock["현재 재고"] = (low_stock["quantity"] / low_stock["package_size"]).round(1).astype(str) + low_stock["package_label"]
        low_stock["추천 발주"] = "2" + low_stock["package_label"]
        st.dataframe(
            low_stock[["name", "part", "owner", "현재 재고", "추천 발주"]].rename(
                columns={"name": "재료명", "part": "파트", "owner": "담당자"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    st.subheader("📈 재료 소모 기반 인기 메뉴 추정")
    st.caption(
        "⚠️ 판매 기록이 아니라 '재고 체크 때마다 얼마나 줄었는지'로 추정한 참고 지표예요. "
        "여러 메뉴가 같은 재료(우유 등)를 함께 쓰기 때문에 정확한 판매량은 아니고, 상대적인 경향 파악용이에요."
    )

    period = st.radio("기간", ["최근 7일", "최근 30일"], horizontal=True)
    days = 7 if period == "최근 7일" else 30
    since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    with get_conn() as conn:
        checks = pd.read_sql_query(
            "SELECT ingredient_id, quantity, checked_at FROM stock_checks WHERE checked_at >= ? ORDER BY checked_at",
            conn,
            params=(since,),
        )
        recipe_df = pd.read_sql_query(
            """
            SELECT r.menu_id, m.name AS menu_name, r.ingredient_id, r.amount_per_serving, i.name AS ing_name
            FROM recipe_items r
            JOIN menus m ON m.id = r.menu_id
            JOIN ingredients i ON i.id = r.ingredient_id
            """,
            conn,
        )

    if checks.empty:
        st.info("아직 해당 기간에 저장된 재고 체크 기록이 없어요. 재고 체크를 입력하면 여기서 소모 추이를 볼 수 있어요.")
    else:
        # 재료별 소모량 = 연속된 체크 사이 감소분의 합
        consumption = {}
        for ing_id, group in checks.groupby("ingredient_id"):
            qtys = group["quantity"].tolist()
            consumed = sum(max(0, qtys[i] - qtys[i + 1]) for i in range(len(qtys) - 1))
            consumption[ing_id] = consumed

        # 메뉴별 추정 판매잔수 = 레시피의 각 재료 소모량/소모기준 중 최솟값(병목 기준)
        est_rows = []
        for menu_id, group in recipe_df.groupby("menu_id"):
            estimates = []
            for _, r in group.iterrows():
                consumed = consumption.get(r["ingredient_id"], 0)
                if r["amount_per_serving"] > 0:
                    estimates.append(consumed / r["amount_per_serving"])
            if estimates:
                est_rows.append(
                    {"메뉴": group["menu_name"].iloc[0], "추정 판매잔수": round(min(estimates), 1)}
                )

        est_df = pd.DataFrame(est_rows).sort_values("추정 판매잔수", ascending=False)
        if est_df.empty or est_df["추정 판매잔수"].sum() == 0:
            st.info("아직 소모된 재료가 없어서 추정할 수 없어요.")
        else:
            st.bar_chart(est_df.set_index("메뉴"))
            st.dataframe(est_df, use_container_width=True, hide_index=True)
