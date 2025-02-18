# Smartsheet Bulk Deactivate Users

## About
The Deactivate User script was created to **help** streamline the process of cleaning up user access before transitioning to User System Management (USM) in Smartsheet. **While the script and information provided herein were developed based of generally known best practices, Smartsheet does not guarantee your use of the script will provide its desired results in each specific circumstance.**

## Overview
This Python script automates user invitations and deactivating users:
- Retrieving all users from the Smartsheet account using pagination.
- Comparing them against an input CSV containing only email addresses.
- Filtering users based on their status:
  - **Existing users**: Deactivates them.
  - **Users with matching domains**: Invites them and adds them to the deactivation list.
  - **Users with non-matching domains**: Skips them.
- Handling deactivation after invitations are complete.
- Implementing exponential backoff for rate limit handling.
- Logging all successes to an external CSV.
- Allowing for import of a CSV to skip already processed users, enabling script restart without losing progress.

## API Endpoints Used
- **List all users:** `GET https://api.smartsheet.com/2.0/users?page={page}&pageSize=1000`
- **Invite a user:** `POST https://api.smartsheet.com/2.0/users?sendEmail=false`
- **Deactivate a user:** `POST https://api.smartsheet.com/2.0/users/{userId}/deactivate`

## Prerequisites
The new User Subscription Model (USM) introduces Provisional Members—users who are not part of your plan but are still shared on assets owned by your plan. These users fall into two categories:

**Never invited** – Users who have never been invited to join your plan.
**Removed users** – Users previously removed by a System Admin but still have access to shared assets.

Since these users exist outside the governance of the System Admin, they must be formally invited to join the account. All invited users must accept the invitation before they are added, except for users with domains configured in **User Auto Provisioning (UAP)**. Users with verified UAP domains will bypass the invitation process and become fully manageable within the system.

This script ensures compliance by:
1. Processing only users already in your account.
2. Automatically inviting users with validated UAP domains.

## Creating your INPUT_USER.CSV
As a System Admin of your Smartsheet account, you can download the Sheet Access Report to identify users who have access to your assets but should not be moved into the User Subscription Model (USM).

To prevent these users from being included in USM, follow these steps:

Create a CSV file named input_users.csv.
List the email addresses of all users you wish to deactivate.
Ensure the first row of the file contains the column header: Email.
This CSV will be used by the script to deactivate the specified users, ensuring they are no longer part of your Smartsheet account.

### Required Python Packages
Ensure you have the following packages installed:
```sh
pip install requests python-dotenv pandas
```
### Environment Variables
Create a `.env` file with:
```ini
SMARTSHEET_TOKEN=your_api_token_here
DOMAINS=example.com,anotherdomain.com
BASE_URL=https://api.smartsheet.com/2.0
```

## Usage
### Running the Script
```sh
python script.py input.csv
```
- Replace `input.csv` with your actual CSV file containing email addresses.
- The script will:
  1. Fetch all users from Smartsheet.
  2. Compare them against the CSV.
  3. Invite or deactivate users as needed.
  4. Log processed users to prevent duplication.

### Handling Rate Limits
- The script implements a **7-level exponential backoff** within **5 minutes** for 429 errors.
- If rate limits are exceeded, the script will pause and retry automatically.

### Restarting the Script
- If interrupted, re-run the script using the same `input.csv`.
- Already processed users will be skipped using the log file.

## Logging
- All successful operations (invitations and deactivations) are logged in `processed_users.csv`.
- This log prevents duplicate processing and allows for restartability.

## Troubleshooting
- **Invalid API Token:** Ensure `SMARTSHEET_API_TOKEN` is correctly set in `.env`.
- **Rate Limit Errors:** The script automatically retries; if persistent, wait before re-running.
- **Users Not Being Invited:** Verify `ALLOWED_DOMAINS` contains the expected domains.
- **Users Not Being Deactivated:** Ensure they exist in Smartsheet and are eligible for deactivation.

## Future Enhancements
- Implement parallel processing for improved efficiency.
- Add support for additional user roles and permissions.
- Improve logging with detailed timestamps and error handling.

---
**Author:** Taylor Fry (Manager, Technical Solutions Engineering)  
**Last Updated:** [02/13/2025]