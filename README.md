# roboface


# Python Package and virtual environments managing
We use uv.

Sync up so you install all the dependencies of the project: uv sync (this is everything that you should do)

Add an extra dependency: uv add (you can do 'uv add -r requirements.txt)

The exact dependency versions are saved in uv.lock, this file should be committed

We keep a seperate .venv for each simulator that we support on the platform.

To make sure that the right .env gets selected you should have direnv installed and type direnv allow in the root directory. Direnv will load .envrc for each directory that you cd in.
