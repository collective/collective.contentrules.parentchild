from OFS.SimpleItem import SimpleItem

from zope.interface import implements, Interface
from zope.component import adapts
from zope.component import queryUtility, getMultiAdapter
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

class IQuerySplitter(Interface):
    """A special condition that will execute a rule on the results of a query instead of the original event context.
    """


    action_source = schema.Choice(
        title=_(u'Rule'),
        description=_(u'For all results of the query fire this rule'),
        source=action_sources,
        default='__this__'
    )

    query = schema.List(
        title=_(u'Query'),
        description=_(u'Query to find related items to fire a rule against. For example all children of the item that fired the event'),
        value_type=schema.Dict(value_type=schema.Field(),
                               key_type=schema.TextLine()),
        default=[{"i": "path", "o": "plone.app.querystring.operation.string.relativePath", "v": ".::1"}],
        required=False,
        missing_value=''
    )
    form.widget('query', QueryStringFieldWidget)
    
    # TODO: optional event to fire on children? or maybe pick a rule name?
         
class QuerySplitter(SimpleItem):
    """The actual persistent implementation of the query splitter.
    """
    implements(IQuerySplitter, IRuleElementData)
    
    query = {}

    action_source = None
    
    element = "collective.contentrules.parentchild.QuerySplitter"
    
    @property
    def summary(self):
        return _(u"Execute ${rule} rule on query: ${query}", mapping=dict(rule=self.action_source, query=self.query))
        # TODO: describe query
    
class QuerySplitterExecutor(object):
    """The executor for this condition.
    """
    implements(IExecutable)
    adapts(Interface, IQuerySplitter, Interface)
         
    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):

        storage = queryUtility(IRuleStorage)
        remaining = None
        # TODO: this could result in loops.
        if self.element.action_source == '__this__':
            # iterate over all actions in all rules to find this one

            #rule = [rule for rule in storage.values() if any([a for a in rule.actions if a == self.element])].pop()
            for rule in storage.values():
                for executable in rule.conditions + rule.actions:
                    if remaining is not None:
                        remaining.append(executable)
                    elif executable == self.element:
                        remaining = []
                if remaining is not None:
                    break
        else:
            rule = storage.get(self.element.action_source, None)
            if rule is not None:
                # rule is Executable so this will result in conditions being checked too. Ignores event though
                remaining = [rule]

        if remaining is None:
            return False

        # get the results of the query
        querybuilder = getMultiAdapter((self.event.object, self.context.REQUEST),
                                       name='querybuilderresults')
        results = querybuilder(
            query=self.element.query, batch=False, limit=1000, brains=False, 
        )

        # execute remaining actions for each of the results
        original_object = self.event.object
        for sub in results:
            self.event.object = sub.getObject()
            for action in remaining:
                # original context is aq_parent(aq_inner(event.object)). Should this be the same?
                executable = getMultiAdapter((self.context, action, self.event), IExecutable)
                if not executable():
                    # TODO: we stop just teh current execution, not the whole search
                    break

        self.event.object = original_object        
        # we don't want to continue the rule with the original event
        return False



class QuerySplitterAddForm(AddForm):
    """An add form for query splitter
    """
    schema = IQuerySplitter
    label = _(u"Add Query Splitter")
    description = _(u"Special condition which executes a given rule on all results of a query")
    Type = QuerySplitter

    def create(self, data):
        a = self.Type()
        applyChanges(self, a, data)
        return a


class QuerySplitterAddFormView(ContentRuleFormWrapper):
    form = QuerySplitterAddForm


class QuerySplitterEditForm(EditForm):
    """An edit form for the query splitter.
    """
    schema = IQuerySplitter
    label = _(u"Edit Query Splitter")
    description = _(u"Special condition which executes a given rule on all results of a query")
    form_name = _(u"Configure element")



class QuerySplitterEditFormView(ContentRuleFormWrapper):
    form = QuerySplitterEditForm
