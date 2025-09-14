// ===========================
// Explain Code Handler
// ===========================
document.getElementById("btnExplain").addEventListener("click", async () => {
  const code = document.getElementById("code").value.trim();
  if (!code) return alert("Please enter some code!");

  try {
    const res = await fetch("/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }) // ⬅️ language removed
    });

    const data = await res.json();
    if (data.error) {
      document.getElementById("explanation-output").innerText = data.error;
      return;
    }



        // 🎯 Now fetch YouTube videos based on key concepts
const keyConcepts = (data.keywords || []).join(" ");

fetch("/get_youtube_videos", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ concepts: keyConcepts })
})
  .then(res => res.json())
  .then(ytData => {
    const grid = document.getElementById("video-grid");
    if (!grid) return; // grid exists only on youtube_results.html
    grid.innerHTML = ytData.videos.map(v => `
      <div class="card">
        <a href="https://www.youtube.com/watch?v=${v.videoId}" target="_blank">
          <img src="${v.thumbnail}" alt="${v.title}">
          ${v.title}
        </a>
      </div>
    `).join("");
  })
  .catch(err => console.error(err));


    // 💬 Explanation Section
    document.getElementById("explanation-output").innerHTML = `
      <div class="bg-[#1f1f3a] p-5 rounded-2xl shadow-md">
        <h2 class="text-2xl font-bold mb-3 text-[#a0e7e5] flex items-center gap-2">
          📖 Code Explanation
        </h2>
        <div class="text-sm opacity-80 mb-3">
          <strong>Language:</strong> ${data.language?.toUpperCase() || "N/A"}
        </div>
        <div class="prose prose-invert max-w-none">
          ${data.explanation}
        </div>
      </div>
    `;

    // 💡 Contextual Keywords
    document.getElementById("contextual-output").innerHTML = `
      <div class="bg-[#1f1f3a] p-5 rounded-2xl shadow-md">
        <h2 class="text-2xl font-bold mb-3 text-yellow-300">📌 Key Concepts</h2>
        <div class="flex flex-wrap gap-2">
          ${(data.keywords || []).map(k =>
            `<span class="bg-indigo-600 px-3 py-1 rounded-full text-sm">${k}</span>`
          ).join("")}
        </div>
      </div>
    `;



    // 💻 Highlighted Code
    document.getElementById("explanation-output").insertAdjacentHTML("beforeend", `
  <div class="mt-6">
    <h3 class="text-lg font-semibold text-green-300 mb-2">💻 Highlighted Code:</h3>
    <div class="rounded-xl overflow-hidden border border-gray-600 bg-[#2d2d2d] p-4">
      ${data.highlighted}
    </div>
  </div>
`);


    // 📚 Resources
// ===========================
// Inject Resources Section
// ===========================
document.getElementById("resources-output").innerHTML = `
  <div class="bg-[#1f1f3a] p-5 rounded-2xl shadow-md">
    <h2 class="text-2xl font-bold mb-3 text-pink-300">📚 Resources</h2>
    <div class="flex gap-4">

      <!-- Official Docs -->
      <a href="${data.resources?.docs || '#'}" 
         target="_blank"
         class="bg-indigo-600 hover:bg-indigo-700 px-4 py-2 rounded-lg text-white font-semibold">
         Official Docs
      </a>

      <!-- YouTube Tutorials -->
      <a href="/youtube_results?concepts=${encodeURIComponent(keyConcepts)}"
         target="_blank"
         class="bg-rose-600 hover:bg-rose-700 px-4 py-2 rounded-lg text-white font-semibold">
         YouTube Tutorials
      </a>

      <!-- Generate Timetable -->
      <button id="btnGenTimetable"
         class="bg-emerald-600 hover:bg-emerald-700 px-4 py-2 rounded-lg text-white font-semibold">
         📅 Generate Timetable
      </button>

    </div>
  </div>
`;



    // Optional: Add returned CSS
    if (data.css) {
      const styleTag = document.createElement("style");
      styleTag.innerHTML = data.css;
      document.head.appendChild(styleTag);
    }

  } catch (err) {
    alert("Error fetching explanation: " + err.message);
  }
});



// ===========================
// Edit Button (Static Existing Items)
// ===========================
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".edit-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      const li = btn.closest("li");
      if (!li) return;

      const timetableIndex = li.dataset.timetableIndex;
      const taskIndex = li.dataset.taskIndex;
      const currentTask = li.querySelector("strong")?.innerText || "";
      const currentStart = li.dataset.start;

      const newTask = prompt("Edit task name:", currentTask);
      const newStart = prompt("Edit start time (HH:MM):", currentStart);
      const newDuration = prompt("Edit duration (minutes):", "60");

      if (newTask && newStart && newDuration) {
        const form = document.createElement("form");
        form.method = "POST";
        form.action = "/edit_task";

        const fields = {
          timetable_index: timetableIndex,
          task_index: taskIndex,
          task_name: newTask,
          start_time: newStart,
          duration_minutes: newDuration
        };

        for (const key in fields) {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = key;
          input.value = fields[key];
          form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
      }
    });
  });
});



