class Singleton(type):
    """
    Metaclass to provide Singleton pattern to any class.
    """
    def __init__(cls, *args, **kwargs):
        super(Singleton, cls).__init__(*args, **kwargs)
        cls._instance = None

    def __call__(cls, *args, **kwargs):
        # If instance still does not exist, create it.
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__call__(*args, **kwargs)
        # Otherwise, return our rather well-known instance.
        return cls._instance
