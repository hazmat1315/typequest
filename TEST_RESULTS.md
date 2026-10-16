# Iteration 1 Test Results

Test plan from Section 7 of the Iteration 1 project specification. Run on 11 October 2026.

- **pytest** = automated server tests in `tests/` (`python -m pytest`, 76 tests, all passing)
- **Chrome** = automated end-to-end run in Google Chrome against the running app (real key
  presses, real timer); screenshots in `docs/screenshots/`

> The spec says each member runs the tests for their own component. Each owner should
> still run their tests by hand in Chrome and initial this table before it goes into the
> planning document.

| ID | Owner | Test | Input | Expected result | Actual | Pass? | How |
|---|---|---|---|---|---|---|---|
| T1 | Henry | Register valid new user | typer01 / secret12 | Account created, sent to home | Redirected to /home showing "Hi typer01! Ready to practise?" | ✅ | pytest, Chrome (04) |
| T2 | Henry | Register taken username | typer01 again | "That username is taken" | Message shown, still 1 row in users (also for "TYPER01") | ✅ | pytest, Chrome |
| T3 | Henry | Register short password (boundary) | 12345 (5 chars) | Rejected: must be 6 or more | "Your password must be 6 or more characters long." No row added. 123456 is accepted. | ✅ | pytest, Chrome (03) |
| T4 | Henry | Login correct details | typer01 / secret12 | Logged in, home page shown | Redirected to /home | ✅ | pytest, Chrome |
| T5 | Henry | Login wrong password | typer01 / wrong | "Incorrect username or password" | Message shown, stays on /login | ✅ | pytest, Chrome (05) |
| T6 | Henry | Open /home when logged out | Go to URL directly | Redirected to /login | /home, /test and /results all redirect to /login | ✅ | pytest, Chrome |
| T7 | Lucas | Timer starts on first key | Press any key | Timer starts counting down | Stays at 1:00 before typing; 0:59 about 1.6 s after the first key | ✅ | Chrome |
| T8 | Lucas | Correct and wrong letters | Type 'Th' then 'x' | T, h green; x red | First 2 letters green, 3rd red with a light red background and underline; cursor on the 4th letter | ✅ | Chrome (07), Node |
| T9 | Lucas | WPM calculation | 150 correct chars in 60 s | WPM = 30.0 | 30.0 | ✅ | pytest, Node |
| T10 | Lucas | Accuracy calculation | 90 correct of 100 presses | Accuracy = 90.0% | 90.0 | ✅ | pytest, Node |
| T11 | Lucas | Paste blocked | Ctrl+V into input | Nothing pasted | Paste event and right-click menu blocked; Cmd+V types nothing; timer does not start | ✅ | Chrome |
| T12 | George | Weak key found | E: 20 presses, 5 errors | E listed as weak (25%) | `weakest()` returns `[("e", 25.0)]` | ✅ | pytest |
| T13 | George | Error rate at boundary | R: 20 presses, 3 errors | R not weak (above 15% only) | Error rate 15.0, not in weak list | ✅ | pytest |
| T14 | George | Too few presses ignored | Q: 4 presses, 2 errors | Q ignored | `error_rate("q")` is None, not in weak list (10 presses is counted) | ✅ | pytest |
| T15 | George | No weak keys | All keys under 15% | "Great job" tip shown | Single "Great job!" tip | ✅ | pytest |
| T16 | All | Full journey | Register, test, results | Result saved and tips shown | Registered, typed a Hard passage with every 3rd "e" wrong: results showed WPM, accuracy and "E (33.3% wrong)" tip; home showed Best WPM and Tests done 1 | ✅ | pytest, Chrome (08-10) |

## Extra checks beyond the test plan

