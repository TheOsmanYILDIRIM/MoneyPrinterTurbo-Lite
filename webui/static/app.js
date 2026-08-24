/* MoneyPrinter Lite Studio - app.js */
"use strict";

let allVoicesList = [];
let pollTimer = null;
let pollDelay = 2500;

/* ---------------- yardımcılar ---------------- */

function el(id) { return document.getElementById(id); }

function clearNode(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
}

function make(tag, className, textContent) {
    const n = document.createElement(tag);
    if (className) n.className = className;
    if (textContent !== undefined) n.textContent = textContent;
    return n;
}

async function api(path, options) {
    let res;
    try {
        res = await fetch(path, options);
    } catch (e) {
        setServerStatus(false);
        throw new Error("Sunucuya ulaşılamıyor");
    }
    setServerStatus(true);
    let data = {};
    try { data = await res.json(); } catch (e) { /* boş gövde */ }
    if (!res.ok) throw new Error(data.error || ("HTTP " + res.status));
    return data;
}

function setServerStatus(ok) {
    const s = el("server-status");
    s.textContent = ok ? "● Yerel Sunucu" : "○ Bağlantı Yok";
    s.className = ok ? "server-ok" : "server-off";
}

/* ---------------- tercihler ---------------- */
/* Üretim ayarları artık sunucuda (Ayarlar -> Üretim Tercihleri) tutulur. */

function savePreferences() { /* global ayarlar sunucuda saklanır */ }
function restorePreferences() { updateCharCount(); }

/* ---------------- sesler ---------------- */

function flagFor(locale) {
    if (!locale) return "🌐";
    if (locale.startsWith("tr")) return "🇹🇷";
    if (locale.startsWith("en")) return "🇺🇸";
    if (locale.startsWith("de")) return "🇩🇪";
    if (locale.startsWith("fr")) return "🇫🇷";
    if (locale.startsWith("es")) return "🇪🇸";
    if (locale.startsWith("ar")) return "🇸🇦";
    return "🌐";
}

function renderVoiceList(voices) {
    const container = el("voice-list-container");
    const current = el("voice").value;
    clearNode(container);

    const sorted = [...voices].sort((a, b) => {
        const at = (a.locale || "").startsWith("tr") ? 0 : 1;
        const bt = (b.locale || "").startsWith("tr") ? 0 : 1;
        return at - bt || String(a.id).localeCompare(String(b.id));
    });

    // Performans için en fazla 150 satır çiz; arama zaten filtreliyor.
    sorted.slice(0, 150).forEach(v => {
        const row = make("div", "voice-item" + (v.id === current ? " selected" : ""));
        const left = make("span", null, null);
        left.appendChild(make("span", null, flagFor(v.locale) + " " + v.id));
        row.appendChild(left);
        row.appendChild(make("span", "v-meta", (v.gender || "") + " " + (v.name ? "· " + v.name : "")));
        row.addEventListener("click", () => selectVoice(v.id));
        container.appendChild(row);
    });

    if (!sorted.length) {
        container.appendChild(make("div", "empty-state", "Ses listesi boş. (storage/all_voices.json yok)"));
    }
}

function filterVoiceList() {
    const q = el("voice-search").value.toLowerCase().trim();
    if (!q) { renderVoiceList(allVoicesList); return; }
    renderVoiceList(allVoicesList.filter(v =>
        String(v.id || "").toLowerCase().includes(q) ||
        String(v.name || "").toLowerCase().includes(q) ||
        String(v.locale || "").toLowerCase().includes(q) ||
        String(v.gender || "").toLowerCase().includes(q)
    ));
}

function selectVoice(voiceId) {
    el("voice").value = voiceId;
    updateSelectedVoiceDisplay(voiceId, "");

    filterVoiceList();
}

async function playVoicePreview() {
    const btn = el("btn-voice-preview");
    const voice = el("voice").value;
    if (!voice) { alert("Önce bir ses seçin."); return; }
    btn.disabled = true;
    btn.textContent = "⏳ Hazırlanıyor...";
    try {
        await api(`/api/voice_preview?voice=${encodeURIComponent(voice)}`);
        new Audio(`/api/voice_preview?voice=${encodeURIComponent(voice)}`).play();
        btn.textContent = "🔊 Örnek Dinle";
    } catch (e) {
        alert("Önizleme hatası: " + e.message);
        btn.textContent = "🔊 Örnek Dinle";
    } finally {
        btn.disabled = false;
    }
}

function updateSelectedVoiceDisplay(voiceId, name) {
    el("selected-voice-display").textContent = voiceId + (name ? ` (${name})` : "");
}

let selectedBatchVoices = [];

function toggleBatchVoiceMode() {
    const isPool = el("batch_vmode_pool") && el("batch_vmode_pool").checked;
    const box = el("batch-voice-pool-box");
    if (box) box.classList.toggle("hidden", !isPool);
    if (isPool) {
        if (selectedBatchVoices.length === 0) {
            selectTurkishBatchVoices();
        } else {
            renderBatchVoiceList(allVoicesList);
            updateBatchVoiceChips();
        }
    }
}

function renderBatchVoiceList(voices) {
    const container = el("batch-voice-list-container");
    if (!container) return;
    clearNode(container);

    const sorted = [...(voices || allVoicesList)].sort((a, b) => {
        const at = (a.locale || "").startsWith("tr") ? 0 : 1;
        const bt = (b.locale || "").startsWith("tr") ? 0 : 1;
        return at - bt || String(a.id).localeCompare(String(b.id));
    });

    sorted.slice(0, 150).forEach(v => {
        const isSel = selectedBatchVoices.includes(v.id);
        const row = make("div", "voice-item-multi" + (isSel ? " selected" : ""));
        const left = make("span", null, null);
        left.appendChild(make("span", null, (isSel ? "☑️ " : "⬜ ") + flagFor(v.locale) + " " + v.id));
        row.appendChild(left);
        row.appendChild(make("span", "v-meta", (v.gender || "") + " " + (v.name ? "· " + v.name : "")));
        row.addEventListener("click", () => toggleBatchVoiceSelection(v.id));
        container.appendChild(row);
    });

    if (!sorted.length) {
        container.appendChild(make("div", "empty-state", "Ses bulunamadı."));
    }
}

function filterBatchVoiceList() {
    const q = (el("batch-voice-search") ? el("batch-voice-search").value : "").toLowerCase().trim();
    if (!q) { renderBatchVoiceList(allVoicesList); return; }
    renderBatchVoiceList(allVoicesList.filter(v =>
        String(v.id || "").toLowerCase().includes(q) ||
        String(v.name || "").toLowerCase().includes(q) ||
        String(v.locale || "").toLowerCase().includes(q) ||
        String(v.gender || "").toLowerCase().includes(q)
    ));
}

