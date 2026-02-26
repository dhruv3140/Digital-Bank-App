import streamlit as st
import random
import string
import pandas as pd  
from datetime import datetime, timezone, timedelta 
from supabase import create_client, Client

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase: Client = init_connection()

# --- DATABASE LOGIC (Supabase Version) ---
class BankDB:
    def generate_account_no(self):
        alpha = random.choices(string.ascii_letters, k=3)
        num = random.choices(string.digits, k=3)
        spchar = random.choices("!@#$%^&*", k=1)
        id_list = alpha + num + spchar
        random.shuffle(id_list)
        return "".join(id_list)

    def create_account(self, name, age, dob, email, pin):
        acc_no = self.generate_account_no()
        data = {
            "account_no": acc_no,
            "name": name,
            "age": age,
            "dob": str(dob),
            "email": email,
            "pin": str(pin),
            "balance": 0
        }
        response = supabase.table("accounts").insert(data).execute()
        return acc_no

    def authenticate_user(self, acc_num, pin):
        response = supabase.table("accounts").select("account_no").eq("account_no", acc_num).eq("pin", str(pin)).execute()
        return len(response.data) > 0
    
    def recover_details(self, email, dob):
        response = supabase.table("accounts").select("account_no, pin").eq("email", email.strip()).eq("dob", str(dob).strip()).execute()
        if response.data:
            return response.data[0]['account_no'], response.data[0]['pin']
        return None       

    def get_user(self, acc_num):
        response = supabase.table("accounts").select("*").eq("account_no", acc_num).execute()
        if response.data:
            user_data = response.data[0]
            return {
                "accountNo.": user_data['account_no'],
                "name": user_data['name'],
                "age": user_data['age'],
                "dob": user_data['dob'],
                "email": user_data['email'],
                "pin": user_data['pin'],
                "balance": user_data['balance']
            }
        return None

    def update_balance(self, acc_num, new_balance):
        supabase.table("accounts").update({"balance": new_balance}).eq("account_no", acc_num).execute()

    def log_transaction(self, acc_num, trans_type, amount):
        ist_offset = timedelta(hours=5, minutes=30)
        ist_tz = timezone(ist_offset)
        now = datetime.now(ist_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        data = {
            "account_no": acc_num,
            "type": trans_type,
            "amount": amount,
            "timestamp": now
        }
        supabase.table("transactions").insert(data).execute()

    def get_transaction_history(self, acc_num):
        response = supabase.table("transactions").select("timestamp, type, amount").eq("account_no", acc_num).order("timestamp", desc=True).execute()
        return response.data

    def update_details(self, acc_num, name, email, pin):
        supabase.table("accounts").update({"name": name, "email": email, "pin": str(pin)}).eq("account_no", acc_num).execute()

    def change_pin(self, acc_num, new_pin):
        supabase.table("accounts").update({"pin": str(new_pin)}).eq("account_no", acc_num).execute()

    def delete_account(self, acc_num):
        supabase.table("transactions").delete().eq("account_no", acc_num).execute()
        supabase.table("accounts").delete().eq("account_no", acc_num).execute()
        
    def get_all_accounts(self):
        response = supabase.table("accounts").select("account_no, name, age, dob, email, pin, balance").execute()
        return response.data

    def get_all_transactions(self):
        response = supabase.table("transactions").select("id, account_no, type, amount, timestamp").order("timestamp", desc=True).execute()
        return response.data


# --- STREAMLIT UI ---
st.set_page_config(page_title="Smart AI Bank", layout="centered")
st.title("🏦 Smart AI Bank Management System")

if 'bank' not in st.session_state:
    st.session_state.bank = BankDB()
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user_acc' not in st.session_state:
    st.session_state.current_user_acc = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

bank = st.session_state.bank

if not st.session_state.logged_in:
    menu = ["Login", "Create Account"]
elif st.session_state.is_admin:
    menu = ["👑 Admin Dashboard", "Logout"]
else:
    menu = ["Dashboard (Details)", "🤖 AI Financial Advisor", "Deposit Money", "Withdraw Money", "Update Details", "Change PIN", "Delete Account", "Logout"]

choice = st.sidebar.selectbox("Select Action", menu)
st.write("---")

if choice == "Login":
    st.header("🔐 Login to Your Account")
    
    with st.form("login_form"):
        acc_num = st.text_input("Account Number")
        pin = st.text_input("PIN", type="password")
        submitted = st.form_submit_button("Login")
        
        if submitted:
            if acc_num.strip() == "ADMIN" and pin.strip() == "9999":
                st.session_state.logged_in = True
                st.session_state.is_admin = True
                st.success("Welcome Boss! Admin mode activated.")
                st.rerun()
            elif bank.authenticate_user(acc_num.strip(), pin.strip()):
                st.session_state.logged_in = True
                st.session_state.is_admin = False
                st.session_state.current_user_acc = acc_num.strip()
                st.success("Login successful!")
                st.rerun() 
            else:
                st.error("Invalid Account Number or PIN.")

    st.write("---")
    
    with st.expander("Forgot your Account Number or PIN?"):
        st.write("Enter your registered email and Date of Birth to recover your details.")
        with st.form("recover_form", clear_on_submit=True):
            rec_email = st.text_input("Registered Email")
            rec_dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1).date(), max_value=datetime.today().date())
            rec_submit = st.form_submit_button("Recover Details")
            
            if rec_submit:
                if not rec_email or not rec_dob:
                    st.warning("Please enter both Email and DOB.")
                else:
                    recovered_data = bank.recover_details(rec_email, rec_dob)
                    if recovered_data:
                        st.success(f"**Account Number:** {recovered_data[0]}")
                        st.success(f"**PIN:** {recovered_data[1]}")
                        st.info("👆 Please note down your details and login above.")
                    else:
                        st.error("No account found with this Email and Date of Birth combination.")

