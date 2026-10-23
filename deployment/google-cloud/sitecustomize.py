"""Early process hook for held VM services; inert outside that profile."""
import os


if os.environ.get("AUREON_CLOUD_CREDENTIAL_ISOLATION") == "1":
    from cloud_credential_boundary import install_cloud_environment_guard

    install_cloud_environment_guard()
