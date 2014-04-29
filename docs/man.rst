Autopilot Man Page
##################

SYNOPSIS
--------
.. argparse_usage::

DESCRIPTION
-----------
autopilot is a tool for writing functional test suites for graphical applications for Ubuntu.

OPTIONS
-------
.. argparse_options::
General Options
       -h --help
            Get help from autopilot. This command can also be present after  a
            sub-command (such as run or list) to get help on the specific com‐
            mand.  Further options are restricted to particular autopilot com‐
            mands.

       suite
            Suites  are listed as a python dotted package name. Autopilot will
            do a recursive import in order to find all tests within  a  python
            package.

   list [options] suite [suite...]
       List the autopilot tests found in the given test suite.

       -ro, --run-order
            List tests in the order they will be run in, rather than alphabet‐
            ically (which is the default).

   run [options]suite [suite...]
       Run one or more test suites.

       -o FILE, --output FILE
            Specify where the test log should be written. Defaults to  stdout.
            If  a directory is specified the file will be created with a file‐
            name of <hostname>_<dd.mm.yyy_HHMMSS>.log

       -f FORMAT, --format FORMAT
            Specify the format for the log. Valid options are 'xml' and 'text'
            for JUnit XML and text format, respectively.

       -r, --record
            Record failed tests. Using this option requires the 'recordmydesk‐
            top' application be installed. By default, videos  are  stored  in
            /tmp/autopilot

       -rd DIR, --record-directory DIR
            Directory where videos should be stored (overrides the default set
            by the -r option).

       -v, --verbose
            Causes autopilot to print the test log to stdout while the test is
            running.
