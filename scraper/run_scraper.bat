@echo off
cd C:\Users\snatt\Documents\MY_APP_PROJECTS_NEW\smart-basket\scraper
set SUPABASE_URL=https://bqwexelzzxgolvzmmovo.supabase.co
set SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxd2V4ZWx6enhnb2x2em1tb3ZvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxNjkwNDEsImV4cCI6MjA4ODc0NTA0MX0.GZFS5ifuNOD6f3xpHMhIB0F7XURlve-cdV3T9BXIOj4

:: Create dated log file e.g. scraper_20260313.log
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /format:list') do set dt=%%I
set logfile=logs\scraper_%dt:~0,8%.log

echo Starting SmartPicks Scraper at %date% %time% > %logfile%
python main.py >> %logfile% 2>&1
echo Finished at %date% %time% >> %logfile%

:: Delete logs older than 7 days
forfiles /p logs /m scraper_*.log /d -7 /c "cmd /c del @path" 2>nul
set TELEGRAM_BOT_TOKEN=8726173615:AAFEfwj38iLg9JYPNGvwOHFO47gqk6KmeHM