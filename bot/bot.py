import os
from telegram import ReplyKeyboardMarkup, KeyboardButton
import asyncio
import html
import json
import logging
import traceback
from datetime import datetime

import ai_generator.abstract as abstract

import ai_generator.openai_utils as openai_utils
import ai_generator.presentation as presentation

import config

import database

import telegram
from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    User,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

# setup
db = database.Database()
logger = logging.getLogger(__name__)

CHAT_MODES = config.chat_modes

HELP_MESSAGE = """<b>Buyruqlar:</b>
💼 /menu – Menyuni ko'rish
🤖 /mode – Rejimni tanlash
💰 /balance – Balansni ko'rish
🆘 /help – Yordam
"""


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("/menu", "Menyuni ko'rish"),
        BotCommand("/mode", "Rejimni tanlash"),
        BotCommand("/balance", "Balansni ko'rish"),
        BotCommand("/help", "Yordam"),
    ])


def split_text_into_chunks(text, chunk_size):
    for i in range(0, len(text), chunk_size):
        yield text[i:i + chunk_size]


async def register_user_if_not_exists(update: Update, context: CallbackContext, user: User):
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )


async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id

    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    reply_text = "<b>Assalomu alaykum!</b> Men Suniy Intelekt asosida ishlaydigan <b>Presento AI</b> botman 🤖\n\n"
    reply_text += "<b>Xizmatlar:</b> \n\n<b>💻 Taqdimot - </b> Bir necha soniya ichida istalgan mavzuda professional shablonlar yordamida taqdimot yaratish \n<b>📝 Tezis (Mustaqil ish) - </b> Bir necha soniya ichida istalgan mavzuda professional word fortmatida tezis (Ilmiy, Mustaqil ish) yaratish \n\n"
    reply_text += "\n Ishni boshlash uchun <b>menu</b> bo'limini tanlang!"
    
    help_text = HELP_MESSAGE
    help_text += "\n <i>Ishni boshlash uchun <b>menu</b> bo'limini tanlang!</i>"

    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)



async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def message_handle(update: Update, context: CallbackContext, message=None):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id

    db.set_user_attribute(user_id, "last_interaction", datetime.now())