function toggleBatchVoiceSelection(voiceId) {
    const idx = selectedBatchVoices.indexOf(voiceId);
    if (idx >= 0) {
        selectedBatchVoices.splice(idx, 1);
    } else {
        selectedBatchVoices.push(voiceId);
    }
    updateBatchVoiceChips();
    filterBatchVoiceList();
}

function updateBatchVoiceChips() {
    const countEl = el("batch-selected-count");
    if (countEl) countEl.textContent = selectedBatchVoices.length;
    const chipsEl = el("batch-voice-chips");
    if (!chipsEl) return;
    clearNode(chipsEl);

    if (selectedBatchVoices.length === 0) {
        chipsEl.appendChild(make("span", "small muted", "Henüz ses seçilmedi. Aşağıdaki listeden sesleri seçin."));
        return;
    }

    selectedBatchVoices.forEach(vid => {
        const vObj = allVoicesList.find(x => x.id === vid);
        const flag = flagFor(vObj ? vObj.locale : "");
        const chip = make("span", "batch-voice-chip");
        chip.appendChild(make("span", null, `${flag} ${vid}`));
        const del = make("span", "chip-del", "✕");
        del.title = "Kaldır";
        del.addEventListener("click", (e) => {
            e.stopPropagation();
            toggleBatchVoiceSelection(vid);
        });
        chip.appendChild(del);
        chipsEl.appendChild(chip);
    });
}

function selectTurkishBatchVoices() {
    const trVoices = allVoicesList.filter(v => (v.locale || "").startsWith("tr") || String(v.id).startsWith("tr-"));
    trVoices.forEach(v => {
        if (!selectedBatchVoices.includes(v.id)) selectedBatchVoices.push(v.id);
    });
    updateBatchVoiceChips();
    filterBatchVoiceList();
}

function clearBatchVoices() {
    selectedBatchVoices = [];
    updateBatchVoiceChips();
    filterBatchVoiceList();
}

async function loadVoices() {
    try {
        const data = await api("/api/voices");
        allVoicesList = data.voices || [];
        filterVoiceList();
        filterBatchVoiceList();
    } catch (e) { console.error(e); }
}

/* ---------------- tekli üretim ---------------- */

function updateCharCount() {
    const t = el("script").value;
    const words = t.trim() ? t.trim().split(/\s+/).length : 0;
    el("char-count").textContent = `Karakter: ${t.length} | Kelime: ${words}`;
}

function toggleBgInputs() {
    const box = el("custom-file-box");
    if (box) box.classList.toggle("hidden", el("bg_style").value !== "custom_file");
}

function toggleBgmInputs() {
    const box = el("bgm-file-box");
    if (box) box.classList.toggle("hidden", el("bgm_source").value !== "file");
}

function collectCommonParams(scope) {
    const p = {
        subject: el("subject").value.trim(),
        script: el("script").value.trim(),
        pexels_query: el("pexels_query") ? el("pexels_query").value.trim() : "",
        voice: el("voice").value,
        voice_rate: el("voice_rate").value,
        voice_volume: el("voice_volume").value,
        aspect: el("aspect").value,
        resolution: el("resolution") ? el("resolution").value : "720p",
        bg_style: el("bg_style").value,
        sub_color: el("sub_color").value,
        sub_pos: el("sub_pos").value,
        sub_size: el("sub_size").value,
        sub_box: el("sub_box").value,
        sub_bold: el("sub_bold_chk") ? (el("sub_bold_chk").checked ? "true" : "false") : "true",
        sub_font: el("sub_font") ? el("sub_font").value : "Roboto",
        outline_color: el("outline_color") ? el("outline_color").value : "#000000",
        subtitle_enabled: el("subtitle_enabled_chk").checked ? "true" : "false",
        bgm_source: el("bgm_source").value,
        bgm_volume: el("bgm_volume").value,
        transition: el("prod_transition") ? el("prod_transition").value : "none",
        transition_dur: el("prod_transition_dur") ? el("prod_transition_dur").value : "0.5"
    };
    if (scope === "batch") p.batch_text = el("batch_text").value;
    return p;
}

async function submitVideo() {
    const params = collectCommonParams("single");
    const bgFile = el("bg_file").files[0];
    const audioFile = el("audio_file").files[0];
    const bgmFile = el("bgm_file").files[0];

    if (!params.script && !audioFile) {
        alert("Lütfen bir ders scripti girin veya hazır ses dosyası seçin.");
        return;
    }


    const btn = el("btn-submit");
    btn.disabled = true;

    const fd = new FormData();
    Object.entries(params).forEach(([k, v]) => fd.append(k, v));
    if (bgFile) fd.append("bg_file", bgFile);
    if (audioFile) fd.append("audio_file", audioFile);
    if (bgmFile) fd.append("bgm_file", bgmFile);

    try {
        await api("/api/generate", { method: "POST", body: fd });
        switchTab("tab-history");
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
    }
}

/* ---------------- toplu üretim ---------------- */

function updateBatchPreview() {
    const raw = el("batch_text").value;
    const box = el("batch-preview-box");
    clearNode(box);

    // JSON girdisi destegi
    const trimmed = raw.trim();
    if (trimmed.startsWith("[") || trimmed.startsWith("{")) {
        try {
            let data = JSON.parse(trimmed);
            if (!Array.isArray(data)) {
                data = data.videos || data.items || [data];
            }
            const items = data.filter(x => x && typeof x === "object");
            box.appendChild(make("div", "accent", `📋 JSON: ${items.length} adet kayıt algılandı:`));
            items.forEach((x, i) => {
                const low = {};
                Object.keys(x).forEach(k => low[k.toLowerCase()] = typeof x[k] === "string" ? x[k] : (Array.isArray(x[k]) ? x[k].join(", ") : ""));
                const subject = low.subject || low.video_subject || low.title || `Kayıt ${i + 1}`;
                const script = low.script || low.video_script || low.text || "";
                const kw = low.pexels_query || low.video_terms || low.keywords || low.terms || "";
                const v = low.voice || low.ses || low.speaker || "";
                const item = make("div", "batch-item-tag");
                const head = make("div");
                head.style.cssText = "display:flex;justify-content:space-between;";
                head.appendChild(make("span", "accent", `${i + 1}. ${subject}`));
                head.appendChild(make("span", "muted", `${script.length} krk`));
                item.appendChild(head);
                const badges = make("div", null, null);
                badges.style.cssText = "display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;";
                if (kw) badges.appendChild(make("span", "kw-badge", "🏷️ " + kw));
                if (v) badges.appendChild(make("span", "kw-badge", "🎙️ " + v));
                if (badges.children.length) item.appendChild(badges);
                box.appendChild(item);
            });
            return;
        } catch (e) { /* JSON degil, metin olarak devam */ }
    }

    const blocks = raw.split(/\n\s*[-=]{3,}\s*\n/).map(b => b.trim()).filter(Boolean);
    if (!blocks.length) {
        box.appendChild(make("span", "muted", "Script bulunamadı."));
        return;
    }
    box.appendChild(make("div", "accent", `📋 ${blocks.length} adet script algılandı:`));

    blocks.forEach((b, i) => {
        const lines = b.split("\n").map(l => l.trim()).filter(Boolean);
        let title = `Ders ${i + 1}`;
        let kw = "";
        let vname = "";
        lines.forEach(line => {
            if (line.startsWith("#")) title = line.replace(/^#+\s*/, "").trim();
            const m = line.match(/^(keywords|etiketler|anahtar kelimeler|terms|tags)\s*:\s*(.+)/i);
            if (m) kw = m[2].trim();
            const mv = line.match(/^(ses|voice|seslendirmen|speaker)\s*:\s*(.+)/i);
            if (mv) vname = mv[2].trim();
        });
        const item = make("div", "batch-item-tag");
        const head = make("div");
        head.style.cssText = "display:flex;justify-content:space-between;";
        head.appendChild(make("span", "accent", `${i + 1}. ${title}`));
        head.appendChild(make("span", "muted", `${b.length} krk`));
        item.appendChild(head);
        const badges = make("div", null, null);
        badges.style.cssText = "display:flex; gap:4px; flex-wrap:wrap; margin-top:2px;";
        if (kw) badges.appendChild(make("span", "kw-badge", "🏷️ " + kw));
        if (vname) badges.appendChild(make("span", "kw-badge", "🎙️ " + vname));
        if (badges.children.length) item.appendChild(badges);
        box.appendChild(item);
    });
}

function handleBatchFileUpload(ev) {
    const file = ev.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        el("batch_text").value = e.target.result;
        updateBatchPreview();
    };
    reader.readAsText(file);
}

