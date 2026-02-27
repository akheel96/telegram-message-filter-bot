"""
Admin UI module for Telegram Loot Filter Bot.
Provides a simple web interface to manage source channels and filter keywords.

Note: Changes made through this UI are runtime changes and will reset on restart.
To make permanent changes, update the environment variables in Render.
"""

import json
import logging
from aiohttp import web

from src.config import config

logger = logging.getLogger(__name__)


# ============================================================
# Admin HTML Page
# ============================================================

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bot Admin - Telegram Loot Filter</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        header h1 {
            font-size: 2rem;
            margin-bottom: 5px;
        }
        header p {
            opacity: 0.9;
            font-size: 0.95rem;
        }
        .warning-banner {
            background: #fff3cd;
            border: 1px solid #ffc107;
            color: #856404;
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 0.9rem;
        }
        .warning-banner strong {
            display: block;
            margin-bottom: 3px;
        }
        .card {
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
            margin-bottom: 20px;
            overflow: hidden;
        }
        .card-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .card-header h2 {
            font-size: 1.1rem;
            color: #333;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .card-body {
            padding: 20px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
        }
        .input-group input {
            flex: 1;
            padding: 10px 15px;
            border: 2px solid #e9ecef;
            border-radius: 8px;
            font-size: 1rem;
            transition: border-color 0.2s;
        }
        .input-group input:focus {
            outline: none;
            border-color: #667eea;
        }
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 8px;
            font-size: 0.95rem;
            cursor: pointer;
            transition: all 0.2s;
            font-weight: 500;
        }
        .btn-primary {
            background: #667eea;
            color: white;
        }
        .btn-primary:hover {
            background: #5a6fd6;
        }
        .btn-danger {
            background: #dc3545;
            color: white;
            padding: 6px 12px;
            font-size: 0.85rem;
        }
        .btn-danger:hover {
            background: #c82333;
        }
        .item-list {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
        }
        .item-tag {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            background: #f0f0f0;
            padding: 8px 12px;
            border-radius: 20px;
            font-size: 0.9rem;
        }
        .item-tag.channel {
            background: #e3f2fd;
            color: #1565c0;
        }
        .item-tag.keyword {
            background: #f3e5f5;
            color: #7b1fa2;
        }
        .item-tag button {
            background: none;
            border: none;
            color: #999;
            cursor: pointer;
            font-size: 1.1rem;
            padding: 0;
            line-height: 1;
        }
        .item-tag button:hover {
            color: #dc3545;
        }
        .empty-state {
            color: #999;
            font-style: italic;
            padding: 20px;
            text-align: center;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        .stat-item {
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            font-size: 0.85rem;
            color: #666;
            margin-top: 5px;
        }
        .toast {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 8px;
            color: white;
            font-size: 0.9rem;
            opacity: 0;
            transform: translateY(20px);
            transition: all 0.3s;
            z-index: 1000;
        }
        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }
        .toast.success { background: #28a745; }
        .toast.error { background: #dc3545; }
        .refresh-btn {
            background: none;
            border: 1px solid #ddd;
            padding: 6px 12px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.85rem;
            color: #666;
        }
        .refresh-btn:hover {
            background: #f0f0f0;
        }
        @media (max-width: 600px) {
            .input-group {
                flex-direction: column;
            }
            .stats {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🤖 Bot Admin Panel</h1>
            <p>Manage source channels and filter keywords</p>
        </header>

        <div class="warning-banner">
            <strong>⚠️ Runtime Changes Only</strong>
            Changes made here are temporary and will reset when the bot restarts. 
            For permanent changes, update environment variables in Render.
        </div>

        <!-- Stats Card -->
        <div class="card">
            <div class="card-header">
                <h2>📊 Current Stats</h2>
                <button class="refresh-btn" onclick="loadConfig()">↻ Refresh</button>
            </div>
            <div class="card-body">
                <div class="stats">
                    <div class="stat-item">
                        <div class="stat-value" id="stat-channels">0</div>
                        <div class="stat-label">Source Channels</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="stat-keywords">0</div>
                        <div class="stat-label">Filter Keywords</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-value" id="stat-dest">-</div>
                        <div class="stat-label">Destination</div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Source Channels Card -->
        <div class="card">
            <div class="card-header">
                <h2>📺 Source Channels</h2>
            </div>
            <div class="card-body">
                <div class="input-group">
                    <input type="text" id="channel-input" placeholder="Enter channel ID (e.g., -1001234567890)">
                    <button class="btn btn-primary" onclick="addChannel()">Add Channel</button>
                </div>
                <div class="item-list" id="channel-list">
                    <div class="empty-state">Loading...</div>
                </div>
            </div>
        </div>

        <!-- Filter Keywords Card -->
        <div class="card">
            <div class="card-header">
                <h2>🔍 Filter Keywords</h2>
            </div>
            <div class="card-body">
                <div class="input-group">
                    <input type="text" id="keyword-input" placeholder="Enter keyword (e.g., loot, deal, offer)">
                    <button class="btn btn-primary" onclick="addKeyword()">Add Keyword</button>
                </div>
                <div class="item-list" id="keyword-list">
                    <div class="empty-state">Loading...</div>
                </div>
            </div>
        </div>
    </div>

    <div class="toast" id="toast"></div>

    <script>
        // Toast notification
        function showToast(message, type = 'success') {
            const toast = document.getElementById('toast');
            toast.textContent = message;
            toast.className = 'toast ' + type + ' show';
            setTimeout(() => toast.classList.remove('show'), 3000);
        }

        // Load current configuration
        async function loadConfig() {
            try {
                const response = await fetch('/admin/api/config');
                const data = await response.json();
                
                // Update stats
                document.getElementById('stat-channels').textContent = data.source_channel_ids.length;
                document.getElementById('stat-keywords').textContent = data.filter_keywords.length;
                document.getElementById('stat-dest').textContent = data.destination_channel_id;
                
                // Render channel list
                const channelList = document.getElementById('channel-list');
                if (data.source_channel_ids.length === 0) {
                    channelList.innerHTML = '<div class="empty-state">No source channels configured</div>';
                } else {
                    channelList.innerHTML = data.source_channel_ids.map(id => `
                        <div class="item-tag channel">
                            ${id}
                            <button onclick="removeChannel(${id})" title="Remove">&times;</button>
                        </div>
                    `).join('');
                }
                
                // Render keyword list
                const keywordList = document.getElementById('keyword-list');
                if (data.filter_keywords.length === 0) {
                    keywordList.innerHTML = '<div class="empty-state">No filter keywords configured</div>';
                } else {
                    keywordList.innerHTML = data.filter_keywords.map(kw => `
                        <div class="item-tag keyword">
                            ${kw}
                            <button onclick="removeKeyword('${kw}')" title="Remove">&times;</button>
                        </div>
                    `).join('');
                }
            } catch (error) {
                showToast('Failed to load config: ' + error.message, 'error');
            }
        }

        // Add channel
        async function addChannel() {
            const input = document.getElementById('channel-input');
            const channelId = input.value.trim();
            
            if (!channelId) {
                showToast('Please enter a channel ID', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/api/channels', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ channel_id: channelId })
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Channel added successfully');
                    input.value = '';
                    loadConfig();
                } else {
                    showToast(data.message || 'Failed to add channel', 'error');
                }
            } catch (error) {
                showToast('Error: ' + error.message, 'error');
            }
        }

        // Remove channel
        async function removeChannel(channelId) {
            if (!confirm('Remove channel ' + channelId + '?')) return;
            
            try {
                const response = await fetch('/admin/api/channels', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ channel_id: channelId })
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Channel removed');
                    loadConfig();
                } else {
                    showToast(data.message || 'Failed to remove channel', 'error');
                }
            } catch (error) {
                showToast('Error: ' + error.message, 'error');
            }
        }

        // Add keyword
        async function addKeyword() {
            const input = document.getElementById('keyword-input');
            const keyword = input.value.trim();
            
            if (!keyword) {
                showToast('Please enter a keyword', 'error');
                return;
            }
            
            try {
                const response = await fetch('/admin/api/keywords', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: keyword })
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Keyword added successfully');
                    input.value = '';
                    loadConfig();
                } else {
                    showToast(data.message || 'Failed to add keyword', 'error');
                }
            } catch (error) {
                showToast('Error: ' + error.message, 'error');
            }
        }

        // Remove keyword
        async function removeKeyword(keyword) {
            if (!confirm('Remove keyword "' + keyword + '"?')) return;
            
            try {
                const response = await fetch('/admin/api/keywords', {
                    method: 'DELETE',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ keyword: keyword })
                });
                const data = await response.json();
                
                if (data.success) {
                    showToast('Keyword removed');
                    loadConfig();
                } else {
                    showToast(data.message || 'Failed to remove keyword', 'error');
                }
            } catch (error) {
                showToast('Error: ' + error.message, 'error');
            }
        }

        // Handle Enter key in inputs
        document.getElementById('channel-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addChannel();
        });
        document.getElementById('keyword-input').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addKeyword();
        });

        // Load config on page load
        loadConfig();
    </script>
