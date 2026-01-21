"""
🤖 ETHIOFARMER BOT - ULTIMATE VERSION
Complete Earning Bot with Beautiful UI
Fixed all issues + Added attractive features
Created for Pydroid 3 on Android
Admin: @esube48
"""

import json
import os
import logging
import asyncio
from datetime import datetime, timedelta
import random
import string
from typing import Dict, List, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# ==================== CONFIGURATION ====================
BOT_TOKEN = "7780485113:AAE4O8n8OHwfapisLtmU_K8Vv_8VdMRkB9s"
ADMIN_ID = 7343312321
BOT_USERNAME = "Ethiofarmer_bot"
SUPPORT_USERNAME = "@esube48"

# Database files
USERS_DB = "users.json"
WITHDRAW_DB = "withdraw.json"
ACCOUNTS_DB = "accounts.json"
TRANSACTIONS_DB = "transactions.json"
SETTINGS_DB = "settings.json"
MESSAGES_DB = "messages.json"

# Settings
COMMISSION_PER_JOB = 10.0  # ETB per completed registration
REFERRAL_COMMISSION_PERCENT = 10  # 10% of invited user's earnings
MIN_WITHDRAWAL = 20.0  # Minimum withdrawal amount
HOLD_PERIOD_DAYS = 1  # Days before hold becomes real

# ==================== LOGGING SETUP ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ==================== DATABASE INITIALIZATION ====================
def init_databases():
    """Initialize all database files if they don't exist"""
    for db_file in [USERS_DB, WITHDRAW_DB, ACCOUNTS_DB, TRANSACTIONS_DB, SETTINGS_DB, MESSAGES_DB]:
        if not os.path.exists(db_file):
            with open(db_file, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=2)
    
    # Initialize settings
    settings = load_db(SETTINGS_DB)
    if not settings:
        settings = {
            'bot_name': 'EthioFarmer Bot',
            'commission_per_job': COMMISSION_PER_JOB,
            'referral_percent': REFERRAL_COMMISSION_PERCENT,
            'min_withdrawal': MIN_WITHDRAWAL,
            'hold_days': HOLD_PERIOD_DAYS,
            'last_hold_transfer': None,
            'total_users': 0,
            'total_earned': 0.0,
            'total_withdrawn': 0.0,
            'total_jobs': 0,
            'created_at': datetime.now().isoformat(),
            'daily_bonus': 5.0,
            'welcome_bonus': 5.0
        }
        save_db(SETTINGS_DB, settings)

def load_db(file_path: str) -> Dict:
    """Load JSON database"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}

def save_db(file_path: str, data: Dict):
    """Save data to JSON database"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")

# ==================== USER MANAGEMENT ====================
class UserManager:
    @staticmethod
    def get_user(user_id: int, update_info: bool = True, username: str = "", first_name: str = "") -> Dict:
        """Get or create user data"""
        users = load_db(USERS_DB)
        user_id_str = str(user_id)
        
        if user_id_str not in users:
            # Give welcome bonus
            settings = load_db(SETTINGS_DB)
            welcome_bonus = settings.get('welcome_bonus', 5.0)
            
            users[user_id_str] = {
                'id': user_id,
                'username': username or '',
                'first_name': first_name or '',
                'join_date': datetime.now().isoformat(),
                'real_etb': welcome_bonus,
                'hold_etb': 0.0,
                'total_earned': welcome_bonus,
                'completed_jobs': 0,
                'referrals': [],  # List of referred user IDs
                'referral_count': 0,
                'referral_earnings': 0.0,
                'withdrawals': 0,
                'total_withdrawn': 0.0,
                'pending_job': None,  # Account ID if user has pending job
                'last_active': datetime.now().isoformat(),
                'is_active': True,
                'banned': False,
                'level': 1,
                'experience': 0,
                'referral_code': ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                'daily_bonus_claimed': False,
                'last_daily_bonus': None,
                'streak_days': 0
            }
            save_db(USERS_DB, users)
            
            # Update total users count
            settings['total_users'] = len(users)
            save_db(SETTINGS_DB, settings)
            
            # Log welcome bonus transaction
            TransactionManager.add_transaction(
                user_id=user_id,
                amount=welcome_bonus,
                type='welcome_bonus',
                description=f"Welcome bonus"
            )
        
        # Update user info if requested
        if update_info:
            if username and users[user_id_str]['username'] != username:
                users[user_id_str]['username'] = username
            if first_name and users[user_id_str]['first_name'] != first_name:
                users[user_id_str]['first_name'] = first_name
        
        users[user_id_str]['last_active'] = datetime.now().isoformat()
        save_db(USERS_DB, users)
        
        return users[user_id_str]

    @staticmethod
    def update_user(user_id: int, data: Dict):
        """Update user data"""
        users = load_db(USERS_DB)
        user_id_str = str(user_id)
        
        if user_id_str in users:
            users[user_id_str].update(data)
            users[user_id_str]['last_active'] = datetime.now().isoformat()
            save_db(USERS_DB, users)

    @staticmethod
    def add_referral(referrer_id: int, referred_id: int):
        """Add referral relationship"""
        users = load_db(USERS_DB)
        referrer_str = str(referrer_id)
        referred_str = str(referred_id)
        
        if referrer_str in users and referred_str in users:
            # Add to referrals list if not already there
            if referred_str not in users[referrer_str]['referrals']:
                users[referrer_str]['referrals'].append(referred_str)
                users[referrer_str]['referral_count'] = len(users[referrer_str]['referrals'])
                
                # Give referral bonus to referrer
                settings = load_db(SETTINGS_DB)
                referral_bonus = 5.0  # Bonus for getting a referral
                users[referrer_str]['real_etb'] += referral_bonus
                users[referrer_str]['total_earned'] += referral_bonus
                
                save_db(USERS_DB, users)
                
                # Log transaction
                TransactionManager.add_transaction(
                    user_id=referrer_id,
                    amount=referral_bonus,
                    type='referral_bonus',
                    description=f"Referral bonus for {referred_id}"
                )

    @staticmethod
    def add_referral_earning(referrer_id: int, amount: float):
        """Add referral commission to referrer"""
        users = load_db(USERS_DB)
        referrer_str = str(referrer_id)
        
        if referrer_str in users:
            commission = amount * (REFERRAL_COMMISSION_PERCENT / 100)
            users[referrer_str]['referral_earnings'] += commission
            users[referrer_str]['real_etb'] += commission
            users[referrer_str]['total_earned'] += commission
            save_db(USERS_DB, users)
            
            # Log transaction
            TransactionManager.add_transaction(
                user_id=referrer_id,
                amount=commission,
                type='referral_commission',
                description=f"Referral commission {REFERRAL_COMMISSION_PERCENT}%"
            )

    @staticmethod
    def get_all_users() -> Dict:
        """Get all users"""
        return load_db(USERS_DB)

    @staticmethod
    def get_active_users_count() -> int:
        """Count users active in last 7 days"""
        users = load_db(USERS_DB)
        week_ago = datetime.now() - timedelta(days=7)
        count = 0
        
        for user in users.values():
            last_active = datetime.fromisoformat(user.get('last_active', user.get('join_date')))
            if last_active > week_ago and user.get('is_active', True):
                count += 1
        
        return count

    @staticmethod
    def get_user_count() -> int:
        """Get total user count"""
        return len(load_db(USERS_DB))

# ==================== ACCOUNT MANAGEMENT ====================
class AccountManager:
    @staticmethod
    def add_account(first_name: str, last_name: str, email: str, password: str, added_by: int = ADMIN_ID) -> str:
        """Add a new account manually through admin"""
        accounts = load_db(ACCOUNTS_DB)
        
        # Generate unique account ID
        account_id = f"ACC{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        accounts[account_id] = {
            'id': account_id,
            'first_name': first_name,
            'last_name': last_name,
            'email': email,
            'password': password,
            'status': 'available',  # available, assigned, completed, cancelled
            'created_at': datetime.now().isoformat(),
            'added_by': added_by,
            'assigned_to': None,
            'assigned_at': None,
            'completed_by': None,
            'completed_at': None,
            'cancelled_at': None
        }
        
        save_db(ACCOUNTS_DB, accounts)
        logger.info(f"New account added by {added_by}: {account_id}")
        return account_id

    @staticmethod
    def get_available_account() -> Optional[Dict]:
        """Get an available account for registration"""
        accounts = load_db(ACCOUNTS_DB)
        
        available_accounts = []
        for acc_id, acc_data in accounts.items():
            if acc_data['status'] == 'available':
                available_accounts.append((acc_id, acc_data))
        
        if not available_accounts:
            return None
        
        # Select random account
        acc_id, account = random.choice(available_accounts)
        
        # Mark as assigned
        account['status'] = 'assigned'
        account['assigned_at'] = datetime.now().isoformat()
        accounts[acc_id] = account
        save_db(ACCOUNTS_DB, accounts)
        
        return {**account, 'account_id': acc_id}

    @staticmethod
    def assign_account_to_user(account_id: str, user_id: int) -> bool:
        """Assign account to user"""
        accounts = load_db(ACCOUNTS_DB)
        
        if account_id in accounts and accounts[account_id]['status'] == 'available':
            accounts[account_id]['status'] = 'assigned'
            accounts[account_id]['assigned_to'] = user_id
            accounts[account_id]['assigned_at'] = datetime.now().isoformat()
            save_db(ACCOUNTS_DB, accounts)
            return True
        
        return False

    @staticmethod
    def complete_account(account_id: str, user_id: int) -> bool:
        """Mark account as completed"""
        accounts = load_db(ACCOUNTS_DB)
        
        if account_id in accounts and accounts[account_id]['status'] == 'assigned':
            accounts[account_id]['status'] = 'completed'
            accounts[account_id]['completed_by'] = user_id
            accounts[account_id]['completed_at'] = datetime.now().isoformat()
            save_db(ACCOUNTS_DB, accounts)
            return True
        
        return False

    @staticmethod
    def cancel_account(account_id: str) -> bool:
        """Mark account as cancelled (make available again)"""
        accounts = load_db(ACCOUNTS_DB)
        
        if account_id in accounts and accounts[account_id]['status'] == 'assigned':
            accounts[account_id]['status'] = 'available'
            accounts[account_id]['assigned_to'] = None
            accounts[account_id]['assigned_at'] = None
            accounts[account_id]['cancelled_at'] = datetime.now().isoformat()
            save_db(ACCOUNTS_DB, accounts)
            return True
        
        return False

    @staticmethod
    def get_account_stats() -> Dict:
        """Get account statistics"""
        accounts = load_db(ACCOUNTS_DB)
        
        stats = {
            'total': len(accounts),
            'available': 0,
            'assigned': 0,
            'completed': 0,
            'cancelled': 0,
            'today_completed': 0
        }
        
        today = datetime.now().date()
        
        for acc in accounts.values():
            status = acc.get('status', 'available')
            stats[status] = stats.get(status, 0) + 1
            
            if status == 'completed':
                completed_at = acc.get('completed_at')
                if completed_at:
                    try:
                        comp_date = datetime.fromisoformat(completed_at).date()
                        if comp_date == today:
                            stats['today_completed'] += 1
                    except:
                        pass
        
        return stats

    @staticmethod
    def get_all_accounts() -> Dict:
        """Get all accounts"""
        return load_db(ACCOUNTS_DB)

    @staticmethod
    def get_completed_accounts() -> List[Dict]:
        """Get all completed accounts with user info"""
        accounts = load_db(ACCOUNTS_DB)
        users = load_db(USERS_DB)
        
        completed = []
        for acc_id, acc_data in accounts.items():
            if acc_data['status'] == 'completed':
                # Get user info
                user_id = acc_data.get('completed_by')
                user_info = {}
                if user_id and str(user_id) in users:
                    user = users[str(user_id)]
                    user_info = {
                        'username': user.get('username', 'N/A'),
                        'first_name': user.get('first_name', 'N/A'),
                        'user_id': user_id
                    }
                
                completed.append({
                    **acc_data,
                    'account_id': acc_id,
                    'user_info': user_info
                })
        
        # Sort by completion date (newest first)
        completed.sort(key=lambda x: x.get('completed_at', ''), reverse=True)
        return completed

