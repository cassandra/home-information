class Singleton:
    _instance = None

    def __new__( cls ):
        if cls._instance is None:
            cls._instance = super(Singleton, cls).__new__( cls )
            cls._instance.__init_singleton__()
        return cls._instance
