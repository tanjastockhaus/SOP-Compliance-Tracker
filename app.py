import csv
import io

from cs50 import SQL
from flask import Flask, Response, redirect, render_template, request, jsonify, session
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import error, login_required, compliance

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///project.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]

    return render_template("index.html")


@app.route("/input", methods=["GET"])
def input():
    return render_template("input.html")


@app.route("/stemi_input", methods=["GET", "POST"])
@login_required
def stemi_input():
    user_id = session["user_id"]

    if request.method == "POST":

        data = request.get_json()
        date = data.get("date")
        on_scene = data.get("time1")
        ecg = data.get("time2")
        force_insert = data.get("force_insert", False)  # from continue button

        if not date:
            return error("Must provide date", 400)
        if not on_scene:
            return error("Must provide On-scene time", 400)
        if not ecg:
            return error("Must provide ECG time", 400)

        # Logic request:
        # if time2 is smaller than time 1 and user didnt continue
        if ecg < on_scene and not force_insert:
            return jsonify({'status': 'show_warning'})

        # INSERT
        protocol_id = db.execute("SELECT id FROM protocolls WHERE name = 'stemi'")
        time = db.execute("SELECT time FROM protocolls WHERE name = 'stemi'")
        compliance_check = compliance(on_scene, ecg, time)

        try:
            db.execute("INSERT INTO missions_stemi (user_id, protocol_id, date, on_scene, ecg, compliance) VALUES (?, ?, ?, ?, ?, ?)",
                       user_id, protocol_id[0]["id"], date, on_scene, ecg, compliance_check)
            return jsonify({'status': 'success'})

        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

    else:
        return render_template("stemi_input.html")


@app.route("/stroke_input", methods=["GET", "POST"])
@login_required
def stroke_input():
    user_id = session["user_id"]

    if request.method == "POST":

        data = request.get_json()
        date = data.get("date")
        on_scene = data.get("time1")
        ct = data.get("time2")
        force_insert = data.get("force_insert", False)  # from continue button

        if not date:
            return error("Must provide date", 400)
        if not on_scene:
            return error("Must provide On-scene time", 400)
        if not ct:
            return error("Must provide CT time", 400)

        # Logic request:
        # if time2 is smaller than time 1 and user didnt continue
        if ct < on_scene and not force_insert:
            return jsonify({'status': 'show_warning'})

        # INSERT
        protocol_id = db.execute("SELECT id FROM protocolls WHERE name = 'stroke'")
        time = db.execute("SELECT time FROM protocolls WHERE name = 'stroke'")
        compliance_check = compliance(on_scene, ct, time)

        try:
            db.execute("INSERT INTO missions_stroke (user_id, protocol_id, date, on_scene, ct, compliance) VALUES (?, ?, ?, ?, ?, ?)",
                       user_id, protocol_id[0]["id"], date, on_scene, ct, compliance_check)
            return jsonify({'status': 'success'})

        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

    else:
        return render_template("stroke_input.html")


@app.route("/trauma_input", methods=["GET", "POST"])
@login_required
def trauma_input():
    user_id = session["user_id"]

    if request.method == "POST":

        data = request.get_json()
        date = data.get("date")
        on_scene = data.get("time1")
        trauma = data.get("time2")
        force_insert = data.get("force_insert", False)  # from continue button

        if not date:
            return error("Must provide date", 400)
        if not on_scene:
            return error("Must provide On-scene time", 400)
        if not trauma:
            return error("Must provide Trauma Bay time", 400)

        # Logic request:
        # if time2 is smaller than time 1 and user didnt continue
        if trauma < on_scene and not force_insert:
            return jsonify({'status': 'show_warning'})

        # INSERT
        protocol_id = db.execute("SELECT id FROM protocolls WHERE name = 'trauma'")
        time = db.execute("SELECT time FROM protocolls WHERE name = 'trauma'")
        compliance_check = compliance(on_scene, trauma, time)

        try:
            db.execute("INSERT INTO missions_trauma (user_id, protocol_id, date, on_scene, trauma, compliance) VALUES (?, ?, ?, ?, ?, ?)",
                       user_id, protocol_id[0]["id"], date, on_scene, trauma, compliance_check)
            return jsonify({'status': 'success'})

        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

    else:
        return render_template("trauma_input.html")


