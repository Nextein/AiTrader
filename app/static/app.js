document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const startBtn = document.getElementById('start-btn');
    const stopBtn = document.getElementById('stop-btn');
    const emergencyBtn = document.getElementById('emergency-btn');
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
    let equityChart = null;

    async function updateStatus() {
        try {
            const resp = await fetch('/status');
            if (!resp.ok) throw new Error('Offline');
            const data = await resp.json();

            isRunning = data.is_running;
            statusText.innerText = isRunning ? 'SYSTEM ACTIVE' : 'SYSTEM IDLE';
            statusPulse.style.background = isRunning ? 'var(--success)' : 'var(--text-secondary)';
            statusPulse.style.animation = isRunning ? 'pulse 2s infinite' : 'none';

            symbolVal.innerText = Array.isArray(data.config.symbols) ? data.config.symbols.join(', ') : data.config.symbol;

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
                </div>
            `).join('');
        }

        // Full view (Agents tab)
        const fullContainer = document.getElementById('agents-container-full');
        const healthyThreadsVal = document.getElementById('healthy-threads-val');

        if (healthyThreadsVal) {
            const runningCount = agents.filter(a => a.is_running).length;
            healthyThreadsVal.innerText = `${runningCount}/${agents.length}`;
        }

        if (fullContainer) {
            fullContainer.innerHTML = agents.map(agent => {
                const configEntries = Object.entries(agent.config || {});
                const configHtml = configEntries.length > 0
                    ? `<div class="agent-config-box" style="margin-top: 1rem; padding: 0.75rem; background: rgba(0,0,0,0.2); border-radius: 8px;">
                        <div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 0.5rem; text-transform: uppercase; font-weight: bold;">Configuration</div>
                        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 4px;">
                            ${configEntries.map(([k, v]) => `
                                <div style="font-size: 0.7rem; color: var(--text-secondary)">${k}:</div>
                                <div style="font-size: 0.7rem; text-align: right; color: var(--accent)">${v}</div>
                            `).join('')}
                        </div>
                       </div>`
                    : '';

                const isActive = agent.is_active !== undefined ? agent.is_active : true;
                const cardOpacity = isActive ? '1' : '0.5';
                const cardFilter = isActive ? 'none' : 'grayscale(50%)';

                return `
                    <div class="agent-card-detailed ${agent.is_running ? 'status-active' : 'status-idle'}" style="opacity: ${cardOpacity}; filter: ${cardFilter};">
                        <div class="agent-header">
                            <div class="agent-title-box">
                                <span class="agent-status-dot"></span>
                                <h4>${agent.name}</h4>
                            </div>
                            <span class="agent-badge">${agent.type}</span>
                        </div>
                        <div class="agent-body">
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Communication Role</span>
                                <span class="agent-stat-value">${getAgentRole(agent.name)}</span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Activation</span>
                                <label class="toggle-switch">
                                    <input type="checkbox" class="activation-toggle" data-agent="${agent.name}" ${isActive ? 'checked' : ''}>
                                    <span class="toggle-slider"></span>
                                </label>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Uptime</span>
                                <span class="agent-stat-value">${formatUptime(agent.uptime)}</span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Events Processed</span>
                                <span class="agent-stat-value">${agent.processed_count || 0}</span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Status</span>
                                <span class="agent-stat-value" style="color: ${agent.is_running ? 'var(--success)' : 'var(--danger)'}">
                                    ${agent.is_running ? 'RUNNING' : 'IDLE'}
                                </span>
                            </div>
                            ${configHtml}
                            <div class="agent-actions">
                                <button class="btn btn-small btn-glow-success restart-agent" data-agent="${agent.name}" ${!isActive ? 'disabled' : ''}>
                                    <i data-lucide="refresh-cw"></i> RESTART
                                </button>
                                <button class="btn btn-small btn-icon view-events" data-agent="${agent.name}" title="View Events">
                                    <i data-lucide="list"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `;
            }).join('');
        }

        updateFlowStates(agents);

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

        // Add event listeners for activation toggles (Task 2)
        document.querySelectorAll('.activation-toggle').forEach(toggle => {
            toggle.onchange = async (e) => {
                const name = toggle.getAttribute('data-agent');
                const isActive = toggle.checked;

                try {
                    const endpoint = isActive ? 'activate' : 'deactivate';
                    const resp = await fetch(`/agents/${name}/${endpoint}`, { method: 'POST' });
                    const result = await resp.json();

                    if (resp.ok) {
                        console.log(`Agent ${name} ${endpoint}d:`, result);
                        setTimeout(updateStatus, 500); // Refresh UI
                    } else {
                        console.error(`Failed to ${endpoint} agent:`, result);
                        toggle.checked = !isActive; // Revert toggle
                    }
                } catch (e) {
                    console.error('Activation toggle failed', e);
                    toggle.checked = !isActive; // Revert toggle
                }
            };
        });

        // Add event listeners for view events buttons (Task 1)
        document.querySelectorAll('.view-events').forEach(btn => {
            btn.onclick = async (e) => {
                e.stopPropagation();
                const name = btn.getAttribute('data-agent');
                await showAgentEvents(name);
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

        // Visual pulse in flow diagram
        if (logs.length > 0) {
            triggerFlowPulse(logs[0]);
        }
    }

    function triggerFlowPulse(latestLog) {
        const type = latestLog.event_type;
        const agent = latestLog.agent_name;

        let nodeId = null;
        if (type === 'market_data' || agent.includes('Market')) nodeId = 'node-market';
        else if (type === 'regime_change' || agent.includes('Regime') || type.includes('anomaly')) nodeId = 'node-analysis';
        else if (type.includes('signal') || agent.includes('Strategy')) nodeId = 'node-strategy';
        else if (agent.includes('Risk')) nodeId = 'node-risk';
        else if (type.includes('order') || agent.includes('Execution')) nodeId = 'node-execution';

        if (nodeId) {
            const el = document.getElementById(nodeId);
            if (el) {
                el.classList.add('pulse-active');
                setTimeout(() => el.classList.remove('pulse-active'), 1000);
            }
        }
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

    emergencyBtn.addEventListener('click', async () => {
        if (!confirm('!!! EMERGENCY STOP !!!\nThis will CLOSE ALL POSITIONS and stop the system. Are you sure?')) return;

        emergencyBtn.disabled = true;
        emergencyBtn.innerText = 'CLOSING...';

        try {
            await fetch('/emergency-stop', { method: 'POST' });
            updateStatus();
            alert('Emergency stop command issued successfully.');
        } catch (e) {
            console.error('Emergency stop failed', e);
            alert('Failed to issue emergency stop!');
        } finally {
            emergencyBtn.disabled = false;
            emergencyBtn.innerHTML = '<i data-lucide="alert-triangle"></i> EMERGENCY STOP';
            if (window.lucide) lucide.createIcons();
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

    function formatUptime(seconds) {
        if (!seconds) return '--';
        if (seconds < 60) return `${seconds}s`;
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    }

    function getAgentRole(name) {
        const roles = {
            'MarketData': 'Data Producer',
            'RegimeDetection': 'Analyst',
            'AnomalyDetection': 'Watchdog',
            'EMACrossStrategy': 'Strategist',
            'Strategy': 'Strategist',
            'Risk': 'Gatekeeper',
            'Execution': 'Executor',
            'AuditLog': 'Historian',
            'Aggregator': 'Reporter',
            'Governor': 'Orchestrator'
        };
        for (const [key, role] of Object.entries(roles)) {
            if (name.includes(key)) return role;
        }
        return 'Participant';
    }

    function updateFlowStates(agents) {
        // Simple logic to highlight flow nodes based on running agents
        const hasMarket = agents.some(a => a.name.includes('MarketData') && a.is_running);
        const hasAnalysis = agents.some(a => (a.name.includes('Regime') || a.name.includes('Anomaly')) && a.is_running);
        const hasStrategy = agents.some(a => (a.name.includes('Strategy')) && a.is_running);
        const hasRisk = agents.some(a => a.name.includes('Risk') && a.is_running);
        const hasExecution = agents.some(a => a.name.includes('Execution') && a.is_running);

        if (hasMarket) document.getElementById('node-market')?.classList.add('active');
        else document.getElementById('node-market')?.classList.remove('active');

        if (hasAnalysis) document.getElementById('node-analysis')?.classList.add('active');
        else document.getElementById('node-analysis')?.classList.remove('active');

        if (hasStrategy) document.getElementById('node-strategy')?.classList.add('active');
        else document.getElementById('node-strategy')?.classList.remove('active');

        if (hasRisk) document.getElementById('node-risk')?.classList.add('active');
        else document.getElementById('node-risk')?.classList.remove('active');

        if (hasExecution) document.getElementById('node-execution')?.classList.add('active');
        else document.getElementById('node-execution')?.classList.remove('active');
    }

    async function updateEquityChart() {
        try {
            const resp = await fetch('/equity');
            const data = await resp.json();

            if (data.length === 0) return;

            const labels = data.map(d => new Date(d.timestamp).toLocaleTimeString());
            const values = data.map(d => d.total_equity);

            if (!equityChart) {
                const ctx = document.getElementById('equity-chart').getContext('2d');
                equityChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Total Equity (USDT)',
                            data: values,
                            borderColor: '#00f2fe',
                            backgroundColor: 'rgba(0, 242, 254, 0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: false }
                        },
                        scales: {
                            y: {
                                grid: { color: 'rgba(255,255,255,0.05)' },
                                ticks: { color: '#8b949e' }
                            },
                            x: {
                                grid: { display: false },
                                ticks: { color: '#8b949e' }
                            }
                        }
                    }
                });
            } else {
                equityChart.data.labels = labels;
                equityChart.data.datasets[0].data = values;
                equityChart.update();
            }
        } catch (e) {
            console.error('Failed to fetch equity data', e);
        }
    }

    async function showAgentEvents(agentName) {
        try {
            const resp = await fetch(`/agents/${agentName}/events?limit=50`);
            const data = await resp.json();

            const modal = document.getElementById('agent-events-modal');
            const modalTitle = document.getElementById('modal-agent-name');
            const eventsContainer = document.getElementById('modal-events-list');

            modalTitle.innerText = agentName;

            if (data.events && data.events.length > 0) {
                eventsContainer.innerHTML = data.events.map(event => {
                    const time = new Date(event.timestamp).toLocaleTimeString();
                    const priorityColor = {
                        'CRITICAL': 'var(--danger)',
                        'HIGH': 'var(--warning)',
                        'NORMAL': 'var(--accent)',
                        'LOW': 'var(--text-secondary)'
                    }[event.priority] || 'var(--text-secondary)';

                    let eventData = typeof event.data === 'string' ? event.data : JSON.stringify(event.data, null, 2);

                    return `
                        <div class="event-item">
                            <div class="event-header">
                                <span class="event-time">${time}</span>
                                <span class="event-type">${event.event_type}</span>
                                <span class="event-priority" style="background: ${priorityColor};">${event.priority}</span>
                            </div>
                            <div class="event-data"><pre>${eventData}</pre></div>
                        </div>
                    `;
                }).join('');
            } else {
                eventsContainer.innerHTML = '<div class="empty-state">No events found for this agent</div>';
            }

            modal.style.display = 'flex';
        } catch (e) {
            console.error('Failed to fetch agent events', e);
            alert('Failed to load agent events');
        }
    }

    // Close modal handlers
    const modal = document.getElementById('agent-events-modal');
    const closeBtn = document.getElementById('close-modal');

    if (closeBtn) {
        closeBtn.onclick = () => {
            modal.style.display = 'none';
        };
    }

    if (modal) {
        modal.onclick = (e) => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        };
    }

    // Initial load
    updateStatus();
    fetchLogs();
    updateEquityChart();

    // Polling
    setInterval(updateStatus, 5000);
    setInterval(fetchLogs, 3000);
    setInterval(updateEquityChart, 10000);
});
