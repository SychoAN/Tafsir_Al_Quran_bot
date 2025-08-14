from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackContext
)
import json
import pytz
from datetime import time, datetime
import asyncio
import os
import aiofiles

# التوكن - استبدله بتوكن بوتك الفعلي
TOKEN = os.getenv("BOT_TOKEN")  # أو استخدم os.environ['BOT_TOKEN']
if not TOKEN:
    raise ValueError("لم يتم تعيين توكن البوت! يرجى تعيين متغير البيئة BOT_TOKEN")
DATA_FILE = "quran_files.json"
WIRD_FILE = "daily_wird.json"
ITEMS_PER_PAGE = 10
CAIRO_TZ = pytz.timezone('Africa/Cairo')

# تهيئة ملف الورد عند بدء التشغيل
async def initialize_wird_file():
    if not os.path.exists(WIRD_FILE):
        initial_data = {"users": {}, "next_id": 1}
        async with aiofiles.open(WIRD_FILE, "w", encoding="utf-8") as f:
            await f.write(json.dumps(initial_data, indent=2))

# تحميل البيانات القرآنية
with open(DATA_FILE, "r", encoding="utf-8") as f:
    audios = json.load(f)

# استخراج قائمة السور بدون أرقام
def get_surah_names():
    names = set()
    for audio in audios:
        title = audio["title"]
        for i, c in enumerate(title):
            if not c.isdigit():
                break
        clean_name = title[i:].lstrip(" -_.")
        names.add(clean_name)
    return sorted(list(names))

SURAH_NAMES = get_surah_names()

# تحميل أو تهيئة بيانات الورد
async def load_wird_data():
    if os.path.exists(WIRD_FILE):
        try:
            async with aiofiles.open(WIRD_FILE, "r", encoding="utf-8") as f:
                data = json.loads(await f.read())
                if "users" not in data:
                    data["users"] = {}
                if "next_id" not in data:
                    data["next_id"] = 1
                return data
        except:
            return {"users": {}, "next_id": 1}
    return {"users": {}, "next_id": 1}

