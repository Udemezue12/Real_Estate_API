from piccolo.table import Table
from piccolo.columns import UUID, Varchar, Boolean, Timestamptz, ForeignKey


class RoleTable(Table):
    id = UUID(primary_key=True)
    name = Varchar(unique=True)


class UserTable(Table):
    id = UUID(primary_key=True)
    first_name = Varchar()
    last_name = Varchar()
    username = Varchar(unique=True)
    email = Varchar(unique=True)
    phone_number = Varchar(null=True)
    role = Varchar()
    is_active = Boolean(default=True)
    is_verified = Boolean(default=False)
    created_at = Timestamptz()
    updated_at = Timestamptz()
    role:ForeignKey[RoleTable] = ForeignKey(references=RoleTable, null=True)
    hashed_password = Varchar(null=True, secret=True)
