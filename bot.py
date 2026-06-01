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
                'bonus_case_cooldown': '86400'
            },
            'required_channels': [],
            'next_case_id': 1,
            'next_item_id': 1,
            'next_inventory_id': 1
        }
        return data
    
    def get_users(self):
        return self.data['users']
    
    def get_user(self, user_id):
        return self.data['users'].get(str(user_id))
    
    def add_user(self, user_id, username, first_name):
        if str(user_id) not in self.data['users']:
            self.data['users'][str(user_id)] = {
                'user_id': user_id,
                'username': username,
                'first_name': first_name,
                'balance': 1000,
                'total_spent': 0,
                'total_opened': 0,
                'last_bonus_time': 0,
                'joined_date': int(datetime.now().timestamp()),
                'games_played': 0,
                'games_won': 0
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
        return 1000
    
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
            'is_sold': 0,
            'from_case': from_case
        })
        self.data['next_inventory_id'] += 1
        self.save_data()
    
    def get_user_inventory(self, user_id):
        return [item for item in self.data['user_inventory'] if item['user_id'] == user_id and item['is_sold'] == 0]
    
    def get_all_user_items(self, user_id):
        return [item for item in self.data['user_inventory'] if item['user_id'] == user_id and item['is_sold'] == 0]
    
    def sell_all_items(self, user_id):
        total = 0
        for item in self.data['user_inventory']:
            if item['user_id'] == user_id and item['is_sold'] == 0:
                total += item['item_value']
                item['is_sold'] = 1
        self.save_data()
        return total
    
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
    
    def get_total_users(self):
        return len(self.data['users'])
    
    def get_total_spent(self):
        return sum(user['total_spent'] for user in self.data['users'].values())
    
    def get_total_opened(self):
        return sum(user['total_opened'] for user in self.data['users'].values())
    
    def get_total_items(self):
        return len([item for item in self.data['user_inventory'] if item['is_sold'] == 0])
    
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
    waiting_for_channel_id = State()
    waiting_for_channel_name = State()
    waiting_for_channel_url = State()
    waiting_for_add_balance = State()

class GameStates(StatesGroup):
    waiting_for_slots_bet = State()
    waiting_for_dice_bet = State()
    waiting_for_rps_bet = State()
    waiting_for_rps_choice = State()
    waiting_for_number_bet = State()
    waiting_for_number_guess = State()
    waiting_for_blackjack_bet = State()
    waiting_for_blackjack_action = State()

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

# ========== КРАСИВОЕ ОТКРЫТИЕ КЕЙСА ==========
async def open_case_animation(message, case_name: str, items: List[Dict]) -> Tuple[Dict, str]:
    total_chance = sum(item['chance'] for item in items)
    rand = random.uniform(0, total_chance)
    cumulative = 0
    selected_item = None
    
    for item in items:
        cumulative += item['chance']
        if rand <= cumulative:
            selected_item = item
            break
    
    if not selected_item:
        selected_item = items[0]
    
    animation_frames = [
        "🎲 🎰 🎲",
        "✨ ⭐ ✨",
        "💫 🌟 💫"
    ]
    
    msg = await message.answer(
        f"🎁 Открываем кейс **{case_name}**...\n\n{animation_frames[0]}",
        parse_mode="Markdown"
    )
    
    await asyncio.sleep(0.5)
    await msg.edit_text(
        f"🎁 Открываем кейс **{case_name}**...\n\n{animation_frames[1]}",
        parse_mode="Markdown"
    )
    
    await asyncio.sleep(0.5)
    await msg.edit_text(
        f"🎁 Открываем кейс **{case_name}**...\n\n{animation_frames[2]}",
        parse_mode="Markdown"
    )
    
    await asyncio.sleep(0.5)
    
    rarity_emoji = get_rarity_emoji(selected_item['rarity'])
    result_text = (
        f"🎉 **ВЫ ВЫИГРАЛИ!** 🎉\n\n"
        f"{selected_item['emoji']} **{selected_item['item_name']}**\n"
        f"{rarity_emoji} Редкость: {selected_item['rarity']}\n"
        f"{get_currency()} Стоимость: {selected_item['item_value']} {get_currency_name()}\n\n"
        f"✨ Предмет добавлен в инвентарь!"
    )
    
    return selected_item, result_text

