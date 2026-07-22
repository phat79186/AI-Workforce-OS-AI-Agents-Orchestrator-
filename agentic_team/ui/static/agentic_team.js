(() => {
  const state = {
    clientId:
      typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
        ? crypto.randomUUID()
        : `agentic-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
    status: "idle",
    teamConfig: null,
    turns: [],
    communications: [],
    logs: [],
    selectedTurnKey: "",
    lastTask: "",
    output: "",
    configData: {
      agents: {},
      workflows: {},
      settings: {},
      agentic_team: { roles: {} },
    },
    availableAgents: [],
    teamValidation: { valid: true, available_agents: [], missing_roles: [] },
  };

  const refs = {
    statusPill: document.getElementById("status-pill"),
    socketPill: document.getElementById("socket-pill"),
    taskInput: document.getElementById("task-input"),
    maxTurns: document.getElementById("max-turns"),
    executeBtn: document.getElementById("execute-btn"),
    followupBtn: document.getElementById("followup-btn"),
    clearBtn: document.getElementById("clear-btn"),
    metaLead: document.getElementById("meta-lead"),
    metaRoles: document.getElementById("meta-roles"),
    metaTurns: document.getElementById("meta-turns"),
    statRoute: document.getElementById("stat-route"),
    statAction: document.getElementById("stat-action"),
    statResult: document.getElementById("stat-result"),
    graph: document.getElementById("graph"),
    timeline: document.getElementById("timeline"),
    liveComms: document.getElementById("live-comms"),
    finalOutput: document.getElementById("final-output"),
    logs: document.getElementById("logs"),
    configPath: document.getElementById("config-path"),
    configForm: document.getElementById("config-form"),
    configStatus: document.getElementById("config-status"),
    reloadConfigBtn: document.getElementById("reload-config-btn"),
    saveConfigBtn: document.getElementById("save-config-btn"),
  };

  const ROLE_COLORS = [
    "#1d4ed8",
    "#0891b2",
    "#15803d",
    "#9333ea",
    "#b45309",
    "#be123c",
    "#0f766e",
  ];
  const AGENT_TYPE_OPTIONS = [
    "cli",
    "ollama",
    "llamacpp",
    "localai",
    "text-generation-webui",
    "openai-compatible",
  ];
  const AGENT_ROLE_OPTIONS = [
    "implementation",
    "review",
    "refinement",
    "suggestions",
    "docs",
    "qa",
    "devops",
  ];
  const WORKFLOW_TASK_OPTIONS = [
    "implement",
    "review",
    "refine",
    "document",
    "suggestions",
    "test",
  ];
  const WORKFLOW_ROLE_OPTIONS = [
    "implementer",
    "reviewer",
    "refiner",
    "writer",
    "tester",
  ];
  const LOG_LEVEL_OPTIONS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

  const normalizeRole = (value) =>
    String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[-\s]+/g, "_");

  const titleCase = (value) =>
    String(value || "")
      .replace(/_/g, " ")
      .replace(/\b\w/g, (c) => c.toUpperCase());

  const normalizeKey = (value) =>
    String(value || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9_-]+/g, "-")
      .replace(/-+/g, "-")
      .replace(/^-|-$/g, "");

  const deepClone = (value) => JSON.parse(JSON.stringify(value));

  const parseCsv = (value) =>
    String(value || "")
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

  const toCsv = (value) => (Array.isArray(value) ? value.join(", ") : "");

  const trim = (value, max = 120) =>
    value.length > max ? `${value.slice(0, max - 1)}...` : value;

  const esc = (value) =>
    String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");

  const optionsWithCurrent = (options, current) => {
    const normalizedCurrent = String(current || "").trim();
    const merged = [...options];
    if (normalizedCurrent && !merged.includes(normalizedCurrent))
      merged.push(normalizedCurrent);
    return merged;
  };

  const renderSelectOptions = (options, current, allowNone = true) => {
    const opts = optionsWithCurrent(options, current)
      .map(
        (opt) =>
          `<option value="${esc(opt)}" ${String(opt) === String(current || "") ? "selected" : ""}>${esc(opt)}</option>`,
      )
      .join("");
    const none = allowNone
      ? `<option value="" ${String(current || "") === "" ? "selected" : ""}>(none)</option>`
      : "";
    return `${none}${opts}`;
  };

  const normalizeConfigData = (value) => {
    const config = value && typeof value === "object" ? deepClone(value) : {};
    if (!config.agents || typeof config.agents !== "object") config.agents = {};
    if (!config.workflows || typeof config.workflows !== "object")
      config.workflows = {};
    if (!config.settings || typeof config.settings !== "object")
      config.settings = {};
    if (!config.settings.offline || typeof config.settings.offline !== "object")
      config.settings.offline = {};
    if (
      !config.settings.fallback ||
      typeof config.settings.fallback !== "object"
    )
      config.settings.fallback = {};
    if (
      !config.settings.fallback.map ||
      typeof config.settings.fallback.map !== "object"
    )
      config.settings.fallback.map = {};
    if (!config.agentic_team || typeof config.agentic_team !== "object")
      config.agentic_team = {};
    if (
      !config.agentic_team.roles ||
      typeof config.agentic_team.roles !== "object"
    )
      config.agentic_team.roles = {};

    Object.entries(config.workflows).forEach(([name, workflow]) => {
      if (Array.isArray(workflow)) {
        config.workflows[name] = {
          description: "",
          offline: false,
          steps: workflow,
        };
      } else if (!workflow || typeof workflow !== "object") {
        config.workflows[name] = { description: "", offline: false, steps: [] };
      } else if (!Array.isArray(workflow.steps)) {
        workflow.steps = [];
      }
    });

    return config;
  };

  const applyTeamDefaults = () => {
    state.configData = normalizeConfigData(state.configData);
    const teamDefaults = state.teamConfig || {};
    const defaultRoles = teamDefaults.roles || {};
    const targetTeam = state.configData.agentic_team || {};
    if (!targetTeam.roles || typeof targetTeam.roles !== "object")
      targetTeam.roles = {};

    if (!targetTeam.lead_role && teamDefaults.lead_role) {
      targetTeam.lead_role = teamDefaults.lead_role;
    }
    if (
      (!targetTeam.max_turns || Number(targetTeam.max_turns) <= 0) &&
      teamDefaults.max_turns
    ) {
      targetTeam.max_turns = Number(teamDefaults.max_turns);
    }

    Object.entries(defaultRoles).forEach(([roleName, roleSpec]) => {
      const existing = targetTeam.roles[roleName];
      const merged = existing && typeof existing === "object" ? existing : {};
      if (!merged.title && roleSpec?.title) merged.title = roleSpec.title;
      if (!merged.agent && roleSpec?.agent) merged.agent = roleSpec.agent;
      if (!merged.responsibilities && roleSpec?.responsibilities) {
        merged.responsibilities = roleSpec.responsibilities;
      }
      targetTeam.roles[roleName] = merged;
    });

    state.configData.agentic_team = targetTeam;
  };

  const turnKey = (turn) =>
    `${turn.turn || ""}|${normalizeRole(turn.from_role)}|${normalizeRole(turn.to_role)}|${turn.action || ""}|${String(turn.message || "").slice(0, 80)}`;

  const communicationKey = (edge) =>
    `${edge.turn || ""}|${normalizeRole(edge.from_role)}|${normalizeRole(edge.to_role)}|${edge.action || ""}|${String(edge.message || "").slice(0, 80)}`;

  const toCommunication = (payload = {}) => ({
    key: communicationKey(payload),
    turn: payload.turn || null,
    action: payload.action || "message",
    from_role: normalizeRole(payload.from_role),
    to_role: normalizeRole(payload.to_role),
    from_agent: payload.from_agent || payload.agent || "",
    to_agent: payload.to_agent || "",
    message: String(payload.message || ""),
    success: payload.success !== false,
    timestamp: payload.timestamp || new Date().toISOString(),
  });

  const addLog = (message, level = "info") => {
    if (!message) return;
    state.logs.push({
      level,
      message: String(message),
      timestamp: new Date().toISOString(),
    });
    if (state.logs.length > 500) state.logs.splice(0, state.logs.length - 500);
    renderLogs();
  };

  const setStatus = (status) => {
    state.status = status;
    refs.statusPill.textContent = titleCase(status);
    refs.statusPill.className = `pill status-${status}`;
    refs.executeBtn.disabled = status === "running";
    refs.followupBtn.disabled = status === "running" || !state.lastTask;
  };

  const setSocketConnected = (connected) => {
    refs.socketPill.textContent = connected ? "Connected" : "Disconnected";
    refs.socketPill.className = `pill ${connected ? "socket-online" : "socket-offline"}`;
  };

  const upsertTurn = (turn) => {
    const key = turnKey(turn);
    const existingIdx = state.turns.findIndex((item) => turnKey(item) === key);
    const enriched = {
      ...turn,
      key,
      timestamp: turn.timestamp || new Date().toISOString(),
    };
    if (existingIdx >= 0) state.turns[existingIdx] = enriched;
    else {
      state.turns.push(enriched);
      state.turns.sort((a, b) => Number(a.turn || 0) - Number(b.turn || 0));
    }
    upsertCommunication(enriched);
    if (!state.selectedTurnKey) state.selectedTurnKey = key;
  };

  const upsertCommunication = (communicationPayload) => {
    const entry = toCommunication(communicationPayload || {});
    if (!entry.from_role || !entry.to_role || entry.to_role === "user") return;
    const idx = state.communications.findIndex(
      (item) => item.key === entry.key,
    );
    if (idx >= 0) {
      state.communications[idx] = entry;
    } else {
      state.communications.push(entry);
      state.communications.sort(
        (a, b) => Number(a.turn || 0) - Number(b.turn || 0),
      );
    }
  };

  const rebuildCommunicationsFromTurns = () => {
    state.communications = [];
    state.turns.forEach((turn) => upsertCommunication(turn));
  };

  const loadCommunications = (entries) => {
    state.communications = [];
    (Array.isArray(entries) ? entries : []).forEach((entry) =>
      upsertCommunication(entry),
    );
  };

  const splitLongToken = (token, maxChars) => {
    const safeMax = Math.max(1, Number(maxChars) || 1);
    const chunks = [];
    const source = String(token || "");
    for (let i = 0; i < source.length; i += safeMax) {
      chunks.push(source.slice(i, i + safeMax));
    }
    return chunks.length ? chunks : [""];
  };

  const wrapTextLines = (text, maxChars = 16) => {
    const safeMax = Math.max(1, Number(maxChars) || 1);
    const words = String(text || "")
      .split(/\s+/)
      .filter(Boolean);
    if (!words.length) return [""];
    const lines = [];
    let current = "";
    words.forEach((word) => {
      if (word.length > safeMax) {
        if (current) {
          lines.push(current);
          current = "";
        }
        splitLongToken(word, safeMax).forEach((chunk) => lines.push(chunk));
        return;
      }
      const candidate = current ? `${current} ${word}` : word;
      if (candidate.length <= safeMax) {
        current = candidate;
      } else {
        if (current) lines.push(current);
        current = word;
      }
    });
    if (current) lines.push(current);
    return lines.length ? lines : [""];
  };

  const buildNodeLabelLayout = (node, coreRadius) => {
    const titleText = String(node.title || titleCase(node.role || ""));
    const agentText = `Agent: ${String(node.agent || "unbound")}`;
    const maxWidth = coreRadius * 2 - 14;
    const maxHeight = coreRadius * 2 - 14;

    for (let fontSize = 12; fontSize >= 2; fontSize -= 0.5) {
      const charCap = Math.max(2, Math.floor(maxWidth / (fontSize * 0.62)));
      const lines = [
        ...wrapTextLines(titleText, charCap).map((text) => ({
          text,
          kind: "title",
        })),
        ...wrapTextLines(agentText, charCap).map((text) => ({
          text,
          kind: "agent",
        })),
      ];
      const maxChars = Math.max(
        1,
        ...lines.map((line) => String(line.text || "").length),
      );
      const estimatedWidth = maxChars * fontSize * 0.62;
      const lineHeight = fontSize * 1.16;
      const totalHeight = lines.length * lineHeight;
      if (estimatedWidth <= maxWidth && totalHeight <= maxHeight) {
        return { lines, fontSize, lineHeight, totalHeight };
      }
    }

    const fallbackFont = 2;
    const fallbackCap = Math.max(
      2,
      Math.floor(maxWidth / (fallbackFont * 0.62)),
    );
    const fallbackLines = [
      ...wrapTextLines(titleText, fallbackCap).map((text) => ({
        text,
        kind: "title",
      })),
      ...wrapTextLines(agentText, fallbackCap).map((text) => ({
        text,
        kind: "agent",
      })),
    ];
    const fallbackLineHeight = fallbackFont * 1.16;
    return {
      lines: fallbackLines,
      fontSize: fallbackFont,
      lineHeight: fallbackLineHeight,
      totalHeight: fallbackLines.length * fallbackLineHeight,
    };
  };

  const renderMeta = () => {
    const leadRole = normalizeRole(state.teamConfig?.lead_role || "");
    const roleCount = Object.keys(state.teamConfig?.roles || {}).length;
    refs.metaLead.textContent = leadRole ? titleCase(leadRole) : "-";
    refs.metaRoles.textContent = String(roleCount);
    refs.metaTurns.textContent = String(state.turns.length);

    const latest = state.turns[state.turns.length - 1];
    refs.statRoute.textContent = latest
      ? `${titleCase(normalizeRole(latest.from_role))} -> ${titleCase(normalizeRole(latest.to_role))}`
      : "-";
    refs.statAction.textContent = latest?.action || "-";
    refs.statResult.textContent = titleCase(state.status);
  };

  const roleMapFromState = () => {
    const mapped = {};
    const cfgRoles = state.teamConfig?.roles || {};
    Object.entries(cfgRoles).forEach(([role, spec]) => {
      const key = normalizeRole(role);
      mapped[key] = {
        role: key,
        title: spec?.title || titleCase(key),
        agent: spec?.agent || "",
      };
    });

    state.turns.forEach((turn) => {
      [turn.from_role, turn.to_role].forEach((raw) => {
        const key = normalizeRole(raw);
        if (!key || key === "user") return;
        if (!mapped[key])
          mapped[key] = { role: key, title: titleCase(key), agent: "" };
      });
    });

    state.communications.forEach((edge) => {
      [edge.from_role, edge.to_role].forEach((raw) => {
        const key = normalizeRole(raw);
        if (!key || key === "user") return;
        if (!mapped[key])
          mapped[key] = { role: key, title: titleCase(key), agent: "" };
      });
      const fromRole = normalizeRole(edge.from_role);
      const toRole = normalizeRole(edge.to_role);
      if (
        fromRole &&
        mapped[fromRole] &&
        !mapped[fromRole].agent &&
        edge.from_agent
      ) {
        mapped[fromRole].agent = String(edge.from_agent);
      }
      if (toRole && mapped[toRole] && !mapped[toRole].agent && edge.to_agent) {
        mapped[toRole].agent = String(edge.to_agent);
      }
    });

    return mapped;
  };

  const renderGraph = () => {
    const svg = refs.graph;
    svg.innerHTML = "";
    const width = 980;
    const height = 520;
    const ringRadius = 80;
    const coreRadius = 64;

    const roles = Object.values(roleMapFromState()).sort((a, b) =>
      a.role.localeCompare(b.role),
    );
    if (!roles.length) {
      const text = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text",
      );
      text.setAttribute("x", "50%");
      text.setAttribute("y", "50%");
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", "#334155");
      text.textContent = "No communication yet";
      svg.appendChild(text);
      return;
    }

    const centerX = width / 2;
    const centerY = height / 2;
    const baseRadius = Math.max(145, Math.min(width, height) * 0.3);
    const requiredRadius =
      (roles.length * (ringRadius * 2 + 18)) / (2 * Math.PI);
    const maxRadius = Math.min(
      width / 2 - ringRadius - 18,
      height / 2 - ringRadius - 18,
    );
    const radius = Math.min(maxRadius, Math.max(baseRadius, requiredRadius));
    const nodeByRole = {};

    roles.forEach((role, idx) => {
      const angle = ((Math.PI * 2) / roles.length) * idx - Math.PI / 2;
      const x = centerX + Math.cos(angle) * radius;
      const y = centerY + Math.sin(angle) * radius;
      nodeByRole[role.role] = {
        ...role,
        x,
        y,
        color: ROLE_COLORS[idx % ROLE_COLORS.length],
      };
    });

    const defs = document.createElementNS("http://www.w3.org/2000/svg", "defs");
    const marker = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "marker",
    );
    marker.setAttribute("id", "edge-arrow");
    marker.setAttribute("viewBox", "0 0 10 10");
    marker.setAttribute("refX", "9");
    marker.setAttribute("refY", "5");
    marker.setAttribute("markerWidth", "6");
    marker.setAttribute("markerHeight", "6");
    marker.setAttribute("orient", "auto-start-reverse");
    const markerPath = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "path",
    );
    markerPath.setAttribute("d", "M 0 0 L 10 5 L 0 10 z");
    markerPath.setAttribute("fill", "#334155");
    marker.appendChild(markerPath);
    defs.appendChild(marker);
    svg.appendChild(defs);

    const groupedEdges = new Map();
    state.communications.forEach((edge) => {
      const fromRole = normalizeRole(edge.from_role);
      const toRole = normalizeRole(edge.to_role);
      if (!fromRole || !toRole || !nodeByRole[fromRole] || !nodeByRole[toRole])
        return;
      const key = `${fromRole}->${toRole}`;
      const existing = groupedEdges.get(key);
      if (existing) {
        existing.count += 1;
        existing.latest = edge;
      } else {
        groupedEdges.set(key, {
          key,
          fromRole,
          toRole,
          count: 1,
          latest: edge,
        });
      }
    });

    const selectedTurn = state.turns.find(
      (turn) => turn.key === state.selectedTurnKey,
    );
    const selectedEdgeKey = selectedTurn
      ? `${normalizeRole(selectedTurn.from_role)}->${normalizeRole(selectedTurn.to_role)}`
      : "";
    const latestEdgeKey =
      state.communications.length > 0
        ? `${normalizeRole(state.communications[state.communications.length - 1].from_role)}->${normalizeRole(
            state.communications[state.communications.length - 1].to_role,
          )}`
        : "";

    Array.from(groupedEdges.values()).forEach((edgeData) => {
      const from = nodeByRole[edgeData.fromRole];
      const to = nodeByRole[edgeData.toRole];
      if (!from || !to) return;

      const edge = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "path",
      );
      edge.classList.add("edge");
      edge.setAttribute("stroke", from.color);
      edge.setAttribute("marker-end", "url(#edge-arrow)");
      edge.dataset.edgeKey = edgeData.key;

      let labelX = (from.x + to.x) / 2;
      let labelY = (from.y + to.y) / 2;

      if (edgeData.fromRole === edgeData.toRole) {
        const loopR = coreRadius + 26;
        const startX = from.x + coreRadius - 8;
        const startY = from.y - 4;
        const cp1X = from.x + loopR;
        const cp1Y = from.y - loopR;
        const cp2X = from.x - loopR;
        const cp2Y = from.y - loopR;
        const endX = from.x - 10;
        const endY = from.y - (coreRadius - 12);
        edge.setAttribute(
          "d",
          `M ${startX} ${startY} C ${cp1X} ${cp1Y} ${cp2X} ${cp2Y} ${endX} ${endY}`,
        );
        labelX = from.x;
        labelY = from.y - loopR - 10;
      } else {
        const mx = from.x + (to.x - from.x) * 0.5;
        const my = from.y + (to.y - from.y) * 0.5 - 35;
        edge.setAttribute(
          "d",
          `M ${from.x} ${from.y} Q ${mx} ${my} ${to.x} ${to.y}`,
        );
        labelX = mx;
        labelY = my - 8;
      }

      if (edgeData.key === latestEdgeKey && state.status === "running")
        edge.classList.add("edge-latest");
      if (edgeData.key === selectedEdgeKey) edge.classList.add("edge-selected");
      svg.appendChild(edge);

      const label = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text",
      );
      label.setAttribute("class", "edge-label");
      label.setAttribute("x", `${labelX}`);
      label.setAttribute("y", `${labelY}`);
      label.setAttribute("text-anchor", "middle");
      label.textContent = `${edgeData.count}x`;
      svg.appendChild(label);
    });

    Object.values(nodeByRole).forEach((node) => {
      const group = document.createElementNS("http://www.w3.org/2000/svg", "g");
      group.setAttribute("class", "node");
      group.setAttribute("transform", `translate(${node.x} ${node.y})`);

      const ring = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle",
      );
      ring.setAttribute("r", `${ringRadius}`);
      ring.setAttribute("fill", `${node.color}33`);
      group.appendChild(ring);

      const core = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "circle",
      );
      core.setAttribute("r", `${coreRadius}`);
      core.setAttribute("fill", node.color);
      group.appendChild(core);

      const layout = buildNodeLabelLayout(node, coreRadius);
      const label = document.createElementNS(
        "http://www.w3.org/2000/svg",
        "text",
      );
      label.setAttribute("class", "node-label");
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("font-size", `${layout.fontSize}`);
      label.setAttribute("font-weight", "700");
      const startY = -layout.totalHeight / 2 + layout.fontSize;

      layout.lines.forEach((line, idx) => {
        const tspan = document.createElementNS(
          "http://www.w3.org/2000/svg",
          "tspan",
        );
        tspan.setAttribute("x", "0");
        tspan.setAttribute("y", `${startY + idx * layout.lineHeight}`);
        tspan.setAttribute(
          "class",
          line.kind === "agent" ? "node-label-agent" : "node-label-title",
        );
        tspan.textContent = String(line.text || "");
        label.appendChild(tspan);
      });
      group.appendChild(label);

      group.addEventListener("click", () => {
        const first = state.turns.find(
          (turn) => normalizeRole(turn.from_role) === node.role,
        );
        if (first) {
          state.selectedTurnKey = first.key;
          renderAll();
        }
      });

      svg.appendChild(group);
    });
  };

  const renderTimeline = () => {
    refs.timeline.innerHTML = "";
    if (!state.turns.length) {
      refs.timeline.innerHTML = `<p class="hint">No team turns yet.</p>`;
      return;
    }

    state.turns.forEach((turn) => {
      const item = document.createElement("button");
      item.type = "button";
      item.className = `timeline-item ${state.selectedTurnKey === turn.key ? "selected" : ""}`;
      item.innerHTML = `
        <div class="timeline-meta">
          <span>Turn ${turn.turn || "?"}</span>
          <span>${esc(turn.action || "message")}</span>
        </div>
        <div class="timeline-route">${esc(titleCase(normalizeRole(turn.from_role)))} -> ${esc(
          titleCase(normalizeRole(turn.to_role)),
        )}</div>
        <div class="timeline-msg">${esc(trim(String(turn.message || ""), 150))}</div>
      `;
      item.addEventListener("click", () => {
        state.selectedTurnKey = turn.key;
        renderAll();
      });
      refs.timeline.appendChild(item);
    });
  };

  const renderCommunications = () => {
    refs.liveComms.innerHTML = "";
    if (!state.communications.length) {
      refs.liveComms.innerHTML = `<p class="hint">No live communications yet.</p>`;
      return;
    }

    state.communications.forEach((item, idx) => {
      const row = document.createElement("div");
      const isLatest = idx === state.communications.length - 1;
      row.className = `comm-item ${isLatest ? "latest" : ""}`;
      row.innerHTML = `
        <div class="comm-meta">Turn ${esc(item.turn || "?")} • ${esc(item.action || "message")} • ${esc(
          new Date(item.timestamp || Date.now()).toLocaleTimeString(),
        )}</div>
        <div class="comm-route">${esc(titleCase(normalizeRole(item.from_role)))} (${esc(
          item.from_agent || "unbound",
        )}) -> ${esc(titleCase(normalizeRole(item.to_role)))} (${esc(item.to_agent || "unbound")})</div>
        <div class="comm-message">${esc(item.message || "")}</div>
      `;
      refs.liveComms.appendChild(row);
    });
  };

  const renderLogs = () => {
    refs.logs.innerHTML = "";
    const recent = state.logs.slice(-120);
    if (!recent.length) {
      refs.logs.innerHTML = `<p class="hint">No logs yet.</p>`;
      return;
    }

    recent.forEach((item) => {
      const row = document.createElement("div");
      row.className = "log-item";
      row.innerHTML = `
        <div class="log-meta">${esc(item.level)} • ${new Date(item.timestamp).toLocaleTimeString()}</div>
        <div>${esc(item.message)}</div>
      `;
      refs.logs.appendChild(row);
    });
  };

  const renderOutput = () => {
    refs.finalOutput.textContent = state.output || "";
  };

  const renderAll = () => {
    renderMeta();
    renderTimeline();
    renderGraph();
    renderCommunications();
    renderOutput();
  };

  const fetchStatus = async () => {
    const res = await fetch(
      `/api/status?client_id=${encodeURIComponent(state.clientId)}`,
    );
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.status) setStatus(payload.status);
    if (Array.isArray(payload.team_turns)) {
      state.turns = [];
      payload.team_turns.forEach((turn) => upsertTurn(turn));
      if (Array.isArray(payload.team_communications))
        loadCommunications(payload.team_communications);
      else rebuildCommunicationsFromTurns();
    } else if (Array.isArray(payload.team_communications)) {
      loadCommunications(payload.team_communications);
    }
    if (payload.team_config) state.teamConfig = payload.team_config;
    if (payload.results?.final_output)
      state.output = payload.results.final_output;
    if (payload.last_task) state.lastTask = payload.last_task;
    if (Array.isArray(payload.logs)) state.logs = payload.logs;
    renderAll();
    renderLogs();
  };

  const fetchTeamConfig = async () => {
    const res = await fetch("/api/team/config");
    if (!res.ok) return;
    const payload = await res.json();
    if (payload.team) state.teamConfig = payload.team;
    if (Array.isArray(payload.agents)) state.availableAgents = payload.agents;
    if (payload.validation && typeof payload.validation === "object") {
      state.teamValidation = payload.validation;
      if (Array.isArray(payload.validation.available_agents)) {
        state.availableAgents = payload.validation.available_agents;
      }
    }
    applyTeamDefaults();
    renderConfigForm();
    renderAll();
  };

  const renderConfigForm = () => {
    state.configData = normalizeConfigData(state.configData);
    const config = state.configData;
    const agentNames = Object.keys(config.agents || {}).sort((a, b) =>
      a.localeCompare(b),
    );
    const availableForTeam = (state.availableAgents || []).length
      ? [...state.availableAgents].sort((a, b) => a.localeCompare(b))
      : agentNames;
    const teamRoleNames = Object.keys(config.agentic_team?.roles || {}).sort(
      (a, b) => a.localeCompare(b),
    );
    const validationNotice =
      state.teamValidation && state.teamValidation.valid === false
        ? `<div class="cfg-warning">Unavailable mappings: ${esc(
            (state.teamValidation.missing_roles || [])
              .map((item) => `${item.role}:${item.agent}`)
              .join(", "),
          )}</div>`
        : "";

    const agentRows = Object.entries(config.agents || {})
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, agent]) => {
        const spec = agent || {};
        return `
          <div class="cfg-card">
            <div class="cfg-head">
              <strong>${esc(name)}</strong>
              <button class="btn btn-ghost" data-action="remove-agent" data-agent="${esc(name)}" type="button">Remove</button>
            </div>
            <div class="cfg-grid">
              <label>Type
                <select data-section="agents" data-agent="${esc(name)}" data-field="type">
                  ${renderSelectOptions(AGENT_TYPE_OPTIONS, spec.type, false)}
                </select>
              </label>
              <label>Role
                <select data-section="agents" data-agent="${esc(name)}" data-field="role">
                  ${renderSelectOptions(AGENT_ROLE_OPTIONS, spec.role, true)}
                </select>
              </label>
              <label>Command<input type="text" data-section="agents" data-agent="${esc(name)}" data-field="command" value="${esc(spec.command || "")}" /></label>
              <label>Model<input type="text" data-section="agents" data-agent="${esc(name)}" data-field="model" value="${esc(spec.model || "")}" /></label>
              <label>Endpoint<input type="text" data-section="agents" data-agent="${esc(name)}" data-field="endpoint" value="${esc(spec.endpoint || "")}" /></label>
              <label>Timeout<input type="number" min="1" data-section="agents" data-agent="${esc(name)}" data-field="timeout" data-value-type="number" value="${esc(spec.timeout ?? 3600)}" /></label>
              <label class="cfg-full">Description<input type="text" data-section="agents" data-agent="${esc(name)}" data-field="description" value="${esc(spec.description || "")}" /></label>
              <label class="cfg-full">Capabilities<input type="text" data-section="agents" data-agent="${esc(name)}" data-field="capabilities" data-value-type="csv" value="${esc(toCsv(spec.capabilities))}" /></label>
            </div>
            <div class="cfg-flags">
              <label><input type="checkbox" data-section="agents" data-agent="${esc(name)}" data-field="enabled" data-value-type="bool" ${spec.enabled ? "checked" : ""} /> Enabled</label>
              <label><input type="checkbox" data-section="agents" data-agent="${esc(name)}" data-field="offline" data-value-type="bool" ${spec.offline ? "checked" : ""} /> Offline</label>
            </div>
          </div>
        `;
      })
      .join("");

    const workflowRows = Object.entries(config.workflows || {})
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([name, workflow]) => {
        const wf = workflow || {};
        const steps = Array.isArray(wf.steps) ? wf.steps : [];
        const stepRows = steps
          .map(
            (step, idx) => `
            <div class="cfg-step">
              <label>Agent
                <select data-section="workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}" data-field="agent">
                  ${renderSelectOptions(agentNames, step?.agent, true)}
                </select>
              </label>
              <label>Task
                <select data-section="workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}" data-field="task">
                  ${renderSelectOptions(WORKFLOW_TASK_OPTIONS, step?.task, true)}
                </select>
              </label>
              <label>Role
                <select data-section="workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}" data-field="role">
                  ${renderSelectOptions(WORKFLOW_ROLE_OPTIONS, step?.role, true)}
                </select>
              </label>
              <label>Fallback
                <select data-section="workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}" data-field="fallback">
                  ${renderSelectOptions(agentNames, step?.fallback, true)}
                </select>
              </label>
              <label class="cfg-full">Description<input type="text" data-section="workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}" data-field="description" value="${esc(step?.description || "")}" /></label>
              <button class="btn btn-ghost" type="button" data-action="remove-workflow-step" data-workflow="${esc(name)}" data-step-index="${idx}">Remove Step</button>
            </div>
          `,
          )
          .join("");
        return `
          <div class="cfg-card">
            <div class="cfg-head">
              <strong>${esc(name)}</strong>
              <button class="btn btn-ghost" type="button" data-action="remove-workflow" data-workflow="${esc(name)}">Remove</button>
            </div>
            <div class="cfg-grid">
              <label class="cfg-full">Description<input type="text" data-section="workflow" data-workflow="${esc(name)}" data-field="description" value="${esc(wf.description || "")}" /></label>
              <label><input type="checkbox" data-section="workflow" data-workflow="${esc(name)}" data-field="offline" data-value-type="bool" ${wf.offline ? "checked" : ""} /> Offline workflow</label>
            </div>
            <div class="cfg-subhead">
              <span>Steps</span>
              <button class="btn btn-ghost" type="button" data-action="add-workflow-step" data-workflow="${esc(name)}">+ Step</button>
            </div>
            <div class="cfg-stack">${stepRows || `<p class="hint">No steps yet.</p>`}</div>
          </div>
        `;
      })
      .join("");

    const fallbackRows = Object.entries(config.settings?.fallback?.map || {})
      .map(
        ([key, value]) => `
        <div class="cfg-map-row">
          <input type="text" data-section="fallback-map-key" data-map-key="${esc(key)}" value="${esc(key)}" />
          <input type="text" data-section="fallback-map-value" data-map-key="${esc(key)}" value="${esc(value || "")}" />
          <button class="btn btn-ghost" type="button" data-action="remove-fallback-map" data-map-key="${esc(key)}">Remove</button>
        </div>
      `,
      )
      .join("");

    const teamRolesRows = Object.entries(config.agentic_team?.roles || {})
      .sort(([a], [b]) => a.localeCompare(b))
      .map(
        ([role, spec]) => `
        <div class="cfg-card">
          <div class="cfg-head">
            <strong>${esc(role)}</strong>
            <button class="btn btn-ghost" type="button" data-action="remove-team-role" data-team-role="${esc(role)}">Remove</button>
          </div>
          <div class="cfg-grid">
            <label>Title<input type="text" data-section="team-role" data-team-role="${esc(role)}" data-field="title" value="${esc(spec?.title || "")}" /></label>
            <label>Agent
              <select data-section="team-role" data-team-role="${esc(role)}" data-field="agent">
                ${renderSelectOptions(availableForTeam, spec?.agent, true)}
              </select>
            </label>
            <label class="cfg-full">Responsibilities<input type="text" data-section="team-role" data-team-role="${esc(role)}" data-field="responsibilities" value="${esc(spec?.responsibilities || "")}" /></label>
          </div>
        </div>
      `,
      )
      .join("");

    refs.configForm.innerHTML = `
      ${validationNotice}
      <div class="cfg-section">
        <div class="cfg-section-head">
          <h3>Agents</h3>
          <div class="cfg-add-row">
            <input type="text" id="new-agent-name" placeholder="new-agent-name" />
            <button class="btn btn-ghost" type="button" data-action="add-agent">Add</button>
          </div>
        </div>
        <div class="cfg-stack">${agentRows || `<p class="hint">No agents configured.</p>`}</div>
      </div>

      <div class="cfg-section">
        <div class="cfg-section-head">
          <h3>Workflows</h3>
          <div class="cfg-add-row">
            <input type="text" id="new-workflow-name" placeholder="new-workflow" />
            <button class="btn btn-ghost" type="button" data-action="add-workflow">Add</button>
          </div>
        </div>
        <div class="cfg-stack">${workflowRows || `<p class="hint">No workflows configured.</p>`}</div>
      </div>

      <div class="cfg-section">
        <div class="cfg-section-head"><h3>Settings</h3></div>
        <div class="cfg-card">
          <div class="cfg-grid">
            <label>Max Iterations<input type="number" min="1" data-section="settings" data-field="max_iterations" data-value-type="number" value="${esc(config.settings?.max_iterations ?? "")}" /></label>
            <label>Log Level
              <select data-section="settings" data-field="log_level">
                ${renderSelectOptions(LOG_LEVEL_OPTIONS, config.settings?.log_level, false)}
              </select>
            </label>
            <label>Output Dir<input type="text" data-section="settings" data-field="output_dir" value="${esc(config.settings?.output_dir || "")}" /></label>
            <label>Workspace Dir<input type="text" data-section="settings" data-field="workspace_dir" value="${esc(config.settings?.workspace_dir || "")}" /></label>
            <label>Reports Dir<input type="text" data-section="settings" data-field="reports_dir" value="${esc(config.settings?.reports_dir || "")}" /></label>
            <label>Min Suggestions<input type="number" min="0" data-section="settings" data-field="min_suggestions_threshold" data-value-type="number" value="${esc(config.settings?.min_suggestions_threshold ?? "")}" /></label>
            <label class="cfg-full">Log File<input type="text" data-section="settings" data-field="log_file" value="${esc(config.settings?.log_file || "")}" /></label>
          </div>
          <div class="cfg-flags">
            <label><input type="checkbox" data-section="settings" data-field="create_reports" data-value-type="bool" ${config.settings?.create_reports ? "checked" : ""} /> Create reports</label>
            <label><input type="checkbox" data-section="settings" data-field="colored_output" data-value-type="bool" ${config.settings?.colored_output ? "checked" : ""} /> Colored output</label>
            <label><input type="checkbox" data-section="settings" data-field="offline.enabled" data-value-type="bool" ${config.settings?.offline?.enabled ? "checked" : ""} /> Offline enabled</label>
            <label><input type="checkbox" data-section="settings" data-field="offline.auto_detect" data-value-type="bool" ${config.settings?.offline?.auto_detect ? "checked" : ""} /> Offline auto detect</label>
            <label><input type="checkbox" data-section="settings" data-field="fallback.enabled" data-value-type="bool" ${config.settings?.fallback?.enabled ? "checked" : ""} /> Fallback enabled</label>
          </div>
          <div class="cfg-subhead">
            <span>Fallback Map</span>
            <button class="btn btn-ghost" type="button" data-action="add-fallback-map">+ Entry</button>
          </div>
          <div class="cfg-stack">${fallbackRows || `<p class="hint">No fallback mappings.</p>`}</div>
        </div>
      </div>

      <div class="cfg-section">
        <div class="cfg-section-head">
          <h3>Agentic Team</h3>
          <div class="cfg-add-row">
            <input type="text" id="new-team-role-name" placeholder="new_team_role" />
            <button class="btn btn-ghost" type="button" data-action="add-team-role">Add</button>
          </div>
        </div>
        <div class="cfg-card">
          <div class="cfg-grid">
            <label>Lead Role
              <select data-section="agentic-team" data-field="lead_role">
                ${renderSelectOptions(teamRoleNames, config.agentic_team?.lead_role, true)}
              </select>
            </label>
            <label>Max Turns<input type="number" min="1" data-section="agentic-team" data-field="max_turns" data-value-type="number" value="${esc(config.agentic_team?.max_turns ?? "")}" /></label>
          </div>
        </div>
        <div class="cfg-stack">${teamRolesRows || `<p class="hint">No team roles configured.</p>`}</div>
      </div>
    `;
  };

  const parseFieldValue = (el) => {
    const kind = el.dataset.valueType || "text";
    if (kind === "bool") return !!el.checked;
    if (kind === "number") {
      const value = Number(el.value);
      return Number.isFinite(value) ? value : 0;
    }
    if (kind === "csv") return parseCsv(el.value);
    return el.value;
  };

  const setPathValue = (obj, path, value) => {
    const parts = String(path || "").split(".");
    let cursor = obj;
    for (let i = 0; i < parts.length - 1; i += 1) {
      const key = parts[i];
      if (!cursor[key] || typeof cursor[key] !== "object") cursor[key] = {};
      cursor = cursor[key];
    }
    cursor[parts[parts.length - 1]] = value;
  };

  const updateGuidedField = (el) => {
    state.configData = normalizeConfigData(state.configData);
    const section = el.dataset.section || "";
    const field = el.dataset.field || "";
    const value = parseFieldValue(el);

    if (section === "agents") {
      const agent = el.dataset.agent;
      if (!agent || !state.configData.agents[agent]) return;
      state.configData.agents[agent][field] = value;
    } else if (section === "workflow") {
      const workflow = el.dataset.workflow;
      if (!workflow || !state.configData.workflows[workflow]) return;
      state.configData.workflows[workflow][field] = value;
    } else if (section === "workflow-step") {
      const workflow = el.dataset.workflow;
      const index = Number(el.dataset.stepIndex);
      const wf = state.configData.workflows[workflow];
      if (!wf || !Array.isArray(wf.steps) || !wf.steps[index]) return;
      wf.steps[index][field] = value;
    } else if (section === "settings") {
      setPathValue(state.configData.settings, field, value);
    } else if (section === "agentic-team") {
      state.configData.agentic_team[field] = value;
    } else if (section === "team-role") {
      const role = el.dataset.teamRole;
      if (!role || !state.configData.agentic_team.roles[role]) return;
      state.configData.agentic_team.roles[role][field] = value;
    } else if (section === "fallback-map-value") {
      const key = el.dataset.mapKey;
      if (!key) return;
      state.configData.settings.fallback.map[key] = value;
    } else if (section === "fallback-map-key") {
      const oldKey = el.dataset.mapKey;
      const newKey = normalizeKey(el.value);
      if (!oldKey || !newKey || oldKey === newKey) return;
      if (
        Object.prototype.hasOwnProperty.call(
          state.configData.settings.fallback.map,
          newKey,
        )
      )
        return;
      const currentValue = state.configData.settings.fallback.map[oldKey];
      delete state.configData.settings.fallback.map[oldKey];
      state.configData.settings.fallback.map[newKey] = currentValue;
      renderConfigForm();
    }
  };

  const handleConfigAction = (actionEl) => {
    state.configData = normalizeConfigData(state.configData);
    const action = actionEl.dataset.action;
    if (!action) return;

    if (action === "add-agent") {
      const input = refs.configForm.querySelector("#new-agent-name");
      const key = normalizeKey(input?.value);
      if (!key || state.configData.agents[key]) return;
      state.configData.agents[key] = {
        type: "cli",
        enabled: true,
        command: key,
        role: "implementation",
        timeout: 3600,
        description: "",
      };
      renderConfigForm();
      return;
    }

    if (action === "remove-agent") {
      const agent = actionEl.dataset.agent;
      if (!agent) return;
      delete state.configData.agents[agent];
      renderConfigForm();
      return;
    }

    if (action === "add-workflow") {
      const input = refs.configForm.querySelector("#new-workflow-name");
      const key = normalizeKey(input?.value);
      if (!key || state.configData.workflows[key]) return;
      state.configData.workflows[key] = {
        description: "",
        offline: false,
        steps: [],
      };
      renderConfigForm();
      return;
    }

    if (action === "remove-workflow") {
      const workflow = actionEl.dataset.workflow;
      if (!workflow) return;
      delete state.configData.workflows[workflow];
      renderConfigForm();
      return;
    }

    if (action === "add-workflow-step") {
      const workflow = actionEl.dataset.workflow;
      const wf = state.configData.workflows[workflow];
      if (!wf || !Array.isArray(wf.steps)) return;
      wf.steps.push({
        agent: "",
        task: "implement",
        role: "",
        description: "",
      });
      renderConfigForm();
      return;
    }

    if (action === "remove-workflow-step") {
      const workflow = actionEl.dataset.workflow;
      const idx = Number(actionEl.dataset.stepIndex);
      const wf = state.configData.workflows[workflow];
      if (!wf || !Array.isArray(wf.steps) || Number.isNaN(idx)) return;
      wf.steps.splice(idx, 1);
      renderConfigForm();
      return;
    }

    if (action === "add-fallback-map") {
      let idx = 1;
      let key = `source-agent-${idx}`;
      while (
        Object.prototype.hasOwnProperty.call(
          state.configData.settings.fallback.map,
          key,
        )
      ) {
        idx += 1;
        key = `source-agent-${idx}`;
      }
      state.configData.settings.fallback.map[key] = "";
      renderConfigForm();
      return;
    }

    if (action === "remove-fallback-map") {
      const mapKey = actionEl.dataset.mapKey;
      if (!mapKey) return;
      delete state.configData.settings.fallback.map[mapKey];
      renderConfigForm();
      return;
    }

    if (action === "add-team-role") {
      const input = refs.configForm.querySelector("#new-team-role-name");
      const key = normalizeKey(input?.value);
      if (!key || state.configData.agentic_team.roles[key]) return;
      state.configData.agentic_team.roles[key] = {
        title: "",
        agent: "",
        responsibilities: "",
      };
      renderConfigForm();
      return;
    }

    if (action === "remove-team-role") {
      const role = actionEl.dataset.teamRole;
      if (!role) return;
      delete state.configData.agentic_team.roles[role];
      renderConfigForm();
    }
  };

  const loadConfig = async () => {
    refs.configStatus.textContent = "Loading config...";
    const res = await fetch("/api/config");
    const payload = await res.json();
    if (!res.ok) {
      refs.configStatus.textContent = payload.error || "Failed to load config";
      return;
    }

    refs.configPath.textContent = payload.path || "";
    state.configData = normalizeConfigData(payload.parsed);
    applyTeamDefaults();
    renderConfigForm();
    refs.configStatus.textContent = `Loaded • ${new Date(payload.last_modified).toLocaleString()}`;
    await fetchTeamConfig();
  };

  const saveConfig = async () => {
    refs.saveConfigBtn.disabled = true;
    refs.configStatus.textContent = "Saving config...";
    try {
      const res = await fetch("/api/config", {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          "X-Client-Id": state.clientId,
        },
        body: JSON.stringify({ config: state.configData }),
      });
      const payload = await res.json();
      if (!res.ok) {
        refs.configStatus.textContent =
          payload.error || "Failed to save config";
        if (payload.validation && typeof payload.validation === "object") {
          state.teamValidation = payload.validation;
        }
        return;
      }

      state.configData = normalizeConfigData(
        payload.parsed || state.configData,
      );
      if (payload.validation && typeof payload.validation === "object") {
        state.teamValidation = payload.validation;
        if (Array.isArray(payload.validation.available_agents)) {
          state.availableAgents = payload.validation.available_agents;
        }
      }
      renderConfigForm();
      refs.configStatus.textContent = `${payload.message} • ${new Date(payload.last_modified).toLocaleString()}`;
      await fetchTeamConfig();
    } finally {
      refs.saveConfigBtn.disabled = false;
    }
  };

  const executeTask = async (isFollowup) => {
    await fetchTeamConfig();
    if (state.teamValidation && state.teamValidation.valid === false) {
      const missing = (state.teamValidation.missing_roles || [])
        .map((item) => `${item.role}:${item.agent}`)
        .join(", ");
      setStatus("error");
      refs.configStatus.textContent = `Fix unavailable mappings before run: ${missing}`;
      addLog(
        `Blocked run due to unavailable role mappings: ${missing}`,
        "error",
      );
      return;
    }

    const task = refs.taskInput.value.trim();
    if (!task) {
      addLog("Task is required", "warn");
      return;
    }

    const maxTurns = Math.max(1, Number(refs.maxTurns.value || 12));
    state.turns = [];
    state.communications = [];
    state.output = "";
    state.logs = [];
    state.selectedTurnKey = "";
    setStatus("running");
    renderAll();
    renderLogs();

    const res = await fetch("/api/execute", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Client-Id": state.clientId,
      },
      body: JSON.stringify({
        task,
        max_turns: maxTurns,
        is_followup: !!isFollowup,
        client_id: state.clientId,
      }),
    });

    const payload = await res.json();
    if (!res.ok) {
      setStatus("error");
      if (payload.validation && typeof payload.validation === "object") {
        state.teamValidation = payload.validation;
        if (Array.isArray(payload.validation.available_agents)) {
          state.availableAgents = payload.validation.available_agents;
        }
        renderConfigForm();
      }
      addLog(payload.error || "Failed to start task", "error");
      return;
    }

    state.lastTask = task;
    refs.taskInput.value = "";
    addLog("Task submitted", "info");
  };

  const connectSocket = () => {
    const socket = io({
      path: "/socket.io",
      transports: ["polling"],
      query: { client_id: state.clientId },
    });

    socket.on("connect", () => {
      setSocketConnected(true);
      addLog("Connected to backend", "success");
      fetchStatus();
    });

    socket.on("disconnect", () => {
      setSocketConnected(false);
      addLog("Disconnected from backend", "warn");
    });

    socket.on("connected", (data) => {
      if (data?.status) setStatus(data.status);
    });

    socket.on("task_started", () => {
      setStatus("running");
      addLog("Agentic team started execution", "info");
    });

    socket.on("progress_log", (payload) => {
      addLog(payload?.message || "", payload?.level || "info");
    });

    socket.on("team_turn", (turn) => {
      upsertTurn(turn || {});
      renderAll();
    });

    socket.on("team_communication", (communication) => {
      upsertCommunication(communication || {});
      renderGraph();
      renderCommunications();
    });

    socket.on("task_completed", (data) => {
      setStatus(data?.success ? "completed" : "failed");
      if (Array.isArray(data?.team_turns)) {
        state.turns = [];
        data.team_turns.forEach((turn) => upsertTurn(turn));
        if (Array.isArray(data?.team_communications))
          loadCommunications(data.team_communications);
        else rebuildCommunicationsFromTurns();
      }
      if (data?.team_config) state.teamConfig = data.team_config;
      state.output = data?.output || "";
      renderAll();
      addLog("Execution completed", data?.success ? "success" : "warn");
    });

    socket.on("task_error", (data) => {
      setStatus("error");
      addLog(`Task error: ${data?.error || "unknown error"}`, "error");
    });
  };

  const wireEvents = () => {
    refs.executeBtn.addEventListener("click", () => executeTask(false));
    refs.followupBtn.addEventListener("click", () => executeTask(true));

    refs.clearBtn.addEventListener("click", async () => {
      await fetch("/api/conversation/clear", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Client-Id": state.clientId,
        },
        body: JSON.stringify({ client_id: state.clientId }),
      });
      state.turns = [];
      state.communications = [];
      state.output = "";
      state.logs = [];
      state.selectedTurnKey = "";
      state.lastTask = "";
      setStatus("idle");
      renderAll();
      renderLogs();
    });

    refs.reloadConfigBtn.addEventListener("click", loadConfig);
    refs.saveConfigBtn.addEventListener("click", saveConfig);

    refs.configForm.addEventListener("click", (event) => {
      const actionEl = event.target.closest("[data-action]");
      if (actionEl) handleConfigAction(actionEl);
    });

    const onConfigFieldChange = (event) => {
      const target = event.target;
      if (
        !(
          target instanceof HTMLInputElement ||
          target instanceof HTMLSelectElement
        )
      )
        return;
      if (!target.dataset.section) return;
      updateGuidedField(target);
    };

    refs.configForm.addEventListener("input", onConfigFieldChange);
    refs.configForm.addEventListener("change", onConfigFieldChange);
  };

  const bootstrap = async () => {
    wireEvents();
    connectSocket();
    await Promise.all([fetchTeamConfig(), loadConfig(), fetchStatus()]);
    renderAll();
    renderLogs();
    setInterval(() => {
      if (state.status === "running") fetchStatus();
    }, 1200);
  };

  bootstrap();
})();
