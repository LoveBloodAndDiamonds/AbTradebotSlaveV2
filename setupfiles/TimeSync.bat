@echo off
net start w32time
w32tm /resync
pause