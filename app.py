"""
«Жас Дарын» мектебінің асханасы — бір файлдық нұсқа
"""

import streamlit as st
import pandas as pd
import requests
import base64
import os
from datetime import datetime
from io import StringIO

# ============================================================
# КОНФИГ
# ============================================================
st.set_page_config(page_title="Жас Дарын асханасы", page_icon="🍽️", layout="wide")

st.markdown("""
<style>
.main-header{font-size:2.5rem;font-weight:bold;color:#FF6B35;text-align:center;margin-bottom:1rem;}
.menu-card{background:#f9f9f9;border-radius:10px;padding:15px;border-left:5px solid #FF6B35;margin-bottom:10px;min-height:150px;}
.price-tag{color:#FF6B35;font-weight:bold;font-size:1.2rem;}
.category-tag{background:#FFE5D9;color:#FF6B35;padding:3px 10px;border-radius:15px;font-size:.85rem;display:inline-block;margin-bottom:8px;}
.week-badge{background:#FF6B35;color:#fff;padding:5px 15px;border-radius:20px;font-weight:bold;}
</style>
""", unsafe_allow_html=True)

WEEKS = ["1-я неделя", "2-я неделя", "3-я неделя", "4-я неделя"]
DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница"]
CATS = ["Завтрак", "Обед", "Салаты", "Первое", "Второе", "Напитки"]

# ============================================================
# GITHUB КОНФИГ
# ============================================================
GH_OWNER, GH_REPO, GH_BRANCH = "aidarpavl", "Stolovaia27", "main"
MENU_PATH = "menu.csv"
DAILY_PATH = "Stolovaia ZHD1.csv"
MONTHLY_PATH = "Stol_Zhd month1.csv"
GH_TOKEN = None
GH_OK = False
CHEF_PWD = "povar2026"

try:
    if hasattr(st, "secrets") and len(st.secrets) > 0:
        if "github" in st.secrets:
            g = st.secrets["github"]
            GH_TOKEN = g.get("token")
            GH_OWNER = g.get("owner", GH_OWNER)
            GH_REPO = g.get("repo", GH_REPO)
            GH_BRANCH = g.get("branch", GH_BRANCH)
            MENU_PATH = g.get("menu_path", MENU_PATH)
            DAILY_PATH = g.get("daily_report_path", DAILY_PATH)
            MONTHLY_PATH = g.get("monthly_report_path", MONTHLY_PATH)
        if "auth" in st.secrets:
            CHEF_PWD = st.secrets["auth"].get("chef_password", CHEF_PWD)
    if GH_TOKEN and isinstance(GH_TOKEN, str):
        GH_TOKEN = GH_TOKEN.strip()
        if GH_TOKEN.startswith(("ghp_", "github_pat_", "gho_", "ghs_")):
            GH_OK = True
        else:
            GH_TOKEN = None
except Exception:
    GH_TOKEN, GH_OK = None, False


def gh_raw(path):
    return f"https://raw.githubusercontent.com/{GH_OWNER}/{GH_REPO}/{GH_BRANCH}/{path}"


def gh_api(path):
    return f"https://api.github.com/repos/{GH_OWNER}/{GH_REPO}/contents/{path}"


REQUIRED = ["week", "day", "item_name", "category", "price", "available"]

# ============================================================
# FALLBACK
# ============================================================
FALLBACK = pd.DataFrame([
    {"week": w, "day": d, "item_name": n, "category": c, "price": p, "available": True}
    for w, d, n, c, p in [
        ("1-я неделя", "Понедельник", "Каша овсяная с ягодами", "Завтрак", 450),
        ("1-я неделя", "Понедельник", "Бутерброд с сыром", "Завтрак", 350),
        ("1-я неделя", "Понедельник", "Борщ со сметаной", "Обед", 550),
        ("1-я неделя", "Понедельник", "Котлета с пюре", "Обед", 650),
        ("1-я неделя", "Понедельник", "Компот из сухофруктов", "Напитки", 150),
        ("1-я неделя", "Вторник", "Салат овощной", "Салаты", 400),
        ("1-я неделя", "Вторник", "Солянка мясная", "Первое", 500),
        ("1-я неделя", "Вторник", "Макароны с сыром", "Второе", 550),
        ("1-я неделя", "Среда", "Винегрет", "Салаты", 450),
        ("1-я неделя", "Среда", "Суп грибной", "Первое", 480),
        ("1-я неделя", "Среда", "Рыба с рисом", "Второе", 700),
        ("1-я неделя", "Четверг", "Морковный салат", "Салаты", 350),
        ("1-я неделя", "Четверг", "Рассольник", "Первое", 470),
        ("1-я неделя", "Четверг", "Гречка с мясом", "Второе", 600),
        ("1-я неделя", "Пятница", "Салат Греческий", "Салаты", 580),
        ("1-я неделя", "Пятница", "Лагман", "Второе", 750),
        ("1-я неделя", "Пятница", "Сок апельсиновый", "Напитки", 250),
    ]
])


