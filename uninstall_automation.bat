@echo off
schtasks /Delete /F /TN "BhaktiDhun-Short-0900"
schtasks /Delete /F /TN "BhaktiDhun-Long-1200"
schtasks /Delete /F /TN "BhaktiDhun-Short-1800"
schtasks /Delete /F /TN "BhaktiDhun-Short-2100"
echo Daily Bhakti Dhun automation tasks removed.
pause
