def flash(request, message: str, category: str = "info"):
    """
    Store a flash message in session.
    category: success | error | warning | info
    """
    request.session.setdefault("_flashes", [])
    request.session["_flashes"].append({
        "message": message,
        "category": category
    })


def get_flashed_messages(request):
    """
    Retrieve and clear flash messages from session.
    """
    return request.session.pop("_flashes", [])
