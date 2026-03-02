# -*- coding: utf-8 -*-
import telebot
from telebot import types
import os
import subprocess
import time
import threading
import sqlite3
import logging
import traceback
import re
import ast
import importlib
import tempfile
import shutil
from datetime import datetime, timedelta
import requests
import uuid
import hashlib
import json
import atexit
import zipfile
from io import BytesIO
import random

# إعدادات التسجيل
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ✅ تحديث التوكن الجديد
TOKEN = "8312804328:AAHWKLYB3ugmuMzZavwSzs3wE0HJVD1scDo"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# تخزين معرفات الرسائل الأخيرة
user_last_messages = {}

UPLOAD_FOLDER = "uploaded_files"
DB_FILE = "bot_data.db"
ANALYSIS_FOLDER = "file_analysis"
TOKENS_FOLDER = "tokens_data"
FOLDERS_FOLDER = "user_folders"
SUB_PROMPT_FOLDER = "subscription_prompts"
PROTECTION_FOLDER = "protection"
PROTECTION_STATE_FILE = os.path.join(PROTECTION_FOLDER, "protection_state.json")
HACK_ATTEMPTS_FOLDER = "hack_attempts"

# إنشاء المجلدات إذا لم تكن موجودة
folders = [UPLOAD_FOLDER, ANALYSIS_FOLDER, TOKENS_FOLDER, FOLDERS_FOLDER, 
           SUB_PROMPT_FOLDER, PROTECTION_FOLDER, HACK_ATTEMPTS_FOLDER]
for folder in folders:
    os.makedirs(folder, exist_ok=True)

# محتوى index.php للحماية
PROTECTION_PHP_CONTENT = """<html><head><meta name="viewport" content="width=device-width; height=device-height;"><link rel="stylesheet" href="resource://content-accessible/ImageDocument.css"><link rel="stylesheet" href="resource://content-accessible/TopLevelImageDocument.css"><link rel="stylesheet" href="chrome://global/skin/media/TopLevelImageDocument.css"><title>(⚠ تحذير اخرج من هنا والا سيتم صعق جهازك📵)</title></head><body><img src="https://4.top4top.net/p_13628pw5v1.jpg" alt="https://4.top4top.net/p_13628pw5v1.jpg" class="shrinkToFit" width="600" height="600"></body></html>
"""

# =============================
# قاعدة بيانات الأنماط الهجومية AI المحسنة
# =============================
HACK_PATTERNS = [
    # أنماط استغلال نظام الملفات
    (r"__import__\s*\(\s*['\"]os['\"]\s*\)", "محاولة استيراد مكتبة نظام خطيرة", 10),
    (r"os\.system\s*\(|subprocess\.Popen\s*\(|subprocess\.call\s*\(", "استدعاء أوامر نظام مباشرة", 9),
    (r"eval\s*\(|exec\s*\(", "استخدام eval/exec لتنفيذ كود ديناميكي", 8),
    (r"open\s*\(\s*['\"](/etc/passwd|/etc/shadow|\.\./\.\./)", "محاولة قراءة ملفات نظام حساسة", 10),
    (r"shutil\.rmtree\s*\(|os\.rmdir\s*\(|os\.removedirs\s*\(", "محاولة حذف مجلدات نظام", 9),
    (r"while\s+True\s*:|for\s+\w+\s+in\s+range\s*\(\s*\d+\s*,\s*\d+\s*\):", "حلقات لا نهائية محتملة", 7),
    (r"import\s+ctypes|import\s+socket|import\s+paramiko", "استيراد مكتبات شبكة/نظام خطيرة", 8),
    (r"requests\.(get|post)\s*\(\s*['\"]https?://", "اتصالات شبكية خارجية", 6),
    (r"urllib\.request\.urlopen|urllib2\.urlopen", "فتح روابط خارجية", 6),
    (r"open\s*\(\s*['\"].*\.(exe|dll|bat|sh|bash)['\"]", "محاولة فتح ملفات تنفيذية", 9),
    (r"__builtins__\s*\.|__import__\s*\(|globals\s*\(|locals\s*\(", "التلاعب بالبيئة التنفيذية", 8),
    (r"import\s+sys\s*;|from\s+sys\s+import", "استيراد sys مع أغراض خبيثة", 7),
    (r"subprocess\.run\s*\(.*shell\s*=\s*True", "تشغيل أوامر shell مباشرة", 9),
    (r"os\.popen\s*\(|popen2\s*\(|popen3\s*\(", "فتح عمليات نظام", 8),
    (r"\.replace\s*\(\s*['\"]token['\"].*|\.replace\s*\(\s*['\"]TOKEN['\"]", "محاولة تغيير التوكن ديناميكيًا", 7),
    (r"import\s+cryptography|import\s+hashing", "مكتبات تشفير قد تستخدم لاختراق", 6),
    (r"base64\.b64decode|base64\.b64encode", "تشفير/فك تشفير قد يكون خبيثًا", 5),
    (r"pickle\.loads|pickle\.dump", "استخدام pickle قد يكون خطيرًا", 7),
    (r"__getattr__\s*\(|__setattr__\s*\(|__delattr__\s*\(", "التلاعب بالسمات ديناميكيًا", 6),
    (r"getattr\s*\(|setattr\s*\(", "وظائف الوصول الديناميكي", 5),
    (r"lambda\s+.*:.*\(.*\)", "دوال lambda معقدة قد تكون خبيثة", 4),
    (r"@.*decorator.*def", "ديكورات مخصصة قد تكون خبيثة", 3),
    (r"import\s+.*\s+as\s+_", "استيراد بأسماء مخفية", 4),
    (r"#.*bypass|#.*hack|#.*exploit", "تعليقات تشير إلى تجاوز أو اختراق", 5),
    (r"token\s*=\s*['\"].*['\"]\s*#.*fake", "توكن مزيف في التعليقات", 6),
    (r"try:.*except\s+Exception:", "معالجة أخطاء عامة قد تخفي نشاطًا خبيثًا", 3),
    (r"exit\s*\(|quit\s*\(|sys\.exit\s*\(", "إغلاق البرنامج فجأة", 4),
    (r"import\s+multiprocessing\s*;", "استخدام multiprocessing لأغراض خبيثة", 5),
    (r"threading\.Thread\s*\(.*target\s*=", "إنشاء ثreads قد تكون خبيثة", 5),
    (r"\.encode\s*\(\s*['\"]rot13['\"]|\.decode\s*\(\s*['\"]rot13['\"]", "تشفير rot13 للاختباء", 4),
    (r"import\s+antigravity", "مكتبة antigravity للدعابة ولكن قد تستخدم للاختباء", 2),
    (r"from\s+crypto\s+import|import\s+pycryptodome", "مكتبات تشفير متقدمة", 6),
    (r"\.replace\s*\(\s*['\"]https://api.telegram.org['\"]", "تغيير رابط API تيليجرام", 8),
    (r"requests\.Session\s*\(\)", "إنشاء جلسات requests مستمرة", 5),
    (r"\.text\.split\s*\(\s*['\"]\\n['\"]\s*\)\[:\d+\]", "تقسيم نصوص قد يكون لاستخراج بيانات", 3),
    (r"if\s+__name__\s*==\s*['\"]__main__['\"]:", "تشغيل كود مباشر قد يكون خبيثًا", 4),
    (r"import\s+.*\s*#.*nocover", "استيراد مع تعليقات غامضة", 3),
    (r"def\s+\w+\s*\(\s*\)\s*:\s*pass", "دوال فارغة قد تكون لواجهات خبيثة", 2),
    (r"class\s+\w+\s*\(\s*\)\s*:\s*pass", "كلاسات فارغة قد تكون خبيثة", 2),
    (r"import\s+this", "استيراد this (زين Python) قد يكون للاختباء", 1),
    (r"import\s+antigravity\s*;", "استيراد antigravity مع فاصلة منقوطة", 2),
    (r"from\s+__future__\s+import.*division", "استيراد من future قد يكون للتغطية", 1),
]

# قائمة بأنماط التهديدات
THREAT_PATTERNS = [
    r"eval\s*\(", r"exec\s*\(", r"__import__\s*\(", r"open\s*\(",
    r"subprocess\.Popen\s*\(", r"os\.system\s*\(", r"os\.popen\s*\(",
    r"shutil\.rmtree\s*\(", r"os\.remove\s*\(", r"os\.unlink\s*\(",
    r"requests\.(get|post)\s*\(", r"urllib\.request\.urlopen\s*\(",
    r"while True:", r"fork\s*\(", r"pty\s*\(", r"spawn\s*\("
]

# المكتبات المحظورة
BLOCKED_LIBRARIES = [
    'os', 'sys', 'subprocess', 'shutil', 'ctypes', 'socket',
    'paramiko', 'ftplib', 'urllib', 'requests', 'selenium',
    'scrapy', 'mechanize', 'webbrowser', 'pyautogui', 'pynput',
    'cryptography', 'hashlib', 'hmac', 'ssl', 'ftplib', 'telnetlib',
    'smtplib', 'imaplib', 'poplib', 'nntplib', 'socketserver',
    'http.server', 'xmlrpc', 'multiprocessing', 'threading'
]

# المتغيرات الرئيسية
VIP_MODE = False
user_file_count = {}
user_processes = {}
running_processes = {}
developer = "@ihh_4"
DEVELOPER_ID =[8313661137, 8313661137]

# =============================
# قاعدة البيانات - محدثة مع جميع الميزات الجديدة
# =============================
def update_db_structure():
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()
    
    # تحديث الجداول الأساسية
    cursor.execute('''CREATE TABLE IF NOT EXISTS files
                    (id INTEGER PRIMARY KEY, filename TEXT, user_id INTEGER, 
                     upload_time TIMESTAMP, status TEXT, analysis_result TEXT,
                     token TEXT, libraries TEXT, folder_name TEXT,
                     security_level TEXT, hack_score INTEGER, 
                     requires_approval INTEGER DEFAULT 0,
                     approved_by INTEGER DEFAULT NULL,
                     approval_time TIMESTAMP DEFAULT NULL,
                     rejection_reason TEXT DEFAULT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, 
                     added_by INTEGER, added_time TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS banned_users
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, 
                     banned_by INTEGER, ban_time TIMESTAMP, reason TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS force_subscribe
                    (id INTEGER PRIMARY KEY, channel_id TEXT UNIQUE, 
                     channel_username TEXT, added_by INTEGER, added_time TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_settings
                    (id INTEGER PRIMARY KEY, setting_key TEXT UNIQUE, 
                     setting_value TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS file_analysis
                    (id INTEGER PRIMARY KEY, filename TEXT, user_id INTEGER, 
                     analysis_time TIMESTAMP, issues_found INTEGER,
                     dangerous_libs TEXT, malicious_patterns TEXT,
                     file_size INTEGER, lines_of_code INTEGER,
                     hack_detected INTEGER DEFAULT 0,
                     hack_score INTEGER DEFAULT 0,
                     hack_details TEXT DEFAULT NULL)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS security_settings
                    (id INTEGER PRIMARY KEY, setting_key TEXT UNIQUE, 
                     setting_value TEXT, description TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS vip_users
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, 
                     activated_by INTEGER, activation_time TIMESTAMP,
                     expiry_date TIMESTAMP, status TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_libraries
                    (id INTEGER PRIMARY KEY, library_name TEXT UNIQUE, 
                     blocked_by INTEGER, block_time TIMESTAMP, reason TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_folders
                    (id INTEGER PRIMARY KEY, user_id INTEGER, 
                     folder_name TEXT, created_time TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS known_users
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, 
                     first_seen TIMESTAMP, last_seen TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_settings
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE,
                     notifications_enabled INTEGER DEFAULT 1, first_free_used INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS pro_users
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, 
                     activated_by INTEGER, activation_time TIMESTAMP,
                     expiry_date TIMESTAMP, status TEXT)''')
    
    # جداول النقاط والدعوات والهدايا
    cursor.execute('''CREATE TABLE IF NOT EXISTS users_points
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE, points INTEGER DEFAULT 0, first_free_used INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS referral_links
                    (id INTEGER PRIMARY KEY, user_id INTEGER, code TEXT UNIQUE, created_at TIMESTAMP, points_per_ref INTEGER DEFAULT 2, uses INTEGER DEFAULT 0)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS referrals
                    (id INTEGER PRIMARY KEY, referrer_id INTEGER, referred_id INTEGER, code TEXT, time TIMESTAMP)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS gift_codes
                    (id INTEGER PRIMARY KEY, code TEXT UNIQUE, creator_id INTEGER, points INTEGER, max_uses INTEGER, used_count INTEGER DEFAULT 0, expires_at TIMESTAMP)''')
    
    # جدول جديد للأسعار
    cursor.execute('''CREATE TABLE IF NOT EXISTS prices
                    (id INTEGER PRIMARY KEY, price_type TEXT UNIQUE, price_value INTEGER)''')
    
    # جدول جديد لسجلات الاختراق
    cursor.execute('''CREATE TABLE IF NOT EXISTS hack_attempts
                    (id INTEGER PRIMARY KEY, user_id INTEGER, filename TEXT,
                     hack_score INTEGER, detection_time TIMESTAMP,
                     patterns_found TEXT, action_taken TEXT,
                     notified_admin INTEGER DEFAULT 0,
                     resolved INTEGER DEFAULT 0)''')
    
    # جدول لإشعارات المطور
    cursor.execute('''CREATE TABLE IF NOT EXISTS admin_notifications
                    (id INTEGER PRIMARY KEY, notification_type TEXT,
                     user_id INTEGER, filename TEXT, details TEXT,
                     notification_time TIMESTAMP, status TEXT DEFAULT 'pending',
                     admin_action TEXT DEFAULT NULL, action_time TIMESTAMP DEFAULT NULL)''')
    
    # جدول جديد لرسائل البوت الأخيرة
    cursor.execute('''CREATE TABLE IF NOT EXISTS bot_messages
                    (id INTEGER PRIMARY KEY, user_id INTEGER, chat_id INTEGER,
                     message_type TEXT, message_id INTEGER,
                     timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                     UNIQUE(user_id, message_type))''')
    
    # ===== الجداول الجديدة للميزات المطلوبة =====
    cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_uploads
                    (id INTEGER PRIMARY KEY, user_id INTEGER UNIQUE,
                     blocked_by INTEGER, block_time TIMESTAMP, reason TEXT)''')
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS points_transactions
                    (id INTEGER PRIMARY KEY, user_id INTEGER, admin_id INTEGER,
                     amount INTEGER, transaction_type TEXT, reason TEXT,
                     transaction_time TIMESTAMP)''')
    
    # إعدادات الافتراضية
    default_settings = [
        ('free_mode', 'enabled'),
        ('paid_mode', 'disabled'),
        ('bot_status', 'enabled'),
        ('upload_price', '0'),
        ('referral_price', '2'),
        ('ai_security', 'enabled'),
        ('auto_block_hackers', 'enabled'),
        ('notify_on_hack_attempt', 'enabled'),
        ('hack_score_threshold', '15')
    ]
    
    for setting in default_settings:
        cursor.execute("INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)", setting)
    
    # الأسعار الافتراضية
    default_prices = [
        ('upload_price', 0),
        ('referral_price', 2)
    ]
    
    for price_type, price_value in default_prices:
        cursor.execute("INSERT OR IGNORE INTO prices (price_type, price_value) VALUES (?, ?)", (price_type, price_value))
    
    # إعدادات الأمان الافتراضية
    default_security_settings = [
        ('auto_scan_files', 'true', 'فحص تلقائي للملفات'),
        ('block_dangerous_libs', 'true', 'منع تثبيت المكتبات الخطرة'),
        ('notify_on_threat', 'true', 'إشعار عند اكتشاف تهديد'),
        ('max_file_size', '10240', 'الحد الأقصى لحجم الملف (كيلوبايت)'),
        ('allowed_file_types', 'py,zip,txt,json', 'أنواع الملفات المسموحة'),
        ('cleanup_interval', '24', 'فترة التنظيف (ساعات)'),
        ('vip_mode', 'false', 'وضع VIP'),
        ('auto_install_libs', 'true', 'تثبيت المكتبات تلقائياً'),
        ('auto_fix_files', 'false', 'إصلاح تلقائي للملفات عند الرفع'),
        ('auto_fix_require_approval', 'true', 'هل يتطلب الإصلاح الموافقة من المستخدم؟'),
        ('ai_hack_detection', 'true', 'كشف محاولات الاختراق بالذكاء الاصطناعي'),
        ('auto_block_high_risk', 'true', 'حظر تلقائي للمخاطر العالية'),
        ('hack_notification_level', 'medium', 'مستوى إشعارات الاختراق')
    ]
    
    for setting in default_security_settings:
        cursor.execute('''INSERT OR IGNORE INTO security_settings 
                        (setting_key, setting_value, description) 
                        VALUES (?, ?, ?)''', setting)
    
    conn.commit()
    conn.close()
    logger.info("✅ تم تحديث بنية قاعدة البيانات مع جميع الميزات الجديدة")

def init_db():
    update_db_structure()

# تهيئة DB
init_db()

# =============================
# دوال المساعدة لقاعدة البيانات - معدلة لعلاج مشكلة القفل
# =============================
def db_execute(query, params=()):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.error(f"خطأ في قاعدة البيانات: {e}")
        raise
    finally:
        conn.close()

