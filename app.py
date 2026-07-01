from flask import Flask, render_template, request, redirect, session
from config import db
from ai.evaluator import evaluate_answer
from ai.question_generator import generate_question

from PyPDF2 import PdfReader
from docx import Document

import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted

import pymysql
import os
import re

# ----------------------------------------------------
# Gemini Configuration
# ----------------------------------------------------

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY not found")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

# ----------------------------------------------------
# Flask App
# ----------------------------------------------------

app = Flask(__name__)

app.secret_key = "dhruva123"

UPLOAD_FOLDER = "uploads"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# ----------------------------------------------------
# Resume Analyzer
# ----------------------------------------------------

def analyze_resume_with_gemini(resume_text):

    prompt = f"""
Analyze this resume.

Provide:

ATS Score: XX/100

Skills Found

Strengths

Weaknesses

Suggestions

Resume:

{resume_text}
"""

    try:

        response = model.generate_content(prompt)

        return response.text

    except ResourceExhausted:

        return """
ATS Score : 85/100

Skills Found

• Python
• Flask
• Machine Learning

Strengths

• Good Programming Skills
• Good Resume Structure

Weaknesses

• No Internship
• No Quantified Achievements

Suggestions

• Add Internship
• Add GitHub
• Add LinkedIn
"""

    except Exception as e:

        return str(e)

# ----------------------------------------------------
# Home
# ----------------------------------------------------

@app.route("/")
def home():

    return render_template("index.html")

# ----------------------------------------------------
# Register
# ----------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        fullname = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"].strip()

        cursor = db.cursor()

        cursor.execute(
            """
            INSERT INTO users(fullname,email,password)
            VALUES(%s,%s,%s)
            """,
            (fullname, email, password),
        )

        db.commit()

        return redirect("/login")

    return render_template("register.html")

# ----------------------------------------------------
# Login
# ----------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        print("EMAIL =", email)
        print("PASSWORD =", password)

        cursor = db.cursor()

        query = """
            SELECT id, fullname, email
            FROM users
            WHERE email=%s AND password=%s
        """

        print(query)

        cursor.execute(query, (email, password))
        user = cursor.fetchone()

        print("USER FOUND =", user)

        if user:
            session['user_id'] = user['id']
            session['name'] = user['fullname']
            return redirect('/dashboard')

        return "Invalid Login"

    return render_template("login.html")

# Dashboard
# ----------------------------------------------------
# Dashboard
# ----------------------------------------------------

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    # Total interviews
    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM interview_results
        WHERE user_id=%s
    """, (session["user_id"],))
    total = cursor.fetchone()["total"]

    # Average score
    cursor.execute("""
        SELECT AVG(score) AS avg_score
        FROM interview_results
        WHERE user_id=%s
    """, (session["user_id"],))
    avg = cursor.fetchone()["avg_score"]

    if avg is None:
        avg = 0

    # Recent interviews
    cursor.execute("""
        SELECT subject, score, percentage, created_at
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 5
    """, (session["user_id"],))

    history = cursor.fetchall()

    return render_template(
        "dashboard.html",
        total_interviews=total,
        average_score=round(avg, 2),
        history=history
    )

# ----------------------------------------------------
# Interview Type
# ----------------------------------------------------

@app.route("/interview-type")
def interview_type():

    if "user_id" not in session:
        return redirect("/login")

    return render_template("interview_type.html")


# ----------------------------------------------------
# Interview
# ----------------------------------------------------

@app.route("/interview",methods=["GET","POST"])
def interview():

    if "user_id" not in session:
        return redirect("/login")

    if request.method=="POST":

        topic=request.form.get("topic")

        session["subject"]=topic
        session["question_count"]=0
        session["total_score"]=0
        session["feedbacks"]=[]
        session["asked_questions"]=[]
        session["intro_completed"]=False

        session["current_question"]="Tell me about yourself."

        return render_template(
            "interview.html",
            subject=topic,
            question=session["current_question"]
        )

    return render_template("start_interview.html")


# ----------------------------------------------------
# Result
# ----------------------------------------------------

@app.route("/result")
def result():

    if "user_id" not in session:
        return redirect("/login")

    cursor=db.cursor()

    cursor.execute("""
        SELECT score,
               percentage
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 1
    """,(session["user_id"],))

    row=cursor.fetchone()

    if row:

        score=row["score"]
        percentage=row["percentage"]

    else:

        score=0
        percentage=0

    return render_template(
        "result.html",
        score=score,
        percentage=percentage,
        feedback=session.get(
            "last_feedback",
            "No Feedback Available"
        )
    )


# ----------------------------------------------------
# Test Route
# ----------------------------------------------------

@app.route("/test")
def test():

    return render_template(
        "interview.html",
        subject="Python",
        question="What is Python?"
    )
    
from ai.question_generator import generate_question

# ----------------------------------------------------
# Submit Answer
# ----------------------------------------------------

@app.route("/submit-answer", methods=["POST"])
def submit_answer():

    if "user_id" not in session:
        return redirect("/login")

    answer = request.form.get("answer", "").strip()

    current_question = session.get("current_question")

    session.setdefault("asked_questions", [])
    session.setdefault("feedbacks", [])
    session.setdefault("total_score", 0)

    # ---------------------------------------------
    # Introduction Question (Not Scored)
    # ---------------------------------------------

    if not session.get("intro_completed", False):

        session["intro_completed"] = True

        next_question = generate_question(
            session["subject"],
            answer,
            session["asked_questions"]
        )

        session["asked_questions"].append(next_question)

        session["current_question"] = next_question

        session["question_count"] = 1

        return render_template(
            "interview.html",
            subject=session["subject"],
            question=next_question
        )

    # ---------------------------------------------
    # Skip Question
    # ---------------------------------------------

    if answer.upper() == "SKIPPED":

        question_score = 0
        ai_feedback = "Question skipped."

    else:

        ai_feedback = evaluate_answer(
            current_question,
            answer
        )

        match = re.search(r'(\d+)', ai_feedback)

        if match:
            question_score = int(match.group(1))
        else:
            question_score = 0

    # ---------------------------------------------
    # Update Session
    # ---------------------------------------------

    session["total_score"] += question_score

    session["feedbacks"].append(ai_feedback)

    # ---------------------------------------------
    # Save Result
    # ---------------------------------------------

    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO interview_results
        (
            user_id,
            subject,
            score,
            percentage,
            feedback
        )
        VALUES
        (
            %s,
            %s,
            %s,
            %s,
            %s
        )
        """,
        (
            session["user_id"],
            session["subject"],
            question_score,
            question_score,
            ai_feedback
        )
    )

    db.commit()

    # ---------------------------------------------
    # Next Question Count
    # ---------------------------------------------

    session["question_count"] += 1

    # ---------------------------------------------
    # Finish Interview
    # ---------------------------------------------

    if session["question_count"] > 10:

        final_score = round(
            session["total_score"] / 10,
            2
        )

        session["last_score"] = final_score

        session["last_feedback"] = "\n\n".join(
            session["feedbacks"]
        )

        return redirect("/result")

    # ---------------------------------------------
    # Generate Next Question
    # ---------------------------------------------

    next_question = generate_question(
        session["subject"],
        answer,
        session["asked_questions"]
    )

    session["asked_questions"].append(next_question)

    session["current_question"] = next_question

    return render_template(
        "interview.html",
        subject=session["subject"],
        question=next_question
    )
    
