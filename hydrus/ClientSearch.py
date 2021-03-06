import calendar
from . import ClientConstants as CC
from . import ClientData
from . import ClientTags
import collections
import datetime
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusTags
from . import HydrusText
import re
import threading
import time

PREDICATE_TYPE_TAG = 0
PREDICATE_TYPE_NAMESPACE = 1
PREDICATE_TYPE_PARENT = 2
PREDICATE_TYPE_WILDCARD = 3
PREDICATE_TYPE_SYSTEM_EVERYTHING = 4
PREDICATE_TYPE_SYSTEM_INBOX = 5
PREDICATE_TYPE_SYSTEM_ARCHIVE = 6
PREDICATE_TYPE_SYSTEM_UNTAGGED = 7
PREDICATE_TYPE_SYSTEM_NUM_TAGS = 8
PREDICATE_TYPE_SYSTEM_LIMIT = 9
PREDICATE_TYPE_SYSTEM_SIZE = 10
PREDICATE_TYPE_SYSTEM_AGE = 11
PREDICATE_TYPE_SYSTEM_HASH = 12
PREDICATE_TYPE_SYSTEM_WIDTH = 13
PREDICATE_TYPE_SYSTEM_HEIGHT = 14
PREDICATE_TYPE_SYSTEM_RATIO = 15
PREDICATE_TYPE_SYSTEM_DURATION = 16
PREDICATE_TYPE_SYSTEM_MIME = 17
PREDICATE_TYPE_SYSTEM_RATING = 18
PREDICATE_TYPE_SYSTEM_SIMILAR_TO = 19
PREDICATE_TYPE_SYSTEM_LOCAL = 20
PREDICATE_TYPE_SYSTEM_NOT_LOCAL = 21
PREDICATE_TYPE_SYSTEM_NUM_WORDS = 22
PREDICATE_TYPE_SYSTEM_FILE_SERVICE = 23
PREDICATE_TYPE_SYSTEM_NUM_PIXELS = 24
PREDICATE_TYPE_SYSTEM_DIMENSIONS = 25
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT = 26
PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER = 27
PREDICATE_TYPE_SYSTEM_KNOWN_URLS = 28
PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS = 29
PREDICATE_TYPE_OR_CONTAINER = 30
PREDICATE_TYPE_LABEL = 31
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING = 32
PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS = 33
PREDICATE_TYPE_SYSTEM_HAS_AUDIO = 34
PREDICATE_TYPE_SYSTEM_MODIFIED_TIME = 35

SYSTEM_PREDICATE_TYPES = { PREDICATE_TYPE_SYSTEM_EVERYTHING, PREDICATE_TYPE_SYSTEM_INBOX, PREDICATE_TYPE_SYSTEM_ARCHIVE, PREDICATE_TYPE_SYSTEM_UNTAGGED, PREDICATE_TYPE_SYSTEM_NUM_TAGS, PREDICATE_TYPE_SYSTEM_LIMIT, PREDICATE_TYPE_SYSTEM_SIZE, PREDICATE_TYPE_SYSTEM_AGE, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, PREDICATE_TYPE_SYSTEM_HASH, PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_RATIO, PREDICATE_TYPE_SYSTEM_DURATION, PREDICATE_TYPE_SYSTEM_HAS_AUDIO, PREDICATE_TYPE_SYSTEM_MIME, PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_SIMILAR_TO, PREDICATE_TYPE_SYSTEM_LOCAL, PREDICATE_TYPE_SYSTEM_NOT_LOCAL, PREDICATE_TYPE_SYSTEM_NUM_WORDS, PREDICATE_TYPE_SYSTEM_FILE_SERVICE, PREDICATE_TYPE_SYSTEM_NUM_PIXELS, PREDICATE_TYPE_SYSTEM_DIMENSIONS, PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS, PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT, PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, PREDICATE_TYPE_SYSTEM_KNOWN_URLS, PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS }

IGNORED_TAG_SEARCH_CHARACTERS = '[](){}/\\"\'-_'
IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE = { ord( char ) : ' ' for char in IGNORED_TAG_SEARCH_CHARACTERS }

def ConvertTagToSearchable( tag ):
    
    if tag == '':
        
        return ''
        
    
    while '**' in tag:
        
        tag = tag.replace( '**', '*' )
        
    
    if IsComplexWildcard( tag ):
        
        return tag
        
    
    tag = tag.translate( IGNORED_TAG_SEARCH_CHARACTERS_UNICODE_TRANSLATE )
    
    tag = HydrusText.re_multiple_spaces.sub( ' ', tag )
    
    tag = tag.strip()
    
    return tag
    
def ConvertEntryTextToSearchText( entry_text ):
    
    wildcard_text = entry_text
    
    while '**' in wildcard_text:
        
        wildcard_text = wildcard_text.replace( '**', '*' )
        
    
    entry_text = ConvertTagToSearchable( entry_text )
    
    ( namespace, subtag ) = HydrusTags.SplitTag( entry_text )
    
    search_text = entry_text
    
    if len( subtag ) > 0 and not subtag.endswith( '*' ):
        
        search_text += '*'
        
    
    return ( wildcard_text, search_text )
    
def FilterPredicatesBySearchText( service_key, search_text, predicates ):
    
    tags_to_predicates = {}
    
    for predicate in predicates:
        
        ( predicate_type, value, inclusive ) = predicate.GetInfo()
        
        if predicate_type == PREDICATE_TYPE_TAG:
            
            tags_to_predicates[ value ] = predicate
            
        
    
    matching_tags = FilterTagsBySearchText( service_key, search_text, list( tags_to_predicates.keys() ) )
    
    matches = [ tags_to_predicates[ tag ] for tag in matching_tags ]
    
    return matches
    
def FilterTagsBySearchText( service_key, search_text, tags, search_siblings = True ):
    
    def compile_re( s ):
        
        regular_parts_of_s = s.split( '*' )
        
        escaped_parts_of_s = list(map( re.escape, regular_parts_of_s ))
        
        s = '.*'.join( escaped_parts_of_s )
        
        # \A is start of string
        # \Z is end of string
        # \s is whitespace
        
        if r'\:' in s:
            
            beginning = r'\A'
            
            s = s.replace( r'\:', r'(\:|.*\s)', 1 )
            
        elif s.startswith( '.*' ):
            
            beginning = r'(\A|\:)'
            
        else:
            
            beginning = r'(\A|\:|\s)'
            
        
        if s.endswith( '.*' ):
            
            end = r'\Z' # end of string
            
        else:
            
            end = r'(\s|\Z)' # whitespace or end of string
            
        
        return re.compile( beginning + s + end )
        
    
    re_predicate = compile_re( search_text )
    
    siblings_manager = HG.client_controller.tag_siblings_manager
    
    result = []
    
    for tag in tags:
        
        if search_siblings:
            
            possible_tags = siblings_manager.GetAllSiblings( service_key, tag )
            
        else:
            
            possible_tags = [ tag ]
            
        
        if not IsComplexWildcard( search_text ):
            
            possible_tags = list(map( ConvertTagToSearchable, possible_tags ))
            
        
        for possible_tag in possible_tags:
            
            if re_predicate.search( possible_tag ) is not None:
                
                result.append( tag )
                
                break
                
            
        
    
    return result
    
