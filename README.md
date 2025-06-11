# Roboface

Roboface is an **AI-native open-source robotics stack**. This repository is the main entry point and glue-code; large components (simulation, assets, etc.) live in separate projects that are included here as Git submodules.

---

## 1. TL;DR – first time setup

### Prerequisites:

#### When running on a VM, you should:
```bash
$ apt update
$ apt upgrade
$ apt install vim
# Install python dev headers (needed for ruckig dependency)
$ apt install python3-dev python3.10-dev
```

#### Vulkan Setup:
```bash
$ apt update && apt install -y libegl1 libxext6 vulkan-tools
$ mkdir -p /usr/share/vulkan/icd.d 
$ mkdir -p /usr/share/glvnd/egl_vendor.d
$ cat > /usr/share/vulkan/icd.d/nvidia_icd.json << 'EOF'
{
    "file_format_version" : "1.0.0",
    "ICD": {
        "library_path": "libGLX_nvidia.so.0",
        "api_version" : "1.3.277"
    }
}
EOF
# Check that vulkan can access GPU
$ vulkaninfo | grep NVIDIA
```

#### On every machine
```bash
# Install the ultra-fast Python tool-chain manager `uv`
$ curl -Ls https://astral.sh/uv/install.sh | bash            #   or brew install uv / pipx install uv

# Install direnv to make sure that we always work in the correct .venv
$ curl -sfL https://direnv.net/install.sh | bash
```

```bash
# 1. Clone *recursively* so that submodules are fetched too
$ git clone --recursive https://github.com/Roboface/roboface.git
$ cd roboface

# 2. Enable direnv so the correct .venv is auto-activated
# Add the following line to the ~/.bashrc:
$ eval "$(direnv hook bash)"
# Write this in the terminal at the root directory (/roboface) and the roboface/SimplerEnv directory
$ direnv allow                                              # once per clone

# 3. Create / update the project environment
$ uv sync                                                   # installs exact versions from uv.lock into .venv (will check if the env is up-to-date as well)

# 4. Smoke-test
$ uv run SimplerEnv/scripts/getting_started.py              
```


You are now ready to develop. The steps above take **well under a minute** on a warm cache.

---

## 2. Project structure (top-level)

```text
.
├── main.py                # quick demo entry-point
├── pyproject.toml         # project metadata – keep dependencies here
├── uv.lock                # fully-resolved lock-file – commit changes!
├── .python-version        # default Python used by uv
├── .envrc                 # direnv script pointing to the local .venv
├── SimplerEnv/            # → Git submodule providing simulation envs
└── README.md
```

### Multiple simulators = multiple virtual environments

We keep a **separate `.venv` per simulator** (and therefore per directory) so heavy native dependencies do not clash. `direnv` inspects the current path and activates the correct environment automatically.

---

## 3. Workflow with `uv`

`uv` is the only tool you need for Python packaging _and_ virtual-env management. A couple of rules keep life simple:

| Task                                 | Command                    |
| ------------------------------------ | -------------------------- |
| Install / update the environment     | `uv sync`                  |
| Add runtime dependencies             | `uv add <pkg>`             |
| Add dev-only / group dependencies    | `uv add --group dev <pkg>` |
| Remove a dependency                  | `uv remove <pkg>`          |
| Run a command inside the project env | `uv run <cmd>`             |
| Regenerate lockfile after edits      | `uv lock`                  |

**Never commit the `.venv` directory** – the lock-file is all we need for deterministic builds.

> Tip: if you are migrating a legacy `requirements.txt` run
> `uv add -r requirements.txt && rm requirements.txt` and forget about pip forever.

---

## 4. Working with the SimplerEnv submodule

`SimplerEnv` is large and evolves quickly. Follow these best practices so it never bites you:

### Updating submodules

```bash

# Pull latest changes for *both* the main repo and its submodules
$ git pull --recurse-submodules
$ git submodule update --init --recursive   # check out the new commits
```

### Making changes inside a submodule

1. `cd SimplerEnv`
2. create a feature branch, commit, push **inside the submodule remote**;
3. `cd ..` and commit the _pointer update_ in the main repo.

| Golden rules                                             |
| -------------------------------------------------------- |
| Never do work on a detached HEAD – create a branch.      |
| Always push the submodule first, **then** the main repo. |

---

## 5. CI / automation guidelines

1. Every pipeline must call `uv sync --no-dev` to reproduce the prod environment.
2. Cache `$HOME/.cache/uv` between jobs for tremendous speed-ups.
3. Use `git submodule update --init --recursive` as the first checkout step.

---

## 6. Run WebRTC example
```bash
# Run on the GPU VM from roboface root folder and specify an exposed tcp port (e.g. 3000)
# Check in the VM config what public port this gets mapped to via NAT (e.g. 40701)
$ uv run scripts/webrtc_example.py --port 3000
# Now in a browser you can run the example via: http://{public-vm-ip}:40701
```

## 7. Troubleshooting

| Symptom                            | Fix                                                                                                 |
| ---------------------------------- | --------------------------------------------------------------------------------------------------- |
| "module X not found" after pulling | `uv sync` (env out of date)                                                                         |
| Submodule directory is empty       | `git submodule update --init --recursive`                                                           |
| Detached HEAD inside submodule     | `git switch -c <branch>` or `git checkout main`                                                     |
| Wrong Python selected              | ensure `.python-version` exists _and_ `uv` has that interpreter installed (`uv python install 3.x`) |

---

## 8. Additional references

- uv documentation – https://docs.astral.sh/uv/
- Submodule survival guide – https://delicious-insights.com/en/posts/mastering-git-submodules/
- direnv – https://direnv.net

Happy hacking! 🤖
