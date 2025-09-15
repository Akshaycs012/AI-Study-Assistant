// static/youtube.js

window.addEventListener("DOMContentLoaded", () => {
  // Get concepts from SERVER_CONCEPTS (from HTML template) or URL params
  const params = new URLSearchParams(window.location.search);
  const conceptsFromUrl = params.get("concepts");
  const concepts = (typeof SERVER_CONCEPTS !== "undefined" && SERVER_CONCEPTS) 
                   ? SERVER_CONCEPTS 
                   : (conceptsFromUrl || "");

  const topicLabel = document.getElementById("topic-label");
  const videoGrid = document.getElementById("video-grid");

  // Add a fallback link element in case API fails
  const fallbackEl = document.createElement("p");
  fallbackEl.id = "youtube-fallback";
  fallbackEl.className = "mt-4 text-blue-400";
  document.body.appendChild(fallbackEl);

  // If no concepts provided, show message and stop
  if (!concepts || concepts.trim() === "") {
    topicLabel.innerText = "No key concepts provided.";
    return;
  }

  topicLabel.innerText = `Searching: ${concepts}`;

  // Send POST request to backend to fetch YouTube videos
  fetch("/get_youtube_videos", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ concepts })
  })
  .then(async res => {
    // Try to parse JSON response
    const data = await res.json().catch(() => null);
    if (!res.ok) {
      throw new Error(data && data.error ? data.error : `Server returned ${res.status}`);
    }
    return data;
  })
  .then(data => {
    if (!data.videos || data.videos.length === 0) {
      topicLabel.innerText = "No videos found.";
      fallbackEl.innerHTML = `<a href="https://www.youtube.com/results?search_query=${encodeURIComponent(concepts)}" target="_blank">Open YouTube search for this topic</a>`;
      return;
    }

    // Clear previous videos (if any)
    videoGrid.innerHTML = "";

    // Render each video in grid
    data.videos.forEach(video => {
      const vidDiv = document.createElement("div");
      vidDiv.className = "bg-gray-800 p-2 rounded shadow";
      vidDiv.innerHTML = `
        <iframe width="100%" height="200" 
                src="https://www.youtube.com/embed/${video.id}" 
                frameborder="0" allowfullscreen></iframe>
        <h2 class="mt-2 text-lg">${video.title}</h2>
      `;
      videoGrid.appendChild(vidDiv);
    });
  })
  .catch(err => {
    // Show error and fallback link
    topicLabel.innerText = "Error: " + err.message;
    console.error("YouTube fetch failed:", err);
    fallbackEl.innerHTML = `<a href="https://www.youtube.com/results?search_query=${encodeURIComponent(concepts)}" target="_blank">Open YouTube search for this topic</a>`;
  });
});
