import asyncio
import random
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ========== НАСТРОЙКИ (ЗАМЕНИТЕ НА СВОИ) ==========
BOT_TOKEN = "8071372461:AAE8RBJ8DwRfKf3ddTHz8zRjAL8YwB8B-bM"
ADMIN_IDS = [5356400377]

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== БАЗА ДАННЫХ (JSON) ==========
import os

class Database:
    def __init__(self, db_file="bot_data.json"):
        self.db_file = db_file
        self.data = self.load_data()
    
    def load_data(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return self.init_data()
    
    def save_data(self):
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def init_data(self):
        data = {
            'users': {},
            'cases': [],
            'case_items': [],
            'user_inventory': [],
            'settings': {
                'currency_symbol': '💰',
                'currency_name': 'монет',
                'casino_min_bet': '10',
                'casino_max_bet': '1000',
                'support_contact': '@support_username',
                'payment_card': '',
                'payment_phone': '',
                'bonus_case_cooldown': '86400',
                'coin_price_rub': '1',
                'case_price_rub': '50'
            },
            'required_channels': [],
            'bonus_cases': [],
            'next_case_id': 1,
            'next_item_id': 1,
            'next_inventory_id': 1,
            'next_bonus_id': 1
        }
        return data
    
    def get_users(self):
        return self.data['users']
    
    def add_user(self, user_id, username, first_name):
        if str(user_id) not in self.data['users']:
            self.data['users'][str(user_id)] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'balance': 500,
                'total_spent': 0,
                'total_opened': 0,
                'last_bonus_time': 0,
                'joined_date': int(datetime.now().timestamp())
            }
            self.save_data()
    
    def update_user_balance(self, user_id, amount):
        user_id = str(user_id)
        if user_id in self.data['users']:
            self.data['users'][user_id]['balance'] += amount
            self.save_data()
            return True
        return False
    
    def get_user_balance(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['users']:
            return self.data['users'][user_id]['balance']
        return 500
    
    def update_user_stats(self, user_id, spent=0, opened=0):
        user_id = str(user_id)
        if user_id in self.data['users']:
            self.data['users'][user_id]['total_spent'] += spent
            self.data['users'][user_id]['total_opened'] += opened
            self.save_data()
    
    def update_bonus_time(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['users']:
            self.data['users'][user_id]['last_bonus_time'] = int(datetime.now().timestamp())
            self.save_data()
    
    def get_last_bonus_time(self, user_id):
        user_id = str(user_id)
        if user_id in self.data['users']:
            return self.data['users'][user_id]['last_bonus_time']
        return 0
    
    def get_cases(self):
        return self.data['cases']
    
    def get_active_cases(self):
        return [c for c in self.data['cases'] if c.get('is_active', 1) == 1]
    
    def get_case(self, case_id):
        for case in self.data['cases']:
            if case['id'] == case_id:
                return case
        return None
    
    def add_case(self, name, price, description):
        case_id = self.data['next_case_id']
        self.data['cases'].append({
            'id': case_id,
            'name': name,
            'price': price,
            'description': description,
            'is_active': 1
        })
        self.data['next_case_id'] += 1
        self.save_data()
        return case_id
    
    def get_case_items(self, case_id):
        return [item for item in self.data['case_items'] if item['case_id'] == case_id]
    
    def add_case_item(self, case_id, item_name, item_value, chance, rarity, emoji):
        item_id = self.data['next_item_id']
        self.data['case_items'].append({
            'id': item_id,
            'case_id': case_id,
            'item_name': item_name,
            'item_value': item_value,
            'chance': chance,
            'rarity': rarity,
            'emoji': emoji
        })
        self.data['next_item_id'] += 1
        self.save_data()
        return item_id
    
    def add_to_inventory(self, user_id, item_name, item_value, item_emoji, rarity, from_case):
        inv_id = self.data['next_inventory_id']
        self.data['user_inventory'].append({
            'id': inv_id,
            'user_id': user_id,
            'item_name': item_name,
            'item_value': item_value,
            'item_emoji': item_emoji,
            'rarity': rarity,
            'received_date': int(datetime.now().timestamp()),
            'from_case': from_case
        })
        self.data['next_inventory_id'] += 1
        self.save_data()
    
    def get_user_inventory(self, user_id):
        return [item for item in self.data['user_inventory'] if item['user_id'] == user_id]
    
    def get_setting(self, key):
        return self.data['settings'].get(key, '')
    
    def set_setting(self, key, value):
        self.data['settings'][key] = value
        self.save_data()
    
    def get_channels(self):
        return self.data['required_channels']
    
    def add_channel(self, channel_id, channel_name, channel_url):
        self.data['required_channels'].append({
            'channel_id': channel_id,
            'channel_name': channel_name,
            'channel_url': channel_url
        })
        self.save_data()
    
    def get_bonus_cases(self):
        return self.data['bonus_cases']
    
    def add_bonus_case(self, name, description, reward_min, reward_max, cooldown):
        bonus_id = self.data['next_bonus_id']
        self.data['bonus_cases'].append({
            'id': bonus_id,
            'name': name,
            'description': description,
            'reward_min': reward_min,
            'reward_max': reward_max,
            'cooldown': cooldown,
            'is_active': 1
        })
        self.data['next_bonus_id'] += 1
        self.save_data()
        return bonus_id
    
    def remove_bonus_case(self, bonus_id):
        self.data['bonus_cases'] = [b for b in self.data['bonus_cases'] if b['id'] != bonus_id]
        self.save_data()
    
    def get_total_users(self):
        return len(self.data['users'])
    
    def get_total_spent(self):
        return sum(user['total_spent'] for user in self.data['users'].values())
    
    def get_total_opened(self):
        return sum(user['total_opened'] for user in self.data['users'].values())
    
    def get_total_balance(self):
        return sum(user['balance'] for user in self.data['users'].values())

db = Database()

# ========== СОСТОЯНИЯ ДЛЯ FSM ==========
class AdminStates(StatesGroup):
    waiting_for_case_name = State()
    waiting_for_case_price = State()
    waiting_for_case_desc = State()
    waiting_for_item_name = State()
    waiting_for_item_value = State()
    waiting_for_item_chance = State()
    waiting_for_item_rarity = State()
    waiting_for_item_emoji = State()
    waiting_for_broadcast_text = State()
    waiting_for_payment_card = State()
    waiting_for_payment_phone = State()
    waiting_for_currency_symbol = State()
    waiting_for_currency_name = State()
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_channel_url = State()
    waiting_for_add_balance = State()
    waiting_for_bonus_name = State()
    waiting_for_bonus_desc = State()
    waiting_for_bonus_min = State()
    waiting_for_bonus_max = State()
    waiting_for_bonus_cooldown = State()
    waiting_for_coin_price = State()
    waiting_for_case_price_rub = State()

class GameStates(StatesGroup):
    waiting_for_crash_bet = State()
    waiting_for_tower_bet = State()
    waiting_for_tower_choice = State()
    waiting_for_mines_bet = State()
    waiting_for_mines_choice = State()
    waiting_for_roulette_bet = State()
    waiting_for_roulette_choice = State()
    waiting_for_plinko_bet = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_user_balance(user_id: int) -> float:
    return db.get_user_balance(user_id)

def update_balance(user_id: int, amount: float):
    db.update_user_balance(user_id, amount)

def add_to_inventory(user_id: int, item_name: str, item_value: float, item_emoji: str = "📦", rarity: str = "Обычный", from_case: str = ""):
    db.add_to_inventory(user_id, item_name, item_value, item_emoji, rarity, from_case)

def get_currency() -> str:
    return db.get_setting('currency_symbol')

def get_currency_name() -> str:
    return db.get_setting('currency_name')

def get_setting(key: str) -> str:
    return db.get_setting(key)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_balance(balance: float) -> str:
    return f"{balance:.0f} {get_currency_name()}"

async def check_subscriptions(user_id: int) -> bool:
    channels = db.get_channels()
    if not channels:
        return True
    
    for channel in channels:
        channel_id = channel['channel_id']
        try:
            member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            pass
    return True

def get_rarity_emoji(rarity: str) -> str:
    rarities = {
        "Обычный": "⬜",
        "Необычный": "🟩",
        "Редкий": "🟦",
        "Эпический": "🟪",
        "Легендарный": "🟧",
        "Мифический": "🔴"
    }
    return rarities.get(rarity, "⬜")

# ========== СОВРЕМЕННЫЕ ИГРЫ ==========

# ИГРА 1: CRASH (Летающий самолет)
async def play_crash(bet: float) -> Tuple[bool, float, float, str]:
    multiplier = random.uniform(1.0, 10.0)
    crash_point = random.uniform(1.0, 5.0)
    
    result_text = f"✈️ **CRASH GAME** ✈️\n\n"
    result_text += f"Множитель: {multiplier:.2f}x\n"
    result_text += f"Точка краша: {crash_point:.2f}x\n\n"
    
    if multiplier <= crash_point:
        win_amount = bet * multiplier
        result_text += f"🎉 ВЫ УСПЕЛИ ВЫЙТИ!\n"
        result_text += f"💰 Выигрыш: {win_amount:.0f} {get_currency_name()}"
        return True, win_amount, multiplier, result_text
    else:
        result_text += f"💥 КРАШ! Самолет улетел!\n"
        result_text += f"😢 Вы проиграли {bet:.0f} {get_currency_name()}"
        return False, 0, multiplier, result_text

# ИГРА 2: TOWER (Башня)
async def play_tower(bet: float, level: int) -> Tuple[bool, float, str, int]:
    success_chance = 0.7 - (level * 0.05)
    is_success = random.random() < success_chance
    
    if is_success:
        new_level = level + 1
        win_amount = bet * (1 + level * 0.3)
        
        if new_level >= 10:
            result_text = f"🗼 **TOWER** 🗼\n\n"
            result_text += f"🎉 ПОБЕДА! Вы прошли башню!\n"
            result_text += f"💰 Выигрыш: {win_amount:.0f} {get_currency_name()}"
            return True, win_amount, result_text, 10
        else:
            result_text = f"🗼 **TOWER** 🗼\n\n"
            result_text += f"✅ Уровень {new_level} пройден!\n"
            result_text += f"💰 Текущий выигрыш: {win_amount:.0f} {get_currency_name()}\n\n"
            result_text += f"🎮 Продолжим?"
            return None, win_amount, result_text, new_level
    else:
        result_text = f"🗼 **TOWER** 🗼\n\n"
        result_text += f"💥 ПРОВАЛ! Башня рухнула!\n"
        result_text += f"😢 Вы проиграли {bet:.0f} {get_currency_name()}"
        return False, 0, result_text, level

# ИГРА 3: MINES (Минное поле)
async def play_mines(bet: float, cell: int, mines: List[int]) -> Tuple[bool, float, str, List[int], float]:
    if cell in mines:
        result_text = f"💣 **MINES** 💣\n\n"
        result_text += f"💥 БАМ! Вы наступили на мину!\n"
        result_text += f"😢 Вы проиграли {bet:.0f} {get_currency_name()}"
        return False, 0, result_text, mines, 0
    
    safe_cells = [c for c in range(1, 26) if c not in mines]
    if len(mines) == len(safe_cells):
        win_amount = bet * 5
        result_text = f"💣 **MINES** 💣\n\n"
        result_text += f"🎉 ПОБЕДА! Вы обезвредили все мины!\n"
        result_text += f"💰 Выигрыш: {win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text, mines, win_amount
    
    current_multiplier = 1 + (len(mines) * 0.2)
    win_amount = bet * current_multiplier
    
    result_text = f"💣 **MINES** 💣\n\n"
    result_text += f"✅ Клетка {cell} безопасна!\n"
    result_text += f"💰 Текущий выигрыш: {win_amount:.0f} {get_currency_name()}\n\n"
    result_text += f"🎮 Продолжим?"
    return None, win_amount, result_text, mines, current_multiplier

# ИГРА 4: ROULETTE (Рулетка)
async def play_roulette(bet: float, choice: str, number: int = None) -> Tuple[bool, float, str]:
    winning_number = random.randint(0, 36)
    result_text = f"🎡 **РУЛЕТКА** 🎡\n\n"
    result_text += f"Выпало число: {winning_number}\n\n"
    
    win = False
    multiplier = 0
    
    if choice == "number" and number == winning_number:
        win = True
        multiplier = 35
        result_text += f"🎉 ТОЧНОЕ ПОПАДАНИЕ! x35!"
    elif choice == "red" and winning_number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        win = True
        multiplier = 2
        result_text += f"🔴 КРАСНОЕ! x2!"
    elif choice == "black" and winning_number in [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]:
        win = True
        multiplier = 2
        result_text += f"⚫ ЧЕРНОЕ! x2!"
    elif choice == "even" and winning_number > 0 and winning_number % 2 == 0:
        win = True
        multiplier = 2
        result_text += f"✅ ЧЕТНОЕ! x2!"
    elif choice == "odd" and winning_number > 0 and winning_number % 2 == 1:
        win = True
        multiplier = 2
        result_text += f"✅ НЕЧЕТНОЕ! x2!"
    elif choice == "1-18" and 1 <= winning_number <= 18:
        win = True
        multiplier = 2
        result_text += f"📊 ОТ 1 ДО 18! x2!"
    elif choice == "19-36" and 19 <= winning_number <= 36:
        win = True
        multiplier = 2
        result_text += f"📊 ОТ 19 ДО 36! x2!"
    else:
        result_text += f"😢 Вы проиграли!"
    
    if win:
        win_amount = bet * multiplier
        result_text += f"\n💰 Выигрыш: {win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        return False, 0, result_text

# ИГРА 5: PLINKO
async def play_plinko(bet: float, risk: str) -> Tuple[bool, float, str]:
    multipliers = {
        "low": [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 1.5, 1.2, 1.0, 0.8, 0.5],
        "medium": [0.3, 0.5, 0.8, 1.2, 1.8, 3.0, 1.8, 1.2, 0.8, 0.5, 0.3],
        "high": [0.2, 0.4, 0.7, 1.5, 3.0, 10.0, 3.0, 1.5, 0.7, 0.4, 0.2]
    }
    
    mults = multipliers.get(risk, multipliers["medium"])
    result_position = random.randint(0, len(mults)-1)
    multiplier = mults[result_position]
    
    result_text = f"🎯 **PLINKO** 🎯\n\n"
    result_text += f"Шарик упал в позицию {result_position + 1}\n"
    result_text += f"Множитель: {multiplier}x\n\n"
    
    if multiplier >= 1:
        win_amount = bet * multiplier
        result_text += f"🎉 ВЫИГРЫШ! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        win_amount = bet * multiplier
        result_text += f"😢 Вы проиграли {bet - win_amount:.0f} {get_currency_name()}"
        return False, 0, result_text

# ========== КЛАВИАТУРЫ ==========
def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Кейсы", callback_data="show_cases")
    builder.button(text="💰 Баланс", callback_data="show_balance")
    builder.button(text="📦 Инвентарь", callback_data="show_inventory")
    builder.button(text="🎮 Игры", callback_data="show_games")
    builder.button(text="🏪 Магазин", callback_data="show_shop")
    builder.button(text="🎁 Бонус кейс", callback_data="show_bonus_cases")
    builder.button(text="🆘 Поддержка", callback_data="support")
    if is_admin(user_id):
        builder.button(text="⚙️ Админ", callback_data="admin_panel")
    builder.adjust(2)
    return builder.as_markup()

def games_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✈️ Crash", callback_data="game_crash")
    builder.button(text="🗼 Tower", callback_data="game_tower")
    builder.button(text="💣 Mines", callback_data="game_mines")
    builder.button(text="🎡 Рулетка", callback_data="game_roulette")
    builder.button(text="🎯 Plinko", callback_data="game_plinko")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

def cases_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    cases = db.get_active_cases()
    for case in cases:
        builder.button(text=f"📦 {case['name']} | {case['price']}{get_currency()}", callback_data=f"case_{case['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def bonus_cases_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    bonuses = db.get_bonus_cases()
    for bonus in bonuses:
        if bonus.get('is_active', 1) == 1:
            builder.button(text=f"🎁 {bonus['name']}", callback_data=f"bonus_{bonus['id']}")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Кейсы", callback_data="admin_cases")
    builder.button(text="🎁 Бонус кейсы", callback_data="admin_bonus_cases")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="💳 Оплата", callback_data="admin_payment")
    builder.button(text="💰 Выдать монеты", callback_data="admin_add_balance")
    builder.button(text="⭐ Настройка валюты", callback_data="admin_currency")
    builder.button(text="💵 Цены в рублях", callback_data="admin_prices")
    builder.button(text="📢 Подписки", callback_data="admin_channels")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="🎮 Настройка игр", callback_data="admin_games")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    builder.adjust(2)
    return builder.as_markup()

def admin_cases_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать кейс", callback_data="admin_create_case")
    builder.button(text="📋 Список кейсов", callback_data="admin_list_cases")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(1)
    return builder.as_markup()

def tower_keyboard(current_win: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬆️ Продолжить", callback_data="tower_continue")
    builder.button(text="💰 Забрать выигрыш", callback_data="tower_cashout")
    return builder.as_markup()

def mines_keyboard(mines: List[int], revealed: List[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in range(1, 26):
        if i in revealed:
            builder.button(text="✅", callback_data=f"mines_{i}")
        else:
            builder.button(text="❓", callback_data=f"mines_{i}")
    builder.adjust(5)
    builder.button(text="💰 Забрать выигрыш", callback_data="mines_cashout")
    return builder.as_markup()

def roulette_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔴 Красное", callback_data="roulette_red")
    builder.button(text="⚫ Черное", callback_data="roulette_black")
    builder.button(text="✅ Четное", callback_data="roulette_even")
    builder.button(text="❌ Нечетное", callback_data="roulette_odd")
    builder.button(text="📊 1-18", callback_data="roulette_1-18")
    builder.button(text="📊 19-36", callback_data="roulette_19-36")
    builder.button(text="🔢 Число", callback_data="roulette_number")
    builder.button(text="🔙 Назад", callback_data="show_games")
    builder.adjust(2)
    return builder.as_markup()

def plinko_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🟢 Низкий риск", callback_data="plinko_low")
    builder.button(text="🟡 Средний риск", callback_data="plinko_medium")
    builder.button(text="🔴 Высокий риск", callback_data="plinko_high")
    builder.button(text="🔙 Назад", callback_data="show_games")
    builder.adjust(1)
    return builder.as_markup()

def get_subscription_keyboard():
    builder = InlineKeyboardBuilder()
    channels = db.get_channels()
    for channel in channels:
        if channel['channel_url']:
            builder.button(text=f"📢 {channel['channel_name']}", url=channel['channel_url'])
    builder.button(text="✅ Проверить подписку", callback_data="check_sub")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    return builder.as_markup()

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "No username"
    first_name = message.from_user.first_name or "No name"
    
    db.add_user(user_id, username, first_name)
    
    await message.answer(
        f"🎉 Добро пожаловать, {first_name}!\n\n"
        f"💰 Ваш баланс: {format_balance(get_user_balance(user_id))}\n\n"
        f"🎮 Добро пожаловать в современное казино!\n"
        f"✨ 5 уникальных игр ждут тебя!\n\n"
        f"Выберите действие:",
        reply_markup=main_keyboard(user_id)
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"💰 Ваш баланс: {format_balance(get_user_balance(callback.from_user.id))}\n\nГлавное меню:",
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    balance = get_user_balance(callback.from_user.id)
    await callback.answer(f"💰 Ваш баланс: {format_balance(balance)}", show_alert=True)

@dp.callback_query(F.data == "show_games")
async def show_games(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 **СОВРЕМЕННЫЕ ИГРЫ** 🎮\n\n"
        "✈️ **Crash** - Самолет летит, забери выигрыш вовремя\n"
        "🗼 **Tower** - Поднимайся по башне, рискуя всем\n"
        "💣 **Mines** - Найди безопасные клетки\n"
        "🎡 **Рулетка** - Классическая рулетка\n"
        "🎯 **Plinko** - Управляй риском и получай множители\n\n"
        "Выберите игру:",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await callback.answer()

# ========== ИГРА CRASH ==========
@dp.callback_query(F.data == "game_crash")
async def game_crash_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"✈️ **CRASH GAME** ✈️\n\n"
        f"Правила: Самолет летит с растущим множителем\n"
        f"Забери выигрыш ДО того, как самолет улетит!\n"
        f"Множитель может вырасти до x100!\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_crash_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_crash_bet)
async def game_crash_play(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
            return
        
        update_balance(message.from_user.id, -bet)
        
        win, win_amount, multiplier, result_text = await play_crash(bet)
        
        if win:
            update_balance(message.from_user.id, win_amount)
        
        await message.answer(
            f"{result_text}\n\n"
            f"💵 Новый баланс: {format_balance(get_user_balance(message.from_user.id))}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

# ========== ИГРА TOWER ==========
@dp.callback_query(F.data == "game_tower")
async def game_tower_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🗼 **TOWER GAME** 🗼\n\n"
        f"Правила: Поднимайся по башне!\n"
        f"С каждым уровнем риск растет, но и выигрыш тоже!\n"
        f"Дойди до 10 уровня и получи x5 от ставки!\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_tower_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_tower_bet)
async def game_tower_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
            return
        
        update_balance(message.from_user.id, -bet)
        await state.update_data(tower_bet=bet, tower_level=1, tower_current_win=0)
        
        win, win_amount, result_text, level = await play_tower(bet, 1)
        
        if win is None:
            await state.update_data(tower_current_win=win_amount, tower_level=level)
            await message.answer(
                result_text,
                parse_mode="Markdown",
                reply_markup=tower_keyboard(win_amount)
            )
            await state.set_state(GameStates.waiting_for_tower_choice)
        else:
            if win:
                update_balance(message.from_user.id, win_amount)
            await message.answer(
                f"{result_text}\n\n"
                f"💵 Новый баланс: {format_balance(get_user_balance(message.from_user.id))}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
            await state.clear()
            
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_tower_choice, F.data.in_(["tower_continue", "tower_cashout"]))
async def game_tower_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('tower_bet', 0)
    level = data.get('tower_level', 1)
    current_win = data.get('tower_current_win', 0)
    
    if callback.data == "tower_cashout":
        update_balance(callback.from_user.id, current_win)
        await callback.message.edit_text(
            f"🗼 **TOWER** 🗼\n\n"
            f"💰 Вы забрали {current_win:.0f} {get_currency_name()}!\n\n"
            f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    else:
        win, win_amount, result_text, new_level = await play_tower(bet, level)
        
        if win is None:
            await state.update_data(tower_current_win=win_amount, tower_level=new_level)
            await callback.message.edit_text(
                result_text,
                parse_mode="Markdown",
                reply_markup=tower_keyboard(win_amount)
            )
        else:
            if win:
                update_balance(callback.from_user.id, win_amount)
            await callback.message.edit_text(
                f"{result_text}\n\n"
                f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
            await state.clear()
    
    await callback.answer()

# ========== ИГРА MINES ==========
@dp.callback_query(F.data == "game_mines")
async def game_mines_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"💣 **MINES GAME** 💣\n\n"
        f"Правила: На поле 5x5 спрятаны мины\n"
        f"Открывай безопасные клетки\n"
        f"Чем больше открыл - тем выше множитель\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_mines_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_mines_bet)
async def game_mines_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
            return
        
        update_balance(message.from_user.id, -bet)
        
        mines = random.sample(range(1, 26), 5)
        await state.update_data(mines_bet=bet, mines_list=mines, mines_revealed=[])
        
        await message.answer(
            f"💣 **MINES GAME** 💣\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n"
            f"💎 Мин на поле: 5\n\n"
            f"Выбирайте безопасные клетки!",
            parse_mode="Markdown",
            reply_markup=mines_keyboard(mines, [])
        )
        await state.set_state(GameStates.waiting_for_mines_choice)
        
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_mines_choice, F.data.startswith("mines_"))
async def game_mines_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('mines_bet', 0)
    mines = data.get('mines_list', [])
    revealed = data.get('mines_revealed', [])
    
    if callback.data == "mines_cashout":
        current_win = data.get('mines_current_win', bet)
        update_balance(callback.from_user.id, current_win)
        await callback.message.edit_text(
            f"💣 **MINES** 💣\n\n"
            f"💰 Вы забрали {current_win:.0f} {get_currency_name()}!\n\n"
            f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    else:
        cell = int(callback.data.split("_")[1])
        if cell in revealed:
            await callback.answer("❌ Вы уже открыли эту клетку!", show_alert=True)
            return
        
        revealed.append(cell)
        win, win_amount, result_text, new_mines, multiplier = await play_mines(bet, cell, mines)
        
        if win is None:
            await state.update_data(mines_revealed=revealed, mines_current_win=win_amount)
            await callback.message.edit_text(
                result_text,
                parse_mode="Markdown",
                reply_markup=mines_keyboard(mines, revealed)
            )
        else:
            if win:
                update_balance(callback.from_user.id, win_amount)
            await callback.message.edit_text(
                f"{result_text}\n\n"
                f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
            await state.clear()
    
    await callback.answer()

# ========== ИГРА ROULETTE ==========
@dp.callback_query(F.data == "game_roulette")
async def game_roulette_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎡 **РУЛЕТКА** 🎡\n\n"
        f"Правила: Ставьте на цвет, четность или число\n"
        f"Цвет и четность - x2\n"
        f"Точное число - x35\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_roulette_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_roulette_bet)
async def game_roulette_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
            return
        
        await state.update_data(roulette_bet=bet)
        await message.answer(
            f"🎡 **РУЛЕТКА** 🎡\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Сделайте ваш выбор:",
            parse_mode="Markdown",
            reply_markup=roulette_keyboard()
        )
        await state.set_state(GameStates.waiting_for_roulette_choice)
        
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_roulette_choice, F.data.startswith("roulette_"))
async def game_roulette_choice(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('roulette_bet', 0)
    choice = callback.data.split("_")[1]
    
    update_balance(callback.from_user.id, -bet)
    
    if choice == "number":
        await callback.message.answer("🔢 Введите число от 0 до 36:")
        await state.update_data(roulette_choice="number")
        return
    
    win, win_amount, result_text = await play_roulette(bet, choice)
    
    if win:
        update_balance(callback.from_user.id, win_amount)
    
    await callback.message.edit_text(
        f"{result_text}\n\n"
        f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await state.clear()
    await callback.answer()

@dp.message(GameStates.waiting_for_roulette_choice)
async def game_roulette_number(message: types.Message, state: FSMContext):
    try:
        number = int(message.text)
        if number < 0 or number > 36:
            await message.answer("❌ Введите число от 0 до 36!")
            return
        
        data = await state.get_data()
        bet = data.get('roulette_bet', 0)
        
        win, win_amount, result_text = await play_roulette(bet, "number", number)
        
        if win:
            update_balance(message.from_user.id, win_amount)
        
        await message.answer(
            f"{result_text}\n\n"
            f"💵 Новый баланс: {format_balance(get_user_balance(message.from_user.id))}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

# ========== ИГРА PLINKO ==========
@dp.callback_query(F.data == "game_plinko")
async def game_plinko_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎯 **PLINKO** 🎯\n\n"
        f"Правила: Шарик падает через гвозди\n"
        f"Выбери уровень риска:\n"
        f"🟢 Низкий - до x2\n"
        f"🟡 Средний - до x3\n"
        f"🔴 Высокий - до x10\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_plinko_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_plinko_bet)
async def game_plinko_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
            return
        
        await state.update_data(plinko_bet=bet)
        await message.answer(
            f"🎯 **PLINKO** 🎯\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Выберите уровень риска:",
            parse_mode="Markdown",
            reply_markup=plinko_keyboard()
        )
        await state.set_state(None)
        
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(F.data.startswith("plinko_"))
async def game_plinko_play(callback: CallbackQuery, state: FSMContext):
    risk = callback.data.split("_")[1]
    data = await state.get_data()
    bet = data.get('plinko_bet', 0)
    
    update_balance(callback.from_user.id, -bet)
    
    win, win_amount, result_text = await play_plinko(bet, risk)
    
    if win:
        update_balance(callback.from_user.id, win_amount)
    
    await callback.message.edit_text(
        f"{result_text}\n\n"
        f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await state.clear()
    await callback.answer()

# ========== КЕЙСЫ ==========
@dp.callback_query(F.data == "show_cases")
async def show_cases_list(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text(
            "❌ Для открытия кейсов необходимо подписаться на наши каналы!",
            reply_markup=get_subscription_keyboard()
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "🎁 **ВЫБЕРИ КЕЙС** 🎁\n\n"
        "Каждый кейс содержит уникальные предметы!\n"
        "Чем дороже кейс - тем ценнее предметы!",
        parse_mode="Markdown",
        reply_markup=cases_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("case_"))
async def open_case_handler(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.answer("❌ Вы не подписаны на каналы!", show_alert=True)
        return
    
    case_id = int(callback.data.split("_")[1])
    case = db.get_case(case_id)
    
    if not case or case.get('is_active', 1) != 1:
        await callback.answer("❌ Кейс не найден!", show_alert=True)
        return
    
    case_name = case['name']
    price = case['price']
    
    balance = get_user_balance(callback.from_user.id)
    if balance < price:
        await callback.answer(f"❌ Недостаточно средств! Нужно {price:.0f} {get_currency_name()}", show_alert=True)
        return
    
    update_balance(callback.from_user.id, -price)
    
    items = db.get_case_items(case_id)
    
    if not items:
        update_balance(callback.from_user.id, price)
        await callback.answer("❌ В кейсе нет предметов!", show_alert=True)
        return
    
    total_chance = sum(item['chance'] for item in items)
    rand = random.uniform(0, total_chance)
    cumulative = 0
    selected_item = None
    
    for item in items:
        cumulative += item['chance']
        if rand <= cumulative:
            selected_item = item
            break
    
    if selected_item:
        add_to_inventory(
            callback.from_user.id,
            selected_item['item_name'],
            selected_item['item_value'],
            selected_item['emoji'],
            selected_item['rarity'],
            case_name
        )
        
        db.update_user_stats(callback.from_user.id, price, 1)
        
        result_text = (
            f"🎉 **ВЫ ВЫИГРАЛИ!** 🎉\n\n"
            f"{selected_item['emoji']} **{selected_item['item_name']}**\n"
            f"{get_rarity_emoji(selected_item['rarity'])} Редкость: {selected_item['rarity']}\n"
            f"{get_currency()} Стоимость: {selected_item['item_value']} {get_currency_name()}\n\n"
            f"✨ Предмет добавлен в инвентарь!"
        )
        
        await callback.message.edit_text(
            result_text,
            parse_mode="Markdown",
            reply_markup=cases_keyboard()
        )
        await callback.answer(f"🎉 Вы выиграли {selected_item['item_name']}!")

# ========== БОНУС КЕЙСЫ ==========
@dp.callback_query(F.data == "show_bonus_cases")
async def show_bonus_cases(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.answer("❌ Подпишитесь на каналы!", show_alert=True)
        return
    
    bonuses = db.get_bonus_cases()
    if not bonuses:
        await callback.answer("😢 Бонусные кейсы временно недоступны!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🎁 **БОНУСНЫЕ КЕЙСЫ** 🎁\n\n"
        "Выберите бонусный кейс для получения награды!\n"
        "Каждый кейс можно получить раз в определенное время!",
        parse_mode="Markdown",
        reply_markup=bonus_cases_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("bonus_"))
async def open_bonus_case(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.answer("❌ Подпишитесь на каналы!", show_alert=True)
        return
    
    bonus_id = int(callback.data.split("_")[1])
    bonuses = db.get_bonus_cases()
    bonus = next((b for b in bonuses if b['id'] == bonus_id), None)
    
    if not bonus:
        await callback.answer("❌ Бонусный кейс не найден!", show_alert=True)
        return
    
    last_time = db.get_last_bonus_time(callback.from_user.id)
    now = int(datetime.now().timestamp())
    cooldown = bonus.get('cooldown', 86400)
    
    if now - last_time < cooldown:
        hours_left = (cooldown - (now - last_time)) // 3600
        minutes_left = ((cooldown - (now - last_time)) % 3600) // 60
        await callback.answer(f"⏰ Бонус доступен через {hours_left}ч {minutes_left}мин!", show_alert=True)
        return
    
    reward = random.randint(bonus['reward_min'], bonus['reward_max'])
    update_balance(callback.from_user.id, reward)
    db.update_bonus_time(callback.from_user.id)
    
    await callback.answer(f"🎁 Вы получили {reward} {get_currency_name()}!", show_alert=True)
    await callback.message.edit_text(
        f"🎁 **{bonus['name']}** 🎁\n\n"
        f"✨ {bonus['description']}\n\n"
        f"💰 Вы получили: {reward} {get_currency_name()}!\n\n"
        f"💵 Новый баланс: {format_balance(get_user_balance(callback.from_user.id))}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(callback.from_user.id)
    )

# ========== ИНВЕНТАРЬ И МАГАЗИН ==========
@dp.callback_query(F.data == "show_inventory")
async def show_inventory(callback: CallbackQuery):
    items = db.get_user_inventory(callback.from_user.id)
    
    if not items:
        await callback.answer("📦 Ваш инвентарь пуст!", show_alert=True)
        return
    
    text = "📦 **ВАШ ИНВЕНТАРЬ** 📦\n\n"
    total_value = 0
    for item in items[:20]:
        rarity_emoji = get_rarity_emoji(item['rarity'])
        text += f"{item['item_emoji']} **{item['item_name']}** {rarity_emoji}\n"
        text += f"   💰 {item['item_value']} {get_currency_name()} | 📦 {item['from_case']}\n\n"
        total_value += item['item_value']
    
    text += f"\n💰 Общая ценность инвентаря: {total_value:.0f} {get_currency_name()}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "show_shop")
async def show_shop(callback: CallbackQuery):
    payment_card = get_setting('payment_card')
    payment_phone = get_setting('payment_phone')
    coin_price = float(get_setting('coin_price_rub'))
    case_price = float(get_setting('case_price_rub'))
    cases = db.get_active_cases()
    
    text = "🏪 **МАГАЗИН** 🏪\n\n"
    text += "💎 **Пополнить баланс:**\n"
    text += f"💰 1000 {get_currency_name()} = {coin_price * 1000:.0f} руб\n"
    text += f"💰 5000 {get_currency_name()} = {coin_price * 5000:.0f} руб\n"
    text += f"💰 10000 {get_currency_name()} = {coin_price * 10000:.0f} руб\n\n"
    
    text += "🎁 **Купить кейсы за рубли:**\n"
    for case in cases:
        text += f"📦 {case['name']} = {case_price:.0f} руб\n"
    
    text += "\n💳 **Реквизиты для оплаты:**\n"
    if payment_card:
        text += f"💳 Карта: `{payment_card}`\n"
    if payment_phone:
        text += f"📱 Телефон: `{payment_phone}`\n"
    
    text += "\n📝 **Как купить?**\n"
    text += "1. Переведите сумму на указанные реквизиты\n"
    text += "2. Напишите @support с чеком\n"
    text += "3. Укажите, что хотите купить (монеты или кейс)\n\n"
    text += f"🆘 Поддержка: {get_setting('support_contact')}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    support_contact = get_setting('support_contact')
    await callback.message.edit_text(
        f"🆘 **ПОДДЕРЖКА** 🆘\n\n"
        f"По всем вопросам обращайтесь:\n"
        f"{support_contact}\n\n"
        f"✅ Вопросы по оплате\n"
        f"✅ Проблемы с ботом\n"
        f"✅ Сотрудничество\n"
        f"✅ Предложения",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "check_sub")
async def check_sub(callback: CallbackQuery):
    if await check_subscriptions(callback.from_user.id):
        await callback.message.edit_text(
            "✅ Подписка подтверждена!\nВозвращаемся в меню...",
            reply_markup=main_keyboard(callback.from_user.id)
        )
    else:
        await callback.answer("❌ Вы не подписаны на все каналы!", show_alert=True)

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⚙️ **АДМИН ПАНЕЛЬ** ⚙️\n\nВыберите действие:",
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_cases")
async def admin_cases_menu(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📦 **УПРАВЛЕНИЕ КЕЙСАМИ** 📦",
        parse_mode="Markdown",
        reply_markup=admin_cases_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_create_case")
async def admin_create_case(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("📝 Введите название кейса:")
    await state.set_state(AdminStates.waiting_for_case_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_case_name)
async def create_case_name(message: types.Message, state: FSMContext):
    await state.update_data(case_name=message.text)
    await message.answer("💰 Введите цену кейса в монетах (число):")
    await state.set_state(AdminStates.waiting_for_case_price)

@dp.message(AdminStates.waiting_for_case_price)
async def create_case_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(case_price=price)
        await message.answer("📝 Введите описание кейса:")
        await state.set_state(AdminStates.waiting_for_case_desc)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_case_desc)
async def create_case_desc(message: types.Message, state: FSMContext):
    await state.update_data(case_desc=message.text)
    data = await state.get_data()
    
    case_id = db.add_case(data['case_name'], data['case_price'], data['case_desc'])
    
    await state.update_data(current_case_id=case_id)
    await message.answer(
        f"✅ Кейс '{data['case_name']}' создан!\n\n"
        f"Теперь добавьте предметы.\n"
        f"Введите название предмета:"
    )
    await state.set_state(AdminStates.waiting_for_item_name)

@dp.message(AdminStates.waiting_for_item_name)
async def add_item_name(message: types.Message, state: FSMContext):
    await state.update_data(item_name=message.text)
    await message.answer("💰 Введите стоимость предмета в монетах (число):")
    await state.set_state(AdminStates.waiting_for_item_value)

@dp.message(AdminStates.waiting_for_item_value)
async def add_item_value(message: types.Message, state: FSMContext):
    try:
        value = float(message.text)
        await state.update_data(item_value=value)
        await message.answer("🎲 Введите шанс выпадения (от 1 до 100):")
        await state.set_state(AdminStates.waiting_for_item_chance)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_item_chance)
async def add_item_chance(message: types.Message, state: FSMContext):
    try:
        chance = float(message.text)
        await state.update_data(item_chance=chance)
        await message.answer("⭐ Выберите редкость предмета:\n\n"
                            "1 - Обычный\n"
                            "2 - Необычный\n"
                            "3 - Редкий\n"
                            "4 - Эпический\n"
                            "5 - Легендарный\n"
                            "6 - Мифический\n\n"
                            "Введите цифру от 1 до 6:")
        await state.set_state(AdminStates.waiting_for_item_rarity)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_item_rarity)
async def add_item_rarity(message: types.Message, state: FSMContext):
    rarities = {
        "1": "Обычный",
        "2": "Необычный",
        "3": "Редкий",
        "4": "Эпический",
        "5": "Легендарный",
        "6": "Мифический"
    }
    
    rarity = rarities.get(message.text)
    if not rarity:
        await message.answer("❌ Введите цифру от 1 до 6!")
        return
    
    await state.update_data(item_rarity=rarity)
    await message.answer("🎨 Введите эмодзи для предмета (например: ⚔️, 🛡️, 💎):")
    await state.set_state(AdminStates.waiting_for_item_emoji)

@dp.message(AdminStates.waiting_for_item_emoji)
async def add_item_emoji(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    db.add_case_item(
        data['current_case_id'],
        data['item_name'],
        data['item_value'],
        data['item_chance'],
        data['item_rarity'],
        message.text
    )
    
    await message.answer(
        f"✅ Предмет '{data['item_name']}' добавлен!\n\n"
        f"Хотите добавить еще предмет? (да/нет)"
    )
    await state.set_state(None)
    
    @dp.message(lambda m: m.text.lower() in ['да', 'нет'])
    async def answer_continue(msg: types.Message):
        if msg.text.lower() == 'да':
            await state.set_state(AdminStates.waiting_for_item_name)
            await msg.answer("Введите название следующего предмета:")
        else:
            await msg.answer("✅ Создание кейса завершено!", reply_markup=admin_keyboard())
            await state.clear()

@dp.callback_query(F.data == "admin_list_cases")
async def admin_list_cases(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    cases = db.get_cases()
    
    if not cases:
        await callback.answer("Нет созданных кейсов!", show_alert=True)
        return
    
    text = "📋 **СПИСОК КЕЙСОВ**\n\n"
    for case in cases:
        items = db.get_case_items(case['id'])
        text += f"ID: {case['id']} | {case['name']}\n"
        text += f"   💰 Цена: {case['price']} {get_currency_name()}\n"
        text += f"   📦 Предметов: {len(items)}\n\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_bonus_cases")
async def admin_bonus_cases(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Создать бонус кейс", callback_data="admin_create_bonus")
    builder.button(text="🗑 Удалить бонус кейс", callback_data="admin_delete_bonus")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    bonuses = db.get_bonus_cases()
    text = "🎁 **БОНУСНЫЕ КЕЙСЫ**\n\n"
    
    if bonuses:
        for bonus in bonuses:
            text += f"ID: {bonus['id']} | {bonus['name']}\n"
            text += f"   🎁 Награда: {bonus['reward_min']}-{bonus['reward_max']} {get_currency_name()}\n"
            text += f"   ⏰ Кд: {bonus['cooldown'] // 3600} часов\n\n"
    else:
        text += "Нет созданных бонус кейсов"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_create_bonus")
async def admin_create_bonus(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("🎁 Введите название бонус кейса:")
    await state.set_state(AdminStates.waiting_for_bonus_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_bonus_name)
async def create_bonus_name(message: types.Message, state: FSMContext):
    await state.update_data(bonus_name=message.text)
    await message.answer("📝 Введите описание бонус кейса:")
    await state.set_state(AdminStates.waiting_for_bonus_desc)

@dp.message(AdminStates.waiting_for_bonus_desc)
async def create_bonus_desc(message: types.Message, state: FSMContext):
    await state.update_data(bonus_desc=message.text)
    await message.answer("💰 Введите минимальную награду (число):")
    await state.set_state(AdminStates.waiting_for_bonus_min)

@dp.message(AdminStates.waiting_for_bonus_min)
async def create_bonus_min(message: types.Message, state: FSMContext):
    try:
        reward_min = float(message.text)
        await state.update_data(bonus_min=reward_min)
        await message.answer("💰 Введите максимальную награду (число):")
        await state.set_state(AdminStates.waiting_for_bonus_max)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_bonus_max)
async def create_bonus_max(message: types.Message, state: FSMContext):
    try:
        reward_max = float(message.text)
        await state.update_data(bonus_max=reward_max)
        await message.answer("⏰ Введите задержку в часах (например: 24):")
        await state.set_state(AdminStates.waiting_for_bonus_cooldown)
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_bonus_cooldown)
async def create_bonus_cooldown(message: types.Message, state: FSMContext):
    try:
        hours = float(message.text)
        cooldown = hours * 3600
        data = await state.get_data()
        
        db.add_bonus_case(
            data['bonus_name'],
            data['bonus_desc'],
            data['bonus_min'],
            data['bonus_max'],
            cooldown
        )
        
        await message.answer(f"✅ Бонус кейс '{data['bonus_name']}' создан!", reply_markup=admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.callback_query(F.data == "admin_delete_bonus")
async def admin_delete_bonus(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("🗑 Введите ID бонус кейса для удаления:")
    await state.set_state(None)
    
    @dp.message()
    async def delete_bonus(msg: types.Message):
        try:
            bonus_id = int(msg.text)
            db.remove_bonus_case(bonus_id)
            await msg.answer(f"✅ Бонус кейс ID {bonus_id} удален!", reply_markup=admin_keyboard())
        except:
            await msg.answer("❌ Ошибка! Введите корректный ID")

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("📢 Введите текст для рассылки (можно с Markdown):")
    await state.set_state(AdminStates.waiting_for_broadcast_text)
    await callback.answer()

@dp.message(AdminStates.waiting_for_broadcast_text)
async def send_broadcast(message: types.Message, state: FSMContext):
    text = message.text
    users = db.get_users()
    
    success = 0
    fail = 0
    
    status_msg = await message.answer(f"📢 Начинаю рассылку для {len(users)} пользователей...")
    
    for user_id in users:
        try:
            await bot.send_message(int(user_id), text, parse_mode="Markdown")
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {fail}")
    await state.clear()

@dp.callback_query(F.data == "admin_payment")
async def admin_payment(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💳 Номер карты", callback_data="admin_set_card")
    builder.button(text="📱 Номер телефона", callback_data="admin_set_phone")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    await callback.message.edit_text(
        "💳 **НАСТРОЙКА ОПЛАТЫ** 💳",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_card")
async def admin_set_card(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💳 Введите номер карты:")
    await state.set_state(AdminStates.waiting_for_payment_card)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_card)
async def save_card(message: types.Message, state: FSMContext):
    db.set_setting('payment_card', message.text)
    await message.answer("✅ Номер карты сохранен!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_set_phone")
async def admin_set_phone(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📱 Введите номер телефона:")
    await state.set_state(AdminStates.waiting_for_payment_phone)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_phone)
async def save_phone(message: types.Message, state: FSMContext):
    db.set_setting('payment_phone', message.text)
    await message.answer("✅ Номер телефона сохранен!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_currency")
async def admin_currency(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐ Символ валюты", callback_data="admin_set_symbol")
    builder.button(text="📝 Название валюты", callback_data="admin_set_name")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    await callback.message.edit_text(
        f"⭐ **ТЕКУЩАЯ ВАЛЮТА** ⭐\n\n"
        f"Символ: {get_currency()}\n"
        f"Название: {get_currency_name()}\n\n"
        f"Выберите что изменить:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_symbol")
async def admin_set_symbol(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("⭐ Введите символ валюты (например: ⭐, $, €, 🪙):")
    await state.set_state(AdminStates.waiting_for_currency_symbol)
    await callback.answer()

@dp.callback_query(F.data == "admin_set_name")
async def admin_set_name(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите название валюты (например: монет, кристаллов):")
    await state.set_state(AdminStates.waiting_for_currency_name)
    await callback.answer()

@dp.message(AdminStates.waiting_for_currency_symbol)
async def save_currency_symbol(message: types.Message, state: FSMContext):
    db.set_setting('currency_symbol', message.text)
    await message.answer(f"✅ Символ валюты изменен на {message.text}!", reply_markup=admin_keyboard())
    await state.clear()

@dp.message(AdminStates.waiting_for_currency_name)
async def save_currency_name(message: types.Message, state: FSMContext):
    db.set_setting('currency_name', message.text)
    await message.answer(f"✅ Название валюты изменено на {message.text}!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_prices")
async def admin_prices(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💎 Цена монет", callback_data="admin_set_coin_price")
    builder.button(text="🎁 Цена кейсов", callback_data="admin_set_case_price")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    coin_price = float(get_setting('coin_price_rub'))
    case_price = float(get_setting('case_price_rub'))
    
    await callback.message.edit_text(
        f"💵 **ЦЕНЫ В РУБЛЯХ** 💵\n\n"
        f"💰 1 {get_currency_name()} = {coin_price:.2f} руб\n"
        f"📦 1 кейс = {case_price:.0f} руб\n\n"
        f"Выберите что изменить:",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_coin_price")
async def admin_set_coin_price(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Введите цену за 1 монету в рублях (например: 0.5):")
    await state.set_state(AdminStates.waiting_for_coin_price)
    await callback.answer()

@dp.callback_query(F.data == "admin_set_case_price")
async def admin_set_case_price(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🎁 Введите цену за 1 кейс в рублях (например: 50):")
    await state.set_state(AdminStates.waiting_for_case_price_rub)
    await callback.answer()

@dp.message(AdminStates.waiting_for_coin_price)
async def save_coin_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        db.set_setting('coin_price_rub', str(price))
        await message.answer(f"✅ Цена монет изменена! 1 монета = {price:.2f} руб", reply_markup=admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.message(AdminStates.waiting_for_case_price_rub)
async def save_case_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        db.set_setting('case_price_rub', str(price))
        await message.answer(f"✅ Цена кейсов изменена! 1 кейс = {price:.0f} руб", reply_markup=admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("💰 Введите ID пользователя и сумму монет через пробел:\nПример: 123456789 1000")
    await state.set_state(AdminStates.waiting_for_add_balance)
    await callback.answer()

@dp.message(AdminStates.waiting_for_add_balance)
async def add_balance_admin(message: types.Message, state: FSMContext):
    try:
        parts = message.text.split()
        user_id = int(parts[0])
        amount = float(parts[1])
        
        update_balance(user_id, amount)
        
        await message.answer(f"✅ Пользователю {user_id} добавлено {amount:.0f} {get_currency_name()}!")
        
        try:
            await bot.send_message(user_id, f"🎉 Администратор добавил вам {amount:.0f} {get_currency_name()} на баланс!")
        except:
            pass
    except:
        await message.answer("❌ Ошибка! Используйте формат: ID Сумма")
    
    await state.clear()

@dp.callback_query(F.data == "admin_games")
async def admin_games(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer(
        "🎮 **НАСТРОЙКА ИГР** 🎮\n\n"
        "Введите минимальную и максимальную ставку через пробел:\n"
        "Пример: 10 1000"
    )
    
    @dp.message(lambda m: m.text and (' ' in m.text))
    async def set_game_limits(msg: types.Message):
        try:
            parts = msg.text.split()
            min_bet = float(parts[0])
            max_bet = float(parts[1])
            
            db.set_setting('casino_min_bet', str(min_bet))
            db.set_setting('casino_max_bet', str(max_bet))
            
            await msg.answer(f"✅ Настройки сохранены!\nМинимальная ставка: {min_bet:.0f}\nМаксимальная ставка: {max_bet:.0f}", 
                           reply_markup=admin_keyboard())
        except:
            await msg.answer("❌ Ошибка! Введите два числа через пробел")

@dp.callback_query(F.data == "admin_channels")
async def admin_channels(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить канал", callback_data="admin_add_channel")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    channels = db.get_channels()
    text = "📢 **ОБЯЗАТЕЛЬНЫЕ ПОДПИСКИ**\n\n"
    
    if channels:
        for channel in channels:
            text += f"• {channel['channel_name']}\n"
            text += f"  🔗 {channel['channel_url']}\n\n"
    else:
        text += "Нет обязательных подписок"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_add_channel")
async def admin_add_channel(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📢 Введите ID канала (например: @channel):")
    await state.set_state(AdminStates.waiting_for_channel_id)
    await callback.answer()

@dp.message(AdminStates.waiting_for_channel_id)
async def add_channel_id(message: types.Message, state: FSMContext):
    await state.update_data(channel_id=message.text)
    await message.answer("📝 Введите название канала:")
    await state.set_state(AdminStates.waiting_for_channel_name)

@dp.message(AdminStates.waiting_for_channel_name)
async def add_channel_name(message: types.Message, state: FSMContext):
    await state.update_data(channel_name=message.text)
    await message.answer("🔗 Введите ссылку на канал (например: https://t.me/channel):")
    await state.set_state(AdminStates.waiting_for_channel_url)

@dp.message(AdminStates.waiting_for_channel_url)
async def add_channel_url(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db.add_channel(data['channel_id'], data['channel_name'], message.text)
    await message.answer("✅ Канал добавлен!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    total_users = db.get_total_users()
    total_spent = db.get_total_spent()
    total_opened = db.get_total_opened()
    total_balance = db.get_total_balance()
    
    text = f"📊 **СТАТИСТИКА БОТА** 📊\n\n"
    text += f"👥 Пользователей: {total_users}\n"
    text += f"💰 Всего потрачено: {total_spent:.0f} {get_currency_name()}\n"
    text += f"🎁 Открыто кейсов: {total_opened}\n"
    text += f"💎 Баланс пользователей: {total_balance:.0f} {get_currency_name()}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("=" * 50)
    print("🤖 СОВРЕМЕННЫЙ БОТ КАЗИНО ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎮 5 современных игр:")
    print("   ✈️ Crash - летающий самолет")
    print("   🗼 Tower - башня с риском")
    print("   💣 Mines - минное поле")
    print("   🎡 Рулетка - классическая")
    print("   🎯 Plinko - падающий шарик")
    print(f"⭐ Валюта: {get_currency()} {get_currency_name()}")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())