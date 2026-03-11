"""
Batch Processing Service for Ussop
Process multiple images in parallel
"""
import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy.orm import Session

from config.settings import settings
from services.inspector import InspectionService, InspectionConfig


class BatchJobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BatchJob:
    """Batch processing job."""
    id: str
    name: str
    status: BatchJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    input_directory: str = ""
    output_directory: str = ""
    results: List[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.results is None:
            self.results = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "progress_percent": self.get_progress(),
            "input_directory": self.input_directory,
            "output_directory": self.output_directory,
            "error_message": self.error_message
        }
    
    def get_progress(self) -> float:
        """Get progress percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100


class BatchProcessor:
    """
    Batch processing service for multiple images.
    
    Features:
    - Process folders of images
    - Parallel processing with asyncio
    - Progress tracking
    - Resume capability
    - Export results to JSON/CSV
    """
    
    def __init__(self):
        self.jobs: Dict[str, BatchJob] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.inspection_service = InspectionService()
        self._callbacks: List[Callable[[BatchJob], None]] = []
    
    def create_job(
        self,
        name: str,
        input_directory: str,
        output_directory: Optional[str] = None,
        pattern: str = "*.jpg"
    ) -> BatchJob:
        """
        Create a new batch processing job.
        
        Args:
            name: Job name
            input_directory: Directory containing images
            output_directory: Directory for results (optional)
            pattern: File pattern to match
        
        Returns:
            BatchJob object
        """
        import uuid
        
        job_id = str(uuid.uuid4())[:8]
        
        # Find matching files
        input_path = Path(input_directory)
        if not input_path.exists():
            raise ValueError(f"Input directory does not exist: {input_directory}")
        
        image_files = list(input_path.glob(pattern)) + list(input_path.glob(pattern.replace("jpg", "jpeg"))) + list(input_path.glob(pattern.replace("jpg", "png")))
        
        # Create output directory
        if output_directory:
            output_path = Path(output_directory)
        else:
            output_path = settings.DATA_DIR / "batch_results" / job_id
        
        output_path.mkdir(parents=True, exist_ok=True)
        
        job = BatchJob(
            id=job_id,
            name=name,
            status=BatchJobStatus.PENDING,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            total_files=len(image_files),
            input_directory=str(input_path.absolute()),
            output_directory=str(output_path.absolute())
        )
        
        # Store image file list
        job.results = [{"file": str(f), "status": "pending"} for f in image_files]
        
        self.jobs[job_id] = job
        
        return job
    
    async def start_job(self, job_id: str, db: Session, config: Optional[InspectionConfig] = None):
        """Start processing a batch job."""
        if job_id not in self.jobs:
            raise ValueError(f"Job not found: {job_id}")
        
        job = self.jobs[job_id]
        
        if job.status == BatchJobStatus.RUNNING:
            raise ValueError("Job is already running")
        
        job.status = BatchJobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Create task
        task = asyncio.create_task(self._process_job(job, db, config))
        self.active_tasks[job_id] = task
        
        # Handle completion
        task.add_done_callback(lambda t: self._on_job_complete(job_id, t))
        
        return job
    
    async def _process_job(self, job: BatchJob, db: Session, config: Optional[InspectionConfig]):
        """Process all images in the job."""
        config = config or InspectionConfig()
        
        # Semaphore to limit concurrent processing
        semaphore = asyncio.Semaphore(4)  # Max 4 concurrent inspections
        
        async def process_file(item: Dict[str, Any]):
            """Process a single file."""
            async with semaphore:
                if job.status == BatchJobStatus.CANCELLED:
                    return
                
                file_path = item["file"]
                
                try:
                    # Run inspection
                    result = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: self.inspection_service.inspect_image(
                            image_path=file_path,
                            db=db,
                            config=config
                        )
                    )
                    
                    # Update item
                    item["status"] = "completed"
                    item["result"] = result
                    
                    job.processed_files += 1
                    
                except Exception as e:
                    item["status"] = "failed"
                    item["error"] = str(e)
                    job.failed_files += 1
                    job.processed_files += 1
                
                # Notify callbacks
                for callback in self._callbacks:
                    try:
                        callback(job)
                    except:
                        pass
        
        # Process all files
        tasks = [process_file(item) for item in job.results]
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Save results to file
        await self._save_results(job)
    
    async def _save_results(self, job: BatchJob):
        """Save job results to file."""
        output_path = Path(job.output_directory)
        
        # Save JSON results
        results_file = output_path / "results.json"
        with open(results_file, 'w') as f:
            json.dump({
                "job": job.to_dict(),
                "results": job.results
            }, f, indent=2, default=str)
        
        # Save CSV summary
        csv_file = output_path / "summary.csv"
        with open(csv_file, 'w') as f:
            f.write("File,Status,Decision,Confidence,Objects,Time_ms\n")
            for item in job.results:
                result = item.get("result", {})
                f.write(f"{item['file']},{item['status']},{result.get('decision','')},{result.get('confidence','')},{result.get('objects_found','')},{result.get('total_time_ms','')}\n")
    
    def _on_job_complete(self, job_id: str, task: asyncio.Task):
        """Handle job completion."""
        if job_id in self.active_tasks:
            del self.active_tasks[job_id]
        
        if job_id not in self.jobs:
            return
        
        job = self.jobs[job_id]
        job.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)
        
        # Check for exception
        try:
            task.result()
            if job.status != BatchJobStatus.CANCELLED:
                job.status = BatchJobStatus.COMPLETED
        except Exception as e:
            job.status = BatchJobStatus.FAILED
            job.error_message = str(e)
        
        # Notify callbacks
        for callback in self._callbacks:
            try:
                callback(job)
            except:
                pass
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        if job_id not in self.jobs:
            return False
        
        job = self.jobs[job_id]
        
        if job.status != BatchJobStatus.RUNNING:
            return False
        
        job.status = BatchJobStatus.CANCELLED
        
        # Cancel task
        if job_id in self.active_tasks:
            self.active_tasks[job_id].cancel()
        
        return True
    
    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID."""
        return self.jobs.get(job_id)
    
    def list_jobs(self, status: Optional[BatchJobStatus] = None) -> List[BatchJob]:
        """List all jobs, optionally filtered by status."""
        jobs = list(self.jobs.values())
        
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created date (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job."""
        if job_id not in self.jobs:
            return False
        
        # Cancel if running
        if self.jobs[job_id].status == BatchJobStatus.RUNNING:
            self.cancel_job(job_id)
        
        del self.jobs[job_id]
        return True
    
    def on_progress(self, callback: Callable[[BatchJob], None]):
        """Register a progress callback."""
        self._callbacks.append(callback)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get batch processing statistics."""
        total = len(self.jobs)
        completed = sum(1 for j in self.jobs.values() if j.status == BatchJobStatus.COMPLETED)
        running = sum(1 for j in self.jobs.values() if j.status == BatchJobStatus.RUNNING)
        failed = sum(1 for j in self.jobs.values() if j.status == BatchJobStatus.FAILED)
        
        total_files = sum(j.total_files for j in self.jobs.values())
        processed_files = sum(j.processed_files for j in self.jobs.values())
        
        return {
            "total_jobs": total,
            "completed_jobs": completed,
            "running_jobs": running,
            "failed_jobs": failed,
            "total_files": total_files,
            "processed_files": processed_files,
            "active_tasks": len(self.active_tasks)
        }


# Singleton instance
_batch_processor: Optional[BatchProcessor] = None


def get_batch_processor() -> BatchProcessor:
    """Get batch processor singleton."""
    global _batch_processor
    if _batch_processor is None:
        _batch_processor = BatchProcessor()
    return _batch_processor
