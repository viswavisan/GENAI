"""
Gmail Model Context Protocol (MCP) Server.

A minimal, pure MCP Server connecting directly to real Gmail via IMAP/SMTP.
Exposes standard MCP primitives:
- Tools: search_emails, read_email, send_email, create_draft
- Resources: gmail://inbox/unread, gmail://inbox/stats
- Prompts: draft_reply_prompt, summarize_inbox_prompt
"""

import os
import smtplib
import imaplib
import email
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.header import decode_header
from email.utils import formatdate, make_msgid, formataddr
import datetime
import asyncio
from pathlib import Path
from typing import Dict, Any, List
import configparser
from dotenv import load_dotenv
from mcp.server.mcpserver import MCPServer

# Initialize MCP Server for Gmail
gmail_mcp_server = MCPServer(name="Gmail-MCP-Server", version="1.0.0")
BASE_DIR = Path(__file__).resolve().parent.parent.parent


def get_credentials():
    """Retrieve Gmail address and App Password from properties.ini, .env, or OS env."""
    user = os.getenv("GMAIL_ADDRESS", "").strip()
    pwd = os.getenv("GMAIL_APP_PASSWORD", "").strip()

    # Check properties.ini
    props_path = BASE_DIR / "properties.ini"
    if props_path.is_file():
        try:
            parser = configparser.ConfigParser()
            parser.read(props_path)
            if parser.has_section("environment"):
                user = user or parser.get("environment", "GMAIL_ADDRESS", fallback="").strip()
                pwd = pwd or parser.get("environment", "GMAIL_APP_PASSWORD", fallback="").strip()
        except Exception:
            pass

    # Check .env
    if not (user and pwd):
        env_path = BASE_DIR / ".env"
        if env_path.is_file():
            load_dotenv(env_path, override=True)
            user = user or os.getenv("GMAIL_ADDRESS", "").strip()
            pwd = pwd or os.getenv("GMAIL_APP_PASSWORD", "").strip()

    if not (user and pwd):
        raise ValueError("Gmail credentials missing. Please set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env or properties.ini.")

    return user, pwd.replace(" ", "")


def get_imap_connection(timeout: float = 10.0):
    """Establish authenticated IMAP connection to Gmail with socket timeout."""
    user, pwd = get_credentials()
    mail = imaplib.IMAP4_SSL("imap.gmail.com", timeout=timeout)
    mail.login(user, pwd)
    return mail


def _decode_mime(header_val: str) -> str:
    """Helper to decode MIME encoded headers."""
    if not header_val:
        return ""
    try:
        parts = decode_header(header_val)
        return "".join(
            p.decode(enc or "utf-8", errors="ignore") if isinstance(p, bytes) else str(p)
            for p, enc in parts
        )
    except Exception:
        return str(header_val)


# =====================================================================
# 1. MCP TOOLS (Real Gmail Actions)
# =====================================================================

@gmail_mcp_server.tool()
def get_unread_count() -> Dict[str, Any]:
    """Get the total count of unread messages in your Gmail inbox."""
    user, _ = get_credentials()
    try:
        mail = get_imap_connection(timeout=10.0)
        # Fast IMAP STATUS query (avoids downloading thousands of message IDs)
        status, data = mail.status("inbox", "(UNSEEN)")
        count = 0
        if status == "OK" and data and data[0]:
            import re
            m = re.search(r'UNSEEN\s+(\d+)', data[0].decode('utf-8', errors='ignore'))
            if m:
                count = int(m.group(1))
        mail.logout()
        return {
            "unread_count": count,
            "account": user,
            "message": f"You have {count} unread emails in your inbox."
        }
    except Exception as e:
        return {
            "unread_count": 0,
            "account": user,
            "error": str(e),
            "message": f"Error fetching unread count: {str(e)}"
        }


