from flask import Flask, jsonify, request, render_template, redirect, url_for, session
from flasgger import Swagger
import os
from dotenv import load_dotenv
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import uuid

from Financial_Tracker import (
    initialize_sheet, get_user_data, add_user, update_password, record_expense,
    get_expenses_by_user, get_financial_summary_by_user, record_investment,
    get_investments_by_user, UserProfile, DailyExpenseTracker, InvestmentManager
)

from calculators import (
    calculate_sip,
    calculate_fd,
    calculate_rd,
    calculate_mutual_fund_lumpsum,
    calculate_emi,
    calculate_inhand_salary,
    calculate_new_regime_tax
)


from datetime import datetime

# Load environment variables from .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('FLASK_SECRET_KEY')

# Initialize Swagger
swagger = Swagger(app)

# Initialize Google Sheets
try:
    gc, spreadsheet = initialize_sheet(os.getenv("GOOGLE_SHEET_ID"),os.getenv("SERVICE_ACCOUNT_FILE"))

    users_sheet = spreadsheet.worksheet("Users")
    expenses_sheet = spreadsheet.worksheet("Daily Expense Tracker")
    investments_sheet = spreadsheet.worksheet("Investment Details")
except Exception as e:
    print(f"Error initializing Google Sheets: {e}")
    users_sheet, expenses_sheet, investments_sheet = None, None, None

# ------------------ Frontend Routes ------------------

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if users_sheet is None:
        return "Google Sheets not initialized.", 500

    if request.method == 'POST':
        print("DEBUG: POST triggered")
        print("Form data:", request.form)

        email = request.form.get('email')
        password = request.form.get('password')

        users = users_sheet.get_all_records()
        for user in users:
            if user.get('email') == email and user.get('password') == password:
                session['user_id'] = user.get('user_id')
                session['email'] = email
                session['name'] = user.get('name')
                return redirect(url_for('dashboard'))

        return render_template('login.html', error="Invalid credentials", email=email)

    return render_template('login.html')





from datetime import datetime, timedelta


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    name = session.get('name')

    # User info
    users = users_sheet.get_all_records()
    user_data = next((u for u in users if u.get('user_id') == user_id), None)
    if not user_data:
        return "User data not found.", 404

    bank_balance = float(user_data.get('bank_balance') or 0)
    salary = float(user_data.get('salary') or 0)

    # Expenses
    expenses = expenses_sheet.get_all_records()
    user_expenses = [e for e in expenses if e.get('user_id') == user_id]
    last_5_expenses = [
        {
            'date': e.get('date'),
            'category': e.get('category'),
            'amount': e.get('amount'),
            'type': e.get('Debit/Credit'),
            'description': e.get('description')
        }
        for e in user_expenses[-5:]
    ]

    # Investments
    investments = investments_sheet.get_all_records()
    user_investments = [i for i in investments if i.get('user_id') == user_id]

    total_savings = sum(float(i.get('Invested Amount', 0)) for i in user_investments)


    # --- 🔍 Upcoming Deductions Logic ---
    upcoming_deduction = []
    today = datetime.today()
    next_month = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
    
    for inv in user_investments:
        if inv.get('Investment Plan') == 'RD':
            try:
                start_date = datetime.strptime(inv.get('Starting Date'), '%Y-%m-%d')
                deduction_day = start_date.day
                next_deduction_date = next_month.replace(day=deduction_day)

                # Build entry
                upcoming_deduction.append({
                    'date': next_deduction_date.strftime('%d-%m-%Y'),
                    'plan': inv.get('Plan Name'),
                    'amount': f"{float(inv.get('Monthly Investment')):.2f}"
                })
            except Exception as e:
                print("Date parse error:", e)
                continue
    # --------------------------------------

    return render_template(
        'dashboard.html',
        name=name,
        bank_balance=bank_balance,
        total_savings=total_savings,
        upcoming_deduction=upcoming_deduction,
        last_5_expenses=last_5_expenses,
        all_investments=user_investments
    )

