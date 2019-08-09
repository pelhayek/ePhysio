import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded (ref: CS50 pset7 finance)
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached (ref: CS50 pset7 finance)
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Configure session to use filesystem (instead of signed cookies) (ref: CS50 pset7 finance)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")

# Home page (logged out)
@app.route("/home", methods=["GET", "POST"])
def home():
    # If a user is logged in, redirect to logged in Home page
    if session.get("user_id") is not None:
        return redirect('/')
    else:
        return render_template("home.html")

# Home page (logged in)
@app.route("/")
@login_required
def index():
    # Get logged in user's username to display in navbar
    username = db.execute("SELECT username FROM users WHERE id = :id",
                          id=session['user_id'])[0]["username"]
    if session.get("user_id") is not None:
        return render_template('index.html', username=username)

# Login page
@app.route("/login", methods=["GET", "POST"])
def login():
    # If login form submitted, search users database for login details
    if request.method == "POST":
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        # If username/hashed password not found in database, return failure.
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            failed = "Login failed - username or password incorrect"
            return render_template("login.html", failed=failed)
        # If details found, create unique session using user id and take user to home page (logged in).
        session["user_id"] = rows[0]["id"]
        return render_template('index.html', username=request.form.get("username"))
    # If user already logged in, redirect to home page (logged in)
    elif session.get("user_id") is not None:
        return redirect('/')
    #If user not logged in, load login page.
    else:
        return render_template("login.html")

# Registration page
@app.route("/register", methods=["GET", "POST"])
def register():
    # If registration form submitted, check database for existing username.
    if request.method == "POST":
        username=request.form.get("username")
        hash = generate_password_hash(request.form.get("password"))
        result = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash)",
                            username=username, hash=hash)
        # If username exists, return failure
        if not result:
            return render_template("register.html", username=username)
        # If username does not exist, log user in using new unique user ID
        session["user_id"] = result
        return render_template("index.html", username=username)
    # If user logged in already, return to logged in home page
    elif session.get("user_id") is not None:
        return redirect('/')
    # If user not logged in, return registration page
    else:
        return render_template("register.html")

# Explore page
@app.route("/browse", methods=["GET", "POST"])
@login_required
def browse():
    # If user selects a body area from a form, return a dict of diagnosis from corresponding area database
    if request.method == "POST":
        area = request.form.get("area")
        results = db.execute("SELECT ddx1, ddx2, ddx3 FROM " + area)
        # Retrieve unique dictionary values and sort in alphabetical order
        results = set( val for dic in results for val in dic.values())
        results = list(results)
        results.sort()
        return render_template("browse.html", results=results, area=area.title().replace ("_", " "))
    else:
        return render_template("browse.html")

# History page
@app.route("/history")
@login_required
def history():
    # Return all previous test results stored in results database for that user, ordered by most recent results
    results = db.execute(
        "SELECT area, ddx1, ddx2, ddx3, timedate FROM results WHERE user_id=:user_id ORDER BY timedate DESC",
        user_id=session["user_id"])
    return render_template("history.html", results=results)

# Checkup page 1
@app.route("/area", methods=["GET", "POST"])
@login_required
def area():
    # If body area selected and submitted, return corresponding page
    if request.method == "POST":
        location=request.form.get("area")
        return render_template("" + location + ".html")
    else:
        return render_template("area.html")