| Requirement | Check | Result |
|---|---|---|
| H3 | Only a hash is in the database; the plain password never appears | ✅ |
| H9 | Logout clears the session and returns to /login | ✅ |
| L2 | 50 Restarts in a row never repeat the previous passage | ✅ |
| L4, L6 | Timer counts down to 0:00 and ends the test (50 correct chars in 60 s = 10.0 WPM) | ✅ Chrome (11) |
| L6 | Finishing the passage early ends the test and uses the real time taken | ✅ |
| L8 | Restart resets timer, colours and input and loads a different passage | ✅ |
| Security | SQL injection attempt in the username (`typer01' --`) does not log in | ✅ |
| Security | Fake WPM sent by the browser is ignored; server recalculates | ✅ |
| Security | The same test cannot be saved twice | ✅ |
| G1 | Bad key data (numbers, more errors than presses, negative numbers) is ignored | ✅ |
| G2 | Key stats carry across tests and are separate for each user | ✅ |
| Quality | Each test was checked by deliberately breaking the code (8 different bugs added on purpose); every one was caught by a failing test | ✅ |

## Bugs found and fixed during Iteration 1

Evidence of iterative testing and modification (DE2).

| # | Found by | Problem | Fix | Re-test |
|---|---|---|---|---|
| 1 | Chrome test | An automated script typed a whole passage in a split second and the server **saved 16,720 WPM**. A student could do the same to fake a score. | `TypingSession.from_json` now refuses any result over 250 WPM (faster than any human) with the message "That was too fast to be real typing." | New pytest cases for 1200 WPM (rejected) and 120 WPM (accepted). Chrome screenshot 08a shows the message. ✅ |
| 2 | Chrome test | Chrome logged a 404 error on every page because the app had no tab icon (`/favicon.ico`). | Added an empty icon link in `base.html` until the real icon is made in Iteration 2. | Chrome console has no errors. ✅ |
| 3 | Screenshot review | On long passages the typing box kept showing the start of the text, so the newest letters were hidden off the right edge. | `typing.js` scrolls the box to the end after every key. | Screenshot 08 shows the latest letters. ✅ |

---

# Iteration 2 Test Results

Test plan from Section 7 of the Iteration 2 project specification. Run on 14 October 2026.

- **pytest** = automated tests in `tests/` (`python -m pytest`, 176 tests, all passing). New files:
  `test_progress.py` (Henry), `test_game.py` (Lucas), `test_practice.py` (George)
- **Node** = `tests/js/game.test.js`, 12 tests of the browser game engine in `game.js`
  (`node --test tests/js/game.test.js`; pytest also runs it if Node is installed)
- **Chrome** = automated end-to-end run in Google Chrome against the running app with real key
  presses; screenshots in `docs/screenshots/iteration2/`

> As in Iteration 1, each owner should still run their own tests by hand in Chrome and initial
> this table before it goes into the planning document.

