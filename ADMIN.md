# Admin Panel Guide

## Access

**URL:** https://poachers.vercel.app/admin  
**Password:** `Douglas42`

### Login Process
1. Navigate to https://poachers.vercel.app/admin
2. Enter password: `Douglas42`
3. Click "Login"
4. You will be logged in with a secure session cookie (valid for 24 hours)
5. Password is **not** visible in the URL
6. Use the "Logout" button to end your session

## Features

### 📊 Dashboard
- View total players, teams, and free agents
- See all players with their team assignments
- View all teams with member counts

### ⚙️ Settings
- **Max Team Size:** Configure the maximum number of members per team (1-10)
  - Default: 2 members
  - Changes apply immediately to all new team joins and poaching attempts
  
- **Poaching Status:** Enable or disable poaching game-wide
  - Toggle button shows current status (✓ Enabled / ✗ Disabled)
  - Green = Enabled (players can poach)
  - Red = Disabled (poaching is blocked)
  - When disabled, all poach requests return 403 error
  - Useful for controlling game phases or preventing disruption

### 🎮 Quick Actions

1. **🔄 Refresh** - Reload the current game state
2. **🎲 Auto-Assign Free Agents** - Automatically assign all free agents to teams
   - First fills existing teams that have available spots
   - If no teams have space, creates new teams with random names
   - Team names are generated from combinations like: LuckyParakeet, HappyMonkey, BraveTiger, etc.
   - Adjectives: Lucky, Happy, Brave, Swift, Mighty, Clever, Bold, Fierce, Gentle, Wise, Quick, Strong, Bright, Wild, Noble, Proud, Fearless, Agile, Cosmic, Magic
   - Animals: Parakeet, Monkey, Tiger, Eagle, Dragon, Phoenix, Wolf, Lion, Falcon, Panther, Bear, Fox, Hawk, Leopard, Dolphin, Shark, Cobra, Jaguar, Raven, Owl
3. **➕ Create Test Data** - Quickly populate the database with 6 test players and 2 teams
   - Players: Alice, Bob, Charlie, Diana, Eve, Frank
   - Teams: TeamAlpha (Alice, Bob) and TeamBeta (Charlie, Diana)
4. **🗑️ Reset Database** - Delete ALL game data (requires confirmation)
   - Removes all players, teams, and relationships
   - Resets all statistics to zero

### 👥 Player Management
- **Delete Player** - Remove a player from the game
  - If player is on a team, they are removed from the team
  - If they were the last member, the team is automatically dissolved

### 🏆 Team Management
- **Delete Team** - Remove a team from the game
  - All team members become free agents
  - Team statistics are updated

## Security

- **Session-based authentication** using signed, HTTP-only cookies
- Password is never exposed in the URL or browser history
- Sessions expire after 24 hours
- Cookies are signed using `itsdangerous` library
- Password is hardcoded in the application: `Douglas42`
- **Do not share the admin URL or password with players!**
- Use the "Logout" button when finished to invalidate your session

## Use Cases

### Setting up a game session
1. Go to admin panel
2. Click "Create Test Data" to populate with sample data
3. Adjust "Max Team Size" if needed (e.g., set to 3 for larger teams)
4. Players can now join and play

### Quickly forming teams from free agents
1. Players join the game (they start as free agents)
2. Go to admin panel
3. Click "Auto-Assign Free Agents"
4. All free agents are automatically distributed to teams
5. Teams with available spots are filled first
6. New teams with fun names are created as needed

### Resetting between sessions
1. Go to admin panel
2. Click "Reset Database" and confirm
3. All data is cleared, ready for a new game

### Changing team size mid-game
1. Go to admin panel
2. Update "Max Team Size" value
3. Click "Update"
4. New limit applies to future joins/poaches
5. Existing teams are not automatically resized

### Managing problematic players/teams
1. Go to admin panel
2. Find the player/team in the table
3. Click "Delete" button
4. Confirm the deletion

## Notes

- The max team size setting is stored in the database (persistent)
- Existing teams with more members than the new limit will not be automatically resized
- All admin actions are immediate and cannot be undone (except by resetting)
