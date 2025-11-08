# Docker Permission Issue - Quick Fix

## The Problem

Docker Desktop is running, but you're getting:
```
permission denied while trying to connect to the Docker daemon socket
```

This means your user account isn't in the `docker` group.

## The Solution (2 minutes)

### Step 1: Add yourself to docker group

In your **current** WSL2 terminal, run:

```bash
sudo usermod -aG docker $USER
```

Enter your password when prompted.

### Step 2: Apply the change

The group change only takes effect in **new** shell sessions.

**You MUST do ONE of these:**

**Option A: Logout and login (BEST)**
```bash
# In WSL2, run:
exit
# Then close the WSL2 window completely
# Open a NEW WSL2 window
```

**Option B: Restart WSL (RECOMMENDED)**
```bash
# In Windows PowerShell (as Administrator), run:
wsl --shutdown
# Wait 5 seconds, then open a new WSL2 terminal
```

**Option C: Use newgrp (QUICK)**
```bash
# In your current WSL2 terminal:
newgrp docker
```

### Step 3: Verify it works

In the new terminal, test:

```bash
docker ps
```

**Expected output:**
```
CONTAINER ID   IMAGE     COMMAND   CREATED   STATUS    PORTS     NAMES
```

(Should be empty list, NOT a permission error)

### Step 4: Return and continue

Once `docker ps` works without sudo, let me know and I'll proceed with database setup!

---

## Alternative: Use sudo (Not Recommended)

If you can't fix permissions now, I can use `sudo` for all Docker commands.

**Drawback:** You'll need to enter your password multiple times during setup.

**To use this option:** Just tell me "use sudo" and I'll adjust the scripts.

---

## Troubleshooting

**"usermod: user 'nomad' does not exist"**
→ Replace `$USER` with your actual username

**"newgrp: group 'docker' does not exist"**
→ Docker Desktop didn't create the group. Try restarting Docker Desktop in Windows.

**Still getting permission denied after all steps**
→ Run: `groups` and verify "docker" is in the list
→ If not, try `wsl --shutdown` in PowerShell and start fresh

**Docker Desktop shows "Docker Engine stopped"**
→ Click the whale icon → Settings → Ensure "Use WSL 2 based engine" is checked
→ Restart Docker Desktop

