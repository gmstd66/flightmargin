function percent(value) {
    if (value === null || value === undefined) {
        return "--";
    }

    return `${Math.round(value)}%`;
}


function formatCountdown(seconds) {
    if (seconds === null || seconds === undefined) {
        return "--";
    }

    if (seconds <= 0) {
        return "Reset pending";
    }

    const days = Math.floor(seconds / 86400);

    seconds %= 86400;

    const hours = Math.floor(seconds / 3600);

    seconds %= 3600;

    const minutes = Math.floor(seconds / 60);

    if (days > 0) {
        return `Resets in ${days}d ${hours}h ${minutes}m`;
    }

    if (hours > 0) {
        return `Resets in ${hours}h ${minutes}m`;
    }

    return `Resets in ${minutes}m`;
}


function formatDate(timestamp) {
    if (!timestamp) {
        return "--";
    }

    return new Date(timestamp * 1000)
        .toLocaleString([], {
            month: "short",
            day: "numeric",
            hour: "numeric",
            minute: "2-digit"
        });
}


function updateWindow(prefix, data) {
    if (!data) {
        return;
    }

    document.getElementById(
        `${prefix}Remaining`
    ).textContent =
        `${percent(data.remaining)} remaining`;

    document.getElementById(
        `${prefix}Used`
    ).textContent =
        `${percent(data.used)} used`;

    document.getElementById(
        `${prefix}Reset`
    ).textContent =
        formatCountdown(data.seconds_until_reset);

    document.getElementById(
        `${prefix}Bar`
    ).style.width =
        `${Math.max(0, Math.min(100, data.used))}%`;

    const card = document.querySelector(`[data-panel="${prefix === "five" ? "five-hour" : prefix}"]`);
    const remaining = data.remaining;
    card.classList.remove("quota-warning", "quota-critical");
    if (remaining !== null && remaining <= QUOTA_THRESHOLDS.critical) card.classList.add("quota-critical");
    else if (remaining !== null && remaining <= QUOTA_THRESHOLDS.warning) card.classList.add("quota-warning");
}

const QUOTA_THRESHOLDS = Object.freeze({ warning: 25, critical: 10 });
const PANEL_LABELS = Object.freeze({
    "five-hour": "5-hour quota",
    weekly: "Weekly quota",
    pace: "Weekly Pace",
    resets: "Full Resets",
    account: "Account",
    history: "Weekly History"
});
let preferences = null;

async function savePreferences() {
    const response = await fetch("/api/preferences", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(preferences) });
    preferences = await response.json();
    applyPreferences();
}

function applyPreferences() {
    let historyBecameVisible = false;
    Object.entries(preferences.panels).forEach(([id, visible]) => {
        const element = document.querySelector(`[data-panel="${id}"]`);
        if (element) {
            historyBecameVisible ||= id === "history" && element.hidden && visible;
            element.hidden = !visible;
        }
    });
    document.getElementById("trayIndicator").checked = preferences.tray_indicator;
    if (historyBecameVisible) requestAnimationFrame(() => { void loadHistory(); });
}

function renderSettings() {
    const target = document.getElementById("panelSettings");
    target.replaceChildren(...Object.entries(preferences.panels).map(([id, visible]) => {
        const row = document.createElement("div"); row.className = "setting-row";
        row.innerHTML = `<label><input type="checkbox" data-visible="${id}" ${visible ? "checked" : ""}> ${PANEL_LABELS[id]}</label>`;
        return row;
    }));
}

async function loadPreferences() {
    preferences = await (await fetch("/api/preferences", { cache: "no-store" })).json();
    applyPreferences(); renderSettings();
}