# ========== ИГРЫ ==========

async def play_slots(bet: float) -> Tuple[bool, float, str]:
    symbols = ["🍒", "🍋", "🍊", "🍉", "⭐", "💎", "7️⃣", "🎰"]
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
        result_text += "😢 Попробуйте еще раз!"
    
    win_amount = bet * win_multiplier if win_multiplier > 0 else 0
    
    if win_amount > 0:
        return True, win_amount, result_text
    return False, 0, result_text

async def play_dice(bet: float) -> Tuple[bool, float, str]:
    user_roll = random.randint(1, 6)
    bot_roll = random.randint(1, 6)
    
    result_text = f"🎲 Ваш бросок: **{user_roll}**\n🎲 Бросок бота: **{bot_roll}**\n\n"
    
    if user_roll > bot_roll:
        win_amount = bet * 1.8
        result_text += f"🎉 Вы выиграли! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    elif user_roll < bot_roll:
        result_text += f"😢 Вы проиграли! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text
    else:
        result_text += f"🤝 Ничья! Ставка возвращена"
        return True, bet, result_text

async def play_rps(bet: float, user_choice: str) -> Tuple[bool, float, str]:
    choices = {"камень": "🪨", "ножницы": "✂️", "бумага": "📄"}
    bot_choice = random.choice(["камень", "ножницы", "бумага"])
    
    result_text = f"Вы: {choices[user_choice]} | Бот: {choices[bot_choice]}\n\n"
    
    if user_choice == bot_choice:
        result_text += "🤝 Ничья! Ставка возвращена"
        return True, bet, result_text
    
    wins = {
        ("камень", "ножницы"): True,
        ("ножницы", "бумага"): True,
        ("бумага", "камень"): True
    }
    
    if wins.get((user_choice, bot_choice), False):
        win_amount = bet * 1.9
        result_text += f"🎉 Вы победили! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        result_text += f"😢 Вы проиграли! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text

async def play_number_guess(bet: float, guess: int) -> Tuple[bool, float, str]:
    secret = random.randint(1, 10)
    result_text = f"🔢 Ваше число: {guess}\n🎲 Загаданное число: {secret}\n\n"
    
    if guess == secret:
        win_amount = bet * 3
        result_text += f"🎉 ТОЧНОЕ ПОПАДАНИЕ! x3! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    elif abs(guess - secret) <= 2:
        win_amount = bet * 1.5
        result_text += f"👍 Близко! x1.5! +{win_amount:.0f} {get_currency_name()}"
        return True, win_amount, result_text
    else:
        result_text += f"😢 Не угадали! -{bet:.0f} {get_currency_name()}"
        return False, 0, result_text

