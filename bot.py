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
            'requests': [],
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
                'shop_message': '🏪 Добро пожаловать в магазин!\n\nВы можете пополнить баланс или купить кейсы.\n\n💰 1000 монет = 50 руб\n🎁 Кейс = 100 руб\n\nПосле оплаты отправьте скриншот в поддержку!',
                'request_message': '📝 Опишите вашу проблему или вопрос:'
            },
            'required_channels': [],
            'bonus_cases': [],
            'next_case_id': 1,
            'next_item_id': 1,
            'next_inventory_id': 1,
            'next_bonus_id': 1,
            'next_request_id': 1
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
    
    def add_request(self, user_id, username, text):
        request_id = self.data['next_request_id']
        self.data['requests'].append({
            'id': request_id,
            'user_id': user_id,
            'username': username,
            'text': text,
            'status': 'pending',
            'created_at': int(datetime.now().timestamp())
        })
        self.data['next_request_id'] += 1
        self.save_data()
        return request_id
    
    def get_requests(self, status=None):
        if status:
            return [r for r in self.data['requests'] if r['status'] == status]
        return self.data['requests']
    
    def update_request_status(self, request_id, status):
        for req in self.data['requests']:
            if req['id'] == request_id:
                req['status'] = status
                self.save_data()
                return True
        return False
    
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
    waiting_for_shop_message = State()
    waiting_for_request_message = State()

class GameStates(StatesGroup):
    waiting_for_coin_bet = State()
    waiting_for_dice_bet = State()
    waiting_for_card_bet = State()
    waiting_for_card_choice = State()
    waiting_for_number_bet = State()
    waiting_for_number_choice = State()

class RequestStates(StatesGroup):
    waiting_for_request_text = State()

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

# ========== ПРОСТЫЕ ПОНЯТНЫЕ ИГРЫ ==========

# ИГРА 1: ОРЁЛ-РЕШКА
async def play_coinflip(bet: float, choice: str) -> Tuple[bool, float, str]:
    result = random.choice(["орел", "решка"])
    result_text = f"🪙 Монетка упала стороной: **{result}**\n\n"
    
    if choice == result:
        win_amount = bet * 1.9
        result_text += f"🎉 ПОБЕДА! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        result_text += f"😢 ПРОИГРЫШ! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text

# ИГРА 2: КОСТИ (Кто больше)
async def play_dice(bet: float) -> Tuple[bool, float, str]:
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    result_text = f"🎲 Ваш бросок: **{user_roll}**\n🎲 Бросок бота: **{bot_roll}**\n\n"
    
    if user_roll > bot_roll:
        win_amount = bet * 2
        result_text += f"🎉 ВЫ ПОБЕДИЛИ! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    elif user_roll < bot_roll:
        result_text += f"😢 ВЫ ПРОИГРАЛИ! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text
    else:
        result_text += f"🤝 НИЧЬЯ! Ставка возвращена"
        return True, bet, result_text

# ИГРА 3: КАРТЫ (Выше/Ниже)
async def play_cards(bet: float, choice: str) -> Tuple[bool, float, str, int, int]:
    user_card = random.randint(2, 14)
    bot_card = random.randint(2, 14)
    
    card_names = {11: "Валет", 12: "Дама", 13: "Король", 14: "Туз"}
    user_name = card_names.get(user_card, str(user_card))
    bot_name = card_names.get(bot_card, str(bot_card))
    
    result_text = f"🃏 Ваша карта: **{user_name}**\n🃏 Карта бота: **{bot_name}**\n\n"
    
    win = False
    win_amount = 0
    
    if choice == "higher" and user_card > bot_card:
        win = True
        win_amount = bet * 1.8
        result_text += f"🎉 ВЕРНО! Ваша карта выше! +{win_amount:.0f} {get_currency_name()}"
    elif choice == "lower" and user_card < bot_card:
        win = True
        win_amount = bet * 1.8
        result_text += f"🎉 ВЕРНО! Ваша карта ниже! +{win_amount:.0f} {get_currency_name()}"
    elif user_card == bot_card:
        win = True
        win_amount = bet
        result_text += f"🤝 НИЧЬЯ! Ставка возвращена"
    else:
        result_text += f"😢 НЕВЕРНО! -{bet:.0f} {get_currency_name()}"
    
    return win, win_amount, result_text, user_card, bot_card

