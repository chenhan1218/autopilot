
#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER emit_tracepoint

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "./emit_tracepoint.h"

#ifdef __cplusplus
extern "C"{
#endif /* __cplusplus */


#if !defined(EMIT_TRACEPOINT_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define EMIT_TRACEPOINT_H

#include <lttng/tracepoint.h>

TRACEPOINT_EVENT(
    emit_tracepoint,
    message,
    TP_ARGS(char *, text),
    TP_FIELDS(
        ctf_string(message, text)
    )
)

#endif /* EMIT_TRACEPOINT_H */

#include <lttng/tracepoint-event.h>

#ifdef __cplusplus
}
#endif /* __cplusplus */

