// Typing test.  Owner: Lucas (L3, L4, L5, L6, L7, L8, L9).
//
// The file has two parts:
//   1. TypingTest - the rules of the test (no web page code), so it can be tested on its own.
//   2. Page code  - connects TypingTest to test.html: colours, timer, buttons, sending the result.
//
// Following the typing test flowchart, every key press moves on to the next letter.
// A right key turns the letter green; a wrong key turns it red and records a mistake
// for the key that SHOULD have been pressed. There is no going back with Backspace,
// so correct key presses always equal correct characters.

"use strict";

const CHARACTERS_PER_WORD = 5;

// Round to 1 decimal place, the same as the server (L5).
function round1(number) {
  return Math.round(number * 10) / 10;
}

// The name a character is stored under in key_errors: "a" to "z", "space",
// or null for numbers and punctuation (which George's tips do not cover).
function keyName(character) {
  if (character === " ") return "space";
  if (/^[a-z]$/i.test(character)) return character.toLowerCase();
  return null;
}

class TypingTest {
  constructor(text, level) {
    this.text = text;
    this.level = level;
    this.position = 0;      // index of the next letter to type
    this.correct = 0;       // correct key presses
    this.total = 0;         // all key presses
    this.keyErrors = {};    // {"e": {presses: 20, errors: 5}, ...}
  }

  // Process one key press. Returns true if it was the right letter.
  type(character) {
    const expected = this.text[this.position];
    const isCorrect = character === expected;

    this.total += 1;
    if (isCorrect) this.correct += 1;

    const name = keyName(expected);
    if (name !== null) {
      const counts = this.keyErrors[name] || (this.keyErrors[name] = { presses: 0, errors: 0 });
      counts.presses += 1;
      if (!isCorrect) counts.errors += 1;
    }

    this.position += 1;
    return isCorrect;
  }

  // L6: the passage is finished when every letter has been typed.
  isFinished() {
    return this.position >= this.text.length;
  }

  // WPM = (correct characters / 5) / minutes taken
  wpm(seconds) {
    if (seconds <= 0) return 0;
    return round1(this.correct / CHARACTERS_PER_WORD / (seconds / 60));
  }

  // Accuracy = correct key presses / total key presses x 100
  accuracy() {
    if (this.total === 0) return 0;
    return round1((this.correct / this.total) * 100);
  }

  // L7: the JSON sent to POST /result. The server checks these numbers and
  // recalculates WPM and accuracy itself before saving.
  toResult(seconds) {
    return {
      wpm: this.wpm(seconds),
      accuracy: this.accuracy(),
      level: this.level,
      key_errors: this.keyErrors,
      correct: this.correct,
      total: this.total,
      seconds: round1(seconds),
    };
  }
}

// Lets Node.js load TypingTest for testing. Browsers skip this line.
if (typeof module !== "undefined") module.exports = { TypingTest, keyName, round1 };

// ---------------------------------------------------------------------------
// Page code: only runs in the browser on the typing test page.
// ---------------------------------------------------------------------------