def IsComplexWildcard( search_text ):
    
    num_stars = search_text.count( '*' )
    
    if num_stars > 1:
        
        return True
        
    
    if num_stars == 1 and not search_text.endswith( '*' ):
        
        return True
        
    
    return False
    
def IsUnacceptableTagSearch( search_text ):
    
    if search_text in ( '', ':', '*' ):
        
        return True
        
    
    ( namespace, subtag ) = HydrusTags.SplitTag( search_text )
    
    if namespace == '*':
        
        return True
        
    
    return False
    
def SortPredicates( predicates ):
    
    key = lambda p: p.GetCount()
    
    predicates.sort( key = key, reverse = True )
    
    return predicates

SEARCH_TYPE_AND = 0
SEARCH_TYPE_OR = 1

class FileSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'File Search Context'
    SERIALISABLE_VERSION = 4
    
    def __init__( self, file_service_key = CC.COMBINED_FILE_SERVICE_KEY, tag_search_context = None, search_type = SEARCH_TYPE_AND, predicates = None ):
        
        if tag_search_context is None:
            
            tag_search_context = TagSearchContext()
            
        
        if predicates is None:
            
            predicates = []
            
        
        self._file_service_key = file_service_key
        self._tag_search_context = tag_search_context
        
        self._search_type = search_type
        
        self._predicates = predicates
        
        self._search_complete = False
        
        self._InitialiseTemporaryVariables()
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_predicates = [ predicate.GetSerialisableTuple() for predicate in self._predicates ]
        
        return ( self._file_service_key.hex(), self._tag_search_context.GetSerialisableTuple(), self._search_type, serialisable_predicates, self._search_complete )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( file_service_key, serialisable_tag_search_context, self._search_type, serialisable_predicates, self._search_complete ) = serialisable_info
        
        self._file_service_key = bytes.fromhex( file_service_key )
        self._tag_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_search_context )
        
        if HG.client_controller.IsBooted():
            
            services_manager = HG.client_controller.services_manager
            
            if not services_manager.ServiceExists( self._file_service_key ):
                
                self._file_service_key = CC.COMBINED_LOCAL_FILE_SERVICE_KEY
                
            
        
        self._predicates = [ HydrusSerialisable.CreateFromSerialisableTuple( pred_tuple ) for pred_tuple in serialisable_predicates ]
        
        self._InitialiseTemporaryVariables()
        
    
    def _InitialiseTemporaryVariables( self ):
        
        system_predicates = [ predicate for predicate in self._predicates if predicate.GetType() in SYSTEM_PREDICATE_TYPES ]
        
        self._system_predicates = FileSystemPredicates( system_predicates )
        
        tag_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == PREDICATE_TYPE_TAG ]
        
        self._tags_to_include = []
        self._tags_to_exclude = []
        
        for predicate in tag_predicates:
            
            tag = predicate.GetValue()
            
            if predicate.GetInclusive(): self._tags_to_include.append( tag )
            else: self._tags_to_exclude.append( tag )
            
        
        namespace_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == PREDICATE_TYPE_NAMESPACE ]
        
        self._namespaces_to_include = []
        self._namespaces_to_exclude = []
        
        for predicate in namespace_predicates:
            
            namespace = predicate.GetValue()
            
            if predicate.GetInclusive(): self._namespaces_to_include.append( namespace )
            else: self._namespaces_to_exclude.append( namespace )
            
        
        wildcard_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == PREDICATE_TYPE_WILDCARD ]
        
        self._wildcards_to_include = []
        self._wildcards_to_exclude = []
        
        for predicate in wildcard_predicates:
            
            wildcard = predicate.GetValue()
            
            if predicate.GetInclusive(): self._wildcards_to_include.append( wildcard )
            else: self._wildcards_to_exclude.append( wildcard )
            
        
        self._or_predicates = [ predicate for predicate in self._predicates if predicate.GetType() == PREDICATE_TYPE_OR_CONTAINER ]
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( file_service_key_hex, tag_service_key_hex, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            search_type = SEARCH_TYPE_AND
            
            new_serialisable_info = ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            # screwed up the serialisation code for the previous update, so these were getting swapped
            
            search_type = SEARCH_TYPE_AND
            include_current_tags = True
            
            new_serialisable_info = ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( file_service_key_hex, tag_service_key_hex, search_type, include_current_tags, include_pending_tags, serialisable_predicates, search_complete ) = old_serialisable_info
            
            tag_service_key = bytes.fromhex( tag_service_key_hex )
            
            tag_search_context = TagSearchContext( service_key = tag_service_key, include_current_tags = include_current_tags, include_pending_tags = include_pending_tags )
            
            serialisable_tag_search_context = tag_search_context.GetSerialisableTuple()
            
            new_serialisable_info = ( file_service_key_hex, serialisable_tag_search_context, search_type, serialisable_predicates, search_complete )
            
            return ( 4, new_serialisable_info )
            
        
    
    def GetFileServiceKey( self ): return self._file_service_key
    def GetNamespacesToExclude( self ): return self._namespaces_to_exclude
    def GetNamespacesToInclude( self ): return self._namespaces_to_include
    def GetORPredicates( self ): return self._or_predicates
    def GetPredicates( self ): return self._predicates
    def GetSystemPredicates( self ): return self._system_predicates
    
    def GetTagSearchContext( self ):
        
        return self._tag_search_context
        
    
    def GetTagsToExclude( self ): return self._tags_to_exclude
    def GetTagsToInclude( self ): return self._tags_to_include
    def GetWildcardsToExclude( self ): return self._wildcards_to_exclude
    def GetWildcardsToInclude( self ): return self._wildcards_to_include
    
    def HasNoPredicates( self ):
        
        return len( self._predicates ) == 0
        
    
    def IsComplete( self ): return self._search_complete
    
    def IsJustSystemEverything( self ):
        
        return len( self._predicates ) == 1 and self._system_predicates.HasSystemEverything()
        
    
    def SetComplete( self ): self._search_complete = True
    
    def SetFileServiceKey( self, file_service_key ):
        
        self._file_service_key = file_service_key
        
    
    def SetIncludeCurrentTags( self, value ):
        
        self._tag_search_context.include_current_tags = value
        
    
    def SetIncludePendingTags( self, value ):
        
        self._tag_search_context.include_pending_tags = value
        
    
    def SetPredicates( self, predicates ):
        
        self._predicates = predicates
        
        self._InitialiseTemporaryVariables()
        
    
    def SetTagServiceKey( self, tag_service_key ):
        
        self._tag_search_context.service_key = tag_service_key
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FILE_SEARCH_CONTEXT ] = FileSearchContext

