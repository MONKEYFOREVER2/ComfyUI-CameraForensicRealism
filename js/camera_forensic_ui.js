import { app } from "../../scripts/app.js";

/**
 * 📸 Camera Forensic Realism Engine — Premium UI Dashboard (v4)
 * ==============================================================
 * Gold/Black themed DOM widget replacing ALL default drawing.
 * Matches the v4 iPhone 17 pipeline parameter set.
 */

const NODE_NAME = "CameraForensicRealismEngine";
const NODE_MIN_WIDTH = 420;
const NODE_TITLE_HEIGHT = 40;

const SECTIONS = {
    master: { icon: "⚡", label: "Master", toggle: null },
    wb:     { icon: "☀️", label: "White Balance", toggle: "enable_white_balance" },
    tone:   { icon: "🌓", label: "Global Tone", toggle: "enable_tone" },
    hdr:    { icon: "✨", label: "Smart HDR", toggle: "enable_smart_hdr" },
    color:  { icon: "🎨", label: "Color Science (Oklab)", toggle: "enable_color" },
    detail: { icon: "🔪", label: "Detail", toggle: "enable_detail" },
    optics: { icon: "📷", label: "Optics & Sensor", toggle: "enable_optics" },
};

const WIDGET_META = {
    photographic_style: { type: "combo", section: "master", label: "Style", desc: "iPhone 17 Photographic Style preset. Undertones steer warmth, moods steer tone+color. Applied as offsets on top of your sliders." },
    master_strength: { type: "slider", section: "master", label: "Master Strength", min: 0, max: 1, step: 0.01, desc: "Final blend between original and fully processed image." },
    seed: { type: "number", section: "master", label: "Seed", desc: "Random seed for grain reproducibility." },
    control_after_generate: { type: "combo", section: "master", label: "Seed Mode", desc: "Change seed behavior after generation." },

    enable_white_balance: { type: "toggle", section: "wb", label: "Enable", desc: "Channel gains in linear light, luminance-preserving." },
    wb_temperature: { type: "slider", section: "wb", label: "Temperature", min: -1, max: 1, step: 0.01, desc: "Blue-Orange axis. iPhone AWB sits slightly warm (~0.1)." },
    wb_tint: { type: "slider", section: "wb", label: "Tint", min: -1, max: 1, step: 0.01, desc: "Green-Magenta axis. 0 = neutral." },

    enable_tone: { type: "toggle", section: "tone", label: "Enable", desc: "Linear-light global tone mapping." },
    exposure: { type: "slider", section: "tone", label: "Exposure", min: -1, max: 1, step: 0.01, desc: "Exposure in EV. iPhone meters slightly bright." },
    contrast: { type: "slider", section: "tone", label: "Contrast", min: -1, max: 1, step: 0.01, desc: "Midtone contrast around the 0.18 photographic pivot." },
    shadows: { type: "slider", section: "tone", label: "Shadows", min: 0, max: 1, step: 0.01, desc: "Luminance-masked shadow lift. iPhone never crushes blacks." },
    highlights: { type: "slider", section: "tone", label: "Highlights", min: 0, max: 1, step: 0.01, desc: "Reinhard soft-knee rolloff — highlights compress smoothly, never clip." },

    enable_smart_hdr: { type: "toggle", section: "hdr", label: "Enable", desc: "Local tone mapping in log-luminance (Smart HDR 5 style fusion look)." },
    hdr_strength: { type: "slider", section: "hdr", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Local dynamic range compression — shadows up, highlights down, detail untouched." },

    enable_color: { type: "toggle", section: "color", label: "Enable", desc: "Perceptual color rendering in Oklab space." },
    vibrance: { type: "slider", section: "color", label: "Vibrance", min: 0, max: 1, step: 0.01, desc: "Smart saturation: boosts muted colors more than saturated ones. Hue-preserving." },
    skin_protection: { type: "slider", section: "color", label: "Skin Protection", min: 0, max: 1, step: 0.01, desc: "Shields skin tones from vibrance and caps skin chroma — no orange faces." },
    shadow_tint: { type: "slider", section: "color", label: "Shadow Tint", min: 0, max: 1, step: 0.01, desc: "Subtle cool/blue tint in shadows — the iPhone blue-black signature." },
    highlight_warmth: { type: "slider", section: "color", label: "Highlight Warmth", min: 0, max: 1, step: 0.01, desc: "Golden warmth in bright areas, complements the cool shadows." },

    enable_detail: { type: "toggle", section: "detail", label: "Enable", desc: "Two-scale luminance detail with halo suppression." },
    texture: { type: "slider", section: "detail", label: "Texture", min: 0, max: 1, step: 0.01, desc: "Fine-scale detail (~1px): pores, fabric, hair." },
    clarity: { type: "slider", section: "detail", label: "Clarity", min: 0, max: 1, step: 0.01, desc: "Mid-scale local punch. Keep low for a natural look." },

    enable_optics: { type: "toggle", section: "optics", label: "Enable", desc: "Lens vignette + sensor grain." },
    grain: { type: "slider", section: "optics", label: "Grain", min: 0, max: 1, step: 0.01, desc: "Photon-weighted sensor noise, stronger in shadows." },
    vignette: { type: "slider", section: "optics", label: "Vignette", min: 0, max: 1, step: 0.01, desc: "Natural illumination falloff applied in linear light." },
};

/* ── CSS injection ───────────────────────────────────────────────────── */
function injectCSS() {
    if (document.getElementById("cfr-styles")) return;
    const style = document.createElement("style");
    style.id = "cfr-styles";
    style.textContent = `
.cfr-root {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: #0d0d08;
    border-radius: 8px;
    color: #d0d0c0;
    user-select: none;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    overflow-y: auto;
    overflow-x: hidden;
    scrollbar-width: thin;
    scrollbar-color: #333322 transparent;
}
.cfr-root::-webkit-scrollbar { width: 6px; }
.cfr-root::-webkit-scrollbar-thumb { background: #333322; border-radius: 3px; }
.cfr-inner { padding: 12px; box-sizing: border-box; }
.cfr-header {
    text-align: center;
    padding: 4px 0 12px;
    border-bottom: 1px solid rgba(255, 215, 0, 0.15);
    margin-bottom: 12px;
}
.cfr-title {
    font-size: 16px; font-weight: 800; letter-spacing: 2px;
    text-transform: uppercase;
    background: linear-gradient(135deg, #FFD700, #b89b00);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    background-clip: text; margin: 0;
}
.cfr-subtitle {
    font-size: 9px; color: #887; letter-spacing: 2px;
    text-transform: uppercase; margin-top: 4px; font-weight: 600;
}
.cfr-info {
    background: rgba(255, 215, 0, 0.04);
    border: 1px solid rgba(255, 215, 0, 0.1);
    border-radius: 8px; padding: 10px 12px;
    margin-bottom: 12px; font-size: 10px; line-height: 1.4;
}
.cfr-info-badge {
    display: inline-block; font-size: 8px; font-weight: 800;
    letter-spacing: 1.5px; padding: 3px 6px; border-radius: 4px;
    background: rgba(255, 215, 0, 0.15); color: #FFD700; margin-bottom: 6px;
}
.cfr-info-desc { color: #bbb; margin: 4px 0; }
.cfr-info-tip { color: #887; font-size: 9px; font-style: italic; margin-top: 6px; }

.cfr-section {
    display: flex; align-items: center; gap: 8px;
    margin: 16px 0 8px; font-size: 10px; font-weight: 700;
    letter-spacing: 1.5px; text-transform: uppercase; color: #FFD700;
}
.cfr-section::after {
    content: ""; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(255,215,0,0.2), transparent);
}
.cfr-row {
    display: flex; align-items: center; gap: 10px; margin: 6px 0;
    height: 24px; transition: opacity 0.2s, max-height 0.2s;
}
.cfr-row.hidden { opacity: 0; max-height: 0; margin: 0; pointer-events: none; overflow: hidden; }

.cfr-label {
    min-width: 100px; font-size: 11px; color: #aaa;
    text-align: right; cursor: help; font-weight: 500;
}
.cfr-label:hover { color: #FFD700; }

.cfr-slider {
    -webkit-appearance: none; appearance: none;
    flex: 1; height: 6px; border-radius: 3px;
    background: linear-gradient(90deg, #1f1f14, #333322);
    outline: none; cursor: pointer;
    box-shadow: inset 0 1px 2px rgba(0,0,0,0.5);
}
.cfr-slider:hover { background: linear-gradient(90deg, #1f1f14, #444422); }
.cfr-slider::-webkit-slider-thumb {
    -webkit-appearance: none; width: 14px; height: 14px;
    border-radius: 50%;
    background: radial-gradient(circle, #fff 10%, #FFD700 80%);
    border: 1px solid #b89b00; cursor: grab;
    box-shadow: 0 0 6px rgba(255, 215, 0, 0.4);
    margin-top: -4px; transition: transform 0.1s;
}
.cfr-slider::-webkit-slider-thumb:hover {
    transform: scale(1.2); box-shadow: 0 0 10px rgba(255, 215, 0, 0.6);
}
.cfr-slider-val {
    min-width: 40px; text-align: right; font-size: 11px;
    font-family: 'Consolas','Monaco',monospace;
    color: #FFD700; font-weight: 700;
}

.cfr-tooltip { position: relative; }
.cfr-tooltip::after {
    content: attr(data-tip);
    position: absolute; bottom: 125%; left: 0%;
    background: #1a1a14; color: #ccc;
    border: 1px solid rgba(255,215,0,0.3);
    padding: 6px 10px; border-radius: 6px;
    font-size: 10px; width: 220px;
    white-space: normal; pointer-events: none; text-align: left;
    opacity: 0; transition: opacity 0.2s; z-index: 999; line-height: 1.4;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5); font-weight: normal; font-family: sans-serif;
}
.cfr-tooltip:hover::after { opacity: 1; }

.cfr-switch { display: flex; align-items: center; gap: 8px; cursor: pointer; flex: 1; }
.cfr-switch-text { font-size: 10px; font-weight: 700; color: #666; width: 26px; text-align: right; letter-spacing: 0.5px; }
.cfr-switch input { display: none; }
.cfr-switch-track { width: 32px; height: 16px; background: #222; border-radius: 8px; position: relative; transition: 0.2s; border: 1px solid #333; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5); }
.cfr-switch-thumb { width: 12px; height: 12px; background: #777; border-radius: 50%; position: absolute; top: 1px; left: 2px; transition: 0.2s; }
.cfr-switch input:checked + .cfr-switch-text { color: #FFD700; }
.cfr-switch input:checked ~ .cfr-switch-track { background: rgba(255,215,0,0.15); border-color: rgba(255,215,0,0.4); }
.cfr-switch input:checked ~ .cfr-switch-track .cfr-switch-thumb { background: #FFD700; transform: translateX(14px); box-shadow: 0 0 8px rgba(255,215,0,0.5); }

.cfr-input { flex: 1; background: #1a1a14; border: 1px solid rgba(255,215,0,0.2); color: #FFD700; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-family: inherit; font-weight: 600; outline: none; }
.cfr-input:focus { border-color: #FFD700; }
`;
    document.head.appendChild(style);
}

/* ── Build DOM ───────────────────────────────────────────────────────── */
function buildUI() {
    const el = document.createElement("div");
    el.className = "cfr-root";
    const inner = document.createElement("div");
    inner.className = "cfr-inner";
    el.appendChild(inner);

    // Header & Description
    let html = `
        <div class="cfr-header">
            <div class="cfr-title">Camera Forensic Realism</div>
            <div class="cfr-subtitle">iPhone 17 • Photonic Engine • Photographic Styles</div>
        </div>
        <div class="cfr-info">
            <span class="cfr-info-badge">★ iPHONE 17 ISP PIPELINE</span>
            <div class="cfr-info-desc">Honest color science: linear-light white balance & tone, Smart HDR local mapping, Oklab vibrance with real skin protection, halo-suppressed detail, photon-weighted grain.</div>
            <div class="cfr-info-tip">💡 Pick a Photographic Style, then fine-tune. Place after detailers, before SaveImage.</div>
        </div>
    `;

    // Generate Sections & Controls
    Object.entries(SECTIONS).forEach(([secId, sec]) => {
        html += `<div class="cfr-section" id="sec_${secId}">${sec.icon} ${sec.label}</div>`;
        html += `<div id="wrap_${secId}">`;

        Object.entries(WIDGET_META).forEach(([wName, w]) => {
            if (w.section !== secId) return;

            html += `<div class="cfr-row" id="row_${wName}">
                <span class="cfr-label cfr-tooltip" data-tip="${w.desc}">${w.label}</span>`;

            if (w.type === "slider") {
                html += `
                    <input type="range" class="cfr-slider" id="inp_${wName}" min="${w.min}" max="${w.max}" step="${w.step}">
                    <span class="cfr-slider-val" id="val_${wName}"></span>`;
            } else if (w.type === "toggle") {
                html += `
                    <label class="cfr-switch">
                        <input type="checkbox" id="inp_${wName}">
                        <span class="cfr-switch-text" id="val_${wName}">OFF</span>
                        <div class="cfr-switch-track"><div class="cfr-switch-thumb"></div></div>
                    </label>`;
            } else if (w.type === "combo") {
                html += `<select class="cfr-input" id="inp_${wName}"></select>`;
            } else if (w.type === "number") {
                html += `<input type="number" class="cfr-input" id="inp_${wName}">`;
            }
            html += `</div>`;
        });
        html += `</div>`;
    });

    inner.innerHTML = html;
    return el;
}

function getWidget(node, name) {
    return node.widgets?.find(w => w.name === name);
}

function hideDefaultWidget(w) {
    if (!w) return;
    w.hidden = true; w.type = "hidden"; w.computeSize = () => [0, -4];
    w.draw = function () { }; w.mouse = function () { return false; };
}

function updateSectionVisibility(el, node) {
    // Hide a section's controls when its enable toggle is off
    Object.entries(SECTIONS).forEach(([secId, sec]) => {
        if (!sec.toggle) return;

        const toggleW = getWidget(node, sec.toggle);
        if (!toggleW) return;

        const isEnabled = !!toggleW.value;

        Object.entries(WIDGET_META).forEach(([name, meta]) => {
            if (meta.section === secId && meta.type !== "toggle") {
                const row = el.querySelector(`#row_${name}`);
                if (row) row.classList.toggle("hidden", !isEnabled);
            }
        });
    });
}

/* ── Extension ───────────────────────────────────────────────────────── */
app.registerExtension({
    name: "CameraForensicRealism.PremiumUI",

    nodeCreated(node) {
        if (node.comfyClass !== NODE_NAME) return;
        injectCSS();

        const paramNames = Object.keys(WIDGET_META);

        // Hide all default widgets
        for (const name of paramNames) hideDefaultWidget(getWidget(node, name));

        /* The frontend's DOM-widget layout (DOMWidgetImpl.computeLayoutSize
           + _arrangeWidgets) sizes the widget area from getMinHeight /
           getMaxHeight, and re-runs on EVERY canvas redraw — including
           clicks. Report the panel's real measured content height as both
           min and max: the layout always allocates exactly enough space and
           can never stretch the panel into leftover node body space. */
        const el = buildUI();
        const inner = el.querySelector(".cfr-inner");
        let contentH = 600;
        const widgetOptions = {
            serialize: false,
            getMinHeight: () => contentH,
            getMaxHeight: () => contentH,
        };
        let domWidget = node.addDOMWidget(
            "cfr_premium_ui", "customwidget", el, widgetOptions);

        /* On workflow reload, the frontend clears its DOM-widget store
           while nodes are being rebuilt; depending on timing our early
           registration can be wiped, leaving the panel orphaned — visible
           detached or gone, never tracking the node. Re-adding the widget
           re-registers it and the Vue overlay adopts the panel again. */
        function remount() {
            if (document.contains(el)) return;
            const idx = node.widgets.indexOf(domWidget);
            if (idx >= 0) node.widgets.splice(idx, 1);
            try { domWidget.onRemove?.(); } catch (e) { /* stale store entry */ }
            domWidget = node.addDOMWidget(
                "cfr_premium_ui", "customwidget", el, widgetOptions);
            node.setDirtyCanvas?.(true, true);
        }

        function measure() {
            if (inner.offsetHeight) contentH = inner.offsetHeight + 2;
        }

        /* Track reflow (e.g. text wrapping after a width change) so the
           layout's min/max height stays accurate. Passive: never resizes
           the node itself. */
        new ResizeObserver(() => measure()).observe(inner);

        /* Resize the node to its authoritative minimum: computeSize()
           already includes our getMinHeight via computeLayoutSize, so this
           both grows undersized and shrinks oversized nodes (the frontend
           itself only ever auto-grows). Width: keep the user's width but
           clamp out garbage serialized by older versions of this node. */
        function fitHeight() {
            requestAnimationFrame(() => {
                measure();
                if (!inner.offsetHeight) return;
                const fit = node.computeSize();
                const width = Math.min(
                    Math.max(node.size[0], NODE_MIN_WIDTH), 800);
                node.setSize([width, fit[1]]);
                node.setDirtyCanvas?.(true, true);
            });
        }

        /* The panel is mounted into the canvas overlay lazily (first time
           the widget becomes visible), so right after configure it may not
           be measurable yet — retry until it is. If it stays unmounted,
           the store registration was lost on reload: remount it. */
        let fitTries = 0;
        function fitWhenReady() {
            measure();
            if (!inner.offsetHeight) {
                if (fitTries === 6 || fitTries === 14) remount();
                if (fitTries++ < 25) {
                    setTimeout(fitWhenReady, 150);
                    return;
                }
                return;
            }
            fitHeight();
        }

        node.color = "#1A1A00"; node.bgcolor = "#0A0A0A";

        // Bind DOM elements to LiteGraph Widgets
        Object.entries(WIDGET_META).forEach(([name, meta]) => {
            const domInp = el.querySelector(`#inp_${name}`);
            const domVal = el.querySelector(`#val_${name}`);
            const lgW = getWidget(node, name);
            if (!domInp || !lgW) return;

            if (meta.type === "slider") {
                domInp.addEventListener("input", () => {
                    lgW.value = parseFloat(domInp.value);
                    if (lgW.callback) lgW.callback(lgW.value);
                    if (domVal) domVal.textContent = Number(lgW.value).toFixed(2);
                });
            } else if (meta.type === "toggle") {
                domInp.addEventListener("change", (e) => {
                    lgW.value = e.target.checked;
                    if (lgW.callback) lgW.callback(lgW.value);
                    if (domVal) domVal.textContent = lgW.value ? "ON" : "OFF";

                    updateSectionVisibility(el, node);
                    fitHeight();
                });
            } else if (meta.type === "combo") {
                (lgW.options?.values || []).forEach(opt => {
                    const o = document.createElement("option"); o.value = opt; o.innerText = opt;
                    domInp.appendChild(o);
                });
                domInp.addEventListener("change", (e) => {
                    lgW.value = e.target.value;
                    if (lgW.callback) lgW.callback(lgW.value);
                });
            } else if (meta.type === "number") {
                domInp.addEventListener("input", (e) => {
                    lgW.value = parseFloat(e.target.value);
                    if (lgW.callback) lgW.callback(lgW.value);
                });
            }
        });

        function syncFromWidgets() {
            Object.entries(WIDGET_META).forEach(([name, meta]) => {
                const domInp = el.querySelector(`#inp_${name}`);
                const domVal = el.querySelector(`#val_${name}`);
                const lgW = getWidget(node, name);
                if (!domInp || !lgW) return;

                if (meta.type === "slider") {
                    domInp.value = lgW.value;
                    if (domVal) domVal.textContent = Number(lgW.value).toFixed(2);
                } else if (meta.type === "toggle") {
                    domInp.checked = !!lgW.value;
                    if (domVal) domVal.textContent = lgW.value ? "ON" : "OFF";
                } else {
                    domInp.value = lgW.value;
                }
            });
            updateSectionVisibility(el, node);
        }

        /* Repair values from workflows saved with the old node version:
           widget values restore by position, so removed v3 params can land
           in today's params with the wrong type or out-of-range values. */
        function sanitize() {
            Object.entries(WIDGET_META).forEach(([name, meta]) => {
                const lgW = getWidget(node, name);
                if (!lgW) return;
                if (meta.type === "slider") {
                    let v = Number(lgW.value);
                    if (!Number.isFinite(v)) v = meta.min;
                    v = Math.min(meta.max, Math.max(meta.min, v));
                    if (v !== lgW.value) { lgW.value = v; lgW.callback?.(v); }
                } else if (meta.type === "toggle") {
                    if (typeof lgW.value !== "boolean") {
                        lgW.value = !!lgW.value;
                        lgW.callback?.(lgW.value);
                    }
                } else if (meta.type === "combo") {
                    const values = lgW.options?.values || [];
                    if (values.length && !values.includes(lgW.value)) {
                        lgW.value = values[0];
                        lgW.callback?.(lgW.value);
                    }
                }
            });
        }

        const origConfigure = node.onConfigure;
        node.onConfigure = function (info) {
            origConfigure?.apply(this, arguments);
            setTimeout(() => {
                sanitize();
                syncFromWidgets();
                fitTries = 0;
                fitWhenReady();
            }, 80);
        };

        const origBG = node.onDrawBackground;
        node.onDrawBackground = function (ctx) {
            if (origBG) origBG.apply(this, arguments);
            if (this.flags?.collapsed) return;
            ctx.save();
            ctx.fillStyle = "#1A1A00"; ctx.fillRect(0, -NODE_TITLE_HEIGHT, this.size[0], NODE_TITLE_HEIGHT);
            ctx.restore();
        };

        setTimeout(() => {
            sanitize();
            syncFromWidgets();
            fitWhenReady();
        }, 150);
    },
});