# just visual site when /stemi in browser
@app.route("/stemi", methods=["GET"])
@login_required
def stemi():
    user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    users = []
    workplaces = []

    if is_admin:
        users = db.execute(
            "SELECT id, username, work FROM users ORDER BY username"
        )
        workplaces = db.execute(
            "SELECT DISTINCT work FROM users WHERE work IS NOT NULL ORDER BY work"
        )

    return render_template(
        "stemi.html",
        users=users,
        workplaces=workplaces,
        is_admin=is_admin,
    )


@app.route("/api/stemidashboard-data", methods=["GET"])
@login_required
def get_stemidashboard_data():

    current_user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    # reading filter from JavaScript-Fetch
    filter_user = request.args.get("user_id", "all")
    filter_workplace = request.args.get("workplace", "all")

    # Data protection in backend:
    # If the user is not an admin, override filters with manipulated requests
    # Users sees only it's own data
    if not is_admin:
        filter_user = str(current_user_id)
        filter_workplace = "all"

    # preparing base-KPIs
    kpi_base_query = """
        SELECT
            COUNT(*) as gesamt,
            SUM(CASE WHEN m.compliance = 1 THEN 1 ELSE 0 END) as konform
        FROM missions_stemi m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    chart_base_query = """
        SELECT m.date, COUNT(*) as count
        FROM missions_stemi m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    sql_params = []

    # dynamic SQL-gerneration based on the filters
    if filter_user != "all":
        kpi_base_query += " AND m.user_id = ?"
        chart_base_query += " AND m.user_id = ?"
        sql_params.append(filter_user)

    if filter_workplace != "all":
        kpi_base_query += " AND u.work = ?"
        chart_base_query += " AND u.work = ?"
        sql_params.append(filter_workplace)

    chart_base_query += " GROUP BY m.date ORDER BY m.date ASC LIMIT 7"

    # crash protection
    if sql_params:
        kpi_result = db.execute(kpi_base_query, *sql_params)
        chart_rows = db.execute(chart_base_query, *sql_params)
    else:
        # CS50 Queries
        kpi_result = db.execute(kpi_base_query)
        chart_rows = db.execute(chart_base_query)

    # Data-parsing
    if kpi_result and len(kpi_result) > 0:
        total_missions = kpi_result[0]["gesamt"] if kpi_result[0]["gesamt"] is not None else 0
        compliant_missions = kpi_result[0]["konform"] if kpi_result[0]["konform"] is not None else 0
    else:
        total_missions = 0
        compliant_missions = 0

    compliance_rate = "0%"
    if total_missions > 0:
        rate = (compliant_missions / total_missions) * 100
        compliance_rate = f"{rate:.1f}%"

    dates = [row["date"] for row in chart_rows]
    mission_counts = [row["count"] for row in chart_rows]

    return jsonify({
        "kpi": {
            "total_missions": total_missions,
            "compliant_missions": compliant_missions,
            "compliance_rate": compliance_rate,
        },
        "charts": {"labels": dates, "values": mission_counts},
    })


@app.route("/stroke", methods=["GET"])
@login_required
def stroke():
    user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    users = []
    workplaces = []

    if is_admin:
        users = db.execute(
            "SELECT id, username, work FROM users ORDER BY username"
        )
        workplaces = db.execute(
            "SELECT DISTINCT work FROM users WHERE work IS NOT NULL ORDER BY work"
        )

    return render_template(
        "stroke.html",
        users=users,
        workplaces=workplaces,
        is_admin=is_admin,
    )


