<img src="../../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Dependencies

_Notes and help for project dependencies._

_Provided for convenience. May be outdated._

### Python

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

### Redis

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