@app.route('/add-expense', methods=['GET', 'POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        category = request.form['category']
        amount = request.form['amount']
        date = request.form['date']
        description = request.form['description']
        txn_type = request.form['type']
        user_id = session.get('user_id')

        if not all([category, amount, date, txn_type]):
            return "Missing required fields", 400

        if expenses_sheet is None or users_sheet is None:
            return "Sheets not initialized.", 500

        try:
            amount = float(amount)
        except ValueError:
            return "Invalid amount", 400

        now = datetime.now()
        time = now.strftime('%H:%M:%S')
        expense_id = str(uuid.uuid4())[:8]

        # Append to expense sheet
        expenses_sheet.append_row([
            date, time, user_id, amount, category,
            txn_type, description, expense_id
        ])

        # Get and update user bank balance
        users = users_sheet.get_all_records()
        user_index = None

        for idx, user in enumerate(users):
            if str(user.get('user_id')) == str(user_id):
                user_index = idx
                break

        if user_index is not None:
            try:
                current_balance = float(user.get('bank_balance', 0) or 0.0)
                new_balance = current_balance - amount if txn_type == 'Debit' else current_balance + amount

                # Update cell (column 5 for bank_balance)
                users_sheet.update_cell(user_index + 2, 6, new_balance)

            except Exception as e:
                print(f"[ERROR] Failed to update balance: {e}")

        return redirect(url_for('dashboard'))

    return render_template('add_expense.html')



@app.route('/new-investment', methods=['GET', 'POST'])
def new_investment():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        investment_type = request.form['investment_type']
        plan_name = request.form['plan_name']
        amount = float(request.form['amount'])
        years = float(request.form['years'])
        interest_rate = float(request.form['interest_rate'])
        date = request.form['date']
        user_id = session.get('user_id')

        # Calculation
        if investment_type in ['SIP', 'RD']:
            invested_amount = amount * 12 * years
        else:  # FD or MF: lump sum
            invested_amount = amount

        estimated_profit = (invested_amount * interest_rate * years) / 100
        total_amount = invested_amount + estimated_profit

        # Round values
        invested_amount = round(invested_amount, 2)
        estimated_profit = round(estimated_profit, 2)
        total_amount = round(total_amount, 2)

        investment_id = str(uuid.uuid4())[:8]

        # Append to sheet
        investments_sheet.append_row([
            investment_id, user_id, investment_type, plan_name,
            amount, years, interest_rate, date,
            invested_amount, estimated_profit, total_amount
        ])

        # Return to same page with summary
        return render_template(
            'new_investment.html',
            summary={
                "type": investment_type,
                "plan_name": plan_name,
                "amount": amount,
                "years": years,
                "rate": interest_rate,
                "invested_amount": invested_amount,
                "profit": estimated_profit,
                "total": total_amount
            }
        )

    return render_template('new_investment.html')





@app.route('/transaction_history')
def transaction_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = str(session['user_id'])  # Convert to string to avoid mismatch

    all_txns = expenses_sheet.get_all_records()
    user_txns = [t for t in all_txns if str(t.get('user_id')) == user_id]  # Ensure both are strings

    return render_template('transaction_history.html', transactions=user_txns)



@app.route('/investment-history')
def investment_history():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    investments = investments_sheet.get_all_records()
    user_investments = [i for i in investments if str(i.get('user_id')) == str(user_id)]

    return render_template('investment_history.html', investments=user_investments)

@app.route('/investment_calculator', methods=['GET', 'POST'])
def investment_calculator():
    result = None
    if request.method == 'POST':
        calc_type = request.form.get('calc_type')

        if calc_type == 'sip':
            p = float(request.form['amount'])
            rate = float(request.form['rate'])
            years = float(request.form['years'])
            maturity, profit, invested = calculate_sip(p, rate, years)
            result = {
                'type': 'SIP',
                'invested': invested,
                'profit': profit,
                'maturity': maturity
            }

        elif calc_type == 'lumpsum':
            p = float(request.form['amount'])
            rate = float(request.form['rate'])
            years = float(request.form['years'])
            maturity, profit = calculate_mutual_fund_lumpsum(p, rate, years)
            result = {
                'type': 'Lump Sum',
                'invested': p,
                'profit': profit,
                'maturity': maturity
            }

        elif calc_type == 'fd':
            p = float(request.form['amount'])
            rate = float(request.form['rate'])
            years = float(request.form['years'])
            maturity, profit = calculate_fd(p, rate, years)
            result = {
                'type': 'FD',
                'invested': p,
                'profit': profit,
                'maturity': maturity
            }

        elif calc_type == 'rd':
            p = float(request.form['amount'])
            rate = float(request.form['rate'])
            months = int(request.form['months'])
            maturity, profit = calculate_rd(p, rate, months)
            result = {
                'type': 'RD',
                'invested': p * months,
                'profit': profit,
                'maturity': maturity
            }

        elif calc_type == 'emi':
            p = float(request.form['principal'])
            rate = float(request.form['rate'])
            years = float(request.form['years'])
            emi, total, interest = calculate_emi(p, rate, years)
            result = {
                'type': 'EMI',
                'emi': emi,
                'total': total,
                'interest': interest
            }

        elif calc_type == 'salary':
            basic = float(request.form['basic'])
            hra = float(request.form['hra'])
            others = float(request.form['other_allowances'])
            tax = float(request.form.get('tax', 0))
            net, gross, deductions = calculate_inhand_salary(basic, hra, others, tax)
            result = {
                'type': 'Salary',
                'net': net,
                'gross': gross,
                'deductions': deductions
            }

    return render_template("investment_calculator.html", result=result)



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if users_sheet is None:
        return "Google Sheets not initialized.", 500

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_users = users_sheet.get_all_records()
        for user in existing_users:
            if user.get('email') == email:
                return render_template('register.html', error="Email already exists.", name=name, email=email)

        user_id = len(existing_users) + 1
        session['pending_user'] = {
            'user_id': str(user_id),
            'name': name,
            'email': email,
            'password': password
        }

        return redirect(url_for('register_details'))

    return render_template('register.html')

@app.route('/register/details', methods=['GET', 'POST'])
def register_details():
    if 'pending_user' not in session:
        return redirect(url_for('register'))
    
    user_name = session.get('name')
    if request.method == 'POST':
        salary = request.form.get('salary')
        bank_balance = request.form.get('bank_balance')
        pending_user = session.pop('pending_user')  # remove from session after use

        users_sheet.append_row([
            pending_user['user_id'],
            pending_user['name'],
            pending_user['email'],
            pending_user['password'],
            salary,
            bank_balance
        ])

        return redirect(url_for('login'))

    return render_template('register_details.html', name=user_name)


# ------------------ API Routes ------------------

@app.route('/user/add', methods=['POST'])
def add_user_endpoint():
    data = request.form
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    if users_sheet and add_user(users_sheet, username, password):
        return jsonify({"message": "User added successfully"}), 200
    return jsonify({"error": "Failed to add user or user already exists"}), 400

@app.route('/user/login', methods=['POST'])
def login_user_endpoint():
    data = request.form
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({"error": "Username and password are required"}), 400
    user = get_user_data(users_sheet, username)
    if user and user['password'] == password:
        return jsonify({"message": "Login successful", "username": username}), 200
    return jsonify({"error": "Invalid credentials"}), 401

@app.route('/user/update_password', methods=['PUT'])
def update_password_endpoint():
    data = request.form
    username = data.get('username')
    old_password = data.get('old_password')
    new_password = data.get('new_password')
    if not all([username, old_password, new_password]):
        return jsonify({"error": "All fields are required"}), 400
    if users_sheet and update_password(users_sheet, username, old_password, new_password):
        return jsonify({"message": "Password updated successfully"}), 200
    return jsonify({"error": "Failed to update password"}), 400

@app.route('/expense/record', methods=['POST'])
def record_expense_endpoint():
    data = request.form
    username = data.get('username')
    amount = data.get('amount')
    category = data.get('category')
    date = data.get('date')
    if not all([username, amount, category, date]):
        return jsonify({"error": "All fields are required"}), 400
    try:
        amount = float(amount)
    except ValueError:
        return jsonify({"error": "Amount must be a number"}), 400
    if expenses_sheet and record_expense(expenses_sheet, username, amount, category, date):
        return jsonify({"message": "Expense recorded successfully"}), 200
    return jsonify({"error": "Failed to record expense"}), 400

@app.route('/expense/get/<username>', methods=['GET'])
def get_expenses_endpoint(username):
    if expenses_sheet:
        expenses = get_expenses_by_user(expenses_sheet, username)
        if expenses:
            return jsonify(expenses), 200
        return jsonify({"message": "No expenses found for this user"}), 404
    return jsonify({"error": "Expenses sheet not initialized"}), 500

@app.route('/summary/<username>', methods=['GET'])
def get_summary_endpoint(username):
    user_profile = UserProfile(users_sheet, username)
    user_profile.load_profile_data()
    expense_tracker = DailyExpenseTracker(expenses_sheet, username)
    investment_manager = InvestmentManager(investments_sheet, username)
    summary = get_financial_summary_by_user(
        user_profile=user_profile,
        expense_tracker=expense_tracker,
        investment_manager=investment_manager
    ).get_financial_summary()
    if summary:
        return jsonify(summary), 200
    return jsonify({"message": "No financial data found for this user"}), 404

@app.route('/investment/record', methods=['POST'])
def record_investment_endpoint():
    data = request.form
    username = data.get('username')
    stock_symbol = data.get('stock_symbol')
    shares = data.get('shares')
    purchase_price = data.get('purchase_price')
    purchase_date = data.get('purchase_date')
    if not all([username, stock_symbol, shares, purchase_price, purchase_date]):
        return jsonify({"error": "All fields are required"}), 400
    try:
        shares = float(shares)
        purchase_price = float(purchase_price)
    except ValueError:
        return jsonify({"error": "Shares and purchase price must be numbers"}), 400
    if investments_sheet and record_investment(investments_sheet, username, stock_symbol, shares, purchase_price, purchase_date):
        return jsonify({"message": "Investment recorded successfully"}), 200
    return jsonify({"error": "Failed to record investment"}), 400

@app.route('/investment/get/<username>', methods=['GET'])
def get_investments_endpoint(username):
    if investments_sheet:
        investments = get_investments_by_user(investments_sheet, username)
        if investments:
            return jsonify(investments), 200
        return jsonify({"message": "No investments found for this user"}), 404
    return jsonify({"error": "Investments sheet not initialized"}), 500

@app.route('/investment/breakdown/<string:user_id>', methods=['GET'])
def get_monthly_investment_breakdown(user_id):
    user_data = get_user_data(users_sheet, user_id)
    if not user_data:
        return jsonify({"error": "User not found"}), 404
    try:
        salary = float(user_data.get('salary', 0))
    except ValueError:
        return jsonify({"error": "User salary is invalid or not set."}), 400
    if salary <= 0:
        return jsonify({"error": "User salary must be set to calculate investment breakdown."}), 400
    investment_manager = InvestmentManager(investments_sheet, user_id)
    breakdown = investment_manager.monthly_investment_breakdown(salary)
    return jsonify(breakdown), 200

# ------------------ Run the Application ------------------
import threading
import webbrowser
import time

def open_tabs():
    time.sleep(1)
    webbrowser.open_new_tab("http://127.0.0.1:5000/")
    webbrowser.open_new_tab("http://127.0.0.1:5000/apidocs")

if __name__ == '__main__':
    app.run(debug=True)