# ИГРА 4: УГАДАЙ ЧИСЛО
async def guess_number(bet: float, guess: int) -> Tuple[bool, float, str]:
    secret = random.randint(1, 10)
    result_text = f"🔢 Ваше число: **{guess}**\n🔢 Загаданное число: **{secret}**\n\n"
    
    if guess == secret:
        win_amount = bet * 3
        result_text += f"🎉 ТОЧНОЕ ПОПАДАНИЕ! x3! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    elif abs(guess - secret) <= 2:
        win_amount = bet * 1.5
        result_text += f"👍 БЛИЗКО! x1.5! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        result_text += f"😢 НЕ УГАДАЛИ! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text

# ИГРА 5: СЛОТЫ
async def play_slots(bet: float) -> Tuple[bool, float, str]:
    symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "💎", "7️⃣"]
    reel1 = random.choice(symbols)
    reel2 = random.choice(symbols)
    reel3 = random.choice(symbols)
    
    result_text = f"🎰 | {reel1} | {reel2} | {reel3} | 🎰\n\n"
    
    win_multiplier = 0
    if reel1 == reel2 == reel3:
        if reel1 == "7️⃣":
            win_multiplier = 10
            result_text += "🌟 ДЖЕКПОТ! Три семерки! x10 🌟"
        elif reel1 == "💎":
            win_multiplier = 7
            result_text += "💎 Три алмаза! x7 💎"
        elif reel1 == "⭐":
            win_multiplier = 5
            result_text += "⭐ Три звезды! x5 ⭐"
        else:
            win_multiplier = 3
            result_text += "🎉 Три одинаковых! x3 🎉"
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        win_multiplier = 1.5
        result_text += "👍 Два одинаковых! x1.5 👍"
    else:
        result_text += "😢 НЕТ СОВПАДЕНИЙ"
    
    if win_multiplier > 0:
        win_amount = bet * win_multiplier
        result_text += f"\n\n💰 Выигрыш: {win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        result_text += f"\n\n😢 Вы проиграли {bet:.0f} {get_currency_name()}"
        return False, 0, result_text

# ========== КЛАВИАТУРЫ ==========
def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Кейсы", callback_data="show_cases")
    builder.button(text="💰 Баланс", callback_data="show_balance")
    builder.button(text="📦 Инвентарь", callback_data="show_inventory")
    builder.button(text="🎮 Игры", callback_data="show_games")
    builder.button(text="🏪 Магазин", callback_data="show_shop")
    builder.button(text="🎁 Бонус", callback_data="show_bonus_cases")
    builder.button(text="📝 Заявка", callback_data="make_request")
    builder.button(text="🆘 Поддержка", callback_data="support")
    if is_admin(user_id):
        builder.button(text="⚙️ Админ", callback_data="admin_panel")
    builder.adjust(2)
    return builder.as_markup()

def games_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🪙 Орёл-Решка", callback_data="game_coin")
    builder.button(text="🎲 Кости", callback_data="game_dice")
    builder.button(text="🃏 Карты (Выше/Ниже)", callback_data="game_cards")
    builder.button(text="🔢 Угадай число", callback_data="game_number")
    builder.button(text="🎰 Слоты", callback_data="game_slots")
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
    builder.button(text="💳 Настройка оплаты", callback_data="admin_payment")
    builder.button(text="💰 Выдать монеты", callback_data="admin_add_balance")
    builder.button(text="⭐ Настройка валюты", callback_data="admin_currency")
    builder.button(text="💵 Цены в рублях", callback_data="admin_prices")
    builder.button(text="📝 Настройка сообщений", callback_data="admin_messages")
    builder.button(text="📢 Подписки", callback_data="admin_channels")
    builder.button(text="📋 Заявки", callback_data="admin_requests")
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

def coinflip_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🪨 Орел", callback_data="coin_orel")
    builder.button(text="📄 Решка", callback_data="coin_reshka")
    builder.button(text="🔙 Назад", callback_data="show_games")
    builder.adjust(2)
    return builder.as_markup()

