from . import ClientConstants as CC
from . import ClientDownloading
from . import ClientImporting
from . import ClientImportFileSeeds
from . import ClientImportGallerySeeds
from . import ClientImportOptions
from . import ClientNetworkingContexts
from . import ClientNetworkingJobs
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusSerialisable
from . import HydrusThreading
import os
import random
import threading
import time

class Subscription( HydrusSerialisable.SerialisableBaseNamed ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION
    SERIALISABLE_NAME = 'Subscription'
    SERIALISABLE_VERSION = 10
    
    def __init__( self, name, gug_key_and_name = None ):
        
        HydrusSerialisable.SerialisableBaseNamed.__init__( self, name )
        
        if gug_key_and_name is None:
            
            gug_key_and_name = ( HydrusData.GenerateKey(), 'unknown source' )
            
        
        self._gug_key_and_name = gug_key_and_name
        
        self._queries = []
        
        new_options = HG.client_controller.new_options
        
        self._checker_options = HG.client_controller.new_options.GetDefaultSubscriptionCheckerOptions()
        
        if HC.options[ 'gallery_file_limit' ] is None:
            
            self._initial_file_limit = 100
            
        else:
            
            self._initial_file_limit = min( 100, HC.options[ 'gallery_file_limit' ] )
            
        
        self._periodic_file_limit = 100
        self._paused = False
        
        self._file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'quiet' )
        
        new_options = HG.client_controller.new_options
        
        self._tag_import_options = ClientImportOptions.TagImportOptions( is_default = True )
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
        self._show_a_popup_while_working = True
        self._publish_files_to_popup_button = True
        self._publish_files_to_page = False
        self._publish_label_override = None
        self._merge_query_publish_events = True
        
    
    def _CanDoWorkNow( self ):
        
        p1 = not ( self._paused or HG.client_controller.options[ 'pause_subs_sync' ] or HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
        p2 = not ( HG.view_shutdown or HydrusThreading.IsThreadShuttingDown() )
        p3 = self._NoDelays()
        
        if HG.subscription_report_mode:
            
            message = 'Subscription "{}" CanDoWork check.'.format( self._name )
            message += os.linesep
            message += 'Paused/Global/Network Pause: {}/{}/{}'.format( self._paused, HG.client_controller.options[ 'pause_subs_sync' ], HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' ) )
            message += os.linesep
            message += 'View/Thread shutdown: {}/{}'.format( HG.view_shutdown, HydrusThreading.IsThreadShuttingDown() )
            message += os.linesep
            message += 'No delays: {}'.format( self._NoDelays() )
            
            HydrusData.ShowText( message )
            
        
        return p1 and p2 and p3
        
    
    def _DelayWork( self, time_delta, reason ):
        
        self._no_work_until = HydrusData.GetNow() + time_delta
        self._no_work_until_reason = reason
        
    
    def _GetPublishingLabel( self, query ):
        
        if self._publish_label_override is None:
            
            label = self._name
            
        else:
            
            label = self._publish_label_override
            
        
        if not self._merge_query_publish_events:
            
            label += ': ' + query.GetHumanName()
            
        
        return label
        
    
    def _GetQueriesForProcessing( self ):
        
        queries = list( self._queries )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            random.shuffle( queries )
            
        else:
            
            def key( q ):
                
                return q.GetHumanName()
                
            
            queries.sort( key = key )
            
        
        return queries
        
    
    def _GetSerialisableInfo( self ):
        
        ( gug_key, gug_name ) = self._gug_key_and_name
        
        serialisable_gug_key_and_name = ( gug_key.hex(), gug_name )
        serialisable_queries = [ query.GetSerialisableTuple() for query in self._queries ]
        serialisable_checker_options = self._checker_options.GetSerialisableTuple()
        serialisable_file_import_options = self._file_import_options.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, serialisable_file_import_options, serialisable_tag_import_options, self._no_work_until, self._no_work_until_reason, self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events ) = serialisable_info
        
        ( serialisable_gug_key, gug_name ) = serialisable_gug_key_and_name
        
        self._gug_key_and_name = ( bytes.fromhex( serialisable_gug_key ), gug_name )
        self._queries = [ HydrusSerialisable.CreateFromSerialisableTuple( serialisable_query ) for serialisable_query in serialisable_queries ]
        self._checker_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_checker_options )
        self._file_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_import_options )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _GenerateNetworkJobFactory( self, query ):
        
        subscription_key = query.GetNetworkJobSubscriptionKey( self._name )
        
        def network_job_factory( *args, **kwargs ):
            
            network_job = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, *args, **kwargs )
            
            network_job.OverrideBandwidth( 30 )
            
            return network_job
            
        
        return network_job_factory
        
    
    def _NoDelays( self ):
        
        return HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def _QueryFileLoginIsOK( self, query ):
        
        file_seed_cache = query.GetFileSeedCache()
        
        file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if file_seed is None:
            
            result = True
            
        else:
            
            nj = file_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( query ) )
            
            nj.engine = HG.client_controller.network_engine
            
            if nj.NeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    
                    if not self._paused:
                        
                        login_fail_reason = str( e )
                        
                        message = 'Query "' + query.GetHumanName() + '" for subscription "' + self._name + '" seemed to have an invalid login for one of its file imports. The reason was:'
                        message += os.linesep * 2
                        message += login_fail_reason
                        message += os.linesep * 2
                        message += 'The subscription has paused. Please see if you can fix the problem and then unpause. Hydrus dev would like feedback on this process.'
                        
                        HydrusData.ShowText( message )
                        
                        self._DelayWork( 300, login_fail_reason )
                        
                        self._paused = True
                        
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetHumanName() + '" pre-work file login test. Login ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def _QuerySyncLoginIsOK( self, query ):
        
        gallery_seed_log = query.GetGallerySeedLog()
        
        gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
        
        if gallery_seed is None:
            
            result = True
            
        else:
            
            nj = gallery_seed.GetExampleNetworkJob( self._GenerateNetworkJobFactory( query ) )
            
            nj.engine = HG.client_controller.network_engine
            
            if nj.NeedsLogin():
                
                try:
                    
                    nj.CheckCanLogin()
                    
                    result = True
                    
                except Exception as e:
                    
                    result = False
                    
                    if not self._paused:
                        
                        login_fail_reason = str( e )
                        
                        message = 'Query "' + query.GetHumanName() + '" for subscription "' + self._name + '" seemed to have an invalid login. The reason was:'
                        message += os.linesep * 2
                        message += login_fail_reason
                        message += os.linesep * 2
                        message += 'The subscription has paused. Please see if you can fix the problem and then unpause. Hydrus dev would like feedback on this process.'
                        
                        HydrusData.ShowText( message )
                        
                        self._DelayWork( 300, login_fail_reason )
                        
                        self._paused = True
                        
                    
                
            else:
                
                result = True
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + query.GetHumanName() + '" pre-work sync login test. Login ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def _ShowHitPeriodicFileLimitMessage( self, query_text ):
        
        message = 'The query "' + query_text + '" for subscription "' + self._name + '" hit its periodic file limit without seeing any already-seen files.'
        
        HydrusData.ShowText( message )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            check_now = False
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, serialisable_file_seed_cache ) = old_serialisable_info
            
            no_work_until = 0
            no_work_until_reason = ''
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache )
            
            return ( 3, new_serialisable_info )
            
        
        if version == 3:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, query, period, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, last_checked, check_now, last_error, no_work_until, no_work_until_reason, serialisable_file_seed_cache ) = old_serialisable_info
            
            checker_options = ClientImportOptions.CheckerOptions( 5, period // 5, period * 10, ( 1, period * 10 ) )
            
            file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
            
            query = SubscriptionQuery( query )
            
            query._file_seed_cache = file_seed_cache
            query._last_check_time = last_checked
            
            query.UpdateNextCheckTime( checker_options )
            
            queries = [ query ]
            
            serialisable_queries = [ query.GetSerialisableTuple() for query in queries ]
            serialisable_checker_options = checker_options.GetSerialisableTuple()
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason )
            
            return ( 4, new_serialisable_info )
            
        
        if version == 4:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, get_tags_if_url_recognised_and_file_redundant, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason )
            
            return ( 5, new_serialisable_info )
            
        
        if version == 5:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason ) = old_serialisable_info
            
            publish_files_to_popup_button = True
            publish_files_to_page = False
            merge_query_publish_events = True
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 6, new_serialisable_info )
            
        
        if version == 6:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            if initial_file_limit is None or initial_file_limit > 1000:
                
                initial_file_limit = 1000
                
            
            if periodic_file_limit is None or periodic_file_limit > 1000:
                
                periodic_file_limit = 1000
                
            
            new_serialisable_info = ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 7, new_serialisable_info )
            
        
        if version == 7:
            
            ( serialisable_gallery_identifier, serialisable_gallery_stream_identifiers, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            gallery_identifier = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_identifier )
            
            ( gug_key, gug_name ) = ClientDownloading.ConvertGalleryIdentifierToGUGKeyAndName( gallery_identifier )
            
            serialisable_gug_key_and_name = ( gug_key.hex(), gug_name )
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 8, new_serialisable_info )
            
        
        if version == 8:
            
            ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            show_a_popup_while_working = True
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events )
            
            return ( 9, new_serialisable_info )
            
        
        if version == 9:
            
            ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, merge_query_publish_events ) = old_serialisable_info
            
            publish_label_override = None
            
            new_serialisable_info = ( serialisable_gug_key_and_name, serialisable_queries, serialisable_checker_options, initial_file_limit, periodic_file_limit, paused, serialisable_file_import_options, serialisable_tag_import_options, no_work_until, no_work_until_reason, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events )
            
            return ( 10, new_serialisable_info )
            
        
    
    def _WorkOnFiles( self, job_key ):
        
        error_count = 0
        
        queries = self._GetQueriesForProcessing()
        
        queries = [ query for query in queries if query.HasFileWorkToDo() ]
        
        num_queries = len( queries )
        
        for ( i, query ) in enumerate( queries ):
            
            this_query_has_done_work = False
            
            query_name = query.GetHumanName()
            file_seed_cache = query.GetFileSeedCache()
            
            text_1 = 'downloading files'
            query_summary_name = self._name
            
            if query_name != self._name:
                
                text_1 += ' for "' + query_name + '"'
                query_summary_name += ': ' + query_name
                
            
            if num_queries > 1:
                
                text_1 += ' (' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_queries ) + ')'
                
            
            job_key.SetVariable( 'popup_text_1', text_1 )
            
            presentation_hashes = []
            presentation_hashes_fast = set()
            
            starting_num_urls = file_seed_cache.GetFileSeedCount()
            starting_num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
            starting_num_done = starting_num_urls - starting_num_unknown
            
            try:
                
                while True:
                    
                    file_seed = file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
                    
                    if file_seed is None:
                        
                        if HG.subscription_report_mode:
                            
                            HydrusData.ShowText( 'Query "' + query_name + '" can do no more file work due to running out of unknown urls.' )
                            
                        
                        break
                        
                    
                    if job_key.IsCancelled():
                        
                        self._DelayWork( 300, 'recently cancelled' )
                        
                        break
                        
                    
                    p1 = not self._CanDoWorkNow()
                    p4 = not query.BandwidthIsOK( self._name )
                    p5 = not self._QueryFileLoginIsOK( query )
                    
                    if p1 or p4 or p5:
                        
                        if p4 and this_query_has_done_work:
                            
                            job_key.SetVariable( 'popup_text_2', 'no more bandwidth to download files, will do some more later' )
                            
                            time.sleep( 5 )
                            
                        
                        break
                        
                    
                    try:
                        
                        num_urls = file_seed_cache.GetFileSeedCount()
                        num_unknown = file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN )
                        num_done = num_urls - num_unknown
                        
                        # 4001/4003 is not as useful as 1/3
                        
                        human_num_urls = num_urls - starting_num_done
                        human_num_done = num_done - starting_num_done
                        
                        x_out_of_y = 'file ' + HydrusData.ConvertValueRangeToPrettyString( human_num_done + 1, human_num_urls ) + ': '
                        
                        job_key.SetVariable( 'popup_gauge_2', ( human_num_done, human_num_urls ) )
                        
                        def status_hook( text ):
                            
                            if len( text ) > 0:
                                
                                text = text.splitlines()[0]
                                
                            
                            job_key.SetVariable( 'popup_text_2', x_out_of_y + text )
                            
                        
                        file_seed.WorkOnURL( file_seed_cache, status_hook, self._GenerateNetworkJobFactory( query ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, self._tag_import_options )
                        
                        query_tag_import_options = query.GetTagImportOptions()
                        
                        if query_tag_import_options.HasAdditionalTags() and file_seed.status in CC.SUCCESSFUL_IMPORT_STATES:
                            
                            if file_seed.HasHash():
                                
                                hash = file_seed.GetHash()
                                
                                in_inbox = HG.client_controller.Read( 'in_inbox', hash )
                                
                                downloaded_tags = []
                                
                                service_keys_to_content_updates = query_tag_import_options.GetServiceKeysToContentUpdates( file_seed.status, in_inbox, hash, downloaded_tags ) # additional tags
                                
                                if len( service_keys_to_content_updates ) > 0:
                                    
                                    HG.client_controller.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
                                    
                                
                            
                        
                        if file_seed.ShouldPresent( self._file_import_options ):
                            
                            hash = file_seed.GetHash()
                            
                            if hash not in presentation_hashes_fast:
                                
                                presentation_hashes.append( hash )
                                
                                presentation_hashes_fast.add( hash )
                                
                            
                        
                    except HydrusExceptions.CancelledException as e:
                        
                        self._DelayWork( 300, str( e ) )
                        
                        break
                        
                    except HydrusExceptions.VetoException as e:
                        
                        status = CC.STATUS_VETOED
                        
                        note = str( e )
                        
                        file_seed.SetStatus( status, note = note )
                        
                    except HydrusExceptions.NotFoundException:
                        
                        status = CC.STATUS_VETOED
                        
                        note = '404'
                        
                        file_seed.SetStatus( status, note = note )
                        
                    except Exception as e:
                        
                        status = CC.STATUS_ERROR
                        
                        job_key.SetVariable( 'popup_text_2', x_out_of_y + 'file failed' )
                        
                        file_seed.SetStatus( status, exception = e )
                        
                        if isinstance( e, HydrusExceptions.DataMissing ):
                            
                            # DataMissing is a quick thing to avoid subscription abandons when lots of deleted files in e621 (or any other booru)
                            # this should be richer in any case in the new system
                            
                            pass
                            
                        else:
                            
                            error_count += 1
                            
                            time.sleep( 5 )
                            
                        
                        error_count_threshold = HG.client_controller.new_options.GetNoneableInteger( 'subscription_file_error_cancel_threshold' )
                        
                        if error_count_threshold is not None and error_count >= error_count_threshold:
                            
                            raise Exception( 'The subscription ' + self._name + ' encountered several errors when downloading files, so it abandoned its sync.' )
                            
                        
                    
                    this_query_has_done_work = True
                    
                    if len( presentation_hashes ) > 0:
                        
                        job_key.SetVariable( 'popup_files', ( list( presentation_hashes ), query_summary_name ) )
                        
                    
                    time.sleep( ClientImporting.DID_SUBSTANTIAL_FILE_WORK_MINIMUM_SLEEP_TIME )
                    
                    HG.client_controller.WaitUntilViewFree()
                    
                
            finally:
                
                if len( presentation_hashes ) > 0:
                    
                    publishing_label = self._GetPublishingLabel( query )
                    
                    ClientImporting.PublishPresentationHashes( publishing_label, presentation_hashes, self._publish_files_to_popup_button, self._publish_files_to_page )
                    
                
            
        
        job_key.DeleteVariable( 'popup_files' )
        job_key.DeleteVariable( 'popup_text_1' )
        job_key.DeleteVariable( 'popup_text_2' )
        job_key.DeleteVariable( 'popup_gauge_2' )
        
    
    def _WorkOnFilesCanDoWork( self ):
        
        for query in self._queries:
            
            if query.HasFileWorkToDo():
                
                if query.BandwidthIsOK( self._name ):
                    
                    if HG.subscription_report_mode:
                        
                        HydrusData.ShowText( 'Subscription "{}" checking if any file work due: True'.format( self._name ) )
                        
                    
                    return True
                    
                
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any file work due: False'.format( self._name ) )
            
        
        return False
        
    
    def _SyncQuery( self, job_key ):
        
        have_made_an_initial_sync_bandwidth_notification = False
        
        gug = HG.client_controller.network_engine.domain_manager.GetGUG( self._gug_key_and_name )
        
        if gug is None:
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription "' + self._name + '" could not find a Gallery URL Generator for "' + self._gug_key_and_name[1] + '"! The sub has paused!' )
            
            return
            
        
        if not gug.IsFunctional():
            
            self._paused = True
            
            HydrusData.ShowText( 'The subscription "' + self._name + '"\'s Gallery URL Generator, "' + self._gug_key_and_name[1] + '" seems not to be functional! Maybe it needs a gallery url class or a gallery parser? The sub has paused!' )
            
            return
            
        
        self._gug_key_and_name = gug.GetGUGKeyAndName() # just a refresher, to keep up with any changes
        
        queries = self._GetQueriesForProcessing()
        
        queries = [ query for query in queries if query.IsSyncDue() ]
        
        num_queries = len( queries )
        
        for ( i, query ) in enumerate( queries ):
            
            query_text = query.GetQueryText()
            query_name = query.GetHumanName()
            file_seed_cache = query.GetFileSeedCache()
            gallery_seed_log = query.GetGallerySeedLog()
            
            this_is_initial_sync = query.IsInitialSync()
            total_new_urls_for_this_sync = 0
            total_already_in_urls_for_this_sync = 0
            
            gallery_urls_seen_this_sync = set()
            
            if this_is_initial_sync:
                
                file_limit_for_this_sync = self._initial_file_limit
                
            else:
                
                file_limit_for_this_sync = self._periodic_file_limit
                
            
            file_seeds_to_add = set()
            file_seeds_to_add_ordered = []
            
            stop_reason = 'unknown stop reason'
            
            prefix = 'synchronising'
            
            if query_name != self._name:
                
                prefix += ' "' + query_name + '"'
                
            
            if num_queries > 1:
                
                prefix += ' (' + HydrusData.ConvertValueRangeToPrettyString( i + 1, num_queries ) + ')'
                
            
            job_key.SetVariable( 'popup_text_1', prefix )
            
            initial_search_urls = gug.GenerateGalleryURLs( query_text )
            
            if len( initial_search_urls ) == 0:
                
                self._paused = True
                
                HydrusData.ShowText( 'The subscription "' + self._name + '"\'s Gallery URL Generator, "' + self._gug_key_and_name[1] + '" did not generate any URLs! The sub has paused!' )
                
                return
                
            
            gallery_seeds = [ ClientImportGallerySeeds.GallerySeed( url, can_generate_more_pages = True ) for url in initial_search_urls ]
            
            gallery_seed_log.AddGallerySeeds( gallery_seeds )
            
            try:
                
                while gallery_seed_log.WorkToDo():
                    
                    p1 = not self._CanDoWorkNow()
                    p3 = not self._QuerySyncLoginIsOK( query )
                    
                    if p1 or p3:
                        
                        if p3:
                            
                            stop_reason = 'Login was invalid!'
                            
                        
                        return
                        
                    
                    if job_key.IsCancelled():
                        
                        stop_reason = 'gallery parsing cancelled, likely by user'
                        
                        self._DelayWork( 600, stop_reason )
                        
                        return
                        
                    
                    gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                    
                    if gallery_seed is None:
                        
                        stop_reason = 'thought there was a page to check, but apparently there was not!'
                        
                        break
                        
                    
                    def status_hook( text ):
                        
                        if len( text ) > 0:
                            
                            text = text.splitlines()[0]
                            
                        
                        job_key.SetVariable( 'popup_text_1', prefix + ': ' + text )
                        
                    
                    def title_hook( text ):
                        
                        pass
                        
                    
                    def file_seeds_callable( file_seeds ):
                        
                        num_urls_added = 0
                        num_urls_already_in_file_seed_cache = 0
                        can_search_for_more_files = True
                        stop_reason = 'unknown stop reason'
                        current_contiguous_num_urls_already_in_file_seed_cache = 0
                        
                        for file_seed in file_seeds:
                            
                            if file_seed in file_seeds_to_add:
                                
                                # this catches the occasional overflow when a new file is uploaded while gallery parsing is going on
                                # we don't want to count these 'seen before this run' urls in the 'caught up to last time' count
                                
                                continue
                                
                            
                            # When are we caught up? This is not a trivial problem. Tags are not always added when files are uploaded, so the order we find files is not completely reliable.
                            # Ideally, we want to search a _bit_ deeper than the first already-seen.
                            # And since we have a page of urls here and now, there is no point breaking early if there might be some new ones at the end.
                            # Current rule is "We are caught up if the final X contiguous files are 'already in'". X is 5 for now.
                            
                            if file_seed_cache.HasFileSeed( file_seed ):
                                
                                num_urls_already_in_file_seed_cache += 1
                                current_contiguous_num_urls_already_in_file_seed_cache += 1
                                
                                if current_contiguous_num_urls_already_in_file_seed_cache >= 100:
                                    
                                    can_search_for_more_files = False
                                    stop_reason = 'saw 100 previously seen urls in a row, so assuming this is a large gallery'
                                    
                                    break
                                    
                                
                            else:
                                
                                num_urls_added += 1
                                current_contiguous_num_urls_already_in_file_seed_cache = 0
                                
                                file_seeds_to_add.add( file_seed )
                                file_seeds_to_add_ordered.append( file_seed )
                                
                            
                            if file_limit_for_this_sync is not None and total_new_urls_for_this_sync + num_urls_added >= file_limit_for_this_sync:
                                
                                # we have found enough new files this sync, so should stop adding files and new gallery pages
                                
                                if this_is_initial_sync:
                                    
                                    stop_reason = 'hit initial file limit'
                                    
                                else:
                                    
                                    if total_already_in_urls_for_this_sync + num_urls_already_in_file_seed_cache > 0:
                                        
                                        # this sync produced some knowns, so it is likely we have stepped through a mix of old and tagged-late new files
                                        # we might also be on the second sync with a periodic limit greater than the initial limit
                                        # either way, this is no reason to go crying to the user
                                        
                                        stop_reason = 'hit periodic file limit after seeing several already-seen files'
                                        
                                    else:
                                        
                                        # this page had all entirely new files
                                        
                                        self._ShowHitPeriodicFileLimitMessage( query_name )
                                        
                                        stop_reason = 'hit periodic file limit without seeing any already-seen files!'
                                        
                                    
                                
                                can_search_for_more_files = False
                                
                                break
                                
                            
                        
                        WE_HIT_OLD_GROUND_THRESHOLD = 5
                        
                        if current_contiguous_num_urls_already_in_file_seed_cache >= WE_HIT_OLD_GROUND_THRESHOLD:
                            
                            # this gallery page has caught up to before, so it should not spawn any more gallery pages
                            
                            can_search_for_more_files = False
                            
                            stop_reason = 'saw ' + HydrusData.ToHumanInt( current_contiguous_num_urls_already_in_file_seed_cache ) + ' previously seen urls, so assuming we caught up'
                            
                        
                        if num_urls_added == 0:
                            
                            can_search_for_more_files = False
                            stop_reason = 'no new urls found'
                            
                        
                        return ( num_urls_added, num_urls_already_in_file_seed_cache, can_search_for_more_files, stop_reason )
                        
                    
                    job_key.SetVariable( 'popup_text_1', prefix + ': found ' + HydrusData.ToHumanInt( total_new_urls_for_this_sync ) + ' new urls, checking next page' )
                    
                    try:
                        
                        ( num_urls_added, num_urls_already_in_file_seed_cache, num_urls_total, result_404, added_new_gallery_pages, stop_reason ) = gallery_seed.WorkOnURL( 'subscription', gallery_seed_log, file_seeds_callable, status_hook, title_hook, self._GenerateNetworkJobFactory( query ), ClientImporting.GenerateMultiplePopupNetworkJobPresentationContextFactory( job_key ), self._file_import_options, gallery_urls_seen_before = gallery_urls_seen_this_sync )
                        
                    except HydrusExceptions.CancelledException as e:
                        
                        stop_reason = 'gallery network job cancelled, likely by user'
                        
                        self._DelayWork( 600, stop_reason )
                        
                        return
                        
                    except Exception as e:
                        
                        stop_reason = str( e )
                        
                        raise
                        
                    
                    total_new_urls_for_this_sync += num_urls_added
                    total_already_in_urls_for_this_sync += num_urls_already_in_file_seed_cache
                    
                    if file_limit_for_this_sync is not None and total_new_urls_for_this_sync >= file_limit_for_this_sync:
                        
                        # we have found enough new files this sync, so stop and cancel any outstanding gallery urls
                        
                        if this_is_initial_sync:
                            
                            stop_reason = 'hit initial file limit'
                            
                        else:
                            
                            stop_reason = 'hit periodic file limit'
                            
                        
                        break
                        
                    
                
            finally:
                
                while gallery_seed_log.WorkToDo():
                    
                    gallery_seed = gallery_seed_log.GetNextGallerySeed( CC.STATUS_UNKNOWN )
                    
                    if gallery_seed is None:
                        
                        break
                        
                    
                    gallery_seed.SetStatus( CC.STATUS_VETOED, note = stop_reason )
                    
                
            
            file_seeds_to_add_ordered.reverse()
            
            # 'first' urls are now at the end, so the file_seed_cache should stay roughly in oldest->newest order
            
            file_seed_cache.AddFileSeeds( file_seeds_to_add_ordered )
            
            query.RegisterSyncComplete( self._checker_options )
            query.UpdateNextCheckTime( self._checker_options )
            
            #
            
            if query.IsDead():
                
                if this_is_initial_sync:
                    
                    HydrusData.ShowText( 'The query "' + query_name + '" for subscription "' + self._name + '" did not find any files on its first sync! Could the query text have a typo, like a missing underscore?' )
                    
                else:
                    
                    HydrusData.ShowText( 'The query "' + query_name + '" for subscription "' + self._name + '" appears to be dead!' )
                    
                
            else:
                
                if this_is_initial_sync:
                    
                    if not query.BandwidthIsOK( self._name ) and not have_made_an_initial_sync_bandwidth_notification:
                        
                        HydrusData.ShowText( 'FYI: The query "' + query_name + '" for subscription "' + self._name + '" performed its initial sync ok, but that domain is short on bandwidth right now, so no files will be downloaded yet. The subscription will catch up in future as bandwidth becomes available. You can review the estimated time until bandwidth is available under the manage subscriptions dialog. If more queries are performing initial syncs in this run, they may be the same.' )
                        
                        have_made_an_initial_sync_bandwidth_notification = True
                        
                    
                
            
        
    
    def _SyncQueryCanDoWork( self ):
        
        result = True in ( query.IsSyncDue() for query in self._queries )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" checking if any sync work due: {}'.format( self._name, result ) )
            
        
        return result
        
    
    def AllPaused( self ):
        
        if self._paused:
            
            return True
            
        
        for query in self._queries:
            
            if not query.IsPaused():
                
                return False
                
            
        
        return True
        
    
    def CanCheckNow( self ):
        
        return True in ( query.CanCheckNow() for query in self._queries )
        
    
    def CanReset( self ):
        
        return True in ( not query.IsInitialSync() for query in self._queries )
        
    
    def CanRetryFailures( self ):
        
        return True in ( query.CanRetryFailed() for query in self._queries )
        
    
    def CanRetryIgnored( self ):
        
        return True in ( query.CanRetryIgnored() for query in self._queries )
        
    
    def CanScrubDelay( self ):
        
        return not HydrusData.TimeHasPassed( self._no_work_until )
        
    
    def CheckNow( self ):
        
        for query in self._queries:
            
            query.CheckNow()
            
        
        self.ScrubDelay()
        
    
    def GetBandwidthWaitingEstimateMinMax( self ):
        
        if len( self._queries ) == 0:
            
            return ( 0, 0 )
            
        
        estimates = []
        
        for query in self._queries:
            
            estimate = query.GetBandwidthWaitingEstimate( self._name )
            
            estimates.append( estimate )
            
        
        min_estimate = min( estimates )
        max_estimate = max( estimates )
        
        return ( min_estimate, max_estimate )
        
    
    def GetBestEarliestNextWorkTime( self ):
        
        next_work_times = set()
        
        for query in self._queries:
            
            next_work_time = query.GetNextWorkTime( self._name )
            
            if next_work_time is not None:
                
                next_work_times.add( next_work_time )
                
            
        
        if len( next_work_times ) == 0:
            
            return None
            
        
        # if there are three queries due fifty seconds after our first one runs, we should wait that little bit longer
        LAUNCH_WINDOW = 15 * 60
        
        earliest_next_work_time = min( next_work_times )
        
        latest_nearby_next_work_time = max( ( work_time for work_time in next_work_times if work_time < earliest_next_work_time + LAUNCH_WINDOW ) )
        
        # but if we are expecting to launch it right now (e.g. check_now call), we won't wait
        if HydrusData.TimeUntil( earliest_next_work_time ) < 60:
            
            best_next_work_time = earliest_next_work_time
            
        else:
            
            best_next_work_time = latest_nearby_next_work_time
            
        
        if not HydrusData.TimeHasPassed( self._no_work_until ):
            
            best_next_work_time = max( ( best_next_work_time, self._no_work_until ) )
            
        
        return best_next_work_time
        
    
    def GetGUGKeyAndName( self ):
        
        return self._gug_key_and_name
        
    
    def GetQueries( self ):
        
        return self._queries
        
    
    def GetMergeable( self, potential_mergees ):
        
        mergeable = []
        unmergeable = []
        
        for subscription in potential_mergees:
            
            if subscription._gug_key_and_name[1] == self._gug_key_and_name[1]:
                
                mergeable.append( subscription )
                
            else:
                
                unmergeable.append( subscription )
                
            
        
        return ( mergeable, unmergeable )
        
    
    def GetPresentationOptions( self ):
        
        return ( self._show_a_popup_while_working, self._publish_files_to_popup_button, self._publish_files_to_page, self._publish_label_override, self._merge_query_publish_events )
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasQuerySearchTextFragment( self, search_text_fragment ):
        
        for query in self._queries:
            
            query_text = query.GetQueryText()
            
            if search_text_fragment in query_text:
                
                return True
                
            
        
        return False
        
    
    def Merge( self, mergees ):
        
        for subscription in mergees:
            
            if subscription._gug_key_and_name[1] == self._gug_key_and_name[1]:
                
                my_new_queries = [ query.Duplicate() for query in subscription._queries ]
                
                self._queries.extend( my_new_queries )
                
            else:
                
                raise Exception( self._name + ' was told to merge an unmergeable subscription, ' + subscription.GetName() + '!' )
                
            
        
    
    def PauseResume( self ):
        
        self._paused = not self._paused
        
    
    def Reset( self ):
        
        for query in self._queries:
            
            query.Reset()
            
        
        self.ScrubDelay()
        
    
    def RetryFailures( self ):
        
        for query in self._queries:
            
            query.RetryFailures()
            
        
    
    def RetryIgnored( self ):
        
        for query in self._queries:
            
            query.RetryIgnored()
            
        
    
    def Separate( self, base_name, only_these_queries = None ):
        
        if only_these_queries is None:
            
            only_these_queries = set( self._queries )
            
        else:
            
            only_these_queries = set( only_these_queries )
            
        
        my_queries = self._queries
        
        self._queries = []
        
        base_sub = self.Duplicate()
        
        self._queries = my_queries
        
        subscriptions = []
        
        for query in my_queries:
            
            if query not in only_these_queries:
                
                continue
                
            
            subscription = base_sub.Duplicate()
            
            subscription._queries = [ query ]
            
            subscription.SetName( base_name + ': ' + query.GetHumanName() )
            
            subscriptions.append( subscription )
            
        
        self._queries = [ query for query in my_queries if query not in only_these_queries ]
        
        return subscriptions
        
    
    def SetCheckerOptions( self, checker_options ):
        
        self._checker_options = checker_options
        
        for query in self._queries:
            
            query.UpdateNextCheckTime( self._checker_options )
            
        
    
    def SetPresentationOptions( self, show_a_popup_while_working, publish_files_to_popup_button, publish_files_to_page, publish_label_override, merge_query_publish_events ):
        
        self._show_a_popup_while_working = show_a_popup_while_working
        self._publish_files_to_popup_button = publish_files_to_popup_button
        self._publish_files_to_page = publish_files_to_page
        self._publish_label_override = publish_label_override
        self._merge_query_publish_events = merge_query_publish_events
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options.Duplicate()
        
    
    def SetTuple( self, gug_key_and_name, queries, checker_options, initial_file_limit, periodic_file_limit, paused, file_import_options, tag_import_options, no_work_until ):
        
        self._gug_key_and_name = gug_key_and_name
        self._queries = queries
        self._checker_options = checker_options
        self._initial_file_limit = initial_file_limit
        self._periodic_file_limit = periodic_file_limit
        self._paused = paused
        
        self._file_import_options = file_import_options
        self._tag_import_options = tag_import_options
        
        self._no_work_until = no_work_until
        
    
    def ScrubDelay( self ):
        
        self._no_work_until = 0
        self._no_work_until_reason = ''
        
    
    def Sync( self ):
        
        sync_ok = self._SyncQueryCanDoWork()
        files_ok = self._WorkOnFilesCanDoWork()
        
        if self._CanDoWorkNow() and ( sync_ok or files_ok ):
            
            job_key = ClientThreading.JobKey( pausable = False, cancellable = True )
            
            try:
                
                job_key.SetVariable( 'popup_title', 'subscriptions - ' + self._name )
                
                if self._show_a_popup_while_working:
                    
                    HG.client_controller.pub( 'message', job_key )
                    
                
                # it is possible a query becomes due for a check while others are syncing, so we repeat this while watching for a stop signal
                while self._CanDoWorkNow() and self._SyncQueryCanDoWork():
                    
                    self._SyncQuery( job_key )
                    
                
                self._WorkOnFiles( job_key )
                
            except HydrusExceptions.NetworkException as e:
                
                delay = HG.client_controller.new_options.GetInteger( 'subscription_network_error_delay' )
                
                HydrusData.Print( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                
                HydrusData.Print( e )
                
                job_key.SetVariable( 'popup_text_1', 'Encountered a network error, will retry again later' )
                
                self._DelayWork( delay, 'network error: ' + str( e ) )
                
                time.sleep( 5 )
                
            except Exception as e:
                
                HydrusData.ShowText( 'The subscription ' + self._name + ' encountered an exception when trying to sync:' )
                HydrusData.ShowException( e )
                
                delay = HG.client_controller.new_options.GetInteger( 'subscription_other_error_delay' )
                
                self._DelayWork( delay, 'error: ' + str( e ) )
                
            finally:
                
                job_key.DeleteVariable( 'popup_network_job' )
                
            
            HG.client_controller.WriteSynchronous( 'serialisable', self )
            
            if job_key.HasVariable( 'popup_files' ):
                
                job_key.Finish()
                
            else:
                
                job_key.Delete()
                
            
        
    
    def ToTuple( self ):
        
        return ( self._name, self._gug_key_and_name, self._queries, self._checker_options, self._initial_file_limit, self._periodic_file_limit, self._paused, self._file_import_options, self._tag_import_options, self._no_work_until, self._no_work_until_reason )
        
    
class SubscriptionJob( object ):
    
    def __init__( self, controller, subscription ):
        
        self._controller = controller
        self._subscription = subscription
        self._job_done = threading.Event()
        
    
    def _DoWork( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription "{}" about to start.'.format( self._subscription.GetName() ) )
            
        
        self._subscription.Sync()
        
    
    def IsDone( self ):
        
        return self._job_done.is_set()
        
    
    def Work( self ):
        
        try:
            
            self._DoWork()
            
        finally:
            
            self._job_done.set()
            
        
    
class SubscriptionsManager( object ):
    
    def __init__( self, controller ):
        
        self._controller = controller
        
        self._running_subscriptions = {}
        self._current_subscription_names = set()
        self._names_to_next_work_time = {}
        self._names_that_cannot_run = set()
        
        self._loading_sub = False
        
        self._lock = threading.Lock()
        
        self._shutdown = False
        self._mainloop_finished = False
        
        self._wake_event = threading.Event()
        
        # cache deals with 'don't need to check, but have more files to do' and delay timings
        # no prob if cache is empty of a sub, we'll just repopulate naturally
        # also cache deals with pause info
        # ideally this lad will launch subs exactly on time, rather than every twenty mins or whatever, but we should have a buffer on natural timings in order to get multiple queries together
        
        self._ReinitialiseNames()
        
        self._controller.sub( self, 'Shutdown', 'shutdown' )
        
    
    def _ClearFinishedSubscriptions( self ):
        
        for ( name, ( thread, job, subscription ) ) in list( self._running_subscriptions.items() ):
            
            if job.IsDone():
                
                self._UpdateSubscriptionInfo( subscription, just_finished_work = True )
                
                del self._running_subscriptions[ name ]
                
            
        
    
    def _GetNameReadyToGo( self ):
        
        p1 = HG.client_controller.options[ 'pause_subs_sync' ]
        p2 = HG.client_controller.new_options.GetBoolean( 'pause_all_new_network_traffic' )
        p3 = HG.view_shutdown
        
        if p1 or p2 or p3:
            
            return None
            
        
        max_simultaneous_subscriptions = HG.client_controller.new_options.GetInteger( 'max_simultaneous_subscriptions' )
        
        if len( self._running_subscriptions ) >= max_simultaneous_subscriptions:
            
            return None
            
        
        possible_names = set( self._current_subscription_names )
        possible_names.difference_update( set( self._running_subscriptions.keys() ) )
        possible_names.difference_update( self._names_that_cannot_run )
        
        # just a couple of seconds for calculation and human breathing room
        SUB_WORK_DELAY_BUFFER = 3
        
        names_not_due = { name for ( name, next_work_time ) in self._names_to_next_work_time.items() if not HydrusData.TimeHasPassed( next_work_time + SUB_WORK_DELAY_BUFFER ) }
        
        possible_names.difference_update( names_not_due )
        
        if len( possible_names ) == 0:
            
            return None
            
        
        possible_names = list( possible_names )
        
        if HG.client_controller.new_options.GetBoolean( 'process_subs_in_random_order' ):
            
            subscription_name = random.choice( possible_names )
            
        else:
            
            possible_names.sort()
            
            subscription_name = possible_names.pop( 0 )
            
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Subscription manager selected "{}" to start.'.format( subscription_name ) )
            
        
        return subscription_name
        
    
    def _GetMainLoopWaitTime( self ):
        
        if self._shutdown:
            
            return 0.1
            
        
        if len( self._running_subscriptions ) > 0:
            
            return 1
            
        else:
            
            subscription_name = self._GetNameReadyToGo()
            
            if subscription_name is not None:
                
                return 1
                
            else:
                
                return 15
                
            
        
    
    def _ReinitialiseNames( self ):
        
        self._current_subscription_names = set( HG.client_controller.Read( 'serialisable_names', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ) )
        
        self._names_that_cannot_run = set()
        self._names_to_next_work_time = {}
        
    
    def _UpdateSubscriptionInfo( self, subscription, just_finished_work = False ):
        
        name = subscription.GetName()
        
        if name in self._names_that_cannot_run:
            
            self._names_that_cannot_run.discard( name )
            
        
        if name in self._names_to_next_work_time:
            
            del self._names_to_next_work_time[ name ]
            
        
        if subscription.AllPaused():
            
            self._names_that_cannot_run.add( name )
            
        else:
            
            next_work_time = subscription.GetBestEarliestNextWorkTime()
            
            if next_work_time is None:
                
                self._names_that_cannot_run.add( name )
                
            else:
                
                if just_finished_work:
                    
                    # don't want to have a load/save cycle repeating over and over
                    # this sets min resolution of a single sub repeat cycle
                    # we'll clear it when we have data breakup done
                    BUFFER_TIME = 60 * 60
                    
                    next_work_time = max( next_work_time, HydrusData.GetNow() + BUFFER_TIME )
                    
                
                self._names_to_next_work_time[ name ] = next_work_time
                
            
        
    
    def ClearCacheAndWake( self ):
        
        with self._lock:
            
            self._ReinitialiseNames()
            
            self.Wake()
            
        
    
    def IsShutdown( self ):
        
        return self._mainloop_finished
        
    
    def LoadAndBootSubscription( self, subscription_name ):
        
        # keep this in its own thing lmao, you don't want a local() 'subscription' variable hanging around eating 400MB in the mainloop, nor the trouble of 'del'-ing it all over the place
        
        try:
            
            subscription = self._controller.Read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION, subscription_name )
            
        except Exception as e:
            
            HydrusData.ShowText( 'Subscription "{}" failed to load! Error information should follow. No more subscriptions will run this boot.'.format( subscription_name ) )
            HydrusData.ShowException( e )
            
            return
            
        
        job = SubscriptionJob( self._controller, subscription )
        
        thread = threading.Thread( target = job.Work, name = 'subscription thread' )
        
        thread.start()
        
        with self._lock:
            
            self._running_subscriptions[ subscription_name ] = ( thread, job, subscription )
            
        
    
    def MainLoop( self ):
        
        try:
            
            self._wake_event.wait( 15 )
            
            while not ( HG.view_shutdown or self._shutdown ):
                
                with self._lock:
                    
                    subscription_name = self._GetNameReadyToGo()
                    
                    if subscription_name is not None:
                        
                        self._loading_sub = True
                        
                    
                
                if subscription_name is not None:
                    
                    try:
                        
                        self.LoadAndBootSubscription( subscription_name )
                        
                    finally:
                        
                        with self._lock:
                            
                            self._loading_sub = False
                            
                        
                    
                
                with self._lock:
                    
                    self._ClearFinishedSubscriptions()
                    
                    wait_time = self._GetMainLoopWaitTime()
                    
                
                self._wake_event.wait( wait_time )
                
                self._wake_event.clear()
                
            
        finally:
            
            with self._lock:
                
                for ( name, ( thread, job, subscription ) ) in self._running_subscriptions.items():
                    
                    HydrusThreading.ShutdownThread( thread )
                    
                
            
            while not HG.view_shutdown:
                
                with self._lock:
                    
                    self._ClearFinishedSubscriptions()
                    
                    if len( self._running_subscriptions ) == 0:
                        
                        break
                        
                    
                
            
            self._mainloop_finished = True
            
        
    
    def NewSubscriptions( self, subscriptions ):
        
        with self._lock:
            
            self._current_subscription_names = { subscription.GetName() for subscription in subscriptions }
            
            self._names_that_cannot_run = set()
            self._names_to_next_work_time = {}
            
            for subscription in subscriptions:
                
                self._UpdateSubscriptionInfo( subscription )
                
            
        
    
    def ShowSnapshot( self ):
        
        with self._lock:
            
            subs = list( self._current_subscription_names )
            subs.sort()
            
            running = list( self._running_subscriptions.keys() )
            running.sort()
            
            cannot_run = list( self._names_that_cannot_run )
            cannot_run.sort()
            
            next_times = list( self._names_to_next_work_time.items() )
            next_times.sort( key = lambda n, nwt: nwt )
            
            message = '{} subs: {}'.format( HydrusData.ToHumanInt( len( self._current_subscription_names ) ), ', '.join( subs ) )
            message += os.linesep * 2
            message += '{} running: {}'.format( HydrusData.ToHumanInt( len( self._running_subscriptions ) ), ', '.join( running ) )
            message += os.linesep * 2
            message += '{} not runnable: {}'.format( HydrusData.ToHumanInt( len( self._names_that_cannot_run ) ), ', '.join( cannot_run ) )
            message += os.linesep * 2
            message += '{} next times: {}'.format( HydrusData.ToHumanInt( len( self._names_to_next_work_time ) ), ', '.join( ( '{}: {}'.format( name, HydrusData.TimestampToPrettyTimeDelta( next_work_time ) ) for ( name, next_work_time ) in next_times ) ) )
            
            HydrusData.ShowText( message )
            
        
    
    def Shutdown( self ):
        
        self._shutdown = True
        
        self._wake_event.set()
        
    
    def Start( self ):
        
        self._controller.CallToThreadLongRunning( self.MainLoop )
        
    
    def SubscriptionsRunning( self ):
        
        with self._lock:
            
            return self._loading_sub or len( self._running_subscriptions ) > 0
            
        
    
    def Wake( self ):
        
        self._wake_event.set()
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION ] = Subscription

class SubscriptionQuery( HydrusSerialisable.SerialisableBase ):
    
    SERIALISABLE_TYPE = HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY
    SERIALISABLE_NAME = 'Subscription Query'
    SERIALISABLE_VERSION = 3
    
    def __init__( self, query = 'query text' ):
        
        HydrusSerialisable.SerialisableBase.__init__( self )
        
        self._query = query
        self._display_name = None
        self._check_now = False
        self._last_check_time = 0
        self._next_check_time = 0
        self._paused = False
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        self._tag_import_options = ClientImportOptions.TagImportOptions()
        
    
    def _GetExampleNetworkContexts( self, subscription_name ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        subscription_key = self.GetNetworkJobSubscriptionKey( subscription_name )
        
        if file_seed is None:
            
            return [ ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_SUBSCRIPTION, subscription_key ), ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
            
        
        url = file_seed.file_seed_data
        
        example_nj = ClientNetworkingJobs.NetworkJobSubscription( subscription_key, 'GET', url )
        example_network_contexts = example_nj.GetNetworkContexts()
        
        return example_network_contexts
        
    
    def _GetSerialisableInfo( self ):
        
        serialisable_gallery_seed_log = self._gallery_seed_log.GetSerialisableTuple()
        serialisable_file_seed_cache = self._file_seed_cache.GetSerialisableTuple()
        serialisable_tag_import_options = self._tag_import_options.GetSerialisableTuple()
        
        return ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
        
    
    def _InitialiseFromSerialisableInfo( self, serialisable_info ):
        
        ( self._query, self._display_name, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options ) = serialisable_info
        
        self._gallery_seed_log = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_gallery_seed_log )
        self._file_seed_cache = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_file_seed_cache )
        self._tag_import_options = HydrusSerialisable.CreateFromSerialisableTuple( serialisable_tag_import_options )
        
    
    def _UpdateSerialisableInfo( self, version, old_serialisable_info ):
        
        if version == 1:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_file_seed_cache ) = old_serialisable_info
            
            gallery_seed_log = ClientImportGallerySeeds.GallerySeedLog()
            
            serialisable_gallery_seed_log = gallery_seed_log.GetSerialisableTuple()
            
            new_serialisable_info = ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache )
            
            return ( 2, new_serialisable_info )
            
        
        if version == 2:
            
            ( query, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache ) = old_serialisable_info
            
            display_name = None
            tag_import_options = ClientImportOptions.TagImportOptions()
            
            serialisable_tag_import_options = tag_import_options.GetSerialisableTuple()
            
            new_serialisable_info = ( query, display_name, check_now, last_check_time, next_check_time, paused, status, serialisable_gallery_seed_log, serialisable_file_seed_cache, serialisable_tag_import_options )
            
            return ( 3, new_serialisable_info )
            
        
    
    def BandwidthIsOK( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        threshold = 90
        
        result = HG.client_controller.network_engine.bandwidth_manager.CanDoWork( example_network_contexts, threshold = threshold )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self.GetHumanName() + '" bandwidth test. Bandwidth ok: ' + str( result ) + '.' )
            
        
        return result
        
    
    def CanCheckNow( self ):
        
        return not self._check_now
        
    
    def CanRetryFailed( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) > 0
        
    
    def CanRetryIgnored( self ):
        
        return self._file_seed_cache.GetFileSeedCount( CC.STATUS_VETOED ) > 0
        
    
    def CheckNow( self ):
        
        self._check_now = True
        self._paused = False
        
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        
    
    def GetBandwidthWaitingEstimate( self, subscription_name ):
        
        example_network_contexts = self._GetExampleNetworkContexts( subscription_name )
        
        ( estimate, bandwidth_network_context ) = HG.client_controller.network_engine.bandwidth_manager.GetWaitingEstimateAndContext( example_network_contexts )
        
        return estimate
        
    
    def GetDisplayName( self ):
        
        return self._display_name
        
    
    def GetFileSeedCache( self ):
        
        return self._file_seed_cache
        
    
    def GetGallerySeedLog( self ):
        
        return self._gallery_seed_log
        
    
    def GetHumanName( self ):
        
        if self._display_name is None:
            
            return self._query
            
        else:
            
            return self._display_name
            
        
    
    def GetLastChecked( self ):
        
        return self._last_check_time
        
    
    def GetLatestAddedTime( self ):
        
        return self._file_seed_cache.GetLatestAddedTime()
        
    
    def GetNextCheckStatusString( self ):
        
        if self._check_now:
            
            return 'checking on dialog ok'
            
        elif self._status == ClientImporting.CHECKER_STATUS_DEAD:
            
            return 'dead, so not checking'
            
        else:
            
            if HydrusData.TimeHasPassed( self._next_check_time ):
                
                s = 'imminent'
                
            else:
                
                s = HydrusData.TimestampToPrettyTimeDelta( self._next_check_time )
                
            
            if self._paused:
                
                s = 'paused, but would be ' + s
                
            
            return s
            
        
    
    def GetNextWorkTime( self, subscription_name ):
        
        if self.IsPaused():
            
            return None
            
        
        work_times = set()
        
        if self.HasFileWorkToDo():
            
            file_bandwidth_estimate = self.GetBandwidthWaitingEstimate( subscription_name )
            
            if file_bandwidth_estimate == 0:
                
                work_times.add( 0 )
                
            else:
                
                file_work_time = HydrusData.GetNow() + file_bandwidth_estimate
                
                work_times.add( file_work_time )
                
            
        
        if not self.IsDead():
            
            work_times.add( self._next_check_time )
            
        
        if len( work_times ) == 0:
            
            return None
            
        
        return min( work_times )
        
    
    def GetNumURLsAndFailed( self ):
        
        return ( self._file_seed_cache.GetFileSeedCount( CC.STATUS_UNKNOWN ), len( self._file_seed_cache ), self._file_seed_cache.GetFileSeedCount( CC.STATUS_ERROR ) )
        
    
    def GetNetworkJobSubscriptionKey( self, subscription_name ):
        
        return subscription_name + ': ' + self.GetHumanName()
        
    
    def GetQueryText( self ):
        
        return self._query
        
    
    def GetTagImportOptions( self ):
        
        return self._tag_import_options
        
    
    def HasFileWorkToDo( self ):
        
        file_seed = self._file_seed_cache.GetNextFileSeed( CC.STATUS_UNKNOWN )
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" HasFileWorkToDo test. Next import is ' + repr( file_seed ) + '.' )
            
        
        return file_seed is not None
        
    
    def IsDead( self ):
        
        return self._status == ClientImporting.CHECKER_STATUS_DEAD
        
    
    def IsInitialSync( self ):
        
        return self._last_check_time == 0
        
    
    def IsPaused( self ):
        
        return self._paused
        
    
    def IsSyncDue( self ):
        
        if HG.subscription_report_mode:
            
            HydrusData.ShowText( 'Query "' + self._query + '" IsSyncDue test. Paused/dead status is {}/{}, check time due is {}, and check_now is {}.'.format( self._paused, self.IsDead(), HydrusData.TimeHasPassed( self._next_check_time ), self._check_now ) )
            
        
        if self._paused or self.IsDead():
            
            return False
            
        
        return HydrusData.TimeHasPassed( self._next_check_time ) or self._check_now
        
    
    def PausePlay( self ):
        
        self._paused = not self._paused
        
    
    def RegisterSyncComplete( self, checker_options ):
        
        self._last_check_time = HydrusData.GetNow()
        
        self._check_now = False
        
        death_period = checker_options.GetDeathFileVelocityPeriod()
        
        compact_before_this_time = self._last_check_time - ( death_period * 2 )
        
        if self._gallery_seed_log.CanCompact( compact_before_this_time ):
            
            self._gallery_seed_log.Compact( compact_before_this_time )
            
        
        if self._file_seed_cache.CanCompact( compact_before_this_time ):
            
            self._file_seed_cache.Compact( compact_before_this_time )
            
        
    
    def Reset( self ):
        
        self._last_check_time = 0
        self._next_check_time = 0
        self._status = ClientImporting.CHECKER_STATUS_OK
        self._paused = False
        
        self._file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
    
    def RetryFailures( self ):
        
        self._file_seed_cache.RetryFailures()    
        
    
    def RetryIgnored( self ):
        
        self._file_seed_cache.RetryIgnored()    
        
    
    def SetCheckNow( self, check_now ):
        
        self._check_now = check_now
        
    
    def SetDisplayName( self, display_name ):
        
        self._display_name = display_name
        
    
    def SetPaused( self, paused ):
        
        self._paused = paused
        
    
    def SetQueryAndSeeds( self, query, file_seed_cache, gallery_seed_log ):
        
        self._query = query
        self._file_seed_cache = file_seed_cache
        self._gallery_seed_log = gallery_seed_log
        
    
    def SetTagImportOptions( self, tag_import_options ):
        
        self._tag_import_options = tag_import_options
        
    
    def UpdateNextCheckTime( self, checker_options ):
        
        if self._check_now:
            
            self._next_check_time = 0
            
            self._status = ClientImporting.CHECKER_STATUS_OK
            
        else:
            
            if checker_options.IsDead( self._file_seed_cache, self._last_check_time ):
                
                self._status = ClientImporting.CHECKER_STATUS_DEAD
                
                if not self.HasFileWorkToDo():
                    
                    self._paused = True
                    
                
            
            last_next_check_time = self._next_check_time
            
            self._next_check_time = checker_options.GetNextCheckTime( self._file_seed_cache, self._last_check_time, last_next_check_time )
            
        
    
    def ToTuple( self ):
        
        return ( self._query, self._check_now, self._last_check_time, self._next_check_time, self._paused, self._status )
        
    
HydrusSerialisable.SERIALISABLE_TYPES_TO_OBJECT_TYPES[ HydrusSerialisable.SERIALISABLE_TYPE_SUBSCRIPTION_QUERY ] = SubscriptionQuery
