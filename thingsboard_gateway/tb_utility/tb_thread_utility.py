import threading


def threadsafe_function(fcn):
    """decorator making sure that the decorated function is thread safe"""
    lock = threading.RLock()

    def new(*args, **kwargs):
        """Lock and call the decorated function
           Unless kwargs['threadsafe'] == False
        """
        threadsafe = kwargs.pop('threadsafe', True)
        if threadsafe:
            lock.acquire()
        try:
            ret = fcn(*args, **kwargs)
        except Exception as excpt:
            raise excpt
        finally:
            if threadsafe:
                lock.release()
        return ret

    return new
