from pathlib import Path

from fastapi import FastAPI, Depends, Query, Request
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from redis import Redis

from src.database.db import get_db, get_redis_client
from src.config.config import settings
from src.routes import posts, analitics, comments, users, auth

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=BASE_DIR / "src" / "templates")

app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "src" / "static"), name="static")
app.mount("/docs", StaticFiles(directory=BASE_DIR / "docs" / "_build" / "html"), name="docs",)
app.mount("/htmlcov", StaticFiles(directory=BASE_DIR / "htmlcov"), name="htmlcov",)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(posts.router, prefix='/api')
app.include_router(comments.router, prefix="/api")
app.include_router(analitics.router, prefix="/api")


@app.get("/api/db_healthchecker", tags=['healthchecker'])
async def database_healthchecker(db: AsyncSession = Depends(get_db)):
    """
    This function is a route handler for the "/api/healthchecker" endpoint. It checks the connection to the database and returns a success message if the connection is established.

    Parameters:
    - db (AsyncSession): A dependency representing the database session. It is obtained using the `get_db` function.

    Returns:
    - dict: A dictionary containing a message indicating that the connection to the database is established.

    Raises:
    - HTTPException: If there is an error connecting to the database, an HTTPException with a status code of 500 and a message indicating the error is raised.
    """
    try:
        result = await db.execute(text("SELECT 1"))
        result = result.fetchone()
        if result is None:
            raise HTTPException(
                status_code=500, detail="Database is not configured correctly"
            )
        return {"message": "Connection to database is established. Welcome to FastAPI Posts"}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to database")


REDIS_URL = settings.redis_url
@app.get("/api/redis_healthchecker", tags=["healthchecker"])
async def redis_healthchecker(
    key: str = Query(default="test"),
    value: str = Query(default="test"),
    redis_client: Redis = Depends(get_redis_client),
):
    """
    This function is a route handler for the "/api/redis_healthchecker" endpoint. It checks the connection to the Redis database and returns a success message if the connection is established.

    Parameters:
    - key (str): A string representing the key to be set in the Redis database. Default is "test".
    - value (str): A string representing the value to be set for the given key in the Redis database. Default is "test".
    - redis_client (Redis): A dependency representing the Redis client. It is obtained using the `get_redis_client` function.

    Returns:
    - dict: A dictionary containing a message indicating that the connection to the Redis database is established.

    Raises:
    - HTTPException: If there is an error connecting to the Redis database, an HTTPException with a status code of 500 and a message indicating the error is raised.
    """
    try:
        await redis_client.set(key, value, ex=5)
        value = await redis_client.get(key)
        if value is None:
            raise HTTPException(
                status_code=500, detail="Redis Database is not configured correctly"
            )
        return {"message": "Connection to Radis is established."}
    except Exception as e:
        print(e)
        raise HTTPException(status_code=500, detail="Error connecting to Radis")


@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    """
    This function is a route handler for the "/" endpoint. It renders the home page of the application using the Jinja2 templating engine.

    Parameters:
    - request (Request): The incoming HTTP request object.

    Returns:
    - Response: A response object containing the rendered HTML content of the "index.html" template.
    """
    return templates.TemplateResponse(
        "index.html", {"request": request, "our": "Build by Harley"}
    )
