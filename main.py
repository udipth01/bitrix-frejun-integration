from fastapi import FastAPI
from dotenv import load_dotenv
import logging
import sys
import os
from contextlib import asynccontextmanager


load_dotenv()

from supabase import create_client, Client

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(supabase_url, supabase_key)


logging.basicConfig(level=logging.INFO, stream=sys.stdout,
format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("frejun-bitrix")


from bitrix import router as bitrix_router
from frejun import router as frejun_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting app...")
    yield
    logger.info("Shutting down app...")


app = FastAPI(lifespan=lifespan)


# include routers
app.include_router(bitrix_router, prefix="", tags=["bitrix"])
app.include_router(frejun_router, prefix="", tags=["frejun"])


@app.get('/')
def health():
    return {"status": "alive"} 