def db_fetchone(query, params=()):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        result = cursor.fetchone()
    except sqlite3.OperationalError as e:
        logger.error(f"خطأ في قاعدة البيانات: {e}")
        result = None
    finally:
        conn.close()
    return result

def db_fetchall(query, params=()):
    conn = sqlite3.connect(DB_FILE, timeout=30)
    cursor = conn.cursor()
    try:
        cursor.execute(query, params)
        result = cursor.fetchall()
    except sqlite3.OperationalError as e:
        logger.error(f"خطأ في قاعدة البيانات: {e}")
        result = []
    finally:
        conn.close()
    return result

# =============================
# دوال إدارة رسائل البوت
# =============================
def save_bot_message(user_id, chat_id, message_type, message_id):
    """حفظ معرف رسالة البوت الأخيرة"""
    try:
        db_execute('''INSERT OR REPLACE INTO bot_messages 
                     (user_id, chat_id, message_type, message_id, timestamp)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_id, chat_id, message_type, message_id, 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ رسالة البوت: {e}")

def get_bot_message(user_id, message_type):
    """الحصول على رسالة البوت المخزنة"""
    try:
        result = db_fetchone('''SELECT chat_id, message_id FROM bot_messages 
                               WHERE user_id = ? AND message_type = ?''',
                            (user_id, message_type))
        return result
    except Exception as e:
        logger.error(f"❌ خطأ في جلب رسالة البوت: {e}")
        return None

def delete_bot_message(user_id, chat_id, message_id):
    """حذف رسالة البوت"""
    try:
        if message_id:
            bot.delete_message(chat_id, message_id)
    except Exception as e:
        logger.error(f"❌ خطأ في حذف رسالة البوت: {e}")

def delete_old_bot_messages(user_id, message_type):
    """حذف الرسائل القديمة لنفس النوع"""
    try:
        result = db_fetchone('''SELECT chat_id, message_id FROM bot_messages 
                               WHERE user_id = ? AND message_type = ?''',
                            (user_id, message_type))
        if result:
            chat_id, message_id = result
            delete_bot_message(user_id, chat_id, message_id)
            db_execute('''DELETE FROM bot_messages 
                         WHERE user_id = ? AND message_type = ?''',
                      (user_id, message_type))
    except Exception as e:
        logger.error(f"❌ خطأ في حذف الرسائل القديمة: {e}")

def safe_edit_message_text(text, chat_id, message_id, reply_markup=None):
    """تحرير رسالة بأمان مع معالجة الأخطاء"""
    try:
        # التحقق من وجود النص قبل التعديل
        if not text or not text.strip():
            logger.error("❌ لا يمكن تعديل رسالة بدون نص")
            return None
            
        bot.edit_message_text(text, chat_id, message_id, 
                            reply_markup=reply_markup, parse_mode="HTML")
        return True
    except telebot.apihelper.ApiTelegramException as e:
        if "message is not modified" in str(e):
            # هذه ليست مشكلة حقيقية، فقط الرسالة لم تتغير
            return True
        elif "message to edit not found" in str(e):
            logger.error("❌ الرسالة المطلوب تعديلها غير موجودة")
            return False
        elif "no text in the message" in str(e):
            logger.error("❌ لا يوجد نص في الرسالة للتعديل")
            return False
        else:
            logger.error(f"❌ خطأ في تعديل الرسالة: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع في تعديل الرسالة: {e}")
        return False

def send_or_edit_message(user_id, chat_id, message_type, text, 
                        reply_markup=None, force_new=False):
    """إرسال رسالة جديدة أو تعديل الرسالة القديمة"""
    try:
        # إذا طُلب رسالة جديدة قسراً، احذف القديمة أولاً
        if force_new:
            delete_old_bot_messages(user_id, message_type)
        
        # حاول الحصول على الرسالة القديمة
        old_message = get_bot_message(user_id, message_type)
        
        if old_message and not force_new:
            old_chat_id, old_message_id = old_message
            
            # حاول تعديل الرسالة القديمة
            if safe_edit_message_text(text, old_chat_id, old_message_id, reply_markup):
                save_bot_message(user_id, old_chat_id, message_type, old_message_id)
                return old_message_id
            else:
                # إذا فشل التعديل، احذف الرسالة القديمة وأرسل جديدة
                delete_bot_message(user_id, old_chat_id, old_message_id)
        
        # إرسال رسالة جديدة
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
        save_bot_message(user_id, chat_id, message_type, msg.message_id)
        return msg.message_id
        
    except Exception as e:
        logger.error(f"❌ خطأ في send_or_edit_message: {e}")
        # حاول إرسال رسالة جديدة رغم الخطأ
        try:
            msg = bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
            save_bot_message(user_id, chat_id, message_type, msg.message_id)
            return msg.message_id
        except Exception as e2:
            logger.error(f"❌ فشل إرسال الرسالة: {e2}")
            return None

# =============================
# دوال الأمان المتقدمة
# =============================
def is_ai_security_enabled():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'ai_security'")
    return result and result[0] == 'enabled'

def get_hack_score_threshold():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'hack_score_threshold'")
    if result:
        try:
            return int(result[0])
        except:
            return 15
    return 15

def is_auto_block_enabled():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'auto_block_hackers'")
    return result and result[0] == 'enabled'

def is_notify_on_hack_enabled():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'notify_on_hack_attempt'")
    return result and result[0] == 'enabled'

# =============================
# نظام كشف الاختراق بالذكاء الاصطناعي
# =============================
def analyze_for_hack_attempts(file_content, filename, user_id):
    """
    دالة الذكاء الاصطناعي لاكتشاف محاولات الاختراق
    تقيم الملف بناء على أنماط هجومية وتعطي درجة خطورة
    """
    hack_score = 0
    detected_patterns = []
    hack_details = []
    security_level = "آمن"
    requires_approval = False
    
    # تحليل المحتوى للبحث عن أنماط هجومية
    for pattern, description, score in HACK_PATTERNS:
        matches = re.findall(pattern, file_content, re.IGNORECASE | re.MULTILINE)
        if matches:
            hack_score += score
            detected_patterns.append(description)
            hack_details.append(f"✅ اكتشاف: {description} (درجة: {score})")
    
    # تحليل المكتبات المحظورة
    lib_pattern = r'^\s*import\s+(\w+)|^\s*from\s+(\w+)\s+import'
    libraries = re.findall(lib_pattern, file_content, re.MULTILINE)
    imported_libs = []
    
    for lib in libraries:
        lib_name = lib[0] or lib[1]
        if lib_name and lib_name in BLOCKED_LIBRARIES:
            hack_score += 8
            detected_patterns.append(f"مكتبة محظورة: {lib_name}")
            hack_details.append(f"🚫 مكتبة محظورة: {lib_name} (درجة: 8)")
            imported_libs.append(lib_name)
    
    # تحليل التوكنات المشبوهة
    token_patterns = [
        r'["\']([0-9]{8,10}:[a-zA-Z0-9_-]{35})["\']',
        r'TOKEN\s*=\s*["\'](fake|test|dummy)["\']',
        r'token\s*=\s*["\'].*hack.*["\']'
    ]
    
    for pattern in token_patterns:
        if re.search(pattern, file_content, re.IGNORECASE):
            hack_score += 5
            detected_patterns.append("توكن مشبوه")
            hack_details.append(f"⚠️ توكن مشبوه (درجة: 5)")
    
    # تحليل محاولات التمويه
    obfuscation_patterns = [
        (r'eval\(.*decode\(.*base64', "تشفير base64 مع eval", 10),
        (r'exec\(.*compile\(', "تنفيذ كود مكتوب", 9),
        (r'__import__\(.*["\']base64["\']\)', "استيراد base64 ديناميكي", 7),
        (r'getattr\(.*__builtins__', "الوصول للبيئة التنفيذية", 8)
    ]
    
    for pattern, description, score in obfuscation_patterns:
        if re.search(pattern, file_content, re.IGNORECASE | re.DOTALL):
            hack_score += score
            detected_patterns.append(description)
            hack_details.append(f"🎭 تمويه: {description} (درجة: {score})")
    
    # تحديد مستوى الأمان
    if hack_score >= 25:
        security_level = "🚨 خطير جداً (محاولة اختراق واضحة)"
        requires_approval = True
    elif hack_score >= 15:
        security_level = "⚠️ خطير (أنماط هجومية متعددة)"
        requires_approval = True
    elif hack_score >= 8:
        security_level = "🔶 متوسط (مشتبه به)"
        requires_approval = True
    elif hack_score >= 3:
        security_level = "🔶 منخفض (قد يكون حميداً)"
        requires_approval = False
    else:
        security_level = "✅ آمن"
        requires_approval = False
    
    # تسجيل محاولة الاختراق إذا كانت خطيرة
    if hack_score >= get_hack_score_threshold():
        log_hack_attempt(user_id, filename, hack_score, detected_patterns)
        
        # إشعار المطور إذا كان الخطر عالي
        if hack_score >= 15 and is_notify_on_hack_enabled():
            send_hack_notification_to_admin(user_id, filename, hack_score, detected_patterns, hack_details)
    
    return {
        'hack_score': hack_score,
        'detected_patterns': detected_patterns,
        'hack_details': hack_details,
        'security_level': security_level,
        'requires_approval': requires_approval,
        'imported_libs': imported_libs
    }

def log_hack_attempt(user_id, filename, hack_score, patterns_found):
    """تسجيل محاولة الاختراق في قاعدة البيانات"""
    patterns_str = " | ".join(patterns_found[:10])  # تقييد طول النص
    db_execute('''INSERT INTO hack_attempts 
                  (user_id, filename, hack_score, detection_time, patterns_found, action_taken, notified_admin)
                  VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (user_id, filename, hack_score, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               patterns_str, "تم الكشف", 1))
    
    # حفظ نسخة من الملف المشبوه
    try:
        hack_file_path = os.path.join(HACK_ATTEMPTS_FOLDER, f"{user_id}_{filename}_{int(time.time())}.py")
        original_file = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(original_file):
            shutil.copy2(original_file, hack_file_path)
            
            # إضافة معلومات التحليل للملف
            with open(hack_file_path, 'a', encoding='utf-8') as f:
                f.write(f"\n\n# ===== تحليل الذكاء الاصطناعي =====\n")
                f.write(f"# درجة الاختراق: {hack_score}\n")
                f.write(f"# الأنماط المكتشفة: {patterns_str}\n")
                f.write(f"# الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# المستخدم: {user_id}\n")
    except Exception as e:
        logger.error(f"❌ فشل حفظ ملف الاختراق: {e}")