</body>
</html>
"""


# ============================================================
# Admin API Routes
# ============================================================

async def admin_page(request):
    """Serve the admin HTML page."""
    return web.Response(text=ADMIN_HTML, content_type='text/html')


async def get_config(request):
    """Get current runtime configuration."""
    return web.json_response(config.get_runtime_config())


async def add_channel(request):
    """Add a source channel."""
    try:
        data = await request.json()
        channel_id_str = str(data.get('channel_id', '')).strip()
        
        if not channel_id_str:
            return web.json_response({'success': False, 'message': 'Channel ID is required'})
        
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return web.json_response({'success': False, 'message': 'Invalid channel ID format'})
        
        success = config.add_source_channel(channel_id)
        
        if success:
            return web.json_response({'success': True, 'message': f'Channel {channel_id} added'})
        else:
            return web.json_response({'success': False, 'message': 'Channel already exists or is invalid'})
            
    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        return web.json_response({'success': False, 'message': str(e)})


async def remove_channel(request):
    """Remove a source channel."""
    try:
        data = await request.json()
        channel_id_str = str(data.get('channel_id', '')).strip()
        
        if not channel_id_str:
            return web.json_response({'success': False, 'message': 'Channel ID is required'})
        
        try:
            channel_id = int(channel_id_str)
        except ValueError:
            return web.json_response({'success': False, 'message': 'Invalid channel ID format'})
        
        success = config.remove_source_channel(channel_id)
        
        if success:
            return web.json_response({'success': True, 'message': f'Channel {channel_id} removed'})
        else:
            return web.json_response({'success': False, 'message': 'Channel not found'})
            
    except Exception as e:
        logger.error(f"Error removing channel: {e}")
        return web.json_response({'success': False, 'message': str(e)})


async def add_keyword(request):
    """Add a filter keyword."""
    try:
        data = await request.json()
        keyword = str(data.get('keyword', '')).strip().lower()
        
        if not keyword:
            return web.json_response({'success': False, 'message': 'Keyword is required'})
        
        success = config.add_keyword(keyword)
        
        if success:
            return web.json_response({'success': True, 'message': f'Keyword "{keyword}" added'})
        else:
            return web.json_response({'success': False, 'message': 'Keyword already exists'})
            
    except Exception as e:
        logger.error(f"Error adding keyword: {e}")
        return web.json_response({'success': False, 'message': str(e)})


async def remove_keyword(request):
    """Remove a filter keyword."""
    try:
        data = await request.json()
        keyword = str(data.get('keyword', '')).strip().lower()
        
        if not keyword:
            return web.json_response({'success': False, 'message': 'Keyword is required'})
        
        success = config.remove_keyword(keyword)
        
        if success:
            return web.json_response({'success': True, 'message': f'Keyword "{keyword}" removed'})
        else:
            return web.json_response({'success': False, 'message': 'Keyword not found'})
            
    except Exception as e:
        logger.error(f"Error removing keyword: {e}")
        return web.json_response({'success': False, 'message': str(e)})


def setup_admin_routes(app: web.Application):
    """Register admin routes with the application."""
    app.router.add_get('/admin', admin_page)
    app.router.add_get('/admin/api/config', get_config)
    app.router.add_post('/admin/api/channels', add_channel)
    app.router.add_delete('/admin/api/channels', remove_channel)
    app.router.add_post('/admin/api/keywords', add_keyword)
    app.router.add_delete('/admin/api/keywords', remove_keyword)
    
    logger.info("📋 Admin panel available at /admin")