if (typeof document !== "undefined" && document.getElementById("typing-test")) {
  const page = document.getElementById("typing-test");
  const passageBox = document.getElementById("passage");
  const input = document.getElementById("typing-input");
  const timeLeftDisplay = document.getElementById("time-left");
  const wpmDisplay = document.getElementById("live-wpm");
  const accuracyDisplay = document.getElementById("live-accuracy");
  const statusLine = document.getElementById("status");
  const restartButton = document.getElementById("restart");
  const levelButtons = document.querySelectorAll("button.level");

  const TEST_SECONDS = Number(page.dataset.seconds);
  const passageUrl = page.dataset.passageUrl;
  const resultUrl = page.dataset.resultUrl;
  const startMessage = statusLine.textContent;

  let test;              // the current TypingTest
  let letterSpans;       // one <span> per letter of the passage
  let startTime = null;  // when the first key was pressed
  let timerId = null;
  let ended = false;
  let typedText = "";    // what the input box should show

  // Show a new passage and reset everything (used on load, by Restart and by the level buttons).
  function setUpTest(text, level) {
    clearInterval(timerId);
    test = new TypingTest(text, level);
    startTime = null;
    timerId = null;
    ended = false;
    typedText = "";

    // One span per letter, so each letter can be coloured on its own.
    passageBox.replaceChildren();
    letterSpans = Array.from(text, (character) => {
      const span = document.createElement("span");
      span.textContent = character;
      passageBox.appendChild(span);
      return span;
    });
    letterSpans[0].classList.add("current");

    input.value = "";
    input.disabled = false;
    restartButton.disabled = false;
    timeLeftDisplay.textContent = formatTime(TEST_SECONDS);
    wpmDisplay.textContent = "-";
    accuracyDisplay.textContent = "-";
    statusLine.textContent = startMessage;
    statusLine.classList.remove("error");
    levelButtons.forEach((button) => {
      const selected = button.dataset.level === level;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    input.focus();
  }

  // 42 -> "0:42"
  function formatTime(seconds) {
    const whole = Math.max(0, Math.ceil(seconds));
    return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
  }

  function secondsTaken() {
    return Math.min((performance.now() - startTime) / 1000, TEST_SECONDS);
  }

  function updateLiveStats() {
    // Use at least 1 second so the WPM does not jump to a silly number on the first key.
    wpmDisplay.textContent = test.wpm(Math.max(secondsTaken(), 1));
    accuracyDisplay.textContent = `${test.accuracy()}%`;
  }

  // L4: called 10 times a second once the timer has started.
  function tick() {
    const remaining = TEST_SECONDS - secondsTaken();
    timeLeftDisplay.textContent = formatTime(remaining);
    updateLiveStats();
    if (remaining <= 0) endTest();
  }

  function handleCharacter(character) {
    // L4: the timer starts on the first key press, not when the page loads.
    if (startTime === null) {
      startTime = performance.now();
      timerId = setInterval(tick, 100);
    }

    // L3: colour the letter, then move the cursor on.
    const span = letterSpans[test.position];
    const isCorrect = test.type(character);
    span.classList.remove("current");
    span.classList.add(isCorrect ? "correct" : "incorrect");
    if (!test.isFinished()) letterSpans[test.position].classList.add("current");

    typedText += character;
    input.value = typedText;
    input.scrollLeft = input.scrollWidth; // keep the newest letters in view
    updateLiveStats();

    // L6: finishing the passage ends the test early.
    if (test.isFinished()) endTest();
  }

  // L6, L7: stop the test and send the result to the server.
  async function endTest() {
    if (ended) return;
    ended = true;
    clearInterval(timerId);
    input.disabled = true;
    restartButton.disabled = true;

    const seconds = secondsTaken();
    timeLeftDisplay.textContent = formatTime(TEST_SECONDS - seconds);
    wpmDisplay.textContent = test.wpm(seconds);
    accuracyDisplay.textContent = `${test.accuracy()}%`;
    statusLine.textContent = "Test finished! Saving your result...";

    try {
      const response = await fetch(resultUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(test.toResult(seconds)),
      });
      const reply = await response.json();
      if (!response.ok) throw new Error(reply.error);
      window.location.href = reply.redirect;
    } catch (problem) {
      statusLine.textContent =
        (problem.message || "Your result could not be saved.") + " Press Restart to try again.";
      statusLine.classList.add("error");
      restartButton.disabled = false;
    }
  }

  // L2, L8: ask the server for a new random passage at this level.
  async function loadNewPassage(level) {
    restartButton.disabled = true;
    try {
      const response = await fetch(passageUrl.replace("LEVEL", level));
      if (!response.ok) throw new Error();
      const passage = await response.json();
      setUpTest(passage.text, passage.level);
    } catch {
      statusLine.textContent = "Could not load a new passage. Check you are still logged in.";
      statusLine.classList.add("error");
      restartButton.disabled = false;
    }
  }

  input.addEventListener("keydown", (event) => {
    if (ended) return;
    // Let shortcuts like Ctrl+R through, but Ctrl+V/Cmd+V is blocked by the paste handler below.
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    // No going back: Backspace and Delete do nothing.
    if (event.key === "Backspace" || event.key === "Delete") {
      event.preventDefault();
      return;
    }
    // Only single printable characters count (not Shift, arrows, Tab and so on).
    if (event.key.length !== 1) return;
    event.preventDefault();
    handleCharacter(event.key);
  });

  // L9: block pasting, dragging text in and the right-click menu.
  ["paste", "drop", "contextmenu"].forEach((eventName) =>
    input.addEventListener(eventName, (event) => event.preventDefault()),
  );
  // Safety net: if anything else changes the box (autofill, other keyboards),
  // put back exactly what was typed through the test.
  input.addEventListener("input", () => {
    input.value = typedText;
  });

  // Clicking on the passage puts the cursor in the typing box.
  passageBox.addEventListener("click", () => input.focus());

  restartButton.addEventListener("click", () => loadNewPassage(test.level));
  levelButtons.forEach((button) =>
    button.addEventListener("click", () => loadNewPassage(button.dataset.level)),
  );

  setUpTest(page.dataset.text, page.dataset.level);
}