def send_hack_notification_to_admin(user_id, filename, hack_score, patterns, details):
    """إرسال إشعار للمطور عن محاولة اختراق"""
    try:
        user_info = db_fetchone("SELECT first_seen FROM known_users WHERE user_id = ?", (user_id,))
        user_text = f"مستخدم {user_id}" if not user_info else f"مستخدم مسجل ({user_id})"
        
        patterns_text = "\n".join([f"• {p}" for p in patterns[:5]])
        details_text = "\n".join(details[:10])
        
        message = f"""
🚨 <b>تنبيه عالي! اكتشاف محاولة اختراق</b>

🔍 <b>تفاصيل الاكتشاف:</b>
𖤓 الملف: <code>{filename}</code>
𖤓 المستخدم: {user_text}
𖤓 درجة الخطر: {hack_score}/100
𖤓 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚠️ <b>الأنماط المكتشفة:</b>
{patterns_text}

📊 <b>تفاصيل التحليل:</b>
{details_text}

🛡️ <b>الإجراءات المطلوبة:</b>
• مراجعة الملف يدوياً
• تقييم خطورة المستخدم
• اتخاذ قرار بالقبول/الرفض
        """
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ قبول الملف", callback_data=f"admin_accept_file:{filename}:{user_id}"),
            types.InlineKeyboardButton("❌ رفض الملف", callback_data=f"admin_reject_file:{filename}:{user_id}")
        )
        markup.add(
            types.InlineKeyboardButton("⛔ حظر المستخدم", callback_data=f"admin_ban_user:{user_id}:hack_attempt"),
            types.InlineKeyboardButton("📁 عرض الملف", callback_data=f"admin_view_file:{filename}")
        )
        markup.add(
            types.InlineKeyboardButton("📊 سجل الاختراقات", callback_data="view_hack_logs"),
            types.InlineKeyboardButton("🔕 تجاهل", callback_data=f"admin_ignore_alert:{filename}")
        )
        
        # حفظ الإشعار في قاعدة البيانات
        notification_details = f"هجوم درجة: {hack_score}, أنماط: {', '.join(patterns[:3])}"
        db_execute('''INSERT INTO admin_notifications 
                      (notification_type, user_id, filename, details, notification_time, status)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                  ('hack_attempt', user_id, filename, notification_details,
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'pending'))
        
        bot.send_message(DEVELOPER_ID, message, reply_markup=markup)
        logger.warning(f"🚨 تم إرسال إشعار اختراق للمطور: {filename} - درجة: {hack_score}")
        
    except Exception as e:
        logger.error(f"❌ فشل إرسال إشعار الاختراق: {e}")

def generate_hack_report(user_id, filename, hack_analysis):
    """إنشاء تقرير مفصل عن محاولة الاختراق"""
    report = f"""
📋 <b>تقرير تحليل الأمان - الذكاء الاصطناعي</b>

🔐 <b>معلومات الملف:</b>
𖤓 اسم الملف: {filename}
𖤓 المستخدم: {user_id}
𖤓 وقت التحليل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚡ <b>نتائج التحليل:</b>
𖤓 درجة الخطورة: {hack_analysis['hack_score']}/100
𖤓 مستوى الأمان: {hack_analysis['security_level']}
𖤓 يتطلب موافقة: {'نعم' if hack_analysis['requires_approval'] else 'لا'}

⚠️ <b>التهديدات المكتشفة:</b>
"""
    
    for detail in hack_analysis['hack_details']:
        report += f"• {detail}\n"
    
    if hack_analysis['imported_libs']:
        report += f"\n📦 <b>المكتبات المحظورة:</b>\n"
        for lib in hack_analysis['imported_libs']:
            report += f"• {lib}\n"
    
    report += f"\n🛡️ <b>توصيات النظام:</b>\n"
    if hack_analysis['hack_score'] >= 25:
        report += "• ⛔ رفض الملف فوراً (خطر عالي)\n• 🚫 حظر المستخدم المحتمل\n• 📋 مراجعة يدوية من المطور"
    elif hack_analysis['hack_score'] >= 15:
        report += "• ⚠️ طلب موافقة المطور\n• 🔍 فحص يدوي إضافي\n• 👁️ مراقبة نشاط المستخدم"
    elif hack_analysis['hack_score'] >= 8:
        report += "• 🔶 تحذير المستخدم\n• 📝 طلب شرح للكود\n• ⏱️ مراقبة محدودة"
    else:
        report += "• ✅ الملف آمن نسبياً\n• 📊 متابعة روتينية\n• 🟢 يمكن المتابعة"
    
    return report

# =============================
# دوال المساعدة الإضافية
# =============================
def get_bot_stats():
    """الحصول على إحصائيات البوت"""
    total_users = db_fetchone("SELECT COUNT(*) FROM known_users")[0] or 0
    total_files = db_fetchone("SELECT COUNT(*) FROM files")[0] or 0
    active_files = len(running_processes)
    total_points = db_fetchone("SELECT SUM(points) FROM users_points")[0] or 0
    hack_attempts = db_fetchone("SELECT COUNT(*) FROM hack_attempts")[0] or 0
    blocked_uploads = db_fetchone("SELECT COUNT(*) FROM blocked_uploads")[0] or 0
    banned_users = db_fetchone("SELECT COUNT(*) FROM banned_users")[0] or 0
    
    return {
        'total_users': total_users,
        'total_files': total_files,
        'active_files': active_files,
        'total_points': total_points,
        'hack_attempts': hack_attempts,
        'blocked_uploads': blocked_uploads,
        'banned_users': banned_users
    }

def get_all_users(limit=50):
    """الحصول على قائمة المستخدمين"""
    users = db_fetchall("SELECT user_id, first_seen, last_seen FROM known_users ORDER BY last_seen DESC LIMIT ?", (limit,))
    return users

def get_all_files(limit=50):
    """الحصول على قائمة جميع الملفات"""
    files = db_fetchall("SELECT filename, user_id, upload_time, status, security_level FROM files ORDER BY upload_time DESC LIMIT ?", (limit,))
    return files

# =============================
# دوال الأسعار الجديدة
# =============================
def get_price(price_type):
    result = db_fetchone("SELECT price_value FROM prices WHERE price_type = ?", (price_type,))
    if result:
        return int(result[0])
    return 0

def set_price(price_type, price_value):
    try:
        price_value = int(price_value)
        if price_value < 0:
            return False, "السعر يجب أن يكون رقم موجب"
        
        db_execute("INSERT OR REPLACE INTO prices (price_type, price_value) VALUES (?, ?)", 
                  (price_type, price_value))
        
        # تحديث الإعدادات أيضًا
        db_execute("UPDATE bot_settings SET setting_value = ? WHERE setting_key = ?", 
                  (str(price_value), price_type))
        
        return True, f"تم تحديث سعر {price_type} إلى {price_value}"
    except ValueError:
        return False, "السعر يجب أن يكون رقم صحيح"

# =============================
# دوال الصلاحيات والتحقق - معدلة
# =============================
def is_admin(user_id):
    result = db_fetchone("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    return result is not None or user_id == DEVELOPER_ID

def is_vip(user_id):
    result = db_fetchone("SELECT user_id FROM vip_users WHERE user_id = ? AND status = 'active'", (user_id,))
    return result is not None

def is_pro(user_id):
    result = db_fetchone("SELECT user_id FROM pro_users WHERE user_id = ? AND status = 'active'", (user_id,))
    return result is not None

def bot_enabled():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'bot_status'")
    return result and result[0] == 'enabled'

def is_paid_mode():
    result = db_fetchone("SELECT setting_value FROM bot_settings WHERE setting_key = 'paid_mode'")
    return result and result[0] == 'enabled'

def is_vip_mode():
    result = db_fetchone("SELECT setting_value FROM security_settings WHERE setting_key = 'vip_mode'")
    return result and result[0] == 'true'

def is_banned(user_id):
    """هل المستخدم محظور؟"""
    row = db_fetchone("SELECT user_id FROM banned_users WHERE user_id = ?", (user_id,))
    return row is not None

def is_upload_blocked(user_id):
    """هل المستخدم محظور من رفع الملفات؟"""
    row = db_fetchone("SELECT user_id FROM blocked_uploads WHERE user_id = ?", (user_id,))
    return row is not None

def ban_user(user_id, banned_by=None, reason="محظور"):
    """حظر مستخدم (يحفظ في DB)"""
    try:
        db_execute("INSERT OR IGNORE INTO banned_users (user_id, banned_by, ban_time, reason) VALUES (?, ?, ?, ?)",
                   (user_id, banned_by or DEVELOPER_ID, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason))
        return True
    except Exception as e:
        logger.error(f"❌ فشل حظر المستخدم {user_id}: {e}")
        return False

def unban_user(user_id):
    try:
        db_execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
        return True
    except Exception as e:
        logger.error(f"❌ فشل فك الحظر للمستخدم {user_id}: {e}")
        return False

def block_user_uploads(user_id, blocked_by=None, reason="محظور من رفع الملفات"):
    """حظر مستخدم من رفع الملفات"""
    try:
        db_execute("INSERT OR IGNORE INTO blocked_uploads (user_id, blocked_by, block_time, reason) VALUES (?, ?, ?, ?)",
                   (user_id, blocked_by or DEVELOPER_ID, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reason))
        return True
    except Exception as e:
        logger.error(f"❌ فشل حظر رفع الملفات للمستخدم {user_id}: {e}")
        return False

def unblock_user_uploads(user_id):
    """فك حظر مستخدم من رفع الملفات"""
    try:
        db_execute("DELETE FROM blocked_uploads WHERE user_id = ?", (user_id,))
        return True
    except Exception as e:
        logger.error(f"❌ فشل فك حظر رفع الملفات للمستخدم {user_id}: {e}")
        return False

def check_subscription(user_id):
    if user_id == DEVELOPER_ID or is_admin(user_id):
        return True

    channels = db_fetchall("SELECT channel_id, channel_username FROM force_subscribe")
    if not channels:
        return True

    for channel in channels:
        channel_id, channel_username = channel
        targets = []
        if channel_id:
            targets.append(channel_id)
        if channel_username:
            targets.append(channel_username)
            if channel_username.startswith("@"):
                targets.append(channel_username[1:])
        
        ok_for_channel = False
        for t in targets:
            try:
                member = bot.get_chat_member(t, user_id)
                if member and getattr(member, "status", "") in ['member', 'administrator', 'creator']:
                    ok_for_channel = True
                    break
            except Exception:
                continue
        
        if not ok_for_channel:
            return False
    return True

def get_security_setting(setting_key):
    result = db_fetchone("SELECT setting_value FROM security_settings WHERE setting_key = ?", (setting_key,))
    return result[0] if result else None

# =============================
# نظام النقاط والدعوات والهدايا
# =============================
def ensure_user_points_row(user_id):
    if not db_fetchone("SELECT user_id FROM users_points WHERE user_id = ?", (user_id,)):
        db_execute("INSERT OR IGNORE INTO users_points (user_id, points, first_free_used) VALUES (?, ?, ?)", (user_id, 0, 0))

def get_points(user_id):
    ensure_user_points_row(user_id)
    row = db_fetchone("SELECT points FROM users_points WHERE user_id = ?", (user_id,))
    return row[0] if row else 0

def add_points(user_id, amount, admin_id=None, reason=None):
    """إضافة نقاط للمستخدم وتسجيل العملية"""
    ensure_user_points_row(user_id)
    
    # تسجيل العملية إذا كان هناك أدمن
    if admin_id:
        db_execute('''INSERT INTO points_transactions 
                     (user_id, admin_id, amount, transaction_type, reason, transaction_time)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, admin_id, amount, 'add', reason or 'إضافة من الأدمن', 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    db_execute("UPDATE users_points SET points = points + ? WHERE user_id = ?", (amount, user_id))
    return get_points(user_id)

def deduct_points(user_id, amount, admin_id=None, reason=None):
    """خصم نقاط من المستخدم وتسجيل العملية"""
    ensure_user_points_row(user_id)
    pts = get_points(user_id)
    
    if pts < amount:
        return False, "رصيد المستخدم غير كافي"
    
    # تسجيل العملية إذا كان هناك أدمن
    if admin_id:
        db_execute('''INSERT INTO points_transactions 
                     (user_id, admin_id, amount, transaction_type, reason, transaction_time)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (user_id, admin_id, amount, 'deduct', reason or 'خصم من الأدمن', 
                   datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    db_execute("UPDATE users_points SET points = points - ? WHERE user_id = ?", (amount, user_id))
    return True, f"تم خصم {amount} نقطة"

def spend_points(user_id, amount):
    ensure_user_points_row(user_id)
    pts = get_points(user_id)
    if pts < amount:
        return False
    db_execute("UPDATE users_points SET points = points - ? WHERE user_id = ?", (amount, user_id))
    return True

def has_used_first_free(user_id):
    ensure_user_points_row(user_id)
    row = db_fetchone("SELECT first_free_used FROM users_points WHERE user_id = ?", (user_id,))
    return bool(row and row[0])

def set_first_free_used(user_id):
    ensure_user_points_row(user_id)
    db_execute("UPDATE users_points SET first_free_used = 1 WHERE user_id = ?", (user_id,))

def generate_referral_code(user_id):
    code = uuid.uuid4().hex[:8]
    points_per_ref = get_price('referral_price')
    db_execute("INSERT OR IGNORE INTO referral_links (user_id, code, created_at, points_per_ref, uses) VALUES (?, ?, ?, ?, ?)",
               (user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), points_per_ref, 0))
    row = db_fetchone("SELECT code FROM referral_links WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
    return row[0] if row else code

def process_referral_code(code, referred_user_id):
    row = db_fetchone("SELECT user_id, points_per_ref, uses FROM referral_links WHERE code = ?", (code,))
    if not row:
        return False, "غير صالح"
    referrer_id, points_per_ref, uses = row
    if referrer_id == referred_user_id:
        return False, "لا يمكنك دعوة نفسك"
    existing = db_fetchone("SELECT id FROM referrals WHERE referrer_id = ? AND referred_id = ?", (referrer_id, referred_user_id))
    if existing:
        return False, "تم استخدام الدعوة سابقاً"
    add_points(referrer_id, points_per_ref)
    db_execute("INSERT INTO referrals (referrer_id, referred_id, code, time) VALUES (?, ?, ?, ?)",
               (referrer_id, referred_user_id, code, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    db_execute("UPDATE referral_links SET uses = uses + 1 WHERE code = ?", (code,))
    return True, f"تم منح {points_per_ref} نقطة للمستخدم الذي دعاك"

def redeem_gift_code(code, user_id):
    row = db_fetchone("SELECT id, points, max_uses, used_count, expires_at FROM gift_codes WHERE code = ?", (code,))
    if not row:
        return False, "كود غير موجود"
    gid, points, max_uses, used_count, expires_at = row
    if max_uses is not None and used_count >= max_uses:
        return False, "انتهت صلاحيات هذا الكود"
    if expires_at:
        try:
            exp = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
            if datetime.now() > exp:
                return False, "انتهى تاريخ صلاحية الكود"
        except Exception:
            pass
    add_points(user_id, points)
    db_execute("UPDATE gift_codes SET used_count = used_count + 1 WHERE id = ?", (gid,))
    return True, f"تمت إضافة {points} نقطة لحسابك"

# =============================
# استخراج التوكن وتحليل الملفات
# =============================
def extract_token_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        patterns = [
            r'bot\.TeleBot\(["\']([^"\']+)["\']\)',
            r'telebot\.TeleBot\(["\']([^"\']+)["\']\)',
            r'TOKEN\s*=\s*["\']([^"\']+)["\']',
            r'token\s*=\s*["\']([^"\']+)["\']',
            r'["\']([0-9]{8,10}:[a-zA-Z0-9_-]{35})["\']'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(1)
        
        return None
    except Exception as e:
        logger.error(f"❌ خطأ في استخراج التوكن: {e}")
        return None

def validate_token(token):
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10)
        return response.status_code == 200
    except Exception:
        return False

def get_token_info(token):
    try:
        url = f"https://api.telegram.org/bot{token}/getMe"
        response = requests.get(url, timeout=10).json()
        if response.get("ok"):
            bot_info = response.get("result", {})
            return f"""
<b>معلومات التوكن:</b>

𖤓 <b>اسم البوت:</b> {bot_info.get('first_name', 'غير معروف')}
𖤓 <b>يوزر البوت:</b> @{bot_info.get('username', 'غير معروف')}
𖤓 <b>آيدي البوت:</b> {bot_info.get('id', 'غير معروف')}
𖤓 <b>الحالة:</b> التوكن صالح ويعمل
            """
        else:
            return " التوكن غير صالح أو لا يعمل"
    except Exception:
        return " فشل في التحقق من التوكن"

def save_token_to_file(filename, token, user_id):
    try:
        token_file = os.path.join(TOKENS_FOLDER, f"{filename}_token.txt")
        with open(token_file, 'w', encoding='utf-8') as f:
            f.write(f"الملف: {filename}\n")
            f.write(f"المستخدم: {user_id}\n")
            f.write(f"التوكن: {token}\n")
            f.write(f"التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        return True
    except Exception as e:
        logger.error(f" خطأ في حفظ التوكن: {e}")
        return False

def analyze_file(file_path, filename, user_id):
    analysis_result = {
        'issues_found': 0,
        'dangerous_libs': [],
        'malicious_patterns': [],
        'file_size': 0,
        'lines_of_code': 0,
        'syntax_errors': False,
        'status': 'safe',
        'libraries': [],
        'token_found': False,
        'token': None,
        'errors': [],
        'hack_analysis': None,
        'requires_approval': False,
        'security_level': 'آمن'
    }
    
    try:
        file_size = os.path.getsize(file_path)
        analysis_result['file_size'] = file_size
        
        max_size = int(get_security_setting('max_file_size') or 10240)
        if file_size > max_size * 1024:
            analysis_result['issues_found'] += 1
            analysis_result['status'] = 'too_large'
            analysis_result['errors'].append(f"الملف كبير جداً: {file_size} بايت > {max_size} كيلوبايت")
            return analysis_result
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        lines = content.split('\n')
        analysis_result['lines_of_code'] = len(lines)
        
        token = extract_token_from_file(file_path)
        if token:
            analysis_result['token_found'] = True
            analysis_result['token'] = token
            save_token_to_file(filename, token, user_id)
        
        lib_pattern = r'^\s*import\s+(\w+)|^\s*from\s+(\w+)\s+import'
        libraries = re.findall(lib_pattern, content, re.MULTILINE)
        for lib in libraries:
            lib_name = lib[0] or lib[1]
            if lib_name and lib_name not in analysis_result['libraries']:
                analysis_result['libraries'].append(lib_name)
        
        try:
            ast.parse(content)
        except SyntaxError as e:
            analysis_result['syntax_errors'] = True
            analysis_result['issues_found'] += 1
            analysis_result['status'] = 'syntax_error'
            analysis_result['errors'].append(f"خطأ نحوي: {str(e)}")
        
        for lib in BLOCKED_LIBRARIES:
            if re.search(rf'^\s*import\s+{lib}\s*$|^\s*from\s+{lib}\s+import', content, re.MULTILINE):
                analysis_result['dangerous_libs'].append(lib)
                analysis_result['issues_found'] += 1
                analysis_result['errors'].append(f"تم استخدام مكتبة محظورة: {lib}")
        
        for pattern in THREAT_PATTERNS:
            if re.search(pattern, content):
                analysis_result['malicious_patterns'].append(pattern)
                analysis_result['issues_found'] += 1
                analysis_result['errors'].append(f"تم اكتشاف نمط خطير: {pattern}")
        
        # ===== تحليل الذكاء الاصطناعي للأمن =====
        if is_ai_security_enabled():
            hack_analysis = analyze_for_hack_attempts(content, filename, user_id)
            analysis_result['hack_analysis'] = hack_analysis
            analysis_result['requires_approval'] = hack_analysis['requires_approval']
            analysis_result['security_level'] = hack_analysis['security_level']
            
            if hack_analysis['hack_score'] >= get_hack_score_threshold():
                analysis_result['status'] = 'hack_detected'
                analysis_result['issues_found'] += 1
                analysis_result['errors'].append(f"تم اكتشاف محاولة اختراق (درجة: {hack_analysis['hack_score']})")
        
        if analysis_result['issues_found'] > 0:
            if analysis_result['status'] != 'hack_detected':
                analysis_result['status'] = 'suspicious'
        
        dangerous_libs_str = ','.join(analysis_result['dangerous_libs'])
        malicious_patterns_str = ','.join(analysis_result['malicious_patterns'])
        libraries_str = ','.join(analysis_result['libraries'])
        
        # تسجيل تحليل الذكاء الاصطناعي إذا كان موجوداً
        hack_detected = 1 if analysis_result.get('hack_analysis') and analysis_result['hack_analysis']['hack_score'] > 0 else 0
        hack_score = analysis_result['hack_analysis']['hack_score'] if analysis_result.get('hack_analysis') else 0
        hack_details = " | ".join(analysis_result['hack_analysis']['detected_patterns']) if analysis_result.get('hack_analysis') else None
        
        db_execute('''INSERT INTO file_analysis 
                     (filename, user_id, analysis_time, issues_found, dangerous_libs, 
                      malicious_patterns, file_size, lines_of_code, hack_detected, hack_score, hack_details)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (filename, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   analysis_result['issues_found'], dangerous_libs_str, 
                   malicious_patterns_str, file_size, len(lines),
                   hack_detected, hack_score, hack_details))
        
        db_execute('''UPDATE files SET libraries = ?, token = ?, security_level = ?, hack_score = ?, requires_approval = ? WHERE filename = ?''',
                  (libraries_str, token, analysis_result['security_level'], hack_score, 
                   1 if analysis_result['requires_approval'] else 0, filename))
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحليل الملف: {e}")
        analysis_result['status'] = 'analysis_error'
        analysis_result['errors'].append(f"خطأ في التحليل: {str(e)}")
    
    return analysis_result

def install_libraries(libraries):
    results = []
    for lib in libraries:
        try:
            subprocess.check_call(["pip", "install", lib])
            results.append(f"✅ {lib} تم التثبيت")
        except Exception as e:
            results.append(f"❌ {lib} فشل: {str(e)}")
    return results

def simulate_ai_fix(file_content, errors):
    fixed_content = file_content
    suggestions = []
    requires_approval = False

    if "eval(" in file_content:
        fixed_content = fixed_content.replace("eval(", "ast.literal_eval(")
        suggestions.append("تم استبدال eval() بـ ast.literal_eval() لأمان أكثر")
    
    open_pattern = r'(^\s*)([^\n]*?)open\s*\(([^)]*)\)'
    if "open(" in file_content and "with open" not in file_content:
        suggestions.append("تم اقتراح استخدام with open() بدلاً من open() لضمان غلق الملفات")
        requires_approval = True
    
    if "subprocess.Popen" in file_content or "os.system" in file_content:
        suggestions.append("تم اكتشاف استدعاءات لنظام التشغيل (subprocess/os.system). يُنصح بتجنبها أو تقييدها.")
        requires_approval = True
    
    for lib in BLOCKED_LIBRARIES:
        if re.search(rf'^\s*import\s+{lib}\s*$|^\s*from\s+{lib}\s+import', file_content, re.MULTILINE):
            suggestions.append(f"اكتشاف مكتبة محظورة: {lib} — مقترح: إزالتها أو استبدالها بمكتبة آمنة")
            requires_approval = True

    if not suggestions:
        suggestions.append("الملف يبدو جيداً، لا توجد اقتراحات تلقائية")
    
    return fixed_content, suggestions, requires_approval

# =============================
# معالجة ملفات ZIP
# =============================
def extract_zip_file(zip_path, user_id):
    try:
        extract_dir = os.path.join(UPLOAD_FOLDER, f"extracted_{user_id}_{int(time.time())}")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        extracted_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    extracted_files.append(file_path)
        
        return True, extracted_files, extract_dir
    except Exception as e:
        return False, [], str(e)

# =============================
# كليشة الترحيب الجديدة
# =============================
WELCOME_MESSAGE = """
🤍 أهلاً بك عزيزي! 

𖤓 مرحباً بك في بوت استضافة ملفات PY & ZIP 𖤓

• رفع وتشغيل ملفات Python
• استخراج وتشغيل ملفات ZIP
• نظام نقاط متكامل
• دعوة الأصدقاء وربح النقاط
• 🛡️ نظام حماية ذكي لاكتشاف الاختراق

𖤓 المطور: @S7ASA7 𖤓

استخدم الأزرار للبدء ↙️
"""

# =============================
# دوال المستخدم والمجلدات - معدلة لحل مشكلة UNIQUE constraint
# =============================
def register_user_if_new(user_id, first_name, username, start_payload=None):
    try:
        existing = db_fetchone("SELECT user_id FROM known_users WHERE user_id = ?", (user_id,))
        if not existing:
            db_execute("INSERT INTO known_users (user_id, first_seen, last_seen) VALUES (?, ?, ?)",
                      (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            ensure_user_points_row(user_id)
            
            if start_payload:
                if start_payload.startswith("ref_"):
                    code = start_payload.split("ref_",1)[1]
                    ok, msg = process_referral_code(code, user_id)
                    try:
                        bot.send_message(user_id, f"<pre>{msg}</pre>")
                    except:
                        pass
                elif start_payload.startswith("gift_"):
                    code = start_payload.split("gift_",1)[1]
                    ok, msg = redeem_gift_code(code, user_id)
                    try:
                        bot.send_message(user_id, f"<pre>{msg}</pre>")
                    except:
                        pass
            
            user_info = f"@{username}" if username else f"{first_name} ({user_id})"
            try:
                bot.send_message(
                    DEVELOPER_ID,
                    f"👤 مستخدم جديد دخل البوت!\n\n"
                    f"𖤓 المستخدم: {user_info}\n"
                    f"𖤓 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"𖤓 آيدي: {user_id}"
                )
            except:
                pass
        else:
            db_execute("UPDATE known_users SET last_seen = ? WHERE user_id = ?",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))
    except sqlite3.IntegrityError as e:
        logger.error(f"خطأ في تسجيل المستخدم: {e}")
        # حاول تحديث آخر ظهور بدلاً من الإدراج
        db_execute("UPDATE known_users SET last_seen = ? WHERE user_id = ?",
                  (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_id))

def create_user_folder(user_id, folder_name):
    user_folder_path = os.path.join(FOLDERS_FOLDER, str(user_id))
    os.makedirs(user_folder_path, exist_ok=True)
    
    folder_path = os.path.join(user_folder_path, folder_name)
    if os.path.exists(folder_path):
        return False, "المجلد موجود بالفعل"
    
    os.makedirs(folder_path)
    db_execute("INSERT INTO user_folders (user_id, folder_name, created_time) VALUES (?, ?, ?)",
              (user_id, folder_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    return True, folder_path

def delete_all_user_folders(user_id):
    user_folder_path = os.path.join(FOLDERS_FOLDER, str(user_id))
    if os.path.exists(user_folder_path):
        shutil.rmtree(user_folder_path)
        db_execute("DELETE FROM user_folders WHERE user_id = ?", (user_id,))
        return True
    return False

def count_active_files(user_id):
    active_files = db_fetchall("SELECT filename FROM files WHERE user_id = ? AND status = 'active'", (user_id,))
    count = 0
    for file in active_files:
        if file[0] in running_processes:
            count += 1
    return count

# =============================
# اللوحات والازرار - معدلة مع الميزات الجديدة
# =============================
def main_dark_panel(user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("📤 رفع ملف (PY/ZIP)", callback_data="upload"),
        types.InlineKeyboardButton(f"حالتي: {'⭐ VIP' if is_vip(user_id) else '🚀 عادي'}", callback_data="my_status")
    )
    
    markup.add(
        types.InlineKeyboardButton("📂 ملفاتي", callback_data="list_files"),
        types.InlineKeyboardButton("💎 نقاطي", callback_data="points")
    )
    
    if not is_vip(user_id) and not is_pro(user_id):
        markup.add(types.InlineKeyboardButton("⭐ ترقية VIP", callback_data="request_vip"))
    
    active_count = count_active_files(user_id)
    markup.add(
        types.InlineKeyboardButton(f"▶️ نشط: {active_count}", callback_data="show_active"),
        types.InlineKeyboardButton("⏸ إيقاف الكل", callback_data="stop_all")
    )
    
    markup.add(
        types.InlineKeyboardButton("🎁 الهدايا", callback_data="gifts"),
        types.InlineKeyboardButton("🔗 دعوة", callback_data="referral")
    )
    
    markup.add(
        types.InlineKeyboardButton("ℹ️ مساعدة", callback_data="help"),
        types.InlineKeyboardButton("🎀 المطور", url=f"https://t.me/{developer}")
    )
    
    if is_admin(user_id):
        markup.add(types.InlineKeyboardButton("🛠️ لوحة الأدمن", callback_data="admin_panel"))
    
    return markup

def admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton("💰 سعر رفع الملفات", callback_data="set_upload_price"),
        types.InlineKeyboardButton("💰 سعر رابط الدعوة", callback_data="set_ref_price")
    )
    
    markup.add(
        types.InlineKeyboardButton("👥 إدارة المستخدمين", callback_data="manage_users"),
        types.InlineKeyboardButton("📁 إدارة الملفات", callback_data="manage_files")
    )
    
    markup.add(
        types.InlineKeyboardButton("⭐ VIP/PRO", callback_data="manage_vip"),
        types.InlineKeyboardButton("📢 البث", callback_data="broadcast")
    )
    
    markup.add(
        types.InlineKeyboardButton("🎁 إنشاء هدية", callback_data="create_gift"),
        types.InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
    )
    
    markup.add(
        types.InlineKeyboardButton("🛡️ إعدادات الأمان", callback_data="security_settings"),
        types.InlineKeyboardButton("🚨 سجلات الاختراق", callback_data="hack_logs")
    )
    
    # إضافة الأزرار الجديدة
    markup.add(
        types.InlineKeyboardButton("➕ إضافة نقاط", callback_data="admin_add_points"),
        types.InlineKeyboardButton("➖ خصم نقاط", callback_data="admin_deduct_points")
    )
    
    markup.add(
        types.InlineKeyboardButton("⛔ حظر عضو", callback_data="admin_ban_user_menu"),
        types.InlineKeyboardButton("✅ فك حظر عضو", callback_data="admin_unban_user_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton("🚫 منع رفع ملفات", callback_data="admin_block_uploads_menu"),
        types.InlineKeyboardButton("📤 فك منع رفع", callback_data="admin_unblock_uploads_menu")
    )
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
    
    return markup

def file_control_panel(filename, user_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    is_running = filename in running_processes
    btn_toggle = types.InlineKeyboardButton(f"{'⏸ إيقاف' if is_running else '▶️ تشغيل'}", callback_data=f"toggle_{filename}")
    btn_change_token = types.InlineKeyboardButton("🔁 تغيير التوكن", callback_data=f"change_token_{filename}")
    btn_token_info = types.InlineKeyboardButton("ℹ️ معلومات", callback_data=f"token_info_{filename}")
    btn_download = types.InlineKeyboardButton("📥 تنزيل", callback_data=f"download_{filename}")
    btn_delete = types.InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{filename}")
    btn_preview = types.InlineKeyboardButton("🔍 معاينة", callback_data=f"preview_{filename}")
    
    markup.add(btn_toggle, btn_change_token)
    markup.add(btn_token_info, btn_download)
    markup.add(btn_delete, btn_preview)
    
    if is_pro(user_id) or is_vip(user_id):
        btn_ai_fix = types.InlineKeyboardButton("🛠️ إصلاح", callback_data=f"ai_fix_{filename}")
        markup.add(btn_ai_fix)
    
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="list_files"))
    
    return markup

# =============================
# دوال الميزات الجديدة
# =============================
def create_gift_code_admin(user_id, points, max_uses, days):
    """إنشاء كود هدية من قبل الأدمن"""
    try:
        code = uuid.uuid4().hex[:8].upper()
        expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        
        db_execute("INSERT INTO gift_codes (code, creator_id, points, max_uses, expires_at) VALUES (?, ?, ?, ?, ?)",
                  (code, user_id, points, max_uses, expires_at))
        
        bot_username = bot.get_me().username or "البوت"
        return f"""
✅ <b>تم إنشاء كود الهدية</b>

𖤓 الكود: <code>{code}</code>
𖤓 النقاط: {points}
𖤓 عدد الاستخدامات: {max_uses}
𖤓 تاريخ الانتهاء: {expires_at}

🔗 رابط الاستخدام:
اضغط /start ثم أرسل: gift_{code}
أو:
https://t.me/{bot_username}?start=gift_{code}
        """
    except Exception as e:
        logger.error(f"❌ خطأ في إنشاء كود الهدية: {e}")
        return f"❌ فشل إنشاء الكود: {str(e)}"

def get_user_info(user_id):
    """الحصول على معلومات المستخدم"""
    user = db_fetchone("SELECT first_seen, last_seen FROM known_users WHERE user_id = ?", (user_id,))
    points = get_points(user_id)
    is_banned_user = is_banned(user_id)
    is_upload_blocked_user = is_upload_blocked(user_id)
    files_count = db_fetchone("SELECT COUNT(*) FROM files WHERE user_id = ?", (user_id,))[0] or 0
    
    if user:
        first_seen, last_seen = user
        return {
            'exists': True,
            'first_seen': first_seen,
            'last_seen': last_seen,
            'points': points,
            'is_banned': is_banned_user,
            'is_upload_blocked': is_upload_blocked_user,
            'files_count': files_count
        }
    return {'exists': False}

# =============================
# معالجات الرسائل - معدلة مع الميزات الجديدة
# =============================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.from_user.id
    payload = None
    if message.text and len(message.text.split()) > 1:
        payload = message.text.split()[1]
    
    if is_banned(user_id):
        row = db_fetchone("SELECT reason FROM banned_users WHERE user_id = ?", (user_id,))
        reason = row[0] if row else "محظور من النظام"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("📨 طلب فك الحظر", callback_data=f"request_unban:{user_id}"))
        bot.send_message(user_id, f"<pre>⛔ أنت محظور من البوت.\nالسبب: {reason}</pre>", reply_markup=markup)
        return
    
    # التحقق إذا كان محظور من رفع الملفات
    if is_upload_blocked(user_id):
        row = db_fetchone("SELECT reason FROM blocked_uploads WHERE user_id = ?", (user_id,))
        reason = row[0] if row else "محظور من رفع الملفات"
        bot.send_message(user_id, f"<pre>🚫 أنت محظور من رفع الملفات.\nالسبب: {reason}</pre>")
    
    register_user_if_new(user_id, message.from_user.first_name, message.from_user.username, start_payload=payload)
    
    if not bot_enabled():
        bot.send_message(message.chat.id, "<pre>🚫 البوت معطل حالياً</pre>")
        return
    
    if is_paid_mode() and not is_admin(user_id):
        bot.send_message(message.chat.id, f"<pre>💵 البوت في وضع مدفوع\nللاشتراك تواصل مع المطور\n@{developer}</pre>")
        return
    
    if not check_subscription(user_id):
        channels = db_fetchall("SELECT channel_id, channel_username FROM force_subscribe")
        if channels:
            markup = types.InlineKeyboardMarkup()
            for channel in channels:
                channel_id, channel_username = channel
                if channel_username:
                    username = channel_username
                    if username.startswith("@"):
                        username = username[1:]
                    btn = types.InlineKeyboardButton(f"@{username}", url=f"https://t.me/{username}")
                    markup.add(btn)
            
            btn_check = types.InlineKeyboardButton("✅ تحقق", callback_data="check_subscription")
            markup.add(btn_check)
            
            bot.send_message(message.chat.id, "<pre>📢 اشترك في القنوات أولاً:</pre>", reply_markup=markup)
            return
    
    # استخدام send_or_edit_message لإرسال أو تعديل الرسالة
    send_or_edit_message(user_id, message.chat.id, 'main_menu', 
                        WELCOME_MESSAGE, 
                        reply_markup=main_dark_panel(user_id))

@bot.message_handler(commands=["admin"])
def admin_command(message):
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "<pre>🚫 لا تمتلك صلاحيات</pre>")
        return
    
    admin_msg = """
<pre>🛠️ <b>لوحة تحكم الأدمن</b>

يمكنك التحكم الكامل في البوت:

• إدارة المستخدمين والملفات
• تعديل الأسعار (رفع ملفات/دعوة)
• إدارة الهدايا والكوبونات
• إعدادات الأمان
• نظام كشف الاختراق بالذكاء الاصطناعي
• VIP & PRO
• <b>الميزات الجديدة:</b>
  - إنشاء أكواد هدايا
  - إضافة/خصم نقاط
  - حظر/فك حظر الأعضاء
  - منع/فك منع رفع الملفات

اختر من القائمة:</pre>
    """
    
    # استخدام send_or_edit_message لإرسال أو تعديل الرسالة
    send_or_edit_message(user_id, message.chat.id, 'admin_panel', 
                        admin_msg, reply_markup=admin_panel())

@bot.message_handler(content_types=['document'])
def handle_document(message):
    try:
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        if is_banned(user_id):
            bot.send_message(user_id, "<pre>⛔ أنت محظور من البوت</pre>")
            return
        
        # التحقق إذا كان محظور من رفع الملفات
        if is_upload_blocked(user_id):
            row = db_fetchone("SELECT reason FROM blocked_uploads WHERE user_id = ?", (user_id,))
            reason = row[0] if row else "محظور من رفع الملفات"
            bot.reply_to(message, f"<pre>🚫 أنت محظور من رفع الملفات.\nالسبب: {reason}</pre>")
            return
        
        if not bot_enabled():
            bot.send_message(chat_id, "<pre>🚫 البوت معطل</pre>")
            return
        
        if is_paid_mode() and not is_admin(user_id):
            bot.send_message(chat_id, f"<pre>💵 البوت في وضع مدفوع\nللاشتراك تواصل مع المطور\n@{developer}</pre>")
            return
        
        if not check_subscription(user_id):
            bot.send_message(chat_id, "<pre>📢 اشترك في القنوات أولاً</pre>")
            return
        
        document = message.document
        file_name = document.file_name
        
        allowed_types = (get_security_setting('allowed_file_types') or 'py,zip,txt,json').split(',')
        file_ext = file_name.split('.')[-1].lower()
        
        if file_ext not in allowed_types:
            bot.reply_to(message, f"<pre>❌ نوع الملف غير مسموح\nالأنواع المسموحة: {', '.join(allowed_types)}</pre>")
            return
        
        # التحقق من السعر إذا كان هناك سعر للرفع
        upload_price = get_price('upload_price')
        if upload_price > 0 and not is_admin(user_id) and not is_vip(user_id) and not is_pro(user_id):
            if not spend_points(user_id, upload_price):
                bot.reply_to(message, f"<pre>❌ تحتاج {upload_price} نقطة لرفع الملف\nرصيدك: {get_points(user_id)} نقطة</pre>")
                return
        
        progress_msg = bot.send_message(chat_id, f"<pre>📤 جار رفع الملف... {file_name}</pre>")
        
        file_info = bot.get_file(document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        
        file_path = os.path.join(UPLOAD_FOLDER, file_name)
        counter = 1
        original_name = file_name
        
        while os.path.exists(file_path):
            name, ext = os.path.splitext(original_name)
            file_name = f"{name}_{counter}{ext}"
            file_path = os.path.join(UPLOAD_FOLDER, file_name)
            counter += 1
        
        with open(file_path, "wb") as f:
            f.write(downloaded)
        
        # معالجة ملف ZIP
        extracted_files = []
        if file_ext == 'zip':
            success, extracted_files, extract_dir = extract_zip_file(file_path, user_id)
            if success and extracted_files:
                result_msg = f"<pre>✅ تم استخراج {len(extracted_files)} ملف من الأرشيف:\n\n"
                for i, py_file in enumerate(extracted_files, 1):
                    py_filename = os.path.basename(py_file)
                    analysis = analyze_file(py_file, py_filename, user_id)
                    
                    # التحقق من محاولات الاختراق
                    if analysis.get('requires_approval', False) and analysis.get('hack_analysis'):
                        hack_score = analysis['hack_analysis']['hack_score']
                        if hack_score >= get_hack_score_threshold():
                            # إشعار المطور
                            send_hack_notification_to_admin(user_id, py_filename, hack_score, 
                                                          analysis['hack_analysis']['detected_patterns'],
                                                          analysis['hack_analysis']['hack_details'])
                            
                            result_msg += f"{i}. {py_filename} - ⚠️ <b>يتطلب موافقة المطور</b> (درجة خطر: {hack_score})\n"
                        else:
                            result_msg += f"{i}. {py_filename} - ✅ تم الرفع\n"
                    else:
                        result_msg += f"{i}. {py_filename} - ✅ تم الرفع\n"
                    
                    libraries_str = ','.join(analysis['libraries'])
                    hack_score = analysis['hack_analysis']['hack_score'] if analysis.get('hack_analysis') else 0
                    requires_approval = 1 if analysis.get('requires_approval') else 0
                    
                    db_execute("INSERT INTO files (filename, user_id, upload_time, status, libraries, token, security_level, hack_score, requires_approval) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (py_filename, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
                              'pending' if analysis.get('requires_approval') else 'stopped', 
                              libraries_str, analysis['token'], analysis.get('security_level', 'آمن'),
                              hack_score, requires_approval))
                
                result_msg += f"\n𖤓 تم معالجة جميع الملفات!</pre>"
                bot.edit_message_text(result_msg, chat_id, progress_msg.message_id)
                return
            else:
                bot.edit_message_text("<pre>❌ فشل في استخراج الأرشيف أو لم يحتوي على ملفات PY</pre>", 
                                     chat_id, progress_msg.message_id)
                return
        
        # للملفات الأخرى
        analysis = analyze_file(file_path, file_name, user_id)
        
        # التحقق من محاولات الاختراق
        requires_approval = analysis.get('requires_approval', False)
        hack_analysis = analysis.get('hack_analysis')
        
        if requires_approval and hack_analysis:
            hack_score = hack_analysis['hack_score']
            
            if hack_score >= get_hack_score_threshold():
                # إرسال تقرير للمستخدم
                user_report = generate_hack_report(user_id, file_name, hack_analysis)
                bot.send_message(user_id, f"<pre>{user_report}</pre>")
                
                # إذا كان الخطر عالي جداً، رفض تلقائي
                if hack_score >= 25 and is_auto_block_enabled():
                    rejection_reason = "تم رفض الملف تلقائياً بسبب اكتشاف محاولة اختراق واضحة"
                    db_execute("UPDATE files SET status = 'rejected', rejection_reason = ? WHERE filename = ? AND user_id = ?",
                              (rejection_reason, file_name, user_id))
                    
                    bot.edit_message_text(f"<pre>🚫 تم رفض الملف تلقائياً\n\nالسبب: {rejection_reason}\n\nدرجة الخطر: {hack_score}</pre>",
                                         chat_id, progress_msg.message_id)
                    
                    # حظر المستخدم إذا كان الخطر عالي جداً
                    if hack_score >= 30:
                        ban_user(user_id, banned_by=DEVELOPER_ID, reason=f"محاولة اختراق - ملف: {file_name}")
                        bot.send_message(user_id, "<pre>⛔ تم حظرك من البوت بسبب محاولة اختراق</pre>")
                    
                    return
                
                # إشعار المطور للموافقة/الرفض
                send_hack_notification_to_admin(user_id, file_name, hack_score, 
                                              hack_analysis['detected_patterns'],
                                              hack_analysis['hack_details'])
                
                # حفظ الملف كمعلق
                libraries_str = ','.join(analysis['libraries'])
                db_execute("INSERT INTO files (filename, user_id, upload_time, status, libraries, token, security_level, hack_score, requires_approval) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                         (file_name, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'pending',
                          libraries_str, analysis['token'], analysis['security_level'], hack_score, 1))
                
                result_msg = f"""
<pre>⚠️ <b>الملف يحتاج مراجعة</b>

𖤓 الملف: {file_name}
𖤓 الحالة: ⏳ في انتظار موافقة المطور
𖤓 درجة الخطر: {hack_score}/100
𖤓 السبب: تم اكتشاف أنماط قد تشير إلى محاولة اختراق

📋 <b>سيتم إعلامك بقرار المطور قريباً</b></pre>
                """
                
                bot.edit_message_text(result_msg, chat_id, progress_msg.message_id)
                return
        
        # إذا كان الملف آمناً
        auto_install = get_security_setting('auto_install_libs') == 'true'
        if auto_install and analysis['libraries']:
            install_results = install_libraries(analysis['libraries'])
            install_summary = "\n".join(install_results)
        else:
            install_summary = "✅ لا توجد مكتبات تحتاج تثبيت"
        
        libraries_str = ','.join(analysis['libraries'])
        hack_score = analysis['hack_analysis']['hack_score'] if analysis.get('hack_analysis') else 0
        
        db_execute("INSERT INTO files (filename, user_id, upload_time, status, libraries, token, security_level, hack_score, requires_approval) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (file_name, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'stopped',
                  libraries_str, analysis['token'], analysis['security_level'], hack_score, 0))
        
        security_info = ""
        if hack_score > 0:
            security_info = f"𖤓 درجة الأمان: {hack_score}/100\n"
        
        result_msg = f"""
<pre>✅ <b>تم الرفع بنجاح!</b>

𖤓 الاسم: {file_name}
𖤓 النوع: {file_ext}
𖤓 الحجم: {analysis['file_size']} بايت
𖤓 الأسطر: {analysis['lines_of_code']}
{security_info}
𖤓 المكتبات: {len(analysis['libraries'])}
𖤓 التوكن: {'✅ موجود' if analysis['token_found'] else '❌ غير موجود'}

{install_summary}</pre>
        """
        
        bot.edit_message_text(result_msg, chat_id, progress_msg.message_id, 
                             reply_markup=file_control_panel(file_name, user_id))
        
        # إشعار المطور
        if user_id != DEVELOPER_ID:
            user_info = f"@{message.from_user.username}" if message.from_user.username else f"{message.from_user.first_name}"
            security_alert = ""
            if hack_score >= 10:
                security_alert = f"\n⚠️ درجة الخطر: {hack_score}"
            
            bot.send_message(
                DEVELOPER_ID,
                f"<pre>📤 ملف جديد\n\n• الملف: {file_name}\n• من: {user_info}\n• النوع: {file_ext}{security_alert}</pre>"
            )
                
    except Exception as e:
        logger.error(f"❌ خطأ في رفع الملف: {str(e)}")
        bot.reply_to(message, f"<pre>❌ حدث خطأ: {str(e)}</pre>")

