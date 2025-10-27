# ABOUTME: HTML templates for admin panel

def get_admin_html(players, teams, stats, max_team_size=2):
    """Generate admin panel HTML"""
    
    # Build players table
    players_rows = ""
    for player in players:
        team_name = "Free Agent"
        for team in teams:
            if player.get("team_id") in team.get("member_ids", []):
                team_name = team.get("name")
                break
        
        players_rows += f"""
        <tr>
            <td>{player.get('name')}</td>
            <td>{team_name}</td>
            <td>{player.get('joined_at', '')[:19]}</td>
            <td>
                <form method="POST" action="/admin/delete-player" style="display: inline;">
                    <input type="hidden" name="password" value="Douglas42">
                    <input type="hidden" name="player_name" value="{player.get('name')}">
                    <button type="submit" onclick="return confirm('Delete player {player.get('name')}?')">Delete</button>
                </form>
            </td>
        </tr>
        """
    
    # Build teams table
    teams_rows = ""
    for team in teams:
        member_count = team.get('member_count', 0)
        status = "Full" if team.get('is_full') else f"{member_count}/2"
        
        teams_rows += f"""
        <tr>
            <td>{team.get('name')}</td>
            <td>{member_count}</td>
            <td>{status}</td>
            <td>{team.get('created_at', '')[:19]}</td>
            <td>
                <form method="POST" action="/admin/delete-team" style="display: inline;">
                    <input type="hidden" name="password" value="Douglas42">
                    <input type="hidden" name="team_name" value="{team.get('name')}">
                    <button type="submit" onclick="return confirm('Delete team {team.get('name')}?')">Delete</button>
                </form>
            </td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Team Poaching Game - Admin Panel</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }}
            h1 {{
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #555;
                margin-top: 30px;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .stat-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            .stat-card h3 {{
                margin: 0 0 10px 0;
                color: #666;
                font-size: 14px;
                text-transform: uppercase;
            }}
            .stat-card .number {{
                font-size: 36px;
                font-weight: bold;
                color: #007bff;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-radius: 8px;
                overflow: hidden;
                margin: 20px 0;
            }}
            th {{
                background: #007bff;
                color: white;
                padding: 12px;
                text-align: left;
                font-weight: 600;
            }}
            td {{
                padding: 12px;
                border-bottom: 1px solid #eee;
            }}
            tr:hover {{
                background: #f8f9fa;
            }}
            button {{
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.2s;
            }}
            button[type="submit"] {{
                background: #dc3545;
                color: white;
            }}
            button[type="submit"]:hover {{
                background: #c82333;
            }}
            .action-buttons {{
                display: flex;
                gap: 10px;
                margin: 20px 0;
                flex-wrap: wrap;
            }}
            .action-buttons button {{
                padding: 12px 24px;
                font-size: 16px;
            }}
            .reset-btn {{
                background: #dc3545;
                color: white;
            }}
            .reset-btn:hover {{
                background: #c82333;
            }}
            .test-data-btn {{
                background: #28a745;
                color: white;
            }}
            .test-data-btn:hover {{
                background: #218838;
            }}
            .auto-assign-btn {{
                background: #17a2b8;
                color: white;
            }}
            .auto-assign-btn:hover {{
                background: #138496;
            }}
            .refresh-btn {{
                background: #007bff;
                color: white;
            }}
            .refresh-btn:hover {{
                background: #0056b3;
            }}
            .warning {{
                background: #fff3cd;
                border: 1px solid #ffc107;
                color: #856404;
                padding: 12px;
                border-radius: 4px;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>🎮 Team Poaching Game - Admin Panel</h1>
        
        <div class="stats">
            <div class="stat-card">
                <h3>Total Players</h3>
                <div class="number">{stats.get('total_players', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Total Teams</h3>
                <div class="number">{stats.get('total_teams', 0)}</div>
            </div>
            <div class="stat-card">
                <h3>Free Agents</h3>
                <div class="number">{stats.get('free_agents_count', 0)}</div>
            </div>
        </div>

        <h2>⚙️ Settings</h2>
        <div style="background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin: 20px 0;">
            <form method="POST" action="/admin/set-team-size" style="display: flex; align-items: center; gap: 15px;">
                <input type="hidden" name="password" value="Douglas42">
                <label style="font-weight: 600;">Max Team Size:</label>
                <input type="number" name="team_size" value="{max_team_size}" min="1" max="10" style="width: 80px; padding: 8px; border: 2px solid #ddd; border-radius: 4px;">
                <button type="submit" style="background: #007bff; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer;">Update</button>
                <span style="color: #666; font-size: 14px;">Current: {max_team_size} members per team</span>
            </form>
        </div>

        <div class="action-buttons">
            <form method="GET" action="/admin" style="display: inline;">
                <input type="hidden" name="password" value="Douglas42">
                <button type="submit" class="refresh-btn">🔄 Refresh</button>
            </form>
            
            <form method="POST" action="/admin/auto-assign" style="display: inline;">
                <input type="hidden" name="password" value="Douglas42">
                <button type="submit" class="test-data-btn">🎲 Auto-Assign Free Agents</button>
            </form>
            
            <form method="POST" action="/admin/create-test-data" style="display: inline;">
                <input type="hidden" name="password" value="Douglas42">
                <button type="submit" class="test-data-btn">➕ Create Test Data</button>
            </form>
            
            <form method="POST" action="/admin/reset" style="display: inline;">
                <input type="hidden" name="password" value="Douglas42">
                <button type="submit" class="reset-btn" onclick="return confirm('⚠️ Are you sure? This will delete ALL data!')">🗑️ Reset Database</button>
            </form>
        </div>

        <h2>👥 Players ({len(players)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Team</th>
                    <th>Joined At</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {players_rows if players_rows else '<tr><td colspan="4" style="text-align: center; color: #999;">No players yet</td></tr>'}
            </tbody>
        </table>

        <h2>🏆 Teams ({len(teams)})</h2>
        <table>
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Members</th>
                    <th>Status</th>
                    <th>Created At</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {teams_rows if teams_rows else '<tr><td colspan="5" style="text-align: center; color: #999;">No teams yet</td></tr>'}
            </tbody>
        </table>

        <div class="warning">
            ⚠️ <strong>Admin Access:</strong> This panel is password protected. Do not share the URL with players.
        </div>
    </body>
    </html>
    """
    
    return html


def get_login_html(error=None):
    """Generate login page HTML"""
    error_msg = f'<div class="error">{error}</div>' if error else ''
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Admin Login</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                display: flex;
                justify-content: center;
                align-items: center;
                min-height: 100vh;
                margin: 0;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            }}
            .login-box {{
                background: white;
                padding: 40px;
                border-radius: 12px;
                box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                width: 100%;
                max-width: 400px;
            }}
            h1 {{
                margin: 0 0 30px 0;
                color: #333;
                text-align: center;
            }}
            input {{
                width: 100%;
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 16px;
                box-sizing: border-box;
                margin-bottom: 20px;
            }}
            input:focus {{
                outline: none;
                border-color: #667eea;
            }}
            button {{
                width: 100%;
                padding: 12px;
                background: #667eea;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background 0.2s;
            }}
            button:hover {{
                background: #5568d3;
            }}
            .error {{
                background: #fee;
                color: #c33;
                padding: 12px;
                border-radius: 6px;
                margin-bottom: 20px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="login-box">
            <h1>🔐 Admin Login</h1>
            {error_msg}
            <form method="GET" action="/admin">
                <input type="password" name="password" placeholder="Enter admin password" required autofocus>
                <button type="submit">Login</button>
            </form>
        </div>
    </body>
    </html>
    """
    
    return html
