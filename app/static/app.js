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

            if (data.agents) {
                updateAgents(data.agents);
            }

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

    function updateAgents(agents) {
        // Mini view (Dashboard)
        const miniContainer = document.getElementById('agents-container-mini');
        if (miniContainer) {
            miniContainer.innerHTML = agents.map(agent => `
                <div class="agent-card ${agent.is_running ? 'status-active' : 'status-idle'}">
                    <div class="agent-info">
                        <span class="agent-status-dot"></span>
                        <span class="agent-name">${agent.name}</span>
                    </div>
                    <div class="agent-meta text-muted" style="font-size: 0.7rem; margin-top: 0.5rem;">
                        Type: ${agent.type}
                    </div>
                </div>
            `).join('');
        }

        // Full view (Agents tab)
        const fullContainer = document.getElementById('agents-container-full');
        if (fullContainer) {
            fullContainer.innerHTML = agents.map(agent => {
                const configEntries = Object.entries(agent.config || {});
                const configHtml = configEntries.length > 0
                    ? `<div class="agent-config-box" style="margin-top: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase; font-weight: bold;">Configuration</div>
                        ${configEntries.map(([k, v]) => `
                            <div class="agent-stat-row" style="border-bottom: none; padding: 2px 0;">
                                <span class="agent-stat-label" style="font-size: 0.75rem;">${k}</span>
                                <span class="agent-stat-value" style="font-size: 0.75rem;">${v}</span>
                            </div>
                        `).join('')}
                       </div>`
                    : '';

                return `
                    <div class="agent-card-detailed ${agent.is_running ? 'status-active' : 'status-idle'}">
                        <div class="agent-header">
                            <div class="agent-title-box">
                                <span class="agent-status-dot"></span>
                                <h4>${agent.name}</h4>
                            </div>
                            <span class="agent-badge">${agent.type}</span>
                        </div>
                        <div class="agent-body">
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Status</span>
                                <span class="agent-stat-value" style="color: ${agent.is_running ? 'var(--success)' : 'var(--danger)'}">
                                    ${agent.is_running ? 'RUNNING' : 'STOPPED'}
                                </span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Thread Health</span>
                                <span class="agent-stat-value">Excellent</span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Last Ping</span>
                                <span class="agent-stat-value">${new Date().toLocaleTimeString()}</span>
                            </div>
                            ${configHtml}
                            <div class="agent-actions">
                                <button class="btn btn-small btn-glow-success restart-agent" data-agent="${agent.name}">
                                    <i data-lucide="refresh-cw"></i> RESTART
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        if (window.lucide) lucide.createIcons();

        // Add event listeners for restart buttons
        document.querySelectorAll('.restart-agent').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const name = btn.getAttribute('data-agent');
                btn.disabled = true;
                btn.innerHTML = '<i data-lucide="loader"></i> ...';
                if (window.lucide) lucide.createIcons();

                try {
                    await fetch(`/agents/restart/${name}`, { method: 'POST' });
                    setTimeout(updateStatus, 1000); // Wait bit for restart
                } catch (e) {
                    console.error('Restart failed', e);
                    btn.disabled = false;
                    btn.innerHTML = '<i data-lucide="refresh-cw"></i> RESTART';
                    if (window.lucide) lucide.createIcons();
                }
            };
        });
    }

    function renderLogs(logs) {
        if (logs.length === 0) {
            const empty = '<div class="empty-state text-muted" style="padding: 1rem;">No logs found</div>';
            const mini = document.getElementById('log-container-mini');
            const full = document.getElementById('log-container-full');
            if (mini) mini.innerHTML = empty;
            if (full) full.innerHTML = empty;
            return;
        }

        const logHtml = logs.map(log => {
            const date = new Date(log.timestamp).toLocaleTimeString();
            let typeClass = '';
            let msg = typeof log.data === 'string' ? log.data : JSON.stringify(log.data);

            if (log.event_type.includes('signal')) {
                typeClass = 'type-signal';
            } else if (log.event_type.includes('order')) {
                typeClass = 'type-order';
            } else if (log.event_type.includes('error')) {
                typeClass = 'type-error';
            } else if (log.event_type === 'market_data') {
                // Task 1: Format market_data event (summarized)
                const d = typeof log.data === 'string' ? JSON.parse(log.data) : log.data;
                const candleCount = d.candles ? d.candles.length : 0;
                msg = `<span style="color: var(--accent); font-weight: bold;">${d.symbol}</span> | ${d.timeframe} | ${candleCount} candles received | Close: ${d.latest_close}`;
            }

            return `
                <div class="log-entry">
                    <span class="log-ts">${date}</span>
                    <span class="log-agent">${log.agent_name}</span>
                    <span class="log-type ${typeClass}">${log.event_type}</span>
                    <span class="log-msg">${msg}</span>
                </div>
            `;
        }).join('');

        const mini = document.getElementById('log-container-mini');
        const full = document.getElementById('log-container-full');
        if (mini) mini.innerHTML = logHtml;
        if (full) full.innerHTML = logHtml;
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
        const msg = '<div class="log-entry system-msg">Logs cleared (locally)</div>';
        const mini = document.getElementById('log-container-mini');
        const full = document.getElementById('log-container-full');
        if (mini) mini.innerHTML = msg;
        if (full) full.innerHTML = msg;
    });

    // Navigation logic
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            item.classList.add('active');

            const viewId = item.getAttribute('data-view');

            // Hide all views
            document.querySelectorAll('.view').forEach(v => v.style.display = 'none');

            // Show target view
            const targetView = document.getElementById(`view-${viewId}`);
            if (targetView) {
                targetView.style.display = 'block';
                // Trigger icon refresh for the new view
                if (window.lucide) lucide.createIcons();
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
