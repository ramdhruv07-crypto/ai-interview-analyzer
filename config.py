import pymysql
db = pymysql.connect(
    host="localhost",
    user="root",
    password="root123",
    database="ai_interview_analyzer"
)

cursor = db.cursor()