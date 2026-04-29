const STORAGE_KEY = "sentinel-session";

function getStorage() {
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function decodeJwt(token) {
  try {
    const payload = token.split(".")[1];
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = decodeURIComponent(
      atob(base64)
        .split("")
        .map((char) => `%${(`00${char.charCodeAt(0).toString(16)}`).slice(-2)}`)
        .join("")
    );

    return JSON.parse(json);
  } catch {
    return null;
  }
}

export function loadStoredUser() {
  const storage = getStorage();

  if (!storage) {
    return null;
  }

  const raw = storage.getItem(STORAGE_KEY);

  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    storage.removeItem(STORAGE_KEY);
    return null;
  }
}

export function persistUser(user) {
  const storage = getStorage();

  if (!storage) {
    return;
  }

  storage.setItem(STORAGE_KEY, JSON.stringify(user));
}

export function clearStoredUser() {
  const storage = getStorage();

  if (!storage) {
    return;
  }

  storage.removeItem(STORAGE_KEY);
}