def cards_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬆️ Выше", callback_data="card_higher")
    builder.button(text="⬇️ Ниже", callback_data="card_lower")
    builder.button(text="🔙 Назад", callback_data="show_games")
    builder.adjust(2)
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
        f"🎮 Простые и понятные игры ждут тебя!\n"
        f"🪙 Орёл-Решка | 🎲 Кости | 🃏 Карты | 🔢 Угадай число | 🎰 Слоты\n\n"
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
        "🎮 **ВЫБЕРИ ИГРУ** 🎮\n\n"
        "🪙 **Орёл-Решка** - Угадай сторону монетки (x1.9)\n"
        "🎲 **Кости** - Кто больше выбросит (x2)\n"
        "🃏 **Карты** - Угадай, выше или ниже карта бота (x1.8)\n"
        "🔢 **Угадай число** - Угадай число от 1 до 10 (до x3)\n"
        "🎰 **Слоты** - Классические слоты (до x10)\n\n"
        f"💰 Ставки от {float(get_setting('casino_min_bet')):.0f} до {float(get_setting('casino_max_bet')):.0f} {get_currency_name()}",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await callback.answer()

# ========== ИГРА ОРЁЛ-РЕШКА ==========
@dp.callback_query(F.data == "game_coin")
async def game_coin_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🪙 **ОРЁЛ-РЕШКА** 🪙\n\n"
        f"Правила: Угадайте, какой стороной упадет монетка\n"
        f"Выигрыш: x1.9 от ставки\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_coin_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_coin_bet)
async def game_coin_bet(message: types.Message, state: FSMContext):
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
        
        await state.update_data(coin_bet=bet)
        await message.answer(
            f"🪙 **ОРЁЛ-РЕШКА** 🪙\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Выберите сторону:",
            parse_mode="Markdown",
            reply_markup=coinflip_keyboard()
        )
        await state.set_state(GameStates.waiting_for_card_choice)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_card_choice, F.data.startswith("coin_"))
async def game_coin_play(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('coin_bet', 0)
    
    choice = "орел" if callback.data == "coin_orel" else "решка"
    
    update_balance(callback.from_user.id, -bet)
    
    win, win_amount, result_text = await play_coinflip(bet, choice)
    
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

# ========== ИГРА КОСТИ ==========
@dp.callback_query(F.data == "game_dice")
async def game_dice_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎲 **КОСТИ** 🎲\n\n"
        f"Правила: Вы и бот бросаете кубик\n"
        f"У кого больше очков - тот победил\n"
        f"Выигрыш: x2 от ставки\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_dice_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_dice_bet)
async def game_dice_play(message: types.Message, state: FSMContext):
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
        
        win, win_amount, result_text = await play_dice(bet)
        
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

# ========== ИГРА КАРТЫ ==========
@dp.callback_query(F.data == "game_cards")
async def game_cards_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🃏 **КАРТЫ (ВЫШЕ/НИЖЕ)** 🃏\n\n"
        f"Правила: Вам выпадает карта\n"
        f"Угадайте, будет ли карта бота выше или ниже\n"
        f"Выигрыш: x1.8 от ставки\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_card_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_card_bet)
async def game_cards_bet(message: types.Message, state: FSMContext):
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
        
        await state.update_data(card_bet=bet)
        await message.answer(
            f"🃏 **КАРТЫ** 🃏\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Ваша карта будет сыграна автоматически!\n"
            f"Угадайте, будет ли карта бота ВЫШЕ или НИЖЕ:",
            parse_mode="Markdown",
            reply_markup=cards_keyboard()
        )
        await state.set_state(GameStates.waiting_for_card_choice)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_card_choice, F.data.startswith("card_"))
