Getting Started
+++++++++++++++

Autopilot is a tool for *functional* testing an application. The basic idea is that we simulate user input at a very low level, and verify that the application under test responde the way we expect it to. Autopilot provides two main facilities to make this possible:

1. **Input Device Emulation**. Autopilot provides several classes that are able to generate X11 input device events. Keyboard and Mouse events are trivial to generate, and other devices may be added in the future. These events are generated using the `xtest` X11 extension, which means that generated events are processed in the same manner as "real" device events (as opposed to some other frameworks that artificially insert events into the application under tests's event loop).

2. **State Introspection**. Autopilot provides several methods of inspecting the applications state, and using the results of that introspection in a test.

Autopilot builds on top of several python unity testing tools. In particular, autopilot tests are written in much the same manner as a python unit test would be.
