import { app } from "/scripts/app.js";

// Clean, non-obfuscated replacement for the previous minified civitai_gallery.js
// bundle, which threw "checkOnLayout is not defined" and never rendered images.
// Talks to the existing /civitai_gallery/images backend route (unchanged) and
// fills the CivitaiGalleryNode's hidden "selection_data" widget with the raw
// Civitai API item the user clicked, exactly as the Python node expects:
//   { item: <civitai image item>, download_image: <is "image" output wired up> }

const NSFW_OPTIONS = [
    ["None", "安全 (None)"],
    ["Soft", "一般 (Soft)"],
    ["Mature", "成人 (Mature)"],
    ["X", "限制級 (X)"],
];
const SORT_OPTIONS = [
    ["Most Reactions", "最多反應"],
    ["Most Comments", "最多留言"],
    ["Newest", "最新"],
];
const PERIOD_OPTIONS = [
    ["Day", "今日"],
    ["Week", "本週"],
    ["Month", "本月"],
    ["Year", "今年"],
    ["AllTime", "所有時間"],
];

function el(tag, style, props) {
    const e = document.createElement(tag);
    if (style) Object.assign(e.style, style);
    if (props) Object.assign(e, props);
    return e;
}

function thumbUrl(url, width) {
    if (!url) return url;
    if (/\/width=\d+\//.test(url)) return url.replace(/\/width=\d+\//, `/width=${width}/`);
    if (url.includes("/original=true/")) return url.replace("/original=true/", `/width=${width}/`);
    return url;
}

function extractModelId(value) {
    if (!value) return null;
    const m = value.match(/models\/(\d+)/) || value.match(/^\s*(\d+)\s*$/);
    return m ? m[1] : null;
}

function isImageOutputConnected(node) {
    const out = node.outputs && node.outputs[2];
    return !!(out && out.links && out.links.length > 0);
}

const selectStyle = {
    background: "#1e1e1e", color: "#ddd", border: "1px solid #555",
    borderRadius: "3px", padding: "2px 4px", fontSize: "11px",
};

function setupCivitaiGallery(node) {
    node.setSize([460, 640]);

    let selectionWidget = node.widgets?.find((w) => w.name === "selection_data");
    if (!selectionWidget) {
        selectionWidget = node.addWidget("text", "selection_data", "{}", () => {}, { serialize: true });
    }
    selectionWidget.computeSize = () => [0, -4];
    selectionWidget.draw = () => {};
    selectionWidget.type = "hidden";

    let selectedItem = null;
    const refreshSelection = () => {
        if (!selectedItem) return;
        selectionWidget.value = JSON.stringify({
            item: selectedItem,
            download_image: isImageOutputConnected(node),
        });
    };
    node._civitaiRefreshSelection = refreshSelection;

    const root = el("div", {
        display: "flex", flexDirection: "column", gap: "6px", height: "100%", width: "100%",
        boxSizing: "border-box", padding: "4px", fontFamily: "sans-serif", fontSize: "11px", color: "#ddd",
    });

    const filterRow1 = el("div", { display: "flex", gap: "4px", flexWrap: "wrap" });
    const filterRow2 = el("div", { display: "flex", gap: "4px", flexWrap: "wrap" });

    const nsfwSelect = el("select", selectStyle);
    NSFW_OPTIONS.forEach(([v, l]) => nsfwSelect.appendChild(el("option", null, { value: v, textContent: l })));

    const sortSelect = el("select", selectStyle);
    SORT_OPTIONS.forEach(([v, l]) => sortSelect.appendChild(el("option", null, { value: v, textContent: l })));

    const periodSelect = el("select", selectStyle);
    PERIOD_OPTIONS.forEach(([v, l]) => periodSelect.appendChild(el("option", null, { value: v, textContent: l })));
    periodSelect.value = "Month";

    const usernameInput = el("input", { ...selectStyle, flex: "1", minWidth: "70px" }, { type: "text", placeholder: "Username" });
    const modelInput = el("input", { ...selectStyle, flex: "1", minWidth: "70px" }, { type: "text", placeholder: "Model ID 或 civitai.com/models/12345" });

    const refreshBtn = el("button", { ...selectStyle, cursor: "pointer" }, { textContent: "🔄 Refresh" });

    filterRow1.append(nsfwSelect, sortSelect, periodSelect, refreshBtn);
    filterRow2.append(usernameInput, modelInput);

    const statusEl = el("div", { opacity: "0.7", minHeight: "14px" });

    const THUMB_SIZE = 90;
    const gridEl = el("div", {
        display: "flex", flexWrap: "wrap", alignContent: "flex-start",
        gap: "4px", overflowY: "auto", overflowX: "hidden", flex: "1 1 0", minHeight: "0",
        border: "1px solid #444", borderRadius: "4px", padding: "4px", background: "#161616",
    });

    const loadMoreBtn = el("button", { ...selectStyle, cursor: "pointer", width: "100%", marginTop: "2px", display: "none" }, { textContent: "載入更多" });

    const detailEl = el("div", {
        display: "none", flexDirection: "column", gap: "4px", maxHeight: "45%",
        overflowY: "auto", border: "1px solid #444", borderRadius: "4px", padding: "6px", background: "#1c1c1c", flexShrink: "0",
    });

    root.append(filterRow1, filterRow2, statusEl, gridEl, loadMoreBtn, detailEl);

    node.addDOMWidget("civitai_gallery_ui", "div", root, { onDraw: () => {} });
    setTimeout(() => node.onResize?.(node.size), 10);

    let cursor = null;
    let loading = false;

    function buildParams() {
        const p = new URLSearchParams({
            nsfw: nsfwSelect.value,
            sort: sortSelect.value,
            period: periodSelect.value,
            domain: "civitai.red",
        });
        const modelId = extractModelId(modelInput.value);
        if (modelId) {
            p.set("modelId", modelId);
        } else if (usernameInput.value.trim()) {
            p.set("username", usernameInput.value.trim());
        }
        if (cursor) p.set("cursor", cursor);
        return p;
    }

    async function loadImages(reset) {
        if (loading) return;
        loading = true;
        if (reset) {
            cursor = null;
            gridEl.innerHTML = "";
        }
        statusEl.textContent = "載入中...";
        loadMoreBtn.disabled = true;
        try {
            const res = await fetch(`/civitai_gallery/images?${buildParams().toString()}`);
            const data = await res.json();
            if (!res.ok || data.error) throw new Error(data.error || `HTTP ${res.status}`);
            const items = data.items || [];
            items.forEach((item) => gridEl.appendChild(buildThumb(item)));
            cursor = data.metadata?.nextCursor || null;
            loadMoreBtn.style.display = cursor ? "block" : "none";
            statusEl.textContent = gridEl.children.length
                ? `已載入 ${gridEl.children.length} 張圖片`
                : "沒有找到符合的圖片";
        } catch (e) {
            statusEl.textContent = "❌ 讀取失敗：" + e.message;
            console.error("CivitaiGallery:", e);
        } finally {
            loading = false;
            loadMoreBtn.disabled = false;
        }
    }

    function buildThumb(item) {
        const wrap = el("div", {
            position: "relative", width: `${THUMB_SIZE}px`, height: `${THUMB_SIZE}px`, flex: "0 0 auto",
            overflow: "hidden", borderRadius: "3px",
            cursor: "pointer", border: "2px solid transparent", background: "#111",
        });
        const img = el("img", { width: "100%", height: "100%", objectFit: "cover", display: "block" });
        img.loading = "lazy";
        img.src = thumbUrl(item.url, 300);
        wrap.appendChild(img);
        wrap.addEventListener("click", () => selectItem(item, wrap));
        return wrap;
    }

    function selectItem(item, wrapEl) {
        selectedItem = item;
        refreshSelection();
        Array.from(gridEl.children).forEach((c) => (c.style.borderColor = "transparent"));
        if (wrapEl) wrapEl.style.borderColor = "#4a7";
        renderDetail(item);
    }

    function buildPromptBox(label, text) {
        const box = el("div", { display: "flex", flexDirection: "column", gap: "2px" });
        const row = el("div", { display: "flex", justifyContent: "space-between", alignItems: "center" });
        row.appendChild(el("div", { fontWeight: "600" }, { textContent: label }));
        const copyBtn = el("button", { ...selectStyle, padding: "1px 6px", cursor: "pointer" }, { textContent: "複製" });
        copyBtn.addEventListener("click", () => {
            navigator.clipboard?.writeText(text || "").then(() => {
                copyBtn.textContent = "已複製";
                setTimeout(() => (copyBtn.textContent = "複製"), 1200);
            }).catch(() => {});
        });
        row.appendChild(copyBtn);
        box.appendChild(row);
        const ta = el("textarea", {
            width: "100%", minHeight: "44px", resize: "vertical", background: "#111", color: "#ccc",
            border: "1px solid #333", borderRadius: "3px", fontSize: "10px", boxSizing: "border-box",
        }, { readOnly: true, value: text || "" });
        box.appendChild(ta);
        return box;
    }

    function renderDetail(item) {
        detailEl.innerHTML = "";
        detailEl.style.display = "flex";
        const meta = item.meta || {};

        detailEl.appendChild(el("div", { opacity: "0.75" }, {
            textContent: `👤 ${item.username || "?"}  |  ${item.width || "?"}x${item.height || "?"}  |  ${item.baseModel || ""}`,
        }));

        detailEl.appendChild(buildPromptBox("Positive Prompt", meta.prompt));
        detailEl.appendChild(buildPromptBox("Negative Prompt", meta.negativePrompt));

        const otherKeys = Object.keys(meta).filter((k) => k !== "prompt" && k !== "negativePrompt");
        if (otherKeys.length) {
            const paramsBox = el("div", {
                display: "flex", flexDirection: "column", gap: "2px",
                background: "#151515", border: "1px solid #333", borderRadius: "3px", padding: "4px",
            });
            otherKeys.forEach((k) => {
                let v = meta[k];
                if (v && typeof v === "object") v = JSON.stringify(v);
                paramsBox.appendChild(el("div", null, { textContent: `${k}: ${v}` }));
            });
            detailEl.appendChild(paramsBox);
        } else {
            detailEl.appendChild(el("div", { opacity: "0.6", fontStyle: "italic" }, { textContent: "此圖片未公開生成參數" }));
        }
    }

    refreshBtn.addEventListener("click", () => loadImages(true));
    loadMoreBtn.addEventListener("click", () => loadImages(false));
    [nsfwSelect, sortSelect, periodSelect].forEach((e) => e.addEventListener("change", () => loadImages(true)));
    usernameInput.addEventListener("keydown", (e) => { if (e.key === "Enter") loadImages(true); });
    modelInput.addEventListener("keydown", (e) => { if (e.key === "Enter") loadImages(true); });

    loadImages(true);
}

app.registerExtension({
    name: "Civitai.GalleryLite",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "CivitaiGalleryNode") return;

        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            onNodeCreated?.apply(this, arguments);
            setupCivitaiGallery(this);
        };

        const onConnectionsChange = nodeType.prototype.onConnectionsChange;
        nodeType.prototype.onConnectionsChange = function (...args) {
            onConnectionsChange?.apply(this, args);
            this._civitaiRefreshSelection?.();
        };
    },
});
