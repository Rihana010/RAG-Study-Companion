export async function fetchJson(
    url,
    options = {}
) {
    const response = await fetch(
        url,
        {
            ...options,
            headers: {
                ...(options.body instanceof FormData
                    ? {}
                    : {
                        "Content-Type":
                            "application/json"
                    }),
                ...(options.headers || {})
            }
        }
    );

    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            `Server returned an invalid response (${response.status}).`
        );
    }

    if (!response.ok) {
        throw new Error(
            data?.message ||
            data?.error ||
            `Request failed (${response.status}).`
        );
    }

    return data;
}
