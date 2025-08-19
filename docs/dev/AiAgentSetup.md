# Setup for AI Agent Assistant

**Goal**: Create a dedicated local user account and GitHub account for Claude Code operations, ensuring clear attribution and separation from personal development work.

**Key Components**:
- Dedicated local user account (`ai-agent`) on both macOS and Ubuntu
- Separate GitHub user account for AI operations
- Claude Code authentication on both platforms
- GitHub CLI (`gh`) for GitHub operations

## Create Dedicated User Accounts

### MacOS

Create dev-shared group
```
sudo dseditgroup -o create -n . dev-shared
```

Find which user ids exists on system and choose a non-existent one
```
dscl . -list /Users UniqueID | sort -k2 -n
```

Create ai-agent user
```
sudo dscl . -create /Users/ai-agent
sudo dscl . -create /Users/ai-agent UserShell /bin/bash
sudo dscl . -create /Users/ai-agent RealName "AI Agent for Claude Code"
sudo dscl . -create /Users/ai-agent UniqueID 505
sudo dscl . -create /Users/ai-agent PrimaryGroupID 20
sudo dscl . -create /Users/ai-agent NFSHomeDirectory /Users/ai-agent
```

Add users to dev-shared group
```
sudo dseditgroup -o edit -a arc -t user dev-shared
sudo dseditgroup -o edit -a ai-agent -t user dev-shared
```

Create home directory with proper permissions
```
sudo createhomedir -c -u ai-agent
sudo chown ai-agent:dev-shared /Users/ai-agent
sudo chmod 770 /Users/ai-agent  # ai-agent: rwx, dev-shared: r-x, others: none
```

Ensure unified environment on login
```
cat >> ~/.bash_profile << 'EOF'
if [ -r ~/.bashrc ] ; then
  . ~/.bashrc
fi
EOF
```

Set password for ai-agent
```
sudo passwd ai-agent
```

Verify setup
```
su - ai-agent
whoami                    # Should show: ai-agent
pwd                       # Should show: /Users/ai-agent (macOS) or /home/ai-agent (Linux)
groups                    # Should show: dev-shared (and other groups)
ls -la                    # Check home directory permissions
```

**Gotcha**: The keychain password warning for macOS can be ignored - it's only relevant for GUI logins.

### Ubuntu (GNU/Linux)

Create dev-shared group
```
sudo groupadd dev-shared
```

Create ai-agent user
```
sudo useradd -m -s /bin/bash -c "AI Agent" ai-agent
```

Add users to dev-shared group  
```
sudo usermod -a -G dev-shared $(whoami)
sudo usermod -a -G dev-shared ai-agent
```

Set proper home directory permissions
```
sudo chown ai-agent:dev-shared /home/ai-agent
sudo chmod 770 /home/ai-agent
```

Set password for ai-agent
```
sudo passwd ai-agent
```

Verify setup
```
su - ai-agent
whoami                    # Should show: ai-agent
pwd                       # Should show: /Users/ai-agent (macOS) or /home/ai-agent (Linux)
groups                    # Should show: dev-shared (and other groups)
ls -la                    # Check home directory permissions
```

## Setup SSH Keys

 Generate SSH key pair (use same email on both machines for consistency)
```
# MacOS
ssh-keygen -t ed25519 -C "ai-agent@strudel" -f ~/.ssh/id_ed25519

# Ubuntu
ssh-keygen -t ed25519 -C "ai-agent@groovy" -f ~/.ssh/id_ed25519
```

Set proper permissions
```
chmod 700 ~/.ssh
chmod 600 ~/.ssh/id_ed25519
chmod 644 ~/.ssh/id_ed25519.pub
```

## Workspace Setup

Create workspace structure
```
mkdir -p ~/proj
cd ~/proj
```

Clone the repository
```
git clone git@github.com:cassandra/home-information.git
mv home-information hi
ln -s hi home-information
cd hi
```

Configure git identity for ai-agent
```
git config user.name "AI Agent"
git config user.email "ai-agent@cassandra.org"
```

Verify the setup
```
git remote -v
git status
pwd
```

Also set global git config for consistency:
```
git config --global user.name "AI Agent"
git config --global user.email "ai-agent@cassandra.org"
```

## App Development Setup

### Environment Variables

**Note**: This is mostly duplicative to [Setup.md](Setup.md) though slightly customized for the AI agent setup.  Check there if you run into issues in case this file gets outdated.

