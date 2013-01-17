import logging
import sys
from autopilot.globals import get_log_verbose
from autopilot.utilities import (LogFormatter,
                                 log_format)

logger = logging.getLogger(__name__)


class AutopilotVerboseResult(object):
    def _setup_logging(self):
        """Adds an appropriate stderr handler for logging."""
        logging_setup = getattr(self, "logging_setup", False)
        if get_log_verbose() and not logging_setup:
            formatter = LogFormatter(log_format)
            stderr_handler = logging.StreamHandler(stream=sys.stderr)
            stderr_handler.setFormatter(formatter)
            logger.addHandler(stderr_handler)
        self.logging_setup = True

    def _teardown_logging(self):
        """Removes all logging handlers"""
        handlers = [h for h in logger.handlers]
        for h in handlers:
            logger.removeHandler(h)
        self.logging_setup = False

    def _log(self, message):
        """Performs the actual message logging"""
        if get_log_verbose():
            logger.debug(message)

    def _log_details(self, details):
        """Logs the relavent test details"""
        for detail in details:
            # Skip the test-log as it was logged while the test executed
            if detail == "test-log":
                continue
            text = "%s: {{{\n%s}}}" % (detail, details[detail].as_text())
            self._log(text)

    def addSuccess(self, test, details=None):
        """Called for a successful test"""
        # Allow for different calling syntax used by the base class.
        self._setup_logging()
        if details is None:
            super(type(self), self).addSuccess(test)
        else:
            super(type(self), self).addSuccess(test, details)
        self._log("OK: %s" % (test.id()))
        self._teardown_logging()

    def addError(self, test, err=None, details=None):
        """Called for a test which failed with an error"""
        # Allow for different calling syntax used by the base class.
        # The xml path only uses 'err'. Use of 'err' can be
        # forced by raising TypeError when it is not specified.
        if err is None:
            raise TypeError
        self._setup_logging()
        if details is None:
            super(type(self), self).addError(test, err)
        else:
            super(type(self), self).addError(test, err, details)
        self._log("ERROR: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(test.getDetails())
        self._teardown_logging()

    def addFailure(self, test, err=None, details=None):
        """Called for a test which failed an assert"""
        # Allow for different calling syntax used by the base class.
        # The xml path only uses 'err' or 'details'. Use of 'err' can be
        # forced by raising TypeError when it is not specified.
        if err is None:
            raise TypeError
        self._setup_logging()
        if details is None:
            super(type(self), self).addFailure(test, err)
        else:
            super(type(self), self).addFailure(test, err, details)
        self._log("FAIL: %s" % (test.id()))
        if hasattr(test, "getDetails"):
            self._log_details(test.getDetails())
        self._teardown_logging()
