@echo off
net stop postgresql-x64-16
timeout /t 3 /nobreak
net start postgresql-x64-16
echo PostgreSQL restarted
timeout /t 2 /nobreak
