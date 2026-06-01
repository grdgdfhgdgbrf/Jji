import requests
import json
import sqlite3
import random
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ТОКЕН БОТА (ЗАМЕНИТЕ НА СВОЙ)
BOT_TOKEN = "8071372461:AAE8RBJ8DwRfKf3ddTHz8zRjAL8YwB8B-bM"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# URL для API запросов
def tg_api(method: str, data: dict = None):
    url = f"{API_URL}/{method}"
    if data:
        response = requests.post(url, json=data)
    else:
        response = requests.get(url)
    return response.json()

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_file="bot_database.db"):
        self.db_file = db_file
        self.init_db()
    
    def get_connection(self):
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Пользователи
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                total_spent REAL DEFAULT 0,
                total_opened INTEGER DEFAULT 0,
                last_bonus_time INTEGER DEFAULT 0,
                joined_date INTEGER DEFAULT 0
            )
        ''')
        
        # Кейсы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                price REAL,
                photo_url TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # Предметы в кейсах
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS case_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER,
                item_name TEXT,
                item_value REAL,
                chance REAL
            )
        ''')
        
        # Инвентарь пользователя
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_inventory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item_name TEXT,
                item_value REAL,
                received_date INTEGER,
                is_sold INTEGER DEFAULT 0
            )
        ''')
        
        # Настройки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Обязательные подписки
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS required_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT,
                channel_name TEXT
            )
        ''')
        
        # Администраторы
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY
            )
        ''')
        
        # Временные данные пользователей для состояний
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT,
                data TEXT
            )
        ''')
        
        # Добавляем настройки по умолчанию
        default_settings = {
            'currency_symbol': '⭐',
            'casino_min_bet': '10',
            'casino_max_bet': '1000',
            'support_contact': '@support_username',
            'payment_card': '',
            'payment_phone': ''
        }
        
        for key, value in default_settings.items():
            cursor.execute('INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)', (key, value))
        
        conn.commit()
        conn.close()
    
    def execute(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        last_id = cursor.lastrowid
        conn.close()
        return last_id
    
    def fetchone(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchone()
        conn.close()
        return result
    
    def fetchall(self, query, params=()):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        result = cursor.fetchall()
        conn.close()
        return result

db = Database()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_balance(user_id: int) -> float:
    result = db.fetchone("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    return result[0] if result else 0

def update_balance(user_id: int, amount: float):
    db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

def add_to_inventory(user_id: int, item_name: str, item_value: float):
    db.execute(
        "INSERT INTO user_inventory (user_id, item_name, item_value, received_date) VALUES (?, ?, ?, ?)",
        (user_id, item_name, item_value, int(datetime.now().timestamp()))
    )

def get_currency() -> str:
    result = db.fetchone("SELECT value FROM settings WHERE key = 'currency_symbol'")
    return result[0] if result else "⭐"

def get_setting(key: str) -> str:
    result = db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
    return result[0] if result else ""

def set_setting(key: str, value: str):
    db.execute("UPDATE settings SET value = ? WHERE key = ?", (value, key))

def is_admin(user_id: int) -> bool:
    result = db.fetchone("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    return result is not None

def get_user_state(user_id: int) -> Tuple[str, dict]:
    result = db.fetchone("SELECT state, data FROM user_states WHERE user_id = ?", (user_id,))
    if result:
        return result[0], json.loads(result[1]) if result[1] else {}
    return None, {}

def set_user_state(user_id: int, state: str, data: dict = None):
    if state is None:
        db.execute("DELETE FROM user_states WHERE user_id = ?", (user_id,))
    else:
        db.execute(
            "INSERT OR REPLACE INTO user_states (user_id, state, data) VALUES (?, ?, ?)",
            (user_id, state, json.dumps(data or {}))
        )

def send_message(chat_id: int, text: str, reply_markup: dict = None, parse_mode: str = None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    if parse_mode:
        data["parse_mode"] = parse_mode
    
    response = tg_api("sendMessage", data)
    return response

def edit_message(chat_id: int, message_id: int, text: str, reply_markup: dict = None):
    data = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text
    }
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    response = tg_api("editMessageText", data)
    return response

def answer_callback(callback_id: str, text: str = None, show_alert: bool = False):
    data = {
        "callback_query_id": callback_id
    }
    if text:
        data["text"] = text
        data["show_alert"] = show_alert
    
    tg_api("answerCallbackQuery", data)

# ========== КЛАВИАТУРЫ ==========
def main_keyboard(user_id: int) -> dict:
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🎁 Кейсы", "callback_data": "show_cases"},
                {"text": "💰 Баланс", "callback_data": "show_balance"}
            ],
            [
                {"text": "📦 Инвентарь", "callback_data": "show_inventory"},
                {"text": "🏪 Магазин", "callback_data": "show_shop"}
            ],
            [
                {"text": "🎰 Казино", "callback_data": "show_casino"},
                {"text": "🔄 Скупка", "callback_data": "show_resell"}
            ],
            [
                {"text": "🎁 Бонус кейс", "callback_data": "bonus_case"},
                {"text": "🆘 Поддержка", "callback_data": "support"}
            ]
        ]
    }
    
    if is_admin(user_id):
        keyboard["inline_keyboard"].append([{"text": "⚙️ Админ панель", "callback_data": "admin_panel"}])
    
    return keyboard

def admin_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📦 Управление кейсами", "callback_data": "admin_cases"}],
            [{"text": "📢 Рассылка", "callback_data": "admin_broadcast"}],
            [{"text": "💳 Настройка оплаты", "callback_data": "admin_payment"}],
            [{"text": "💰 Управление балансом", "callback_data": "admin_balance"}],
            [{"text": "⭐ Настройка валюты", "callback_data": "admin_currency"}],
            [{"text": "📢 Обязательные подписки", "callback_data": "admin_channels"}],
            [{"text": "👑 Управление админами", "callback_data": "admin_admins"}],
            [{"text": "📊 Статистика", "callback_data": "admin_stats"}],
            [{"text": "🔙 Назад", "callback_data": "back_to_main"}]
        ]
    }

