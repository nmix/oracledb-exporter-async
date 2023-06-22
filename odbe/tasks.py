'''
Metric collector module

Terminology:
Metric - a module artifact. This is what is sent to Prometheus.
Task - the source data for metric formation. A task is a single query
    to the database, which is executed according to its own schedule.
    Multiple metrics can be described within one task.
    Tasks are described in the TOML file within the [[metrics]] section.
Job - a background task execution mechanism provided
    by the APSchedule package.
'''

import sqlalchemy as sa
import tomllib
import prometheus_client

from apscheduler.triggers import cron

from odbe import extensions as ext


DEFAULT_TRIGGER_INTERVAL = 30  # seconds


# --- global task registry
_tasks_registry = []


def collect_metrics(task: dict):
    '''Create metric objects with task data and response from DB

    Args:
        task - scheduled task with DB reponse
        example:
        {
            'context': 'context_no_label',
            'labels': [ 'label_1', 'label_2' ]
            'request': "SELECT 1 as value_1, 2 as value_2, "
                "'First label' as label_1, "
                "'Second label' as label_2 FROM DUAL",
            'metricsdesc': {
                'value_1': 'Simple example returning always 1.',
                'value_2': 'Same but returning always 2.'
                },
            'response': {
                'value_1': 1,
                'value_2': 2,
                'label_1': 'First label',
                'label_2': 'Second label'
                },
            'metrics': {
                'value_1': prometheus_client.Gauge(),
                'value_2': prometheus_client.Counter(),
                }
        }
    '''
    metricsdesc = task.get('metricsdesc', [])
    labels = task.get('labels', [])
    response = task.get('response', {})
    metrics = task.get('metrics', {})
    for name in metricsdesc:
        # --- lower() - reponse from db always in lowercase
        value = response.get(name.lower(), 0.0)
        # --- value can be None
        if value is None:
            value = 0.0
        # ---
        label_vals = [response.get(label.lower(), None) for label in labels]
        metric_obj = metrics.get(name, None)
        if not metric_obj:
            continue
        if len(label_vals) > 0:
            metric_obj = metric_obj.labels(*label_vals)
        if isinstance(metric_obj, prometheus_client.Counter):
            metric_obj.inc(float(value))
        else:
            metric_obj.set(float(value))


def execute(index: int):
    '''
    Job executor - background request to the database

    Args:
        index - task index in global registry
    '''
    with ext.scheduler.app.app_context():
        task = _tasks_registry[index]
        context = task.get('context')
        ext.scheduler.app.logger.info(f'Request for {context}')
        # --- make sql request to DB
        #     take first row in response only
        #     response example:
        #     {
        #       'value_1': 1,
        #       'value_2': 2,
        #       'label_1': 'First label',
        #       'label_2': 'Second label'
        #       }
        request = task['request']
        response = ext.db.session.execute(sa.text(request)).mappings().first()
        task['response'] = response
        ext.scheduler.app.logger.info(f'Response: {response}')
        collect_metrics(task)


def _create_metrics(task: dict) -> dict:
    '''
    Create metrics for the task.

    One task can describe one or multiple metrics,
    which are generated based on the response from the database.
    Metrics are described in the 'metricsdesc' field:
    each key represents a metric.

    Args:
        task - task description
    Returns:
        Dictionary of metrics, where the key is the metric name from
        'metricsdesc',
        and the value is the metric object, e.g., 'prometheus_client.Gauge'
    '''
    metrics = {}
    context = task.get('context', 'odbe')
    metricsdesc = task.get('metricsdesc', [])
    metricstype = task.get('metricstype', {})
    labels = task.get('labels', [])
    for name in metricsdesc:
        desc = metricsdesc[name]
        if metricstype.get(name, 'gauge') == 'counter':
            klass = prometheus_client.Counter
        else:
            klass = prometheus_client.Gauge
        full_name = f'{context}_{name}'
        metrics[name] = klass(full_name, desc, labels)
    return metrics


def _read_tasks(path: str):
    '''
    Read tasks into the global list.

    Args:
        path - path to the TOML file with metric descriptions
    '''
    file = open(path, 'rb')
    # TODO
    # make file validation
    tasks = tomllib.load(file).get('metric', [])
    if len(tasks) == 0:
        ext.scheduler.app.logger.warn(
                f'There are no metrics load from {path}')
    return tasks


def _create_job(task: dict, func_args: list, job_id: str):
    '''
    Schedule job for task

    Args:
        task - task description
        func_args - list of argumets for execute function
        job_id - job id
    '''
    context = task.get('context', 'task')
    job_name = f'{context}_{job_id}'
    if 'cron' in task:
        crontab = task['cron']
        job = ext.scheduler.add_job(
            func=execute,
            args=func_args,
            trigger=cron.CronTrigger.from_crontab(crontab),
            id=job_id,
            name=job_name,
            replace_existing=True,
        )
    else:
        interval = task.get('interval', DEFAULT_TRIGGER_INTERVAL)
        job = ext.scheduler.add_job(
            func=execute,
            args=func_args,
            trigger='interval',
            seconds=interval,
            id=job_id,
            name=job_name,
            replace_existing=True,
        )
    return job


def load(metrics_path: str):
    '''
    Load metrics.

    Args:
        metrics_path - path to the TOML file with metric descriptions
    '''
    _tasks_registry.extend(_read_tasks(metrics_path))

    for index, task in enumerate(_tasks_registry):
        job = _create_job(task, func_args=[index], job_id=str(index))
        task['metrics'] = _create_metrics(task)
        ext.scheduler.app.logger.info(f'job {job.name} scheduled')