async def play_blackjack(bet: float, action: str = None, player_cards: List = None, dealer_cards: List = None):
    if player_cards is None:
        deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        random.shuffle(deck)
        player_cards = [deck.pop(), deck.pop()]
        dealer_cards = [deck.pop(), deck.pop()]
        
        result_text = f"🃏 **БЛЭКДЖЕК** 🃏\n\n"
        result_text += f"Ваши карты: {player_cards} (сумма: {sum(player_cards)})\n"
        result_text += f"Карта дилера: {dealer_cards[0]} ❓\n\n"
        result_text += "Что делаем?"
        
        return None, bet, result_text, player_cards, dealer_cards
    
    if action == "hit":
        deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        player_cards.append(random.choice(deck))
        
        if sum(player_cards) > 21:
            result_text = f"🃏 **БЛЭКДЖЕК** 🃏\n\n"
            result_text += f"Ваши карты: {player_cards} (сумма: {sum(player_cards)})\n"
            result_text += f"😢 ПЕРЕБОР! Вы проиграли -{bet:.0f} {get_currency_name()}"
            return False, 0, result_text, player_cards, dealer_cards
        
        result_text = f"🃏 **БЛЭКДЖЕК** 🃏\n\n"
        result_text += f"Ваши карты: {player_cards} (сумма: {sum(player_cards)})\n"
        result_text += f"Карта дилера: {dealer_cards[0]} ❓\n\n"
        result_text += "Что делаем?"
        
        return None, bet, result_text, player_cards, dealer_cards
    
    elif action == "stand":
        player_sum = sum(player_cards)
        dealer_sum = sum(dealer_cards)
        
        while dealer_sum < 17:
            deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
            new_card = random.choice(deck)
            dealer_cards.append(new_card)
            dealer_sum += new_card
        
        result_text = f"🃏 **БЛЭКДЖЕК** 🃏\n\n"
        result_text += f"Ваши карты: {player_cards} (сумма: {player_sum})\n"
        result_text += f"Карты дилера: {dealer_cards} (сумма: {dealer_sum})\n\n"
        
        if dealer_sum > 21 or player_sum > dealer_sum:
            win_amount = bet * 2
            result_text += f"🎉 ВЫ ПОБЕДИЛИ! +{win_amount:.0f} {get_currency_name()}"
            return True, win_amount, result_text, player_cards, dealer_cards
        elif player_sum < dealer_sum:
            result_text += f"😢 Дилер победил! -{bet:.0f} {get_currency_name()}"
            return False, 0, result_text, player_cards, dealer_cards
        else:
            result_text += f"🤝 Ничья! Ставка возвращена"
            return True, bet, result_text, player_cards, dealer_cards

# ========== КЛАВИАТУРЫ ==========
def main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎁 Кейсы", callback_data="show_cases")
    builder.button(text="💰 Баланс", callback_data="show_balance")
    builder.button(text="📦 Инвентарь", callback_data="show_inventory")
    builder.button(text="🎮 Игры", callback_data="show_games")
    builder.button(text="🏪 Магазин", callback_data="show_shop")
    builder.button(text="🔄 Скупка", callback_data="show_resell")
    builder.button(text="🎁 Бонус кейс", callback_data="bonus_case")
    builder.button(text="🆘 Поддержка", callback_data="support")
    if is_admin(user_id):
        builder.button(text="⚙️ Админ", callback_data="admin_panel")
    builder.adjust(2)
    return builder.as_markup()

def games_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎰 Слоты", callback_data="game_slots")
    builder.button(text="🎲 Кости", callback_data="game_dice")
    builder.button(text="✂️ КНБ", callback_data="game_rps")
    builder.button(text="🔢 Угадай число", callback_data="game_number")
    builder.button(text="🃏 Блэкджек", callback_data="game_blackjack")
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

def admin_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📦 Кейсы", callback_data="admin_cases")
    builder.button(text="📢 Рассылка", callback_data="admin_broadcast")
    builder.button(text="💳 Оплата", callback_data="admin_payment")
    builder.button(text="💰 Баланс юзеров", callback_data="admin_balance_users")
    builder.button(text="⭐ Валюта", callback_data="admin_currency")
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

def blackjack_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🎴 Взять карту", callback_data="bj_hit")
    builder.button(text="✋ Остановиться", callback_data="bj_stand")
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
    add_to_inventory(user_id, "Приветственный бонус", 100, "🎁", "Особый", "Бонус")
    
    await message.answer(
        f"🎉 Добро пожаловать, {first_name}!\n\n"
        f"💰 Ваш баланс: {get_user_balance(user_id)} {get_currency_name()}\n\n"
        f"Выберите действие:",
        reply_markup=main_keyboard(user_id)
    )

@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text(
        f"💰 Ваш баланс: {get_user_balance(callback.from_user.id)} {get_currency_name()}\n\nГлавное меню:",
        reply_markup=main_keyboard(callback.from_user.id)
    )
    await callback.answer()

