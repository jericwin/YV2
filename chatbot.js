/**
 * chatbot.js
 * Injects and manages the Gemini AI Chatbot UI.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Inject CSS
  const link = document.createElement('link');
  link.rel = 'stylesheet';
  // Check if we are in buyer/ or root
  const isInBuyer = window.location.pathname.includes('/buyer/');
  link.href = isInBuyer ? '../chatbot.css' : 'chatbot.css';
  document.head.appendChild(link);

  // Inject HTML structure
  const container = document.createElement('div');
  container.id = 'chatbot-widget-container';
  container.innerHTML = `
    <div class="chatbot-window" id="chatbot-window">
      <div class="chatbot-header">
        <div class="chatbot-header-left">
          <div class="chatbot-header-icon">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"/><rect width="16" height="12" x="4" y="8" rx="2"/><path d="M2 14h2"/><path d="M20 14h2"/><path d="M15 13v2"/><path d="M9 13v2"/></svg>
          </div>
          <div>
            <div class="chatbot-header-title">YV2 AI</div>
            <div class="chatbot-header-subtitle">Ask me anything about books</div>
          </div>
        </div>
        <button class="chatbot-close" id="chatbot-close-btn">
          <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
        </button>
      </div>
      
      <div class="chatbot-body" id="chatbot-messages">
        <div class="chat-msg bot">
          <p>Hi there! 👋 I'm your YV2 AI.</p>
          <p>How can I help you find your next great read today?</p>
        </div>
        <div class="chatbot-suggestions" id="chatbot-suggestions">
          <button class="chat-suggestion-chip">What is YouVersion 2?</button>
          <button class="chat-suggestion-chip">How do I buy a book?</button>
          <button class="chat-suggestion-chip">Can I save books for later?</button>
        </div>
      </div>

      <div class="chatbot-footer">
        <form class="chatbot-input-wrap" id="chatbot-form">
          <input type="text" id="chatbot-input" placeholder="Type your message..." autocomplete="off">
          <button type="submit" class="chatbot-send-btn">
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
          </button>
        </form>
      </div>
    </div>
    
    <button class="chatbot-trigger" id="chatbot-trigger-btn">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/></svg>
    </button>
  `;
  document.body.appendChild(container);

  // Logic
  const triggerBtn = document.getElementById('chatbot-trigger-btn');
  const closeBtn = document.getElementById('chatbot-close-btn');
  const chatWindow = document.getElementById('chatbot-window');
  const chatForm = document.getElementById('chatbot-form');
  const chatInput = document.getElementById('chatbot-input');
  const messagesContainer = document.getElementById('chatbot-messages');

  let isChatOpen = false;

  const toggleChat = () => {
    isChatOpen = !isChatOpen;
    if (isChatOpen) {
      chatWindow.classList.add('open');
      chatInput.focus();
    } else {
      chatWindow.classList.remove('open');
    }
  };

  triggerBtn.addEventListener('click', toggleChat);
  closeBtn.addEventListener('click', toggleChat);

  // Parse markdown-like bold/italic/links simply
  const formatText = (text) => {
    return text
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/\n/g, '<br>');
  };

  const addMessage = (text, sender) => {
    const msgDiv = document.createElement('div');
    msgDiv.className = `chat-msg ${sender}`;
    msgDiv.innerHTML = `<p>${formatText(text)}</p>`;
    messagesContainer.appendChild(msgDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  };

  const addLoading = () => {
    const loader = document.createElement('div');
    loader.className = 'chat-loading';
    loader.id = 'chat-loader';
    loader.innerHTML = `<span></span><span></span><span></span>`;
    messagesContainer.appendChild(loader);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
  };

  const removeLoading = () => {
    const loader = document.getElementById('chat-loader');
    if (loader) loader.remove();
  };

  // Setup suggestion chips
  const chips = document.querySelectorAll('.chat-suggestion-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.innerText;
      // manually trigger submit event
      chatForm.dispatchEvent(new Event('submit'));
      // remove suggestions after first use to clean up UI
      const suggDiv = document.getElementById('chatbot-suggestions');
      if (suggDiv) suggDiv.style.display = 'none';
    });
  });

  chatForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;

    // Hide suggestions if present
    const suggDiv = document.getElementById('chatbot-suggestions');
    if (suggDiv) suggDiv.style.display = 'none';

    // 1. Add User Message
    addMessage(text, 'user');
    chatInput.value = '';
    
    // 2. Prepare bot message container
    const msgDiv = document.createElement('div');
    msgDiv.className = 'chat-msg bot';
    msgDiv.innerHTML = '<p></p>';
    messagesContainer.appendChild(msgDiv);
    const p = msgDiv.querySelector('p');

    // 3. Add temporary loading indicator inside it
    p.innerHTML = '<div class="chat-loading" style="display:inline-flex;padding:0;"><span></span><span></span><span></span></div>';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // 4. Send request and stream response
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text })
      });

      if (!response.ok) {
        let errText = "Unknown error";
        try {
           const errData = await response.json();
           errText = errData.error || errText;
        } catch(e) {}
        p.innerHTML = formatText('Sorry, I encountered an error: ' + errText);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullText = "";

      // Remove loading indicator on first chunk
      let isFirstChunk = true;
      p.classList.add('typing-active');

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          p.classList.remove('typing-active');
          break;
        }

        const chunk = decoder.decode(value, { stream: true });
        fullText += chunk;
        
        // Only clear the 3 dots when actual text (not padding) arrives
        if (isFirstChunk && fullText.trim().length > 0) {
          p.innerHTML = '';
          isFirstChunk = false;
        }

        if (!isFirstChunk) {
          // Update DOM with formatted text
          p.innerHTML = formatText(fullText.trim());
          messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
      }
    } catch (err) {
      p.classList.remove('typing-active');
      p.innerHTML = formatText('Network error. Please try again.');
    }
  });
});
