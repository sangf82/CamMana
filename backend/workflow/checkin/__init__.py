"""Checkin Workflow Module

API routes and business logic for vehicle check-in process.
"""
from backend.workflow.checkin.api import checkin_router
from backend.workflow.checkin.logic import CheckInService, CheckInResult, get_checkin_service

__all__ = ['checkin_router', 'CheckInService', 'CheckInResult', 'get_checkin_service']
