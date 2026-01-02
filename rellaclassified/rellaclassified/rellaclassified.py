from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key"  # change in production

db_config = {
    "host": "localhost",
    "user": "root",
    "password": "Clement-88",
    "database": "classifieds_db"
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

# ---------------- HOME ----------------
@app.route("/")
def index():
    category_id = request.args.get("category_id")
    search = request.args.get("search")

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
    SELECT 
        ads.id,
        ads.title,
        ads.description,
        ads.contact,
        ads.province,
        ads.town,
        users.username,
        categories.name AS category,
        ads.category_id
    FROM ads
    JOIN users ON ads.user_id = users.id
    JOIN categories ON ads.category_id = categories.id
    WHERE 1=1
    """

    params = []

    if category_id:
        query += " AND ads.category_id = %s"
        params.append(category_id)

    if search:
        query += " AND ads.title LIKE %s"
        params.append(f"%{search}%")

    query += " ORDER BY ads.province, ads.town, ads.created_at DESC"

    cursor.execute(query, params)
    ads = cursor.fetchall()

    # Group ads by province → town
    grouped_ads = {}
    for ad in ads:
        province = ad["province"]
        town = ad["town"]

        grouped_ads.setdefault(province, {})
        grouped_ads[province].setdefault(town, [])
        grouped_ads[province][town].append(ad)

    # Load categories for dropdown
    cursor.execute("SELECT id, name FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        "index.html",
        grouped_ads=grouped_ads,
        categories=categories,
        category_id=category_id,
        search=search
    )




# ---------------- REGISTER ----------------
# Example register route
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]  # make sure this field exists in your form
        password = request.form["password"]
        hashed_password = generate_password_hash(password)

        # Set admin by default
        is_admin = 1

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password, is_admin) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_password, is_admin)
        )
        conn.commit()
        cursor.close()
        conn.close()

        flash("User registered successfully!", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["is_admin"] = user["is_admin"]
            flash("Login successful!", "success")
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")

#------------------ EDIT AD --------------
@app.route("/admin/edit_ad/<int:ad_id>", methods=["GET", "POST"])
def edit_ad(ad_id):
    if not session.get("is_admin"):
        flash("Unauthorized access", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Load ad
    cursor.execute("SELECT * FROM ads WHERE id = %s", (ad_id,))
    ad = cursor.fetchone()

    if not ad:
        cursor.close()
        conn.close()
        flash("Ad not found", "danger")
        return redirect(url_for("index"))

    # Update ad
    if request.method == "POST":
        title = request.form["title"]
        category_id = request.form["category_id"]
        description = request.form["description"]
        contact = request.form["contact"]
        province = request.form["province"]
        town = request.form["town"]

        cursor.execute("""
            UPDATE ads
            SET title=%s,
                category_id=%s,
                description=%s,
                contact=%s,
                province=%s,
                town=%s
            WHERE id=%s
        """, (title, category_id, description, contact, province, town, ad_id))

        conn.commit()
        cursor.close()
        conn.close()

        flash("Ad updated successfully", "success")
        return redirect(url_for("index"))

    # Load categories for dropdown
    cursor.execute("SELECT id, name FROM categories")
    categories = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("edit_ad.html", ad=ad, categories=categories)

#------------------ADD PROVINCE----------
@app.route("/admin/add_province", methods=["GET", "POST"])
def add_province():
    if not session.get("is_admin"):
        flash("Admin access only", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form.get("name")
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO provinces (name) VALUES (%s)", (name,))
            conn.commit()
            flash(f"Province '{name}' added.", "success")
        except:
            flash("Province already exists.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("add_province"))

    return render_template("add_province.html")
def get_provinces():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM provinces ORDER BY name")
    provinces = cursor.fetchall()
    cursor.close()
    conn.close()
    return provinces


#-------------------ADD TOWN-------------
@app.route("/admin/add_town", methods=["GET", "POST"])
def add_town():
    if not session.get("is_admin"):
        flash("Admin access only", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM provinces ORDER BY name")
    provinces = cursor.fetchall()

    if request.method == "POST":
        name = request.form.get("name")
        province_id = request.form.get("province_id")
        try:
            cursor.execute(
                "INSERT INTO towns (name, province_id) VALUES (%s, %s)",
                (name, province_id)
            )
            conn.commit()
            flash(f"Town '{name}' added.", "success")
        except:
            flash("Town already exists.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("add_town"))

    cursor.close()
    conn.close()
    return render_template("add_town.html", provinces=provinces)
def get_towns(province_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM towns WHERE province_id=%s ORDER BY name", (province_id,))
    towns = cursor.fetchall()
    cursor.close()
    conn.close()
    return towns



#-------------------DELETE AD -----------
@app.route("/admin/delete_ad/<int:ad_id>")
def delete_ad(ad_id):
    if not session.get("is_admin"):
        flash("Unauthorized access")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM ads WHERE id=%s", (ad_id,))
    conn.commit()
    cursor.close()
    conn.close()

    flash("Ad deleted successfully")
    return redirect(url_for("index"))

#-------------------VIEW & DELETE ADS-----------
@app.route("/admin/ads")
def admin_ads():
    if not session.get("is_admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT ads.id, ads.title, ads.contact,
               categories.name AS category,
               ads.province, ads.town
        FROM ads
        JOIN categories ON ads.category_id = categories.id
        ORDER BY ads.id DESC
    """)
    ads = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("admin_ads.html", ads=ads)