async function submitBatch() {
    if (!el("batch_text").value.trim()) {
        alert("Lütfen çoklu ders scriptlerini girin.");
        return;
    }
    const btn = el("btn-batch-submit");
    btn.disabled = true;

    const fd = new FormData();
    Object.entries(collectCommonParams("batch")).forEach(([k, v]) => fd.append(k, v));

    // Çoklu ses havuzu kontrolü
    const isPool = el("batch_vmode_pool") && el("batch_vmode_pool").checked;
    if (isPool && selectedBatchVoices.length > 0) {
        fd.set("voices", selectedBatchVoices.join(","));
    }

    try {
        const data = await api("/api/batch", { method: "POST", body: fd });
        alert(`✅ ${data.count} adet ders kuyruğa alındı!`);
        switchTab("tab-history");
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
    }
}

/* ---------------- galeri ---------------- */

const STATUS_LABELS = {
    queued: "Kuyrukta", processing: "İşleniyor", completed: "Tamamlandı",
    failed: "Hata", interrupted: "Duraklatıldı"
};

function taskCard(t) {
    const card = make("div", "task-card");

    const header = make("div", "task-header");
    const hleft = make("div");
    hleft.appendChild(make("h3", "task-title", t.subject || "Ders Scripti"));
    let timeLine = t.created_at_str || "";
    if (t.batch_index && t.batch_total) timeLine += ` • Toplu ${t.batch_index}/${t.batch_total}`;
    timeLine += ` • ${t.aspect}`;
    hleft.appendChild(make("div", "task-time", timeLine));
    header.appendChild(hleft);

    const headerRight = make("div", "task-actions-right");
    const pill = make("span", "status-pill st-" + t.state, STATUS_LABELS[t.state] || t.state);
    if (t.state === "queued" && t.queue_position > 0) pill.textContent += ` (#${t.queue_position})`;
    headerRight.appendChild(pill);
    if (t.state === "queued" || t.state === "processing") {
        const cancelBtn = actionBtn("İptal", "btn-cancel-job", () => cancelTask(t.task_id));
        cancelBtn.title = "İşlemi iptal et";
        headerRight.appendChild(cancelBtn);
    }
    if (t.state === "completed") {
        const dots = make("button", "btn-dots", "⋮");
        dots.title = "Varyantlar / İşlemler";
        dots.addEventListener("click", (e) => { e.stopPropagation(); toggleDotsMenu(dots, t); });
        headerRight.appendChild(dots);
    }
    header.appendChild(headerRight);
    card.appendChild(header);

    card.appendChild(make("div", "muted small", t.step_text || ""));

    if (t.parent_task_id) {
        const modeLabels = { voice: "Ses", visuals: "Görüntü", subtitles: "Altyazı", all: "Tam" };
        const label = modeLabels[t.regenerate_mode] || "Varyant";
        card.appendChild(make("span", "variant-tag", `↳ ${label} varyantı`));
    }

    if (t.state === "processing" || t.state === "queued") {
        const bar = make("div", "progress-bar");
        bar.appendChild(make("div", "progress-val")).style.width = (t.progress || 5) + "%";
        card.appendChild(bar);
    }

    if (t.state === "completed" && t.video_url) {
        const vb = make("div", "video-box");
        const video = document.createElement("video");
        video.controls = true;
        video.preload = "metadata";
        video.src = t.video_url;
        vb.appendChild(video);
        card.appendChild(vb);

        const actions = make("div", "actions-row");
        const dlName = (t.subject || "ders_video").replace(/[^\w\- ]+/g, "_").trim() || "ders_video";
        const dl = make("a", "btn-sm btn-download",
            `⬇️ İndir (${t.file_size_mb || "?"} MB)`);
        dl.href = t.video_url + "?download=" + encodeURIComponent(dlName);
        dl.setAttribute("download", dlName + ".mp4");
        actions.appendChild(dl);
        actions.appendChild(delBtn(t.task_id));
        card.appendChild(actions);
    }

    if (t.state === "failed") {
        card.appendChild(make("div", "error-text", t.error || t.step_text || "İşlem başarısız"));
        const actions = make("div", "actions-row");
        actions.appendChild(actionBtn("🔄 Tekrar Dene", "btn-retry", () => resumeTask(t.task_id)));
        actions.appendChild(delBtn(t.task_id, true));
        card.appendChild(actions);
    }

    if (t.state === "interrupted") {
        const actions = make("div", "actions-row");
        actions.appendChild(actionBtn("▶️ Devam Et", "btn-resume", () => resumeTask(t.task_id)));
        actions.appendChild(delBtn(t.task_id, true));
        card.appendChild(actions);
    }

    if (t.logs && t.logs.length) {
        const logBtn = actionBtn("📜 Loglar", "btn-del", null);
        logBtn.style.maxWidth = "100%";
        logBtn.style.flex = "1";
        logBtn.style.color = "#94a3b8";
        logBtn.addEventListener("click", async () => {
            let box = card.querySelector(".log-box");
            if (box) { box.remove(); return; }
            try {
                const data = await api(`/api/tasks/${t.task_id}/logs`);
                box = make("div", "log-box", (data.logs || []).join("\n") || "Log yok.");
                card.appendChild(box);
                box.scrollTop = box.scrollHeight;
            } catch (e) { console.error(e); }
        });
        card.appendChild(logBtn);
    }

    return card;
}

