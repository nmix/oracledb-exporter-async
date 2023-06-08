import pytest

from odbe import tasks
import prometheus_client


@pytest.fixture(scope='session')
def task():
    return {
            'context': 'test_context',
            'labels': ['label_1', 'label_2'],
            'request': "SELECT 1 as value_1, 2 as value_2, "
            "'First label' as label_1, 'Second label' as label_2 FROM DUAL",
            'metricsdesc': {
                'value_1': 'Simple example returning always 1.',
                'value_2': 'Same but returning always 2.'
                },
            'metricstype': {'value_1': 'counter'},
        }


@pytest.fixture(scope='session')
def metrics(task):
    return tasks._create_metrics(task)


def test_create_metrics_count(metrics):
    assert len(metrics) == 2


@pytest.mark.parametrize(
        'value_name, type_',
        [
            ('value_1', prometheus_client.Counter),
            ('value_2', prometheus_client.Gauge),
            ]
        )
def test_create_metrics_types(metrics, value_name, type_):
    assert isinstance(metrics[value_name], type_)


@pytest.mark.parametrize(
        'value_name, metric_name, metric_doc',
        [
            ('value_1',
             'test_context_value_1',
             'Simple example returning always 1.'),
            ('value_2',
             'test_context_value_2',
             'Same but returning always 2.'),
            ]
        )
def test_create_metrics_name(metrics, value_name, metric_name, metric_doc):
    assert metrics[value_name]._name == metric_name
    assert metrics[value_name]._documentation == metric_doc


@pytest.mark.parametrize(
        'value_name, labels',
        [
            ('value_1', ('label_1', 'label_2')),
            ('value_2', ('label_1', 'label_2')),
            ]
        )
def test_create_metrics_labels(metrics, value_name, labels):
    assert metrics[value_name]._labelnames == labels
