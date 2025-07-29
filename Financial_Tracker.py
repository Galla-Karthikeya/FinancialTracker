import os
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import logging
import uuid
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
import traceback
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json
import gspread
import logging
import traceback
import os
import requests

from google.oauth2 import service_account

# Configure logging for models (optional, but good for debugging)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- In-memory Data Stores (Simulating a Database) ---
# In a real application, these would be replaced by database models and ORM operations.
# Data is keyed by user_id for multi-user support.
users_db = {}  # Stores UserProfile objects, keyed by user_id
expenses_db = {} # Stores lists of expense dictionaries, keyed by user_id
investments_db = {} # Stores lists of investment dictionaries, keyed by user_id

# Load environment variables from .env file
load_dotenv()

# --- Configuration from .env ---
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")

# Debugging: Print loaded environment variables (remove in production)
print(f"DEBUG: SERVICE_ACCOUNT_FILE loaded as: {SERVICE_ACCOUNT_FILE}")
print(f"DEBUG: GOOGLE_SHEET_ID loaded as: {GOOGLE_SHEET_ID}")

# Define Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

import gspread
from oauth2client.service_account import ServiceAccountCredentials

def initialize_sheet(sheet_id, SERVICE_ACCOUNT_FILE):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    response = requests.get(SERVICE_ACCOUNT_FILE)
    response.raise_for_status()
    creds_dict = json.loads(response.content)
    creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(sheet_id)
    return client, spreadsheet


def get_user_data(username):
    sheet, sheet_id = initialize_sheet()
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range="Financial Tracker!A2:E"
    ).execute()
    rows = result.get('values', [])
    for row in rows:
        if row[1] == username:  # Assuming name is in column B
            return {
                "user_id": row[0],
                "name": row[1],
                "email": row[2],
                "salary": row[3],
                "bank_balance": row[4]
            }
    return None

def get_expenses(user_id):
    sheet, sheet_id = initialize_sheet()
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range="Daily Expense Tracker!A2:H"
    ).execute()
    rows = result.get('values', [])
    user_expenses = [row for row in rows if row[2] == user_id]
    return user_expenses


def get_investments(user_id):
    sheet, sheet_id = initialize_sheet()
    result = sheet.values().get(
        spreadsheetId=sheet_id,
        range="Investment Details!A2:K"
    ).execute()
    rows = result.get('values', [])
    user_investments = [row for row in rows if row[1] == user_id]
    return user_investments

def add_user(sheet, username, password):
    try:
        existing_users = sheet.get_all_records()
        print("Existing users:", existing_users)

        for user in existing_users:
            print("Checking user:", user)
            if user['name'] == username:
                print("User already exists.")
                return False  # User already exists

        next_id = 1
        if existing_users:
            last_user = existing_users[-1]
            try:
                next_id = int(last_user['user_id']) + 1
            except Exception as e:
                print("Error parsing user_id:", e)

        new_row = [str(next_id), username, password, '', '']
        print("Appending row:", new_row)
        sheet.append_row(new_row)
        print("User added successfully.")
        return True
    except Exception as e:
        print("Unexpected error in add_user:", e)
        return False





def update_password(sheet, username, old_password, new_password):
    records = sheet.get_all_records()
    for idx, row in enumerate(records):
        if row.get('name') == username and row.get('password') == old_password:
            sheet.update_cell(idx + 2, 6, new_password)  # Assuming 'password' is in column 6
            return True
    return False

from datetime import datetime
import uuid

def record_expense(sheet, username, amount, category, date):
    expense_id = str(uuid.uuid4())[:8]
    now = datetime.now()
    sheet.append_row([
        date,
        now.strftime("%H:%M:%S"),
        username,
        amount,
        category,
        "Debit",
        f"Expense on {category}",
        expense_id
    ])
    return True

import uuid

def record_investment(sheet, username, stock_symbol, shares, purchase_price, purchase_date):
    investment_id = str(uuid.uuid4())[:8]
    total_investment = round(float(shares) * float(purchase_price), 2)
    est_profit = round(total_investment * 0.1, 2)  # Assuming 10% estimated profit
    total_value = total_investment + est_profit
    sheet.append_row([
        investment_id,
        username,
        "Stock",
        stock_symbol,
        total_investment,  # as Monthly Investment
        1,  # default 1 year
        10,  # default interest rate 10%
        purchase_date,
        total_investment,
        est_profit,
        total_value
    ])
    return True