@dp.callback_query(F.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    balance = get_user_balance(callback.from_user.id)
    await callback.answer(f"💰 Ваш баланс: {balance} {get_currency_name()}", show_alert=True)

@dp.callback_query(F.data == "show_games")
async def show_games(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎮 **ВЫБЕРИ ИГРУ** 🎮\n\n"
        "🎰 **Слоты** - x1.5 до x10\n"
        "🎲 **Кости** - кто больше выбросит\n"
        "✂️ **Камень-ножницы-бумага** - классика\n"
        "🔢 **Угадай число** - угадай от 1 до 10\n"
        "🃏 **Блэкджек** - 21 очко\n\n"
        "Выберите игру:",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await callback.answer()

# ========== ИГРЫ ОБРАБОТЧИКИ ==========
@dp.callback_query(F.data == "game_slots")
async def game_slots_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎰 **СЛОТЫ** 🎰\n\n"
        f"Правила: выпадают 3 символа\n"
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
    await state.set_state(GameStates.waiting_for_slots_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_slots_bet)
async def game_slots_play(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} {get_currency_name()}")
            return
        
        update_balance(message.from_user.id, -bet)
        
        win, win_amount, result_text = await play_slots(bet)
        
        if win:
            update_balance(message.from_user.id, win_amount)
            await message.answer(
                f"🎰 **РЕЗУЛЬТАТ** 🎰\n\n{result_text}\n\n"
                f"💰 Выигрыш: +{win_amount:.0f} {get_currency_name()}\n"
                f"💵 Новый баланс: {get_user_balance(message.from_user.id)} {get_currency_name()}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
        else:
            await message.answer(
                f"🎰 **РЕЗУЛЬТАТ** 🎰\n\n{result_text}\n\n"
                f"💵 Новый баланс: {get_user_balance(message.from_user.id)} {get_currency_name()}",
                parse_mode="Markdown",
                reply_markup=games_keyboard()
            )
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(F.data == "game_dice")
async def game_dice_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🎲 **КОСТИ** 🎲\n\n"
        f"Правила: вы и бот бросаете кубик\n"
        f"У кого больше - тот победил\n"
        f"Выигрыш: x1.8 от ставки\n\n"
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
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} {get_currency_name()}")
            return
        
        update_balance(message.from_user.id, -bet)
        
        win, win_amount, result_text = await play_dice(bet)
        
        if win:
            update_balance(message.from_user.id, win_amount)
        
        await message.answer(
            f"🎲 **РЕЗУЛЬТАТ** 🎲\n\n{result_text}\n\n"
            f"💵 Новый баланс: {get_user_balance(message.from_user.id)} {get_currency_name()}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(F.data == "game_rps")
async def game_rps_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"✂️ **КАМЕНЬ-НОЖНИЦЫ-БУМАГА** ✂️\n\n"
        f"Правила: выберите свой вариант\n"
        f"Выигрыш: x1.9 от ставки\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_rps_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_rps_bet)
async def game_rps_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} {get_currency_name()}")
            return
        
        await state.update_data(rps_bet=bet)
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🪨 Камень", callback_data="rps_rock")
        builder.button(text="✂️ Ножницы", callback_data="rps_scissors")
        builder.button(text="📄 Бумага", callback_data="rps_paper")
        builder.button(text="🔙 Назад", callback_data="show_games")
        builder.adjust(3)
        
        await message.answer(
            f"✂️ **СДЕЛАЙТЕ ВЫБОР** ✂️\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}",
            parse_mode="Markdown",
            reply_markup=builder.as_markup()
        )
        await state.set_state(GameStates.waiting_for_rps_choice)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_rps_choice, F.data.startswith("rps_"))
async def game_rps_play(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('rps_bet', 0)
    
    choices_map = {
        "rps_rock": "камень",
        "rps_scissors": "ножницы",
        "rps_paper": "бумага"
    }
    
    user_choice = choices_map.get(callback.data)
    if not user_choice:
        return
    
    update_balance(callback.from_user.id, -bet)
    
    win, win_amount, result_text = await play_rps(bet, user_choice)
    
    if win:
        update_balance(callback.from_user.id, win_amount)
    
    await callback.message.edit_text(
        f"✂️ **РЕЗУЛЬТАТ** ✂️\n\n{result_text}\n\n"
        f"💵 Новый баланс: {get_user_balance(callback.from_user.id)} {get_currency_name()}",
        parse_mode="Markdown",
        reply_markup=games_keyboard()
    )
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "game_number")
async def game_number_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🔢 **УГАДАЙ ЧИСЛО** 🔢\n\n"
        f"Правила: угадайте число от 1 до 10\n"
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
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} {get_currency_name()}")
            return
        
        await state.update_data(number_bet=bet)
        await message.answer(
            f"🔢 **УГАДАЙ ЧИСЛО** 🔢\n\n"
            f"💰 Ставка: {bet:.0f} {get_currency_name()}\n\n"
            f"Введите число от 1 до 10:",
            parse_mode="Markdown"
        )
        await state.set_state(GameStates.waiting_for_number_guess)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.message(GameStates.waiting_for_number_guess)
