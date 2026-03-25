"use client";

export function readBrowserStorage(key: string): string | null {
    if (typeof window === "undefined") {
        return null;
    }
    return window.localStorage.getItem(key);
}

export function writeBrowserStorage(key: string, value?: string | null) {
    if (typeof window === "undefined") {
        return;
    }
    if (!value) {
        window.localStorage.removeItem(key);
        return;
    }
    window.localStorage.setItem(key, value);
}
