#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
IslamQuiz - телеграм-бот ислам туралы білімді тексеруге арналған.
Бот күнделікті сұрақтар жібереді, жауаптарды қабылдайды және ұпайларды есептейді.
"""

import json
import logging
import random
import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any

import pytz
from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Poll,
    ChatMemberUpdated,
    ChatMember,
    Message,
    User,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    PollAnswerHandler,
    ChatMemberHandler,
    CallbackQueryHandler,
    AIORateLimiter,
    JobQueue,
)

# Логгер баптау
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константалар
TOKEN = "YOUR_TOKEN_HERE"  # Ботыңыздың токенін осында орнатыңыз
# Астана уақыт белдеуі
TIMEZONE = pytz.timezone("Asia/Almaty")

# Сұрақтар базасын жүктеу
def load_questions() -> List[Dict]:
    """Сұрақтар базасын JSON файлынан жүктеу"""
    with open("questions.json", "r", encoding="utf-8") as file:
        questions = json.load(file)
    return questions

# Ұпайлар базасын жүктеу және сақтау
def load_scores() -> Dict:
    """Ұпайлар базасын JSON файлынан жүктеу"""
    try:
        with open("scores.json", "r", encoding="utf-8") as file:
            scores = json.load(file)
        return scores
    except FileNotFoundError:
        return {}

def save_scores(scores: Dict) -> None:
    """Ұпайлар базасын JSON файлына сақтау"""
    with open("scores.json", "w", encoding="utf-8") as file:
        json.dump(scores, file, ensure_ascii=False, indent=4)

# Бот командалары
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Бот бастау командасы"""
    user = update.effective_user
    
    welcome_text = (
        f"Ассаламу алейкум, {user.first_name}! 🌙\n\n"
        f"*IslamQuiz* ботына қош келдіңіз!\n\n"
        f"Бұл бот арқылы ислам дінінің әр түрлі салалары бойынша білімінізді тексере аласыз.\n\n"
        f"Күн сайын жаңа сұрақ жіберіледі. Дұрыс жауап бергеніңіз үшін ұпай аласыз.\n"
        f"Апта соңында ең көп ұпай жинағандар анықталады!\n\n"
        f"Бот командалары:\n"
        f"/quiz - арнайы сұрақ сұрату\n"
        f"/score - өз ұпайыңызды тексеру\n"
        f"/leaderboard - көшбасшылар тізімін көру\n\n"
        f"Бүгінгі сұраққа дайынсыз ба? 😊"
    )
    
    await update.message.reply_text(welcome_text, parse_mode=ParseMode.MARKDOWN)

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Арнайы сұрақ сұрату командасы"""
    questions = load_questions()
    question_data = random.choice(questions)
    
    await send_quiz(context, update.effective_chat.id, question_data)
    
    await update.message.reply_text(
        "Сізге арнайы сұрақ дайын! Жақсы бағың келсін! 🎯",
        parse_mode=ParseMode.MARKDOWN
    )

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пайдаланушының ұпайын көрсету"""
    user_id = str(update.effective_user.id)
    scores = load_scores()
    
    user_score = scores.get(user_id, {"total": 0, "weekly": 0})
    
    await update.message.reply_text(
        f"*Сіздің ұпайыңыз:*\n"
        f"Барлық ұпай: {user_score['total']}\n"
        f"Осы аптадағы ұпай: {user_score['weekly']}",
        parse_mode=ParseMode.MARKDOWN
    )

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Көшбасшылар тізімін көрсету"""
    scores = load_scores()
    
    # Апталық ұпайлар бойынша сұрыптау
    leaderboard_data = sorted(
        [(user_id, data["weekly"]) for user_id, data in scores.items()],
        key=lambda x: x[1],
        reverse=True
    )[:10]  # Тек 10 көшбасшы
    
    if not leaderboard_data:
        await update.message.reply_text(
            "Әзірше ешкім ұпай жинаған жоқ 🤷‍♂️",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = "*Апталық көшбасшылар:*\n\n"
    
    for i, (user_id, points) in enumerate(leaderboard_data, start=1):
        user_info = await context.bot.get_chat(int(user_id))
        username = user_info.first_name
        text += f"{i}. {username}: {points} ұпай\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# Сұрақтар жіберу логикасы
async def send_quiz(context: ContextTypes.DEFAULT_TYPE, chat_id: int, question_data: Dict) -> None:
    """Сұрақ жіберу"""
    question = question_data["question"]
    options = question_data["options"]
    correct_option_id = question_data["correct_option_id"]
    
    # Сұрақ жіберу (сауалнама түрінде)
    message = await context.bot.send_poll(
        chat_id=chat_id,
        question=question,
        options=options,
        type=Poll.QUIZ,
        correct_option_id=correct_option_id,
        is_anonymous=False,
        explanation=None,  # Түсіндірмені кейін жіберу
        open_period=86400,  # 24 сағат (86400 секунд)
        protect_content=True,
    )
    
    # Сұрақтың мәліметтерін сақтау
    context.bot_data.setdefault("polls", {})[message.poll.id] = {
        "chat_id": chat_id,
        "message_id": message.message_id,
        "question_data": question_data,
    }
    
    # 24 сағаттан кейін дұрыс жауапты және түсіндірмені жіберу үшін тапсырма қосу
    when = datetime.datetime.now(TIMEZONE) + datetime.timedelta(days=1)
    context.job_queue.run_once(
        send_explanation,
        when,
        data={
            "chat_id": chat_id,
            "poll_id": message.poll.id,
        },
        name=f"poll_{message.poll.id}",
    )

async def send_explanation(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Дұрыс жауап пен түсіндірмені жіберу"""
    job = context.job
    data = job.data
    
    chat_id = data["chat_id"]
    poll_id = data["poll_id"]
    
    poll_data = context.bot_data["polls"].get(poll_id)
    if not poll_data:
        return
    
    question_data = poll_data["question_data"]
    correct_option = question_data["options"][question_data["correct_option_id"]]
    explanation = question_data["explanation"]
    motivation = question_data["motivation"]
    
    text = (
        f"*Дұрыс жауап:* {correct_option}\n\n"
        f"*Түсіндірме:*\n{explanation}\n\n"
        f"{motivation}"
    )
    
    await context.bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.MARKDOWN,
    )

