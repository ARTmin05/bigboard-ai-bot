@echo off
chcp 65001 >nul
schtasks /Run /TN BigBoardBot >nul && echo Бот запущен в фоне. || echo Не удалось запустить. Сначала выполните setup-autostart.ps1
timeout /t 3 >nul
