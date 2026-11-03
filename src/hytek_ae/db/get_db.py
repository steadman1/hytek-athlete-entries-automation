"""Database connection helper for Microsoft Access databases."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from pyodbc import Connection, connect

logger = logging.getLogger(__name__)

# Hy-Tek databases (Team Manager and Meet Manager) have a hardcoded Jet/Access
# master database password embedded in their .mdb file headers: '5hY-tek'
DEFAULT_HYTEK_PWD = "5hY-tek"


def get_db(path: Path | str, password: Optional[str] = DEFAULT_HYTEK_PWD) -> Connection:
    """Connect to a Microsoft Access database via pyodbc.

    Hy-Tek Team Manager databases are encrypted with the master password '5hY-tek'.
    If the database is not password protected, falls back to connecting without PWD.
    """
    p = Path(path).resolve()
    base_conn = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        r"DBQ=" + str(p) + ";"
    )

    # First attempt: with the Hy-Tek password (or user-supplied password)
    if password:
        try:
            conn_str = f"{base_conn}PWD={password};"
            return connect(conn_str)
        except Exception as e:
            # If with password failed, try without password
            logger.debug("Failed connecting with password: %s. Trying without password...", e)

    # Second attempt: without password
    try:
        return connect(base_conn)
    except Exception as e:
        # Third attempt: try older 32-bit driver string if installed
        legacy_driver = (
            r"DRIVER={Microsoft Access Driver (*.mdb)};"
            r"DBQ=" + str(p) + ";"
        )
        if password:
            try:
                return connect(f"{legacy_driver}PWD={password};")
            except Exception:
                pass
        return connect(legacy_driver)