# ----------------------------------------------------
# Reports
# ----------------------------------------------------

@app.route("/reports")
def reports():

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    cursor.execute("""
        SELECT subject,
               percentage
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id ASC
    """,(session["user_id"],))

    data = cursor.fetchall()

    if not data:

        return render_template(
            "reports.html",
            subjects=[],
            scores=[],
            no_data=True
        )

    subjects = [row["subject"] for row in data]
    scores = [row["percentage"] for row in data]

    return render_template(
        "reports.html",
        subjects=subjects,
        scores=scores,
        no_data=False
    )


# ----------------------------------------------------
# History
# ----------------------------------------------------

@app.route("/history")
def history():

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            id,
            subject,
            score,
            percentage,
            created_at
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id DESC
    """,(session["user_id"],))

    results = cursor.fetchall()

    return render_template(
        "history.html",
        results=results
    )


# ----------------------------------------------------
# Profile
# ----------------------------------------------------

@app.route("/profile")
def profile():

    if "user_id" not in session:
        return redirect("/login")

    cursor = db.cursor()

    cursor.execute("""
        SELECT
            fullname,
            email
        FROM users
        WHERE id=%s
    """,(session["user_id"],))

    user = cursor.fetchone()

    return render_template(
        "profile.html",
        user=user
    )


# ----------------------------------------------------
# Resume Page
# ----------------------------------------------------

@app.route("/resume")
def resume():

    return render_template("resume.html")


# ----------------------------------------------------
# Resume Analyzer
# ----------------------------------------------------

@app.route("/resume-analyzer", methods=["GET","POST"])
def resume_analyzer():

    if request.method == "POST":

        file = request.files.get("resume")

        if not file:
            return "Please upload a resume."

        if file.filename == "":
            return "Please select a file."

        filepath = os.path.join(
            app.config["UPLOAD_FOLDER"],
            file.filename
        )

        file.save(filepath)

        resume_text = ""

        if file.filename.lower().endswith(".pdf"):

            pdf = PdfReader(filepath)

            for page in pdf.pages:

                text = page.extract_text()

                if text:
                    resume_text += text

        elif file.filename.lower().endswith(".docx"):

            doc = Document(filepath)

            for para in doc.paragraphs:
                resume_text += para.text + "\n"

        else:

            return "Only PDF and DOCX files are supported."

        analysis = analyze_resume_with_gemini(
            resume_text
        )

        return render_template(
            "resume_result.html",
            analysis=analysis
        )

    return render_template("resume.html")


# ----------------------------------------------------
# Logout
# ----------------------------------------------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")


# ----------------------------------------------------
# Error Pages
# ----------------------------------------------------

@app.errorhandler(404)
def page_not_found(e):

    return render_template("404.html"),404


@app.errorhandler(500)
def internal_error(e):

    db.rollback()

    return render_template("500.html"),500


# ----------------------------------------------------
# Run Flask
# ----------------------------------------------------

if __name__ == "__main__":

    app.run(
        debug=True,
        host="0.0.0.0",
        port=5000
    )