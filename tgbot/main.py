from tgbot.bot import run_polling
from tgbot.config import get_settings, load_dotenv_file
from tgbot.logging import configure_logging


def main() -> None:
    load_dotenv_file()
    configure_logging(get_settings().log_level)
    run_polling()


if __name__ == "__main__":
    main()
