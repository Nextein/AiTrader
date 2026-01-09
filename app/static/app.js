document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const statusText = document.querySelector('.status-text');
    const statusPulse = document.querySelector('.pulse');
    const symbolVal = document.getElementById('symbol-value');
    const regimeVal = document.getElementById('regime-value');
    const logContainer = document.getElementById('log-container');
    const agentsContainer = document.getElementById('agents-container');
    const statSignals = document.getElementById('stat-signals');
    const statOrders = document.getElementById('stat-orders');
    const clearLogsBtn = document.getElementById('clear-logs');

    let isRunning = false;
    let knownAgents = new Set();

    async function updateStatus() {
        try {
            const resp = await fetch('/status');
            if (!resp.ok) throw new Error('Offline');
            const data = await resp.json();

            isRunning = data.is_running;
            statusText.innerText = isRunning ? 'SYSTEM ACTIVE' : 'SYSTEM IDLE';
            statusPulse.style.background = isRunning ? 'var(--success)' : 'var(--text-secondary)';
            statusPulse.style.animation = isRunning ? 'pulse 2s infinite' : 'none';

            symbolVal.innerText = data.config.symbol;

            // Update button states
            startBtn.disabled = isRunning;
            stopBtn.disabled = !isRunning;
            startBtn.style.opacity = isRunning ? '0.5' : '1';
            stopBtn.style.opacity = !isRunning ? '0.5' : '1';

        } catch (e) {
            statusText.innerText = 'OFFLINE';
            statusPulse.style.background = 'var(--danger)';
            statusPulse.style.animation = 'none';
        }
    }

    async function fetchLogs() {
        try {
            const resp = await fetch('/logs?limit=50');
            const logs = await resp.json();

            processStats(logs);
            updateAgents(logs);
            renderLogs(logs);

            // Update regime from logs
            const latestRegime = logs.find(l => l.event_type === 'regime_change');
            if (latestRegime) {
                regimeVal.innerText = latestRegime.data.regime;
                regimeVal.style.color = latestRegime.data.regime === 'TRENDING' ? 'var(--accent)' : 'var(--warning)';
            }
        } catch (e) {
            console.error('Failed to fetch logs', e);
        }
    }

    function processStats(logs) {
        const signalCount = logs.filter(l => l.event_type.includes('signal')).length;
        const orderCount = logs.filter(l => l.event_type.includes('order')).length;

        statSignals.innerText = signalCount;
        statOrders.innerText = orderCount;
    }

    function updateAgents(logs) {
        const uniqueAgents = [...new Set(logs.map(l => l.agent_name))];

        if (uniqueAgents.length === 0) return;

        agentsContainer.innerHTML = uniqueAgents.map(name => {
            const lastLog = logs.find(l => l.agent_name === name);
            const isRecent = (new Date() - new Date(lastLog.timestamp)) < 60000; // Active if logged in last 60s

            return `
                <div class="agent-card ${isRecent ? 'status-active' : 'status-idle'}">
                    <div class="agent-info">
                        <span class="agent-status-dot"></span>
                        <span class="agent-name">${name}</span>
                    </div>
                    <div class="agent-meta text-muted" style="font-size: 0.7rem; margin-top: 0.5rem;">
                        Last seen: ${new Date(lastLog.timestamp).toLocaleTimeString()}
                    </div>
                </div>
            `;
        }).join('');
    }

    function renderLogs(logs) {
        if (logs.length === 0) {
            logContainer.innerHTML = '<div class="empty-state text-muted" style="padding: 1rem;">No logs found</div>';
            return;
        }

        logContainer.innerHTML = logs.map(log => {
            const date = new Date(log.timestamp).toLocaleTimeString();
            let typeClass = '';

            if (log.event_type.includes('signal')) {
                typeClass = 'type-signal';
            } else if (log.event_type.includes('order')) {
                typeClass = 'type-order';
            } else if (log.event_type.includes('error')) {
                typeClass = 'type-error';
            }

            return `
                <div class="log-entry">
                    <span class="log-ts">${date}</span>
                    <span class="log-agent">${log.agent_name}</span>
                    <span class="log-type ${typeClass}">${log.event_type}</span>
                    <span class="log-msg">${typeof log.data === 'string' ? log.data : JSON.stringify(log.data)}</span>
                </div>
            `;
        }).join('');

    }

    startBtn.addEventListener('click', async () => {
        try {
            await fetch('/start', { method: 'POST' });
            updateStatus();
        } catch (e) {
            console.error('Start failed', e);
        }
    });

    stopBtn.addEventListener('click', async () => {
        try {
            await fetch('/stop', { method: 'POST' });
            updateStatus();
        } catch (e) {
            console.error('Stop failed', e);
        }
    });

    clearLogsBtn.addEventListener('click', () => {
        logContainer.innerHTML = '<div class="log-entry system-msg">Logs cleared (locally)</div>';
    });

    // Navigation logic
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const view = item.getAttribute('data-view');
            if (view === 'agents') {
                document.querySelector('.agents-section').scrollIntoView({ behavior: 'smooth' });
            } else if (view === 'logs') {
                document.querySelector('.audit-section').scrollIntoView({ behavior: 'smooth' });
            } else {
                window.scrollTo({ top: 0, behavior: 'smooth' });
            }
        });
    });

    // Initial load
    updateStatus();
    fetchLogs();

    // Polling
    setInterval(updateStatus, 5000);
    setInterval(fetchLogs, 3000);
});
