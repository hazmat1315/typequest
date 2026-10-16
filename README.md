# TypeQuest

A typing tutor web app for Year 7/8 students. It measures typing speed and accuracy,
records every mistake per key, and gives each student personalised tips about the
exact keys they get wrong.

**Stage 2 Digital Technologies, AT2 Collaborative Project.** Team: Henry, Lucas, George.
**Current version: Iteration 3 (refined final version).** Students register, take 60 second
typing tests, get tips for the exact keys they get wrong, see a keyboard heatmap of their
mistakes and a finger guide, practise adaptive drills built from their weak keys, play a
falling words game, and track their progress on a graph and leaderboard. Iteration 3 added the changes students and the
client asked for (see [Iteration 3: changes from feedback](#iteration-3-changes-from-feedback))
and made the app reliable (error pages, server-side checks, session expiry, edge cases).

## Who built what

| Member | Built |
|---|---|
| **Henry** (accounts and data, client liaison) | Login and registration, password hashing, the database and migrations, saving results, progress graph, leaderboard and filters, personal best, streak, home dashboard, error pages, session expiry, demo database, README |
| **Lucas** (typing engine, game and UI) | Typing test and `TypingBox`, WPM and accuracy, passages, Backspace and time-up handling, falling words game and the `Game` class, level progression (F5), settings for sound and slow mode (F6), shared layout and styles, user guide |
| **George** (tips, heatmap and drills, lead tester) | Per-key mistake tracking, weak keys, tips and rotating tips, keyboard heatmap, adaptive drill generator, finger guide (F7), tip and word bank fallbacks, test plan and test evidence |

## Running the app

You need Python 3.10 or newer. In a terminal, from this `typequest` folder:

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Then open **http://127.0.0.1:5000** in Chrome or Edge. The database (`typequest.db`) and a
secret key file (`.secret_key`) are created automatically the first time it runs (H20), and
again if `typequest.db` is ever deleted. Delete it to start again with no accounts.

### Demo database (for markers)

`demo.db` has 8 students with two weeks of tests, games and drills,
so every feature can be seen straight away:

```bash
python app.py --demo
```

| Log in as | Password | To see |
|---|---|---|
| `speedyfingers12` | `demo123` | A student with weak keys (R, O, E): results, heatmap, finger guide, drills, progress graph, leaderboard |
| `keyboardking` | `demo123` | The top of the leaderboard, with no weak keys ("Great job" tip) |
| `newbie01` | `demo123` | A student who hasn't done anything yet |

`python make_demo_db.py` rebuilds `demo.db` from scratch (it always makes the same data).

**Upgrading from Iteration 1 or 2:** an existing `typequest.db` is upgraded automatically when
the app starts. Every account and result is kept. To do it by hand (or to see what changed),
run `python migrate.py`.

Chart.js (for the progress graph) is saved in `static/js/vendor/`, so the app works on school
laptops with no internet connection.

## Running the tests

```bash
python -m pytest
```

There are 250 automated tests in `tests/`, named after the test plan IDs (T1 to T53) and
requirement IDs (H1-H23, L1-L23, G1-G19, F5-F7). Every test uses its own temporary database,
so your real `typequest.db` is never touched. Results are recorded in
[TEST_RESULTS.md](TEST_RESULTS.md).

| File | Owner | Tests |
|---|---|---|
| `test_accounts.py`, `test_typing.py`, `test_tips.py`, `test_journey.py` | All | Iteration 1 (T1-T16) |
| `test_progress.py` | Henry | T17-T24, H10-H18, database migration |
| `test_game.py` | Lucas | T25-T30, L10-L18, T51 (F5 levels) |
| `test_practice.py` | George | T31-T36, G8-G15 |
| `test_reliability.py` | All | T38-T49: H19-H23, L19-L22, G16-G19, demo database |
| `test_feedback.py` | Lucas, George | T51-T53: the F-changes from client feedback |
| `js/game.test.js`, `js/typing.test.js` | Lucas | The browser game and typing engines (`node --test tests/js/game.test.js tests/js/typing.test.js`) |

If Node.js is installed, pytest runs the JavaScript tests too; otherwise those 2 tests are skipped.

## Project structure and owners

```
typequest/
  app.py                         All    (routes, grouped by owner)
  migrate.py                     Henry  (upgrades an older database)
  make_demo_db.py, demo.db       Henry  (demo data for markers)
  models/
    database.py, user.py         Henry  (accounts, results, leaderboard, streak, personal best, settings)
    passage.py, typing_session.py  Lucas  (passages, WPM and accuracy)
    game.py                      Lucas  (Game class: game rules, levels and score checking)
    key_stats.py, tip_engine.py  George (weak keys, heatmap bands, rotating tips)
    drill_generator.py           George (adaptive drills)
    finger_guide.py              George (which finger presses each key)
  templates/
    base.html                    Lucas  (shared layout and nav bar)
    login.html, register.html, home.html, progress.html, error.html   Henry
    test.html, game.html         Lucas
    settings.html                Lucas  (game settings)
    results.html                 Lucas (results) + Henry (personal best) + George (tips, heatmap)
    practice.html, _finger_guide.html   George
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
  docs/screenshots/              Every Iteration 1 screen; iteration2/ and iteration3/ have every new screen
```

## How it works

1. **Accounts (Henry).** Register and login forms check the details, then save a
   `generate_password_hash` hash (never the plain password). The signed session cookie
   remembers who is logged in, and `@login_required` sends logged-out visitors to `/login`.
2. **Typing test (Lucas).** `/test` picks a random passage with `Passage.random(level)`.
   `typing.js` colours each letter as it is typed, starts the 60 second timer on the first
   key and ends the test when time runs out or the passage is finished. Backspace takes back
   the last letter. It then sends the totals to `POST /result` as JSON.
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
9. **Settings (Lucas).** `/settings` saves sound effects and slow mode in the
   `users` table. The game page hands them to `game.js`, which plays short beeps with the Web
   Audio API (no sound files) and multiplies the fall speed by 0.6 in slow mode.
10. **Finger guide (George).** `FingerGuide.finger_for()` knows the finger for every key.
   `FingerGuide.guide()` builds a keyboard coloured by finger and a picture of two hands, with
   the fingers for the student's weak keys highlighted, on the results and practice pages.
11. **Every request (Henry).** Before each page, `make_database_if_missing()` creates the
   tables if `typequest.db` is missing and `log_out_idle_users()` logs out anyone idle for 2
   hours. Errors show `error.html` instead of Flask's own page.

### Formulas (Section 2.4 of the spec)

| Measure | Formula |
|---|---|
| WPM | (correct characters / 5) / minutes taken (letters that are right in the finished text) |
| Accuracy % | correct key presses / total key presses x 100 (a mistake fixed with Backspace still counts) |
| Key error rate % | mistakes on that key / times that key was pressed x 100 |
| Improvement (WPM) | (average of last 3 results) - (average of first 3 results); with fewer than 6 results, latest - first |
| Words to the next level (F5) | 3 + 2 x (level - 1): 3 words to reach level 2, then 5, 7, 9 ... (level 2 after 3 words, level 3 after 8, level 4 after 15) |
| Fall speed | base speed x 1.15^(level - 1), base speed = 12% of the play area per second; x 0.6 in slow mode |
| Time between new words | 2.5 seconds / (1 + 0.1 x (level - 1)) |
| Word score (drills) | number of letters in the word that are weak keys (repeats count) |
| Heatmap | green below 5%, orange 5% to 15%, red above 15%, grey under 10 presses |

## Design decisions made during Iteration 1

These go slightly beyond the spec. Each one has a reason we can explain to the client.

- **No Backspace.** Following our typing test flowchart, every key press moves on to the
  next letter. This means "correct key presses" and "correct characters" are the same
  number, so WPM and accuracy stay consistent. Students are told "Keep going, you can't go back!"
  *(Changed in Iteration 3 for L20: Backspace now works. See below.)*
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

## Iteration 3: changes from feedback

Section 2.1 of the Iteration 3 specification. The feedback comes from our student survey
(`data.xlsx`, 25 Year 7/8 students, question "Are there any specific things you would like
the website to have?"). The spec says every member must deliver at least one change (DE2);
**Henry's F-change is still to be chosen** (a teacher class view was built and then taken out).

| ID | Client feedback | Change we made | Owner | Done when | Test |
|---|---|---|---|---|---|
| F5 | "Lessons that start really easy" (student 3); "Slow mode for beginners" (student 23) | Levels need more words as they go: 3 words to reach level 2, then 5 more for level 3, then 7, 9 ... (was 10 words for every level). The game shows how many words are left until the next level | Lucas | Level 2 after exactly 3 words, level 3 after 8, level 4 after 15, in both game.js and the server | T51 |
| F6 | "Sound effects that can be turned off" (student 18); "Slow mode for beginners" (student 23) | Settings page with sound effects on/off (off by default) and slow mode (words fall at 60% speed) | Lucas | Settings are saved to the account and the game uses them | T52 |
| F7 | "Shows which finger to use for each key" (student 20); "On-screen keyboard showing where fingers go" (student 7) | Finger guide on the results and practice pages: a keyboard coloured by finger, a picture of two hands, and the fingers for the student's weak keys highlighted with a sentence each | George | A student with E weak sees "E: use your left middle finger. It starts on D." with that finger highlighted | T53 |

Candidate features from Section 2.2 that were **not** built because nobody asked for them:
"Most improved key", weekly goal, hide from leaderboard, and custom passages (student 8 asked
to type their own text, which is noted as a future improvement below). Teacher accounts with
class codes, a class view and a "My class" leaderboard were built for students 2 and 25 and
then removed from the final version.

## Design decisions made during Iteration 3

- **Backspace (L20).** Students can now fix a mistake with Backspace, but the mistake still
  counts against their accuracy and the heatmap, so fixing it doesn't hide it. Because of
  this there are now two numbers: correct key presses (for accuracy) and correct characters
  in the finished text (for WPM). The browser sends both and the server checks that they
  make sense (`characters <= correct <= total`, no more than 20 key presses a second).
- **Keys after 0:00 (L19).** The timer only checks 10 times a second, so a key pressed just
  after 0:00 could have counted. Every key press now checks the clock first, and the
  server never counts more than 60 seconds.
- **Sound is off by default.** Our planning document says the app should work quietly in a
  classroom, so sound is something a student turns on for themselves.
- **Session expiry (H23).** After 2 hours without using TypeQuest the student is logged out,
  because school laptops are shared. Every page they open resets the 2 hours.
- **One check for every account page.** `@login_required` now loads the account from the
  database. If it no longer exists (for example the database was reset), the student is sent
  to log in again instead of seeing an error.
- **Safe database queries (H22).** The two places that joined strings to build SQL (a
  `WHERE` in `_find_user` and `PRAGMA table_info`) were rewritten, and
  `test_H22_no_string_joined_sql` searches every Python file so it can't come back.
- **Shorter play area on short screens (L23).** At 1280 x 720 the browser's toolbars leave
  less room, so the game's play area is a little shorter and the typing box stays on screen.

## Limitations and future improvements

| Limitation | How it could be fixed |
|---|---|
| Runs only on one computer (localhost), so every student needs it installed, and results stay on that computer | Host it online (for example on PythonAnywhere) with one shared database for the school |
| Teachers can't see their class's results, and the leaderboard can't be limited to classmates (asked for by students 2 and 25) | Teacher accounts with a class code students type when they register, a class results page, and a "My class" leaderboard filter |
| Students can't type their own text, like school notes or spelling words (asked for by students 8 and 19) | Custom passages added by students or teachers |
| Typing tests only use letters and spaces for tips; numbers and punctuation aren't tracked (asked for by student 4) | Add number and punctuation keys to `KeyStats`, the heatmap and tips |
| No dark mode or themes (students 10 and 17) | CSS variables are already used for every colour, so a dark theme could be a second set of variables |
| Works on laptops but is not designed for phones (no on-screen keyboard typing) | A mobile layout, though typing practice really needs a physical keyboard |
