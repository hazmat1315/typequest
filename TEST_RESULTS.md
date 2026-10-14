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