# ============================================================
# МӘЗІР
# ============================================================
def normalize(df):
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    if "week" not in df.columns:
        df["week"] = "1-я неделя"
    for c in REQUIRED:
        if c not in df.columns:
            raise ValueError(f"Баған жоқ: {c}")
    df = df[REQUIRED].dropna(how="all")
    df = df[df["item_name"].notna() & (df["item_name"].astype(str).str.strip() != "")]
    df["week"] = df["week"].astype(str).str.strip()
    df["day"] = df["day"].astype(str).str.strip()
    df["item_name"] = df["item_name"].astype(str).str.strip()
    df["category"] = df["category"].astype(str).str.strip()
    df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0).astype(int)
    df["available"] = df["available"].astype(str).str.upper().isin(["TRUE", "1", "YES"])
    return df.reset_index(drop=True)


@st.cache_data(ttl=300, show_spinner=False)
def load_menu():
    try:
        r = requests.get(gh_raw(MENU_PATH), timeout=10)
        if r.status_code == 200 and r.text.strip():
            return normalize(pd.read_csv(StringIO(r.text)))
    except Exception:
        pass
    try:
        if os.path.exists("menu.csv"):
            return normalize(pd.read_csv("menu.csv"))
    except Exception:
        pass
    return normalize(FALLBACK)