# =============================
# دوال الخطوات الإضافية
# =============================
def process_broadcast_step(message):
    """معالجة خطوة البث"""
    broadcast_text = message.text
    
    # حساب عدد المستخدمين
    users = db_fetchall("SELECT user_id FROM known_users")
    total_users = len(users)
    
    # إرسال البث
    sent = 0
    failed = 0
    
    for user in users:
        try:
            bot.send_message(user[0], broadcast_text, parse_mode="HTML")
            sent += 1
        except:
            failed += 1
    
    # إرسال تقرير
    bot.send_message(message.chat.id, f"""
<pre>✅ <b>تم إرسال البث</b>

𖤓 إجمالي المستخدمين: {total_users}
𖤓 تم الإرسال بنجاح: {sent}
𖤓 فشل الإرسال: {failed}
𖤓 نسبة النجاح: {round((sent/total_users)*100 if total_users > 0 else 0, 2)}%</pre>
    """, reply_markup=admin_panel())

def create_gift_step(message):
    """معالجة خطوة إنشاء كود هدية"""
    try:
        parts = message.text.split(":")
        if len(parts) != 3:
            bot.send_message(message.chat.id, "<pre>❌ صيغة غير صحيحة\nاستخدم: نقاط:عدد_الاستخدامات:عدد_الأيام</pre>", reply_markup=admin_panel())
            return
        
        points = int(parts[0])
        max_uses = int(parts[1])
        days = int(parts[2])
        
        result = create_gift_code_admin(message.from_user.id, points, max_uses, days)
        bot.send_message(message.chat.id, f"<pre>{result}</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ قيم غير صحيحة\nتأكد من إدخال أرقام صحيحة</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def add_vip_step(message):
    """إضافة مستخدم VIP"""
    try:
        target_id = int(message.text)
        
        # التحقق من وجود المستخدم
        existing = db_fetchone("SELECT user_id FROM known_users WHERE user_id = ?", (target_id,))
        if not existing:
            bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_id} غير موجود</pre>", reply_markup=admin_panel())
            return
        
        # التحقق إذا كان VIP بالفعل
        existing_vip = db_fetchone("SELECT user_id FROM vip_users WHERE user_id = ?", (target_id,))
        if existing_vip:
            bot.send_message(message.chat.id, f"<pre>⚠️ المستخدم {target_id} عضو VIP بالفعل</pre>", reply_markup=admin_panel())
            return
        
        # إضافة VIP
        db_execute("INSERT INTO vip_users (user_id, activated_by, activation_time, expiry_date, status) VALUES (?, ?, ?, ?, ?)",
                  (target_id, message.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"), 'active'))
        
        # إعلام المستخدم
        try:
            bot.send_message(target_id, f"<pre>🎉 تمت ترقيتك إلى VIP!\n\nمميزات VIP:\n• إصلاح تلقائي للملفات\n• أولوية في الدعم\n• ميزات إضافية</pre>")
        except:
            pass
        
        bot.send_message(message.chat.id, f"<pre>✅ تمت ترقية المستخدم {target_id} إلى VIP</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def add_pro_step(message):
    """إضافة مستخدم PRO"""
    try:
        target_id = int(message.text)
        
        # التحقق من وجود المستخدم
        existing = db_fetchone("SELECT user_id FROM known_users WHERE user_id = ?", (target_id,))
        if not existing:
            bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_id} غير موجود</pre>", reply_markup=admin_panel())
            return
        
        # التحقق إذا كان PRO بالفعل
        existing_pro = db_fetchone("SELECT user_id FROM pro_users WHERE user_id = ?", (target_id,))
        if existing_pro:
            bot.send_message(message.chat.id, f"<pre>⚠️ المستخدم {target_id} عضو PRO بالفعل</pre>", reply_markup=admin_panel())
            return
        
        # إضافة PRO
        db_execute("INSERT INTO pro_users (user_id, activated_by, activation_time, expiry_date, status) VALUES (?, ?, ?, ?, ?)",
                  (target_id, message.from_user.id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                   (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"), 'active'))
        
        # إعلام المستخدم
        try:
            bot.send_message(target_id, f"<pre>🚀 تمت ترقيتك إلى PRO!\n\nمميزات PRO:\n• جميع مميزات VIP\n• ميزات حصرية إضافية\n• دعم فوري</pre>")
        except:
            pass
        
        bot.send_message(message.chat.id, f"<pre>✅ تمت ترقية المستخدم {target_id} إلى PRO</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def send_rejection_reason(message, filename, target_user_id, admin_id):
    """إرسال سبب الرفض للمستخدم وتحديث حالة الملف"""
    reason = message.text
    
    # تحديث حالة الملف
    db_execute("UPDATE files SET status = 'rejected', rejection_reason = ?, requires_approval = 0 WHERE filename = ? AND user_id = ?",
              (reason, filename, target_user_id))
    
    # تحديث الإشعار
    db_execute("UPDATE admin_notifications SET status = 'resolved', admin_action = 'rejected', action_time = ? WHERE filename = ? AND user_id = ?",
              (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filename, target_user_id))
    
    # إرسال السبب للمستخدم
    try:
        bot.send_message(target_user_id, f"""
<pre>❌ <b>تم رفض ملفك</b>

𖤓 اسم الملف: {filename}
𖤓 سبب الرفض: {reason}

📨 يمكنك استئناف القرار من خلال قائمة ملفاتك.</pre>
        """)
    except:
        pass
    
    bot.send_message(message.chat.id, f"<pre>✅ تم إرسال سبب الرفض للمستخدم\nالملف: {filename}</pre>", reply_markup=admin_panel())

def set_upload_price_step(message):
    try:
        price = int(message.text)
        success, msg = set_price('upload_price', price)
        bot.send_message(message.chat.id, f"<pre>{msg}</pre>", reply_markup=admin_panel())
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ الرجاء إدخال رقم صحيح</pre>", reply_markup=admin_panel())

def set_ref_price_step(message):
    try:
        price = int(message.text)
        success, msg = set_price('referral_price', price)
        bot.send_message(message.chat.id, f"<pre>{msg}</pre>", reply_markup=admin_panel())
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ الرجاء إدخال رقم صحيح</pre>", reply_markup=admin_panel())

def set_hack_threshold_step(message):
    try:
        threshold = int(message.text)
        if threshold < 5 or threshold > 50:
            bot.send_message(message.chat.id, "<pre>❌ القيمة يجب أن تكون بين 5 و 50</pre>", reply_markup=admin_panel())
            return
        
        db_execute("UPDATE bot_settings SET setting_value = ? WHERE setting_key = 'hack_score_threshold'", (str(threshold),))
        bot.send_message(message.chat.id, f"<pre>✅ تم تحديث عتبة درجة الخطر إلى {threshold}</pre>", reply_markup=admin_panel())
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ الرجاء إدخال رقم صحيح</pre>", reply_markup=admin_panel())

def change_token_step(message, filename):
    new_token = message.text.strip()
    
    if not validate_token(new_token):
        bot.send_message(message.chat.id, "<pre>❌ التوكن غير صالح</pre>")
        return
    
    db_execute("UPDATE files SET token = ? WHERE filename = ? AND user_id = ?", 
              (new_token, filename, message.from_user.id))
    
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        old_token = db_fetchone("SELECT token FROM files WHERE filename = ?", (filename,))
        if old_token and old_token[0]:
            content = content.replace(old_token[0], new_token)
        else:
            patterns = [
                r'bot\.TeleBot\(["\']([^"\']+)["\']\)',
                r'telebot\.TeleBot\(["\']([^"\']+)["\']\)',
                r'TOKEN\s*=\s*["\']([^"\']+)["\']',
                r'token\s*=\s*["\']([^"\']+)["\']'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    content = content.replace(match.group(1), new_token)
                    break
            else:
                content = f"TOKEN = '{new_token}'\n{content}"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    bot.send_message(message.chat.id, f"<pre>✅ تم تحديث التوكن</pre>")

def redeem_gift_step(message):
    code = message.text.strip()
    user_id = message.from_user.id
    ok, msg = redeem_gift_code(code, user_id)
    bot.send_message(message.chat.id, f"<pre>{msg}</pre>", reply_markup=main_dark_panel(user_id))

# =============================
# دوال الميزات الجديدة - معالجة الخطوات
# =============================
def add_points_step(message, target_user_id=None):
    """معالجة إضافة نقاط"""
    try:
        if target_user_id is None:
            # إذا لم يتم تحديد المستهدف، طلب الآيدي أولاً
            if message.text.isdigit():
                target_user_id = int(message.text)
                msg = bot.send_message(message.chat.id, "<pre>💰 <b>إضافة نقاط</b>\n\nأرسل عدد النقاط:</pre>")
                bot.register_next_step_handler(msg, add_points_step, target_user_id)
            else:
                bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
            return
        
        # هنا target_user_id محدد ونطلب عدد النقاط
        points = int(message.text)
        if points <= 0:
            bot.send_message(message.chat.id, "<pre>❌ عدد النقاط يجب أن يكون أكبر من صفر</pre>", reply_markup=admin_panel())
            return
        
        # التحقق من وجود المستخدم
        user_info = get_user_info(target_user_id)
        if not user_info['exists']:
            bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
            return
        
        # إضافة النقاط
        new_points = add_points(target_user_id, points, message.from_user.id, "إضافة من الأدمن")
        
        # إرسال إشعار للمستخدم
        try:
            bot.send_message(target_user_id, f"<pre>💰 <b>تمت إضافة نقاط لحسابك</b>\n\n𖤓 النقاط المضافة: {points}\n𖤓 رصيدك الجديد: {new_points}\n𖤓 من قبل: الأدمن</pre>")
        except:
            pass
        
        bot.send_message(message.chat.id, f"<pre>✅ تم إضافة {points} نقطة للمستخدم {target_user_id}\nرصيده الجديد: {new_points}</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ الرجاء إدخال رقم صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def deduct_points_step(message, target_user_id=None):
    """معالجة خصم نقاط"""
    try:
        if target_user_id is None:
            # إذا لم يتم تحديد المستهدف، طلب الآيدي أولاً
            if message.text.isdigit():
                target_user_id = int(message.text)
                msg = bot.send_message(message.chat.id, "<pre>💰 <b>خصم نقاط</b>\n\nأرسل عدد النقاط:</pre>")
                bot.register_next_step_handler(msg, deduct_points_step, target_user_id)
            else:
                bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
            return
        
        # هنا target_user_id محدد ونطلب عدد النقاط
        points = int(message.text)
        if points <= 0:
            bot.send_message(message.chat.id, "<pre>❌ عدد النقاط يجب أن يكون أكبر من صفر</pre>", reply_markup=admin_panel())
            return
        
        # التحقق من وجود المستخدم
        user_info = get_user_info(target_user_id)
        if not user_info['exists']:
            bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
            return
        
        # التحقق من رصيد المستخدم
        current_points = user_info['points']
        if current_points < points:
            bot.send_message(message.chat.id, f"<pre>❌ رصيد المستخدم غير كافي\nرصيده الحالي: {current_points}\nالمطلوب خصمه: {points}</pre>", reply_markup=admin_panel())
            return
        
        # خصم النقاط
        success, msg = deduct_points(target_user_id, points, message.from_user.id, "خصم من الأدمن")
        
        if success:
            # إرسال إشعار للمستخدم
            try:
                new_points = get_points(target_user_id)
                bot.send_message(target_user_id, f"<pre>⚠️ <b>تم خصم نقاط من حسابك</b>\n\n𖤓 النقاط المخصومة: {points}\n𖤓 رصيدك الجديد: {new_points}\n𖤓 من قبل: الأدمن</pre>")
            except:
                pass
            
            bot.send_message(message.chat.id, f"<pre>✅ تم خصم {points} نقطة من المستخدم {target_user_id}\nرصيده الجديد: {get_points(target_user_id)}</pre>", reply_markup=admin_panel())
        else:
            bot.send_message(message.chat.id, f"<pre>❌ {msg}</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ الرجاء إدخال رقم صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def ban_user_step(message, target_user_id=None, reason=None):
    """معالجة حظر مستخدم"""
    try:
        if target_user_id is None:
            # إذا لم يتم تحديد المستهدف، طلب الآيدي أولاً
            if message.text.isdigit():
                target_user_id = int(message.text)
                msg = bot.send_message(message.chat.id, "<pre>⛔ <b>حظر مستخدم</b>\n\nأرسل سبب الحظر (اختياري):</pre>")
                bot.register_next_step_handler(msg, ban_user_step, target_user_id)
            else:
                bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
            return
        
        # هنا target_user_id محدد
        if reason is None:
            # طلب السبب إذا لم يكن موجوداً
            reason = message.text or "بدون سبب"
            
            # التحقق من وجود المستخدم
            user_info = get_user_info(target_user_id)
            if not user_info['exists']:
                bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
                return
            
            # حظر المستخدم
            ban_user(target_user_id, message.from_user.id, reason)
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(target_user_id, f"<pre>⛔ <b>تم حظرك من البوت</b>\n\n𖤓 السبب: {reason}\n𖤓 من قبل: الأدمن\n𖤓 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</pre>")
            except:
                pass
            
            bot.send_message(message.chat.id, f"<pre>✅ تم حظر المستخدم {target_user_id}\nالسبب: {reason}</pre>", reply_markup=admin_panel())
    
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def unban_user_step(message):
    """معالجة فك حظر مستخدم"""
    try:
        if message.text.isdigit():
            target_user_id = int(message.text)
            
            # التحقق من وجود المستخدم
            user_info = get_user_info(target_user_id)
            if not user_info['exists']:
                bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
                return
            
            # التحقق إذا كان محظوراً أصلاً
            if not is_banned(target_user_id):
                bot.send_message(message.chat.id, f"<pre>⚠️ المستخدم {target_user_id} ليس محظوراً</pre>", reply_markup=admin_panel())
                return
            
            # فك الحظر
            unban_user(target_user_id)
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(target_user_id, f"<pre>✅ <b>تم فك الحظر عنك</b>\n\nيمكنك الآن استخدام البوت بشكل طبيعي.</pre>")
            except:
                pass
            
            bot.send_message(message.chat.id, f"<pre>✅ تم فك حظر المستخدم {target_user_id}</pre>", reply_markup=admin_panel())
        else:
            bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def block_uploads_step(message, target_user_id=None, reason=None):
    """معالجة منع مستخدم من رفع ملفات"""
    try:
        if target_user_id is None:
            # إذا لم يتم تحديد المستهدف، طلب الآيدي أولاً
            if message.text.isdigit():
                target_user_id = int(message.text)
                msg = bot.send_message(message.chat.id, "<pre>🚫 <b>منع مستخدم من رفع ملفات</b>\n\nأرسل السبب (اختياري):</pre>")
                bot.register_next_step_handler(msg, block_uploads_step, target_user_id)
            else:
                bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
            return
        
        # هنا target_user_id محدد
        if reason is None:
            # طلب السبب إذا لم يكن موجوداً
            reason = message.text or "بدون سبب"
            
            # التحقق من وجود المستخدم
            user_info = get_user_info(target_user_id)
            if not user_info['exists']:
                bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
                return
            
            # التحقق إذا كان محظوراً من الرفع أصلاً
            if is_upload_blocked(target_user_id):
                bot.send_message(message.chat.id, f"<pre>⚠️ المستخدم {target_user_id} محظور من رفع الملفات بالفعل</pre>", reply_markup=admin_panel())
                return
            
            # حظره من رفع الملفات
            block_user_uploads(target_user_id, message.from_user.id, reason)
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(target_user_id, f"<pre>🚫 <b>تم منعك من رفع الملفات</b>\n\n𖤓 السبب: {reason}\n𖤓 من قبل: الأدمن\n𖤓 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</pre>")
            except:
                pass
            
            bot.send_message(message.chat.id, f"<pre>✅ تم منع المستخدم {target_user_id} من رفع الملفات\nالسبب: {reason}</pre>", reply_markup=admin_panel())
    
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

def unblock_uploads_step(message):
    """معالجة فك منع مستخدم من رفع ملفات"""
    try:
        if message.text.isdigit():
            target_user_id = int(message.text)
            
            # التحقق من وجود المستخدم
            user_info = get_user_info(target_user_id)
            if not user_info['exists']:
                bot.send_message(message.chat.id, f"<pre>❌ المستخدم {target_user_id} غير موجود</pre>", reply_markup=admin_panel())
                return
            
            # التحقق إذا كان محظوراً من الرفع أصلاً
            if not is_upload_blocked(target_user_id):
                bot.send_message(message.chat.id, f"<pre>⚠️ المستخدم {target_user_id} ليس محظوراً من رفع الملفات</pre>", reply_markup=admin_panel())
                return
            
            # فك الحظر
            unblock_user_uploads(target_user_id)
            
            # إرسال إشعار للمستخدم
            try:
                bot.send_message(target_user_id, f"<pre>✅ <b>تم فك المنع عنك من رفع الملفات</b>\n\nيمكنك الآن رفع الملفات بشكل طبيعي.</pre>")
            except:
                pass
            
            bot.send_message(message.chat.id, f"<pre>✅ تم فك منع المستخدم {target_user_id} من رفع الملفات</pre>", reply_markup=admin_panel())
        else:
            bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
        
    except ValueError:
        bot.send_message(message.chat.id, "<pre>❌ آيدي المستخدم غير صحيح</pre>", reply_markup=admin_panel())
    except Exception as e:
        bot.send_message(message.chat.id, f"<pre>❌ خطأ: {str(e)}</pre>", reply_markup=admin_panel())

# =============================
# معالجات الكال باك - كاملة مع جميع المعالجات الجديدة
# =============================
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    data = call.data
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id
    
    try:
        # ===== معالجة الميزات الجديدة =====
        
        # إضافة نقاط
        if data == "admin_add_points":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>💰 <b>إضافة نقاط لمستخدم</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, add_points_step)
            bot.answer_callback_query(call.id, "💰 إضافة نقاط")
            return
        
        # خصم نقاط
        elif data == "admin_deduct_points":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>💰 <b>خصم نقاط من مستخدم</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, deduct_points_step)
            bot.answer_callback_query(call.id, "💰 خصم نقاط")
            return
        
        # حظر عضو
        elif data == "admin_ban_user_menu":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>⛔ <b>حظر مستخدم</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, ban_user_step)
            bot.answer_callback_query(call.id, "⛔ حظر عضو")
            return
        
        # فك حظر عضو
        elif data == "admin_unban_user_menu":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>✅ <b>فك حظر مستخدم</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, unban_user_step)
            bot.answer_callback_query(call.id, "✅ فك حظر")
            return
        
        # منع رفع ملفات
        elif data == "admin_block_uploads_menu":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>🚫 <b>منع مستخدم من رفع ملفات</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, block_uploads_step)
            bot.answer_callback_query(call.id, "🚫 منع رفع")
            return
        
        # فك منع رفع ملفات
        elif data == "admin_unblock_uploads_menu":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>📤 <b>فك منع مستخدم من رفع ملفات</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, unblock_uploads_step)
            bot.answer_callback_query(call.id, "📤 فك المنع")
            return
        
        # ===== بقية المعالجات الحالية =====
        
        # معالجة قبول/رفض الملفات من قبل المطور
        if data.startswith("admin_accept_file:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            parts = data.split(":")
            filename = parts[1]
            target_user_id = int(parts[2])
            
            # تحديث حالة الملف
            db_execute("UPDATE files SET status = 'stopped', requires_approval = 0, approved_by = ?, approval_time = ? WHERE filename = ? AND user_id = ?",
                      (user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filename, target_user_id))
            
            # تحديث الإشعار
            db_execute("UPDATE admin_notifications SET status = 'resolved', admin_action = 'accepted', action_time = ? WHERE filename = ? AND user_id = ?",
                      (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), filename, target_user_id))
            
            # إعلام المستخدم
            try:
                bot.send_message(target_user_id, f"<pre>✅ تمت الموافقة على ملفك: {filename}\n\nيمكنك الآن استخدام الملف من قائمة ملفاتك.</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ تم قبول الملف")
            safe_edit_message_text(f"<pre>✅ تمت الموافقة على الملف: {filename}</pre>", chat_id, message_id)
            return
        
        elif data.startswith("admin_reject_file:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            parts = data.split(":")
            filename = parts[1]
            target_user_id = int(parts[2])
            
            # طلب سبب الرفض
            msg = bot.send_message(chat_id, f"<pre>❌ رفض الملف: {filename}\n\nأرسل سبب الرفض للمستخدم:</pre>")
            bot.register_next_step_handler(msg, send_rejection_reason, filename, target_user_id, user_id)
            
            bot.answer_callback_query(call.id, "❌ رفض الملف")
            return
        
        elif data.startswith("admin_ban_user:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            parts = data.split(":")
            target_user_id = int(parts[1])
            reason = parts[2] if len(parts) > 2 else "محاولة اختراق"
            
            ban_user(target_user_id, banned_by=user_id, reason=reason)
            
            try:
                bot.send_message(target_user_id, f"<pre>⛔ تم حظرك من البوت\nالسبب: {reason}</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, f"⛔ تم حظر المستخدم {target_user_id}")
            safe_edit_message_text(f"<pre>⛔ تم حظر المستخدم {target_user_id}</pre>", chat_id, message_id)
            return
        
        elif data.startswith("admin_view_file:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            filename = data.split(":")[1]
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if os.path.exists(file_path):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # إرسال أول 1000 حرف
                    preview = content[:1000]
                    if len(content) > 1000:
                        preview += f"\n\n... وأكثر ({len(content)} حرف)"
                    
                    bot.send_message(chat_id, f"<pre>📄 محتوى الملف: {filename}\n\n{preview}</pre>")
                except Exception as e:
                    bot.send_message(chat_id, f"<pre>❌ خطأ في قراءة الملف: {str(e)}</pre>")
            else:
                bot.send_message(chat_id, "<pre>❌ الملف غير موجود</pre>")
            
            bot.answer_callback_query(call.id, "📄 عرض الملف")
            return
        
        elif data == "view_hack_logs":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            logs = db_fetchall("SELECT user_id, filename, hack_score, detection_time, patterns_found FROM hack_attempts ORDER BY detection_time DESC LIMIT 20")
            
            if not logs:
                bot.send_message(chat_id, "<pre>📊 لا توجد سجلات اختراق</pre>")
                return
            
            log_text = "<pre>🚨 <b>آخر 20 محاولة اختراق</b>\n\n</pre>"
            for i, log in enumerate(logs, 1):
                user_id_log, filename, score, time_log, patterns = log
                patterns_short = patterns[:50] + "..." if len(patterns) > 50 else patterns
                log_text += f"<pre>{i}. {filename} - درجة: {score}\n   👤 {user_id_log} - ⏰ {time_log}\n   📝 {patterns_short}\n\n</pre>"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑️ مسح السجلات", callback_data="clear_hack_logs"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            bot.send_message(chat_id, log_text, reply_markup=markup)
            bot.answer_callback_query(call.id, "🚨 سجلات الاختراق")
            return
        
        elif data == "hack_logs":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            # نفس وظيفة view_hack_logs
            logs = db_fetchall("SELECT user_id, filename, hack_score, detection_time, patterns_found FROM hack_attempts ORDER BY detection_time DESC LIMIT 20")
            
            if not logs:
                safe_edit_message_text("<pre>📊 لا توجد سجلات اختراق</pre>", chat_id, message_id)
                return
            
            log_text = "<pre>🚨 <b>آخر 20 محاولة اختراق</b>\n\n</pre>"
            for i, log in enumerate(logs, 1):
                user_id_log, filename, score, time_log, patterns = log
                patterns_short = patterns[:50] + "..." if len(patterns) > 50 else patterns
                log_text += f"<pre>{i}. {filename} - درجة: {score}\n   👤 {user_id_log} - ⏰ {time_log}\n   📝 {patterns_short}\n\n</pre>"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🗑️ مسح السجلات", callback_data="clear_hack_logs"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            safe_edit_message_text(log_text, chat_id, message_id)
            # إضافة الـ markup بشكل منفصل
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
            except:
                pass
            
            bot.answer_callback_query(call.id, "🚨 سجلات الاختراق")
            return
        
        elif data == "clear_hack_logs":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            db_execute("DELETE FROM hack_attempts")
            bot.answer_callback_query(call.id, "🗑️ تم مسح السجلات")
            safe_edit_message_text("<pre>🗑️ تم مسح جميع سجلات الاختراق</pre>", chat_id, message_id)
            return
        
        elif data.startswith("admin_ignore_alert:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            filename = data.split(":")[1]
            bot.answer_callback_query(call.id, "🔕 تم تجاهل التنبيه")
            safe_edit_message_text(f"<pre>🔕 تم تجاهل تنبيه الملف: {filename}</pre>", chat_id, message_id)
            return
        
        elif data == "security_settings":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            markup = types.InlineKeyboardMarkup(row_width=2)
            
            # الحصول على الإعدادات الحالية
            ai_security = "🟢 مفعل" if is_ai_security_enabled() else "🔴 معطل"
            auto_block = "🟢 مفعل" if is_auto_block_enabled() else "🔴 معطل"
            notifications = "🟢 مفعل" if is_notify_on_hack_enabled() else "🔴 معطل"
            threshold = get_hack_score_threshold()
            
            markup.add(types.InlineKeyboardButton(f"{ai_security} AI الحماية", callback_data="toggle_ai_security"))
            markup.add(types.InlineKeyboardButton(f"{auto_block} الحظر التلقائي", callback_data="toggle_auto_block"))
            markup.add(types.InlineKeyboardButton(f"{notifications} الإشعارات", callback_data="toggle_hack_notifications"))
            markup.add(types.InlineKeyboardButton(f"📊 عتبة الخطر: {threshold}", callback_data="set_hack_threshold"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            settings_text = f"""
<pre>🛡️ <b>إعدادات نظام الأمان</b>

𖤓 حماية الذكاء الاصطناعي: {ai_security}
𖤓 الحظر التلقائي: {auto_block}
𖤓 إشعارات الاختراق: {notifications}
𖤓 عتبة درجة الخطر: {threshold}

اختر الإعداد لتعديله:</pre>
            """
            
            if safe_edit_message_text(settings_text, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            bot.answer_callback_query(call.id, "🛡️ إعدادات الأمان")
            return
        
        elif data == "toggle_ai_security":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current = is_ai_security_enabled()
            new_value = "disabled" if current else "enabled"
            db_execute("UPDATE bot_settings SET setting_value = ? WHERE setting_key = 'ai_security'", (new_value,))
            
            bot.answer_callback_query(call.id, f"✅ AI الحماية {'مفعل' if not current else 'معطل'}")
            callback_query(call)  # تحديث القائمة
            return
        
        elif data == "toggle_auto_block":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current = is_auto_block_enabled()
            new_value = "disabled" if current else "enabled"
            db_execute("UPDATE bot_settings SET setting_value = ? WHERE setting_key = 'auto_block_hackers'", (new_value,))
            
            bot.answer_callback_query(call.id, f"✅ الحظر التلقائي {'مفعل' if not current else 'معطل'}")
            callback_query(call)  # تحديث القائمة
            return
        
        elif data == "toggle_hack_notifications":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current = is_notify_on_hack_enabled()
            new_value = "disabled" if current else "enabled"
            db_execute("UPDATE bot_settings SET setting_value = ? WHERE setting_key = 'notify_on_hack_attempt'", (new_value,))
            
            bot.answer_callback_query(call.id, f"✅ إشعارات الاختراق {'مفعل' if not current else 'معطل'}")
            callback_query(call)  # تحديث القائمة
            return
        
        elif data == "set_hack_threshold":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current = get_hack_score_threshold()
            msg = bot.send_message(chat_id, f"<pre>📊 عتبة درجة الخطر الحالية: {current}\n\nأرسل القيمة الجديدة (5-50):</pre>")
            bot.register_next_step_handler(msg, set_hack_threshold_step)
            bot.answer_callback_query(call.id, "📊 تعديل عتبة الخطر")
            return
        
        # ===== معالجة طلب فك الحظر =====
        if data.startswith("request_unban:"):
            try:
                target = int(data.split(":",1)[1])
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ قبول", callback_data=f"approve_unban_{target}"))
                markup.add(types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_unban_{target}"))
                
                user_info = call.from_user.username or call.from_user.first_name
                bot.send_message(DEVELOPER_ID,
                               f"<pre>📨 طلب فك حظر\n• من: {user_info}\n• الآيدي: {target}</pre>",
                               reply_markup=markup)
                bot.answer_callback_query(call.id, "📨 تم إرسال الطلب")
            except:
                bot.answer_callback_query(call.id, "❌ خطأ")
            return
        
        # معالجة الموافقة على فك الحظر
        if data.startswith("approve_unban_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            target = int(data.replace("approve_unban_", ""))
            unban_user(target)
            
            try:
                bot.send_message(target, "<pre>✅ تم فك الحظر عنك</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ تم فك الحظر")
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            except:
                pass
            return
        
        # معالجة رفض فك الحظر
        if data.startswith("reject_unban_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            target = int(data.replace("reject_unban_", ""))
            bot.answer_callback_query(call.id, "❌ تم رفض الطلب")
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            except:
                pass
            return
        
        # التحقق من الاشتراك
        if data == "check_subscription":
            if check_subscription(user_id):
                bot.answer_callback_query(call.id, "✅ أنت مشترك")
                send_or_edit_message(user_id, chat_id, 'main_menu', WELCOME_MESSAGE, reply_markup=main_dark_panel(user_id))
            else:
                bot.answer_callback_query(call.id, "❌ لم تشترك بعد")
            return
        
        # العودة للقائمة الرئيسية
        if data == "back_main":
            send_or_edit_message(user_id, chat_id, 'main_menu', WELCOME_MESSAGE, reply_markup=main_dark_panel(user_id))
            return
        
        # تحميل الملفات
        if data == "upload":
            bot.answer_callback_query(call.id, "📤 أرسل الملف الآن")
            bot.send_message(chat_id, "<pre>📤 أرسل ملفك (PY أو ZIP):</pre>")
            return
        
        # لوحة التحكم
        if data == "admin_panel":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            admin_msg = "<pre>🛠️ لوحة تحكم الأدمن</pre>"
            send_or_edit_message(user_id, chat_id, 'admin_panel', admin_msg, reply_markup=admin_panel())
            return
        
        # تغيير سعر رفع الملفات
        if data == "set_upload_price":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current_price = get_price('upload_price')
            msg = bot.send_message(chat_id, f"<pre>💰 السعر الحالي لرفع الملفات: {current_price} نقطة\n\nأرسل السعر الجديد (رقم صحيح):</pre>")
            bot.register_next_step_handler(msg, set_upload_price_step)
            bot.answer_callback_query(call.id, "💰 تعديل سعر الرفع")
            return
        
        # تغيير سعر رابط الدعوة
        if data == "set_ref_price":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            current_price = get_price('referral_price')
            msg = bot.send_message(chat_id, f"<pre>💰 السعر الحالي لنقاط الدعوة: {current_price} نقطة\n\nأرسل السعر الجديد (رقم صحيح):</pre>")
            bot.register_next_step_handler(msg, set_ref_price_step)
            bot.answer_callback_query(call.id, "💰 تعديل سعر الدعوة")
            return
        
        # عرض نقاطي
        if data == "points":
            points = get_points(user_id)
            upload_price = get_price('upload_price')
            ref_price = get_price('referral_price')
            
            msg = f"""
<pre>💎 <b>رصيد النقاط</b>

𖤓 نقاطك الحالية: {points} نقطة
𖤓 سعر رفع ملف: {upload_price} نقطة
𖤓 سعر دعوة صديق: {ref_price} نقطة

• كل تشغيل ملف يكلف 4 نقاط
• أول تشغيل مجاني لكل مستخدم
• اربح نقاط بدعوة الأصدقاء</pre>
            """
            
            # استخدام safe_edit_message_text لتعديل الرسالة الحالية
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=main_dark_panel(user_id))
                except:
                    pass
            
            bot.answer_callback_query(call.id, "💎 نقاطك")
            return
        
        # عرض رابط الدعوة
        if data == "referral":
            code_row = db_fetchone("SELECT code FROM referral_links WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,))
            if not code_row:
                code = generate_referral_code(user_id)
            else:
                code = code_row[0]
            
            bot_username = bot.get_me().username
            if bot_username:
                link = f"https://t.me/{bot_username}?start=ref_{code}"
            else:
                link = f"اضغط /start ثم أرسل: ref_{code}"
            
            ref_price = get_price('referral_price')
            msg = f"""
<pre>🔗 <b>رابط الدعوة الخاص بك</b>

𖤓 الرابط: {link}
𖤓 الكود: {code}
𖤓 المكافأة: {ref_price} نقطة لكل صديق

• شارك الرابط مع أصدقائك
• احصل على {ref_price} نقطة لكل صديق يسجل
• يمكن للصديق استخدام الرابط مباشرة</pre>
            """
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔗 مشاركة الرابط", url=f"https://t.me/share/url?url={link}&text=انضم%20للبوت%20الرائع%20للحصول%20على%20خدمات%20استضافة%20ملفات%20Python%20مجاناً!"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "🔗 رابط الدعوة")
            return
        
        # عرض ملفاتي
        if data == "list_files":
            user_files = db_fetchall("SELECT filename, status, security_level, requires_approval FROM files WHERE user_id = ? ORDER BY upload_time DESC", (user_id,))
            if not user_files:
                bot.answer_callback_query(call.id, "📂 لا توجد ملفات")
                bot.send_message(chat_id, "<pre>📂 لا توجد ملفات مرفوعة بعد</pre>", reply_markup=main_dark_panel(user_id))
                return
            
            markup = types.InlineKeyboardMarkup(row_width=1)
            for file in user_files:
                filename, status, security_level, requires_approval = file
                
                if status == 'pending':
                    status_icon = "⏳"
                    status_text = "بانتظار المطور"
                elif status == 'rejected':
                    status_icon = "❌"
                    status_text = "مرفوض"
                elif status == 'active':
                    status_icon = "▶️"
                    status_text = "نشط"
                else:
                    status_icon = "⏸️"
                    status_text = "متوقف"
                
                # إضافة رمز الأمان
                if security_level and "خطر" in security_level:
                    security_icon = "⚠️"
                elif security_level and "آمن" in security_level:
                    security_icon = "✅"
                else:
                    security_icon = ""
                
                btn_text = f"{status_icon} {filename} {security_icon}"
                if requires_approval and status == 'pending':
                    btn_text = f"⏳ {filename} ⚠️"
                
                btn = types.InlineKeyboardButton(btn_text, callback_data=f"file_{filename}")
                markup.add(btn)
            
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
            
            if safe_edit_message_text(f"<pre>📂 <b>ملفاتك ({len(user_files)})</b></pre>", chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "📂 ملفاتك")
            return
        
        # عرض ملف معين
        if data.startswith("file_"):
            filename = data.replace("file_", "")
            file_info = db_fetchone("SELECT status, upload_time, security_level, hack_score, rejection_reason FROM files WHERE filename = ? AND user_id = ?", (filename, user_id))
            
            if not file_info:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
                return
            
            status, upload_time, security_level, hack_score, rejection_reason = file_info
            
            if status == 'rejected' and rejection_reason:
                status_text = f"مرفوض - السبب: {rejection_reason}"
            elif status == 'pending':
                status_text = "بانتظار موافقة المطور ⏳"
            elif status == 'active':
                status_text = "نشط"
            else:
                status_text = "متوقف"
            
            msg = f"""
<pre>📄 <b>تفاصيل الملف</b>

𖤓 الاسم: {filename}
𖤓 الحالة: {status_text}
𖤓 وقت الرفع: {upload_time}
𖤓 مستوى الأمان: {security_level or 'غير محدد'}
𖤓 درجة الخطر: {hack_score or 0}/100
𖤓 التشغيل: {'✅ يعمل' if filename in running_processes else '❌ متوقف'}</pre>
            """
            
            # إذا كان الملف مرفوضاً، إضافة زر للاستئناف
            if status == 'rejected':
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("📨 استئناف القرار", callback_data=f"appeal_rejection:{filename}"))
                markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="list_files"))
                
                if safe_edit_message_text(msg, chat_id, message_id):
                    try:
                        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                    except:
                        pass
            else:
                if safe_edit_message_text(msg, chat_id, message_id):
                    try:
                        bot.edit_message_reply_markup(chat_id, message_id, reply_markup=file_control_panel(filename, user_id))
                    except:
                        pass
            
            bot.answer_callback_query(call.id, f"📄 {filename}")
            return
        
        # استئناف قرار الرفض
        if data.startswith("appeal_rejection:"):
            filename = data.replace("appeal_rejection:", "")
            
            # إرسال طلب استئناف للمطور
            user_info = f"@{call.from_user.username}" if call.from_user.username else f"{call.from_user.first_name}"
            file_info = db_fetchone("SELECT rejection_reason FROM files WHERE filename = ? AND user_id = ?", (filename, user_id))
            rejection_reason = file_info[0] if file_info else "غير محدد"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ قبول الاستئناف", callback_data=f"accept_appeal:{filename}:{user_id}"))
            markup.add(types.InlineKeyboardButton("❌ رفض الاستئناف", callback_data=f"reject_appeal:{filename}:{user_id}"))
            
            appeal_msg = f"""
<pre>📨 طلب استئناف قرار رفض ملف

𖤓 الملف: {filename}
𖤓 المستخدم: {user_info} ({user_id})
𖤓 سبب الرفض الأصلي: {rejection_reason}
𖤓 وقت الطلب: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</pre>
            """
            
            bot.send_message(DEVELOPER_ID, appeal_msg, reply_markup=markup)
            bot.answer_callback_query(call.id, "📨 تم إرسال طلب الاستئناف")
            bot.send_message(chat_id, "<pre>📨 تم إرسال طلب استئناف للمطور</pre>")
            return
        
        # قبول الاستئناف
        if data.startswith("accept_appeal:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            parts = data.split(":")
            filename = parts[1]
            target_user_id = int(parts[2])
            
            # تغيير حالة الملف إلى متوقف
            db_execute("UPDATE files SET status = 'stopped', requires_approval = 0, rejection_reason = NULL WHERE filename = ? AND user_id = ?",
                      (filename, target_user_id))
            
            try:
                bot.send_message(target_user_id, f"<pre>✅ تم قبول استئنافك لملف: {filename}\n\nيمكنك الآن استخدام الملف.</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ تم قبول الاستئناف")
            safe_edit_message_text(f"<pre>✅ تم قبول استئناف الملف: {filename}</pre>", chat_id, message_id)
            return
        
        # رفض الاستئناف
        if data.startswith("reject_appeal:"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            parts = data.split(":")
            filename = parts[1]
            target_user_id = int(parts[2])
            
            try:
                bot.send_message(target_user_id, f"<pre>❌ تم رفض استئنافك لملف: {filename}\n\nالقرار النهائي باقي.</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "❌ تم رفض الاستئناف")
            safe_edit_message_text(f"<pre>❌ تم رفض استئناف الملف: {filename}</pre>", chat_id, message_id)
            return
        
        # تشغيل/إيقاف الملف
        if data.startswith("toggle_"):
            filename = data.replace("toggle_", "")
            
            # التحقق من حالة الملف
            file_info = db_fetchone("SELECT status, requires_approval FROM files WHERE filename = ? AND user_id = ?", (filename, user_id))
            if not file_info:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
                return
            
            status, requires_approval = file_info
            
            # إذا كان الملف يحتاج موافقة
            if requires_approval == 1 and status == 'pending':
                bot.answer_callback_query(call.id, "⏳ الملف بانتظار موافقة المطور")
                return
            
            # إذا كان الملف مرفوضاً
            if status == 'rejected':
                bot.answer_callback_query(call.id, "❌ الملف مرفوض ولا يمكن تشغيله")
                return
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if filename in running_processes:
                # إيقاف الملف
                try:
                    running_processes[filename].terminate()
                    del running_processes[filename]
                    db_execute("UPDATE files SET status = 'stopped' WHERE filename = ? AND user_id = ?", (filename, user_id))
                    bot.answer_callback_query(call.id, "⏸️ تم إيقاف الملف")
                except Exception as e:
                    bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}")
            else:
                # تشغيل الملف
                if os.path.exists(file_path):
                    # التحقق من النقاط
                    if has_used_first_free(user_id):
                        # خصم 4 نقاط للتشغيل
                        if not spend_points(user_id, 4):
                            bot.answer_callback_query(call.id, f"❌ تحتاج 4 نقاط لتشغيل الملف")
                            return
                    else:
                        # أول تشغيل مجاني
                        set_first_free_used(user_id)
                    
                    try:
                        p = subprocess.Popen(["python", file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        running_processes[filename] = p
                        db_execute("UPDATE files SET status = 'active' WHERE filename = ? AND user_id = ?", (filename, user_id))
                        
                        if has_used_first_free(user_id):
                            bot.answer_callback_query(call.id, "▶️ تم التشغيل (خصم 4 نقاط)")
                        else:
                            bot.answer_callback_query(call.id, "▶️ تم التشغيل (الأول مجاني)")
                    except Exception as e:
                        if has_used_first_free(user_id):
                            add_points(user_id, 4)  # استرجاع النقاط إذا فشل التشغيل
                        bot.answer_callback_query(call.id, f"❌ فشل التشغيل: {str(e)}")
                else:
                    bot.answer_callback_query(call.id, "❌ الملف غير موجود")
            
            # تحديث اللوحة
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=file_control_panel(filename, user_id))
            except:
                pass
            return
        
        # تغيير التوكن
        if data.startswith("change_token_"):
            filename = data.replace("change_token_", "")
            msg = bot.send_message(chat_id, f"<pre>🔁 أرسل التوكن الجديد للملف {filename}:</pre>")
            bot.register_next_step_handler(msg, change_token_step, filename)
            bot.answer_callback_query(call.id, "🔁 تغيير التوكن")
            return
        
        # معلومات التوكن
        if data.startswith("token_info_"):
            filename = data.replace("token_info_", "")
            file_info = db_fetchone("SELECT token FROM files WHERE filename = ? AND user_id = ?", (filename, user_id))
            
            if not file_info or not file_info[0]:
                bot.answer_callback_query(call.id, "❌ لا يوجد توكن")
                return
            
            token = file_info[0]
            info = get_token_info(token)
            bot.send_message(chat_id, f"<pre>{info}</pre>", reply_markup=file_control_panel(filename, user_id))
            bot.answer_callback_query(call.id, "ℹ️ معلومات التوكن")
            return
        
        # تنزيل الملف
        if data.startswith("download_"):
            filename = data.replace("download_", "")
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    bot.send_document(chat_id, f, caption=f"<pre>📥 {filename}</pre>")
            else:
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
            return
        
        # حذف الملف
        if data.startswith("delete_"):
            filename = data.replace("delete_", "")
            
            # إيقاف التشغيل إذا كان شغال
            if filename in running_processes:
                try:
                    running_processes[filename].terminate()
                    del running_processes[filename]
                except:
                    pass
            
            # حذف الملف
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # حذف من قاعدة البيانات
            db_execute("DELETE FROM files WHERE filename = ? AND user_id = ?", (filename, user_id))
            
            bot.answer_callback_query(call.id, "🗑️ تم الحذف")
            safe_edit_message_text("<pre>🗑️ تم حذف الملف بنجاح</pre>", chat_id, message_id)
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=main_dark_panel(user_id))
            except:
                pass
            return
        
        # معاينة الملف
        if data.startswith("preview_"):
            filename = data.replace("preview_", "")
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            if not os.path.exists(file_path):
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
                return
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                lines = content.split('\n')
                preview = ""
                for i, line in enumerate(lines[:20], 1):
                    preview += f"{i}: {line}\n"
                
                if len(lines) > 20:
                    preview += f"\n... وأكثر ({len(lines)} سطر)"
                
                msg = f"<pre>🔍 معاينة {filename}\n\n{preview}</pre>"
                bot.send_message(chat_id, msg, reply_markup=file_control_panel(filename, user_id))
            except Exception as e:
                bot.send_message(chat_id, f"<pre>❌ خطأ في قراءة الملف: {str(e)}</pre>")
            
            bot.answer_callback_query(call.id, "🔍 معاينة")
            return
        
        # إصلاح الملف
        if data.startswith("ai_fix_"):
            filename = data.replace("ai_fix_", "")
            
            if not (is_pro(user_id) or is_vip(user_id)):
                bot.answer_callback_query(call.id, "⭐ هذه الميزة للمشتركين فقط")
                return
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            if not os.path.exists(file_path):
                bot.answer_callback_query(call.id, "❌ الملف غير موجود")
                return
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                fixed_content, suggestions, requires_approval = simulate_ai_fix(content, [])
                
                if requires_approval:
                    msg = f"<pre>🛠️ <b>اقتراحات الإصلاح لـ {filename}</b>\n\n"
                    for suggestion in suggestions:
                        msg += f"• {suggestion}\n"
                    msg += "\n⚠️ يتطلب موافقتك لتطبيق التغييرات</pre>"
                    
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("✅ موافق على التغييرات", callback_data=f"apply_fix_{filename}"))
                    markup.add(types.InlineKeyboardButton("❌ رفض التغييرات", callback_data=f"reject_fix_{filename}"))
                    
                    bot.send_message(chat_id, msg, reply_markup=markup)
                else:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(fixed_content)
                    
                    msg = f"<pre>✅ تم إصلاح الملف {filename}\n\nالتغييرات:</pre>"
                    for suggestion in suggestions:
                        msg += f"\n• {suggestion}"
                    
                    bot.send_message(chat_id, msg, reply_markup=file_control_panel(filename, user_id))
                
                bot.answer_callback_query(call.id, "🛠️ جاري الإصلاح")
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}")
            return
        
        # تطبيق الإصلاح
        if data.startswith("apply_fix_"):
            filename = data.replace("apply_fix_", "")
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                fixed_content, suggestions, _ = simulate_ai_fix(content, [])
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                
                msg = f"<pre>✅ تم تطبيق الإصلاح على {filename}\n\nالتغييرات المطبقة:</pre>"
                for suggestion in suggestions:
                    msg += f"\n• {suggestion}"
                
                bot.send_message(chat_id, msg, reply_markup=file_control_panel(filename, user_id))
                bot.answer_callback_query(call.id, "✅ تم التطبيق")
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}")
            return
        
        # رفض الإصلاح
        if data.startswith("reject_fix_"):
            bot.answer_callback_query(call.id, "❌ تم رفض التغييرات")
            return
        
        # طلب ترقية VIP
        if data == "request_vip":
            bot.answer_callback_query(call.id, "⭐ تم إرسال طلبك")
            
            user_info = f"@{call.from_user.username}" if call.from_user.username else f"{call.from_user.first_name}"
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ قبول VIP", callback_data=f"accept_vip_{user_id}"))
            markup.add(types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_vip_{user_id}"))
            
            bot.send_message(
                DEVELOPER_ID,
                f"<pre>⭐ طلب ترقية VIP\n\n• المستخدم: {user_info}\n• الآيدي: {user_id}</pre>",
                reply_markup=markup
            )
            
            bot.send_message(chat_id, "<pre>⭐ تم إرسال طلب الترقية للمطور</pre>")
            return
        
        # قبول VIP
        if data.startswith("accept_vip_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            target_id = int(data.replace("accept_vip_", ""))
            
            # التحقق إذا كان موجود بالفعل
            existing = db_fetchone("SELECT user_id FROM vip_users WHERE user_id = ?", (target_id,))
            if existing:
                db_execute("UPDATE vip_users SET status = 'active' WHERE user_id = ?", (target_id,))
            else:
                db_execute("INSERT INTO vip_users (user_id, activated_by, activation_time, expiry_date, status) VALUES (?, ?, ?, ?, ?)",
                          (target_id, user_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                           (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"), 'active'))
            
            try:
                bot.send_message(target_id, "<pre>🎉 تم قبول طلبك! أنت الآن عضو VIP</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "✅ تم الترقية")
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            except:
                pass
            safe_edit_message_text(f"<pre>✅ تم ترقية المستخدم {target_id} إلى VIP</pre>", chat_id, message_id)
            return
        
        # رفض VIP
        if data.startswith("reject_vip_"):
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            target_id = int(data.replace("reject_vip_", ""))
            
            try:
                bot.send_message(target_id, "<pre>❌ تم رفض طلب الترقية إلى VIP</pre>")
            except:
                pass
            
            bot.answer_callback_query(call.id, "❌ تم الرفض")
            try:
                bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            except:
                pass
            safe_edit_message_text(f"<pre>❌ تم رفض طلب الترقية للمستخدم {target_id}</pre>", chat_id, message_id)
            return
        
        # عرض الملفات النشطة
        if data == "show_active":
            active_files = []
            for filename, process in running_processes.items():
                file_info = db_fetchone("SELECT user_id FROM files WHERE filename = ?", (filename,))
                if file_info and file_info[0] == user_id:
                    active_files.append(filename)
            
            if not active_files:
                msg = "<pre>⏸️ لا توجد ملفات نشطة</pre>"
            else:
                msg = "<pre>▶️ <b>الملفات النشطة:</b>\n\n"
                for i, filename in enumerate(active_files, 1):
                    msg += f"{i}. {filename}\n"
                msg += "</pre>"
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=main_dark_panel(user_id))
                except:
                    pass
            
            bot.answer_callback_query(call.id, "▶️ الملفات النشطة")
            return
        
        # إيقاف جميع الملفات
        if data == "stop_all":
            stopped = 0
            for filename, process in list(running_processes.items()):
                file_info = db_fetchone("SELECT user_id FROM files WHERE filename = ?", (filename,))
                if file_info and file_info[0] == user_id:
                    try:
                        process.terminate()
                        del running_processes[filename]
                        db_execute("UPDATE files SET status = 'stopped' WHERE filename = ?", (filename,))
                        stopped += 1
                    except:
                        pass
            
            msg = f"<pre>⏸️ تم إيقاف {stopped} ملف</pre>"
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=main_dark_panel(user_id))
                except:
                    pass
            
            bot.answer_callback_query(call.id, f"⏸️ تم الإيقاف")
            return
        
        # الهدايا
        if data == "gifts":
            msg = bot.send_message(chat_id, "<pre>🎁 أرسل كود الهدية:</pre>")
            bot.register_next_step_handler(msg, redeem_gift_step)
            bot.answer_callback_query(call.id, "🎁 الهدايا")
            return
        
        # المساعدة
        if data == "help":
            help_msg = """
<pre>ℹ️ <b>مساعدة واستخدام البوت</b>

🛡️ <b>نظام الحماية الذكي:</b>
• كشف محاولات الاختراق تلقائياً
• تحليل الملفات بالذكاء الاصطناعي
• إشعارات فورية للمطور عن التهديدات
• نظام قبول/رفض للملفات الخطرة

📤 <b>رفع الملفات:</b>
• أرسل ملف Python (.py) أو ملف Zip يحتوي على ملفات Python
• يمكن رفع ملفات ZIP وسيتم استخراج ملفات PY منها تلقائياً

💎 <b>نظام النقاط:</b>
• أول تشغيل مجاني لكل مستخدم
• كل تشغيل لاحق يكلف 4 نقاط
• اربح نقاط بدعوة الأصدقاء
• يمكن للأدمن تعديل أسعار الرفع والدعوة

⭐ <b>VIP:</b>
• مزايا إضافية مثل الإصلاح التلقائي
• أولوية في الدعم
• طلب الترقية من القائمة

🔧 <b>الملفات:</b>
• تشغيل/إيقاف الملفات
• تغيير التوكن
• معاينة المحتوى
• تنزيل الملفات
• حذف الملفات

🎁 <b>الهدايا:</b>
• استخدم كود الهدية لربح نقاط إضافية
• يمكن للأدمن إنشاء أكواد هدايا

🔗 <b>الدعوة:</b>
• احصل على رابط دعوة خاص بك
• اربح نقاط لكل صديق يسجل عبر رابطك

🛠️ <b>للأدمن:</b>
• /admin للوصول إلى لوحة التحكم
• تعديل الأسعار (رفع ملفات/دعوة)
• إدارة المستخدمين والملفات
• نظام مراقبة الاختراق
• إنشاء أكواد هدايا
• إضافة/خصم نقاط للمستخدمين
• حظر/فك حظر الأعضاء
• منع/فك منع رفع الملفات</pre>
            """
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back_main"))
            
            if safe_edit_message_text(help_msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "ℹ️ مساعدة")
            return
        
        # حالتي
        if data == "my_status":
            points = get_points(user_id)
            vip_status = "⭐ VIP" if is_vip(user_id) else ""
            pro_status = "⭐ PRO" if is_pro(user_id) else ""
            admin_status = "🛠️ أدمن" if is_admin(user_id) else ""
            
            status_text = vip_status or pro_status or admin_status or "🚀 عادي"
            
            # التحقق من الحظر
            banned_status = "⛔ محظور" if is_banned(user_id) else "✅ غير محظور"
            upload_blocked_status = "🚫 محظور من الرفع" if is_upload_blocked(user_id) else "✅ مسموح بالرفع"
            
            # الحصول على إحصائيات الملفات
            total_files = db_fetchone("SELECT COUNT(*) FROM files WHERE user_id = ?", (user_id,))
            pending_files = db_fetchone("SELECT COUNT(*) FROM files WHERE user_id = ? AND status = 'pending'", (user_id,))
            rejected_files = db_fetchone("SELECT COUNT(*) FROM files WHERE user_id = ? AND status = 'rejected'", (user_id,))
            
            total_files = total_files[0] if total_files else 0
            pending_files = pending_files[0] if pending_files else 0
            rejected_files = rejected_files[0] if rejected_files else 0
            
            msg = f"""
<pre>👤 <b>حالتك</b>

𖤓 الآيدي: {user_id}
𖤓 النقاط: {points} نقطة
𖤓 المستوى: {status_text}
𖤓 حالة الحظر: {banned_status}
𖤓 رفع الملفات: {upload_blocked_status}
𖤓 الملفات النشطة: {count_active_files(user_id)}
𖤓 إجمالي الملفات: {total_files}
𖤓 بانتظار الموافقة: {pending_files}
𖤓 المرفوضة: {rejected_files}
𖤓 أول تشغيل: {'✅ مستخدم' if has_used_first_free(user_id) else '⚠️ متاح'}</pre>
            """
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=main_dark_panel(user_id))
                except:
                    pass
            
            bot.answer_callback_query(call.id, "👤 حالتك")
            return
        
        # ===== المعالجات الجديدة من الكود الثاني =====
        
        # إدارة المستخدمين
        if data == "manage_users":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            users = get_all_users(30)
            msg = "<pre>👥 <b>إدارة المستخدمين</b>\n\n</pre>"
            
            if not users:
                msg += "<pre>لا يوجد مستخدمين بعد</pre>"
            else:
                for i, user in enumerate(users, 1):
                    user_id_user, first_seen, last_seen = user
                    msg += f"<pre>{i}. آيدي: {user_id_user}\n   أول دخول: {first_seen}\n   آخر دخول: {last_seen}\n\n</pre>"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "👥 إدارة المستخدمين")
            return
        
        # إدارة الملفات
        if data == "manage_files":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            files = get_all_files(30)
            msg = "<pre>📁 <b>إدارة الملفات</b>\n\n</pre>"
            
            if not files:
                msg += "<pre>لا يوجد ملفات بعد</pre>"
            else:
                for i, file in enumerate(files, 1):
                    filename, file_user_id, upload_time, status, security_level = file
                    msg += f"<pre>{i}. {filename}\n   المستخدم: {file_user_id}\n   الحالة: {status}\n   الأمان: {security_level or 'غير محدد'}\n\n</pre>"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "📁 إدارة الملفات")
            return
        
        # البث
        if data == "broadcast":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>📢 <b>نظام البث للمستخدمين</b>\n\nأرسل الرسالة التي تريد بثها:\n\n• يمكن استخدام HTML\n• أضرفي رابط بصيغة: <a href='رابط'>نص</a>\n• استخدم <code>\\n</code> للسطر الجديد</pre>")
            bot.register_next_step_handler(msg, process_broadcast_step)
            bot.answer_callback_query(call.id, "📢 نظام البث")
            return
        
        # إنشاء هدية
        if data == "create_gift":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>🎁 <b>إنشاء كود هدية</b>\n\nأرسل التفاصيل بالصيغة التالية:\n\nالنقاط:العدد_الأقصى:عدد_الأيام\n\nمثال: 100:10:30\nيعني: 100 نقطة، 10 استخدامات، صلاحية 30 يوم</pre>")
            bot.register_next_step_handler(msg, create_gift_step)
            bot.answer_callback_query(call.id, "🎁 إنشاء هدية")
            return
        
        # الإحصائيات
        if data == "stats":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            stats = get_bot_stats()
            msg = f"""
<pre>📊 <b>إحصائيات البوت</b>

👥 <b>المستخدمين:</b>
𖤓 إجمالي المستخدمين: {stats['total_users']}
𖤓 إجمالي النقاط: {stats['total_points']}
𖤓 المستخدمين المحظورين: {stats['banned_users']}
𖤓 المحظورين من الرفع: {stats['blocked_uploads']}

📁 <b>الملفات:</b>
𖤓 إجمالي الملفات: {stats['total_files']}
𖤓 الملفات النشطة: {stats['active_files']}

🛡️ <b>الأمان:</b>
𖤓 محاولات الاختراق: {stats['hack_attempts']}

⚙️ <b>النظام:</b>
𖤓 وقت التشغيل: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
𖤓 حالة البوت: {'🟢 نشط' if bot_enabled() else '🔴 معطل'}
𖤓 وضع VIP: {'🟢 مفعل' if is_vip_mode() else '🔴 معطل'}</pre>
            """
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔄 تحديث", callback_data="stats"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "📊 الإحصائيات")
            return
        
        # إدارة VIP
        if data == "manage_vip":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            vip_users = db_fetchall("SELECT user_id, activation_time, expiry_date, status FROM vip_users ORDER BY activation_time DESC")
            pro_users = db_fetchall("SELECT user_id, activation_time, expiry_date, status FROM pro_users ORDER BY activation_time DESC")
            
            msg = "<pre>⭐ <b>إدارة VIP/PRO</b>\n\n</pre>"
            
            if vip_users:
                msg += "<pre>👑 <b>المستخدمين VIP:</b>\n\n</pre>"
                for i, user in enumerate(vip_users[:10], 1):
                    user_id_vip, activation_time, expiry_date, status = user
                    msg += f"<pre>{i}. آيدي: {user_id_vip}\n   الحالة: {status}\n   الانتهاء: {expiry_date}\n\n</pre>"
            
            if pro_users:
                msg += "<pre>🚀 <b>المستخدمين PRO:</b>\n\n</pre>"
                for i, user in enumerate(pro_users[:10], 1):
                    user_id_pro, activation_time, expiry_date, status = user
                    msg += f"<pre>{i}. آيدي: {user_id_pro}\n   الحالة: {status}\n   الانتهاء: {expiry_date}\n\n</pre>"
            
            if not vip_users and not pro_users:
                msg += "<pre>لا يوجد مستخدمين VIP أو PRO</pre>"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("➕ إضافة VIP", callback_data="add_vip"))
            markup.add(types.InlineKeyboardButton("➕ إضافة PRO", callback_data="add_pro"))
            markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel"))
            
            if safe_edit_message_text(msg, chat_id, message_id):
                try:
                    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)
                except:
                    pass
            
            bot.answer_callback_query(call.id, "⭐ إدارة VIP/PRO")
            return
        
        # إضافة VIP
        if data == "add_vip":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>➕ <b>إضافة مستخدم VIP</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, add_vip_step)
            bot.answer_callback_query(call.id, "➕ إضافة VIP")
            return
        
        # إضافة PRO
        if data == "add_pro":
            if not is_admin(user_id):
                bot.answer_callback_query(call.id, "🚫 لا تمتلك صلاحيات")
                return
            
            msg = bot.send_message(chat_id, "<pre>➕ <b>إضافة مستخدم PRO</b>\n\nأرسل آيدي المستخدم:</pre>")
            bot.register_next_step_handler(msg, add_pro_step)
            bot.answer_callback_query(call.id, "➕ إضافة PRO")
            return
        
        # ===== نهاية المعالجات الجديدة =====
        
        # إذا وصلنا إلى هنا ولم يتم معالجة الكال باك
        bot.answer_callback_query(call.id, "⚙️ تمت المعالجة")
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة الكال باك: {str(e)}")
        try:
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
        except:
            pass

# =============================
# دوال الحماية
# =============================
def save_protection_php():
    try:
        path = os.path.join(PROTECTION_FOLDER, "index.php")
        with open(path, "w", encoding="utf-8") as f:
            f.write(PROTECTION_PHP_CONTENT)
        logger.info("✅ تم حفظ ملف الحماية index.php")
    except Exception as e:
        logger.error(f"❌ فشل حفظ ملف الحماية: {e}")

def file_hash(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdig()
    except Exception:
        return None

def load_protection_state():
    try:
        if os.path.exists(PROTECTION_STATE_FILE):
            with open(PROTECTION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except:
        pass
    return {}

def save_protection_state(state):
    try:
        with open(PROTECTION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception as e:
        logger.error(f"❌ فشل حفظ حالة الحماية: {e}")

def monitor_uploaded_files(interval=300):
    try:
        state = load_protection_state()
        while True:
            current = {}
            changes = []
            for root, _, files in os.walk(UPLOAD_FOLDER):
                for fn in files:
                    path = os.path.join(root, fn)
                    h = file_hash(path)
                    if not h:
                        continue
                    rel = os.path.relpath(path, UPLOAD_FOLDER)
                    current[rel] = h
                    if rel not in state:
                        changes.append(f"NEW: {rel}")
                    elif state.get(rel) != h:
                        changes.append(f"MODIFIED: {rel}")
            
            for prev in list(state.keys()):
                if prev not in current:
                    changes.append(f"REMOVED: {prev}")
            
            if changes:
                try:
                    msg = "<pre>⚠️ تنبيه تغيير في ملفات الاستضافة:\n\n"
                    for c in changes[:10]:
                        msg += f"• {c}\n"
                    if len(changes) > 10:
                        msg += f"• ... و {len(changes)-10} تغيير آخر\n"
                    msg += "</pre>"
                    bot.send_message(DEVELOPER_ID, msg)
                except:
                    pass
            
            state = current
            save_protection_state(state)
            time.sleep(interval)
    except Exception as e:
        logger.error(f"❌ خطأ في مُراقب الملفات: {e}")

def start_protection_monitor():
    save_protection_php()
    t = threading.Thread(target=monitor_uploaded_files, args=(300,), daemon=True)
    t.start()
    logger.info("🛡️ Started file protection monitor thread")

def on_exit():
    try:
        state = load_protection_state()
        save_protection_state(state)
    except:
        pass

atexit.register(on_exit)

# =============================
# تشغيل البوت مع معالجة الأخطاء
# =============================
def infinity_polling_with_reconnect():
    """تشغيل البوت مع إعادة الاتصال التلقائي عند حدوث أخطاء"""
    while True:
        try:
            logger.info("🤖 بدء تشغيل البوت مع نظام الذكاء الاصطناعي للحماية...")
            logger.info(f"🛡️ نظام كشف الاختراق: {'مفعل' if is_ai_security_enabled() else 'معطل'}")
            logger.info(f"📊 عتبة درجة الخطر: {get_hack_score_threshold()}")
            
            start_protection_monitor()
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
            
        except KeyboardInterrupt:
            logger.info("⏹️ توقف البوت يدوياً")
            break
        except Exception as e:
            logger.error(f"❌ خطأ في تشغيل البوت: {e}")
            logger.info("🔄 إعادة الاتصال بعد 10 ثوانٍ...")
            time.sleep(10)

if __name__ == "__main__":
    infinity_polling_with_reconnect()