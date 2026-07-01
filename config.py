import os
import pymysql
from urllib.parse import urlparse

DATABASE_URL = os.getenv("MYSQL_URL")

print("DATABASE_URL =", DATABASE_URL)

url = urlparse(DATABASE_URL)

print("HOST =", url.hostname)
print("DATABASE =", url.path.lstrip("/"))

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

cursor.execute("SELECT DATABASE()")
print("Connected database:", cursor.fetchone())

cursor.execute("SHOW TABLES")
print("Tables:", cursor.fetchall())