function delBtn(taskId, wide) {
    const b = actionBtn("🗑️", "btn-del", async () => {
        if (!confirm("Bu görevi ve videoyu silmek istiyor musunuz?")) return;
        try {
            await api("/api/tasks/" + taskId, { method: "DELETE" });
            loadTasks();
        } catch (e) { alert(e.message); }
    });
    if (wide) { b.style.maxWidth = "100%"; b.style.flex = "1"; b.textContent = "🗑️ Sil"; }
    return b;
}

function actionBtn(text, cls, handler) {
    const b = make("button", "btn-sm " + cls, text);
    if (handler) b.addEventListener("click", handler);
    return b;
}

async function resumeTask(taskId) {
    try {
        await api(`/api/tasks/${taskId}/resume`, { method: "POST" });
        loadTasks();
    } catch (e) { alert(e.message); }
}

async function cancelTask(taskId) {
    if (!confirm("Bu işlem iptal edilsin mi?")) return;
    try {
        await api(`/api/tasks/${taskId}/cancel`, { method: "POST" });
        loadTasks();
    } catch (e) { alert(e.message); }
}

async function cancelAllTasks() {
    if (!confirm("Kuyruktaki ve çalışan TÜM görevler iptal edilsin mi?")) return;
    const btn = el("btn-cancel-all");
    if (btn) btn.disabled = true;
    try {
        const data = await api("/api/tasks/cancel-all", { method: "POST" });
        alert(`⏹️ ${data.count || 0} görev iptal edildi.`);
        loadTasks();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function deleteAllTasks() {
    if (!confirm("⚠️ DİKKAT: Galerideki TÜM görevler ve videolar kalıcı olarak silinecek!\n\nOnaylıyor musunuz?")) return;
    const btn = el("btn-delete-all");
    if (btn) btn.disabled = true;
    try {
        const data = await api("/api/tasks/delete-all", { method: "POST" });
        alert(`🗑️ ${data.count || 0} görev ve video silindi.`);
        loadTasks();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        if (btn) btn.disabled = false;
    }
}


/* ---------------- varyant (ses / görüntü / altyazı) menüsü ---------------- */

let openMenuEl = null;
let currentModal = null;

function escapeAttr(s) {
    return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;");
}

function toggleDotsMenu(btn, t) {
    if (openMenuEl) { openMenuEl.remove(); openMenuEl = null; return; }
    const menu = make("div", "dots-menu");
    const items = [
        ["🎙️ Seslendirmeyi tekrar al", () => openVariantModal(t, "voice")],
        ["🎬 Görüntüyü tekrar bul", () => openVariantModal(t, "visuals")],
        ["📝 Altyazıyı farklı yap", () => openVariantModal(t, "subtitles")]
    ];
    items.forEach(([label, fn]) => {
        const b = make("button", null, label);
        b.addEventListener("click", (e) => { e.stopPropagation(); menu.remove(); openMenuEl = null; fn(); });
        menu.appendChild(b);
    });
    btn.parentElement.appendChild(menu);
    openMenuEl = menu;
}

function openVariantModal(t, mode) {
    currentModal = { taskId: t.task_id, mode };
    const titles = {
        voice: "🎙️ Seslendirmeyi Tekrar Al",
        visuals: "🎬 Görüntüyü Tekrar Bul",
        subtitles: "📝 Altyazıyı Farklı Yap",
        all: "🔁 Tamamen Yeniden Üret"
    };
    el("vm-title").textContent = titles[mode] || "Varyant Üret";

    let body = "";
    const rate = String(t.voice_rate);
    if (mode === "voice") {
        const voiceOpts = (allVoicesList || []).map(v =>
            `<option value="${v.id}" ${v.id === t.voice ? "selected" : ""}>${v.id}${v.name ? " · " + v.name : ""}</option>`).join("");
        body = `
        <div class="vm-field"><label>Ses (Model)</label><select id="vm_voice">${voiceOpts}</select></div>
        <div class="vm-field"><label>Okuma Hızı</label>
            <select id="vm_rate">
                <option value="0.9" ${rate === "0.9" ? "selected" : ""}>0.9x (Yavaş)</option>
                <option value="1.0" ${rate !== "0.9" && rate !== "1.15" && rate !== "1.25" ? "selected" : ""}>1.0x (Normal)</option>
                <option value="1.15" ${rate === "1.15" ? "selected" : ""}>1.15x (Akıcı)</option>
                <option value="1.25" ${rate === "1.25" ? "selected" : ""}>1.25x (Hızlı)</option>
            </select></div>
        <p class="hint">Seslendirme yeniden üretilir; görüntü aynı kalır.</p>`;
    } else if (mode === "visuals") {
        body = `
        <div class="vm-field"><label>Pexels Anahtar Kelimeler (virgülle)</label>
            <input type="text" id="vm_pexels" value="${escapeAttr(t.pexels_query || "")}" placeholder="math, study"></div>
        <p class="hint">Görüntüler yeniden aranıp birleştirilir (Pexels anahtarı Ayarlar'dan girilmeli).</p>`;
    } else if (mode === "subtitles") {
        const sz = String(t.sub_size);
        body = `
        <div class="vm-field"><label>Altyazı Rengi</label>
            <select id="vm_sub_color">
                <option value="#FFFFFF" ${t.sub_color === "#FFFFFF" ? "selected" : ""}>⚪ Parlak Beyaz</option>
                <option value="#FFD700" ${t.sub_color === "#FFD700" ? "selected" : ""}>🟡 Altın Sarısı</option>
                <option value="#38BDF8" ${t.sub_color === "#38BDF8" ? "selected" : ""}>🔵 Canlı Mavi</option>
                <option value="#4ADE80" ${t.sub_color === "#4ADE80" ? "selected" : ""}>🟢 Yeşil</option>
            </select></div>
        <div class="grid-2">
            <div class="vm-field"><label>Konum</label>
                <select id="vm_sub_pos">
                    <option value="bottom" ${t.sub_pos === "bottom" ? "selected" : ""}>Alt</option>
                    <option value="center" ${t.sub_pos === "center" ? "selected" : ""}>Orta</option>
                    <option value="top" ${t.sub_pos === "top" ? "selected" : ""}>Üst</option>
                </select></div>
            <div class="vm-field"><label>Boyut</label>
                <select id="vm_sub_size">
                    <option value="14" ${sz === "14" ? "selected" : ""}>Küçük</option>
                    <option value="18" ${sz !== "14" && sz !== "22" && sz !== "28" ? "selected" : ""}>Normal</option>
                    <option value="22" ${sz === "22" ? "selected" : ""}>Büyük</option>
                    <option value="28" ${sz === "28" ? "selected" : ""}>Çok Büyük</option>
                </select></div>
        </div>
        <div class="vm-field"><label>Okunabilirlik</label>
            <select id="vm_sub_box">
                <option value="false" ${!t.sub_box ? "selected" : ""}>Düz (kontur)</option>
                <option value="true" ${t.sub_box ? "selected" : ""}>Yarı saydam kutu</option>
            </select></div>
        <p class="hint">Altyazılar orijinal cümle zamanlamasıyla yeniden yazılır.</p>`;
    } else {
        body = `<p class="hint">Tüm video (ses, görüntü, altyazı) baştan üretilir.</p>`;
    }
    el("vm-body").innerHTML = body;
    el("variant-modal").classList.remove("hidden");
}

function closeVariantModal() {
    el("variant-modal").classList.add("hidden");
    currentModal = null;
}

async function applyVariant() {
    if (!currentModal) return;
    const { taskId, mode } = currentModal;
    const payload = { mode };
    if (mode === "voice") {
        payload.voice = el("vm_voice").value;
        payload.voice_rate = parseFloat(el("vm_rate").value);
    } else if (mode === "visuals") {
        payload.pexels_query = el("vm_pexels").value.trim();
    } else if (mode === "subtitles") {
        payload.sub_color = el("vm_sub_color").value;
        payload.sub_pos = el("vm_sub_pos").value;
        payload.sub_size = parseInt(el("vm_sub_size").value, 10);
        payload.sub_box = el("vm_sub_box").value === "true";
    }
    const btn = el("vm-apply");
    btn.disabled = true;
    btn.textContent = "⏳ Üretiliyor...";
    try {
        await api(`/api/tasks/${taskId}/regenerate`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        closeVariantModal();
        loadTasks();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "Üret";
    }
}

let collapsedBatches = new Set();

function downloadBatchZip(batchId) {
    if (!batchId) return;
    window.location.href = `/api/tasks/download-zip?batch_id=${encodeURIComponent(batchId)}`;
}

function downloadAllVideosZip() {
    window.location.href = `/api/tasks/download-zip?all=1`;
}

async function deleteBatch(batchId) {
    if (!confirm("Bu toplu gruptaki tüm videoları ve görevleri silmek istiyor musunuz?")) return;
    try {
        await api(`/api/batches/${encodeURIComponent(batchId)}`, { method: "DELETE" });
        loadTasks();
    } catch (e) {
        alert("Silme hatası: " + e.message);
    }
}

async function loadTasks() {
    // Video oynatilirken arka plan guncellemesi yapma (oynatmayi bozmasin)
    const playing = [...document.querySelectorAll("#tasks-container video")]
        .some(v => !v.paused && !v.ended);
    if (playing) { schedulePoll(); return; }

    let data;
    try {
        data = await api("/api/tasks");
    } catch (e) {
        pollDelay = 6000;
        schedulePoll();
        return;
    }

    const tasks = data.tasks || [];
    el("task-count").textContent = tasks.length;

    const container = el("tasks-container");
    clearNode(container);

    if (!tasks.length) {
        container.appendChild(make("div", "empty-state", "Henüz üretilen video bulunmuyor."));
    } else {
        // Toplu başlatmalara (batch_id) göre grupla
        const groupsMap = {};

        tasks.forEach(t => {
            let gid = t.batch_id;
            if (!gid && t.batch_total) {
                const cTime = Math.floor((t.created_at || 0) / 120);
                gid = `batch_legacy_${cTime}_${t.batch_total}`;
            } else if (!gid) {
                gid = "single";
            }

            if (!groupsMap[gid]) {
                groupsMap[gid] = {
                    id: gid,
                    isSingle: gid === "single",
                    tasks: [],
                    completedCount: 0,
                    processingCount: 0,
                    failedCount: 0,
                    latestTime: 0,
                    earliestTime: Infinity,
                    dateStr: ""
                };
            }
            const grp = groupsMap[gid];
            grp.tasks.push(t);
            const ct = t.created_at || 0;
            if (ct > grp.latestTime) grp.latestTime = ct;
            if (ct < grp.earliestTime) {
                grp.earliestTime = ct;
                grp.dateStr = t.created_at_str || "";
            }
            if (t.state === "completed") grp.completedCount++;
            else if (t.state === "processing" || t.state === "queued") grp.processingCount++;
            else if (t.state === "failed" || t.state === "interrupted") grp.failedCount++;
        });

        // Grupları en yeni başlatılana göre sırala
        const sortedGroups = Object.values(groupsMap).sort((a, b) => b.latestTime - a.latestTime);

        sortedGroups.forEach(grp => {
            // Görevleri batch_index veya created_at sırasına göre diz
            grp.tasks.sort((a, b) => (a.batch_index || 0) - (b.batch_index || 0) || (a.created_at || 0) - (b.created_at || 0));

            const isCollapsed = collapsedBatches.has(grp.id);
            const accordion = make("div", "batch-accordion" + (isCollapsed ? "" : " open"));

            // Başlık Formatı
            let titleText = "";
            let timeFormatted = grp.dateStr;
            if (timeFormatted && timeFormatted.includes("-")) {
                const parts = timeFormatted.split(" ");
                const dPart = parts[0].split("-").reverse().join(".");
                timeFormatted = dPart + (parts[1] ? " " + parts[1].slice(0, 5) : "");
            }

            if (grp.isSingle) {
                titleText = `📝 Tekli Üretimler (${grp.tasks.length} Video)`;
            } else {
                titleText = `📚 Toplu Başlatma (${grp.tasks.length} Video) • ${timeFormatted || "Dersler"}`;
            }

            // Akordiyon Başlığı
            const header = make("div", "batch-header");
            const hLeft = make("div", "batch-header-left");

            const toggleIcon = make("span", "batch-toggle-icon", "▶");
            hLeft.appendChild(toggleIcon);

            const infoDiv = make("div");
            infoDiv.appendChild(make("div", "batch-title", titleText));

            const metaDiv = make("div", "batch-meta");
            const readyBadge = make("span", "batch-badge" + (grp.completedCount > 0 ? " ready" : ""),
                `${grp.completedCount} / ${grp.tasks.length} Hazır`);
            metaDiv.appendChild(readyBadge);

            if (grp.processingCount > 0) {
                metaDiv.appendChild(make("span", "batch-badge processing", `⏳ ${grp.processingCount} İşleniyor`));
            }
            if (grp.failedCount > 0) {
                const errBadge = make("span", "batch-badge", `⚠️ ${grp.failedCount} Hata`);
                errBadge.style.color = "#f87171";
                metaDiv.appendChild(errBadge);
            }
            infoDiv.appendChild(metaDiv);
            hLeft.appendChild(infoDiv);
            header.appendChild(hLeft);

            // Başlık Sağ Butonları (ZIP İndir & Sil)
            const actionsDiv = make("div", "batch-actions");
            if (grp.completedCount > 0) {
                const zipBtn = make("button", "btn-batch-zip");
                zipBtn.innerHTML = `📦 ZIP İndir (${grp.completedCount})`;
                zipBtn.title = `Bu gruptaki ${grp.completedCount} tamamlanan videoyu sıkıştırmasız ZIP olarak indir`;
                zipBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    if (grp.isSingle) {
                        const compIds = grp.tasks.filter(x => x.state === "completed").map(x => x.task_id).join(",");
                        window.location.href = `/api/tasks/download-zip?task_ids=${encodeURIComponent(compIds)}`;
                    } else {
                        downloadBatchZip(grp.id);
                    }
                });
                actionsDiv.appendChild(zipBtn);
            }

            const delGrpBtn = make("button", "btn-batch-del", "🗑️");
            delGrpBtn.title = "Bu grubu ve videolarını sil";
            delGrpBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                if (grp.isSingle) {
                    if (confirm("Tekli üretimlerdeki tüm videolar silinsin mi?")) {
                        Promise.all(grp.tasks.map(t => api("/api/tasks/" + t.task_id, { method: "DELETE" })))
                            .then(() => loadTasks())
                            .catch(err => alert(err.message));
                    }
                } else {
                    deleteBatch(grp.id);
                }
            });
            actionsDiv.appendChild(delGrpBtn);
            header.appendChild(actionsDiv);

            // Akordiyon Gövdesi
            const body = make("div", "batch-body" + (isCollapsed ? " collapsed" : ""));
            grp.tasks.forEach(t => {
                const card = taskCard(t);
                card.dataset.tid = t.task_id;
                body.appendChild(card);
            });

            // Tıklama ile Aç / Kapa
            header.addEventListener("click", () => {
                const nowCollapsed = !body.classList.contains("collapsed");
                body.classList.toggle("collapsed", nowCollapsed);
                accordion.classList.toggle("open", !nowCollapsed);
                if (nowCollapsed) {
                    collapsedBatches.add(grp.id);
                } else {
                    collapsedBatches.delete(grp.id);
                }
            });

            accordion.appendChild(header);
            accordion.appendChild(body);
            container.appendChild(accordion);
        });
    }

    const hasRunning = tasks.some(t => t.state === "processing" || t.state === "queued");
    pollDelay = hasRunning ? 2000 : 12000;

    if (data.auth_url) el("auth-link").value = data.auth_url;
    schedulePoll();
}

