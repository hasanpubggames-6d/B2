# Enterprise OCR & Translation Telegram Bot

هذا البوت هو نظام متكامل لاستخراج النصوص من الصور وترجمتها باستخدام تقنيات الذكاء الاصطناعي (GPT-4 Vision).

## المميزات الرئيسية:
- **نظام OCR ذكي:** يستخدم GPT-4 Vision لاستخراج النصوص بدقة عالية جداً.
- **ترجمة فائقة:** ترجمة طبيعية (Human-like) باستخدام نماذج لغوية متقدمة.
- **لوحة تحكم داخلية:** إدارة كاملة للمستخدمين، القنوات، والإحصائيات من داخل التيليجرام.
- **نظام اشتراك إجباري:** دعم حتى 10 قنوات مع التحقق التلقائي.
- **أداء عالي:** معالجة غير متزامنة (Async) مع دعم Redis للتخزين المؤقت وتحديد معدل الطلبات (Rate Limiting).
- **هندسة برمجية نظيفة:** مبني باستخدام `aiogram` و `SQLAlchemy` مع بنية Modular قابلة للتوسع.

## متطلبات التشغيل:
- Python 3.10+
- Redis Server (اختياري ولكن ينصح به للأداء العالي)
- OpenAI API Key (لدعم GPT-4 Vision والترجمة)
- Telegram Bot Token

## خطوات التنصيب:

1. **تثبيت المكتبات المطلوبة:**
   ```bash
   pip install aiogram sqlalchemy aiosqlite openai python-dotenv pillow reportlab python-docx redis aiohttp
   ```

2. **إعداد ملف البيئة (.env):**
   قم بتعديل ملف `.env` وإضافة التوكنات الخاصة بك:
   ```env
   BOT_TOKEN=your_bot_token
   DEVELOPER_ID=your_telegram_id
   OPENAI_API_KEY=your_openai_key
   DATABASE_URL=sqlite+aiosqlite:///bot_database.db
   REDIS_URL=redis://localhost:6379/0
   ```

3. **تشغيل البوت:**
   ```bash
   python main.py
   ```

## هيكل المشروع:
- `core/`: يحتوي على المنطق الأساسي (الاشتراك، تحديد المعدل).
- `database/`: نماذج قاعدة البيانات وإدارة الجلسات.
- `engines/`: محركات OCR والترجمة.
- `handlers/`: معالجات الرسائل ولوحة التحكم.
- `utils/`: أدوات التصدير والمعالجة.

## ملاحظات الأمان:
- تم تشفير المفاتيح الحساسة في ملف `.env`.
- يدعم البوت الحماية ضد الـ Flood والـ Rate Limiting.
- جميع العمليات مسجلة في قاعدة البيانات للرقابة.
