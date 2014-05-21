# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

"""Base module for application launchers."""

import fixtures
from gi.repository import GLib, UpstartAppLaunch
import json
import logging
import os
import psutil
import subprocess
import signal
from testtools.content import content_from_file, text_content

from autopilot._timeout import Timeout
from autopilot.application._environment import (
    GtkApplicationEnvironment,
    QtApplicationEnvironment,
)
from autopilot.introspection import (
    get_proxy_object_for_existing_process,
)

_logger = logging.getLogger(__name__)


class ApplicationLauncher(fixtures.Fixture):

    """A class that knows how to launch an application with a certain type of
    introspection enabled.

    """

    def __init__(self, case_addDetail=None, emulator_base=None,
                 dbus_bus='session'):
        super().__init__()
        self.case_addDetail = case_addDetail or self.addDetail
        self.emulator_base = emulator_base
        self.dbus_bus = dbus_bus

    def setUp(self):
        super().setUp()
        if self.dbus_bus != 'session':
            self.useFixture(
                fixtures.EnvironmentVariable(
                    "DBUS_SESSION_BUS_ADDRESS",
                    self.dbus_bus
                )
            )

    def launch(self, *arguments):
        raise NotImplementedError("Sub-classes must implement this method.")


class UpstartApplicationLauncher(ApplicationLauncher):

    """A launcher class that launches applications with UpstartAppLaunch."""

    Timeout = object()
    Failed = object()
    Started = object()
    Stopped = object()

    def launch(self, app_id, app_uris=[]):
        """Launch an application with upstart.

        This method launches an application via the ``upstart-app-launch``
        library, on platforms that support it.

        Usage is similar to the
        :py:meth:`NormalApplicationLauncher.launch`::

            from autopilot.application import ClickApplicationLauncher
            launcher = ClickApplicationLauncher()
            launcher.setUp()
            app_proxy = launcher.launch('gallery-app')

        :param application_name: The name of the application to launch.
        :keyword emulator_base: If set, specifies the base class to be used for
            all emulators for this loaded application.

        :raises RuntimeError: If the specified application cannot be launched.

        :returns: proxy object for the launched package application

        """
        if isinstance(app_uris, (str, bytes)):
            app_uris = [app_uris]
        _logger.info(
            "Attempting to launch application '%s' with URIs '%s' via "
            "upstart-app-launch",
            app_id,
            ','.join(app_uris)
        )
        state = {}
        state['loop'] = self._get_glib_loop()
        state['expected_app_id'] = app_id
        state['message'] = ''

        UpstartAppLaunch.observer_add_app_failed(self._on_failed, state)
        UpstartAppLaunch.observer_add_app_started(self._on_started, state)
        UpstartAppLaunch.observer_add_app_focus(self._on_started, state)
        GLib.timeout_add_seconds(10.0, self._on_timeout, state)

        self._launch_app(app_id, app_uris)
        state['loop'].run()
        UpstartAppLaunch.observer_delete_app_failed(self._on_failed)
        UpstartAppLaunch.observer_delete_app_started(self._on_started)
        UpstartAppLaunch.observer_delete_app_focus(self._on_started)
        self._maybe_add_application_cleanups(state)
        self._check_status_error(
            state.get('status', None),
            state.get('message', '')
        )
        pid = self._get_pid_for_launched_app(app_id)
        proxy_object = get_proxy_object_for_existing_process(
            dbus_bus=self.dbus_bus,
            emulator_base=self.emulator_base,
            pid=pid
        )
        return proxy_object

    @staticmethod
    def _on_failed(launched_app_id, failure_type, state):
        if launched_app_id == state['expected_app_id']:
            if failure_type == UpstartAppLaunch.AppFailed.CRASH:
                state['message'] = 'Application crashed.'
            elif failure_type == UpstartAppLaunch.AppFailed.START_FAILURE:
                state['message'] = 'Application failed to start.'
            state['status'] = UpstartApplicationLauncher.Failed
            state['loop'].quit()

    @staticmethod
    def _on_started(launched_app_id, state):
        if launched_app_id == state['expected_app_id']:
            state['status'] = UpstartApplicationLauncher.Started
            state['loop'].quit()

    @staticmethod
    def _on_stopped(stopped_app_id, state):
        if stopped_app_id == state['expected_app_id']:
            state['status'] = UpstartApplicationLauncher.Stopped
            state['loop'].quit()

    @staticmethod
    def _on_timeout(state):
        state['status'] = UpstartApplicationLauncher.Timeout
        state['loop'].quit()

    def _maybe_add_application_cleanups(self, state):
        if state.get('status', None) == UpstartApplicationLauncher.Started:
            app_id = state['expected_app_id']
            self.addCleanup(self._stop_application, app_id)
            self.addCleanup(self._attach_application_log, app_id)

    def _attach_application_log(self, app_id):
        log_path = UpstartAppLaunch.application_log_path(app_id)
        if log_path and os.path.exists(log_path):
            self.case_addDetail(
                "Application Log (%s)" % app_id,
                content_from_file(log_path)
            )

    def _stop_application(self, app_id):
        state = {}
        state['loop'] = self._get_glib_loop()
        state['expected_app_id'] = app_id

        UpstartAppLaunch.observer_add_app_stop(self._on_stopped, state)
        GLib.timeout_add_seconds(10.0, self._on_timeout, state)

        UpstartAppLaunch.stop_application(app_id)
        state['loop'].run()
        UpstartAppLaunch.observer_delete_app_stop(self._on_stopped)

        if state.get('status', None) == UpstartApplicationLauncher.Timeout:
            _logger.error(
                "Timed out waiting for Application with app_id '%s' to stop.",
                app_id
            )

    @staticmethod
    def _get_glib_loop():
        return GLib.MainLoop()

    @staticmethod
    def _get_pid_for_launched_app(app_id):
        return UpstartAppLaunch.get_primary_pid(app_id)

    @staticmethod
    def _launch_app(app_name, app_uris):
        UpstartAppLaunch.start_application_test(app_name, app_uris)

    @staticmethod
    def _check_status_error(status, extra_message=''):
        message_parts = []
        if status == UpstartApplicationLauncher.Timeout:
            message_parts.append(
                "Timed out while waiting for application to launch"
            )
        elif status == UpstartApplicationLauncher.Failed:
            message_parts.append("Application Launch Failed")
        if message_parts and extra_message:
            message_parts.append(extra_message)
        if message_parts:
            raise RuntimeError(': '.join(message_parts))


