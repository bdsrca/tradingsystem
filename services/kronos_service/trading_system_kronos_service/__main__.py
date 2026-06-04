from __future__ import annotations

import uvicorn

from trading_system_kronos_service.app import create_app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)