# Сауалнамаға жауаптарды өңдеу
async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сауалнамаға берілген жауаптарды өңдеу"""
    poll_answer = update.poll_answer
    poll_id = poll_answer.poll_id
    user_id = str(poll_answer.user.id)
    
    poll_data = context.bot_data.get("polls", {}).get(poll_id)
    if not poll_data:
        return
    
    question_data = poll_data["question_data"]
    selected_option = poll_answer.option_ids[0] if poll_answer.option_ids else -1
    correct_option = question_data["correct_option_id"]
    
    # Ұпайларды жаңарту
    scores = load_scores()
    user_data = scores.setdefault(user_id, {"total": 0, "weekly": 0})
    
    # Дұрыс жауап бергені үшін ұпай беру
    if selected_option == correct_option:
        user_data["total"] += 1
        user_data["weekly"] += 1
        save_scores(scores)

# Жаңа мүшелерді қарсы алу
async def greet_new_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Чатқа жаңадан қосылған мүшелерді қарсы алу"""
    result = extract_status_change(update.chat_member)
    if result is None:
        return
    
    was_member, is_member = result
    
    if not was_member and is_member:
        # Жаңа мүше чатқа қосылды
        new_member = update.chat_member.new_chat_member.user
        await update.effective_chat.send_message(
            f"Ассаламу алейкум, {new_member.first_name}! 🌙\n\n"
            f"*IslamQuiz* чатына қош келдіңіз!\n"
            f"Бүгінгі сұраққа жауап беруге дайынсыз ба?",
            parse_mode=ParseMode.MARKDOWN
        )

def extract_status_change(chat_member_update: ChatMemberUpdated) -> Optional[Tuple[bool, bool]]:
    """Мүшенің статусының өзгеруін анықтау көмекші функциясы"""
    status_change = chat_member_update.difference().get("status")
    old_is_member, new_is_member = chat_member_update.difference().get("is_member", (None, None))
    
    if status_change is None:
        return None
    
    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)
    
    return was_member, is_member