def cases_keyboard() -> dict:
    cases = db.fetchall("SELECT id, name, price FROM cases WHERE is_active = 1")
    keyboard = {"inline_keyboard": []}
    
    for case_id, name, price in cases:
        keyboard["inline_keyboard"].append([
            {"text": f"📦 {name} - {price}{get_currency()}", "callback_data": f"open_case_{case_id}"}
        ])
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back_to_main"}])
    return keyboard

def admin_cases_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "➕ Создать кейс", "callback_data": "create_case"}],
            [{"text": "📋 Список кейсов", "callback_data": "list_cases"}],
            [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
        ]
    }

def back_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "🔙 Назад", "callback_data": "back_to_main"}]
        ]
    }

def shop_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "💎 Пополнить баланс", "callback_data": "deposit"}],
            [{"text": "🔙 Назад", "callback_data": "back_to_main"}]
        ]
    }

def resell_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "💰 Продать все предметы", "callback_data": "sell_all_items"}],
            [{"text": "🔙 Назад", "callback_data": "back_to_main"}]
        ]
    }

def get_subscription_keyboard() -> dict:
    channels = db.fetchall("SELECT channel_id, channel_name FROM required_channels")
    keyboard = {"inline_keyboard": []}
    
    for channel_id, channel_name in channels:
        keyboard["inline_keyboard"].append([
            {"text": f"📢 {channel_name}", "url": f"https://t.me/{channel_id.replace('@', '')}"}
        ])
    
    keyboard["inline_keyboard"].append([{"text": "✅ Проверить подписку", "callback_data": "check_subscription"}])
    return keyboard

def inventory_keyboard(user_id: int, page: int = 0) -> dict:
    items = db.fetchall("SELECT id, item_name, item_value FROM user_inventory WHERE user_id = ? AND is_sold = 0", (user_id,))
    keyboard = {"inline_keyboard": []}
    
    start = page * 5
    end = start + 5
    
    for item_id, item_name, item_value in items[start:end]:
        keyboard["inline_keyboard"].append([
            {"text": f"📦 {item_name} - {item_value}{get_currency()}", "callback_data": f"sell_item_{item_id}"}
        ])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append({"text": "◀️ Назад", "callback_data": f"inv_page_{page-1}"})
    if end < len(items):
        nav_buttons.append({"text": "Вперед ▶️", "callback_data": f"inv_page_{page+1}"})
    
    if nav_buttons:
        keyboard["inline_keyboard"].append(nav_buttons)
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Назад", "callback_data": "back_to_main"}])
    return keyboard

