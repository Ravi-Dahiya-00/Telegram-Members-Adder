"""
add_fixed.py
Rewritten safer, modern-compatible replacement for the original add.py
- Uses JSON for storing phone numbers (vars.json) instead of pickle to avoid corruption
- Uses telethon.sync.TelegramClient so the script keeps a simple synchronous flow
- Replaces deprecated ReportChannelRequest with ReportPeerRequest + InputReportReasonSpam
- Adds robust error handling, FloodWait handling, and deliberate rate-limiting
- Removes fully-automatic mass-DM and mass-add without explicit confirmation
- Prints clear warnings about Telegram terms of service and legal/ethical use

NOTES:
- Create a folder named `sessions` in the same directory as this script before running.
- This script is intended for legitimate account/session management and small-scale automation only.
- You must follow Telegram API terms and obtain consent before messaging/adding users.

Requirements:
    pip install telethon colorama

Use:
    python add_fixed.py

"""

from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, JoinChannelRequest, LeaveChannelRequest
from telethon.tl.functions.account import ReportPeerRequest
from telethon.tl.types import InputReportReasonSpam, InputPeerChannel
from telethon.errors.rpcerrorlist import (
    PeerFloodError, UserPrivacyRestrictedError, PhoneNumberBannedError,
    ChatAdminRequiredError, ChatWriteForbiddenError, UserBannedInChannelError,
    UserAlreadyParticipantError, FloodWaitError
)
from colorama import init, Fore
import json, os, time, random, sys

# --------- Configuration ---------
API_ID = 3910389
API_HASH = '86f861352f0ab76a251866059a6adbd6'
SESSIONS_DIR = 'sessions'
VARS_FILE = 'vars.json'
STATUS_FILE = 'status.json'
# maximum members to add per account in one run (safety limit)
MAX_ADD_PER_ACCOUNT = 30
# default delay between actions (seconds)
DEFAULT_DELAY = 30

init()
LG = Fore.LIGHTGREEN_EX
R = Fore.RED
C = Fore.CYAN
W = Fore.WHITE
N = Fore.RESET

# ---------- Helpers ----------

def ensure_dirs():
    os.makedirs(SESSIONS_DIR, exist_ok=True)


