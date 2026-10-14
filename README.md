# TypeQuest

A typing tutor web app for Year 7/8 students. It measures typing speed and accuracy,
records every mistake per key, and gives each student personalised tips about the
exact keys they get wrong.

**Stage 2 Digital Technologies, AT2 Collaborative Project.** Team: Henry, Lucas, George.
**Current version: Iteration 1 (core working prototype).** A student can log in, complete
a typing test, see their WPM and accuracy, get tips about their weakest keys, and have the
result saved to their account.

## Running the app

You need Python 3.10 or newer. In a terminal, from this `typequest` folder:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in Chrome. The database (`typequest.db`) and a
secret key file (`.secret_key`) are created automatically the first time it runs.
Delete `typequest.db` to start again with no accounts.

> Start the app with `python app.py` (not `flask run`), because that is what creates the
> database tables.

## Running the tests

```bash
python -m pytest
```

There are 76 automated tests in `tests/`, one file per team member, named after the
test plan IDs (T1 to T16) and requirement IDs (H1-H9, L1-L9, G1-G7). Every test uses
its own temporary database, so your real `typequest.db` is never touched.
Results are recorded in [TEST_RESULTS.md](TEST_RESULTS.md).

## Project structure and owners

```
typequest/
  app.py                         All    (routes, grouped by owner)
  models/
    database.py, user.py         Henry  (accounts, results, home stats)
    passage.py, typing_session.py  Lucas  (passages, WPM and accuracy)
    key_stats.py, tip_engine.py  George (weak-key algorithm, tips)
  templates/
    base.html                    Lucas  (shared layout and nav)
    login.html, register.html, home.html   Henry
    test.html                    Lucas
    results.html                 Lucas (results) + George (tips section)
  static/
    js/typing.js                 Lucas
    css/style.css                Lucas
  data/
    passages.json                Lucas  (6 passages per level)
    tips.json                    George (26 letters + space + "great job")
  tests/                         George (lead tester); one file per component
  docs/screenshots/              Every Iteration 1 screen
```

## How it works

1. **Accounts (Henry).** Register and login forms check the details, then save a
   `generate_password_hash` hash (never the plain password). The signed session cookie
   remembers who is logged in, and `@login_required` sends logged-out visitors to `/login`.
2. **Typing test (Lucas).** `/test` picks a random passage with `Passage.random(level)`.
   `typing.js` colours each letter as it is typed, starts the 60 second timer on the first
   key and ends the test when time runs out or the passage is finished. It then sends the
   totals to `POST /result` as JSON.
3. **Saving (Henry and Lucas).** The server rebuilds the test as a `TypingSession`, checks the
   numbers, calculates WPM and accuracy itself and saves a row in `results`.
4. **Tips (George).** `KeyStats` adds that test's per-key presses and mistakes to the user's
   running totals in `key_stats`. `weakest()` finds keys with an error rate above 15%
   (pressed at least 10 times), and `TipEngine.tips_for()` turns the 3 worst into tips.

### Formulas (Section 2.4 of the spec)

| Measure | Formula |
|---|---|
| WPM | (correct characters / 5) / minutes taken |
| Accuracy % | correct key presses / total key presses x 100 |
| Key error rate % | mistakes on that key / times that key was pressed x 100 |

## Design decisions made during Iteration 1

These go slightly beyond the spec. Each one has a reason we can explain to the client.

- **No Backspace.** Following our typing test flowchart, every key press moves on to the
  next letter. This means "correct key presses" and "correct characters" are the same
  number, so WPM and accuracy stay consistent. Students are told "Keep going, you can't go back!"
- **A mistake counts against the key you should have pressed.** If the passage says `e` and
  you type `w`, that is a mistake on E. E is the key the student needs to practise.
- **The server does not trust the browser.** The browser sends its WPM, but the server
  works it out again from the raw counts. It also checks the level and counts against the
  passage it handed out (kept in the session) and refuses results it has already saved.
  This means a student cannot edit the page to post a fake score.
- **Results faster than 250 WPM are refused.** During testing, an automated script typed
  a whole passage in a split second and saved **16,720 WPM**. No human can type faster than
  about 250 WPM, so these results are now rejected with a clear message.
- **Usernames are not case sensitive.** `Typer01` and `typer01` are treated as the same
  user, so a student cannot accidentally make two accounts.
- **Tips use every test, not just the last one.** One 60 second test does not give many
  presses per key. Running totals make the weak-key list fairer and let students see a
  tip disappear as they improve.

## Not in Iteration 1 (planned for Iterations 2 and 3)

Game mode, progress graph, leaderboard, keyboard mistake heatmap, adaptive practice drills,
personal best badge, visual polish, teacher view of class results.
