import requests
import datetime

from flask import redirect, render_template, session
from functools import wraps


def error(message, code=400):

    # Render error message
    return render_template("error.html", message=message, code=code)


def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def compliance(timestamp1, timestamp2, time):

    input_start = timestamp1
    input_end = timestamp2

    # strptime automatic: 01.01.1900 at 08:30 or 10:15
    start = datetime.datetime.strptime(input_start, "%H:%M")
    end = datetime.datetime.strptime(input_end, "%H:%M")

    difference = end - start

    # if mission around midnigth
    if difference.days < 0:
        difference = datetime.timedelta(days=1) + difference

    minutes = int(difference.total_seconds() / 60)

    if minutes > time[0]["time"]:
        return (False)
    else:
        return (True)