class ClickApplicationLauncher(UpstartApplicationLauncher):

    """Fixture to manage launching a Click application."""

    def launch(self, package_id, app_name=None, app_uris=[]):
        """Launch a click package application with introspection enabled.

        This method takes care of launching a click package with introspection
        exabled. You probably want to use this method if your application is
        packaged in a click application, or is started via upstart.

        Usage is similar to the
        :py:meth:`NormalApplicationLauncher.launch`::

            from autopilot.application import ClickApplicationLauncher
            launcher = ClickApplicationLauncher()
            launcher.setUp()
            app_proxy = launcher.launch('com.ubuntu.dropping-letters')

        :param package_id: The Click package name you want to launch. For
            example: ``com.ubuntu.dropping-letters``
        :param app_name: Currently, only one application can be packaged in a
            click package, and this parameter can be left at None. If
            specified, it should be the application name you wish to launch.
        :param app_uris: Parameters used to launch the click package. This
            parameter will be left empty if not used.

        :raises RuntimeError: If the specified package_id cannot be found in
            the click package manifest.
        :raises RuntimeError: If the specified app_name cannot be found within
            the specified click package.

        :returns: proxy object for the launched package application

        """
        if isinstance(app_uris, (str, bytes)):
            app_uris = [app_uris]
        _logger.info(
            "Attempting to launch click application '%s' from click package "
            " '%s' and URIs '%s'",
            app_name if app_name is not None else "(default)",
            package_id,
            ','.join(app_uris)
        )
        app_id = _get_click_app_id(package_id, app_name)
        return self._do_upstart_launch(app_id, app_uris)

    def _do_upstart_launch(self, app_id, app_uris):
        return super().launch(app_id, app_uris)