async def game_number_play(message: types.Message, state: FSMContext):
    try:
        guess = int(message.text)
        if guess < 1 or guess > 10:
            await message.answer("❌ Введите число от 1 до 10!")
            return
        
        data = await state.get_data()
        bet = data.get('number_bet', 0)
        
        update_balance(message.from_user.id, -bet)
        
        win, win_amount, result_text = await play_number_guess(bet, guess)
        
        if win:
            update_balance(message.from_user.id, win_amount)
        
        await message.answer(
            f"🔢 **РЕЗУЛЬТАТ** 🔢\n\n{result_text}\n\n"
            f"💵 Новый баланс: {get_user_balance(message.from_user.id)} {get_currency_name()}",
            parse_mode="Markdown",
            reply_markup=games_keyboard()
        )
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(F.data == "game_blackjack")
async def game_blackjack_start(callback: CallbackQuery, state: FSMContext):
    min_bet = float(get_setting('casino_min_bet'))
    max_bet = float(get_setting('casino_max_bet'))
    
    await callback.message.edit_text(
        f"🃏 **БЛЭКДЖЕК** 🃏\n\n"
        f"Правила: наберите 21 очко или ближе к нему\n"
        f"Перебор - проигрыш\n"
        f"Победа - x2 от ставки\n\n"
        f"💰 Ставка от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}\n\n"
        f"Введите сумму ставки:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="show_games")]])
    )
    await state.set_state(GameStates.waiting_for_blackjack_bet)
    await callback.answer()

@dp.message(GameStates.waiting_for_blackjack_bet)
async def game_blackjack_bet(message: types.Message, state: FSMContext):
    try:
        bet = float(message.text)
        min_bet = float(get_setting('casino_min_bet'))
        max_bet = float(get_setting('casino_max_bet'))
        
        if bet < min_bet or bet > max_bet:
            await message.answer(f"❌ Ставка должна быть от {min_bet:.0f} до {max_bet:.0f} {get_currency_name()}")
            return
        
        balance = get_user_balance(message.from_user.id)
        if balance < bet:
            await message.answer(f"❌ Недостаточно средств! Ваш баланс: {balance} {get_currency_name()}")
            return
        
        update_balance(message.from_user.id, -bet)
        
        result = await play_blackjack(bet)
        win, win_amount, result_text, player_cards, dealer_cards = result
        
        await state.update_data(blackjack_bet=bet, player_cards=player_cards, dealer_cards=dealer_cards)
        
        await message.answer(
            result_text,
            parse_mode="Markdown",
            reply_markup=blackjack_keyboard()
        )
        await state.set_state(GameStates.waiting_for_blackjack_action)
    except ValueError:
        await message.answer("❌ Введите число!")
        await state.clear()