def save_csv_gh(df, path, msg):
    if not GH_OK:
        return False
    h = {"Authorization": f"token {GH_TOKEN}",
         "Accept": "application/vnd.github.v3+json"}
    url = gh_api(path)
    try:
        r = requests.get(url, headers=h, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None
        if r.status_code == 401:
            st.error("❌ Токен жарамсыз!")
            return False
        content = base64.b64encode(df.to_csv(index=False).encode()).decode()
        payload = {"message": msg, "content": content, "branch": GH_BRANCH}
        if sha:
            payload["sha"] = sha
        p = requests.put(url, headers=h, json=payload, timeout=15)
        if p.status_code in (200, 201):
            return True
        st.error(f"❌ Сақтау: {p.status_code}")
        return False
    except Exception as e:
        st.error(f"❌ GitHub: {e}")
        return False


def save_menu(df):
    return save_csv_gh(df, MENU_PATH, f"Мәзір ({datetime.now():%Y-%m-%d %H:%M})")


# ============================================================
# ТАПСЫРЫСТАР
# ============================================================
ORDER_COLS = ["timestamp", "class", "week", "day", "item_name",
              "category", "price", "quantity", "total"]


def load_orders():
    try:
        if os.path.exists("Orders.csv"):
            df = pd.read_csv("Orders.csv")
            for c in ORDER_COLS:
                if c not in df.columns:
                    df[c] = None
            return df[ORDER_COLS]
    except Exception:
        pass
    return pd.DataFrame(columns=ORDER_COLS)


def save_order(row):
    df = load_orders()
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv("Orders.csv", index=False)


# ============================================================
# ЕСЕПТЕР
# ============================================================
def daily_report(date_str):
    df = load_orders()
    if df.empty:
        return pd.DataFrame()
    df["d"] = df["timestamp"].astype(str).str[:10]
    d = df[df["d"] == date_str].copy()
    if d.empty:
        return pd.DataFrame()
    r = d.groupby(["item_name", "category"]).agg(
        {"quantity": "sum", "total": "sum"}).reset_index()
    r.columns = ["Тағам", "Санат", "Саны", "Жалпы сома (₸)"]
    r["Есеп күні"] = date_str
    r["Есеп уақыты"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return r


def monthly_report(year, month):
    df = load_orders()
    if df.empty:
        return pd.DataFrame()
    df["d"] = pd.to_datetime(df["timestamp"].astype(str).str[:10], errors="coerce")
    m = df[(df["d"].dt.year == year) & (df["d"].dt.month == month)].copy()
    if m.empty:
        return pd.DataFrame()
    r = m.groupby(["item_name", "category"]).agg(
        {"quantity": "sum", "total": "sum"}).reset_index()
    r.columns = ["Тағам", "Санат", "Саны", "Жалпы сома (₸)"]
    r["Ай"] = f"{year}-{month:02d}"
    r["Есеп уақыты"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return r


def append_report(report_df, path, key_col):
    if report_df.empty:
        return False
    val = report_df[key_col].iloc[0]
    existing = pd.DataFrame()
    try:
        r = requests.get(gh_raw(path), timeout=10)
        if r.status_code == 200 and r.text.strip():
            existing = pd.read_csv(StringIO(r.text))
    except Exception:
        pass
    if not existing.empty and key_col in existing.columns:
        existing = existing[existing[key_col].astype(str) != str(val)]
    final = pd.concat([existing, report_df], ignore_index=True)
    return save_csv_gh(final, path, f"Есеп {val}")


# ============================================================
# СЕССИЯ
# ============================================================
for k, v in {"cart": [], "role": "Ученик", "week": "1-я неделя",
             "day": "Понедельник", "class": "", "last_order": None,
             "chef_ok": False, "show_full": False}.items():
    if k not in st.session_state:
        st.session_state[k] = v

menu_df = load_menu()

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ Режим")
    role = st.radio("Роль:", ["Ученик", "Повар"],
                    index=0 if st.session_state.role == "Ученик" else 1)
    st.session_state.role = role

    st.markdown("---")
    if GH_OK:
        st.success("🔗 GitHub ✅")
    else:
        st.warning("📴 GitHub: тек оқу")

    if role == "Повар":
        st.markdown("---")
        st.markdown("### 🔐 Кіру")
        if not st.session_state.chef_ok:
            pwd = st.text_input("Пароль:", type="password", key="pwd")
            if st.button("🔓 Кіру", use_container_width=True, type="primary"):
                if pwd == CHEF_PWD:
                    st.session_state.chef_ok = True
                    st.rerun()
                else:
                    st.error("❌ Пароль дұрыс емес!")
        else:
            st.success("✅ Кірдіңіз")
            if st.button("🚪 Шығу", use_container_width=True):
                st.session_state.chef_ok = False
                st.rerun()

    st.markdown("---")

    if role == "Ученик":
        st.markdown("### 🛒 Корзина")
        if not st.session_state.cart:
            st.info("Бос")
        else:
            total = 0
            for i, it in enumerate(st.session_state.cart):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.write(f"**{it['item_name']}**")
                    st.caption(f"{it['category']} · {it['price']}₸ × {it['quantity']}")
                with c2:
                    if st.button("❌", key=f"rm{i}"):
                        st.session_state.cart.pop(i)
                        st.rerun()
                total += it["price"] * it["quantity"]
            st.markdown(f"### 💰 {total}₸")
            if st.button("🗑️ Тазалау", use_container_width=True):
                st.session_state.cart = []
                st.rerun()
            if st.button("✅ Тапсырыс беру", type="primary", use_container_width=True):
                if not st.session_state["class"]:
                    st.error("⚠️ Класс енгізіңіз!")
                else:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    for it in st.session_state.cart:
                        save_order({"timestamp": ts, "class": st.session_state["class"],
                                    "week": st.session_state.week, "day": st.session_state.day,
                                    "item_name": it["item_name"], "category": it["category"],
                                    "price": it["price"], "quantity": it["quantity"],
                                    "total": it["price"] * it["quantity"]})
                    st.session_state.last_order = {
                        "timestamp": ts, "items": st.session_state.cart.copy(),
                        "total": total}
                    st.session_state.cart = []
                    st.success("✅ Тапсырыс қабылданды!")
                    st.balloons()
                    st.rerun()

# ============================================================
# ОҚУШЫ
# ============================================================
if st.session_state.role == "Ученик":
    st.markdown('<div class="main-header">🍽️ Столовая школы Жас Дарын</div>',
                unsafe_allow_html=True)
    st.markdown("---")

    st.markdown("### 🎓 Класс")
    c1, c2 = st.columns([1, 3])
    with c1:
        cls = st.text_input("Класс:", value=st.session_state["class"] or "8")
    with c2:
        st.markdown("<br>", unsafe_allow_html=True)
        if cls:
            n = int("".join(filter(str.isdigit, cls)) or 0)
            grp = ("1-4" if n <= 4 else "5-8" if n <= 8 else "9-11")
            st.success(f"🎓 {grp}: {cls}")
    st.session_state["class"] = cls
    st.markdown("---")

    st.markdown("### 📅 Апта")
    wc = st.columns(4)
    for i, w in enumerate(WEEKS):
        with wc[i]:
            if st.button(w, key=f"w{i}", use_container_width=True,
                         type="primary" if st.session_state.week == w else "secondary"):
                st.session_state.week = w
                st.rerun()

    st.markdown("### 📆 Күн:")
    idx = DAYS.index(st.session_state.day) if st.session_state.day in DAYS else 0
    sd = st.selectbox("Күн:", DAYS, index=idx, label_visibility="collapsed")
    st.session_state.day = sd

    cats = ["Все"] + sorted(menu_df["category"].unique().tolist())
    st.markdown("### 🏷️ Санат:")
    sc = st.selectbox("Санат:", cats, label_visibility="collapsed")

    st.markdown("---")
    st.markdown(f"### 🍽️ {sd} <span class='week-badge'>{st.session_state.week}</span>",
                unsafe_allow_html=True)

    dm = menu_df[(menu_df["week"] == st.session_state.week) &
                 (menu_df["day"] == sd)].copy()
    if sc != "Все":
        dm = dm[dm["category"] == sc]

    if dm.empty:
        st.warning("⚠️ Бұл күнге тағамдар жоқ.")
    else:
        cols = st.columns(3)
        for i, (rid, row) in enumerate(dm.iterrows()):
            with cols[i % 3]:
                st.markdown(
                    '<div class="menu-card">'
                    f'<h4>{row["item_name"]}</h4>'
                    f'<span class="category-tag">{row["category"]}</span>'
                    f'<p class="price-tag">💰 {row["price"]}₸</p></div>',
                    unsafe_allow_html=True)
                q = st.number_input("Саны", 1, 10, 1, key=f"q{rid}")
                if st.button("🛒 Себетке", key=f"a{rid}",
                             use_container_width=True, type="primary"):
                    found = False
                    for it in st.session_state.cart:
                        if it["item_name"] == row["item_name"]:
                            it["quantity"] += q
                            found = True
                            break
                    if not found:
                        st.session_state.cart.append({
                            "item_name": row["item_name"],
                            "category": row["category"],
                            "price": int(row["price"]),
                            "quantity": q})
                    st.success(f"✅ {row['item_name']}")
                    st.rerun()

    if st.session_state.last_order:
        st.markdown("---")
        st.success(f"✅ Соңғы: {st.session_state.last_order['timestamp']}")
        with st.expander("📋 Мәлімет"):
            for it in st.session_state.last_order["items"]:
                st.write(f"• {it['item_name']} — {it['price']}₸ × {it['quantity']}")
            st.write(f"**Жалпы: {st.session_state.last_order['total']}₸**")

# ============================================================
# АСХАНАШЫ
# ============================================================
else:
    st.markdown('<div class="main-header">👨‍🍳 Панель повара</div>',
                unsafe_allow_html=True)

    if not st.session_state.chef_ok:
        st.warning("🔐 Парольді сол жақтан енгізіңіз.")
        st.stop()

    t1, t2, t3, t4, t5 = st.tabs(["📋 Меню", "➕ Қосу", "📦 Заказы",
                                  "📊 Күндік", "📈 Айлық"])

    # --- МӘЗІР ---
    with t1:
        st.markdown("### 📋 Мәзір (4 апта)")
        c1, c2 = st.columns(2)
        with c1:
            ew = st.selectbox("Апта:", WEEKS, index=WEEKS.index(st.session_state.week))
        with c2:
            ed = st.selectbox("Күн:", ["Все дни"] + DAYS)

        if ed == "Все дни":
            fd = menu_df[menu_df["week"] == ew].copy()
        else:
            fd = menu_df[(menu_df["week"] == ew) & (menu_df["day"] == ed)].copy()

        st.caption(f"💡 {ew} / {ed} — {len(fd)} тағам")

        edited = st.data_editor(
            fd, use_container_width=True, num_rows="dynamic",
            column_config={
                "week": st.column_config.SelectboxColumn("Апта", options=WEEKS, required=True),
                "day": st.column_config.SelectboxColumn("Күн", options=DAYS, required=True),
                "item_name": st.column_config.TextColumn("Блюдо", required=True),
                "category": st.column_config.SelectboxColumn("Санат", options=CATS, required=True),
                "price": st.column_config.NumberColumn("Баға ₸", min_value=0, format="%d₸"),
                "available": st.column_config.CheckboxColumn("Бар"),
            }, key="menu_ed")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💾 GitHub-қа сақтау", use_container_width=True, type="primary"):
                if ed == "Все дни":
                    keep = menu_df[menu_df["week"] != ew].copy()
                else:
                    keep = menu_df[~((menu_df["week"] == ew) & (menu_df["day"] == ed))].copy()
                final = pd.concat([keep, edited], ignore_index=True)
                with st.spinner("Жіберілуде..."):
                    if save_menu(final):
                        st.cache_data.clear()
                        st.success("✅ Сақталды!")
                        st.rerun()
        with c2:
            if st.button("🔄 Жаңарту", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with c3:
            if st.button("📋 Барлық", use_container_width=True):
                st.session_state.show_full = not st.session_state.show_full

        if st.session_state.show_full:
            st.dataframe(menu_df, use_container_width=True, height=400)

    # --- ҚОСУ ---
    with t2:
        st.markdown("### ➕ Жаңа тағам")
        with st.form("add"):
            c1, c2 = st.columns(2)
            with c1:
                nw = st.selectbox("Апта:", WEEKS, key="aw")
                nd = st.selectbox("Күн:", DAYS, key="ad")
                nn = st.text_input("Атауы:", key="an")
                nc = st.selectbox("Санат:", CATS, key="ac")
            with c2:
                nprice = st.number_input("Баға ₸:", min_value=0, value=500, step=50, key="ap")
                na = st.checkbox("Бар", value=True, key="aa")
            if st.form_submit_button("➕ Қосу", use_container_width=True, type="primary"):
                if not nn:
                    st.error("⚠️ Атауын енгізіңіз!")
                else:
                    new = pd.DataFrame([{"week": nw, "day": nd, "item_name": nn,
                                          "category": nc, "price": nprice, "available": na}])
                    upd = pd.concat([menu_df, new], ignore_index=True)
                    with st.spinner("Жіберілуде..."):
                        if save_menu(upd):
                            st.cache_data.clear()
                            st.success("✅ Қосылды!")
                            st.rerun()

    # --- ЗАКАЗЫ ---
    with t3:
        st.markdown("### 📦 Заказы")
        odf = load_orders()
        if odf.empty:
            st.info("📭 Жоқ")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("Саны", len(odf))
            c2.metric("Сома", f"{odf['total'].fillna(0).sum():,}₸")
            c3.metric("Сыныптар", odf["class"].nunique())
            st.dataframe(odf, use_container_width=True, height=400)
            st.download_button("📥 CSV", odf.to_csv(index=False).encode(),
                               "orders.csv", "text/csv", use_container_width=True)

    # --- КҮНДІК ---
    with t4:
        st.markdown("### 📊 Күндік есеп")
        st.caption("→ `Stolovaia ZHD1.csv`")
        c1, c2 = st.columns([2, 1])
        with c1:
            d = st.date_input("Күн:")
        with c2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📊 Жасау", use_container_width=True, type="primary"):
                ds = d.strftime("%Y-%m-%d")
                r = daily_report(ds)
                if r.empty:
                    st.warning("⚠️ Деректер жоқ.")
                else:
                    st.session_state.daily_r = r
                    st.success(f"✅ {len(r)} жазба")

        if "daily_r" in st.session_state and not st.session_state.daily_r.empty:
            st.dataframe(st.session_state.daily_r, use_container_width=True)
           if st.button("💾 Күндік есепті сақтау", key="save_daily",
             use_container_width=True, type="primary"):
    with st.spinner("Жіберілуде..."):
        if append_report(st.session_state.daily_r, DAILY_PATH, "Есеп күні"):
            st.success("✅ Сақталды!")
    # --- АЙЛЫҚ ---
    with t5:
        st.markdown("### 📈 Айлық есеп")
        st.caption("→ `Stol_Zhd month1.csv`")
        today = datetime.now()
        c1, c2, c3 = st.columns(3)
        with c1:
            y = st.number_input("Жыл:", 2024, 2030, today.year)
        with c2:
            m = st.number_input("Ай:", 1, 12, today.month)
        with c3:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("📈 Жасау", use_container_width=True, type="primary"):
                r = monthly_report(int(y), int(m))
                if r.empty:
                    st.warning("⚠️ Деректер жоқ.")
                else:
                    st.session_state.month_r = r
                    st.success(f"✅ {len(r)} жазба")

        if "month_r" in st.session_state and not st.session_state.month_r.empty:
            st.dataframe(st.session_state.month_r, use_container_width=True)
            if st.button("💾 Айлық есепті сақтау", key="save_monthly",
             use_container_width=True, type="primary"):
    with st.spinner("Жіберілуде..."):
        if append_report(st.session_state.month_r, MONTHLY_PATH, "Ай"):
            st.success("✅ Сақталды!")
# ============================================================
st.markdown("---")
st.markdown("<p style='text-align:center;color:gray;font-size:.85rem;'>"
            "🍽️ Жас Дарын · GitHub + Streamlit · 2026</p>",
            unsafe_allow_html=True)