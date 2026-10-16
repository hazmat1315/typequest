// Falling words game.  Owner: Lucas (L10-L15, L17, L21, L22, F5, F6).
//
// The file has two parts:
//   1. FallingWordsGame - the rules of the game (no web page code), so they can be tested
//                         with Node. The server has the same rules in models/game.py.
//   2. Page code        - draws the words on game.html, runs the game loop with
//                         requestAnimationFrame, and sends the result at game over.
//
// Words fall from the top. Type a word and press Enter (or Space) to destroy it for
// 10 points. A word that reaches the ground costs a life, and at 0 lives the game is over.

"use strict";

// keyName() and round1() come from typing.js (loaded first on the page), so the game
// records key mistakes exactly the same way as the typing test.
const typingEngine =
  typeof module !== "undefined" ? require("./typing.js") : { keyName, round1 };

const BANDS = ["short", "medium", "long"];

class FallingWordsGame {
  // settings comes from the server (app.py), so both sides use the same numbers.
  // random() can be swapped for a fixed sequence when testing.
  constructor(settings, random = Math.random) {
    this.settings = settings;
    this.random = random;
    this.score = 0;
    this.level = 1;
    this.lives = settings.startLives;
    this.falling = [];      // [{id, text, x, y}]: x and y go from 0 to 1 across the play area
    this.typed = "";        // what is in the input box
    this.seconds = 0;       // time played, not counting pauses
    this.spawnTimer = 0;    // seconds since the last word appeared
    this.nextId = 1;
    this.correct = 0;       // correct key presses
    this.total = 0;         // key presses that were counted
    this.keyErrors = {};    // {"e": {presses: 20, errors: 5}, ...} like the typing test
    this.events = [];       // things the page should show: "matched", "landed", "levelup"
  }

  // L13: fall speed = base speed x 1.15^(level - 1)  (share of the play area per second)
  // F6: slow mode (from the Settings page) makes every word fall at 60% of that speed.
  fallSpeed() {
    const speed = this.settings.baseSpeed * this.settings.speedGrowth ** (this.level - 1);
    return this.settings.slowMode ? speed * this.settings.slowModeSpeed : speed;
  }

  // L13: time between new words = 2.5 / (1 + 0.1 x (level - 1))
  spawnSeconds() {
    return this.settings.baseSpawnSeconds / (1 + 0.1 * (this.level - 1));
  }

  // L14: levels 1-2 use short words, 3-4 medium words, 5 or more long words.
  wordBand() {
    return BANDS[Math.min(Math.floor((this.level - 1) / 2), BANDS.length - 1)];
  }

  // Drop a new word from the top, never the same as one already falling.
  spawn() {
    const onScreen = new Set(this.falling.map((word) => word.text));
    const choices = this.settings.words[this.wordBand()].filter((word) => !onScreen.has(word));
    const text = choices[Math.floor(this.random() * choices.length)];
    // Try a few places so a new word doesn't land on top of one that just appeared.
    let x = 0;
    for (let attempt = 0; attempt < 5; attempt += 1) {
      x = this.random() * 0.8;
      const crowded = this.falling.some((word) => word.y < 0.2 && Math.abs(word.x - x) < 0.2);
      if (!crowded) break;
    }
    const word = { id: this.nextId, text, x, y: 0 };
    this.nextId += 1;
    this.falling.push(word);
    return word;
  }

  // One step of the game loop. dt is the seconds since the last frame.
  update(dt) {
    if (this.isOver()) return;
    this.seconds += dt;
    // The first word appears straight away, then one every spawnSeconds().
    this.spawnTimer += dt;
    if (this.falling.length === 0 && this.nextId === 1) this.spawn();
    if (this.spawnTimer >= this.spawnSeconds()) {
      this.spawnTimer = 0;
      this.spawn();
    }
    const fall = this.fallSpeed() * dt;
    for (const word of [...this.falling]) {
      word.y += fall;
      if (word.y >= 1) this.wordLanded(word);
    }
  }

  // L12: a word reached the ground, so it goes and a life is lost.
  wordLanded(word) {
    this.falling = this.falling.filter((other) => other !== word);
    this.lives -= 1;
    this.events.push({ type: "landed", word });
  }

  // L11: the falling word that matches what has been typed so far (the lowest one if
  // more than one matches), or null.
  target() {
    if (!this.typed) return null;
    return this.lowest(this.falling.filter((word) => word.text.startsWith(this.typed)));
  }

  lowest(words) {
    return words.reduce((best, word) => (best === null || word.y > best.y ? word : best), null);
  }

