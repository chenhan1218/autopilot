#include <Python.h>

#define TRACEPOINT_CREATE_PROBES
/*
 * The header containing our TRACEPOINT_EVENTs.
 */
#define TRACEPOINT_DEFINE
#include "emit_tracepoint.h"

static PyObject *
emit_tracepoint(PyObject *self, PyObject *args)
{
    const char *mesg_text;

    if(!PyArg_ParseTuple(args, "s", &mesg_text))
    {
        return NULL;
    }
    tracepoint(emit_tracepoint, message, mesg_text);

    Py_RETURN_NONE;
}

static PyMethodDef EmitMethods[] = {
    {"tracepoint", emit_tracepoint, METH_VARARGS, "Generate a tracepoint message."},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};


PyMODINIT_FUNC
initemit(void)
{
    (void) Py_InitModule("emit", EmitMethods);
}
