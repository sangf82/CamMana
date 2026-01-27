"""
CI/CD Package

Automated testing and health checks for CamMana backend.
Includes package validation, model checks, API testing, and more.
"""

from backend.ci_cd.runner import run_all_checks, CheckResult

__all__ = ['run_all_checks', 'CheckResult']