@gmail_mcp_server.tool()
def search_emails(query: str = "", max_results: int = 8, page: int = 1) -> List[Dict[str, Any]]:
    """
    Search inbox emails by keyword or Gmail search syntax (e.g. 'is:unread', 'from:google', 'security').
    Supports page pagination.
    """
    try:
        mail = get_imap_connection(timeout=10.0)
        status, select_data = mail.select("inbox", readonly=True)
        if status != "OK" or not select_data or not select_data[0]:
            mail.logout()
            return []

        total_msgs = int(select_data[0].decode('utf-8', errors='ignore')) if select_data[0].isdigit() else 0
        if total_msgs == 0:
            mail.logout()
            return []

        q = query.strip()
        results = []
        page = max(1, int(page))

        # Optimization: empty query fetches recent messages by sequence range in 1 single network request
        if not q or q.upper() == "ALL":
            end_num = max(1, total_msgs - (page - 1) * max_results)
            start_num = max(1, end_num - max_results + 1)
            seq_range = f"{start_num}:{end_num}"
            st, fetch_data = mail.fetch(seq_range, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
            mail.logout()
            if st == "OK" and fetch_data:
                for item in reversed(fetch_data):
                    if isinstance(item, tuple) and len(item) == 2:
                        seq_id = item[0].split()[0].decode('utf-8', errors='ignore') if item[0] else ""
                        msg = email.message_from_bytes(item[1])
                        results.append({
                            "id": seq_id,
                            "sender": _decode_mime(msg.get("From")),
                            "subject": _decode_mime(msg.get("Subject")),
                            "timestamp": msg.get("Date", ""),
                            "body": _decode_mime(msg.get("Subject")),
                            "unread": False,
                            "labels": ["Inbox"]
                        })
            return results

        # Targeted query
        status, data = "NO", None
        if q.lower() in ["unread", "is:unread", "unseen"]:
            status, data = mail.search(None, "UNSEEN")
        else:
            try:
                status, data = mail.search(None, "X-GM-RAW", q)
            except Exception:
                status = "NO"

            if status != "OK" or not data or not data[0]:
                try:
                    status, data = mail.search(None, f'(OR (HEADER Subject "{q}") (HEADER From "{q}"))')
                except Exception:
                    status, data = "NO", None

        if status == 'OK' and data and data[0]:
            ids = data[0].split()
            target_ids = ids[-max_results:]
            if target_ids:
                id_spec = b",".join(target_ids).decode('utf-8')
                st, fetch_data = mail.fetch(id_spec, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                if st == 'OK' and fetch_data:
                    for item in reversed(fetch_data):
                        if isinstance(item, tuple) and len(item) == 2:
                            seq_id = item[0].split()[0].decode('utf-8', errors='ignore') if item[0] else ""
                            msg = email.message_from_bytes(item[1])
                            results.append({
                                "id": seq_id,
                                "sender": _decode_mime(msg.get("From")),
                                "subject": _decode_mime(msg.get("Subject")),
                                "timestamp": msg.get("Date", ""),
                                "body": _decode_mime(msg.get("Subject")),
                                "unread": False,
                                "labels": ["Inbox"]
                            })
        mail.logout()
        return results
    except Exception as e:
        return [{"error": f"Search error or timeout: {str(e)}"}]




@gmail_mcp_server.tool()
def get_sent_emails(max_results: int = 8, page: int = 1) -> Dict[str, Any]:
    """Retrieve recent sent emails from the Gmail Sent / Outbox folder with pagination."""
    import math
    try:
        mail = get_imap_connection(timeout=10.0)
        sent_folder = chr(34) + "[Gmail]/Sent Mail" + chr(34)
        status, select_data = mail.select(sent_folder, readonly=True)
        if status != "OK" or not select_data or not select_data[0]:
            mail.logout()
            return {"emails": [], "total_count": 0, "page": 1, "total_pages": 1, "start_index": 0, "end_index": 0, "folder": "outbox"}

        total_msgs = int(select_data[0].decode("utf-8", errors="ignore")) if select_data[0].isdigit() else 0
        if total_msgs == 0:
            mail.logout()
            return {"emails": [], "total_count": 0, "page": 1, "total_pages": 1, "start_index": 0, "end_index": 0, "folder": "outbox"}

        page = max(1, int(page))
        total_pages = max(1, math.ceil(total_msgs / max_results))
        page = min(page, total_pages)

        end_num = max(1, total_msgs - (page - 1) * max_results)
        start_num = max(1, end_num - max_results + 1)
        seq_range = f"{start_num}:{end_num}"
        st, fetch_data = mail.fetch(seq_range, "(BODY[HEADER.FIELDS (SUBJECT TO DATE)])")
        mail.logout()
        results = []
        if st == "OK" and fetch_data:
            for item in reversed(fetch_data):
                if isinstance(item, tuple) and len(item) == 2:
                    seq_id = item[0].split()[0].decode("utf-8", errors="ignore") if item[0] else ""
                    msg = email.message_from_bytes(item[1])
                    recipient_val = _decode_mime(msg.get("To"))
                    subj_val = _decode_mime(msg.get("Subject"))
                    results.append({
                        "id": seq_id,
                        "recipient": recipient_val,
                        "sender": os.getenv("GMAIL_USER", "viswa30031990@gmail.com"),
                        "subject": subj_val,
                        "timestamp": msg.get("Date", ""),
                        "body": subj_val,
                        "folder": "Sent Mail"
                    })
        start_idx = (page - 1) * max_results + 1 if results else 0
        end_idx = min(total_msgs, (page - 1) * max_results + len(results)) if results else 0
        return {
            "emails": results,
            "total_count": total_msgs,
            "page": page,
            "page_size": max_results,
            "total_pages": total_pages,
            "start_index": start_idx,
            "end_index": end_idx,
            "has_next": page < total_pages,
            "has_prev": page > 1,
            "folder": "outbox"
        }
    except Exception as e:
        return {"emails": [], "error": f"Failed to fetch sent emails: {str(e)}", "total_count": 0, "page": 1, "total_pages": 1, "folder": "outbox"}


def list_inbox_emails(page: int = 1, page_size: int = 8) -> Dict[str, Any]:
    """Helper for Live Inbox pagination."""
    import math
    try:
        mail = get_imap_connection(timeout=10.0)
        status, select_data = mail.select("inbox", readonly=True)
        if status != "OK" or not select_data or not select_data[0]:
            mail.logout()
            return {"emails": [], "total_count": 0, "page": page, "total_pages": 1, "start_index": 0, "end_index": 0, "has_next": False, "has_prev": False}

        total_msgs = int(select_data[0].decode("utf-8", errors="ignore")) if select_data[0].isdigit() else 0
        if total_msgs == 0:
            mail.logout()
            return {"emails": [], "total_count": 0, "page": page, "total_pages": 1, "start_index": 0, "end_index": 0, "has_next": False, "has_prev": False}

        page = max(1, int(page))
        total_pages = max(1, math.ceil(total_msgs / page_size))
        page = min(page, total_pages)

        end_num = max(1, total_msgs - (page - 1) * page_size)
        start_num = max(1, end_num - page_size + 1)
        seq_range = f"{start_num}:{end_num}"

        st, fetch_data = mail.fetch(seq_range, "(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])")
        mail.logout()
        results = []
        if st == "OK" and fetch_data:
            for item in reversed(fetch_data):
                if isinstance(item, tuple) and len(item) == 2:
                    seq_id = item[0].split()[0].decode("utf-8", errors="ignore") if item[0] else ""
                    msg = email.message_from_bytes(item[1])
                    results.append({
                        "id": seq_id,
                        "sender": _decode_mime(msg.get("From")),
                        "subject": _decode_mime(msg.get("Subject")),
                        "timestamp": msg.get("Date", ""),
                        "body": _decode_mime(msg.get("Subject")),
                        "unread": False,
                        "labels": ["Inbox"]
                    })

        start_idx = (page - 1) * page_size + 1 if results else 0
        end_idx = min(total_msgs, (page - 1) * page_size + len(results)) if results else 0

        return {
            "emails": results,
            "total_count": total_msgs,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "start_index": start_idx,
            "end_index": end_idx,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }
    except Exception as e:
        return {"emails": [], "error": str(e), "total_count": 0, "page": 1, "total_pages": 1, "start_index": 0, "end_index": 0, "has_next": False, "has_prev": False}


@gmail_mcp_server.tool()
def get_inbox_emails(max_results: int = 8, page: int = 1) -> Dict[str, Any]:
    """Retrieve recent inbox emails from Gmail with sender, subject, timestamp, snippet, and unread status with pagination."""
    res = list_inbox_emails(page=page, page_size=max_results)
    res["folder"] = "inbox"
    return res


@gmail_mcp_server.tool()
def delete_email(message_id: str) -> Dict[str, Any]:
    """Delete an email message by its ID from the inbox (moves to Bin / Trash)."""
    try:
        mail = get_imap_connection(timeout=10.0)
        mail.select("inbox")
        mid = str(message_id).strip()
        trash_folder = chr(34) + "[Gmail]/Bin" + chr(34)
        try:
            mail.copy(mid, trash_folder)
        except Exception:
            pass

        mail.store(mid, "+FLAGS", "\\Deleted")
        mail.expunge()
        mail.logout()
        return {
            "success": True,
            "message": f"Email #{mid} successfully deleted from inbox."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to delete email #{message_id}: {str(e)}"
        }


@gmail_mcp_server.tool()
def read_email(message_id: str) -> Dict[str, Any]:
    """Retrieve full headers and body text of a real Gmail message by its ID."""
    try:
        mail = get_imap_connection(timeout=10.0)
        mail.select("inbox")
        status, data = mail.fetch(message_id, "(RFC822)")

        if status != "OK" or not data or not data[0] or not isinstance(data[0], tuple):
            mail.logout()
            return {"error": f"Message ID '{message_id}' not found in inbox."}

        raw = data[0][1]
        msg = email.message_from_bytes(raw)
        subject = _decode_mime(msg.get("Subject"))
        sender = _decode_mime(msg.get("From"))
        recipient = _decode_mime(msg.get("To"))
        date_ = msg.get("Date", "")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))
                if ctype == "text/plain" and "attachment" not in cdispo:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode("utf-8", errors="ignore")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode("utf-8", errors="ignore")

        mail.logout()
        return {
            "id": message_id,
            "sender": sender,
            "recipient": recipient,
            "subject": subject,
            "timestamp": date_,
            "body": body.strip() or "(Formatted HTML email)"
        }
    except Exception as e:
        return {"error": f"Failed to read message {message_id}: {str(e)}"}


