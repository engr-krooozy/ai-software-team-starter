const ideaInput = document.getElementById("idea");
const buildBtn = document.getElementById("build-btn");
const teamPanel = document.getElementById("team-panel");
const resultPanel = document.getElementById("result-panel");
const timeline = document.getElementById("timeline");
const previewFrame = document.getElementById("preview-frame");
const codeView = document.getElementById("code-view");
const planView = document.getElementById("plan-view");
const downloadBtn = document.getElementById("download-btn");

let sessionId = null;
let productHtml = null;

// Example chips fill the textarea
document.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    ideaInput.value = chip.dataset.idea;
    ideaInput.focus();
  });
});

// Tab switching
document.querySelectorAll(".tab").forEach((tab) => {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelectorAll(".tab-content").forEach((c) => c.classList.add("hidden"));
    document.getElementById(`tab-${tab.dataset.tab}`).classList.remove("hidden");
  });
});

downloadBtn.addEventListener("click", () => {
  if (!productHtml) return;
  const blob = new Blob([productHtml], { type: "text/html" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "product.html";
  a.click();
  URL.revokeObjectURL(a.href);
});

function logLine(text, cls) {
  const li = document.createElement("li");
  li.textContent = text;
  if (cls) li.classList.add(cls);
  timeline.appendChild(li);
  timeline.scrollTop = timeline.scrollHeight;
}

function setMemberState(agent, state) {
  const member = document.getElementById(`member-${agent}`);
  if (!member) return;
  member.classList.remove("active", "done");
  if (state === "active") member.classList.add("active");
  if (state === "done") member.classList.add("done");
  member.querySelector(".state").textContent = state;
}

function resetUI() {
  timeline.innerHTML = "";
  ["planner", "builder", "reviewer", "orchestrator"].forEach((a) => setMemberState(a, "idle"));
  teamPanel.classList.remove("hidden");
  resultPanel.classList.add("hidden");
  productHtml = null;
}

buildBtn.addEventListener("click", async () => {
  const idea = ideaInput.value.trim();
  if (!idea) {
    ideaInput.focus();
    return;
  }

  resetUI();
  buildBtn.disabled = true;
  buildBtn.textContent = "⏳ The team is working...";
  setMemberState("orchestrator", "active");
  logLine("🎯 Orchestrator kicked off the pipeline.");

  try {
    const response = await fetch("/api/build_stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: idea, session_id: sessionId }),
    });
    if (!response.ok) throw new Error(`Server error: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let currentAgent = null;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep incomplete last line in the buffer

      for (const line of lines) {
        if (!line.trim()) continue;
        const event = JSON.parse(line);

        if (event.type === "session") {
          sessionId = event.session_id;
        } else if (event.type === "status") {
          if (currentAgent) setMemberState(currentAgent, "done");
          currentAgent = event.agent;
          setMemberState(event.agent, "active");
          logLine(event.text);
        } else if (event.type === "plan") {
          planView.textContent = event.text;
        } else if (event.type === "review") {
          const passed = event.status === "pass";
          logLine(
            passed
              ? `✅ Review iteration ${event.iteration}: PASS — ${event.feedback}`
              : `❌ Review iteration ${event.iteration}: FAIL — sending back to the Builder`,
            passed ? "pass" : "fail"
          );
        } else if (event.type === "result") {
          if (currentAgent) setMemberState(currentAgent, "done");
          setMemberState("orchestrator", "done");
          if (event.html) {
            productHtml = event.html;
            previewFrame.srcdoc = event.html;
            codeView.textContent = event.html;
            resultPanel.classList.remove("hidden");
            logLine(`🚢 Shipped after ${event.iterations} build iteration(s).`, "pass");
          } else {
            logLine("⚠️ The builder did not return a usable HTML file. Raw output shown in the Code tab.", "fail");
            codeView.textContent = event.raw || "(empty response)";
            resultPanel.classList.remove("hidden");
          }
        }
      }
    }
  } catch (err) {
    logLine(`💥 Error: ${err.message}`, "fail");
  } finally {
    buildBtn.disabled = false;
    buildBtn.textContent = "🚀 Build it";
  }
});
