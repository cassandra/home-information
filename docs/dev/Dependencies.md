<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Dependencies

_Notes and help for project dependencies._

_Provided for convenience. May be outdated._

### Python

_Needed for running and for local development._

#### MacOS

Get python 3.11 package and install from: [https://www.python.org/downloads/](https://www.python.org/downloads/)

#### Ubuntu (GNU/Linux)

``` shell
 sudo apt update && sudo apt upgrade
 sudo add-apt-repository ppa:deadsnakes/ppa
 sudo apt-get update
 apt list | grep python3.11
 sudo apt-get install python3.11
 sudo apt install python3.11-venv
```

### Docker

_For running, optional for local development._

#### MacOS

See: [https://docs.docker.com/desktop/setup/install/mac-install/](https://docs.docker.com/desktop/setup/install/mac-install/)

#### Ubuntu (GNU/Linux)

``` shell
sudo apt-get update
sudo apt-get remove docker docker-engine docker.io
sudo apt install docker.io
sudo apt install docker-compose
sudo systemctl start docker
```

### GitHub - SSH Key Setup

_For local development only._

#### MacOS and Ubuntu (GNU/Linux)

It is a better security practice, but not required, to generate an SSH key dedicated for GitHub use. If you do not have an SSH key already generated, or want to generate one for GitHub use, then use one of these, replacing with your email:
``` shell
ssh-keygen -t ed25519 -C "yourname@example.com" -f ~/.ssh/github_key

# or just
ssh-keygen -t ed25519 -C "yourname@example.com"
```

Then on GitHub:
- go to your profile settings (click your profile picture, then "Settings");
- click "SSH and GPG keys";
- click "New SSH key" (or "Add SSH key");
- give the key a descriptive name (e.g., "My Laptop"),
- type is "Authentication Key" (the default);
- paste your public key into the key field. (e..g, `~/.ssh/github_key.pub` or `~/.ssh/id_e25519.pub`); and then
- finish by clicking the "Add SSH Key" button.

If you decided to use a dedicated GitHub key (i.e., not the default key), it is also recommeneded (but not required) to add this section to `~/.ssh/config`:
``` shell
Host github.com
    IdentityFile ~/.ssh/github_key
    PreferredAuthentications publickey
```

You can test if this is set up and working properly from your local command line with:
``` shell
ssh -T git@github.com
```
If it is working, you should see a message like:
``` shell
Hi <yourname>! You've successfully authenticated, but GitHub does not provide shell access.
```

### Redis

_For local development only._

#### MacOS

Download tarball from: [https://redis.io/download](https://redis.io/download).


``` shell
brew install redis

# Yields these executables:
/usr/local/bin/redis-server 
/usr/local/bin/redis-cli 

mkdir ~/.redis
touch ~/.redis/redis.conf
```
Then run with `redis-server`.

#### Ubuntu (GNU/Linux)

``` shell
cd ~/Downloads
tar zxvf redis-6.2.1.tar.gz
cd redis-6.2.1
make test
make

sudo cp src/redis-server /usr/local/bin
sudo cp src/redis-cli /usr/local/bin

mkdir ~/.redis
touch ~/.redis/redis.conf
```
Then run with `redis-server`.
