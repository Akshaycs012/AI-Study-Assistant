from flask import Flask, request, jsonify, render_template, redirect, url_for
from pygments import highlight
from pygments.lexers import get_lexer_by_name, guess_lexer, TextLexer
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound
from datetime import datetime, timedelta
from groq import Groq
import requests
import re
import os
import markdown
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

app = Flask(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

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
    safe_tables = [t for t in TIMETABLES if isinstance(t, dict) and "items" in t]
    return render_template("index.html", timetables=safe_tables)



@app.route("/generate_timetable", methods=["POST"])
def generate_timetable():
    task_name = request.form.get("task_name")
    start_time = request.form.get("start_time")
    duration = request.form.get("duration_minutes")

    if not task_name or not duration:
        return "Missing fields", 400

    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = start_dt + timedelta(minutes=int(duration))

    # ✅ correct format
    new_timetable = {
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "items": [
            {
                "task": task_name,
                "start": start_dt.strftime("%H:%M"),
                "end": end_dt.strftime("%H:%M"),
                "minutes": int(duration)
            }
        ]
    }

    TIMETABLES.append(new_timetable)
    return redirect(url_for("index"))


@app.route("/generate_study_timetable", methods=["POST"])
def generate_study_timetable():
    import json
    data = request.get_json(silent=True) or {}
    code = data.get("code", "")
    concepts = data.get("concepts", "")

    if not code.strip():
        return jsonify(success=False, error="No code provided"), 400

    # ✅ new prompt with clear marker
    prompt = f"""
You are a helpful code tutor and study planner.

Analyze the given code and do the following:

PART 1 — Formal Explanation:
- Write a beginner-friendly explanation of the code (plain text, no stars, dots, bullets, markdown)
- Use 2-4 sentences per section: Overview, Step-by-Step Explanation, Algorithm, Key Concepts, Output Behavior

PART 2 — Study Plan JSON:
- After the explanation, output this exact marker on a new line:
  ---JSON---
- Then output ONLY a valid JSON array like:
[
  {{"task": "Understand loops", "minutes": 30}},
  {{"task": "Practice functions", "minutes": 40}}
]

Key concepts: {concepts}

Code:
```{code}```
"""

    try:
        resp = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        raw = (resp.choices[0].message.content or "").strip()

        # ✅ Split explanation vs JSON
        if "---JSON---" not in raw:
            raise ValueError("No JSON marker found in model output")
        _, json_part = raw.split("---JSON---", 1)

        # ✅ Clean + parse JSON
        json_text = json_part.strip()
        items = json.loads(json_text)
        if not isinstance(items, list):
            raise ValueError("Expected a JSON list")

        TIMETABLES.append({
            "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "items": items
        })
        return jsonify(success=True)

    except Exception as e:
        return jsonify(success=False, error=str(e)), 500



@app.route("/timetables")
def view_timetables():
    # Ensure TIMETABLES is always a list of dicts with "items" key
    safe_tables = []
    for t in TIMETABLES:
        if isinstance(t, dict) and "items" in t:
            safe_tables.append(t)
    return render_template("timetables.html", timetables=safe_tables)




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


@app.route("/line_explain", methods=["POST"])
def line_explain():
    data = request.get_json(silent=True) or {}
    user_input = (data.get("code") or "").strip()

    if not user_input:
        return jsonify({"error": "No input provided"}), 400

    prompt = f"""
You are a senior coding tutor.

If the user input is code:
- Start with a clear and short **overview** explaining what the code does overall.
- Then give a **line-by-line explanation**.
- Each line explanation should feel like a **topper friend is explaining**, in a warm and very understandable tone.
- Each line or block gets its **own paragraph** (or more if needed).
- ❌ Do NOT include or repeat the actual code here — assume it’s already shown above in the Explanation part.

If it's NOT code:
- Reply normally and conversationally.
✅ Output rules:
- Return pure HTML only
- Wrap everything in:
  <div class="bg-gray-900 p-6 rounded-xl shadow space-y-6 max-w-3xl mx-auto">

- Use Tailwind classes like:
  - text-emerald-300, text-indigo-300 for headings
  - text-gray-300 for text
  - p-4, rounded-xl, shadow for sections

- For the **overview**:
  <p class="text-gray-300 leading-relaxed bg-gray-800 p-4 rounded-lg shadow">

- For the line-by-line section heading:
  <h3 class="text-emerald-300 text-lg font-semibold">Line-by-Line Explanation</h3>

- For each explanation line:
  <div class="space-y-3">
    <p class="text-gray-300 leading-relaxed p-4 rounded-lg shadow odd:bg-gray-800 even:bg-gray-700">
      explanation here
    </p>
  </div>

- Inline highlight for code keywords:
  <span class="text-pink-400 font-mono">java.util.*</span>,
  <span class="text-yellow-300 font-mono">Scanner</span>,
  <span class="text-cyan-300 font-mono">dist</span>, etc.

- ❌ Do NOT include full code here (assume shown above)
- Only do: Overview + line-by-line logic
Input:
{user_input}
"""

    try:
        resp = client.chat.completions.create(
            model="gemma2-9b-it",  # ✅ same working model
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4
        )

        content = resp.choices[0].message.content.strip()
        if not content:
            return jsonify({"line_explanation": "<p class='text-red-400'>No explanation generated.</p>"}), 200

        return jsonify({"line_explanation": content})

    except Exception as e:
        print("LINE_EXPLAIN ERROR:", e)  # ✅ show full error in console
        return jsonify({"error": str(e)}), 500





@app.route("/get_youtube_videos", methods=["POST"])
def get_youtube_videos():
    # Now we get 'concepts' instead of 'code'
    concepts = request.json.get("concepts", "")

    # If nothing is provided, return error
    if not concepts.strip():
        return jsonify({"error": "No concepts provided"}), 400

    # Clean search query
    search_query = concepts.replace("\n", " ").strip()

    yt_response = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "part": "snippet",
            "q": search_query,
            "key": os.getenv("YOUTUBE_API_KEY"),
            "maxResults": 6,
            "type": "video"
        }
    )

    videos = yt_response.json().get("items", [])

    return jsonify({
        "query": search_query,
        "videos": [
            {
                "title": v["snippet"]["title"],
                "thumbnail": v["snippet"]["thumbnails"]["medium"]["url"],
                "videoId": v["id"]["videoId"]
            } for v in videos
        ]
    })