async function loadQuota() {
    const response = await fetch(
        "/api/quota",
        { cache: "no-store" }
    );

    if (!response.ok) {
        let message =
            `Quota API returned ${response.status}`;

        try {
            const error = await response.json();
            message = error.detail || message;
        } catch (_error) {
            // Retain the status-based message for non-JSON errors.
        }

        throw new Error(message);
    }

    const data = await response.json();

    updateWindow(
        "five",
        data.five_hour
    );

    updateWindow(
        "weekly",
        data.weekly
    );


    if (data.weekly) {

        document.getElementById(
            "paceStatus"
        ).textContent =
            data.weekly.pace_status;

        document.getElementById(
            "paceRatio"
        ).textContent =
            `${data.weekly.pace_ratio.toFixed(2)}× sustainable pace`;

        document.getElementById(
            "paceDescription"
        ).textContent =
            `${percent(data.weekly.used)} of quota used while ` +
            `${percent(data.weekly.elapsed_percent)} of the weekly window has elapsed.`;

        if (
            data.weekly.projected_exhaustion_at
        ) {

            document.getElementById(
                "exhaustion"
            ).textContent =
                `Projected exhaustion: ${
                    formatDate(
                        data.weekly.projected_exhaustion_at
                    )
                }`;

        } else {

            document.getElementById(
                "exhaustion"
            ).textContent =
                "At the current average pace, the quota should last through reset.";
        }
    }


    document.getElementById(
        "resetCredits"
    ).textContent =
        data.reset_credits_available ?? "--";


    document.getElementById(
        "plan"
    ).textContent =
        data.plan_type
            ? data.plan_type.toUpperCase()
            : "--";


    document.getElementById(
        "credits"
    ).textContent =
        `Credits: ${data.credits_balance ?? "--"}`;


    const captured = new Date(
        data.captured_at * 1000
    );

    document.getElementById(
        "status"
    ).textContent =
        `Last sample ${captured.toLocaleTimeString()}`;
}


async function loadHistory() {
    const response = await fetch(
        "/api/history?hours=168",
        { cache: "no-store" }
    );

    if (!response.ok) {
        return;
    }

    const data = await response.json();

    drawHistory(
        data.samples
    );
}


function drawHistory(samples) {

    const canvas =
        document.getElementById(
            "historyCanvas"
        );

    const rect =
        canvas.getBoundingClientRect();

    const ratio =
        window.devicePixelRatio || 1;

    canvas.width =
        rect.width * ratio;

    const displayHeight = Math.max(38, Math.round(rect.height));

    canvas.height =
        displayHeight * ratio;

    const ctx =
        canvas.getContext("2d");

    ctx.scale(ratio, ratio);

    const width = rect.width;
    const height = displayHeight;

    const compact = height < 80;
    const left = compact ? 28 : 46;
    const right = compact ? 6 : 12;
    const top = compact ? 4 : 15;
    const bottom = compact ? 14 : 34;

    const graphWidth =
        width - left - right;

    const graphHeight =
        height - top - bottom;


    ctx.clearRect(
        0,
        0,
        width,
        height
    );


    /*
     * Fixed rolling 7-day time window.
     */
    const maxTime =
        Math.floor(Date.now() / 1000);

    const minTime =
        maxTime - (7 * 24 * 3600);

    const range =
        maxTime - minTime;


    function timeToX(timestamp) {
        return (
            left +
            (
                (timestamp - minTime) /
                range
            ) *
            graphWidth
        );
    }


    /*
     * Horizontal percentage grid.
     */
    ctx.font = "11px system-ui";
    ctx.fillStyle = "#7d828b";
    ctx.strokeStyle = "#2d3036";
    ctx.lineWidth = 1;

    [0, 25, 50, 75, 100]
        .forEach(value => {

            const y =
                top +
                graphHeight *
                (1 - value / 100);

            ctx.beginPath();

            ctx.moveTo(
                left,
                y
            );

            ctx.lineTo(
                width - right,
                y
            );

            ctx.stroke();

            ctx.fillText(
                `${value}%`,
                4,
                y + 4
            );
        });


    /*
     * Find the first 4-hour block
     * inside the current 7-day window.
     */
    const firstGridDate =
        new Date(minTime * 1000);

    firstGridDate.setMinutes(
        0,
        0,
        0
    );

    const firstHour =
        firstGridDate.getHours();

    const hoursToNextGrid =
        (4 - (firstHour % 4)) % 4;

    firstGridDate.setHours(
        firstHour + hoursToNextGrid
    );

    let gridTime =
        Math.floor(
            firstGridDate.getTime() / 1000
        );

    const fourHours =
        4 * 3600;


    /*
     * Vertical grid:
     *
     * Every 4 hours = minor line
     * Midnight       = major day line
     */
    while (gridTime <= maxTime) {

        const date =
            new Date(gridTime * 1000);

        const x =
            timeToX(gridTime);

        const hour =
            date.getHours();

        const midnight =
            hour === 0;


        ctx.beginPath();

        ctx.strokeStyle =
            midnight
                ? "#454950"
                : "#25282d";

        ctx.lineWidth =
            midnight
                ? 1.2
                : 1;

        ctx.moveTo(
            x,
            top
        );

        ctx.lineTo(
            x,
            top + graphHeight
        );

        ctx.stroke();


        /*
         * Day label under each midnight line.
         */
        if (midnight) {

            const label =
                date.toLocaleDateString(
                    [],
                    {
                        weekday: "short",
                        day: "numeric"
                    }
                );

            ctx.fillStyle =
                "#9ca1a9";

            ctx.font =
                "11px system-ui";

            ctx.textAlign =
                "center";

            ctx.fillText(
                label,
                x,
                height - 10
            );
        }

        gridTime += fourHours;
    }


    /*
     * Hour labels for each 4-hour grid.
     *
     * Midnight is left unlabeled because
     * the day label already identifies it.
     */
    gridTime =
        Math.floor(
            firstGridDate.getTime() / 1000
        );

    while (gridTime <= maxTime) {

        const date =
            new Date(gridTime * 1000);

        const hour =
            date.getHours();

        if (hour !== 0) {

            const x =
                timeToX(gridTime);

            ctx.fillStyle =
                "#626770";

            ctx.font =
                "9px system-ui";

            ctx.textAlign =
                "center";

            ctx.fillText(
                String(hour)
                    .padStart(2, "0"),
                x,
                top + graphHeight + 15
            );
        }

        gridTime += fourHours;
    }


    ctx.textAlign = "left";


    /*
     * If there are no samples,
     * leave the time/grid axis visible.
     */
    if (!samples.length) {
        return;
    }


    /*
     * Weekly quota usage line.
     */
    ctx.strokeStyle =
        "#e5e7eb";

    ctx.lineWidth = 2;

    ctx.beginPath();

    let started = false;


    samples.forEach(sample => {

        if (
            sample.weekly_used === null ||
            sample.weekly_used === undefined
        ) {
            return;
        }

        if (
            sample.captured_at < minTime ||
            sample.captured_at > maxTime
        ) {
            return;
        }

        const x =
            timeToX(
                sample.captured_at
            );

        const y =
            top +
            graphHeight *
            (
                1 -
                sample.weekly_used /
                100
            );

        if (!started) {

            ctx.moveTo(
                x,
                y
            );

            started = true;

        } else {

            ctx.lineTo(
                x,
                y
            );
        }
    });


    if (started) {
        ctx.stroke();
    }
}


