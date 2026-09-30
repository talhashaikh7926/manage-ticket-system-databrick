import os
import logging
from databricks.sdk import WorkspaceClient
import psycopg
from psycopg.rows import dict_row

logger = logging.getLogger("ticketing-app")

_w = WorkspaceClient()

PGHOST = os.environ.get("PGHOST")
PGDATABASE = os.environ.get("PGDATABASE", "databricks_postgres")
PGUSER = os.environ.get("PGUSER")
PGPORT = os.environ.get("PGPORT", "5432")
ENDPOINT_NAME = os.environ.get("ENDPOINT_NAME")


def get_connection():
    token = _w.postgres.generate_database_credential(endpoint=ENDPOINT_NAME).token
    conn = psycopg.connect(
        host=PGHOST,
        port=PGPORT,
        dbname=PGDATABASE,
        user=PGUSER,
        password=token,
        sslmode="require",
    )
    conn.row_factory = dict_row
    return conn
