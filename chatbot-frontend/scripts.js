document.addEventListener("DOMContentLoaded", () => {
    const chatBox = document.getElementById("chat-box");
    const userInput = document.getElementById("user-input");
    const sendButton = document.getElementById("send-button");

    sendButton.addEventListener("click", sendMessage);
    userInput.addEventListener("keypress", (e) => {
        if (e.key === "Enter") sendMessage();
    });

    function sendMessage() {
        const message = userInput.value.trim();
        if (!message) return;

        appendMessage(message, "user-message");
        userInput.value = "";
        
        fetch("https://website-chatbot-sy3i.onrender.com/chat", {  // Render backend
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.error) {
                appendMessage(`Error: ${data.error}`, "bot-message error");
            } else {
                appendMessage(data.response, "bot-message");
            }
        })
        .catch(error => {
            console.error("Error:", error);
            appendMessage(`Connection error: ${error.message}`, "bot-message error");
        });
    }

    function appendMessage(text, className) {
        const messageDiv = document.createElement("div");
        messageDiv.classList.add(className);
        messageDiv.textContent = text;
        chatBox.appendChild(messageDiv);
        chatBox.scrollTop = chatBox.scrollHeight;  // Auto-scroll to latest message
    }
});