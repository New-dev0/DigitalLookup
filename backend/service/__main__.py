import asyncio

# from . import test_twitter
# asyncio.run(test_twitter())

# exit()

import uvicorn
from .app import app

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
