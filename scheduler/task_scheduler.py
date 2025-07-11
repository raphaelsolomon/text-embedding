"""
Task scheduler for cron jobs using native asyncio with seconds support and enhanced debugging
"""
import asyncio
from datetime import datetime, timedelta
from typing import Callable, Awaitable, Dict, Optional
import traceback
from config.logger import get_logger

logger = get_logger(__name__)

class ExtendedCronTab:
    """Enhanced CronTab that supports seconds field"""
    
    def __init__(self, cron_expression: str):
        self.expression = cron_expression
        self.fields = cron_expression.split()
        self.has_seconds = len(self.fields) == 6
        
        # Validate the expression
        if not (5 <= len(self.fields) <= 6):
            raise ValueError(f"Invalid cron expression: {cron_expression}. Must have 5 or 6 fields.")
        
        # Parse the expression
        self._parse_expression()
    
    def _parse_expression(self):
        """Parse and validate each field of the cron expression"""
        # If we have seconds field, process it separately
        if self.has_seconds:
            self.seconds = self._parse_field(self.fields[0], 0, 59)
            # Remove seconds field for standard fields
            fields_without_seconds = self.fields[1:]
        else:
            self.seconds = [0]  # Default to 0 seconds if not specified
            fields_without_seconds = self.fields
        
        # Field ranges
        ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
        
        # Parse standard fields (minute, hour, day, month, weekday)
        self.minutes = self._parse_field(fields_without_seconds[0], *ranges[0])
        self.hours = self._parse_field(fields_without_seconds[1], *ranges[1])
        self.days = self._parse_field(fields_without_seconds[2], *ranges[2])
        self.months = self._parse_field(fields_without_seconds[3], *ranges[3])
        self.weekdays = self._parse_field(fields_without_seconds[4], *ranges[4])
    
    def _parse_field(self, field: str, min_val: int, max_val: int) -> list:
        """Parse a cron field into a list of valid values"""
        if field == '*':
            return list(range(min_val, max_val + 1))
        
        values = []
        
        # Handle step values (*/10)
        if '/' in field:
            parts = field.split('/')
            if parts[0] == '*':
                step = int(parts[1])
                values.extend(range(min_val, max_val + 1, step))
            else:
                raise ValueError(f"Invalid cron field: {field}")
        
        # Handle ranges (1-5)
        elif '-' in field:
            parts = field.split('-')
            start = int(parts[0])
            end = int(parts[1])
            if start < min_val or end > max_val:
                raise ValueError(f"Values out of range in cron field: {field}")
            values.extend(range(start, end + 1))
        
        # Handle lists (1,3,5)
        elif ',' in field:
            for val in field.split(','):
                num = int(val)
                if min_val <= num <= max_val:
                    values.append(num)
                else:
                    raise ValueError(f"Value out of range in cron field: {field}")
        
        # Handle single values
        else:
            num = int(field)
            if min_val <= num <= max_val:
                values.append(num)
            else:
                raise ValueError(f"Value out of range in cron field: {field}")
        
        return values
    
    def is_time_to_run(self, dt: datetime) -> bool:
        """Check if it's time to run the job for given datetime"""
        return (
            dt.second in self.seconds and
            dt.minute in self.minutes and
            dt.hour in self.hours and
            dt.day in self.days and
            dt.month in self.months and
            dt.weekday() in self.weekdays
        )
    
    def next(self, from_time: datetime = None, default_utc: bool = False) -> float:
        """
        Calculate seconds until next run time
        
        Args:
            from_time: The datetime to calculate from (default: now)
            default_utc: Whether to use UTC (ignored, we always use the provided time's timezone)
            
        Returns:
            Seconds until next run time
        """
        if from_time is None:
            from_time = datetime.utcnow() if default_utc else datetime.now()
        
        # Start checking from the next second
        check_time = from_time + timedelta(seconds=1)
        
        # Brute force approach: check each second until we find a match
        # This is simplified and could be optimized for production use
        for i in range(24 * 60 * 60):  # Check up to 24 hours ahead
            if self.is_time_to_run(check_time):
                return (check_time - from_time).total_seconds()
            check_time += timedelta(seconds=1)
        
        # If no match in 24 hours, default to 1 day later
        return 24 * 60 * 60


