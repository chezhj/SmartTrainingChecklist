from django.db import IntegrityError
from django.forms import ValidationError
from django.test import TestCase
from django.utils.text import slugify

# Create your tests here.
from checklist.models import CheckItem
from checklist.models import Procedure
from checklist.models import Attribute, SessionProfile


class testCheckItem(TestCase):
    def setUp(self):
        defaultProcedure = Procedure.objects.create(title="procedure one", step=1)
        Attribute.objects.create(title="left", order=1)
        Attribute.objects.create(title="right", order=2)
        Attribute.objects.create(title="center", order=3)
        profile = SessionProfile.objects.create(sessionId=1)
        profile.attributes.add(Attribute.objects.get(title="left"))

        CheckItem.objects.create(item="item one", procedure=defaultProcedure, step=3)
        CheckItem.objects.create(item="item two", procedure=defaultProcedure, step=1)
        item = CheckItem.objects.create(
            item="item three", procedure=defaultProcedure, step=5
        )

    def test_OrderCheckItem(self):
        items = CheckItem.objects.all()
        self.assertEqual(items[0].step, 1)
        self.assertEqual(items[1].step, 3)
        self.assertEqual(items[2].step, 5)

    def test_strCheckItem(self):
        item = CheckItem.objects.get(item="item three")
        self.assertEqual(str(item), item.item)

    def test_negative_step(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        with self.assertRaises(IntegrityError):
            CheckItem.objects.create(item="item three", procedure=procedure, step=-5)

    def test_cascade_delete(self):
        item = CheckItem.objects.get(item="item three")
        item.procedure.delete()
        with self.assertRaises(CheckItem.DoesNotExist):
            item.refresh_from_db()

    def test_negative_step(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        with self.assertRaises(IntegrityError):
            CheckItem.objects.create(item="item three", procedure=procedure, step=-5)

    def test_toolong_itemname(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        too_long_string = "item name" * 10
        item = CheckItem.objects.create(
            item=too_long_string, procedure=procedure, step=8
        )
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_toolong_setting(self):
        procedure = CheckItem.objects.get(item="item three").procedure
        too_long_string = "item name" * 10
        item = CheckItem.objects.create(item="test item", procedure=procedure, step=8)
        item.setting = too_long_string
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_shouldshow_with_no_attributes(self):
        item = CheckItem.objects.get(item="item three")
        self.assertTrue(item.shouldshow(SessionProfile.objects.get(sessionId=1)))

    def test_shouldshow_with_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="left"))
        self.assertTrue(item.shouldshow(SessionProfile.objects.get(sessionId=1)))

    def test_should_NOT_show_with_NON_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        self.assertFalse(item.shouldshow(SessionProfile.objects.get(sessionId=1)))

    def test_should_show_with_ONE_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        # prepare profile with two attributes
        profile = SessionProfile.objects.get(sessionId=1)
        profile.attributes.add(Attribute.objects.get(title="right"))

        self.assertTrue(item.shouldshow(SessionProfile.objects.get(sessionId=1)))

    def test_should_show_with_ALL_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        item.attributes.add(Attribute.objects.get(title="left"))
        # prepare profile with two attributes
        profile = SessionProfile.objects.get(sessionId=1)
        profile.attributes.add(Attribute.objects.get(title="right"))

        self.assertTrue(item.shouldshow(SessionProfile.objects.get(sessionId=1)))

    def test_should_NOT_show_with_two_and_one_matching_attributes(self):
        item = CheckItem.objects.get(item="item three")
        item.attributes.add(Attribute.objects.get(title="right"))
        item.attributes.add(Attribute.objects.get(title="left"))
        # prepare profile with two attributes
        profile = SessionProfile.objects.get(sessionId=1)

        self.assertFalse(item.shouldshow(SessionProfile.objects.get(sessionId=1)))


class testProcedure(TestCase):
    def setUp(self):
        defaultProcedure = Procedure.objects.create(title="procedure one", step=1)
        defaultProcedure.slug = slugify(defaultProcedure.title)
        defaultProcedure.step = 4
        defaultProcedure.save()

        CheckItem.objects.create(item="item one", procedure=defaultProcedure, step=3)
        CheckItem.objects.create(item="item two", procedure=defaultProcedure, step=1)
        CheckItem.objects.create(item="item three", procedure=defaultProcedure, step=5)

    def test_strProcedure(self):
        proc = Procedure.objects.get(title="procedure one")
        self.assertEqual(str(proc), proc.title)

    def test_get_absolute_url(self):
        proc = Procedure.objects.get(title="procedure one")
        self.assertEqual(proc.get_absolute_url(), "/checklist/" + proc.slug)


class testAttribute(TestCase):
    def test_title_as_string(self):
        att = Attribute.objects.create(title="left", order=1)
        self.assertEqual(str(att), att.title)