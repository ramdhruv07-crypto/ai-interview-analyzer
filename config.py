import os
import pymysql
from urllib.parse import urlparse

DATABASE_URL = os.getenv("MYSQL_URL")

url = urlparse(DATABASE_URL)

db = pymysql.connect(
    host=url.hostname,
    user=url.username,
    password=url.password,
    database=url.path.lstrip("/"),
    port=url.port,
    cursorclass=pymysql.cursors.DictCursor
)

cursor = db.cursor()