| ID | Owner | Test | Input | Expected result | Actual | Pass? | How |
|---|---|---|---|---|---|---|---|
| T17 | Henry | Progress graph with results | User with 5 saved tests | Graph shows 5 points, oldest first | Chart.js data is `[20.0, 24.5, 23.0, 27.0, 30.0]` labelled Test 1 to Test 5, oldest first. Games and drills are not plotted. | ✅ | pytest, Chrome (20) |
| T18 | Henry | Progress graph with no results | New user | "Do a test to see your progress" | Message shown with a Typing test button; no graph | ✅ | pytest, Chrome (24) |
| T19 | Henry | Improvement with 6+ results | WPM 20, 22, 21, 30, 31, 32 | +10 WPM (31 minus 21) | `improvement()` = 10.0; progress page shows "+10 WPM" | ✅ | pytest |
| T20 | Henry | Leaderboard tie | Two users at 40 WPM, 95% and 90% | 95% user ranked higher | 95% user is 1st, 90% user is 2nd | ✅ | pytest |
| T21 | Henry | Rank outside top 10 | User ranked 15th | "You: 15th" row shown | Table has 10 rows without the user; "You: 15th, 28.0 WPM" shown underneath | ✅ | pytest |
| T22 | Henry | Personal best | Best 30, new result 32 | Badge shown, personal_best = 32 | "New personal best!" shown; `users.personal_best` = 32.0. A slower test shows no badge. | ✅ | pytest, Chrome (13) |
| T23 | Henry | Streak continues | Activity today, yesterday, 2 days ago | Streak = 3 | 3 | ✅ | pytest, Chrome (22) |
| T24 | Henry | Streak broken | Activity today and 3 days ago only | Streak = 1 | 1 | ✅ | pytest |
| T25 | Lucas | Word matched | Type 'rocket' + Enter | Word removed, score +10 | Word removed, score 0 to 10, input cleared | ✅ | pytest, Node, Chrome (17) |
| T26 | Lucas | Word hits ground | Let a word fall | Lives 3 to 2 | Lives 3 to 2, word removed, play area flashes red | ✅ | pytest, Node, Chrome |
| T27 | Lucas | Level up (boundary) | Score reaches exactly 100 | Level 2, words fall faster | Level 2 at exactly 100 (still 1 at 90); fall speed 0.12 to 0.138 | ✅ | pytest, Node, Chrome |
| T28 | Lucas | Game over | Lose all 3 lives | Game stops, score sent and saved | Game over panel with final score and level; "Score saved!"; `results` row with mode `game`, score and level_reached | ✅ | pytest, Node, Chrome (19) |
| T29 | Lucas | Pause | Press Esc during game | Words stop moving; Esc resumes | Words did not move for 1.2 s while paused and the Paused panel showed; after Esc they moved again. Switching tabs also pauses. | ✅ | Chrome (18) |
| T30 | Lucas | Impossible score rejected | Edit request: score 99999 | Server refuses to save | 400 "Your score could not be saved: That score is not possible." No row saved. 99990 is also refused. | ✅ | pytest |
| T31 | George | Heatmap colours | E 25%, T 10%, A 2%, Q 4 presses | E red, T orange, A green, Q grey | red, orange, green, grey | ✅ | pytest, Chrome (13) |
| T32 | George | Word scoring | Weak keys E, R; word 'error' | Score = 4 | 4 ("tree" 3, "cat" 0) | ✅ | pytest |
| T33 | George | Drill uses weak keys | Weak keys E, R, O | Most drill words contain E, R or O | All 20 words contain E, R or O | ✅ | pytest, Chrome (14) |
| T34 | George | Two drills differ | Generate 2 drills in a row | Drills are not identical | Different every time (also checked with the New drill button in Chrome) | ✅ | pytest, Chrome |
| T35 | George | No weak keys | New user | Mixed drill with a message | 20 random words with "You don't have any weak keys yet, so this drill is a random mix of words." | ✅ | pytest, Chrome (23) |
| T36 | George | Tip rotation | Same weak key in 2 tests | Different tip shown each time | 4 tests in a row with E weak: the E tip changed every time, and refreshing the results page kept the same tip | ✅ | pytest |
| T37 | All | Regression | Re-run T1 to T16 | All still pass | All 76 Iteration 1 tests pass. One of them (`test_G5_tips_name_the_finger_and_home_key`) was updated because each key now has a list of tips (G15); it now checks every tip. | ✅ | pytest |

## Extra checks beyond the test plan

