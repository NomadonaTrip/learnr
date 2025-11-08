# Docker Desktop WSL2 Setup Guide

Docker is currently not available in your WSL2 environment. Follow these steps to enable it:

## Step 1: Enable Docker Desktop WSL2 Integration

### If Docker Desktop is Already Installed:

1. **Open Docker Desktop** on Windows (not in WSL2)
   - Find it in your Windows Start menu

2. **Open Settings**
   - Click the gear icon (⚙️) in the top right

3. **Navigate to Resources → WSL Integration**
   - In the left sidebar: Settings → Resources → WSL Integration

4. **Enable WSL Integration**
   - Toggle ON: "Enable integration with my default WSL distro"
   - Find your WSL2 distro in the list (likely "Ubuntu" or similar)
   - Toggle it ON

5. **Apply & Restart**
   - Click "Apply & Restart" button
   - Wait for Docker Desktop to restart (may take 30-60 seconds)

### If Docker Desktop is NOT Installed:

1. **Download Docker Desktop for Windows**
   - Visit: https://www.docker.com/products/docker-desktop/
   - Download the Windows version

2. **Install Docker Desktop**
   - Run the installer
   - Ensure "Use WSL 2 instead of Hyper-V" is checked during installation
   - Restart your computer if prompted

3. **Enable WSL2 Integration** (follow steps above)

## Step 2: Verify Docker Works in WSL2

After enabling WSL2 integration, open a NEW WSL2 terminal and run:

```bash
docker --version
docker-compose --version
```

You should see version numbers like:
```
Docker version 24.x.x, build xxxxx
Docker Compose version v2.x.x
```

## Step 3: Return to LearnR Setup

Once Docker is working, let me know and I'll proceed with:
1. Starting PostgreSQL container
2. Generating database migration
3. Creating tables
4. Seeding test data
5. Testing the API

## Troubleshooting

### "Docker daemon is not running"
- Make sure Docker Desktop is running on Windows
- Look for the Docker icon in Windows system tray (bottom right)
- It should NOT have a red X on it

### "Cannot connect to Docker daemon"
- Restart Docker Desktop
- Close and reopen your WSL2 terminal
- Try running `wsl --shutdown` in Windows PowerShell, then reopen WSL2

### WSL2 distro not showing in Docker settings
- Make sure you're using WSL2 (not WSL1)
- Check in PowerShell: `wsl -l -v`
- Should show "VERSION 2" for your distro

### Still having issues?
- Restart your computer
- Update Docker Desktop to the latest version
- Check Docker Desktop logs (Settings → Troubleshoot → View logs)

## Next Steps

Once Docker is working, run this command to verify everything:

```bash
cd /mnt/e/toolmaker/python/learnr_build
docker-compose config
```

This should show your Docker Compose configuration without errors.

Then we'll proceed with database setup!
