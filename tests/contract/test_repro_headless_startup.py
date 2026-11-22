# SPDX-License-Identifier: AGPL-3.0-only
"""BUG-01 campaign outcome and renderer-PID attribution."""

from tools.repro_headless_startup import summarize


def test_pass_requires_the_renderer_pid_and_a_completed_child_wait():
    progress = [dict(pid=20, stage='finished')]
    launcher = dict(event='watching', pid=10)
    renderer = dict(event='watching', pid=20)
    terminal = dict(event='target_exit', pid=10, returncode=0, child_waited=True)
    assert summarize(0, progress, [launcher, renderer, terminal])['outcome'] == 'passed'
    assert summarize(0, progress, [launcher, terminal])['outcome'] == 'unobserved'
    assert summarize(0, progress, [launcher, renderer])['outcome'] == 'failed'


def test_retains_timeout_stage_and_pool_loss_even_on_a_clean_worker_exit():
    progress = [dict(pid=20, stage='reading_pixels')]
    renderer = dict(event='watching', pid=20)
    timeout = dict(event='timeout', active_pids=[10, 20])
    terminal = dict(event='target_exit', returncode=124, child_waited=True)
    result = summarize(124, progress, [renderer, timeout, terminal])
    assert result['outcome'] == 'timeout'
    assert result['last_stage'] == 'reading_pixels'
    assert result['child_exit'] == 124 and result['child_waited']

    loss = dict(event='default_pool_lost', pid=20, handle=28, now='Semaphore')
    result = summarize(0, [dict(pid=20, stage='finished')],
                       [renderer, loss, dict(terminal, returncode=0)])
    assert result['outcome'] == 'pool_loss' and result['losses'] == [loss]