async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    keyboard = []
    for chat_mode, chat_mode_dict in CHAT_MODES.items():
        keyboard.append([InlineKeyboardButton(chat_mode_dict["name"], callback_data=f"set_chat_mode|{chat_mode}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Chat rejimini tanlang:", reply_markup=reply_markup)
    
async def document_filter(update):
    return update.document is not None


async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    user_id = update.callback_query.from_user.id
    query = update.callback_query
    await query.answer()
    chat_mode = query.data.split("|")[1]
    db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
    await query.edit_message_text(f"{CHAT_MODES[chat_mode]['welcome_message']}\n\n" + HELP_MESSAGE,
                                  parse_mode=ParseMode.HTML)


SELECTING_ACTION, SELECTING_MENU, INPUT_TOPIC, INPUT_PROMPT = map(chr, range(4))
END = ConversationHandler.END
PRESENTATION = "Taqdimot"
ABSTRACT = "Tezis"
LANGUAGES = ['English', 'Uzbek', 'Russian','Korean', 'German', 'French', 'Italian', 'Spanish', 'Ukrainian', 'Polish', 'Turkish',
             'Romanian', 'Dutch', 'Greek', 'Czech', 'Portuguese', 'Swedish', 'Hungarian', 'Serbian', 'Bulgarian',
             'Danish', 'Norwegian', 'Finnish', 'Slovak', 'Croatian', 'Arabic', 'Hebrew', 'Lithuanian', 'Slovenian',
             'Bengali', 'Chinese', 'Persian', 'Indonesian', 'Latvian', 'Tamil', 'Japanese',
             ]
LANGUAGES_EMOJI = ['🇬🇧', '🇺🇿','🇷🇺','🇰🇷', '🇩🇪', '🇫🇷', '🇮🇹', '🇪🇸', '🇺🇦', '🇵🇱', '🇹🇷', '🇷🇴', '🇳🇱', '🇬🇷',
                   '🇨🇿', '🇵🇹', '🇸🇪', '🇭🇺', '🇷🇸', '🇧🇬', '🇩🇰', '🇳🇴', '🇫🇮', '🇸🇰', '🇭🇷', '🇸🇦',
                   '🇮🇱', '🇱🇹', '🇸🇮', '🇧🇩', '🇨🇳', '🇮🇷', '🇮🇩', '🇱🇻', '🇮🇳', '🇯🇵', 
                   ]
TEMPLATES = ["Mountains", "Organic", "East Asia", "Explore", "3D Float", "Luminous", "Academic", "Snowflake", "Floral",
             "Minimal"]
TEMPLATES_EMOJI = ["🗻", "🌿", "🐼", "🧭", "🌑", "🕯️", "🎓", "❄️", "🌺", "◽"]
TYPES = ["Ilmiy","Ma'lumot beruvchi", "Kreativ", "Biografik", "Kulguli", "Jiddiy", "Ilhomlantiruvchi", "Motivatsion", "Tarbiyaviy", "Tarixiy",
         "Romantik", "Sirli", "Dam olish", "Sarguzashtli", "Hazil",  "Musiqiy", "Dahshat", "Fantaziya",
         "Action", "Dramatik", "Satirik", "She'riy", "Triller", "Sport", "Komediya", "Biografik", "Siyosiy",
         "Sehrli", "Sir", "Sayohat", "Hujjatli film", "Jinoyat", "Ovqat pishirish"]
TYPES_EMOJI = ["🔬","📚","🎨","📜","😂", "😐", "🌟", "💪", "👨‍🎓", "🏛️", "💕", "🕵️‍♂️", "🧘‍♀️", "🗺️", "🤣", "🎵", "😱", "🦄",
               "💥", "😮", "🙃", "🌸", "😰", "⚽", "😆",  "🗳️", "✨", "🔮", "✈️", "🎥", "🚓", "🍽️"]
COUNTS = [str(i) for i in range(4, 16)]
COUNTS_EMOJI = ["", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", "", ""]
BACK = "⬅️Back"
(
    PRESENTATION_LANGUAGE_CHOICE,
    ABSTRACT_LANGUAGE_CHOICE,
    TEMPLATE_CHOICE,
    PRESENTATION_TYPE_CHOICE,
    ABSTRACT_TYPE_CHOICE,
    COUNT_SLIDE_CHOICE,
    TOPIC_CHOICE,
    API_RESPONSE,
    START_OVER,
    MESSAGE_ID,
) = map(chr, range(10, 20))

async def check_user_channels(update: Update, context: CallbackContext) -> bool:
    user = update.effective_user
    print("User ID:", user.id)
    required_channels = ["-1002109445838"]  # Add your required channel IDs here
    for channel in required_channels:
        try:
            chat_member = await context.bot.get_chat_member(chat_id=channel, user_id=user.id)
            print("Chat member status:", chat_member.status)
            if chat_member.status not in ["member", "administrator", "creator"]:
                return False
        except telegram.error.BadRequest as e:
            # Handle the case where the user is not found in the channel
            print(f"User not found in channel {channel}: {e}")
            return False
    return True


async def menu_handle(update: Update, context: CallbackContext) -> str:
    try:
        await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    except AttributeError:
        await register_user_if_not_exists(update, context, update.message.from_user)
        try:
            if MESSAGE_ID in context.chat_data:
                await context.bot.delete_message(chat_id=update.effective_chat.id,
                                                 message_id=context.chat_data[MESSAGE_ID].message_id)
        except telegram.error.BadRequest:
            pass

    if not await check_user_channels(update, context):
        await update.message.reply_text("Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling va qaytadan urinib ko'ring:\n\n👉 <a href='https://t.me/presento_ai'>Presento AI</a>", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
        return
    
    # If the user has joined the required channels, display the menu with inline buttons
    keyboard = [
        [
            InlineKeyboardButton(f"💻 {PRESENTATION}", callback_data=PRESENTATION)
        ],
        [
            InlineKeyboardButton(f"📝 {ABSTRACT}", callback_data=ABSTRACT)
        ]
    ]
    if context.user_data.get(START_OVER):
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Menu:", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        context.chat_data[MESSAGE_ID] = await update.message.reply_text("Menu:",
                                                                        reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data[START_OVER] = False
    return SELECTING_ACTION

async def generate_keyboard(page, word_array, emoji_array, callback):
    keyboard = []
    per_page = 12
    for i, words in enumerate(word_array[(page-1)*per_page:page*per_page]):
        if i % 2 == 0:
            keyboard.append([InlineKeyboardButton(emoji_array[i+((page-1)*per_page)] + words,
                                                  callback_data=f"{callback}{words}")])
        else:
            keyboard[-1].append(InlineKeyboardButton(emoji_array[i+((page-1)*per_page)] + words,
                                                     callback_data=f"{callback}{words}"))
    if len(word_array) > per_page and page == 1:
        keyboard.append([InlineKeyboardButton(">>", callback_data=f"page_{callback}{page+1}")])
    elif page != 1:
        if len(word_array) > page*per_page:
            keyboard.append([
                InlineKeyboardButton("<<", callback_data=f"page_{callback}{page-1}"),
                InlineKeyboardButton(">>", callback_data=f"page_{callback}{page+1}")
            ])
        else:
            keyboard.append([InlineKeyboardButton("<<", callback_data=f"page_{callback}{page-1}")])
    keyboard.append([InlineKeyboardButton(text=BACK, callback_data=str(END))])
    return InlineKeyboardMarkup(keyboard)


async def presentation_language_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_language_"):
        page = int(data.replace("page_language_", ""))
    text = "Taqdimotingiz tilini tanlang:"
    reply_markup = await generate_keyboard(page, LANGUAGES, LANGUAGES_EMOJI, "language_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def abstract_language_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_language_"):
        page = int(data.replace("page_language_", ""))
    text = "Tezisingiz tilini tanlang:"
    reply_markup = await generate_keyboard(page, LANGUAGES, LANGUAGES_EMOJI, "language_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def presentation_template_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_template_"):
        page = int(data.replace("page_template_", ""))
    else:
        context.user_data[PRESENTATION_LANGUAGE_CHOICE] = data
    text = "Taqdimotingiz shablonini tanlang:"
    reply_markup = await generate_keyboard(page, TEMPLATES, TEMPLATES_EMOJI, "template_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def presentation_type_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_type_"):
        page = int(data.replace("page_type_", ""))
    else:
        context.user_data[TEMPLATE_CHOICE] = data
    text = "Taqdimotingiz turini tanlang:"
    reply_markup = await generate_keyboard(page, TYPES, TYPES_EMOJI, "type_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def abstract_type_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_type_"):
        page = int(data.replace("page_type_", ""))
    else:
        context.user_data[ABSTRACT_LANGUAGE_CHOICE] = data
    text = "Tezis turini tanlang:"
    reply_markup = await generate_keyboard(page, TYPES, TYPES_EMOJI, "type_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def presentation_slide_count_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    page = 1
    if data.startswith("page_slide_count_"):
        page = int(data.replace("page_slide_count_", ""))
    else:
        context.user_data[PRESENTATION_TYPE_CHOICE] = data
    text = "Taqdimotingiz uchun slaydlarning taxminiy sonini tanlang:"
    reply_markup = await generate_keyboard(page, COUNTS, COUNTS_EMOJI, "slide_count_")
    await query.answer()
    await query.edit_message_text(text=text, reply_markup=reply_markup)
    return SELECTING_MENU


async def presentation_topic_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    text =("<b>Taqdimot mavzusi kiriting:</b>"
    "\n\n <b>Muhim❗️:</b>"
    "\n\n1. Men ingliz tilida kiritilgan mavzularni yaxshi tushunaman."
    "\n2. Ingliz tiliga tarjima qilinganda ma'nosi o'zgarishi mumkin bo'lgan mavzularni kiritmaslikka harakat qiling."
    "\n3. Mavzu qaysi tilda kiritilishidan qat'iy nazar, tanlangan til asosida taqdimot yarataman."
    "\n4. Har bir mavzuga umumiy qarayman. Qaysidir tor doirada berilgan mavzularni kiritishda ularni aniqroq izohlashga harakat qiling."
    "\n5. Men butun dunyo ma'lumotlari asosida taqdimot tayyorlayman. Agar O'zbekistonga oid ma'lumot kerak bo'lsa, mavzuni kiritishda davlat nomini ham kiritgan ma'qul."
    "\n6. Shaxslar tog'risida taqdimot yaratishda, shaxs haqida aniqroq ma'lumot berishga urinib ko'ring."
    "\n7. Qisqartma so'zlarga, imloviy xato so'zlarga tushunmasligim mumkin."
    "\n ❗️ Agar kiritilgan mavzuga tushunmasam boshqa mavzuga chalg'ib ketishim ehtimoli mavjud. Iltimos, mavzuni tasvirlashda e'tiborli bo'ling!")
    context.user_data[COUNT_SLIDE_CHOICE] = data
    await query.answer()
    await query.edit_message_text(text=text, parse_mode=ParseMode.HTML)
    if MESSAGE_ID in context.chat_data:
        del context.chat_data[MESSAGE_ID]
    return INPUT_TOPIC


async def abstract_topic_callback(update: Update, context: CallbackContext) -> str:
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    query = update.callback_query
    data = query.data
    text =("<b>Tezis mavzusi kiriting:</b>"
    "\n\n <b>Muhim❗️:</b>"
    "\n\n1. Men ingliz tilida kiritilgan mavzularni yaxshi tushunaman."
    "\n2. Ingliz tiliga tarjima qilinganda ma'nosi o'zgarishi mumkin bo'lgan mavzularni kiritmaslikka harakat qiling."
    "\n3. Mavzu qaysi tilda kiritilishidan qat'iy nazar, tanlangan til asosida tezis yarataman."
    "\n4. Har bir mavzuga umumiy qarayman. Qaysidir tor doirada berilgan mavzularni kiritishda ularni aniqroq izohlashga harakat qiling."
    "\n5. Men butun dunyo ma'lumotlari asosida tezis tayyorlayman. Agar O'zbekistonga oid ma'lumot kerak bo'lsa, mavzuni kiritishda davlat nomini ham kiritish tavsiya qilinadi."
    "\n6. Shaxslar tog'risida taqdimot yaratishda, shaxs haqida aniqroq ma'lumot berishga urinib ko'ring."
    "\n7. Qisqartma so'zlarga, imloviy xato so'zlarga tushunmasligim mumkin."
    "\n ❗️ Agar kiritilgan mavzuga tushunmasam boshqa mavzuga chalg'ib ketishim ehtimoli mavjud. Iltimos, mavzuni tasvirlashda e'tiborli bo'ling!")
    
    context.user_data[ABSTRACT_TYPE_CHOICE] = data
    await query.answer()
    await query.edit_message_text(text=text, parse_mode=ParseMode.HTML)
    if MESSAGE_ID in context.chat_data:
        del context.chat_data[MESSAGE_ID]
    return INPUT_TOPIC


async def auto_generate_presentation(update: Update, context: CallbackContext, user_id, message_id, prompt, template_choice):
    notification_message = await update.message.reply_text("⌛", reply_to_message_id=message_id)
    try:
        response, n_used_tokens = await openai_utils.process_prompt(prompt)
    except OverflowError:
        await notification_message.delete()
        await update.message.reply_text(text="Tizim hozirda haddan tashqari band. Iltimos, keyinroq qayta urinib ko'ring. 😊",
                                        reply_to_message_id=message_id)
        return END
    except RuntimeError:
        await notification_message.delete()
        await update.message.reply_text(text="Qandaydir xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 😊",
                                        reply_to_message_id=message_id)
        return END
    except ValueError:
        await notification_message.delete()
        await update.message.reply_text(text="Taqdimotingiz juda katta. Iltimos, qayta urinib ko'ring. 😊",
                                        reply_to_message_id=message_id)
        return END
    available_tokens = db.get_user_attribute(user_id, "n_available_tokens")
    db.set_user_attribute(user_id, "n_available_tokens", available_tokens - n_used_tokens)
    used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    db.set_user_attribute(user_id, "n_used_tokens", n_used_tokens + used_tokens)
    pptx_bytes, pptx_title = await presentation.generate_ppt(response, template_choice)
    await update.message.reply_document(document=pptx_bytes, filename=pptx_title)
    await notification_message.delete()


async def presentation_save_input(update: Update, context: CallbackContext):
    if update.edited_message is not None:
        return
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_data = context.user_data
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    topic_choice = update.message.text
    user_mode = db.get_user_attribute(user_id, "current_chat_mode")
    language_choice = user_data[PRESENTATION_LANGUAGE_CHOICE].replace("language_", "")
    template_choice = user_data[TEMPLATE_CHOICE].replace("template_", "")
    type_choice = user_data[PRESENTATION_TYPE_CHOICE].replace("type_", "")
    count_slide_choice = user_data[COUNT_SLIDE_CHOICE].replace("slide_count_", "")
    prompt = await presentation.generate_ppt_prompt(language_choice, type_choice, count_slide_choice, topic_choice)
    if user_mode == "auto":
        available_tokens = db.get_user_attribute(user_id, "n_available_tokens")
        if available_tokens > 0:
            loop = asyncio.get_event_loop()
            loop.create_task(auto_generate_presentation(update, context, user_id, message_id, prompt, template_choice))
        else:
            await update.message.reply_text("Tokenlaringiz yetarli emas."
                                            "\n\Iltimos, balansingizni to'ldiring. Balansni to'ldirish uchun - /balansni_toldirish buyrug'ini kiriting.")
    else:
        try:
            await update.message.reply_text(text="`" + prompt + "`", parse_mode=ParseMode.MARKDOWN_V2)
        except telegram.error.BadRequest:
            await update.message.reply_text("Kiritilgan ma'lumotlarni tekshiring va mavzuni qayta kiriting😊")
            return INPUT_TOPIC
        await update.message.reply_text(text="1) Bundan oldingi xabarni ko'rsatma bilan nusxalang va qayta ishlang😊"
                                             "\n2) Qayta ishlangan so'rovning javobidan nusxa oling va uni chatga joylashtiring😊"
                                             "\n\nTavsiya etilgan veb-saytlar:",
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton(text='Poe', url='https://poe.com/ChatGPT')],
                                            [InlineKeyboardButton(text='Chat OpenAI', url='https://chat.openai.com/')],
                                        ]))
        return INPUT_PROMPT
    return END


async def auto_generate_abstract(update: Update, context: CallbackContext, user_id, message_id, prompt):
    notification_message = await update.message.reply_text("⌛", reply_to_message_id=message_id)
    try:
        response, n_used_tokens = await openai_utils.process_prompt(prompt)
    except OverflowError:
        await notification_message.delete()
        await update.message.reply_text(text="Tizim hozirda haddan tashqari band. Iltimos, keyinroq qayta urinib ko'ring. 😊",
                                        reply_to_message_id=message_id)
        return END
    except RuntimeError:
        await notification_message.delete()
        await update.message.reply_text(text="Qandaydir xatolik yuz berdi. Iltimos, qayta urinib ko'ring. 😊",
                                        reply_to_message_id=message_id)
        return END
    except ValueError:
        await notification_message.delete()
        await update.message.reply_text(text="Tezisingiz juda katta. Iltimos, qayta urinib ko'ring😊",
                                        reply_to_message_id=message_id)
        return END
    available_tokens = db.get_user_attribute(user_id, "n_available_tokens")
    db.set_user_attribute(user_id, "n_available_tokens", available_tokens - n_used_tokens)
    used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    db.set_user_attribute(user_id, "n_used_tokens", n_used_tokens + used_tokens)
    docx_bytes, docx_title = await abstract.generate_docx(response)
    await update.message.reply_document(document=docx_bytes, filename=docx_title)
    await notification_message.delete()


async def abstract_save_input(update: Update, context: CallbackContext):
    if update.edited_message is not None:
        return
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_data = context.user_data
    user_id = update.message.from_user.id
    message_id = update.message.message_id
    topic_choice = update.message.text
    user_mode = db.get_user_attribute(user_id, "current_chat_mode")
    language_choice = user_data[ABSTRACT_LANGUAGE_CHOICE].replace("language_", "")
    type_choice = user_data[ABSTRACT_TYPE_CHOICE].replace("type_", "")
    prompt = await abstract.generate_docx_prompt(language_choice, type_choice, topic_choice)
    if user_mode == "auto":
        available_tokens = db.get_user_attribute(user_id, "n_available_tokens")
        if available_tokens > 0:
            loop = asyncio.get_event_loop()
            loop.create_task(auto_generate_abstract(update, context, user_id, message_id, prompt))
        else:
            await update.message.reply_text("Tokenlaringiz yetarli emas😊")
    else:
        try:
            await update.message.reply_text(text="`" + prompt + "`", parse_mode=ParseMode.MARKDOWN_V2)
        except telegram.error.BadRequest:
            await update.message.reply_text("Kiritilgan maʼlumotlarni va kiritilgan mavzuni yana tekshiring😊")
            return INPUT_TOPIC
        await update.message.reply_text(text="1) Bundan oldingi xabarni ko'rsatma bilan nusxalang va qayta ishlang😊"
                                             "\n2) Qayta ishlangan so'rovning javobidan nusxa oling va uni chatga joylashtiring😊"
                                             "\n\nTavsiya etilgan veb-saytlar:",
                                        reply_markup=InlineKeyboardMarkup([
                                            [InlineKeyboardButton(text='Poe', url='https://poe.com/ChatGPT')],
                                            [InlineKeyboardButton(text='Chat OpenAI', url='https://chat.openai.com/')],
                                        ]))
        return INPUT_PROMPT
    return END


async def presentation_prompt_callback(update: Update, context: CallbackContext):
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
    await register_user_if_not_exists(update, context, update.message.from_user)
    api_response = update.message.text
    user_data = context.user_data
    template_choice = user_data[TEMPLATE_CHOICE].replace("template_", "")
    try:
        pptx_bytes, pptx_title = await presentation.generate_ppt(api_response, template_choice)
        await update.message.reply_document(document=pptx_bytes, filename=pptx_title)
    except IndexError:
        await update.message.reply_text("Kiritilgan maʼlumotlarni tekshiring va qayta urinib koʻring😊")
        return INPUT_PROMPT
    return END


async def abstract_prompt_callback(update: Update, context: CallbackContext):
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
    await register_user_if_not_exists(update, context, update.message.from_user)
    api_response = update.message.text
    try:
        docx_bytes, docx_title = await abstract.generate_docx(api_response)
        await update.message.reply_document(document=docx_bytes, filename=docx_title)
    except IndexError:
        await update.message.reply_text("Kiritilgan maʼlumotlarni tekshiring va qayta urinib koʻring😊")
        return INPUT_PROMPT
    return END


async def end_second_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Return to top level conversation."""
    context.user_data[START_OVER] = True
    await menu_handle(update, context)
    return END


async def show_balance_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    n_available_tokens = db.get_user_attribute(user_id, "n_available_tokens")

    text = f"🟢 Sizda <b>{n_available_tokens}</b> token mavjud\n"
    text += f"🔴 Siz <b>{n_used_tokens}</b> token ishlatdingiz\n\n"
    text += f"💰 Balansni to'ldirish uchun <b>/balansni_toldirish</b> buyrog'ini kiriting.\n\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    
async def balansni_toldirish(update: Update, context: CallbackContext):
    instruction0 = (
        "*Tariflar:*"
        "\n\n 2000 token - *2000 so\'m.*"
        "\n 5000 token - *4000 so\'m.*"
        "\n 7000 token - *6000 so\'m.*"
        "\n 10000 token - *8000 so\'m.*"
        "\n\n *1800 token evaziga 15 ta sahifa (list)dan tashkil topdan toʼliq bir taqdimot yaratish mumkin.*"
    )
    instruction1 = (
        "Balansni to\'ldirish uchun quyidagi toʼlov kartalridan biriga to\'lov qiling:\n"
        "_Nusxa olish uchun raqamlar ustiga bosing._ \n\n"
        "💳 Karta Raqami: `9860190112621585`"
        "\n 👤 Karta egasi: Umidjon Azamkulov\n\n"
        "💳 Karta Raqami: `9860606736003199`"
        "\n👤 Karta egasi: Azamkulov Umidjon"
    )

    instruction2 = (
        "*❗️Eslatmalar*\n\n"
        "1.To\'lov chekisiz balansingiz to\'ldirilmaydi. Chekni albatta yuboring.\n"
        "2.Chekni inson tekshiradi. Shuning uchun biroz vaqt oladi. \n"
        "3.Chekda To\'lov vaqti ko\'rinmagan, yoki aniq ko\'rinmagan bo\'lsa, to\'lov qabul qilinmaydi \n"
        "4. Faqatgina Tariflar bo\'limida keltirilgan mablag\' miqdorida to\'lov qiling, Agarda mab\'lag\' tariflardagi miqdordan ko\'p bo\'lsa, eng yaqin ekvivaliyent ta\'rif tanlanadi. \n"
        "Bunday holatda bo\'lsangiz qo\'shimcha to\'lov qiling va adminga murojaat qiling.\n"
    )

    # Send both sets of instructions
    await update.message.reply_text(instruction1, parse_mode=ParseMode.MARKDOWN)
    await update.message.reply_text(instruction2, parse_mode=ParseMode.MARKDOWN)

    # Send the instruction message with the inline keyboard
    await update.message.reply_text(
        "*To\'lov qilish qadamlari:*\n\n"
        "1. *TO\'LOV:* Ko\'rsatilgan karta raqamlaridan biriga to\'lov qiling.\n"
        "2. *SAQLASH:* To\'lov chekini rasmga oling, yoki chek faylini saqlab oling. \n"
        "3. *BUYRUQ:* Pastdagi *Chekni yuborish* tugmasini bosing \n"
        "4. *YUBORISH:* To\'lov chekining rasmini yoki faylini botga yuboring. \n"
        "5. *YAKUN:* Biz chekni tekshirgandan so\'ng hisobingizni to\'ldiramiz.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Chekni yuborish", callback_data="payment_receipt")]]
        ),
    )

# Define callback handler to handle payment receipt submission button click
async def handle_payment_receipt_button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback
    if query.data == "payment_receipt":  
      await update.effective_message.reply_text("To'lov chekini rasmini yuboring (jpg yoki pdf formatida)")

# Define message handler to handle payment receipt submission
async def handle_payment_receipt(update: Update, context: CallbackContext):
    # Assuming the payment receipt is submitted as a photo or document
    # You may need to adjust this based on your specific use case
    if update.message.photo or update.message.document:
        # Forward the receipt to the admin for approval
        await update.message.forward(chat_id=config.admin_chat_id)
        # Send the payment receipt to the admin with "Approve" and "Reject" inline buttons
        await context.bot.send_message(
            chat_id=config.admin_chat_id,
            text="To'lov chekini tasdiqlang yoki rad eting:",
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("Tasdiqlash", callback_data="approve"),
                    InlineKeyboardButton("Rad etish", callback_data="reject")
                ]
            ])
        )
        
        await update.message.reply_text("To'lov cheki qabul qilindi. Admin tasdiqlashni kuting.")

    else:
        await update.message.reply_text("To'lov chekini rasmini yuboring (jpg yoki pdf formatida)")

# Define callback handler to handle admin actions
async def handle_admin_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    message_id = query.message.message_id  # Get the message ID to delete the message later
    if query.data == "approve":
        # Admin approves the payment receipt
        await query.answer("To'lov tasdiqlandi. Token miqdorini tanlang:")
        await query.message.reply_text(
            "Token miqdorini tanlang:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("2000", callback_data="token_amount|2000")],
                [InlineKeyboardButton("5000", callback_data="token_amount|5000")],
                [InlineKeyboardButton("7000", callback_data="token_amount|7000")],
                [InlineKeyboardButton("10000", callback_data="token_amount|10000")],
            ])
        )
    elif query.data == "reject":
        # Admin rejects the payment receipt
        await query.answer("To'lov rad etildi.")
        # Notify the user who made the payment about the rejection
        await update.effective_user.send_message("Sizning to'lovingiz rad etildi. Iltimos, qaytadan urinib ko'ring.")

    # Delete the message after processing
    try:
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
    except telegram.error.BadRequest:
        # Message might have already been deleted or is inaccessible
        pass

# Define callback handler to handle token amount selection
# Define callback handler to handle token amount selection
async def handle_token_amount_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    token_amount = int(query.data.split("|")[1])
    user_id = query.from_user.id
    n_available_tokens = db.get_user_attribute(user_id, "n_available_tokens")
    db.set_user_attribute(user_id, "n_available_tokens", n_available_tokens + token_amount)
    await query.answer("Tokenlar muvaffaqiyatli qo'shildi")
    
    # Delete the message containing token amount selection options
    await query.message.delete()

    # Send a message to the user who made the payment
    await update.effective_user.send_message(f"{token_amount} tokenlar sizning balansingizga muvaffaqiyatli qo'shildi.")

    # Delete the message from the admin chat
    try:
        await context.bot.delete_message(chat_id=query.message.chat_id, message_id=query.message.message_id)
    except telegram.error.BadRequest:
        # Message might have already been deleted or is inaccessible
        pass

async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲 Afsuski, xabar <b>editing</b> qo'llab quvvatlanmadi"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)


async def error_handle(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    # send error to the chat for test
    try:
        # collect error message
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = "".join(tb_list)
        update_str = update.to_dict() if isinstance(update, Update) else str(update)
        message = (
            f"An exception was raised while handling an update\n"
            f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
            "</pre>\n\n"
            f"<pre>{html.escape(tb_string)}</pre>"
        )

        # split text into multiple messages due to 4096 character limit
        for message_chunk in split_text_into_chunks(message, 4096):
            try:
                await context.bot.send_message(update.effective_chat.id, message_chunk, parse_mode=ParseMode.HTML)
            except telegram.error.BadRequest:
                # answer has invalid characters, so we send it without parse_mode
                await context.bot.send_message(update.effective_chat.id, message_chunk)
    except Exception:
        await context.bot.send_message(update.effective_chat.id, "Some error in error handler")


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .read_timeout(30)
        .write_timeout(20)
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )

    # add handlers
    if len(config.allowed_telegram_usernames) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.allowed_telegram_usernames)

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))

    application.add_handler(MessageHandler(filters.COMMAND & user_filter, message_handle), group=2)

    application.add_handler(CommandHandler("mode", show_chat_modes_handle, filters=user_filter))
    application.add_handler(CallbackQueryHandler(set_chat_mode_handle, pattern="^set_chat_mode"))

    presentation_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(presentation_language_callback, pattern=f"^{PRESENTATION}$")],
        states={
            SELECTING_MENU: [
                CallbackQueryHandler(presentation_language_callback, pattern="^page_language_"),
                CallbackQueryHandler(presentation_template_callback, pattern="^language_"),
                CallbackQueryHandler(presentation_template_callback, pattern="^page_template_"),
                CallbackQueryHandler(presentation_type_callback, pattern="^template_"),
                CallbackQueryHandler(presentation_type_callback, pattern="^page_type_"),
                CallbackQueryHandler(presentation_slide_count_callback, pattern="^type_"),
                CallbackQueryHandler(presentation_slide_count_callback, pattern="^page_slide_count_"),
                CallbackQueryHandler(presentation_topic_callback, pattern="^slide_count_"),
                             ],
            INPUT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, presentation_save_input)],
            INPUT_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, presentation_prompt_callback)],
        },
        fallbacks=[
            CallbackQueryHandler(end_second_level, pattern=f"^{str(END)}$"),
            CommandHandler("menu", menu_handle, filters=user_filter)
        ],
        map_to_parent={
            END: SELECTING_ACTION,
            SELECTING_ACTION: SELECTING_ACTION,
        },
        allow_reentry=True,
    )

    abstract_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(abstract_language_callback, pattern=f"^{ABSTRACT}$")],
        states={
            SELECTING_MENU: [
                CallbackQueryHandler(abstract_language_callback, pattern="^page_language_"),
                CallbackQueryHandler(abstract_type_callback, pattern="^language_"),
                CallbackQueryHandler(abstract_type_callback, pattern="^page_type_"),
                CallbackQueryHandler(abstract_topic_callback, pattern="^type_")
                             ],
            INPUT_TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, abstract_save_input)],
            INPUT_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, abstract_prompt_callback)],
        },
        fallbacks=[
            CallbackQueryHandler(end_second_level, pattern=f"^{str(END)}$"),
            CommandHandler("menu", menu_handle, filters=user_filter)
        ],
        map_to_parent={
            END: SELECTING_ACTION,
            SELECTING_ACTION: SELECTING_ACTION,
        },
        allow_reentry=True,
    )

    selection_handlers = [
        presentation_conv,
        abstract_conv,
    ]

    menu_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("menu", menu_handle, filters=user_filter)],
        states={
            SELECTING_ACTION: selection_handlers,
        },
        fallbacks=[
            CommandHandler("menu", menu_handle, filters=user_filter)
        ],
    )
    application.add_handler(menu_conv_handler)

    application.add_handler(CommandHandler("balance", show_balance_handle, filters=user_filter))
# Add command handlers to the application
    application.add_handler(CommandHandler("balansni_toldirish", balansni_toldirish))
    
# Add callback handler to handle payment receipt button click
    application.add_handler(CallbackQueryHandler(handle_payment_receipt_button, pattern="payment_receipt"))

# Add message handler to handle payment receipt submission
    application.add_handler(MessageHandler(None, handle_payment_receipt))

# Add callback handler to handle admin approval and rejection
    application.add_handler(CallbackQueryHandler(handle_admin_actions, pattern="^(approve|reject)"))

# Add callback handler to handle token amount selection
    application.add_handler(CallbackQueryHandler(handle_token_amount_selection, pattern="^token_amount"))



    
    application.add_error_handler(error_handle)

    application.run_polling()


if __name__ == "__main__":
    run_bot()
