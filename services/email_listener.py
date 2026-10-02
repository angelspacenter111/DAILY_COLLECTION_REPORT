import asyncio
import email
from email.header import decode_header
import imaplib
import logging
from typing import Any, Dict, List, Optional, Tuple

from config import (
    EMAIL_CHECK_INTERVAL_SECONDS,
    EMAIL_FOLDER,
    EMAIL_HOST,
    EMAIL_MARK_AS_SEEN,
    EMAIL_PASSWORD,
    EMAIL_PORT,
    EMAIL_USER,
    ENABLE_EMAIL_LISTENER,
)
from controllers.master_controller import _parse_pdf_sync
from helpers.database_helper import insert_dcr_report

logger = logging.getLogger("email_listener")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


def decode_mime_header(header_val: Optional[str]) -> str:
    """Decodes MIME encoded headers such as Subject or From."""
    if not header_val:
        return ""
    try:
        decoded_parts = decode_header(header_val)
        fragments = []
        for fragment, charset in decoded_parts:
            if isinstance(fragment, bytes):
                encoding = charset or "utf-8"
                try:
                    fragments.append(fragment.decode(encoding, errors="replace"))
                except Exception:
                    fragments.append(fragment.decode("utf-8", errors="replace"))
            else:
                fragments.append(str(fragment))
        return "".join(fragments).strip()
    except Exception:
        return str(header_val).strip()


def extract_attachment_filename(part) -> Optional[str]:
    """Extracts and decodes filename from an email message part."""
    filename = part.get_filename()
    if filename:
        return decode_mime_header(filename).strip()

    cd = part.get("Content-Disposition")
    if cd:
        for param in cd.split(";"):
            param = param.strip()
            if param.lower().startswith("filename="):
                raw_name = param.split("=", 1)[1].strip(' "')
                return decode_mime_header(raw_name).strip()
    return None


def fetch_unread_pdf_attachments_sync() -> Tuple[List[Dict[str, Any]], int, Optional[str]]:
    """
    Connects to IMAP synchronously, finds UNSEEN emails, extracts PDF attachments,
    marks emails as SEEN to prevent re-processing, and returns (attachments, unread_count, error_msg).
    """
    attachments: List[Dict[str, Any]] = []

    if not EMAIL_USER or not EMAIL_PASSWORD:
        logger.warning("[EMAIL LISTENER] EMAIL_USER or EMAIL_PASSWORD not configured. Skipping check.")
        return attachments, 0, "Email credentials not configured."

    mail = None
    try:
        mail = imaplib.IMAP4_SSL(EMAIL_HOST, EMAIL_PORT)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select(EMAIL_FOLDER)

        status, search_data = mail.search(None, "UNSEEN")
        if status != "OK" or not search_data or not search_data[0]:
            return attachments, 0, None

        msg_ids = search_data[0].split()
        unread_count = len(msg_ids)
        if not msg_ids:
            return attachments, 0, None

        logger.info("[EMAIL LISTENER] Found %d unread email(s). Inspecting for DCR PDFs...", unread_count)

        for msg_id in msg_ids:
            try:
                res, fetch_data = mail.fetch(msg_id, "(RFC822)")
                if res != "OK" or not fetch_data or not fetch_data[0]:
                    continue

                raw_email = fetch_data[0][1]
                msg = email.message_from_bytes(raw_email)
                subject = decode_mime_header(msg.get("Subject", ""))
                from_addr = decode_mime_header(msg.get("From", ""))

                for part in msg.walk():
                    if part.get_content_maintype() == "multipart":
                        continue

                    filename = extract_attachment_filename(part)
                    content_type = part.get_content_type()

                    is_pdf = False
                    if filename and filename.lower().endswith(".pdf"):
                        is_pdf = True
                    elif content_type == "application/pdf":
                        is_pdf = True
                        if not filename:
                            filename = f"dcr_mail_{msg_id.decode('ascii', errors='ignore')}.pdf"

                    if is_pdf and filename:
                        pdf_bytes = part.get_payload(decode=True)
                        if pdf_bytes:
                            attachments.append({
                                "msg_id": msg_id.decode("ascii", errors="ignore"),
                                "filename": filename,
                                "pdf_bytes": pdf_bytes,
                                "sender": from_addr,
                                "subject": subject,
                            })
                            logger.info(
                                "[EMAIL LISTENER] Found PDF attachment: '%s' in email from '%s' (Subject: '%s')",
                                filename, from_addr, subject
                            )

                if EMAIL_MARK_AS_SEEN:
                    # Mark email as read so it isn't repeatedly fetched on next cycle
                    mail.store(msg_id, "+FLAGS", "\\Seen")

            except Exception as e:
                logger.error("[EMAIL LISTENER] Error processing email ID %s: %s", msg_id, e)

        return attachments, unread_count, None

    except imaplib.IMAP4.error as imap_err:
        err_msg = str(imap_err)
        if "AUTHENTICATIONFAILED" in err_msg or "Invalid credentials" in err_msg:
            msg = "Gmail Authentication Failed. Please verify App Password in .env."
            logger.warning("[EMAIL LISTENER] %s", msg)
            return [], 0, msg
        else:
            logger.warning("[EMAIL LISTENER] IMAP error: %s", err_msg)
            return [], 0, f"IMAP error: {err_msg}"

    except Exception as exc:
        logger.warning("[EMAIL LISTENER] Connection / fetch error: %s", exc)
        return [], 0, f"Connection error: {str(exc)}"

    finally:
        if mail:
            try:
                mail.close()
            except Exception:
                pass
            try:
                mail.logout()
            except Exception:
                pass