elif choice == "Create Account":
    st.header("📝 Open a New Account")
    # clear_on_submit=False kiya hai taaki error screen par ruke
    with st.form("create_form", clear_on_submit=False):
        name = st.text_input("Full Name")
        dob = st.date_input("Date of Birth", min_value=datetime(1900, 1, 1).date(), max_value=datetime.today().date())
        email = st.text_input("Email")
        pin = st.text_input("4-Digit PIN", type="password")
        submitted = st.form_submit_button("Register")

        if submitted:
            
            today = datetime.today().date()
            calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            
            if not name or not email:
                st.error("Name and Email cannot be empty.")
            elif calculated_age < 18:
                st.error(f"Your calculated age is {calculated_age} years. You must be at least 18 years old to open an account.")
            elif len(pin) != 4 or not pin.isdigit():
                st.error("PIN must be exactly 4 numeric digits.")
            else:
                
                try:
                    acc_no = bank.create_account(name, calculated_age, dob, email, pin)
                    st.success(f"✅ Step 3: Account created successfully! Your Account Number is: **{acc_no}**")
                except Exception as e:
                    st.error(f"❌ Step 3 (ERROR): Supabase Connection Failed -> {e}")

elif choice == "👑 Admin Dashboard":
    st.header("👑 Admin Database Viewer")
    st.write("Here you can see all the data stored securely on Supabase Cloud.")
    
    st.subheader("👥 All Bank Accounts")
    try:
        accounts = bank.get_all_accounts()
        if accounts:
            df_acc = pd.DataFrame(accounts)
            df_acc = df_acc[["account_no", "name", "age", "dob", "email", "pin", "balance"]]
            df_acc.columns = ["Account No", "Name", "Age", "DOB", "Email", "PIN", "Balance (₹)"]
            st.dataframe(df_acc, use_container_width=True, hide_index=True)
        else:
            st.info("No accounts in the database yet.")
    except Exception as e:
        st.error(f"Database Error: {e}")
        
    st.write("---")
    st.subheader("📜 All Transactions")
    try:
        transactions = bank.get_all_transactions()
        if transactions:
            df_trans = pd.DataFrame(transactions)
            df_trans = df_trans[["id", "account_no", "type", "amount", "timestamp"]]
            df_trans.columns = ["ID", "Account No", "Type", "Amount (₹)", "Date & Time"]
            st.dataframe(df_trans, use_container_width=True, hide_index=True)
        else:
            st.info("No transactions recorded yet.")
    except Exception as e:
        st.error(f"Database Error: {e}")

elif choice == "Dashboard (Details)":
    st.header("📊 Account Dashboard")
    user = bank.get_user(st.session_state.current_user_acc)
    col1, col2 = st.columns(2)
    col1.metric("Current Balance", f"₹{user['balance']}")
    col2.write(f"**Name:** {user['name']}")
    col2.write(f"**Email:** {user['email']}")
    col2.write(f"**Account No:** {user['accountNo.']}")
    col2.write(f"**DOB:** {user['dob']}")
    
    st.write("---")
    st.subheader("📜 Transaction History")
    history = bank.get_transaction_history(st.session_state.current_user_acc)
    if history:
        df = pd.DataFrame(history)
        df = df[["timestamp", "type", "amount"]]
        df.columns = ["Date & Time", "Type", "Amount (₹)"]
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No transactions yet. Deposit some money to see history!")

