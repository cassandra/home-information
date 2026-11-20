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

### Poppler

_Optional. Required for PDF thumbnail previews on file attributes. Without it, PDF attributes still upload and work — they just display a generic icon instead of a rendered preview._

The `pdf2image` Python package (installed via requirements) shells out to `pdftoppm` from the `poppler-utils` system package. Docker builds install this automatically; local development needs it installed separately.

#### MacOS

``` shell
brew install poppler
```

#### Ubuntu (GNU/Linux)

``` shell
sudo apt install poppler-utils
```


### pdf.js

_Vendored; nothing to install. Renders PDFs in the in-app file viewer (`file-viewer-pdf.js`)._

[pdf.js](https://github.com/mozilla/pdf.js) (Mozilla, Apache-2.0) is checked in under `src/hi/static/pdfjs-<version>/`, taken from the `pdfjs-dist` npm package:

- `build/`: the **legacy** build (`legacy/build/pdf.min.mjs`, `pdf.worker.min.mjs`). Per the pdf.js FAQ, it supports Chrome 125+, Firefox ESR, and Safari 18+ (so iOS/iPadOS 18+, which every iOS browser shares). Older browsers show the viewer's "Couldn't load this file" message for PDFs.
- `wasm/`: image decoders for scanned PDFs (JBIG2, JPEG 2000) and color management (qcms), with their non-wasm fallbacks. QuickJS (PDF form scripting) is left out.
- `iccs/`, `standard_fonts/`: color profile and fonts for PDFs that use, without embedding, the standard fonts.
- `cmaps/` (CJK text) is left out.
- License files from the package are kept alongside each part.

The browser loads these only when a PDF is opened; the resource folders only when a document needs them.

**Serving:** the build ships as `.mjs` ES modules, which browsers load only with a JavaScript content type. `package/docker_nginx.conf` maps `.mjs` for `/static/`, since nginx's `mime.types` does not.

**Updating:** watch the [pdf.js releases](https://github.com/mozilla/pdf.js/releases) and security advisories. To update:

1. `npm pack pdfjs-dist@<version>` and extract it.
2. Create `src/hi/static/pdfjs-<version>/` with the same files as the current version, then remove the old directory.
3. Update `PdfJsAssets.STATIC_DIRECTORY` in `src/hi/apps/common/file_viewer.py`.
4. Check the PDF samples on the File Viewer UI test page (`/testing/ui/common/file-viewer`).
