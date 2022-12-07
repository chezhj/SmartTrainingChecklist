from django.test import TestCase

# Create your tests here.
from checklist.models import CheckItem
from checklist.models import Procedure

class testCheckItem(TestCase):

    def setUp(self) :
        defaultProcedure = Procedure.objects.create(title="procedure one", step=1)
        CheckItem.objects.create(item="item one", procedure = defaultProcedure , step=3)
        CheckItem.objects.create(item="item two", procedure = defaultProcedure , step=1)
        CheckItem.objects.create(item="item three", procedure = defaultProcedure , step=5)

    def test_OrderCheckItem(self):
        items=CheckItem.objects.all()
        self.assertEqual(items[0].step,1)
        self.assertEqual(items[1].step,3)
        self.assertEqual(items[2].step,5)

    def test_strCheckItem(self):
        item=CheckItem.objects.get(item="item three")
        self.assertEqual(str(item),item.item)   

class testProcedure(TestCase): 

    def setUp(self) :
        defaultProcedure = Procedure.objects.create(title="procedure one", step=1)
        CheckItem.objects.create(item="item one", procedure = defaultProcedure , step=3)
        CheckItem.objects.create(item="item two", procedure = defaultProcedure , step=1)
        CheckItem.objects.create(item="item three", procedure = defaultProcedure , step=5)

    def test_strProcedure(self):
        proc=Procedure.objects.get(title="procedure one")
        self.assertEqual(str(proc),proc.title)
        

       