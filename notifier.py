import asyncio
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

from telegram import Bot
from telegram.error import Forbidden

from bot import load_bot_token
from outages import outages_reader
from users import users

LOG_FILE = "notifier.log"

def configure_logging() -> None:
    file_handler = TimedRotatingFileHandler(
        LOG_FILE,
        when="midnight",
        interval=1,
        backupCount=5,
        encoding="utf-8",
        utc=True,
    )
    file_handler.suffix = "%Y-%m-%d.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[file_handler, logging.StreamHandler(sys.stdout)],
    )

    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel(logging.WARNING)

    logging.info("Starting notification script.")


async def main() -> None:
    configure_logging()

    bot = Bot(token=load_bot_token())

    outages = outages_reader.get_outages()
    subscribed_users = users.all()

    for chat_id, user in subscribed_users:
        outage = user.get_first_outage(outages)

        if outage:
            if (user.is_notified(outage)):
                logging.info(f"Outage already notified for user {chat_id} - {user.street_name}, {user.building}")
                continue

            try:
                await bot.send_message(chat_id=chat_id, text=outage.format_message(), parse_mode="HTML")
                users.save(chat_id, user.set_outage(outage))
                logging.info(f"Notification sent to {chat_id} - {user.street_name}, {user.building}")
            except Forbidden:
                users.remove(chat_id)
                logging.info(f"Subscription removed for blocked user {chat_id}.")
            except Exception as e:
                logging.error(f"Failed to send message to {chat_id}: {e}")
        else:
            logging.info(f"No relevant outage found for user {chat_id} - {user.street_name}, {user.building}")


if __name__ == "__main__":
    asyncio.run(main())
