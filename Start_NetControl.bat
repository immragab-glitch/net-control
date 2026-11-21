@echo off
rem Starts Net Control (it will ask for Administrator permission)
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"
start "" "%PYW%" "%~dp0net_control.py"
