
import email, smtplib, ssl
import json
from providers import PROVIDERS
import tkinter as tk
from tkinter import filedialog
from email.mime.image import MIMEImage
import time
from tkinter import ttk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os.path import basename
import imaplib
import email
import json
import re

import threading


def update_opt_out_list(number):
    # Load existing opt-out list
    with open('opt_out_list.json', 'r') as file:
        opt_out_list = json.load(file)

    # Add the new number
    opt_out_list.append(number)

    # Write back to the file
    with open('opt_out_list.json', 'w') as file:
        json.dump(opt_out_list, file)


def process_opt_out_emails():

        # Load config.json
    with open('config.json', 'r') as file:
        config = json.load(file)


    # Connect to Gmail
    server = imaplib.IMAP4_SSL('imap.gmail.com')
    server.login(config["email"], config["password"])

    # Select the inbox
    server.select('inbox')

    # Search for all unread messages
    result, data = server.search(None, '(UNSEEN)')
    email_ids = data[0].split()

    for e_id in email_ids:
        # Fetch the email
        result, data = server.fetch(e_id, '(RFC822)')
        raw_email = data[0][1]

        # Parse the email
        email_message = email.message_from_bytes(raw_email)
        subject = email_message['subject']
        from_email = email_message['from']
        body = email_message.get_payload(decode=True).decode()
    #    print(body)  
        # Check if the body contains the word "STOP"
        if "STOP" in body:
            # Extract the phone number from the sender's email address
            match = re.search(r'(\d+)@', from_email)
            if match:
                phone_number = match.group(1)
                update_opt_out_list(phone_number)

    # Close the connection
    server.logout()


process_opt_out_emails()     # Call this function periodically, or run it on a schedule


def send_sms_via_email(
    number: str,
    message: str,
    provider: str,
    sender_credentials: tuple,
    subject: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):
    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("sms")}'

    email_message = MIMEText(message, "plain") # Only include the message, not the subject
    email_message["Subject"] = subject
    # Omitting the "From" field
    email_message["To"] = receiver_email

    text = email_message.as_string()

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, text)


def send_mms_via_email(
    number: str,
    message: str,
    file_path: str,
    mime_maintype: str,
    mime_subtype: str,
    provider: str,
    sender_credentials: tuple,
    subject: str,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 465,
):

    sender_email, email_password = sender_credentials
    receiver_email = f'{number}@{PROVIDERS.get(provider).get("mms")}'

    email_message=MIMEMultipart()
    email_message["Subject"] = subject
    email_message["From"] = sender_email
    email_message["To"] = receiver_email

    email_message.attach(MIMEText(message, "plain"))

    with open(file_path, "rb") as attachment:
        image_data = attachment.read()
        part = MIMEImage(image_data, mime_subtype)

        part.add_header(
            "Content-Disposition",
            f"attachment; filename={basename(file_path)}",
        )

        email_message.attach(part)

    text = email_message.as_string()

    with smtplib.SMTP_SSL(
        smtp_server, smtp_port, context=ssl.create_default_context()
    ) as email:
        email.login(sender_email, email_password)
        email.sendmail(sender_email, receiver_email, text)


def send_all_messages(subject, description, file_path):

    process_opt_out_emails()
    # Load existing opt-out list
    with open('opt_out_list.json', 'r') as file:
        opt_out_list = json.load(file)

    # List of tuples containing phone numbers and corresponding carriers
    numbers_and_providers = [
        # ... other numbers
    ]

        # Set the maximum value for the progress bar to the total number of recipients
    progress_bar['maximum'] = len(numbers_and_providers)

    message = description + "\nReply \"STOP\" to opt out of more messages"  # Added opt-out notice

    # Load config.json
    with open('config.json', 'r') as file:
        config = json.load(file)

    sender_credentials = (config["email"], config["password"])

    # MMS
    mime_maintype = "image"
    mime_subtype = "png"

    # Loop through the numbers and carriers
    for number, provider in numbers_and_providers:
        # Check if the number is in the opt-out list
        if number not in opt_out_list:
            try:
                                # Update progress bar
                progress_bar['value'] += 1
                root.update_idletasks()  # Force update of GUI

                # Update log text
                log_message = f"Sent to {number}\n"
                log_text.insert(tk.END, log_message)
                log_text.see(tk.END)  # Scroll to the end
                if file_path:  # If an image is selected
                    # MMS
                    send_mms_via_email(
                        number,
                        message,
                        file_path,
                        mime_maintype,
                        mime_subtype,
                        provider,
                        sender_credentials,
                        subject
                    )
                else:  # If no image is selected
                    # SMS
                    send_sms_via_email(number, message, provider, sender_credentials, subject)
            except Exception as e:
                print(f"Error sending to {number}: {e}")

            time.sleep(5)


def select_image():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.gif")])
    image_path_label.config(text=file_path)
    return file_path


def send_messages():
    subject = subject_entry.get()
    description = description_text.get("1.0", tk.END)
    file_path = image_path_label.cget("text")  # Get the selected image file path
    send_thread = threading.Thread(target=send_all_messages, args=(subject, description, file_path))
    send_thread.start()
    print("Messages sent!")


# GUI code
root = tk.Tk()
root.title("Message Sender")

# Create frames to organize the widgets
subject_frame = tk.Frame(root)
subject_frame.pack(padx=10, pady=5)
image_frame = tk.Frame(root)
image_frame.pack(padx=10, pady=5)
description_frame = tk.Frame(root)
description_frame.pack(padx=10, pady=5)

# Title field
subject_label = tk.Label(subject_frame, text="subject:")
subject_label.grid(row=0, column=0)
subject_entry = tk.Entry(subject_frame)
subject_entry.grid(row=0, column=1)

# Image selection button
select_image_button = tk.Button(image_frame, text="Select Image", command=select_image)
select_image_button.grid(row=0, column=0)
image_path_label = tk.Label(image_frame, text="")
image_path_label.grid(row=0, column=1)

# Description field
description_label = tk.Label(description_frame, text="Description:")
description_label.grid(row=0, column=0)
description_text = tk.Text(description_frame, height=10, width=40)
description_text.grid(row=1, column=0)

# Send button
send_button = tk.Button(root, text="Send", command=send_messages)
send_button.pack(padx=10, pady=20)

# Progress bar
progress_bar = ttk.Progressbar(root, orient="horizontal", length=200, mode="determinate")
progress_bar.pack(padx=10, pady=5)
log_text = tk.Text(root, height=5, width=40)
log_text.pack(padx=10, pady=5)


root.mainloop()