async def check_emails_and_process() -> Dict[str, Any]:
    """
    Checks for unread emails, parses any DCR PDF attachments, and inserts them into MongoDB.
    Returns a status dictionary suitable for API responses and logging.
    """
    attachments, unread_count, err_msg = await asyncio.to_thread(fetch_unread_pdf_attachments_sync)
    if err_msg:
        return {
            "status": False,
            "success_count": 0,
            "unread_count": unread_count,
            "pdf_count": 0,
            "message": err_msg
        }

    if unread_count == 0:
        return {
            "status": True,
            "success_count": 0,
            "unread_count": 0,
            "pdf_count": 0,
            "message": "No new unread emails found in inbox."
        }

    if not attachments:
        return {
            "status": True,
            "success_count": 0,
            "unread_count": unread_count,
            "pdf_count": 0,
            "message": f"Found {unread_count} unread email(s), but no DCR PDF attachments were attached."
        }

    success_count = 0
    failed_details: List[str] = []
    for item in attachments:
        filename = item["filename"]
        pdf_bytes = item["pdf_bytes"]
        sender = item["sender"]

        try:
            parsed_data, error_reason = await asyncio.to_thread(_parse_pdf_sync, pdf_bytes, filename)
            if not parsed_data:
                logger.warning(
                    "[EMAIL LISTENER] Could not parse DCR from email attachment '%s' (From: %s): %s",
                    filename, sender, error_reason
                )
                failed_details.append(f"{filename}: {error_reason}")
                continue

            report_id = await insert_dcr_report(parsed_data)
            success_count += 1
            logger.info(
                "[EMAIL LISTENER] Successfully imported DCR report from email!\n"
                "  File: %s\n"
                "  Cinema: %s\n"
                "  Date: %s\n"
                "  MongoDB ID: %s",
                filename,
                parsed_data.get("cinema_name"),
                parsed_data.get("date_display"),
                report_id
            )
        except Exception as e:
            logger.exception("[EMAIL LISTENER] Failed to insert DCR report from email '%s': %s", filename, e)
            failed_details.append(f"{filename}: {str(e)}")

    if success_count > 0:
        msg = f"Successfully synced {success_count} DCR report(s) from email."
        if failed_details:
            msg += f" ({len(failed_details)} file(s) failed parsing)."
        return {
            "status": True,
            "success_count": success_count,
            "unread_count": unread_count,
            "pdf_count": len(attachments),
            "message": msg
        }
    else:
        return {
            "status": False,
            "success_count": 0,
            "unread_count": unread_count,
            "pdf_count": len(attachments),
            "message": f"Found {len(attachments)} PDF(s), but none contained valid DCR table data: " + "; ".join(failed_details)
        }


async def run_email_listener_loop():
    """Background task loop that periodically checks for incoming DCR emails."""
    logger.info(
        "[EMAIL LISTENER] Starting background listener loop (checking %s every %d seconds)...",
        EMAIL_USER, EMAIL_CHECK_INTERVAL_SECONDS
    )
    while True:
        try:
            await check_emails_and_process()
        except asyncio.CancelledError:
            logger.info("[EMAIL LISTENER] Background task received cancellation signal. Stopping.")
            break
        except Exception as e:
            logger.error("[EMAIL LISTENER] Error during cycle: %s", e)

        try:
            await asyncio.sleep(EMAIL_CHECK_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            logger.info("[EMAIL LISTENER] Sleep interrupted by cancellation. Stopping.")
            break


def main():
    """Standalone entry point to run email listener in a separate process/terminal."""
    print("=" * 80)
    print(" DCR AUTOMATED EMAIL LISTENER (STANDALONE RUNNER)")
    print(f" Account: {EMAIL_USER}")
    print(f" Poll Interval: {EMAIL_CHECK_INTERVAL_SECONDS}s")
    print("=" * 80)
    try:
        asyncio.run(run_email_listener_loop())
    except KeyboardInterrupt:
        print("\nEmail listener stopped by user.")


if __name__ == "__main__":
    main()
