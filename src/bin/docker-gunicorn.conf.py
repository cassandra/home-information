def post_worker_init( worker ):
    """Start all background processes.

    Note that launching these needs to happen elsewhere for the
    non-gunicorn executions, e.g., "./manage.py runserver".  See the
    AppConfig.ready() function of these app modules for this other case.
    """
    from hi.background_tasks import HiBackgroundTaskHelper
    HiBackgroundTaskHelper.start_background_tasks()
    return