elif choice == "🤖 AI Financial Advisor":
    st.header("🤖 Your Personal AI Financial Advisor")
    st.write("Get smart, personalized financial advice based on your current balance and recent transactions!")
    user = bank.get_user(st.session_state.current_user_acc)
    history = bank.get_transaction_history(st.session_state.current_user_acc)
    
    if st.button("Generate My Financial Report"):
        with st.spinner("🧠 Analyzing your transactions... Please wait."):
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                from google import genai
                client = genai.Client(api_key=api_key)
                prompt = f"""
                You are a professional, helpful, and friendly AI financial advisor for a digital bank.
                Your client's name is {user['name']}. Their current bank balance is ₹{user['balance']}.
                Here is their recent transaction history (Date, Type, Amount): {history}
                Based on their balance and history, provide a short (3-4 bullet points) personalized financial advice in English.
                If they have no transactions, encourage them to start saving. 
                Keep the tone encouraging, professional, and use simple language.
                """
                response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
                st.success("Analysis Complete! Here is your personalized advice:")
                st.info(response.text)
            except KeyError:
                st.error("API Key not found! Please check your secrets.")
            except Exception as e:
                st.error(f"Oops! Something went wrong. Error details: {e}")

elif choice == "Deposit Money":
    st.header("💵 Deposit Funds")
    user = bank.get_user(st.session_state.current_user_acc)
    with st.form("deposit_form", clear_on_submit=True):
        amount = st.number_input("Amount to Deposit", min_value=1, max_value=100000, step=100)
        submitted = st.form_submit_button("Deposit")
        if submitted:
            new_balance = user['balance'] + amount
            bank.update_balance(user['accountNo.'], new_balance)
            bank.log_transaction(user['accountNo.'], "Deposit", amount) 
            st.success(f"Successfully deposited ₹{amount}. New balance: ₹{new_balance}")
            st.rerun()

elif choice == "Withdraw Money":
    st.header("🏧 Withdraw Funds")
    user = bank.get_user(st.session_state.current_user_acc)
    with st.form("withdraw_form", clear_on_submit=True):
        amount = st.number_input("Amount to Withdraw", min_value=1, step=100)
        submitted = st.form_submit_button("Withdraw")
        if submitted:
            if user['balance'] >= amount:
                new_balance = user['balance'] - amount
                bank.update_balance(user['accountNo.'], new_balance)
                bank.log_transaction(user['accountNo.'], "Withdraw", amount) 
                st.success(f"Successfully withdrew ₹{amount}. Remaining balance: ₹{new_balance}")
                st.rerun()
            else:
                st.error("Insufficient funds.")

elif choice == "Update Details":
    st.header("⚙️ Update Information")
    user = bank.get_user(st.session_state.current_user_acc)
    with st.form("update_form", clear_on_submit=True):
        new_name = st.text_input("New Name", value=user['name'])
        new_email = st.text_input("New Email", value=user['email'])
        new_pin = st.text_input("New PIN (4 digits)", value=user['pin'], type="password")
        submitted = st.form_submit_button("Save Changes")
        if submitted:
            if len(new_pin) != 4 or not new_pin.isdigit():
                st.error("PIN must be exactly 4 numeric digits.")
            else:
                bank.update_details(user['accountNo.'], new_name, new_email, new_pin)
                st.success("Details updated successfully!")
                st.rerun()

elif choice == "Change PIN":
    st.header("🔑 Change Your PIN")
    user = bank.get_user(st.session_state.current_user_acc)
    with st.form("change_pin_form", clear_on_submit=True):
        old_pin = st.text_input("Enter Old PIN", type="password")
        new_pin = st.text_input("Enter New 4-Digit PIN", type="password")
        confirm_pin = st.text_input("Confirm New PIN", type="password")
        submitted = st.form_submit_button("Update PIN")
        
        if submitted:
            if not bank.authenticate_user(user['accountNo.'], old_pin.strip()):
                st.error("Incorrect Old PIN. Please try again.")
            elif len(new_pin.strip()) != 4 or not new_pin.strip().isdigit():
                st.error("New PIN must be exactly 4 numeric digits.")
            elif new_pin.strip() != confirm_pin.strip():
                st.error("New PIN and Confirm PIN do not match.")
            elif old_pin.strip() == new_pin.strip():
                st.warning("New PIN cannot be the same as the Old PIN.")
            else:
                bank.change_pin(user['accountNo.'], new_pin.strip())
                st.success("PIN changed successfully! Please remember your new PIN.")

elif choice == "Delete Account":
    st.header("🗑️ Close Account")
    with st.form("delete_form"):
        confirm = st.checkbox("I confirm I want to permanently delete my account.")
        submitted = st.form_submit_button("Delete My Account", type="primary")
        if submitted:
            if confirm:
                bank.delete_account(st.session_state.current_user_acc)
                st.session_state.logged_in = False
                st.session_state.current_user_acc = None
                st.success("Account deleted. You have been logged out.")
                st.rerun()
            else:
                st.error("Please check the confirmation box.")

elif choice == "Logout":
    st.session_state.logged_in = False
    st.session_state.current_user_acc = None
    st.session_state.is_admin = False
    st.rerun()
