"""
CI/CD Runner - Main entry point for health checks

Runs all checks and provides unified results.
"""

import logging
import sys
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    """Result of a health check."""
    name: str
    success: bool
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


def run_all_checks(
    auto_fix: bool = False,
    skip_cameras: bool = False,
    skip_api: bool = False
) -> Dict[str, Any]:
    """
    Run all health checks.
    
    Args:
        auto_fix: If True, attempt to fix issues (install packages, download models)
        skip_cameras: Skip camera connectivity checks (faster for offline testing)
        skip_api: Skip external API checks
        
    Returns:
        Comprehensive check results
    """
    results = []
    overall_success = True
    
    print("=" * 60)
    print("CamMana CI/CD Health Check")
    print("=" * 60)
    
    # 1. Package Check
    print("\n[1/5] Checking packages...")
    try:
        from backend.ci_cd.package_check import run_package_check
        pkg_result = run_package_check(auto_install=auto_fix)
        results.append(CheckResult(
            name="packages",
            success=pkg_result["success"],
            details=pkg_result
        ))
        if not pkg_result["success"]:
            overall_success = False
            print(f"  ❌ Missing packages: {pkg_result['missing']}")
        else:
            print("  ✅ All packages installed")
    except Exception as e:
        logger.error(f"Package check failed: {e}")
        results.append(CheckResult(name="packages", success=False, error=str(e)))
        overall_success = False
        print(f"  ❌ Package check error: {e}")
    
    # 2. Model Check
    print("\n[2/5] Checking AI models...")
    try:
        from backend.ci_cd.model_check import run_model_check
        model_result = run_model_check(auto_download=auto_fix)
        results.append(CheckResult(
            name="models",
            success=model_result["success"],
            details=model_result
        ))
        if not model_result["success"]:
            overall_success = False
            print(f"  ❌ Missing models: {model_result['missing']}")
        else:
            print("  ✅ All models available")
    except Exception as e:
        logger.error(f"Model check failed: {e}")
        results.append(CheckResult(name="models", success=False, error=str(e)))
        overall_success = False
        print(f"  ❌ Model check error: {e}")
    
    # 3. Data Check
    print("\n[3/5] Checking data storage...")
    try:
        from backend.ci_cd.data_check import run_data_check
        data_result = run_data_check()
        results.append(CheckResult(
            name="data",
            success=data_result["success"],
            details=data_result
        ))
        if not data_result["success"]:
            overall_success = False
            print("  ❌ Data storage issues detected")
        else:
            print("  ✅ Data storage OK")
    except Exception as e:
        logger.error(f"Data check failed: {e}")
        results.append(CheckResult(name="data", success=False, error=str(e)))
        overall_success = False
        print(f"  ❌ Data check error: {e}")
    
    # 4. External API Check
    if not skip_api:
        print("\n[4/5] Checking external APIs...")
        try:
            from backend.ci_cd.api_check import run_api_check
            api_result = run_api_check()
            results.append(CheckResult(
                name="external_apis",
                success=api_result["success"],
                details=api_result
            ))
            
            # Show details for each API
            for detail in api_result.get("details", []):
                name = detail.get("name", "Unknown")
                status = detail.get("status_code")
                time_ms = detail.get("response_time_ms")
                error = detail.get("error")
                resp_data = detail.get("response_data")
                
                if detail.get("reachable") and status == 200:
                    # Show brief response data for some endpoints
                    extra = ""
                    if resp_data:
                        if "plates" in resp_data:
                            extra = f" -> plates: {resp_data['plates']}"
                        elif "wheel_count" in resp_data:
                            extra = f" -> wheels: {resp_data['wheel_count']}"
                        elif "detections" in resp_data and "color" in str(resp_data):
                            colors = [d.get("color") for d in resp_data.get("detections", []) if d.get("color")]
                            if colors:
                                extra = f" -> colors: {colors}"
                        elif "volume" in resp_data:
                            extra = f" -> volume: {resp_data['volume']} m³"
                    print(f"  ✅ {name}: HTTP {status} ({time_ms}ms){extra}")
                elif status:
                    print(f"  ❌ {name}: HTTP {status} - {error}")
                else:
                    print(f"  ⚠️ {name}: {error}")
            
            if api_result["success"]:
                print("  ✅ All external APIs reachable (HTTP 200)")
            else:
                print("  ⚠️ Some external APIs failed (app may still work)")
        except Exception as e:
            logger.error(f"API check failed: {e}")
            results.append(CheckResult(name="external_apis", success=False, error=str(e)))
            print(f"  ⚠️ API check error: {e}")
    else:
        print("\n[4/5] Skipping external API check")
        results.append(CheckResult(name="external_apis", success=True, details={"skipped": True}))
    
    # 5. Camera Check
    if not skip_cameras:
        print("\n[5/5] Checking camera connectivity...")
        try:
            from backend.ci_cd.camera_check import run_camera_check
            cam_result = run_camera_check()
            results.append(CheckResult(
                name="cameras",
                success=cam_result["success"],
                details=cam_result
            ))
            connected = cam_result.get("connected", 0)
            total = cam_result.get("total_cameras", 0)
            if total == 0:
                print("  ℹ️ No cameras configured")
            elif connected > 0:
                print(f"  ✅ {connected}/{total} cameras connected")
            else:
                print(f"  ⚠️ No cameras reachable ({total} configured)")
        except Exception as e:
            logger.error(f"Camera check failed: {e}")
            results.append(CheckResult(name="cameras", success=False, error=str(e)))
            print(f"  ⚠️ Camera check error: {e}")
    else:
        print("\n[5/5] Skipping camera check")
        results.append(CheckResult(name="cameras", success=True, details={"skipped": True}))
    
    # Summary
    print("\n" + "=" * 60)
    if overall_success:
        print("✅ All critical checks passed")
    else:
        print("❌ Some checks failed - review details above")
    print("=" * 60)
    
    return {
        "success": overall_success,
        "timestamp": datetime.now().isoformat(),
        "results": [{"name": r.name, "success": r.success, "error": r.error, "details": r.details} for r in results]
    }


def main():
    """CLI entry point for CI/CD checks."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CamMana CI/CD Health Check")
    parser.add_argument("--auto-fix", action="store_true", help="Attempt to fix issues automatically")
    parser.add_argument("--skip-cameras", action="store_true", help="Skip camera connectivity checks")
    parser.add_argument("--skip-api", action="store_true", help="Skip external API checks")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    result = run_all_checks(
        auto_fix=args.auto_fix,
        skip_cameras=args.skip_cameras,
        skip_api=args.skip_api
    )
    
    if args.json:
        import json
        print(json.dumps(result, indent=2))
    
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