// ===========================
// Event Delegation: Edit / Remove Dynamic Items
// ===========================
document.addEventListener("click", async (e) => {
  // 🔻 Remove task
  const removeBtn = e.target.closest(".remove-btn");
  if (removeBtn) {
    e.preventDefault();
    const li = removeBtn.closest("li");
    if (!li) return;

    const ttIndex = li.dataset.timetableIndex;
    const taskIndex = li.dataset.taskIndex;

    if (!confirm("Remove this task?")) return;

    try {
      const res = await fetch("/delete_task", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ timetable_index: ttIndex, task_index: taskIndex })
      });
      const data = await res.json();
      if (data.success) {
        location.reload();
      } else {
        alert("Failed to remove task: " + (data.error || "unknown error"));
      }
    } catch (err) {
      alert("Network error: " + err.message);
    }
    return;
  }

  // ✏️ Edit task
  const editBtn = e.target.closest(".edit-btn");
  if (editBtn) {
    e.preventDefault();
    const li = editBtn.closest("li");
    if (!li) return;

    const ttIndex = li.dataset.timetableIndex;
    const taskIndex = li.dataset.taskIndex;
    const current = li.querySelector("strong")?.innerText || "";
    const newName = prompt("Edit task name:", current);

    if (!newName || newName.trim() === current) return;

    try {
      const res = await fetch("/edit_task", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          timetable_index: ttIndex,
          task_index: taskIndex,
          new_name: newName.trim()
        })
      });
      const data = await res.json();
      if (data.success) {
        location.reload();
      } else {
        alert("Failed to edit task: " + (data.error || "unknown error"));
      }
    } catch (err) {
      alert("Network error: " + err.message);
    }
  }
});


// ===========================
// Add File -> Load content into #code
// ===========================
document.getElementById("fileInput").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;

  try {
    const text = await file.text();
    document.getElementById("code").value = text;
  } catch (err) {
    alert("Error reading file: " + err.message);
  }
});



document.addEventListener("click", async (e) => {
  if (e.target.id === "btnGenTimetable") {
    const code = document.getElementById("code").value.trim();
    const concepts = [...document.querySelectorAll("#contextual-output span")]
      .map(s => s.innerText)
      .join(", ");

    if (!code) return alert("Please paste your code first!");

    try {
      const res = await fetch("/generate_study_timetable", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ code, concepts })
      });
      const data = await res.json();

      if (data.success) {
        alert("Timetable created successfully!");
        window.location.href = "/timetables";
      } else {
        alert("Error: " + (data.error || "unknown"));
      }
    } catch (err) {
      alert("Network error: " + err.message);
    }
  }
});


// ===========================
// Focus Session Logic
// ===========================
let focusTasks = [];
let currentIndex = 0;
let remaining = 0;
let timer = null;
let onBreak = false;

async function startSession() {
  const res = await fetch("/api/get_current_timetable");
  const data = await res.json();
  focusTasks = data.items || [];

  if (!focusTasks.length) {
    alert("No tasks found. Please generate a study timetable first.");
    return;
  }

  document.getElementById("focus-idle").classList.add("hidden");
  document.getElementById("focus-active").classList.remove("hidden");
  currentIndex = 0;
  startTask();
}

function startTask() {
  if (currentIndex >= focusTasks.length) {
    alert("🎉 All tasks completed!");
    resetSession();
    return;
  }
  const task = focusTasks[currentIndex];
  remaining = parseInt(task.minutes) * 60 || 1500; // fallback 25 min
  onBreak = false;
  updateUI();
  runTimer();
}

function startBreak() {
  onBreak = true;
  remaining = 10 * 60; // 10-min break
  document.getElementById("current-task").textContent = "☕ Break Time!";
  runTimer();
}

function runTimer() {
  clearInterval(timer);
  timer = setInterval(() => {
    if (remaining <= 0) {
      clearInterval(timer);
      if (onBreak) {
        currentIndex++;
        startTask();
      } else {
        startBreak();
      }
      return;
    }
    remaining--;
    updateUI();
  }, 1000);
}

function updateUI() {
  const mins = String(Math.floor(remaining / 60)).padStart(2, '0');
  const secs = String(remaining % 60).padStart(2, '0');
  document.getElementById("timer").textContent = `${mins}:${secs}`;
  if (!onBreak)
    document.getElementById("current-task").textContent = focusTasks[currentIndex].task;
}

function resetSession() {
  clearInterval(timer);
  document.getElementById("focus-active").classList.add("hidden");
  document.getElementById("focus-idle").classList.remove("hidden");
}

document.getElementById("startFocusBtn").onclick = startSession;
let paused = false;

document.getElementById("pauseBtn").onclick = () => {
  if (!paused) {
    clearInterval(timer);
    paused = true;
    document.getElementById("pauseBtn").textContent = "▶️ Resume";
  } else {
    runTimer();
    paused = false;
    document.getElementById("pauseBtn").textContent = "⏸ Pause";
  }
};

document.getElementById("stopBtn").onclick = resetSession;
document.getElementById("restartBtn").onclick = () => startTask();



async function deleteTimetable(index) {
  if (!confirm("Delete this entire timetable?")) return;
  const res = await fetch(`/delete_timetable/${index}`, { method: "POST" });
  const data = await res.json();
  if (data.success) location.reload();
}

async function deleteTask(tableIndex, taskIndex) {
  if (!confirm("Delete this task?")) return;
  const res = await fetch(`/delete_task/${tableIndex}/${taskIndex}`, { method: "POST" });
  const data = await res.json();
  if (data.success) location.reload();
}


async function deleteTimetable(index) {
  if (!confirm("Delete this timetable?")) return;
  const res = await fetch("/delete_timetable", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({timetable_index: index})
  });
  const data = await res.json();
  if (data.success) location.reload();
  else alert("Failed to delete timetable");
}

async function deleteTask(tableIndex, taskIndex) {
  if (!confirm("Delete this task?")) return;
  const res = await fetch("/delete_task", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({timetable_index: tableIndex, task_index: taskIndex})
  });
  const data = await res.json();
  if (data.success) location.reload();
  else alert("Failed to delete task");
}


