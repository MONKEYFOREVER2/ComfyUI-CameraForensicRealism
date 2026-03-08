import { app } from "../../scripts/app.js";

/**
 * 📸 Camera Forensic Realism Engine — Premium UI Dashboard
 * ==========================================================
 * Gold/Black themed DOM widget replacing ALL default drawing.
 * Includes tooltips, styled sliders, toggles, and dynamic layout
 * mimicking the Advanced Image Denoiser style.
 */

const NODE_NAME = "CameraForensicRealismEngine";
const NODE_MIN_WIDTH = 420;
const NODE_TITLE_HEIGHT = 40;

const SECTIONS = {
    master: { icon: "⚡", label: "Master Settings" },
    tone: { icon: "🌓", label: "Tone Curve" },
    color: { icon: "🎨", label: "Display P3 Color" },
    hdr: { icon: "✨", label: "Smart HDR" },
    skin: { icon: "👩🏽‍🦱", label: "Real Tone" },
    fusion: { icon: "🧠", label: "Deep Fusion" },
    wb: { icon: "☀️", label: "White Balance" },
    grade: { icon: "🔵", label: "Color Grading" },
    sharp: { icon: "🔪", label: "ISP Sharpening" },
    sensor: { icon: "📷", label: "Sensor FX" },
};

const WIDGET_META = {
    master_strength: { type: "slider", section: "master", label: "Master Strength", min: 0, max: 2, step: 0.01, desc: "Global intensity of all forensic realism effects." },
    seed: { type: "number", section: "master", label: "Seed", desc: "Random seed for noise generation." },
    control_after_generate: { type: "combo", section: "master", label: "Seed Mode", desc: "Change seed behavior after generation." },

    enable_tone_mapping: { type: "toggle", section: "tone", label: "Enable", desc: "Apply Apple-style tone mapping curve." },
    tone_strength: { type: "slider", section: "tone", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Overall strength of the tone curve effect." },
    highlight_rolloff: { type: "slider", section: "tone", label: "Highlight Rolloff", min: 0, max: 1, step: 0.01, desc: "Smooth compression of bright highlights to prevent clipping." },
    shadow_lift: { type: "slider", section: "tone", label: "Shadow Lift", min: 0, max: 1, step: 0.01, desc: "Raises shadow black point for a slightly softer, photographic look." },
    contrast: { type: "slider", section: "tone", label: "Contrast", min: 0, max: 1, step: 0.01, desc: "Midtone contrast intensity (S-curve steepness)." },

    enable_p3_color: { type: "toggle", section: "color", label: "Enable", desc: "Transform gamut to Display P3 space (richer reds/greens)." },
    color_strength: { type: "slider", section: "color", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Intensity of the P3 color transformation." },
    color_saturation: { type: "slider", section: "color", label: "Saturation", min: 0, max: 1, step: 0.01, desc: "Overall image saturation boost." },
    color_warmth: { type: "slider", section: "color", label: "Warmth", min: 0, max: 1, step: 0.01, desc: "Apple's signature slight warmth bias in reds/yellows." },

    enable_local_tone: { type: "toggle", section: "hdr", label: "Enable", desc: "Smart HDR local contrast emulation." },
    local_tone_strength: { type: "slider", section: "hdr", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Intensity of local contrast enhancements." },
    detail_boost: { type: "slider", section: "hdr", label: "Detail Boost", min: 0, max: 1, step: 0.01, desc: "Micro-contrast extraction in mid-frequency details." },

    enable_skin_rendering: { type: "toggle", section: "skin", label: "Enable", desc: "Real Tone skin color protection and rendering." },
    skin_strength: { type: "slider", section: "skin", label: "Strength", min: 0, max: 1, step: 0.01, desc: "How aggressively skin tones are isolated and processed." },
    skin_warmth: { type: "slider", section: "skin", label: "Skin Warmth", min: 0, max: 1, step: 0.01, desc: "Reduces orange bias and adds natural rosy warmth to skin." },

    enable_deep_fusion: { type: "toggle", section: "fusion", label: "Enable", desc: "Isolate and crunch high-frequency textures (fabric, pores) without halos." },
    fusion_strength: { type: "slider", section: "fusion", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Texture amplification strength (the iPhone computational crunch)." },
    fusion_texture_freq: { type: "slider", section: "fusion", label: "Texture Freq", min: 0, max: 1, step: 0.01, desc: "Determines which texture thicknesses are crunched." },

    enable_white_balance: { type: "toggle", section: "wb", label: "Enable", desc: "Apply signature iPhone warm auto-white-balance bias." },
    wb_strength: { type: "slider", section: "wb", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Overall intensity of the AWB correction." },
    wb_temperature: { type: "slider", section: "wb", label: "Temperature", min: -1, max: 1, step: 0.01, desc: "Blue-Yellow axis balance." },
    wb_tint: { type: "slider", section: "wb", label: "Tint", min: -1, max: 1, step: 0.01, desc: "Green-Magenta axis balance." },

    enable_color_grading: { type: "toggle", section: "grade", label: "Enable", desc: "Cinematic color grading (blue shadows, warm highlights)." },
    blue_shadows: { type: "slider", section: "grade", label: "Blue Shadows", min: 0, max: 1, step: 0.01, desc: "Injects deep inky blue tint into the darkest shadows." },
    warm_highlights: { type: "slider", section: "grade", label: "Warm Highlights", min: 0, max: 1, step: 0.01, desc: "Pushes bright highlights towards a soft golden hue." },

    enable_sharpening: { type: "toggle", section: "sharp", label: "Enable", desc: "ISP-style luminance unsharp mask computation." },
    sharpen_strength: { type: "slider", section: "sharp", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Intensity of the sharpening halo effect." },

    enable_sensor: { type: "toggle", section: "sensor", label: "Enable", desc: "Physical sensor imperfections (noise, vignette)." },
    sensor_strength: { type: "slider", section: "sensor", label: "Strength", min: 0, max: 1, step: 0.01, desc: "Overall intensity of sensor effects combined." },
    sensor_noise: { type: "slider", section: "sensor", label: "Luma Noise", min: 0, max: 1, step: 0.01, desc: "Amount of fine digital grain added to midtones/shadows." },
    sensor_vignette: { type: "slider", section: "sensor", label: "Vignette", min: 0, max: 1, step: 0.01, desc: "f/1.78 lens shading light falloff at the corners." },
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
    padding: 12px;
    color: #d0d0c0;
    user-select: none;
    width: 100%;
    box-sizing: border-box;
    overflow: hidden;
}
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

    // Header & Description
    let html = `
        <div class="cfr-header">
            <div class="cfr-title">Camera Forensic Realism</div>
            <div class="cfr-subtitle">iPhone 15 Pro • ISP Emulation • 9 Stages</div>
        </div>
        <div class="cfr-info">
            <span class="cfr-info-badge">★ iPHONE ISP PIPELINE</span>
            <div class="cfr-info-desc">Emulates Apple’s Image Signal Processor color science. Transforms AI images to match iPhone photography with accurate tone mapping, P3 color, and blue-black shadows.</div>
            <div class="cfr-info-tip">💡 Place after detailers, before SaveImage.</div>
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

    el.innerHTML = html;
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
    // Hide controls if section is toggled off
    Object.keys(SECTIONS).forEach(secId => {
        if (secId === "master") return;

        const toggleName = "enable_" + (secId === "hdr" ? "local_tone" : secId === "skin" ? "skin_rendering" : secId === "fusion" ? "deep_fusion" : secId === "sharp" ? "sharpening" : secId === "tone" ? "tone_mapping" : secId === "grade" ? "color_grading" : secId === "color" ? "p3_color" : secId === "wb" ? "white_balance" : secId);

        const toggleW = getWidget(node, toggleName);
        if (!toggleW) return;

        const isEnabled = !!toggleW.value;

        // Find all rows in this section except the toggle itself
        Object.entries(WIDGET_META).forEach(([name, meta]) => {
            if (meta.section === secId && meta.type !== "toggle") {
                const row = el.querySelector(`#row_${name}`);
                if (row) row.classList.toggle("hidden", !isEnabled);
            }
        });
    });
}

