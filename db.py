"""
인마이험블 카페 재고관리 시스템 - DB 모듈
파트타이머 각자가 담당 재료를 체크하고, 사장님은 부족 재료 발주와 인기 메뉴 추정을 확인합니다.
"""
import sqlite3
from contextlib import contextmanager

DB_PATH = "cafe_inventory.db"

PART_OWNERS = {
    "공통": "공통",
    "파트1": "새난",
    "파트2": "동락",
    "파트3": "연지",
}


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS ingredients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                unit TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                min_threshold REAL NOT NULL DEFAULT 0,
                part TEXT NOT NULL DEFAULT '공통',
                owner TEXT NOT NULL DEFAULT '공통',
                package_size REAL NOT NULL DEFAULT 1,
                package_label TEXT NOT NULL DEFAULT '개'
            );

            CREATE TABLE IF NOT EXISTS menus (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                price INTEGER NOT NULL DEFAULT 0,
                part TEXT NOT NULL DEFAULT '공통'
            );

            CREATE TABLE IF NOT EXISTS recipe_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                menu_id INTEGER NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                amount_per_serving REAL NOT NULL,
                UNIQUE(menu_id, ingredient_id)
            );

            CREATE TABLE IF NOT EXISTS stock_checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ingredient_id INTEGER NOT NULL REFERENCES ingredients(id) ON DELETE CASCADE,
                quantity REAL NOT NULL,
                checked_by TEXT NOT NULL,
                checked_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );
            """
        )


def seed_if_empty():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) AS c FROM ingredients").fetchone()["c"]
        if count > 0:
            return

        # (이름, 단위, 현재수량, 부족기준, 파트, 담당자, 포장단위(1개당 용량), 포장라벨)
        ingredients = [
            ("HI BLEND", "g", 3000, 1000, "공통", "공통", 1000, "봉"),
            ("VIBE BLEND", "g", 2000, 1000, "공통", "공통", 1000, "봉"),
            ("DECAFEIN", "g", 1500, 500, "공통", "공통", 500, "봉"),
            ("우유", "ml", 4000, 1000, "공통", "공통", 1000, "팩"),
            ("아이스", "g", 8000, 2000, "공통", "공통", 2000, "봉"),
            ("휘핑크림", "ml", 1500, 500, "공통", "공통", 500, "캔"),
            ("유기농녹차", "g", 1500, 500, "파트1", "새난", 500, "봉"),
            ("베버시티", "ml", 1500, 500, "파트1", "새난", 500, "병"),
            ("초코파우더", "g", 1200, 400, "파트1", "새난", 400, "봉"),
            ("기라델리", "g", 900, 300, "파트1", "새난", 300, "봉"),
            ("다빈치", "ml", 2100, 700, "파트1", "새난", 700, "병"),
            ("초코컬에버휩", "ml", 1200, 400, "파트1", "새난", 400, "캔"),
            ("바닐라소스", "ml", 2250, 750, "파트1", "새난", 750, "병"),
            ("카라멜소스", "ml", 1500, 750, "파트1", "새난", 750, "병"),
            ("아몬드시럽", "ml", 1400, 700, "파트1", "새난", 700, "병"),
            ("마스카포네", "g", 600, 200, "파트1", "새난", 200, "통"),
            ("아이스티베이스", "ml", 3000, 1000, "파트2", "동락", 1000, "병"),
            ("찻잎", "g", 300, 100, "파트2", "동락", 100, "통"),
            ("콘플라워", "g", 900, 300, "파트2", "동락", 300, "봉"),
            ("비정제설탕", "g", 3000, 1000, "파트2", "동락", 1000, "봉"),
            ("키위시럽", "ml", 2250, 750, "파트2", "동락", 750, "병"),
            ("라임즙", "ml", 600, 200, "파트2", "동락", 200, "병"),
            ("냉동키위", "g", 3000, 1000, "파트2", "동락", 1000, "봉"),
            ("레몬즙", "ml", 600, 200, "파트2", "동락", 200, "병"),
            ("레몬제스트", "g", 150, 50, "파트2", "동락", 50, "통"),
            ("알로에청", "ml", 2400, 800, "파트3", "연지", 800, "병"),
            ("알로에젤", "g", 1800, 600, "파트3", "연지", 600, "통"),
            ("레몬청", "ml", 1600, 800, "파트3", "연지", 800, "병"),
            ("레몬", "개", 20, 5, "파트3", "연지", 1, "개"),
            ("머틀", "g", 150, 50, "파트3", "연지", 50, "통"),
            ("오렌지청", "ml", 1400, 700, "파트3", "연지", 700, "병"),
            ("히비스커스시럽", "ml", 1800, 600, "파트3", "연지", 600, "병"),
            ("탄산수", "ml", 4000, 1000, "파트3", "연지", 1000, "병"),
            ("애플시럽", "ml", 1500, 500, "파트3", "연지", 500, "병"),
            ("민트", "g", 150, 50, "파트3", "연지", 50, "팩"),
            ("로즈마리", "g", 100, 50, "파트3", "연지", 50, "팩"),
            ("티백", "개", 50, 10, "파트3", "연지", 1, "개"),
            ("밀크시럽", "ml", 1500, 500, "파트3", "연지", 500, "병"),
            ("라즈베리잼", "g", 1200, 400, "파트3", "연지", 400, "병"),
        ]
        conn.executemany(
            "INSERT INTO ingredients (name, unit, quantity, min_threshold, part, owner, package_size, package_label) VALUES (?,?,?,?,?,?,?,?)",
            ingredients,
        )

        menus = [
            ("아메리카노", 4500, "공통"),
            ("카페라떼", 5000, "공통"),
            ("바닐라라떼", 5500, "공통"),
            ("말차라떼", 6000, "파트1"),
            ("초코라떼", 6000, "파트1"),
            ("아인슈페너", 6500, "파트1"),
            ("아이스티", 5000, "파트2"),
            ("밀크티", 5500, "파트2"),
            ("키위소르베", 6500, "파트2"),
            ("레몬에이드", 5500, "파트3"),
            ("히비스커스티", 5000, "파트3"),
            ("알로에CCC", 6000, "파트3"),
        ]
        conn.executemany("INSERT INTO menus (name, price, part) VALUES (?,?,?)", menus)

        ing = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM ingredients")}
        menu = {r["name"]: r["id"] for r in conn.execute("SELECT id, name FROM menus")}

        recipe = [
            (menu["아메리카노"], ing["HI BLEND"], 18),
            (menu["카페라떼"], ing["HI BLEND"], 18),
            (menu["카페라떼"], ing["우유"], 150),
            (menu["바닐라라떼"], ing["HI BLEND"], 18),
            (menu["바닐라라떼"], ing["우유"], 150),
            (menu["바닐라라떼"], ing["바닐라소스"], 20),
            (menu["말차라떼"], ing["유기농녹차"], 15),
            (menu["말차라떼"], ing["우유"], 150),
            (menu["초코라떼"], ing["초코파우더"], 25),
            (menu["초코라떼"], ing["기라델리"], 15),
            (menu["초코라떼"], ing["우유"], 150),
            (menu["아인슈페너"], ing["HI BLEND"], 18),
            (menu["아인슈페너"], ing["마스카포네"], 20),
            (menu["아인슈페너"], ing["초코컬에버휩"], 30),
            (menu["아이스티"], ing["찻잎"], 5),
            (menu["아이스티"], ing["비정제설탕"], 15),
            (menu["아이스티"], ing["아이스"], 200),
            (menu["밀크티"], ing["찻잎"], 5),
            (menu["밀크티"], ing["콘플라워"], 10),
            (menu["밀크티"], ing["우유"], 150),
            (menu["밀크티"], ing["비정제설탕"], 15),
            (menu["키위소르베"], ing["냉동키위"], 100),
            (menu["키위소르베"], ing["키위시럽"], 20),
            (menu["키위소르베"], ing["라임즙"], 10),
            (menu["키위소르베"], ing["레몬즙"], 10),
            (menu["레몬에이드"], ing["레몬청"], 30),
            (menu["레몬에이드"], ing["탄산수"], 200),
            (menu["레몬에이드"], ing["레몬"], 0.5),
            (menu["히비스커스티"], ing["히비스커스시럽"], 20),
            (menu["히비스커스티"], ing["로즈마리"], 1),
            (menu["알로에CCC"], ing["알로에청"], 30),
            (menu["알로에CCC"], ing["알로에젤"], 20),
            (menu["알로에CCC"], ing["탄산수"], 150),
        ]
        conn.executemany(
            "INSERT INTO recipe_items (menu_id, ingredient_id, amount_per_serving) VALUES (?,?,?)",
            recipe,
        )
