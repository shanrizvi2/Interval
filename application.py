import os
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from passlib.apps import custom_app_context as pwd_context
import datetime

from helpers import apology, login_required

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///hours.db")

@app.route("/register", methods=["GET", "POST"])
def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure password was submitted
        if request.form.get("password") != request.form.get("confirmation"):
            return apology("passwords do not match", 403)

        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hashed)", username = request.form.get("username"), hashed = generate_password_hash(request.form.get("password")))

        if not result:
            return apology("username already exists, try a different one", 403)

        session["user_id"] = result

        return render_template("login.html")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/dash")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")




@app.route("/")
def index():
    return render_template("title.html")

@app.route("/dash")
@login_required
def dash():
    activities = db.execute("SELECT * FROM activities WHERE id = :id", id=session["user_id"])
    data = db.execute("SELECT * FROM log WHERE id = :id", id=session["user_id"])
    array = []

    for activities in activities:
        for i in reversed(range(7)):
            day = datetime.datetime.now() - datetime.timedelta(days = i)
            print (day)
            check = db.execute("SELECT * FROM log WHERE id = :id AND activity = :activity AND date = :date", id=session["user_id"], activity=activities["activity"], date=day)
            if not check:
                array.append(0)
            else:
                array.append(int(check[0]["hours"]))
    print(array)
    activities = db.execute("SELECT * FROM activities WHERE id = :id", id=session["user_id"])
    return render_template("dash.html", rows=activities, data = data, array = array)


@app.route("/new", methods=["GET", "POST"])
@login_required
def new():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        activity = request.form.get("name")
        goal = int(request.form.get("goal"))

        curAct = db.execute("SELECT * FROM activities WHERE id = :id AND activity = :activity", id=session["user_id"], activity=activity)

        if curAct:
            return apology("You have already created this activity", 403)
        else:
            db.execute("INSERT INTO activities (activity, goal, id) VALUES(:activity, :goal, :id)", activity=activity, goal = goal, id=session["user_id"])

        # Redirect user to home page
        return redirect("/log")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("new.html")

@app.route("/log", methods=["GET", "POST"])
@login_required
def log():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        activity = request.form.get("active")
        if activity == "":
            return apology("Please select an activity", 403)

        if request.form.get("hour") == "":
            hour = 0
        else:
            hour = int(request.form.get("hour"))
        if request.form.get("minutes") == "":
            minutes = 0
        else:
            minutes = int(request.form.get("minutes"))

        time = hour + (minutes/60)
        curLog = db.execute("SELECT * FROM log WHERE id = :id AND activity = :activity AND date=:date", id=session["user_id"], activity=activity, date= datetime.date.today())
        if not curLog:
            db.execute("INSERT INTO log (id, activity, hours) VALUES (:id, :activity, :hours)", id = session["user_id"], activity=activity, hours=time)
        else:
            totHours = curLog[0]["hours"] + time
            db.execute("UPDATE log SET hours=:hours WHERE id = :id AND activity = :activity AND date=:date", hours=totHours, id = session["user_id"], activity=activity, date= datetime.date.today())

        total = db.execute("SELECT * FROM activities WHERE id = :id AND activity = :activity", id = session["user_id"], activity=activity)
        if total[0]["total"] is None:
            totalHours = time
        else:
            totalHours = total[0]["total"] + time

        db.execute("UPDATE activities SET total=:total WHERE id = :id AND activity = :activity", total=totalHours, id = session["user_id"], activity=activity)

        db.execute("INSERT INTO history (id, activity, hours, minutes) VALUES(:id, :activity, :hours, :minutes)", id=session["user_id"], activity=activity, hours=hour, minutes=minutes)

        # Redirect user to home page
        return redirect("/dash")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        activities = db.execute("SELECT * FROM activities WHERE id = :id", id=session["user_id"])
        return render_template("log.html", rows=activities)

@app.route("/history")
@login_required
def history():
    row = db.execute("SELECT * FROM history WHERE id = :ids", ids = session["user_id"])
    return render_template("history.html", row = reversed(row))


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
