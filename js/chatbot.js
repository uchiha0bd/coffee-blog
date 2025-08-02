// This script will handle the custom chatbot's frontend logic

document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chatHistory');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
  

    // Function to add a message to the chat history display
    function addMessageToChat(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'ai-message');
        messageDiv.textContent = message;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight; // Auto-scroll to bottom
    }

    // Event listener for the Send button
    sendBtn.addEventListener('click', async () => {
        const message = userInput.value.trim(); // Get user input and remove whitespace
        if (!message) { // Don't send empty messages
            return;
        }

        addMessageToChat('user', message); // Display user's message
        userInput.value = ''; // Clear input field

        // Show a loading indicator
        addMessageToChat('ai', "Thinking..."); 
        chatHistory.lastChild.classList.add('loading-message'); // Add a class for loading indicator styling

        try {
            // Send message to Flask backend's /chat endpoint
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: message }),
            });

            const data = await response.json(); // Parse the JSON response from Flask

            // Remove loading indicator
            if (chatHistory.lastChild && chatHistory.lastChild.classList.contains('loading-message')) {
                chatHistory.lastChild.remove();
            }

            addMessageToChat('ai', data.response); // Display AI's response
        } catch (error) {
            console.error('Error sending message to backend:', error);
            // Remove loading indicator if there was an error
            if (chatHistory.lastChild && chatHistory.lastChild.classList.contains('loading-message')) {
                chatHistory.lastChild.remove();
            }
            addMessageToChat('ai', "Sorry, I'm having trouble connecting right now. Please try again.");
        }
    });

    // Allow sending message by pressing Enter key in the input field
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendBtn.click(); // Simulate a click on the send button
        }
    });

    // Event Listener for file upload - MOVED OUTSIDE OF THE KEYPRESS LISTENER
    

    // Initial welcome message (optional)
    addMessageToChat('ai', "Hi there! I'm your Coffee Chronicles chatbot. What would you like to know about coffee?");
});