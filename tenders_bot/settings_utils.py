import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class MissingEnvironment(Exception):
    pass


def env_or_err(key: str, default: Any = None, parse_bool: bool = False) -> str:
    env = os.getenv(key, default)
    if env is None:
        raise MissingEnvironment(f"Environment variable {key} is not set")
    if parse_bool:
        val = str(env).lower()
        if val in ("t", "true", "1", "y", "yes"):
            env = True
        elif val in ("f", "false", "0", "n", "no"):
            env = False
        else:
            env = None
    return env


def try_load_env_file(path: Path, absent_ok: bool = True) -> None:
    if os.path.exists(path):
        load_dotenv(path)
    elif not absent_ok:
        raise MissingEnvironment(f"Environment file {path} does not exist")
