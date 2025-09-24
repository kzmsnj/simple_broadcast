document.addEventListener('DOMContentLoaded', () => {
    // === DOM Elements ===
    const messagesDiv = document.getElementById('messages');
    const roomNameDisplay = document.getElementById('room-name-display');
    const statusIndicator = document.getElementById('status');
    const subscribeButtons = document.querySelectorAll('.subscribe-btn');
    const onlineUsersCountSpan = document.getElementById('online-users-count');
    const typingIndicator = document.getElementById('typing-indicator');

    // === Application State ===
    let ws; // Variabel untuk menyimpan koneksi WebSocket
    let currentRoom = null; // Untuk melacak room yang sedang aktif
    
    // PERBAIKAN #1: Selector diubah ke '.dash-sidebar' agar username terbaca benar
    const usernameBadgeElement = document.querySelector('.chat-header .username-badge.custom-badge-dark');
    const username = usernameBadgeElement ? usernameBadgeElement.textContent.replace('account_circle', '').trim() : null;

    const feedPlaceholderHTML = `<div class="feed-placeholder custom-feed-placeholder"><span class="material-icons">notifications</span><p>No messages yet</p><small>Subscribe to a channel to receive messages</small></div>`;

    // === WebSocket Logic ===
    function connect(roomName) {
        if (!username) {
            alert("Username tidak ditemukan. Silakan login kembali.");
            return;
        }

        if (ws) {
            ws.close(); // Tutup koneksi lama jika ada
        }
        
        currentRoom = roomName;
        updateUIForNewRoom(roomName);

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(`${wsProtocol}//${location.host}/subscribe?room=${roomName}&username=${username}`);

        ws.onopen = () => {
            statusIndicator.classList.add('connected');
        };

        ws.onclose = () => {
            statusIndicator.classList.remove('connected');
            if(currentRoom === roomName) {
                 updateUIForNewRoom("Not Subscribed");
            }
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            handleIncomingData(data);
        };
    }
    
    function handleIncomingData(data) {
        switch (data.type) {
            case 'chat':
            case 'history':
                renderMessage(data);
                break;
            case 'update-users':
                onlineUsersCountSpan.textContent = data.users.length;
                break;
            case 'typing':
                 if (data.isTyping && data.username !== username) {
                    typingIndicator.textContent = `${data.username} is typing...`;
                 } else {
                    typingIndicator.textContent = '';
                 }
                 break;
        }
    }

    // === UI Rendering Functions ===
    function updateUIForNewRoom(roomName) {
        roomNameDisplay.textContent = roomName;
        messagesDiv.innerHTML = feedPlaceholderHTML;
        onlineUsersCountSpan.textContent = '0';
        typingIndicator.textContent = '';

        subscribeButtons.forEach(btn => {
            if (btn.dataset.room === roomName) {
                btn.textContent = 'Subscribed';
                btn.classList.remove('custom-btn-primary');
                btn.classList.add('btn-secondary', 'disabled');
            } else {
                btn.textContent = 'Subscribe';
                btn.classList.add('custom-btn-primary');
                btn.classList.remove('btn-secondary', 'disabled');
            }
        });
    }
    
    function renderMessage(data) {
        if (messagesDiv.querySelector('.custom-feed-placeholder')) {
            messagesDiv.innerHTML = '';
        }

        const isHistory = data.type === 'history';
        const wrapper = document.createElement('div');
        wrapper.classList.add('message-wrapper');
        
        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');

        if (data.username === username) {
            wrapper.classList.add('sent');
        } else {
            wrapper.classList.add('received');
        }

        bubble.innerHTML = `
            <div class="message-meta">${data.username}</div>
            <div class="message-text">${data.message}</div>
            <div class="message-time">${data.timestamp}</div>
        `;
        wrapper.appendChild(bubble);

        // PERBAIKAN #2: Logika render dibalik agar urutan pesan benar
        if (isHistory) {
            // Riwayat pesan ditambahkan ke bagian atas (prepend)
            // agar pesan terlama muncul di paling atas (paling bawah di layar)
            messagesDiv.prepend(wrapper); 
        } else {
            // Pesan baru ditambahkan ke bagian bawah (append)
            // agar muncul di paling bawah (paling atas di layar)
            messagesDiv.appendChild(wrapper); 
        }
        
        // PERBAIKAN #3: Logika auto-scroll disederhanakan
        // Selalu scroll ke paling bawah (paling baru) setelah render
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // === Event Listeners ===
    subscribeButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const roomToJoin = event.target.dataset.room;
            if (currentRoom !== roomToJoin) {
                connect(roomToJoin);
            }
        });
    });

    console.log("Subscriber dashboard script loaded and ready.");
});