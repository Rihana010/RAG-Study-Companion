document.addEventListener("DOMContentLoaded", () => {

    // ============================================================
    // STATE
    // ============================================================

    let conversationHistory = [];
    let documents = [];

    let currentQuiz = null;
    let currentQuizIndex = 0;

    let currentFlashcards = [];
    let currentFlashcardIndex = 0;
    let currentFlashcardRevealed = false;


    // ============================================================
    // HELPERS
    // ============================================================

    const $ = (id) => document.getElementById(id);

    function escapeHtml(value) {
        const div = document.createElement("div");
        div.textContent = value ?? "";
        return div.innerHTML;
    }

    function formatText(text) {
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

    function setStatus(message, type = "ready") {
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

    function showError(message) {
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

    async function fetchJson(
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


    // ============================================================
    // TABS
    // ============================================================

    const tabButtons =
        document.querySelectorAll(".tab-btn");

    const tabPanes =
        document.querySelectorAll(".tab-pane");

    tabButtons.forEach((button) => {

        button.addEventListener(
            "click",
            () => {

                const targetId =
                    button.dataset.tab;

                tabButtons.forEach((btn) => {
                    btn.classList.toggle(
                        "active",
                        btn === button
                    );
                });

                tabPanes.forEach((pane) => {
                    pane.classList.toggle(
                        "active",
                        pane.id === targetId
                    );
                });
            }
        );
    });


    // ============================================================
    // PDF UPLOAD
    // ============================================================

    const pdfInput =
        $("pdf-input");

    const uploadBox =
        $("upload-box");

    const browseBtn =
        $("browse-btn");


    browseBtn?.addEventListener(
        "click",
        (event) => {
            event.stopPropagation();
            pdfInput?.click();
        }
    );


    uploadBox?.addEventListener(
        "click",
        (event) => {

            if (
                event.target === browseBtn ||
                event.target.closest("#browse-btn")
            ) {
                return;
            }

            pdfInput?.click();
        }
    );


    uploadBox?.addEventListener(
        "dragover",
        (event) => {

            event.preventDefault();

            uploadBox.classList.add(
                "dragging"
            );
        }
    );


    uploadBox?.addEventListener(
        "dragleave",
        () => {
            uploadBox.classList.remove(
                "dragging"
            );
        }
    );


    uploadBox?.addEventListener(
        "drop",
        (event) => {

            event.preventDefault();

            uploadBox.classList.remove(
                "dragging"
            );

            const file =
                event.dataTransfer.files?.[0];

            if (file) {
                uploadPdf(file);
            }
        }
    );


    pdfInput?.addEventListener(
        "change",
        () => {

            const file =
                pdfInput.files?.[0];

            if (file) {
                uploadPdf(file);
            }

            pdfInput.value = "";
        }
    );


    async function uploadPdf(file) {

        if (
            !file.name
                .toLowerCase()
                .endsWith(".pdf")
        ) {

            showError(
                "Please select a PDF file."
            );

            return;
        }

        const progress =
            $("upload-progress");

        const uploadContent =
            document.querySelector(
                ".upload-content"
            );

        const progressBar =
            $("progress-bar-fill");

        const progressStatus =
            $("progress-status");


        progress?.classList.remove(
            "hidden"
        );

        uploadContent?.classList.add(
            "hidden"
        );


        if (progressBar) {
            progressBar.style.width =
                "15%";
        }

        if (progressStatus) {
            progressStatus.textContent =
                "Uploading…";
        }

        setStatus(
            "Uploading…",
            "busy"
        );


        const formData =
            new FormData();

        formData.append(
            "file",
            file
        );


        try {

            const response =
                await fetch(
                    "/api/documents/upload",
                    {
                        method: "POST",
                        body: formData
                    }
                );


            let data;

            try {
                data =
                    await response.json();
            } catch {
                throw new Error(
                    "The server returned an invalid response."
                );
            }


            if (!response.ok) {
                throw new Error(
                    data?.message ||
                    data?.error ||
                    "Could not upload the PDF."
                );
            }


            if (progressBar) {
                progressBar.style.width =
                    "70%";
            }

            if (progressStatus) {
                progressStatus.textContent =
                    "Indexing study material…";
            }


            await loadDocuments();


            if (progressBar) {
                progressBar.style.width =
                    "100%";
            }

            if (progressStatus) {
                progressStatus.textContent =
                    "Ready";
            }


            setStatus(
                "Ready",
                "online"
            );


            setTimeout(() => {

                progress?.classList.add(
                    "hidden"
                );

                uploadContent?.classList.remove(
                    "hidden"
                );

                if (progressBar) {
                    progressBar.style.width =
                        "0%";
                }

            }, 700);


        } catch (error) {

            progress?.classList.add(
                "hidden"
            );

            uploadContent?.classList.remove(
                "hidden"
            );

            setStatus(
                "Upload failed",
                "error"
            );

            showError(
                error.message ||
                "Could not upload the PDF."
            );
        }
    }


    // ============================================================
    // DOCUMENT LIBRARY
    // ============================================================

    async function loadDocuments() {

        try {

            const data =
                await fetchJson(
                    "/api/documents/"
                );

            documents =
                data?.documents ||
                data?.data?.documents ||
                [];

            if (!Array.isArray(documents)) {
                documents = [];
            }

            renderDocuments();

        } catch (error) {

            console.error(
                "Could not load documents:",
                error
            );
        }
    }


    function renderDocuments() {

        const list =
            $("doc-list");

        const count =
            $("doc-count");

        if (!list) return;


        if (count) {

            count.textContent =
                `${documents.length} ${documents.length === 1
                    ? "source"
                    : "sources"
                }`;
        }


        if (!documents.length) {

            list.innerHTML = `
                <li class="doc-item empty-notice">
                    No study material yet.
                </li>
            `;

            return;
        }


        list.innerHTML =
            documents.map(
                (doc) => {

                    const name =
                        typeof doc === "string"
                            ? doc
                            : (
                                doc.filename ||
                                doc.name ||
                                doc.source ||
                                doc.title ||
                                "Untitled source"
                            );


                    const type =
                        typeof doc === "object" &&
                            (
                                doc.source_type === "youtube" ||
                                doc.type === "youtube"
                            )
                            ? "YouTube"
                            : "PDF";


                    return `
                        <li
                            class="doc-item"
                            data-document="${escapeHtml(name)}"
                        >

                            <div class="doc-info">

                                <span
                                    class="doc-name"
                                    title="${escapeHtml(name)}"
                                >
                                    ${escapeHtml(name)}
                                </span>

                                <span class="doc-meta">
                                    ${type}
                                </span>

                            </div>

                            <button
                                type="button"
                                class="doc-delete-btn"
                                data-filename="${encodeURIComponent(name)}"
                                title="Delete ${escapeHtml(name)}"
                                aria-label="Delete ${escapeHtml(name)}"
                            >
                                ×
                            </button>

                        </li>
                    `;
                }
            ).join("");


        // Attach delete handlers AFTER rendering.
        list.querySelectorAll(
            ".doc-delete-btn"
        ).forEach((button) => {

            button.addEventListener(
                "click",
                async (event) => {

                    event.stopPropagation();

                    const filename =
                        decodeURIComponent(
                            button.dataset.filename
                        );

                    await deleteDocument(
                        filename,
                        button
                    );
                }
            );
        });
    }


    // ============================================================
    // DELETE DOCUMENT
    // ============================================================

    async function deleteDocument(
        filename,
        button
    ) {

        const confirmed =
            window.confirm(
                `Delete "${filename}" from your study library?\n\nThis will remove its indexed content too.`
            );

        if (!confirmed) {
            return;
        }


        const originalText =
            button.textContent;

        button.disabled = true;

        button.textContent =
            "…";


        setStatus(
            "Deleting…",
            "busy"
        );


        try {

            const response =
                await fetch(
                    `/api/documents/${encodeURIComponent(filename)}`,
                    {
                        method: "DELETE"
                    }
                );


            let data = {};

            try {
                data =
                    await response.json();
            } catch {
                // Some servers may return an empty body.
            }


            if (!response.ok) {

                throw new Error(
                    data?.message ||
                    data?.error ||
                    `Could not delete "${filename}".`
                );
            }


            // Refresh library from backend.
            await loadDocuments();


            setStatus(
                "Ready",
                "online"
            );


        } catch (error) {

            button.disabled = false;

            button.textContent =
                originalText;

            setStatus(
                "Ready",
                "online"
            );

            showError(
                error.message ||
                "Could not delete the document."
            );
        }
    }


    // ============================================================
    // YOUTUBE
    // ============================================================

    $("yt-add-btn")?.addEventListener(
        "click",
        addYouTube
    );


    $("yt-url-input")?.addEventListener(
        "keydown",
        (event) => {

            if (event.key === "Enter") {

                event.preventDefault();

                addYouTube();
            }
        }
    );


    async function addYouTube() {

        const input =
            $("yt-url-input");

        const button =
            $("yt-add-btn");

        const url =
            input?.value.trim();


        if (!url) {

            showError(
                "Paste a YouTube URL first."
            );

            return;
        }


        button.disabled = true;

        button.textContent =
            "Adding…";

        setStatus(
            "Processing video…",
            "busy"
        );


        try {

            const data =
                await fetchJson(
                    "/api/youtube",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            url
                        })
                    }
                );


            input.value = "";

            await loadDocuments();


            setStatus(
                "Ready",
                "online"
            );


            addAssistantMessage(
                "The YouTube lecture has been added to your study library."
            );


        } catch (error) {

            setStatus(
                "Ready",
                "online"
            );

            showError(
                error.message ||
                "Could not add the YouTube video."
            );


        } finally {

            button.disabled = false;

            button.textContent =
                "Add";
        }
    }


    // ============================================================
    // CHAT
    // ============================================================

    const chatForm =
        $("chat-form");

    const chatInput =
        $("chat-input");

    const chatMessages =
        $("chat-messages");

    const sendBtn =
        $("send-btn");


    chatInput?.addEventListener(
        "input",
        () => {

            chatInput.style.height =
                "auto";

            chatInput.style.height =
                `${Math.min(
                    chatInput.scrollHeight,
                    130
                )}px`;
        }
    );


    chatInput?.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                chatForm?.requestSubmit();
            }
        }
    );


    chatForm?.addEventListener(
        "submit",
        async (event) => {

            event.preventDefault();

            const query =
                chatInput.value.trim();

            if (!query) return;


            addUserMessage(query);

            chatInput.value = "";

            chatInput.style.height =
                "auto";


            setChatLoading(true);

            setStatus(
                "Searching your material…",
                "busy"
            );


            const loadingMessage =
                addLoadingMessage();


            try {

                const data =
                    await fetchJson(
                        "/api/chat",
                        {
                            method: "POST",
                            body: JSON.stringify({
                                message: query,
                                query,
                                conversation_history:
                                    conversationHistory
                            })
                        }
                    );


                loadingMessage.remove();


                const reply =
                    data?.reply ||
                    data?.response ||
                    data?.data?.reply ||
                    data?.data?.response ||
                    "I couldn't generate a response.";


                const sources =
                    data?.sources ||
                    data?.data?.sources ||
                    [];


                conversationHistory.push({
                    role: "user",
                    content: query
                });


                conversationHistory.push({
                    role: "assistant",
                    content: reply
                });


                addAssistantMessage(
                    reply,
                    sources
                );


                setStatus(
                    "Ready",
                    "online"
                );


            } catch (error) {

                loadingMessage.remove();


                addAssistantMessage(
                    "I couldn't complete that request. Please try again."
                );


                setStatus(
                    "Ready",
                    "online"
                );


                showError(
                    error.message ||
                    "Something went wrong."
                );


            } finally {

                setChatLoading(
                    false
                );
            }
        }
    );


    function setChatLoading(
        isLoading
    ) {

        if (!sendBtn) return;

        sendBtn.disabled =
            isLoading;

        sendBtn.innerHTML =
            isLoading
                ? "Thinking…"
                : `
                    Send

                    <svg
                        class="btn-icon"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        stroke-width="1.8"
                    >
                        <path d="M22 2 11 13"></path>
                        <path d="m22 2-7 20-4-9 20-7Z"></path>
                    </svg>
                `;
    }


    function addUserMessage(text) {

        if (!chatMessages) return;


        const message =
            document.createElement(
                "div"
            );

        message.className =
            "message user-message";


        message.innerHTML = `
            <div class="message-header">
                <span class="sender-name">
                    You
                </span>

                <span class="timestamp">
                    Now
                </span>
            </div>

            <div class="message-body">
                ${formatText(text)}
            </div>
        `;


        chatMessages.appendChild(
            message
        );

        scrollChatToBottom();
    }


    function addAssistantMessage(
        text,
        sources = []
    ) {

        if (!chatMessages) return;


        const message =
            document.createElement(
                "div"
            );

        message.className =
            "message assistant-message";


        message.innerHTML = `
            <div class="message-header">
                <span class="sender-name">
                    Study Companion
                </span>

                <span class="timestamp">
                    Now
                </span>
            </div>

            <div class="message-body">
                ${formatText(
            cleanThinking(text)
        )}
            </div>

            ${renderSources(sources)}
        `;


        chatMessages.appendChild(
            message
        );

        scrollChatToBottom();
    }


    function addLoadingMessage() {

        const message =
            document.createElement(
                "div"
            );

        message.className =
            "message assistant-message";


        message.innerHTML = `
            <div class="message-header">
                <span class="sender-name">
                    Study Companion
                </span>

                <span class="timestamp">
                    Now
                </span>
            </div>

            <div class="message-body">
                Searching your study material…
            </div>
        `;


        chatMessages.appendChild(
            message
        );

        scrollChatToBottom();

        return message;
    }


    function cleanThinking(text) {

        if (!text) return "";

        text =
            text.replace(
                /<think>[\s\S]*?<\/think>/gi,
                ""
            );

        return text.trim();
    }


    function renderSources(
        sources
    ) {

        if (
            !Array.isArray(sources) ||
            sources.length === 0
        ) {
            return "";
        }


        const unique = [];

        const seen = new Set();


        sources.forEach(
            (source) => {

                const name =
                    source.source ||
                    source.document ||
                    source.filename ||
                    source.video_title ||
                    "Unknown source";


                const page =
                    source.page;

                const timestamp =
                    source.timestamp ||
                    source.timestamp_start;


                const key =
                    `${name}|${page}|${timestamp}`;


                if (seen.has(key)) {
                    return;
                }


                seen.add(key);


                unique.push({
                    name,
                    page,
                    timestamp,
                    videoUrl:
                        source.video_url
                });
            }
        );


        return `
            <div class="sources-list">

                <div class="sources-header">
                    Sources
                </div>

                ${unique.map(
            (source) => {

                let label =
                    escapeHtml(
                        source.name
                    );


                if (source.page) {

                    label +=
                        ` · Page ${escapeHtml(
                            String(
                                source.page
                            )
                        )
                        }`;
                }


                if (source.timestamp) {

                    label +=
                        ` · ${escapeHtml(
                            String(
                                source.timestamp
                            )
                        )
                        }`;
                }


                if (source.videoUrl) {

                    return `
                                <a
                                    class="source-item"
                                    href="${escapeHtml(
                        source.videoUrl
                    )}"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    ${label}
                                </a>
                            `;
                }


                return `
                            <span class="source-item">
                                ${label}
                            </span>
                        `;
            }
        ).join("")}

            </div>
        `;
    }


    function scrollChatToBottom() {

        if (!chatMessages) return;

        requestAnimationFrame(
            () => {
                chatMessages.scrollTop =
                    chatMessages.scrollHeight;
            }
        );
    }


    // ============================================================
    // QUIZ
    // ============================================================

    $("generate-quiz-btn")?.addEventListener(
        "click",
        generateQuiz
    );


    async function generateQuiz() {

        const button =
            $("generate-quiz-btn");

        const container =
            $("quiz-container");


        const topic =
            $("quiz-topic")
                ?.value
                .trim() || "";


        const count =
            Number(
                $("quiz-count")
                    ?.value || 5
            );


        button.disabled = true;

        button.textContent =
            "Generating…";


        container.innerHTML = `
            <div class="empty-state">

                <strong>
                    Generating your quiz…
                </strong>

                <span>
                    Searching your study material
                    and preparing questions.
                </span>

            </div>
        `;


        try {

            const data =
                await fetchJson(
                    "/api/study/quiz",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            topic,
                            count
                        })
                    }
                );


            const quiz =
                data?.quiz ||
                data?.data?.quiz ||
                data?.data ||
                data;


            currentQuiz =
                normalizeQuiz(
                    quiz
                );

            currentQuizIndex = 0;

            renderQuiz();


        } catch (error) {

            container.innerHTML = `
                <div class="empty-state">

                    <strong>
                        Quiz could not be generated.
                    </strong>

                    <span>
                        ${escapeHtml(
                error.message
            )}
                    </span>

                </div>
            `;


        } finally {

            button.disabled = false;

            button.textContent =
                "Generate quiz";
        }
    }


    function normalizeQuiz(
        quiz
    ) {

        if (Array.isArray(quiz)) {

            return {
                title: "Study quiz",
                questions: quiz
            };
        }


        return {
            title:
                quiz?.title ||
                "Study quiz",

            questions:
                Array.isArray(
                    quiz?.questions
                )
                    ? quiz.questions
                    : []
        };
    }


    function renderQuiz() {

        const container =
            $("quiz-container");


        if (
            !currentQuiz?.questions?.length
        ) {

            container.innerHTML = `
                <div class="empty-state">

                    <strong>
                        No questions were returned.
                    </strong>

                    <span>
                        Try another topic or add more
                        study material.
                    </span>

                </div>
            `;

            return;
        }


        const question =
            currentQuiz.questions[
            currentQuizIndex
            ];


        const total =
            currentQuiz.questions.length;


        const options =
            Array.isArray(
                question.options
            )
                ? question.options
                : [];


        container.innerHTML = `
            <div class="quiz-wrapper">

                <div class="quiz-header-bar">

                    <span class="quiz-title">
                        ${escapeHtml(
            currentQuiz.title
        )}
                    </span>

                    <span class="quiz-progress">
                        ${currentQuizIndex + 1}
                        /
                        ${total}
                    </span>

                </div>


                <div class="question-card">

                    <h3 class="question-text">
                        ${escapeHtml(
            question.question || ""
        )}
                    </h3>


                    <div class="options-group">

                        ${options.map(
            (option, index) => `
                                <button
                                    type="button"
                                    class="option-item"
                                    data-option-index="${index}"
                                >

                                    <span class="option-prefix">
                                        ${String.fromCharCode(
                65 + index
            )}
                                    </span>

                                    <span class="option-label">
                                        ${escapeHtml(
                option
            )}
                                    </span>

                                </button>
                            `
        ).join("")}

                    </div>


                    <div class="quiz-footer-nav">

                        <button
                            type="button"
                            class="btn btn-primary"
                            id="submit-ans-btn"
                        >
                            Check answer
                        </button>

                    </div>

                </div>

            </div>
        `;


        let selectedIndex = null;


        const optionButtons =
            container.querySelectorAll(
                ".option-item"
            );


        optionButtons.forEach(
            (optionButton) => {

                optionButton.addEventListener(
                    "click",
                    () => {

                        optionButtons.forEach(
                            (button) => {
                                button.classList.remove(
                                    "selected"
                                );
                            }
                        );


                        optionButton.classList.add(
                            "selected"
                        );


                        selectedIndex =
                            Number(
                                optionButton.dataset
                                    .optionIndex
                            );
                    }
                );
            }
        );


        const submitBtn =
            document.getElementById(
                "submit-ans-btn"
            );


        submitBtn?.addEventListener(
            "click",
            () => {

                if (
                    selectedIndex === null
                ) {

                    showError(
                        "Choose an answer first."
                    );

                    return;
                }


                const correctIndex =
                    normalizeAnswerIndex(
                        question.correct_answer
                    );


                const isCorrect =
                    selectedIndex ===
                    correctIndex;


                optionButtons.forEach(
                    (button, index) => {

                        button.disabled =
                            true;


                        if (
                            index ===
                            correctIndex
                        ) {

                            button.classList.add(
                                "correct"
                            );

                        } else if (
                            index ===
                            selectedIndex &&
                            !isCorrect
                        ) {

                            button.classList.add(
                                "incorrect"
                            );
                        }
                    }
                );


                const explanation =
                    document.createElement(
                        "div"
                    );


                explanation.className =
                    `explanation-box ${isCorrect
                        ? "correct-box"
                        : "incorrect-box"
                    }`;


                explanation.innerHTML = `
                    <strong>
                        ${isCorrect
                        ? "Correct"
                        : "Not quite"
                    }
                    </strong>

                    <div
                        style="margin-top: 4px;"
                    >
                        ${escapeHtml(
                        question.explanation ||
                        "Review the cited material for more context."
                    )}
                    </div>
                `;


                container
                    .querySelector(
                        ".question-card"
                    )
                    ?.appendChild(
                        explanation
                    );


                const footer =
                    container.querySelector(
                        ".quiz-footer-nav"
                    );


                if (footer) {

                    footer.innerHTML = `
                        <button
                            type="button"
                            class="btn btn-primary"
                            id="next-q-btn"
                        >
                            ${currentQuizIndex + 1 <
                            total
                            ? "Next question"
                            : "Finish quiz"
                        }
                        </button>
                    `;


                    document
                        .getElementById(
                            "next-q-btn"
                        )
                        ?.addEventListener(
                            "click",
                            () => {

                                if (
                                    currentQuizIndex + 1 <
                                    total
                                ) {

                                    currentQuizIndex +=
                                        1;

                                    renderQuiz();

                                } else {

                                    showQuizComplete();
                                }
                            }
                        );
                }
            }
        );
    }


    function normalizeAnswerIndex(
        value
    ) {

        if (
            typeof value === "number"
        ) {
            return value;
        }


        if (
            typeof value === "string"
        ) {

            const trimmed =
                value.trim();


            if (
                /^\d+$/.test(
                    trimmed
                )
            ) {

                return Number(
                    trimmed
                );
            }


            const index =
                trimmed
                    .toUpperCase()
                    .charCodeAt(0) - 65;


            if (
                index >= 0 &&
                index < 26
            ) {

                return index;
            }
        }


        return -1;
    }


    function showQuizComplete() {

        $("quiz-container").innerHTML = `
            <div class="empty-state">

                <strong>
                    Quiz complete
                </strong>

                <span>
                    You've reached the end
                    of this set.
                </span>

                <button
                    type="button"
                    class="btn btn-secondary"
                    id="restart-quiz-btn"
                >
                    Review again
                </button>

            </div>
        `;


        document
            .getElementById(
                "restart-quiz-btn"
            )
            ?.addEventListener(
                "click",
                () => {

                    currentQuizIndex = 0;

                    renderQuiz();
                }
            );
    }


    // ============================================================
    // FLASHCARDS
    // ============================================================

    $("generate-flashcards-btn")
        ?.addEventListener(
            "click",
            generateFlashcards
        );


    async function generateFlashcards() {

        const button =
            $("generate-flashcards-btn");

        const container =
            $("flashcards-container");


        const topic =
            $("flashcards-topic")
                ?.value
                .trim() || "";


        const count =
            Number(
                $("flashcards-count")
                    ?.value || 10
            );


        button.disabled = true;

        button.textContent =
            "Generating…";


        container.innerHTML = `
            <div class="empty-state">

                <strong>
                    Generating flashcards…
                </strong>

                <span>
                    Building cards from your
                    study material.
                </span>

            </div>
        `;


        try {

            const data =
                await fetchJson(
                    "/api/study/flashcards",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            topic,
                            count
                        })
                    }
                );


            const cards =
                data?.flashcards ||
                data?.data?.flashcards ||
                data?.data ||
                data;


            currentFlashcards =
                Array.isArray(cards)
                    ? cards
                    : [];


            currentFlashcardIndex =
                0;

            currentFlashcardRevealed =
                false;


            renderFlashcard();


        } catch (error) {

            container.innerHTML = `
                <div class="empty-state">

                    <strong>
                        Flashcards could not be generated.
                    </strong>

                    <span>
                        ${escapeHtml(
                error.message
            )}
                    </span>

                </div>
            `;


        } finally {

            button.disabled = false;

            button.textContent =
                "Generate cards";
        }
    }


    function renderFlashcard() {

        const container =
            $("flashcards-container");


        if (!currentFlashcards.length) {

            container.innerHTML = `
                <div class="empty-state">

                    <strong>
                        No flashcards were returned.
                    </strong>

                    <span>
                        Try another topic or add
                        more study material.
                    </span>

                </div>
            `;

            return;
        }


        const card =
            currentFlashcards[
            currentFlashcardIndex
            ];


        const front =
            card?.front ||
            card?.question ||
            "";


        const back =
            card?.back ||
            card?.answer ||
            "";


        container.innerHTML = `
            <div class="flashcard-container">

                <div class="flashcard">

                    <span class="flashcard-label">
                        ${currentFlashcardRevealed
                ? "Answer"
                : "Question"
            }
                    </span>

                    <div class="flashcard-text">
                        ${escapeHtml(
                currentFlashcardRevealed
                    ? back
                    : front
            )}
                    </div>

                    <button
                        type="button"
                        class="btn btn-secondary"
                        id="reveal-card-btn"
                    >
                        ${currentFlashcardRevealed
                ? "Hide answer"
                : "Show answer"
            }
                    </button>

                </div>

            </div>


            <div class="flashcard-controls">

                <button
                    type="button"
                    class="btn btn-secondary"
                    id="prev-card-btn"
                >
                    Previous
                </button>


                <span class="quiz-progress">
                    ${currentFlashcardIndex + 1}
                    /
                    ${currentFlashcards.length}
                </span>


                <button
                    type="button"
                    class="btn btn-secondary"
                    id="next-card-btn"
                >
                    Next
                </button>

            </div>
        `;


        document
            .getElementById(
                "reveal-card-btn"
            )
            ?.addEventListener(
                "click",
                () => {

                    currentFlashcardRevealed =
                        !currentFlashcardRevealed;

                    renderFlashcard();
                }
            );


        document
            .getElementById(
                "prev-card-btn"
            )
            ?.addEventListener(
                "click",
                () => {

                    currentFlashcardIndex =
                        (
                            currentFlashcardIndex -
                            1 +
                            currentFlashcards.length
                        ) %
                        currentFlashcards.length;


                    currentFlashcardRevealed =
                        false;

                    renderFlashcard();
                }
            );


        document
            .getElementById(
                "next-card-btn"
            )
            ?.addEventListener(
                "click",
                () => {

                    currentFlashcardIndex =
                        (
                            currentFlashcardIndex +
                            1
                        ) %
                        currentFlashcards.length;


                    currentFlashcardRevealed =
                        false;

                    renderFlashcard();
                }
            );
    }


    // ============================================================
    // SUMMARY
    // ============================================================

    $("generate-summary-btn")
        ?.addEventListener(
            "click",
            generateSummary
        );


    async function generateSummary() {

        const button =
            $("generate-summary-btn");

        const container =
            $("summary-container");


        const topic =
            $("summary-topic")
                ?.value
                .trim() || "";


        button.disabled = true;

        button.textContent =
            "Generating…";


        container.innerHTML = `
            <div class="empty-state">

                <strong>
                    Generating summary…
                </strong>

                <span>
                    Reviewing your study material.
                </span>

            </div>
        `;


        try {

            const data =
                await fetchJson(
                    "/api/study/summary",
                    {
                        method: "POST",
                        body: JSON.stringify({
                            topic
                        })
                    }
                );


            const summary =
                data?.summary ||
                data?.data?.summary ||
                data?.data ||
                data;


            renderSummary(
                summary
            );


        } catch (error) {

            container.innerHTML = `
                <div class="empty-state">

                    <strong>
                        Summary could not be generated.
                    </strong>

                    <span>
                        ${escapeHtml(
                error.message
            )}
                    </span>

                </div>
            `;


        } finally {

            button.disabled = false;

            button.textContent =
                "Generate summary";
        }
    }


    function renderSummary(
        summary
    ) {

        const container =
            $("summary-container");


        if (
            typeof summary ===
            "string"
        ) {

            container.innerHTML = `
                <div class="summary-container">

                    <div class="summary-section">

                        ${formatText(
                cleanThinking(
                    summary
                )
            )}

                    </div>

                </div>
            `;

            return;
        }


        const sections = [];


        if (summary?.overview) {

            sections.push(`
                <div class="summary-section">

                    <h3>
                        Overview
                    </h3>

                    ${formatText(
                summary.overview
            )}

                </div>
            `);
        }


        const keyConcepts =
            summary?.key_concepts ||
            summary?.keyConcepts ||
            summary?.main_points ||
            summary?.mainPoints;


        if (
            Array.isArray(
                keyConcepts
            ) &&
            keyConcepts.length
        ) {

            sections.push(`
                <div class="summary-section">

                    <h3>
                        Key concepts
                    </h3>

                    <ul class="summary-list">

                        ${keyConcepts.map(
                item => `
                                <li>
                                    ${escapeHtml(
                    String(item)
                )}
                                </li>
                            `
            ).join("")}

                    </ul>

                </div>
            `);
        }


        const definitions =
            summary?.definitions;


        if (
            Array.isArray(
                definitions
            ) &&
            definitions.length
        ) {

            sections.push(`
                <div class="summary-section">

                    <h3>
                        Definitions
                    </h3>

                    <table class="def-table">

                        <thead>

                            <tr>
                                <th>Term</th>
                                <th>Meaning</th>
                            </tr>

                        </thead>

                        <tbody>

                            ${definitions.map(
                item => `
                                    <tr>

                                        <td>
                                            ${escapeHtml(
                    item.term ||
                    item.name ||
                    ""
                )}
                                        </td>

                                        <td>
                                            ${escapeHtml(
                    item.definition ||
                    item.meaning ||
                    ""
                )}
                                        </td>

                                    </tr>
                                `
            ).join("")}

                        </tbody>

                    </table>

                </div>
            `);
        }


        if (!sections.length) {

            const fallback =
                summary?.content ||
                summary?.summary ||
                JSON.stringify(
                    summary,
                    null,
                    2
                );


            sections.push(`
                <div class="summary-section">

                    ${formatText(
                cleanThinking(
                    String(
                        fallback
                    )
                )
            )}

                </div>
            `);
        }


        container.innerHTML = `
            <div class="summary-container">
                ${sections.join("")}
            </div>
        `;
    }


    // ============================================================
    // INITIAL LOAD
    // ============================================================

    loadDocuments();

    setStatus(
        "Ready",
        "online"
    );

});