const preview = document.getElementById("preview");
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const statusEl = document.getElementById("status");
const metaEl = document.getElementById("meta");

const params = new URLSearchParams(window.location.search);
const tabIdParam = params.get("tabId");
const tabId = tabIdParam ? Number(tabIdParam) : NaN;

/** @type {MediaStream | null} */
let captureStream = null;
/** @type {MediaRecorder | null} */
let recorder = null;
const chunks = [];

function setStatus(message, isError = false) {
  statusEl.textContent = message ?? "";
  statusEl.classList.toggle("error", Boolean(isError));
}

async function getTabCaptureStream() {
  if (!Number.isInteger(tabId)) {
    throw new Error("Missing or invalid tab id.");
  }

  if (chrome.tabCapture.getMediaStreamId) {
    const streamId = await chrome.tabCapture.getMediaStreamId({
      targetTabId: tabId,
    });
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        mandatory: {
          chromeMediaSource: "tab",
          chromeMediaSourceId: streamId,
        },
      },
      video: {
        mandatory: {
          chromeMediaSource: "tab",
          chromeMediaSourceId: streamId,
        },
      },
    });
    return stream;
  }

  return new Promise((resolve, reject) => {
    chrome.tabCapture.capture({ audio: true, video: true }, (stream) => {
      const err = chrome.runtime.lastError;
      if (err) {
        reject(new Error(err.message));
        return;
      }
      if (!stream) {
        reject(new Error("Tab capture failed (no stream)."));
        return;
      }
      resolve(stream);
    });
  });
}

function pickMimeType() {
  const candidates = [
    "video/webm;codecs=vp9,opus",
    "video/webm;codecs=vp8,opus",
    "video/webm",
  ];
  for (const t of candidates) {
    if (MediaRecorder.isTypeSupported(t)) return t;
  }
  return "";
}

startBtn.addEventListener("click", async () => {
  setStatus("");
  chunks.length = 0;
  try {
    captureStream = await getTabCaptureStream();
    preview.srcObject = captureStream;

    const mimeType = pickMimeType();
    const options = mimeType ? { mimeType } : undefined;
    recorder = new MediaRecorder(captureStream, options);

    recorder.ondataavailable = (e) => {
      if (e.data && e.data.size > 0) chunks.push(e.data);
    };

    recorder.onerror = (e) => {
      setStatus(e.error?.message ?? "Recording error.", true);
    };

    recorder.start(1000);
    startBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus("Recording…");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
    await stopCapture();
  }
});

async function stopCapture() {
  if (recorder && recorder.state !== "inactive") {
    await new Promise((resolve) => {
      recorder.addEventListener("stop", resolve, { once: true });
      recorder.stop();
    });
  }
  recorder = null;

  if (captureStream) {
    captureStream.getTracks().forEach((t) => t.stop());
    captureStream = null;
  }
  preview.srcObject = null;
}

stopBtn.addEventListener("click", async () => {
  try {
    stopBtn.disabled = true;
    await stopCapture();
    startBtn.disabled = false;

    if (chunks.length === 0) {
      setStatus("No data recorded.", true);
      return;
    }

    const blob = new Blob(chunks, { type: chunks[0].type || "video/webm" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const stamp = new Date().toISOString().replace(/[:.]/g, "-");
    a.href = url;
    a.download = `session-recording-${stamp}.webm`;
    a.click();
    URL.revokeObjectURL(url);
    setStatus("Saved. You can close this window.");
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    setStatus(msg, true);
    startBtn.disabled = false;
  }
});

(async function init() {
  if (!Number.isInteger(tabId)) {
    metaEl.textContent = "Open this page from the extension popup (tab id missing).";
    startBtn.disabled = true;
    return;
  }

  try {
    const tab = await chrome.tabs.get(tabId);
    metaEl.textContent = `Tab: ${tab.title ?? "(no title)"}`;
  } catch {
    metaEl.textContent = `Tab id: ${tabId}`;
  }
})();