Create environment variables for secrets (never commit these!)
```
# Copy your development.sh file

cd ~/proj/hi
mkdir -p .private/env
cat > .private/env/development.sh << 'EOF'
[[paste your development.sh contents here]]
EOF
```

### Redis Tweaks

If you also are presonally also doing development on the same machine, then you should be running Redis and that can also be used by the agent with no extra Redis server needed, but with an environment variable tweak needed (see below). 

If Redis is not running on the machine, you'll need to install and/or start redis as shown in [Dependencies.md](Dependencies.md).

When sharing the same Redis server, we will need to avoid collisions on the key space between development environments.  There is a Redis key prefix environment variable that can be used to do that. For the ai-agent user, chnage this:

export HI_REDIS_KEY_PREFIX="dev-ai"
```
grep -q "HI_REDIS_KEY_PREFIX" .private/env/development.sh && sed -i '' '/HI_REDIS_KEY_PREFIX/c\
export HI_REDIS_KEY_PREFIX="dev-ai"
' .private/env/development.sh

# Then verify value change
grep HI_REDIS_KEY_PREFIX .private/env/development.sh
```

### Virtual Environment

Create and initialize virtual environment
```
python3.11 -m venv venv

# Activate and source
. ./init-env-dev.sh
```

Install python dependencies
```
pip install -r src/hi/requirements/development.txt
```

### App and Database Initializations
```
cd ~/proj/hi
mkdir -p data/database
./src/manage.py check
./src/manage.py migrate
./src/manage.py hi_createsuperuser
./src/manage.py hi_creategroups
```

Verify app code
```
cd ~/proj/hi
make check
```

## Claude Code

Install Claude Code using the official installer
```
curl -fsSL https://claude.ai/install.sh | bash
```

Add to PATH env (now and future)
```
export PATH="~/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
```


After installation, verify:
```
claude-code --version
```


### MacOS-only Create Keychain for Claude OAuth token

**Critical**: Terminal-created users don't have a login keychain, which Claude needs.

Create a keychain for ai-agent:
```
security create-keychain -p "b92ZnuzkXfAYcAth7gXk" ~/Library/Keychains/login.keychain-db
```

Set it as the default keychain
```
security default-keychain -s ~/Library/Keychains/login.keychain-db
```

Verify it exists
```
security list-keychains
security default-keychain
```

Unlock it for use and keep it unlocked for session
```
security unlock-keychain ~/Library/Keychains/login.keychain-db
security set-keychain-settings -t 3600 ~/Library/Keychains/login.keychain-db
```

Create convenience script

```
cat > ~/start-claude.sh << 'EOF'
#!/bin/bash
cd ~/workspace/repos/home-information
security unlock-keychain ~/Library/Keychains/login.keychain-db
security set-keychain-settings -t 3600 ~/Library/Keychains/login.keychain-db
claude
EOF

chmod +x ~/start-claude.sh

# Then just run:
~/start-claude.sh
```

### Run OAuth flow to Autheticate to Anthropic

- Start up with `claude`.
- Select the color scheme when prompted
- On authetication screen, choose subsciption login
- This gives a browser URL (or visits url if browser access available)
- Visit URL, login into Anthropic account (if needed)
- Click button to authorize
- Copy and paste resulting token from browser into terninal.

**Gotcha**: After OAuth completes, you may have to exit and restart Claude for the authentication to take effect.

## GitHub Setup

### Option 1: Separate GitHub User

#### Create new GitHub account:

- Go to github.com in incognito/private browser
- Sign up with a new email (ai-agent@cassandra.org)
- Username suggestion: cassandra-ai-agent

#### Add SSH keys to New Account

Display the public key to add to GitHub
```
cat ~/.ssh/id_ed25519.pub
```

For GitHub setup:

1. Copy the public key output from both machines
2. Go to GitHub → User Icon → Settings → SSH and GPG keys → New SSH key
3. Add both public keys with descriptive titles:
  - "ai-agent@strudel (MacOS laptop)"
  - "ai-agent@groovy (Ubuntu Desktop)"

Test SSH connection (run on both machines as ai-agent):
```
ssh -T git@github.com
```

#### Add as collaborator:

- In your main account, go to repository Settings
- Collaborators → Add people
- Invite the new account with "Write" access

#### Install gh CLI

Install from main account (system-wide install)
```
# MacOS
brew install gh

# Ubuntu
sudo apt install gh

# Verify installation (as ai-agent on both):
gh --version
```

#### Configure gh CLI:

