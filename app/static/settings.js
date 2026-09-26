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
let aboutInformation = null;

function nativeInvoke() {
    return window.__TAURI__?.core?.invoke
        ?? window.__TAURI_INTERNALS__?.invoke
        ?? null;
}

function tauriInvoke(command) {
    const invoke = nativeInvoke();
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

function showSettingsSection(sectionName) {
    document.querySelectorAll("[data-settings-section]").forEach(section => {
        section.hidden = section.dataset.settingsSection !== sectionName;
    });
    document.querySelectorAll("[data-settings-tab]").forEach(button => {
        const active = button.dataset.settingsTab === sectionName;
        button.classList.toggle("is-active", active);
        button.setAttribute("aria-selected", String(active));
    });
}

function openSettingsSection(sectionName) {
    const availableSections = new Set(
        nativeInvoke()
            ? ["dashboard", "startup", "tray", "about"]
            : ["dashboard", "about"]
    );
    const targetSection = availableSections.has(sectionName) ? sectionName : "dashboard";
    showSettingsSection(targetSection);
    if (targetSection === "about" && !aboutInformation) {
        loadAbout().catch(error => {
            document.getElementById("settingsStatus").textContent =
                `About information unavailable: ${error.message}`;
        });
    }
}

window.openSettingsSection = openSettingsSection;

if (!nativeInvoke()) {
    document.querySelectorAll("[data-native-only]").forEach(element => {
        element.hidden = true;
    });
}

function renderAbout(information) {
    const codexVersion = information.codex_cli_version;
    document.getElementById("aboutVersion").textContent =
        `Version ${information.app_version} · ${information.status}`;
    document.getElementById("aboutCodex").textContent = codexVersion
        ? `Detected: ${codexVersion}`
        : "Not detected";
    document.getElementById("detailAppVersion").textContent = information.app_version;
    document.getElementById("detailCodexVersion").textContent = codexVersion ?? "Not detected";
    document.getElementById("detailOperatingSystem").textContent = information.operating_system;
    document.getElementById("detailArchitecture").textContent = information.architecture;
    document.getElementById("detailDataDirectory").textContent = information.data_directory;
    document.getElementById("detailLogDirectory").textContent = information.log_directory;
    document.getElementById("aboutCopyright").textContent =
        `© ${information.copyright_year} ${information.copyright_owner}`;
    document.getElementById("copyDiagnostics").disabled = false;
}

async function loadAbout() {
    aboutInformation = await (await fetch("/api/about", { cache: "no-store" })).json();
    renderAbout(aboutInformation);
}

async function copyText(text) {
    if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        return;
    }
    const field = document.createElement("textarea");
    field.value = text;
    field.style.position = "fixed";
    field.style.opacity = "0";
    document.body.appendChild(field);
    field.select();
    document.execCommand("copy");
    field.remove();
}

document.querySelectorAll("[data-settings-tab]").forEach(button => {
    button.addEventListener("click", () => {
        openSettingsSection(button.dataset.settingsTab);
    });
});

openSettingsSection(new URLSearchParams(window.location.search).get("section"));

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

document.getElementById("copyDiagnostics").addEventListener("click", async () => {
    if (!aboutInformation) return;
    const status = document.getElementById("copyDiagnosticsStatus");
    try {
        await copyText(aboutInformation.diagnostics);
        status.textContent = "Copied";
        window.setTimeout(() => { status.textContent = ""; }, 2000);
    } catch (error) {
        status.textContent = `Copy failed: ${error.message}`;
    }
});

document.getElementById("closeSettings").addEventListener("click", async () => {
    if (!nativeInvoke()) {
        window.location.assign("/");
        return;
    }
    try {
        await tauriInvoke("close_settings");
    } catch (error) {
        document.getElementById("settingsStatus").textContent = `Unable to close Settings: ${error}`;
    }
});

loadPreferences().catch(error => {
    document.getElementById("settingsStatus").textContent = `Settings unavailable: ${error.message}`;
});
