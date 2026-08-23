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

async function loadVoices() {
    try {
        const data = await api("/api/voices");
        allVoicesList = data.voices || [];
        filterVoiceList();
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
    // Tüm üretim ayarları artık Ayarlar -> Üretim Tercihleri'nde (global).
    const p = {
        subject: el("subject").value.trim(),
        script: el("script").value.trim(),
        pexels_query: el("pexels_query").value.trim(),
        voice: el("voice").value,
        voice_rate: el("voice_rate").value,
        voice_volume: el("voice_volume").value,
        aspect: el("aspect").value,
        bg_style: el("bg_style").value,
        sub_color: el("sub_color").value,
        sub_pos: el("sub_pos").value,
        sub_size: el("sub_size").value,
        sub_box: el("sub_box").value,
        subtitle_enabled: el("subtitle_enabled_chk").checked ? "true" : "false",
        bgm_source: el("bgm_source").value,
        bgm_volume: el("bgm_volume").value,
        transition: el("prod_transition").value,
        transition_dur: el("prod_transition_dur").value
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
                const item = make("div", "batch-item-tag");
                const head = make("div");
                head.style.cssText = "display:flex;justify-content:space-between;";
                head.appendChild(make("span", "accent", `${i + 1}. ${subject}`));
                head.appendChild(make("span", "muted", `${script.length} krk`));
                item.appendChild(head);
                if (kw) item.appendChild(make("div", "kw-badge", "🏷️ " + kw));
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
        lines.forEach(line => {
            if (line.startsWith("#")) title = line.replace(/^#+\s*/, "").trim();
            const m = line.match(/^(keywords|etiketler|anahtar kelimeler|terms|tags)\s*:\s*(.+)/i);
            if (m) kw = m[2].trim();
        });
        const item = make("div", "batch-item-tag");
        const head = make("div");
        head.style.cssText = "display:flex;justify-content:space-between;";
        head.appendChild(make("span", "accent", `${i + 1}. ${title}`));
        head.appendChild(make("span", "muted", `${b.length} krk`));
        item.appendChild(head);
        if (kw) item.appendChild(make("div", "kw-badge", "🏷️ " + kw));
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
    const existing = {};
    container.querySelectorAll(".task-card").forEach(c => { existing[c.dataset.tid] = c; });

    let prevNode = null;
    let addedOrChanged = false;
    tasks.forEach(t => {
        const sig = [t.state, t.progress, t.step_text || "", t.queue_position,
                     t.error || "", t.file_size_mb ?? ""].join("|");
        const old = existing[t.task_id];
        if (old && old.dataset.sig === sig) {
            delete existing[t.task_id];
            prevNode = old;
            return; // degismedi -> dokunma (video oynatma durumu korunur)
        }
        const card = taskCard(t);
        card.dataset.tid = t.task_id;
        card.dataset.sig = sig;
        delete existing[t.task_id];
        if (old) {
            old.replaceWith(card);      // yerinde degistir
        } else if (prevNode) {
            prevNode.after(card);       // dogru siraya ekle
        } else {
            container.prepend(card);
        }
        prevNode = card;
        addedOrChanged = true;
    });

    // Artik listede olmayan kartlari kaldir
    Object.values(existing).forEach(node => node.remove());

    // bos durum mesaji
    const emptyBox = container.querySelector(".empty-state");
    if (!tasks.length && !emptyBox) {
        container.prepend(make("div", "empty-state", "Henüz üretilen video bulunmuyor."));
    } else if (tasks.length && emptyBox) {
        emptyBox.remove();
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
    const modelSel = el("ai_model");
    clearNode(modelSel);
    modelSel.appendChild(make("option", null, "Yükleniyor..."));
    if (!provider) return;
    try {
        const data = await api("/api/models?provider=" + encodeURIComponent(provider));
        clearNode(modelSel);
        const models = data.models || [];
        if (!models.length) {
            modelSel.appendChild(make("option", null, "Model bulunamadı"));
            return;
        }
        models.forEach(m => {
            const o = make("option", null, m.label && m.label !== m.id ? `${m.label} (${m.id})` : m.id);
            o.value = m.id;
            modelSel.appendChild(o);
        });
    } catch (e) {
        clearNode(modelSel);
        modelSel.appendChild(make("option", null, "Hata: " + e.message.slice(0, 40)));
    }
}

async function aiGenerateScript() {
    const btn = el("btn-ai-generate");
    const provider = el("ai_provider").value;
    const model = el("ai_model").value;
    const subject = el("subject").value.trim();
    if (!model) { alert("Önce bir model seçin."); return; }
    if (!subject) { alert("Önce konu başlığı girin (script bu konuya göre üretilir)."); return; }

    btn.disabled = true;
    btn.textContent = "⏳ Üretiliyor...";
    try {
        const data = await api("/api/llm/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                provider: provider,
                model: model,
                subject: subject,
                paragraph_number: parseInt(el("ai_paragraphs").value, 10),
                extra_requirements: el("ai_extra").value.trim(),
                gen_terms: el("ai_gen_terms_chk").checked
            })
        });
        el("script").value = (data.script || "").trim();
        updateCharCount();
        if (data.terms && data.terms.length) {
            el("pexels_query").value = data.terms.join(", ");
        }
    
        alert("✅ Script üretildi ve forma dolduruldu.");
    } catch (e) {
        alert("Script üretilemedi: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "✨ Script Üret";
    }
}

/* ---------------- JSON girdisi ---------------- */

function fillFormFromJson() {
    let data;
    try {
        data = JSON.parse(el("json_input").value);
    } catch (e) {
        alert("Geçersiz JSON: " + e.message);
        return;
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) {
        alert("Tek kayıtlı bir JSON nesnesi bekleniyor.");
        return;
    }
    const low = {};
    Object.keys(data).forEach(k => low[k.toLowerCase()] =
        typeof data[k] === "string" ? data[k] : (Array.isArray(data[k]) ? data[k].join(", ") : ""));
    if (low.subject || low.video_subject) el("subject").value = low.subject || low.video_subject;
    const script = low.script || low.video_script || low.text || "";
    if (script) el("script").value = script;
    const kw = low.pexels_query || low.video_terms || low.keywords || low.terms || "";
    if (kw) el("pexels_query").value = kw;
    updateCharCount();

}

/* ---------------- müzik kütüphanesi ---------------- */

async function loadSongs() {
    const box = el("songs-list");
    let data;
    try {
        data = await api("/api/songs");
    } catch (e) {
        box.textContent = "Liste alınamadı: " + e.message;
        return;
    }
    clearNode(box);
    const songs = data.songs || [];
    if (!songs.length) {
        box.appendChild(make("div", "muted small", "Kütüphane boş. Yukarıdan müzik ekleyin."));
        return;
    }
    songs.forEach(s => {
        const row = make("div", "song-item");
        row.appendChild(make("span", "song-name", `🎵 ${s.name} (${s.size_mb} MB)`));
        const del = make("button", "btn-song-del", "🗑️");
        del.title = s.name + " sil";
        del.addEventListener("click", async () => {
            if (!confirm(`"${s.name}" kütüphaneden silinsin mi?`)) return;
            try {
                await api("/api/songs/" + encodeURIComponent(s.name), { method: "DELETE" });
                loadSongs();
            } catch (e) { alert(e.message); }
        });
        row.appendChild(del);
        box.appendChild(row);
    });
}

async function uploadSongs() {
    const input = el("song_files");
    if (!input.files.length) {
        alert("Önce müzik dosyası seçin.");
        return;
    }
    const btn = el("btn-upload-songs");
    btn.disabled = true;
    btn.textContent = "⏳...";
    const fd = new FormData();
    [...input.files].forEach(f => fd.append("song_file", f));
    try {
        const data = await api("/api/songs", { method: "POST", body: fd });
        alert(data.message || "Eklendi");
        input.value = "";
        loadSongs();
    } catch (e) {
        alert("Hata: " + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = "⬆️ Ekle";
    }
}

/* ---------------- ayarlar ---------------- */

const SECRET_INPUTS = ["set_pexels", "set_pixabay", "set_openai", "set_gemini",
    "set_groq", "set_deepseek", "set_azure_key", "set_elevenlabs", "set_ngrok"];

async function loadSettings() {
    try {
        const data = await api("/api/settings");
        const s = data.settings || {};
        SECRET_INPUTS.forEach(id => {
            const key = id.replace("set_", "");
            const mapKey = { pexels: "pexels_api_keys",
                pixabay: "pixabay_api_keys",
                openai: "openai_api_key", gemini: "gemini_api_key",
                groq: "groq_api_key", deepseek: "deepseek_api_key",
                azure_key: "azure_speech_key", azure_reg: "azure_speech_region",
                elevenlabs: "elevenlabs_api_key", ngrok: "ngrok_authtoken" }[key] || key;
            const input = el(id);
            input.value = "";
            input.placeholder = s[mapKey] ? `Kayıtlı: ${s[mapKey]}` : "Kayıtlı değil";
        });
        el("auth-link").value = location.origin + "/?token=" + encodeURIComponent(s.auth_token || "");
        applyProductionSettings(s);
    } catch (e) { console.error(e); }
}

function applyProductionSettings(s) {
    const set = (id, val) => { const e = el(id); if (e && val !== undefined && val !== null) e.value = val; };
    set("voice", s.prod_voice);
    set("voice_rate", s.prod_voice_rate);
    set("voice_volume", s.prod_voice_volume);
    set("aspect", s.prod_aspect);
    set("bg_style", s.prod_bg_style);
    set("subtitle_enabled_chk", s.prod_subtitle_enabled);
    set("sub_color", s.prod_sub_color);
    set("sub_pos", s.prod_sub_pos);
    set("sub_size", s.prod_sub_size);
    set("sub_box", String(s.prod_sub_box) === "true" ? "true" : "false");
    set("bgm_source", s.prod_bgm_mode);
    set("bgm_volume", s.prod_bgm_volume);
    set("prod_transition", s.prod_transition);
    set("prod_transition_dur", s.prod_transition_dur);
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
        prod_bg_style: el("bg_style").value,
        prod_subtitle_enabled: el("subtitle_enabled_chk").checked,
        prod_sub_color: el("sub_color").value,
        prod_sub_pos: el("sub_pos").value,
        prod_sub_size: parseInt(el("sub_size").value || "18", 10),
        prod_sub_box: el("sub_box").value === "true",
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

async function startTunnel() {
    const btn = el("btn-tunnel-start");
    const status = el("tunnel-status");
    btn.disabled = true;
    status.textContent = "Başlatılıyor...";
    try {
        const data = await api("/api/tunnel/start", { method: "POST" });
        status.innerHTML = "";
        if (data.public_url) {
            const a = document.createElement("a");
            a.href = data.public_url;
            a.textContent = data.public_url;
            a.target = "_blank";
            a.className = "accent";
            status.appendChild(a);
        } else {
            status.textContent = data.error || "Tunnel başlatılamadı";
        }
    } catch (e) {
        status.textContent = e.message;
    } finally {
        btn.disabled = false;
    }
}

/* ---------------- sekmeler ---------------- */

const TAB_IDS = ["tab-create", "tab-batch", "tab-history", "tab-settings"];
const TAB_ENTER = {
    "tab-batch": updateBatchPreview,
    "tab-history": loadTasks,
    "tab-settings": () => { loadSettings(); loadSongs(); }
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
    el("btn-tunnel-start").addEventListener("click", startTunnel);
    el("btn-upload-songs").addEventListener("click", uploadSongs);
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
