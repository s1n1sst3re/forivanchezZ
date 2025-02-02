import logging
import json
from datetime import datetime, timedelta
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

API_TOKEN = "8138057398:AAGLnW9nSQ4s6GDpWcICYWqru8e4OHB-1Z0"
CHANNEL_ID = "-1002427749393"
CHANNEL_USERNAME = "OTBROSGK"  # Публичное имя канала
OPERATOR_USER_ID = 7620008618
MESSAGE_COOLDOWN = timedelta(minutes=30)
ADMIN_MESSAGE_COOLDOWN = timedelta(hours=1)
USER_DATA_FILE = "user_data.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class UserManager:
    def __init__(self):
        self.user_data = self._load_data()

    def _load_data(self):
        try:
            with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for user in data["users"].values():
                    user.setdefault("agreed", False)
                    user.setdefault("last_message_time", None)
                    user.setdefault("last_admin_message_time", None)
                if "pending_messages" not in data:
                    data["pending_messages"] = {}
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            return {"users": {}, "last_number": 0, "pending_messages": {}}

    def _save_data(self):
        with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.user_data, f, ensure_ascii=False, indent=4)

    def get_user_info(self, user_id: int) -> dict:
        str_id = str(user_id)
        if str_id not in self.user_data["users"]:
            self.user_data["last_number"] += 1
            self.user_data["users"][str_id] = {
                "number": self.user_data["last_number"],
                "messages_sent": 0,
                "agreed": False,
                "last_message_time": None,
                "last_admin_message_time": None,
                "created_at": datetime.now().isoformat()
            }
            self._save_data()
        return self.user_data["users"][str_id]

    def increment_message_count(self, user_id: int):
        user = self.get_user_info(user_id)
        user["messages_sent"] += 1
        self._save_data()

    def set_agreed(self, user_id: int):
        user = self.get_user_info(user_id)
        user["agreed"] = True
        self._save_data()

    def set_last_message_time(self, user_id: int, time: datetime):
        user = self.get_user_info(user_id)
        user["last_message_time"] = time.isoformat()
        self._save_data()

    def set_last_admin_message_time(self, user_id: int, time: datetime):
        user = self.get_user_info(user_id)
        user["last_admin_message_time"] = time.isoformat()
        self._save_data()

    def get_last_message_time(self, user_id: int) -> datetime | None:
        user = self.get_user_info(user_id)
        if user["last_message_time"]:
            return datetime.fromisoformat(user["last_message_time"])
        return None

    def get_last_admin_message_time(self, user_id: int) -> datetime | None:
        user = self.get_user_info(user_id)
        if user["last_admin_message_time"]:
            return datetime.fromisoformat(user["last_admin_message_time"])
        return None

    def add_pending_message(self, user_id: int, message_type: str, content: str, caption: str = None):
        str_id = str(user_id)
        self.user_data["pending_messages"][str_id] = {
            "type": message_type,
            "content": content,
            "caption": caption,
            "timestamp": datetime.now().isoformat()
        }
        self._save_data()

    def get_pending_message(self, user_id: int):
        str_id = str(user_id)
        return self.user_data["pending_messages"].get(str_id)

    def remove_pending_message(self, user_id: int):
        str_id = str(user_id)
        if str_id in self.user_data["pending_messages"]:
            del self.user_data["pending_messages"][str_id]
            self._save_data()

user_manager = UserManager()

def main_keyboard():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Отправить сообщение"), KeyboardButton("Создать обращение админу")],
        [KeyboardButton("Личный кабинет")]
    ], resize_keyboard=True)

FAQ_TEXT = """
Добро пожаловать!
❗️ Запрещено:
- Оскорбление Власти    
- Оскорбление учителей
- Другие виды некорректного поведения.
За всё написанное вами несёте ответственность только ВЫ. См конституцию РФ [здесь](http://kremlin.ru/acts/constitution).
Нажмите "Ознакомлен(а) ✅", чтобы продолжить использование бота.
"""

async def send_main_menu(update: Update, text: str):
    if update.message:
        await update.message.reply_text(text, reply_markup=main_keyboard())
    elif update.callback_query:
        await update.callback_query.message.reply_text(text, reply_markup=main_keyboard())

def format_user_tag(user_id: int) -> str:
    user_info = user_manager.get_user_info(user_id)
    return f"#отброс{user_info['number']}"

async def check_agreement(update: Update) -> bool:
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    if not user_info["agreed"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ознакомлен(а) ✅", callback_data=f"agree:{user_id}")]
        ])
        await update.message.reply_markdown(FAQ_TEXT, reply_markup=keyboard)
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    
    if not user_info["agreed"]:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Ознакомлен(а) ✅", callback_data=f"agree:{user_id}")]
        ])
        await update.message.reply_markdown(FAQ_TEXT, reply_markup=keyboard)
    else:
        await send_main_menu(update, "Главное меню:")

