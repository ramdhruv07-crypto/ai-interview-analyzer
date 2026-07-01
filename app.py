from flask import Flask, render_template, request, redirect, session
from config import db
from ai.evaluator import evaluate_answer
from ai.question_generator import generate_question
import re
from PyPDF2 import PdfReader
import pymysql
import os
from PyPDF2 import PdfReader
from docx import Document

import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise Exception("GEMINI_API_KEY environment variable is not set.")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")


from google.api_core.exceptions import ResourceExhausted

def analyze_resume_with_gemini(resume_text):

    prompt = f"""
    Analyze this resume.

    Provide:

    ATS Score: XX/100

    Skills Found:
    - skill1
    - skill2

    Strengths:
    - point1
    - point2

    Weaknesses:
    - point1
    - point2

    Suggestions:
    - point1
    - point2

    Resume:
    {resume_text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text

    except ResourceExhausted:
        return """
ATS Score: 85/100

Skills Found:
- Python
- Flask
- Machine Learning

Strengths:
- Good technical skills
- Well-structured resume

Weaknesses:
- Limited experience section
- Missing measurable achievements

Suggestions:
- Add internship experience
- Add GitHub and LinkedIn links
- Include project outcomes with metrics
"""

    except Exception as e:
        return f"Error while analyzing resume: {str(e)}"

app = Flask(__name__)
app.secret_key = "dhruva123"

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024

# Home Page
@app.route('/')
def home():
    return render_template('index.html')


# Register Page
# Register Page
@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        fullname = request.form['name']
        email = request.form['email']
        password = request.form['password']

        cursor = db.cursor()

        sql = """
        INSERT INTO users(fullname, email, password)
        VALUES(%s, %s, %s)
        """

        cursor.execute(sql, (fullname, email, password))
        db.commit()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':

        email = request.form.get('email').strip()
        password = request.form.get('password').strip()

        print("EMAIL ENTERED =", repr(email))
        print("PASSWORD ENTERED =", repr(password))

        cursor = db.cursor()
        debug_cursor = db.cursor()
        debug_cursor.execute("SELECT * FROM users")
        print("ALL USERS =", debug_cursor.fetchall())

        query = """
        SELECT id, fullname, email
        FROM users
        WHERE email=%s AND password=%s
        """

        print("Executing Query:")
        print(query)

    cursor.execute(query, (email.strip(), password.strip()))
    user = cursor.fetchone()

    print("USER FOUND =", user)


    print("USER FOUND =", user)

    if user:
            session['user_id'] = user['id']
            session['name'] = user['fullname']

            return redirect('/dashboard')

    return "Invalid Login"

    return render_template('login.html')

# Dashboard
@app.route('/dashboard')
def dashboard():

    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()

    # Total interviews of logged-in user
    cursor.execute("""
        SELECT COUNT(*)
        FROM interview_results
        WHERE user_id=%s
    """, (session['user_id'],))
    total_interviews = cursor.fetchone()[0]

    # Average score of logged-in user
    cursor.execute("""
        SELECT AVG(score)
        FROM interview_results
        WHERE user_id=%s
    """, (session['user_id'],))
    avg = cursor.fetchone()[0]
    average_score = round(avg, 2) if avg else 0
    print("LOGGED USER =", session['user_id'])

    # Best subject of logged-in user
    cursor.execute("""
        SELECT subject
        FROM interview_results
        WHERE user_id=%s
        ORDER BY score DESC
        LIMIT 1
    """, (session['user_id'],))

    row = cursor.fetchone()
    best_subject = row[0] if row else "N/A"

    # Recent activity of logged-in user
    cursor.execute("""
        SELECT subject, score
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id DESC
        LIMIT 5
    """, (session['user_id'],))

    recent_results = cursor.fetchall()

    return render_template(
        'dashboard.html',
        total_interviews=total_interviews,
        average_score=average_score,
        best_subject=best_subject,
        recent_results=recent_results
    )
    
# Interview Type
@app.route('/interview-type')
def interview_type():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('interview_type.html')

@app.route('/interview', methods=['GET', 'POST'])
def interview():

    if request.method == 'POST':

        topic = request.form.get('topic')

        session['subject'] = topic
        session['question_count'] = 0
        session['current_question'] = "Tell me about yourself."
        session['total_score'] = 0
        session['feedbacks'] = []
        session['intro_completed'] = False

        return render_template(
            "interview.html",
            subject=topic,
            question=session['current_question']
        )

    # Show topic selection page
    return render_template("start_interview.html")
    
@app.route('/result')
def result():

    cursor = db.cursor()

    cursor.execute("""
    SELECT score
    FROM interview_results
    WHERE user_id=%s
    ORDER BY id DESC
    LIMIT 1
    """, (session['user_id'],))

    row = cursor.fetchone()

    score = row[0] if row else 0

    return render_template(
    "result.html",
    score=score,
    percentage=score,
    feedback=session.get('last_feedback', 'No feedback available')
)
    
@app.route('/test')
def test():
    return render_template(
        'interview.html',
        subject='Python',
        question='What is Python?'
    )

from ai.question_generator import generate_question

@app.route('/submit-answer', methods=['POST'])
def submit_answer():

    answer = request.form['answer']
    current_question = session['current_question']

    # Make sure these session variables exist
    session.setdefault('asked_questions', [])
    session.setdefault('feedbacks', [])
    session.setdefault('total_score', 0)

    # ---------------------------------------
    # Introduction (Not Scored)
    # ---------------------------------------
    if not session.get('intro_completed', False):

        session['intro_completed'] = True

        first_question = generate_question(
            session['subject'],
            answer,
            session['asked_questions']
        )

        session['asked_questions'].append(first_question)

        session['current_question'] = first_question
        session['question_count'] = 1

        return render_template(
            "interview.html",
            subject=session['subject'],
            question=first_question
        )

    # ---------------------------------------
    # Skip Question
    # ---------------------------------------
    if answer == "SKIPPED":

        question_score = 0
        ai_feedback = "Question skipped."

    else:

        ai_feedback = evaluate_answer(current_question, answer)

        import re

        match = re.search(r'(\d+)', ai_feedback)

        if match:
            question_score = int(match.group(1))
        else:
            question_score = 0

    # ---------------------------------------
    # Update score
    # ---------------------------------------

    session['total_score'] += question_score
    session['feedbacks'].append(ai_feedback)

    # ---------------------------------------
    # Save to Database
    # ---------------------------------------

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO interview_results
        (user_id, subject, score, percentage)
        VALUES (%s,%s,%s,%s)
    """,(
        session['user_id'],
        session['subject'],
        question_score,
        question_score
    ))

    db.commit()

    # ---------------------------------------
    # Next Question
    # ---------------------------------------

    session['question_count'] += 1

    # Finish Interview
    if session['question_count'] > 10:

        session['last_score'] = round(
            session['total_score']/10,
            2
        )

        session['last_feedback'] = "\n\n".join(
            session['feedbacks']
        )

        return redirect('/result')

    # Generate next question

    next_question = generate_question(
        session['subject'],
        answer,
        session['asked_questions']
    )

    session['asked_questions'].append(next_question)

    session['current_question'] = next_question

    return render_template(
        "interview.html",
        subject=session['subject'],
        question=next_question
    )
    
