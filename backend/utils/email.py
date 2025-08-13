import os
import resend

# initialize with your API key
resend.api_key = os.environ["RESEND_API_KEY"]
login_url = os.environ["FRONT_END_URL"] + "/login"

def send_registration_email(to_email: str, username: str, otp_code: str) -> None:

    html = f"""\
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <title>One-Time Password</title>
    <style>
      * {{
        box-sizing: border-box;
        -webkit-font-smoothing: antialiased;
      }}
      body {{
        margin: 0;
        padding: 0;
        background: #f1f5f9;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        color: #374151;
      }}
      table.wrapper {{ width: 100%; border-collapse: collapse; }}
      td.container {{
        width: 100%;
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 8px 18px rgba(0,0,0,0.06);
      }}
      .header {{
        background: linear-gradient(135deg,#0052cc 0%,#6c63ff 100%);
        color: #ffffff;
        text-align: center;
        padding: 32px 20px;
      }}
      h1 {{ margin: 0; font-size: 24px; font-weight: 600; }}
      .content {{ padding: 32px; font-size: 16px; line-height: 1.6; }}
      .otp-code {{
        display: inline-block;
        padding: 18px 28px;
        font-size: 32px;
        font-weight: 700;
        letter-spacing: 10px;
        color: #1e40af;
        background: #eef2ff;
        border: 2px solid #c7d2fe;
        border-radius: 12px;
        box-shadow: inset 0 0 1px rgba(0,0,0,0.08), 0 4px 10px rgba(99,102,241,0.15);
        margin: 24px auto;
      }}
      .footer {{
        padding: 28px 20px;
        text-align: center;
        font-size: 13px;
        color: #6b7280;
        background: #f9fafb;
      }}
      @media only screen and (max-width: 620px) {{
        .content {{ padding: 24px; }}
        h1 {{ font-size: 22px; }}
        .otp-code {{ font-size: 24px; letter-spacing: 6px; }}
      }}
    </style>
    </head>
    <body>
      <table role="presentation" class="wrapper">
        <tr>
          <td align="center">
            <table role="presentation" class="container">
              <tr><td class="header"><h1>Welcome&nbsp;to&nbsp;IoT&nbsp;Smart&nbsp;Door</h1></td></tr>
              <tr>
                <td class="content">
                  <p>Hello <strong>{username}</strong>,</p>
                  <p>Use the one-time password below to finish creating your account:</p>
                  <p style="text-align:center;">
                    <span class="otp-code">{otp_code}</span>
                  </p>
                  <p>This code expires in 10&nbsp;minutes. If you didn’t request it, just ignore this message.</p>
                </td>
              </tr>
              <tr><td class="footer">&copy; IOT, Nhóm 8 - 23CLC03</td></tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    params: resend.Emails.SendParams = {
        "from": "IOT Smart Door <Nhom8_23CLC03@obiwan.io.vn>",
        "to": [to_email],
        "subject": "Registration OTP",
        "html": html,
    }
    resend.Emails.send(params)
    
def send_fingerprint_action_email(to_email: str, username: str, action: str) -> None:
    subject = f"Smart Door Notification: Fingerprint {action} Success!"
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8" />
    <title>Smart Door Notification</title>
    <style>
        * {{
        box-sizing: border-box;
        -webkit-font-smoothing: antialiased;
        }}
        body {{
        margin: 0;
        padding: 0;
        background: #f1f5f9;
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        color: #374151;
        }}
        table.wrapper {{ width: 100%; border-collapse: collapse; }}
        td.container {{
        width: 100%;
        max-width: 600px;
        margin: 40px auto;
        background: #ffffff;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 8px 18px rgba(0,0,0,0.06);
        }}
        .header {{
        background: linear-gradient(135deg,#0052cc 0%,#6c63ff 100%);
        color: #ffffff;
        padding: 20px;
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        }}
        .content {{
        padding: 30px;
        line-height: 1.6;
        }}
        .footer {{
        padding: 20px;
        text-align: center;
        font-size: 13px;
        color: #6b7280;
        background: #f9fafb;
        }}
        @media only screen and (max-width: 620px) {{
        .content {{ padding: 24px; }}
        h1 {{ font-size: 22px; }}
        }}
    </style>
    </head>
    <body>
        <table role="presentation" class="wrapper">
            <tr>
            <td align="center">
                <table role="presentation" class="container">
                <tr><td class="header">Smart Door Notification</td></tr>
                <tr>
                    <td class="content">
                    <p>Hello <strong>{username}</strong>,</p>
                    <p>A fingerprint has been successfully <strong>{action}</strong> from your Smart Door system.</p>
                    <p>If you did not initiate this action, please contact support immediately.</p>
                    </td>
                </tr>
                <tr><td class="footer">&copy; IOT, Nhóm 8 - 23CLC03</td></tr>
                </table>
            </td>
            </tr>
        </table>
    </body>
    </html>
    """
    params: resend.Emails.SendParams = {
        "from": "IOT Smart Door <Nhom8_23CLC03@obiwan.io.vn>",
        "to": [to_email],
        "subject": subject,
        "html": html_content,
    }
    resend.Emails.send(params)