| Requirement | Check | Result |
|---|---|---|
| H12 | One row per user using their best WPM; if a user got the same best WPM twice, their better accuracy is used | ✅ |
| H12, Fairness | Only typing tests count on the leaderboard, so a fast drill of short words can't beat a real test | ✅ |
| H14 | This week / All time change the table without reloading the page (checked in Chrome) | ✅ Chrome (21) |
| H16 | Streak still counts if the last activity was yesterday; games and drills count | ✅ |
| H17 | Home shows best WPM, average accuracy (tests only), tests done, streak, 3 activity buttons and a tip of the day | ✅ Chrome (12, 22) |
| H18 | `results` has `mode`, `score` and `level_reached`; unknown modes are refused | ✅ |
| Migration | An Iteration 1 database is upgraded with every account and result kept; personal_best set from each user's best test; running it twice changes nothing. Also tried on a copy of our real `typequest.db`. | ✅ |
| L14 | `game_words.json` has 86 short, 81 medium and 70 long words, all the right length | ✅ |
| L16 | `Game` inherits from `TypingSession`; the server refuses scores that are not multiples of 10, don't match the level, need more letters than were typed, are too high for the time played, or claim more time than has passed since Start was pressed | ✅ |
| L18 | Every page has the shared nav bar and one `style.css`; current page highlighted; no font size under 16px | ✅ |
| G8 | Heatmap boundaries: 4% green, 5% and 15% orange, 16% red, 9 presses grey | ✅ |
| G9 | `words.json` has 909 different lower-case words | ✅ |
| G11 | No word more than twice, even for rare weak keys like Q, X and Z | ✅ |
| G13 | Drill shows before and after for each focus key (Chrome: "E: 23.8% to 15.2% (better!)") | ✅ Chrome (15) |
| Reuse | The practice page uses `TypingBox` from `typing.js`; `Game` inherits `TypingSession` | ✅ |
| Privacy | Leaderboard JSON only has rank, username, WPM, accuracy and "you"; usernames are inserted as text so they can't add HTML | ✅ |
| Performance | Leaderboard with 100 users and 2000 results takes well under 1 second | ✅ |
| Accessibility | Heatmap uses the Okabe-Ito colour-blind safe palette; red keys also have stripes and a thick border; grey keys a dashed border; every key shows its % on hover and when tabbed to | ✅ |
| Usability | No horizontal scrolling at 400px wide on Home, Game, Practice and Progress; no Chrome console errors on any page | ✅ Chrome |
| Quality | 10 bugs were added on purpose (one at a time). 7 were caught straight away. The 3 that were missed showed gaps in our tests, so 3 tests were added (see below), and then all 10 were caught. | ✅ |

## Bugs found and fixed during Iteration 2

| # | Found by | Problem | Fix | Re-test |
|---|---|---|---|---|
| 4 | Chrome test | After a drill finished, the page moved the cursor to the **New drill** button. A key pressed straight after the last word (like a space) "clicked" it and the before/after results disappeared before they could be read. The game over panel had the same problem with **Play again**, and players are pressing Enter as the game ends. | The cursor is no longer moved to those buttons. | Chrome run: results stay on screen after finishing; game over panel stays up. ✅ |
| 5 | Chrome test | After pressing This week, the leaderboard showed "52" instead of "52.0", and the drill showed "E: 25% to 16.4%". JavaScript drops the ".0" from whole numbers. | `progress.js` and `practice.js` always show 1 decimal place, like the server does. | Screenshots 15 and 21. ✅ |
| 6 | Screenshot review | After a level up, the Level box stayed yellow for the rest of the game. | It now flashes yellow and fades back to white. | Screenshot 19. ✅ |
| 7 | Screenshot review | The stripes on red heatmap keys were orange, so red keys looked a bit like orange keys. | Darker stripes. | Screenshot 13. ✅ |
| 8 | Code check against L18 | The graph's axis labels were 14px, under the 16px minimum. | Changed to 16px. | `test_L18_text_at_least_16px` and screenshot 20. ✅ |
| 9 | Adding bugs on purpose | `improvement()` still passed T19 when it averaged only the first **2** results, because T19's numbers (20, 22, 21) give 21 either way. | Added `test_H11_averages_use_3_results_each` (10 to 60 must give +30). | Planted bug now caught. ✅ |
| 10 | Adding bugs on purpose | Nothing tested which accuracy is used when one user gets the same best WPM twice, or that drills really use the top **40** words. | Added `test_H12_users_own_tie_uses_their_better_accuracy` and `test_G11_picked_from_top_40_not_just_top_20`. | Planted bugs now caught. ✅ |

## Still to do by the team (not code)

- **Section 1.3 (F1 to F3):** the Iteration 1 client check feedback was not written down anywhere
  in the project files, so these rows are still empty.
