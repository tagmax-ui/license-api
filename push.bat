@echo off
REM Ce script ajoute tout, commit avec la date et heure, puis push

REM Récupère la date et l'heure au format AAAA-MM-JJ_HH-MM-SS
for /f "tokens=1-4 delims=/ " %%a in ('date /t') do set DATE=%%d-%%b-%%c
for /f "tokens=1-2 delims=: " %%a in ('time /t') do set HEURE=%%a-%%b

REM Pour un format unique et portable :
set TIMESTAMP=%DATE%_%HEURE%

REM Add, commit, push
git add -A
git commit -m "Auto commit %TIMESTAMP%"
git push

pause
