from ..base import OptionsGroup
from ..exceptions import ConfigurationError


class MasterProcess(OptionsGroup):
    """Master process is a separate process offering mentoring capabilities
    for other processes. Only one master process per uWSGI instance.

    uWSGI's built-in prefork+threading multi-worker management mode,
    activated by flicking the master switch on.

    .. note:: For all practical serving deployments it's not really a good idea not to use master mode.

    """

    def set_basic_params(self, enabled=None, name=None, no_orphans=None, as_root=None,
                         subproc_check_interval=None):
        """

        :param bool enabled: Enable uWSGI master process.

        :param str|unicode master_enabled: Set master process name to given value.

        :param bool no_orphans: Automatically kill workers if master dies (can be dangerous for availability).

        :param bool as_root: Leave master process running as root.

        :param int subproc_check_interval: Set the interval (in seconds) of master checks. Default: 1
            The master process makes a scan of subprocesses, etc. every N seconds.

            .. warning:: You can increase this time if you need to, but it's DISCOURAGED.

        """
        self._set('master', enabled, cast=bool)
        self._set('procname-master', name)
        self._set('no-orphans', no_orphans)
        self._set('master-as-root', as_root)
        self._set('check-interval', subproc_check_interval)

        return self._section

    def add_cron_task(self, command, weekday=None, month=None, day=None, hour=None, minute=None,
                      legion=None, unique=None, harakiri=None):
        """Adds a cron task running the given command on the given schedule.
        http://uwsgi.readthedocs.io/en/latest/Cron.html

        HINTS:
            * Use negative values to say `every`:
                hour=-3  stands for `every 3 hours`

            * Use - (minus) to make interval:
                minute='13-18'  stands for `from minute 13 to 18`

        .. note:: We use cron2 option available since 1.9.11.

        :param str|unicode command: Command to execute on schedule (with or without path).

        :param int|str|unicode weekday: Day of a the week number. Defaults to `each`.
            0 - Sunday  1 - Monday  2 - Tuesday  3 - Wednesday
            4 - Thursday  5 - Friday  6 - Saturday

        :param int|str|unicode month: Month number 1-12. Defaults to `each`.

        :param int|str|unicode day: Day of the month number 1-31. Defaults to `each`.

        :param int|str|unicode hour: Hour 0-23. Defaults to `each`.

        :param int|str|unicode minute: Minute 0-59. Defaults to `each`.

        :param str|unicode legion: Set legion (cluster) name to use this cron command against.
            Such commands are only executed by legion lord node.

        :param bool unique: Marks command as unique. Default to not unique.
            Some commands can take a long time to finish or just hang doing their thing.
            Sometimes this is okay, but there are also cases when running multiple instances
            of the same command can be dangerous.

        :param int harakiri: Enforce a time limit (in seconds) on executed commands.
            If a command is taking longer it will be killed.

        """
        rule = []
        locals_ = locals()

        aliases = {
            'weekday': 'week',
        }

        for chunk in ['weekday', 'month', 'day', 'hour', 'minute', 'harakiri', 'legion']:
            val = locals_[chunk]
            if val is not None:
                rule.append('%s=%s' % (aliases.get(chunk, chunk), val))

        if unique:
            rule.append('unique=1')

        self._set('cron2', '%s %s' % (','.join(rule), command))

        return self._section

    def attach_process_classic(self, command_or_pid_path, background, control=False, for_legion=False):
        """Attaches a command/daemon to the master process optionally managed by a pidfile.

        This will allow the uWSGI master to control/monitor/respawn this process.

        .. note:: This uses old classic uWSGI means of process attaching
            To have more control use ``.attach_process()`` method (requires  uWSGI 2.0+)

        http://uwsgi-docs.readthedocs.io/en/latest/AttachingDaemons.html

        :param str|unicode command_or_pid_path:

        :param bool background: Must indicate whether process is in background.

        :param bool control: Consider this process a control: when the daemon dies, the master exits.

            .. note:: pidfile managed processed not supported.

        :param bool for_legion: Legion daemons will be executed only on the legion lord node,
            so there will always be a single daemon instance running in each legion.
            Once the lord dies a daemon will be spawned on another node.

            .. note:: uWSGI 1.9.9+ required.

        """
        prefix = 'legion-' if for_legion else ''

        if '.pid' in command_or_pid_path:

            if background:
                # Attach a command/daemon to the master process managed by a pidfile (the command must daemonize)
                self._set(prefix + 'smart-attach-daemon', command_or_pid_path, multi=True)

            else:
                # Attach a command/daemon to the master process managed by a pidfile (the command must NOT daemonize)
                self._set(prefix + 'smart-attach-daemon2', command_or_pid_path, multi=True)

        else:
            if background:
                raise ConfigurationError('Background flag is only supported for pid-governed commands')

            if control:
                # todo needs check
                self._set('attach-control-daemon', command_or_pid_path, multi=True)

            else:
                # Attach a command/daemon to the master process (the command has to remain in foreground)
                self._set(prefix + 'attach-daemon', command_or_pid_path, multi=True)

        return self._section

    def attach_process(
            self, command, for_legion=False, broken_counter=None, pidfile=None, control=None, daemonize=None,
            touch_reload=None, signal_stop=None, signal_reload=None, honour_stdin=None,
            uid=None, gid=None, new_pid_ns=None, change_dir=None):
        """Attaches a command/daemon to the master process.

        This will allow the uWSGI master to control/monitor/respawn this process.

        http://uwsgi-docs.readthedocs.io/en/latest/AttachingDaemons.html

        :param str|unicode command: The command line to execute.

        :param bool for_legion: Legion daemons will be executed only on the legion lord node,
            so there will always be a single daemon instance running in each legion.
            Once the lord dies a daemon will be spawned on another node.

        :param int broken_counter: Maximum attempts before considering a daemon "broken".

        :param str|unicode pidfile: The pidfile path to check (enable smart mode).

        :param bool control: If True, the daemon becomes a `control` one:
            if it dies the whole uWSGI instance dies.

        :param bool daemonize: Daemonize the process (enable smart2 mode).

        :param list|str|unicode touch_reload: List of files to check:
            whenever they are 'touched', the daemon is restarted

        :param int signal_stop: The signal number to send to the daemon when uWSGI is stopped.

        :param int signal_reload: The signal number to send to the daemon when uWSGI is reloaded.

        :param bool honour_stdin: The signal number to send to the daemon when uWSGI is reloaded.

        :param str|unicode|int uid: Drop privileges to the specified uid.

            .. note:: Requires master running as root.

        :param str|unicode|int gid: Drop privileges to the specified gid.

            .. note:: Requires master running as root.

        :param bool new_pid_ns: Spawn the process in a new pid namespace.

            .. note:: Requires master running as root.

            .. note:: Linux only.

        :param str|unicode change_dir: Use chdir() to the specified directory
            before running the command.

        """
        line = []
        locals_ = locals()

        aliases = {
            'command': 'cmd',
            'broken_counter': 'freq',
            'touch_reload': 'touch',
            'signal_stop': 'stopsignal',
            'signal_reload': 'reloadsignal',
            'honour_stdin': 'stdin',
            'new_pid_ns': 'ns_pid',
            'change_dir': 'chdir',
        }

        bool_chunks = ['control', 'daemonize', 'honour_stdin']

        chunks = [
            'command', 'broken_counter', 'pidfile', 'control', 'daemonize',
            'signal_stop', 'signal_reload', 'honour_stdin',
            'uid', 'gid', 'new_pid_ns', 'change_dir',
        ]

        for chunk in chunks:
            val = locals_[chunk]

            if val is not None:
                val = 1 if chunk in bool_chunks else val
                line.append('%s=%s' % (aliases.get(chunk, chunk), val))

        if touch_reload:
            if not isinstance(touch_reload, list):
                touch_reload = [touch_reload]

            line.append('touch=%s' % ';'.join(touch_reload))

        prefix = 'legion-' if for_legion else ''

        self._set(prefix + 'attach-daemon2', ','.join(line), multi=True)

        return self._section
