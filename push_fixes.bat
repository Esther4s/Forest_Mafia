@echo off
echo Adding files to git...
git add callback_handler.py night_actions.py night_interface.py
echo Committing changes...
git commit -m "Исправлены ошибки в ночных действиях волка и зайцев

- Исправлен метод _find_user_game в callback_handler.py для корректного поиска игры пользователя
- Добавлен импорт logger в night_actions.py
- Улучшена обработка зайцев в night_interface.py
- Исправлена логика проверки завершения ночных действий для всех ролей"
echo Pushing to remote repository...
git push origin main
echo Done!
pause