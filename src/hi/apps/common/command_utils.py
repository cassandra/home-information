class CommandLoggerMixin:
    """ Add to Command to provide convenience logger methods. """

    def message( self, message : str ):
        self.stdout.write( self.style.HTTP_INFO( message ))
        return

    def debug( self, message : str ):
        self.stdout.write( self.style.HTTP_INFO( message ))
        return

    def warning( self, message : str ):
        self.stdout.write( self.style.WARNING( message ))
        return

    def error( self, message : str ):
        self.stdout.write( self.style.ERROR( message ))
        return

    def success( self, message : str ):
        self.stdout.write( self.style.SUCCESS( message ))
        return

    def info( self, message : str ):
        self.stdout.write( self.style.MIGRATE_HEADING( message ))
        return
  
