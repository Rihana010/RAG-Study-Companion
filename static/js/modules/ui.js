export const $ = (id) => document.getElementById(id);

export function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value ?? "";
    return div.innerHTML;
}

export function formatText(text) {
    if (!text) return "";

    let html = escapeHtml(text);

    html = html.replace(
        /\*\*(.*?)\*\*/g,
        "<strong>$1</strong>"
    );

    html = html.replace(
        /\*(.*?)\*/g,
        "<em>$1</em>"
    );

    html = html.replace(
        /\n\n+/g,
        "</p><p>"
    );

    html = html.replace(
        /\n/g,
        "<br>"
    );

    return `<p>${html}</p>`;
}

export function setStatus(message, type = "ready") {
    const statusText = $("status-text");
    const indicator = document.querySelector(
        ".status-indicator"
    );

    if (statusText) {
        statusText.textContent = message;
    }

    if (indicator) {
        indicator.className =
            `status-indicator ${type}`;
    }
}

export function showError(message) {
    console.error(message);

    const existing =
        document.querySelector(".frontend-error");

    if (existing) {
        existing.remove();
    }

    const error =
        document.createElement("div");

    error.className =
        "frontend-error";

    error.textContent =
        message;

    Object.assign(error.style, {
        position: "fixed",
        right: "20px",
        bottom: "20px",
        zIndex: "9999",
        maxWidth: "360px",
        padding: "12px 14px",
        border: "1px solid #e2b7b3",
        borderRadius: "8px",
        background: "#f8eae8",
        color: "#8b3632",
        fontSize: "12px",
        boxShadow:
            "0 4px 18px rgba(0,0,0,.08)"
    });

    document.body.appendChild(error);

    setTimeout(() => {
        error.remove();
    }, 5000);
}