async def handle_agreement(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    _, user_id = query.data.split(":")
    if int(user_id) != query.from_user.id:
        await query.message.edit_text("⚠️ Ошибка авторизации!")
        return
    
    user_manager.set_agreed(int(user_id))
    await query.message.edit_text("✅ Вы успешно подтвердили правила!")
    await send_main_menu(update, "Главное меню:")

async def handle_message_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_agreement(update):
        return
    
    user_id = update.effective_user.id
    last_time = user_manager.get_last_message_time(user_id)
    
    if last_time and (datetime.now() - last_time) < MESSAGE_COOLDOWN:
        remaining = MESSAGE_COOLDOWN - (datetime.now() - last_time)
        await update.message.reply_text(
            f"⏳ Вы можете отправить следующее сообщение через {remaining.seconds//60} минут.",
            reply_markup=main_keyboard()
        )
        return
    
    context.user_data["awaiting_message"] = True
    await update.message.reply_text(
        "📝 Отправьте ваше сообщение (текст, фото или видео) для публикации:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True)
    )

async def handle_admin_request_btn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_agreement(update):
        return
    
    user_id = update.effective_user.id
    last_time = user_manager.get_last_admin_message_time(user_id)
    
    if last_time and (datetime.now() - last_time) < ADMIN_MESSAGE_COOLDOWN:
        remaining = ADMIN_MESSAGE_COOLDOWN - (datetime.now() - last_time)
        hours = remaining.seconds // 3600
        minutes = (remaining.seconds % 3600) // 60
        await update.message.reply_text(
            f"⏳ Вы можете отправить следующее обращение через {hours} часов и {minutes} минут.",
            reply_markup=main_keyboard()
        )
        return
    
    context.user_data["awaiting_admin_message"] = True
    await update.message.reply_text(
        "📨 Введите ваше обращение к администратору:",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("❌ Отмена")]], resize_keyboard=True)
    )

async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_agreement(update):
        return
    
    user_id = update.effective_user.id
    
    if context.user_data.get("awaiting_message"):
        message_type = None
        content = None
        caption = None

        if update.message.text:
            message_type = "text"
            content = update.message.text
        elif update.message.photo:
            message_type = "photo"
            content = update.message.photo[-1].file_id
            caption = update.message.caption
        elif update.message.video:
            message_type = "video"
            content = update.message.video.file_id
            caption = update.message.caption

        if message_type:
            user_manager.add_pending_message(user_id, message_type, content, caption)
            context.user_data["awaiting_message"] = False
            
            preview_text = "✉️ Подтвердите отправку в канал:\n\n"
            if caption:
                preview_text += f"Подпись: {caption}\n"
            
            await update.message.reply_text(
                preview_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Подтвердить", callback_data="confirm_yes"),
                     InlineKeyboardButton("Отмена", callback_data="confirm_no")]
                ])
            )
        else:
            await update.message.reply_text("⚠️ Поддерживаются только текст, фото и видео!")

    elif context.user_data.get("awaiting_admin_message"):
        message_text = update.message.text
        if not message_text.strip():
            await update.message.reply_text("⚠️ Сообщение не может быть пустым!")
            return
        
        try:
            user_tag = format_user_tag(user_id)
            await context.bot.send_message(
                chat_id=OPERATOR_USER_ID,
                text=f"🚨 Обращение от {user_tag}:\n\n{message_text}"
            )
            user_manager.set_last_admin_message_time(user_id, datetime.now())
            await update.message.reply_text("✅ Ваше обращение отправлено администратору!", reply_markup=main_keyboard())
        except Exception as e:
            logger.error(f"Ошибка отправки: {e}")
            await update.message.reply_text("⚠️ Ошибка отправки обращения!", reply_markup=main_keyboard())
        
        # Сбрасываем состояние
        context.user_data.pop("awaiting_admin_message", None)

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_yes":
        user_id = query.from_user.id
        pending = user_manager.get_pending_message(user_id)
        
        if pending:
            if pending['type'] == 'text':
                user_tag = format_user_tag(user_id)
                try:
                    # Новый формат для текста
                    text = f"Новое анонимное сообщение от {user_tag}\n\n{pending['content']}"
                    sent_message = await context.bot.send_message(
                        chat_id=CHANNEL_ID,
                        text=text
                    )
                    # Новая ссылка на сообщение
                    message_link = f"https://t.me/{CHANNEL_USERNAME}/{sent_message.message_id}"
                    user_manager.increment_message_count(user_id)
                    user_manager.set_last_message_time(user_id, datetime.now())
                    await query.message.reply_text(f"✅ Сообщение опубликовано: {message_link}")
                except Exception as e:
                    logger.error(f"Ошибка публикации: {e}")
                    await query.message.reply_text("⚠️ Ошибка публикации!")
                finally:
                    user_manager.remove_pending_message(user_id)
                
            else:
                user_tag = format_user_tag(user_id)
                # Новый формат для медиа
                moderator_text = f"Новое анонимное сообщение от {user_tag}"
                if pending['caption']:
                    moderator_text += f"\n{pending['caption']}"
                
                try:
                    if pending['type'] == 'photo':
                        await context.bot.send_photo(
                            chat_id=OPERATOR_USER_ID,
                            photo=pending['content'],
                            caption=moderator_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_{user_id}"),
                                InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_{user_id}")
                            ]])
                        )
                    elif pending['type'] == 'video':
                        await context.bot.send_video(
                            chat_id=OPERATOR_USER_ID,
                            video=pending['content'],
                            caption=moderator_text,
                            reply_markup=InlineKeyboardMarkup([[
                                InlineKeyboardButton("✅ Одобрить", callback_data=f"moderate_approve_{user_id}"),
                                InlineKeyboardButton("❌ Отклонить", callback_data=f"moderate_reject_{user_id}")
                            ]])
                        )
                    
                    user_manager.set_last_message_time(user_id, datetime.now())
                    await query.message.reply_text("✅ Медиа отправлено на модерацию!")
                except Exception as e:
                    logger.error(f"Ошибка: {e}")
                    await query.message.reply_text("⚠️ Ошибка отправки медиа!")
                    user_manager.remove_pending_message(user_id)
            
            await send_main_menu(update, "Главное меню:")

        else:
            await query.message.reply_text("⚠️ Сообщение не найдено!")

    elif query.data == "confirm_no":
        user_manager.remove_pending_message(query.from_user.id)
        await query.message.reply_text("❌ Действие отменено.")
        await send_main_menu(update, "Главное меню:")

