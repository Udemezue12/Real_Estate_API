from fastapi_admin.resources import Model
from fastapi_admin.widgets import displays, inputs
from models.models import User


class UserResource(Model):
    label = "Users"
    model = User

    fields = [
        "id",
        "first_name",
        "last_name",
        "username",
        "email",
        "phone_number",
        "role",
        "is_active",
        "is_verified",
        # displays.DatetimeDisplay(),
        # displays.DatetimeDisplay(name="updated_at", label="Updated At"),
    ]
    # inputs.
    # filters = [
    #     inputs.Search(name="username", label="Search by Username"),
    #     inputs.Search(name="email", label="Search by Email"),
    #     inputs.Search(name="first_name", label="Search First Name"),
    #     inputs.Search(name="last_name", label="Search Last Name"),
    # ]
