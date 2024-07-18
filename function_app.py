import logging
import azure.functions as func
import imaplib
import email
from email.header import decode_header
from exchangelib import Credentials, Account, Message, Folder

app = func.FunctionApp()

@app.schedule(schedule="0 * * * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')
    
    pidevmail()
    
    logging.info('Python timer trigger function executed.')

def pidevmail():
    gmx_username = "your_gmx_username"
    gmx_password = "your_gmx_password"
    outlook_username = "your_outlook_username"
    outlook_password = "your_outlook_password"
    
    email_id, msg = get_oldest_email_from_gmx(gmx_username, gmx_password)
    if msg:
        copy_email_to_outlook(msg, outlook_username, outlook_password)
        delete_email_from_gmx(gmx_username, gmx_password, email_id)
        logging.info('Email transferred from GMX to Outlook and deleted from GMX.')

def get_oldest_email_from_gmx(username, password):
    mail = imaplib.IMAP4_SSL("imap.gmx.com")
    mail.login(username, password)
    mail.select("inbox")
    result, data = mail.search(None, "ALL")
    email_ids = data[0].split()
    if not email_ids:
        logging.info('No emails found in GMX inbox.')
        return None, None
    oldest_email_id = email_ids[0]
    result, msg_data = mail.fetch(oldest_email_id, "(RFC822)")
    raw_email = msg_data[0][1]
    msg = email.message_from_bytes(raw_email)
    mail.logout()
    return oldest_email_id, msg

def copy_email_to_outlook(msg, outlook_username, outlook_password):
    credentials = Credentials(username=outlook_username, password=outlook_password)
    account = Account(outlook_username, credentials=credentials, autodiscover=True)
    gmx_folder = None
    for folder in account.inbox.children:
        if folder.name == "GMX":
            gmx_folder = folder
            break
    if gmx_folder is None:
        gmx_folder = Folder(parent=account.inbox, name="GMX")
        gmx_folder.save()
    new_msg = Message(
        account=account,
        folder=gmx_folder,
        subject=msg['subject'],
        body=msg.get_payload(decode=True),
        to_recipients=[outlook_username]
    )
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart' or part.get('Content-Disposition') is None:
            continue
        new_msg.attach(part.get_filename(), part.get_payload(decode=True))
    new_msg.save()
    new_msg.send()

def delete_email_from_gmx(username, password, email_id):
    mail = imaplib.IMAP4_SSL("imap.gmx.com")
    mail.login(username, password)
    mail.select("inbox")
    mail.store(email_id, '+FLAGS', '\\Deleted')
    mail.expunge()
    mail.logout()