Generate a Personal Acess Toke (PAT in GitHub Console
1. Login to the new GitHub account (in any browser)
2. Go to Settings → Developer settings → Personal access tokens → Tokens (classic)
3. Click Generate new token → Generate new token (classic)
4. Set name
5. Set expiry (Custom -> One year)
6. Set permission scopes
  - repo (all)
  - workflow
  - admin.org -> read.org
  - write:discussion
  - project (all)
7. Generate and save in 1Password

Autheticate CLI with token
```
gh auth login
```

1. Choose: GitHub.com
2. HTTPS
3. Auth w/GitHub Credentials
4. Paste token from 1Password

####  Prepare for Use

Create helper script.  Environment must be initialized before starting claude!
```
cat > ~/start.sh << 'EOF'
#!/bin/bash
cd proj/hi
. init-env-dev.sh
claude
EOF

chmod 755 ~/start.sh
```

Usage
```
su - aipagent
./start.sh
```

## Option to Avoid: GitHub App Setup (Aborted)

* THIS DID NOT WORK. LIKELY BUG IN CLAUDE CODE. SAVING STEPS FOR REFERFENCE ONLY.  *

#### Create GitHub App

In GitHub console:

- Creat GitHub app in GitHub profile 
  - Read and write access to actions, checks, code, commit statuses, discussions, issues, and pull requests 
- Generate and downloaded private key
- Connect GitHub app to home-information repo.

#### App Details

- cassandra-ai-agent
- App ID: 1798555
- Client ID: Iv23lik8L3LA5QzJVd9K
- Installation Id for home-information repo: 81448612
- Private key: ~/.ssh//cassandra-ai-agent.2025-08-17.private-key.pem

### Setting GitHub App Credentials

Create Claude Code configuration directory
```
mkdir -p ~/.claude-code
```

Create project-specific Claude settings
```
cd ~/proj/hi
mkdir -p .claude
```

Copy the GitHub app private key to both ai-agent accounts:
```
# As 'arc' user:
scp ~/.ssh/cassandra-ai-agent.2025-08-17.private-key.pem strudel:/tmp
scp ~/.ssh/cassandra-ai-agent.2025-08-17.private-key.pem groovy:/tmp
```

As ai-agent, create secure directory for GitHub App credentials
```
mkdir -p ~/.config/github-app
chmod 700 ~/.config/github-app
```

Copy your .pem file to this location (you'll need to do this manually).
```
cp /tmp/cassandra-ai-agent.2025-08-17.private-key.pem ~/.config/github-app/github-app-private-key.pem
```

Then set proper permissions:
``` 
chmod 600 ~/.config/github-app/github-app-private-key.pem
```

Create Claude settings to use GitHub App instead of PAT
```
cd ~/proj/hi

cat > .claude/settings.local.json << 'EOF'
{
  "mcp": {
    "servers": {
      "github": {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-github"],
        "env": {
          "GITHUB_APP_ID": "1798555",
          "GITHUB_APP_INSTALLATION_ID": "81448612",
          "GITHUB_APP_PRIVATE_KEY_PATH": "~/.config/github-app/github-app-private-key.pem"
        }
      }
    }
  },
  "permissions": {
    "allow": [
      "mcp__github__*",
      "Bash(python manage.py:*)",
      "Bash(./manage.py test:*)",
      "Bash(flake8:*)",
      "Bash(gh issue:*)",
      "Bash(python -m pytest:*)",
      "Bash(find:*)",
      "Bash(grep:*)",
      "Bash(python -m flake8:*)",
      "Bash(python:*)",
      "Bash(git:*)"
    ],
    "deny": []
  }
}
EOF
```

### Node Install

Also install Node.js if not available (needed for GitHub MCP server)
```
# On macOS (as 'arc' user who has Homebrew access available):
brew install node

# On Ubuntu (as 'arc' user who has apt access available):
sudo apt update && sudo apt install nodejs npm

```

Verify ai-agent user can access required executables:
```
which claude
which node
which npm
```

### Verify Authentication to GitHub


Test GitHub App authentication by starting Claude and asking it to list issues
```
claude
```

In Claude, test these commands:
1. List the open issues in this repository
2. Show me the recent commits
3. What files are in the src directory?
  
Expected results:
- Claude Code starts without errors
- MCP GitHub server connects successfully
- You can see repository issues
- GitHub App authentication works

If you get errors:
- Check file paths in settings.local.json
- Verify .pem file permissions (should be 600)
- Ensure the repository directory contains .claude/settings.local.json
