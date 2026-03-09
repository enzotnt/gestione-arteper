# TrueFlow Auto-Instrumentation
# This file is automatically loaded when Python starts (via PYTHONPATH)
import os
import sys

# Only activate if TRUEFLOW_ENABLED is set
if os.environ.get('TRUEFLOW_ENABLED', '0') == '1':
    # Add runtime injector to path
    injector_path = os.path.join(os.path.dirname(__file__), 'runtime_injector')
    if injector_path not in sys.path:
        sys.path.insert(0, injector_path)

    # Import and start the instrumentor
    try:
        from python_runtime_instrumentor import RuntimeInstrumentor

        # Configure from environment
        trace_dir = os.environ.get('TRUEFLOW_TRACE_DIR', os.path.join(os.path.dirname(__file__), 'traces'))
        socket_port = int(os.environ.get('TRUEFLOW_SOCKET_PORT', '5678'))
        modules_to_trace = os.environ.get('TRUEFLOW_MODULES', '').split(',') if os.environ.get('TRUEFLOW_MODULES') else None
        exclude_modules = os.environ.get('TRUEFLOW_EXCLUDE', 'logging,asyncio,concurrent,socket,threading').split(',')

        # Start tracing
        instrumentor = RuntimeInstrumentor(
            trace_dir=trace_dir,
            socket_port=socket_port,
            modules_to_trace=modules_to_trace,
            exclude_modules=exclude_modules
        )
        instrumentor.start()

        print(f"[TrueFlow] Runtime instrumentation active - traces: {trace_dir}, socket: {socket_port}")
    except Exception as e:
        print(f"[TrueFlow] Failed to start instrumentation: {e}")