function schedulePoll() {
    if (pollTimer) clearTimeout(pollTimer);
    pollTimer = setTimeout(loadTasks, pollDelay);
}

/* ---------------- AI script uretimi ---------------- */

async function loadAIProviders() {
    const sel = el("ai_provider");
    try {
        const data = await api("/api/llm/providers");
        clearNode(sel);
        const providers = data.providers || [];
        if (!providers.length) {
            sel.appendChild(make("option", null, "API key yok (Ayarlar)"));
            return;
        }
        providers.forEach(p => {
            const o = make("option", null, p.id.toUpperCase());
            o.value = p.id;
            sel.appendChild(o);
        });
        loadModels();
    } catch (e) {
        console.error(e);
    }
}

async function loadModels() {
    const provider = el("ai_provider").value;
    const sel = el("ai_model");
    clearNode(sel);
    if (!provider) return;
    try {
        const data = await api(`/api/models?provider=${provider}`);
        const models = data.models || [];
        models.forEach(m => {
            const o = make("option", null, m);
            o.value = m;
            sel.appendChild(o);
        });
    } catch (e) {
        sel.appendChild(make("option", null, "Varsayılan"));
    }
}

async function aiGenerateScript() {
    const btn = el("btn-ai-generate");
    const subject = el("subject").value.trim();
    if (!subject) { alert("Lütfen önce bir Ders / Konu Başlığı girin."); return; }
    btn.disabled = true;
    btn.textContent = "⏳ Yazılıyor...";
    try {
        const data = await api("/api/llm/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                provider: el("ai_provider").value,
                model: el("ai_model").value,
                subject,
                paragraph_number: parseInt(el("ai_paragraphs").value, 10),
                extra_requirements: el("ai_extra").value,
                gen_terms: el("ai_gen_terms_chk").checked
            })
        });
        if (data.script) {
            el("script").value = data.script;
            updateCharCount();
        }
        if (data.terms && data.terms.length) {
            el("pexels_query").value = data.terms.join(", ");
        }
    } catch (e) {
        alert("Üretim hatası: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "✨ Script Üret";
    }
}

