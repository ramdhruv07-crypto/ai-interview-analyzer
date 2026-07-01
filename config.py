import os
import pymysql
from urllib.parse import urlparse

DATABASE_URL = os.getenv("MYSQL_URL")

if not DATABASE_URL:
    raise Exception("MYSQL_URL environment variable is missing.")

url = urlparse(DATABASE_URL)

db = pymysql.connect(
    host=url.hostname,
    user=url.username,
    password=url.password,
    database=url.path.lstrip("/"),
    port=url.port,
    connect_timeout=30,
    cursorclass=pymysql.cursors.DictCursor
)

cursor = db.cursor()