function calcNodeSize(el, node) {
    const visibleRows = el.querySelectorAll(".cfr-row:not(.hidden)").length;
    const numSections = Object.keys(SECTIONS).length;

    const headerH = 120; // Title bar + info box
    const rowH = 30;     // height + margins
    const secH = 36;     // section headers

    const totalH = NODE_TITLE_HEIGHT + headerH + (numSections * secH) + (visibleRows * rowH);
    const currentW = Math.max(node.size?.[0] || 0, NODE_MIN_WIDTH);
    return [currentW, totalH];
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

        // Build native DOM
        const el = buildUI();
        node.addDOMWidget("cfr_premium_ui", "customwidget", el, { serialize: false });

        if (!node.size || node.size[0] < NODE_MIN_WIDTH) node.size = [NODE_MIN_WIDTH, 600];

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
                    requestAnimationFrame(() => {
                        node.setSize(calcNodeSize(el, node));
                        node.setDirtyCanvas(true, true);
                    });
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

        const origConfigure = node.onConfigure;
        node.onConfigure = function (info) {
            origConfigure?.apply(this, arguments);
            setTimeout(() => {
                syncFromWidgets();
                node.setSize(calcNodeSize(el, node));
                node.setDirtyCanvas?.(true, true);
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
            syncFromWidgets();
            node.setSize(calcNodeSize(el, node));
            node.setDirtyCanvas?.(true, true);
        }, 150);
    },
});