  // A letter was typed. Like the typing test, a mistake counts against the key that
  // SHOULD have been pressed: the next letter of the word being typed (or, for the
  // first letter, the word closest to the ground).
  type(character) {
    if (this.isOver()) return;
    const next = this.typed + character;
    const anyMatch = this.falling.some((word) => word.text.startsWith(next));
    if (anyMatch) {
      this.count(character, true);
    } else {
      const aimingAt = this.typed ? this.target() : this.lowest(this.falling);
      // After one mistake the typed text matches nothing, so further letters are not
      // counted again until it is fixed with Backspace.
      if (aimingAt && aimingAt.text.length > this.typed.length) {
        this.count(aimingAt.text[this.typed.length], false);
      }
    }
    this.typed = next;
  }

  count(expected, isCorrect) {
    this.total += 1;
    if (isCorrect) this.correct += 1;
    const name = typingEngine.keyName(expected);
    if (name === null) return;
    const counts = this.keyErrors[name] || (this.keyErrors[name] = { presses: 0, errors: 0 });
    counts.presses += 1;
    if (!isCorrect) counts.errors += 1;
  }

  backspace() {
    this.typed = this.typed.slice(0, -1);
  }

  // Enter (or Space) was pressed. Returns true if a word was destroyed.
  submit() {
    const matched = this.checkWord(this.typed);
    this.typed = "";
    return matched;
  }

  // L11: if the word is falling, remove it (the lowest copy) and add 10 points.
  checkWord(text) {
    const word = this.lowest(this.falling.filter((other) => other.text === text));
    if (word === null) return false;
    this.falling = this.falling.filter((other) => other !== word);
    this.score += this.settings.pointsPerWord;
    this.events.push({ type: "matched", word });
    if (this.levelUp()) this.events.push({ type: "levelup", level: this.level });
    return true;
  }

  // F5: words needed to go from this level to the next: 3, then 5, then 7 ...
  wordsToNextLevel(level) {
    return this.settings.firstLevelWords + this.settings.extraWordsPerLevel * (level - 1);
  }

  // F5: the level for a score. Level 2 after 3 words, level 3 after 8, level 4 after 15 ...
  // The same rule as level_for_score() in models/game.py, so the server agrees.
  levelForScore(score) {
    let words = Math.floor(score / this.settings.pointsPerWord);
    let level = 1;
    // Spend the words one level at a time until there aren't enough for the next level.
    while (words >= this.wordsToNextLevel(level)) {
      words -= this.wordsToNextLevel(level);
      level += 1;
    }
    return level;
  }

  // F5: how many more words until the next level (shown under the level number).
  wordsLeftInLevel() {
    let words = Math.floor(this.score / this.settings.pointsPerWord);
    for (let level = 1; level < this.level; level += 1) words -= this.wordsToNextLevel(level);
    return this.wordsToNextLevel(this.level) - words;
  }

  // Move up a level when the score is high enough. Returns true if the level went up.
  levelUp() {
    const newLevel = this.levelForScore(this.score);
    if (newLevel > this.level) {
      this.level = newLevel;
      return true;
    }
    return false;
  }

  // L12: the game is over when there are no lives left.
  isOver() {
    return this.lives <= 0;
  }

  // L15: the JSON sent to POST /game/result. The server checks it is possible.
  toResult() {
    return {
      score: this.score,
      level_reached: this.level,
      correct: this.correct,
      total: this.total,
      seconds: typingEngine.round1(this.seconds),
      key_errors: this.keyErrors,
    };
  }
}

// Lets Node.js load FallingWordsGame for testing. Browsers skip this line.
if (typeof module !== "undefined") module.exports = { FallingWordsGame };

// ---------------------------------------------------------------------------
// Page code: only runs in the browser on the game page.
// ---------------------------------------------------------------------------