# ==================== WITHDRAWAL MANAGEMENT ====================
class WithdrawalManager:
    @staticmethod
    def create_request(user_id: int, name: str, telebirr: str, amount: float) -> str:
        """Create new withdrawal request"""
        withdraws = load_db(WITHDRAW_DB)
        
        request_id = f"WD{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        withdraws[request_id] = {
            'id': request_id,
            'user_id': user_id,
            'name': name,
            'telebirr': telebirr,
            'amount': amount,
            'status': 'pending',  # pending, approved, rejected, paid
            'created_at': datetime.now().isoformat(),
            'processed_at': None,
            'processed_by': None,
            'notes': '',
            'payment_method': 'telebirr'
        }
        
        save_db(WITHDRAW_DB, withdraws)
        
        # Update user withdrawals count
        user = UserManager.get_user(user_id, update_info=False)
        user['withdrawals'] += 1
        user['total_withdrawn'] += amount
        UserManager.update_user(user_id, user)
        
        # Update system stats
        settings = load_db(SETTINGS_DB)
        settings['total_withdrawn'] += amount
        save_db(SETTINGS_DB, settings)
        
        return request_id

    @staticmethod
    def get_pending_requests() -> List[Dict]:
        """Get all pending withdrawal requests"""
        withdraws = load_db(WITHDRAW_DB)
        pending = []
        
        for req in withdraws.values():
            if req['status'] == 'pending':
                pending.append(req)
        
        # Sort by creation date (oldest first)
        pending.sort(key=lambda x: x['created_at'])
        return pending

    @staticmethod
    def approve_request(request_id: str, admin_id: int) -> bool:
        """Approve withdrawal request"""
        withdraws = load_db(WITHDRAW_DB)
        
        if request_id in withdraws:
            withdraws[request_id]['status'] = 'approved'
            withdraws[request_id]['processed_at'] = datetime.now().isoformat()
            withdraws[request_id]['processed_by'] = admin_id
            save_db(WITHDRAW_DB, withdraws)
            return True
        
        return False

    @staticmethod
    def mark_as_paid(request_id: str, admin_id: int, notes: str = "") -> bool:
        """Mark withdrawal as paid"""
        withdraws = load_db(WITHDRAW_DB)
        
        if request_id in withdraws:
            withdraws[request_id]['status'] = 'paid'
            withdraws[request_id]['processed_at'] = datetime.now().isoformat()
            withdraws[request_id]['processed_by'] = admin_id
            withdraws[request_id]['notes'] = notes
            save_db(WITHDRAW_DB, withdraws)
            return True
        
        return False

    @staticmethod
    def reject_request(request_id: str, admin_id: int, reason: str = "") -> bool:
        """Reject withdrawal request"""
        withdraws = load_db(WITHDRAW_DB)
        
        if request_id in withdraws:
            withdraws[request_id]['status'] = 'rejected'
            withdraws[request_id]['processed_at'] = datetime.now().isoformat()
            withdraws[request_id]['processed_by'] = admin_id
            withdraws[request_id]['notes'] = reason
            save_db(WITHDRAW_DB, withdraws)
            
            # Return money to user
            req = withdraws[request_id]
            user = UserManager.get_user(req['user_id'], update_info=False)
            user['real_etb'] += req['amount']
            UserManager.update_user(req['user_id'], user)
            
            return True
        
        return False

    @staticmethod
    def get_stats() -> Dict:
        """Get withdrawal statistics"""
        withdraws = load_db(WITHDRAW_DB)
        
        stats = {
            'total': len(withdraws),
            'pending': 0,
            'approved': 0,
            'rejected': 0,
            'paid': 0,
            'total_amount': 0.0,
            'today_amount': 0.0
        }
        
        today = datetime.now().date()
        
        for req in withdraws.values():
            status = req.get('status', 'pending')
            stats[status] += 1
            
            amount = req.get('amount', 0)
            stats['total_amount'] += amount
            
            created_at = req.get('created_at')
            if created_at:
                try:
                    created_date = datetime.fromisoformat(created_at).date()
                    if created_date == today:
                        stats['today_amount'] += amount
                except:
                    pass
        
        return stats

# ==================== TRANSACTION MANAGEMENT ====================
class TransactionManager:
    @staticmethod
    def add_transaction(user_id: int, amount: float, type: str, description: str = ""):
        """Add transaction record"""
        transactions = load_db(TRANSACTIONS_DB)
        
        trans_id = f"TXN{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        transactions[trans_id] = {
            'id': trans_id,
            'user_id': user_id,
            'amount': amount,
            'type': type,  # registration, referral, withdrawal, bonus, adjustment
            'description': description,
            'timestamp': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        save_db(TRANSACTIONS_DB, transactions)

# ==================== MESSAGE MANAGEMENT ====================
class MessageManager:
    @staticmethod
    def save_message(user_id: int, admin_id: int, message: str, direction: str):
        """Save message to database"""
        messages = load_db(MESSAGES_DB)
        
        msg_id = f"MSG{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        
        messages[msg_id] = {
            'id': msg_id,
            'user_id': user_id,
            'admin_id': admin_id,
            'message': message,
            'direction': direction,  # admin_to_user or user_to_admin
            'timestamp': datetime.now().isoformat(),
            'read': False
        }
        
        save_db(MESSAGES_DB, messages)
        return msg_id

# ==================== BEAUTIFUL KEYBOARD GENERATORS ====================
def home_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Generate main menu keyboard - 2x2 grid"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("📝 Register Task", callback_data="register"),
            InlineKeyboardButton("💰 Balance", callback_data="balance")
        ],
        # Row 2: Two buttons
        [
            InlineKeyboardButton("👥 Referrals", callback_data="referrals"),
            InlineKeyboardButton("🎁 Daily Bonus", callback_data="daily_bonus")
        ],
        # Row 3: Two buttons
        [
            InlineKeyboardButton("📤 Withdraw", callback_data="withdraw"),
            InlineKeyboardButton("📊 Statistics", callback_data="stats")
        ]
    ]
    
    # Add admin panel button if user is admin
    if is_admin:
        keyboard.append([InlineKeyboardButton("🛠 ADMIN PANEL", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(keyboard)

def back_home_keyboard() -> InlineKeyboardMarkup:
    """Back to home button - centered"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Home", callback_data="home")]])

def back_admin_keyboard() -> InlineKeyboardMarkup:
    """Back to admin button"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")]])

