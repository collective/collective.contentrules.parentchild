from OFS.SimpleItem import SimpleItem

from zope.interface import implementer, Interface
from zope.component import adapts
from zope import schema
from zope.i18nmessageid import MessageFactory
from z3c.form.form import applyChanges

from plone.contentrules.rule.interfaces import IExecutable, IRuleElementData

from plone.app.contentrules.browser.formhelper import AddForm, EditForm 
from plone.app.contentrules.browser.formhelper import ContentRuleFormWrapper

from Acquisition import aq_parent, aq_chain
from Products.CMFCore.utils import getToolByName

from Products.CMFPlone import utils
from Products.statusmessages.interfaces import IStatusMessage

_ = MessageFactory('collective.contentrules.parentchild')

class IAutoTransitionAction(Interface):
    """An action to invoke automatic transitions on the current or a parent
    object.
    """

    parent = schema.Bool(title=_(u"Use parent"),
                         description=_(u"If selected, automatic transitions will be invoked "
                                        "on the parent of the current object."),
                         required=True,
                         default=False)
    
    check_types = schema.Set(title=_(u"Content type"),
                             description=_(u"The content type of the object to invoke automatic transitions one. "
                                            "If not given, the current object or immediate parent (depending on "
                                            "the setting above) will be used. If given, the closest object of a "
                                            "type matching the selected type(s) will be used."),
                             required=False,
                             value_type=schema.Choice(title=_(u"Type"),
                                                       vocabulary="plone.app.vocabularies.PortalTypes"))
         
@implementer(IAutoTransitionAction, IRuleElementData)
class AutoTransitionAction(SimpleItem):
    """The actual persistent implementation of the action element.
    """
    
    parent = True
    check_types = None
    
    element = "collective.contentrules.parentchild.AutoTransition"
    
    @property
    def summary(self):
        if not self.parent:
            return _(u"Execute automatic transitions on the current object")
        else:
            return _(u"Execute automatic transitions on a parent object")
    
@implementer(IExecutable)
class AutoTransitionActionExecutor(object):
    """The executor for this action.
    """
    adapts(Interface, IAutoTransitionAction, Interface)
         
    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        portal_workflow = getToolByName(self.context, 'portal_workflow', None)
        if portal_workflow is None:
            return False
        
        obj = self.event.object
        
        if self.element.parent:
            obj = aq_parent(obj)
        
        if self.element.check_types:
            obtained = False
            for obj in aq_chain(obj):
                if getattr(obj, 'portal_type', None) in self.element.check_types:
                    obtained = True
                    break
            if not obtained:
                return False
        
        chain = list(portal_workflow.getChainFor(obj))
        chain.reverse()
        changed = False
        for wfid in chain:
            workflow = portal_workflow.getWorkflowById(wfid)
            sdef = workflow._getWorkflowStateOf(obj)
            if sdef is None:
                continue
            tdef = workflow._findAutomaticTransition(obj, sdef)
            if tdef is None:
                continue
            changed = True
            workflow._changeStateOf(obj, tdef)
        if changed:
            portal_workflow._reindexWorkflowVariables(obj)
        
        return True 

    def error(self, obj, error):
        request = getattr(self.context, 'REQUEST', None)
        if request is not None:
            title = utils.pretty_title_or_id(obj, obj)
            message = _(u"Unable to change state of ${name} as part of content rule 'workflow' action: ${error}",
                          mapping={'name' : title, 'error' : error})
            IStatusMessage(request).addStatusMessage(message, type="error")
        
class AutoTransitionAddForm(AddForm):
    """An add form for workflow actions.
    """
    schema = IAutoTransitionAction
    label = _(u"Add Auto Transition Action")
    description = _(u"This action triggers a workflow transition on a parent object.")
    form_name = _(u"Configure element")
    Type = AutoTransitionAction
    
    def create(self, data):
        a = self.Type()
        applyChanges(self, a, data)
        return a

class AutoTransitionEditForm(EditForm):
    """An edit form for workflow rule actions.
    """
    schema = IAutoTransitionAction
    label = _(u"Edit PArent Transition Action")
    description = _(u"This action triggers a workflow transition on a parent object.")
    form_name = _(u"Configure element")


class AutoTransitionAddFormView(ContentRuleFormWrapper):
    form = AutoTransitionAddForm

class AutoTransitionEditFormView(ContentRuleFormWrapper):
    form = AutoTransitionEditForm