async def save_wird_data(data):
    async with aiofiles.open(WIRD_FILE, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

# إنشاء لوحة المفاتيح
def build_keyboard(page: int):
    start_idx = page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_names = SURAH_NAMES[start_idx:end_idx]

    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"play_{name}")]
        for name in page_names
    ]

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅ السابق", callback_data=f"page_{page-1}"))
    if end_idx < len(SURAH_NAMES):
        nav_buttons.append(InlineKeyboardButton("التالي ➡", callback_data=f"page_{page+1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # إضافة زر إدارة الورد
    keyboard.append([InlineKeyboardButton("📅 إدارة الورد اليومي", callback_data="manage_wird")])

    return InlineKeyboardMarkup(keyboard)

# لوحة مفاتيح إدارة الورد
def build_wird_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏱ تعيين مدة الورد", callback_data="set_duration")],
        [InlineKeyboardButton("➕ إضافة سورة للورد", callback_data="add_surah")],
        [InlineKeyboardButton("❌ إيقاف الورد", callback_data="stop_wird")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

# تقدير وقت السورة
def estimate_surah_time(surah_name, duration_per_day):
    # تقدير افتراضي: معظم السور يمكن إكمالها في 1-5 أيام
    # يمكن استبدال هذا بدالة أكثر دقة
    surah_length = len(surah_name) % 5 + 1  # قيمة افتراضية للتمثيل
    days_needed = max(1, surah_length // 2)
    return days_needed, duration_per_day

# إرسال الورد اليومي
async def send_daily_wird(context: CallbackContext):
    wird_data = await load_wird_data()
    if "users" not in wird_data:
        return
        
    for user_id, user_data in wird_data["users"].items():
        if not user_data.get("active", False) or not user_data.get("surahs", []):
            continue

        chat_id = user_data.get("chat_id")
        if not chat_id:
            continue
            
        try:
            # التحقق من أن البوت أدمن في الجروب
            chat = await context.bot.get_chat(chat_id)
            if chat.type != "private":
                admins = await chat.get_administrators()
                if not any(admin.user.id == context.bot.id for admin in admins):
                    continue

            # إرسال الورد
            for surah_name in user_data["surahs"]:
                matched_audios = [a for a in audios if surah_name in a["title"]]
                for audio in matched_audios:
                    await context.bot.forward_message(
                        chat_id=chat_id,
                        from_chat_id=audio["chat_id"],
                        message_id=audio["message_id"]
                    )
            
            # رسالة تأكيد
            days_needed, daily_duration = estimate_surah_time(
                surah_name, 
                user_data.get("duration", 10)
            )
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"⏰ هذا وردك اليومي ({daily_duration} دقيقة)\n"
                     f"سورة {surah_name} تحتاج {days_needed} أيام لإكمالها"
            )
        except Exception as e:
            print(f"فشل إرسال الورد لـ {user_id}: {e}")

# معالجة الأوامر
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    wird_data = await load_wird_data()
    
    # إرسال رسالة ترحيبية للمستخدمين الجدد
    if str(user.id) not in wird_data.get("users", {}):
        await update.message.reply_text(
            "مرحبًا بك في بوت القرآن الكريم!\n"
            "⏰ سيتم إرسال الورد اليومي الساعة 5 صباحًا بتوقيت القاهرة\n"
            "يمكنك ضبط الورد من خلال زر '📅 إدارة الورد اليومي'"
        )
        
        # تسجيل المستخدم الجديد
        wird_data.setdefault("users", {})[str(user.id)] = {
            "active": False,
            "duration": 10,  # القيمة الافتراضية
            "surahs": [],
            "chat_id": update.message.chat_id
        }
        await save_wird_data(wird_data)
    
    await update.message.reply_text(
        "🎵 اختر السورة:",
        reply_markup=build_keyboard(0)
    )

# معالجة ضغطات الأزرار
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    wird_data = await load_wird_data()
    user_id = str(query.from_user.id)
    
    if data.startswith("page_"):
        page = int(data.split("_")[1])
        await query.edit_message_text(
            text="🎵 اختر السورة:",
            reply_markup=build_keyboard(page)
        )
    
    elif data.startswith("play_"):
        surah_name = data[len("play_"):]
        matched_audios = [a for a in audios if surah_name in a["title"]]
        
        for audio in matched_audios:
            await context.bot.forward_message(
                chat_id=query.message.chat_id,
                from_chat_id=audio["chat_id"],
                message_id=audio["message_id"]
            )
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة", callback_data="page_0")]]
        await query.message.reply_text(
            "🎵 تم إرسال الملفات! اختر آخر:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    elif data == "manage_wird":
        await query.edit_message_text(
            text="⚙️ إدارة الورد اليومي:",
            reply_markup=build_wird_keyboard()
        )
    
    elif data == "set_duration":
        await query.edit_message_text(
            "⏱ الرجاء إرسال المدة اليومية بالدقائق (مثال: 10):"
        )
        context.user_data["action"] = "set_duration"
    
    elif data == "add_surah":
        await query.edit_message_text(
            "📖 الرجاء إرسال اسم السورة لإضافتها للورد:"
        )
        context.user_data["action"] = "add_surah"
    
    elif data == "stop_wird":
        user_data = wird_data.get("users", {}).get(user_id, {})
        user_data["active"] = False
        wird_data.setdefault("users", {})[user_id] = user_data
        await save_wird_data(wird_data)
        await query.edit_message_text("✅ تم إيقاف الورد اليومي")
    
    elif data == "back_main":
        await query.edit_message_text(
            text="🎵 اختر السورة:",
            reply_markup=build_keyboard(0)
        )

# معالجة الرسائل النصية
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    
    if "action" not in context.user_data:
        return
    
    action = context.user_data["action"]
    wird_data = await load_wird_data()
    user_wird = wird_data.get("users", {}).get(user_id, {
        "active": False,
        "duration": 10,
        "surahs": [],
        "chat_id": update.message.chat_id
    })
    
    if action == "set_duration":
        try:
            duration = int(update.message.text)
            if duration < 5 or duration > 60:
                await update.message.reply_text("المدة يجب أن تكون بين 5 و 60 دقيقة")
                return
                
            user_wird["duration"] = duration
            user_wird["active"] = True
            wird_data.setdefault("users", {})[user_id] = user_wird
            await save_wird_data(wird_data)
            
            await update.message.reply_text(
                f"✅ تم تعيين مدة الورد اليومي إلى {duration} دقائق\n"
                "سيتم إرسال الورد الساعة 5 صباحًا بتوقيت القاهرة"
            )
        except ValueError:
            await update.message.reply_text("الرجاء إدخال رقم صحيح")
    
    elif action == "add_surah":
        surah_name = update.message.text
        if surah_name not in SURAH_NAMES:
            await update.message.reply_text("اسم السورة غير صحيح. الرجاء المحاولة مرة أخرى")
            return
            
        if "surahs" not in user_wird:
            user_wird["surahs"] = []
            
        user_wird["surahs"].append(surah_name)
        user_wird["active"] = True
        wird_data.setdefault("users", {})[user_id] = user_wird
        await save_wird_data(wird_data)
        
        days_needed, daily_duration = estimate_surah_time(
            surah_name, 
            user_wird.get("duration", 10)
        )
        
        await update.message.reply_text(
            f"✅ تمت إضافة سورة {surah_name} للورد اليومي\n"
            f"ستحتاج {days_needed} أيام ({daily_duration} دقيقة/يوم)"
        )
    
    # مسح حالة المستخدم
    context.user_data.pop("action", None)

def main():
    # إنشاء event loop جديد
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # تهيئة ملف الورد
    loop.run_until_complete(initialize_wird_file())
    
    # بناء التطبيق
    application = ApplicationBuilder().token(TOKEN).build()
    
    # جدولة الورد اليومي
    if application.job_queue:
        application.job_queue.run_daily(
            send_daily_wird,
            time=time(hour=5, minute=0, tzinfo=CAIRO_TZ),
            days=(0, 1, 2, 3, 4, 5, 6)
        )
    
    # تسجيل المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot is running...")
    
    # بدء البوت
    application.run_polling()

if __name__ == "__main__":
    main()
