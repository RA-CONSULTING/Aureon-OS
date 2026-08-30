"use strict";

const PRACTICE_TEXT = "local practice note";
const screens = Array.from(document.querySelectorAll(".screen"));
const progress = document.querySelector("#progress");
const lesson = document.querySelector("#lesson-screen");
const lessonNext = document.querySelector("#lesson-next");
const sentinel = document.querySelector("#lesson-scroll-sentinel");
const practiceInput = document.querySelector("#practice-input");
const practiceNext = document.querySelector("#practice-next");
const practiceStatus = document.querySelector("#practice-status");

const progressText = {
  "start-screen": "Step 1 of 4",
  "lesson-screen": "Step 2 of 4",
  "practice-screen": "Step 3 of 4",
  "sandbox-screen": "Step 4 of 4",
  "completion-screen": "Complete"
};

function showScreen(screenId) {
  for (const screen of screens) {
    screen.hidden = screen.id !== screenId;
  }
  document.body.dataset.screen = screenId;
  progress.textContent = progressText[screenId];
  window.scrollTo({ top: 0, left: 0, behavior: "instant" });
}

function markLessonScrolled() {
  lesson.dataset.scrollComplete = "true";
  lessonNext.disabled = false;
}

function updateScrollGate() {
  if (lesson.hidden || lesson.dataset.scrollComplete === "true") {
    return;
  }
  const reachedBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 8;
  if (reachedBottom) {
    markLessonScrolled();
  }
}

document.querySelector("#start-course").addEventListener("click", () => {
  showScreen("lesson-screen");
  updateScrollGate();
});

window.addEventListener("scroll", updateScrollGate, { passive: true });

if ("IntersectionObserver" in window) {
  const observer = new IntersectionObserver((entries) => {
    if (!lesson.hidden && entries.some((entry) => entry.isIntersecting)) {
      markLessonScrolled();
    }
  });
  observer.observe(sentinel);
}

lessonNext.addEventListener("click", () => {
  if (!lessonNext.disabled) {
    showScreen("practice-screen");
    practiceInput.focus();
  }
});

practiceInput.addEventListener("input", () => {
  const exact = practiceInput.value === PRACTICE_TEXT;
  practiceNext.disabled = !exact;
  practiceStatus.textContent = exact
    ? "Practice phrase matched."
    : "Waiting for the exact practice phrase.";
});

practiceNext.addEventListener("click", () => {
  if (!practiceNext.disabled) {
    showScreen("sandbox-screen");
  }
});

document.querySelector("#complete-sandbox").addEventListener("click", () => {
  document.body.dataset.benchmarkStatus = "completed";
  showScreen("completion-screen");
});

document.querySelector("#reset-benchmark").addEventListener("click", () => {
  lesson.dataset.scrollComplete = "false";
  lessonNext.disabled = true;
  practiceInput.value = "";
  practiceNext.disabled = true;
  practiceStatus.textContent = "Waiting for the exact practice phrase.";
  document.body.dataset.benchmarkStatus = "ready";
  showScreen("start-screen");
});

