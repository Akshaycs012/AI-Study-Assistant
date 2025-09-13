window.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);
  const code = params.get("code");

  if (!code) {
    document.getElementById("topic-label").innerText = "No code provided.";
    return;
  }

  fetch("/get_youtube_videos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ code })
  })
  .then(res => res.json())
  .then(data => {
    document.getElementById("topic-label").innerText = `Results for: ${data.query}`;

    const grid = document.getElementById("video-grid");
    grid.innerHTML = data.videos.map(v => `
      <div class="bg-gray-800 rounded-xl overflow-hidden shadow-md hover:shadow-lg transition">
        <a href="https://www.youtube.com/watch?v=${v.videoId}" target="_blank">
          <img src="${v.thumbnail}" alt="${v.title}" class="w-full">
          <div class="p-3">
            <p class="font-semibold text-sm text-white">${v.title}</p>
          </div>
        </a>
      </div>
    `).join("");
  })
  .catch(err => {
    document.getElementById("topic-label").innerText = "Error: " + err.message;
  });
});