/* ---------------- JSON girdisi ---------------- */

function fillFormFromJson() {
    const raw = el("json_input").value.trim();
    if (!raw) { alert("Lütfen bir JSON metni yapıştırın."); return; }
    try {
        let obj = JSON.parse(raw);
        if (Array.isArray(obj)) obj = obj[0] || {};
        const low = {};
        Object.keys(obj).forEach(k => low[k.toLowerCase()] = obj[k]);
        const subj = low.subject || low.video_subject || low.title || "";
        const scr = low.script || low.video_script || low.text || "";
        const terms = low.pexels_query || low.video_terms || low.keywords || low.terms || "";
        if (subj) el("subject").value = subj;
        if (scr) { el("script").value = scr; updateCharCount(); }
        if (terms) {
            el("pexels_query").value = Array.isArray(terms) ? terms.join(", ") : String(terms);
        }
        alert("✅ JSON içeriği forma aktarıldı.");
    } catch (e) {
        alert("Geçersiz JSON formatı: " + e.message);
    }
}

/* ---------------- şarkılar & ayarlar ---------------- */

async function loadSongs() {
    try {
        const data = await api("/api/songs");
        const container = el("songs-list");
        clearNode(container);
        const songs = data.songs || [];
        if (!songs.length) {
            container.appendChild(make("div", "empty-state", "Klasörde müzik bulunamadı."));
            return;
        }
        songs.forEach(s => {
            const row = make("div", "song-item");
            const left = make("span", "song-name", `${s.name} (${s.size_mb} MB)`);
            const del = make("button", "btn-song-del", "Sil");
            del.addEventListener("click", async () => {
                if (!confirm(`"${s.name}" silinsin mi?`)) return;
                try {
                    await api(`/api/songs/${encodeURIComponent(s.name)}`, { method: "DELETE" });
                    loadSongs();
                } catch (e) { alert(e.message); }
            });
            row.appendChild(left);
            row.appendChild(del);
            container.appendChild(row);
        });
    } catch (e) { console.error(e); }
}

