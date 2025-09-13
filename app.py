from flask import Flask, request, jsonify, render_template, redirect, url_for
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from datetime import datetime, timedelta
from groq import Groq
import re
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# In-memory storage
TIMETABLES = []

# Language resources
LANG_RESOURCES = {
    "python": {"docs": "https://docs.python.org/3/", "youtube_query": "Python beginner tutorial functions loops explained"},
    "javascript": {"docs": "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "youtube_query": "JavaScript basics tutorial functions closures explained"},
    "java": {"docs": "https://docs.oracle.com/javase/8/docs/api/", "youtube_query": "Java tutorial for beginners OOP explained"},
    "c": {"docs": "https://en.cppreference.com/w/c", "youtube_query": "C programming tutorial pointers arrays explained"},
    "cpp": {"docs": "https://en.cppreference.com/w/", "youtube_query": "C++ tutorial classes templates explained"},
    "go": {"docs": "https://go.dev/doc/", "youtube_query": "Golang tutorial basics goroutines channels explained"},
    "rust": {"docs": "https://doc.rust-lang.org/book/", "youtube_query": "Rust tutorial ownership borrowing explained"}
}

# --------------------------
# Study-style Explain Logic
# --------------------------
def study_explain(language: str, code: str) -> str:
    prompt = f"""
You are a helpful study assistant.
Analyze the following {language} code in detail and explain it as if teaching a beginner student.

...
Format your response as styled HTML using Tailwind CSS classes.
Use:
- <h3 class="text-xl font-semibold text-indigo-400 border-b border-gray-700 pb-1"> for section titles
- <ul class="list-disc list-inside space-y-1 text-gray-200"> and <li> for bullet points
- <p class="text-gray-300 leading-relaxed"> for normal explanation text

Also include:
- <h3 class="text-lg font-semibold text-blue-400 mt-4">💻 Highlighted Code</h3> followed by a 
<pre class="bg-gray-800 text-green-300 rounded-lg p-4 overflow-x-auto text-sm shadow-inner"> block

Code:
```{language}
{code}
```"""


    try:
        resp = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"<p style='color:red'>Groq API error: {e}</p>"


# --------------------------
# Syntax Highlighting Utils
# --------------------------
def highlight_code(language: str, code: str):
    try:
        lexer = get_lexer_by_name(language, stripall=True)
    except Exception:
        try:
            lexer = guess_lexer(code)
        except Exception:
            lexer = TextLexer()
    formatter = HtmlFormatter(style="friendly", linenos=False, cssclass="codehilite")
    return highlight(code, lexer, formatter), formatter.get_style_defs('.codehilite')

def extract_keywords(code: str):
    keywords = []
    funcs = re.findall(r"\bdef\s+(\w+)|\bfunction\s+(\w+)", code)
    classes = re.findall(r"\bclass\s+(\w+)", code)
    methods = re.findall(r"\.(\w+)\(", code)

    if funcs:
        keywords.extend([f"Function: {f[0] or f[1]}()" for f in funcs])
    if classes:
        keywords.extend([f"Class: {c}" for c in classes])
    if re.search(r"\bfor\b|\bwhile\b", code):
        keywords.append("Loop")
    if re.search(r"\bif\b|\belse\b|\belif\b|\bswitch\b", code):
        keywords.append("Conditional")
    if re.search(r"\bimport\b|\bfrom\b|\#include|\busing\b", code):
        keywords.append("Import")
    if re.search(r"\bprint\b|\bconsole\.log\b|\bSystem\.out\.println\b|\bcout\b", code):
        keywords.append("Output")
    if methods:
        keywords.extend([f"Method: {m}()" for m in set(methods)])

    return keywords or ["No major elements detected."]

# --------------------------
# Routes
# --------------------------
@app.route("/")
def index():
    return render_template("index.html", timetables=TIMETABLES)

@app.route("/generate_timetable", methods=["POST"])
def generate_timetable():
    start_time = request.form.get("start_time")
    task_name = request.form.get("task_name")
    duration = request.form.get("duration_minutes")

    if not task_name or not duration:
        return "Error: Task name and duration are required", 400

    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = start_dt + timedelta(minutes=int(duration))

    timetable = [{
        "task": task_name,
        "start": start_dt.strftime("%H:%M"),
        "end": end_dt.strftime("%H:%M")
    }]

    if not TIMETABLES:
        TIMETABLES.append([])
    TIMETABLES[0].append(timetable)

    return redirect(url_for("index"))

@app.route("/explain", methods=["POST"])
def explain():
    payload = request.get_json(silent=True) or {}
    code = (payload.get("code") or "").strip()

    if not code:
        return jsonify(error="Please provide some code"), 400

    try:
        detected = guess_lexer(code)
        language = detected.name.lower()
    except ClassNotFound:
        language = "python"

    if language not in LANG_RESOURCES:
        language = "python"

    explanation = study_explain(language, code)
    highlighted, css = highlight_code(language, code)
    keywords = extract_keywords(code)

    yt_query = LANG_RESOURCES[language]["youtube_query"]
    youtube_search_url = f"https://www.youtube.com/results?search_query={yt_query.replace(' ', '+')}"

    return jsonify({
        "language": language,
        "explanation": explanation,
        "highlighted": highlighted,
        "css": css,
        "keywords": keywords,
        "resources": {
            "docs": LANG_RESOURCES[language]["docs"],
            "youtube_search": youtube_search_url
        }
    })

@app.route("/delete_task", methods=["POST"])
def delete_task():
    data = request.get_json(silent=True) or {}
    tt_idx = int(data.get("timetable_index", -1))
    task_idx = int(data.get("task_index", -1))

    if 0 <= tt_idx < len(TIMETABLES) and 0 <= task_idx < len(TIMETABLES[tt_idx]):
        TIMETABLES[tt_idx].pop(task_idx)
        return jsonify(success=True)
    return jsonify(success=False, error="Invalid indices"), 400

@app.route("/edit_task", methods=["POST"])
def edit_task():
    timetable_index = int(request.form.get("timetable_index"))
    task_index = int(request.form.get("task_index"))
    task_name = request.form.get("task_name")
    start_time = request.form.get("start_time")
    duration = request.form.get("duration_minutes")

    try:
        start_dt = datetime.strptime(start_time, "%H:%M")
        end_dt = start_dt + timedelta(minutes=int(duration))
        TIMETABLES[timetable_index][task_index] = {
            "task": task_name,
            "start": start_dt.strftime("%H:%M"),
            "end": end_dt.strftime("%H:%M")
        }
        return redirect(url_for("index"))
    except Exception as e:
        return f"Failed to edit: {e}", 400

if __name__ == "__main__":
    app.run(debug=True, port=5000)
