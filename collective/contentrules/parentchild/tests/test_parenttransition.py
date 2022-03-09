from unittest import defaultTestLoader

from zope.interface import implementer
from zope.component import getUtility, getMultiAdapter

from plone.contentrules.engine.interfaces import IRuleStorage
from plone.contentrules.rule.interfaces import IRuleAction
from plone.contentrules.rule.interfaces import IExecutable

from collective.contentrules.parentchild.parenttransition import ParentTransitionAction
from collective.contentrules.parentchild.parenttransition import ParentTransitionEditForm

from plone.app.contentrules.rule import Rule

from zope.component.interfaces import IObjectEvent

from Products.CMFPlone.utils import _createObjectByType

from collective.contentrules.parentchild.testing import FUNCTIONAL_TESTING
import unittest


@implementer(IObjectEvent)
class DummyEvent(object):

    def __init__(self, object):
        self.object = object


class TestParentTransitionAction(unittest.TestCase):

    layer = FUNCTIONAL_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.folder = self.portal.folder
        self.folder.invokeFactory('Folder', 'f1')
        self.folder.f1.invokeFactory('Document', 'd1')

    def testRegistered(self):
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        self.assertEqual('collective.contentrules.parentchild.ParentTransition', element.addview)
        self.assertEqual('edit', element.editview)
        self.assertEqual(None, element.for_)
        self.assertEqual(IObjectEvent, element.event)

    def testInvokeAddView(self):
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        storage = getUtility(IRuleStorage)
        storage[u'foo'] = Rule()
        rule = self.portal.restrictedTraverse('++rule++foo')

        adding = getMultiAdapter((rule, self.portal.REQUEST), name='+action')
        addview = getMultiAdapter((adding, self.portal.REQUEST), name=element.addview).form_instance

        addview.updateFields()
        addview.add(addview.create(data={'transition': 'publish', 'check_types': set(['Document'])}))

        e = rule.actions[0]
        self.assertTrue(isinstance(e, ParentTransitionAction))
        self.assertEqual('publish', e.transition)
        self.assertEqual(set(['Document']), e.check_types)

    def testInvokeEditView(self):
        element = getUtility(IRuleAction, name='collective.contentrules.parentchild.ParentTransition')
        e = ParentTransitionAction()
        editview = getMultiAdapter((e, self.folder.REQUEST), name=element.editview).form_instance
        self.assertTrue(isinstance(editview, ParentTransitionEditForm))

    def testExecute(self):
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = None

        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteWithError(self):
        e = ParentTransitionAction()
        e.transition = 'foobar'
        e.check_types = None

        old_state = self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state')

        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(False, ex())

        self.assertEqual(old_state, self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeImmediateParent(self):
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = set(['Folder'])

        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.d1)), IExecutable)
        self.assertEqual(True, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))

    def testExecuteTypeNestedParent(self):
        e = ParentTransitionAction()
        e.transition = 'publish'
        e.check_types = set(['Folder'])

        _createObjectByType('Folder', self.folder.f1, id='f2')
        self.folder.f1.f2.invokeFactory('Document', 'd2')

        old_state = self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state')

        self.folder.f1.f2.portal_type = 'Not Folder'
        ex = getMultiAdapter((self.folder, e, DummyEvent(self.folder.f1.f2.d1)), IExecutable)
        self.assertEqual(True, ex())

        self.assertEqual('published', self.portal.portal_workflow.getInfoFor(self.folder.f1, 'review_state'))
        self.folder.f1.f2.portal_type = 'Folder'
        self.assertEqual(old_state, self.portal.portal_workflow.getInfoFor(self.folder.f1.f2, 'review_state'))


def test_suite():
    return defaultTestLoader.loadTestsFromName(__name__)
