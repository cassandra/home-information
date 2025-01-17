class ZmSimConstants:

    # TODO: ZoneMinder's API using naive times with no timezone info.
    # Internally, ZoneMinder does have a timezone defined, but it is up to
    # the external API user to know what that is (unfortunately). Thus, in
    # the ZoneMinder integration, it has a timezone attribute the user must
    # set and ensure it matches ZoneMinder.  When simulating ZoneMinder's
    # API we also have to ensure the integration configuration matches the
    # timezone used in the simulator.  For now, we just hardcode this and
    # expect the developer to make sure the integration setting matches. It
    # would be better if the simulator allowed this to be adjusable through
    # the UI.
    #
    TIMEZONE_NAME = 'America/Chicago'
    