@app.route("/youtube_results")
def youtube_results():
    # just pass concepts from query to template if you want
    concepts = request.args.get("concepts", "")
    return render_template("youtube_results.html", concepts=concepts)


@app.route("/api/get_current_timetable")
def get_current_timetable():
    if not TIMETABLES or "items" not in TIMETABLES[-1]:
        return jsonify({"items": []})
    return jsonify({"items": TIMETABLES[-1]["items"]})

@app.route("/delete_timetable", methods=["POST"])
def delete_timetable():
    data = request.get_json(silent=True) or {}
    idx = int(data.get("timetable_index", -1))

    if 0 <= idx < len(TIMETABLES):
        TIMETABLES.pop(idx)
        return jsonify({"success": True})
    return jsonify({"success": False}), 400


@app.route("/delete_task", methods=["POST"])
def delete_task():
    data = request.get_json(silent=True) or {}
    table_index = int(data.get("timetable_index", -1))
    task_index = int(data.get("task_index", -1))

    if 0 <= table_index < len(TIMETABLES):
        timetable = TIMETABLES[table_index]
        if "items" in timetable and 0 <= task_index < len(timetable["items"]):
            timetable["items"].pop(task_index)
            return jsonify({"success": True})
    return jsonify({"success": False}), 400



@app.route("/notes")
def notes_page():
    return render_template("notes.html")



@app.route('/generate-notes', methods=['POST'])
def generate_notes():
    data = request.get_json()
    topic = data.get("topic")

    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    try:
        # Prepare the prompt
        prompt = (
            f"Provide a comprehensive explanation of '{topic}' in Markdown format. "
            f"Use headings, bullet points, numbered lists, and code blocks for relevant examples. "
            f"The response should be at least 300 words long."
        )

        # Call Grok API
        response = client.chat.completions.create(
            model="gemma2-9b-it",
            messages=[
                {"role": "system", "content": "You are a knowledgeable tutor who explains topics clearly."},
                {"role": "user", "content": prompt}
            ]
        )

        # Extract content from response
        content = response.choices[0].message.content

        # Convert Markdown to HTML
        html_notes = markdown.markdown(content, extensions=['fenced_code'])

        return jsonify({"notes": html_notes})

    except Exception as e:
        return jsonify({"error": f"An error occurred: {e}"}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)