# ========== ПРОВЕРКА ПОДПИСОК ==========
def check_subscriptions(user_id: int) -> bool:
    channels = db.fetchall("SELECT channel_id FROM required_channels")
    if not channels:
        return True
    
    for channel in channels:
        channel_id = channel[0]
        try:
            response = tg_api("getChatMember", {"chat_id": channel_id, "user_id": user_id})
            if response.get("ok") and response["result"]["status"] in ["left", "kicked"]:
                return False
        except:
            return False
    return True

# ========== КЕЙСЫ ==========
def open_case(user_id: int, case_id: int) -> Optional[Dict]:
    items = db.fetchall("SELECT item_name, item_value, chance FROM case_items WHERE case_id = ?", (case_id,))
    if not items:
        return None
    
    total_chance = sum(item[2] for item in items)
    rand = random.uniform(0, total_chance)
    cumulative = 0
    
    for item_name, item_value, chance in items:
        cumulative += chance
        if rand <= cumulative:
            add_to_inventory(user_id, item_name, item_value)
            return {"name": item_name, "value": item_value}
    return None

# ========== КАЗИНО ==========
def casino_game(user_id: int, bet: float) -> tuple:
    if bet <= 0:
        return (False, "Ставка должна быть больше 0!")
    
    balance = get_user_balance(user_id)
    if balance < bet:
        return (False, "Недостаточно средств!")
    
    update_balance(user_id, -bet)
    
    secret_number = random.randint(1, 10)
    user_number = random.randint(1, 10)
    
    if user_number == secret_number:
        win_amount = bet * 2
        update_balance(user_id, win_amount)
        return (True, f"🎉 Поздравляю! Выпало число {secret_number}, вы выиграли {win_amount}{get_currency()}!")
    else:
        return (False, f"😢 К сожалению, выпало число {secret_number}, а не {user_number}. Вы проиграли {bet}{get_currency()}.")

