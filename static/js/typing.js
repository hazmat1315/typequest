// Typing engine.  Owner: Lucas (L3-L9, L19, L20).
//
// The file has three parts:
//   1. TypingTest - the rules of typing a passage (no web page code), so it can be tested on its own.
//   2. TypingBox  - connects a TypingTest to a passage box and a typing input: colours each
//                   letter, handles Backspace and blocks paste. Reused by George's practice
//                   page (practice.js, G12) instead of copying this code.
//   3. Page code  - the typing test page (test.html): timer, buttons, sending the result.
//
// Following the typing test flowchart, every key press moves on to the next letter.
// A right key turns the letter green; a wrong key turns it red and records a mistake
// for the key that SHOULD have been pressed.
//
// L20 (Iteration 3): Backspace takes back the last letter so it can be typed again. The
// mistake still counts for accuracy and the heatmap, so fixing it doesn't hide it. This
// means there are two different "correct" numbers:
//   correct    = correct key presses, used for accuracy
//   characters = letters that are right in the finished text, used for WPM

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
    this.total = 0;         // all key presses (not counting Backspace)
    this.keyErrors = {};    // {"e": {presses: 20, errors: 5}, ...}
    this.marks = [];        // true or false for each letter typed so far (right or wrong)
    this.stopped = false;   // L19: true once time is up, so no more keys are counted
  }

  // Process one key press. Returns true if it was the right letter, or null if it was
  // ignored because the test is over.
  type(character) {
    if (this.stopped || this.isFinished()) return null;
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

    this.marks.push(isCorrect);
    this.position += 1;
    return isCorrect;
  }

  // L20: take back the last letter. Returns false if there is nothing to take back.
  // The key press and any mistake have already been counted, so they stay counted.
  backspace() {
    if (this.stopped || this.position === 0) return false;
    this.marks.pop();
    this.position -= 1;
    return true;
  }

  // L19: time is up, so ignore any more keys.
  stop() {
    this.stopped = true;
  }

  // Letters that are right in the text as it is now (mistakes fixed with Backspace count).
  characters() {
    return this.marks.filter((mark) => mark).length;
  }

  // L6: the passage is finished when every letter has been typed.
  isFinished() {
    return this.position >= this.text.length;
  }

  // WPM = (correct characters / 5) / minutes taken
  wpm(seconds) {
    if (seconds <= 0) return 0;
    return round1(this.characters() / CHARACTERS_PER_WORD / (seconds / 60));
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
      characters: this.characters(),
      seconds: round1(seconds),
    };
  }
}

// ---------------------------------------------------------------------------
// TypingBox: the typing input and coloured passage, shared by the test and practice pages.
// ---------------------------------------------------------------------------

class TypingBox {
  // passageBox: the element that shows the passage; input: the <input> students type in.
  // handlers (all optional): onFirstKey(), onKey(isCorrect), onFinish(), and
  // allowKey(), which can return false to ignore a key (L19: the timer has run out).
  constructor(passageBox, input, handlers = {}) {
    this.passageBox = passageBox;
    this.input = input;
    this.handlers = handlers;
    this.test = null;
    this.letterSpans = [];
    this.typedText = "";   // what the input box should show
    this.stopped = true;

    input.addEventListener("keydown", (event) => this.keydown(event));
    // L9: block pasting, dragging text in and the right-click menu.
    ["paste", "drop", "contextmenu"].forEach((eventName) =>
      input.addEventListener(eventName, (event) => event.preventDefault()),
    );
    // Safety net: if anything else changes the box (autofill, other keyboards),
    // put back exactly what was typed through the test.
    input.addEventListener("input", () => {
      input.value = this.typedText;
    });
    // Clicking on the passage puts the cursor in the typing box.
    passageBox.addEventListener("click", () => input.focus());
  }

  // Show a new passage and get ready for the first key.
  load(text, level) {
    this.test = new TypingTest(text, level);
    this.typedText = "";
    this.stopped = false;

    // One span per letter, so each letter can be coloured on its own.
    this.passageBox.replaceChildren();
    this.letterSpans = Array.from(text, (character) => {
      const span = document.createElement("span");
      span.textContent = character;
      this.passageBox.appendChild(span);
      return span;
    });
    this.letterSpans[0].classList.add("current");

    this.input.value = "";
    this.input.disabled = false;
    this.input.focus();
  }

  // No more typing (the test or drill is over).
  stop() {
    this.stopped = true;
    if (this.test) this.test.stop();
    this.input.disabled = true;
  }

