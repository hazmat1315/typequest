// Tests for the typing engine in static/js/typing.js (Lucas): T42, T43 and L19, L20.
// Run with:  node --test tests/js/typing.test.js      (pytest runs this too, see test_typing.py)

"use strict";

const test = require("node:test");
const assert = require("node:assert/strict");
const { TypingTest } = require("../../static/js/typing.js");

function typeText(typingTest, text) {
  for (const character of text) typingTest.type(character);
}

test("T43 type 'Thw', Backspace, 'e': text right, 1 mistake still counted", () => {
  const typingTest = new TypingTest("The cat", "easy");
  typeText(typingTest, "Thw");
  assert.equal(typingTest.backspace(), true);
  typingTest.type("e");
  assert.equal(typingTest.position, 3);
  assert.equal(typingTest.characters(), 3);      // "The" is right now
  assert.equal(typingTest.total, 4);             // T, h, w, e
  assert.equal(typingTest.correct, 3);
  assert.equal(typingTest.accuracy(), 75);       // the fixed mistake still counts
  assert.deepEqual(typingTest.keyErrors.e, { presses: 2, errors: 1 });
});

test("L20 WPM uses the letters that are right in the end, not every correct key press", () => {
  const typingTest = new TypingTest("abcde", "easy");
  typeText(typingTest, "ab");
  typingTest.backspace();
  typingTest.backspace();
  typeText(typingTest, "abcde");
  assert.equal(typingTest.correct, 7);
  assert.equal(typingTest.characters(), 5);
  assert.equal(typingTest.wpm(60), 1);           // 5 letters / 5 / 1 minute
  assert.equal(typingTest.toResult(60).characters, 5);
});

test("L20 Backspace at the start does nothing", () => {
  const typingTest = new TypingTest("abc", "easy");
  assert.equal(typingTest.backspace(), false);
  assert.equal(typingTest.position, 0);
});

test("T42 keys typed after time is up are not counted", () => {
  const typingTest = new TypingTest("the cat sat", "easy");
  typeText(typingTest, "the");
  typingTest.stop();
  assert.equal(typingTest.type(" "), null);
  assert.equal(typingTest.backspace(), false);
  assert.equal(typingTest.total, 3);
  assert.equal(typingTest.position, 3);
  assert.equal(typingTest.toResult(60).total, 3);
});

test("keys after the end of the passage are ignored", () => {
  const typingTest = new TypingTest("ab", "easy");
  typeText(typingTest, "abc");
  assert.equal(typingTest.total, 2);
  assert.equal(typingTest.isFinished(), true);
});
