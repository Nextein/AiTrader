document.addEventListener('DOMContentLoaded', () => {
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusBadge = document.getElementById('system-status');
    const regimeVal = document.getElementById('regime-value');
    const symbolVal = document.getElementById('symbol-value');
    const logContainer = document.getElementById('log-container');

    let isRunning = false;

    async function updateStatus() {
        try {
            const resp = await fetch('/status');
            const data = await resp.json();

            isRunning = data.is_running;
            statusBadge.innerText = isRunning ? 'SYSTEM ACTIVE' : 'SYSTEM IDLE';
            statusBadge.className = 'status-badge ' + (isRunning ? 'status-active' : '');

            symbolVal.innerText = data.config.symbol;
        } catch (e) {
            statusBadge.innerText = 'OFFLINE';
            statusBadge.className = 'status-badge';
        }
    }

    async function fetchLogs() {
        try {
            const resp = await fetch('/logs?limit=50');
            const logs = await resp.json();

            renderLogs(logs);

            // Check for latest regime in logs if not otherwise available
            const latestRegime = logs.find(l => l.event_type === 'regime_change');
            if (latestRegime) {
                regimeVal.innerText = latestRegime.data.regime;
                regimeVal.style.color = latestRegime.data.regime === 'TRENDING' ? '#58a6ff' : '#d29922';
            }
        } catch (e) {
            console.error('Failed to fetch logs', e);
        }
    }

    function renderLogs(logs) {
        logContainer.innerHTML = logs.map(log => {
            const date = new Date(log.timestamp).toLocaleTimeString();
            const typeClass = log.event_type.includes('signal') ? 'type-signal' :
                log.event_type.includes('order') ? 'type-order' :
                    log.event_type.includes('error') ? 'type-error' : '';

            return `
                <div class="log-entry">
                    <span class="log-ts">${date}</span>
                    <span class="log-agent">${log.agent_name}</span>
                    <span class="log-type ${typeClass}">${log.event_type.toUpperCase()}</span>
                    <span class="log-msg">${JSON.stringify(log.data)}</span>
                </div>
            `;
        }).join('');
    }

    startBtn.addEventListener('click', async () => {
        await fetch('/start', { method: 'POST' });
        updateStatus();
    });

    stopBtn.addEventListener('click', async () => {
        await fetch('/stop', { method: 'POST' });
        updateStatus();
    });

    // Polling
    setInterval(updateStatus, 5000);
    setInterval(fetchLogs, 3000);

    updateStatus();
    fetchLogs();
});