  keydown(event) {
    if (this.stopped) return;
    // Let shortcuts like Ctrl+R through, but Ctrl+V/Cmd+V is blocked by the paste handler.
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    const isBackspace = event.key === "Backspace";
    // Only Backspace and single printable characters count (not Shift, arrows, Tab and so on).
    // Delete is blocked too, because there is never anything after the cursor.
    if (!isBackspace && event.key !== "Delete" && event.key.length !== 1) return;
    event.preventDefault();
    if (event.key === "Delete") return;
    // L19: a key pressed after the timer reached 0:00 is not counted.
    if (this.handlers.allowKey && !this.handlers.allowKey()) return;
    if (isBackspace) this.backspace();
    else this.typeCharacter(event.key);
  }

  // L20: un-colour the last letter and move the cursor back onto it.
  backspace() {
    const test = this.test;
    if (!test.backspace()) return;
    if (test.position + 1 < this.letterSpans.length) {
      this.letterSpans[test.position + 1].classList.remove("current");
    }
    const span = this.letterSpans[test.position];
    span.classList.remove("correct", "incorrect");
    span.classList.add("current");
    this.typedText = this.typedText.slice(0, -1);
    this.input.value = this.typedText;
    if (this.handlers.onKey) this.handlers.onKey(null);
  }

  typeCharacter(character) {
    const test = this.test;
    if (test.total === 0 && this.handlers.onFirstKey) this.handlers.onFirstKey();

    // L3: colour the letter, then move the cursor on.
    const span = this.letterSpans[test.position];
    const isCorrect = test.type(character);
    if (isCorrect === null) return;
    span.classList.remove("current");
    span.classList.add(isCorrect ? "correct" : "incorrect");
    if (!test.isFinished()) this.letterSpans[test.position].classList.add("current");

    this.typedText += character;
    this.input.value = this.typedText;
    this.input.scrollLeft = this.input.scrollWidth; // keep the newest letters in view
    if (this.handlers.onKey) this.handlers.onKey(isCorrect);

    // L6: finishing the passage ends early.
    if (test.isFinished() && this.handlers.onFinish) this.handlers.onFinish();
  }
}

// Lets Node.js load TypingTest for testing. Browsers skip this line.
if (typeof module !== "undefined") module.exports = { TypingTest, TypingBox, keyName, round1 };

// ---------------------------------------------------------------------------
// Page code: only runs in the browser on the typing test page.
// ---------------------------------------------------------------------------

if (typeof document !== "undefined" && document.getElementById("typing-test")) {
  const page = document.getElementById("typing-test");
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

  let startTime = null;  // when the first key was pressed
  let timerId = null;
  let ended = false;

  const box = new TypingBox(document.getElementById("passage"), document.getElementById("typing-input"), {
    // L4: the timer starts on the first key press, not when the page loads.
    onFirstKey() {
      startTime = performance.now();
      timerId = setInterval(tick, 100);
    },
    onKey: updateLiveStats,
    onFinish: endTest,
    // L19: the timer only checks 10 times a second, so a key pressed in the moment after
    // 0:00 could sneak in. Checking the clock on every key stops that and ends the test.
    allowKey() {
      if (startTime !== null && secondsTaken() >= TEST_SECONDS) {
        endTest();
        return false;
      }
      return true;
    },
  });

  // Show a new passage and reset everything (used on load, by Restart and by the level buttons).
  function setUpTest(text, level) {
    clearInterval(timerId);
    startTime = null;
    timerId = null;
    ended = false;
    box.load(text, level);

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
    wpmDisplay.textContent = box.test.wpm(Math.max(secondsTaken(), 1));
    accuracyDisplay.textContent = `${box.test.accuracy()}%`;
  }

  // L4: called 10 times a second once the timer has started.
  function tick() {
    const remaining = TEST_SECONDS - secondsTaken();
    timeLeftDisplay.textContent = formatTime(remaining);
    updateLiveStats();
    if (remaining <= 0) endTest();
  }

  // L6, L7: stop the test and send the result to the server.
  async function endTest() {
    if (ended) return;
    ended = true;
    clearInterval(timerId);
    box.stop();
    restartButton.disabled = true;

    const test = box.test;
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

  restartButton.addEventListener("click", () => loadNewPassage(box.test.level));
  levelButtons.forEach((button) =>
    button.addEventListener("click", () => loadNewPassage(button.dataset.level)),
  );

  setUpTest(page.dataset.text, page.dataset.level);
}
