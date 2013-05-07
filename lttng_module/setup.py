from distutils.core import setup, Extension

autopilot_tracepoint = Extension('tracepoint',
                                 libraries=['lttng-ust'],
                                 include_dirs=['./'],
                                 sources = ['emit_tracepoint.c'])

setup (name = 'Autopilot lttng provider',
       version = '1.0',
       description = 'Emits a lttng tracepoint message',
       ext_modules = [autopilot_tracepoint])
