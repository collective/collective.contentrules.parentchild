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
from Acquisition import aq_parent, aq_inner, aq_base
from Acquisition.interfaces import IAcquirer
from ZODB.POSException import ConflictError
from Products.CMFCore.utils import getToolByName

from Products.CMFPlone import utils
from Products.statusmessages.interfaces import IStatusMessage

_ = MessageFactory('collective.contentrules.parentchild')

class IParentTransitionAction(Interface):
    """An action to transition a parent object.
    """
    
    transition = schema.Choice(title=_(u"Transition"),
                               description=_(u"Select the workflow transition to attempt"),
                               required=True,
                               vocabulary='plone.app.vocabularies.WorkflowTransitions')
    
    check_types = schema.Set(title=_(u"Content type"),
                              description=_(u"The content type of the parent. If not given, the "
                                             "immediate parent will be transitioned. If given, the "
                                             "closest parent of a type matching the selected type(s) "
                                             "will be used."),
                              required=False,
                              value_type=schema.Choice(title=_(u"Type"),
                                                       vocabulary="plone.app.vocabularies.PortalTypes"))
         
@implementer(IParentTransitionAction, IRuleElementData)
class ParentTransitionAction(SimpleItem):
    """The actual persistent implementation of the action element.
    """
    
    transition = ''
    check_types = None
    
    element = "collective.contentrules.parentchild.ParentTransition"
    
    @property
    def summary(self):
        return _(u"Execute transition ${transition} on parent", mapping=dict(transition=self.transition))
    
@implementer(IExecutable)    
class ParentTransitionActionExecutor(object):
    """The executor for this action.
    """
    
    adapts(Interface, IParentTransitionAction, Interface)
         
    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        portal_workflow = getToolByName(self.context, 'portal_workflow', None)
        if portal_workflow is None:
            return False
            
        obj = aq_parent(self.event.object)
        
        if self.element.check_types:
            obtained = False
            for obj in aq_chain(obj):
                if getattr(obj, 'portal_type', None) in self.element.check_types:
                    obtained = True
                    break
            if not obtained:
                return False
        
        try:
            portal_workflow.doActionFor(obj, self.element.transition)
        except ConflictError as e:
            raise e
        except Exception as e:
            self.error(obj, str(e))
            return False
        
        return True 

    def error(self, obj, error):
        request = getattr(self.context, 'REQUEST', None)
        if request is not None:
            title = utils.pretty_title_or_id(obj, obj)
            message = _(u"Unable to change state of ${name} as part of content rule 'workflow' action: ${error}",
                          mapping={'name' : title, 'error' : error})
            IStatusMessage(request).addStatusMessage(message, type="error")
        
class ParentTransitionAddForm(AddForm):
    """An add form for workflow actions.
    """
    schema = IParentTransitionAction
    label = _(u"Add Parent Transition Action")
    description = _(u"This action triggers a workflow transition on a parent object.")
    form_name = _(u"Configure element")
    Type = ParentTransitionAction
    
    def create(self, data):
        obj = self.Type()
        container = aq_inner(self.context)

        if IAcquirer.providedBy(obj):
            obj = obj.__of__(container)
        applyChanges(self, obj, data)
        obj = aq_base(obj)
        return obj

class ParentTransitionEditForm(EditForm):
    """An edit form for workflow rule actions.
    """
    schema = IParentTransitionAction
    label = _(u"Edit PArent Transition Action")
    description = _(u"This action triggers a workflow transition on a parent object.")
    form_name = _(u"Configure element")

class ParentTransitionAddFormView(ContentRuleFormWrapper):
    form = ParentTransitionAddForm

class ParentTransitionEditFormView(ContentRuleFormWrapper):
    form = ParentTransitionEditForm
