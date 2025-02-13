import smartsheet as client
import requests
import time
import csv
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
SMARTSHEET_TOKEN = os.getenv("SMARTSHEET_TOKEN")  # Get token from.env
headers = {'Authorization': 'Bearer ' + SMARTSHEET_TOKEN}  # Set headers for API requests
DOMAINS = os.getenv("DOMAINS").split(",") if os.getenv("DOMAINS") else []  # Get domains from .env
BASE_URL = os.getenv("BASE_URL") if os.getenv("BASE_URL") else "https://api.smartsheet.com/2.0" # Get base URL from .env

# CSV file for input users (emails)
INPUT_USERS_CSV = "input_users.csv"

# CSV file for logging processed users
PROCESSED_USERS_CSV = "processed_users.csv"

# Initialize Smartsheet client
smartsheet = client.Smartsheet(SMARTSHEET_TOKEN)

# Retrieves all users in the account
def get_all_users():
    all_users = []
    page_size = 1000
    page = 1

    while True:
        try:
            users_page = smartsheet.Users.list_users(page=page, page_size=page_size).data
            all_users.extend(users_page)
            if len(users_page) < page_size:  # No more pages
                break
            page += 1
        except smartsheet.exceptions.SmartsheetRateLimitExceeded as e:
            print(f"Rate limit exceeded. Retrying after backoff: {e}")
            backoff_time = 2
            for attempt in range(7):  # 7 levels of exponential backoff
                time.sleep(backoff_time)
                try:
                    users_page = smartsheet.Users.list_users(page=page, page_size=page_size).data
                    all_users.extend(users_page)
                    if len(users_page) < page_size:  # No more pages
                        break
                    page += 1
                    print(f"Got Users Page {page} (after retry)")
                    break  # Success
                except smartsheet.exceptions.SmartsheetRateLimitExceeded:
                    print(f"Rate limit exceeded (retry {attempt + 1}). Retrying after {backoff_time} seconds.")
                    backoff_time *= 2
                    if backoff_time > 300:  # 5 minute max
                        backoff_time = 300
                        print("Max backoff time reached while fetching users. Exiting User Fetch.")
                        return all_users  # Return what we have
            else:
                return all_users  # All retries failed
        except Exception as e:
            print(f"Error fetching users: {e}")
            return all_users  # Return what we have
    return all_users

# Invites a user to the account so that they can be deactivated
def invite_user(email):
    try:
        user_obj = {
            'email': email,
            'admin': False,
            'licensedSheetCreator': False
        }
        new_user = smartsheet.Users.add_user(smartsheet.models.User(user_obj), send_email=False) #sendEmail=False
        if new_user.message == "SUCCESS":
            print(f"Invited user: {email}")
            return new_user.data
        else:
            print(f"Failed to invite user {email}: {result.message}")
            return False
    except smartsheet.exceptions.SmartsheetRateLimitExceeded as e:
        print(f"Rate limit exceeded. Retrying after backoff: {e}")
        backoff_time = 2
        for attempt in range(7):  # 7 levels of exponential backoff
            time.sleep(backoff_time)
            try:
                result = smartsheet.Users.add_user(smartsheet.models.User(email=email, send_email=False))
                if result.message == "SUCCESS":
                    print(f"Invited user: {email} (after retry)")
                    return True
                else:
                    print(f"Failed to invite user {email} (retry {attempt + 1}): {result.message}")
                    backoff_time *= 2
                    if backoff_time > 300:  # 5 minute max
                        backoff_time = 300
                        print("Max backoff time reached. Skipping user")
                        return False
            except smartsheet.exceptions.SmartsheetRateLimitExceeded:
                print(f"Rate limit exceeded (retry {attempt + 1}). Retrying after {backoff_time} seconds.")
                backoff_time *= 2
                if backoff_time > 300:
                    backoff_time = 300
                    print("Max backoff time reached. Skipping user")
                    return False
        return False
    except Exception as e:
        print(f"An error occurred while inviting {email}: {e}")
        return False