async function reloadAll() {

    try {

        await Promise.all([
            loadQuota(),
            loadHistory()
        ]);

    } catch (error) {

        document.getElementById(
            "status"
        ).textContent =
            `Error: ${error.message}`;
    }
}


document.getElementById(
    "refresh"
).addEventListener(
    "click",
    async () => {

        const button =
            document.getElementById(
                "refresh"
            );

        button.disabled = true;
        button.textContent =
            "Refreshing…";

        try {

            const response =
                await fetch(
                    "/api/refresh",
                    {
                        method: "POST"
                    }
                );

            if (!response.ok) {
                throw new Error(
                    `Refresh failed: ${
                        response.status
                    }`
                );
            }

            await reloadAll();

        } catch (error) {

            document.getElementById(
                "status"
            ).textContent =
                error.message;

        } finally {

            button.disabled = false;
            button.textContent =
                "Refresh";
        }
    }
);


document.getElementById("settings").addEventListener("click", () => document.getElementById("settingsDialog").showModal());
document.getElementById("trayIndicator").addEventListener("change", async event => { preferences.tray_indicator = event.target.checked; await savePreferences(); });
document.getElementById("panelSettings").addEventListener("change", async event => {
    const panelId = event.target.dataset.visible;
    if (!panelId) return;
    preferences.panels[panelId] = event.target.checked;
    applyPreferences();
    await savePreferences();
});
document.getElementById("showAllPanels").addEventListener("click", async () => {
    preferences = await (await fetch("/api/preferences/show-all", { method: "POST" })).json();
    applyPreferences();
    renderSettings();
});

loadPreferences().catch(error => { document.getElementById("status").textContent = `Settings unavailable: ${error.message}`; });
reloadAll();


/*
 * The server samples Codex every 60 seconds.
 *
 * The browser only reloads values from the
 * local FastAPI/SQLite backend every 15 seconds,
 * so this does not increase Codex quota polling.
 */
setInterval(
    reloadAll,
    15000
);


window.addEventListener(
    "resize",
    loadHistory
);
