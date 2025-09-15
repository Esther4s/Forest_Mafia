@echo off
echo Начинаем пуш в GitHub...

echo 1. Добавляем все файлы...
"C:\Program Files\Git\bin\git.exe" add .

echo 2. Делаем коммит...
"C:\Program Files\Git\bin\git.exe" commit -m "feat: полная реализация бота с административными правами и исправленными callback обработчиками"

echo 3. Переименовываем ветку в main...
"C:\Program Files\Git\bin\git.exe" branch -M main

echo 4. Пушим в GitHub...
"C:\Program Files\Git\bin\git.exe" push origin main

echo Готово! Проверьте https://github.com/Esther4s/Forest_Mafia
pause