def get_financial_summary_by_user(user_profile, expense_tracker, investment_manager):
    class Summary:
        def get_financial_summary(self):
            return {
                "username": user_profile.username,
                "salary": user_profile.salary,
                "bank_balance": user_profile.bank_balance,
                "total_expenses": expense_tracker.total_expenses(),
                "total_invested": investment_manager.total_invested(),
                "estimated_profit": investment_manager.estimated_profit(),
                "net_worth": user_profile.bank_balance + investment_manager.total_value() - expense_tracker.total_expenses()
            }
    return Summary()

def get_expenses_by_user(sheet, username):
    try:
        result = sheet.values().get(
            spreadsheetId=os.getenv("GOOGLE_SHEET_ID"),
            range="Daily Expense Tracker!A2:H"  # assuming headers are in row 1
        ).execute()
        values = result.get('values', [])
        user_expenses = []

        for row in values:
            if len(row) >= 3 and row[2] == username:
                user_expenses.append({
                    "date": row[0],
                    "time": row[1],
                    "user_id": row[2],
                    "amount": float(row[3]),
                    "category": row[4],
                    "type": row[5],
                    "description": row[6],
                    "expense_id": row[7] if len(row) > 7 else ""
                })

        return user_expenses
    except Exception as e:
        print(f"[ERROR] Failed to fetch expenses: {e}")
        return []

def get_investments_by_user(sheet, username):
    try:
        result = sheet.values().get(
            spreadsheetId=os.getenv("GOOGLE_SHEET_ID"),
            range="Investment Details!A2:K"  # adjust to match all columns
        ).execute()
        values = result.get('values', [])
        user_investments = []

        for row in values:
            if len(row) >= 2 and row[1] == username:
                user_investments.append({
                    "Investment_id": row[0],
                    "user_id": row[1],
                    "Investment Plan": row[2],
                    "Plan Name": row[3],
                    "Monthly Investment": float(row[4]) if len(row) > 4 else 0,
                    "Time Period (years)": float(row[5]) if len(row) > 5 else 0,
                    "Interest Rate": float(row[6]) if len(row) > 6 else 0,
                    "Starting Date": row[7] if len(row) > 7 else "",
                    "Invested Amount": float(row[8]) if len(row) > 8 else 0,
                    "Est Profit": float(row[9]) if len(row) > 9 else 0,
                    "Total Amount": float(row[10]) if len(row) > 10 else 0
                })

        return user_investments
    except Exception as e:
        print(f"[ERROR] Failed to fetch investments: {e}")
        return []



# --- Google Sheets Manager (Singleton) ---
class GSheetManager:
    _instance = None # Singleton pattern to ensure only one connection

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GSheetManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        try:
            if not GOOGLE_SHEET_ID or not SERVICE_ACCOUNT_FILE:
                raise ValueError("GOOGLE_SHEET_ID or SERVICE_ACCOUNT_FILE_URL not set in environment")

            response = requests.get(SERVICE_ACCOUNT_FILE)
            response.raise_for_status()
            creds_dict = json.loads(response.content)

            self.credentials = service_account.Credentials.from_service_account_info(creds_dict)
            self.client = gspread.authorize(self.credentials)

            self.financial_tracker_sheet = self.client.open_by_key(GOOGLE_SHEET_ID).worksheet("Financial Tracker")
            self.daily_expense_sheet = self.client.open_by_key(GOOGLE_SHEET_ID).worksheet("Daily Expense Tracker")
            self.investment_details_sheet = self.client.open_by_key(GOOGLE_SHEET_ID).worksheet("Investment Details")

            logging.info("Google Sheets connected successfully.")
            self._initialized = True
        except Exception as e:
            logging.error(f"Error initializing Google Sheets: {e}")
            traceback.print_exc()
            self.financial_tracker_sheet = None
            self.daily_expense_sheet = None
            self.investment_details_sheet = None
            self._initialized = True

# Global instance of GSheetManager
gsheet_manager = GSheetManager()

# --- Classes for Financial Management (Google Sheets Backend) ---