async def game_cards_play(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('card_bet', 0)
    
    choice = "higher" if callback.data == "card_higher" else "lower"
    
    update_balance(callback.from_user.id, -bet)
    
    win, win_amount, result_text, user_card, bot_card = await play_cards(bet, choice)
    
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

# ========== ИГРА УГАДАЙ ЧИСЛО ==========
@dp.callback_query(F.data == "game_number")
async def game_number_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🔢 **УГАДАЙ ЧИСЛО** 🔢\n\n"
        f"Правила: Загадано число от 1 до 10\n"
        f"Точное попадание - x3\n"
        f"Отклонение до 2 - x1.5\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_number_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_number_bet)
async def game_number_bet(message: types.Message, state: FSMContext):
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
        
        await state.update_data(number_bet=bet)
        await message.answer(
            f"🔢 **УГАДАЙ ЧИСЛО** 🔢\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Введите число от 1 до 10:",
            parse_mode="Markdown"
        )
        await state.set_state(GameStates.waiting_for_number_choice)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.message(GameStates.waiting_for_number_choice)
async def game_number_play(message: types.Message, state: FSMContext):
    try:
        guess = int(message.text)
        if guess < 1 or guess > 10:
            await message.answer("❌ Введите число от 1 до 10!")
            return
        
        data = await state.get_data()
        bet = data.get('number_bet', 0)
        
        update_balance(message.from_user.id, -bet)
        
        win, win_amount, result_text = await guess_number(bet, guess)
        
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

# ========== ИГРА СЛОТЫ ==========
@dp.callback_query(F.data == "game_slots")
async def game_slots_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎰 **СЛОТЫ** 🎰\n\n"
        f"Правила: Выпадают 3 символа\n"
        f"2 одинаковых - x1.5\n"
        f"3 одинаковых - x3\n"
        f"3 звезды - x5\n"
        f"3 алмаза - x7\n"
        f"3 семерки - x10 (ДЖЕКПОТ!)\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(None)
    
    @dp.message()
    async def play_slots_game(msg: types.Message):
        try:
            bet = float(msg.text)
            min_bet = float(get_setting('casino_min_bet'))
            max_bet = float(get_setting('casino_max_bet'))
            
            if bet < min_bet or bet > max_bet:
                await msg.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
                return
            
            balance = get_user_balance(msg.from_user.id)
            if balance < bet:
                await msg.answer(f"❌ Недостаточно средств! Ваш баланс: {format_balance(balance)}")
                return
            
            update_balance(msg.from_user.id, -bet)
            
            win, win_amount, result_text = await play_slots(bet)
            
            if win:
                update_balance(msg.from_user.id, win_amount)
            
            await msg.answer(
                f"{result_text}\n\n"
                f"💵 Новый баланс: {format_balance(get_user_balance(msg.from_user.id))}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
            await state.clear()
        except ValueError:
            await msg.answer("❌ Введите число!")

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

# ========== ИНВЕНТАРЬ ==========
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

# ========== МАГАЗИН ==========
@dp.callback_query(F.data == "show_shop")
async def show_shop(callback: CallbackQuery):
    shop_message = get_setting('shop_message')
    payment_card = get_setting('payment_card')
    payment_phone = get_setting('payment_phone')
    
    text = shop_message + "\n\n"
    
    if payment_card:
        text += f"💳 Карта: `{payment_card}`\n"
    if payment_phone:
        text += f"📱 Телефон: `{payment_phone}`\n"
    
    text += f"\n🆘 Поддержка: {get_setting('support_contact')}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить 1000 монет", callback_data="buy_coins_1000")],
            [InlineKeyboardButton(text="💰 Пополнить 5000 монет", callback_data="buy_coins_5000")],
            [InlineKeyboardButton(text="💰 Пополнить 10000 монет", callback_data="buy_coins_10000")],
            [InlineKeyboardButton(text="🆘 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_coins_"))
async def buy_coins(callback: CallbackQuery):
    amount = int(callback.data.split("_")[2])
    coin_price = float(get_setting('coin_price_rub'))
    total_rub = amount * coin_price
    
    payment_card = get_setting('payment_card')
    payment_phone = get_setting('payment_phone')
    
    text = f"💎 **ПОКУПКА {amount} МОНЕТ** 💎\n\n"
    text += f"💰 Сумма к оплате: {total_rub:.0f} руб\n\n"
    text += "📝 **Инструкция:**\n"
    text += "1. Переведите сумму на реквизиты ниже\n"
    text += "2. Нажмите кнопку '✅ Я оплатил'\n"
    text += "3. Отправьте скриншот чека\n\n"
    text += "💳 **Реквизиты:**\n"
    if payment_card:
        text += f"💳 Карта: `{payment_card}`\n"
    if payment_phone:
        text += f"📱 Телефон: `{payment_phone}`\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"paid_{amount}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="show_shop")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("paid_"))
async def paid_handler(callback: CallbackQuery, state: FSMContext):
    amount = int(callback.data.split("_")[1])
    await state.update_data(pending_coins=amount)
    
    await callback.message.edit_text(
        f"📝 **ОТПРАВЬТЕ ЧЕК** 📝\n\n"
        f"Пожалуйста, отправьте скриншот или фото чека об оплате {amount} монет.\n"
        f"После проверки администратор начислит вам монеты.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="show_shop")]
        ])
    )
    await state.set_state(RequestStates.waiting_for_request_text)

