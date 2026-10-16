"""
=========================================================
Database Models
=========================================================
"""

from backend.app.models.user import User
from backend.app.models.diagnosis_record import DiagnosisRecord
from backend.app.models.advisory_record import AdvisoryRecord
from backend.app.models.extension_comment import ExtensionComment
from backend.app.models.extension_agent import ExtensionAgent
from backend.app.models.farmer_profile import FarmerProfile
from backend.app.models.sms_record import SMSRecord
from backend.app.models.outbreak_alert import OutbreakAlert
from backend.app.models.password_reset_otp import PasswordResetOTP
from backend.app.models.discussion_post import DiscussionPost
from backend.app.models.discussion_reply import DiscussionReply
from backend.app.models.discussion_post_like import DiscussionPostLike
from backend.app.models.offline_sync_record import OfflineSyncRecord
from backend.app.models.pending_registration import PendingRegistration
__all__ = [
    "User",
    "DiagnosisRecord",
    "AdvisoryRecord",
    "ExtensionComment",
    "ExtensionAgent",
    "FarmerProfile",
    "SMSRecord",
    "OutbreakAlert",
    "PasswordResetOTP",
    "DiscussionPost",
    "DiscussionReply",
    "DiscussionPostLike",
    "OfflineSyncRecord",
    "PendingRegistration",
]
