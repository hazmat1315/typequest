# TypeQuest

A typing tutor web app for Year 7/8 students. It measures typing speed and accuracy,
records every mistake per key, and gives each student personalised tips about the
exact keys they get wrong.

**Stage 2 Digital Technologies, AT2 Collaborative Project.** Team: Henry, Lucas, George.
**Current version: Iteration 2 (full feature version).** On top of Iteration 1 (login, typing
test, WPM and accuracy, weak-key tips, saved results), students can now play a falling words
game, practise adaptive drills built from their weak keys, see a keyboard heatmap of their
mistakes, track their progress on a graph, and compete on a leaderboard with personal bests
and practice streaks.

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

**Upgrading from Iteration 1:** your existing `typequest.db` is upgraded automatically when
`python app.py` starts. Every account and result is kept. To do it by hand (or to see
what changed), run `python migrate.py`.

Chart.js (for the progress graph) is saved in `static/js/vendor/`, so the app works on school
laptops with no internet connection.

> Start the app with `python app.py` (not `flask run`), because that is what creates the
> database tables.

## Running the tests

```bash
python -m pytest
```

There are 176 automated tests in `tests/`, named after the test plan IDs (T1 to T37) and
requirement IDs (H1-H18, L1-L18, G1-G15). Every test uses its own temporary database, so
your real `typequest.db` is never touched. Results are recorded in
[TEST_RESULTS.md](TEST_RESULTS.md).

| File | Owner | Tests |
|---|---|---|
| `test_accounts.py`, `test_typing.py`, `test_tips.py`, `test_journey.py` | All | Iteration 1 (T1-T16, re-run for T37) |
| `test_progress.py` | Henry | T17-T24, H10-H18, database migration |
| `test_game.py` | Lucas | T25-T30, L10-L18 |
| `test_practice.py` | George | T31-T36, G8-G15 |
| `js/game.test.js` | Lucas | The browser game engine (`node --test tests/js/game.test.js`) |

If Node.js is installed, pytest runs the game.js tests too; otherwise that one test is skipped.

## Project structure and owners

```
typequest/
  app.py                         All    (routes, grouped by owner)
  migrate.py                     Henry  (upgrades an Iteration 1 database)
  models/
    database.py, user.py         Henry  (accounts, results, leaderboard, streak, personal best)
    passage.py, typing_session.py  Lucas  (passages, WPM and accuracy)
    game.py                      Lucas  (Game class: game rules and score checking)
    key_stats.py, tip_engine.py  George (weak keys, heatmap bands, rotating tips)
    drill_generator.py           George (adaptive drills)
  templates/
    base.html                    Lucas  (shared layout and nav bar)
    login.html, register.html, home.html, progress.html   Henry
    test.html, game.html         Lucas
    results.html                 Lucas (results) + Henry (personal best) + George (tips, heatmap)
    practice.html                George
  static/
    js/typing.js                 Lucas  (TypingTest rules + TypingBox, shared with practice)
    js/game.js                   Lucas  (falling words game)
    js/practice.js               George (drill page, uses TypingBox)
    js/progress.js               Henry  (graph and leaderboard filters)
    js/vendor/chart.umd.min.js   Chart.js 4.4.1 (MIT licence), for the progress graph
    css/style.css                Lucas
    favicon.svg                  Lucas
  data/
    passages.json                Lucas  (6 passages per level)
    game_words.json              Lucas  (short, medium and long word bands)
    words.json                   George (909-word drill word bank)
    tips.json                    George (2 tips per key, "great job", tips of the day)
  tests/                         George (lead tester); one file per component
  docs/screenshots/              Every Iteration 1 screen; iteration2/ has every new screen
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
   Each key has 2 tips; `next_tip()` picks one that is different from the last tip the
   student saw for that key (remembered in the `last_tips` table).
5. **Personal best and progress (Henry).** When a test is saved, `User.update_best()` checks it
   against `personal_best` and the results page shows the badge. `/progress` draws every test
   with Chart.js and works out the improvement. The leaderboard uses each user's best test
   (ties go to higher accuracy), and the This week / All time buttons fetch `/leaderboard`
   as JSON so the page doesn't reload. `User.streak()` counts days in a row with any activity.
6. **Heatmap (George).** `KeyStats.band()` gives each key a colour and
   `TipEngine.heatmap_colours()` lays them out as a QWERTY keyboard on the results page.
7. **Practice drills (George).** `DrillGenerator.make_drill()` scores every word in
   `words.json` by how many weak letters it has, then picks 20 at random from the top 40.
   `/practice` uses Lucas's `TypingBox` for typing, and after the drill the server sends back
   the error rate of each focus key before and after.
8. **Game (Lucas).** `game.js` runs the game loop with `requestAnimationFrame`. At game over it
   sends the score, level and key errors to `POST /game/result`. The server rebuilds it as a
   `Game` (which inherits `TypingSession`), checks it is possible, then saves it with mode
   `game` and adds its key errors to the heatmap. Drills are saved with mode `drill`.

### Formulas (Section 2.4 of the spec)

| Measure | Formula |
|---|---|
| WPM | (correct characters / 5) / minutes taken |
| Accuracy % | correct key presses / total key presses x 100 |
| Key error rate % | mistakes on that key / times that key was pressed x 100 |
| Improvement (WPM) | (average of last 3 results) - (average of first 3 results); with fewer than 6 results, latest - first |
| Fall speed | base speed x 1.15^(level - 1), base speed = 12% of the play area per second |
| Time between new words | 2.5 seconds / (1 + 0.1 x (level - 1)) |
| Word score (drills) | number of letters in the word that are weak keys (repeats count) |
| Heatmap | green below 5%, orange 5% to 15%, red above 15%, grey under 10 presses |

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

## Design decisions made during Iteration 2

- **One results table for everything.** Games and drills are saved in `results` with a `mode`
  column (H18). Games and drills have no Easy/Medium/Hard level, and SQLite can't remove the
  old "level must not be empty" rule, so the migration copies the results into a new table.
- **Only typing tests count for WPM records.** The leaderboard, personal best, progress graph,
  best WPM and average accuracy all use typing tests only. Game WPM is slowed down by waiting
  for words to fall, and a drill of short words is not the same as a passage, so mixing them
  would not be fair. The streak counts tests, games and drills.
- **Game scores are checked by the server (fairness).** Words appear one at a time, so the
  server works out the highest score a perfect player could get in the time played and
  refuses anything higher. The time is checked against when Start was pressed, so it can't be
  made up either.
- **Space works like Enter in the game.** The spec says Enter, but students press space after
  every word out of habit, so both destroy a matching word.
- **Game key mistakes count against the key you meant to press.** The same rule as the typing
  test: if you are typing "rocket" and press `x` instead of `k`, that is a mistake on K.
- **Words for each level.** Levels 1-2 use short words (3-4 letters), 3-4 medium (5-6) and 5 or
  more long words (7+).
- **Tips change once per test.** A new tip is chosen when a test is saved, not every time the
  results page loads, so refreshing the page doesn't change the tip.
- **Colour-blind safe heatmap.** Green, orange and red are the Okabe-Ito colours, which can be
  told apart with the common types of colour blindness. Red keys also have stripes and a thick
  border, and grey keys a dashed border, so colour is never the only clue.

## Not in Iteration 2 (planned for Iteration 3 or future)

Teacher accounts and class view, "My class" leaderboard filter, "Most improved key" stat,
custom passages written by teachers, sound effects and settings page, hosting online.
