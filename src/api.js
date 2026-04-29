const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    ...options
  });

  const isJson = response.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await response.json() : null;

  if (!response.ok) {
    throw new Error(body?.detail || "Request failed.");
  }

  return body;
}

export function loginWithGoogle(credential) {
  return request("/api/auth/google", {
    method: "POST",
    body: JSON.stringify({ credential })
  });
}

export function fetchCurrentUser(token) {
  return request("/api/auth/me", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchHomeData(token) {
  return request("/api/dashboard/home", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchAnalyticsData(token) {
  return request("/api/dashboard/analytics", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchAlertsData(token) {
  return request("/api/dashboard/alerts", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

function withQuery(path, params = {}) {
  const query = new URLSearchParams(
    Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined)
  );
  return query.size ? `${path}?${query.toString()}` : path;
}

export function fetchSignals(token, params = {}) {
  return request(withQuery("/api/signals", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchPredictions(token, params = {}) {
  return request(withQuery("/api/predictions", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchAlertsList(token, params = {}) {
  return request(withQuery("/api/alerts", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchRecommendations(token, params = {}) {
  return request(withQuery("/api/recommendations", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchClinicReports(token, params = {}) {
  return request(withQuery("/api/clinic-reports", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

function postWithToken(path, token, payload) {
  return request(path, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`
    },
    body: JSON.stringify(payload)
  });
}

export function fetchSymptomReports(token, params = {}) {
  return request(withQuery("/api/symptom-reports", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchWeatherRecords(token, params = {}) {
  return request(withQuery("/api/weather-records", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchNewsRecords(token, params = {}) {
  return request(withQuery("/api/news-records", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchNotifications(token, params = {}) {
  return request(withQuery("/api/notifications", params), {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function createSignal(token, payload) {
  return postWithToken("/api/signals", token, payload);
}

export function createClinicReport(token, payload) {
  return postWithToken("/api/clinic-reports", token, payload);
}

export function createSymptomReport(token, payload) {
  return postWithToken("/api/symptom-reports", token, payload);
}

export function createWeatherRecord(token, payload) {
  return postWithToken("/api/weather-records", token, payload);
}

export function createNewsRecord(token, payload) {
  return postWithToken("/api/news-records", token, payload);
}

export function createNotification(token, payload) {
  return postWithToken("/api/notifications", token, payload);
}

export function analyzeNewsRecord(token, payload) {
  return postWithToken("/api/news-records/analyze", token, payload);
}

export function runTrustedNewsIngestion(token, payload) {
  return postWithToken("/api/ingestion/news", token, payload);
}

export function runLiveWeatherIngestion(token, payload) {
  return postWithToken("/api/ingestion/weather", token, payload);
}

export function generateDailyReport(token, payload) {
  return postWithToken("/api/reports/daily-summary", token, payload);
}

export function generateNotifications(token, payload) {
  return postWithToken("/api/notifications/generate", token, payload);
}

export function sendQueuedEmailNotifications(token) {
  return postWithToken("/api/notifications/send-email", token, {});
}

export function sendQueuedSmsNotifications(token) {
  return postWithToken("/api/notifications/send-sms", token, {});
}

export function sendQueuedWhatsAppNotifications(token) {
  return postWithToken("/api/notifications/send-whatsapp", token, {});
}

export function runPipelineAnalysis(token, payload) {
  return postWithToken("/api/pipeline/run-analysis", token, payload);
}

export function fetchModelStatus(token) {
  return request("/api/model/status", {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function trainModel(token) {
  return postWithToken("/api/model/train", token, {});
}

export function fetchDatasetStatus(token, disease = "Lassa fever") {
  return request(`/api/dataset/status?disease=${encodeURIComponent(disease)}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchHistoricalReports(token, disease = "Lassa fever") {
  return request(`/api/dataset/reports?disease=${encodeURIComponent(disease)}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function fetchModelHistory(token, disease = "Lassa fever", limit = 20) {
  return request(`/api/model/history?disease=${encodeURIComponent(disease)}&limit=${limit}`, {
    headers: {
      Authorization: `Bearer ${token}`
    }
  });
}

export function runAutoDatasetRefresh(token) {
  return postWithToken("/api/dataset/run-auto", token, {});
}
