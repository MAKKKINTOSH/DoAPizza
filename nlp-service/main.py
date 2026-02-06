import os

import uvicorn

from nlp_service.app import app, get_port


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=get_port())


if __name__ == "__main__":
    main()