- **Section 8:** the Thursday client and Year 7/8 testing session, the rating survey and the
  Iteration 3 changes (Section 8.4).

---

# Iteration 3 Test Results

Test plan from Section 5.1 of the Iteration 3 project specification. Run on 16 October 2026.

- **pytest** = automated tests in `tests/` (`python -m pytest`, 250 tests, all passing). New files:
  `test_reliability.py` (T38-T49) and `test_feedback.py` (T51-T53)
- **Node** = `tests/js/game.test.js` (15 tests) and the new `tests/js/typing.test.js` (5 tests) of the
  browser engines in `game.js` and `typing.js`
- **Chrome** = automated end-to-end run in headless Google Chrome against the running app with the
  demo database and real key presses; screenshots in `docs/screenshots/iteration3/`

> As in earlier iterations, each owner should still run their own tests by hand in Chrome and Edge
> and initial this table before it goes into the planning document. L23 in particular asks for
> Chrome **and Edge** on a real school laptop; only Chrome was used here.

| ID | Owner | Test | Input | Expected result | Actual | Pass? | How |
|---|---|---|---|---|---|---|---|
| T38 | Henry | 404 page | Go to /nothing | TypeQuest 404 page with Home link | "Page not found" page in the TypeQuest layout with a "Go to the home page" button. 405, 413 and 500 also have friendly pages. | ✅ | pytest, Chrome (i3-01) |
| T39 | Henry | Missing database | Delete typequest.db, start app | Tables created, app runs | All 5 tables made on the first request (also with `flask run`); registering works straight away. Deleting the file while the app runs makes it again. | ✅ | pytest |
| T40 | Henry | SQL injection attempt | Username: `' OR 1=1 --` | Login refused, no error | "Incorrect username or password", still logged out. Also tried `typer01' --` and `" OR ""="`. | ✅ | pytest |
| T41 | Henry | Session expiry | Idle over 2 hours | Sent to login with message | Sent to /login with "You were logged out because TypeQuest wasn't used for 2 hours". Still logged in at 1 hour 59 minutes. | ✅ | pytest |
| T42 | Lucas | Typing after time up | Keep typing at 0:00 | Nothing counted | Typed 5 letters, waited 60.5 s with the page's timer stopped, then typed 10 more: the test ended on the first late key and saved 1.0 WPM (the 10 late letters would have made it 3.0) | ✅ | Node, Chrome |
| T43 | Lucas | Backspace | Type 'Thw', backspace, 'e' | Text correct; 1 error counted | The wrong letter turned red, Backspace cleared it, the retyped letter turned green; accuracy 75% (3 of 4 presses), WPM counts the 3 right letters | ✅ | Node, pytest, Chrome (i3-08) |
| T44 | Lucas | Resize during game | Resize window mid-game | Game keeps working | Window made 600 px wide mid-game: the same 2 words stayed on screen, inside the play area, and kept falling | ✅ | Chrome (i3-11) |
| T45 | Lucas | Tab switch | Switch tab mid-game | Game paused | Paused panel shown and words did not move for 1.2 s. Headless Chrome can't really switch tabs, so the page was sent the same "hidden" event a tab switch sends. **Check by hand with a real tab switch.** | ✅ | Chrome (i3-12) |
| T46 | George | Key with 0 presses | New key in stats | No crash, key grey | `error_rate` is None, band grey, not a weak key; a test sending Q with 0 presses saves and the results page loads | ✅ | pytest |
| T47 | George | Missing tip | Remove 'Q' from tips.json | General tip shown | The new `home_row` tip is shown for Q, and tip rotation doesn't crash | ✅ | pytest |
| T48 | George | Few matching words | Weak keys Q, Z, X | Drill still has 20 words | 20 words. With a word bank of only 2 Q words, the drill uses each twice then 16 general words; with a 3-word bank it still makes 20 | ✅ | pytest |
| T49 | George | Brand-new user | Open every page | No errors anywhere | Home, Test, Results, Practice, New drill, Progress, Leaderboard, Game and Settings all load with friendly "nothing yet" messages | ✅ | pytest |
| T51 | Lucas | F5 levels | Destroy 3 words, then more | Level 2 after 3 words, level 3 after 8, level 4 after 15 | Exactly those boundaries in `game.py` and `game.js`; in Chrome the Level box showed "5 words to level 3" straight after the 3rd word | ✅ | pytest, Node, Chrome (i3-10) |
| T52 | Lucas | F6 settings | Tick sound effects and slow mode | Saved and used by the game | Saved to the account; the game page says "Slow mode is on and sound is on" and words fall at 60% speed. Both are off for new accounts. | ✅ | pytest, Node, Chrome (i3-09) |
| T53 | George | F7 finger guide | Student with E, R, O weak | The right fingers highlighted with a sentence each | Left middle, left pointer and right ring fingers highlighted; "E: use your left middle finger. It starts on D."; the practice page updates for each new drill | ✅ | pytest, Chrome (i3-05, i3-07) |
| Regression | All | Re-run all earlier tests | T1 to T37 | All still pass | All pass. Changed on purpose: T27 now levels up at 3 words instead of 100 points (F5), and the test JSON now includes `characters` (L20). One drill test that relied on "more key presses than letters is impossible" now fakes too many right letters instead, because Backspace makes extra key presses possible. | ✅ | pytest |