async function uploadSongs() {
    const input = el("song_files");
    if (!input.files || !input.files.length) { alert("Lütfen en az bir müzik dosyası seçin."); return; }
    const fd = new FormData();
    for (let i = 0; i < input.files.length; i++) {
        fd.append("song_file", input.files[i]);
    }
    const btn = el("btn-upload-songs");
    btn.disabled = true;
    btn.textContent = "⏳ Yükleniyor...";
    try {
        const res = await api("/api/songs", { method: "POST", body: fd });
        alert(res.message || "Müzikler eklendi.");
        input.value = "";
        loadSongs();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "⬆️ Ekle";
    }
}

const SECRET_INPUTS = [
    "set_pexels", "set_pixabay", "set_openai", "set_gemini", "set_groq",
    "set_deepseek", "set_azure_key", "set_elevenlabs", "set_ngrok"
];

async function loadSettings() {
    let s = {};
    try {
        const data = await api("/api/settings");
        s = data.settings || {};
    } catch (e) { console.error(e); }

    SECRET_INPUTS.forEach(id => {
        const k = id.replace(/^set_/, "");
        const map = {
            pexels: "pexels_api_keys", pixabay: "pixabay_api_keys",
            openai: "openai_api_key", gemini: "gemini_api_key", groq: "groq_api_key",
            deepseek: "deepseek_api_key", azure_key: "azure_speech_key",
            elevenlabs: "elevenlabs_api_key", ngrok: "ngrok_authtoken"
        };
        const keyName = map[k] || k;
        if (s[keyName] !== undefined && s[keyName] !== "") el(id).placeholder = s[keyName];
    });

    if (s.azure_speech_region) el("set_azure_reg").value = s.azure_speech_region;
    if (s.prod_voice) el("voice").value = s.prod_voice;
    if (s.prod_voice_rate !== undefined) el("voice_rate").value = String(s.prod_voice_rate);
    if (s.prod_voice_volume !== undefined) el("voice_volume").value = String(s.prod_voice_volume);
    if (s.prod_aspect) el("aspect").value = s.prod_aspect;
    if (s.prod_resolution) el("resolution").value = s.prod_resolution;
    if (s.prod_bg_style) el("bg_style").value = s.prod_bg_style;
    if (s.prod_subtitle_enabled !== undefined) el("subtitle_enabled_chk").checked = s.prod_subtitle_enabled;
    if (s.prod_sub_color) el("sub_color").value = s.prod_sub_color;
    if (s.prod_sub_pos) el("sub_pos").value = s.prod_sub_pos;
    if (s.prod_sub_size !== undefined) el("sub_size").value = String(s.prod_sub_size);
    if (s.prod_sub_box !== undefined) el("sub_box").value = String(s.prod_sub_box);
    if (s.prod_highlight_color && el("prod_highlight_color")) el("prod_highlight_color").value = s.prod_highlight_color;
    if (s.prod_highlight_words !== undefined && el("prod_highlight_words")) el("prod_highlight_words").value = s.prod_highlight_words;
    if (s.prod_bgm_mode) el("bgm_source").value = s.prod_bgm_mode;
    if (s.prod_bgm_volume !== undefined) el("bgm_volume").value = String(s.prod_bgm_volume);
    if (s.prod_transition) el("prod_transition").value = s.prod_transition;
    if (s.prod_transition_dur !== undefined) el("prod_transition_dur").value = String(s.prod_transition_dur);
    if (s.prod_voice) updateSelectedVoiceDisplay(s.prod_voice, "");
}

async function saveSettings() {
    const payload = {
        pexels_api_keys: el("set_pexels").value.trim(),
        pixabay_api_keys: el("set_pixabay").value.trim(),
        openai_api_key: el("set_openai").value.trim(),
        gemini_api_key: el("set_gemini").value.trim(),
        groq_api_key: el("set_groq").value.trim(),
        deepseek_api_key: el("set_deepseek").value.trim(),
        azure_speech_key: el("set_azure_key").value.trim(),
        azure_speech_region: el("set_azure_reg").value.trim(),
        elevenlabs_api_key: el("set_elevenlabs").value.trim(),
        ngrok_authtoken: el("set_ngrok").value.trim(),
        prod_voice: el("voice").value,
        prod_voice_rate: parseFloat(el("voice_rate").value || "1.0"),
        prod_voice_volume: parseFloat(el("voice_volume").value || "1.0"),
        prod_aspect: el("aspect").value,
        prod_resolution: el("resolution") ? el("resolution").value : "720p",
        prod_bg_style: el("bg_style").value,
        prod_subtitle_enabled: el("subtitle_enabled_chk").checked,
        prod_sub_color: el("sub_color").value,
        prod_sub_pos: el("sub_pos").value,
        prod_sub_size: parseInt(el("sub_size").value || "18", 10),
        prod_sub_box: el("sub_box").value === "true",
        prod_highlight_color: el("prod_highlight_color") ? el("prod_highlight_color").value : "#FFD700",
        prod_highlight_words: el("prod_highlight_words") ? el("prod_highlight_words").value.trim() : "",
        prod_bgm_mode: el("bgm_source").value,
        prod_bgm_volume: parseFloat(el("bgm_volume").value || "0.15"),
        prod_transition: el("prod_transition").value,
        prod_transition_dur: parseFloat(el("prod_transition_dur").value || "0.5")
    };
    try {
        await api("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        alert("✅ Ayarlar kaydedildi!");
        loadSettings();
    } catch (e) {
        alert("Hata: " + e.message);
    }
}

function toggleKeyVisibility() {
    const show = el("toggle_key_visibility").checked;
    SECRET_INPUTS.forEach(id => { el(id).type = show ? "text" : "password"; });
}

async function loadTunnelStatus() {
    try {
        const data = await api("/api/tunnel/status");
        const badge = el("tunnel-status-badge");
        const urlBox = el("tunnel-url-container");
        const pubInput = el("tunnel-public-url");
        const openLink = el("btn-open-tunnel-url");
        const btnStart = el("btn-tunnel-start");
        const btnStop = el("btn-tunnel-stop");
        const localList = el("local-urls-list");

        if (data.running && data.public_url) {
            badge.textContent = `● Aktif (${data.provider || "Tunnel"})`;
            badge.style.background = "#065f46";
            badge.style.color = "#6ee7b7";
            badge.style.borderColor = "#059669";
            pubInput.value = data.auth_url || data.public_url;
            openLink.href = data.auth_url || data.public_url;
            urlBox.classList.remove("hidden");
            btnStart.classList.add("hidden");
            btnStop.classList.remove("hidden");
            if (data.provider && el("tunnel_provider_select")) {
                el("tunnel_provider_select").value = data.provider;
                toggleNgrokTokenField();
            }
        } else {
            badge.textContent = "○ Kapalı";
            badge.style.background = "#1e293b";
            badge.style.color = "#94a3b8";
            badge.style.borderColor = "#334155";
            urlBox.classList.add("hidden");
            btnStart.classList.remove("hidden");
            btnStop.classList.add("hidden");
        }

        if (localList) {
            localList.innerHTML = "";
            const urls = (data.local_urls && data.local_urls.length > 0) ? data.local_urls : [`http://127.0.0.1:${data.port || 8080}/?token=${data.token || ""}`];
            urls.forEach(u => {
                const div = document.createElement("div");
                div.style.marginTop = "3px";
                div.innerHTML = `👉 <a href="${u}" target="_blank" class="accent" style="text-decoration:underline;">${u}</a>`;
                localList.appendChild(div);
            });
        }
    } catch (e) {
        console.warn("Tunnel durumu alınamadı:", e);
    }
}

function toggleNgrokTokenField() {
    const sel = el("tunnel_provider_select");
    const container = el("ngrok_token_container");
    if (sel && container) {
        container.classList.toggle("hidden", sel.value !== "ngrok");
    }
}

async function startTunnel() {
    const btn = el("btn-tunnel-start");
    const badge = el("tunnel-status-badge");
    const provider = (el("tunnel_provider_select") ? el("tunnel_provider_select").value : "cloudflare") || "cloudflare";
    btn.disabled = true;
    badge.textContent = `⏳ Başlatılıyor (${provider})...`;
    try {
        const data = await api("/api/tunnel/start", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider })
        });
        if (data.error) {
            alert("⚠️ " + data.error);
        }
        await loadTunnelStatus();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
        await loadTunnelStatus();
    }
}