@gmail_mcp_server.tool()
def send_email(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Send a real email via Gmail SMTP with anti-spam compliant RFC headers and multipart formatting."""
    try:
        user, pwd = get_credentials()
        
        msg = EmailMessage()
        msg["Subject"] = subject
        sender_name = user.split("@")[0].capitalize()
        msg["From"] = formataddr((sender_name, user))
        msg["To"] = recipient
        msg["Reply-To"] = user
        msg["Date"] = formatdate(localtime=True)
        # Note: Do not set manual Message-ID; Gmail SMTP automatically stamps its own authentic Google Message-ID
        msg["MIME-Version"] = "1.0"
        
        # Plain-text version
        msg.set_content(body)
        
        # HTML version (multipart/alternative heavily improves spam scores on Yahoo & Outlook)
        import html
        html_paragraphs = "".join(f"<p>{html.escape(line)}</p>" for line in body.split("\n\n") if line.strip())
        html_content = f"""\
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 14px; line-height: 1.5; color: #1f2937;">
{html_paragraphs}
</body>
</html>"""
        msg.add_alternative(html_content, subtype="html")

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10.0) as server:
            server.login(user, pwd)
            server.send_message(msg)

        return {
            "success": True,
            "message": f"Real email sent to {recipient} via Gmail SMTP."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to send email to {recipient}: {str(e)}"
        }


@gmail_mcp_server.tool()
def create_draft(recipient: str, subject: str, body: str) -> Dict[str, Any]:
    """Save an email draft in real Gmail Drafts folder."""
    try:
        user, _ = get_credentials()
        msg = EmailMessage()
        msg["Subject"] = subject
        sender_name = user.split("@")[0].capitalize()
        msg["From"] = formataddr((sender_name, user))
        msg["To"] = recipient
        msg["Reply-To"] = user
        msg["Date"] = formatdate(localtime=True)
        msg["MIME-Version"] = "1.0"
        msg.set_content(body)

        mail = get_imap_connection(timeout=10.0)
        drafts_folder = "[Gmail]/Drafts"
        try:
            mail.select(drafts_folder)
        except Exception:
            drafts_folder = "Drafts"
            mail.select(drafts_folder)

        mail.append(drafts_folder, "\\Draft", imaplib.Time2Internaldate(datetime.datetime.now()), bytes(msg))
        mail.logout()

        return {
            "success": True,
            "message": f"Draft saved in Gmail Drafts folder for {recipient}."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": f"Failed to create draft: {str(e)}"
        }


# =====================================================================
# 2. MCP RESOURCES (Real Context Feeds)
# =====================================================================

@gmail_mcp_server.resource("gmail://inbox/unread")
def resource_unread_emails() -> str:
    """Summarized feed of real unread emails."""
    try:
        mail = get_imap_connection(timeout=10.0)
        mail.select("inbox", readonly=True)
        status, data = mail.search(None, "UNSEEN")

        if status != "OK" or not data or not data[0]:
            mail.logout()
            return "No unread emails in Gmail inbox."

        ids = data[0].split()
        total_unread = len(ids)
        target_ids = ids[-5:]
        lines = [f"Real Gmail Unread Count: {total_unread} unread message(s)\n"]

        if target_ids:
            id_spec = b",".join(target_ids).decode('utf-8')
            st, fetch_data = mail.fetch(id_spec, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
            if st == 'OK' and fetch_data:
                for item in reversed(fetch_data):
                    if isinstance(item, tuple) and len(item) == 2:
                        seq_id = item[0].split()[0].decode('utf-8', errors='ignore') if item[0] else ""
                        m = email.message_from_bytes(item[1])
                        lines.append(f"- [ID: {seq_id}] From: {_decode_mime(m.get('From'))} | Subject: {_decode_mime(m.get('Subject'))}")

        mail.logout()
        return "\n".join(lines)
    except Exception as e:
        return f"Error retrieving unread emails: {str(e)}"


@gmail_mcp_server.resource("gmail://inbox/stats")
def resource_inbox_stats() -> str:
    """Real account telemetry and total inbox count."""
    try:
        user, _ = get_credentials()
        mail = get_imap_connection(timeout=10.0)
        status, data = mail.status("inbox", "(MESSAGES UNSEEN)")
        mail.logout()
        total_emails = "Unknown"
        unseen_emails = "Unknown"
        if status == "OK" and data and data[0]:
            import re
            m_total = re.search(r'MESSAGES\s+(\d+)', data[0].decode('utf-8', errors='ignore'))
            m_unseen = re.search(r'UNSEEN\s+(\d+)', data[0].decode('utf-8', errors='ignore'))
            if m_total:
                total_emails = m_total.group(1)
            if m_unseen:
                unseen_emails = m_unseen.group(1)

        return (
            f"Gmail MCP Server Telemetry:\n"
            f"- Account: {user}\n"
            f"- Total Inbox Emails: {total_emails}\n"
            f"- Unread Emails: {unseen_emails}\n"
            f"- Connection Protocol: IMAP (Port 993) / SMTP (Port 465)"
        )
    except Exception as e:
        return f"Error fetching inbox stats: {str(e)}"


# =====================================================================
# 3. MCP PROMPTS (Pre-configured Templates)
# =====================================================================

@gmail_mcp_server.prompt()
def draft_reply_prompt(message_id: str, tone: str = "professional") -> str:
    """Prompt template for drafting a reply to a Gmail message."""
    return f"Draft a {tone} reply to the email with ID '{message_id}'. Acknowledge the message and keep it clear."


@gmail_mcp_server.prompt()
def summarize_inbox_prompt() -> str:
    """Prompt template for summarizing inbox action items."""
    return "Analyze all unread emails in 'gmail://inbox/unread'. Provide top action items and urgent alerts."


if __name__ == "__main__":
    asyncio.run(gmail_mcp_server.run_stdio_async())
