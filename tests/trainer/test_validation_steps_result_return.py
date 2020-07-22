"""
Tests to ensure that the training loop works with a dict
"""
import os
import torch
from pytorch_lightning import Trainer
from tests.base.deterministic_model import DeterministicModel
from pytorch_lightning.core.step_result import Result, TrainResult, EvalResult
from tests.base import EvalModelTemplate
import pytest


# test with train_step_end
# add logging + row interval tests

def test_val_step_result_callbacks(tmpdir):
    """
    Tests that val step can be used:
    - val step
    - no other val_xxx
    - train loop
    - callbacks coming from val loop (not train loop)
    """
    # enable internal debugging actions
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_result_callbacks
    model.validation_step_end = None
    model.validation_epoch_end = None

    batches = 3
    epochs = 300
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        early_stop_callback=True,
        row_log_interval=1,
        limit_train_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert not model.validation_epoch_end_called

    # assert that early stopping happened after the requested num of steps
    # if it used the train step for ES then it wouldn't be 5
    assert len(trainer.dev_debugger.early_stopping_history) == 5

    # only 2 checkpoints expected
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 2

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171 + 22

    # did not request any metrics to log (except the metrics saying which epoch we are on)
    assert len(trainer.progress_bar_metrics) == 0
    assert len(trainer.dev_debugger.logged_metrics) == 5


def test_val_step_using_train_callbacks(tmpdir):
    """
    ES conditioned in train
    CKPT conditioned in val
    """
    # enable internal debugging actions
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_result_no_callbacks
    model.validation_step_end = None
    model.validation_epoch_end = None

    batches = 3
    epochs = 300
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        early_stop_callback=True,
        row_log_interval=1,
        limit_train_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    expected_epochs = 10

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert not model.validation_epoch_end_called

    # early stopping was not conditioned in val loop, but instead in train loop
    assert len(trainer.dev_debugger.early_stopping_history) == expected_epochs

    # only 2 checkpoints expected
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 2

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171 + 50

    # did not request any metrics to log (except the metrics saying which epoch we are on)
    assert len(trainer.progress_bar_metrics) == 0
    assert len(trainer.dev_debugger.logged_metrics) == expected_epochs


def test_val_step_only_epoch_metrics(tmpdir):
    """
    Make sure the logged + pbar metrics are allocated accordingly when auto-reduced at epoch end
    """
    # enable internal debugging actions
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_result_only_epoch_metrics
    model.validation_step_end = None
    model.validation_epoch_end = None

    batches = 3
    epochs = 3
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        row_log_interval=1,
        limit_train_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert not model.validation_epoch_end_called

    # no early stopping
    assert len(trainer.dev_debugger.early_stopping_history) == 0

    # make sure we logged the exact number of metrics
    assert len(trainer.dev_debugger.logged_metrics) == epochs
    assert len(trainer.dev_debugger.pbar_added_metrics) == epochs

    # make sure we logged the correct epoch metrics
    for metric in trainer.dev_debugger.logged_metrics:
        assert 'no_val_no_pbar' not in metric
        assert 'val_step_pbar_acc' not in metric
        assert metric['val_step_log_acc'] == (12 + 13) / 2
        assert metric['val_step_log_pbar_acc'] == (13 + 14) / 2

    # make sure we logged the correct epoch pbar metrics
    for metric in trainer.dev_debugger.pbar_added_metrics:
        assert 'no_val_no_pbar' not in metric
        assert 'val_step_log_acc' not in metric
        assert metric['val_step_log_pbar_acc'] == (13 + 14) / 2
        assert metric['val_step_pbar_acc'] == (14 + 15) / 2

    # only 1 checkpoint expected since values didn't change after that
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 1

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171


