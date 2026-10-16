// Adaptive practice drill page.  Owner: George (G11, G12, G13, G14, F7).
//
// Typing input and letter colouring come from Lucas's TypingBox in typing.js (loaded
// first on the page), so the drill works exactly like the typing test. There is no
// timer: the drill ends when every word is typed or the student presses Finish.

"use strict";

if (document.getElementById("practice")) {
  const page = document.getElementById("practice");
  const drillUrl = page.dataset.drillUrl;
  const resultUrl = page.dataset.resultUrl;

  const weakKeysList = document.getElementById("weak-keys");
  const message = document.getElementById("drill-message");
  const progressBar = document.getElementById("drill-progress");
  const statusLine = document.getElementById("drill-status");
  const newDrillButton = document.getElementById("new-drill");
  const finishButton = document.getElementById("finish");
  const resultsPanel = document.getElementById("drill-results");
  const startMessage = statusLine.textContent;

  // 25 -> "25.0", the same as the tips on the results page
  const oneDecimal = (number) => Number(number).toFixed(1);

  let startTime = null;
  let finished = false;

  const box = new TypingBox(document.getElementById("drill-passage"), document.getElementById("drill-input"), {
    onFirstKey() {
      startTime = performance.now();
    },
    onKey() {
      progressBar.value = box.test.position;
    },
    onFinish: finishDrill,
  });

  function setUpDrill(drill) {
    box.load(drill.text, null);
    startTime = null;
    finished = false;
    progressBar.max = drill.text.length;
    progressBar.value = 0;
    message.textContent = drill.message;
    statusLine.textContent = startMessage;
    statusLine.classList.remove("error");
    finishButton.disabled = false;
    resultsPanel.hidden = true;
    drawWeakKeys(drill.weak_keys);
    drawFingerGuide(drill.finger_guide);
  }

  // F7: highlight the fingers and keys for this drill's focus keys, and list what to do.
  function drawFingerGuide(guide) {
    const section = document.getElementById("finger-guide");
    const weakKeys = new Set(guide.keyboard.flat().filter((key) => key.weak).map((key) => key.name));
    const weakFingers = new Set(guide.hands.filter((finger) => finger.weak).map((finger) => finger.id));
    section.querySelectorAll("[data-key]").forEach((element) =>
      element.classList.toggle("weak", weakKeys.has(element.dataset.key)),
    );
    section.querySelectorAll("[data-finger]").forEach((element) =>
      element.classList.toggle("weak", weakFingers.has(element.dataset.finger)),
    );
    section.classList.toggle("has-weak", guide.steps.length > 0);
    const steps = document.getElementById("finger-steps");
    steps.replaceChildren(
      ...guide.steps.map((step) => {
        const item = document.createElement("li");
        item.textContent = step;
        return item;
      }),
    );
    if (guide.steps.length === 0) {
      const item = document.createElement("li");
      item.className = "none";
      item.textContent = "You don't have any weak keys right now. Hover over or tab to a key to see which finger presses it.";
      steps.appendChild(item);
    }
  }

  // The coloured key boxes at the top, e.g. [E] [R] [O].
  function drawWeakKeys(weakKeys) {
    weakKeysList.replaceChildren(
      ...weakKeys.map((key) => {
        const item = document.createElement("li");
        item.className = `key ${key.band}`;
        item.textContent = key.label;
        item.title = `${key.label}: ${oneDecimal(key.percent)}% wrong`;
        return item;
      }),
    );
    if (weakKeys.length === 0) {
      const item = document.createElement("li");
      item.className = "none";
      item.textContent = "None yet";
      weakKeysList.appendChild(item);
    }
  }

  // G13: send the drill, then show the before and after for each focus key.
  async function finishDrill() {
    if (finished) return;
    if (box.test.total === 0) {
      statusLine.textContent = "Type some of the words first, then press Finish.";
      return;
    }
    finished = true;
    box.stop();
    finishButton.disabled = true;
    statusLine.textContent = "Drill finished! Saving...";

    const seconds = Math.max((performance.now() - startTime) / 1000, 0.1);
    try {
      const response = await fetch(resultUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(box.test.toResult(seconds)),
      });
      const reply = await response.json();
      if (!response.ok) throw new Error(reply.error);
      showResults(reply);
      statusLine.textContent = "Saved! Press New drill to keep practising.";
    } catch (problem) {
      statusLine.textContent = problem.message || "Your drill could not be saved.";
      statusLine.classList.add("error");
    }
    // Focus is NOT moved to the New drill button: found in testing that a key pressed
    // just after the last word (often a space) would "click" it and hide the results.
  }

  function showResults(reply) {
    document.getElementById("drill-wpm").textContent = oneDecimal(reply.wpm);
    document.getElementById("drill-accuracy").textContent = `${oneDecimal(reply.accuracy)}%`;
    const list = document.getElementById("before-after");
    list.replaceChildren(
      ...reply.focus.map((key) => {
        const item = document.createElement("li");
        const after = key.after === null ? "-" : `${oneDecimal(key.after)}%`;
        const better = key.after !== null && key.after < key.before;
        item.textContent = `${key.key}: ${oneDecimal(key.before)}% to ${after}`;
        item.className = better ? "better" : "";
        if (better) item.textContent += " (better!)";
        return item;
      }),
    );
    document.getElementById("before-after-section").hidden = reply.focus.length === 0;
    resultsPanel.hidden = false;
  }

  // G11: every new drill is different.
  async function loadNewDrill() {
    newDrillButton.disabled = true;
    try {
      const response = await fetch(drillUrl);
      if (!response.ok) throw new Error();
      setUpDrill(await response.json());
    } catch {
      statusLine.textContent = "Could not load a new drill. Check you are still logged in.";
      statusLine.classList.add("error");
    }
    newDrillButton.disabled = false;
  }

  newDrillButton.addEventListener("click", loadNewDrill);
  finishButton.addEventListener("click", finishDrill);

  setUpDrill(JSON.parse(page.dataset.drill));
}
