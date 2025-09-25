document.addEventListener('DOMContentLoaded', () => {
    // === DOM Elements ===
    const messagesDiv = document.getElementById('messages');
    const roomNameDisplay = document.getElementById('room-name-display');
    const statusIndicator = document.getElementById('status');
    const subscribeButtons = document.querySelectorAll('.subscribe-btn');
    const onlineUsersCountSpan = document.getElementById('online-users-count');
    const typingIndicator = document.getElementById('typing-indicator');
    const subscriptionsCountSpan = document.getElementById('subscriptions-count');

    // === Application State ===
    let activeConnections = {}; // Melacak koneksi WebSocket yang aktif
    const username = currentUsername; // Mengambil dari variabel global di HTML
    const feedPlaceholderHTML = `<div class="feed-placeholder custom-feed-placeholder"><span class="material-icons">notifications</span><p>No messages yet</p><small>Subscribe to channels to receive messages</small></div>`;

    // === Fungsi Utama ===

    /**
     * Mengirim request ke server untuk subscribe/unsubscribe sebuah channel.
     * @param {string} channelId - ID dari channel.
     * @param {HTMLElement} buttonElement - Elemen tombol yang diklik.
     */
    async function toggleSubscription(channelId, buttonElement) {
        try {
            const response = await fetch('/subscriber/toggle_subscription', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ channel_id: channelId })
            });
            const data = await response.json();

            if (response.ok) {
                const roomName = buttonElement.dataset.room;
                if (data.action === 'subscribed') {
                    // Berhasil subscribe, sekarang hubungkan ke WebSocket
                    connect(roomName);
                    updateButtonState(buttonElement, true);
                } else {
                    // Berhasil unsubscribe, putuskan koneksi WebSocket
                    disconnect(roomName);
                    updateButtonState(buttonElement, false);
                }
                // Update kartu statistik
                subscriptionsCountSpan.textContent = data.subscription_count;
            } else {
                alert(`Error: ${data.message || 'Terjadi kesalahan.'}`);
            }
        } catch (error) {
            console.error("Gagal melakukan toggle subscription:", error);
            alert("Gagal terhubung ke server.");
        }
    }

    /**
     * Membuat dan mengelola koneksi WebSocket untuk sebuah room.
     * @param {string} roomName - Nama room yang akan dihubungkan.
     */
    function connect(roomName) {
        if (!username || username === 'Guest' || activeConnections[roomName]) {
            return;
        }

        const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsURL = `${wsProtocol}//${location.host}/subscribe?room=${roomName}&username=${username}`;
        const ws = new WebSocket(wsURL);

        ws.onopen = () => {
            activeConnections[roomName] = ws;
            updateGlobalStatus();
            // Tampilkan feed dari channel yang baru di-subscribe
            roomNameDisplay.textContent = roomName; 
            messagesDiv.innerHTML = ''; // Kosongkan feed untuk pesan baru
        };

        ws.onclose = () => {
            delete activeConnections[roomName];
            updateGlobalStatus();
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            data.room = roomName; // Tambahkan info room ke data
            handleIncomingData(data);
        };
        
        ws.onerror = (error) => console.error(`WebSocket Error di room '${roomName}':`, error);
    }

    /**
     * Menutup koneksi WebSocket untuk sebuah room.
     * @param {string} roomName - Nama room yang akan diputuskan.
     */
    function disconnect(roomName) {
        if (activeConnections[roomName]) {
            activeConnections[roomName].close();
        }
    }

    /**
     * Memproses semua jenis data yang masuk dari WebSocket.
     * @param {object} data - Data JSON dari server.
     */
    function handleIncomingData(data) {
        renderMessage(data);
        if (data.type === 'update-users' && data.room === roomNameDisplay.textContent) {
            onlineUsersCountSpan.textContent = data.users.length;
        }
    }

    // === UI Rendering Functions ===

    /** Memperbarui status global UI (indikator koneksi & jumlah subscription). */
    function updateGlobalStatus() {
        const count = Object.keys(activeConnections).length;
        if (count > 0) {
            statusIndicator.classList.add('connected');
        } else {
            statusIndicator.classList.remove('connected');
            roomNameDisplay.textContent = 'Not Subscribed';
            messagesDiv.innerHTML = feedPlaceholderHTML;
            onlineUsersCountSpan.textContent = '0';
        }
    }

    /** Mengubah tampilan tombol menjadi 'Subscribed' atau 'Subscribe'. */
    function updateButtonState(button, isSubscribed) {
        if (isSubscribed) {
            button.textContent = 'Subscribed';
            button.classList.remove('custom-btn-primary');
            button.classList.add('btn-secondary', 'disabled');
        } else {
            button.textContent = 'Subscribe';
            button.classList.add('custom-btn-primary');
            button.classList.remove('btn-secondary', 'disabled');
            button.disabled = false;
        }
    }
    
    /** Menampilkan pesan di message feed. */
    function renderMessage(data) {
        if (messagesDiv.querySelector('.feed-placeholder')) {
            messagesDiv.innerHTML = '';
        }

        const wrapper = document.createElement('div');
        wrapper.classList.add('message-wrapper');
        const bubble = document.createElement('div');
        bubble.classList.add('message-bubble');

        const roomBadge = `<span class="badge bg-dark me-2">${data.room}</span>`;

        if (data.username === username) wrapper.classList.add('sent');
        else wrapper.classList.add('received');

        bubble.innerHTML = `
            <div class="message-meta">${roomBadge}${data.username}</div>
            <div class="message-text">${data.message}</div>
            <div class="message-time">${data.timestamp}</div>
        `;
        wrapper.appendChild(bubble);

        // Selalu tambahkan pesan baru di paling atas (secara visual di bawah karena flex-reverse)
        messagesDiv.prepend(wrapper);
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    }

    // === Event Listeners Initialization ===

    /** Menambahkan event listener ke semua tombol subscribe. */
    subscribeButtons.forEach(button => {
        button.addEventListener('click', (event) => {
            const buttonElement = event.target;
            const channelId = buttonElement.dataset.channelId;
            // Panggil fungsi API, bukan langsung connect
            toggleSubscription(channelId, buttonElement);
        });
    });

    /**
     * Saat halaman dimuat, otomatis hubungkan WebSocket ke channel
     * yang sudah di-subscribe dari database.
     */
    function initializeSubscriptions() {
        const subscribedButtons = document.querySelectorAll('.subscribe-btn.disabled, .subscribe-btn.btn-secondary');
        subscriptionsCountSpan.textContent = subscribedButtons.length;
        subscribedButtons.forEach(button => {
            connect(button.dataset.room);
        });
    }

    initializeSubscriptions();
});