# ========== ОБРАБОТЧИКИ ==========
def process_start(message: dict):
    user_id = message["from"]["id"]
    username = message["from"].get("username", "No username")
    first_name = message["from"].get("first_name", "No name")
    
    user = db.fetchone("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not user:
        db.execute(
            "INSERT INTO users (user_id, username, first_name, joined_date) VALUES (?, ?, ?, ?)",
            (user_id, username, first_name, int(datetime.now().timestamp()))
        )
        db.execute("INSERT INTO user_inventory (user_id, item_name, item_value, received_date, is_sold) VALUES (?, ?, ?, ?, ?)",
                   (user_id, "Приветственный подарок", 100, int(datetime.now().timestamp()), 0))
        update_balance(user_id, 100)
    
    text = f"🎉 Добро пожаловать, {first_name}!\n\n💰 Ваш баланс: {get_user_balance(user_id)}{get_currency()}\n\nВыберите действие:"
    
    send_message(user_id, text, main_keyboard(user_id))

def process_callback_query(callback: dict):
    callback_id = callback["id"]
    user_id = callback["from"]["id"]
    message = callback["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    data = callback["data"]
    
    # Проверка админа для некоторых действий
    if data.startswith("admin") and not is_admin(user_id):
        answer_callback(callback_id, "❌ Нет доступа!", True)
        return
    
    # Главное меню
    if data == "back_to_main":
        text = f"💰 Ваш баланс: {get_user_balance(user_id)}{get_currency()}\n\nГлавное меню:"
        edit_message(chat_id, message_id, text, main_keyboard(user_id))
        answer_callback(callback_id)
        return
    
    # Баланс
    elif data == "show_balance":
        balance = get_user_balance(user_id)
        text = f"💰 Ваш баланс: {balance}{get_currency()}"
        edit_message(chat_id, message_id, text, main_keyboard(user_id))
        answer_callback(callback_id)
        return
    
    # Кейсы
    elif data == "show_cases":
        if not check_subscriptions(user_id):
            text = "❌ Для открытия кейсов необходимо подписаться на наши каналы:"
            edit_message(chat_id, message_id, text, get_subscription_keyboard())
            answer_callback(callback_id)
            return
        
        edit_message(chat_id, message_id, "🎁 Выберите кейс для открытия:", cases_keyboard())
        answer_callback(callback_id)
        return
    
    # Открытие кейса
    elif data.startswith("open_case_"):
        if not check_subscriptions(user_id):
            answer_callback(callback_id, "❌ Вы не подписаны на наши каналы!", True)
            return
        
        case_id = int(data.split("_")[2])
        case = db.fetchone("SELECT name, price FROM cases WHERE id = ?", (case_id,))
        
        if not case:
            answer_callback(callback_id, "Кейс не найден!", True)
            return
        
        case_name, price = case
        balance = get_user_balance(user_id)
        
        if balance < price:
            answer_callback(callback_id, f"❌ Недостаточно средств! Нужно {price}{get_currency()}", True)
            return
        
        update_balance(user_id, -price)
        result = open_case(user_id, case_id)
        
        if result:
            db.execute("UPDATE users SET total_opened = total_opened + 1 WHERE user_id = ?", (user_id,))
            db.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id = ?", (price, user_id))
            
            text = f"🎉 Вы открыли кейс '{case_name}'!\n\n📦 Вам выпало: {result['name']}\n💰 Стоимость: {result['value']}{get_currency()}"
            edit_message(chat_id, message_id, text, cases_keyboard())
        else:
            update_balance(user_id, price)
            text = f"❌ Ошибка при открытии кейса! Ваши средства возвращены."
            edit_message(chat_id, message_id, text, cases_keyboard())
        
        answer_callback(callback_id)
        return
    
    # Инвентарь
    elif data == "show_inventory":
        edit_message(chat_id, message_id, "📦 Ваш инвентарь:", inventory_keyboard(user_id))
        answer_callback(callback_id)
        return
    
    elif data.startswith("inv_page_"):
        page = int(data.split("_")[2])
        edit_message(chat_id, message_id, "📦 Ваш инвентарь:", inventory_keyboard(user_id, page))
        answer_callback(callback_id)
        return
    
    # Продажа предмета
    elif data.startswith("sell_item_"):
        item_id = int(data.split("_")[2])
        item = db.fetchone("SELECT item_name, item_value FROM user_inventory WHERE id = ? AND user_id = ? AND is_sold = 0", 
                           (item_id, user_id))
        
        if item:
            item_name, item_value = item
            update_balance(user_id, item_value)
            db.execute("UPDATE user_inventory SET is_sold = 1 WHERE id = ?", (item_id,))
            answer_callback(callback_id, f"✅ Вы продали {item_name} за {item_value}{get_currency()}!", True)
            edit_message(chat_id, message_id, "📦 Ваш инвентарь:", inventory_keyboard(user_id))
        else:
            answer_callback(callback_id, "❌ Предмет не найден!", True)
        return
    
    # Магазин
    elif data == "show_shop":
        edit_message(chat_id, message_id, "🏪 Магазин\n\nВыберите действие:", shop_keyboard())
        answer_callback(callback_id)
        return
    
    elif data == "deposit":
        payment_card = get_setting('payment_card')
        payment_phone = get_setting('payment_phone')
        
        text = "💳 Способы пополнения:\n\n"
        if payment_card:
            text += f"💳 Карта: `{payment_card}`\n"
        if payment_phone:
            text += f"📱 Телефон: `{payment_phone}`\n"
        
        text += "\nПосле оплаты отправьте скриншот в поддержку (укажите ник)"
        
        edit_message(chat_id, message_id, text, shop_keyboard())
        answer_callback(callback_id)
        return
    
    # Казино
    elif data == "show_casino":
        min_bet = get_setting('casino_min_bet')
        max_bet = get_setting('casino_max_bet')
        
        text = f"🎰 КАЗИНО 🎰\n\nПравила: компьютер загадывает число от 1 до 10, вы пытаетесь угадать.\nПри совпадении вы выигрываете x2 ставки!\n\n💰 Минимальная ставка: {min_bet}{get_currency()}\n💰 Максимальная ставка: {max_bet}{get_currency()}\n\nВведите сумму ставки в чат:"
        
        edit_message(chat_id, message_id, text, back_keyboard())
        set_user_state(user_id, "waiting_casino_bet", {})
        answer_callback(callback_id)
        return
    
    # Скупка
    elif data == "show_resell":
        edit_message(chat_id, message_id, "🔄 Скупка предметов\n\nЗдесь вы можете продать все предметы из инвентаря по их стоимости.", resell_keyboard())
        answer_callback(callback_id)
        return
    
    elif data == "sell_all_items":
        items = db.fetchall("SELECT id, item_value FROM user_inventory WHERE user_id = ? AND is_sold = 0", (user_id,))
        
        if not items:
            answer_callback(callback_id, "❌ У вас нет предметов для продажи!", True)
            return
        
        total = 0
        for item_id, value in items:
            total += value
            db.execute("UPDATE user_inventory SET is_sold = 1 WHERE id = ?", (item_id,))
        
        update_balance(user_id, total)
        answer_callback(callback_id, f"✅ Вы продали все предметы за {total}{get_currency()}!", True)
        
        text = f"✅ Продано на сумму: {total}{get_currency()}\n💰 Новый баланс: {get_user_balance(user_id)}{get_currency()}"
        edit_message(chat_id, message_id, text, main_keyboard(user_id))
        return
    
    # Бонус кейс
    elif data == "bonus_case":
        if not check_subscriptions(user_id):
            answer_callback(callback_id, "❌ Вы не подписаны на наши каналы!", True)
            return
        
        user = db.fetchone("SELECT last_bonus_time FROM users WHERE user_id = ?", (user_id,))
        last_time = user[0] if user else 0
        now = int(datetime.now().timestamp())
        
        if now - last_time < 86400:
            hours_left = 24 - (now - last_time) // 3600
            answer_callback(callback_id, f"⏰ Бонусный кейс доступен через {hours_left} часов!", True)
            return
        
        bonus_value = random.randint(50, 500)
        add_to_inventory(user_id, "Бонусный предмет", bonus_value)
        db.execute("UPDATE users SET last_bonus_time = ? WHERE user_id = ?", (now, user_id))
        
        answer_callback(callback_id, f"🎁 Вы получили бонусный предмет стоимостью {bonus_value}{get_currency()}!", True)
        
        text = f"🎁 Бонус получен!\n📦 Вам выпал предмет стоимостью {bonus_value}{get_currency()}"
        edit_message(chat_id, message_id, text, main_keyboard(user_id))
        return
    
    # Поддержка
    elif data == "support":
        support_contact = get_setting('support_contact')
        text = f"🆘 Поддержка\n\nСвяжитесь с нами: {support_contact}\n\nПо всем вопросам: оплата, проблемы с ботом, сотрудничество."
        edit_message(chat_id, message_id, text, main_keyboard(user_id))
        answer_callback(callback_id)
        return
    
    # Проверка подписки
    elif data == "check_subscription":
        if check_subscriptions(user_id):
            text = f"✅ Подписка подтверждена! Возвращаемся в меню.\n💰 Ваш баланс: {get_user_balance(user_id)}{get_currency()}"
            edit_message(chat_id, message_id, text, main_keyboard(user_id))
        else:
            answer_callback(callback_id, "❌ Вы не подписаны на все каналы!", True)
        return
    
    # ========== АДМИН ПАНЕЛЬ ==========
    elif data == "admin_panel":
        edit_message(chat_id, message_id, "⚙️ Админ панель\n\nВыберите действие:", admin_keyboard())
        answer_callback(callback_id)
        return
    
    elif data == "admin_cases":
        edit_message(chat_id, message_id, "📦 Управление кейсами:", admin_cases_keyboard())
        answer_callback(callback_id)
        return
    
    elif data == "create_case":
        set_user_state(user_id, "waiting_case_name", {})
        text = "Введите название кейса:"
        send_message(chat_id, text)
        answer_callback(callback_id)
        return
    
    elif data == "list_cases":
        cases = db.fetchall("SELECT id, name, price, is_active FROM cases")
        
        if not cases:
            answer_callback(callback_id, "Нет созданных кейсов!", True)
            return
        
        text = "📋 Список кейсов:\n\n"
        for case_id, name, price, is_active in cases:
            status = "✅ Активен" if is_active else "❌ Неактивен"
            text += f"ID: {case_id} | {name} - {price}{get_currency()} | {status}\n"
        
        send_message(chat_id, text)
        answer_callback(callback_id)
        return
    
    elif data == "admin_broadcast":
        set_user_state(user_id, "waiting_broadcast", {})
        send_message(chat_id, "Введите текст для рассылки (можно с HTML разметкой):")
        answer_callback(callback_id)
        return
    
    elif data == "admin_payment":
        keyboard = {
            "inline_keyboard": [
                [{"text": "💳 Номер карты", "callback_data": "set_card"}],
                [{"text": "📱 Номер телефона", "callback_data": "set_phone"}],
                [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
            ]
        }
        edit_message(chat_id, message_id, "💳 Настройка способов оплаты:", keyboard)
        answer_callback(callback_id)
        return
    
    elif data == "set_card":
        set_user_state(user_id, "waiting_card", {})
        send_message(chat_id, "Введите номер карты для пополнения:")
        answer_callback(callback_id)
        return
    
    elif data == "set_phone":
        set_user_state(user_id, "waiting_phone", {})
        send_message(chat_id, "Введите номер телефона для пополнения:")
        answer_callback(callback_id)
        return
    
    elif data == "admin_currency":
        set_user_state(user_id, "waiting_currency", {})
        send_message(chat_id, "Введите символ валюты (например: ⭐, $, €, 🪙):")
        answer_callback(callback_id)
        return
    
    elif data == "admin_balance":
        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ Добавить баланс", "callback_data": "add_balance"}],
                [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
            ]
        }
        edit_message(chat_id, message_id, "💰 Управление балансом пользователей:", keyboard)
        answer_callback(callback_id)
        return
    
    elif data == "add_balance":
        set_user_state(user_id, "waiting_add_balance", {})
        send_message(chat_id, "Введите ID пользователя и сумму через пробел (например: 123456789 100):")
        answer_callback(callback_id)
        return
    
    elif data == "admin_channels":
        channels = db.fetchall("SELECT id, channel_id, channel_name FROM required_channels")
        text = "📢 Обязательные подписки:\n\n"
        
        for ch_id, channel_id, name in channels:
            text += f"📌 {name} ({channel_id})\n"
        
        if not channels:
            text += "Нет обязательных подписок\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ Добавить канал", "callback_data": "add_channel"}],
                [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
            ]
        }
        edit_message(chat_id, message_id, text, keyboard)
        answer_callback(callback_id)
        return
    
    elif data == "add_channel":
        set_user_state(user_id, "waiting_channel_id", {})
        send_message(chat_id, "Введите ID канала (например: @channel_username или -100123456789):")
        answer_callback(callback_id)
        return
    
    elif data == "admin_admins":
        admins = db.fetchall("SELECT user_id FROM admins")
        text = "👑 Список администраторов:\n\n"
        
        for admin in admins:
            text += f"🆔 {admin[0]}\n"
        
        keyboard = {
            "inline_keyboard": [
                [{"text": "➕ Добавить админа", "callback_data": "add_admin"}],
                [{"text": "🔙 Назад", "callback_data": "admin_panel"}]
            ]
        }
        edit_message(chat_id, message_id, text, keyboard)
        answer_callback(callback_id)
        return
    
    elif data == "add_admin":
        set_user_state(user_id, "waiting_admin_id", {})
        send_message(chat_id, "Введите ID пользователя для добавления в администраторы:")
        answer_callback(callback_id)
        return
    
    elif data == "admin_stats":
        total_users = db.fetchone("SELECT COUNT(*) FROM users")[0]
        total_spent = db.fetchone("SELECT SUM(total_spent) FROM users")[0] or 0
        total_opened = db.fetchone("SELECT SUM(total_opened) FROM users")[0] or 0
        total_items = db.fetchone("SELECT COUNT(*) FROM user_inventory WHERE is_sold = 0")[0]
        
        text = f"📊 СТАТИСТИКА\n\n"
        text += f"👥 Всего пользователей: {total_users}\n"
        text += f"💰 Всего потрачено: {total_spent}{get_currency()}\n"
        text += f"🎁 Всего открыто кейсов: {total_opened}\n"
        text += f"📦 Предметов в инвентаре: {total_items}\n"
        
        edit_message(chat_id, message_id, text, admin_keyboard())
        answer_callback(callback_id)
        return