if (typeof document !== "undefined" && document.getElementById("game")) {
  const page = document.getElementById("game");
  const settings = JSON.parse(page.dataset.settings);
  const startUrl = page.dataset.startUrl;
  const resultUrl = page.dataset.resultUrl;

  const playArea = document.getElementById("play-area");
  const input = document.getElementById("game-input");
  const scoreDisplay = document.getElementById("score");
  const levelDisplay = document.getElementById("level");
  const nextLevelDisplay = document.getElementById("next-level");
  const livesDisplay = document.getElementById("lives");
  const announcer = document.getElementById("game-status");

  const startPanel = document.getElementById("start-panel");
  const pausePanel = document.getElementById("pause-panel");
  const overPanel = document.getElementById("over-panel");
  const finalScore = document.getElementById("final-score");
  const finalLevel = document.getElementById("final-level");
  const saveStatus = document.getElementById("save-status");

  let game = null;
  let running = false;    // the loop is moving words
  let paused = false;
  let lastFrame = null;
  const wordElements = new Map(); // word id -> its <div>

  // F6: short beeps made with the Web Audio API, so there are no sound files to load.
  // Sound is off unless the student turns it on in Settings, so a classroom stays quiet.
  const SOUNDS = {
    matched: [[880, 0.08]],
    wrong: [[220, 0.08]],
    landed: [[180, 0.25]],
    levelup: [[523, 0.1], [659, 0.1], [784, 0.15]],
    gameover: [[392, 0.2], [330, 0.2], [262, 0.35]],
  };
  let audio = null;

  // Play a list of [frequency in Hz, seconds] notes one after another.
  function playSound(name) {
    if (!settings.soundOn || audio === null) return;
    let start = audio.currentTime;
    for (const [frequency, seconds] of SOUNDS[name]) {
      const note = audio.createOscillator();
      const volume = audio.createGain();
      note.frequency.value = frequency;
      volume.gain.setValueAtTime(0.15, start);
      volume.gain.exponentialRampToValueAtTime(0.001, start + seconds); // fade out, no click
      note.connect(volume).connect(audio.destination);
      note.start(start);
      note.stop(start + seconds);
      start += seconds;
    }
  }

  function showPanel(panel) {
    [startPanel, pausePanel, overPanel].forEach((other) => {
      other.hidden = other !== panel;
    });
  }

  async function startGame() {
    // The server remembers when the game started, so it can check the score later (L16).
    try {
      const response = await fetch(startUrl, { method: "POST" });
      if (!response.ok) throw new Error();
    } catch {
      saveStatus.textContent = "Could not start a game. Check you are still logged in.";
      return;
    }
    // Browsers only allow sound after a click, so the audio is set up here (Start is a click).
    if (settings.soundOn && audio === null && window.AudioContext) audio = new AudioContext();
    game = new FallingWordsGame(settings);
    wordElements.forEach((element) => element.remove());
    wordElements.clear();
    showPanel(null);
    input.disabled = false;
    input.value = "";
    input.focus();
    paused = false;
    running = true;
    lastFrame = null;
    drawStats();
    requestAnimationFrame(frame);
  }

  // L10: the game loop. The browser calls this about 60 times a second.
  function frame(now) {
    if (!running) return;
    if (!paused) {
      // dt is capped so words don't jump if the laptop stutters.
      const dt = lastFrame === null ? 0 : Math.min((now - lastFrame) / 1000, 0.1);
      game.update(dt);
      handleEvents();
      drawWords();
      if (game.isOver()) {
        endGame();
        return;
      }
    }
    lastFrame = now;
    requestAnimationFrame(frame);
  }

  function handleEvents() {
    for (const event of game.events) {
      if (event.type === "matched") removeWord(event.word, "matched");
      if (event.type === "landed") {
        removeWord(event.word, "landed");
        flash(playArea, "hit");
        announcer.textContent = `Ouch! "${event.word.text}" hit the ground.`;
      }
      if (event.type === "levelup") {
        flash(levelDisplay.parentElement, "level-up");
        announcer.textContent = `Level ${event.level}! Words fall faster now.`;
      }
      // A level up also counts as a match, so only the level up sound is played.
      const levelledUp = game.events.some((other) => other.type === "levelup");
      if (event.type !== "matched" || !levelledUp) playSound(event.type);
    }
    if (game.events.length) drawStats();
    game.events = [];
  }

  // Show a quick animation by adding a class for a moment.
  function flash(element, className) {
    element.classList.remove(className);
    void element.offsetWidth; // restart the animation
    element.classList.add(className);
  }

  function removeWord(word, how) {
    const element = wordElements.get(word.id);
    if (!element) return;
    wordElements.delete(word.id);
    element.classList.add(how);
    setTimeout(() => element.remove(), 250);
  }

  function drawWords() {
    const width = playArea.clientWidth;
    const height = playArea.clientHeight;
    const target = game.target();
    for (const word of game.falling) {
      let element = wordElements.get(word.id);
      if (!element) {
        element = document.createElement("div");
        element.className = "falling-word";
        playArea.appendChild(element);
        wordElements.set(word.id, element);
      }
      // L11: the matching word turns green, with the typed part underlined.
      const isTarget = word === target;
      const label = isTarget ? `${game.typed}|${word.text.slice(game.typed.length)}` : word.text;
      if (element.dataset.label !== label) {
        element.dataset.label = label;
        element.classList.toggle("match", isTarget);
        if (isTarget) {
          const typedPart = document.createElement("span");
          typedPart.className = "typed";
          typedPart.textContent = game.typed;
          element.replaceChildren(typedPart, word.text.slice(game.typed.length));
        } else {
          element.textContent = word.text;
        }
      }
      // Measured once, so the loop doesn't ask the browser for the size every frame.
      if (!element.dataset.height) {
        element.dataset.height = element.offsetHeight;
        element.dataset.width = element.offsetWidth;
      }
      // L21: keep the whole word inside the play area, even if the window got narrower.
      const x = Math.max(0, Math.min(word.x * width, width - Number(element.dataset.width)));
      const y = word.y * (height - Number(element.dataset.height));
      // transform moves the word without making the browser redo the page layout,
      // which keeps the game smooth on school laptops.
      element.style.transform = `translate(${x}px, ${y}px)`;
    }
  }

  function drawStats() {
    scoreDisplay.textContent = game.score;
    levelDisplay.textContent = game.level;
    const wordsLeft = game.wordsLeftInLevel();
    nextLevelDisplay.textContent =
      `${wordsLeft} ${wordsLeft === 1 ? "word" : "words"} to level ${game.level + 1}`;
    livesDisplay.replaceChildren(
      ...Array.from({ length: settings.startLives }, (_, index) => {
        const life = document.createElement("span");
        life.className = index < game.lives ? "life" : "life lost";
        return life;
      }),
    );
    livesDisplay.setAttribute("aria-label", `${game.lives} of ${settings.startLives} lives left`);
  }

  // L17: Esc or leaving the tab pauses; Esc again carries on.
  function pause() {
    if (!running || paused) return;
    paused = true;
    showPanel(pausePanel);
  }

  function resume() {
    if (!running || !paused) return;
    paused = false;
    lastFrame = null; // don't count the time spent paused
    showPanel(null);
    input.focus();
  }

  // L12, L15: stop, show the final score and send the result to the server.
  async function endGame() {
    running = false;
    playSound("gameover");
    input.disabled = true;
    finalScore.textContent = game.score;
    finalLevel.textContent = game.level;
    saveStatus.textContent = "Saving your score...";
    saveStatus.classList.remove("error");
    showPanel(overPanel);
    // Focus is NOT moved to Play again: players are pressing Enter as the game ends,
    // and that would start a new game before they see their score.

    try {
      const response = await fetch(resultUrl, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(game.toResult()),
      });
      const reply = await response.json();
      if (!response.ok) throw new Error(reply.error);
      saveStatus.textContent = "Score saved! Your key mistakes have been added to your heatmap.";
    } catch (problem) {
      saveStatus.textContent = problem.message || "Your score could not be saved.";
      saveStatus.classList.add("error");
    }
  }

  input.addEventListener("keydown", (event) => {
    if (!running || paused) return;
    if (event.ctrlKey || event.metaKey || event.altKey) return;
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      if (game.typed && !game.submit()) {
        flash(input, "wrong");
        playSound("wrong");
      }
    } else if (event.key === "Backspace") {
      event.preventDefault();
      game.backspace();
    } else if (event.key.length === 1) {
      event.preventDefault();
      game.type(event.key.toLowerCase());
    } else {
      return;
    }
    input.value = game.typed;
    drawWords();
    drawStats();
  });

  // Same as the typing test: no pasting, dropping text in or right-click menu.
  ["paste", "drop", "contextmenu"].forEach((eventName) =>
    input.addEventListener(eventName, (event) => event.preventDefault()),
  );
  input.addEventListener("input", () => {
    input.value = game ? game.typed : "";
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    if (paused) resume();
    else pause();
  });
  // L17, L22: switching to another tab or window pauses the game, so no lives are lost
  // while the student isn't looking.
  window.addEventListener("blur", pause);
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) pause();
  });

  // L21: when the window changes size, measure each word again and redraw. Word positions
  // are kept as fractions of the play area (0 to 1), so no word is lost or jumps away.
  window.addEventListener("resize", () => {
    wordElements.forEach((element) => {
      delete element.dataset.height;
      delete element.dataset.width;
    });
    if (game) drawWords();
  });

  document.getElementById("start").addEventListener("click", startGame);
  document.getElementById("resume").addEventListener("click", resume);
  document.getElementById("play-again").addEventListener("click", startGame);
  playArea.addEventListener("click", () => {
    if (running && !paused) input.focus();
  });

  showPanel(startPanel);
  document.getElementById("start").focus();
}