@app.route("/api/strokedashboard-data", methods=["GET"])
@login_required
def get_strokedashboard_data():

    current_user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    # reading filter from JavaScript-Fetch
    filter_user = request.args.get("user_id", "all")
    filter_workplace = request.args.get("workplace", "all")

    # Data protection in backend:
    # If the user is not an admin, override filters with manipulated requests
    # Users sees only it's own data
    if not is_admin:
        filter_user = str(current_user_id)
        filter_workplace = "all"

    # preparing base KPIs
    kpi_base_query = """
        SELECT
            COUNT(*) as gesamt,
            SUM(CASE WHEN m.compliance = 1 THEN 1 ELSE 0 END) as konform
        FROM missions_stroke m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    chart_base_query = """
        SELECT m.date, COUNT(*) as count
        FROM missions_stroke m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    sql_params = []

    # dynamic SQL-generation based on filters
    if filter_user != "all":
        kpi_base_query += " AND m.user_id = ?"
        chart_base_query += " AND m.user_id = ?"
        sql_params.append(filter_user)

    if filter_workplace != "all":
        kpi_base_query += " AND u.work = ?"
        chart_base_query += " AND u.work = ?"
        sql_params.append(filter_workplace)

    chart_base_query += " GROUP BY m.date ORDER BY m.date ASC LIMIT 7"

    # crash protection
    if sql_params:
        kpi_result = db.execute(kpi_base_query, *sql_params)
        chart_rows = db.execute(chart_base_query, *sql_params)
    else:
        # CS50 Queries
        kpi_result = db.execute(kpi_base_query)
        chart_rows = db.execute(chart_base_query)

    # Data-parsing
    if kpi_result and len(kpi_result) > 0:
        total_missions = kpi_result[0]["gesamt"] if kpi_result[0]["gesamt"] is not None else 0
        compliant_missions = kpi_result[0]["konform"] if kpi_result[0]["konform"] is not None else 0
    else:
        total_missions = 0
        compliant_missions = 0

    compliance_rate = "0%"
    if total_missions > 0:
        rate = (compliant_missions / total_missions) * 100
        compliance_rate = f"{rate:.1f}%"

    dates = [row["date"] for row in chart_rows]
    mission_counts = [row["count"] for row in chart_rows]

    return jsonify({
        "kpi": {
            "total_missions": total_missions,
            "compliant_missions": compliant_missions,
            "compliance_rate": compliance_rate,
        },
        "charts": {"labels": dates, "values": mission_counts},
    })


@app.route("/trauma", methods=["GET"])
@login_required
def trauma():

    user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    users = []
    workplaces = []

    if is_admin:
        users = db.execute(
            "SELECT id, username, work FROM users ORDER BY username"
        )
        workplaces = db.execute(
            "SELECT DISTINCT work FROM users WHERE work IS NOT NULL ORDER BY work"
        )

    return render_template(
        "trauma.html",
        users=users,
        workplaces=workplaces,
        is_admin=is_admin,
    )


