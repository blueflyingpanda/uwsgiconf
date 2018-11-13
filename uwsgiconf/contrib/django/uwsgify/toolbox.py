import inspect
import os


if False:  # pragma: nocover
    from uwsgiconf.base import Section


def find_project_dir():
    """Runs up the stack to find the location of manage.py
    which will be considered a project base path.

    :rtype: str|unicode
    """
    frame = inspect.currentframe()

    while True:
        frame = frame.f_back
        fname = frame.f_globals['__file__']

        if os.path.basename(fname) == 'manage.py':
            break

    return os.path.dirname(fname)


def get_project_name(project_dir):
    """Return project name from project directory.

    :param str|unicode project_dir:
    :rtype: str|unicode
    """
    return os.path.basename(project_dir)


class SectionMutator(object):
    """Configuration file section mutator."""

    def __init__(self, section, dir_base, project_name, options):
        # todo maybe integrate envbox
        from django.conf import settings

        self.section = section  # type: Section
        self.dir_base = dir_base
        self.project_name = project_name
        self.settings = settings
        self.options = options

    @classmethod
    def get_pid_filepath(cls, project_name):
        """Return pidfile path for the given project.

        :param str|unicode project_name:
        :rtype: str|unicode

        """
        path_tpl = '/var/run/user/{user}/{project}_uwsgi.pid'
        # PID file path template. User dir to not to bother with permissions.

        return path_tpl.format(user=os.getuid(), project=project_name)

    @classmethod
    def get_fifo_filepath(cls, project_name):
        """Return master FIFO path for the given project.

        :param str|unicode project_name:
        :rtype: str|unicode

        """
        path_tpl = '/var/run/user/{user}/{project}_uwsgi.fifo'
        # FIFO file path template. User dir to not to bother with permissions.

        return path_tpl.format(user=os.getuid(), project=project_name)

    @classmethod
    def run(cls, dir_base, options):
        """Alternative constructor. Creates a mutator and returns section object.

        :param str|unicode dir_base:
        :param dict options:
        :rtype: Section

        """
        from uwsgiconf.utils import ConfModule

        name_module = ConfModule.default_name
        name_project = get_project_name(dir_base)
        path_conf = os.path.join(dir_base, name_module)

        if os.path.exists(path_conf):
            # Read an existing config for further modification of first section.
            section = cls._get_section_existing(name_module, name_project)

        else:
            # Create section on-fly.
            section = cls._get_section_new(dir_base)

        wrapped = cls(
            section=section,
            dir_base=dir_base,
            project_name=name_project,
            options=options)

        wrapped.mutate()

        return section

    @classmethod
    def _get_section_existing(self, name_module, name_project):
        """Loads config section from existing configuration file (aka uwsgicfg.py)

        :param str|unicode name_module:
        :param str|unicode name_project:
        :rtype: Section

        """
        from importlib import import_module

        from uwsgiconf.settings import CONFIGS_MODULE_ATTR

        config = getattr(
            import_module(os.path.splitext(name_module)[0], package=name_project),
            CONFIGS_MODULE_ATTR)[0]

        return config.sections[0]

    @classmethod
    def _get_section_new(cls, dir_base):
        """Creates a new section with default settings.

        :param str|unicode dir_base:
        :rtype: Section

        """
        from uwsgiconf.presets.nice import PythonSection

        section = PythonSection(
            wsgi_module='%s/wsgi.py' % dir_base,

        ).networking.register_socket(
            PythonSection.networking.sockets.http('127.0.0.1:8000')
        )

        return section

    def contribute_static(self):
        """Contributes static and media file serving settings to an existing section."""

        options = self.options
        if options['compile'] or not options['use_static_handler']:
            return

        from django.core import management

        settings = self.settings
        statics = self.section.statics
        statics.register_static_map(settings.STATIC_URL, settings.STATIC_ROOT)
        statics.register_static_map(settings.MEDIA_URL, settings.MEDIA_ROOT)

        management.call_command('collectstatic', clear=True, interactive=False)

    def contribute_error_pages(self):
        """Contributes generic static error massage pages to an existing section."""

        self.section.routing.set_error_pages(
            common_prefix=os.path.join(self.settings.STATIC_ROOT, 'uwsgify'))

    def mutate(self):
        """Mutates current section."""
        section = self.section
        project_name = self.project_name

        main = section.main_process
        main.set_owner_params(os.getuid(), os.getegid())
        main.set_naming_params(prefix='[%s] ' % project_name)
        main.set_pid_file(
            self.get_pid_filepath(project_name),
            before_priv_drop=False,  # For vacuum to cleanup properly.
            safe=True
        )

        section.master_process.set_basic_params(fifo_file=self.get_fifo_filepath(project_name))

        # todo maybe autoreload in debug

        apps = section.applications
        apps.set_basic_params(
            manage_script_name=True,
        )

        self.contribute_error_pages()
        self.contribute_static()


def run_uwsgi(config_section, compile_only=False):
    """Runs uWSGI using the given section configuration.

    :param Section config_section:
    :param bool compile_only: Do not run, only compile and output configuration file for run.

    """
    config = config_section.as_configuration()

    if compile_only:
        config.print_ini()
        return

    config_path = config.tofile()
    os.execvp('uwsgi', ['uwsgi', '--ini=%s' % config_path])
