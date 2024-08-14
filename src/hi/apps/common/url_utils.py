from typing import List

# Prefixes of URL paths to strip all additional pathing when forming
# the name that we count (via Datadog). Goal is to:
#
#  1) Consolidate counts by type of operation.
#  2) Keep the cardinality of metrics down (Datadog charges by number of custom metrics).
#
# Note that this dictates a certain ordering we prefer in the URL
# structures. We want all the high-cardinality components at the end of
# the URL.
#
WAA_PATH_STRIP_REMAINING_SET = {
    '/game',
    '/api/user/info',
    '/img/avatar',
    '/img/map/usa',
    '/img/map/region',
    '/img/award',
    '/img/badge',
    '/img/location',
}


def simplify_url_path( original_path        : str,
                       strip_remaining_set  : List[str] = WAA_PATH_STRIP_REMAINING_SET ):

    path = original_path
    if path[0] == '/':
        path = path[1:]
    if path and path[-1] == '/':
        path = path[0:-1]

    path_components = path.split('/')

    prefix_path = '/'
    for end_idx in range( len(path_components) ):
        prefix_path = '/' + '/'.join( path_components[0:end_idx] )
        if prefix_path in strip_remaining_set:
            return prefix_path
        continue

    return original_path
