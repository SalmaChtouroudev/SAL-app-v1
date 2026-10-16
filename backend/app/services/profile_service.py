from __future__ import annotations

from app.core.security import hash_password, verify_password
from app.repositories.platform_repository import PlatformRepository
from app.schemas.common import ApiMessage
from app.schemas.platform import (
    AuditLogCreate,
    CurrentUserPasswordUpdate,
    CurrentUserProfileRead,
    CurrentUserProfileUpdate,
    UserActivitySummaryRead,
)


class ProfileService:
    def __init__(self, repository: PlatformRepository) -> None:
        self.repository = repository

    def get_profile(self, user_id: str) -> CurrentUserProfileRead:
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise ValueError("Unknown current user.")

        company = self.repository.get_company(user.enterprise_id)
        if company is None:
            raise ValueError("Unknown company for current user.")

        import_batches = [
            batch
            for batch in self.repository.list_import_batches(user.enterprise_id)
            if batch.uploadedBy == user_id
        ]
        report_exports = [
            export
            for export in self.repository.list_report_exports(user.enterprise_id)
            if export.requestedBy == user_id
        ]
        audit_logs = [
            entry
            for entry in self.repository.list_audit_logs(user.enterprise_id)
            if entry.userId == user_id
        ]

        return CurrentUserProfileRead(
            userId=user.user_id,
            enterpriseId=user.enterprise_id,
            email=user.email,
            fullName=user.full_name,
            title=user.title,
            roleType=user.role_type,
            status=user.status,
            companyName=company.name,
            accountCreatedDate=user.created_at or company.lastSyncAt,
            lastLoginAt=user.last_login_at,
            avatarUrl=user.avatar_url,
            activitySummary=UserActivitySummaryRead(
                totalImports=len(import_batches),
                lastImportDate=import_batches[0].createdAt if import_batches else None,
                totalReportsGenerated=len(report_exports),
                lastActivity=audit_logs[0].occurredAt if audit_logs else None,
            ),
        )

    def update_profile(
        self, user_id: str, payload: CurrentUserProfileUpdate
    ) -> CurrentUserProfileRead:
        updated_user = self.repository.update_current_user_profile(user_id, payload)
        if updated_user is None:
            raise ValueError("Unknown current user.")

        self.repository.create_audit_log(
            AuditLogCreate(
                enterpriseId=updated_user.enterprise_id,
                userId=updated_user.user_id,
                actionType="PROFILE_UPDATED",
                status="SUCCESS",
                description="User profile updated from the account center.",
            )
        )
        return self.get_profile(user_id)

    def change_password(self, user_id: str, payload: CurrentUserPasswordUpdate) -> ApiMessage:
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise ValueError("Unknown current user.")

        if not verify_password(payload.currentPassword, user.password_hash):
            raise ValueError("Current password is invalid.")

        if payload.currentPassword == payload.newPassword:
            raise ValueError("New password must be different from the current password.")

        self.repository.update_user_password(user_id, hash_password(payload.newPassword))
        self.repository.create_audit_log(
            AuditLogCreate(
                enterpriseId=user.enterprise_id,
                userId=user.user_id,
                actionType="PASSWORD_UPDATED",
                status="SUCCESS",
                description="User password changed from the account center.",
            )
        )
        return ApiMessage(status="UPDATED", message="Password updated successfully.")
