from unittest import defaultTestLoader
import unittest

from zope.interface import implementer
from zope.component import getUtility, getMultiAdapter

from zope.component.interfaces import IObjectEvent

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleCondition
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.child import ChildCondition
from collective.contentrules.parentchild.child import ChildEditForm

from plone.app.contentrules.rule import Rule

from collective.contentrules.parentchild.testing import FUNCTIONAL_TESTING


@implementer(IObjectEvent)
class DummyEvent(object):

    def __init__(self, obj):
        self.object = obj


class TestChildCondition(unittest.TestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.folder

    def testRegistered(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        self.assertEqual('collective.contentrules.parentchild.Child', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)

    def testInvokeAddView(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')

        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+condition')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview).form_instance

        addview.updateFields()
        condition = addview.create(data={'check_types': set(['Folder', 'Image']),
                                         'wf_states': set(['published']),
                                         'recursive': True,
                                         'min_count': 2,
                                         'max_count': 3})
        addview.add(condition)

        e = rule.conditions[0]
        self.assertTrue(isinstance(e, ChildCondition))
        self.assertEqual(set(['Folder', 'Image']), e.check_types)
        self.assertEqual(set(['published']), e.wf_states)
        self.assertEqual(True, e.recursive)
        self.assertEqual(2, e.min_count)
        self.assertEqual(3, e.max_count)

    def testInvokeEditView(self):
        element = getUtility(IRuleCondition, name='collective.contentrules.parentchild.Child')
        e = ChildCondition()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview).form_instance
        self.assertTrue(isinstance(editview, ChildEditForm))

    def testExecuteType(self):
        e = ChildCondition()
        e.check_types = ['Document', 'Image']
        e.wf_states = None
        e.recursive = False
        e.min_count = 1
        e.max_count = None

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

        self.folder.invokeFactory('Document', 'd2')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

    def testExecuteWorkflow(self):
        e = ChildCondition()
        e.check_types = None
        e.wf_states = set(['published'])
        e.recursive = False
        e.min_count = 1
        e.max_count = None

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd2')
        self.portal.portal_workflow.doActionFor(self.folder.d2, 'publish')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

    def testExecuteCountMin(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = False
        e.min_count = 2
        e.max_count = None

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd2')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

    def testExecuteCountMinMax(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = False
        e.min_count = 2
        e.max_count = 3

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Document', 'd2')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

        self.folder.invokeFactory('Document', 'd3')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

        self.folder.invokeFactory('Document', 'd4')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

    def testExecuteRecursive(self):
        e = ChildCondition()
        e.check_types = set(['Document', 'Image'])
        e.wf_states = None
        e.recursive = True
        e.min_count = 1
        e.max_count = None

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.invokeFactory('Folder', 'f1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.f1.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())

    def testExecuteRecursiveDoesNotCountSelf(self):
        e = ChildCondition()
        e.check_types = set(['Folder', 'Document'])
        e.wf_states = None
        e.recursive = True
        e.min_count = 1
        e.max_count = None

        self.folder.invokeFactory('Folder', 'f1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder.f1)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.f1.invokeFactory('Folder', 'f11')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder.f1)), IExecutable)
        self.assertEqual(True, ex())

    def testExecuteComplex(self):
        e = ChildCondition()
        e.check_types = set(['Folder', 'Document'])
        e.wf_states = set(['published'])
        e.recursive = True
        e.min_count = 2
        e.max_count = 3

        self.folder.invokeFactory('Folder', 'f1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.folder.f1.invokeFactory('Document', 'd1')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.portal.portal_workflow.doActionFor(self.folder.f1, 'publish')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(False, ex())

        self.portal.portal_workflow.doActionFor(self.folder.f1.d1, 'publish')

        ex = getMultiAdapter((self.portal, e, DummyEvent(self.folder)), IExecutable)
        self.assertEqual(True, ex())


def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)