def registration_keyboard(account_id: str) -> InlineKeyboardMarkup:
    """Registration action buttons - 2x1 + 1x1"""
    keyboard = [
        # Row 1: Two action buttons side by side
        [
            InlineKeyboardButton("✅ Task Completed", callback_data=f"done:{account_id}"),
            InlineKeyboardButton("❌ Cancel Task", callback_data=f"cancel:{account_id}")
        ],
        # Row 2: Single centered button
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def referrals_keyboard() -> InlineKeyboardMarkup:
    """Referrals menu keyboard - 2x1 + 1x1"""
    keyboard = [
        # Row 1: Two buttons side by side
        [
            InlineKeyboardButton("📋 Copy Link", callback_data="copy_ref"),
            InlineKeyboardButton("🔗 Share", callback_data="share_ref")
        ],
        # Row 2: Single centered button
        [
            InlineKeyboardButton("🏠 Main Menu", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def withdraw_method_keyboard() -> InlineKeyboardMarkup:
    """Withdrawal method selection"""
    keyboard = [
        [
            InlineKeyboardButton("📱 Telebirr", callback_data="withdraw_telebirr"),
            InlineKeyboardButton("🏦 Bank", callback_data="withdraw_bank")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin main panel - 3x3 grid"""
    keyboard = [
        # Row 1: Three buttons
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="admin_users"),
            InlineKeyboardButton("💰 Hold Transfer", callback_data="admin_hold_transfer")
        ],
        # Row 2: Three buttons
        [
            InlineKeyboardButton("📤 Withdrawals", callback_data="admin_withdrawals"),
            InlineKeyboardButton("📝 Accounts", callback_data="admin_accounts"),
            InlineKeyboardButton("➕ Add Account", callback_data="admin_add_account")
        ],
        # Row 3: Three buttons
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast"),
            InlineKeyboardButton("💬 Messages", callback_data="admin_messages"),
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
        ],
        # Row 4: Single button
        [
            InlineKeyboardButton("🏠 Home", callback_data="home")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_users_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Users list with pagination - 2x4 grid"""
    users = UserManager.get_all_users()
    user_ids = list(users.keys())
    
    items_per_page = 8
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    
    keyboard = []
    
    # Create 4 rows of 2 buttons each (2x4 grid)
    for i in range(0, items_per_page, 2):
        row = []
        if start_idx + i < len(user_ids):
            user_id1 = user_ids[start_idx + i]
            user1 = users[user_id1]
            name1 = user1.get('first_name', f"ID:{user_id1[:6]}")
            row.append(InlineKeyboardButton(
                f"👤 {name1[:10]}", 
                callback_data=f"admin_view_user:{user_id1}"
            ))
        
        if start_idx + i + 1 < len(user_ids):
            user_id2 = user_ids[start_idx + i + 1]
            user2 = users[user_id2]
            name2 = user2.get('first_name', f"ID:{user_id2[:6]}")
            row.append(InlineKeyboardButton(
                f"👤 {name2[:10]}", 
                callback_data=f"admin_view_user:{user_id2}"
            ))
        
        if row:  # Only add non-empty rows
            keyboard.append(row)
    
    # Navigation buttons row
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"admin_users_page:{page-1}"))
    
    # Page indicator
    total_pages = (len(user_ids) + items_per_page - 1) // items_per_page
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="none"))
    
    if end_idx < len(user_ids):
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_users_page:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Bottom row: Back buttons
    keyboard.append([
        InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user"),
        InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
    ])
    
    return InlineKeyboardMarkup(keyboard)

def admin_user_detail_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """User detail actions - 2x2 grid"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("💵 Add Balance", callback_data=f"admin_add_balance:{user_id}"),
            InlineKeyboardButton("📩 Message", callback_data=f"admin_message_user:{user_id}")
        ],
        # Row 2: Two buttons
        [
            InlineKeyboardButton("💰 Transfer Hold", callback_data=f"admin_transfer_user_hold:{user_id}"),
            InlineKeyboardButton("📊 Details", callback_data=f"admin_user_details:{user_id}")
        ],
        # Row 3: Two buttons
        [
            InlineKeyboardButton("👥 View Referrals", callback_data=f"admin_view_referrals:{user_id}"),
            InlineKeyboardButton("📋 Transactions", callback_data=f"admin_user_transactions:{user_id}")
        ],
        # Row 4: Single button
        [
            InlineKeyboardButton("🔙 Back to Users", callback_data="admin_users:0")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_withdrawals_keyboard() -> InlineKeyboardMarkup:
    """Withdrawal requests management - 2xN grid"""
    requests = WithdrawalManager.get_pending_requests()
    
    keyboard = []
    
    if not requests:
        keyboard.append([InlineKeyboardButton("📭 No Pending Requests", callback_data="none")])
    else:
        # Show first 6 requests in 2x3 grid
        for i in range(0, min(6, len(requests)), 2):
            row = []
            if i < len(requests):
                req1 = requests[i]
                user_id1 = req1['user_id']
                amount1 = req1['amount']
                row.append(InlineKeyboardButton(
                    f"✅ {user_id1}:{amount1}ETB", 
                    callback_data=f"admin_view_withdrawal:{req1['id']}"
                ))
            
            if i + 1 < len(requests):
                req2 = requests[i + 1]
                user_id2 = req2['user_id']
                amount2 = req2['amount']
                row.append(InlineKeyboardButton(
                    f"✅ {user_id2}:{amount2}ETB", 
                    callback_data=f"admin_view_withdrawal:{req2['id']}"
                ))
            
            if row:
                keyboard.append(row)
    
    # Action buttons row
    action_row = []
    if requests:
        action_row.append(InlineKeyboardButton("📊 Stats", callback_data="admin_wd_stats"))
    action_row.append(InlineKeyboardButton("🔙 Admin", callback_data="admin_panel"))
    
    if action_row:
        keyboard.append(action_row)
    
    return InlineKeyboardMarkup(keyboard)

def admin_withdrawal_detail_keyboard(request_id: str) -> InlineKeyboardMarkup:
    """Withdrawal detail actions"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"admin_approve_wd:{request_id}"),
            InlineKeyboardButton("💰 Mark Paid", callback_data=f"admin_mark_paid:{request_id}")
        ],
        # Row 2: Two buttons
        [
            InlineKeyboardButton("❌ Reject", callback_data=f"admin_reject_wd:{request_id}"),
            InlineKeyboardButton("📩 Message User", callback_data=f"admin_msg_wd_user:{request_id}")
        ],
        # Row 3: Single button
        [
            InlineKeyboardButton("🔙 Back to Withdrawals", callback_data="admin_withdrawals")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_accounts_keyboard() -> InlineKeyboardMarkup:
    """Account management keyboard - 2x2 grid"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("➕ Add Account", callback_data="admin_add_account"),
            InlineKeyboardButton("📋 View All", callback_data="admin_view_accounts")
        ],
        # Row 2: Two buttons
        [
            InlineKeyboardButton("✅ Completed", callback_data="admin_completed_accounts"),
            InlineKeyboardButton("📊 Stats", callback_data="admin_account_stats")
        ],
        # Row 3: Single button
        [
            InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_completed_accounts_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    """Completed accounts with pagination"""
    accounts = AccountManager.get_completed_accounts()
    
    items_per_page = 5
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    
    keyboard = []
    
    for acc in accounts[start_idx:end_idx]:
        user_info = acc.get('user_info', {})
        username = user_info.get('username', user_info.get('first_name', 'Unknown'))
        keyboard.append([InlineKeyboardButton(
            f"✅ {acc['first_name']} {acc['last_name']} - 👤{username}",
            callback_data=f"admin_view_account:{acc['account_id']}"
        )])
    
    # Navigation buttons
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ Prev", callback_data=f"admin_completed_acc_page:{page-1}"))
    
    total_pages = (len(accounts) + items_per_page - 1) // items_per_page
    nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="none"))
    
    if end_idx < len(accounts):
        nav_buttons.append(InlineKeyboardButton("Next ▶️", callback_data=f"admin_completed_acc_page:{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    keyboard.append([InlineKeyboardButton("🔙 Accounts Menu", callback_data="admin_accounts")])
    
    return InlineKeyboardMarkup(keyboard)

def admin_hold_transfer_keyboard() -> InlineKeyboardMarkup:
    """Hold transfer options"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("🔄 All Users", callback_data="admin_transfer_all_hold"),
            InlineKeyboardButton("👤 Specific User", callback_data="admin_transfer_select_user")
        ],
        # Row 2: Single button
        [
            InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def admin_settings_keyboard() -> InlineKeyboardMarkup:
    """Admin settings"""
    keyboard = [
        # Row 1: Two buttons
        [
            InlineKeyboardButton("💰 Commission", callback_data="admin_set_commission"),
            InlineKeyboardButton("💵 Min Withdraw", callback_data="admin_set_min_withdraw")
        ],
        # Row 2: Two buttons
        [
            InlineKeyboardButton("🎁 Welcome Bonus", callback_data="admin_set_welcome_bonus"),
            InlineKeyboardButton("📅 Hold Days", callback_data="admin_set_hold_days")
        ],
        # Row 3: Single button
        [
            InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Yes/No confirmation"""
    keyboard = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=yes_data),
            InlineKeyboardButton("❌ No", callback_data=no_data)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    user_id = user.id
    
    # Get or create user
    user_data = UserManager.get_user(
        user_id, 
        username=user.username or "", 
        first_name=user.first_name or ""
    )
    
    # Check for referral
    if context.args:
        ref_code = context.args[0]
        if ref_code.startswith('ref'):
            try:
                referrer_id = int(ref_code[3:])
                if referrer_id != user_id:
                    # Add referral relationship
                    UserManager.add_referral(referrer_id, user_id)
                    
                    # Notify referrer
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 *New Referral!*\n\n"
                                 f"👤 @{user.username or user.first_name} joined using your link!\n"
                                 f"💰 You earned 5 ETB referral bonus!\n"
                                 f"📈 You will also earn {REFERRAL_COMMISSION_PERCENT}% of their earnings.",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            except:
                pass
    
    welcome_msg = (
        f"🎊 *Welcome {user.first_name}!*\n\n"
        f"🤖 *Welcome to EthioFarmer Bot!*\n\n"
        f"💰 *You received {user_data['real_etb']:.1f} ETB welcome bonus!*\n\n"
        f"*📝 How to Earn:*\n"
        f"• Complete Gmail registration tasks\n"
        f"• Earn 10 ETB per completed task\n"
        f"• Claim daily bonus every 24 hours\n"
        f"• Invite friends and earn commissions\n\n"
        f"*👥 Referral Program:*\n"
        f"• Earn 5 ETB per new referral\n"
        f"• Plus {REFERRAL_COMMISSION_PERCENT}% of their earnings\n"
        f"• Lifetime passive income!\n\n"
        f"*💰 Withdrawal:*\n"
        f"• Minimum: {MIN_WITHDRAWAL} ETB\n"
        f"• Hold period: {HOLD_PERIOD_DAYS} day\n"
        f"• Processing: 24-48 hours\n\n"
        f"💬 *Support:* {SUPPORT_USERNAME}\n\n"
        f"👇 *Select an option below:*"
    )
    
    is_admin = user_id == ADMIN_ID
    await update.message.reply_text(
        welcome_msg,
        parse_mode='Markdown',
        reply_markup=home_keyboard(is_admin)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Admin check
    is_admin = user_id == ADMIN_ID
    
    # Route to appropriate handler
    if data == "home":
        await home_menu(query, is_admin)
    elif data == "register":
        await register_account(query, user_id)
    elif data == "balance":
        await show_balance(query, user_id)
    elif data == "referrals":
        await show_referrals(query, user_id)
    elif data == "withdraw":
        await start_withdrawal(query, user_id)
    elif data == "withdraw_telebirr":
        await ask_withdrawal_amount(query, user_id, "telebirr")
    elif data == "withdraw_bank":
        await ask_withdrawal_amount(query, user_id, "bank")
    elif data == "stats":
        await show_stats(query, user_id)
    elif data == "daily_bonus":
        await claim_daily_bonus(query, user_id)
    elif data == "admin_panel":
        await admin_panel(query, user_id)
    elif data.startswith("done:"):
        await handle_done(query, data, user_id)
    elif data.startswith("cancel:"):
        await handle_cancel(query, data, user_id)
    elif data.startswith("admin_"):
        await handle_admin_action(query, data, user_id, context)
    elif data == "copy_ref":
        await copy_referral_link(query, user_id)
    elif data == "share_ref":
        await share_referral(query, user_id)
    elif data == "none":
        await query.answer("ℹ️ Information button", show_alert=False)

async def home_menu(query, is_admin=False):
    """Show home menu"""
    await query.edit_message_text(
        "🏠 *Main Menu*\n\nSelect an option:",
        parse_mode='Markdown',
        reply_markup=home_keyboard(is_admin)
    )

async def register_account(query, user_id):
    """Get account for registration"""
    # Check if user already has pending job
    user_data = UserManager.get_user(user_id, update_info=False)
    
    if user_data.get('pending_job'):
        await query.edit_message_text(
            "⚠️ *You have a pending registration!*\n\n"
            "Please complete or cancel your current task before starting a new one.",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )
        return
    
    # Get available account
    account = AccountManager.get_available_account()
    
    if not account:
        await query.edit_message_text(
            "📭 *No accounts available!*\n\n"
            "All registration tasks are currently assigned.\n"
            "Please check back later or contact admin.",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )
        return
    
    # Assign account to user
    AccountManager.assign_account_to_user(account['account_id'], user_id)
    
    # Update user's pending job
    UserManager.update_user(user_id, {'pending_job': account['account_id']})
    
    # Show account details
    reg_message = (
        f"📝 *Account Registration Task*\n\n"
        f"〰〰〰〰〰〰〰〰〰〰〰〰〰\n"
        f"*Account Details:*\n\n"
        f"*First Name:* `{account['first_name']}`\n"
        f"*Last Name:* `{account['last_name']}`\n"
        f"*Email:* `{account['email']}`\n"
        f"*Password:* `{account['password']}`\n\n"
        f"〰〰〰〰〰〰〰〰〰〰〰〰〰\n\n"
        f"*💰 Reward:* {COMMISSION_PER_JOB} ETB\n"
        f"*⏱️ Hold Period:* {HOLD_PERIOD_DAYS} day\n\n"
        f"*📋 Instructions:*\n"
        f"1. Copy the information above\n"
        f"2. Go to Gmail registration\n"
        f"3. Complete the registration\n"
        f"4. Click '✅ Task Completed' below\n\n"
        f"⚠️ *Do not share these details!*"
    )
    
    await query.edit_message_text(
        reg_message,
        parse_mode='Markdown',
        reply_markup=registration_keyboard(account['account_id'])
    )

async def handle_done(query, data, user_id):
    """Handle registration completion"""
    account_id = data.split(":")[1]
    
    # Complete the account
    success = AccountManager.complete_account(account_id, user_id)
    
    if success:
        # Update user balance and stats
        user_data = UserManager.get_user(user_id, update_info=False)
        
        # Add hold ETB
        user_data['hold_etb'] += COMMISSION_PER_JOB
        user_data['total_earned'] += COMMISSION_PER_JOB
        user_data['completed_jobs'] += 1
        user_data['pending_job'] = None
        
        # Add experience
        user_data['experience'] = min(100, user_data.get('experience', 0) + 10)
        
        # Level up check
        if user_data['experience'] >= 100:
            user_data['level'] = user_data.get('level', 1) + 1
            user_data['experience'] = 0
        
        UserManager.update_user(user_id, user_data)
        
        # Add transaction record
        TransactionManager.add_transaction(
            user_id=user_id,
            amount=COMMISSION_PER_JOB,
            type='registration',
            description=f"Account registration: {account_id}"
        )
        
        # Update system stats
        settings = load_db(SETTINGS_DB)
        settings['total_earned'] += COMMISSION_PER_JOB
        settings['total_jobs'] += 1
        save_db(SETTINGS_DB, settings)
        
        # Check for referrer and add commission
        users = UserManager.get_all_users()
        for uid, udata in users.items():
            if str(user_id) in udata.get('referrals', []):
                UserManager.add_referral_earning(int(uid), COMMISSION_PER_JOB)
                break
        
        success_msg = (
            f"✅ *Registration Completed Successfully!*\n\n"
            f"💰 *+{COMMISSION_PER_JOB} ETB added to your account*\n"
            f"⏳ *Hold Balance:* {user_data['hold_etb']:.1f} ETB\n"
            f"📊 *Total Jobs:* {user_data['completed_jobs']}\n"
            f"💎 *Level:* {user_data.get('level', 1)}\n\n"
            f"*⏰ Funds available in:* {HOLD_PERIOD_DAYS} day\n"
            f"*🎯 Complete more tasks to earn more!*"
        )
        
        await query.edit_message_text(
            success_msg,
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ *Error completing registration!*\n"
            "Please contact admin for assistance.",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )

async def handle_cancel(query, data, user_id):
    """Handle registration cancellation"""
    account_id = data.split(":")[1]
    
    # Cancel the account
    success = AccountManager.cancel_account(account_id)
    
    if success:
        # Update user's pending job
        UserManager.update_user(user_id, {'pending_job': None})
        
        await query.edit_message_text(
            "❌ *Registration Cancelled*\n\n"
            "The account has been returned to available pool.\n"
            "You can try again with a new account.",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )
    else:
        await query.edit_message_text(
            "⚠️ *Cancellation Error*\n"
            "Please contact admin.",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )

async def show_balance(query, user_id):
    """Show user balance"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    balance_msg = (
        f"💰 *Your Balance*\n\n"
        f"💵 *Available ETB:* `{user_data['real_etb']:.1f}`\n"
        f"⏳ *Hold ETB:* `{user_data['hold_etb']:.1f}`\n"
        f"💰 *Total Earned:* `{user_data['total_earned']:.1f}`\n\n"
        f"📊 *Statistics:*\n"
        f"📝 Completed Jobs: `{user_data['completed_jobs']}`\n"
        f"👥 Referrals: `{user_data['referral_count']}`\n"
        f"💸 Referral Earnings: `{user_data['referral_earnings']:.1f}` ETB\n"
        f"📤 Withdrawals: `{user_data['withdrawals']}`\n"
        f"💳 Total Withdrawn: `{user_data['total_withdrawn']:.1f}` ETB\n\n"
        f"💎 *Level:* {user_data.get('level', 1)}\n"
        f"⭐ *Experience:* {user_data.get('experience', 0)}/100\n\n"
        f"📅 *Member Since:* {datetime.fromisoformat(user_data['join_date']).strftime('%d %b %Y')}"
    )
    
    await query.edit_message_text(
        balance_msg,
        parse_mode='Markdown',
        reply_markup=back_home_keyboard()
    )

async def show_referrals(query, user_id):
    """Show referrals information"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    ref_msg = (
        f"👥 *Referral Program*\n\n"
        f"💰 *Earn 5 ETB + {REFERRAL_COMMISSION_PERCENT}% of referrals' earnings!*\n\n"
        f"🔗 *Your Referral Link:*\n`{referral_link}`\n\n"
        f"👥 *Your Referrals:* `{user_data['referral_count']}`\n"
        f"💵 *Referral Earnings:* `{user_data['referral_earnings']:.1f}` ETB\n\n"
        f"*How it works:*\n"
        f"1. Share your referral link with friends\n"
        f"2. When they join, you get 5 ETB instantly!\n"
        f"3. When they complete tasks, you get {REFERRAL_COMMISSION_PERCENT}% commission\n"
        f"4. Lifetime passive income!\n\n"
        f"*Example:* If your referral earns 100 ETB, you get 10 ETB!"
    )
    
    await query.edit_message_text(
        ref_msg,
        parse_mode='Markdown',
        reply_markup=referrals_keyboard()
    )

# ==================== FIXED WITHDRAWAL FLOW ====================
async def start_withdrawal(query, user_id):
    """Start withdrawal process - FIXED VERSION"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    if user_data['real_etb'] < MIN_WITHDRAWAL:
        await query.edit_message_text(
            f"❌ *Minimum withdrawal is {MIN_WITHDRAWAL} ETB!*\n\n"
            f"💰 Your available balance: {user_data['real_etb']:.1f} ETB\n"
            f"⏳ You need: {MIN_WITHDRAWAL - user_data['real_etb']:.1f} more ETB\n\n"
            "Complete more tasks to reach minimum withdrawal!",
            parse_mode='Markdown',
            reply_markup=back_home_keyboard()
        )
        return
    
    await query.edit_message_text(
        f"📤 *Withdraw Funds*\n\n"
        f"💰 *Available Balance:* {user_data['real_etb']:.1f} ETB\n"
        f"📝 *Minimum Withdrawal:* {MIN_WITHDRAWAL} ETB\n\n"
        "Select withdrawal method:",
        parse_mode='Markdown',
        reply_markup=withdraw_method_keyboard()
    )

async def ask_withdrawal_amount(query, user_id, method: str):
    """Ask for withdrawal amount - FIXED VERSION"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    await query.edit_message_text(
        f"📤 *Withdraw to {method.upper()}*\n\n"
        f"💰 *Available Balance:* {user_data['real_etb']:.1f} ETB\n"
        f"📝 *Minimum:* {MIN_WITHDRAWAL} ETB\n\n"
        f"💵 *Enter withdrawal amount (ETB):*\n"
        f"Example: `50` or `100.5`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    # Store method in context
    context = query.message._bot.application
    context.user_data[user_id] = {
        'withdraw_step': 'ask_amount',
        'method': method,
        'max_amount': user_data['real_etb']
    }

# ==================== HANDLE WITHDRAWAL MESSAGES ====================
async def handle_withdrawal_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal process messages - FIXED VERSION"""
    user_id = update.effective_user.id
    text = update.message.text
    
    if user_id not in context.user_data:
        await update.message.reply_text(
            "Please use the menu buttons to start withdrawal.",
            reply_markup=home_keyboard(user_id == ADMIN_ID)
        )
        return
    
    user_data = context.user_data[user_id]
    
    if user_data.get('withdraw_step') == 'ask_amount':
        # Validate amount
        try:
            amount = float(text.strip())
            
            if amount < MIN_WITHDRAWAL:
                await update.message.reply_text(
                    f"❌ *Minimum withdrawal is {MIN_WITHDRAWAL} ETB!*\n\n"
                    f"Please enter at least {MIN_WITHDRAWAL} ETB.",
                    parse_mode='Markdown'
                )
                return
            
            if amount > user_data['max_amount']:
                await update.message.reply_text(
                    f"❌ *Insufficient balance!*\n\n"
                    f"Available: {user_data['max_amount']:.1f} ETB\n"
                    f"Requested: {amount:.1f} ETB\n\n"
                    f"Please enter a smaller amount.",
                    parse_mode='Markdown'
                )
                return
            
            context.user_data[user_id]['amount'] = amount
            context.user_data[user_id]['withdraw_step'] = 'ask_name'
            
            await update.message.reply_text(
                "👤 *Enter Your Full Name:*\n\n"
                "Please enter your full name as registered:\n"
                "Example: *John Smith*\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid amount!*\n\n"
                "Please enter a valid number.\n"
                "Example: `50` or `100.5`",
                parse_mode='Markdown'
            )
    
    elif user_data.get('withdraw_step') == 'ask_name':
        # Validate name
        if len(text.strip()) < 3:
            await update.message.reply_text(
                "⚠️ *Please enter a valid name!*\n\n"
                "Minimum 3 characters required.",
                parse_mode='Markdown'
            )
            return
        
        context.user_data[user_id]['name'] = text.strip()
        context.user_data[user_id]['withdraw_step'] = 'ask_account'
        
        method = user_data.get('method', 'telebirr')
        
        if method == 'telebirr':
            await update.message.reply_text(
                "📱 *Enter Your Telebirr Number:*\n\n"
                "*Format:* 09XXXXXXXX or +2519XXXXXXXX\n"
                "Example: *0912345678*\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
        else:  # bank
            await update.message.reply_text(
                "🏦 *Enter Your Bank Account Details:*\n\n"
                "Include:\n"
                "• Bank name\n"
                "• Account number\n"
                "• Account holder name\n\n"
                "Example:\n"
                "*Commercial Bank of Ethiopia | 100023456789 | John Smith*\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
    
    elif user_data.get('withdraw_step') == 'ask_account':
        method = user_data.get('method', 'telebirr')
        account = text.strip()
        
        # Validate based on method
        if method == 'telebirr':
            # Validate Telebirr number
            if not (account.startswith('09') and len(account) == 10 and account[2:].isdigit()) and \
               not (account.startswith('+2519') and len(account) == 13 and account[5:].isdigit()):
                await update.message.reply_text(
                    "⚠️ *Invalid Telebirr number!*\n\n"
                    "Please use format:\n"
                    "*09XXXXXXXX* or *+2519XXXXXXXX*\n\n"
                    "Example: *0912345678*\n"
                    "Type /cancel to cancel",
                    parse_mode='Markdown'
                )
                return
        
        name = user_data['name']
        amount = user_data['amount']
        
        # Create withdrawal request
        request_id = WithdrawalManager.create_request(user_id, name, account, amount, method)
        
        # Get user info for message
        current_user = UserManager.get_user(user_id, update_info=False)
        new_balance = current_user['real_etb']
        
        # Send beautiful confirmation to user
        if method == 'telebirr':
            detail_msg = f"📱 *TeleBirr Number:* `{account}`"
        else:
            detail_msg = f"🏦 *Bank Details:* {account}"
        
        confirmation_msg = (
            f"✨ *Withdrawal Request Submitted Successfully!*\n\n"
            f"✅ *Request ID:* `{request_id}`\n"
            f"💰 *Amount:* {amount:.1f} ETB\n"
            f"👤 *Name:* {name}\n"
            f"{detail_msg}\n"
            f"📊 *Payment Method:* {method.upper()}\n\n"
            f"📋 *Request Status:* ⏳ PENDING\n"
            f"⏰ *Processing Time:* 24-48 hours\n"
            f"💵 *New Balance:* {new_balance:.1f} ETB\n\n"
            f"📞 *Support:* {SUPPORT_USERNAME}\n"
            f"📅 *Submitted:* {datetime.now().strftime('%d %b %Y, %H:%M')}\n\n"
            f"Thank you for using {BOT_USERNAME}! 🎉"
        )
        
        await update.message.reply_text(
            confirmation_msg,
            parse_mode='Markdown',
            reply_markup=confirm_withdrawal_keyboard(request_id)
        )
        
        # Forward to admin
        try:
            admin_msg = (
                f"📤 *NEW WITHDRAWAL REQUEST*\n\n"
                f"🆔 *Request ID:* `{request_id}`\n"
                f"👤 *User ID:* `{user_id}`\n"
                f"📛 *Name:* {name}\n"
                f"💰 *Amount:* {amount:.1f} ETB\n"
                f"📋 *Method:* {method.upper()}\n"
            )
            
            if method == 'telebirr':
                admin_msg += f"📱 *TeleBirr:* `{account}`\n"
            else:
                admin_msg += f"🏦 *Bank Details:* {account}\n"
            
            admin_msg += (
                f"📅 *Date:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"💵 *User Balance:* {new_balance:.1f} ETB\n\n"
                f"Use Admin Panel to process this request."
            )
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        # Clear user data
        del context.user_data[user_id]
async def claim_daily_bonus(query, user_id):
    """Claim daily bonus"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    # Check if already claimed today
    last_bonus = user_data.get('last_daily_bonus')
    if last_bonus:
        last_date = datetime.fromisoformat(last_bonus).date()
        if last_date == datetime.now().date():
            await query.edit_message_text(
                "🎁 *Daily Bonus Already Claimed!*\n\n"
                "You have already claimed your daily bonus today.\n"
                "Come back tomorrow for more rewards!",
                parse_mode='Markdown',
                reply_markup=back_home_keyboard()
            )
            return
    
    # Calculate bonus
    settings = load_db(SETTINGS_DB)
    base_bonus = settings.get('daily_bonus', 5.0)
    
    # Streak bonus
    streak = user_data.get('streak_days', 0) + 1
    streak_bonus = min(streak * 0.5, 10.0)  # Max 10 ETB streak bonus
    
    total_bonus = base_bonus + streak_bonus
    
    # Update user
    user_data['real_etb'] += total_bonus
    user_data['total_earned'] += total_bonus
    user_data['last_daily_bonus'] = datetime.now().isoformat()
    user_data['streak_days'] = streak
    UserManager.update_user(user_id, user_data)
    
    # Log transaction
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=total_bonus,
        type='daily_bonus',
        description=f"Daily bonus (Streak: {streak} days)"
    )
    
    bonus_msg = (
        f"🎁 *Daily Bonus Claimed!*\n\n"
        f"💰 *Bonus Earned:* {total_bonus:.1f} ETB\n"
        f"   ├─ Base Bonus: {base_bonus:.1f} ETB\n"
        f"   └─ Streak Bonus: {streak_bonus:.1f} ETB\n\n"
        f"📈 *Current Streak:* {streak} days\n"
        f"💵 *New Balance:* {user_data['real_etb']:.1f} ETB\n\n"
        f"Come back tomorrow for more rewards!"
    )
    
    await query.edit_message_text(
        bonus_msg,
        parse_mode='Markdown',
        reply_markup=back_home_keyboard()
    )

async def show_stats(query, user_id):
    """Show user statistics"""
    user_data = UserManager.get_user(user_id, update_info=False)
    account_stats = AccountManager.get_account_stats()
    
    # Calculate rank
    users = UserManager.get_all_users()
    sorted_users = sorted(users.values(), key=lambda x: x.get('total_earned', 0), reverse=True)
    rank = next((i+1 for i, u in enumerate(sorted_users) if u.get('id') == user_id), 0)
    
    stats_msg = (
        f"📊 *Your Statistics*\n\n"
        f"🏆 *Rank:* #{rank} out of {len(users)} users\n"
        f"💎 *Level:* {user_data.get('level', 1)}\n"
        f"⭐ *Experience:* {user_data.get('experience', 0)}/100\n\n"
        f"📝 *Tasks Completed:* {user_data['completed_jobs']}\n"
        f"⏳ *Pending Tasks:* {1 if user_data.get('pending_job') else 0}\n"
        f"🔥 *Daily Streak:* {user_data.get('streak_days', 0)} days\n\n"
        f"👥 *Referrals:* {user_data['referral_count']}\n"
        f"💰 *Referral Earnings:* {user_data['referral_earnings']:.1f} ETB\n\n"
        f"📤 *Withdrawals:* {user_data['withdrawals']}\n"
        f"💸 *Total Withdrawn:* {user_data['total_withdrawn']:.1f} ETB\n\n"
        f"💵 *Total Earned:* {user_data['total_earned']:.1f} ETB\n\n"
        f"📅 *Member Since:* {datetime.fromisoformat(user_data['join_date']).strftime('%d %b %Y')}\n\n"
        f"*System Status:*\n"
        f"📝 Available Tasks: {account_stats.get('available', 0)}\n"
        f"✅ Today's Completions: {account_stats.get('today_completed', 0)}"
    )
    
    await query.edit_message_text(
        stats_msg,
        parse_mode='Markdown',
        reply_markup=back_home_keyboard()
    )

async def copy_referral_link(query, user_id):
    """Copy referral link to clipboard"""
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    await query.answer(f"📋 Copied to clipboard:\n{referral_link}", show_alert=True)

async def share_referral(query, user_id):
    """Share referral link"""
    referral_link = f"https://t.me/{BOT_USERNAME}?start=ref{user_id}"
    
    share_text = (
        f"💰 *Earn Money with EthioFarmer Bot!*\n\n"
        f"Join using my referral link and get 5 ETB welcome bonus!\n\n"
        f"🔗 {referral_link}\n\n"
        f"*Features:*\n"
        f"• Earn 10 ETB per Gmail registration\n"
        f"• Daily bonus every 24 hours\n"
        f"• Referral commissions ({REFERRAL_COMMISSION_PERCENT}%)\n"
        f"• Withdraw to Telebirr (Min: {MIN_WITHDRAWAL} ETB)\n\n"
        f"Support: {SUPPORT_USERNAME}"
    )
    
    await query.edit_message_text(
        share_text,
        parse_mode='Markdown',
        reply_markup=referrals_keyboard()
    )

# ==================== ADMIN HANDLERS ====================
async def admin_panel(query, user_id):
    """Show admin panel"""
    if user_id != ADMIN_ID:
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    admin_msg = (
        "🛠 *Admin Control Panel*\n\n"
        "*Quick Stats:*\n"
        f"👥 Users: {UserManager.get_user_count()}\n"
        f"💰 Total Earned: {load_db(SETTINGS_DB).get('total_earned', 0):.1f} ETB\n"
        f"📝 Available Tasks: {AccountManager.get_account_stats().get('available', 0)}\n\n"
        "👇 *Select an option below:*"
    )
    
    await query.edit_message_text(
        admin_msg,
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def handle_admin_action(query, data, user_id, context):
    """Handle admin button actions"""
    if user_id != ADMIN_ID:
        await query.answer("❌ Access denied!", show_alert=True)
        return
    
    # Handle all admin actions
    if data == "admin_stats":
        await show_admin_stats(query)
    elif data == "admin_users":
        await show_admin_users(query, 0)
    elif data.startswith("admin_users_page:"):
        page = int(data.split(":")[1])
        await show_admin_users(query, page)
    elif data.startswith("admin_view_user:"):
        target_id = int(data.split(":")[1])
        await show_user_info(query, target_id)
    elif data == "admin_hold_transfer":
        await admin_hold_transfer_menu(query)
    elif data == "admin_transfer_all_hold":
        await transfer_all_hold_to_real(query)
    elif data == "admin_transfer_select_user":
        await select_user_for_hold_transfer(query, context)
    elif data.startswith("admin_transfer_user_hold:"):
        target_id = int(data.split(":")[1])
        await transfer_user_hold_to_real(query, target_id)
    elif data == "admin_withdrawals":
        await show_withdrawal_requests(query)
    elif data.startswith("admin_view_withdrawal:"):
        req_id = data.split(":")[1]
        await show_withdrawal_detail(query, req_id)
    elif data.startswith("admin_approve_wd:"):
        req_id = data.split(":")[1]
        await approve_withdrawal(query, req_id)
    elif data.startswith("admin_mark_paid:"):
        req_id = data.split(":")[1]
        await mark_withdrawal_paid(query, req_id, context)
    elif data.startswith("admin_reject_wd:"):
        req_id = data.split(":")[1]
        await reject_withdrawal_prompt(query, req_id, context)
    elif data.startswith("admin_msg_wd_user:"):
        req_id = data.split(":")[1]
        await message_withdrawal_user(query, req_id, context)
    elif data == "admin_wd_stats":
        await withdrawal_stats(query)
    elif data == "admin_accounts":
        await account_management(query)
    elif data == "admin_add_account":
        await add_account_prompt(query, context)
    elif data == "admin_view_accounts":
        await view_all_accounts(query)
    elif data == "admin_completed_accounts":
        await show_completed_accounts(query, 0)
    elif data.startswith("admin_completed_acc_page:"):
        page = int(data.split(":")[1])
        await show_completed_accounts(query, page)
    elif data.startswith("admin_view_account:"):
        account_id = data.split(":")[1]
        await show_account_detail(query, account_id)
    elif data == "admin_account_stats":
        await show_account_stats(query)
    elif data.startswith("admin_add_balance:"):
        target_id = int(data.split(":")[1])
        await add_balance_prompt(query, target_id, context)
    elif data.startswith("admin_message_user:"):
        target_id = int(data.split(":")[1])
        await message_user_prompt(query, target_id, context)
    elif data.startswith("admin_user_details:"):
        target_id = int(data.split(":")[1])
        await user_detailed_info(query, target_id)
    elif data.startswith("admin_view_referrals:"):
        target_id = int(data.split(":")[1])
        await show_user_referrals(query, target_id)
    elif data.startswith("admin_user_transactions:"):
        target_id = int(data.split(":")[1])
        await show_user_transactions(query, target_id)
    elif data == "admin_broadcast":
        await broadcast_prompt(query, context)
    elif data == "admin_messages":
        await admin_messages_menu(query)
    elif data == "admin_settings":
        await admin_settings_menu(query)
    elif data == "admin_search_user":
        await search_user_prompt(query, context)
    elif data == "admin_set_commission":
        await set_commission_prompt(query, context)
    elif data == "admin_set_min_withdraw":
        await set_min_withdraw_prompt(query, context)
    elif data == "admin_set_welcome_bonus":
        await set_welcome_bonus_prompt(query, context)
    elif data == "admin_set_hold_days":
        await set_hold_days_prompt(query, context)

async def show_admin_stats(query):
    """Show system statistics"""
    users = UserManager.get_all_users()
    total_users = len(users)
    active_users = UserManager.get_active_users_count()
    total_balance = UserManager.get_total_balance()
    account_stats = AccountManager.get_account_stats()
    wd_stats = WithdrawalManager.get_stats()
    settings = load_db(SETTINGS_DB)
    
    # Today's stats
    today = datetime.now().date()
    today_users = len([u for u in users.values() if datetime.fromisoformat(u['join_date']).date() == today])
    today_earnings = sum(u['total_earned'] for u in users.values() if datetime.fromisoformat(u.get('last_active', u['join_date'])).date() == today)
    
    stats_msg = (
        f"📊 *System Statistics*\n\n"
        f"👥 *Users:* {total_users}\n"
        f"   ├─ Active (7 days): {active_users}\n"
        f"   ├─ New Today: {today_users}\n"
        f"   └─ Banned: {len([u for u in users.values() if u.get('banned')])}\n\n"
        f"💰 *Balance Overview:*\n"
        f"   ├─ Real ETB: {total_balance['real']:.1f}\n"
        f"   └─ Hold ETB: {total_balance['hold']:.1f}\n\n"
        f"📝 *Account Status:*\n"
        f"   ├─ Total: {account_stats['total']}\n"
        f"   ├─ Available: {account_stats['available']}\n"
        f"   ├─ Assigned: {account_stats['assigned']}\n"
        f"   └─ Completed: {account_stats['completed']}\n"
        f"       └─ Today: {account_stats['today_completed']}\n\n"
        f"📤 *Withdrawals:*\n"
        f"   ├─ Total: {wd_stats['total']}\n"
        f"   ├─ Pending: {wd_stats['pending']}\n"
        f"   ├─ Approved: {wd_stats['approved']}\n"
        f"   ├─ Paid: {wd_stats['paid']}\n"
        f"   └─ Amount: {wd_stats['total_amount']:.1f} ETB\n"
        f"       └─ Today: {wd_stats['today_amount']:.1f} ETB\n\n"
        f"📈 *System Totals:*\n"
        f"   ├─ Total Earned: {settings.get('total_earned', 0):.1f} ETB\n"
        f"   ├─ Total Withdrawn: {settings.get('total_withdrawn', 0):.1f} ETB\n"
        f"   ├─ Total Jobs: {settings.get('total_jobs', 0)}\n"
        f"   └─ Today's Earnings: {today_earnings:.1f} ETB"
    )
    
    await query.edit_message_text(
        stats_msg,
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def show_admin_users(query, page=0):
    """Show users list"""
    users = UserManager.get_all_users()
    total_users = len(users)
    items_per_page = 8
    total_pages = (total_users + items_per_page - 1) // items_per_page
    
    header = f"👥 *All Users* - Page {page + 1}/{total_pages}\nTotal: {total_users}\n\n"
    
    await query.edit_message_text(
        header,
        parse_mode='Markdown',
        reply_markup=admin_users_keyboard(page)
    )

async def show_user_info(query, user_id):
    """Show user information"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    user_msg = (
        f"👤 *User Information*\n\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📛 *Name:* {user_data['first_name']}\n"
        f"👤 *Username:* @{user_data['username']}\n\n"
        f"💰 *Balance:*\n"
        f"   ├─ Real ETB: {user_data['real_etb']:.1f}\n"
        f"   └─ Hold ETB: {user_data['hold_etb']:.1f}\n\n"
        f"📊 *Stats:*\n"
        f"   ├─ Jobs: {user_data['completed_jobs']}\n"
        f"   ├─ Referrals: {user_data['referral_count']}\n"
        f"   └─ Withdrawals: {user_data['withdrawals']}\n\n"
        f"📅 *Joined:* {datetime.fromisoformat(user_data['join_date']).strftime('%d %b %Y %H:%M')}\n"
        f"📅 *Last Active:* {datetime.fromisoformat(user_data['last_active']).strftime('%d %b %Y %H:%M')}"
    )
    
    await query.edit_message_text(
        user_msg,
        parse_mode='Markdown',
        reply_markup=admin_user_detail_keyboard(user_id)
    )

async def admin_hold_transfer_menu(query):
    """Show hold transfer menu"""
    await query.edit_message_text(
        "💰 *Hold to Real Transfer*\n\n"
        "Select transfer option:",
        parse_mode='Markdown',
        reply_markup=admin_hold_transfer_keyboard()
    )

async def transfer_all_hold_to_real(query):
    """Transfer all hold ETB to real ETB for all users"""
    users = UserManager.get_all_users()
    total_transferred = 0
    users_affected = 0
    
    for user_id_str, user_data in users.items():
        hold_etb = user_data.get('hold_etb', 0)
        if hold_etb > 0:
            user_id = int(user_id_str)
            new_real = user_data.get('real_etb', 0) + hold_etb
            
            UserManager.update_user(user_id, {
                'real_etb': new_real,
                'hold_etb': 0
            })
            
            total_transferred += hold_etb
            users_affected += 1
            
            # Add transaction record
            TransactionManager.add_transaction(
                user_id=user_id,
                amount=hold_etb,
                type='hold_to_real',
                description='Hold balance transferred to real'
            )
    
    # Update settings
    settings = load_db(SETTINGS_DB)
    settings['last_hold_transfer'] = datetime.now().isoformat()
    save_db(SETTINGS_DB, settings)
    
    await query.edit_message_text(
        f"✅ *Hold ETB Transferred!*\n\n"
        f"💰 Total Amount: {total_transferred:.1f} ETB\n"
        f"👥 Users Affected: {users_affected}\n"
        f"📅 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"All hold balances are now available for withdrawal.",
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def select_user_for_hold_transfer(query, context):
    """Prompt admin to select user for hold transfer"""
    await query.edit_message_text(
        "👤 *Select User for Hold Transfer*\n\n"
        "Enter the User ID you want to transfer hold balance for:\n\n"
        "Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['hold_transfer_select'] = True

async def transfer_user_hold_to_real(query, user_id):
    """Transfer hold to real for specific user"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    hold_etb = user_data.get('hold_etb', 0)
    if hold_etb <= 0:
        await query.edit_message_text(
            f"ℹ️ *No Hold Balance*\n\n"
            f"User {user_id} has no hold balance to transfer.\n"
            f"Current hold: {hold_etb:.1f} ETB",
            parse_mode='Markdown',
            reply_markup=admin_user_detail_keyboard(user_id)
        )
        return
    
    new_real = user_data.get('real_etb', 0) + hold_etb
    
    UserManager.update_user(user_id, {
        'real_etb': new_real,
        'hold_etb': 0
    })
    
    # Add transaction record
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=hold_etb,
        type='hold_to_real',
        description='Hold balance transferred to real by admin'
    )
    
    # Notify user
    try:
        await query.bot.send_message(
            chat_id=user_id,
            text=f"💰 *Hold Balance Transferred!*\n\n"
                 f"✅ Amount: {hold_etb:.1f} ETB\n"
                 f"📈 New Balance: {new_real:.1f} ETB\n"
                 f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                 f"Your hold balance is now available for withdrawal!",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
    
    await query.edit_message_text(
        f"✅ *Hold Balance Transferred!*\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"💰 Amount: {hold_etb:.1f} ETB\n"
        f"📈 New Balance: {new_real:.1f} ETB\n\n"
        f"User has been notified.",
        parse_mode='Markdown',
        reply_markup=admin_user_detail_keyboard(user_id)
    )

async def show_withdrawal_requests(query):
    """Show pending withdrawal requests"""
    requests = WithdrawalManager.get_pending_requests()
    
    if not requests:
        await query.edit_message_text(
            "📭 *No pending withdrawal requests*",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        return
    
    total_amount = sum(req['amount'] for req in requests)
    
    header = (
        f"📤 *Pending Withdrawal Requests*\n\n"
        f"📊 Total: {len(requests)} requests\n"
        f"💰 Amount: {total_amount:.1f} ETB\n\n"
        f"👇 *Click to view details:*"
    )
    
    await query.edit_message_text(
        header,
        parse_mode='Markdown',
        reply_markup=admin_withdrawals_keyboard()
    )

async def show_withdrawal_detail(query, request_id):
    """Show withdrawal request details"""
    withdraws = load_db(WITHDRAW_DB)
    req_data = withdraws.get(request_id)
    
    if not req_data:
        await query.edit_message_text(
            "❌ *Request not found!*",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        return
    
    # Get user info
    user_data = UserManager.get_user(req_data['user_id'], update_info=False)
    
    detail_msg = (
        f"📋 *Withdrawal Request Details*\n\n"
        f"🆔 *Request ID:* `{request_id}`\n"
        f"👤 *User:* {user_data['first_name']} (@{user_data['username']})\n"
        f"🆔 *User ID:* `{req_data['user_id']}`\n\n"
        f"💰 *Amount:* {req_data['amount']:.1f} ETB\n"
        f"📱 *TeleBirr:* {req_data['telebirr']}\n"
        f"📛 *Name:* {req_data['name']}\n\n"
        f"📅 *Created:* {datetime.fromisoformat(req_data['created_at']).strftime('%d %b %Y %H:%M')}\n"
        f"📊 *Status:* {req_data['status'].upper()}"
    )
    
    await query.edit_message_text(
        detail_msg,
        parse_mode='Markdown',
        reply_markup=admin_withdrawal_detail_keyboard(request_id)
    )

async def approve_withdrawal(query, request_id):
    """Approve withdrawal request"""
    success = WithdrawalManager.approve_request(request_id, query.from_user.id)
    
    if success:
        # Notify user
        withdraws = load_db(WITHDRAW_DB)
        req_data = withdraws.get(request_id)
        
        if req_data:
            user_id = req_data['user_id']
            amount = req_data['amount']
            
            try:
                await query.bot.send_message(
                    chat_id=user_id,
                    text=f"✅ *Withdrawal Approved!*\n\n"
                         f"💰 Amount: {amount:.1f} ETB\n"
                         f"📱 Telebirr: {req_data['telebirr']}\n"
                         f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                         f"Your withdrawal has been approved and will be processed within 24 hours.\n"
                         f"For any issues, contact {SUPPORT_USERNAME}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        
        await query.edit_message_text(
            f"✅ *Withdrawal Approved!*\n\n"
            f"📋 Request ID: {request_id}\n"
            f"💰 Amount: {req_data['amount']:.1f} ETB\n"
            f"👤 User: {req_data.get('name', 'N/A')}\n\n"
            f"User has been notified.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ *Error approving withdrawal!*",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )

async def mark_withdrawal_paid(query, request_id, context):
    """Mark withdrawal as paid"""
    context.user_data['mark_paid_id'] = request_id
    
    await query.edit_message_text(
        "💰 *Mark as Paid*\n\n"
        "Enter payment details/notes:\n"
        "Example: `Transaction ID: 123456`\n\n"
        "Type /cancel to cancel",
        parse_mode='Markdown'
    )

async def reject_withdrawal_prompt(query, request_id, context):
    """Prompt for rejection reason"""
    context.user_data['reject_request_id'] = request_id
    
    await query.edit_message_text(
        "📝 *Enter rejection reason:*\n\n"
        "Send the reason for rejecting this withdrawal request.\n\n"
        "Type /cancel to cancel",
        parse_mode='Markdown'
    )

async def message_withdrawal_user(query, request_id, context):
    """Message user about withdrawal"""
    withdraws = load_db(WITHDRAW_DB)
    req_data = withdraws.get(request_id)
    
    if req_data:
        context.user_data['message_withdrawal_user'] = req_data['user_id']
        
        await query.edit_message_text(
            f"📩 *Message User About Withdrawal*\n\n"
            f"👤 User ID: `{req_data['user_id']}`\n"
            f"💰 Amount: {req_data['amount']:.1f} ETB\n\n"
            f"Send your message to this user:\n\n"
            f"Type /cancel to cancel",
            parse_mode='Markdown'
        )

async def withdrawal_stats(query):
    """Show withdrawal statistics"""
    wd_stats = WithdrawalManager.get_stats()
    
    stats_msg = (
        f"📤 *Withdrawal Statistics*\n\n"
        f"📊 Total Requests: {wd_stats['total']}\n"
        f"⏳ Pending: {wd_stats['pending']}\n"
        f"✅ Approved: {wd_stats['approved']}\n"
        f"💰 Paid: {wd_stats.get('paid', 0)}\n"
        f"❌ Rejected: {wd_stats['rejected']}\n\n"
        f"💵 Total Amount: {wd_stats['total_amount']:.1f} ETB\n"
        f"📅 Today's Amount: {wd_stats['today_amount']:.1f} ETB\n\n"
        f"📈 Success Rate: {(wd_stats['paid'] / wd_stats['total'] * 100 if wd_stats['total'] > 0 else 0):.1f}%"
    )
    
    await query.edit_message_text(
        stats_msg,
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def account_management(query):
    """Show account management"""
    stats = AccountManager.get_account_stats()
    
    accounts_msg = (
        f"📝 *Account Management*\n\n"
        f"📊 *Statistics:*\n"
        f"├─ Total Accounts: {stats['total']}\n"
        f"├─ Available: {stats['available']}\n"
        f"├─ Assigned: {stats['assigned']}\n"
        f"└─ Completed: {stats['completed']}\n"
        f"    └─ Today: {stats['today_completed']}\n\n"
        f"*Options:*\n"
        f"• Add new accounts manually\n"
        f"• View all accounts\n"
        f"• View completed accounts\n"
        f"• View statistics"
    )
    
    await query.edit_message_text(
        accounts_msg,
        parse_mode='Markdown',
        reply_markup=admin_accounts_keyboard()
    )

async def add_account_prompt(query, context):
    """Prompt to add new account"""
    await query.edit_message_text(
        "➕ *Add New Account*\n\n"
        "Send account details in this format:\n\n"
        "`first_name|last_name|email|password`\n\n"
        "*Example:*\n"
        "`John|Doe|john@gmail.com|Pass1234`\n\n"
        "Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['add_account'] = True

async def view_all_accounts(query):
    """View all accounts"""
    accounts = AccountManager.get_all_accounts()
    
    if not accounts:
        await query.edit_message_text(
            "📭 *No accounts in database*",
            parse_mode='Markdown',
            reply_markup=admin_accounts_keyboard()
        )
        return
    
    # Show account stats
    stats = AccountManager.get_account_stats()
    
    accounts_list = []
    for acc_id, acc_data in list(accounts.items())[:15]:  # Show first 15
        status_emoji = {
            'available': '🟢',
            'assigned': '🟡',
            'completed': '✅',
            'cancelled': '❌'
        }.get(acc_data['status'], '❓')
        
        assigned_to = acc_data.get('assigned_to', 'None')
        accounts_list.append(
            f"{status_emoji} *{acc_id[:8]}...*\n"
            f"   👤 {acc_data['first_name']} {acc_data['last_name']}\n"
            f"   📧 {acc_data['email']}\n"
            f"   🔑 {acc_data['password']}\n"
            f"   📅 {datetime.fromisoformat(acc_data['created_at']).strftime('%d/%m')}\n"
            f"   👥 Assigned to: {assigned_to}\n"
        )
    
    accounts_msg = (
        f"📋 *All Accounts*\n\n"
        f"📊 Stats: {stats['available']}🟢 {stats['assigned']}🟡 {stats['completed']}✅ {stats['cancelled']}❌\n\n" +
        "\n".join(accounts_list) +
        f"\n\n📝 *Total:* {len(accounts)} accounts"
    )
    
    await query.edit_message_text(
        accounts_msg[:4000],  # Telegram message limit
        parse_mode='Markdown',
        reply_markup=admin_accounts_keyboard()
    )

async def show_completed_accounts(query, page=0):
    """Show completed accounts with user info"""
    accounts = AccountManager.get_completed_accounts()
    
    if not accounts:
        await query.edit_message_text(
            "📭 *No completed accounts*",
            parse_mode='Markdown',
            reply_markup=admin_accounts_keyboard()
        )
        return
    
    total_accounts = len(accounts)
    items_per_page = 5
    
    header = f"✅ *Completed Accounts* - Page {page + 1}/{(total_accounts + items_per_page - 1) // items_per_page}\nTotal: {total_accounts}\n\n"
    
    await query.edit_message_text(
        header,
        parse_mode='Markdown',
        reply_markup=admin_completed_accounts_keyboard(page)
    )

async def show_account_detail(query, account_id):
    """Show account detail"""
    accounts = load_db(ACCOUNTS_DB)
    acc_data = accounts.get(account_id)
    
    if not acc_data:
        await query.edit_message_text(
            "❌ *Account not found!*",
            parse_mode='Markdown',
            reply_markup=admin_accounts_keyboard()
        )
        return
    
    # Get user info
    user_info = {}
    if acc_data.get('completed_by'):
        user_data = UserManager.get_user(acc_data['completed_by'], update_info=False)
        user_info = {
            'name': user_data['first_name'],
            'username': user_data['username'],
            'user_id': acc_data['completed_by']
        }
    
    detail_msg = (
        f"📋 *Account Details*\n\n"
        f"🆔 *Account ID:* `{account_id}`\n"
        f"👤 *Name:* {acc_data['first_name']} {acc_data['last_name']}\n"
        f"📧 *Email:* `{acc_data['email']}`\n"
        f"🔑 *Password:* `{acc_data['password']}`\n\n"
        f"📊 *Status:* {acc_data['status'].upper()}\n"
        f"📅 *Created:* {datetime.fromisoformat(acc_data['created_at']).strftime('%d %b %Y %H:%M')}\n"
    )
    
    if acc_data['status'] == 'completed':
        detail_msg += (
            f"\n✅ *Completed By:*\n"
            f"   👤 Name: {user_info.get('name', 'N/A')}\n"
            f"   🆔 User ID: `{user_info.get('user_id', 'N/A')}`\n"
            f"   📅 Time: {datetime.fromisoformat(acc_data['completed_at']).strftime('%d %b %Y %H:%M')}"
        )
    elif acc_data['status'] == 'assigned':
        if acc_data.get('assigned_to'):
            user_data = UserManager.get_user(acc_data['assigned_to'], update_info=False)
            detail_msg += (
                f"\n🟡 *Assigned To:*\n"
                f"   👤 Name: {user_data['first_name']}\n"
                f"   🆔 User ID: `{acc_data['assigned_to']}`\n"
                f"   📅 Time: {datetime.fromisoformat(acc_data['assigned_at']).strftime('%d %b %Y %H:%M')}"
            )
    
    await query.edit_message_text(
        detail_msg,
        parse_mode='Markdown',
        reply_markup=admin_accounts_keyboard()
    )

async def show_account_stats(query):
    """Show account statistics"""
    stats = AccountManager.get_account_stats()
    
    accounts = AccountManager.get_all_accounts()
    today = datetime.now().date()
    
    # Calculate daily completion rate
    daily_completions = {}
    for acc in accounts.values():
        if acc['status'] == 'completed' and acc.get('completed_at'):
            try:
                comp_date = datetime.fromisoformat(acc['completed_at']).date()
                daily_completions[comp_date] = daily_completions.get(comp_date, 0) + 1
            except:
                pass
    
    # Last 7 days
    last_7_days = []
    for i in range(7):
        date = today - timedelta(days=i)
        count = daily_completions.get(date, 0)
        last_7_days.append(f"{date.strftime('%a')}: {count}")
    
    stats_msg = (
        f"📊 *Account Statistics*\n\n"
        f"📈 *Status Distribution:*\n"
        f"├─ Total: {stats['total']}\n"
        f"├─ Available: {stats['available']} ({stats['available']/stats['total']*100:.1f}%)\n"
        f"├─ Assigned: {stats['assigned']} ({stats['assigned']/stats['total']*100:.1f}%)\n"
        f"└─ Completed: {stats['completed']} ({stats['completed']/stats['total']*100:.1f}%)\n\n"
        f"📅 *Today's Completions:* {stats['today_completed']}\n\n"
        f"📆 *Last 7 Days:*\n"
        f"{' | '.join(reversed(last_7_days))}\n\n"
        f"📝 *Daily Average:* {stats['completed']/max(1, (datetime.now().date() - datetime.fromisoformat(min([acc['created_at'] for acc in accounts.values()])).date()).days):.1f}"
    )
    
    await query.edit_message_text(
        stats_msg,
        parse_mode='Markdown',
        reply_markup=admin_accounts_keyboard()
    )

async def add_balance_prompt(query, user_id, context):
    """Prompt to add balance to user"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    context.user_data['add_balance_to'] = user_id
    
    await query.edit_message_text(
        f"💵 *Add Balance to User*\n\n"
        f"👤 User: {user_data['first_name']} (ID: {user_id})\n"
        f"💰 Current Balance: {user_data['real_etb']:.1f} ETB\n\n"
        f"Send the amount to add (ETB):\n"
        f"Example: `50` or `25.5`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )

async def message_user_prompt(query, user_id, context):
    """Prompt to message user"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    context.user_data['message_user'] = user_id
    
    await query.edit_message_text(
        f"📩 *Send Message to User*\n\n"
        f"👤 User: {user_data['first_name']} (ID: {user_id})\n"
        f"Send your message:\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )

async def user_detailed_info(query, user_id):
    """Show detailed user information"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    detailed_msg = (
        f"📋 *User Details*\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"📛 Name: {user_data['first_name']}\n"
        f"👤 Username: @{user_data['username']}\n\n"
        f"💰 Balance:\n"
        f"  Real ETB: {user_data['real_etb']:.1f}\n"
        f"  Hold ETB: {user_data['hold_etb']:.1f}\n"
        f"  Total Earned: {user_data['total_earned']:.1f}\n\n"
        f"📊 Activity:\n"
        f"  Completed Jobs: {user_data['completed_jobs']}\n"
        f"  Referrals: {user_data['referral_count']}\n"
        f"  Referral Earnings: {user_data['referral_earnings']:.1f}\n"
        f"  Withdrawals: {user_data['withdrawals']}\n"
        f"  Total Withdrawn: {user_data['total_withdrawn']:.1f}\n\n"
        f"📅 Join Date: {datetime.fromisoformat(user_data['join_date']).strftime('%Y-%m-%d %H:%M')}\n"
        f"📅 Last Active: {datetime.fromisoformat(user_data['last_active']).strftime('%Y-%m-%d %H:%M')}\n\n"
        f"🔗 Referral Code: {user_data.get('referral_code', 'N/A')}\n"
        f"📝 Pending Job: {user_data.get('pending_job', 'None')}"
    )
    
    await query.edit_message_text(
        detailed_msg,
        parse_mode='Markdown',
        reply_markup=admin_user_detail_keyboard(user_id)
    )

async def show_user_referrals(query, user_id):
    """Show user's referrals"""
    user_data = UserManager.get_user(user_id, update_info=False)
    users = UserManager.get_all_users()
    
    referrals_list = []
    for ref_id in user_data.get('referrals', []):
        if ref_id in users:
            ref_user = users[ref_id]
            referrals_list.append(
                f"👤 {ref_user.get('first_name', 'User')} (@{ref_user.get('username', 'N/A')})\n"
                f"   🆔 ID: `{ref_id}`\n"
                f"   📅 Joined: {datetime.fromisoformat(ref_user.get('join_date')).strftime('%d %b %Y')}\n"
            )
    
    if not referrals_list:
        referrals_msg = f"👥 *{user_data['first_name']}'s Referrals*\n\nNo referrals yet."
    else:
        referrals_msg = (
            f"👥 *{user_data['first_name']}'s Referrals*\n\n"
            f"📊 Total: {user_data['referral_count']} referrals\n\n" +
            "\n".join(referrals_list[:10])  # Show first 10
        )
    
    await query.edit_message_text(
        referrals_msg[:4000],
        parse_mode='Markdown',
        reply_markup=admin_user_detail_keyboard(user_id)
    )

async def show_user_transactions(query, user_id):
    """Show user's transactions"""
    transactions = load_db(TRANSACTIONS_DB)
    
    user_transactions = []
    for trans in transactions.values():
        if trans['user_id'] == user_id:
            user_transactions.append(trans)
    
    # Sort by date (newest first)
    user_transactions.sort(key=lambda x: x['timestamp'], reverse=True)
    
    if not user_transactions:
        trans_msg = "📝 *Transaction History*\n\nNo transactions found."
    else:
        trans_list = []
        for trans in user_transactions[:10]:  # Show last 10
            trans_list.append(
                f"📅 {datetime.fromisoformat(trans['timestamp']).strftime('%d %b %H:%M')}\n"
                f"   💰 {trans['amount']:.1f} ETB - {trans['type'].replace('_', ' ').title()}\n"
                f"   📋 {trans.get('description', '')}\n"
            )
        
        trans_msg = f"📝 *Transaction History*\n\n" + "\n".join(trans_list)
    
    await query.edit_message_text(
        trans_msg[:4000],
        parse_mode='Markdown',
        reply_markup=admin_user_detail_keyboard(user_id)
    )

async def broadcast_prompt(query, context):
    """Prompt for broadcast message"""
    total_users = UserManager.get_user_count()
    
    await query.edit_message_text(
        f"📢 *Broadcast Message*\n\n"
        f"👥 Total Users: {total_users}\n\n"
        f"Send the message you want to broadcast to all users:\n\n"
        f"*Formatting:*\n"
        f"• Use *bold*\n"
        f"• Use `code`\n"
        f"• Links supported\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['broadcast'] = True

async def admin_messages_menu(query):
    """Admin messages menu"""
    await query.edit_message_text(
        "💬 *Messages*\n\n"
        "Select an option:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📨 Send to All", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👤 Send to User", callback_data="admin_search_user")],
            [InlineKeyboardButton("🔙 Admin", callback_data="admin_panel")]
        ])
    )

async def admin_settings_menu(query):
    """Admin settings menu"""
    settings = load_db(SETTINGS_DB)
    
    settings_msg = (
        f"⚙️ *System Settings*\n\n"
        f"💰 Commission per job: {settings.get('commission_per_job', COMMISSION_PER_JOB)} ETB\n"
        f"💵 Minimum withdrawal: {settings.get('min_withdrawal', MIN_WITHDRAWAL)} ETB\n"
        f"🎁 Welcome bonus: {settings.get('welcome_bonus', 5.0)} ETB\n"
        f"📅 Hold days: {settings.get('hold_days', HOLD_PERIOD_DAYS)} days\n"
        f"👥 Referral percent: {settings.get('referral_percent', REFERRAL_COMMISSION_PERCENT)}%\n\n"
        f"Select setting to change:"
    )
    
    await query.edit_message_text(
        settings_msg,
        parse_mode='Markdown',
        reply_markup=admin_settings_keyboard()
    )

async def search_user_prompt(query, context):
    """Prompt to search for user"""
    await query.edit_message_text(
        "🔍 *Search User*\n\n"
        "Send User ID or Username to search:\n\n"
        "Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['search_user'] = True

async def set_commission_prompt(query, context):
    """Prompt to set commission"""
    settings = load_db(SETTINGS_DB)
    current = settings.get('commission_per_job', COMMISSION_PER_JOB)
    
    await query.edit_message_text(
        f"💰 *Set Commission per Job*\n\n"
        f"Current: {current} ETB\n\n"
        f"Enter new commission amount (ETB):\n"
        f"Example: `10` or `15.5`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['set_commission'] = True

async def set_min_withdraw_prompt(query, context):
    """Prompt to set minimum withdrawal"""
    settings = load_db(SETTINGS_DB)
    current = settings.get('min_withdrawal', MIN_WITHDRAWAL)
    
    await query.edit_message_text(
        f"💵 *Set Minimum Withdrawal*\n\n"
        f"Current: {current} ETB\n\n"
        f"Enter new minimum withdrawal amount (ETB):\n"
        f"Example: `20` or `50`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['set_min_withdraw'] = True

async def set_welcome_bonus_prompt(query, context):
    """Prompt to set welcome bonus"""
    settings = load_db(SETTINGS_DB)
    current = settings.get('welcome_bonus', 5.0)
    
    await query.edit_message_text(
        f"🎁 *Set Welcome Bonus*\n\n"
        f"Current: {current} ETB\n\n"
        f"Enter new welcome bonus amount (ETB):\n"
        f"Example: `5` or `10`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['set_welcome_bonus'] = True

async def set_hold_days_prompt(query, context):
    """Prompt to set hold days"""
    settings = load_db(SETTINGS_DB)
    current = settings.get('hold_days', HOLD_PERIOD_DAYS)
    
    await query.edit_message_text(
        f"📅 *Set Hold Days*\n\n"
        f"Current: {current} days\n\n"
        f"Enter new hold period (days):\n"
        f"Example: `1` or `2`\n\n"
        f"Type /cancel to cancel",
        parse_mode='Markdown'
    )
    
    context.user_data['set_hold_days'] = True

# ==================== MESSAGE HANDLERS ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Check if admin
    is_admin = user_id == ADMIN_ID
    
    # Admin message handlers
    if is_admin:
        if 'add_account' in context.user_data:
            await handle_add_account(update, context)
            return
        elif 'broadcast' in context.user_data:
            await handle_broadcast(update, context)
            return
        elif 'search_user' in context.user_data:
            await handle_search_user(update, context)
            return
        elif 'hold_transfer_select' in context.user_data:
            await handle_hold_transfer_select(update, context)
            return
        elif 'add_balance_to' in context.user_data:
            await handle_add_balance(update, context)
            return
        elif 'message_user' in context.user_data:
            await handle_message_user(update, context)
            return
        elif 'message_withdrawal_user' in context.user_data:
            await handle_message_withdrawal_user(update, context)
            return
        elif 'reject_request_id' in context.user_data:
            await handle_reject_reason(update, context)
            return
        elif 'mark_paid_id' in context.user_data:
            await handle_mark_paid(update, context)
            return
        elif 'set_commission' in context.user_data:
            await handle_set_commission(update, context)
            return
        elif 'set_min_withdraw' in context.user_data:
            await handle_set_min_withdraw(update, context)
            return
        elif 'set_welcome_bonus' in context.user_data:
            await handle_set_welcome_bonus(update, context)
            return
        elif 'set_hold_days' in context.user_data:
            await handle_set_hold_days(update, context)
            return
    
    # User withdrawal process
    if user_id in context.user_data:
        user_data = context.user_data[user_id]
        if 'withdraw_step' in user_data:
            await handle_withdrawal(update, context)
            return
    
    # Default response
    await update.message.reply_text(
        "Please use the menu buttons to navigate.",
        reply_markup=home_keyboard(is_admin)
    )

async def handle_add_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding new account"""
    text = update.message.text.strip()
    
    try:
        # Parse input: first_name|last_name|email|password
        parts = text.split('|')
        if len(parts) != 4:
            raise ValueError("Invalid format")
        
        first_name, last_name, email, password = parts
        
        # Add account
        account_id = AccountManager.add_account(first_name, last_name, email, password)
        
        await update.message.reply_text(
            f"✅ *Account Added Successfully!*\n\n"
            f"📝 Account ID: `{account_id}`\n"
            f"👤 Name: {first_name} {last_name}\n"
            f"📧 Email: `{email}`\n"
            f"🔑 Password: `{password}`\n\n"
            f"Account is now available for registration tasks.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['add_account']
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Error adding account!*\n\n"
            f"Please use format:\n"
            f"`first_name|last_name|email|password`\n\n"
            f"Example:\n"
            f"`John|Doe|john@gmail.com|Pass1234`",
            parse_mode='Markdown'
        )

async def handle_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broadcast message"""
    message = update.message.text
    users = UserManager.get_all_users()
    
    total_users = len(users)
    sent_count = 0
    failed_count = 0
    
    await update.message.reply_text(f"📤 Sending broadcast to {total_users} users...")
    
    for user_id_str in users.keys():
        try:
            user_id = int(user_id_str)
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 *Announcement from Admin*\n\n{message}\n\n_This is an official message from administrator._",
                parse_mode='Markdown'
            )
            sent_count += 1
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(0.05)
            
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send to {user_id_str}: {e}")
    
    # Clear state
    del context.user_data['broadcast']
    
    await update.message.reply_text(
        f"✅ *Broadcast Completed!*\n\n"
        f"📊 Results:\n"
        f"├─ Total Users: {total_users}\n"
        f"├─ Successfully Sent: {sent_count}\n"
        f"└─ Failed: {failed_count}\n\n"
        f"Message has been delivered.",
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def handle_search_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user search"""
    search_term = update.message.text.strip()
    users = UserManager.get_all_users()
    
    found_users = []
    
    for user_id_str, user_data in users.items():
        user_id = int(user_id_str)
        username = user_data.get('username', '').lower()
        first_name = user_data.get('first_name', '').lower()
        
        # Search by ID
        if search_term == user_id_str:
            found_users.append((user_id, user_data))
            break
        
        # Search by username (with or without @)
        search_lower = search_term.lower()
        if search_lower.startswith('@'):
            search_lower = search_lower[1:]
        
        if search_lower in username or search_lower in first_name:
            found_users.append((user_id, user_data))
    
    if not found_users:
        await update.message.reply_text(
            f"❌ *User not found!*\n\n"
            f"No user found for: `{search_term}`",
            parse_mode='Markdown'
        )
        return
    
    if len(found_users) == 1:
        # Directly show user info if only one found
        user_id, user_data = found_users[0]
        await update.message.reply_text(
            f"✅ *User Found!*\n\n"
            f"👤 Name: {user_data['first_name']}\n"
            f"🆔 ID: `{user_id}`\n"
            f"💰 Balance: {user_data['real_etb']:.1f} ETB\n\n"
            f"What would you like to do?",
            parse_mode='Markdown',
            reply_markup=admin_user_detail_keyboard(user_id)
        )
    else:
        # Show list of found users
        user_list = []
        for i, (user_id, user_data) in enumerate(found_users[:10], 1):
            user_list.append(
                f"{i}. {user_data['first_name']} (@{user_data['username']})\n"
                f"   🆔 ID: `{user_id}` | 💰 {user_data['real_etb']:.1f} ETB\n"
            )
        
        await update.message.reply_text(
            f"🔍 *Search Results*\n\n"
            f"Found {len(found_users)} users:\n\n" +
            "\n".join(user_list) +
            f"\n\nReply with the number to select a user.",
            parse_mode='Markdown'
        )
        
        # Store found users in context
        context.user_data['search_results'] = found_users
        context.user_data['awaiting_user_selection'] = True
    
    # Clear search state
    del context.user_data['search_user']

async def handle_hold_transfer_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user selection for hold transfer"""
    try:
        target_id = int(update.message.text.strip())
        
        # Check if user exists
        users = UserManager.get_all_users()
        if str(target_id) not in users:
            await update.message.reply_text(
                f"❌ *User not found!*\n\n"
                f"User ID `{target_id}` does not exist.",
                parse_mode='Markdown'
            )
            return
        
        await transfer_user_hold_to_real_bot(update, context, target_id)
        
        # Clear state
        del context.user_data['hold_transfer_select']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid User ID!*\n\n"
            "Please enter a valid numeric User ID.",
            parse_mode='Markdown'
        )

async def transfer_user_hold_to_real_bot(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Transfer hold to real for specific user (from bot)"""
    user_data = UserManager.get_user(user_id, update_info=False)
    
    hold_etb = user_data.get('hold_etb', 0)
    if hold_etb <= 0:
        await update.message.reply_text(
            f"ℹ️ *No Hold Balance*\n\n"
            f"User {user_id} has no hold balance to transfer.\n"
            f"Current hold: {hold_etb:.1f} ETB",
            parse_mode='Markdown'
        )
        return
    
    new_real = user_data.get('real_etb', 0) + hold_etb
    
    UserManager.update_user(user_id, {
        'real_etb': new_real,
        'hold_etb': 0
    })
    
    # Add transaction record
    TransactionManager.add_transaction(
        user_id=user_id,
        amount=hold_etb,
        type='hold_to_real',
        description='Hold balance transferred to real by admin'
    )
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💰 *Hold Balance Transferred!*\n\n"
                 f"✅ Amount: {hold_etb:.1f} ETB\n"
                 f"📈 New Balance: {new_real:.1f} ETB\n"
                 f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                 f"Your hold balance is now available for withdrawal!",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to notify user {user_id}: {e}")
    
    await update.message.reply_text(
        f"✅ *Hold Balance Transferred!*\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"💰 Amount: {hold_etb:.1f} ETB\n"
        f"📈 New Balance: {new_real:.1f} ETB\n\n"
        f"User has been notified.",
        parse_mode='Markdown',
        reply_markup=admin_main_keyboard()
    )

async def handle_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding balance to user"""
    try:
        amount = float(update.message.text.strip())
        target_id = context.user_data['add_balance_to']
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ *Amount must be positive!*",
                parse_mode='Markdown'
            )
            return
        
        # Add balance
        user_data = UserManager.get_user(target_id, update_info=False)
        new_balance = user_data['real_etb'] + amount
        
        UserManager.update_user(target_id, {
            'real_etb': new_balance,
            'total_earned': user_data['total_earned'] + amount
        })
        
        # Add transaction
        TransactionManager.add_transaction(
            user_id=target_id,
            amount=amount,
            type='admin_add',
            description=f"Balance added by admin {update.effective_user.id}"
        )
        
        # Notify user
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"💰 *Balance Added by Admin!*\n\n"
                     f"✅ Amount: {amount:.1f} ETB\n"
                     f"📈 New Balance: {new_balance:.1f} ETB\n"
                     f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                     f"Added by administrator.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify user {target_id}: {e}")
        
        await update.message.reply_text(
            f"✅ *Balance Added Successfully!*\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"💰 Amount: {amount:.1f} ETB\n"
            f"📈 New Balance: {new_balance:.1f} ETB\n\n"
            f"User has been notified.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['add_balance_to']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount!*\n\n"
            "Please enter a valid number.\n"
            "Example: `50` or `25.5`",
            parse_mode='Markdown'
        )

async def handle_message_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle sending message to specific user"""
    message = update.message.text
    target_id = context.user_data['message_user']
    
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"📩 *Message from Admin*\n\n{message}\n\n"
                 f"_This is an official message from administrator._",
            parse_mode='Markdown'
        )
        
        # Save message
        MessageManager.save_message(
            user_id=target_id,
            admin_id=update.effective_user.id,
            message=message,
            direction='admin_to_user'
        )
        
        await update.message.reply_text(
            f"✅ *Message Sent!*\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"📝 Message delivered successfully.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['message_user']
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Failed to send message!*\n\n"
            f"Error: {str(e)}\n\n"
            f"The user may have blocked the bot.",
            parse_mode='Markdown'
        )

async def handle_message_withdrawal_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle messaging user about withdrawal"""
    message = update.message.text
    target_id = context.user_data['message_withdrawal_user']
    
    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"📩 *Message About Your Withdrawal*\n\n{message}\n\n"
                 f"_This is an official message from administrator._",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(
            f"✅ *Message Sent!*\n\n"
            f"👤 User ID: `{target_id}`\n"
            f"📝 Message delivered successfully.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['message_withdrawal_user']
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ *Failed to send message!*\n\n"
            f"Error: {str(e)}\n\n"
            f"The user may have blocked the bot.",
            parse_mode='Markdown'
        )

async def handle_reject_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle rejection reason"""
    reason = update.message.text
    request_id = context.user_data['reject_request_id']
    
    # Reject the withdrawal
    success = WithdrawalManager.reject_request(request_id, update.effective_user.id, reason)
    
    if success:
        # Notify user
        withdraws = load_db(WITHDRAW_DB)
        req_data = withdraws.get(request_id)
        
        if req_data:
            user_id = req_data['user_id']
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"❌ *Withdrawal Rejected*\n\n"
                         f"💰 Amount: {req_data['amount']:.1f} ETB\n"
                         f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                         f"*Reason:* {reason}\n\n"
                         f"Your funds have been returned to your balance.\n"
                         f"Contact {SUPPORT_USERNAME} for more information.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"❌ *Withdrawal Rejected!*\n\n"
            f"📋 Request ID: {request_id}\n"
            f"👤 User: {req_data.get('name', 'N/A')}\n"
            f"💰 Amount: {req_data['amount']:.1f} ETB\n"
            f"📝 Reason: {reason}\n\n"
            f"User has been notified and funds returned.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ *Error rejecting withdrawal!*",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
    
    # Clear state
    del context.user_data['reject_request_id']

async def handle_mark_paid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle marking withdrawal as paid"""
    notes = update.message.text
    request_id = context.user_data['mark_paid_id']
    
    # Mark as paid
    success = WithdrawalManager.mark_as_paid(request_id, update.effective_user.id, notes)
    
    if success:
        # Notify user
        withdraws = load_db(WITHDRAW_DB)
        req_data = withdraws.get(request_id)
        
        if req_data:
            user_id = req_data['user_id']
            
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"💰 *Withdrawal Paid!*\n\n"
                         f"✅ Amount: {req_data['amount']:.1f} ETB\n"
                         f"📱 Telebirr: {req_data['telebirr']}\n"
                         f"📅 Time: {datetime.now().strftime('%d %b %Y %H:%M')}\n\n"
                         f"Your withdrawal has been processed and paid!\n"
                         f"*Notes:* {notes}\n\n"
                         f"Thank you for using our service!",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Failed to notify user {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ *Withdrawal Marked as Paid!*\n\n"
            f"📋 Request ID: {request_id}\n"
            f"👤 User: {req_data.get('name', 'N/A')}\n"
            f"💰 Amount: {req_data['amount']:.1f} ETB\n"
            f"📝 Notes: {notes}\n\n"
            f"User has been notified.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ *Error marking as paid!*",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
    
    # Clear state
    del context.user_data['mark_paid_id']

async def handle_set_commission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting commission"""
    try:
        amount = float(update.message.text.strip())
        
        if amount <= 0:
            await update.message.reply_text(
                "❌ *Commission must be positive!*",
                parse_mode='Markdown'
            )
            return
        
        # Update settings
        settings = load_db(SETTINGS_DB)
        settings['commission_per_job'] = amount
        save_db(SETTINGS_DB, settings)
        
        global COMMISSION_PER_JOB
        COMMISSION_PER_JOB = amount
        
        await update.message.reply_text(
            f"✅ *Commission Updated!*\n\n"
            f"💰 New commission: {amount} ETB per job\n\n"
            f"This change will apply to all new registrations.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['set_commission']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount!*\n\n"
            "Please enter a valid number.\n"
            "Example: `10` or `15.5`",
            parse_mode='Markdown'
        )

async def handle_set_min_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting minimum withdrawal"""
    try:
        amount = float(update.message.text.strip())
        
        if amount < 0:
            await update.message.reply_text(
                "❌ *Amount cannot be negative!*",
                parse_mode='Markdown'
            )
            return
        
        # Update settings
        settings = load_db(SETTINGS_DB)
        settings['min_withdrawal'] = amount
        save_db(SETTINGS_DB, settings)
        
        global MIN_WITHDRAWAL
        MIN_WITHDRAWAL = amount
        
        await update.message.reply_text(
            f"✅ *Minimum Withdrawal Updated!*\n\n"
            f"💵 New minimum: {amount} ETB\n\n"
            f"This change takes effect immediately.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['set_min_withdraw']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount!*\n\n"
            "Please enter a valid number.\n"
            "Example: `20` or `50`",
            parse_mode='Markdown'
        )

async def handle_set_welcome_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting welcome bonus"""
    try:
        amount = float(update.message.text.strip())
        
        if amount < 0:
            await update.message.reply_text(
                "❌ *Amount cannot be negative!*",
                parse_mode='Markdown'
            )
            return
        
        # Update settings
        settings = load_db(SETTINGS_DB)
        settings['welcome_bonus'] = amount
        save_db(SETTINGS_DB, settings)
        
        await update.message.reply_text(
            f"✅ *Welcome Bonus Updated!*\n\n"
            f"🎁 New welcome bonus: {amount} ETB\n\n"
            f"This will apply to new users only.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['set_welcome_bonus']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid amount!*\n\n"
            "Please enter a valid number.\n"
            "Example: `5` or `10`",
            parse_mode='Markdown'
        )

async def handle_set_hold_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle setting hold days"""
    try:
        days = int(update.message.text.strip())
        
        if days < 0:
            await update.message.reply_text(
                "❌ *Days cannot be negative!*",
                parse_mode='Markdown'
            )
            return
        
        # Update settings
        settings = load_db(SETTINGS_DB)
        settings['hold_days'] = days
        save_db(SETTINGS_DB, settings)
        
        global HOLD_PERIOD_DAYS
        HOLD_PERIOD_DAYS = days
        
        await update.message.reply_text(
            f"✅ *Hold Days Updated!*\n\n"
            f"📅 New hold period: {days} days\n\n"
            f"This applies to new registrations only.",
            parse_mode='Markdown',
            reply_markup=admin_main_keyboard()
        )
        
        # Clear state
        del context.user_data['set_hold_days']
        
    except ValueError:
        await update.message.reply_text(
            "❌ *Invalid number!*\n\n"
            "Please enter a valid number of days.\n"
            "Example: `1` or `2`",
            parse_mode='Markdown'
        )

async def handle_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle withdrawal process"""
    user_id = update.effective_user.id
    text = update.message.text
    user_data = context.user_data.get(user_id, {})
    
    if user_data.get('withdraw_step') == 'ask_amount':
        # Validate amount
        try:
            amount = float(text.strip())
            
            if amount < MIN_WITHDRAWAL:
                await update.message.reply_text(
                    f"❌ *Minimum withdrawal is {MIN_WITHDRAWAL} ETB!*\n\n"
                    f"Please enter at least {MIN_WITHDRAWAL} ETB.",
                    parse_mode='Markdown'
                )
                return
            
            if amount > user_data['max_amount']:
                await update.message.reply_text(
                    f"❌ *Insufficient balance!*\n\n"
                    f"Available: {user_data['max_amount']:.1f} ETB\n"
                    f"Requested: {amount:.1f} ETB\n\n"
                    f"Please enter a smaller amount.",
                    parse_mode='Markdown'
                )
                return
            
            context.user_data[user_id]['amount'] = amount
            context.user_data[user_id]['withdraw_step'] = 'ask_name'
            
            await update.message.reply_text(
                "📝 *Enter your full name:*\n\n"
                "Please enter your full name as registered in Telebirr:\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text(
                "❌ *Invalid amount!*\n\n"
                "Please enter a valid number.\n"
                "Example: `50` or `100.5`",
                parse_mode='Markdown'
            )
    
    elif user_data.get('withdraw_step') == 'ask_name':
        # Validate name
        if len(text.strip()) < 3:
            await update.message.reply_text(
                "⚠️ *Please enter a valid name!*\n\n"
                "Minimum 3 characters required.",
                parse_mode='Markdown'
            )
            return
        
        context.user_data[user_id]['name'] = text.strip()
        context.user_data[user_id]['withdraw_step'] = 'ask_telebirr'
        
        method = user_data.get('method', 'telebirr')
        
        if method == 'telebirr':
            await update.message.reply_text(
                "📱 *Enter your Telebirr number:*\n\n"
                "*Format:* 09XXXXXXXX or +2519XXXXXXXX\n"
                "Example: *0912345678*\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
        else:  # bank
            await update.message.reply_text(
                "🏦 *Enter your bank account details:*\n\n"
                "Include:\n"
                "• Bank name\n"
                "• Account number\n"
                "• Account name\n\n"
                "Example:\n"
                "`CBE|1234567890|John Doe`\n\n"
                "Type /cancel to cancel",
                parse_mode='Markdown'
            )
    
    elif user_data.get('withdraw_step') == 'ask_telebirr':
        method = user_data.get('method', 'telebirr')
        account_info = text.strip()
        
        # Validate based on method
        if method == 'telebirr':
            # Validate Telebirr number
            if not (account_info.startswith('09') and len(account_info) == 10 and account_info[2:].isdigit()) and \
               not (account_info.startswith('+2519') and len(account_info) == 13 and account_info[5:].isdigit()):
                await update.message.reply_text(
                    "⚠️ *Invalid Telebirr number!*\n\n"
                    "Please use format:\n"
                    "*09XXXXXXXX* or *+2519XXXXXXXX*\n\n"
                    "Example: *0912345678*",
                    parse_mode='Markdown'
                )
                return
        
        name = user_data['name']
        amount = user_data['amount']
        
        # Create withdrawal request
        if method == 'telebirr':
            request_id = WithdrawalManager.create_request(user_id, name, account_info, amount)
        else:
            # For bank, store details in notes
            request_id = WithdrawalManager.create_request(user_id, name, "Bank Transfer", amount)
            # Update with bank details in notes
            withdraws = load_db(WITHDRAW_DB)
            if request_id in withdraws:
                withdraws[request_id]['notes'] = f"Bank details: {account_info}"
                save_db(WITHDRAW_DB, withdraws)
        
        # Deduct from user balance
        current_user = UserManager.get_user(user_id, update_info=False)
        new_balance = current_user['real_etb'] - amount
        
        UserManager.update_user(user_id, {
            'real_etb': new_balance
        })
        
        # Add transaction
        TransactionManager.add_transaction(
            user_id=user_id,
            amount=amount,
            type='withdrawal_request',
            description=f"Withdrawal request: {request_id}"
        )
        
        # Send confirmation to user
        if method == 'telebirr':
            detail_msg = f"📱 *TeleBirr:* {account_info}"
        else:
            detail_msg = f"🏦 *Bank Details:* {account_info}"
        
        await update.message.reply_text(
            f"✅ *Withdrawal Request Submitted Successfully!*\n\n"
            f"📋 *Request ID:* `{request_id}`\n"
            f"💰 *Amount:* {amount:.1f} ETB\n"
            f"👤 *Name:* {name}\n"
            f"{detail_msg}\n\n"
            f"⏰ *Processing time:* 24-48 hours\n"
            f"📊 *New Balance:* {new_balance:.1f} ETB\n\n"
            f"📞 *For faster payment support contact:* {SUPPORT_USERNAME}\n\n"
            f"Thank you for using {BOT_USERNAME}!",
            parse_mode='Markdown',
            reply_markup=home_keyboard(user_id == ADMIN_ID)
        )
        
        # Forward to admin
        try:
            admin_msg = (
                f"📤 *New Withdrawal Request*\n\n"
                f"🆔 Request ID: {request_id}\n"
                f"👤 User ID: {user_id}\n"
                f"📛 Name: {name}\n"
                f"💰 Amount: {amount:.1f} ETB\n"
                f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            )
            
            if method == 'telebirr':
                admin_msg += f"📱 TeleBirr: {account_info}\n"
            else:
                admin_msg += f"🏦 Bank Details: {account_info}\n"
            
            admin_msg += f"\nUse Admin Panel to approve/reject."
            
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_msg,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        # Clear user data
        if user_id in context.user_data:
            del context.user_data[user_id]

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel conversation"""
    user_id = update.effective_user.id
    is_admin = user_id == ADMIN_ID
    
    # Clear all states
    if user_id in context.user_data:
        del context.user_data[user_id]
    
    # Clear admin states
    admin_states = ['add_account', 'broadcast', 'search_user', 'hold_transfer_select',
                   'add_balance_to', 'message_user', 'message_withdrawal_user',
                   'reject_request_id', 'mark_paid_id', 'set_commission',
                   'set_min_withdraw', 'set_welcome_bonus', 'set_hold_days',
                   'search_results', 'awaiting_user_selection']
    for state in admin_states:
        if state in context.user_data:
            del context.user_data[state]
    
    await update.message.reply_text(
        "Operation cancelled.",
        reply_markup=home_keyboard(is_admin)
    )
    
    return ConversationHandler.END

# ==================== ADMIN COMMANDS ====================
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Show stats"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await show_admin_stats(update.callback_query)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Show users"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await show_admin_users(update.callback_query, 0)

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Account management"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await account_management(update.callback_query)

async def withdrawals_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Withdrawal requests"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await show_withdrawal_requests(update.callback_query)

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Broadcast"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await broadcast_prompt(update.callback_query, context)

async def addaccount_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: Add account"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Access denied!")
        return
    
    await add_account_prompt(update.callback_query, context)

# ==================== MAIN FUNCTION ====================
def main():
    """Start the bot"""
    # Initialize databases
    init_databases()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("users", users_command))
    application.add_handler(CommandHandler("accounts", accounts_command))
    application.add_handler(CommandHandler("withdrawals", withdrawals_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))
    application.add_handler(CommandHandler("addaccount", addaccount_command))
    application.add_handler(CommandHandler("cancel", cancel))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Start the bot
    print("\n" + "="*50)
    print("🤖 ETHIOFARMER BOT - ULTIMATE VERSION")
    print("="*50)
    print(f"📱 Bot Username: @{BOT_USERNAME}")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"💬 Support: {SUPPORT_USERNAME}")
    print(f"💰 Commission per job: {COMMISSION_PER_JOB} ETB")
    print(f"👥 Referral commission: {REFERRAL_COMMISSION_PERCENT}%")
    print(f"💵 Minimum withdrawal: {MIN_WITHDRAWAL} ETB")
    print(f"⏱️ Hold period: {HOLD_PERIOD_DAYS} day")
    print(f"🎁 Welcome bonus: {load_db(SETTINGS_DB).get('welcome_bonus', 5.0)} ETB")
    print(f"📅 Daily bonus: {load_db(SETTINGS_DB).get('daily_bonus', 5.0)} ETB")
    print("="*50)
    print("📁 Databases initialized:")
    print(f"  • users.json - User data")
    print(f"  • withdraw.json - Withdrawal requests")
    print(f"  • accounts.json - Registration accounts")
    print(f"  • transactions.json - Transaction history")
    print(f"  • settings.json - System settings")
    print(f"  • messages.json - Message history")
    print("="*50)
    print("🚀 Bot is starting...")
    print("✅ Ready to receive messages!")
    print("="*50)
    print("\n💡 To stop the bot: Press Ctrl+C in Pydroid 3\n")
    
    # Run bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        print("Please check your configuration and try again.")