async def handle_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        data_parts = query.data.split('_')
        action = data_parts[1]
        user_id = int(data_parts[2])
        
        await query.message.edit_reply_markup(reply_markup=None)
        
        pending = user_manager.get_pending_message(user_id)
        if not pending:
            return

        user_info = user_manager.get_user_info(user_id)
        anonymous_tag = f"#отброс{user_info['number']}"

        if action == "approve":
            # Новый формат для канала
            if pending['type'] == 'text':
                text = f"Новое анонимное сообщение от {anonymous_tag}\n\n{pending['content']}"
                await context.bot.send_message(CHANNEL_ID, text=text)
            else:
                base_caption = f"Новое анонимное сообщение от {anonymous_tag}"
                caption = f"{base_caption}\n{pending['caption']}" if pending.get('caption') else base_caption
                
                if pending['type'] == 'photo':
                    await context.bot.send_photo(CHANNEL_ID, pending['content'], caption=caption)
                elif pending['type'] == 'video':
                    await context.bot.send_video(CHANNEL_ID, pending['content'], caption=caption)

            await context.bot.send_message(user_id, "✅ Ваше сообщение опубликовано в канале!")
            user_manager.increment_message_count(user_id)

        else:
            await context.bot.send_message(user_id, "❌ Ваше сообщение отклонено модератором.")

        user_manager.remove_pending_message(user_id)

    except Exception as e:
        logger.error(f"Ошибка модерации: {e}")
        await query.message.reply_text("⚠️ Произошла ошибка при обработке!")

async def handle_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_agreement(update):
        return
    
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    
    profile_text = (
        f"👤 Ваш личный кабинет:\n\n"
        f"🔢 Ваш номер: {user_info['number']}\n"
        f"📨 Отправлено сообщений: {user_info['messages_sent']}\n"
    )
    
    last_message_time = user_manager.get_last_message_time(user_id)
    if last_message_time:
        next_message_time = last_message_time
        profile_text += f"⏳ Следующее сообщение можно отправить через {remaining.seconds // 60} минут.\n"
    
    last_admin_message_time = user_manager.get_last_admin_message_time(user_id)
    if last_admin_message_time:
        next_admin_message_time = last_admin_message_time + ADMIN_MESSAGE_COOLDOWN
        if datetime.now() < next_admin_message_time:
            remaining = next_admin_message_time - datetime.now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            profile_text += f"⏳ Следующее обращение к администратору можно отправить через {hours} часов и {minutes} минут.\n"
    
    await update.message.reply_text(profile_text, reply_markup=main_keyboard())

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_agreement(update):
        return
    
    context.user_data.pop("awaiting_message", None)
    context.user_data.pop("awaiting_admin_message", None)
    await update.message.reply_text("❌ Действие отменено.", reply_markup=main_keyboard())

async def handle_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚠️ Неизвестная команда. Используйте кнопки ниже.", reply_markup=main_keyboard())

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}")
    if update and update.message:
        await update.message.reply_text("⚠️ Произошла ошибка. Пожалуйста, попробуйте позже.")

def main():
    application = Application.builder().token(API_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_agreement, pattern="^agree:"))
    application.add_handler(CallbackQueryHandler(handle_confirmation, pattern="^confirm_"))
    application.add_handler(CallbackQueryHandler(handle_moderation, pattern="^moderate_"))
    
    application.add_handler(MessageHandler(filters.Text(["Отправить сообщение"]), handle_message_btn))
    application.add_handler(MessageHandler(filters.Text(["Создать обращение админу"]), handle_admin_request_btn))
    application.add_handler(MessageHandler(filters.Text(["Личный кабинет"]), handle_profile))
    application.add_handler(MessageHandler(filters.Text(["❌ Отмена"]), handle_cancel))
    
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))
    application.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_user_message))
    
    application.add_handler(MessageHandler(filters.ALL, handle_unknown))
    
    application.add_error_handler(error_handler)
    
    logger.info("Бот запущен.")
    application.run_polling()

if __name__ == "__main__":
    main()