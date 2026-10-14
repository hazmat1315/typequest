// Tests for the browser game engine in static/js/game.js (Lucas): T25-T28 and L11-L13.
// Run with:  node --test tests/js/      (pytest runs this too, see test_game.py)

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { FallingWordsGame } = require("../../static/js/game.js");

const SETTINGS = {
  words: { short: ["cat", "dog", "sun"], medium: ["rocket", "planet", "river"], long: ["volcano", "treasure"] },
  startLives: 3,
  pointsPerWord: 10,
  pointsPerLevel: 100,
  baseSpeed: 0.12,
  speedGrowth: 1.15,
  baseSpawnSeconds: 2.5,
};

// A game with these words already falling (y = how far down, 0 to 1).
function gameWith(...words) {
  const game = new FallingWordsGame(SETTINGS, () => 0.5);
  game.nextId = 100; // stop the first automatic word
  game.falling = words.map(([text, y], index) => ({ id: index + 1, text, x: 0.1, y }));
  return game;
}

function typeWord(game, text) {
  for (const character of text) game.type(character);
}

test("T25 word matched: type 'rocket' + Enter removes it and adds 10", () => {
  const game = gameWith(["rocket", 0.3], ["river", 0.5]);
  typeWord(game, "rocket");
  assert.equal(game.submit(), true);
  assert.deepEqual(game.falling.map((word) => word.text), ["river"]);
  assert.equal(game.score, 10);
  assert.equal(game.typed, "");
});

test("L11 the matching word is the target (turns green), lowest first", () => {
  const game = gameWith(["rocket", 0.3], ["rock", 0.6], ["river", 0.9]);
  typeWord(game, "roc");
  assert.equal(game.target().text, "rock");
  game.type("k");
  game.type("e");
  assert.equal(game.target().text, "rocket");
  game.type("z");
  assert.equal(game.target(), null);
});

test("L11 Enter on a word that is not falling scores nothing", () => {
  const game = gameWith(["rocket", 0.3]);
  typeWord(game, "rock");
  assert.equal(game.submit(), false);
  assert.equal(game.score, 0);
  assert.equal(game.falling.length, 1);
});

test("T26 word hits ground: lives 3 to 2", () => {
  const game = gameWith(["cat", 0.99]);
  game.update(0.5);
  assert.equal(game.lives, 2);
  assert.equal(game.falling.some((word) => word.text === "cat"), false);
});

test("T27 level up at exactly 100 points, and words fall faster", () => {
  const game = gameWith();
  game.score = 90;
  const slowSpeed = game.fallSpeed();
  game.falling = [{ id: 1, text: "cat", x: 0, y: 0 }];
  typeWord(game, "cat");
  game.submit();
  assert.equal(game.score, 100);
  assert.equal(game.level, 2);
  assert.ok(game.fallSpeed() > slowSpeed);
  assert.equal(game.fallSpeed().toFixed(4), (0.12 * 1.15).toFixed(4));
});

test("L13 spawn time follows 2.5 / (1 + 0.1 x (level - 1))", () => {
  const game = gameWith();
  assert.equal(game.spawnSeconds(), 2.5);
  game.level = 6;
  assert.equal(game.spawnSeconds(), 2.5 / 1.5);
});

test("L13 a new word appears straight away, then every spawnSeconds()", () => {
  const game = new FallingWordsGame(SETTINGS, () => 0.5);
  game.update(0.016);
  assert.equal(game.falling.length, 1);
  game.update(2.0);
  assert.equal(game.falling.length, 1);
  game.update(0.6);
  assert.equal(game.falling.length, 2);
});

test("L14 word band changes with level", () => {
  const game = gameWith();
  assert.equal(game.wordBand(), "short");
  game.level = 3;
  assert.equal(game.wordBand(), "medium");
  game.level = 9;
  assert.equal(game.wordBand(), "long");
});

test("T28 game over after losing all 3 lives; nothing moves after that", () => {
  const game = gameWith(["cat", 0.99], ["dog", 0.99], ["sun", 0.99]);
  game.update(0.5);
  assert.equal(game.lives, 0);
  assert.equal(game.isOver(), true);
  const seconds = game.seconds;
  game.update(1);
  assert.equal(game.seconds, seconds);
});

test("L15 result has score, level and key errors for the server", () => {
  const game = gameWith(["cat", 0.2]);
  typeWord(game, "cxt"); // x should have been a
  const result = game.toResult();
  assert.deepEqual(Object.keys(result).sort(),
    ["correct", "key_errors", "level_reached", "score", "seconds", "total"]);
  assert.equal(result.correct, 1);
  assert.equal(result.total, 2); // after the mistake, the t is not counted again
  assert.deepEqual(result.key_errors, { c: { presses: 1, errors: 0 }, a: { presses: 1, errors: 1 } });
});

test("key mistakes on the first letter count against the lowest word", () => {
  const game = gameWith(["cat", 0.2], ["dog", 0.7]);
  game.type("x");
  assert.deepEqual(game.keyErrors, { d: { presses: 1, errors: 1 } });
});

test("backspace fixes a mistake so the word can still be matched", () => {
  const game = gameWith(["dog", 0.2]);
  typeWord(game, "dx");
  game.backspace();
  typeWord(game, "og");
  assert.equal(game.submit(), true);
});
