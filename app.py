import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import qrcode
from io import BytesIO
from PIL import Image
import datetime
import hashlib
import time
import os
import csv

st.set_page_config(page_title="SchoolEats", page_icon="🍽️", layout="wide")

def load_css():
    st.markdown("""
    <style>
        .card { background: white; border-radius: 2rem; padding: 1.5rem; box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.05); border: 1px solid #f1f5f9; }
        .card-junior { background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%); border: 1px solid #bbf7d0; }
        .stButton > button { border-radius: 1rem !important; font-weight: 700 !important; background-color: #f97316 !important; color: white !important; border: none !important; }
        .order-number { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 1rem; text-align: center; font-size: 1.5rem; font-weight: bold; margin: 1rem 0; }
        .week-badge { background: linear-gradient(135deg, #f97316 0%, #ea580c 100%); color: white; padding: 0.5rem 1rem; border-radius: 1rem; display: inline-block; font-weight: 700; margin-bottom: 1rem; }
        .class-badge { background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; padding: 0.5rem 1rem; border-radius: 1rem; display: inline-block; font-weight: 700; margin-bottom: 1rem; }
        .info-chip { background: #f1f5f9; color: #475569; padding: 0.25rem 0.75rem; border-radius: 0.5rem; font-size: 0.75rem; display: inline-block; margin-right: 0.5rem; margin-top: 0.5rem; }
        footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

load_css()

def ensure_directories():
    if not os.path.exists('reports'):
        os.makedirs('reports')
    if not os.path.exists('data'):
        os.makedirs('data')

REPORT_DIR = "reports"
DATA_DIR = "data"
WEEKLY_REPORT_FILE = "Stolovaia ZHD1.csv"
MONTHLY_REPORT_FILE = "Stol_Zhd month1.csv"
ORDERS_FILE = "orders.csv"
MENU_FILE = "menu.csv"

def save_weekly_report(data):
    ensure_directories()
    pd.DataFrame(data).to_csv(os.path.join(REPORT_DIR, WEEKLY_REPORT_FILE), index=False, encoding='utf-8-sig')

def save_monthly_report(data):
    ensure_directories()
    pd.DataFrame(data).to_csv(os.path.join(REPORT_DIR, MONTHLY_REPORT_FILE), index=False, encoding='utf-8-sig')

def load_weekly_report():
    ensure_directories()
    fp = os.path.join(REPORT_DIR, WEEKLY_REPORT_FILE)
    cols = ['order_number','date','day','student_name','student_class','item','category','quantity','price','total_item_price','order_total','payment_method','status']
    try:
        if os.path.exists(fp):
            return pd.read_csv(fp, encoding='utf-8-sig')
    except Exception:
        pass
    return pd.DataFrame(columns=cols)

def load_monthly_report():
    ensure_directories()
    fp = os.path.join(REPORT_DIR, MONTHLY_REPORT_FILE)
    cols = ['order_number','date','day','student_name','student_class','item','category','quantity','price','total_item_price','order_total','payment_method','status']
    try:
        if os.path.exists(fp):
            return pd.read_csv(fp, encoding='utf-8-sig')
    except Exception:
        pass
    return pd.DataFrame(columns=cols)

def load_orders():
    ensure_directories()
    fp = os.path.join(REPORT_DIR, ORDERS_FILE)
    cols = ['order_number','date','day','student_name','student_class','items','total_price','payment_method','status']
    try:
        if os.path.exists(fp):
            df = pd.read_csv(fp, encoding='utf-8-sig')
            for c in cols:
                if c not in df.columns:
                    df[c] = ''
            return df
    except Exception:
        pass
    return pd.DataFrame(columns=cols)

def save_orders(odf):
    ensure_directories()
    odf.to_csv(os.path.join(REPORT_DIR, ORDERS_FILE), index=False, encoding='utf-8-sig')

def create_default_menu():
    ensure_directories()
    rows = []
    for week in [1,2,3,4]:
        for day in ['Понедельник','Вторник','Среда','Четверг','Пятница']:
            if day == 'Понедельник':
                j = [('Каша манная','Завтрак',200,210),('Борщ','Обед',250,180),('Котлета с пюре','Обед',180,320),('Компот','Напитки',200,80)]
                s = [('Борщ','Обед',450),('Котлета с пюре','Обед',550),('Компот','Напитки',150)]
            elif day == 'Вторник':
                j = [('Овсяная каша','Завтрак',200,220),('Суп куриный','Обед',250,190),('Плов','Обед',180,340),('Чай с молоком','Напитки',200,90)]
                s = [('Суп куриный','Обед',400),('Плов','Обед',600),('Чай','Напитки',100)]
            elif day == 'Среда':
                j = [('Рисовая каша','Завтрак',200,230),('Солянка','Обед',250,200),('Рыба с рисом','Обед',180,310),('Кисель','Напитки',200,100)]
                s = [('Солянка','Обед',480),('Рыба с рисом','Обед',650),('Кисель','Напитки',120)]
            elif day == 'Четверг':
                j = [('Пшённая каша','Завтрак',200,215),('Рассольник','Обед',250,185),('Гречка с мясом','Обед',180,330),('Сок','Напитки',200,110)]
                s = [('Рассольник','Обед',470),('Гречка с мясом','Обед',550),('Сок','Напитки',200)]
            else:
                j = [('Кукурузная каша','Завтрак',200,225),('Лагман','Обед',250,260),('Макароны','Обед',180,300),('Кофейный напиток','Напитки',200,95)]
                s = [('Лагман','Обед',700),('Макароны','Обед',500),('Кофе','Напитки',250)]
            for n,c,w,cal in j:
                rows.append({'week':week,'day':day,'menu_type':'junior','item_name':n,'category':c,'price':0,'weight':w,'calories':cal,'available':True})
            for n,c,p in s:
                rows.append({'week':week,'day':day,'menu_type':'senior','item_name':n,'category':c,'price':p,'weight':0,'calories':0,'available':True})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DATA_DIR, MENU_FILE), index=False, encoding='utf-8-sig')
    return df

def load_menu_from_sheet():
    ensure_directories()
    fp = os.path.join(DATA_DIR, MENU_FILE)
    try:
        if os.path.exists(fp):
            for enc in ['utf-8-sig','utf-8','cp1251','latin1']:
                try:
                    df = pd.read_csv(fp, encoding=enc)
                    if not df.empty and 'day' in df.columns:
                        if 'week' not in df.columns: df['week'] = 1
                        if 'menu_type' not in df.columns: df['menu_type'] = 'senior'
                        if 'weight' not in df.columns: df['weight'] = 0
                        if 'calories' not in df.columns: df['calories'] = 0
                        df.to_csv(fp, index=False, encoding='utf-8-sig')
                        return df
                except Exception:
                    continue
            return create_default_menu()
        return create_default_menu()
    except Exception:
        return create_default_menu()

def save_menu_to_sheet(mdf):
    ensure_directories()
    mdf.to_csv(os.path.join(DATA_DIR, MENU_FILE), index=False, encoding='utf-8-sig')

def add_new_item(week, day, mtype, name, cat, price=0, weight=0, cal=0, avail=True):
    df = load_menu_from_sheet()
    new = pd.DataFrame({'week':[week],'day':[day],'menu_type':[mtype],'item_name':[name],'category':[cat],'price':[price],'weight':[weight],'calories':[cal],'available':[avail]})
    df = pd.concat([df, new], ignore_index=True)
    save_menu_to_sheet(df)
    return True

def get_menu_by_week_day_type(week, day, mtype):
    df = load_menu_from_sheet()
    if df.empty: return pd.DataFrame()
    return df[(df['week']==week)&(df['day']==day)&(df['menu_type']==mtype)]

def is_junior_class(cls):
    try:
        s = ''.join(filter(str.isdigit, str(cls)))
        if s: return 1 <= int(s) <= 4
    except Exception:
        pass
    return False

def generate_order_number():
    return f"ORD-{datetime.datetime.now().strftime('%Y%m%d')}-{str(int(time.time()))[-4:]}"

def place_order(name, cls, items, total, pm):
    ensure_directories()
    num = generate_order_number()
    now = datetime.datetime.now()
    tr = {'Monday':'Понедельник','Tuesday':'Вторник','Wednesday':'Среда','Thursday':'Четверг','Friday':'Пятница','Saturday':'Суббота','Sunday':'Воскресенье'}
    day_ru = tr.get(now.strftime("%A"), now.strftime("%A"))
    items_str = ", ".join([f"{i['name']} x{i['quantity']}" for i in items])
    data = {'order_number':num,'date':now.strftime("%Y-%m-%d %H:%M:%S"),'day':day_ru,'student_name':name,'student_class':cls,'items':items_str,'total_price':total,'payment_method':pm,'status':'pending'}
    odf = load_orders()
    odf = pd.concat([odf, pd.DataFrame([data])], ignore_index=True)
    save_orders(odf)
    update_reports(num, now.date(), day_ru, name, cls, items, total, pm)
    return num

def update_reports(num, date, day, name, cls, items, total, pm):
    ensure_directories()
    wdf = load_weekly_report()
    mdf = load_monthly_report()
    ds = date.strftime("%Y-%m-%d")
    for item in items:
        entry = pd.DataFrame([{'order_number':num,'date':ds,'day':day,'student_name':name,'student_class':cls,'item':item['name'],'category':item.get('category',''),'quantity':item['quantity'],'price':item.get('price',0),'total_item_price':item.get('price',0)*item['quantity'],'order_total':total,'payment_method':pm,'status':'pending'}])
        wdf = pd.concat([wdf, entry], ignore_index=True)
        mdf = pd.concat([mdf, entry], ignore_index=True)
    save_weekly_report(wdf)
    save_monthly_report(mdf)

def complete_order(num):
    odf = load_orders()
    odf.loc[odf['order_number']==num,'status'] = 'completed'
    save_orders(odf)
    wdf = load_weekly_report()
    if not wdf.empty and 'order_number' in wdf.columns:
        wdf.loc[wdf['order_number']==num,'status'] = 'completed'
        save_weekly_report(wdf)
    mdf = load_monthly_report()
    if not mdf.empty and 'order_number' in mdf.columns:
        mdf.loc[mdf['order_number']==num,'status'] = 'completed'
        save_monthly_report(mdf)

def get_pending_orders():
    odf = load_orders()
    if not odf.empty and 'status' in odf.columns:
        return odf[odf['status']=='pending']
    return pd.DataFrame()

def get_completed_orders():
    odf = load_orders()
    if not odf.empty and 'status' in odf.columns:
        return odf[odf['status']=='completed']
    return pd.DataFrame()

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="black", back_color="white")

def generate_payment_qr(oid, amt):
    return generate_qr(f"PAYMENT:{oid}:{amt}:{int(time.time())}")

def generate_chef_qr():
    return generate_qr(f"CHEF_QR:{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}")

def verify_chef_password(p):
    return p == "123*"

def main():
    ensure_directories()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
            <div style="text-align:center;margin-bottom:2rem;">
                <div style="background-color:#f97316;display:inline-block;padding:0.75rem;border-radius:1.5rem;margin-bottom:1rem;">🍽️</div>
                <h1 style="font-size:2rem;font-weight:900;">Столовая школы</h1>
                <p style="color:#64748b;">Закажи обед онлайн</p>
            </div>
        """, unsafe_allow_html=True)

    if 'role' not in st.session_state: st.session_state.role = "student"
    if 'cart' not in st.session_state: st.session_state.cart = []
    if 'chef_authenticated' not in st.session_state: st.session_state.chef_authenticated = False
    if 'last_order_number' not in st.session_state: st.session_state.last_order_number = None
    if 'selected_week' not in st.session_state:
        d = datetime.datetime.now().day
        st.session_state.selected_week = 1 if d <= 7 else 2 if d <= 14 else 3 if d <= 21 else 4
    if 'student_class' not in st.session_state: st.session_state.student_class = ""

    with st.sidebar:
        st.markdown("### 🎯 Режим работы")
        role = st.radio("Роль:", ["Ученик", "Повар"], horizontal=True)
        st.session_state.role = "student" if role == "Ученик" else "chef"

        if st.session_state.role == "student":
            st.markdown("---")
            st.markdown("### 🛒 Корзина")
            if st.session_state.cart:
                total = sum(i['price']*i['quantity'] for i in st.session_state.cart)
                for i, item in enumerate(st.session_state.cart):
                    c1, c2, c3 = st.columns([2,1,1])
                    with c1: st.write(item['name'])
                    with c2:
                        if item['price'] > 0: st.write(f"{item['quantity']} x {item['price']}₸")
                        else: st.write(f"{item['quantity']} порц.")
                    with c3:
                        if st.button("❌", key=f"rm_{i}_{item['name']}"):
                            st.session_state.cart.pop(i)
                            st.rerun()
                if total > 0: st.markdown(f"**Итого: {total}₸**")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("🗑️ Очистить", use_container_width=True):
                        st.session_state.cart = []
                        st.rerun()
                with c2:
                    if st.button("✅ Оформить", use_container_width=True):
                        st.session_state.show_checkout = True
            else:
                st.info("Корзина пуста")

    if st.session_state.role == "student":
        if st.session_state.last_order_number:
            st.markdown(f'<div class="order-number">🎫 Номер заказа: <strong>{st.session_state.last_order_number}</strong></div>', unsafe_allow_html=True)

        st.markdown("### 🎓 Введите ваш класс")
        ci = st.text_input("Класс (например, 3А или 7Б):", value=st.session_state.student_class, key="ci")
        if ci != st.session_state.student_class:
            st.session_state.student_class = ci
            st.rerun()

        is_jr = is_junior_class(st.session_state.student_class) if st.session_state.student_class else False
        mtype = 'junior' if is_jr else 'senior'

        if st.session_state.student_class:
            if is_jr:
                st.markdown(f'<div class="class-badge">🍎 1-4 классы: {st.session_state.student_class}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="week-badge">🎓 5-11 классы: {st.session_state.student_class}</div>', unsafe_allow_html=True)
        else:
            st.info("👆 Укажите класс")

        st.markdown("### 📅 Выберите неделю")
        wopts = {1:"1-я неделя", 2:"2-я неделя", 3:"3-я неделя", 4:"4-я неделя"}
        wcols = st.columns(4)
        for i, (wn, wl) in enumerate(wopts.items()):
            with wcols[i]:
                lbl = f"✅ {wl}" if wn == st.session_state.selected_week else wl
                if st.button(lbl, key=f"wb_{wn}", use_container_width=True):
                    st.session_state.selected_week = wn
                    st.rerun()

        st.markdown(f'<div class="week-badge">📆 Текущая: {st.session_state.selected_week}-я неделя</div>', unsafe_allow_html=True)

        days = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница']
        sday = st.selectbox("День:", days, index=0)

        if not st.session_state.student_class:
            st.warning("⚠️ Введите класс")
        else:
            mdf = get_menu_by_week_day_type(st.session_state.selected_week, sday, mtype)
            if mdf.empty:
                st.warning(f"Меню на {sday} пока не загружено")
            else:
                cats = ['Все'] + list(mdf['category'].unique())
                scat = st.selectbox("Категория:", cats)
                fm = mdf.copy()
                if scat != 'Все':
                    fm = fm[fm['category'] == scat]

                st.markdown(f"### 🍽️ Меню на {sday}")
                if not fm.empty:
                    cols = st.columns(3)
                    for idx, (_, item) in enumerate(fm.iterrows()):
                        if item['available']:
                            with cols[idx % 3]:
                                with st.container():
                                    if is_jr:
                                        w = int(item.get('weight', 0)) if pd.notna(item.get('weight', 0)) else 0
                                        cal = int(item.get('calories', 0)) if pd.notna(item.get('calories', 0)) else 0
                                        st.markdown(f'<div class="card card-junior"><h4 style="font-weight:800;">{item["item_name"]}</h4><p style="color:#64748b;font-size:0.875rem;">{item["category"]}</p><div style="margin-top:1rem;"><span class="info-chip">⚖️ {w} г</span><span class="info-chip">🔥 {cal} ккал</span></div></div>', unsafe_allow_html=True)
                                    else:
                                        st.markdown(f'<div class="card"><h4 style="font-weight:800;">{item["item_name"]}</h4><p style="color:#64748b;font-size:0.875rem;">{item["category"]}</p><div style="margin-top:1rem;"><span style="font-size:1.25rem;font-weight:800;color:#f97316;">{int(item["price"])}₸</span></div></div>', unsafe_allow_html=True)

                                    c1, c2 = st.columns([1, 1])
                                    with c1:
                                        q = st.number_input("Кол-во", min_value=0, max_value=10, key=f"q_{st.session_state.selected_week}_{item['item_name']}_{idx}", label_visibility="collapsed")
                                    with c2:
                                        if st.button("➕ В корзину", key=f"a_{st.session_state.selected_week}_{item['item_name']}_{idx}", use_container_width=True):
                                            if q > 0:
                                                found = False
                                                for x in st.session_state.cart:
                                                    if x['name'] == item['item_name']:
                                                        x['quantity'] += q
                                                        found = True
                                                        break
                                                if not found:
                                                    st.session_state.cart.append({'name':item['item_name'],'price':int(item['price']) if not is_jr else 0,'quantity':q,'category':item['category']})
                                                st.success(f"Добавлено {q}")
                                                st.rerun()
        if st.session_state.get('show_checkout', False):
            with st.expander("Оформление", expanded=True):
                total = sum(i['price']*i['quantity'] for i in st.session_state.cart)
                sname = st.text_input("Ваше имя")
                sclass = st.text_input("Класс", value=st.session_state.student_class)

                if is_jr:
                    st.info("🍎 Для 1-4 классов питание бесплатное")
                    if st.button("Подтвердить заказ"):
                        if sname and sclass:
                            onum = place_order(sname, sclass, st.session_state.cart, 0, "free")
                            st.session_state.last_order_number = onum
                            st.success(f"✅ Номер: {onum}")
                            st.session_state.cart = []
                            st.session_state.show_checkout = False
                            time.sleep(2)
                            st.rerun()
                else:
                    pm = st.radio("Оплата:", ["Картой", "QR-код", "Наличными"])
                    if st.button("Подтвердить заказ"):
                        if sname and sclass:
                            if pm == "Картой":
                                st.markdown("### 💳 Kaspi Gold: 4400 4301 2345 6789")
                                if st.button("✅ Оплачено"):
                                    onum = place_order(sname, sclass, st.session_state.cart, total, "card")
                                    st.session_state.last_order_number = onum
                                    st.success(f"✅ Номер: {onum}")
                                    st.session_state.cart = []
                                    st.session_state.show_checkout = False
                                    time.sleep(2)
                                    st.rerun()
                            elif pm == "QR-код":
                                temp = generate_order_number()
                                qr = generate_payment_qr(temp, total)
                                buf = BytesIO()
                                qr.save(buf, format="PNG")
                                st.image(buf.getvalue(), caption="QR-код", width=250)
                                if st.button("✅ Я оплатил"):
                                    onum = place_order(sname, sclass, st.session_state.cart, total, "qr")
                                    st.session_state.last_order_number = onum
                                    st.success(f"✅ Номер: {onum}")
                                    st.session_state.cart = []
                                    st.session_state.show_checkout = False
                                    time.sleep(2)
                                    st.rerun()
                            else:
                                onum = place_order(sname, sclass, st.session_state.cart, total, "cash")
                                st.session_state.last_order_number = onum
                                st.success(f"✅ Номер: {onum}")
                                st.session_state.cart = []
                                st.session_state.show_checkout = False
                                time.sleep(2)
                                st.rerun()

    else:
        if not st.session_state.chef_authenticated:
            st.markdown("### 🔐 Доступ повара")
            pwd = st.text_input("Пароль:", type="password")
            if st.button("Войти", use_container_width=True):
                if verify_chef_password(pwd):
                    st.session_state.chef_authenticated = True
                    st.rerun()
                else:
                    st.error("Неверный пароль")
        else:
            t1, t2, t3, t4, t5 = st.tabs(["📋 Меню", "➕ Добавить", "📦 Заказы", "📊 Отчеты", "🔐 QR"])

            with t1:
                st.markdown("### 📋 Редактирование меню")
                c1, c2 = st.columns(2)
                with c1:
                    ew = st.selectbox("Неделя:", [1,2,3,4], format_func=lambda x: f"{x}-я неделя", key="ew")
                with c2:
                    et = st.selectbox("Тип:", ['junior','senior'], format_func=lambda x: "🍎 1-4" if x=='junior' else "🎓 5-11", key="et")
                mdf = load_menu_from_sheet()
                fm = mdf[(mdf['week']==ew)&(mdf['menu_type']==et)].copy()
                if not fm.empty:
                    edf = st.data_editor(fm, use_container_width=True, hide_index=True,
                        column_config={
                            "week": st.column_config.NumberColumn("Неделя", disabled=True),
                            "day": st.column_config.SelectboxColumn("День", options=['Понедельник','Вторник','Среда','Четверг','Пятница']),
                            "menu_type": st.column_config.SelectboxColumn("Тип", options=['junior','senior'], disabled=True),
                            "item_name": "Блюдо",
                            "category": st.column_config.SelectboxColumn("Категория", options=['Завтрак','Обед','Выпечка','Напитки']),
                            "price": st.column_config.NumberColumn("Цена", min_value=0),
                            "weight": st.column_config.NumberColumn("Вес (г)", min_value=0),
                            "calories": st.column_config.NumberColumn("Ккал", min_value=0),
                            "available": st.column_config.CheckboxColumn("Доступно")
                        }, key=f"ed_{ew}_{et}")
                    if st.button("💾 Сохранить", key=f"sv_{ew}_{et}"):
                        others = mdf[~((mdf['week']==ew)&(mdf['menu_type']==et))]
                        upd = pd.concat([others, edf], ignore_index=True)
                        save_menu_to_sheet(upd)
                        st.success("Обновлено!")
                        st.rerun()
                else:
                    st.info("Меню пустое")

            with t2:
                st.markdown("### ➕ Добавить блюдо")
                c1, c2 = st.columns(2)
                with c1:
                    nw = st.selectbox("Неделя", [1,2,3,4], format_func=lambda x: f"{x}-я неделя", key="nw")
                    nd = st.selectbox("День", ['Понедельник','Вторник','Среда','Четверг','Пятница'], key="nd")
                    nt = st.selectbox("Тип", ['junior','senior'], format_func=lambda x: "🍎 1-4" if x=='junior' else "🎓 5-11", key="nt")
                    nname = st.text_input("Название", key="nname")
                with c2:
                    ncat = st.selectbox("Категория", ['Завтрак','Обед','Выпечка','Напитки'], key="ncat")
                    np = st.number_input("Цена (₸)", min_value=0, step=10, key="np")
                    nwt = st.number_input("Вес (г)", min_value=0, step=10, key="nwt")
                    nc = st.number_input("Ккал", min_value=0, step=10, key="nc")
                if st.button("➕ Добавить", key="addbtn"):
                    if nname:
                        add_new_item(nw, nd, nt, nname, ncat, np, nwt, nc)
                        st.success(f"Добавлено: {nname}")
                        st.rerun()
                    else:
                        st.error("Введите название")

            with t3:
                st.markdown("### 📦 Заказы")
                po = get_pending_orders()
                if not po.empty:
                    st.info(f"Ожидают: {len(po)}")
                    for idx, (_, o) in enumerate(po.iterrows()):
                        with st.expander(f"🎫 {o.get('order_number','N/A')} - {o.get('student_name','N/A')}"):
                            st.markdown(f"**Сумма:** {o.get('total_price',0)}₸")
                            st.markdown(f"**Заказ:** {o.get('items','N/A')}")
                            if st.button("✅ Выдать", key=f"c_{idx}"):
                                complete_order(o['order_number'])
                                st.rerun()
                else:
                    st.success("🎉 Нет активных заказов")

            with t4:
                st.markdown("### 📊 Отчеты")
                rt = st.radio("Тип:", ["Недельный","Месячный"], horizontal=True)
                df = load_weekly_report() if rt == "Недельный" else load_monthly_report()
                if not df.empty and 'order_number' in df.columns:
                    cc = len(df[df['status']=='completed']['order_number'].unique()) if 'status' in df.columns else 0
                    pc = len(df[df['status']=='pending']['order_number'].unique()) if 'status' in df.columns else 0
                    tr = df['order_total'].sum() if 'order_total' in df.columns else 0
                    c1, c2, c3 = st.columns(3)
                    with c1: st.metric("✅ Выдано", cc)
                    with c2: st.metric("⏳ Ожидают", pc)
                    with c3: st.metric("💰 Выручка", f"{tr:,.0f}₸")
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    fname = WEEKLY_REPORT_FILE if rt == "Недельный" else MONTHLY_REPORT_FILE
                    st.download_button("📥 Скачать", csv_data, fname, "text/csv")
                else:
                    st.info("Нет данных")

            with t5:
                st.markdown("### 🔐 QR-код повара")
                if st.button("🔄 Сгенерировать"):
                    qr = generate_chef_qr()
                    buf = BytesIO()
                    qr.save(buf, format="PNG")
                    st.session_state.chef_qr = buf.getvalue()
                if st.session_state.get('chef_qr'):
                    st.image(st.session_state.chef_qr, caption="QR повара", width=250)
                    st.download_button("📥 Скачать QR", st.session_state.chef_qr, "chef_qr.png", "image/png")
                st.markdown("---")
                if st.button("🚪 Выйти"):
                    st.session_state.chef_authenticated = False
                    st.rerun()

if __name__ == "__main__":
    main()