@dp.callback_query(GameStates.waiting_for_blackjack_action, F.data.in_(["bj_hit", "bj_stand"]))
async def game_blackjack_action(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    bet = data.get('blackjack_bet', 0)
    player_cards = data.get('player_cards', [])
    dealer_cards = data.get('dealer_cards', [])
    
    action = "hit" if callback.data == "bj_hit" else "stand"
    
    result = await play_blackjack(bet, action, player_cards, dealer_cards)
    win, win_amount, result_text, new_player_cards, new_dealer_cards = result
    
    if win is None:
        await state.update_data(player_cards=new_player_cards, dealer_cards=new_dealer_cards)
        await callback.message.edit_text(
            result_text,
            parse_mode="Markdown",
            reply_markup=blackjack_keyboard()
        )
    else:
        if win and win_amount > 0:
            update_balance(callback.from_user.id, win_amount)
        
        await callback.message.edit_text(
            f"🃏 **РЕЗУЛЬТАТ** 🃏\n\n{result_text}\n\n"
            f"💵 Новый баланс: {get_user_balance(callback.from_user.id)} {get_currency_name()}",
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
    items_list = items
    
    if not items_list:
        update_balance(callback.from_user.id, price)
        await callback.answer("❌ В кейсе нет предметов!", show_alert=True)
        return
    
    selected_item, result_text = await open_case_animation(callback.message, case_name, items_list)
    
    add_to_inventory(
        callback.from_user.id, 
        selected_item['item_name'], 
        selected_item['item_value'],
        selected_item['emoji'],
        selected_item['rarity'],
        case_name
    )
    
    db.update_user_stats(callback.from_user.id, price, 1)
    
    await callback.message.edit_text(
        result_text,
        parse_mode="Markdown",
        reply_markup=cases_keyboard()
    )
    
    await callback.answer(f"🎉 Вы выиграли {selected_item['item_name']}!")

@dp.callback_query(F.data == "bonus_case")
async def bonus_case_handler(callback: CallbackQuery):
    if not await check_subscriptions(callback.from_user.id):
        await callback.answer("❌ Подпишитесь на каналы!", show_alert=True)
        return
    
    last_time = db.get_last_bonus_time(callback.from_user.id)
    now = int(datetime.now().timestamp())
    cooldown = int(get_setting('bonus_case_cooldown'))
    
    if now - last_time < cooldown:
        hours_left = (cooldown - (now - last_time)) // 3600
        minutes_left = ((cooldown - (now - last_time)) % 3600) // 60
        await callback.answer(f"⏰ Бонус через {hours_left}ч {minutes_left}мин!", show_alert=True)
        return
    
    bonus_value = random.randint(50, 500)
    bonus_items = [
        ("✨ Золотая монета", bonus_value, "🪙", "Легендарный"),
        ("💎 Драгоценный камень", bonus_value, "💎", "Эпический"),
        ("🎁 Секретный сундук", bonus_value, "🎁", "Редкий"),
        ("⭐ Удача дня", bonus_value, "⭐", "Необычный")
    ]
    
    item_name, item_value, emoji, rarity = random.choice(bonus_items)
    add_to_inventory(callback.from_user.id, item_name, item_value, emoji, rarity, "Бонусный кейс")
    db.update_bonus_time(callback.from_user.id)
    
    await callback.answer(f"🎁 Бонус получен!", show_alert=True)
    await callback.message.answer(
        f"🎁 **БОНУСНЫЙ КЕЙС** 🎁\n\n"
        f"{emoji} **{item_name}**\n"
        f"💰 Стоимость: {item_value} {get_currency_name()}\n"
        f"⭐ Редкость: {rarity}\n\n"
        f"Предмет добавлен в инвентарь!",
        parse_mode="Markdown",
        reply_markup=main_keyboard(callback.from_user.id)
    )

# ========== ИНВЕНТАРЬ И СКУПКА ==========
@dp.callback_query(F.data == "show_inventory")
async def show_inventory(callback: CallbackQuery):
    items = db.get_user_inventory(callback.from_user.id)
    
    if not items:
        await callback.answer("📦 Ваш инвентарь пуст!", show_alert=True)
        return
    
    text = "📦 **ВАШ ИНВЕНТАРЬ** 📦\n\n"
    for item in items[:20]:
        rarity_emoji = get_rarity_emoji(item['rarity'])
        text += f"{item['item_emoji']} **{item['item_name']}** {rarity_emoji}\n"
        text += f"   💰 {item['item_value']} {get_currency_name()} | 📦 {item['from_case']}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Продать всё", callback_data="sell_all")
    builder.button(text="🔙 Назад", callback_data="back_to_main")
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "show_resell")
async def show_resell(callback: CallbackQuery):
    items = db.get_user_inventory(callback.from_user.id)
    count = len(items)
    
    await callback.message.edit_text(
        "🔄 **СКУПКА ПРЕДМЕТОВ** 🔄\n\n"
        f"📦 У вас {count} предметов в инвентаре\n\n"
        "💰 Вы можете продать все предметы по их полной стоимости!\n\n"
        "Продажа: нажмите кнопку ниже",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Продать всё за раз", callback_data="sell_all")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "sell_all")
async def sell_all_items(callback: CallbackQuery):
    items = db.get_all_user_items(callback.from_user.id)
    
    if not items:
        await callback.answer("❌ Нет предметов для продажи!", show_alert=True)
        return
    
    total = db.sell_all_items(callback.from_user.id)
    update_balance(callback.from_user.id, total)
    
    await callback.answer(f"✅ Продано на {total:.0f} {get_currency_name()}!", show_alert=True)
    await callback.message.edit_text(
        f"✅ **ПРОДАЖА ЗАВЕРШЕНА**\n\n"
        f"💰 Выручено: {total:.0f} {get_currency_name()}\n"
        f"💵 Новый баланс: {get_user_balance(callback.from_user.id)} {get_currency_name()}",
        parse_mode="Markdown",
        reply_markup=main_keyboard(callback.from_user.id)
    )

@dp.callback_query(F.data == "show_shop")
async def show_shop(callback: CallbackQuery):
    payment_card = get_setting('payment_card')
    payment_phone = get_setting('payment_phone')
    
    text = "🏪 **МАГАЗИН** 🏪\n\n"
    text += "💳 **Способы пополнения:**\n"
    if payment_card:
        text += f"💳 Карта: `{payment_card}`\n"
    if payment_phone:
        text += f"📱 Телефон: `{payment_phone}`\n"
    
    text += "\nПосле оплаты отправьте скриншот в поддержку\n"
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
        f"Вопросы по оплате, проблемы с ботом, сотрудничество.",
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
    await message.answer("💰 Введите цену кейса (число):")
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
    await message.answer("💰 Введите стоимость предмета (число):")
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
        text += f"ID: {case['id']} | {case['name']} - {case['price']} {get_currency_name()}\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_keyboard()
    )
    await callback.answer()

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
async def admin_payment(callback: CallbackQuery):
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
    
    await callback.message.answer("⭐ Введите символ валюты (например: ⭐, $, €, 🪙):")
    await state.set_state(AdminStates.waiting_for_currency_symbol)
    await callback.answer()