@app.route("/api/traumadashboard-data", methods=["GET"])
@login_required
def get_traumadashboard_data():

    current_user_id = session["user_id"]
    is_admin = session.get("is_admin", False)

    # reading filter from JavaScript-Fetch
    filter_user = request.args.get("user_id", "all")
    filter_workplace = request.args.get("workplace", "all")

    # Data protection in backend:
    # If the user is not an admin, override filters with manipulated requests
    # Users sees only it's own data
    if not is_admin:
        filter_user = str(current_user_id)
        filter_workplace = "all"

    # preparing base KPIs
    kpi_base_query = """
        SELECT
            COUNT(*) as gesamt,
            SUM(CASE WHEN m.compliance = 1 THEN 1 ELSE 0 END) as konform
        FROM missions_trauma m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    chart_base_query = """
        SELECT m.date, COUNT(*) as count
        FROM missions_trauma m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """

    sql_params = []

    # Ddynamic SQL-generation based on the filters
    if filter_user != "all":
        kpi_base_query += " AND m.user_id = ?"
        chart_base_query += " AND m.user_id = ?"
        sql_params.append(filter_user)

    if filter_workplace != "all":
        kpi_base_query += " AND u.work = ?"
        chart_base_query += " AND u.work = ?"
        sql_params.append(filter_workplace)

    chart_base_query += " GROUP BY m.date ORDER BY m.date ASC LIMIT 7"

    # crash protection
    if sql_params:
        kpi_result = db.execute(kpi_base_query, *sql_params)
        chart_rows = db.execute(chart_base_query, *sql_params)
    else:
        # CS50 Queries
        kpi_result = db.execute(kpi_base_query)
        chart_rows = db.execute(chart_base_query)

    # Data-parsing
    if kpi_result and len(kpi_result) > 0:
        total_missions = kpi_result[0]["gesamt"] if kpi_result[0]["gesamt"] is not None else 0
        compliant_missions = kpi_result[0]["konform"] if kpi_result[0]["konform"] is not None else 0
    else:
        total_missions = 0
        compliant_missions = 0

    compliance_rate = "0%"
    if total_missions > 0:
        rate = (compliant_missions / total_missions) * 100
        compliance_rate = f"{rate:.1f}%"

    dates = [row["date"] for row in chart_rows]
    mission_counts = [row["count"] for row in chart_rows]

    return jsonify({
        "kpi": {
            "total_missions": total_missions,
            "compliant_missions": compliant_missions,
            "compliance_rate": compliance_rate,
        },
        "charts": {"labels": dates, "values": mission_counts},
    })


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return error("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return error("must provide password", 403)

        # Query database for username
        rows = db.execute(
            "SELECT * FROM users WHERE username = ?", request.form.get("username")
        )

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(
            rows[0]["hash"], request.form.get("password")
        ):
            return error("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # admin
        if rows[0]["is_admin"] == 1:
            session["is_admin"] = True
        else:
            session["is_admin"] = False

        # Redirect user to home page
        return redirect("/")

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")
        work = request.form.get("work")

        if not username:
            return error("must provide username", 400)
        if not password:
            return error("must provide password", 400)
        if not confirmation:
            return error("must confirm password", 400)
        if not work:
            return error("must provide work", 400)

        if password != confirmation:
            return error("passwords do not match", 400)

        hash_password = generate_password_hash(password)

        try:
            db.execute(
                "INSERT INTO users (username, hash, work, is_admin) VALUES (?, ?, ?, 0)",
                username,
                hash_password,
                work
            )
        except ValueError:
            return error("username already exists", 400)

        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/export/<protocol>")
@login_required
def export_csv(protocol):
    # Saftey-Check: Only Admins are allowed to export
    if not session.get("is_admin"):
        return error("Unauthorized access", 403)

    # Whitelist against SQL-Injection
    allowed_protocols = {
        "stemi": ("missions_stemi", "ecg"),
        "stroke": ("missions_stroke", "ct"),
        "trauma": ("missions_trauma", "trauma"),
    }

    if protocol not in allowed_protocols:
        return error("Invalid protocol", 400)

    table_name, time_col = allowed_protocols[protocol]

    # filters from URL (user, workplace)
    filter_user = request.args.get("user_id", "all")
    filter_workplace = request.args.get("workplace", "all")

    query = f"""
        SELECT m.id, u.username, u.work, m.date, m.on_scene, m.{time_col}, m.compliance
        FROM {table_name} m
        JOIN users u ON m.user_id = u.id
        WHERE 1=1
    """
    params = []

    if filter_user != "all":
        query += " AND m.user_id = ?"
        params.append(filter_user)

    if filter_workplace != "all":
        query += " AND u.work = ?"
        params.append(filter_workplace)

    query += " ORDER BY m.date DESC"

    rows = db.execute(query, *params) if params else db.execute(query)

    # generating CSV in RAM
    output = io.StringIO()
    writer = csv.writer(output)

    # writing column headings
    writer.writerow(["Mission ID", "Username", "Workplace", "Date",
                    "On Scene", time_col.upper(), "Compliant"])

    # wrriting rows
    for row in rows:
        writer.writerow([
            row["id"],
            row["username"],
            row["work"],
            row["date"],
            row["on_scene"],
            row[time_col],
            "Yes" if row["compliance"] == 1 else "No"
        ])

    # csv download
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={protocol}_missions.csv"}
    )