class UserProfile:
    """
    Manages user profile data including personal details, salary, and bank balance
    using Google Sheets as the backend.
    """
    def __init__(self, user_id, name, email, salary=0.0, bank_balance=0.0):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.salary = float(salary)
        self.bank_balance = float(bank_balance)
        self.sheet = gsheet_manager.daily_expense_sheet # Reference to the Google Sheet
        self.sheet1 = gsheet_manager.financial_tracker_sheet # Reference to the Financial Tracker sheet

    def to_dict(self):
        """Converts UserProfile object to a dictionary for JSON serialization."""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "salary(pa)": self.salary,
            "bank_balance": self.bank_balance
        }

    @staticmethod
    def load_profile(user_id):
        """
        Loads a user profile from the Google Sheet.
        Returns a UserProfile object or None if not found.
        """
        sheet1 = gsheet_manager.financial_tracker_sheet
        if not sheet1:
            logging.error("Google Sheet for UserProfile is not initialized.")
            return None
        try:
            records = sheet1.get_all_records()
            for record in records:
                if str(record.get('user_id')) == str(user_id):
                    return UserProfile(
                        user_id=record['user_id'],
                        name=record['name'],
                        email=record['email'],
                        salary=float(record.get('salary(pa)', 0.0)),
                        bank_balance=float(record.get('bank_balance', 0.0))
                    )
            logging.warning(f"Profile not found for user: {user_id}")
            return None
        except Exception as e:
            logging.error(f"Error loading user profile from Google Sheet: {e}")
            traceback.print_exc()
            return None

    def save_profile(self):
        """
        Saves the current user profile to the Google Sheet.
        Updates an existing row or appends a new one.
        """
        if not self.sheet1:
            logging.error("Google Sheet for UserProfile is not initialized.")
            return False
        try:
            # Get all records to find the row index
            records = self.sheet1.get_all_records()
            headers = self.sheet1.row_values(1) # Get headers from the first row

            profile_data = [
                self.user_id,
                self.name,
                self.email,
                self.salary,
                self.bank_balance
            ]

            # Find if user exists by user_id
            user_found = False
            for i, record in enumerate(records):
                # Ensure comparison is robust (e.g., convert to string)
                if str(record.get('user_id')) == str(self.user_id):
                    # Update existing row (row_index is 1-based, plus 1 for header)
                    self.sheet1.update(f'A{i+2}', [profile_data]) # Update the entire row
                    user_found = True
                    logging.info(f"Profile updated for user: {self.user_id}")
                    break

            if not user_found:
                # Append new row if user_id not found
                self.sheet1.append_row(profile_data)
                logging.info(f"New profile added for user: {self.user_id}")
            return True
        except Exception as e:
            logging.error(f"Error saving user profile to Google Sheet: {e}")
            traceback.print_exc()
            return False

    def update_profile(self, **kwargs):
        """
        Updates specific fields of the user profile and saves to Google Sheet.
        """
        updated = False
        if 'name' in kwargs:
            self.name = kwargs['name']
            updated = True
        if 'email' in kwargs:
            self.email = kwargs['email']
            updated = True
        # Changed 'salary(pa)' to 'salary' for consistency with OpenAPI spec
        if 'salary' in kwargs:
            try:
                self.salary = float(kwargs['salary'])
                updated = True
            except ValueError:
                logging.error("Invalid salary value provided.")
        if 'bank_balance' in kwargs:
            try:
                self.bank_balance = float(kwargs['bank_balance'])
                updated = True
            except ValueError:
                logging.error("Invalid bank_balance value provided.")
        if updated:
            self.save_profile() # Persist changes to Google Sheet
            logging.info(f"Profile updated for user: {self.user_id}")
        return updated

