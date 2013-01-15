import testtools
import logging
import sys
import testcase
from autopilot.globals import (get_log_verbose)

logger = logging.getLogger(__name__)


class VerboseTextTestResult(testtools.TextTestResult):
    def _setup_logging(self):
        log_format = "%(asctime)s %(levelname)s %(module)s:%(lineno)d - %(message)s"
        formatter = testcase.MyFormatter(log_format)
        if get_log_verbose():
            stderr_handler = logging.StreamHandler(stream=sys.stderr)
            stderr_handler.setFormatter(formatter)
            logger.addHandler(stderr_handler)

    def _teardown_logging(self):
        handlers = [h for h in logger.handlers]
        for h in handlers:
            logger.removeHandler(h)

    def addSuccess(self, test, details=None):
        self._setup_logging()
        super(VerboseTextTestResult, self).addSuccess(test, details)
        logger.debug("%s: ok" % (test.id()))
        self._teardown_logging()

    def addError(self, test, err=None, details=None):
        self._setup_logging()
        super(VerboseTextTestResult, self).addError(test, err, details)
        logger.debug("%s: ERROR" % (test.id()))
        self._teardown_logging()

    def addFailure(self, test, err=None, details=None):
        self._setup_logging()
        super(VerboseTextTestResult, self).addFailure(test, err, details)
        logger.debug("%s: FAIL" % (test.id()))
        self._teardown_logging()