class TagSearchContext( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_TAG_SEARCH_CONTEXT
    SERIALISABLE_NAME = 'Tag Search Context'
    SERIALISABLE_VERSION = 1
    
    def __init__( self, service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True ):
        
        self.service_key = service_key
        
        self.include_current_tags = include_current_tags
        self.include_pending_tags = include_pending_tags
        
    
    def _GetSerialisableInfo( self ):
        
        return ( self.service_key.hex(), self.include_current_tags, self.include_pending_tags )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( encoded_service_key, self.include_current_tags, self.include_pending_tags ) = serialisable_info
        
        self.service_key = bytes.fromhex( encoded_service_key )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_TAG_SEARCH_CONTEXT ] = TagSearchContext

class FavouriteSearchManager( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER
    SERIALISABLE_NAME = 'Favourite Search Manager'
    SERIALISABLE_VERSION = 1
    
    def __init__( self ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._favourite_search_rows = []
        
        self._lock = threading.Lock()
        self._dirty = False
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_favourite_search_info = []
        
        for row in self._favourite_search_rows:
            
            ( folder, name, file_search_context, synchronised, media_sort, media_collect ) = row
            
            serialisable_file_search_context = file_search_context.GetSerialisableTuple()
            
            if media_sort is None:
                
                serialisable_media_sort = None
                
            else:
                
                serialisable_media_sort = media_sort.GetSerialisableTuple()
                
            
            if media_collect is None:
                
                serialisable_media_collect = None
                
            else:
                
                serialisable_media_collect = media_collect.GetSerialisableTuple()
                
            
            serialisable_row = ( folder, name, serialisable_file_search_context, synchronised, serialisable_media_sort, serialisable_media_collect )
            
            serialisable_favourite_search_info.append( serialisable_row )
            
        
        return serialisable_favourite_search_info
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        self._favourite_search_rows = []
        
        for serialisable_row in serialisable_info:
            
            ( folder, name, serialisable_file_search_context, synchronised, serialisable_media_sort, serialisable_media_collect ) = serialisable_row
            
            file_search_context = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_search_context )
            
            if serialisable_media_sort is None:
                
                media_sort = None
                
            else:
                
                media_sort = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_media_sort )
                
            
            if serialisable_media_collect is None:
                
                media_collect = None
                
            else:
                
                media_collect = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_media_collect )
                
            
            row = ( folder, name, file_search_context, synchronised, media_sort, media_collect )
            
            self._favourite_search_rows.append( row )
            
        
    
    def GetFavouriteSearch( self, desired_folder_name, desired_name ):
        
        with self._lock:
            
            for ( folder, name, file_search_context, synchronised, media_sort, media_collect ) in self._favourite_search_rows:
                
                if folder == desired_folder_name and name == desired_name:
                    
                    return ( file_search_context, synchronised, media_sort, media_collect )
                    
                
            
        
        raise HydrusExceptions.DataMissing( 'Could not find a favourite search named "{}"!'.format( desired_name ) )
        
    
    def GetFavouriteSearchRows( self ):
        
        return list( self._favourite_search_rows )
        
    
    def GetFoldersToNames( self ):
        
        with self._lock:
            
            folders_to_names = collections.defaultdict( list )
            
            for ( folder, name, file_search_context, synchronised, media_sort, media_collect ) in self._favourite_search_rows:
                
                folders_to_names[ folder ].append( name )
                
            
            return folders_to_names
            
        
    
    def IsDirty( self ):
        
        with self._lock:
            
            return self._dirty
            
        
    
    def SetClean( self ):
        
        with self._lock:
            
            self._dirty = False
            
        
    
    def SetDirty( self ):
        
        with self._lock:
            
            self._dirty = True
            
        
    
    def SetFavouriteSearchRows( self, favourite_search_rows ):
        
        with self._lock:
            
            self._favourite_search_rows = list( favourite_search_rows )
            
            self._dirty = True
            
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_FAVOURITE_SEARCH_MANAGER ] = FavouriteSearchManager

