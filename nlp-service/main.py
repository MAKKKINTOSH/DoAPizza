import uvicorn

from nlp_service.app import app, get_port
from nlp_service.logging import configure_logging


def main() -> None:
    configure_logging()
    uvicorn.run(app, host="0.0.0.0", port=get_port(), log_config=None)


if __name__ == "__main__":
    main()
