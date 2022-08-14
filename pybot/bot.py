# pylint: disable=unused-argument, wrong-import-position
import logging
import os
import html
import requests
import json
import traceback

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, \
    ConversationHandler, ContextTypes, filters

from notion_helper import get_channels

CHOOSE_CHANNEL_PREFIX = "choose_channel:"

CHOOSE_CHANNEL, WRITE_YOUR_REQUEST = range(2)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text("Доступные команды: /start, /help, /my_channels, /post.")


async def show_my_channels(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Shows all user's channels with invite links."""
    channels = get_channels(update.message.from_user.username)
    context.user_data['channels'] = channels

    if len(channels) == 0:
        await update.message.reply_text("У вас пока нет доступов к каналам")
    else:
        channel_names = [f'\n<a href="{c.url}">{c.name}</a>' for c in channels]
        await update.message.reply_text("Доступные вам каналы:" + ''.join(channel_names), parse_mode='HTML')


async def choose_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Sends a message with channel options."""
    channels = get_channels(update.message.from_user.username)
    context.user_data['channel_urls'] = {c.id: c.url for c in channels}

    if len(channels) == 0:
        await update.message.reply_text("Вы пока не можете постить запросы в каналы")
        return -1
    else:
        keyboard = [
            [InlineKeyboardButton(f'{c.name}', callback_data=CHOOSE_CHANNEL_PREFIX + str(c.id))]
            for c in channels]

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Выберите канал для отправки запроса:", reply_markup=reply_markup)

        return CHOOSE_CHANNEL


async def write_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    channel_id = query.data[len(CHOOSE_CHANNEL_PREFIX):]
    context.user_data['channel_entry_id'] = channel_id
    channel_info = await context.bot.getChat(chat_id=channel_id)
    channel_url = context.user_data['channel_urls'][int(channel_id)]

    await query.edit_message_text(
        text=f'Напечатайте запрос, который вы хотите отправить в канал '
             f'\n<a href="{channel_url}">{channel_info.title}</a>',
        parse_mode="HTML")

    return WRITE_YOUR_REQUEST


async def post_to_channel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    channel_id = context.user_data['channel_entry_id']
    channel_text = update.message.text

    await context.bot.send_message(
        channel_id,
        f'Запрос от @{update.message.from_user.username}' + '\n\n' + channel_text,
        parse_mode='HTML',
        disable_web_page_preview=True,
    )

    await update.message.reply_text("Ваш запрос отправлен в канал")

    return -1


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: add logging and notification to dev channel
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    print(tb_string)

    return -1


def main() -> None:
    """Run the bot."""
    application = Application.builder().token(os.environ['BOT_TOKEN']).build()

    msg_filter = filters.TEXT & filters.ChatType.PRIVATE
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", help_command),
            CommandHandler("help", help_command),
            CommandHandler("my_channels", show_my_channels),
            CommandHandler("post", choose_channel),
        ],
        states={
            CHOOSE_CHANNEL: [
                CallbackQueryHandler(write_request, pattern=CHOOSE_CHANNEL_PREFIX)
            ],
            WRITE_YOUR_REQUEST: [
                MessageHandler(msg_filter, post_to_channel)
            ],
        },
        fallbacks=[
            CommandHandler("start", help_command),
            CommandHandler("help", help_command),
            CommandHandler("my_channels", show_my_channels),
            CommandHandler("post", choose_channel),
            MessageHandler(msg_filter, help_command)
        ]
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error_handler)

    # Run the bot until the user presses Ctrl-C
    application.run_polling()


if __name__ == "__main__":
    main()
