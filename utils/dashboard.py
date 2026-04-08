"""
Dashboard Module
Web interface for monitoring bot status
"""

import json
import time
from datetime import datetime
from flask import Flask, render_template_string, jsonify
from threading import Thread


app = Flask(__name__)

# Global state (shared with bot)
bot_state = {
    "running": False,
    "trades": 0,
    "profits": 0.0,
    "spreads": [],
    "errors": 0,
    "start_time": None,
    "last_opportunities": [],
    "last_trade": None,
}


def update_state(new_state: dict):
    """Update bot state from main thread"""
    global bot_state
    bot_state.update(new_state)


def get_stats():
    """Get current stats"""
    global bot_state

    uptime = time.time() - bot_state["start_time"] if bot_state["start_time"] else 0
    avg_spread = sum(bot_state["spreads"]) / len(bot_state["spreads"]) if bot_state["spreads"] else 0

    return {
        "running": bot_state["running"],
        "uptime_seconds": uptime,
        "trades": bot_state["trades"],
        "profits": bot_state["profits"],
        "avg_spread": avg_spread,
        "errors": bot_state["errors"],
        "last_opportunities": bot_state["last_opportunities"],
        "last_trade": bot_state["last_trade"],
    }


HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>XLayer Arbitrage Bot</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { background: #0f0f0f; color: #fff; font-family: monospace; }
        .card { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 20px; }
        .stat-value { font-size: 2rem; font-weight: bold; color: #22c55e; }
        .stat-label { color: #888; font-size: 0.875rem; }
        .status-running { color: #22c55e; }
        .status-stopped { color: #ef4444; }
        .opp-card { background: #252525; padding: 10px; margin: 5px 0; border-radius: 4px; }
    </style>
</head>
<body class="p-8">
    <div class="max-w-6xl mx-auto">
        <header class="mb-8 flex justify-between items-center">
            <div>
                <h1 class="text-3xl font-bold">🤖 XLayer Arbitrage Bot</h1>
                <p class="text-gray-400">Autonomous DEX arbitrage on X Layer</p>
            </div>
            <div class="text-right">
                <div id="status" class="text-xl font-bold status-stopped">STOPPED</div>
                <div id="uptime" class="text-gray-400">--</div>
            </div>
        </header>

        <div class="grid grid-cols-4 gap-4 mb-8">
            <div class="card">
                <div class="stat-label">Total Trades</div>
                <div id="trades" class="stat-value">0</div>
            </div>
            <div class="card">
                <div class="stat-label">Total Profits</div>
                <div id="profits" class="stat-value">$0.00</div>
            </div>
            <div class="card">
                <div class="stat-label">Avg Spread</div>
                <div id="avg-spread" class="stat-value">0%</div>
            </div>
            <div class="card">
                <div class="stat-label">Errors</div>
                <div id="errors" class="stat-value text-red-500">0</div>
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
            <div class="card">
                <h2 class="text-xl font-bold mb-4">Recent Opportunities</h2>
                <div id="opportunities">
                    <p class="text-gray-500">No opportunities found yet</p>
                </div>
            </div>
            <div class="card">
                <h2 class="text-xl font-bold mb-4">Last Trade</h2>
                <div id="last-trade">
                    <p class="text-gray-500">No trades executed yet</p>
                </div>
            </div>
        </div>

        <div class="mt-8 text-center">
            <a href="/stop" class="bg-red-600 hover:bg-red-700 px-4 py-2 rounded">Stop Bot</a>
            <a href="/restart" class="bg-green-600 hover:bg-green-700 px-4 py-2 rounded ml-4">Restart Bot</a>
        </div>
    </div>

    <script>
        async function updateStats() {
            try {
                const resp = await fetch('/api/stats');
                const data = await resp.json();

                document.getElementById('status').textContent = data.running ? 'RUNNING' : 'STOPPED';
                document.getElementById('status').className = 'text-xl font-bold ' + (data.running ? 'status-running' : 'status-stopped');

                const hours = Math.floor(data.uptime_seconds / 3600);
                const mins = Math.floor((data.uptime_seconds % 3600) / 60);
                document.getElementById('uptime').textContent = `Uptime: ${hours}h ${mins}m`;

                document.getElementById('trades').textContent = data.trades;
                document.getElementById('profits').textContent = '$' + data.profits.toFixed(4);
                document.getElementById('avg-spread').textContent = data.avg_spread.toFixed(2) + '%';
                document.getElementById('errors').textContent = data.errors;

                // Opportunities
                const oppDiv = document.getElementById('opportunities');
                if (data.last_opportunities.length > 0) {
                    oppDiv.innerHTML = data.last_opportunities.map(o =>
                        '<div class="opp-card">' + o.pair + ': ' + o.spread.toFixed(2) + '% spread</div>'
                    ).join('');
                }

                // Last trade
                const tradeDiv = document.getElementById('last-trade');
                if (data.last_trade) {
                    tradeDiv.innerHTML = '<div class="opp-card">' + data.last_trade + '</div>';
                }
            } catch(e) {
                console.error(e);
            }
        }

        updateStats();
        setInterval(updateStats, 5000);
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Dashboard home"""
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/stats")
def api_stats():
    """API endpoint for stats"""
    return jsonify(get_stats())


@app.route("/start")
def start_bot():
    """Start the bot"""
    global bot_state
    bot_state["running"] = True
    return "Bot started"


@app.route("/stop")
def stop_bot():
    """Stop the bot"""
    global bot_state
    bot_state["running"] = False
    return "Bot stopped"


@app.route("/restart")
def restart_bot():
    """Restart the bot"""
    global bot_state
    bot_state["running"] = True
    bot_state["start_time"] = time.time()
    return "Bot restarted"


def run_dashboard(host: str = "0.0.0.0", port: int = 5000):
    """Run dashboard server"""
    app.run(host=host, port=port, debug=False)


def start_dashboard_thread(host: str = "0.0.0.0", port: int = 5000):
    """Start dashboard in background thread"""
    thread = Thread(target=run_dashboard, args=(host, port))
    thread.daemon = True
    thread.start()
    return thread