# ========== ОБРАБОТКА ТЕКСТОВЫХ СООБЩЕНИЙ ==========
def process_message(message: dict):
    user_id = message["from"]["id"]
    text = message.get("text", "")
    chat_id = message["chat"]["id"]
    
    state, state_data = get_user_state(user_id)
    
    # Создание кейса - название
    if state == "waiting_case_name":
        set_user_state(user_id, "waiting_case_price", {"case_name": text})
        send_message(chat_id, "Введите цену кейса (число):")
        return
    
    # Создание кейса - цена
    elif state == "waiting_case_price":
        try:
            price = float(text)
            data = state_data
            data["case_price"] = price
            set_user_state(user_id, "waiting_case_photo", data)
            send_message(chat_id, "Отправьте фото для кейса (или отправьте 'пропустить'):")
        except ValueError:
            send_message(chat_id, "❌ Введите число!")
        return
    
    # Создание кейса - фото
    elif state == "waiting_case_photo":
        data = state_data
        photo_url = ""
        
        if message.get("photo"):
            photo_url = message["photo"][-1]["file_id"]
        elif text.lower() != "пропустить":
            send_message(chat_id, "❌ Отправьте фото или напишите 'пропустить'")
            return
        
        case_id = db.execute(
            "INSERT INTO cases (name, price, photo_url) VALUES (?, ?, ?)",
            (data["case_name"], data["case_price"], photo_url)
        )
        
        set_user_state(user_id, "waiting_item_name", {"case_id": case_id})
        send_message(chat_id, f"✅ Кейс '{data['case_name']}' создан!\n\nТеперь добавьте предметы в кейс.\nВведите название предмета:")
        return
    
    # Добавление предмета - название
    elif state == "waiting_item_name":
        set_user_state(user_id, "waiting_item_value", {"case_id": state_data["case_id"], "item_name": text})
        send_message(chat_id, "Введите стоимость предмета (число):")
        return
    
    # Добавление предмета - стоимость
    elif state == "waiting_item_value":
        try:
            value = float(text)
            data = state_data
            data["item_value"] = value
            set_user_state(user_id, "waiting_item_chance", data)
            send_message(chat_id, "Введите шанс выпадения (например, 10.5 - это 10.5%):")
        except ValueError:
            send_message(chat_id, "❌ Введите число!")
        return
    
    # Добавление предмета - шанс
    elif state == "waiting_item_chance":
        try:
            chance = float(text)
            data = state_data
            
            db.execute(
                "INSERT INTO case_items (case_id, item_name, item_value, chance) VALUES (?, ?, ?, ?)",
                (data["case_id"], data["item_name"], data["item_value"], chance)
            )
            
            send_message(chat_id, f"✅ Предмет '{data['item_name']}' добавлен!\n\nХотите добавить еще предмет? (да/нет)")
            set_user_state(user_id, "waiting_more_items", {"case_id": data["case_id"]})
        except ValueError:
            send_message(chat_id, "❌ Введите число!")
        return
    
    # Добавление еще предметов
    elif state == "waiting_more_items":
        if text.lower() == "да":
            set_user_state(user_id, "waiting_item_name", {"case_id": state_data["case_id"]})
            send_message(chat_id, "Введите название следующего предмета:")
        else:
            set_user_state(user_id, None, None)
            send_message(chat_id, "✅ Создание кейса завершено!", admin_keyboard())
        return
    
    # Рассылка
    elif state == "waiting_broadcast":
        set_user_state(user_id, None, None)
        users = db.fetchall("SELECT user_id FROM users")
        
        success = 0
        fail = 0
        
        send_message(chat_id, f"📢 Начинаю рассылку для {len(users)} пользователей...")
        
        for user in users:
            try:
                send_message(user[0], text, parse_mode="HTML")
                success += 1
                time.sleep(0.05)
            except:
                fail += 1
        
        send_message(chat_id, f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {fail}")
        return
    
    # Настройка карты
    elif state == "waiting_card":
        set_setting("payment_card", text)
        set_user_state(user_id, None, None)
        send_message(chat_id, "✅ Номер карты сохранен!", admin_keyboard())
        return
    
    # Настройка телефона
    elif state == "waiting_phone":
        set_setting("payment_phone", text)
        set_user_state(user_id, None, None)
        send_message(chat_id, "✅ Номер телефона сохранен!", admin_keyboard())
        return
    
    # Настройка валюты
    elif state == "waiting_currency":
        set_setting("currency_symbol", text)
        set_user_state(user_id, None, None)
        send_message(chat_id, f"✅ Валюта изменена на {text}!", admin_keyboard())
        return
    
    # Добавление баланса
    elif state == "waiting_add_balance":
        try:
            parts = text.split()
            target_user_id = int(parts[0])
            amount = float(parts[1])
            
            update_balance(target_user_id, amount)
            set_user_state(user_id, None, None)
            send_message(chat_id, f"✅ Пользователю {target_user_id} добавлено {amount}{get_currency()}!", admin_keyboard())
            
            try:
                send_message(target_user_id, f"🎉 Администратор добавил вам {amount}{get_currency()} на баланс!")
            except:
                pass
        except:
            send_message(chat_id, "❌ Ошибка! Используйте формат: ID Сумма")
        return
    
    # Добавление канала
    elif state == "waiting_channel_id":
        set_user_state(user_id, "waiting_channel_name", {"channel_id": text})
        send_message(chat_id, "Введите название канала (для отображения в кнопке):")
        return
    
    elif state == "waiting_channel_name":
        channel_id = state_data["channel_id"]
        db.execute(
            "INSERT INTO required_channels (channel_id, channel_name) VALUES (?, ?)",
            (channel_id, text)
        )
        set_user_state(user_id, None, None)
        send_message(chat_id, "✅ Канал добавлен в обязательные подписки!", admin_keyboard())
        return
    
    # Добавление админа
    elif state == "waiting_admin_id":
        try:
            admin_id = int(text)
            db.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (admin_id,))
            set_user_state(user_id, None, None)
            send_message(chat_id, f"✅ Пользователь {admin_id} добавлен в администраторы!", admin_keyboard())
        except ValueError:
            send_message(chat_id, "❌ Введите число!")
        return
    
    # Казино - ставка
    elif state == "waiting_casino_bet":
        try:
            bet = float(text)
            min_bet = float(get_setting('casino_min_bet'))
            max_bet = float(get_setting('casino_max_bet'))
            
            if bet < min_bet or bet > max_bet:
                send_message(chat_id, f"❌ Ставка должна быть от {min_bet} до {max_bet}{get_currency()}")
                return
            
            win, result = casino_game(user_id, bet)
            set_user_state(user_id, None, None)
            
            send_message(chat_id, f"{result}\n\n💰 Новый баланс: {get_user_balance(user_id)}{get_currency()}", main_keyboard(user_id))
        except ValueError:
            send_message(chat_id, "❌ Введите число!")
            set_user_state(user_id, None, None)
        return

# ========== ОСНОВНОЙ ЦИКЛ ПОЛЛИНГА ==========
def main():
    logger.info("Бот запущен!")
    
    last_update_id = 0
    
    while True:
        try:
            response = tg_api("getUpdates", {"offset": last_update_id + 1, "timeout": 30})
            
            if response.get("ok"):
                for update in response["result"]:
                    last_update_id = update["update_id"]
                    
                    if "message" in update:
                        message = update["message"]
                        
                        if "text" in message and message["text"] == "/start":
                            process_start(message)
                        else:
                            process_message(message)
                    
                    elif "callback_query" in update:
                        process_callback_query(update["callback_query"])
            
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()