@dp.message(AdminStates.waiting_for_currency_symbol)
async def save_currency(message: types.Message, state: FSMContext):
    db.set_setting('currency_symbol', message.text)
    await message.answer(f"✅ Валюта изменена на {message.text}!", reply_markup=admin_keyboard())
    await state.clear()

@dp.callback_query(F.data == "admin_balance_users")
async def admin_balance_users(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Нет доступа!", show_alert=True)
        return
    
    await callback.message.answer("💰 Введите ID пользователя и сумму через пробел:\nПример: 123456789 1000")
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
    total_items = db.get_total_items()
    total_balance = db.get_total_balance()
    
    text = f"📊 **СТАТИСТИКА БОТА** 📊\n\n"
    text += f"👥 Пользователей: {total_users}\n"
    text += f"💰 Всего потрачено: {total_spent:.0f} {get_currency_name()}\n"
    text += f"🎁 Открыто кейсов: {total_opened}\n"
    text += f"📦 Предметов в инвентаре: {total_items}\n"
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
    print("🤖 БОТ ЗАПУЩЕН!")
    print(f"👑 Администраторы: {ADMIN_IDS}")
    print("🎮 5 игр доступно: Слоты, Кости, КНБ, Угадай число, Блэкджек")
    print("🎁 Система кейсов с анимацией")
    print("💾 Данные хранятся в JSON файле")
    print("=" * 50)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())