#-------------------EDIT AD-----------------
@app.route("/admin/edit_ad/<int:ad_id>", methods=["GET", "POST"])
def admin_edit_ad(ad_id):
    if not session.get("is_admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch ad
    cursor.execute("SELECT * FROM ads WHERE id = %s", (ad_id,))
    ad = cursor.fetchone()

    if not ad:
        flash("Ad not found.", "danger")
        return redirect(url_for("admin_ads"))

    categories = get_categories()
    provinces = get_provinces()
    towns = get_towns()  # existing function

    if request.method == "POST":
        cursor.execute("""
            UPDATE ads SET
                title=%s,
                category_id=%s,
                description=%s,
                contact=%s,
                province=%s,
                town=%s
            WHERE id=%s
        """, (
            request.form["title"],
            request.form["category_id"],
            request.form["description"],
            request.form["contact"],
            request.form["province"],
            request.form["town"],
            ad_id
        ))

        conn.commit()
        flash("Ad updated successfully.", "success")
        return redirect(url_for("admin_ads"))

    cursor.close()
    conn.close()

    return render_template(
        "admin_edit_ad.html",
        ad=ad,
        categories=categories,
        provinces=provinces,
        towns=towns
    )



#-------------------MANAGE LOCATION-------
@app.route("/admin/manage_locations", methods=["GET", "POST"])
def manage_locations():
    if not session.get("is_admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Determine which form was submitted
    if request.method == "POST":
        if "province_name" in request.form:  # Add Province form
            province_name = request.form["province_name"].strip()
            if province_name:
                try:
                    cursor.execute("INSERT INTO provinces (name) VALUES (%s)", (province_name,))
                    conn.commit()
                    flash(f"Province '{province_name}' added successfully!", "success")
                except mysql.connector.IntegrityError:
                    flash(f"Province '{province_name}' already exists.", "danger")
            else:
                flash("Province name cannot be empty.", "warning")

        elif "town_name" in request.form:  # Add Town form
            town_name = request.form["town_name"].strip()
            province_id = request.form.get("province_id")
            if town_name and province_id:
                try:
                    cursor.execute(
                        "INSERT INTO towns (name, province_id) VALUES (%s, %s)",
                        (town_name, province_id)
                    )
                    conn.commit()
                    flash(f"Town '{town_name}' added successfully!", "success")
                except mysql.connector.IntegrityError:
                    flash(f"Town '{town_name}' already exists for this province.", "danger")
            else:
                flash("Please select a province and enter a town name.", "warning")

        return redirect(url_for("manage_locations"))

    # Load provinces and towns for display
    cursor.execute("SELECT * FROM provinces ORDER BY name")
    provinces = cursor.fetchall()

    cursor.execute("""
        SELECT towns.id, towns.name, provinces.name AS province_name
        FROM towns
        JOIN provinces ON towns.province_id = provinces.id
        ORDER BY provinces.name, towns.name
    """)
    towns = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template("manage_locations.html", provinces=provinces, towns=towns)

#---------------GET TOWN---------
@app.route("/get_towns/<int:province_id>")
def get_towns_for_province(province_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name FROM towns WHERE province_id = %s ORDER BY name", (province_id,))
    towns = cursor.fetchall()
    cursor.close()
    conn.close()
    
    # Return JSON list of towns
    return {"towns": towns}






# ----------------- ADMIN-----------------
@app.route("/admin/categories", methods=["GET", "POST"])
def manage_categories():
    if not session.get("is_admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        name = request.form["name"]

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO categories (name) VALUES (%s)", (name,))
            conn.commit()
            flash("Category added.", "success")
        except:
            flash("Category already exists.", "danger")
        finally:
            cursor.close()
            conn.close()

    return render_template(
        "manage_categories.html",
        categories=get_categories()
    )

#--------------DASH BOARD----------------
@app.route("/admin")
def admin_dashboard():
    if not session.get("is_admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM ads")
    total_ads = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM categories")
    total_categories = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM provinces")
    total_provinces = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM towns")
    total_towns = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        total_ads=total_ads,
        total_users=total_users,
        total_categories=total_categories,
        total_provinces=total_provinces,
        total_towns=total_towns
    )

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# ---------------- POST AD ----------------
@app.route("/post", methods=["GET", "POST"])
def post_ad():
    if "user_id" not in session:
        flash("Login required.", "warning")
        return redirect(url_for("login"))

    categories = get_categories()
    provinces = get_provinces()

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Load ALL towns so the dropdown works
    cursor.execute("SELECT id, name FROM towns ORDER BY name")
    towns = cursor.fetchall()

    if request.method == "POST":
        title = request.form["title"]
        category_id = request.form["category_id"]
        description = request.form["description"]
        contact = request.form["contact"]
        province_id = request.form["province_id"]
        town_id = request.form["town_id"]

        cursor.execute("""
            INSERT INTO ads (title, category_id, description, contact, user_id, province, town)
            VALUES (%s, %s, %s, %s, %s,
                (SELECT name FROM provinces WHERE id = %s),
                (SELECT name FROM towns WHERE id = %s))
        """, (
            title,
            category_id,
            description,
            contact,
            session["user_id"],
            province_id,
            town_id
        ))

        conn.commit()
        flash("Ad posted successfully!", "success")
        return redirect(url_for("index"))

    cursor.close()
    conn.close()

    return render_template(
        "post_ad.html",
        categories=categories,
        provinces=provinces,
        towns=towns
    )



def get_categories():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM categories ORDER BY name")
    categories = cursor.fetchall()
    cursor.close()
    conn.close()
    return categories



if __name__ == "__main__":
    app.run(debug=True)