# ========== ЗАЯВКИ ==========
@dp.callback_query(F.data == "make_request")
async def make_request(callback: CallbackQuery, state: FSMContext):
    request_message = get_setting('request_message')
    
    await callback.message.edit_text(
        f"📝 **СОЗДАНИЕ ЗАЯВКИ** 📝\n\n"
        f"{request_message}\n\n"
        f"Отправьте ваше сообщение:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Отмена", callback_data="back_to_main")]
        ])
    )
    await state.set_state(RequestStates.waiting_for_request_text)
    await callback.answer()

@dp.message(RequestStates.waiting_for_request_text)
async def process_request(message: types.Message, state: FSMContext):
    request_text = message.text
    user_id = message.from_user.id
    username = message.from_user.username or f"user{user_id}"
    
    request_id = db.add_request(user_id, username, request_text)
    
    await message.answer(
        f"✅ **ЗАЯВКА СОЗДАНА!** ✅\n\n"
        f"📝 Ваша заявка #{request_id} отправлена администратору.\n"
        f"⏰ Ожидайте ответа в ближайшее время.\n\n"
        f"Вы можете проверить статус заявки в админ-панели.",
        parse_mode="Markdown",
        reply_markup=main_keyboard(user_id)
    )
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"📋 **НОВАЯ ЗАЯВКА** 📋\n\n"
                f"🆔 ID: #{request_id}\n"
                f"👤 Пользователь: {username}\n"
                f"🆔 User ID: {user_id}\n"
                f"📝 Текст: {request_text}\n\n"
                f"Используйте кнопки для ответа:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="✅ Ответить", callback_data=f"reply_request_{request_id}")],
                    [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"close_request_{request_id}")]
                ])
            )
        except:
            pass
    
    await state.clear()