class CronJob:
    """Represents a scheduled cron job"""
    def __init__(self, 
                name: str, 
                cron_expression: str, 
                callback: Callable[[], Awaitable[None]],
                timezone: str = "UTC"):
        self.name = name
        self.cron_expression = cron_expression
        self.callback = callback
        self.timezone = timezone
        self.crontab = ExtendedCronTab(cron_expression)
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        
        # Debug - Log cron details
        if self.crontab.has_seconds:
            logger.info(f"Job {name} configured with seconds field: {self.crontab.seconds}")
    
    async def _run_job(self):
        """Execute the job callback with error handling"""
        try:
            logger.info(f"Executing job: {self.name}")
            start_time = datetime.utcnow()
            
            # Debug - Log before invoking callback
            logger.info(f"About to invoke callback for {self.name}")
            
            # Execute the callback
            await self.callback()
            
            # Debug - Log after callback completes
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Job {self.name} completed in {duration:.2f} seconds")
        except Exception as e:
            logger.error(f"Error in job {self.name}: {str(e)}")
            logger.error(f"Exception details: {traceback.format_exc()}")
    
    async def _schedule_loop(self):
        """Main loop for checking and executing the cron job"""
        logger.info(f"Starting scheduling loop for job: {self.name}")
        
        # Debug - Log initial state
        now = datetime.utcnow()
        if self.crontab.has_seconds:
            logger.info(f"Current time: {now.isoformat()}, next seconds to check: {self.crontab.seconds}")
        else:
            logger.info(f"Current time: {now.isoformat()}, checking on minute changes")
        
        while self.running:
            try:
                now = datetime.utcnow()
                
                # Every 10 seconds, log that we're still checking
                if now.second % 10 == 0 and (self.last_run is None or (now - self.last_run).total_seconds() >= 10):
                    logger.debug(f"Job {self.name} checking schedule at {now.isoformat()}")
                
                # Check if it's time to run based on cron schedule
                should_run = self.crontab.is_time_to_run(now)
                
                if should_run:
                    # Only run if this is first run or enough time has passed since last run
                    if self.last_run is None or (now - self.last_run).total_seconds() >= 1:
                        logger.info(f"Time to run job {self.name} at {now.isoformat()}")
                        self.last_run = now
                        await self._run_job()
                
                # Wait a short time before checking again (for more precise timing)
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in scheduling loop for {self.name}: {str(e)}")
                logger.error(f"Exception details: {traceback.format_exc()}")
                # Don't crash the loop - wait and try again
                await asyncio.sleep(1)
    
    def start(self):
        """Start the cron job scheduler"""
        if self.running:
            logger.warning(f"Job {self.name} is already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._schedule_loop())
        logger.info(f"Job {self.name} scheduled with cron: {self.cron_expression}")
    
    def stop(self):
        """Stop the cron job scheduler"""
        if not self.running:
            logger.warning(f"Job {self.name} is not running")
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info(f"Job {self.name} stopped")


class TaskScheduler:
    """Task scheduler for managing cron jobs"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskScheduler, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the scheduler"""
        self.jobs: Dict[str, CronJob] = {}
        self.running = False
        logger.info("Task scheduler initialized")
    
    def register_job(self, 
                    name: str, 
                    cron_expression: str, 
                    callback: Callable[[], Awaitable[None]], 
                    timezone: str = "UTC") -> None:
        """
        Register a new cron job
        
        Args:
            name: Unique name for the job
            cron_expression: Cron expression (e.g. "*/10 * * * *" or "*/10 * * * * *" with seconds)
            callback: Async function to execute
            timezone: Timezone for the cron job
        """
        if name in self.jobs:
            logger.warning(f"Job {name} already registered, skipping")
            return
        
        # Create and store the job
        try:
            logger.info(f"Creating job {name} with cron: {cron_expression}")
            
            job = CronJob(
                name=name,
                cron_expression=cron_expression,
                callback=callback,
                timezone=timezone
            )
            
            self.jobs[name] = job
            logger.info(f"Registered job '{name}' with schedule: {cron_expression} ({timezone})")
            
            # Start the job if scheduler is running
            if self.running:
                job.start()
        except Exception as e:
            logger.error(f"Failed to register job '{name}': {str(e)}")
            logger.error(f"Exception details: {traceback.format_exc()}")
    
    def start(self) -> None:
        """Start the scheduler and all registered jobs"""
        if not self.jobs:
            logger.warning("No jobs registered, scheduler not started")
            return
        
        self.running = True
        for name, job in self.jobs.items():
            logger.info(f"Starting job: {name}")
            job.start()
        
        logger.info(f"Started scheduler with {len(self.jobs)} registered jobs")
    
    def stop(self) -> None:
        """Stop the scheduler and all running jobs"""
        self.running = False
        for name, job in self.jobs.items():
            job.stop()
        
        logger.info("Scheduler stopped")