async function stopTunnel() {
    const btn = el("btn-tunnel-stop");
    const badge = el("tunnel-status-badge");
    btn.disabled = true;
    badge.textContent = "⏳ Durduruluyor...";
    try {
        await api("/api/tunnel/stop", { method: "POST" });
        await loadTunnelStatus();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
        await loadTunnelStatus();
    }
}

function copyTunnelUrl() {
    const pubInput = el("tunnel-public-url");
    if (!pubInput || !pubInput.value) return;
    navigator.clipboard.writeText(pubInput.value).then(() => {
        const btn = el("btn-copy-tunnel-url");
        const orig = btn.textContent;
        btn.textContent = "✅ Kopyalandı!";
        setTimeout(() => { btn.textContent = orig; }, 2000);
    }).catch(() => {
        pubInput.select();
        document.execCommand("copy");
    });
}

/* ---------------- sekmeler ---------------- */

const TAB_IDS = ["tab-create", "tab-batch", "tab-history", "tab-settings"];
const TAB_ENTER = {
    "tab-batch": updateBatchPreview,
    "tab-history": loadTasks,
    "tab-settings": () => { loadSettings(); loadSongs(); loadTunnelStatus(); }
};

function switchTab(tabId) {
    TAB_IDS.forEach(id => el(id).classList.toggle("hidden", id !== tabId));
    document.querySelectorAll(".tab-btn").forEach((b, i) =>
        b.classList.toggle("active", TAB_IDS[i] === tabId));
    if (TAB_ENTER[tabId]) TAB_ENTER[tabId]();
}

/* ---------------- init ---------------- */

function bindEvents() {
    document.querySelectorAll(".tab-btn").forEach(b =>
        b.addEventListener("click", () => switchTab(b.dataset.tab)));

    el("script").addEventListener("input", updateCharCount);
    el("voice-search").addEventListener("input", filterVoiceList);

    el("btn-submit").addEventListener("click", submitVideo);
    el("btn-voice-preview").addEventListener("click", playVoicePreview);
    el("btn-batch-submit").addEventListener("click", submitBatch);
    el("btn-save-settings").addEventListener("click", saveSettings);
    
    const bTunStart = el("btn-tunnel-start");
    if (bTunStart) bTunStart.addEventListener("click", startTunnel);
    const bTunStop = el("btn-tunnel-stop");
    if (bTunStop) bTunStop.addEventListener("click", stopTunnel);
    const bCopyTun = el("btn-copy-tunnel-url");
    if (bCopyTun) bCopyTun.addEventListener("click", copyTunnelUrl);
    const selTunProv = el("tunnel_provider_select");
    if (selTunProv) selTunProv.addEventListener("change", toggleNgrokTokenField);

    el("btn-upload-songs").addEventListener("click", uploadSongs);
    const bCancelAll = el("btn-cancel-all");
    if (bCancelAll) bCancelAll.addEventListener("click", cancelAllTasks);
    const bDeleteAll = el("btn-delete-all");
    if (bDeleteAll) bDeleteAll.addEventListener("click", deleteAllTasks);
    const bDlAll = el("btn-download-all-zip");
    if (bDlAll) bDlAll.addEventListener("click", downloadAllVideosZip);
    const bDlDay = el("btn-download-day");
    if (bDlDay) bDlDay.addEventListener("click", downloadAllVideosZip);

    // Toplu ses havuzu olayları
    const bVmodeDef = el("batch_vmode_default");
    if (bVmodeDef) bVmodeDef.addEventListener("change", toggleBatchVoiceMode);
    const bVmodePool = el("batch_vmode_pool");
    if (bVmodePool) bVmodePool.addEventListener("change", toggleBatchVoiceMode);
    const bVSearch = el("batch-voice-search");
    if (bVSearch) bVSearch.addEventListener("input", filterBatchVoiceList);
    const bSelTr = el("btn-batch-sel-tr");
    if (bSelTr) bSelTr.addEventListener("click", selectTurkishBatchVoices);
    const bSelClr = el("btn-batch-sel-clear");
    if (bSelClr) bSelClr.addEventListener("click", clearBatchVoices);

    el("btn-ai-generate").addEventListener("click", aiGenerateScript);
    el("btn-json-fill").addEventListener("click", fillFormFromJson);
    const bFill = el("btn-batch-example-fill");
    if (bFill) bFill.addEventListener("click", () => {
        fetch("/static/examples/mpt_ornek_toplu.json")
            .then(r => r.text())
            .then(txt => { el("batch_text").value = txt; updateBatchPreview(); });
    });
    el("batch_file_upload").addEventListener("change", handleBatchFileUpload);
    el("batch_text").addEventListener("input", updateBatchPreview);
    el("toggle_key_visibility").addEventListener("change", toggleKeyVisibility);

    el("vm-cancel").addEventListener("click", closeVariantModal);
    el("vm-apply").addEventListener("click", applyVariant);
    document.addEventListener("click", (e) => {
        if (openMenuEl && !openMenuEl.contains(e.target) && !(e.target.classList && e.target.classList.contains("btn-dots"))) {
            openMenuEl.remove();
            openMenuEl = null;
        }
    });

    document.querySelectorAll(".btn-copy").forEach(b =>
        b.addEventListener("click", () => {
            const input = el(b.dataset.copy);
            navigator.clipboard?.writeText(input.value).then(
                () => { b.textContent = "✓"; setTimeout(() => b.textContent = "Kopyala", 1500); },
                () => {}
            );
        }));
}

bindEvents();
restorePreferences();
loadVoices();
loadAIProviders();
updateBatchPreview();
loadTasks();
