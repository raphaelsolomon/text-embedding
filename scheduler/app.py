from datetime import timezone
from config.logger import get_logger
from scheduler.task_scheduler import TaskScheduler

logger = get_logger(__name__)

async def setup_scheduler() -> TaskScheduler:
    """
    Set up and configure the task scheduler
    
    Returns:
        Configured TaskScheduler instance
    """
    try:
        scheduler = TaskScheduler()
        logger.info("Scheduler setup complete")

        # Register NordPool job to run every 10 seconds (for development/testing)
        logger.info("Registering Comparison job")
        scheduler.register_job(
            name="Comparison job update",
            cron_expression="*/30 * * * *",  # Every 30 minutes
            callback=tester,  # Replace None with your actual callback function
            timezone="UTC"
        )

        return scheduler
    except Exception as e:
        logger.error(f"Error setting up scheduler: {str(e)}")
        raise e
    
async def tester():
    print("Scheduler is working correctly")