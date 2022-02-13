import smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import config

sending_email = "kamil.radzimowski02@gmail.com"
p_word = config.EMAIL_PASSWORD
templates_folder_dir = "C:\\Users\\kradz\\AppData\\Roaming\\Code\\User\\workspaceStorage" \
                       "\\5f1a6f905f974b503775b1e93fcd3d8c\\redhat.java\\jdt_ws\\mario-9_dabcd7df\\bin" \
                       "\\messengerServer\\templates\\ "


def send_email_create_account(reciving_email):
    context = ssl.create_default_context()
    message = MIMEMultipart("alternative")
    message['Subject'] = "Messenger account created"
    message['From'] = sending_email
    message['To'] = reciving_email
    html = open(templates_folder_dir + "message_create_account.html", "r")
    text = """
    Hello, you have created an account on the Messenger app. If it's not you contact us immediately at contact@messenger.com.
    """
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html.read(), "html")
    message.attach(part1)
    message.attach(part2)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sending_email, p_word)
        server.sendmail(sending_email, reciving_email, message.as_string())