class FileSystemPredicates( object ):
    
    def __init__( self, system_predicates, apply_implicit_limit = True ):
        
        self._has_system_everything = False
        
        self._inbox = False
        self._archive = False
        self._local = False
        self._not_local = False
        
        self._common_info = {}
        
        self._limit = None
        self._similar_to = None
        
        self._file_services_to_include_current = []
        self._file_services_to_include_pending = []
        self._file_services_to_exclude_current = []
        self._file_services_to_exclude_pending = []
        
        self._ratings_predicates = []
        
        self._duplicate_count_predicates = []
        
        self._king_filter = None
        
        self._file_viewing_stats_predicates = []
        
        new_options = HG.client_controller.new_options
        
        for predicate in system_predicates:
            
            predicate_type = predicate.GetType()
            value = predicate.GetValue()
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_EVERYTHING: self._has_system_everything = True
            if predicate_type == PREDICATE_TYPE_SYSTEM_INBOX: self._inbox = True
            if predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE: self._archive = True
            if predicate_type == PREDICATE_TYPE_SYSTEM_LOCAL: self._local = True
            if predicate_type == PREDICATE_TYPE_SYSTEM_NOT_LOCAL: self._not_local = True
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                ( operator, rule_type, rule, description ) = value
                
                if 'known_url_rules' not in self._common_info:
                    
                    self._common_info[ 'known_url_rules' ] = []
                    
                
                self._common_info[ 'known_url_rules' ].append( ( operator, rule_type, rule ) )
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
                
                has_audio = value
                
                self._common_info[ 'has_audio' ] = has_audio
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
                
                ( hashes, hash_type ) = value
                
                self._common_info[ 'hash' ] = ( hashes, hash_type )
                
            
            if predicate_type in ( PREDICATE_TYPE_SYSTEM_AGE, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME ):
                
                if predicate_type == PREDICATE_TYPE_SYSTEM_AGE:
                    
                    min_label = 'min_import_timestamp'
                    max_label = 'max_import_timestamp'
                    
                elif predicate_type == PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
                    
                    min_label = 'min_modified_timestamp'
                    max_label = 'max_modified_timestamp'
                    
                
                ( operator, age_type, age_value ) = value
                
                if age_type == 'delta':
                    
                    ( years, months, days, hours ) = age_value
                    
                    age = ( ( ( ( ( ( ( years * 12 ) + months ) * 30 ) + days ) * 24 ) + hours ) * 3600 )
                    
                    now = HydrusData.GetNow()
                    
                    # this is backwards (less than means min timestamp) because we are talking about age, not timestamp
                    
                    if operator == '<':
                        
                        self._common_info[ min_label ] = now - age
                        
                    elif operator == '>':
                        
                        self._common_info[ max_label ] = now - age
                        
                    elif operator == '\u2248':
                        
                        self._common_info[ min_label ] = now - int( age * 1.15 )
                        self._common_info[ max_label ] = now - int( age * 0.85 )
                        
                    
                elif age_type == 'date':
                    
                    ( year, month, day ) = age_value
                    
                    # convert this dt, which is in local time, to a gmt timestamp
                    
                    day_dt = datetime.datetime( year, month, day )
                    timestamp = int( time.mktime( day_dt.timetuple() ) )
                    
                    if operator == '<':
                        
                        self._common_info[ max_label ] = timestamp
                        
                    elif operator == '>':
                        
                        self._common_info[ min_label ] = timestamp + 86400
                        
                    elif operator == '=':
                        
                        self._common_info[ min_label ] = timestamp
                        self._common_info[ max_label ] = timestamp + 86400
                        
                    elif operator == '\u2248':
                        
                        self._common_info[ min_label ] = timestamp - 86400 * 30
                        self._common_info[ max_label ] = timestamp + 86400 * 30
                        
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
                
                mimes = value
                
                if isinstance( mimes, int ): mimes = ( mimes, )
                
                self._common_info[ 'mimes' ] = mimes
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_DURATION:
                
                ( operator, duration ) = value
                
                if operator == '<': self._common_info[ 'max_duration' ] = duration
                elif operator == '>': self._common_info[ 'min_duration' ] = duration
                elif operator == '=': self._common_info[ 'duration' ] = duration
                elif operator == '\u2248':
                    
                    if duration == 0:
                        
                        self._common_info[ 'duration' ] = 0
                        
                    else:
                        
                        self._common_info[ 'min_duration' ] = int( duration * 0.85 )
                        self._common_info[ 'max_duration' ] = int( duration * 1.15 )
                        
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_RATING:
                
                ( operator, value, service_key ) = value
                
                self._ratings_predicates.append( ( operator, value, service_key ) )
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_RATIO:
                
                ( operator, ratio_width, ratio_height ) = value
                
                if operator == '=': self._common_info[ 'ratio' ] = ( ratio_width, ratio_height )
                elif operator == 'wider than':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == 'taller than':
                    
                    self._common_info[ 'max_ratio' ] = ( ratio_width, ratio_height )
                    
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_ratio' ] = ( ratio_width * 0.85, ratio_height )
                    self._common_info[ 'max_ratio' ] = ( ratio_width * 1.15, ratio_height )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_SIZE:
                
                ( operator, size, unit ) = value
                
                size = size * unit
                
                if operator == '<': self._common_info[ 'max_size' ] = size
                elif operator == '>': self._common_info[ 'min_size' ] = size
                elif operator == '=': self._common_info[ 'size' ] = size
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_size' ] = int( size * 0.85 )
                    self._common_info[ 'max_size' ] = int( size * 1.15 )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                ( operator, num_tags ) = value
                
                if operator == '<': self._common_info[ 'max_num_tags' ] = num_tags
                elif operator == '=': self._common_info[ 'num_tags' ] = num_tags
                elif operator == '>': self._common_info[ 'min_num_tags' ] = num_tags
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                ( namespace, operator, num ) = value
                
                if operator == '<': self._common_info[ 'max_tag_as_number' ] = ( namespace, num )
                elif operator == '>': self._common_info[ 'min_tag_as_number' ] = ( namespace, num )
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_tag_as_number' ] = ( namespace, int( num * 0.85 ) )
                    self._common_info[ 'max_tag_as_number' ] = ( namespace, int( num * 1.15 ) )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH:
                
                ( operator, width ) = value
                
                if operator == '<': self._common_info[ 'max_width' ] = width
                elif operator == '>': self._common_info[ 'min_width' ] = width
                elif operator == '=': self._common_info[ 'width' ] = width
                elif operator == '\u2248':
                    
                    if width == 0: self._common_info[ 'width' ] = 0
                    else:
                        
                        self._common_info[ 'min_width' ] = int( width * 0.85 )
                        self._common_info[ 'max_width' ] = int( width * 1.15 )
                        
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                ( operator, num_pixels, unit ) = value
                
                num_pixels = num_pixels * unit
                
                if operator == '<': self._common_info[ 'max_num_pixels' ] = num_pixels
                elif operator == '>': self._common_info[ 'min_num_pixels' ] = num_pixels
                elif operator == '=': self._common_info[ 'num_pixels' ] = num_pixels
                elif operator == '\u2248':
                    
                    self._common_info[ 'min_num_pixels' ] = int( num_pixels * 0.85 )
                    self._common_info[ 'max_num_pixels' ] = int( num_pixels * 1.15 )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT:
                
                ( operator, height ) = value
                
                if operator == '<': self._common_info[ 'max_height' ] = height
                elif operator == '>': self._common_info[ 'min_height' ] = height
                elif operator == '=': self._common_info[ 'height' ] = height
                elif operator == '\u2248':
                    
                    if height == 0: self._common_info[ 'height' ] = 0
                    else:
                        
                        self._common_info[ 'min_height' ] = int( height * 0.85 )
                        self._common_info[ 'max_height' ] = int( height * 1.15 )
                        
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_NUM_WORDS:
                
                ( operator, num_words ) = value
                
                if operator == '<': self._common_info[ 'max_num_words' ] = num_words
                elif operator == '>': self._common_info[ 'min_num_words' ] = num_words
                elif operator == '=': self._common_info[ 'num_words' ] = num_words
                elif operator == '\u2248':
                    
                    if num_words == 0: self._common_info[ 'num_words' ] = 0
                    else:
                        
                        self._common_info[ 'min_num_words' ] = int( num_words * 0.85 )
                        self._common_info[ 'max_num_words' ] = int( num_words * 1.15 )
                        
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_LIMIT:
                
                limit = value
                
                if self._limit is None:
                    
                    self._limit = limit
                    
                else:
                    
                    self._limit = min( limit, self._limit )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                ( operator, current_or_pending, service_key ) = value
                
                if operator == True:
                    
                    if current_or_pending == HC.CONTENT_STATUS_CURRENT: self._file_services_to_include_current.append( service_key )
                    else: self._file_services_to_include_pending.append( service_key )
                    
                else:
                    
                    if current_or_pending == HC.CONTENT_STATUS_CURRENT: self._file_services_to_exclude_current.append( service_key )
                    else: self._file_services_to_exclude_pending.append( service_key )
                    
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
                
                ( hashes, max_hamming ) = value
                
                self._similar_to = ( hashes, max_hamming )
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT:
                
                ( operator, num_relationships, dupe_type ) = value
                
                self._duplicate_count_predicates.append( ( operator, num_relationships, dupe_type ) )
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING:
                
                king = value
                
                self._king_filter = king
                
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                ( view_type, viewing_locations, operator, viewing_value ) = value
                
                self._file_viewing_stats_predicates.append( ( view_type, viewing_locations, operator, viewing_value ) )
                
            
        
    
    def GetDuplicateRelationshipCountPredicates( self ):
        
        return self._duplicate_count_predicates
        
    
    def GetFileServiceInfo( self ):
        
        return ( self._file_services_to_include_current, self._file_services_to_include_pending, self._file_services_to_exclude_current, self._file_services_to_exclude_pending )
        
    
    def GetFileViewingStatsPredicates( self ):
        
        return self._file_viewing_stats_predicates
        
    
    def GetKingFilter( self ):
        
        return self._king_filter
        
    
    def GetLimit( self, apply_implicit_limit = True ):
        
        if self._limit is None and apply_implicit_limit:
            
            forced_search_limit = HG.client_controller.new_options.GetNoneableInteger( 'forced_search_limit' )
            
            return forced_search_limit
            
        
        return self._limit
        
    
    def GetSimpleInfo( self ):
        
        return self._common_info
        
    
    def GetRatingsPredicates( self ):
        
        return self._ratings_predicates
        
    
    def GetSimilarTo( self ):
        
        return self._similar_to
        
    
    def HasSimilarTo( self ):
        
        return self._similar_to is not None
        
    
    def HasSystemEverything( self ):
        
        return self._has_system_everything
        
    
    def MustBeArchive( self ): return self._archive
    
    def MustBeInbox( self ): return self._inbox
    
    def MustBeLocal( self ): return self._local
    
    def MustNotBeLocal( self ): return self._not_local
    