class NormalApplicationLauncher(ApplicationLauncher):

    """Fixture to manage launching an application."""

    def launch(self, application, arguments=[], app_type=None, cwd=None,
               capture_output=True):
        """Launch an application and return a proxy object.

        Use this method to launch an application and start testing it. The
        list of arguments passed in ``application`` are used as arguments to
        the application to launch. Additional keyword arguments are used to
        control the manner in which the application is launched.

        This method is designed to be flexible enough to launch all supported
        types of applications. Autopilot can automatically determine how to
        enable introspection support for dynamically linked binary
        applications. For example, to launch a binary Gtk application, a test
        might start with::

            from autopilot.application import NormalApplicationLauncher
            launcher = NormalApplicationLauncher()
            launcher.setUp()
            app_proxy = launcher.launch('gedit')

        For use within a testcase, use useFixture:

            launcher = self.useFixture(NormalApplicationLauncher())
            app_proxy = launcher.launch('gedit')

        Applications can be given command line arguments by supplying an
        ``arguments`` argument to this method. For example, if we want to
        launch ``gedit`` with a certain document loaded, we might do this::

            app_proxy = launcher.launch(
                'gedit', arguments=['/tmp/test-document.txt'])

        ... a Qt5 Qml application is launched in a similar fashion::

            app_proxy = launcher.launch(
                'qmlscene', arguments=['my_scene.qml'])

        If you wish to launch an application that is not a dynamically linked
        binary, you must specify the application type. For example, a Qt4
        python application might be launched like this::

            app_proxy = launcher.launch(
                'my_qt_app.py', app_type='qt')

        Similarly, a python/Gtk application is launched like so::

            app_proxy = launcher.launch(
                'my_gtk_app.py', app_type='gtk')

        :param application: The application to launch. The application can be
            specified as:

             * A full, absolute path to an executable file.
               (``/usr/bin/gedit``)
             * A relative path to an executable file.
               (``./build/my_app``)
             * An app name, which will be searched for in $PATH (``my_app``)

        :keyword arguments: If set, the list of arguments is passed to the
            launched app.

        :keyword app_type: If set, provides a hint to autopilot as to which
            kind of introspection to enable. This is needed when the
            application you wish to launch is *not* a dynamically linked
            binary. Valid values are 'gtk' or 'qt'. These strings are case
            insensitive.

        :keyword launch_dir: If set to a directory that exists the process
            will be launched from that directory.

        :keyword capture_output: If set to True (the default), the process
            output will be captured and attached to the test as test detail.

        :return: A proxy object that represents the application. Introspection
         data is retrievable via this object.

        """
        _logger.info(
            "Attempting to launch application '%s' with arguments '%s' as a "
            "normal process",
            application,
            ' '.join(arguments)
        )
        app_path = _get_application_path(application)
        app_path, arguments = self._setup_environment(
            app_path, app_type, *arguments)
        self.process = self._launch_application_process(
            app_path, capture_output, cwd, *arguments)
        proxy_object = get_proxy_object_for_existing_process(
            dbus_bus=self.dbus_bus,
            emulator_base=self.emulator_base,
            process=self.process,
            pid=self.process.pid
        )
        return proxy_object

    def _setup_environment(self, app_path, app_type, *arguments):
        app_env = self.useFixture(
            _get_application_environment(app_type, app_path)
        )
        return app_env.prepare_environment(
            app_path,
            list(arguments),
        )

    def _launch_application_process(self, app_path, capture_output, cwd,
                                    *arguments):
        process = launch_process(
            app_path,
            arguments,
            capture_output,
            cwd=cwd,
        )

        self.addCleanup(self._kill_process_and_attach_logs, process, app_path)
        return process

    def _kill_process_and_attach_logs(self, process, app_path):
        stdout, stderr, return_code = _kill_process(process)
        self.case_addDetail(
            'process-return-code (%s)' % app_path,
            text_content(str(return_code))
        )
        self.case_addDetail(
            'process-stdout (%s)' % app_path,
            text_content(stdout)
        )
        self.case_addDetail(
            'process-stderr (%s)' % app_path,
            text_content(stderr)
        )


def launch_process(application, args, capture_output=False, **kwargs):
    """Launch an autopilot-enabled process and return the process object."""
    commandline = [application]
    commandline.extend(args)
    _logger.info("Launching process: %r", commandline)
    cap_mode = None
    if capture_output:
        cap_mode = subprocess.PIPE
    process = subprocess.Popen(
        commandline,
        stdin=subprocess.PIPE,
        stdout=cap_mode,
        stderr=cap_mode,
        close_fds=True,
        preexec_fn=os.setsid,
        universal_newlines=True,
        **kwargs
    )
    return process


