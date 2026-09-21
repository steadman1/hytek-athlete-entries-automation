from pathlib import Path

from pyodbc import Connection, connect


def get_db(path: Path) -> Connection:
    connection_str = (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        r"DBQ=" + str(path) + ";"
    )

    return connect(connection_str)
