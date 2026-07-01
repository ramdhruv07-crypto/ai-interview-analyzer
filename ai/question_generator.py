import google.generativeai as genai

# Configure Gemini
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Load Model
model = genai.GenerativeModel("gemini-2.5-flash")


def generate_question(topic, previous_answer="", asked_questions=None):

    if asked_questions is None:
        asked_questions = []

    previous_questions = "\n".join(
        [f"- {q}" for q in asked_questions]
    )

    prompt = f"""
You are a professional AI Technical Interviewer.

Conduct an interview ONLY for the subject:

{topic}

Candidate's previous answer:

{previous_answer}

Already asked questions:

{previous_questions}

Rules:

1. Ask ONLY ONE interview question.
2. NEVER repeat any question from the list above.
3. Question MUST belong ONLY to {topic}.
4. Start from basic concepts and gradually increase difficulty.
5. If there are no previous questions, ask an introductory technical question.
6. Return ONLY the question.
7. Do not include numbering.
8. Do not include explanations.
9. Do not include markdown.
10. Keep the question under 30 words.

Examples:

Python:
What is Python?

Java:
What is JVM?

DBMS:
What is normalization?

Machine Learning:
What is supervised learning?

Generate ONE unique interview question.
"""

    try:

        response = model.generate_content(prompt)

        question = response.text.strip()

        # Remove unwanted formatting
        question = question.replace("*", "")
        question = question.replace('"', "")
        question = question.replace("Question:", "")
        question = question.replace("Q:", "")

        # Prevent duplicate question
        if question in asked_questions:

            fallback = [
                f"What is {topic}?",
                f"Explain the fundamentals of {topic}.",
                f"What are the advantages of {topic}?",
                f"Describe real-world applications of {topic}.",
                f"What are the challenges in {topic}?"
            ]

            for q in fallback:
                if q not in asked_questions:
                    return q

        return question

    except Exception as e:

        print("Gemini Error:", e)

        fallback = [
            f"What is {topic}?",
            f"Explain the fundamentals of {topic}.",
            f"What are the advantages of {topic}?",
            f"Describe real-world applications of {topic}.",
            f"What are the challenges in {topic}?"
        ]

        for q in fallback:
            if q not in asked_questions:
                return q

        return f"Explain the importance of {topic}."