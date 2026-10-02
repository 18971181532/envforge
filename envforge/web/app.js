// EnvForge Dashboard — app.js
(function () {
  "use strict";

  const state = {
    profiles: [],
    selected: null,
    graph: null,
    graphOffset: { x: 0, y: 0 },
    graphScale: 1,
    dragging: false,
    dragStart: null,
    compareA: null,
    compareB: null,
  };

  const $ = (id) => document.getElementById(id);
  const api = async (path) => {
    const res = await fetch(path);
    return res.json();
  };

  // --- Init ---
  async function init() {
    setupTabs();
    setupButtons();
    setupCanvas();
    await loadProfiles();
  }

  // --- Tabs ---
  function setupTabs() {
    document.querySelectorAll(".tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
        document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));
        tab.classList.add("active");
        $("tab-" + tab.dataset.tab).classList.add("active");
        if (tab.dataset.tab === "graph" && state.selected) renderGraph();
      });
    });
  }

  // --- Buttons ---
  function setupButtons() {
    $("btn-refresh").addEventListener("click", loadProfiles);
    $("btn-capture").addEventListener("click", captureProfile);
    $("btn-drift").addEventListener("click", runDrift);
    $("btn-compare").addEventListener("click", openCompareModal);
    $("btn-bootstrap").addEventListener("click", openBootstrapModal);
    $("btn-delete").addEventListener("click", deleteProfile);
    $("modal-cancel").addEventListener("click", closeModal);
  }

  // --- Profiles ---
  async function loadProfiles() {
    state.profiles = await api("/api/profiles");
    renderProfileList();
    if (state.selected) {
      const stillExists = state.profiles.find((p) => p.name === state.selected);
      if (!stillExists) {
        state.selected = null;
        updateActionButtons();
      } else {
        selectProfile(state.selected);
      }
    }
  }

  function renderProfileList() {
    const list = $("profile-list");
    if (state.profiles.length === 0) {
      list.innerHTML = '<p style="color:var(--text-dim);font-size:12px;padding:8px;">No profiles yet. Click + Capture to create one.</p>';
      return;
    }
    list.innerHTML = state.profiles
      .map(
        (p) => `
      <div class="profile-item ${p.name === state.selected ? "selected" : ""}" data-name="${p.name}">
        <div class="pname">${escapeHtml(p.name)}</div>
        <div class="pmeta">${escapeHtml(p.os)} · ${p.tools} tools · ${p.packages} pkgs</div>
      </div>`
      )
      .join("");
    list.querySelectorAll(".profile-item").forEach((el) => {
      el.addEventListener("click", () => selectProfile(el.dataset.name));
    });
  }

  async function selectProfile(name) {
    state.selected = name;
    renderProfileList();
    updateActionButtons();
    const profile = await api("/api/profile?name=" + encodeURIComponent(name));
    renderDetail(profile);
    const graph = await api("/api/graph?name=" + encodeURIComponent(name));
    state.graph = graph;
    $("graph-stats").textContent = `${graph.stats.total_nodes} nodes · ${graph.stats.total_edges} edges · ${graph.stats.tools} tools · ${graph.stats.packages} packages`;
    if ($("tab-graph").classList.contains("active")) renderGraph();
  }

  function updateActionButtons() {
    const has = !!state.selected;
    $("btn-drift").disabled = !has;
    $("btn-compare").disabled = state.profiles.length < 2;
    $("btn-bootstrap").disabled = !has;
    $("btn-delete").disabled = !has;
  }

  async function captureProfile() {
    const name = prompt("Enter profile name:", "capture_" + Date.now());
    if (!name) return;
    $("btn-capture").textContent = "Capturing...";
    $("btn-capture").disabled = true;
    try {
      const res = await fetch("/api/capture", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      });
      await res.json();
      await loadProfiles();
      await selectProfile(name);
    } finally {
      $("btn-capture").textContent = "+ Capture";
      $("btn-capture").disabled = false;
    }
  }

  async function deleteProfile() {
    if (!state.selected) return;
    if (!confirm(`Delete profile "${state.selected}"?`)) return;
    await fetch("/api/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: state.selected }),
    });
    state.selected = null;
    await loadProfiles();
    $("detail-content").innerHTML = '<p class="placeholder">Select a profile to view details.</p>';
    state.graph = null;
    renderGraph();
  }

  // --- Detail ---
  function renderDetail(profile) {
    const s = profile.os || {};
    let html = `
      <div class="detail-section">
        <h4>Overview</h4>
        <div class="detail-grid">
          <div class="detail-row"><span class="key">Name</span><span class="val">${escapeHtml(profile.name)}</span></div>
          <div class="detail-row"><span class="key">Captured</span><span class="val">${escapeHtml(profile.captured_at_iso || "")}</span></div>
          <div class="detail-row"><span class="key">OS</span><span class="val">${escapeHtml(s.system || "?")} ${escapeHtml(s.release || "")}</span></div>
          <div class="detail-row"><span class="key">Python</span><span class="val">${escapeHtml(s.python_version || "?")}</span></div>
          <div class="detail-row"><span class="key">Shell</span><span class="val">${escapeHtml(profile.shell?.name || "?")} ${escapeHtml(profile.shell?.version || "")}</span></div>
          <div class="detail-row"><span class="key">Machine</span><span class="val">${escapeHtml(s.machine || "?")}</span></div>
        </div>
      </div>`;

    // Tools
    const tools = profile.tools || {};
    const toolNames = Object.keys(tools).sort();
    html += `<div class="detail-section"><h4>Tools (${toolNames.length})</h4><div class="detail-grid">`;
    toolNames.forEach((name) => {
      const t = tools[name];
      html += `<div class="tool-card">
        <div class="tname">${escapeHtml(name)}</div>
        <div class="tversion">v${escapeHtml(t.version || "?")}</div>
        <div class="tpath">${escapeHtml(t.path || "")}</div>
      </div>`;
    });
    html += `</div></div>`;

    // Packages
    const packages = profile.packages || {};
    Object.keys(packages).sort().forEach((mgr) => {
      const pkgs = packages[mgr];
      html += `<div class="detail-section"><h4>Packages — ${escapeHtml(mgr)} (${pkgs.length})</h4><div class="detail-grid">`;
      pkgs.slice(0, 40).forEach((p) => {
        html += `<div class="detail-row"><span class="key">${escapeHtml(p.name || "?")}</span><span class="val">${escapeHtml(p.version || "?")}</span></div>`;
      });
      if (pkgs.length > 40) html += `<div class="detail-row"><span class="key">... and ${pkgs.length - 40} more</span><span class="val"></span></div>`;
      html += `</div></div>`;
    });

    // Env vars
    const envVars = profile.env_vars || {};
    const envKeys = Object.keys(envVars).sort();
    html += `<div class="detail-section"><h4>Environment Variables (${envKeys.length})</h4><div class="detail-grid">`;
    envKeys.forEach((key) => {
      const val = envVars[key];
      const display = val.length > 60 ? val.substring(0, 60) + "..." : val;
      html += `<div class="detail-row"><span class="key">${escapeHtml(key)}</span><span class="val" title="${escapeHtml(val)}">${escapeHtml(display)}</span></div>`;
    });
    html += `</div></div>`;

    // Git config
    const gitConfig = profile.git_config || {};
    const gitKeys = Object.keys(gitConfig).sort();
    if (gitKeys.length) {
      html += `<div class="detail-section"><h4>Git Config (${gitKeys.length})</h4><div class="detail-grid">`;
      gitKeys.forEach((key) => {
        html += `<div class="detail-row"><span class="key">${escapeHtml(key)}</span><span class="val">${escapeHtml(gitConfig[key])}</span></div>`;
      });
      html += `</div></div>`;
    }

    $("detail-content").innerHTML = html;
  }

  // --- Drift ---
  async function runDrift() {
    if (!state.selected) return;
    document.querySelector('.tab[data-tab="drift"]').click();
    $("drift-content").innerHTML = '<p class="placeholder">Checking drift...</p>';
    const drift = await api("/api/drift?name=" + encodeURIComponent(state.selected));
    renderDrift(drift);
  }

  function renderDrift(drift) {
    const s = drift.summary;
    let html = `
      <div class="drift-summary">
        <div class="drift-badge"><div class="num">${s.total_changes}</div><div class="label">Total</div></div>
        <div class="drift-badge added"><div class="num">${s.added || 0}</div><div class="label">Added</div></div>
        <div class="drift-badge removed"><div class="num">${s.removed || 0}</div><div class="label">Removed</div></div>
        <div class="drift-badge modified"><div class="num">${s.modified || 0}</div><div class="label">Modified</div></div>
        <div class="drift-badge version"><div class="num">${s.version_changed || 0}</div><div class="label">Version Δ</div></div>
      </div>`;

    if (s.total_changes === 0) {
      html += '<p style="color:var(--green);text-align:center;padding:40px;">✓ No drift detected — environment matches profile.</p>';
      $("drift-content").innerHTML = html;
      return;
    }

    // Tools
    if (drift.tools && drift.tools.length) {
      html += `<div class="drift-category"><h4>Tools (${drift.tools.length})</h4>`;
      drift.tools.forEach((c) => {
        if (c.type === "added") html += `<div class="drift-item added"><span class="icon">+</span>${c.name} ${c.version}</div>`;
        else if (c.type === "removed") html += `<div class="drift-item removed"><span class="icon">−</span>${c.name} ${c.version}</div>`;
        else if (c.type === "version_changed") html += `<div class="drift-item version"><span class="icon">↻</span>${c.name}: ${c.captured_version} → ${c.current_version}</div>`;
      });
      html += `</div>`;
    }

    // Packages
    Object.keys(drift.packages || {}).forEach((mgr) => {
      const changes = drift.packages[mgr];
      if (changes.length) {
        html += `<div class="drift-category"><h4>Packages — ${mgr} (${changes.length})</h4>`;
        changes.forEach((c) => {
          if (c.type === "added") html += `<div class="drift-item added"><span class="icon">+</span>${c.name} ${c.current?.version || ""}</div>`;
          else if (c.type === "removed") html += `<div class="drift-item removed"><span class="icon">−</span>${c.name} ${c.captured?.version || ""}</div>`;
          else if (c.type === "version_changed") html += `<div class="drift-item version"><span class="icon">↻</span>${c.name}: ${c.captured_version} → ${c.current_version}</div>`;
        });
        html += `</div>`;
      }
    });

    // Env vars
    if (drift.env_vars && drift.env_vars.length) {
      html += `<div class="drift-category"><h4>Environment Variables (${drift.env_vars.length})</h4>`;
      drift.env_vars.slice(0, 30).forEach((c) => {
        const path = c.path.replace("env.", "");
        if (c.type === "added") html += `<div class="drift-item added"><span class="icon">+</span>${path}</div>`;
        else if (c.type === "removed") html += `<div class="drift-item removed"><span class="icon">−</span>${path}</div>`;
        else if (c.type === "modified") html += `<div class="drift-item modified"><span class="icon">~</span>${path}</div>`;
      });
      if (drift.env_vars.length > 30) html += `<div class="drift-item modified"><span class="icon">…</span>and ${drift.env_vars.length - 30} more</div>`;
      html += `</div>`;
    }

    $("drift-content").innerHTML = html;
  }

  // --- Compare ---
  function openCompareModal() {
    if (state.profiles.length < 2) return;
    const options = state.profiles.map((p) => `<option value="${escapeHtml(p.name)}">${escapeHtml(p.name)}</option>`).join("");
    $("modal-title").textContent = "Compare Profiles";
    $("modal-body").innerHTML = `
      <div class="compare-selector">
        <label>A: <select id="cmp-a">${options}</select></label>
        <span>vs</span>
        <label>B: <select id="cmp-b">${options}</select></label>
      </div>`;
    if (state.profiles.length >= 2) {
      $("cmp-a").value = state.profiles[0].name;
      $("cmp-b").value = state.profiles[1].name;
    }
    $("modal-confirm").textContent = "Compare";
    $("modal-confirm").onclick = async () => {
      state.compareA = $("cmp-a").value;
      state.compareB = $("cmp-b").value;
      closeModal();
      document.querySelector('.tab[data-tab="compare"]').click();
      await runCompare();
    };
    $("modal").classList.remove("hidden");
  }

  async function runCompare() {
    if (!state.compareA || !state.compareB) return;
    $("compare-content").innerHTML = '<p class="placeholder">Comparing...</p>';
    const diff = await api(`/api/compare?a=${encodeURIComponent(state.compareA)}&b=${encodeURIComponent(state.compareB)}`);
    renderCompare(diff);
  }

  function renderCompare(diff) {
    const s = diff.summary;
    let html = `
      <div class="compare-summary">
        <div class="drift-badge"><div class="num">${s.total_differences}</div><div class="label">Differences</div></div>
      </div>`;

    if (s.total_differences === 0) {
      html += '<p style="color:var(--green);text-align:center;padding:40px;">✓ Profiles are identical.</p>';
      $("compare-content").innerHTML = html;
      return;
    }

    if (diff.tools && diff.tools.length) {
      html += `<div class="drift-category"><h4>Tools (${diff.tools.length})</h4>`;
      diff.tools.forEach((d) => {
        if (d.type === "only_in_a") html += `<div class="drift-item added"><span class="icon">A</span>${d.name} ${d.version_a} (only in ${diff.a})</div>`;
        else if (d.type === "only_in_b") html += `<div class="drift-item removed"><span class="icon">B</span>${d.name} ${d.version_b} (only in ${diff.b})</div>`;
        else if (d.type === "version_different") html += `<div class="drift-item version"><span class="icon">↻</span>${d.name}: ${d.version_a} (${diff.a}) vs ${d.version_b} (${diff.b})</div>`;
      });
      html += `</div>`;
    }

    Object.keys(diff.packages || {}).forEach((mgr) => {
      const changes = diff.packages[mgr];
      if (changes.length) {
        html += `<div class="drift-category"><h4>Packages — ${mgr} (${changes.length})</h4>`;
        changes.forEach((c) => {
          if (c.type === "added") html += `<div class="drift-item added"><span class="icon">A</span>${c.name} (only in ${diff.a})</div>`;
          else if (c.type === "removed") html += `<div class="drift-item removed"><span class="icon">B</span>${c.name} (only in ${diff.b})</div>`;
          else if (c.type === "version_changed") html += `<div class="drift-item version"><span class="icon">↻</span>${c.name}: ${c.captured_version} vs ${c.current_version}</div>`;
        });
        html += `</div>`;
      }
    });

    $("compare-content").innerHTML = html;
  }

  // --- Bootstrap ---
  function openBootstrapModal() {
    if (!state.selected) return;
    $("modal-title").textContent = "Generate Bootstrap Script";
    $("modal-body").innerHTML = `
      <p style="margin-bottom:12px;font-size:13px;">Generate a script to recreate "${escapeHtml(state.selected)}" on a new machine.</p>
      <label style="font-size:13px;">Shell:
        <select id="boot-shell" style="margin-left:8px;padding:4px 8px;background:var(--bg);border:1px solid var(--border);border-radius:4px;color:var(--text);">
          <option value="auto">Auto-detect</option>
          <option value="bash">Bash</option>
          <option value="powershell">PowerShell</option>
          <option value="cmd">CMD</option>
        </select>
      </label>`;
    $("modal-confirm").textContent = "Generate";
    $("modal-confirm").onclick = () => {
      const shell = $("boot-shell").value;
      window.location.href = `/api/profile?name=${encodeURIComponent(state.selected)}`;
      closeModal();
      alert("Bootstrap generation is available via CLI: envforge bootstrap " + state.selected);
    };
    $("modal").classList.remove("hidden");
  }

  function closeModal() {
    $("modal").classList.add("hidden");
  }

  // --- Canvas Graph ---
  function setupCanvas() {
    const canvas = $("graph-canvas");
    canvas.addEventListener("mousedown", (e) => {
      state.dragging = true;
      state.dragStart = { x: e.clientX - state.graphOffset.x, y: e.clientY - state.graphOffset.y };
    });
    window.addEventListener("mousemove", (e) => {
      if (!state.dragging) return;
      state.graphOffset.x = e.clientX - state.dragStart.x;
      state.graphOffset.y = e.clientY - state.dragStart.y;
      renderGraph();
    });
    window.addEventListener("mouseup", () => { state.dragging = false; });
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      state.graphScale = Math.max(0.3, Math.min(3, state.graphScale * delta));
      renderGraph();
    });
  }

  function renderGraph() {
    const canvas = $("graph-canvas");
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, rect.width, rect.height);

    if (!state.graph || !state.graph.nodes) {
      ctx.fillStyle = "#8b949e";
      ctx.font = "14px sans-serif";
      ctx.textAlign = "center";
      ctx.fillText("Select a profile to view environment graph", rect.width / 2, rect.height / 2);
      return;
    }

    const nodes = state.graph.nodes;
    const edges = state.graph.edges;

    // Layout: radial/tree layout
    const layout = computeLayout(nodes, edges, rect.width, rect.height);

    ctx.save();
    ctx.translate(rect.width / 2 + state.graphOffset.x, rect.height / 2 + state.graphOffset.y);
    ctx.scale(state.graphScale, state.graphScale);

    // Draw edges
    ctx.strokeStyle = "#30363d";
    ctx.lineWidth = 1;
    edges.forEach((edge) => {
      const from = layout[edge.source];
      const to = layout[edge.target];
      if (!from || !to) return;
      ctx.beginPath();
      ctx.moveTo(from.x, from.y);
      const mx = (from.x + to.x) / 2;
      const my = (from.y + to.y) / 2;
      ctx.quadraticCurveTo(mx, from.y, mx, my);
      ctx.quadraticCurveTo(mx, to.y, to.x, to.y);
      ctx.stroke();
    });

    // Draw nodes
    const colors = {
      os: "#bc8cff", shell: "#39c5cf", tool: "#58a6ff",
      manager: "#d29922", package: "#3fb950",
    };
    nodes.forEach((node) => {
      const pos = layout[node.id];
      if (!pos) return;
      const color = colors[node.type] || "#8b949e";
      const radius = node.type === "package" ? 4 : node.type === "os" ? 14 : 8;

      // Glow
      ctx.shadowColor = color;
      ctx.shadowBlur = 8;

      ctx.beginPath();
      ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
      ctx.shadowBlur = 0;

      // Label
      if (node.type !== "package" || radius > 3) {
        ctx.fillStyle = "#c9d1d9";
        ctx.font = `${node.type === "package" ? 9 : 11}px sans-serif`;
        ctx.textAlign = "center";
        const label = node.label.length > 22 ? node.label.substring(0, 20) + ".." : node.label;
        ctx.fillText(label, pos.x, pos.y - radius - 4);
      }
    });

    ctx.restore();
  }

  function computeLayout(nodes, edges, width, height) {
    // Simple layered layout based on node type and edges
    const layout = {};
    const byType = { os: [], shell: [], tool: [], manager: [], package: [] };
    nodes.forEach((n) => {
      if (byType[n.type]) byType[n.type].push(n);
      else byType.tool.push(n);
    });

    const layers = ["os", "shell", "tool", "manager", "package"];
    const layerX = { os: -width * 0.35, shell: -width * 0.18, tool: 0, manager: width * 0.2, package: width * 0.38 };

    layers.forEach((type) => {
      const list = byType[type];
      const count = list.length;
      const spacing = Math.min(40, (height - 80) / Math.max(count, 1));
      const startY = -(count - 1) * spacing / 2;
      list.forEach((node, i) => {
        layout[node.id] = { x: layerX[type], y: startY + i * spacing };
      });
    });

    return layout;
  }

  // --- Utils ---
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = String(str || "");
    return div.innerHTML;
  }

  // Start
  init();
})();
