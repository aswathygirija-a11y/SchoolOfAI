const statusEl = document.getElementById("status");
const openBtn = document.getElementById("openRecorder");

function setStatus(message) {
  statusEl.textContent = message ?? "";
}

openBtn.addEventListener("click", async () => {
  setStatus("");
  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });
    if (!tab?.id) {
      setStatus("No active tab found.");
      return;
    }
    const url = new URL(chrome.runtime.getURL("recorder.html"));
    url.searchParams.set("tabId", String(tab.id));
    await chrome.windows.create({
      url: url.href,
      type: "popup",
      width: 420,
      height: 280,
      focused: true,
    });
    window.close();
  } catch (err) {
    setStatus(err instanceof Error ? err.message : String(err));
  }
});
