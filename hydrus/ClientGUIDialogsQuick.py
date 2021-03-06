from . import ClientGUIScrolledPanelsButtonQuestions
from . import ClientGUIScrolledPanelsEdit
from . import ClientGUITopLevelWindows
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusGlobals as HG
from qtpy import QtWidgets as QW

def GetDeleteFilesJobs( win, media, default_reason, suggested_file_service_key = None ):
    
    title = 'Delete files?'
    
    with ClientGUITopLevelWindows.DialogEdit( win, title, frame_key = 'regular_center_dialog' ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditDeleteFilesPanel( dlg, media, default_reason, suggested_file_service_key = suggested_file_service_key )
        
        dlg.SetPanel( panel )
        
        if panel.QuestionIsAlreadyResolved():
            
            ( involves_physical_delete, jobs ) = panel.GetValue()
            
            return ( involves_physical_delete, jobs )
            
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            ( involves_physical_delete, jobs ) = panel.GetValue()
            
            return ( involves_physical_delete, jobs )
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    
def GetFinishFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionFinishFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        result = ( dlg.exec(), dlg.WasCancelled() )
        
        return result
        
    
def GetInterstitialFilteringAnswer( win, label ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, label ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionCommitInterstitialFilteringPanel( dlg, label )
        
        dlg.SetPanel( panel )
        
        result = dlg.exec()
        
        return result
        
    
def GetYesNo( win, message, title = 'Are you sure?', yes_label = 'yes', no_label = 'no', auto_yes_time = None, auto_no_time = None, check_for_cancelled = False ):
    
    with ClientGUITopLevelWindows.DialogCustomButtonQuestion( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsButtonQuestions.QuestionYesNoPanel( dlg, message, yes_label = yes_label, no_label = no_label )
        
        dlg.SetPanel( panel )
        
        if auto_yes_time is None and auto_no_time is None:
            
            return dlg.exec() if not check_for_cancelled else ( dlg.exec(), dlg.WasCancelled() )
            
        else:
            
            if auto_yes_time is not None:
                
                job = HG.client_controller.CallLaterQtSafe( dlg, auto_yes_time, dlg.done, QW.QDialog.Accepted )
                
            elif auto_no_time is not None:
                
                job = HG.client_controller.CallLaterQtSafe( dlg, auto_no_time, dlg.done, QW.QDialog.Rejected )
                
            
            try:
                
                return dlg.exec() if not check_for_cancelled else ( dlg.exec(), dlg.WasCancelled() )
                
            finally:
                
                job.Cancel()
                
            
        
    
def SelectFromList( win, title, choice_tuples, value_to_select = None, sort_tuples = True ):
    
    with ClientGUITopLevelWindows.DialogEdit( win, title ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditSelectFromListPanel( dlg, choice_tuples, value_to_select = value_to_select, sort_tuples = sort_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    
def SelectFromListButtons( win, title, choice_tuples ):
    
    with ClientGUITopLevelWindows.DialogEdit( win, title, hide_buttons = True ) as dlg:
        
        panel = ClientGUIScrolledPanelsEdit.EditSelectFromListButtonsPanel( dlg, choice_tuples )
        
        dlg.SetPanel( panel )
        
        if dlg.exec() == QW.QDialog.Accepted:
            
            result = panel.GetValue()
            
            return result
            
        else:
            
            raise HydrusExceptions.CancelledException( 'Dialog cancelled.' )
            
        
    
def SelectServiceKey( service_types = HC.ALL_SERVICES, service_keys = None, unallowed = None ):
    
    if service_keys is None:
        
        services = HG.client_controller.services_manager.GetServices( service_types )
        
        service_keys = [ service.GetServiceKey() for service in services ]
        
    
    if unallowed is not None:
        
        service_keys.difference_update( unallowed )
        
    
    if len( service_keys ) == 0:
        
        return None
        
    elif len( service_keys ) == 1:
        
        ( service_key, ) = service_keys
        
        return service_key
        
    else:
        
        services = { HG.client_controller.services_manager.GetService( service_key ) for service_key in service_keys }
        
        choice_tuples = [ ( service.GetName(), service.GetServiceKey() ) for service in services ]
        
        try:
            
            service_key = SelectFromList( HG.client_controller.gui, 'select service', choice_tuples )
            
            return service_key
            
        except HydrusExceptions.CancelledException:
            
            return None
            
        
    