# Deactivates a user in the account
def deactivate_user(user_id, email):
    try:
        url = BASE_URL + "/users/" + str(user_id) + "/deactivate"
        response = requests.post(url, headers=headers)

        result = response.json()

        if result.get('message') == "SUCCESS":
            print(f"Deactivated user: {email}")
            return True
        else:
            url = BASE_URL + "/users/" + str(user_id) + "/deactivate"
            response = requests.post(url, headers=headers)

            result = response.json()

            if result.get('message') == "SUCCESS":
                print(f"Deactivated user: {email}")
                return True
        print(f"Failed to deactivate user {email}: {result.message}")
        return False
    except smartsheet.exceptions.SmartsheetRateLimitExceeded as e:
        print(f"Rate limit exceeded. Retrying after backoff: {e}")
        backoff_time = 2
        for attempt in range(7):
            time.sleep(backoff_time)
            try:
                url = BASE_URL + "/users/" + str(user_id) + "/deactivate"
                print((url, headers))
                response = requests.post(url, headers=headers)

                result = response.json()

                if result.response.message == "SUCCESS":
                    print(f"Deactivated user: {email} (after retry)")
                    return True
                else:
                    print(f"Failed to deactivate user {email} (retry {attempt + 1}): {result.message}")
                    backoff_time *= 2
                    if backoff_time > 300:
                        backoff_time = 300
                        print("Max backoff time reached. Skipping user")
                        return False
            except smartsheet.exceptions.SmartsheetRateLimitExceeded:
                print(f"Rate limit exceeded (retry {attempt + 1}). Retrying after {backoff_time} seconds.")
                backoff_time *= 2
                if backoff_time > 300:
                    backoff_time = 300
                    print("Max backoff time reached. Skipping user")
                    return False
        return False
    except Exception as e:
        print(f"An error occurred while deactivating {email}: {e}")
        return False

# Process users from input CSV
def process_users():
    print(f"Processing users from '{INPUT_USERS_CSV}'")

    all_users = get_all_users()
    print(f"Found {len(all_users)} existing users.")

    existing_user_emails = {user.email for user in all_users}
    deactivate_list = []
    invited_list = []
    skipped_list = []

    try:
        with open(INPUT_USERS_CSV, 'r', encoding='utf-8') as csvfile:
            users = csv.reader(csvfile)
            next(users)  # Skip header row

            for user in users:
                email = user[0]
                domain = email.split("@")[1]

                print()

                if email in existing_user_emails:
                    user_id = next((user.id for user in all_users if user.email == email), None)
                    if user_id:
                        deactivate_list.append({'id': user_id, 'email': email})
                elif domain in DOMAINS:
                    new_user = invite_user(email)
                    if new_user: # Only add to deactivate list if invite succeeds
                        invited_list.append(email)
                        user_id = new_user.id
                        deactivate_list.append({'id': user_id, 'email': email})
                    else:
                        print(f"User {email} not found after successful invite.")
                else:
                    print(f"User {email} (domain {domain}) outside control. Skipping.")
                    skipped_list.append(email)

    except FileNotFoundError:
        print(f"Input CSV file '{INPUT_USERS_CSV}' not found.")
        return

    print(f"Found {len(deactivate_list)} user(s) to deactivate.")
    # Deactivate users and log all actions
    with open(PROCESSED_USERS_CSV, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        if not os.path.exists(PROCESSED_USERS_CSV) or os.stat(PROCESSED_USERS_CSV).st_size == 0: # Check if file exists and is empty
            writer.writerow(['Email', 'User ID', 'Status', 'Timestamp'])  # Write header if new file or empty

        for user in deactivate_list:
            user_id = user["id"]
            email = user["email"]
            deactivate_success = deactivate_user(user_id, email)

            if deactivate_success:
                writer.writerow([email, user_id, "Deactivated", datetime.now().isoformat()])
                print(f"Successfully deactivated {email}")
            else:
                print(f"Failed to deactivate {email}")



# Call the process_users function
process_users()