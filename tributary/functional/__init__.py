from __future__ import print_function
from concurrent.futures import ThreadPoolExecutor, _base
from concurrent.futures.thread import _WorkItem
import concurrent.futures.thread as cft

try:
    # For Travis/ python 3.6
    from concurrent.futures.thread import BrokenThreadPool
except ImportError:
    BrokenThreadPool = Exception


_EXECUTOR = ThreadPoolExecutor(max_workers=2)


def submit(fn, *args, **kwargs):
    if _EXECUTOR is None:
        raise RuntimeError('Already stopped!')
    self = _EXECUTOR
    with self._shutdown_lock:
        if self._broken:
            raise BrokenThreadPool(self._broken)

        if self._shutdown:
            raise RuntimeError('cannot schedule new futures after shutdown')
        if cft._shutdown:
            raise RuntimeError('cannot schedule new futures after'
                               'interpreter shutdown')

        f = _base.Future()
        w = _WorkItem(f, fn, args, kwargs)

        self._work_queue.put(w)
        self._adjust_thread_count()
        return f


def run_submit(fn, function_to_call, *args, **kwargs):
    try:
        f = submit(fn, *args, **kwargs)
    except RuntimeError:
        # means we've shutdown, stop
        return

    if function_to_call:
        f.add_done_callback(lambda fut: function_to_call(fut.result()) if fut.result() else None)


def pipeline(foos, foo_callbacks, foo_kwargs=None, on_data=print, on_data_kwargs=None):
    global _EXECUTOR
    if _EXECUTOR is None:
        _EXECUTOR = ThreadPoolExecutor(max_workers=2)

    foo_kwargs = foo_kwargs or []
    on_data_kwargs = on_data_kwargs or {}

    # organize args for functional pipeline
    assembled = []
    for i, foo in enumerate(foos):
        cb = foo_callbacks[i] if i < len(foo_callbacks) else 'on_data'
        kwargs = foo_kwargs[i] if i < len(foo_kwargs) else {}
        assembled.append((foo, cb, kwargs))

    # assemble pipeline
    assembled.reverse()
    lambdas = [lambda d, f=on_data: run_submit(f, None, d, **on_data_kwargs)]
    for i, a in enumerate(assembled):
        foo, cb, kwargs = a
        function_to_call = lambdas[i]
        kwargs[cb] = function_to_call

        if i != len(assembled)-1:
            lambdas.append(lambda d, kw=kwargs, f=foo: run_submit(f, function_to_call, d, **kw))
            lambdas[-1].__name__ = foo.__name__
        else:
            lambdas.append(lambda kw=kwargs, f=foo: run_submit(f, function_to_call, **kw))
            lambdas[-1].__name__ = foo.__name__

    # start entrypoint
    lambdas[-1]()


def stop():
    global _EXECUTOR
    _EXECUTOR.shutdown(False)
    _EXECUTOR._threads.clear()
    cft._threads_queues.clear()
    _EXECUTOR = None