def test_val_step_only_step_metrics(tmpdir):
    """
    Make sure the logged + pbar metrics are allocated accordingly at every step when requested
    """
    # enable internal debugging actions
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_result_only_step_metrics
    model.validation_step_end = None
    model.validation_epoch_end = None

    batches = 3
    epochs = 3
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        row_log_interval=1,
        limit_train_batches=batches,
        limit_val_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert not model.validation_epoch_end_called

    # no early stopping
    assert len(trainer.dev_debugger.early_stopping_history) == 0

    # make sure we logged the exact number of metrics
    assert len(trainer.dev_debugger.logged_metrics) == epochs * batches + (epochs)
    assert len(trainer.dev_debugger.pbar_added_metrics) == epochs * batches + (epochs)

    # make sure we logged the correct epoch metrics
    total_empty_epoch_metrics = 0
    for metric in trainer.dev_debugger.logged_metrics:
        if len(metric) > 2:
            assert 'no_val_no_pbar' not in metric
            assert 'val_step_pbar_acc' not in metric
            assert metric['val_step_log_acc']
            assert metric['val_step_log_pbar_acc']
        else:
            total_empty_epoch_metrics += 1

    assert total_empty_epoch_metrics == 3

    # make sure we logged the correct epoch pbar metrics
    total_empty_epoch_metrics = 0
    for metric in trainer.dev_debugger.pbar_added_metrics:
        if len(metric) > 2:
            assert 'no_val_no_pbar' not in metric
            assert 'val_step_log_acc' not in metric
            assert metric['val_step_log_pbar_acc']
            assert metric['val_step_pbar_acc']
        else:
            total_empty_epoch_metrics += 1

    assert total_empty_epoch_metrics == 3

    # only 1 checkpoint expected since values didn't change after that
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 1

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171


def test_val_step_epoch_step_metrics(tmpdir):
    """
    Make sure the logged + pbar metrics are allocated accordingly at every step when requested
    """
    # enable internal debugging actions
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_result_epoch_step_metrics
    model.validation_step_end = None
    model.validation_epoch_end = None

    batches = 3
    epochs = 3
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        row_log_interval=1,
        limit_train_batches=batches,
        limit_val_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert not model.validation_epoch_end_called

    # no early stopping
    assert len(trainer.dev_debugger.early_stopping_history) == 0

    # make sure we logged the exact number of metrics
    assert len(trainer.dev_debugger.logged_metrics) == epochs * batches + (epochs)
    assert len(trainer.dev_debugger.pbar_added_metrics) == epochs * batches + (epochs)

    # make sure we logged the correct epoch metrics
    for metric_idx in range(0, len(trainer.dev_debugger.logged_metrics), batches + 1):
        batch_metrics = trainer.dev_debugger.logged_metrics[metric_idx: metric_idx + batches]
        epoch_metric = trainer.dev_debugger.logged_metrics[metric_idx + batches]
        
        # make sure the metric was split
        for batch_metric in batch_metrics:
            assert 'step_val_step_log_acc' in batch_metric
            assert 'step_val_step_log_pbar_acc' in batch_metric
        
        # make sure the epoch split was correct
        assert 'epoch_val_step_log_acc' in epoch_metric
        assert 'epoch_val_step_log_pbar_acc' in epoch_metric

    # make sure we logged the correct pbar metrics
    for metric_idx in range(0, len(trainer.dev_debugger.pbar_added_metrics), batches + 1):
        batch_metrics = trainer.dev_debugger.pbar_added_metrics[metric_idx: metric_idx + batches]
        epoch_metric = trainer.dev_debugger.pbar_added_metrics[metric_idx + batches]

        # make sure the metric was split
        for batch_metric in batch_metrics:
            assert 'step_val_step_pbar_acc' in batch_metric
            assert 'step_val_step_log_pbar_acc' in batch_metric

        # make sure the epoch split was correct
        assert 'epoch_val_step_pbar_acc' in epoch_metric
        assert 'epoch_val_step_log_pbar_acc' in epoch_metric

    # only 1 checkpoint expected since values didn't change after that
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 1

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171


