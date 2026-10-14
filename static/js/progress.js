// Progress page.  Owner: Henry (H10, H14).
//
// Draws the WPM-over-time line graph with Chart.js (loaded first on the page), and
// makes the This week / All time buttons change the leaderboard without reloading.

"use strict";

if (document.getElementById("progress")) {
  const page = document.getElementById("progress");
  const leaderboardUrl = page.dataset.leaderboardUrl;

  // ---------- H10: WPM over time ----------

  const canvas = document.getElementById("wpm-graph");
  if (canvas) {
    const graph = JSON.parse(canvas.dataset.graph);
    const styles = getComputedStyle(document.documentElement);
    const lineColour = styles.getPropertyValue("--graph").trim();
    const inkColour = styles.getPropertyValue("--ink").trim();

    new Chart(canvas, {
      type: "line",
      data: {
        labels: graph.labels,
        datasets: [{
          label: "WPM",
          data: graph.wpm,
          borderColor: lineColour,
          backgroundColor: lineColour,
          pointRadius: 5,
          pointHoverRadius: 7,
          tension: 0.2,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              // e.g. "Test 3 (2026-10-14)"
              title: (items) => `${items[0].label} (${graph.dates[items[0].dataIndex]})`,
              label: (item) => `${item.parsed.y} WPM`,
            },
          },
        },
        scales: {
          x: {
            title: { display: true, text: "Tests (oldest to newest)", color: inkColour, font: { size: 16 } },
            ticks: { color: inkColour, font: { size: 16 } },
          },
          y: {
            beginAtZero: true,
            title: { display: true, text: "WPM", color: inkColour, font: { size: 16 } },
            ticks: { color: inkColour, font: { size: 16 }, precision: 0 },
          },
        },
      },
    });
  }

  // ---------- H12-H14: leaderboard ----------

  const tableBody = document.getElementById("leaderboard-rows");
  const yourRank = document.getElementById("your-rank");
  const emptyMessage = document.getElementById("leaderboard-empty");
  const filterButtons = document.querySelectorAll("button.filter");

  // 52 -> "52.0", the same as the server shows it
  const oneDecimal = (number) => Number(number).toFixed(1);

  function drawLeaderboard(board) {
    tableBody.replaceChildren(
      ...board.rows.map((row) => {
        const tableRow = document.createElement("tr");
        if (row.you) tableRow.className = "you";
        const name = row.you ? `${row.username} (you)` : row.username;
        for (const value of [row.rank, name, oneDecimal(row.wpm)]) {
          const cell = document.createElement("td");
          cell.textContent = value; // textContent, so a username can never add HTML
          tableRow.appendChild(cell);
        }
        return tableRow;
      }),
    );
    emptyMessage.hidden = board.rows.length > 0;

    // H13: the user's own place when they are outside the top 10.
    if (board.you && !board.you.in_top) {
      yourRank.textContent = `You: ${board.you.place}, ${oneDecimal(board.you.wpm)} WPM`;
      yourRank.hidden = false;
    } else if (!board.you && board.rows.length > 0) {
      yourRank.textContent = board.period === "week"
        ? "You haven't done a test this week. Do one to get on the board!"
        : "Do a typing test to get on the board!";
      yourRank.hidden = false;
    } else {
      yourRank.hidden = true;
    }
  }

  async function loadLeaderboard(period) {
    filterButtons.forEach((button) => {
      const selected = button.dataset.period === period;
      button.classList.toggle("selected", selected);
      button.setAttribute("aria-pressed", String(selected));
    });
    try {
      const response = await fetch(`${leaderboardUrl}?period=${period}`);
      if (!response.ok) throw new Error();
      drawLeaderboard(await response.json());
    } catch {
      yourRank.textContent = "Could not load the leaderboard. Check you are still logged in.";
      yourRank.hidden = false;
    }
  }

  filterButtons.forEach((button) =>
    button.addEventListener("click", () => loadLeaderboard(button.dataset.period)),
  );
}
