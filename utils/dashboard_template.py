DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Adapt Hub | Dashboard</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://unpkg.com/lucide@latest"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased;
        }

        :root {
            --bg: #05060f;
            --bg-grid: rgba(255, 255, 255, 0.015);
            --card-bg: rgba(13, 16, 31, 0.7);
            --card-border: rgba(255, 255, 255, 0.06);
            --primary: #7c3aed;
            --primary-glow: rgba(124, 58, 237, 0.3);
            --secondary: #06b6d4;
            --secondary-glow: rgba(6, 182, 212, 0.3);
            --success: #10b981;
            --success-glow: rgba(16, 185, 129, 0.2);
            --text: #f3f4f6;
            --text-muted: #9ca3af;
        }

        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(at 0% 0%, rgba(124, 58, 237, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(6, 182, 212, 0.12) 0px, transparent 50%),
                linear-gradient(rgba(255, 255, 255, 0.003) 1px, transparent 1px),
                linear-gradient(90deg, rgba(255, 255, 255, 0.003) 1px, transparent 1px);
            background-size: 100% 100%, 100% 100%, 40px 40px, 40px 40px;
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
            display: flex;
            justify-content: center;
        }

        .container {
            width: 100%;
            max-width: 1200px;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }

        /* Glassmorphic Navbar */
        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 1.25rem 2rem;
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            backdrop-filter: blur(16px);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
        }

        .bot-profile {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .bot-avatar {
            width: 48px;
            height: 48px;
            border-radius: 50%;
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            border: 2px solid var(--card-border);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
            font-weight: 700;
            color: #fff;
            box-shadow: 0 0 15px var(--primary-glow);
        }

        .bot-info h1 {
            font-size: 1.25rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .bot-status {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 0.1rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background-color: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 10px var(--success-glow);
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }

        .latency-badge {
            background: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            color: var(--success);
            padding: 0.4rem 0.8rem;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }

        /* Top Grid Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
        }

        .stat-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 1.5rem;
            border-radius: 20px;
            backdrop-filter: blur(12px);
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-4px);
            border-color: rgba(255, 255, 255, 0.12);
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }

        .stat-left {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .stat-label {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 500;
        }

        .stat-value {
            font-size: 1.75rem;
            font-weight: 700;
            letter-spacing: -0.5px;
        }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .icon-violet {
            background: rgba(124, 58, 237, 0.1);
            color: var(--primary);
            border: 1px solid rgba(124, 58, 237, 0.15);
        }

        .icon-cyan {
            background: rgba(6, 182, 212, 0.1);
            color: var(--secondary);
            border: 1px solid rgba(6, 182, 212, 0.15);
        }

        /* Layout Main Sections */
        .main-layout {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
        }

        @media (max-width: 900px) {
            .main-layout {
                grid-template-columns: 1fr;
            }
        }

        .section-card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            padding: 2rem;
            border-radius: 24px;
            backdrop-filter: blur(12px);
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 1rem;
        }

        .section-title {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 0.6rem;
        }

        /* Cogs Extension Grid */
        .cogs-list {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 1rem;
        }

        .cog-item {
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: all 0.2s ease;
        }

        .cog-item:hover {
            background: rgba(255, 255, 255, 0.04);
            border-color: rgba(255, 255, 255, 0.1);
        }

        .cog-name {
            font-size: 0.9rem;
            font-weight: 600;
        }

        .cog-status {
            font-size: 0.75rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 8px;
        }

        .cog-active {
            background: rgba(16, 185, 129, 0.1);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .cog-inactive {
            background: rgba(239, 68, 68, 0.1);
            color: #ef4444;
            border: 1px solid rgba(239, 68, 68, 0.2);
        }

        /* System Metrics */
        .metric-container {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .metric-item {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .metric-label-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .metric-title {
            color: var(--text-muted);
        }

        .metric-value {
            color: var(--text);
        }

        .progress-bar-bg {
            height: 10px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
            overflow: hidden;
            border: 1px solid var(--card-border);
        }

        .progress-bar-fill {
            height: 100%;
            width: 0%;
            border-radius: 5px;
            transition: width 0.8s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .fill-primary {
            background: linear-gradient(90deg, var(--primary), #a78bfa);
            box-shadow: 0 0 10px rgba(124, 58, 237, 0.5);
        }

        .fill-secondary {
            background: linear-gradient(90deg, var(--secondary), #22d3ee);
            box-shadow: 0 0 10px rgba(6, 182, 212, 0.5);
        }

        /* Meta System Details */
        .meta-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .meta-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            padding-bottom: 0.75rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
        }

        .meta-row:last-child {
            border: none;
            padding-bottom: 0;
        }

        .meta-label {
            color: var(--text-muted);
            font-weight: 500;
        }

        .meta-value {
            font-weight: 600;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header / Navbar -->
        <header>
            <div class="bot-profile">
                <div class="bot-avatar" id="bot-avatar-char">A</div>
                <div class="bot-info">
                    <h1 id="bot-name">Adapt Bot</h1>
                    <div class="bot-status">
                        <div class="status-dot"></div>
                        <span id="bot-status-text">Online</span>
                    </div>
                </div>
            </div>
            <div class="latency-badge">
                <i data-lucide="activity" style="width: 16px; height: 16px;"></i>
                <span id="bot-ping">-- ms</span>
            </div>
        </header>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-left">
                    <span class="stat-label">Total Servers</span>
                    <span class="stat-value" id="stat-servers">--</span>
                </div>
                <div class="stat-icon icon-violet">
                    <i data-lucide="server" style="width: 24px; height: 24px;"></i>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-left">
                    <span class="stat-label">Total Members</span>
                    <span class="stat-value" id="stat-members">--</span>
                </div>
                <div class="stat-icon icon-cyan">
                    <i data-lucide="users" style="width: 24px; height: 24px;"></i>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-left">
                    <span class="stat-label">Uptime</span>
                    <span class="stat-value" style="font-size: 1.1rem; line-height: 2.1rem;" id="stat-uptime">--</span>
                </div>
                <div class="stat-icon icon-violet">
                    <i data-lucide="clock" style="width: 24px; height: 24px;"></i>
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-left">
                    <span class="stat-label">Database Status</span>
                    <span class="stat-value" id="stat-db">--</span>
                </div>
                <div class="stat-icon icon-cyan" id="stat-db-icon">
                    <i data-lucide="database" style="width: 24px; height: 24px;"></i>
                </div>
            </div>
        </div>

        <!-- Main Layout -->
        <div class="main-layout">
            <!-- Cogs Section -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <i data-lucide="package" style="color: var(--primary); width: 20px; height: 20px;"></i>
                        <span>System Extensions & Cogs</span>
                    </div>
                </div>
                <div class="cogs-list" id="cogs-grid">
                    <!-- Dynamic Cogs will load here -->
                </div>
            </div>

            <!-- Resource Metrics Section -->
            <div class="section-card">
                <div class="section-header">
                    <div class="section-title">
                        <i data-lucide="cpu" style="color: var(--secondary); width: 20px; height: 20px;"></i>
                        <span>System Performance</span>
                    </div>
                </div>
                <div class="metric-container">
                    <div class="metric-item">
                        <div class="metric-label-row">
                            <span class="metric-title">CPU Usage</span>
                            <span class="metric-value" id="cpu-percent">--%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-primary" id="cpu-bar"></div>
                        </div>
                    </div>
                    <div class="metric-item">
                        <div class="metric-label-row">
                            <span class="metric-title">RAM Usage</span>
                            <span class="metric-value" id="ram-percent">--%</span>
                        </div>
                        <div class="progress-bar-bg">
                            <div class="progress-bar-fill fill-secondary" id="ram-bar"></div>
                        </div>
                    </div>
                </div>

                <div class="meta-list" style="margin-top: 1rem;">
                    <div class="meta-row">
                        <span class="meta-label">Process ID</span>
                        <span class="meta-value" id="meta-pid">--</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Python Version</span>
                        <span class="meta-value" id="meta-python">--</span>
                    </div>
                    <div class="meta-row">
                        <span class="meta-label">Operating System</span>
                        <span class="meta-value" id="meta-os">--</span>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Initialize Lucide Icons
        lucide.createIcons();

        function formatUptime(seconds) {
            const d = Math.floor(seconds / (3600*24));
            const h = Math.floor(seconds % (3600*24) / 3600);
            const m = Math.floor(seconds % 3600 / 60);
            const s = Math.floor(seconds % 60);
            
            const parts = [];
            if (d > 0) parts.push(`${d}d`);
            if (h > 0) parts.push(`${h}h`);
            if (m > 0) parts.push(`${m}m`);
            parts.push(`${s}s`);
            return parts.join(' ');
        }

        async function fetchStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();

                // Set general bot details
                document.getElementById('bot-name').innerText = data.bot_name || 'Adapt Bot';
                if (data.bot_name) {
                    document.getElementById('bot-avatar-char').innerText = data.bot_name.charAt(0).toUpperCase();
                }
                document.getElementById('bot-ping').innerText = `${Math.round(data.latency_ms)} ms`;

                // Set status counters
                document.getElementById('stat-servers').innerText = data.server_count;
                document.getElementById('stat-members').innerText = data.member_count;
                document.getElementById('stat-uptime').innerText = formatUptime(data.uptime_seconds);
                
                // Database
                const dbElement = document.getElementById('stat-db');
                const dbIconContainer = document.getElementById('stat-db-icon');
                if (data.database_connected) {
                    dbElement.innerText = 'Connected';
                    dbElement.style.color = 'var(--success)';
                    dbIconContainer.className = 'stat-icon icon-cyan';
                } else {
                    dbElement.innerText = 'Disconnected';
                    dbElement.style.color = '#ef4444';
                    dbIconContainer.className = 'stat-icon';
                    dbIconContainer.style.background = 'rgba(239, 68, 68, 0.1)';
                    dbIconContainer.style.color = '#ef4444';
                    dbIconContainer.style.border = '1px solid rgba(239, 68, 68, 0.15)';
                }

                // Performance meters
                document.getElementById('cpu-percent').innerText = `${data.cpu_usage_percent}%`;
                document.getElementById('cpu-bar').style.width = `${data.cpu_usage_percent}%`;
                
                document.getElementById('ram-percent').innerText = `${data.memory_usage_percent}% (${data.memory_usage_mb} MB)`;
                document.getElementById('ram-bar').style.width = `${data.memory_usage_percent}%`;

                // System details
                document.getElementById('meta-pid').innerText = data.pid;
                document.getElementById('meta-python').innerText = data.python_version;
                document.getElementById('meta-os').innerText = data.os;

                // Load cogs extension grid
                const cogsGrid = document.getElementById('cogs-grid');
                cogsGrid.innerHTML = '';
                
                for (const [cogName, isLoaded] of Object.entries(data.cogs)) {
                    const cleanName = cogName.replace('cogs.', '');
                    const cogItem = document.createElement('div');
                    cogItem.className = 'cog-item';
                    
                    const nameSpan = document.createElement('span');
                    nameSpan.className = 'cog-name';
                    nameSpan.innerText = cleanName;
                    
                    const statusSpan = document.createElement('span');
                    statusSpan.className = `cog-status ${isLoaded ? 'cog-active' : 'cog-inactive'}`;
                    statusSpan.innerText = isLoaded ? 'Active' : 'Disabled';
                    
                    cogItem.appendChild(nameSpan);
                    cogItem.appendChild(statusSpan);
                    cogsGrid.appendChild(cogItem);
                }

            } catch (error) {
                console.error('Error fetching dashboard stats:', error);
                document.getElementById('bot-status-text').innerText = 'Reconnecting...';
                document.getElementById('bot-status-text').style.color = '#ef4444';
            }
        }

        // Fetch metrics immediately, then every 3 seconds
        fetchStats();
        setInterval(fetchStats, 3000);
    </script>
</body>
</html>
"""
