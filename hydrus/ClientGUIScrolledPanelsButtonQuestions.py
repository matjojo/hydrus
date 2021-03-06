from . import ClientConstants as CC
from . import ClientGUICommon
from . import ClientGUIScrolledPanels
from . import HydrusGlobals as HG
from qtpy import QtCore as QC
from qtpy import QtWidgets as QW
from . import QtPorting as QP

class QuestionCommitInterstitialFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit and continue', self.parentWidget().done, QW.QDialog.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        self._back = ClientGUICommon.BetterButton( self, 'go back', self.parentWidget().done, QW.QDialog.Rejected )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( label, self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._commit, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( '-or-', self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        HG.client_controller.CallAfterQtSafe( self._commit, self._commit.setFocus, QC.Qt.OtherFocusReason )
        
    
class QuestionFinishFilteringPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, label ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._commit = ClientGUICommon.BetterButton( self, 'commit', self.parentWidget().done, QW.QDialog.Accepted )
        self._commit.setObjectName( 'HydrusAccept' )
        
        self._forget = ClientGUICommon.BetterButton( self, 'forget', self.parentWidget().done, QW.QDialog.Rejected )
        self._forget.setObjectName( 'HydrusCancel' )
        
        def cancel_callback( parent ):
            
            parent.SetCancelled( True )
            parent.done( QW.QDialog.Rejected )
            
        
        self._back = ClientGUICommon.BetterButton( self, 'back to filtering', cancel_callback, parent )
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._commit, CC.FLAGS_EXPAND_BOTH_WAYS )
        QP.AddToLayout( hbox, self._forget, CC.FLAGS_EXPAND_BOTH_WAYS )
        
        vbox = QP.VBoxLayout()
        
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( label, self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_EXPAND_SIZER_PERPENDICULAR )
        QP.AddToLayout( vbox, QP.MakeQLabelWithAlignment( '-or-', self, QC.Qt.AlignVCenter | QC.Qt.AlignHCenter ), CC.FLAGS_EXPAND_PERPENDICULAR )
        QP.AddToLayout( vbox, self._back, CC.FLAGS_EXPAND_PERPENDICULAR )
        
        self.widget().setLayout( vbox )
        
        HG.client_controller.CallAfterQtSafe( self._commit, self._commit.setFocus, QC.Qt.OtherFocusReason )
        
    
class QuestionYesNoPanel( ClientGUIScrolledPanels.ResizingScrolledPanel ):
    
    def __init__( self, parent, message, yes_label = 'yes', no_label = 'no' ):
        
        ClientGUIScrolledPanels.ResizingScrolledPanel.__init__( self, parent )
        
        self._yes = ClientGUICommon.BetterButton( self, yes_label, self.parentWidget().done, QW.QDialog.Accepted )
        self._yes.setObjectName( 'HydrusAccept' )
        self._yes.setText( yes_label )
        
        self._no = ClientGUICommon.BetterButton( self, no_label, self.parentWidget().done, QW.QDialog.Rejected )
        self._no.setObjectName( 'HydrusCancel' )
        self._no.setText( no_label )
        
        #
        
        hbox = QP.HBoxLayout()
        
        QP.AddToLayout( hbox, self._yes )
        QP.AddToLayout( hbox, self._no )
        
        vbox = QP.VBoxLayout()
        
        text = ClientGUICommon.BetterStaticText( self, message )
        text.setWordWrap( True )
        
        QP.AddToLayout( vbox, text )
        QP.AddToLayout( vbox, hbox, CC.FLAGS_BUTTON_SIZER )
        
        self.widget().setLayout( vbox )
        
        HG.client_controller.CallAfterQtSafe( self._yes, self._yes.setFocus, QC.Qt.OtherFocusReason )
        
    

