
#undef TRACEPOINT_PROVIDER
#define TRACEPOINT_PROVIDER com_canonical_autopilot

#undef TRACEPOINT_INCLUDE
#define TRACEPOINT_INCLUDE "./autopilot_tracepoint.h"

#ifdef __cplusplus
extern "C"{
#endif /* __cplusplus */


#if !defined(AUTOPILOT_TRACEPOINT_H) || defined(TRACEPOINT_HEADER_MULTI_READ)
#define AUTOPILOT_TRACEPOINT_H

#include <lttng/tracepoint.h>


TRACEPOINT_EVENT(
    com_canonical_autopilot,
    test_event,
    TP_ARGS(const char *, started_or_stopped, const char *, test_id),
    /* Next are the fields */
    TP_FIELDS(
        ctf_string(started_or_stopped, started_or_stopped)
        ctf_string(test_id, test_id)
    )
)

#endif /* AUTOPILOT_TRACEPOINT_H */

#include <lttng/tracepoint-event.h>

#ifdef __cplusplus
}
#endif /* __cplusplus */

