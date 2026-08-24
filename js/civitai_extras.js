import { app } from "/scripts/app.js";

// Additive extension: adds a domain switcher, an API key input, and a Base
// Model filter for the Models Gallery, WITHOUT touching the
// civitai_models_gallery.js bundle. It works by patching window.fetch to
// inject the chosen options into the requests that bundle (and the images
// gallery) already make to this node pack's own backend routes
// (/civitai_gallery/*, /civitai_models_gallery/*).

const STORAGE_KEY = "civitai_gallery_extras_v1";
const DOMAIN_OPTIONS = ["civitai.red", "civitai.com"];

function loadPrefs() {
    let stored = {};
    try {
        stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
    } catch (e) {
        stored = {};
    }
    const prefs = Object.assign({ domain: "civitai.red", baseModel: "" }, stored);
    if (!DOMAIN_OPTIONS.includes(prefs.domain)) prefs.domain = "civitai.red";
    return prefs;
}

function savePrefs(prefs) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch (e) {
        console.error("CivitaiExtras: failed to persist preferences", e);
    }
}

const prefs = loadPrefs();
const originalFetch = window.fetch.bind(window);

function isGalleryUrl(url) {
    return typeof url === "string" && (url.includes("/civitai_gallery/") || url.includes("/civitai_models_gallery/"));
}

window.fetch = function (input, init) {
    try {
        const rawUrl = typeof input === "string" ? input : (input && input.url);
        if (rawUrl && isGalleryUrl(rawUrl)) {
            const method = (((init && init.method) || (typeof input !== "string" && input.method) || "GET") + "").toUpperCase();
            if (method === "GET") {
                const u = new URL(rawUrl, window.location.origin);
                if (prefs.domain) u.searchParams.set("domain", prefs.domain);
                if (prefs.baseModel && u.pathname.includes("/civitai_models_gallery/models")) {
                    u.searchParams.set("baseModels", prefs.baseModel);
                }
                const newUrl = u.pathname + u.search;
                input = (typeof input === "string") ? newUrl : new Request(newUrl, input);
            } else if (init && typeof init.body === "string") {
                try {
                    const bodyObj = JSON.parse(init.body);
                    if (prefs.domain) bodyObj.domain = prefs.domain;
                    init = Object.assign({}, init, { body: JSON.stringify(bodyObj) });
                } catch (e) {
                    // body wasn't JSON, leave it alone
                }
            }
        }
    } catch (e) {
        console.error("CivitaiExtras: fetch patch error", e);
    }
    return originalFetch(input, init);
};

function buildPanel() {
    const wrap = document.createElement("div");
    wrap.style.cssText = `
        position: fixed; bottom: 16px; right: 16px; z-index: 9999;
        font-family: sans-serif; font-size: 12px;
    `;

    const toggleBtn = document.createElement("button");
    toggleBtn.textContent = "🖼️ Civitai";
    toggleBtn.title = "Civitai Gallery settings (domain / API key / base model filter)";
    toggleBtn.style.cssText = `
        background: #353535; color: #ddd; border: 1px solid #555; border-radius: 6px;
        padding: 6px 10px; cursor: pointer;
    `;

    const panel = document.createElement("div");
    panel.style.cssText = `
        display: none; position: absolute; bottom: 36px; right: 0;
        background: #2a2a2a; border: 1px solid #555; border-radius: 8px;
        padding: 12px; width: 260px; color: #ddd; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    `;

    panel.innerHTML = `
        <div style="font-weight:600; margin-bottom:8px;">Civitai Gallery Settings</div>

        <label style="display:block; margin-bottom:4px; opacity:0.8;">Domain / Mirror</label>
        <select id="civitai-extras-domain" style="width:100%; margin-bottom:10px; background:#1e1e1e; color:#ddd; border:1px solid #555; border-radius:4px; padding:4px;">
            ${DOMAIN_OPTIONS.map(d => `<option value="${d}">${d}</option>`).join("")}
        </select>

        <label style="display:block; margin-bottom:4px; opacity:0.8;">Base Model Filter (Models Gallery)</label>
        <input id="civitai-extras-basemodel" type="text" placeholder="e.g. SDXL 1.0"
            style="width:100%; margin-bottom:10px; background:#1e1e1e; color:#ddd; border:1px solid #555; border-radius:4px; padding:4px; box-sizing:border-box;" />

        <label style="display:block; margin-bottom:4px; opacity:0.8;">Civitai API Key</label>
        <input id="civitai-extras-apikey" type="password" placeholder="Enter API key to save"
            style="width:100%; margin-bottom:6px; background:#1e1e1e; color:#ddd; border:1px solid #555; border-radius:4px; padding:4px; box-sizing:border-box;" />
        <button id="civitai-extras-save" style="width:100%; padding:5px; background:#4a7; border:none; border-radius:4px; color:#111; cursor:pointer; font-weight:600;">
            Save API Key
        </button>
        <div id="civitai-extras-status" style="margin-top:6px; opacity:0.75;"></div>
    `;

    wrap.appendChild(panel);
    wrap.appendChild(toggleBtn);
    document.body.appendChild(wrap);

    const domainSelect = panel.querySelector("#civitai-extras-domain");
    const baseModelInput = panel.querySelector("#civitai-extras-basemodel");
    const apiKeyInput = panel.querySelector("#civitai-extras-apikey");
    const saveBtn = panel.querySelector("#civitai-extras-save");
    const statusEl = panel.querySelector("#civitai-extras-status");

    domainSelect.value = prefs.domain;
    baseModelInput.value = prefs.baseModel;

    domainSelect.addEventListener("change", () => {
        prefs.domain = domainSelect.value;
        savePrefs(prefs);
    });

    baseModelInput.addEventListener("change", () => {
        prefs.baseModel = baseModelInput.value.trim();
        savePrefs(prefs);
    });

    saveBtn.addEventListener("click", async () => {
        const key = apiKeyInput.value.trim();
        if (!key) {
            statusEl.textContent = "Enter a key first.";
            return;
        }
        statusEl.textContent = "Saving...";
        try {
            const res = await originalFetch("/civitai_gallery/save_api_key", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ api_key: key }),
            });
            const data = await res.json();
            if (data.status === "success") {
                statusEl.textContent = "✅ API key saved.";
                apiKeyInput.value = "";
                refreshStatus();
            } else {
                statusEl.textContent = "❌ " + (data.message || "Failed to save.");
            }
        } catch (e) {
            statusEl.textContent = "❌ " + e.message;
        }
    });

    async function refreshStatus() {
        try {
            const res = await originalFetch("/civitai_gallery/api_key_status");
            const data = await res.json();
            if (data.has_key) {
                statusEl.textContent = "🔑 API key is configured.";
            }
        } catch (e) {
            // ignore
        }
    }

    toggleBtn.addEventListener("click", () => {
        const isOpen = panel.style.display === "block";
        panel.style.display = isOpen ? "none" : "block";
        if (!isOpen) refreshStatus();
    });
}

app.registerExtension({
    name: "Civitai.GalleryExtras",
    async setup() {
        buildPanel();
    },
});