class DailyExpenseTracker:
    """
    Manages daily expenses (debits and credits) for a user using Google Sheets.
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.sheet = gsheet_manager.daily_expense_sheet # Reference to the Google Sheet

    def add_expense(self, amount, category, Debit_Credit, description=""):
        """
        Adds a new expense (debit or credit) for the user to Google Sheet.
        Generates a unique ID for each expense.
        Includes a constraint: debits are not allowed if they make the balance negative.
        """
        if not self.sheet:
            logging.error("Google Sheet for DailyExpenseTracker is not initialized.")
            return None
        if Debit_Credit not in ['Debit', 'Credit']:
            logging.error("Invalid Debit/Credit type. Must be 'Debit' or 'Credit'.")
            return None

        user = UserProfile.load_profile(self.user_id)
        if not user:
            logging.error(f"User {self.user_id} not found for expense tracking.")
            return None

        amount_val = float(amount)

        # Constraint 1: Debits should not make the balance negative
        if Debit_Credit == 'Debit':
            if user.bank_balance - amount_val < 0:
                logging.warning(f"Debit of {amount_val} not allowed. Insufficient balance for user {self.user_id}. Current balance: {user.bank_balance}")
                return {"error": "Insufficient balance. Debit not allowed."}

        expense_id = str(uuid.uuid4())
        expense_data = [
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%H:%M:%S'),
            self.user_id,
            amount_val, # Use the float value directly
            category,
            Debit_Credit,
            description,
            expense_id # Store the generated ID in the sheet
        ]
        try:
            self.sheet.append_row(expense_data)
            logging.info(f"Expense added for user {self.user_id}: {expense_data}")

            # Update bank balance immediately when new credit/debit is added
            if Debit_Credit == 'Debit':
                user.update_profile(bank_balance=user.bank_balance - amount_val)
            elif Debit_Credit == 'Credit':
                user.update_profile(bank_balance=user.bank_balance + amount_val)

            # Return the full expense dictionary including the generated ID
            return {
                'id': expense_id,
                'date': expense_data[0],
                'time': expense_data[1],
                'user_id': expense_data[2],
                'amount': expense_data[3],
                'category': expense_data[4],
                'Debit/Credit': expense_data[5],
                'description': expense_data[6]
            }
        except Exception as e:
            logging.error(f"Error adding expense to Google Sheet: {e}")
            traceback.print_exc()
            return None

    def _get_all_user_expenses(self):
        """Helper to fetch all expenses for the current user from the sheet."""
        if not self.sheet:
            logging.error("Google Sheet for DailyExpenseTracker is not initialized.")
            return []
        try:
            all_records = self.sheet.get_all_records()
            # Assuming 'user_id' is a column in your Daily Expense Tracker sheet
            user_expenses = [r for r in all_records if str(r.get('user_id')) == str(self.user_id)]
            return user_expenses
        except Exception as e:
            logging.error(f"Error fetching expenses from Google Sheet: {e}")
            traceback.print_exc()
            return []



    def get_expenses_by_date(self, target_date_str):
        """
        Retrieves all expenses for a specific date for the user.
        target_date_str format: 'YYYY-MM-DD'
        """
        user_expenses = self._get_all_user_expenses()
        print(user_expenses)
        return [e for e in user_expenses if e.get('date') == target_date_str]

    def get_expense(self, expense_id):
        """
        Retrieves a single expense by its ID for the user.
        """
        user_expenses = self._get_all_user_expenses()
        print(user_expenses)
        for e in user_expenses:
            if str(e.get('expense_id')) == str(expense_id):
                return e
        return None

    def get_expenses_by_type_and_date(self, Debit_Credit_type, target_date_str):
        """
        Retrieves expenses of a specific type ('Debit' or 'Credit') for a given date for the user.
        """
        user_expenses = self._get_all_user_expenses()
        return [e for e in user_expenses if e.get('date') == target_date_str and e.get('Debit/Credit') == Debit_Credit_type]

    def update_expense(self, expense_id, **kwargs):
        """
        Updates an existing expense by its ID in the Google Sheet.
        Includes a constraint: debits are not allowed if they make the balance negative.
        """
        if not self.sheet:
            logging.error("Google Sheet for DailyExpenseTracker is not initialized.")
            return False
        try:
            all_records = self.sheet.get_all_records()
            headers = self.sheet.row_values(1) # Get headers for column mapping

            row_index_to_update = -1
            current_expense_data = None

            for i, record in enumerate(all_records):
                if str(record.get('expense_id')) == str(expense_id) and str(record.get('user_id')) == str(self.user_id):
                    row_index_to_update = i + 2 # +2 for 1-based index and header row
                    current_expense_data = record
                    break

            if row_index_to_update == -1:
                logging.warning(f"Expense {expense_id} not found for user {self.user_id}.")
                return False

            user = UserProfile.load_profile(self.user_id)
            if not user:
                logging.error(f"User {self.user_id} not found for expense update.")
                return False

            amount_change = 0
            original_amount = float(current_expense_data.get('amount', 0.0))
            original_debit_credit = current_expense_data.get('Debit/Credit')

            # Pre-check for debit constraint if amount or type is changing
            if 'amount' in kwargs and original_debit_credit == 'Debit':
                try:
                    new_amount = float(kwargs['amount'])
                    # If the updated debit amount would cause negative balance
                    if user.bank_balance + original_amount - new_amount < 0:
                        logging.warning(f"Update of debit {expense_id} not allowed. Insufficient balance for user {self.user_id}.")
                        return {"error": "Insufficient balance. Debit update not allowed."}
                except ValueError:
                    logging.error(f"Invalid amount value for expense {expense_id}.")
                    return False
            
            # Update the current_expense_data with new kwargs
            updated = False
            for key, value in kwargs.items():
                if key in current_expense_data:
                    if key == 'amount':
                        try:
                            current_expense_data[key] = float(value)
                            updated = True
                        except ValueError:
                            logging.error(f"Invalid amount value for expense {expense_id}.")
                            return False
                    else:
                        current_expense_data[key] = value
                        updated = True

            # Calculate amount change for balance update after all potential changes are applied to current_expense_data
            if updated:
                new_amount = float(current_expense_data.get('amount', 0.0))
                new_debit_credit = current_expense_data.get('Debit/Credit')

                if original_debit_credit == 'Debit' and new_debit_credit == 'Debit':
                    amount_change = original_amount - new_amount # If debit decreases, balance increases
                elif original_debit_credit == 'Credit' and new_debit_credit == 'Credit':
                    amount_change = new_amount - original_amount # If credit increases, balance increases
                elif original_debit_credit == 'Debit' and new_debit_credit == 'Credit':
                    amount_change = original_amount + new_amount # Debit becomes credit, both add to balance
                elif original_debit_credit == 'Credit' and new_debit_credit == 'Debit':
                    amount_change = -(original_amount + new_amount) # Credit becomes debit, both subtract from balance

            # Prepare data for update based on column order
            updated_values = [current_expense_data.get(header, '') for header in headers]
            self.sheet.update(f'A{row_index_to_update}', [updated_values])
            logging.info(f"Expense {expense_id} updated for user {self.user_id}.")

            if updated and amount_change != 0:
                user.update_profile(bank_balance=user.bank_balance + amount_change)
            return True
        except Exception as e:
            logging.error(f"Error updating expense in Google Sheet: {e}")
            traceback.print_exc()
            return False

    def delete_expense(self, expense_id):
        """
        Deletes an expense by its ID from the Google Sheet.
        Adjusts the user's bank balance accordingly.
        """
        if not self.sheet:
            logging.error("Google Sheet for DailyExpenseTracker is not initialized.")
            return False
        try:
            all_records = self.sheet.get_all_records()
            row_index_to_delete = -1
            deleted_expense = None
            for i, record in enumerate(all_records):
                if str(record.get('expense_id')) == str(expense_id) and str(record.get('user_id')) == str(self.user_id):
                    row_index_to_delete = i + 2 # +2 for 1-based index and header row
                    deleted_expense = record
                    break

            if row_index_to_delete == -1:
                logging.warning(f"Expense {expense_id} not found for user {self.user_id}.")
                return False

            self.sheet.delete_rows(row_index_to_delete)
            logging.info(f"Expense {expense_id} deleted for user {self.user_id}.")

            # Adjust bank balance after deletion
            if deleted_expense:
                user = UserProfile.load_profile(self.user_id)
                if user:
                    deleted_amount = float(deleted_expense.get('amount', 0.0))
                    if deleted_expense.get('Debit/Credit') == 'Debit':
                        user.update_profile(bank_balance=user.bank_balance + deleted_amount) # Add back debit amount
                    else: # Credit
                        user.update_profile(bank_balance=user.bank_balance - deleted_amount) # Subtract credit amount
            return True
        except Exception as e:
            logging.error(f"Error deleting expense from Google Sheet: {e}")
            traceback.print_exc()
            return False

    def get_debts_credits_total(self, target_date_str=None):
        """
        Calculates total debits and credits for the user from Google Sheet.
        If target_date_str is provided, calculates for that specific date.
        Otherwise, calculates for all recorded expenses.
        """
        user_expenses = self._get_all_user_expenses()
        filtered_expenses = user_expenses
        if target_date_str:
            filtered_expenses = [e for e in user_expenses if e.get('date') == target_date_str]

        total_debits = sum(abs(float(e['amount'])) for e in filtered_expenses if e.get('Debit/Credit') == 'Debit')
        total_credits = sum(float(e['amount']) for e in filtered_expenses if e.get('Debit/Credit') == 'Credit')
        overall_total = total_credits - total_debits
        return {
            'total_debits': total_debits,
            'total_credits': total_credits,
            'overall_net': overall_total
        }

class InvestmentManager:
    """
    Manages user investments, including adding, updating, deleting, and calculating returns
    using Google Sheets as the backend.
    """
    def __init__(self, user_id):
        self.user_id = user_id
        self.sheet = gsheet_manager.investment_details_sheet # Reference to the Google Sheet

        # Default interest rates for each plan type (can be customized)
        self.plan_interest_rates = {
            "SIP": 12.0, "RD": 6.5, "FD": 7.0, "PPF": 7.1,
            "Lumpsum": 10.0, "NPS": 8.0, "EPF": 8.1, "MF": 12.0, "SI": 6.0
        }

    def calculate_estimated_amount(self, plan, monthly_investment, time_period_years, interest_rate=None):
        """
        Calculates estimated future value and invested amount for an investment.
        """
        if interest_rate is None:
            interest_rate = self.plan_interest_rates.get(plan, 7.0)
        n = 12  # compounding monthly
        r = interest_rate / 100 / n
        t = time_period_years
        invested_amount = monthly_investment * 12 * t # Total invested over the period

        if plan.upper() in ["SIP", "MF", "NPS"]:
            # SIP formula: FV = P * [((1+r)^nt - 1)/r] * (1+r)
            if r == 0: # Handle zero interest rate case
                fv = monthly_investment * n * t
            else:
                fv = monthly_investment * (((1 + r) ** (n * t) - 1) / r) * (1 + r)
        else:
            # Simple interest for others (or lump sum with simple interest)
            fv = invested_amount * (1 + (interest_rate / 100 * t))

        return round(invested_amount, 2), round(fv, 2)

    def add_investment(self, plan, plan_name, monthly_investment, time_period_years, interest_rate=None):
        """
        Adds a new investment for the user to Google Sheet.
        Generates a unique ID for each investment.
        Includes a constraint: total monthly investments should not exceed 60% of monthly income.
        """
        if not self.sheet:
            logging.error("Google Sheet for InvestmentManager is not initialized.")
            return None
        try:
            user = UserProfile.load_profile(self.user_id)
            if not user:
                logging.error(f"User {self.user_id} not found for investment.")
                return None

            monthly_salary = user.salary / 12
            if monthly_salary <= 0:
                logging.warning(f"User {self.user_id} has no monthly salary set. Cannot add investment with percentage constraint.")
                return {"error": "Monthly salary not set. Cannot add investment with percentage constraint."}

            current_total_monthly_investments = self.sum_investments_per_month()
            new_monthly_investment_amount = float(monthly_investment)
            
            # Constraint 2: Investments should not exceed 60% of monthly income
            if (current_total_monthly_investments + new_monthly_investment_amount) > (0.60 * monthly_salary):
                logging.warning(f"Investment not allowed. Total monthly investments would exceed 60% of monthly income for user {self.user_id}.")
                return {"error": "Adding this investment would cause total monthly investments to exceed 60% of your monthly income."}

            investment_id = str(uuid.uuid4())
            if interest_rate is None:
                interest_rate = self.plan_interest_rates.get(plan.upper(), 7.0)

            invested_amount, est_amount = self.calculate_estimated_amount(
                plan, new_monthly_investment_amount, time_period_years, interest_rate
            )

            investment_data = [
                investment_id,
                self.user_id, # Add user_id to investment records
                plan,
                plan_name,
                new_monthly_investment_amount,
                float(time_period_years),
                float(interest_rate),
                datetime.now().strftime("%Y-%m-%d"),
                invested_amount,
                est_amount - invested_amount, # Est Profit
                est_amount # Total Amount
            ]
            self.sheet.append_row(investment_data)
            logging.info(f"Investment added for user {self.user_id}: {investment_data}")
            # Return the full investment dictionary
            return {
                "id": investment_id,
                "Investment Plan": plan,
                "Plan Name": plan_name,
                "Monthly Investment": new_monthly_investment_amount,
                "Time Period (years)": float(time_period_years),
                "Interest Rate": float(interest_rate),
                "Starting Date": datetime.now().strftime("%Y-%m-%d"),
                "Invested Amount": invested_amount,
                "Est Profit": est_amount - invested_amount,
                "Total Amount": est_amount
            }
        except Exception as e:
            logging.error(f"Error adding investment to Google Sheet: {e}")
            traceback.print_exc()
            return None

    def _get_all_user_investments(self):
        """Helper to fetch all investments for the current user from the sheet."""
        if not self.sheet:
            logging.error("Google Sheet for InvestmentManager is not initialized.")
            return []
        try:
            all_records = self.sheet.get_all_records()
            print(all_records)
            # Assuming 'user_id' is a column in your Investment Details sheet
            user_investments = [r for r in all_records if str(r.get('user_id')) == str(self.user_id)]
            print(user_investments)
            return user_investments
        except Exception as e:
            logging.error(f"Error fetching investments from Google Sheet: {e}")
            traceback.print_exc()
            return []

    def get_investment(self, investment_id):
        """Retrieves a single investment by its ID for the user from Google Sheet."""
        user_investments = self._get_all_user_investments()
        for inv in user_investments:
            if str(inv.get('Investment_id')) == str(investment_id):
                return inv
        return None

    def update_investment(self, investment_id, **kwargs):
        """
        Updates an existing investment by its ID in the Google Sheet.
        Recalculates estimated amounts if relevant fields change.
        Includes a constraint: total monthly investments should not exceed 60% of monthly income.
        """
        if not self.sheet:
            logging.error("Google Sheet for InvestmentManager is not initialized.")
            return False
        try:
            all_records = self.sheet.get_all_records()
            headers = self.sheet.row_values(1) # Get headers for column mapping

            row_index_to_update = -1
            current_investment_data = None

            for i, record in enumerate(all_records):
                if str(record.get('Investment_id')) == str(investment_id) and str(record.get('user_id')) == str(self.user_id):
                    row_index_to_update = i + 2 # +2 for 1-based index and header row
                    current_investment_data = record
                    break

            if row_index_to_update == -1:
                logging.warning(f"Investment {investment_id} not found for user {self.user_id}.")
                return False

            user = UserProfile.load_profile(self.user_id)
            if not user:
                logging.error(f"User {self.user_id} not found for investment update.")
                return False

            monthly_salary = user.salary / 12
            if monthly_salary <= 0:
                logging.warning(f"User {self.user_id} has no monthly salary set. Cannot update investment with percentage constraint.")
                return {"error": "Monthly salary not set. Cannot update investment with percentage constraint."}

            original_monthly_investment = float(current_investment_data.get("Monthly Investment", 0.0))
            
            # Update the current_investment_data with new kwargs
            updated = False
            for key, value in kwargs.items():
                if key in current_investment_data:
                    if key in ["Monthly Investment", "Time Period (years)", "Interest Rate"]:
                        try:
                            current_investment_data[key] = float(value)
                            updated = True
                        except ValueError:
                            logging.error(f"Invalid numeric value for {key} in investment {investment_id}.")
                            return False
                    else:
                        current_investment_data[key] = value
                        updated = True

            # Recalculate amounts if relevant fields changed
            if updated and any(k in kwargs for k in ["Monthly Investment", "Time Period (years)", "Interest Rate", "Investment Plan"]):
                new_monthly_investment_amount = float(current_investment_data.get("Monthly Investment", 0.0))
                
                # Re-check the 60% constraint with the new monthly investment amount
                current_total_monthly_investments = self.sum_investments_per_month() - original_monthly_investment # Subtract old investment
                
                if (current_total_monthly_investments + new_monthly_investment_amount) > (0.60 * monthly_salary):
                    logging.warning(f"Update not allowed. Total monthly investments would exceed 60% of monthly income for user {self.user_id}.")
                    return {"error": "Updating this investment would cause total monthly investments to exceed 60% of your monthly income."}

                invested_amount, est_amount = self.calculate_estimated_amount(
                    current_investment_data.get("Investment Plan", ""),
                    new_monthly_investment_amount,
                    current_investment_data.get("Time Period (years)", 0.0),
                    current_investment_data.get("Interest Rate")
                )
                current_investment_data["Invested Amount"] = invested_amount
                current_investment_data["Est Profit"] = est_amount - invested_amount
                current_investment_data["Total Amount"] = est_amount

            # Prepare data for update based on column order
            updated_values = [current_investment_data.get(header, '') for header in headers]
            self.sheet.update(f'A{row_index_to_update}', [updated_values])
            logging.info(f"Investment {investment_id} updated for user {self.user_id}.")
            return True
        except Exception as e:
            logging.error(f"Error updating investment in Google Sheet: {e}")
            traceback.print_exc()
            return False

    def delete_investment(self, investment_id):
        """
        Deletes an investment by its ID from the Google Sheet.
        """
        if not self.sheet:
            logging.error("Google Sheet for InvestmentManager is not initialized.")
            return False
        try:
            all_records = self.sheet.get_all_records()
            row_index_to_delete = -1
            for i, record in enumerate(all_records):
                if str(record.get('Investment_id')) == str(investment_id) and str(record.get('user_id')) == str(self.user_id):
                    row_index_to_delete = i + 2 # +2 for 1-based index and header row
                    break

            if row_index_to_delete == -1:
                logging.warning(f"Investment {investment_id} not found for user {self.user_id}.")
                return False

            self.sheet.delete_rows(row_index_to_delete)
            logging.info(f"Investment {investment_id} deleted for user {self.user_id}.")
            return True
        except Exception as e:
            logging.error(f"Error deleting investment from Google Sheet: {e}")
            traceback.print_exc()
            return False

    def sum_investments_per_month(self):
        """
        Calculates the total monthly investment across all plans for the user from Google Sheet.
        """
        user_investments = self._get_all_user_investments()
        return sum(float(inv.get("Monthly Investment", 0.0)) for inv in user_investments)

    def monthly_investment_breakdown(self, salary):
        """
        Provides a detailed breakdown of monthly investments for the user from Google Sheet.
        """
        breakdown = []
        user_investments = self._get_all_user_investments()
        for inv in user_investments:
            try:
                start_date = datetime.strptime(inv.get("Starting Date"), "%Y-%m-%d")
                today = datetime.now()
                months_completed = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                total_months = int(float(inv.get("Time Period (years)", 0.0)) * 12)

                duration = "Ongoing"
                if total_months > 0:
                    remaining_months = total_months - months_completed
                    if remaining_months <= 0:
                        duration = "Completed"
                    else:
                        years = remaining_months // 12
                        months = remaining_months % 12
                        duration = f"{years}y {months}m remaining"

                monthly_investment_amount = float(inv.get("Monthly Investment", 0.0))
                percent_salary = (monthly_investment_amount / (salary / 12)) * 100 if salary else 0 # Calculate percentage of monthly salary

                breakdown.append({
                    "Investment_id": inv.get("Investment_id"),
                    "Plan Name": inv.get("Plan Name"),
                    "Investment Plan": inv.get("Investment Plan"),
                    "Duration": duration,
                    "Months Completed": months_completed,
                    "Total Months": total_months,
                    "Monthly Investment": monthly_investment_amount,
                    "Percent of Salary": round(percent_salary, 2)
                })
            except Exception as e:
                logging.error(f"Error processing investment record {inv.get('Investment_id')}: {e}")
                traceback.print_exc()
                continue
        return breakdown

class FinancialTracker:
    """
    Provides overall financial summaries and EOD balance calculations.
    """
    def __init__(self, user_id):
        self.user_id = user_id
        # UserProfile needs to be loaded first to get current balance and salary
        self.user_profile = UserProfile.load_profile(user_id)
        self.expense_tracker = DailyExpenseTracker(user_id)
        self.investment_manager = InvestmentManager(user_id)

    def EOD_balance(self):
        """
        Calculate the end-of-day balance for the user based on initial bank balance
        and today's expenses.
        """
        if not self.user_profile:
            logging.error(f"User profile not found for EOD balance calculation: {self.user_id}")
            return None

        # The bank balance is now updated in real-time by add_expense, update_expense, delete_expense
        # So, EOD_balance simply returns the current bank balance from the user profile.
        # It's still good to have this method if you want to explicitly "finalize" the day's balance
        # or perform other EOD summaries.
        
        # Re-load profile to ensure we have the absolute latest balance from the sheet
        self.user_profile = UserProfile.load_profile(self.user_id) 
        if self.user_profile:
            logging.info(f"End of Day Balance for user {self.user_id}: {self.user_profile.bank_balance}")
            return self.user_profile.bank_balance
        return None

    def get_monthly_financials(self):
        """
        Calculates and returns monthly financial summary.
        Includes monthly salary, total monthly investments, and remaining monthly balance.
        """
        if not self.user_profile:
            return None

        monthly_salary = self.user_profile.salary / 12 # Assuming salary is annual
        total_monthly_investments = self.investment_manager.sum_investments_per_month()

        # To get remaining monthly balance, we need monthly expenses.
        current_month_start_date = datetime.now().replace(day=1)
        # Fetch all expenses for the user and filter by month/year
        all_user_expenses = self.expense_tracker._get_all_user_expenses()
        current_month_expenses = [
            e for e in all_user_expenses
            if e.get('date') and \
               datetime.strptime(e['date'], '%Y-%m-%d').month == current_month_start_date.month and \
               datetime.strptime(e['date'], '%Y-%m-%d').year == current_month_start_date.year and \
               e.get('Debit/Credit') == 'Debit'
        ]
        total_monthly_expenses = sum(float(e.get('amount', 0.0)) for e in current_month_expenses)

        remaining_monthly_balance = monthly_salary - total_monthly_investments - total_monthly_expenses

        return {
            "monthly_salary": monthly_salary,
            "total_monthly_investments": total_monthly_investments,
            "total_monthly_expenses": total_monthly_expenses,
            "remaining_monthly_balance": remaining_monthly_balance
        }