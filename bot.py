import random
import time
from threading import Thread

import vk_api
from flask import Flask, jsonify
from vk_api.bot_longpoll import VkBotEventType, VkBotLongPoll

from config import (
    ATTACHMENT_CACHE_FILE,
    GROUP_ID,
    QUOTES_FILE,
    REPLIES_FILE,
    TOKEN,
)
from dice import DiceResult, format_multiple_rolls, format_single_roll, roll
from media import MediaManager
from quotes import QuoteManager
from replies import ReplyManager


app = Flask(__name__)
bot_state = {
    "running": False,
    "started_at": time.time(),
    "quotes": 0,
    "triggers": 0,
}


@app.route("/")
def home():
    return "Кубятня работает!"


@app.route("/health")
def health():
    uptime = max(0, int(time.time() - bot_state["started_at"]))
    return jsonify(
        running=bot_state["running"],
        uptime_seconds=uptime,
        quotes=bot_state["quotes"],
        triggers=bot_state["triggers"],
    )


def run_web():
    import os

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def send_message(vk, peer_id: int, message: str, attachment=None) -> None:
    params = {
        "peer_id": peer_id,
        "random_id": random.randint(1, 2**31 - 1),
        "message": message,
    }

    if attachment:
        params["attachment"] = attachment

    vk.messages.send(**params)


def get_user_name(vk, user_id: int) -> str:
    try:
        user = vk.users.get(user_ids=user_id)[0]
        return f"[id{user_id}|{user['first_name']}]"
    except Exception:
        return f"[id{user_id}|Игрок]"


def make_help(quotes_count: int) -> str:
    return (
        "🎲 КУБЯТНЯ — СПРАВКА\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📖 Броски:\n"
        "[к100 — один кубик\n"
        "[2к20 — несколько кубиков\n"
        "[3к20+15 — бросок с бонусом\n"
        "[3к20-5 — бросок со штрафом\n"
        "[3к20+15 #атака — комментарий\n\n"
        "Можно отправить несколько бросков отдельными строками.\n\n"
        "📜 Цитаты:\n"
        "[цитата\n"
        "[ц\n\n"
        f"📚 Цитат в базе: {quotes_count}\n"
        "⚔ Команды распознаются только через символ ["
    )


def make_quote(quote: str) -> str:
    return (
        "📜 ЦИТАТА ДНЯ\n"
        "━━━━━━━━━━━━━━━\n"
        f"«{quote}»"
    )


def main():
    if not TOKEN:
        raise RuntimeError("TOKEN не найден")

    vk_session = vk_api.VkApi(token=TOKEN)
    vk = vk_session.get_api()
    longpoll = VkBotLongPoll(vk_session, GROUP_ID)

    quotes = QuoteManager(QUOTES_FILE)
    replies = ReplyManager(REPLIES_FILE)
    media = MediaManager(vk_session, ATTACHMENT_CACHE_FILE)

    bot_state["running"] = True
    bot_state["quotes"] = len(quotes)
    bot_state["triggers"] = len(replies.replies)

    print(
        f"Кубятня запущена. Цитат: {len(quotes)}. "
        f"Триггеров: {len(replies.replies)}.",
        flush=True,
    )

    try:
        for event in longpoll.listen():
            if event.type != VkBotEventType.MESSAGE_NEW:
                continue

            message = event.object.message
            text = message.get("text", "").strip()

            if not text:
                continue

            peer_id = message["peer_id"]
            print(f"Получено сообщение: {text}", flush=True)

            triggered = replies.find_available(peer_id, text)
            if triggered:
                trigger, data = triggered
                attachment = media.resolve_attachment(
                    trigger=trigger,
                    attachment=data.get("attachment"),
                    image_path=data.get("image"),
                )
                send_message(
                    vk,
                    peer_id,
                    str(data.get("text", "")),
                    attachment,
                )

            if not text.startswith("["):
                continue

            user_id = message["from_id"]
            player = get_user_name(vk, user_id)
            lower_text = text.lower().strip()

            if lower_text == "[help":
                send_message(vk, peer_id, make_help(len(quotes)))
                continue

            if lower_text in ("[цитата", "[ц"):
                send_message(vk, peer_id, make_quote(quotes.get_random()))
                continue

            parsed_results: list[DiceResult | str] = []

            for line in text.splitlines():
                result = roll(line)
                if isinstance(result, (DiceResult, str)):
                    parsed_results.append(result)

            if not parsed_results:
                continue

            quote = quotes.get_random()

            if (
                len(parsed_results) == 1
                and isinstance(parsed_results[0], DiceResult)
            ):
                answer = format_single_roll(
                    player,
                    parsed_results[0],
                    quote,
                )
            else:
                answer = format_multiple_rolls(
                    player,
                    parsed_results,
                    quote,
                )

            send_message(vk, peer_id, answer)
    finally:
        bot_state["running"] = False


def run_bot_forever():
    while True:
        try:
            main()
        except Exception as error:
            bot_state["running"] = False
            print(
                f"Ошибка VK LongPoll: "
                f"{type(error).__name__}: {error}",
                flush=True,
            )
            time.sleep(10)


if __name__ == "__main__":
    Thread(target=run_web, daemon=True).start()
    run_bot_forever()
