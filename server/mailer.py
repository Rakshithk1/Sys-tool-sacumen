import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime

def send_alert_email(config, alert_type, current_value):
    sender_email = config.get("sender_email")
    receiver_email = config.get("receiver_email")
    app_password = config.get("app_password")
    
    if not sender_email or not receiver_email or not app_password:
        return False, "Missing email configuration"

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = f"⚠️ SysTool Alert: {alert_type}"

        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        body = f"""
        Monitoring Alert Triggered
        
        Alert Type: {alert_type}
        Current Value: {current_value}
        Time: {time_str}
        
        This is an automated message from SysTool 1.0.
        """
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, app_password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