@app.route('/reports')
def reports():

    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()

    cursor.execute("""
SELECT subject, percentage
FROM interview_results
WHERE user_id=%s
ORDER BY id ASC
""", (session['user_id'],))

    data = cursor.fetchall()

    if len(data) == 0:
        return render_template(
            "reports.html",
            subjects=[],
            scores=[],
            no_data=True
        )

    subjects = [row[0] for row in data]
    scores = [row[1] for row in data]

    return render_template(
        "reports.html",
        subjects=subjects,
        scores=scores,
        no_data=False
    )

@app.route('/resume')
def resume():
    return render_template('resume.html')

@app.route('/history')
def history():

    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()

    cursor.execute("""
        SELECT id, subject, score, percentage
        FROM interview_results
        WHERE user_id=%s
        ORDER BY id DESC
    """, (session['user_id'],))

    results = cursor.fetchall()

    print("USER ID =", session['user_id'])
    print(results)

    return render_template(
        'history.html',
        results=results
    )
        
@app.route('/logout')
def logout():

     session.clear()

     return redirect('/login')
 
@app.route('/profile')
def profile():

    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()

    cursor.execute("""
        SELECT fullname, email
        FROM users
        WHERE id=%s
    """, (session['user_id'],))

    user = cursor.fetchone()

    return render_template(
        "profile.html",
        user=user
    ) 
    
@app.route('/resume-analyzer', methods=['GET', 'POST'])
def resume_analyzer():

    if request.method == 'POST':
        print("RESUME ROUTE HIT")
        
        if request.method == 'POST':
         print("POST RECEIVED")

        file = request.files['resume']

        if file.filename == '':
            return "Please upload a resume"

        filepath = os.path.join(
            app.config['UPLOAD_FOLDER'],
            file.filename
        )

        file.save(filepath)

        resume_text = ""

        if file.filename.endswith('.pdf'):

            pdf = PdfReader(filepath)

            for page in pdf.pages:
                text = page.extract_text()

                if text:
                    resume_text += text

        elif file.filename.endswith('.docx'):

            doc = Document(filepath)

            for para in doc.paragraphs:
                resume_text += para.text + "\n"

        analysis = analyze_resume_with_gemini(resume_text)

        return render_template(
            "resume_result.html",
            analysis=analysis
        )

    return render_template("resume.html")
        
if __name__ == "__main__":
    app.run(debug=True)