class Predicate( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE
    SERIALISABLE_NAME = 'File Search Predicate'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, predicate_type = None, value = None, inclusive = True, min_current_count = 0, min_pending_count = 0, max_current_count = None, max_pending_count = None ):
        
        if isinstance( value, ( list, set ) ):
            
            value = tuple( value )
            
        
        self._predicate_type = predicate_type
        self._value = value
        
        self._inclusive = inclusive
        
        self._min_current_count = min_current_count
        self._min_pending_count = min_pending_count
        self._max_current_count = max_current_count
        self._max_pending_count = max_pending_count
        
    
    def __eq__( self, other ):
        
        if isinstance( other, Predicate ):
            
            return self.__hash__() == other.__hash__()
            
        
        return NotImplemented
        
    
    def __hash__( self ):
        
        return ( self._predicate_type, self._value, self._inclusive ).__hash__()
        
    
    def __ne__( self, other ):
        
        return self.__hash__() != other.__hash__()
        
    
    def __repr__( self ):
        
        return 'Predicate: ' + str( ( self._predicate_type, self._value, self._inclusive, self.GetCount() ) )
        
    
    def _GetSerialisableInfo( self ):
        
        if self._predicate_type in ( PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
            
            ( operator, value, service_key ) = self._value
            
            serialisable_value = ( operator, value, service_key.hex() )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            ( hashes, max_hamming ) = self._value
            
            serialisable_value = ( [ hash.hex() for hash in hashes ], max_hamming )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            ( operator, rule_type, rule, description ) = self._value
            
            if rule_type in ( 'url_match', 'url_class' ):
                
                serialisable_rule = rule.GetSerialisableTuple()
                
            else:
                
                serialisable_rule = rule
                
            
            serialisable_value = ( operator, rule_type, serialisable_rule, description )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
            
            ( hashes, hash_type ) = self._value
            
            serialisable_value = ( [ hash.hex() for hash in hashes ], hash_type )
            
        elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            or_predicates = self._value
            
            serialisable_value = HydrusSerialisable.SerialisableList( or_predicates ).GetSerialisableTuple()
            
        else:
            
            serialisable_value = self._value
            
        
        return ( self._predicate_type, serialisable_value, self._inclusive )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._predicate_type, serialisable_value, self._inclusive ) = serialisable_info
        
        if self._predicate_type in ( PREDICATE_TYPE_SYSTEM_RATING, PREDICATE_TYPE_SYSTEM_FILE_SERVICE ):
            
            ( operator, value, service_key ) = serialisable_value
            
            self._value = ( operator, value, bytes.fromhex( service_key ) )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            ( serialisable_hashes, max_hamming ) = serialisable_value
            
            self._value = ( tuple( [ bytes.fromhex( serialisable_hash ) for serialisable_hash in serialisable_hashes ] ) , max_hamming )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            ( operator, rule_type, serialisable_rule, description ) = serialisable_value
            
            if rule_type in ( 'url_match', 'url_class' ):
                
                rule = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_rule )
                
            else:
                
                rule = serialisable_rule
                
            
            self._value = ( operator, rule_type, rule, description )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
            
            ( serialisable_hashes, hash_type ) = serialisable_value
            
            self._value = ( tuple( [ bytes.fromhex( serialisable_hash ) for serialisable_hash in serialisable_hashes ] ), hash_type )
            
        elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_AGE, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME ):
            
            ( operator, age_type, age_value ) = serialisable_value
            
            self._value = ( operator, age_type, tuple( age_value ) )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            ( view_type, viewing_locations, operator, viewing_value ) = serialisable_value
            
            self._value = ( view_type, tuple( viewing_locations ), operator, viewing_value )
            
        elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            serialisable_or_predicates = serialisable_value
            
            self._value = tuple( HydrusSerialisable.CreateFromSerialisableTuple( serialisable_or_predicates ) )
            
        else:
            
            self._value = serialisable_value
            
        
        if isinstance( self._value, list ):
            
            self._value = tuple( self._value )
            
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type == PREDICATE_TYPE_SYSTEM_AGE:
                
                ( operator, years, months, days, hours ) = serialisable_value
                
                serialisable_value = ( operator, 'delta', ( years, months, days, hours ) )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( predicate_type, serialisable_value, inclusive ) = old_serialisable_info
            
            if predicate_type in ( PREDICATE_TYPE_SYSTEM_HASH, PREDICATE_TYPE_SYSTEM_SIMILAR_TO ):
                
                # other value is either hash type or max hamming distance
                
                ( serialisable_hash, other_value ) = serialisable_value
                
                serialisable_hashes = ( serialisable_hash, )
                
                serialisable_value = ( serialisable_hashes, other_value )
                
            
            new_serialisable_info = ( predicate_type, serialisable_value, inclusive )
            
            return ( 3, new_serialisable_info )
            
        
    
    def AddCounts( self, predicate ):
        
        ( min_current_count, max_current_count, min_pending_count, max_pending_count ) = predicate.GetAllCounts()
        
        ( self._min_current_count, self._max_current_count ) = ClientData.MergeCounts( self._min_current_count, self._max_current_count, min_current_count, max_current_count )
        ( self._min_pending_count, self._max_pending_count) = ClientData.MergeCounts( self._min_pending_count, self._max_pending_count, min_pending_count, max_pending_count )
        
    
    def GetAllCounts( self ):
        
        return ( self._min_current_count, self._max_current_count, self._min_pending_count, self._max_pending_count )
        
    
    def GetCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive, self._min_current_count, self._min_pending_count, self._max_current_count, self._max_pending_count )
        
    
    def GetCountlessCopy( self ):
        
        return Predicate( self._predicate_type, self._value, self._inclusive )
        
    
    def GetCount( self, current_or_pending = None ):
        
        if current_or_pending is None:
            
            return self._min_current_count + self._min_pending_count
            
        elif current_or_pending == HC.CONTENT_STATUS_CURRENT:
            
            return self._min_current_count
            
        elif current_or_pending == HC.CONTENT_STATUS_PENDING:
            
            return self._min_pending_count
            
        
    
    def GetNamespace( self ):
        
        if self._predicate_type in SYSTEM_PREDICATE_TYPES:
            
            return 'system'
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            return namespace
            
        elif self._predicate_type in ( PREDICATE_TYPE_PARENT, PREDICATE_TYPE_TAG, PREDICATE_TYPE_WILDCARD ):
            
            tag_analogue = self._value
            
            ( namespace, subtag ) = HydrusTags.SplitTag( tag_analogue )
            
            return namespace
            
        else:
            
            return ''
            
        
    
    def GetInclusive( self ):
        
        # patch from an upgrade mess-up ~v144
        if not hasattr( self, '_inclusive' ):
            
            if self._predicate_type not in SYSTEM_PREDICATE_TYPES:
                
                ( operator, value ) = self._value
                
                self._value = value
                
                self._inclusive = operator == '+'
                
            else: self._inclusive = True
            
        
        return self._inclusive
        
    
    def GetInfo( self ):
        
        return ( self._predicate_type, self._value, self._inclusive )
        
    
    def GetInverseCopy( self ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_INBOX )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_INBOX:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_ARCHIVE )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LOCAL:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_NOT_LOCAL )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NOT_LOCAL:
            
            return Predicate( PREDICATE_TYPE_SYSTEM_LOCAL )
            
        elif self._predicate_type in ( PREDICATE_TYPE_TAG, PREDICATE_TYPE_NAMESPACE, PREDICATE_TYPE_WILDCARD ):
            
            return Predicate( self._predicate_type, self._value, not self._inclusive )
            
        elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
            
            return Predicate( self._predicate_type, not self._value )
            
        else:
            
            return None
            
        
    
    def GetTextsAndNamespaces( self, or_under_construction = False ):
        
        if self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            texts_and_namespaces = []
            
            if or_under_construction:
                
                texts_and_namespaces.append( ( 'OR: ', 'system' ) )
                
            
            for or_predicate in self._value:
                
                texts_and_namespaces.append( ( or_predicate.ToString(), or_predicate.GetNamespace() ) )
                
                texts_and_namespaces.append( ( ' OR ', 'system' ) )
                
            
            texts_and_namespaces = texts_and_namespaces[ : -1 ]
            
        else:
            
            texts_and_namespaces = [ ( self.ToString(), self.GetNamespace() ) ]
            
        
        return texts_and_namespaces
        
    
    def GetType( self ):
        
        return self._predicate_type
        
    
    def IsInclusive( self ):
        
        return self._inclusive
        
    
    def IsMutuallyExclusive( self, predicate ):
        
        if self._predicate_type == PREDICATE_TYPE_SYSTEM_EVERYTHING:
            
            return True
            
        
        if predicate == self.GetInverseCopy():
            
            return True
            
        
        my_type = self._predicate_type
        other_type = predicate.GetType()
        
        if my_type == other_type:
            
            if my_type in ( PREDICATE_TYPE_SYSTEM_LIMIT, PREDICATE_TYPE_SYSTEM_HASH, PREDICATE_TYPE_SYSTEM_SIMILAR_TO ):
                
                return True
                
            
        
        return False
        
    
    def ToString( self, with_count = True, sibling_service_key = None, render_for_user = False, or_under_construction = False ):
        
        count_text = ''
        
        if with_count:
            
            if self._min_current_count > 0:
                
                number_text = HydrusData.ToHumanInt( self._min_current_count )
                
                if self._max_current_count is not None:
                    
                    number_text += '-' + HydrusData.ToHumanInt( self._max_current_count )
                    
                
                count_text += ' (' + number_text + ')'
                
            
            if self._min_pending_count > 0:
                
                number_text = HydrusData.ToHumanInt( self._min_pending_count )
                
                if self._max_pending_count is not None:
                    
                    number_text += '-' + HydrusData.ToHumanInt( self._max_pending_count )
                    
                
                count_text += ' (+' + number_text + ')'
                
            
        
        if self._predicate_type in SYSTEM_PREDICATE_TYPES:
            
            if self._predicate_type == PREDICATE_TYPE_SYSTEM_EVERYTHING: base = 'everything'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_INBOX: base = 'inbox'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_ARCHIVE: base = 'archive'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_UNTAGGED: base = 'untagged'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LOCAL: base = 'local'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NOT_LOCAL: base = 'not local'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_DIMENSIONS: base = 'dimensions'
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS: base = 'file relationships'
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_WIDTH, PREDICATE_TYPE_SYSTEM_HEIGHT, PREDICATE_TYPE_SYSTEM_NUM_WORDS ):
                
                if self._predicate_type == PREDICATE_TYPE_SYSTEM_WIDTH: base = 'width'
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HEIGHT: base = 'height'
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_WORDS: base = 'number of words'
                
                if self._value is not None:
                    
                    ( operator, value ) = self._value
                    
                    base += ' ' + operator + ' ' + HydrusData.ToHumanInt( value )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_DURATION:
                
                base = 'duration'
                
                if self._value is not None:
                    
                    ( operator, value ) = self._value
                    
                    if operator == '>' and value == 0:
                        
                        base = 'has duration'
                        
                    elif operator == '=' and value == 0:
                        
                        base = 'no duration'
                        
                    else:
                        
                        base += ' ' + operator + ' ' + HydrusData.ConvertMillisecondsToPrettyTime( value )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                base = 'number of tags'
                
                if self._value is not None:
                    
                    ( operator, value ) = self._value
                    
                    if operator == '>' and value == 0:
                        
                        base = 'has tags'
                        
                    elif operator == '=' and value == 0:
                        
                        base = 'untagged'
                        
                    else:
                        
                        base += ' ' + operator + ' ' + HydrusData.ToHumanInt( value )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_RATIO:
                
                base = 'ratio'
                
                if self._value is not None:
                    
                    ( operator, ratio_width, ratio_height ) = self._value
                    
                    base += ' ' + operator + ' ' + str( ratio_width ) + ':' + str( ratio_height )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIZE:
                
                base = 'filesize'
                
                if self._value is not None:
                    
                    ( operator, size, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( size ) + HydrusData.ConvertIntToUnit( unit )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_LIMIT:
                
                base = 'limit'
                
                if self._value is not None:
                    
                    value = self._value
                    
                    base += ' is ' + HydrusData.ToHumanInt( value )
                    
                
            elif self._predicate_type in ( PREDICATE_TYPE_SYSTEM_AGE, PREDICATE_TYPE_SYSTEM_MODIFIED_TIME ):
                
                if self._predicate_type == PREDICATE_TYPE_SYSTEM_AGE:
                    
                    base = 'time imported'
                    
                elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
                    
                    base = 'modified time'
                    
                
                if self._value is not None:
                    
                    ( operator, age_type, age_value ) = self._value
                    
                    if age_type == 'delta':
                        
                        ( years, months, days, hours ) = age_value
                        
                        DAY = 86400
                        MONTH = DAY * 30
                        YEAR = MONTH * 12
                        
                        time_delta = 0
                        
                        time_delta += hours * 3600
                        time_delta += days * DAY
                        time_delta += months * MONTH
                        time_delta += years * YEAR
                        
                        if operator == '<':
                            
                            pretty_operator = 'since '
                            
                        elif operator == '>':
                            
                            pretty_operator = 'before '
                            
                        elif operator == '\u2248':
                            
                            pretty_operator = 'around '
                            
                        
                        base += ': ' + pretty_operator + HydrusData.TimeDeltaToPrettyTimeDelta( time_delta ) + ' ago'
                        
                    elif age_type == 'date':
                        
                        ( year, month, day ) = age_value
                        
                        dt = datetime.datetime( year, month, day )
                        
                        # make a timestamp (IN GMT SECS SINCE 1970) from the local meaning of 2018/02/01
                        timestamp = int( time.mktime( dt.timetuple() ) )
                        
                        if operator == '<':
                            
                            pretty_operator = 'before '
                            
                        elif operator == '>':
                            
                            pretty_operator = 'since '
                            
                        elif operator == '=':
                            
                            pretty_operator = 'on the day of '
                            
                        elif operator == '\u2248':
                            
                            pretty_operator = 'a month either side of '
                            
                        
                        # convert this GMT TIMESTAMP to a pretty local string
                        base += ': ' + pretty_operator + HydrusData.ConvertTimestampToPrettyTime( timestamp, include_24h_time = False )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                base = 'num_pixels'
                
                if self._value is not None:
                    
                    ( operator, num_pixels, unit ) = self._value
                    
                    base += ' ' + operator + ' ' + str( num_pixels ) + ' ' + HydrusData.ConvertIntToPixels( unit )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                base = 'known url'
                
                if self._value is not None:
                    
                    ( operator, rule_type, rule, description ) = self._value
                    
                    base = description
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HAS_AUDIO:
                
                base = 'has audio'
                
                if self._value is not None:
                    
                    has_audio = self._value
                    
                    if not has_audio:
                        
                        base = 'no audio'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_HASH:
                
                base = 'hash'
                
                if self._value is not None:
                    
                    ( hashes, hash_type ) = self._value
                    
                    if len( hashes ) == 1:
                        
                        base = '{} hash is {}'.format( hash_type, hashes[0].hex() )
                        
                    else:
                        
                        base = '{} hash is in {} hashes'.format( hash_type, HydrusData.ToHumanInt( len( hashes ) ) )
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_MIME:
                
                base = 'filetype'
                
                if self._value is not None:
                    
                    mimes = self._value
                    
                    if set( mimes ) == set( HC.SEARCHABLE_MIMES ):
                        
                        mime_text = 'anything'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.APPLICATIONS ) ):
                        
                        mime_text = 'application'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.AUDIO ) ):
                        
                        mime_text = 'audio'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.IMAGES ) ):
                        
                        mime_text = 'image'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.ANIMATIONS ) ):
                        
                        mime_text = 'animation'
                        
                    elif set( mimes ) == set( HC.SEARCHABLE_MIMES ).intersection( set( HC.VIDEO ) ):
                        
                        mime_text = 'video'
                        
                    else:
                        
                        mime_text = ', '.join( [ HC.mime_string_lookup[ mime ] for mime in mimes ] )
                        
                    
                    base += ' is ' + mime_text
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_RATING:
                
                base = 'rating'
                
                if self._value is not None:
                    
                    ( operator, value, service_key ) = self._value
                    
                    try:
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        service_type = service.GetServiceType()
                        
                        pretty_value = str( value )
                        
                        if service_type == HC.LOCAL_RATING_LIKE:
                            
                            if value == 0:
                                
                                pretty_value = 'dislike'
                                
                            elif value == 1:
                                
                                pretty_value = 'like'
                                
                            
                        elif service_type == HC.LOCAL_RATING_NUMERICAL:
                            
                            if isinstance( value, float ):
                                
                                allow_zero = service.AllowZero()
                                num_stars = service.GetNumStars()
                                
                                if allow_zero:
                                    
                                    star_range = num_stars
                                    
                                else:
                                    
                                    star_range = num_stars - 1
                                    
                                
                                pretty_x = int( round( value * star_range ) )
                                pretty_y = num_stars
                                
                                if not allow_zero:
                                    
                                    pretty_x += 1
                                    
                                
                                pretty_value = HydrusData.ConvertValueRangeToPrettyString( pretty_x, pretty_y )
                                
                            
                        
                        base += ' for ' + service.GetName() + ' ' + operator + ' ' + pretty_value
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'system:unknown rating service system predicate'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
                
                base = 'similar to'
                
                if self._value is not None:
                    
                    ( hashes, max_hamming ) = self._value
                    
                    base += ' {} files using max hamming of {}'.format( HydrusData.ToHumanInt( len( hashes ) ), max_hamming )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                if self._value is None:
                    
                    base = 'file service'
                    
                else:
                    
                    ( operator, current_or_pending, service_key ) = self._value
                    
                    if operator == True: base = 'is'
                    else: base = 'is not'
                    
                    if current_or_pending == HC.CONTENT_STATUS_PENDING: base += ' pending to '
                    else: base += ' currently in '
                    
                    try:
                        
                        service = HG.client_controller.services_manager.GetService( service_key )
                        
                        base += service.GetName()
                        
                    except HydrusExceptions.DataMissing:
                        
                        base = 'unknown file service system predicate'
                        
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                if self._value is None:
                    
                    base = 'tag as number'
                    
                else:
                    
                    ( namespace, operator, num ) = self._value
                    
                    if namespace == '':
                        
                        n_text = 'tag'
                        
                    else:
                        
                        n_text = namespace
                        
                    
                    if operator == '\u2248':
                        
                        o_text = ' about '
                        
                    elif operator == '<':
                        
                        o_text = ' less than '
                        
                    elif operator == '>':
                        
                        o_text = ' more than '
                        
                    
                    base = n_text + o_text + HydrusData.ToHumanInt( num )
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT:
                
                base = 'num file relationships'
                
                if self._value is not None:
                    
                    ( operator, num_relationships, dupe_type ) = self._value
                    
                    if operator == '\u2248':
                        
                        o_text = ' about '
                        
                    elif operator == '<':
                        
                        o_text = ' less than '
                        
                    elif operator == '>':
                        
                        o_text = ' more than '
                        
                    elif operator == '=':
                        
                        o_text = ' '
                        
                    
                    base += ' - has' + o_text + HydrusData.ToHumanInt( num_relationships ) + ' ' + HC.duplicate_type_string_lookup[ dupe_type ]
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING:
                
                base = ''
                
                if self._value is not None:
                    
                    king = self._value
                    
                    if king:
                        
                        o_text = 'is the best quality file of its duplicate group'
                        
                    else:
                        
                        o_text = 'is not the best quality file of its duplicate group'
                        
                    
                    base += o_text
                    
                
            elif self._predicate_type == PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                base = 'file viewing statistics'
                
                if self._value is not None:
                    
                    ( view_type, viewing_locations, operator, viewing_value ) = self._value
                    
                    include_media = 'media' in viewing_locations
                    include_previews = 'preview' in viewing_locations
                    
                    if include_media and include_previews:
                        
                        domain = 'all '
                        
                    elif include_media:
                        
                        domain = 'media '
                        
                    elif include_previews:
                        
                        domain = 'preview '
                        
                    else:
                        
                        domain = 'unknown '
                        
                    
                    if view_type == 'views':
                        
                        value_string = HydrusData.ToHumanInt( viewing_value )
                        
                    elif view_type == 'viewtime':
                        
                        value_string = HydrusData.TimeDeltaToPrettyTimeDelta( viewing_value )
                        
                    
                    base = domain + view_type + operator + value_string
                    
                
            
            base = HydrusTags.CombineTag( 'system', base )
            
            base = ClientTags.RenderTag( base, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_TAG:
            
            tag = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
            if sibling_service_key is not None:
                
                siblings_manager = HG.client_controller.tag_siblings_manager
                
                sibling = siblings_manager.GetSibling( sibling_service_key, tag )
                
                if sibling is not None:
                    
                    sibling = ClientTags.RenderTag( sibling, render_for_user )
                    
                    base += ' (will display as ' + sibling + ')'
                    
                
            
        elif self._predicate_type == PREDICATE_TYPE_PARENT:
            
            base = '    '
            
            tag = self._value
            
            base += ClientTags.RenderTag( tag, render_for_user )
            
            base += count_text
            
        elif self._predicate_type == PREDICATE_TYPE_NAMESPACE:
            
            namespace = self._value
            
            if not self._inclusive: base = '-'
            else: base = ''
            
            anything_tag = HydrusTags.CombineTag( namespace, '*anything*' )
            
            anything_tag = ClientTags.RenderTag( anything_tag, render_for_user )
            
            base += anything_tag
            
        elif self._predicate_type == PREDICATE_TYPE_WILDCARD:
            
            wildcard = self._value + ' (wildcard search)'
            
            if not self._inclusive:
                
                base = '-'
                
            else:
                
                base = ''
                
            
            base += wildcard
            
        elif self._predicate_type == PREDICATE_TYPE_OR_CONTAINER:
            
            or_predicates = self._value
            
            base = ''
            
            if or_under_construction:
                
                base += 'OR: '
                
            
            base += ' OR '.join( ( or_predicate.ToString( render_for_user = render_for_user ) for or_predicate in or_predicates ) )
            
        elif self._predicate_type == PREDICATE_TYPE_LABEL:
            
            label = self._value
            
            base = label
            
        
        return base
        
    
    def GetUnnamespacedCopy( self ):
        
        if self._predicate_type == PREDICATE_TYPE_TAG:
            
            ( namespace, subtag ) = HydrusTags.SplitTag( self._value )
            
            return Predicate( self._predicate_type, subtag, self._inclusive, self._min_current_count, self._min_pending_count, self._max_current_count, self._max_pending_count )
            
        
        return self.GetCopy()
        
    
    def GetValue( self ):
        
        return self._value
        
    
    def HasNonZeroCount( self ):
        
        return self._min_current_count > 0 or self._min_pending_count > 0
        
    
    def SetInclusive( self, inclusive ):
        
        self._inclusive = inclusive
        

HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_PREDICATE ] = Predicate

SYSTEM_PREDICATE_INBOX = Predicate( PREDICATE_TYPE_SYSTEM_INBOX, None )

SYSTEM_PREDICATE_ARCHIVE = Predicate( PREDICATE_TYPE_SYSTEM_ARCHIVE, None )

SYSTEM_PREDICATE_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM_LOCAL, None )

SYSTEM_PREDICATE_NOT_LOCAL = Predicate( PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None )
