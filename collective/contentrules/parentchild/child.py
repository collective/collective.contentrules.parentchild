from OFS.SimpleItem import SimpleItem

from zope.interface import implements, Interface
from zope.component import adapts
from zope.formlib import form
from zope import schema
from zope.app.component.hooks import getSite
from zope.i18nmessageid import MessageFactory

from plone.contentrules.rule.interfaces import IExecutable, IRuleElementData

from plone.app.contentrules.browser.formhelper import AddForm, EditForm 

from Acquisition import aq_inner
from Products.CMFCore.utils import getToolByName

_ = MessageFactory('collective.contentrules.parentchild')

class IChildCondition(Interface):
    """A condition to test for the existence of a child object of a given type
    and/or workflow state.
    """
    
    check_types = schema.Set(title=_(u"Content type"),
                              description=_(u"The content type to check for."),
                              required=False,
                              value_type=schema.Choice(vocabulary="plone.app.vocabularies.PortalTypes"))
    
    wf_states = schema.Set(title=_(u"Workflow state"),
                           description=_(u"The workflow states to check for."),
                           required=False,
                           value_type=schema.Choice(vocabulary="plone.app.vocabularies.WorkflowStates"))
    
    recursive = schema.Bool(title=_(u"Recursive"),
                            description=_(u"If selected, the check will apply to child objects "
                                            "contained within other child objects."),
                            required=True,
                            default=True)
    
    min_count = schema.Int(title=_(u"Minimum count"),
                               description=_(u"The minimum number of child objects required"),
                               required=True,
                               min=1,
                               default=1)

    max_count = schema.Int(title=_(u"Maximum count"),
                               description=_(u"The maximum number of child objects required"),
                               min=1,
                               required=False)
         
class ChildCondition(SimpleItem):
    """The actual persistent implementation of the portal type condition element.
    
    Note that we must mix in SimpleItem to keep Zope 2 security happy.
    """
    implements(IChildCondition, IRuleElementData)
    
    check_types = None
    wf_states = None
    recursive = True
    min_count = 1
    max_count = None
    
    element = "collective.contentrules.parentchild.Child"
    
    @property
    def summary(self):
        portal_types = getToolByName(getSite(), 'portal_types')
        
        types = []
        if self.check_types:
            for name in self.check_types:
                fti = getattr(portal_types, name, None)
                if fti is not None:
                    types.append(fti.title or name)
        
        states = self.wf_states or []
        
        return _(u"Child exists of type ${names} and/or state ${states}",
                   mapping=dict(names=", ".join(types), states=','.join(states)))

class ChildConditionExecutor(object):
    """The executor for this condition.
    """
    implements(IExecutable)
    adapts(Interface, IChildCondition, Interface)
         
    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        obj = aq_inner(self.event.object)
        catalog = getToolByName(obj, 'portal_catalog')
        query = {}
        
        obj_path = '/'.join(obj.getPhysicalPath())
        
        if self.element.recursive:
            query['path'] = obj_path
        else:
            query['path'] = {'query': obj_path, 'depth': 1}
        
        if self.element.check_types:
            query['portal_type'] = tuple(self.element.check_types)
        if self.element.wf_states:
            query['review_state'] = tuple(self.element.wf_states)
        
        results = catalog(**query)
        
        if self.element.recursive:
            # without the depth parameter, we could have obtained the source object itself
            results = filter(lambda x: x.getPath() != obj_path, results)
        
        result_count = len(results)
        if result_count < self.element.min_count:
            return False
        
        if self.element.max_count and result_count > self.element.max_count:
            return False
        
        return True
        
class ChildAddForm(AddForm):
    """An add form for portal type conditions.
    """
    form_fields = form.FormFields(IChildCondition)
    label = _(u"Add Content Type Condition")
    description = _(u"A portal type condition makes the rule apply only to certain content types.")
    form_name = _(u"Configure element")
    
    def create(self, data):
        c = ChildCondition()
        form.applyChanges(c, self.form_fields, data)
        return c

class ChildEditForm(EditForm):
    """An edit form for portal type conditions
    """
    form_fields = form.FormFields(IChildCondition)
    label = _(u"Edit Content Type Condition")
    description = _(u"A portal type condition makes the rule apply only to certain content types.")
    form_name = _(u"Configure element")
