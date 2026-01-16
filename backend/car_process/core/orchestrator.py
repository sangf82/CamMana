"""
Detection Orchestrator

Main controller that coordinates detection execution based on camera type.
Handles both predefined camera types and custom configurations.
"""

from typing import Dict, Any, List, Optional
import time
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed

from backend.car_process.config.function_config import (
    get_function,
    get_function_metadata,
    get_functions_by_parallel_group,
    validate_function_list
)
from backend.car_process.config.camera_type_config import get_preset


class DetectionOrchestrator:
    """
    Orchestrates detection execution for cameras based on their type configuration.
    
    Supports:
    1. Predefined camera types (check-in, check-out, volume, etc.)
    2. Custom camera types with user-selected functions
    3. Parallel execution optimization
    4. Function dependency management
    """
    
    def __init__(self):
        """Initialize orchestrator"""
        self._function_instances = {}  # Cache function instances for reuse
    
    def execute_for_camera_type(self,
                                camera_type: Dict[str, Any],
                                front_frame: np.ndarray,
                                side_frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Execute detection for a camera type configuration.
        
        Args:
            camera_type: Camera type config from database
                {
                    "name": "Check-in Scanner",
                    "functions": "car_detect;plate_detect;color_detect"
                }
            front_frame: Front camera frame (numpy array)
            side_frame: Optional side camera frame (numpy array)
            
        Returns:
            {
                "success": bool,
                "results": {
                    "car_detect": {...},
                    "plate_detect": {...},
                    "color_detect": {...}
                },
                "camera_type": str,
                "executed_functions": List[str],
                "execution_time_ms": float
            }
        """
        start_time = time.time()
        
        # Parse function list
        functions_str = camera_type.get('functions', '')
        function_ids = [f.strip() for f in functions_str.split(';') if f.strip()]
        
        if not function_ids:
            return {
                "success": False,
                "error": "No functions configured for this camera type",
                "camera_type": camera_type.get('name', 'Unknown')
            }
        
        # Validate functions
        is_valid, invalid = validate_function_list(function_ids)
        if not is_valid:
            return {
                "success": False,
                "error": f"Invalid functions: {invalid}",
                "camera_type": camera_type.get('name', 'Unknown')
            }
        
        # Prepare frames
        frames = {
            'front_cam': front_frame,
            'side_cam': side_frame
        }
        
        # Group functions by parallel group
        grouped_functions = get_functions_by_parallel_group(function_ids)
        
        # Execute groups sequentially, functions within group in parallel
        all_results = {}
        for group_id in sorted(grouped_functions.keys()):
            func_ids_in_group = grouped_functions[group_id]
            
            try:
                group_results = self._execute_parallel_group(func_ids_in_group, frames)
                all_results.update(group_results)
                
                # Check if car_detect failed (blocks further detection)
                if 'car_detect' in group_results:
                    car_result = group_results['car_detect']
                    if not car_result.get('success') or not car_result.get('detected'):
                        # No car detected, stop processing
                        break
                
            except Exception as e:
                print(f"[Orchestrator] Error in parallel group {group_id}: {e}")
                # Continue with next group
        
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        return {
            "success": True,
            "results": all_results,
            "camera_type": camera_type.get('name', 'Unknown'),
            "executed_functions": list(all_results.keys()),
            "execution_time_ms": round(execution_time, 2)
        }
    
    def execute_for_preset(self,
                          preset_id: str,
                          front_frame: np.ndarray,
                          side_frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """
        Execute detection using a predefined camera type preset.
        
        Args:
            preset_id: Preset ID (e.g., "check_in_scanner")
            front_frame: Front camera frame
            side_frame: Optional side camera frame
            
        Returns:
            Detection results dictionary
        """
        preset = get_preset(preset_id)
        
        # Convert preset to camera_type format
        camera_type = {
            "name": preset.name,
            "functions": ";".join(preset.functions)
        }
        
        return self.execute_for_camera_type(camera_type, front_frame, side_frame)
    
    def preview_execution_plan(self, camera_type: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preview what functions will be executed without running them.
        
        Useful for UI to show user what will happen before execution.
        
        Args:
            camera_type: Camera type configuration
            
        Returns:
            {
                "camera_type": str,
                "total_functions": int,
                "execution_plan": [
                    {
                        "parallel_group": int,
                        "execution_mode": "parallel" | "sequential",
                        "functions": [{"id":..., "name":..., "input_source":...}]
                    }
                ],
                "requires_side_camera": bool,
                "estimated_time_ms": int
            }
        """
        functions_str = camera_type.get('functions', '')
        function_ids = [f.strip() for f in functions_str.split(';') if f.strip()]
        
        if not function_ids:
            return {
                "camera_type": camera_type.get('name', 'Unknown'),
                "error": "No functions configured"
            }
        
        # Validate functions
        is_valid, invalid = validate_function_list(function_ids)
        if not is_valid:
            return {
                "camera_type": camera_type.get('name', 'Unknown'),
                "error": f"Invalid functions: {invalid}"
            }
        
        # Build execution plan
        grouped = get_functions_by_parallel_group(function_ids)
        
        plan = []
        for group_id in sorted(grouped.keys()):
            func_ids = grouped[group_id]
            group_info = {
                "parallel_group": group_id,
                "execution_mode": "parallel" if len(func_ids) > 1 else "sequential",
                "functions": []
            }
            
            for func_id in func_ids:
                metadata = get_function_metadata(func_id)
                group_info["functions"].append({
                    "id": func_id,
                    "name": metadata.get('name', func_id),
                    "input_source": metadata.get('input_source', 'unknown'),
                    "description": metadata.get('description', '')
                })
            
            plan.append(group_info)
        
        # Check if side camera is required
        requires_side = any(
            get_function_metadata(fid).get('input_source') == 'side_cam'
            for fid in function_ids
        )
        
        # Estimate execution time (rough estimate)
        estimated_time = 0
        for group in plan:
            # Assume each function takes ~400ms
            # Parallel functions only count as max time in group
            group_time = 400 if group["execution_mode"] == "parallel" else 400 * len(group["functions"])
            estimated_time += group_time
        
        return {
            "camera_type": camera_type.get('name', 'Unknown'),
            "total_functions": len(function_ids),
            "execution_plan": plan,
            "requires_side_camera": requires_side,
            "estimated_time_ms": estimated_time
        }
    
    def _execute_parallel_group(self,
                                function_ids: List[str],
                                frames: Dict[str, np.ndarray]) -> Dict[str, Any]:
        """
        Execute a group of functions in parallel.
        
        Args:
            function_ids: List of function IDs to execute
            frames: Dict mapping 'front_cam'/'side_cam' to frame arrays
            
        Returns:
            Dict mapping function_id to result dict
        """
        results = {}
        
        def run_function(func_id: str) -> tuple[str, Dict[str, Any]]:
            """Execute a single function and return (func_id, result)"""
            # Get or create function instance (cached for performance)
            if func_id not in self._function_instances:
                self._function_instances[func_id] = get_function(func_id)
            
            func_instance = self._function_instances[func_id]
            metadata = get_function_metadata(func_id)
            
            # Get required frame
            frame_source = metadata.get('input_source', 'front_cam')
            frame = frames.get(frame_source)
            
            if frame is None:
                return (func_id, {
                    "success": False,
                    "error": f"Frame from {frame_source} not available"
                })
            
            # Execute detection
            try:
                result = func_instance.detect(frame)
                return (func_id, result)
            except Exception as e:
                return (func_id, {
                    "success": False,
                    "error": f"Function execution failed: {str(e)}"
                })
        
        # Execute in parallel if multiple functions
        if len(function_ids) == 1:
            # Single function, no need for threading
            func_id, result = run_function(function_ids[0])
            results[func_id] = result
        else:
            # Multiple functions, execute in parallel
            max_workers = min(len(function_ids), 4)  # Limit concurrent workers
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(run_function, fid): fid
                    for fid in function_ids
                }
                
                for future in as_completed(futures):
                    try:
                        func_id, result = future.result(timeout=15)
                        results[func_id] = result
                    except Exception as e:
                        func_id = futures[future]
                        results[func_id] = {
                            "success": False,
                            "error": f"Execution timeout or error: {str(e)}"
                        }
        
        return results


# Singleton instance
_orchestrator_instance: Optional[DetectionOrchestrator] = None


def get_orchestrator() -> DetectionOrchestrator:
    """Get singleton orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = DetectionOrchestrator()
    return _orchestrator_instance


__all__ = ['DetectionOrchestrator', 'get_orchestrator']