# Апта сайынғы рейтинг жариялау
async def weekly_results(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Апта сайынғы нәтижелерді жариялау"""
    # Барлық чаттарға жібереміз (чаттар тізімін жүйеде сақтау керек)
    # Бұл жерде мысал үшін тек бір чатқа жіберілуде
    chat_ids = context.bot_data.get("active_chats", [])
    
    if not chat_ids:
        return
    
    scores = load_scores()
    
    # Апталық ұпайлар бойынша сұрыптау
    leaderboard_data = sorted(
        [(user_id, data["weekly"]) for user_id, data in scores.items()],
        key=lambda x: x[1],
        reverse=True
    )[:5]  # Тек 5 үздік
    
    if not leaderboard_data:
        for chat_id in chat_ids:
            await context.bot.send_message(
                chat_id=chat_id,
                text="Бұл аптада ешкім ұпай жинаған жоқ 😔",
                parse_mode=ParseMode.MARKDOWN
            )
        return
    
    text = (
        "*Апталық нәтижелер!* 🏆\n\n"
        "Ең көп дұрыс жауап берген қатысушылар:\n\n"
    )
    
    for i, (user_id, points) in enumerate(leaderboard_data, start=1):
        user_info = await context.bot.get_chat(int(user_id))
        username = user_info.first_name
        
        if i == 1:
            text += f"🥇 {username}: {points} ұпай\n"
        elif i == 2:
            text += f"🥈 {username}: {points} ұпай\n"
        elif i == 3:
            text += f"🥉 {username}: {points} ұпай\n"
        else:
            text += f"{i}. {username}: {points} ұпай\n"
    
    text += "\nБарлық қатысушыларға рахмет! Жаңа аптада жаңа білім мен жаңа сұрақтар күтіңіздер! 📚"
    
    # Апталық нәтижелерді барлық чатқа жіберу
    for chat_id in chat_ids:
        await context.bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    # Апталық ұпайларды нөлдеу
    for user_id in scores:
        scores[user_id]["weekly"] = 0
    
    save_scores(scores)

# Күнделікті сұрақ жіберу
async def daily_quiz(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Күнделікті сұрақ жіберу"""
    chat_ids = context.bot_data.get("active_chats", [])
    
    if not chat_ids:
        return
    
    questions = load_questions()
    question_data = random.choice(questions)
    
    intro_text = (
        "*Бүгінгі IslamQuiz сұрағы!* 🌙\n\n"
        "Құрметті қатысушылар, жаңа сұраққа дайын болыңыздар!\n"
        "Дұрыс жауап берсеңіз, ұпай аласыз. Жауап беру уақыты: 24 сағат."
    )
    
    for chat_id in chat_ids:
        await context.bot.send_message(
            chat_id=chat_id,
            text=intro_text,
            parse_mode=ParseMode.MARKDOWN
        )
        await send_quiz(context, chat_id, question_data)

# Күнделікті ескерту жіберу
async def daily_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Күнделікті ескерту жіберу"""
    chat_ids = context.bot_data.get("active_chats", [])
    
    if not chat_ids:
        return
    
    reminder_text = (
        "🌙 *IslamQuiz ескертуі*\n\n"
        "Құрметті қатысушылар, бүгінгі сұраққа жауап беруді ұмытпаңыз!\n"
        "Білім - ең үлкен байлық! 📚"
    )
    
    for chat_id in chat_ids:
        await context.bot.send_message(
            chat_id=chat_id,
            text=reminder_text,
            parse_mode=ParseMode.MARKDOWN
        )

# Чатты тіркеу
async def register_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Чатты белсенді чаттар тізіміне қосу"""
    chat_id = update.effective_chat.id
    active_chats = context.bot_data.setdefault("active_chats", [])
    
    if chat_id not in active_chats:
        active_chats.append(chat_id)
        await update.message.reply_text(
            "Чат сәтті тіркелді! Енді күнделікті сұрақтар осы чатқа жіберіледі.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            "Бұл чат бұрыннан тіркелген!",
            parse_mode=ParseMode.MARKDOWN
        )

# Негізгі функция
def main() -> None:
    """Бот іске қосу"""
    # Аппликация жасау
    application = Application.builder().token(TOKEN).rate_limiter(AIORateLimiter()).build()
    
    # Командалар
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("quiz", quiz))
    application.add_handler(CommandHandler("score", score))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("register", register_chat))
    
    # Сауалнама жауаптарын өңдеу
    application.add_handler(PollAnswerHandler(handle_poll_answer))
    
    # Жаңа мүшелерді қарсы алу
    application.add_handler(ChatMemberHandler(greet_new_members, ChatMemberHandler.CHAT_MEMBER))
    
    # Кесте бойынша тапсырмаларды қосу
    job_queue = application.job_queue
    
    # Күнделікті сұрақ - таңғы 9:00-де
    job_queue.run_daily(
        daily_quiz,
        time=datetime.time(hour=9, minute=0, tzinfo=TIMEZONE),
        days=(0, 1, 2, 3, 4, 5, 6),  # Барлық күндері
    )
    
    # Күнделікті ескерту - кешкі 18:00-де
    job_queue.run_daily(
        daily_reminder,
        time=datetime.time(hour=18, minute=0, tzinfo=TIMEZONE),
        days=(0, 1, 2, 3, 4, 5, 6),  # Барлық күндері
    )
    
    # Апталық нәтижелер - жексенбі күні кешкі 20:00-де
    job_queue.run_daily(
        weekly_results,
        time=datetime.time(hour=20, minute=0, tzinfo=TIMEZONE),
        days=(6,),  # Тек жексенбі
    )
    
    # Ботты іске қосу
    application.run_polling()

if __name__ == "__main__":
    main() 