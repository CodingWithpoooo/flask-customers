import os

import mysql.connector
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

@app.route('/')
def home():
    return render_template('index.html')

def is_valid_phone(phone):
    return phone.isdigit() and phone.startswith('09') and len(phone) == 11

def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

def init_db():
    try:
        db_connection = get_db_connection()
        cursor = db_connection.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS customers (name VARCHAR(100), address VARCHAR(255))")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'phone'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE customers ADD COLUMN phone VARCHAR(20)")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'city'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE customers ADD COLUMN city VARCHAR(50)")
        cursor.execute("SHOW COLUMNS FROM customers LIKE 'state'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE customers ADD COLUMN state VARCHAR(50)")
        db_connection.commit()
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

@app.route('/submit', methods=['POST'])
def submit():
    customer_name = (request.form.get('name') or '').strip()
    customer_address = (request.form.get('address') or '').strip()
    customer_phone = (request.form.get('phone') or '').strip()
    customer_state = (request.form.get('state') or '').strip()
    customer_city = (request.form.get('city') or '').strip()
    if customer_phone and not is_valid_phone(customer_phone):
        flash("شماره تلفن معتبر نیست (باید ۱۱ رقم عددی و با پیش‌شماره 09 باشد).")
        return redirect('/')
    if not customer_name or not customer_address:
        flash("نام و آدرس باید وارد شوند.")
        return redirect('/')
    if customer_state and len(customer_state) > 2:
        flash("نام استان باید حداکثر ۲ حرف باشد.")
        return redirect('/')
    try:
        db_connection = get_db_connection()
        cursor = db_connection.cursor()

        cursor.execute("SELECT name FROM customers WHERE name = %s", (customer_name,))
        if cursor.fetchone() is not None:
            flash("این نام قبلاً ثبت شده است.")
            return redirect('/')
        if customer_phone:
            cursor.execute("SELECT phone FROM customers WHERE phone = %s", (customer_phone,))
            if cursor.fetchone() is not None:
                flash("این شماره تلفن قبلاً ثبت شده است.")
                return redirect('/')
        sql = "INSERT INTO customers(name, address, phone, city, state) VALUES (%s, %s, %s, %s, %s)"
        val = (customer_name, customer_address, customer_phone, customer_city, customer_state)
        cursor.execute(sql, val)
        db_connection.commit()
    except mysql.connector.Error as err:
        flash(f"خطا در اتصال به دیتابیس: {err}")
        return redirect('/')
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

    flash("مشتری با موفقیت ثبت شد.")
    return redirect('/customers')

@app.route('/customers')
def show_customers():
    try:
        db_connection = get_db_connection()
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute("SELECT name, address, city, state, phone FROM customers ORDER BY name")
        all_customers = cursor.fetchall()
        total_customers = len(all_customers)
    except mysql.connector.Error as err:
        return f"خطا در بارگذاری اطلاعات: {err}", 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

    return render_template('customers.html', names_list=all_customers, total_customers=total_customers)

@app.route('/search', methods=['POST'])
def search_customers():
    search_name = (request.form.get('search_name') or '').strip()
    try:
        db_connection = get_db_connection()
        cursor = db_connection.cursor(dictionary=True)

        sql = "SELECT name, address, city, state, phone FROM customers WHERE name LIKE %s OR city LIKE %s OR state LIKE %s OR phone LIKE %s ORDER BY name"
        search_text = f"%{search_name}%"
        val = (search_text, search_text, search_text, search_text)
        cursor.execute(sql, val)
        all_customers = cursor.fetchall()
        total_customers = len(all_customers)
    except mysql.connector.Error as err:
        return f"خطا در جستجو: {err}", 500
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

    return render_template('customers.html', names_list=all_customers, total_customers=total_customers)

@app.route('/delete', methods=['POST'])
def delete_customer():
    remove_name = (request.form.get('removed_name') or '').strip()
    if not remove_name:
        flash("نام مشتری باید وارد شود.")
        return redirect('/customers')

    try:
        db_connection = get_db_connection()
        cursor = db_connection.cursor()
        cursor.execute("SELECT name FROM customers WHERE name = %s", (remove_name,))
        if cursor.fetchone() is None:
            flash("مشتری با این نام پیدا نشد.")
            return redirect('/customers')
        cursor.execute("DELETE FROM customers WHERE name = %s", (remove_name,))
        db_connection.commit()
    except mysql.connector.Error as err:
        flash(f"خطا در حذف اطلاعات: {err}")
        return redirect('/customers')
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

    flash("مشتری با موفقیت حذف شد.")
    return redirect('/customers')

@app.route('/update', methods=['POST'])
def update_customer():
    customer_name = (request.form.get('customer_name') or '').strip()
    new_phone = (request.form.get('new_phone') or '').strip()
    new_city = (request.form.get('new_city') or '').strip()
    new_address = (request.form.get('new_address') or '').strip()
    new_state = (request.form.get('new_state') or '').strip()
    if not customer_name:
        flash("نام مشتری باید وارد شود.")
        return redirect('/customers')
    if new_phone and not is_valid_phone(new_phone):
        flash("شماره تلفن معتبر نیست (باید ۱۱ رقم عددی و با پیش‌شماره 09 باشد).")
        return redirect('/customers')
    if new_state and len(new_state) > 2:
        flash("نام استان باید حداکثر ۲ حرف باشد.")
        return redirect('/customers')

    try:
        db_connection = get_db_connection()

        cursor = db_connection.cursor()
        cursor.execute("SELECT phone, city, address, state FROM customers WHERE name = %s", (customer_name,))
        current_data = cursor.fetchone()
        if current_data is None:
            flash("مشتری با این نام پیدا نشد.")
            return redirect('/customers')

        current_phone, current_city, current_address, current_state = current_data

        if not new_phone:
            new_phone = current_phone
        if not new_city:
            new_city = current_city
        if not new_address:
            new_address = current_address
        if not new_state:
            new_state = current_state

        if new_phone:
            cursor.execute("SELECT phone FROM customers WHERE phone = %s AND name != %s", (new_phone, customer_name))
            if cursor.fetchone() is not None:
                flash("این شماره تلفن متعلق به مشتری دیگری است.")
                return redirect('/customers')
        sql = "UPDATE customers SET phone = %s, city = %s, address = %s, state = %s WHERE name = %s"
        val = (new_phone, new_city, new_address, new_state, customer_name)
        cursor.execute(sql, val)
        db_connection.commit()
    except mysql.connector.Error as err:
        flash(f"خطا در به‌روزرسانی: {err}")
        return redirect('/customers')
    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'db_connection' in locals() and db_connection.is_connected():
            db_connection.close()

    flash("اطلاعات مشتری با موفقیت به‌روزرسانی شد.")
    return redirect('/customers')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)