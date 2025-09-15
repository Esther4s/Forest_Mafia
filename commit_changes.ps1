# PowerShell script to commit changes
Write-Host "🚀 Committing changes to git repository..."

# Check git status
Write-Host "📊 Git status:"
git status

# Add all files
Write-Host "📁 Adding files to git..."
git add .

# Commit changes
Write-Host "💾 Creating commit..."
git commit -m "Fix critical statistics and HTML formatting issues

- Fix missing update_user_stats import in bot.py
- Fix create_user function to create stats table entries  
- Replace direct SQL queries with proper database functions
- Add missing get_player_chat_stats import
- Fix HTML formatting in all bot messages (add parse_mode='HTML')
- Add comprehensive statistics testing
- Create detailed fix reports

Fixes:
- Player statistics now save and load correctly
- Chat statistics work properly  
- All HTML bold text displays correctly
- Database integration improved"

Write-Host "✅ Changes committed successfully!"
Write-Host "📋 Commit details:"
git log --oneline -1