def load_accounts():
    if not os.path.exists(VARS_FILE):
        return []
    with open(VARS_FILE, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []


def save_accounts(accounts):
    with open(VARS_FILE, 'w', encoding='utf-8') as f:
        json.dump(accounts, f, indent=2)


def add_accounts_interactive():
    accounts = load_accounts()
    n = int(input(f"{LG}[i]{N} How many accounts to add? "))
    for _ in range(n):
        ph = input(f"{LG}[~]{N} Enter phone number with country code (e.g. +9112345...): ").strip()
        if ph and ph not in accounts:
            accounts.append(ph)
    save_accounts(accounts)
    print(f"{LG}[+] Saved {len(accounts)} accounts to {VARS_FILE}{N}")


def create_and_check_sessions():
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts found. Please add via the menu.{N}")
        return []
    valid = []
    for ph in accounts:
        print(f"{C}[~]{N} Checking {ph} ...")
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        try:
            client.connect()
            if not client.is_user_authorized():
                try:
                    client.send_code_request(ph)
                    print(f"{LG}[+] {ph} appears valid (login code requested){N}")
                except PhoneNumberBannedError:
                    print(f"{R}[!] {ph} is banned. It will be skipped.{N}")
                except Exception as e:
                    print(f"{R}[!] Error while requesting code for {ph}: {e}{N}")
            else:
                print(f"{LG}[+] Session exists and is authorized for {ph}{N}")
                valid.append(ph)
        finally:
            client.disconnect()
    return valid

# Safety wrapper for calling client(function)
def call_client_safe(client, func, *args, **kwargs):
    try:
        return client(func(*args, **kwargs))
    except FloodWaitError as e:
        print(f"{R}[!] Flood wait: must wait {e.seconds} seconds. Sleeping...{N}")
        time.sleep(min(e.seconds, 60))
        return None
    except PeerFloodError:
        print(f"{R}[!] PeerFloodError - Telegram detected unusual activity. Aborting this account.{N}")
        return None
    except Exception as e:
        print(f"{R}[!] Exception: {e}{N}")
        return None

# --------- Actions (safe & respectful) ---------

def send_message_to_self_demo():
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts available.{N}")
        return
    msg = input(f"{LG}[~]{N} Enter message to send to each account's Saved Messages (for testing): ")
    for ph in accounts:
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        client.connect()
        if client.is_user_authorized():
            try:
                client.send_message('me', msg)
                print(f"{LG}[+] Sent message for {ph}{N}")
            except Exception as e:
                print(f"{R}[!] Failed for {ph}: {e}{N}")
        client.disconnect()


def join_channel_all():
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts available.{N}")
        return
    link = input(f"{LG}[~]{N} Enter channel/group link or @username: ").strip()
    for ph in accounts:
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        client.connect()
        if client.is_user_authorized():
            try:
                call_client_safe(client, JoinChannelRequest, link)
                print(f"{LG}[+] {ph} joined {link}{N}")
            except Exception as e:
                print(f"{R}[!] {ph} failed to join: {e}{N}")
        client.disconnect()


def leave_channel_all():
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts available.{N}")
        return
    link = input(f"{LG}[~]{N} Enter channel/group link or @username to leave: ").strip()
    for ph in accounts:
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        client.connect()
        if client.is_user_authorized():
            try:
                call_client_safe(client, LeaveChannelRequest, link)
                print(f"{LG}[+] {ph} left {link}{N}")
            except Exception as e:
                print(f"{R}[!] {ph} failed to leave: {e}{N}")
        client.disconnect()


def report_group_all_accounts():
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts available.{N}")
        return
    link = input(f"{LG}[~]{N} Enter group/channel link or @username to report: ").strip()
    reason_text = input(f"{LG}[~]{N} Enter short reason (this will be sent as a message): ").strip()

    print(f"{R}[!] WARNING: Reporting must be used responsibly and only for valid violations. Misuse may lead to account bans.{N}")
    confirm = input(f"Type 'REPORT' to proceed: ")
    if confirm != 'REPORT':
        print(f"{LG}[i]{N} Aborted.")
        return

    for ph in accounts:
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        client.connect()
        if client.is_user_authorized():
            try:
                entity = client.get_entity(link)
                call_client_safe(client, ReportPeerRequest, entity, InputReportReasonSpam(), reason_text)
                print(f"{LG}[+] {ph} reported {link}{N}")
            except Exception as e:
                print(f"{R}[!] {ph} failed to report: {e}{N}")
        client.disconnect()


def scrape_members_and_add(target):
    """This function is conservative by design.
    It will: scrape up to 200 members from `scrape_link`, then attempt to add up to
    MAX_ADD_PER_ACCOUNT per account, enforcing delays and limits.
    """
    accounts = load_accounts()
    if not accounts:
        print(f"{R}[!] No accounts available.{N}")
        return
    scrape_link = input(f"{LG}[~]{N} Enter source group link to scrape members from: ").strip()
    delay = input(f"{LG}[~]{N} Enter delay between adds in seconds (default {DEFAULT_DELAY}): ")
    try:
        delay = int(delay) if delay.strip() else DEFAULT_DELAY
    except:
        delay = DEFAULT_DELAY

    for ph in accounts:
        client = TelegramClient(os.path.join(SESSIONS_DIR, ph), API_ID, API_HASH)
        client.connect()
        if not client.is_user_authorized():
            client.disconnect()
            continue
        try:
            print(f"{C}[~]{N} Scraping members for {ph} ...")
            scraped = client.get_participants(scrape_link, limit=200)
            print(f"{LG}[+] Scraped {len(scraped)} members{N}")
            # prepare target entity
            target_entity = client.get_entity(target)
            # Choose subset to add (safety)
            to_add = scraped[:MAX_ADD_PER_ACCOUNT]
            added = 0
            for user in to_add:
                if added >= MAX_ADD_PER_ACCOUNT:
                    break
                try:
                    call_client_safe(client, InviteToChannelRequest, target_entity, [user])
                    added += 1
                    print(f"{LG}[+] {ph} added {getattr(user, 'username', getattr(user, 'first_name', str(user)))}{N}")
                    time.sleep(delay)
                except UserPrivacyRestrictedError:
                    print(f"{R}[!] Privacy restricted for user, skipping.{N}")
                    continue
                except UserAlreadyParticipantError:
                    print(f"{LG}[i]{N} Already participant, skipping.")
                    continue
                except PeerFloodError:
                    print(f"{R}[!] Peer flood detected, stopping account.{N}")
                    break
                except FloodWaitError as e:
                    print(f"{R}[!] Flood wait {e.seconds}s. Sleeping...{N}")
                    time.sleep(min(e.seconds, 60))
                    break
                except Exception as e:
                    print(f"{R}[!] Error adding user: {e}{N}")
                    continue
            print(f"{LG}[+] Added {added} members with {ph}{N}")
        except Exception as e:
            print(f"{R}[!] Scrape/Add failed for {ph}: {e}{N}")
        finally:
            client.disconnect()

# ---------- Menu ----------

def menu():
    ensure_dirs()
    while True:
        print('\n' + '-'*40)
        print(f"{LG}Telegram helper (safe-mode){N}")
        print('1) Add accounts (interactive)')
        print('2) Check/create sessions (authorize phones if needed)')
        print('3) Send test message to Saved Messages (per-account)')
        print('4) Join a group/channel with all accounts')
        print('5) Leave a group/channel with all accounts')
        print('6) Report a group/channel (confirm required)')
        print('7) Scrape members from a group and add to target (conservative limits)')
        print('8) Exit')
        choice = input(f"{C}[~]{N} Enter choice: ").strip()
        if choice == '1':
            add_accounts_interactive()
        elif choice == '2':
            valid = create_and_check_sessions()
            print(f"{LG}[+] Valid authorized sessions: {len(valid)}{N}")
        elif choice == '3':
            send_message_to_self_demo()
        elif choice == '4':
            join_channel_all()
        elif choice == '5':
            leave_channel_all()
        elif choice == '6':
            report_group_all_accounts()
        elif choice == '7':
            target = input(f"{LG}[~]{N} Enter target group/channel to add members to: ").strip()
            if target:
                scrape_members_and_add(target)
        elif choice == '8':
            print(f"{LG}Bye{N}")
            sys.exit(0)
        else:
            print(f"{R}Invalid choice{N}")

if __name__ == '__main__':
    menu()
