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
    const modeVal = document.getElementById('mode-value');
    const clearLogsBtn = document.getElementById('clear-logs');

    // New Elements
    const portfolioBody = document.getElementById('portfolio-body');
    const regimeBody = document.getElementById('regime-body');
    const tradeHistoryBody = document.getElementById('trade-history-body');

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

            if (modeVal) {
                const isDemo = data.config.demo_mode;
                modeVal.innerText = isDemo ? 'DEMO' : 'LIVE';
                const modeIndicator = document.getElementById('mode-indicator');
                if (modeIndicator) {
                    modeIndicator.className = isDemo ? 'mode-badge demo' : 'mode-badge live';
                }
            }

            // Update button states
            startBtn.disabled = isRunning;
            stopBtn.disabled = !isRunning;
            startBtn.style.opacity = isRunning ? '0.5' : '1';
            stopBtn.style.opacity = !isRunning ? '0.5' : '1';


            if (data.agents) {
                updateAgents(data.agents);
                updateRegimes(data.agents); // Task 7
            }

        } catch (e) {
            statusText.innerText = 'OFFLINE';
            statusPulse.style.background = 'var(--danger)';
            statusPulse.style.animation = 'none';
        }
    }

    async function fetchPortfolio() { // Task 1
        try {
            const resp = await fetch('/portfolio');
            const positions = await resp.json();
            renderPortfolio(positions);
        } catch (e) { console.error('Portfolio fetch failed', e); }
    }

    async function fetchTrades() { // Task 2
        try {
            const resp = await fetch('/trades?limit=50');
            const trades = await resp.json();
            renderTrades(trades);
        } catch (e) { console.error('Trades fetch failed', e); }
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
                <div class="agent-card ${agent.is_running ? 'status-active' : 'status-idle'}" data-agent="${agent.name}">
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

                const tasksHtml = (agent.tasks || []).length > 0
                    ? `<div class="agent-metadata-box">
                        <div class="agent-metadata-title"><i data-lucide="check-circle" style="width:12px"></i> Tasks</div>
                        <ul class="agent-metadata-list">
                            ${agent.tasks.map(t => `<li>${t}</li>`).join('')}
                        </ul>
                       </div>`
                    : '';

                const respHtml = (agent.responsibilities || []).length > 0
                    ? `<div class="agent-metadata-box">
                        <div class="agent-metadata-title"><i data-lucide="shield" style="width:12px"></i> Responsibilities</div>
                        <ul class="agent-metadata-list">
                            ${agent.responsibilities.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                       </div>`
                    : '';

                const promptsHtml = (agent.prompts || []).length > 0
                    ? `<div class="agent-metadata-box">
                        <div class="agent-metadata-title"><i data-lucide="file-text" style="width:12px"></i> Prompts</div>
                        <div class="prompt-tags-container">
                            ${agent.prompts.map(p => `<span class="prompt-tag" data-prompt="${p}">${p}</span>`).join('')}
                        </div>
                       </div>`
                    : '';

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
                            <div class="agent-desc">${agent.description || 'No description provided.'}</div>
                            
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Uptime</span>
                                <span class="agent-stat-value">${formatUptime(agent.uptime)}</span>
                            </div>
                            <div class="agent-stat-row">
                                <span class="agent-stat-label">Events</span>
                                <span class="agent-stat-value">${agent.processed_count || 0}</span>
                            </div>
                            
                            ${tasksHtml}
                            ${respHtml}
                            ${promptsHtml}
                            ${configHtml}

                            <div class="agent-actions" style="margin-top: 1rem;">
                                <div style="display: flex; align-items: center; gap: 0.5rem; flex: 1;">
                                    <label class="toggle-switch">
                                        <input type="checkbox" class="activation-toggle" data-agent="${agent.name}" ${isActive ? 'checked' : ''}>
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <span style="font-size: 0.7rem; color: var(--text-secondary)">Active</span>
                                </div>
                                <button class="btn btn-small btn-glow-success restart-agent" data-agent="${agent.name}" ${!isActive ? 'disabled' : ''}>
                                    <i data-lucide="refresh-cw"></i>
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

    function updateRegimes(agents) {
        // Find RegimeDetectionAgent and extract 'regimes' data
        const regimeAgent = agents.find(a => a.name === 'RegimeDetectionAgent');
        if (!regimeAgent || !regimeAgent.data || !regimeAgent.data.regimes || !regimeBody) return;

        const regimes = regimeAgent.data.regimes;
        const entries = Object.entries(regimes);

        if (entries.length === 0) {
            regimeBody.innerHTML = '<tr><td colspan="4" class="empty-cell">No regime data yet</td></tr>';
            return;
        }

        regimeBody.innerHTML = entries.map(([symbol, regime]) => {
            const color = regime === 'TRENDING' ? 'var(--success)' : 'var(--warning)';
            // We don't have per-symbol ADX here readily unless we store it in the agent.
            // For now, just show regime.
            return `
                <tr>
                    <td><span style="font-weight: bold; color: var(--text-primary)">${symbol}</span></td>
                    <td><span style="color: ${color}; font-weight: bold; padding: 2px 6px; background: rgba(255,255,255,0.05); border-radius: 4px;">${regime}</span></td>
                    <td>--</td>
                    <td>${new Date().toLocaleTimeString()}</td>
                </tr>
            `;
        }).join('');
    }

    function renderPortfolio(orders) {
        if (!portfolioBody) return;
        if (orders.length === 0) {
            portfolioBody.innerHTML = '<tr><td colspan="7" class="empty-cell">No open positions</td></tr>';
            return;
        }

        portfolioBody.innerHTML = orders.map(o => {
            const sideClass = o.side === 'buy' ? 'pos-buy' : 'pos-sell';

            // Format current price
            const currentPrice = o.current_price !== null && o.current_price !== undefined ? o.current_price.toFixed(2) : '--';

            // Format unrealized PnL with color coding
            let pnlDisplay = '--';
            let pnlClass = '';
            if (o.unrealized_pnl !== null && o.unrealized_pnl !== undefined) {
                const pnlValue = o.unrealized_pnl.toFixed(2);
                const pnlPct = o.unrealized_pnl_pct !== null && o.unrealized_pnl_pct !== undefined ? o.unrealized_pnl_pct.toFixed(2) : '0.00';
                pnlDisplay = `${pnlValue} (${pnlPct}%)`;
                pnlClass = o.unrealized_pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
            }

            const sl = o.sl_price ? (Array.isArray(o.sl_price) ? o.sl_price.join(', ') : o.sl_price) : '--';
            const tp = o.tp_price ? (Array.isArray(o.tp_price) ? o.tp_price.join(', ') : o.tp_price) : '--';

            return `
                <tr>
                    <td><b>${o.symbol}</b></td>
                    <td class="${sideClass}">${o.side.toUpperCase()}</td>
                    <td>${o.amount.toFixed(4)}</td>
                    <td>${o.price.toFixed(2)}</td>
                    <td>${currentPrice}</td>
                    <td class="${pnlClass}">${pnlDisplay}</td>
                   <td><span style="font-size: 0.8rem">SL: ${sl}<br>TP: ${tp}</span></td>
                </tr>
            `;
        }).join('');
    }

    function renderTrades(trades) {
        if (!tradeHistoryBody) return;
        if (trades.length === 0) {
            tradeHistoryBody.innerHTML = '<tr><td colspan="8" class="empty-cell">No trade history</td></tr>';
            return;
        }

        tradeHistoryBody.innerHTML = trades.map(t => {
            const sideClass = t.side === 'buy' ? 'pos-buy' : 'pos-sell';
            const pnlClass = t.pnl >= 0 ? 'pnl-pos' : 'pnl-neg';
            const date = new Date(t.closed_at || t.timestamp).toLocaleString();

            return `
                <tr>
                    <td>${date}</td>
                    <td>${t.symbol}</td>
                    <td class="${sideClass}">${t.side.toUpperCase()}</td>
                    <td>${t.amount.toFixed(4)}</td>
                    <td>${t.price.toFixed(2)}</td>
                    <td>${t.exit_price ? t.exit_price.toFixed(2) : '--'}</td>
                    <td class="${pnlClass}">${t.pnl ? t.pnl.toFixed(2) : '--'}</td>
                    <td style="font-size: 0.8rem; color: var(--text-secondary);">${t.rationale || '--'}</td>
                </tr>
            `;
        }).join('');
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
            let msgClass = '';
            let msg = typeof log.data === 'string' ? log.data : JSON.stringify(log.data);
            const lowerMsg = msg.toLowerCase();

            // Heuristic for message color
            if (lowerMsg.includes('error') || lowerMsg.includes('failed') || lowerMsg.includes('exception') || lowerMsg.includes('critical')) {
                msgClass = 'error';
            } else if (lowerMsg.includes('warning') || lowerMsg.includes('warn')) {
                msgClass = 'warning';
            } else if (lowerMsg.includes('success') || lowerMsg.includes('completed') || lowerMsg.includes('connected') || lowerMsg.includes('initialized')) {
                msgClass = 'success';
            }

            if (log.event_type.includes('signal')) {
                typeClass = 'type-signal';
            } else if (log.event_type.includes('order')) {
                typeClass = 'type-order';
            } else if (log.event_type.includes('error')) {
                typeClass = 'type-error';
                msgClass = 'error'; // Ensure error events are always red
            } else if (log.event_type === 'market_data') {
                typeClass = 'type-market';
                // Task 8: Making logs beautiful (enhanced market data)
                const d = typeof log.data === 'string' ? JSON.parse(log.data) : log.data;
                const candleCount = d.candles || 0;
                msg = `<span class="text-muted">${d.symbol}</span> <span class="text-accent">${d.latest_close.toFixed(2)}</span> (${candleCount} candles)`;
            } else if (log.event_type === 'agent_log') {
                typeClass = 'type-regime'; // Using a distinct color
                const d = typeof log.data === 'string' ? JSON.parse(log.data) : log.data;
                const level = d.level || 'INFO';
                if (level === 'ERROR') msgClass = 'error';
                else if (level === 'WARNING') msgClass = 'warning';

                if (d.type === 'llm_call') {
                    msg = `<span class="text-accent">[LLM] ${d.prompt_name}</span> ${d.symbol ? `for ${d.symbol}` : ''}`;
                    if (d.result) {
                        msg += ` <span class="text-muted">→ ${JSON.stringify(d.result).substring(0, 100)}...</span>`;
                    }
                } else if (d.type === 'market_action') {
                    msg = `<span style="color: #00f2fe">[Market] ${d.action}</span> for ${d.symbol}`;
                } else {
                    msg = d.message || JSON.stringify(d);
                }
            } else if (log.event_type === 'order_request' || log.event_type === 'order_filled') {
                // Task 8: Beautiful orders
                const d = typeof log.data === 'string' ? JSON.parse(log.data) : log.data;
                const sideColor = d.side === 'buy' ? 'var(--success)' : 'var(--danger)';
                const status = d.status || 'REQUESTED';
                msg = `<span style="font-weight: bold; color: ${sideColor}">${d.side.toUpperCase()} ${d.symbol}</span> | Amt: ${d.amount.toFixed(4)} | Status: ${status}`;
            }

            return `
                <div class="log-entry">
                    <span class="log-ts">${date}</span>
                    <span class="log-agent">${log.agent_name}</span>
                    <span class="log-type ${typeClass}">${log.event_type}</span>
                    <span class="log-msg ${msgClass}">${msg}</span>
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

        // 1. Pulse the specific agent card in dashboard
        const agentCard = document.querySelector(`.agent-card[data-agent="${agent}"]`);
        if (agentCard) {
            agentCard.classList.add('pulse-active');
            setTimeout(() => agentCard.classList.remove('pulse-active'), 1000);
        }

        // 2. Pulse the flow node in sidebar
        let nodeId = null;
        if (type === 'market_data' || agent.includes('Market')) nodeId = 'node-market';
        else if (type === 'regime_change' || agent.includes('Regime') || type === 'analysis_update' || type.includes('anomaly')) nodeId = 'node-analysis';
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

    // Prompt Viewer Modal logic
    const promptModal = document.getElementById('prompt-modal');
    const closePromptBtn = document.getElementById('close-prompt-modal');

    if (closePromptBtn) {
        closePromptBtn.onclick = () => {
            promptModal.style.display = 'none';
        };
    }

    if (promptModal) {
        promptModal.onclick = (e) => {
            if (e.target === promptModal) {
                promptModal.style.display = 'none';
            }
        };
    }

    async function showPromptContent(promptPath) {
        try {
            const resp = await fetch(`/prompts/${promptPath}`);
            const data = await resp.json();

            document.getElementById('modal-prompt-name').innerText = promptPath;
            document.getElementById('prompt-system-content').innerText = data.system || '-- Empty --';
            document.getElementById('prompt-user-content').innerText = data.user || '-- Empty --';

            promptModal.style.display = 'flex';
        } catch (e) {
            console.error('Failed to fetch prompt content', e);
            alert('Failed to load prompt content');
        }
    }

    // Delegation for prompt tags
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('prompt-tag')) {
            const path = e.target.getAttribute('data-prompt');
            showPromptContent(path);
        }
    });

    // Intelligence Page Logic
    let selectedAnalysisSymbol = null;
    let analysisSymbols = [];

    async function fetchAnalysisSymbols() {
        try {
            const resp = await fetch('/analysis/symbols');
            analysisSymbols = await resp.json();
            renderAnalysisSymbolList();
        } catch (e) {
            console.error('Failed to fetch analysis symbols', e);
        }
    }

    function renderAnalysisSymbolList() {
        const container = document.getElementById('analysis-symbol-list');
        const searchInput = document.getElementById('symbol-search');
        if (!container) return;

        const filter = searchInput ? searchInput.value.toUpperCase() : '';

        const filtered = analysisSymbols.filter(s => s.toUpperCase().includes(filter));

        if (filtered.length === 0) {
            container.innerHTML = '<div class="empty-state">No symbols found</div>';
            return;
        }

        container.innerHTML = filtered.map(symbol => `
            <div class="symbol-item ${selectedAnalysisSymbol === symbol ? 'active' : ''}" data-symbol="${symbol}">
                <span>${symbol}</span>
                <i data-lucide="chevron-right" style="width: 14px;"></i>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();

        // Add click listeners
        container.querySelectorAll('.symbol-item').forEach(item => {
            item.onclick = () => {
                selectedAnalysisSymbol = item.getAttribute('data-symbol');
                renderAnalysisSymbolList(); // Update active state
                fetchAnalysisData(selectedAnalysisSymbol);
            };
        });
    }

    async function fetchAnalysisData(symbol) {
        if (!symbol) return;

        try {
            const resp = await fetch(`/analysis/${encodeURIComponent(symbol)}`);
            const data = await resp.json();
            renderAnalysisData(data);
        } catch (e) {
            console.error('Failed to fetch analysis data', e);
        }
    }

    function renderAnalysisData(data) {
        const placeholder = document.getElementById('analysis-placeholder');
        const header = document.getElementById('analysis-content-header');
        const grid = document.getElementById('analysis-data-container');

        if (!placeholder || !header || !grid) return;

        placeholder.style.display = 'none';
        header.style.display = 'flex';
        grid.style.display = 'grid';

        document.getElementById('current-analysis-symbol').innerText = data.symbol || 'N/A';
        document.getElementById('analysis-state-badge').innerText = data.analysis_state || 'UNKNOWN';
        document.getElementById('analysis-created-date').innerText = data.date_created ? new Date(data.date_created * 1000).toLocaleString() : '--';
        document.getElementById('analysis-sync-time').innerText = new Date().toLocaleTimeString();

        let html = '';

        // Helper to format values
        const fmt = (val, precision = 2) => {
            if (val === undefined || val === null) return '--';
            if (typeof val === 'number') return val.toFixed(precision);
            return val;
        };

        const getStatusClass = (val) => {
            const v = String(val).toUpperCase();
            if (['UP', 'TRENDING', 'HIGHER', 'BULLISH', 'TRUE', '1', 'ASCENDING', 'EXPANDING'].includes(v)) return 'state-positive';
            if (['DOWN', 'LOWER', 'BEARISH', 'FALSE', '-1', 'DESCENDING'].includes(v)) return 'state-negative';
            if (['NEUTRAL', 'RANGING', 'UNDEFINED', '0', 'UNKNOWN'].includes(v)) return 'state-neutral';
            return '';
        };

        // 1. Market Regime & High Level Intel
        if (data.market_regime) {
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="compass"></i> Market Regime</h4>
                    <div class="data-grid">
            `;
            const tfs = ['4h', '1h', '15m', '5m'];
            tfs.forEach(tf => {
                const regime = data.market_regime[tf];
                if (!regime) return;
                html += `
                    <div class="data-item">
                        <div class="data-label">${tf} Regime</div>
                        <div class="data-value ${getStatusClass(regime)}">${regime}</div>
                    </div>
                `;
            });
            html += `</div></div>`;
        }

        // 1b. Unified Analysis (Master Bias)
        if (data.unified_analysis) {
            html += `
                <div class="analysis-section-card highlight">
                    <h4><i data-lucide="user-check"></i> Master Analyst Summary</h4>
                    <div style="padding: 1rem; background: rgba(0,242,254,0.05); border-radius: 8px; margin-bottom: 1rem;">
                        <div style="font-weight: bold; color: var(--accent); margin-bottom: 0.5rem;">BIAS: ${data.unified_analysis.primary_bias}</div>
                        <div style="font-size: 0.9rem; line-height: 1.5;">${data.unified_analysis.summary}</div>
                    </div>
                    <div class="data-grid">
                        ${(data.unified_analysis.top_setups || []).map(s => `
                            <div class="data-item">
                                <div class="data-label">${s.strategy} (${s.timeframe})</div>
                                <div class="data-value state-positive">${s.reasoning}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // 2. Support & Resistance
        if (data.support_resistance) {
            const sr = data.support_resistance.overall || data.support_resistance['1h'] || {};
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="layers"></i> Support & Resistance</h4>
                    <div class="data-grid">
                        <div class="data-item">
                            <div class="data-label">Closest Support</div>
                            <div class="data-value state-positive">${fmt(sr.closest_support)}</div>
                        </div>
                        <div class="data-item">
                            <div class="data-label">Closest Resistance</div>
                            <div class="data-value state-negative">${fmt(sr.closest_resistance)}</div>
                        </div>
                    </div>
                    ${(sr.confluences || []).length > 0 ? `
                        <div style="margin-top: 1rem; border-top: 1px solid var(--border); padding-top: 0.5rem;">
                            <div class="data-label" style="font-size: 0.7rem;">CONFLUENCES</div>
                            ${sr.confluences.map(c => `
                                <div style="font-size: 0.8rem; display: flex; justify-content: space-between; margin-top: 4px;">
                                    <span>${c.sources.join(' + ')}</span>
                                    <span class="text-accent">${fmt(c.price)}</span>
                                </div>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            `;
        }

        // 3. Fibonacci & CC Channel
        if (data.fibonacci) {
            const fib = data.fibonacci['1h'] || {};
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="hash"></i> Fibonacci & CC Channel</h4>
                    <div class="data-grid">
                        <div class="data-item">
                            <div class="data-label">CC High (66.6%)</div>
                            <div class="data-value text-accent">${fmt(fib.cc_channel?.high)}</div>
                        </div>
                        <div class="data-item">
                            <div class="data-label">CC Low (70.6%)</div>
                            <div class="data-value text-accent">${fmt(fib.cc_channel?.low)}</div>
                        </div>
                        <div class="data-item" style="grid-column: span 2">
                            <div class="data-label">In CC Channel</div>
                            <div class="data-value ${fib.in_cc_channel ? 'state-positive' : 'state-neutral'}">${fib.in_cc_channel ? 'YES' : 'NO'}</div>
                        </div>
                    </div>
                </div>
            `;
        }

        // 4. Anchored VWAP & GP
        if (data.anchored_vwap) {
            const avwap = data.anchored_vwap['1h'] || {};
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="trending-up"></i> Anchored VWAP + GP</h4>
                    <div class="data-grid">
                        ${(avwap.vwaps || []).map(v => `
                            <div class="data-item">
                                <div class="data-label">Anchor @ ${new Date(v.anchor_time).toLocaleTimeString()}</div>
                                <div class="data-value" style="color: #00f2fe">${fmt(v.current_val)}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }

        // 2. Market Structure Analysis
        if (data.market_structure) {
            html += `
                <div class="analysis-section-card" style="grid-column: span 2;">
                    <h4><i data-lucide="layout"></i> Market Structure</h4>
                    <div class="data-grid" style="grid-template-columns: repeat(4, 1fr);">
            `;

            const tfs = ['4h', '1h', '15m', '5m'];
            tfs.forEach(tf => {
                const struct = data.market_structure[tf];
                if (!struct || typeof struct !== 'object') return;

                html += `
                    <div class="tf-row-header" style="grid-column: span 4;">
                        <span class="tf-badge">${tf}</span> Structure
                    </div>
                    <div class="data-item">
                        <div class="data-label">Highs</div>
                        <div class="data-value ${getStatusClass(struct.highs)}">${fmt(struct.highs)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Lows</div>
                        <div class="data-value ${getStatusClass(struct.lows)}">${fmt(struct.lows)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">VA Trend</div>
                        <div class="data-value ${getStatusClass(struct.value_areas)}">${fmt(struct.value_areas || 'NEUTRAL')}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">EMAs Order</div>
                        <div class="data-value ${getStatusClass(struct.emas_in_order)}">${fmt(struct.emas_in_order)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">EMAs Fanning</div>
                        <div class="data-value ${getStatusClass(struct.emas_fanning)}">${fmt(struct.emas_fanning)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Pivot Points</div>
                        <div class="data-value ${getStatusClass(struct.pivot_points)}">${fmt(struct.pivot_points)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">ADX</div>
                        <div class="data-value ${getStatusClass(struct.adx)}">${fmt(struct.adx)}</div>
                    </div>
                    <div class="data-item" style="opacity: 0.5;">
                        <div class="data-label">Last Updated</div>
                        <div class="data-value" style="font-size: 0.7rem;">${struct.last_updated ? new Date(struct.last_updated * 1000).toLocaleTimeString() : '--'}</div>
                    </div>
                `;
            });

            html += `</div></div>`;
        }

        // 3. Key Levels & S/R
        if (data.key_levels) {
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="layers"></i> Supply & Demand Zones</h4>
                    <div class="data-grid">
            `;
            Object.entries(data.key_levels).forEach(([k, v]) => {
                if (k === 'last_updated') return;
                html += `
                    <div class="data-item">
                        <div class="data-label">${k.replace(/_/g, ' ').toUpperCase()}</div>
                        <div class="data-value text-accent">${fmt(v)}</div>
                    </div>
                `;
            });
            html += `</div></div>`;
        }

        // 4. Detailed Indicators Overview
        if (data.market_data) {
            html += `
                <div class="analysis-section-card">
                    <h4><i data-lucide="activity"></i> Oscillator & Volatility</h4>
                    <div class="data-grid">
            `;

            const tfs = ['4h', '1h', '15m', '5m'];
            tfs.forEach(tf => {
                const candles = data.market_data[tf];
                if (!Array.isArray(candles) || candles.length === 0) return;
                const last = candles[candles.length - 1];

                html += `
                    <div class="tf-row-header">
                         <span class="tf-badge">${tf}</span> Technicals
                    </div>
                    <div class="data-item">
                        <div class="data-label">Latest Price</div>
                        <div class="data-value large">${fmt(last.Close || last.close)}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">ADX (14)</div>
                        <div class="data-value">${fmt(last['Average Directional Index'])}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">ATR</div>
                        <div class="data-value">${fmt(last['Average True Range'])}</div>
                    </div>
                    <div class="data-item">
                        <div class="data-label">Weis Waves Vol</div>
                        <div class="data-value text-warning">${fmt(last['Weis Waves Volume'] || 0, 0)}</div>
                    </div>
                `;
            });

            html += `</div></div>`;
        }

        // 5. Raw Data (Hidden by default, used for "see every datapoint" goal)
        html += `
            <div class="analysis-section-card" style="grid-column: 1 / -1;">
                <h4><i data-lucide="database"></i> Raw JSON State</h4>
                <div style="background: rgba(0,0,0,0.3); padding: 1rem; border-radius: 8px; max-height: 300px; overflow-y: auto;">
                    <pre style="font-size: 0.75rem; color: var(--text-secondary); margin: 0;">${JSON.stringify(data, (key, value) => {
            // Truncate long arrays for display
            if (Array.isArray(value) && value.length > 5) return `[Array(${value.length})]`;
            return value;
        }, 2)}</pre>
                </div>
            </div>
        `;

        grid.innerHTML = html;
        if (window.lucide) lucide.createIcons();
    }

    // Event listeners for Intelligence Page
    const symbolSearch = document.getElementById('symbol-search');
    if (symbolSearch) {
        symbolSearch.oninput = renderAnalysisSymbolList;
    }

    const refreshAnalysisBtn = document.getElementById('refresh-analysis');
    if (refreshAnalysisBtn) {
        refreshAnalysisBtn.onclick = () => fetchAnalysisData(selectedAnalysisSymbol);
    }

    // Initial load
    updateStatus();
    fetchLogs();
    updateEquityChart();
    fetchAnalysisSymbols();

    // Polling
    setInterval(updateStatus, 5000);
    setInterval(fetchLogs, 3000);
    setInterval(updateEquityChart, 10000);
    setInterval(fetchPortfolio, 2000); // Polling for portfolio
    setInterval(fetchTrades, 5000); // Polling for trades history
    setInterval(fetchAnalysisSymbols, 10000);
});

