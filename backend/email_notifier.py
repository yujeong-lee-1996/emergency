import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class EmailNotifier:
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_pass = os.getenv('SMTP_PASS')
        self.alert_email = os.getenv('ALERT_EMAIL')

    def send_emergency_alert(self, job_id, scores, timestamp=None):
        """119 호출 상황 시 긴급 메일 발송"""
        if not all([self.smtp_user, self.smtp_pass, self.alert_email]):
            print("⚠️ 이메일 설정이 완료되지 않았습니다.")
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.smtp_user
            msg['To'] = self.alert_email
            msg['Subject'] = f"🚨 [긴급] 화재 감지 알림 - Job {job_id}"

            html_body = f"""
            <html>
            <body>
                <h2 style="color: #ff3333;">🚨 긴급 화재 감지 알림</h2>
                <p><strong>발생 시간:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>작업 ID:</strong> {job_id}</p>
                <p><strong>영상 시점:</strong> {timestamp or 'N/A'}초</p>

                <h3>감지 점수:</h3>
                <ul>
                    <li>🔥 <strong>화재:</strong> {scores.get('fire', 0)*100:.1f}%</li>
                    <li>💨 <strong>연기:</strong> {scores.get('smoke', 0)*100:.1f}%</li>
                    <li>⚠️ <strong>위험도:</strong> {scores.get('hazard', 0)*100:.1f}%</li>
                </ul>

                <p style="color: #ff3333; font-weight: bold;">
                    즉시 119에 신고하고 안전한 곳으로 대피하세요!
                </p>

                <hr>
                <p style="font-size: 12px; color: #666;">
                    이 알림은 안전 감지 자동화 시스템에서 발송되었습니다.
                </p>
            </body>
            </html>
            """

            msg.attach(MIMEText(html_body, 'html', 'utf-8'))

            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_pass)
                text = msg.as_string()
                server.sendmail(self.smtp_user, self.alert_email, text)

            print(f"✅ 긴급 알림 메일 발송 완료: {self.alert_email}")
            return True

        except Exception as e:
            print(f"❌ 메일 발송 실패: {e}")
            return False

# 사용 예시
if __name__ == "__main__":
    notifier = EmailNotifier()
    test_scores = {'fire': 0.65, 'smoke': 0.45, 'hazard': 0.87}
    notifier.send_emergency_alert("test123", test_scores, 45.2)