@dp.callback_query(F.data.startswith("reply_request_"))
async def reply_to_request(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    requests = db.get_requests(status="pending")
    request = next((r for r in requests if r['id'] == request_id), None)
    
    if not request:
        await callback.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    
    await state.update_data(reply_request_id=request_id, reply_user_id=request['user_id'])
    await callback.message.answer(
        f"📝 **ОТВЕТ НА ЗАЯВКУ #{request_id}**\n\n"
        f"Пользователь: {request['username']}\n"
        f"Текст заявки: {request['text']}\n\n"
        f"Введите ваш ответ:",
        parse_mode="Markdown"
    )
    await state.set_state(None)
    
    @dp.message()
    async def send_reply(msg: types.Message):
        data = await state.get_data()
        reply_user_id = data.get('reply_user_id')
        reply_request_id = data.get('reply_request_id')
        
        try:
            await bot.send_message(
                reply_user_id,
                f"📨 **ОТВЕТ НА ЗАЯВКУ #{reply_request_id}** 📨\n\n"
                f"{msg.text}\n\n"
                f"💬 Если остались вопросы, создайте новую заявку!",
                parse_mode="Markdown"
            )
            db.update_request_status(reply_request_id, "answered")
            await msg.answer(f"✅ Ответ отправлен пользователю!", reply_markup=admin_keyboard())
        except:
            await msg.answer("❌ Не удалось отправить ответ!", reply_markup=admin_keyboard())
        
        await state.clear()

@dp.callback_query(F.data.startswith("close_request_"))
async def close_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    db.update_request_status(request_id, "closed")
    
    await callback.message.edit_text(f"✅ Заявка #{request_id} закрыта!")
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
        f"✅ Предложения\n\n"
        f"📝 Или создайте заявку через меню!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Создать заявку", callback_data="make_request")],
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
        "💳 **НАСТРОЙКА ОПЛАТЫ** 💳\n\n"
        f"Текущие реквизиты:\n"
        f"💳 Карта: {get_setting('payment_card') or 'не указана'}\n"
        f"📱 Телефон: {get_setting('payment_phone') or 'не указан'}",
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
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    coin_price = float(get_setting('coin_price_rub'))
    
    await callback.message.edit_text(
        f"💵 **ЦЕНЫ В РУБЛЯХ** 💵\n\n"
        f"💰 1 {get_currency_name()} = {coin_price:.2f} руб\n"
        f"💰 1000 {get_currency_name()} = {coin_price * 1000:.0f} руб\n"
        f"💰 5000 {get_currency_name()} = {coin_price * 5000:.0f} руб\n"
        f"💰 10000 {get_currency_name()} = {coin_price * 10000:.0f} руб\n\n"
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

@dp.message(AdminStates.waiting_for_coin_price)
async def save_coin_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        db.set_setting('coin_price_rub', str(price))
        await message.answer(f"✅ Цена монет изменена! 1 монета = {price:.2f} руб", reply_markup=admin_keyboard())
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")

@dp.callback_query(F.data == "admin_messages")
async def admin_messages(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🏪 Текст магазина", callback_data="admin_set_shop_msg")
    builder.button(text="📝 Текст заявки", callback_data="admin_set_request_msg")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    
    await callback.message.edit_text(
        f"📝 **НАСТРОЙКА СООБЩЕНИЙ** 📝\n\n"
        f"Вы можете изменить текст сообщений:\n\n"
        f"🏪 Магазин - приветствие в магазине\n"
        f"📝 Заявка - текст при создании заявки\n\n"
        f"Текущий текст магазина:\n{get_setting('shop_message')[:100]}...\n\n"
        f"Текущий текст заявки:\n{get_setting('request_message')}",
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_set_shop_msg")
async def admin_set_shop_msg(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("🏪 Введите новый текст для магазина (можно с Markdown):")
    await state.set_state(AdminStates.waiting_for_shop_message)
    await callback.answer()

@dp.message(AdminStates.waiting_for_shop_message)
async def save_shop_message(message: types.Message, state: FSMContext):
    db.set_setting('shop_message', message.text)
    await message.answer("✅ Текст магазина обновлен!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_set_request_msg")
async def admin_set_request_msg(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("📝 Введите новый текст для создания заявки:")
    await state.set_state(AdminStates.waiting_for_request_message)
    await callback.answer()

@dp.message(AdminStates.waiting_for_request_message)
async def save_request_message(message: types.Message, state: FSMContext):
    db.set_setting('request_message', message.text)
    await message.answer("✅ Текст создания заявки обновлен!", reply_markup=admin_keyboard())
    await state.clear()

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

@dp.callback_query(F.data == "admin_requests")
async def admin_requests(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    requests = db.get_requests(status="pending")
    
    if not requests:
        await callback.answer("📋 Нет активных заявок!", show_alert=True)
        return
    
    text = "📋 **АКТИВНЫЕ ЗАЯВКИ** 📋\n\n"
    for req in requests:
        text += f"🆔 #{req['id']} | 👤 {req['username']}\n"
        text += f"📝 {req['text'][:50]}...\n\n"
    
    builder = InlineKeyboardBuilder()
    for req in requests[:10]:
        builder.button(text=f"Заявка #{req['id']}", callback_data=f"view_request_{req['id']}")
    builder.button(text="🔙 Назад", callback_data="admin_panel")
    builder.adjust(1)
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("view_request_"))
async def view_request(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    requests = db.get_requests(status="pending")
    request = next((r for r in requests if r['id'] == request_id), None)
    
    if not request:
        await callback.answer("❌ Заявка уже обработана!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📋 **ЗАЯВКА #{request['id']}** 📋\n\n"
        f"👤 Пользователь: {request['username']}\n"
        f"🆔 ID: {request['user_id']}\n"
        f"📝 Текст: {request['text']}\n"
        f"⏰ Время: {datetime.fromtimestamp(request['created_at']).strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Выберите действие:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Ответить", callback_data=f"reply_request_{request_id}")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data=f"close_request_{request_id}")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_requests")]
        ])
    )
    await callback.answer()

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
    pending_requests = len(db.get_requests(status="pending"))
    
    text = f"📊 **СТАТИСТИКА БОТА** 📊\n\n"
    text += f"👥 Пользователей: {total_users}\n"
    text += f"💰 Всего потрачено: {total_spent:.0f} {get_currency_name()}\n"
    text += f"🎁 Открыто кейсов: {total_opened}\n"
    text += f"💎 Баланс пользователей: {total_balance:.0f} {get_currency_name()}\n"
    text += f"📋 Активных заявок: {pending_requests}"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

# ========== ЗАПУСК ==========
async def main():
    print("=" * 60)
    print("🤖 ПРОСТОЙ И ПОНЯТНЫЙ БОТ КАЗИНО ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎮 5 простых игр:")
    print("   🪙 Орёл-Решка - угадай сторону монетки")
    print("   🎲 Кости - кто больше выбросит")
    print("   🃏 Карты - выше или ниже карта бота")
    print("   🔢 Угадай число - угадай число от 1 до 10")
    print("   🎰 Слоты - классические слоты")
    print(f"⭐ Валюта: {get_currency()} {get_currency_name()}")
    print("📝 Система заявок активна!")
    print("=" * 60)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())