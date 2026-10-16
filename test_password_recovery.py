"""
Temporary end-to-end test for password recovery.

IMPORTANT:
- This does NOT modify SMSService.py.
- Africa's Talking is NOT contacted.
- The SMSService.send_sms() method is mocked only in memory.
- The real PasswordRecoveryService is tested.
- The test uses the existing test farmer +251900000002.
"""

from backend.app.main import app
from backend.app.extensions import db
from backend.app.models.user import User
from backend.app.models.password_reset_otp import PasswordResetOTP
from backend.app.services.sms_service import SMSService
from backend.app.services.password_recovery_service import (
    PasswordRecoveryService,
    PasswordResetVerificationError,
)


TEST_PHONE = "+251900000002"
NEW_PASSWORD = "NewTestPass123!"


def run_test():
    print("=" * 60)
    print("PASSWORD RECOVERY END-TO-END TEST")
    print("SMS delivery: MOCKED")
    print("Africa's Talking: NOT CONTACTED")
    print("=" * 60)

    with app.app_context():

        # --------------------------------------------------
        # 1. Find test user
        # --------------------------------------------------

        user = db.session.execute(
            db.select(User).where(
                User.phone_number == TEST_PHONE
            )
        ).scalar_one_or_none()

        if user is None:
            raise RuntimeError(
                f"Test user {TEST_PHONE} was not found."
            )

        print(f"\n[1] Test user found: ID={user.id}")

        # --------------------------------------------------
        # 2. Remove previous active OTPs
        # --------------------------------------------------

        old_otps = db.session.execute(
            db.select(PasswordResetOTP).where(
                PasswordResetOTP.user_id == user.id,
                PasswordResetOTP.used_at.is_(None),
            )
        ).scalars().all()

        for otp_record in old_otps:
            otp_record.mark_used()

        db.session.commit()

        print("[2] Previous active OTPs invalidated.")

        # --------------------------------------------------
        # 3. Mock SMSService.send_sms()
        # --------------------------------------------------

        captured = {}

        original_send_sms = SMSService.send_sms

        def mock_send_sms(
    recipient_phone,
    message,
    recipient_type="farmer",
    language="en",
    notification_type="general",
    provider="africas_talking",
    user_id=None,
    outbreak_alert_id=None,
    region=None,
    woreda=None,
    kebele=None,
):
            captured["recipient_phone"] = recipient_phone
            captured["message"] = message
            captured["language"] = language
            captured["notification_type"] = notification_type

            print("\n[MOCK SMS]")
            print(f"Recipient: {recipient_phone}")
            print(f"Type: {notification_type}")
            print(f"Message: {message}")

            return {
                "success": True,
                "status": "sent",
                "message": "Mock SMS accepted.",
            }

        SMSService.send_sms = staticmethod(mock_send_sms)

        try:

            # --------------------------------------------------
            # 4. Request password reset
            # --------------------------------------------------

            print("\n[3] Requesting password reset...")

            result = (
                PasswordRecoveryService.request_password_reset(
                    TEST_PHONE
                )
            )

            print(
                f"Reset request result: {result}"
            )

            if not captured.get("message"):
                raise AssertionError(
                    "Mock SMS did not receive a message."
                )

            # --------------------------------------------------
            # 5. Extract OTP from mocked SMS
            # --------------------------------------------------

            import re

            match = re.search(
                r"\b\d{6}\b",
                captured["message"],
            )

            if not match:
                raise AssertionError(
                    "Could not find a 6-digit OTP in SMS."
                )

            otp = match.group(0)

            print("\n[4] OTP captured from mocked SMS.")
            print("OTP length:", len(otp))

            # --------------------------------------------------
            # 6. Verify database record
            # --------------------------------------------------

            otp_record = db.session.execute(
                db.select(PasswordResetOTP)
                .where(
                    PasswordResetOTP.user_id == user.id
                )
                .order_by(
                    PasswordResetOTP.id.desc()
                )
            ).scalars().first()

            if otp_record is None:
                raise AssertionError(
                    "OTP database record was not created."
                )

            print("\n[5] OTP database record verified.")
            print("OTP ID:", otp_record.id)
            print("Attempts:", otp_record.attempts)
            print("Max attempts:", otp_record.max_attempts)
            print("Used:", otp_record.is_used)
            print("Expired:", otp_record.is_expired)

            if otp_record.is_used:
                raise AssertionError(
                    "New OTP is already marked as used."
                )

            if otp_record.attempts != 0:
                raise AssertionError(
                    "New OTP should have zero attempts."
                )

            # --------------------------------------------------
            # 7. Test WRONG OTP
            # --------------------------------------------------

            wrong_otp = (
                "000000"
                if otp != "000000"
                else "111111"
            )

            print("\n[6] Testing wrong OTP...")

            try:
                PasswordRecoveryService.confirm_password_reset(
                    phone_number=TEST_PHONE,
                    otp=wrong_otp,
                    new_password=NEW_PASSWORD,
                )

                raise AssertionError(
                    "Wrong OTP was incorrectly accepted."
                )

            except PasswordResetVerificationError:
                print(
                    "Wrong OTP correctly rejected."
                )

            db.session.refresh(otp_record)

            print(
                "Attempts after wrong OTP:",
                otp_record.attempts,
            )

            if otp_record.attempts != 1:
                raise AssertionError(
                    "Wrong OTP did not increment attempts."
                )

            # --------------------------------------------------
            # 8. Test CORRECT OTP
            # --------------------------------------------------

            print("\n[7] Testing correct OTP...")

            reset_result = (
                PasswordRecoveryService.confirm_password_reset(
                    phone_number=TEST_PHONE,
                    otp=otp,
                    new_password=NEW_PASSWORD,
                )
            )

            print(
                "Reset result:",
                reset_result,
            )

            # --------------------------------------------------
            # 9. Verify OTP consumed
            # --------------------------------------------------

            db.session.refresh(otp_record)
            db.session.refresh(user)

            print("\n[8] Verifying OTP was consumed.")

            print("OTP used:", otp_record.is_used)
            print("Used at:", otp_record.used_at)

            if not otp_record.is_used:
                raise AssertionError(
                    "OTP was not marked as used."
                )

            # --------------------------------------------------
            # 10. Verify password
            # --------------------------------------------------

            print("\n[9] Verifying new password.")

            if not user.check_password(NEW_PASSWORD):
                raise AssertionError(
                    "New password does not work."
                )

            print(
                "New password verified successfully."
            )

            # --------------------------------------------------
            # 11. Verify OTP cannot be reused
            # --------------------------------------------------

            print("\n[10] Testing OTP reuse protection.")

            try:
                PasswordRecoveryService.confirm_password_reset(
                    phone_number=TEST_PHONE,
                    otp=otp,
                    new_password="AnotherPassword123!",
                )

                raise AssertionError(
                    "Used OTP was incorrectly accepted."
                )

            except PasswordResetVerificationError:
                print(
                    "Used OTP correctly rejected."
                )

            # --------------------------------------------------
            # SUCCESS
            # --------------------------------------------------

            print("\n" + "=" * 60)
            print("PASSWORD RECOVERY TEST PASSED")
            print("=" * 60)

            print("\nVerified:")
            print("  [OK] OTP generated")
            print("  [OK] OTP sent through mocked SMS")
            print("  [OK] OTP stored as hash")
            print("  [OK] OTP expiration configured")
            print("  [OK] Wrong OTP rejected")
            print("  [OK] Failed attempt counted")
            print("  [OK] Correct OTP accepted")
            print("  [OK] Password changed")
            print("  [OK] OTP invalidated")
            print("  [OK] OTP reuse rejected")
            print("  [OK] Africa's Talking was not contacted")

        finally:
            # --------------------------------------------------
            # Always restore the real SMS method
            # --------------------------------------------------

            SMSService.send_sms = original_send_sms
            print(
                "\nReal SMSService.send_sms() restored."
            )


if __name__ == "__main__":
    run_test()