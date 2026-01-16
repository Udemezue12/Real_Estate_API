# piccolo_conf.py
from piccolo.engine.postgres import PostgresEngine
from admin_piccolo_folder.admin_table import UserTable, RoleTable

DB = PostgresEngine(
    config={
        "user": "estate",
        "password": "wS6IbkAHvZIYfr3FFd7ElQboqYkDjL0i",
        "host": "dpg-d4slpvmr433s739o71mg-a.oregon-postgres.render.com",
        "port": 5432,
        "database": "estate_db_z1er",
        # Optional SSL if Render requires it:
        "ssl": True,
    }
)

APP_REGISTRY = ["admin_piccolo_folder.admin_table"]
