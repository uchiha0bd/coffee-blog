// This script will handle the custom chatbot's frontend logic

document.addEventListener('DOMContentLoaded', () => {
    const chatHistory = document.getElementById('chatHistory');
    const userInput = document.getElementById('userInput');
    const sendBtn = document.getElementById('sendBtn');
    const chatbotContainer = document.querySelector('.chatbot-container');
    const chatbotTrigger = document.getElementById('chatbotTrigger');

    const suggestedQuestionsArea = document.getElementById('suggestedQuestionsArea');
    const questionList = document.getElementById('questionList');
    const resetBtn = document.getElementById('resetBtn'); // Get the new reset button

    const suggestedQuestions = [
        "Why is coffee named coffee?",
        "Fun fact about coffee?",
        "What are the benefits of coffee?",
        "How is coffee cultivated?",
        "Tell me about Arabica vs Robusta."
    ];

    // Function to display suggested questions
    function displaySuggestedQuestions() {
        questionList.innerHTML = ''; // Clear previous questions
        suggestedQuestions.forEach(question => {
            const questionItem = document.createElement('span');
            questionItem.classList.add('suggested-question-item');
            questionItem.textContent = question;
            questionItem.addEventListener('click', () => {
                userInput.value = question; // Put question into input field
                sendMessage(); // Call the main send function
            });
            questionList.appendChild(questionItem);
        });
        suggestedQuestionsArea.style.display = 'block'; // Make sure the area is visible
    }
    
    // Function to add a message to the chat history display
    function addMessageToChat(sender, message) {
        const messageDiv = document.createElement('div');
        messageDiv.classList.add(sender === 'user' ? 'user-message' : 'ai-message');
        messageDiv.textContent = message;
        chatHistory.appendChild(messageDiv);
        chatHistory.scrollTop = chatHistory.scrollHeight; // Auto-scroll to bottom
    }

    // --- REFACTORED SEND LOGIC ---
    // Central function to handle sending a message
    async function sendMessage() {
        const message = userInput.value.trim();
        if (!message) {
            return;
        }

        addMessageToChat('user', message);
        userInput.value = '';
        suggestedQuestionsArea.style.display = 'none'; // Hide suggestions after interaction

        // Show a loading indicator
        addMessageToChat('ai', "Thinking..."); 
        const loadingMessage = chatHistory.lastChild;
        loadingMessage.classList.add('loading-message');

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: message }),
            });
            const data = await response.json();
            loadingMessage.remove(); // Remove loading indicator
            addMessageToChat('ai', data.response);
        } catch (error) {
            console.error('Error sending message to backend:', error);
            loadingMessage.remove(); // Remove loading indicator on error
            addMessageToChat('ai', "Sorry, I'm having trouble connecting right now. Please try again.");
        }
    }

    // Event listener for the Send button
    sendBtn.addEventListener('click', sendMessage);

    // ==================== NEW RESET FUNCTION ====================
    // Function to reset the chat to its initial state
    function resetChat() {
        chatHistory.innerHTML = ''; // Clear all messages from the history
        addMessageToChat('ai', welcomeMessage); // Add the welcome message back
        displaySuggestedQuestions(); // Show the suggested questions again
    }
    // ================== END NEW RESET FUNCTION ==================

    // Allow sending message by pressing Enter key
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });
    // --- END REFACTORED SEND LOGIC ---
    
    
    // The welcome message to be reused
    const welcomeMessage = "Hi there! I'm your Coffee Chronicles chatbot. I've loaded information about coffee. Ask me anything about it!";

    // NEW: Event listener for the Reset button
    resetBtn.addEventListener('click', resetChat);

    // Initial welcome message
    addMessageToChat('ai', welcomeMessage); // Use the variable here
    displaySuggestedQuestions();

    // Event listener for the chatbot trigger button
    chatbotTrigger.addEventListener('click', () => {
        chatbotContainer.classList.toggle('active');
        // If we just opened the chat and there are no messages from the user yet, show suggestions
        if (chatbotContainer.classList.contains('active') && chatHistory.querySelectorAll('.user-message').length === 0) {
            displaySuggestedQuestions(); 
        } else {
            suggestedQuestionsArea.style.display = 'none';
        }
    });
});