## Extra checks beyond the test plan

| Requirement | Check | Result |
|---|---|---|
| H21 | Server refuses an unknown account type, passwords over 100 characters, unknown leaderboard filters, unknown settings forms and requests over 64 KB | ✅ |
| H22 | `test_H22_no_string_joined_sql` searches every Python file for SQL built with f-strings, `%`, `.format()` or `+` with a variable | ✅ |
| L20 | The server checks `characters <= correct <= total` and no more than 20 key presses a second | ✅ |
| L23 | No sideways scrolling on Home, Results, Practice, Progress, Settings and Game at 1280 x 720, 1920 x 1080 and 400 px wide; the whole game fits at 1280 x 720 | ✅ Chrome |
| F6 | An Iteration 2 database is upgraded with the new settings columns and every account kept | ✅ |
| Demo | `make_demo_db.py` makes 8 students; logging in as the demo student opens every page | ✅ |
| Console | No JavaScript errors or warnings on any page during the Chrome run (only the expected 404 for /nothing) | ✅ Chrome |
| Quality | Every Python class and function has a docstring; no print statements left in the app | ✅ |

## Bugs found and fixed during Iteration 3

| # | Found by | Problem | Fix | Re-test |
|---|---|---|---|---|
| 11 | Code check for H22 | Two SQL statements were built by joining text: `"... WHERE " + where` in `_find_user` and `f"PRAGMA table_info({table})"`. Only fixed values were ever joined, so they couldn't be attacked, but they broke the H22 rule. | Two separate queries with `?`, and `pragma_table_info(?)`. | `test_H22_no_string_joined_sql` passes and catches both old lines when they are put back. ✅ |
| 12 | Code review for L19 | The timer only checks 10 times a second, so a key pressed in the 0.1 s after 0:00 could still count. | Every key press checks the clock first and ends the test if time is up. | T42 in Chrome. ✅ |
| 13 | Chrome screenshot at 1280 x 720 | The game's typing box was right at the bottom edge of the screen, so on a school laptop with browser toolbars it would be cut off. | The play area is shorter on screens under 760 px tall. | Screenshot i3-10 shows the whole game. ✅ |

## Still to do by the team (not code)

- Run T44, T45 and L23 by hand in **Chrome and Edge** on a real school laptop (T45 with a real tab switch).
- User acceptance testing with 3 Year 7/8 students (Section 5.2) and the final client evaluation (Section 6).
- User guide (Lucas) and updated flowcharts and class diagram: add `FingerGuide`,
  `User.sound_on` / `slow_mode`, and the new `Database` methods.
- **Henry's F-change (T50):** still to be chosen and tested. The spec needs one per member.
