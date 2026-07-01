CREATE DATABASE ai_interview;

USE ai_interview;

CREATE TABLE users(
id INT AUTO_INCREMENT PRIMARY KEY,
fullname VARCHAR(100),
email VARCHAR(100) UNIQUE,
phone VARCHAR(20),
password VARCHAR(255),
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interviews(
id INT AUTO_INCREMENT PRIMARY KEY,
user_id INT,
interview_type VARCHAR(100),
score INT,
percentage FLOAT,
feedback TEXT,
created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE questions(
id INT AUTO_INCREMENT PRIMARY KEY,
interview_type VARCHAR(100),
question TEXT
);

CREATE TABLE answers(
id INT AUTO_INCREMENT PRIMARY KEY,
interview_id INT,
question_id INT,
answer TEXT,
FOREIGN KEY(interview_id) REFERENCES interviews(id)
);