def test_val_step_epoch_end_result(tmpdir):
    """
    Make sure val step + val epoch end works with EvalResult
    """
    os.environ['PL_DEV_DEBUG'] = '1'

    model = DeterministicModel()
    model.training_step = model.training_step_result_log_epoch_and_step_for_callbacks
    model.training_step_end = None
    model.training_epoch_end = None
    model.validation_step = model.validation_step_for_epoch_end_result
    model.validation_step_end = None
    model.validation_epoch_end = model.validation_epoch_end_result

    batches = 3
    epochs = 3
    trainer = Trainer(
        default_root_dir=tmpdir,
        max_epochs=epochs,
        row_log_interval=1,
        limit_train_batches=batches,
        limit_val_batches=batches,
        weights_summary=None,
    )
    trainer.fit(model)

    # make sure correct steps were called
    assert model.validation_step_called
    assert not model.validation_step_end_called
    assert model.validation_epoch_end_called

    # no early stopping
    assert len(trainer.dev_debugger.early_stopping_history) == 0

    # make sure we logged the exact number of metrics
    assert len(trainer.dev_debugger.logged_metrics) == epochs
    assert len(trainer.dev_debugger.pbar_added_metrics) == epochs

    # make sure we logged the correct metrics
    for metric in trainer.dev_debugger.logged_metrics:
        assert metric['val_epoch_end_metric'] == 189
        assert 'val_step_metric' in metric

    # make sure we pbar logged the correct metrics
    for metric in trainer.dev_debugger.pbar_added_metrics:
        assert metric['val_epoch_end_metric'] == 189
        assert 'val_step_metric' in metric

    # only 1 checkpoint expected since values didn't change after that
    assert len(trainer.dev_debugger.checkpoint_callback_history) == 1

    # make sure the last known metric is correct
    assert trainer.callback_metrics['val_checkpoint_on'] == 171


@pytest.mark.skipif(torch.cuda.device_count() < 2, reason="test requires multi-GPU machine")
def test_val_step_full_loop_result_dp(tmpdir):
    # TODO: finish the full train, val, test loop with dp
    os.environ['PL_DEV_DEBUG'] = '1'

    batches = 10
    epochs = 3

    model = EvalModelTemplate()
    model.training_step = model.training_step_full_loop_result_obj_dp
    model.training_step_end = model.training_step_end_full_loop_result_obj_dp
    model.training_epoch_end = model.training_epoch_end_full_loop_result_obj_dp
    model.validation_step = model.eval_step_full_loop_result_obj_dp
    model.validation_step_end = model.eval_step_end_full_loop_result_obj_dp
    model.validation_epoch_end = model.eval_epoch_end_full_loop_result_obj_dp
    model.test_step = model.eval_step_full_loop_result_obj_dp
    model.test_step_end = model.eval_step_end_full_loop_result_obj_dp
    model.test_epoch_end = model.eval_epoch_end_full_loop_result_obj_dp

    trainer = Trainer(
        default_root_dir=tmpdir,
        distributed_backend='dp',
        gpus=[0, 1],
        max_epochs=epochs,
        early_stop_callback=True,
        row_log_interval=2,
        limit_train_batches=batches,
        weights_summary=None,
    )

    trainer.fit(model)

    results = trainer.test()

    # assert we returned all metrics requested
    assert len(results) == 1
    results = results[0]
    assert 'test_epoch_end_metric' in results

    # make sure we saw all the correct keys along all paths
    seen_keys = set()
    for metric in trainer.dev_debugger.logged_metrics:
        seen_keys.update(metric.keys())

    import pdb; pdb.set_trace()
    assert 'train_step_metric' in seen_keys
    assert 'train_step_end_metric' in seen_keys
    assert 'epoch_train_epoch_end_metric' in seen_keys
    assert 'validation_step_metric' in seen_keys
    assert 'validation_step_end_metric' in seen_keys
    assert 'validation_epoch_end_metric' in seen_keys
    assert 'test_step_metric' in seen_keys
    assert 'test_step_end_metric' in seen_keys
    assert 'test_epoch_end_metric' in seen_keys


# TODO: finish the full train, val, test loop with dp

test_val_step_full_loop_result_dp('')