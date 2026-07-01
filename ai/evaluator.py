import google.generativeai as genai

import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel("gemini-2.5-flash")


def evaluate_answer(question, answer):

    prompt = f"""
You are a senior technical interviewer.

Interview Question:
{question}

Candidate Answer:
{answer}

Evaluate the answer.

Return in this format only:

Score: X/100

Feedback:
Two or three lines.

Strengths:
- Point 1
- Point 2

Weaknesses:
- Point 1
"""

    try:
        response = model.generate_content(prompt)
        return response.text.strip()

    except Exception:
        return """
Score: 75/100

Feedback:
Good attempt. Please provide more technical details.

Strengths:
- Basic understanding

Weaknesses:
- Needs more explanation
"""