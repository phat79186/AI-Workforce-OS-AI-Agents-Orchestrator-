import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { io } from "socket.io-client";
import axios from "axios";

const configuredApiUrl = (import.meta.env.VITE_API_URL || "").trim();
const configuredSocketUrl = (import.meta.env.VITE_SOCKET_URL || "").trim();

// Default to same-origin so Vite proxy can forward /api and /socket.io.
const apiBaseUrl = configuredApiUrl || "";
const socketBaseUrl = configuredSocketUrl || configuredApiUrl || undefined;
const socketPath = import.meta.env.VITE_SOCKET_PATH || "/socket.io";
const socketTransportsEnv = import.meta.env.VITE_SOCKET_TRANSPORTS;
const socketTransports = socketTransportsEnv
  ? socketTransportsEnv
      .split(",")
      .map((t) => t.trim())
      .filter(Boolean)
  : ["websocket", "polling"];
const api = axios.create({ baseURL: apiBaseUrl });
const backendLabel =
  apiBaseUrl ||
  (typeof window !== "undefined"
    ? `${window.location.origin} (same-origin)`
    : "same-origin");
const STATUS_POLL_INTERVAL_MS = 1200;
const MAX_LOG_ENTRIES = 500;

const createClientId = () => {
  if (
    typeof crypto !== "undefined" &&
    typeof crypto.randomUUID === "function"
  ) {
    return crypto.randomUUID();
  }
  return `client-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
};

// Persist clientId across page reloads so the session survives refresh
const STORAGE_KEY = "ai-orchestrator-client-id";
const clientId = (() => {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY);
    if (stored) return stored;
  } catch {}
  const id = createClientId();
  try {
    sessionStorage.setItem(STORAGE_KEY, id);
  } catch {}
  return id;
})();
api.defaults.headers.common["X-Client-Id"] = clientId;

export const useOrchestratorStore = defineStore("orchestrator", () => {
  // State
  const socket = ref(null);
  const status = ref("idle"); // idle, running, completed, error
  const task = ref("");
  const workflow = ref("default");
  const maxIterations = ref(3);
  const output = ref("");
  const files = ref([]);
  const iterations = ref([]);
  const agents = ref([]);
  const localModelStatus = ref({ summary: {}, backends: [], agents: [] });
  const workflows = ref([]);
  const configData = ref({
    agents: {},
    workflows: {},
    settings: {},
    agentic_team: { roles: {} },
  });
  const configPath = ref("");
  const configLastModified = ref("");
  const configStatus = ref("");
  const configLoading = ref(false);
  const configSaving = ref(false);
  const currentFile = ref(null);
  const fileContent = ref("");
  const lastTask = ref("");
  const lastOutput = ref("");
  const canFollowUp = ref(false);
  const errorMessage = ref("");
  const logs = ref([]);
  let logCounter = 0;
  let statusPollIntervalId = null;
  let hasReportedStatusPollError = false;
  const seenLogSignatures = new Set();

  // Computed
  const isRunning = computed(() => status.value === "running");
  const hasOutput = computed(() => output.value.length > 0);
  const hasFiles = computed(() => files.value.length > 0);
  const hasError = computed(() => errorMessage.value.length > 0);
  const hasLogs = computed(() => logs.value.length > 0);
  const hasLocalModelStatus = computed(
    () =>
      (localModelStatus.value?.backends?.length || 0) > 0 ||
      (localModelStatus.value?.agents?.length || 0) > 0,
  );
  const hasConfig = computed(() => !!configPath.value);

  const deepClone = (value) => JSON.parse(JSON.stringify(value));

  const normalizeConfigObject = (value) => {
    const base = value && typeof value === "object" ? deepClone(value) : {};

    if (!base.agents || typeof base.agents !== "object") base.agents = {};
    if (!base.workflows || typeof base.workflows !== "object")
      base.workflows = {};
    if (!base.settings || typeof base.settings !== "object") base.settings = {};
    if (!base.agentic_team || typeof base.agentic_team !== "object") {
      base.agentic_team = {};
    }
    if (
      !base.agentic_team.roles ||
      typeof base.agentic_team.roles !== "object"
    ) {
      base.agentic_team.roles = {};
    }

    return base;
  };

  const buildApiErrorMessage = (error, context) => {
    if (error?.response) {
      if (error.response.status === 403) {
        return `${context}: Forbidden (403). Start the backend on ${backendLabel} and ensure it allows browser requests.`;
      }
      return `${context}: Server responded with ${error.response.status}`;
    }
    if (error?.request) {
      return `${context}: Unable to reach the backend. Is it running on ${backendLabel}?`;
    }
    return `${context}: ${error?.message || "Unknown error"}`;
  };

  const setError = (message) => {
    errorMessage.value = message;
  };

  const formatLogTime = (timestamp) => {
    if (!timestamp) return new Date().toLocaleTimeString();
    const parsed = new Date(timestamp);
    if (Number.isNaN(parsed.getTime())) return new Date().toLocaleTimeString();
    return parsed.toLocaleTimeString();
  };

  const addLog = (message, level = "info", options = {}) => {
    if (typeof message !== "string" || !message.trim()) return;
    const normalizedMessage = message.trim();
    const normalizedLevel = String(level || "info").toLowerCase();
    const signature =
      options.signature ||
      `${options.timestamp || ""}|${normalizedLevel}|${normalizedMessage}`;

    if (seenLogSignatures.has(signature)) {
      return;
    }
    seenLogSignatures.add(signature);

    logs.value.push({
      id: ++logCounter,
      message: normalizedMessage,
      level: normalizedLevel,
      time: options.time || formatLogTime(options.timestamp),
      timestamp: options.timestamp || null,
      signature,
    });

    if (logs.value.length > MAX_LOG_ENTRIES) {
      const removed = logs.value.splice(0, logs.value.length - MAX_LOG_ENTRIES);
      removed.forEach((entry) => {
        if (entry.signature) {
          seenLogSignatures.delete(entry.signature);
        }
      });
    }
  };

  const syncLogsFromSession = (sessionLogs) => {
    if (!Array.isArray(sessionLogs)) return;
    sessionLogs.forEach((entry) => {
      if (!entry || typeof entry !== "object") return;
      addLog(entry.message || "", entry.level || "info", {
        timestamp: entry.timestamp,
      });
    });
  };

  const clearLogs = () => {
    logs.value = [];
    logCounter = 0;
    seenLogSignatures.clear();
  };

  const stopStatusPolling = () => {
    if (statusPollIntervalId) {
      clearInterval(statusPollIntervalId);
      statusPollIntervalId = null;
    }
  };

  const applyBackendSessionStatus = (session, source = "poll") => {
    if (!session || typeof session !== "object") return;

    const backendStatus = session.status;
    if (typeof backendStatus === "string" && backendStatus.length > 0) {
      status.value = backendStatus;
    }

    syncLogsFromSession(session.logs);

    if (Array.isArray(session.files)) {
      files.value = session.files;
    }

    const results = session.results;
    if (results && typeof results === "object") {
      output.value = results.final_output || output.value || "";
      if (Array.isArray(results.iterations)) {
        iterations.value = results.iterations;
      }
      if (typeof results.success === "boolean") {
        status.value = results.success ? "completed" : status.value;
      }
    }

    if (typeof session.last_task === "string" && session.last_task) {
      lastTask.value = session.last_task;
      canFollowUp.value = true;
    }
    if (typeof session.last_output === "string") {
      lastOutput.value = session.last_output;
    }

    if (status.value === "running" && source !== "poll") {
      startStatusPolling();
    }

    if (
      source === "poll" &&
      (status.value === "completed" ||
        status.value === "error" ||
        status.value === "failed")
    ) {
      stopStatusPolling();
    }
  };

  const startStatusPolling = () => {
    if (statusPollIntervalId) return;
    statusPollIntervalId = setInterval(async () => {
      try {
        const response = await api.get("/api/status", {
          params: { client_id: clientId },
        });
        hasReportedStatusPollError = false;
        applyBackendSessionStatus(response.data, "poll");
      } catch (error) {
        if (!hasReportedStatusPollError) {
          addLog(
            "Status polling temporarily unavailable; waiting for realtime events.",
            "warn",
          );
          hasReportedStatusPollError = true;
        }
      }
    }, STATUS_POLL_INTERVAL_MS);
  };

  const loadStatusOnce = async () => {
    try {
      const response = await api.get("/api/status", {
        params: { client_id: clientId },
      });
      applyBackendSessionStatus(response.data, "initial");
    } catch (error) {
      // Best-effort only; realtime connection will still drive updates.
    }
  };

  // Actions
  function init() {
    const socketUrlLabel =
      (socketBaseUrl ||
        (typeof window !== "undefined" ? window.location.origin : "")) +
      socketPath;
    const attemptedTransportProfiles = new Set();

    const attachSocket = (transports) => {
      if (socket.value) {
        socket.value.removeAllListeners();
        socket.value.disconnect();
      }

      const socketOptions = {
        path: socketPath,
        transports,
        forceNew: true,
        withCredentials: false,
        reconnection: true,
        reconnectionAttempts: Infinity,
        reconnectionDelay: 1000,
        reconnectionDelayMax: 5000,
        query: { client_id: clientId },
      };

      console.info("Connecting to Socket.IO", {
        url: socketUrlLabel,
        transports,
      });

      socket.value = io(socketBaseUrl, socketOptions);

      socket.value.on("connect", () => {
        console.log("Connected to server");
        if (status.value === "error") {
          status.value = "idle";
        }
        setError("");
        loadStatusOnce();
        fetchWorkspaceFiles();
        addLog("Connected to backend", "success");
      });

      socket.value.on("disconnect", () => {
        console.log("Disconnected from server");
        setError(
          `Lost connection to the backend. Check that it is running on ${backendLabel}.`,
        );
        if (status.value === "running") {
          startStatusPolling();
        }
        addLog("Disconnected from backend", "warn");
      });

      socket.value.on("connect_error", (error) => {
        console.error("Socket connection error:", error);

        const profile = transports.join(",");
        if (
          transports.includes("websocket") &&
          transports.includes("polling") &&
          !attemptedTransportProfiles.has("polling")
        ) {
          attemptedTransportProfiles.add(profile);
          attemptedTransportProfiles.add("polling");
          addLog(
            "WebSocket handshake failed; retrying Socket.IO with polling-only transport.",
            "warn",
          );
          attachSocket(["polling"]);
          return;
        }

        setError(
          `Unable to reach the backend (WebSocket/polling). URL: ${socketUrlLabel} via [${transports.join(", ")}]. Ensure the server at ${backendLabel} is accessible.`,
        );
        if (status.value !== "running") {
          status.value = "error";
        }
        startStatusPolling();
        addLog("Socket connection error; check backend availability.", "error");
      });

      socket.value.on("task_started", (data) => {
        console.log("Task started:", data);
        status.value = "running";
        startStatusPolling();
        addLog(
          `Task started (workflow: ${data.workflow || workflow.value})`,
          "info",
        );
      });

      socket.value.on("progress_log", (data) => {
        const message = data?.message || JSON.stringify(data || {});
        const level = data?.level || "info";
        addLog(message, level, { timestamp: data?.timestamp });
      });

      socket.value.on("task_completed", (data) => {
        console.log("Task completed:", data);
        stopStatusPolling();
        status.value = data.success ? "completed" : "error";
        output.value = data.output || "";
        files.value = data.files || [];
        iterations.value = data.iterations || [];

        // Store for follow-ups
        lastTask.value = data.task;
        lastOutput.value = data.output || "";
        canFollowUp.value = data.success !== false;
        addLog(
          `Task completed ${data.success === false ? "(failed)" : "successfully"}`,
          data.success === false ? "warn" : "success",
        );
      });

      socket.value.on("task_cancelled", (data) => {
        console.log("Task cancelled:", data);
        stopStatusPolling();
        status.value = "idle";
        addLog("Execution cancelled by user", "warn");
      });

      socket.value.on("task_error", (data) => {
        console.error("Task error:", data);
        stopStatusPolling();
        status.value = "error";
        output.value = `Error: ${data.error}`;
        addLog(`Task error: ${data.error}`, "error");
      });
    };

    // Initialize Socket.IO (default to websocket+polling)
    attachSocket(
      socketTransports.length ? socketTransports : ["websocket", "polling"],
    );

    // Load agents, local model status, and workflows
    loadAgents();
    loadLocalModelStatus();
    loadWorkflows();
    loadConfig();
    // Recover session state if backend already has one
    loadStatusOnce();
  }

  async function loadAgents() {
    try {
      const response = await api.get("/api/agents");
      agents.value = response.data.agents;
      setError("");
    } catch (error) {
      console.error("Failed to load agents:", error);
      setError(buildApiErrorMessage(error, "Failed to load agents"));
    }
  }

  async function loadWorkflows() {
    try {
      const response = await api.get("/api/workflows");
      workflows.value = response.data.workflows;
      setError("");
    } catch (error) {
      console.error("Failed to load workflows:", error);
      setError(buildApiErrorMessage(error, "Failed to load workflows"));
    }
  }

  async function loadLocalModelStatus() {
    try {
      const response = await api.get("/api/models/status");
      const payload = response.data || {};
      localModelStatus.value = {
        summary: payload.summary || {},
        backends: Array.isArray(payload.backends) ? payload.backends : [],
        agents: Array.isArray(payload.agents) ? payload.agents : [],
      };
    } catch (error) {
      console.error("Failed to load local model status:", error);
      addLog("Unable to load local model status", "warn");
    }
  }

  async function loadConfig() {
    configLoading.value = true;
    configStatus.value = "Loading config...";
    try {
      const response = await api.get("/api/config");
      const payload = response.data || {};
      configPath.value = payload.path || "";
      configLastModified.value = payload.last_modified || "";
      configData.value = normalizeConfigObject(payload.parsed);
      configStatus.value = configLastModified.value
        ? `Loaded • ${new Date(configLastModified.value).toLocaleString()}`
        : "Loaded";
      setError("");
    } catch (error) {
      console.error("Failed to load config:", error);
      configStatus.value = "Failed to load config";
      setError(buildApiErrorMessage(error, "Failed to load config"));
    } finally {
      configLoading.value = false;
    }
  }

  async function saveConfig() {
    configSaving.value = true;
    configStatus.value = "Saving config...";
    try {
      const response = await api.put("/api/config", {
        config: configData.value,
        client_id: clientId,
      });
      const payload = response.data || {};
      configPath.value = payload.path || configPath.value;
      configLastModified.value =
        payload.last_modified || configLastModified.value;
      configData.value = normalizeConfigObject(
        payload.parsed || configData.value,
      );
      configStatus.value = configLastModified.value
        ? `${payload.message || "Configuration saved"} • ${new Date(configLastModified.value).toLocaleString()}`
        : payload.message || "Configuration saved";
      setError("");
      await Promise.all([
        loadAgents(),
        loadWorkflows(),
        loadLocalModelStatus(),
      ]);
    } catch (error) {
      console.error("Failed to save config:", error);
      const serverError = error?.response?.data?.error;
      configStatus.value = serverError || "Failed to save config";
      setError(buildApiErrorMessage(error, "Failed to save config"));
    } finally {
      configSaving.value = false;
    }
  }

  async function executeTask() {
    if (!task.value.trim()) {
      alert("Please enter a task description");
      return;
    }

    // Clear previous logs for new task
    clearLogs();
    files.value = [];
    iterations.value = [];
    output.value = "";
    status.value = "running";
    setError("");
    addLog("Submitting task to backend...", "info");
    startStatusPolling();

    try {
      const response = await api.post("/api/execute", {
        task: task.value,
        workflow: workflow.value,
        max_iterations: maxIterations.value,
        is_followup: false,
        client_id: clientId,
      });
      console.log("Task submitted:", response.data);
      addLog("Task submitted to backend", "info");
      // Clear task input after submission
      task.value = "";
      setError("");
    } catch (error) {
      stopStatusPolling();
      console.error("Failed to execute task:", error);
      status.value = "error";
      setError(buildApiErrorMessage(error, "Failed to execute task"));
      alert("Failed to execute task");
    }
  }

  async function loadFile(filename) {
    try {
      const response = await api.get("/api/files", {
        params: { path: filename },
      });
      currentFile.value = response.data;
      fileContent.value = response.data.content;
      setError("");
    } catch (error) {
      console.error("Failed to load file:", error);
      setError(buildApiErrorMessage(error, "Failed to load file"));
      alert("Failed to load file");
    }
  }

  async function fetchWorkspaceFiles() {
    try {
      const response = await api.get("/api/files/list");
      if (response.data.files && response.data.files.length > 0) {
        // Merge with existing files, avoiding duplicates
        const existingPaths = new Set(files.value);
        const newFiles = response.data.files.filter(
          (f) => !existingPaths.has(f),
        );
        files.value = [...files.value, ...newFiles];
      }
    } catch (error) {
      console.error("Failed to fetch workspace files:", error);
    }
  }

  async function executeFollowUp(followUpInstructions) {
    if (!lastTask.value) {
      alert("No previous task to follow up on");
      return;
    }

    status.value = "running";
    files.value = [];
    iterations.value = [];
    output.value = "";
    setError("");
    addLog("Submitting follow-up to backend...", "info");
    startStatusPolling();
    try {
      const response = await api.post("/api/execute", {
        task: followUpInstructions,
        workflow: workflow.value,
        max_iterations: maxIterations.value,
        is_followup: true,
        client_id: clientId,
      });
      console.log("Follow-up submitted:", response.data);
      addLog("Follow-up submitted to backend", "info");
      // Clear task input after submission
      task.value = "";
      setError("");
    } catch (error) {
      stopStatusPolling();
      console.error("Failed to execute follow-up:", error);
      status.value = "error";
      setError(buildApiErrorMessage(error, "Failed to execute follow-up"));
      alert("Failed to execute follow-up");
    }
  }

  function clear() {
    stopStatusPolling();
    task.value = "";
    output.value = "";
    files.value = [];
    iterations.value = [];
    currentFile.value = null;
    fileContent.value = "";
    status.value = "idle";
    lastTask.value = "";
    lastOutput.value = "";
    canFollowUp.value = false;
    setError("");
    clearLogs();
  }

  function downloadFile(filename, content) {
    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.split("/").pop();
    a.click();
    URL.revokeObjectURL(url);
  }

  return {
    // State
    status,
    task,
    workflow,
    maxIterations,
    output,
    files,
    iterations,
    agents,
    localModelStatus,
    workflows,
    configData,
    configPath,
    configLastModified,
    configStatus,
    configLoading,
    configSaving,
    currentFile,
    fileContent,
    lastTask,
    lastOutput,
    canFollowUp,
    errorMessage,
    logs,
    // Computed
    isRunning,
    hasOutput,
    hasFiles,
    hasError,
    hasLogs,
    hasLocalModelStatus,
    hasConfig,
    // Actions
    init,
    executeTask,
    executeFollowUp,
    loadFile,
    fetchWorkspaceFiles,
    loadLocalModelStatus,
    loadConfig,
    saveConfig,
    clear,
    clearLogs,
    clearError: () => setError(""),
    downloadFile,
    clientId,
  };
});
