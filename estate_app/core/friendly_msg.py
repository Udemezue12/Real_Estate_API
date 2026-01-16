FRIENDLY_MESSAGES = {
    "ConnectionError": "Unable to connect to a required service. Please try again later.",
    "TimeoutError": "The request took too long. Please try again later.",
    "DatabaseError": "Temporary issue while accessing data. Please try again shortly.",
    "ValueError": "Invalid data received. Please check your input and try again.",
    "KeyError": "Some required information is missing.",
    "PermissionError": "You don’t have permission to perform this action.",
}


def get_friendly_message(error: Exception) -> str:
    for key, msg in FRIENDLY_MESSAGES.items():
        if key.lower() in str(type(error)).lower():
            return msg
    return "Something went wrong on our end. Please try again."