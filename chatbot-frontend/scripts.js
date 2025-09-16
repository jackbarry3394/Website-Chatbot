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
        
        // Show typing indicator
        appendMessage("Typing...", "bot-message typing");
        // Send message to backend
        fetch("https://website-chatbot-sy3i.onrender.com/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: message })
        })
        .then(response => {
            console.log("Response status:", response.status);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Remove typing indicator
            document.querySelectorAll(".typing").forEach(el => el.remove());
            
            if (data.error) {
                appendMessage(`Error: ${data.error}`, "bot-message error");
            } else {
                appendMessage(data.response, "bot-message");
            }
        })
        .catch(error => {
            // Remove typing indicator
            document.querySelectorAll(".typing").forEach(el => el.remove());
            
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