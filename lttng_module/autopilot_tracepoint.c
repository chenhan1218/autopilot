
#define TRACEPOINT_CREATE_PROBES
/*
 * The header containing our TRACEPOINT_EVENTs.
 */
#define TRACEPOINT_DEFINE
#include "autopilot_tracepoint.h"

/// Python module stuff below here:

#include <Python.h>

static PyObject *
emit_test_started(PyObject *self, PyObject *args)
{
    const char *mesg_text;

    if(!PyArg_ParseTuple(args, "s", &mesg_text))
    {
        return NULL;
    }
    tracepoint(com_canonical_autopilot, test_event, "started", mesg_text);

    Py_RETURN_NONE;
}

static PyObject *
emit_test_ended(PyObject *self, PyObject *args)
{
    const char *mesg_text;

    if(!PyArg_ParseTuple(args, "s", &mesg_text))
    {
        return NULL;
    }
    tracepoint(com_canonical_autopilot, test_event, "ended", mesg_text);

    Py_RETURN_NONE;
}

static PyMethodDef TracepointMethods[] = {
    {"emit_test_started", emit_test_started, METH_VARARGS, "Generate a tracepoint for test started."},
    {"emit_test_ended", emit_test_ended, METH_VARARGS, "Generate a tracepoint for test started."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
inittracepoint(void)
{
    (void) Py_InitModule("tracepoint", TracepointMethods);
}
