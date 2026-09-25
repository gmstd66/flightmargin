const PANEL_LABELS = Object.freeze({
    "five-hour": "5-hour quota",
    weekly: "Weekly quota",
    pace: "Weekly Pace",
    resets: "Full Resets",
    account: "Account",
    history: "Weekly History"
});
const preferenceChannel = "BroadcastChannel" in window
    ? new BroadcastChannel("codex-quota-preferences")
    : null;
let preferences = null;

function tauriInvoke(command) {
    const invoke = window.__TAURI__?.core?.invoke
        ?? window.__TAURI_INTERNALS__?.invoke;
    if (!invoke) throw new Error("Native Settings bridge is unavailable");
    return invoke(command);
}

function renderSettings() {
    const target = document.getElementById("panelSettings");
    target.replaceChildren(...Object.entries(preferences.panels).map(([id, visible]) => {
        const row = document.createElement("div");
        row.className = "setting-row";
        row.innerHTML = `<label><input type="checkbox" data-visible="${id}" ${visible ? "checked" : ""}> ${PANEL_LABELS[id]}</label>`;
        return row;
    }));
    document.getElementById("trayIndicator").checked = preferences.tray_indicator;
}

async function loadPreferences() {
    preferences = await (await fetch("/api/preferences", { cache: "no-store" })).json();
    renderSettings();
}

async function savePreferences() {
    const response = await fetch("/api/preferences", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(preferences)
    });
    preferences = await response.json();
    renderSettings();
    preferenceChannel?.postMessage("changed");
}

document.getElementById("trayIndicator").addEventListener("change", async event => {
    preferences.tray_indicator = event.target.checked;
    await savePreferences();
});

document.getElementById("panelSettings").addEventListener("change", async event => {
    const panelId = event.target.dataset.visible;
    if (!panelId) return;
    preferences.panels[panelId] = event.target.checked;
    await savePreferences();
});

document.getElementById("showAllPanels").addEventListener("click", async () => {
    preferences = await (await fetch("/api/preferences/show-all", { method: "POST" })).json();
    renderSettings();
    preferenceChannel?.postMessage("changed");
});

document.getElementById("closeSettings").addEventListener("click", async () => {
    try {
        await tauriInvoke("close_settings");
    } catch (error) {
        document.getElementById("settingsStatus").textContent = `Unable to close Settings: ${error}`;
    }
});

loadPreferences().catch(error => {
    document.getElementById("settingsStatus").textContent = `Settings unavailable: ${error.message}`;
});
