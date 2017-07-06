import pytest

from uwsgiconf import Section
from uwsgiconf.exceptions import ConfigurationError


def test_master_process_basics(assert_lines):

    assert_lines([
        'master = true',
    ], Section().master_process.set_basic_params(enabled=True))


def test_master_attach_process_classic(assert_lines):

    assert_lines([
        'smart-attach-daemon2 = /here/a.pid',
    ], Section().master_process.attach_process_classic('/here/a.pid', background=False))

    assert_lines([
        'smart-attach-daemon = /here/a.pid',
    ], Section().master_process.attach_process_classic('/here/a.pid', background=True))

    with pytest.raises(ConfigurationError):
        assert_lines([
            '',
        ], Section().master_process.attach_process_classic('command', background=True))

    assert_lines([
        'attach-daemon = command',
    ], Section().master_process.attach_process_classic('command', background=False))

    assert_lines([
        'attach-control-daemon = command',
    ], Section().master_process.attach_process_classic(
        'command', background=False, control=True))


def test_master_attach_process(assert_lines):

    assert_lines([
        'attach-daemon2 = cmd=date',
    ], Section().master_process.attach_process('date'))

    assert_lines([
        'legion-attach-daemon2 = cmd=date',
    ], Section().master_process.attach_process('date', for_legion=True))

    assert_lines([
        'attach-daemon2 = cmd=date,pidfile=/here/my.pid,control=1,touch=/here/one',
    ], Section().master_process.attach_process('date', control=True, pidfile='/here/my.pid', touch_reload='/here/one'))

    assert_lines([
        'attach-daemon2 = cmd=date,touch=/here/one;/there/two',
    ], Section().master_process.attach_process('date', touch_reload=['/here/one', '/there/two']))


def test_cron(assert_lines):

    assert_lines([
        'cron2 = torrt walk',
    ], Section().master_process.add_cron_task('torrt walk'))

    assert_lines([
        'cron2 = week=1-3,hour=2,minute=-10,harakiri=10,legion=first,unique=1 some',
    ], Section().master_process.add_cron_task(
        'some', hour=2, minute=-10, weekday='1-3', harakiri=10, unique=True, legion='first'
    ))