def _get_click_app_id(package_id, app_name=None):
    for pkg in _get_click_manifest():
        if pkg['name'] == package_id:
            if app_name is None:
                # py3 dict.keys isn't indexable.
                app_name = list(pkg['hooks'].keys())[0]
            elif app_name not in pkg['hooks']:
                raise RuntimeError(
                    "Application '{}' is not present within the click "
                    "package '{}'.".format(app_name, package_id))

            return "{0}_{1}_{2}".format(package_id, app_name, pkg['version'])
    raise RuntimeError(
        "Unable to find package '{}' in the click manifest."
        .format(package_id)
    )


def _get_click_manifest():
    """Return the click package manifest as a python list."""
    # get the whole click package manifest every time - it seems fast enough
    # but this is a potential optimisation point for the future:
    click_manifest_str = subprocess.check_output(
        ["click", "list", "--manifest"],
        universal_newlines=True
    )
    return json.loads(click_manifest_str)


def _get_application_environment(app_type=None, app_path=None):
    if app_type is None and app_path is None:
        raise ValueError("Must specify either app_type or app_path.")
    try:
        if app_type is not None:
            return _get_app_env_from_string_hint(app_type)
        else:
            return get_application_launcher_wrapper(app_path)
    except (RuntimeError, ValueError) as e:
        _logger.error(str(e))
        raise RuntimeError(
            "Autopilot could not determine the correct introspection type "
            "to use. You can specify this by providing app_type."
        )


def get_application_launcher_wrapper(app_path):
    """Return an instance of :class:`ApplicationLauncher` that knows how to
    launch the application at 'app_path'.
    """
    # TODO: this is a teeny bit hacky - we call ldd to check whether this
    # application links to certain library. We're assuming that linking to
    # libQt* or libGtk* means the application is introspectable. This excludes
    # any non-dynamically linked executables, which we may need to fix further
    # down the line.

    try:
        ldd_output = subprocess.check_output(
            ["ldd", app_path],
            universal_newlines=True
        ).strip().lower()
    except subprocess.CalledProcessError as e:
        raise RuntimeError(str(e))
    if 'libqtcore' in ldd_output or 'libqt5core' in ldd_output:
        return QtApplicationEnvironment()
    elif 'libgtk' in ldd_output:
        return GtkApplicationEnvironment()
    return None


def _get_application_path(application):
    try:
        return subprocess.check_output(
            ['which', application],
            universal_newlines=True
        ).strip()
    except subprocess.CalledProcessError as e:
        raise ValueError(
            "Unable to find path for application {app}: {reason}"
            .format(app=application, reason=str(e))
        )


def _get_app_env_from_string_hint(hint):
    lower_hint = hint.lower()
    if lower_hint == 'qt':
        return QtApplicationEnvironment()
    elif lower_hint == 'gtk':
        return GtkApplicationEnvironment()

    raise ValueError("Unknown hint string: {hint}".format(hint=hint))


def _kill_process(process):
    """Kill the process, and return the stdout, stderr and return code."""
    stdout_parts = []
    stderr_parts = []
    _logger.info("waiting for process to exit.")
    _attempt_kill_pid(process.pid)
    for _ in Timeout.default():
        tmp_out, tmp_err = process.communicate()
        if isinstance(tmp_out, bytes):
            tmp_out = tmp_out.decode('utf-8', errors='replace')
        if isinstance(tmp_err, bytes):
            tmp_err = tmp_err.decode('utf-8', errors='replace')
        stdout_parts.append(tmp_out)
        stderr_parts.append(tmp_err)
        if not _is_process_running(process.pid):
            break
    else:
        _logger.info(
            "Killing process group, since it hasn't exited after "
            "10 seconds."
        )
        _attempt_kill_pid(process.pid, signal.SIGKILL)
    return u''.join(stdout_parts), u''.join(stderr_parts), process.returncode


def _attempt_kill_pid(pid, sig=signal.SIGTERM):
    try:
        _logger.info("Killing process %d", pid)
        os.killpg(pid, sig)
    except OSError:
        _logger.info("Appears process has already exited.")


def _is_process_running(pid):
    return psutil.pid_exists(pid)
