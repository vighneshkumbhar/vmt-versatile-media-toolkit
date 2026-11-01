def get_recommended_version(extension):
    from app.models.extension_version import VerificationStatus
    
    verified_versions = [v for v in extension.versions if v.verification_status == VerificationStatus.VERIFIED]
    if verified_versions:
        return max(verified_versions, key=lambda v: v.created_at)
        
    unverified_versions = [v for v in extension.versions if v.verification_status == VerificationStatus.UNVERIFIED]
    if unverified_versions:
        return max(unverified_versions, key=lambda v: v.created_at)
        
    return None
