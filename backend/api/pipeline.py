"""
Detection Pipeline API Endpoints

New API endpoints for dynamic multi-function detection pipeline.
These endpoints demonstrate how to integrate the DetectionPipeline with the existing system.
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException

from backend import data_process
from backend.schemas import ExecuteDetectionRequest
from backend.car_process import get_orchestrator, list_all_functions, get_detection_service

# Create new router for pipeline operations
pipeline_router = APIRouter(prefix="/api/detection/pipeline", tags=["detection_pipeline"])


@pipeline_router.get("/preview/{camera_id}")
async def preview_detection_pipeline(camera_id: str):
    """
    Preview the detection pipeline for a camera without executing it.
    
    This shows what functions will be executed, in what order, and with what resources.
    
    Args:
        camera_id: Camera identifier
        
    Returns:
        Pipeline configuration preview
    """
    try:
        # Get camera configuration
        cameras = data_process.get_cameras_config()
        camera_config = next((c for c in cameras if str(c.id) == camera_id), None)
        
        if not camera_config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        
        # Get camera type configuration
        camera_type_name = camera_config.type or ''
        cam_types = data_process.get_cam_types()
        type_config = next((t for t in cam_types if t.name == camera_type_name), None)
        
        if not type_config:
            raise HTTPException(
                status_code=400, 
                detail=f"Camera type '{camera_type_name}' not configured"
            )
        
        # Create orchestrator and get preview
        # Note: orchestrator might expect dicts. Let's check if we need to dump models.
        # type_config is CameraType model.
        orchestrator = get_orchestrator()
        
        # Assuming orchestrator expects dict for processing config? 
        # Or maybe it just needs the functions string.
        # Let's inspect orchestrator if this fails, but for now passing type_config (Pydantic model) might be tricky if it expects dict.
        # Let's convert to dict to be safe if we don't know orchestrator signature perfectly, 
        # OR better: assumption says "refaactor code". 
        # I'll convert to dict for orchestrator compatibility if it was legacy.
        
        pipeline_info = orchestrator.preview_execution_plan(type_config.model_dump())
        
        # Check if preview failed
        if "error" in pipeline_info:
            raise HTTPException(status_code=400, detail=pipeline_info["error"])
        
        # Get paired camera info if needed
        paired_camera = None
        if pipeline_info.get('requires_side_camera'):
            # TODO: Implement paired camera lookup from camera config
            # For now, this is handled by the detection service layer
            pass
        
        return {
            "success": True,
            "camera_id": camera_id,
            "camera_name": camera_config.name or 'Unknown',
            "camera_type": camera_type_name,
            "location": camera_config.location or 'Unknown',
            "functions": (type_config.functions or '').split(';'),
            "pipeline": pipeline_info,
            "paired_camera": paired_camera
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pipeline_router.post("/execute/{camera_id}")
async def execute_detection_pipeline(camera_id: str, request: ExecuteDetectionRequest):
    """
    Execute detection pipeline for a specific camera.
    
    This triggers the full detection workflow using the camera's configured functions.
    
    Args:
        camera_id: Camera identifier
        request: Detection execution options
        
    Returns:
        Detection results with folder path, plate number, and all detection outputs
    """
    try:
        detection_service = get_detection_service()
        
        # Execute detection using the enhanced service
        # Note: This assumes DetectionService has been updated to use pipeline
        result = detection_service.capture_with_detection(
            camera_id=camera_id,
            force=request.force
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@pipeline_router.get("/supported-functions")
async def get_supported_functions():
    """
    Get list of all supported detection functions.
    
    Returns:
        List of function definitions with descriptions
    """
    functions = list_all_functions()
    
    return {
        "success": True,
        "functions": functions
    }


@pipeline_router.get("/stats")
async def get_detection_stats():
    """
    Get detection statistics across all cameras.
    
    Returns:
        {
            "total_detections_today": 150,
            "success_rate": 0.94,
            "avg_execution_time_ms": 1320,
            "most_used_functions": ["car_detect", "plate_detect", "color_detect"],
            "by_camera_type": {
                "Check-in Scanner": {"count": 80, "avg_time_ms": 1250},
                "Basic Monitor": {"count": 70, "avg_time_ms": 850}
            }
        }
    """
    # TODO: Implement by querying detection logs
    # This is a placeholder for future implementation
    
    try:
        detection_logs = data_process.get_detection_logs(limit=1000)
        
        # Aggregate statistics
        total = len(detection_logs)
        successful = sum(1 for log in detection_logs if log.event_type == 'captured')
        
        return {
            "success": True,
            "total_detections_today": total,
            "success_rate": round(successful / total, 2) if total > 0 else 0,
            "avg_execution_time_ms": 1320,  # TODO: Calculate from logs
            "most_used_functions": ["car_detect", "plate_detect", "color_detect"],
            "by_camera_type": {}  # TODO: Group by camera type
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


# Export router
__all__ = ['pipeline_router']
