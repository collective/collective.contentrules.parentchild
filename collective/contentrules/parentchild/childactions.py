from OFS.SimpleItem import SimpleItem

from zope.interface import implements, Interface
from zope.component import adapts
from zope.component import queryUtility, getMultiAdapter
from zope.formlib.form import FormFields
from z3c.form.form import applyChanges

from zope import schema
from zope.i18nmessageid import MessageFactory

from plone.contentrules.rule.interfaces import IExecutable, IRuleElementData
from plone.contentrules.engine.interfaces import IRuleStorage

from plone.app.contentrules.browser.formhelper import AddForm, EditForm 
from plone.app.contentrules.browser.formhelper import ContentRuleFormWrapper

from Acquisition import aq_parent, aq_chain
from Products.CMFCore.utils import getToolByName

from Products.CMFPlone import utils
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.z3cform.widget import QueryStringFieldWidget
from plone.autoform import directives as form
from zope.interface import provider
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary

_ = MessageFactory('collective.contentrules.parentchild')

@provider(IContextSourceBinder)
def action_sources(context):
    terms = [SimpleVocabulary.createTerm('__this__','__this__', 'This Rule: (excluding this action)')]
    storage = queryUtility(IRuleStorage)
    for rule in storage.values():
        if rule == context.__parent__:
            continue
        terms.append(SimpleVocabulary.createTerm(rule.__name__, rule.__name__, rule.title))
    # TODO: put in the events too?

    return SimpleVocabulary(terms)

class IChildAction(Interface):
    """An action to execute procedding actions on current items children or other items that match a query
    """

    query = schema.List(
        title=_(u'Search terms'),
        description=_(u'Define the search terms for the items you want '
                      u'to apply the following actions to, by choosing what to match on. '
                      u'The list of results will be dynamically updated'),
        value_type=schema.Dict(value_type=schema.Field(),
                               key_type=schema.TextLine()),
        default=[{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::1"}],
        required=False,
        missing_value=''
    )
    form.widget('query', QueryStringFieldWidget)

    action_source = schema.Choice(
        title=_(u'Actions'),
        description=_(u'Which actions to trigger on the query results'),
        source=action_sources,
        default='__this__'
    )
    
    # TODO: optional event to fire on children? or maybe pick a rule name?
         
class ChildAction(SimpleItem):
    """The actual persistent implementation of the action element.
    """
    implements(IChildAction, IRuleElementData)
    
    query = {}

    action_source = None
    
    element = "collective.contentrules.parentchild.ChildAction"
    
    @property
    def summary(self):
        return _(u"Execute proceeding actions eleents with the following query")
        # TODO: describe query
    
class ChildActionExecutor(object):
    """The executor for this action.
    """
    implements(IExecutable)
    adapts(Interface, IChildAction, Interface)
         
    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):

        storage = queryUtility(IRuleStorage)
        remaining_actions = None
        if self.element.action_source == '__this__':
            # iterate over all actions in all rules to find this one
            rule = storage.get(self.element.__parent__.__name__, None)
            if rule is None:
                return False # TODO: or should raise error?
            remaining_actions = [a for a in rule.actions if a != self.element]
            # for rule in storage.values():
            #     for action in rule.actions:
            #         if action == self.element:
            #             remaining_actions = []
            #         elif remaining_actions is not None:
            #             remaining_actions.append(action)
            #     if remaining_actions is not None:
            #         break
        else:
            rule = storage.get(self.element.action_source, None)
            if rule is not None:
                # rule is Executable so this will result in conditions being checked too. Ignores event though
                remaining_actions = [rule]

        if remaining_actions is None:
            return False

        # get the results of the query
        querybuilder = getMultiAdapter((self.context, self.context.REQUEST),
                                       name='querybuilderresults')
        results = querybuilder(
            query=self.element.query, batch=False, limit=1000, brains=False, 
        )

        # execute remaining actions for each of the results
        original_object = self.event.object
        for sub in results:
            self.event.object = sub
            for action in remaining_actions:
                # original context is aq_parent(aq_inner(event.object)). Should this be the same?
                executable = getMultiAdapter((self.context, action, self.event), IExecutable)
                if not executable():
                    break

        # we don't want to continue the rule with the original event
        self.event.object = original_object        
        return False



    def error(self, obj, error):
        request = getattr(self.context, 'REQUEST', None)
        if request is not None:
            title = utils.pretty_title_or_id(obj, obj)
            message = _(u"Unable to change state of ${name} as part of content rule 'workflow' action: ${error}",
                          mapping={'name' : title, 'error' : error})
            IStatusMessage(request).addStatusMessage(message, type="error")
        
class ChildActionAddForm(AddForm):
    """An add form for query action
    """
    schema = IChildAction
    label = _(u"Add Query Action")
    description = _(u"This action triggers a futher actions on objects queried")
    Type = ChildAction

    def create(self, data):
        a = self.Type()
        applyChanges(self, a, data)
        return a


class ChildActionAddFormView(ContentRuleFormWrapper):
    form = ChildActionAddForm


class ChildActionEditForm(EditForm):
    """An edit form for workflow rule actions.
    """
    schema = IChildAction
    label = _(u"Edit Query Action")
    description = _(u"This action triggers further actions on objects queried")
    form_name = _(u"Configure element")



class ChildActionEditFormView(ContentRuleFormWrapper):
    form = ChildActionEditForm