# One function below will load in response to the pain location selected in the /area page.
# These functions are unique as questions for each pain location differ.
# The shoulder() function, described below, is similar to all of the functions after it.
# e.g. Shoulder page
@app.route("/shoulder", methods=["GET", "POST"])
@login_required
def shoulder():
    # If shoulder form submitted
    if request.method == "POST":
        # Return a dict called "diagnosis" containing three diagnoses (ddx1, ddx2, ddx3) that corresponds to the user's
        # answers submitted in the form regarding pain location, pain onset and shoulder instability.
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM shoulder WHERE location=:location AND onset=:onset AND unstable=:unstable",
            location=request.form.get("location"), onset=request.form.get("onset"), unstable=request.form.get("unstable"))
        # Save the results into a "results" database with the user's unique user_id
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Shoulder", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        # Return the results (diagnosis) page with the three likely diagnoses
        return render_template("diagnosis.html", area="shoulder", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        # If user tries to access shoulder quiz directly, redirect back to home page.
        return redirect('/')

@app.route("/upper_arm", methods=["GET", "POST"])
@login_required
def upper_arm():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM upper_arm WHERE location=:location AND onset=:onset AND referred=:referred",
            location=request.form.get("location"), onset=request.form.get("onset"), referred=request.form.get("referred"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Upper arm", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="upper arm", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/elbow", methods=["GET", "POST"])
@login_required
def elbow():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM elbow WHERE location=:location AND onset=:onset AND click=:click",
            location=request.form.get("location"), onset=request.form.get("onset"), click=request.form.get("click"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Elbow", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="elbow", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/forearm", methods=["GET", "POST"])
@login_required
def forearm():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM forearm WHERE location=:location AND onset=:onset AND time=:time",
            location=request.form.get("location"), onset=request.form.get("onset"), time=request.form.get("time"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Forearm", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="forearm", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/wrist", methods=["GET", "POST"])
@login_required
def wrist():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM wrist WHERE location=:location AND onset=:onset AND time=:time",
            location=request.form.get("location"), onset=request.form.get("onset"), time=request.form.get("time"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Wrist", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="wrist", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/hand", methods=["GET", "POST"])
@login_required
def hand():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM hand WHERE location=:location AND onset=:onset AND deformity=:deformity",
            location=request.form.get("location"), onset=request.form.get("onset"), deformity=request.form.get("deformity"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Hand", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="hand", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/neck", methods=["GET", "POST"])
@login_required
def neck():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM neck WHERE location=:location AND onset=:onset AND referred=:referred",
            location=request.form.get("location"), onset=request.form.get("onset"), referred=request.form.get("referred"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Neck", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="neck", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/middle_back", methods=["GET", "POST"])
@login_required
def middle_back():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM middle_back WHERE location=:location AND onset=:onset AND neck_pain=:neck_pain",
            location=request.form.get("location"), onset=request.form.get("onset"), neck_pain=request.form.get("neck_pain"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Middle Back", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="middle back", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/lower_back", methods=["GET", "POST"])
@login_required
def lower_back():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM lower_back WHERE location=:location AND onset=:onset AND time=:time AND referred=:referred",
            location=request.form.get("location"), onset=request.form.get("onset"), time=request.form.get("time"), referred=request.form.get("referred"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Lower Back", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="lower back", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/hip", methods=["GET", "POST"])
@login_required
def hip():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM hip WHERE location=:location AND onset=:onset AND age=:age AND lbp=:lbp",
            location=request.form.get("location"), onset=request.form.get("onset"), age=request.form.get("age"), lbp=request.form.get("lbp"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Hip", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="hip", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/upper_leg", methods=["GET", "POST"])
@login_required
def upper_leg():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM upper_leg WHERE location=:location AND onset=:onset AND lbp=:lbp",
            location=request.form.get("location"), onset=request.form.get("onset"), lbp=request.form.get("lbp"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Upper Leg", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="upper leg", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/knee", methods=["GET", "POST"])
@login_required
def knee():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM knee WHERE location=:location AND onset=:onset AND unstable=:unstable AND lock=:lock",
            location=request.form.get("location"), onset=request.form.get("onset"), unstable=request.form.get("unstable"), lock=request.form.get("lock"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Knee", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="knee", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/lower_leg", methods=["GET", "POST"])
@login_required
def lower_leg():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM lower_leg WHERE location=:location AND onset=:onset AND swelling=:swelling",
            location=request.form.get("location"), onset=request.form.get("onset"), swelling=request.form.get("swelling"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Lower Leg", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="lower leg", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/ankle", methods=["GET", "POST"])
@login_required
def ankle():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM ankle WHERE location=:location AND onset=:onset AND unstable=:unstable",
            location=request.form.get("location"), onset=request.form.get("onset"), unstable=request.form.get("unstable"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Ankle", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="ankle", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

@app.route("/foot", methods=["GET", "POST"])
@login_required
def foot():
    if request.method == "POST":
        diagnosis = db.execute(
            "SELECT ddx1, ddx2, ddx3 FROM foot WHERE location=:location AND onset=:onset AND time=:time",
            location=request.form.get("location"), onset=request.form.get("onset"), time=request.form.get("time"))
        save = db.execute(
            "INSERT INTO results (user_id, area, ddx1, ddx2, ddx3) VALUES (:user_id, :area, :ddx1, :ddx2, :ddx3)",
            user_id=session["user_id"], area="Foot", ddx1=diagnosis[0]["ddx1"], ddx2=diagnosis[0]["ddx2"], ddx3=diagnosis[0]["ddx3"])
        return render_template("diagnosis.html", area="foot", result1=diagnosis[0]["ddx1"], result2=diagnosis[0]["ddx2"], result3=diagnosis[0]["ddx3"])
    else:
        return redirect('/')

# Logout function
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect("/")